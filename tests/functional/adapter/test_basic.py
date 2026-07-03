"""Standard dbt-tests-adapter basic suite.

Requires a live Denodo VDP 8 server (see test.env.example). The connected
user needs CREATE DATABASE privileges because the framework creates a
unique schema (virtual database) per test, and the server needs the cache
engine enabled for table/seed/incremental materializations.

Snapshot tests are omitted: snapshots are not supported on Denodo (no
MERGE, no RENAME in VQL).
"""

import pytest

from dbt.tests.adapter.basic.test_adapter_methods import BaseAdapterMethod
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.adapter.basic.test_empty import BaseEmpty
from dbt.tests.adapter.basic.test_ephemeral import BaseEphemeral
from dbt.tests.adapter.basic.test_generic_tests import BaseGenericTests
from dbt.tests.adapter.basic.test_incremental import BaseIncremental
from dbt.tests.adapter.basic.test_singular_tests import BaseSingularTests
from dbt.tests.adapter.basic.test_singular_tests_ephemeral import (
    BaseSingularTestsEphemeral,
)


class TestSimpleMaterializationsDenodo(BaseSimpleMaterializations):
    pass


class TestSingularTestsDenodo(BaseSingularTests):
    pass


class TestSingularTestsEphemeralDenodo(BaseSingularTestsEphemeral):
    pass


class TestEmptyDenodo(BaseEmpty):
    pass


class TestEphemeralDenodo(BaseEphemeral):
    pass


class TestIncrementalDenodo(BaseIncremental):
    pass


class TestGenericTestsDenodo(BaseGenericTests):
    pass


class TestBaseAdapterMethodDenodo(BaseAdapterMethod):
    pass
