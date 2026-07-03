from decimal import Decimal

import agate
import pytest

from dbt.adapters.denodo import DenodoAdapter, Plugin
from dbt.adapters.denodo.column import DenodoColumn
from dbt.adapters.denodo.relation import DenodoRelation
from dbt_common.exceptions import DbtRuntimeError


class TestPlugin:
    def test_plugin_wiring(self):
        assert Plugin.adapter is DenodoAdapter
        assert Plugin.credentials.__name__ == "DenodoCredentials"
        assert Plugin.include_path.endswith("denodo")

    def test_adapter_type(self):
        assert DenodoAdapter.type() == "denodo"


class TestRelation:
    def test_two_level_rendering(self):
        relation = DenodoRelation.create(
            database="analytics", schema="analytics", identifier="my_view"
        )
        # database is never rendered: Denodo namespace is <database>.<view>
        assert relation.render() == "analytics.my_view"

    def test_database_never_rendered(self):
        # dbt keeps target.database on every node while schema varies
        # (e.g. tests' audit schema); database must be carried but ignored.
        relation = DenodoRelation.create(
            database="analytics", schema="analytics_dbt_test__audit", identifier="t"
        )
        assert relation.render() == "analytics_dbt_test__audit.t"

    def test_quoted_rendering(self):
        relation = DenodoRelation.create(
            database="analytics",
            schema="analytics",
            identifier="My View",
            quote_policy={"schema": True, "identifier": True},
        )
        assert relation.render() == '"analytics"."My View"'

    def test_ephemeral_prefix(self):
        assert DenodoRelation.add_ephemeral_prefix("model") == "__dbt__cte__model"


class TestTypeConversions:
    def test_date_function(self):
        assert DenodoAdapter.date_function() == "now()"

    def test_convert_text_type(self):
        table = agate.Table([("x",)], ["a"], [agate.Text()])
        assert DenodoAdapter.convert_text_type(table, 0) == "text"

    def test_convert_integer_number_type(self):
        table = agate.Table([(Decimal("1"),)], ["n"], [agate.Number()])
        assert DenodoAdapter.convert_number_type(table, 0) == "long"

    def test_convert_decimal_number_type(self):
        table = agate.Table([(Decimal("1.5"),)], ["n"], [agate.Number()])
        assert DenodoAdapter.convert_number_type(table, 0) == "double"

    def test_convert_boolean_type(self):
        table = agate.Table([(True,)], ["b"], [agate.Boolean()])
        assert DenodoAdapter.convert_boolean_type(table, 0) == "boolean"

    def test_convert_datetime_type(self):
        table = agate.Table([("2024-01-01T10:00:00",)], ["d"], [agate.DateTime()])
        assert DenodoAdapter.convert_datetime_type(table, 0) == "timestamp"

    def test_convert_date_type(self):
        table = agate.Table([("2024-01-01",)], ["d"], [agate.Date()])
        assert DenodoAdapter.convert_date_type(table, 0) == "date"


class TestColumn:
    def test_string_column(self):
        col = DenodoColumn(column="name", dtype="text", char_size=None)
        assert col.is_string()
        assert not col.is_number()
        assert col.data_type == "text"

    def test_number_columns(self):
        assert DenodoColumn(column="c", dtype="long").is_integer()
        assert DenodoColumn(column="c", dtype="int").is_integer()
        assert DenodoColumn(column="c", dtype="double").is_float()
        assert DenodoColumn(column="c", dtype="decimal").is_numeric()
        assert DenodoColumn(column="c", dtype="decimal").is_number()

    def test_bare_data_type_without_size(self):
        col = DenodoColumn(column="c", dtype="text", char_size=255)
        assert col.data_type == "text"

    def test_string_type(self):
        assert DenodoColumn.string_type(255) == "text"

    def test_numeric_type(self):
        assert DenodoColumn.numeric_type("decimal", 38, 9) == "decimal"

    def test_translate_type(self):
        assert DenodoColumn.translate_type("string") == "TEXT"
        assert DenodoColumn.translate_type("float") == "DOUBLE"
        assert DenodoColumn.translate_type("bigint") == "LONG"


class TestUnsupportedFeatures:
    def test_rename_relation_raises(self):
        adapter = DenodoAdapter.__new__(DenodoAdapter)
        src = DenodoRelation.create(schema="db", identifier="a")
        dst = DenodoRelation.create(schema="db", identifier="b")
        with pytest.raises(DbtRuntimeError, match="rename"):
            adapter.rename_relation(src, dst)

    def test_incremental_strategies(self):
        adapter = DenodoAdapter.__new__(DenodoAdapter)
        assert adapter.valid_incremental_strategies() == ["append", "delete+insert"]

    def test_timestamp_add_sql(self):
        adapter = DenodoAdapter.__new__(DenodoAdapter)
        assert adapter.timestamp_add_sql("now()", 3, "day") == "addday(now(), 3)"
        with pytest.raises(DbtRuntimeError):
            adapter.timestamp_add_sql("now()", 1, "fortnight")
