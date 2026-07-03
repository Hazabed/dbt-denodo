# Changelog

## 0.1.0 (unreleased)

Initial release.

- Connects to Denodo Virtual DataPort (Platform 8 and 9) through the PostgreSQL-compatible
  interface (port 9996) via psycopg2, Denodo's officially supported Python
  connectivity for both platform versions.
- Materializations: `view` (VQL derived views), `table` (materialized
  tables), `incremental` (`append` and `delete+insert`), `ephemeral`, seeds.
- Metadata via `GET_VIEWS()` / `GET_VIEW_COLUMNS()` / `LIST DATABASES`;
  catalog support for `dbt docs generate`.
- No-rename architecture: all materializations use `CREATE OR REPLACE`
  (VQL has no RENAME).
- Explicitly unsupported, failing with clear errors: snapshots, grants,
  `persist_docs`, constraints, `incremental_predicates`.
