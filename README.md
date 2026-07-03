# dbt-denodo

[![CI](https://github.com/Hazabed/dbt-denodo/actions/workflows/ci.yml/badge.svg)](https://github.com/Hazabed/dbt-denodo/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dbt-denodo)](https://pypi.org/project/dbt-denodo/)
[![Python versions](https://img.shields.io/pypi/pyversions/dbt-denodo)](https://pypi.org/project/dbt-denodo/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A [dbt](https://www.getdbt.com/) adapter for [Denodo Platform 8](https://community.denodo.com/docs/html/browse/8.0/en/) and [9](https://community.denodo.com/docs/html/browse/9.0/en/) (Virtual DataPort).

`dbt-denodo` lets dbt Core connect directly to Denodo Virtual DataPort (VDP) and manage
derived views and materialized tables with dbt's modeling, testing, and documentation workflow.

Built and maintained by [Hassan Abid](https://github.com/Hazabed) as a personal
open-source project for the dbt and Denodo community.

> **Status: alpha.** The adapter follows the current
> [dbt adapter architecture](https://docs.getdbt.com/guides/adapter-creation)
> (decoupled `dbt-adapters` interface, post-dbt-Core-1.8). It has a full unit test
> suite and has been verified working against a live Denodo 9 server; running the
> functional suite requires a live VDP server. See
> [Assumptions to verify against a live server](#assumptions-to-verify-against-a-live-server).

## Requirements

- Python >= 3.10 (tested on 3.14)
- dbt Core >= 1.11 (the adapter depends only on the decoupled `dbt-adapters` /
  `dbt-common` interfaces and is forward-compatible with future dbt Core 1.x
  releases, including 1.12 when it ships — as of July 2026 the latest dbt Core is 1.11.x)
- Denodo Platform 8 or 9 with the VDP server's ODBC (PostgreSQL-compatible) interface
  enabled (port 9996 by default)
- For `table`, `incremental`, and `seed` materializations: the VDP **cache engine**
  must be configured (materialized tables store their data in the cache data source)

## Supported Denodo versions

The adapter has no version-specific code: it only requires the PostgreSQL-compatible
interface accepting VQL, the `GET_VIEWS()` / `GET_VIEW_COLUMNS()` stored procedures,
`CREATE OR REPLACE VIEW / MATERIALIZED TABLE`, and (for materialized models) the
cache engine.

| Denodo version | Status |
|---|---|
| Platform 9 / 9.x | ✅ Supported — verified against a live server |
| Platform 8.0 | ✅ Supported — original design target |
| Platform 7.0 | ⚠️ Untested — exposes the required interface and VQL, but is past end-of-support |
| 6.0 and earlier | ❌ Not supported |

## How it connects (and why not JDBC)

Denodo's officially supported way to reach VDP from Python is the
**PostgreSQL-compatible interface** on port 9996 via `psycopg2` — the same driver and
interface used by Denodo's official
[SQLAlchemy dialect](https://community.denodo.com/docs/html/document/denodoconnects/8.0/en/Denodo%20Dialect%20for%20SQLAlchemy%20-%20User%20Manual)
for Denodo 8 and 9. This interface accepts VQL, so the adapter issues native VQL statements.

The official Denodo **JDBC driver is a Java artifact** and cannot be loaded natively by
CPython (it would require a JVM bridge such as JPype/jaydebeapi, which Denodo does not
recommend for Python). Denodo's Arrow **Flight SQL** interface would be preferable for
throughput but only exists in **Denodo 9.1+**; this adapter sticks to the pg-wire
interface so a single code path covers both Platform 8 and 9.

### Python 3.14 note

`dbt-core` 1.11.x pins `mashumaro<3.15`, and mashumaro only gained Python 3.14
compatibility in 3.17 (older versions fail to import on 3.14 due to PEP 649 lazy
annotations). Until dbt-core relaxes its pin, running on Python 3.14 requires:

```bash
pip install "mashumaro[msgpack]==3.17"   # after installing dbt-core
```

mashumaro 3.17 satisfies `dbt-adapters`' own pin (`<3.18`) and passes this adapter's
full test suite. On Python 3.10–3.13 no override is needed.

## Installation

```bash
pip install dbt-denodo        # once published; from source: pip install .
```

## Profile

Denodo has a **two-level namespace**: a *virtual database* containing views. There is no
separate catalog/schema split, so — like `dbt-spark` — the dbt `schema` maps to the Denodo
virtual database, and `database` must be omitted (or equal to `schema`).

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: denodo
      host: vdp.example.com
      port: 9996                # VDP ODBC (pg-wire) port
      user: dbt_user
      password: "{{ env_var('DENODO_PASSWORD') }}"
      schema: analytics         # the Denodo virtual database
      threads: 4
      # optional:
      sslmode: prefer           # any libpq sslmode value
      connect_timeout: 10
      retries: 1
```

## Feature support

| Feature | Support | Implementation |
|---|---|---|
| `view` models | ✅ | `CREATE OR REPLACE VIEW` (VQL derived view) |
| `table` models | ✅ (needs cache engine) | `CREATE OR REPLACE MATERIALIZED TABLE ... AS SELECT` |
| `incremental` models | ✅ `append`, `delete+insert` | staging derived view + `INSERT` / `DELETE` on the materialized table |
| `ephemeral` models | ✅ | CTEs |
| Seeds | ✅ (needs cache engine) | materialized table + row-by-row `INSERT` |
| Tests (generic + singular) | ✅ | plain `SELECT` |
| Docs (`dbt docs generate`) | ✅ | `GET_VIEWS()` / `GET_VIEW_COLUMNS()` |
| Snapshots | ❌ | VQL has no `MERGE` and no `RENAME` |
| Grants (`grants:` config) | ❌ | VDP privileges are administered separately; fails loudly |
| `persist_docs` | ❌ | fails loudly if enabled |
| Constraints | ❌ | reported as not supported to dbt |
| `incremental_predicates` | ❌ | fails loudly if configured |

### Design notes

- **No RENAME in VQL.** Denodo cannot rename views or tables, so this adapter's
  materializations use `CREATE OR REPLACE` instead of dbt's default
  create → swap → drop pattern. `rename_relation` raises if anything calls it.
- **Transactions.** VQL DDL is not transactional; connections run in autocommit and
  dbt's BEGIN/COMMIT hooks are no-ops.
- **Schemas are virtual databases.** `create_schema` issues `CREATE DATABASE`
  (administrator privilege required). Most production setups should pre-create the
  virtual database and let dbt build inside it; custom `generate_schema_name` logic
  that fans out across many schemas will require databases to exist or admin rights.
- **`CREATE MATERIALIZED TABLE ... AS SELECT` runs the query on the server** and,
  per Denodo documentation, keeps the database in single-user mode while it runs.
  Prefer views for heavy models, or schedule table builds off-hours.
- **Folders.** Set `folder: '/dbt'` in a model config to place created elements in a
  VDP folder (`FOLDER = '...'` modifier).

## Known limitations & platform caveats

- Denodo is a **data virtualization** layer: `view` models add zero storage cost, while
  `table`/`incremental`/`seed` models write into the cache data source.
- `delete+insert` incremental strategy requires a **single-column** `unique_key`.
- `truncate` is implemented as `DELETE FROM` (VQL has no `TRUNCATE`).
- Cross-database references (`database` different from the profile `schema`) are rejected.

## Assumptions to verify against a live server

These follow documented Denodo behavior and have been exercised successfully against a
live Denodo 9 server; end-to-end verification specifically on a Platform 8 instance is
still welcome. Each is isolated in one macro for easy patching:

1. **`GET_VIEW_COLUMNS()` output field names** (`column_name`, `column_vdp_type`,
   `column_size`, `column_decimals`) — used by `denodo__get_columns_in_relation`
   ([macros/adapters.sql](dbt/include/denodo/macros/adapters.sql)) and
   [macros/catalog.sql](dbt/include/denodo/macros/catalog.sql). `GET_VIEWS()` fields
   (`name`, `database_name`, `view_type`) and the `view_type` codes
   (0 base / 1 derived / 2 interface / 3 materialized / 4 summary) are documented.
2. **`LIST DATABASES` through the pg-wire interface** returns one row per database
   (`denodo__list_schemas`). If unavailable for non-admin users, replace with a
   `GET_ELEMENTS()`-based query.
3. **`INSERT INTO <materialized table> SELECT ... FROM <view>`** — used by the
   incremental materialization.
4. **`FOLDER = '<path>'` modifier position** in `CREATE OR REPLACE VIEW` /
   `CREATE OR REPLACE MATERIALIZED TABLE` (only emitted when the optional `folder`
   config is set).
5. **Qualified names (`db.view`) in DDL statements.** With the default single-database
   setup the qualified name always matches the connected database, which is safe.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit                 # no server needed
cp test.env.example test.env      # then edit
pytest tests/functional           # needs a live Denodo VDP server (8 or 9)
```

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
development setup, test instructions, and PR guidelines. Bug reports and
feature requests go through
[GitHub issues](https://github.com/Hazabed/dbt-denodo/issues); security
reports follow [SECURITY.md](SECURITY.md).

If you have access to a live Denodo VDP server, running the functional
suite and reporting results against the
[assumptions listed above](#assumptions-to-verify-against-a-live-server) is
one of the most valuable contributions you can make right now.

## License

[Apache License 2.0](LICENSE)
