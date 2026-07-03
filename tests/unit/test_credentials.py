import pytest
from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.denodo.connections import DenodoCredentials


def test_type_and_unique_field():
    creds = DenodoCredentials(host="vdp.example.com", schema="analytics")
    assert creds.type == "denodo"
    assert creds.unique_field == "vdp.example.com"


def test_defaults():
    creds = DenodoCredentials(host="vdp", schema="analytics")
    assert creds.port == 9996
    assert creds.sslmode == "prefer"
    assert creds.connect_timeout == 10
    assert creds.retries == 1


def test_database_defaults_to_schema():
    creds = DenodoCredentials(host="vdp", schema="analytics")
    assert creds.database == "analytics"


def test_matching_database_and_schema_allowed():
    creds = DenodoCredentials(host="vdp", schema="analytics", database="analytics")
    assert creds.database == "analytics"


def test_mismatched_database_raises():
    with pytest.raises(DbtRuntimeError):
        DenodoCredentials(host="vdp", schema="analytics", database="other")


def test_missing_schema_raises():
    with pytest.raises(DbtRuntimeError):
        DenodoCredentials(host="vdp", schema=None)


def test_aliases():
    translated = DenodoCredentials.translate_aliases(
        {"host": "vdp", "dbname": "analytics", "pass": "pw", "username": "u"}
    )
    assert translated["database"] == "analytics"
    assert translated["password"] == "pw"
    assert translated["user"] == "u"


def test_connection_keys_hide_password():
    creds = DenodoCredentials(host="vdp", schema="analytics", password="secret")
    keys = creds._connection_keys()
    assert "password" not in keys
    assert "host" in keys
    assert "schema" in keys
