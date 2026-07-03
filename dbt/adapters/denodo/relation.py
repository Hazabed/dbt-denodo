from dataclasses import dataclass, field

from dbt.adapters.base.relation import BaseRelation
from dbt.adapters.contracts.relation import Policy
from dbt_common.exceptions import DbtRuntimeError


@dataclass
class DenodoQuotePolicy(Policy):
    database: bool = False
    schema: bool = False
    identifier: bool = False


@dataclass
class DenodoIncludePolicy(Policy):
    # Denodo has a two-level namespace: <virtual database>.<view>. The dbt
    # schema maps to the virtual database, and the database component is
    # never rendered.
    database: bool = False
    schema: bool = True
    identifier: bool = True


@dataclass(frozen=True, eq=False, repr=False)
class DenodoRelation(BaseRelation):
    quote_policy: DenodoQuotePolicy = field(default_factory=lambda: DenodoQuotePolicy())
    include_policy: DenodoIncludePolicy = field(default_factory=lambda: DenodoIncludePolicy())
    quote_character: str = '"'

    # Note: `database` is intentionally not validated against `schema` here.
    # dbt assigns target.database to every node, while `schema` varies with
    # custom schema configs (e.g. the tests' `<schema>_dbt_test__audit`).
    # The database component is carried for cache bookkeeping only and is
    # never rendered; each dbt schema addresses its own Denodo virtual
    # database.

    @staticmethod
    def add_ephemeral_prefix(name: str) -> str:
        return f"__dbt__cte__{name}"

    def render(self) -> str:
        if self.include_policy.database and self.include_policy.schema:
            raise DbtRuntimeError(
                "Got a Denodo relation with both database and schema set to "
                "include, but Denodo relations may only have one component."
            )
        return super().render()
