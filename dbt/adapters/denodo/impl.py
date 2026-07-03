from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from dbt.adapters.base import AdapterConfig
from dbt.adapters.base.impl import ConstraintSupport
from dbt.adapters.sql import SQLAdapter
from dbt_common.contracts.constraints import ConstraintType
from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.denodo.column import DenodoColumn
from dbt.adapters.denodo.connections import DenodoConnectionManager
from dbt.adapters.denodo.relation import DenodoRelation

if TYPE_CHECKING:
    import agate


@dataclass
class DenodoConfig(AdapterConfig):
    # Optional VDP folder for created elements, e.g. '/dbt'. Only emitted
    # when configured.
    folder: Optional[str] = None


class DenodoAdapter(SQLAdapter):
    """dbt adapter for Denodo Virtual DataPort (Denodo Platform 8).

    Key platform characteristics this adapter accounts for:

    - Two-level namespace: dbt ``schema`` == Denodo virtual database.
    - ``view`` models become VQL derived views (CREATE OR REPLACE VIEW).
    - ``table`` models become materialized tables (CREATE OR REPLACE
      MATERIALIZED TABLE ... AS SELECT), which require the VDP cache engine
      to be enabled.
    - VQL has no RENAME statement, so materializations rely on
      CREATE OR REPLACE instead of the create-swap-drop pattern.
    - Constraints are metadata-only in VDP and are not supported.
    """

    Relation = DenodoRelation
    Column = DenodoColumn
    ConnectionManager = DenodoConnectionManager
    AdapterSpecificConfigs = DenodoConfig

    CONSTRAINT_SUPPORT = {
        ConstraintType.check: ConstraintSupport.NOT_SUPPORTED,
        ConstraintType.not_null: ConstraintSupport.NOT_SUPPORTED,
        ConstraintType.unique: ConstraintSupport.NOT_SUPPORTED,
        ConstraintType.primary_key: ConstraintSupport.NOT_SUPPORTED,
        ConstraintType.foreign_key: ConstraintSupport.NOT_SUPPORTED,
    }

    @classmethod
    def date_function(cls) -> str:
        return "now()"

    @classmethod
    def is_cancelable(cls) -> bool:
        return True

    # === agate type conversions (used by seeds) ===

    @classmethod
    def convert_text_type(cls, agate_table: "agate.Table", col_idx: int) -> str:
        return "text"

    @classmethod
    def convert_number_type(cls, agate_table: "agate.Table", col_idx: int) -> str:
        import agate

        decimals = agate_table.aggregate(agate.MaxPrecision(col_idx))
        return "double" if decimals else "long"

    @classmethod
    def convert_integer_type(cls, agate_table: "agate.Table", col_idx: int) -> str:
        return "long"

    @classmethod
    def convert_boolean_type(cls, agate_table: "agate.Table", col_idx: int) -> str:
        return "boolean"

    @classmethod
    def convert_datetime_type(cls, agate_table: "agate.Table", col_idx: int) -> str:
        return "timestamp"

    @classmethod
    def convert_date_type(cls, agate_table: "agate.Table", col_idx: int) -> str:
        return "date"

    @classmethod
    def convert_time_type(cls, agate_table: "agate.Table", col_idx: int) -> str:
        return "time"

    # === behavior overrides ===

    def check_schema_exists(self, database: str, schema: str) -> bool:
        # Avoids the default information_schema-based macro, which does not
        # exist on Denodo. `list_schemas` is backed by `LIST DATABASES`.
        return schema.lower() in (s.lower() for s in self.list_schemas(database))

    def rename_relation(
        self, from_relation: DenodoRelation, to_relation: DenodoRelation
    ) -> None:
        raise DbtRuntimeError(
            "Denodo VQL does not support renaming views or tables. "
            "dbt-denodo materializations use CREATE OR REPLACE instead; "
            "rename_relation should never be called."
        )

    def valid_incremental_strategies(self) -> List[str]:
        return ["append", "delete+insert"]

    def debug_query(self) -> None:
        # Denodo requires a FROM-less SELECT to be a literal projection;
        # `select 1 as id` works through the pg-wire interface.
        self.execute("select 1 as id")

    def timestamp_add_sql(self, add_to: str, number: int = 1, interval: str = "hour") -> str:
        # VQL: ADDHOUR/ADDDAY/ADDMINUTE/... functions
        interval_fn = {
            "second": "addsecond",
            "minute": "addminute",
            "hour": "addhour",
            "day": "addday",
            "week": "addweek",
            "month": "addmonth",
            "year": "addyear",
        }.get(interval.lower())
        if interval_fn is None:
            raise DbtRuntimeError(f"Unsupported interval for Denodo timestamp_add_sql: {interval}")
        return f"{interval_fn}({add_to}, {number})"

