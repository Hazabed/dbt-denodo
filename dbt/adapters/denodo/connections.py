"""Connection management for the Denodo dbt adapter.

Denodo's officially supported way to connect from Python is the
PostgreSQL-compatible interface of Virtual DataPort (the "ODBC" interface,
port 9996 by default). It is the same interface used by Denodo's official
SQLAlchemy dialect for Denodo 8 (``denodo-sqlalchemy``), and it accepts VQL
statements. The Denodo JDBC driver is a Java artifact and cannot be used
natively from CPython, and the Arrow Flight SQL interface only exists in
Denodo 9.1+, so psycopg2 over port 9996 is the recommended approach for
Denodo Platform 8.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extensions
from dbt.adapters.contracts.connection import (
    AdapterResponse,
    Connection,
    ConnectionState,
    Credentials,
)
from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.sql import SQLConnectionManager
from dbt_common.exceptions import DbtDatabaseError, DbtRuntimeError

logger = AdapterLogger("Denodo")


@dataclass
class DenodoCredentials(Credentials):
    """Profile parameters for connecting to Denodo Virtual DataPort.

    Denodo has a two-level namespace: a *virtual database* containing views.
    There is no separate catalog/schema split, so — like dbt-spark — the dbt
    ``schema`` maps to the Denodo virtual database and ``database`` must be
    omitted or equal to ``schema``.
    """

    host: str = "localhost"
    port: int = 9996
    user: str = ""
    password: str = ""
    database: str | None = None
    schema: str | None = None
    sslmode: str = "prefer"
    connect_timeout: int = 10
    retries: int = 1

    _ALIASES = {
        "dbname": "database",
        "pass": "password",
        "username": "user",
    }

    def __post_init__(self) -> None:
        if not self.schema:
            raise DbtRuntimeError(
                "Must specify `schema` (the Denodo virtual database) in the Denodo profile."
            )
        if self.database is not None and self.database != self.schema:
            raise DbtRuntimeError(
                f"    schema: {self.schema} \n"
                f"    database: {self.database} \n"
                "On Denodo, the dbt `schema` is the Virtual DataPort database. "
                "`database` must be omitted or match `schema`."
            )
        self.database = self.schema

    @property
    def type(self) -> str:
        return "denodo"

    @property
    def unique_field(self) -> str:
        return self.host

    def _connection_keys(self) -> tuple[str, ...]:
        # `database` must be present: dbt builds the `target` jinja context
        # from these keys, and generate_database_name() assigns
        # target.database to every node. Omitting it would leave nodes with
        # an empty database and break relation-cache lookups.
        return (
            "host",
            "port",
            "user",
            "database",
            "schema",
            "sslmode",
            "connect_timeout",
            "retries",
        )


class DenodoConnectionManager(SQLConnectionManager):
    TYPE = "denodo"

    @contextmanager
    def exception_handler(self, sql: str):
        try:
            yield
        except psycopg2.DatabaseError as e:
            logger.debug(f"Denodo error while running:\n{sql}")
            try:
                self.rollback_if_open()
            except Exception:
                logger.debug("Failed to release connection!")
            raise DbtDatabaseError(str(e).strip()) from e
        except Exception as e:
            logger.debug(f"Error while running:\n{sql}")
            self.rollback_if_open()
            if isinstance(e, DbtRuntimeError):
                raise
            raise DbtRuntimeError(str(e)) from e

    @classmethod
    def open(cls, connection: Connection) -> Connection:
        if connection.state == ConnectionState.OPEN:
            logger.debug("Connection is already open, skipping open.")
            return connection

        credentials: DenodoCredentials = connection.credentials

        kwargs: dict[str, Any] = {
            "host": credentials.host,
            "port": credentials.port,
            "user": credentials.user,
            "password": credentials.password,
            # The Denodo virtual database is the pg-wire "dbname".
            "dbname": credentials.schema,
            "sslmode": credentials.sslmode,
            "connect_timeout": credentials.connect_timeout,
            "application_name": "dbt-denodo",
        }

        def connect() -> psycopg2.extensions.connection:
            handle = psycopg2.connect(**kwargs)
            # VQL DDL is not transactional; run everything in autocommit and
            # treat dbt's BEGIN/COMMIT bookkeeping as no-ops (see
            # add_begin_query/add_commit_query below).
            handle.set_session(autocommit=True)
            return handle

        retryable_exceptions: list[type] = [psycopg2.OperationalError]

        return cls.retry_connection(
            connection,
            connect=connect,
            logger=logger,
            retry_limit=credentials.retries,
            retryable_exceptions=retryable_exceptions,
        )

    def cancel(self, connection: Connection) -> None:
        connection_name = connection.name
        try:
            logger.debug(f"Cancelling query on connection '{connection_name}'")
            connection.handle.cancel()
        except psycopg2.InterfaceError as exc:
            if "already closed" in str(exc):
                logger.debug(f"Connection '{connection_name}' was already closed")
                return
            raise
        except Exception as exc:
            # Denodo's pg-wire interface may not implement the PostgreSQL
            # cancellation protocol; failing to cancel must not crash dbt.
            logger.warning(f"Failed to cancel query on '{connection_name}': {exc}")

    @classmethod
    def get_response(cls, cursor: Any) -> AdapterResponse:
        message = str(cursor.statusmessage) if cursor.statusmessage else "OK"
        rows = cursor.rowcount if cursor.rowcount is not None else -1
        return AdapterResponse(_message=message, rows_affected=rows)

    def add_begin_query(self):
        # Connections run in autocommit; VQL DDL is not transactional.
        pass

    def add_commit_query(self):
        pass

    @classmethod
    def data_type_code_to_name(cls, type_code: Any) -> str:
        string_types = psycopg2.extensions.string_types
        if type_code in string_types:
            return string_types[type_code].name
        return f"unknown type_code {type_code}"
