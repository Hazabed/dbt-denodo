from dbt.adapters.base import AdapterPlugin

from dbt.adapters.denodo.__version__ import version as __version__
from dbt.adapters.denodo.column import DenodoColumn
from dbt.adapters.denodo.connections import DenodoConnectionManager, DenodoCredentials
from dbt.adapters.denodo.impl import DenodoAdapter
from dbt.adapters.denodo.relation import DenodoRelation
from dbt.include import denodo

Plugin = AdapterPlugin(
    adapter=DenodoAdapter,  # type: ignore[arg-type]
    credentials=DenodoCredentials,
    include_path=denodo.PACKAGE_PATH,
)

__all__ = [
    "DenodoAdapter",
    "DenodoColumn",
    "DenodoConnectionManager",
    "DenodoCredentials",
    "DenodoRelation",
    "Plugin",
    "__version__",
]
