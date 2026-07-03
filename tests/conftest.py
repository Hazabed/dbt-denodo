import os

import pytest

# Import the dbt functional-testing fixtures (project, adapter, etc.)
pytest_plugins = ["dbt.tests.fixtures.project"]


@pytest.fixture(scope="class")
def dbt_profile_target():
    return {
        "type": "denodo",
        "threads": 1,
        "host": os.getenv("DENODO_TEST_HOST", "localhost"),
        "port": int(os.getenv("DENODO_TEST_PORT", "9996")),
        "user": os.getenv("DENODO_TEST_USER", "admin"),
        "password": os.getenv("DENODO_TEST_PASSWORD", "admin"),
        "schema": os.getenv("DENODO_TEST_DATABASE", "dbt_test"),
    }
