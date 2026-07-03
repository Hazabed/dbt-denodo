from types import SimpleNamespace
from unittest import mock

import psycopg2
import pytest

from dbt.adapters.contracts.connection import AdapterResponse, ConnectionState
from dbt.adapters.denodo.connections import DenodoConnectionManager, DenodoCredentials


def make_connection(**overrides):
    creds = DenodoCredentials(
        host="vdp.example.com",
        port=9996,
        user="dbt_user",
        password="secret",
        schema="analytics",
        **overrides,
    )
    return SimpleNamespace(
        state=ConnectionState.INIT,
        credentials=creds,
        handle=None,
        name="test",
    )


class TestOpen:
    @mock.patch("dbt.adapters.denodo.connections.psycopg2.connect")
    def test_open_sets_handle_and_state(self, mock_connect):
        connection = make_connection()
        result = DenodoConnectionManager.open(connection)

        assert result.state == ConnectionState.OPEN
        assert result.handle is mock_connect.return_value
        mock_connect.return_value.set_session.assert_called_once_with(autocommit=True)

    @mock.patch("dbt.adapters.denodo.connections.psycopg2.connect")
    def test_open_connects_to_pg_wire_interface(self, mock_connect):
        connection = make_connection()
        DenodoConnectionManager.open(connection)

        kwargs = mock_connect.call_args.kwargs
        assert kwargs["host"] == "vdp.example.com"
        assert kwargs["port"] == 9996
        assert kwargs["user"] == "dbt_user"
        assert kwargs["password"] == "secret"
        # the Denodo virtual database is the pg-wire dbname
        assert kwargs["dbname"] == "analytics"
        assert kwargs["sslmode"] == "prefer"
        assert kwargs["application_name"] == "dbt-denodo"

    @mock.patch("dbt.adapters.denodo.connections.psycopg2.connect")
    def test_open_short_circuits_when_already_open(self, mock_connect):
        connection = make_connection()
        connection.state = ConnectionState.OPEN
        DenodoConnectionManager.open(connection)
        mock_connect.assert_not_called()

    @mock.patch("dbt.adapters.denodo.connections.psycopg2.connect")
    def test_open_retries_operational_errors(self, mock_connect):
        handle = mock.MagicMock()
        mock_connect.side_effect = [psycopg2.OperationalError("boom"), handle]
        connection = make_connection(retries=2)

        result = DenodoConnectionManager.open(connection)

        assert result.state == ConnectionState.OPEN
        assert mock_connect.call_count == 2


class TestGetResponse:
    def test_get_response_with_status(self):
        cursor = SimpleNamespace(statusmessage="SELECT 42", rowcount=42)
        response = DenodoConnectionManager.get_response(cursor)
        assert isinstance(response, AdapterResponse)
        assert response._message == "SELECT 42"
        assert response.rows_affected == 42

    def test_get_response_without_status(self):
        cursor = SimpleNamespace(statusmessage=None, rowcount=None)
        response = DenodoConnectionManager.get_response(cursor)
        assert response._message == "OK"
        assert response.rows_affected == -1


class TestTransactionsAreNoOps:
    def test_add_begin_query_is_noop(self):
        manager = DenodoConnectionManager.__new__(DenodoConnectionManager)
        assert manager.add_begin_query() is None

    def test_add_commit_query_is_noop(self):
        manager = DenodoConnectionManager.__new__(DenodoConnectionManager)
        assert manager.add_commit_query() is None


class TestCancel:
    def test_cancel_calls_handle_cancel(self):
        manager = DenodoConnectionManager.__new__(DenodoConnectionManager)
        connection = make_connection()
        connection.handle = mock.MagicMock()
        manager.cancel(connection)
        connection.handle.cancel.assert_called_once()

    def test_cancel_swallows_unsupported_cancellation(self):
        manager = DenodoConnectionManager.__new__(DenodoConnectionManager)
        connection = make_connection()
        connection.handle = mock.MagicMock()
        connection.handle.cancel.side_effect = RuntimeError("not supported")
        manager.cancel(connection)  # must not raise


class TestDataTypeCodeToName:
    def test_known_oid(self):
        # 25 is the pg OID for text
        assert DenodoConnectionManager.data_type_code_to_name(25).upper() != ""

    def test_unknown_oid(self):
        assert "unknown" in DenodoConnectionManager.data_type_code_to_name(-1)
