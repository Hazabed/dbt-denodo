# Contributing to dbt-denodo

Thanks for your interest in contributing! This document covers how to set up
a development environment, run the tests, and submit changes.

## Development setup

```bash
git clone https://github.com/Hazabed/dbt-denodo.git
cd dbt-denodo
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

> **Python 3.14:** after installing, run
> `pip install "mashumaro[msgpack]==3.17"` — see the README's Python 3.14
> note. On 3.10–3.13 no override is needed.

## Running the tests

**Unit tests** need no server:

```bash
pytest tests/unit
```

**Functional tests** require a live Denodo VDP server (8 or 9) with the
PostgreSQL-compatible interface enabled (port 9996) and the cache engine
configured:

```bash
cp test.env.example test.env     # then edit with your server details
pytest tests/functional
```

`test.env` is gitignored — never commit credentials.

## Linting and formatting

The project uses [ruff](https://docs.astral.sh/ruff/) for linting and
formatting, run automatically via pre-commit:

```bash
ruff check .
ruff format .
```

CI runs the same checks; PRs must pass them.

## Project layout

| Path | Purpose |
|---|---|
| `dbt/adapters/denodo/` | Python adapter: credentials, connection manager, adapter implementation, relation/column classes |
| `dbt/include/denodo/macros/` | VQL macro implementations (DDL, metadata, catalog) |
| `dbt/include/denodo/macros/materializations/` | `view`, `table`, `incremental`, seed materializations |
| `tests/unit/` | Unit tests (no server needed) |
| `tests/functional/` | dbt standard adapter tests against a live VDP server |

## Guidelines for changes

- **VQL correctness matters most.** Denodo's VQL differs from SQL in
  important ways (no `RENAME`, no `MERGE`, no `TRUNCATE`, non-transactional
  DDL). If your change alters emitted VQL, verify it against a live VDP (8 or 9)
  server, or document the assumption in the README's
  "Assumptions to verify against a live server" section.
- **Fail loudly.** Features VQL cannot support (snapshots, grants,
  `persist_docs`, constraints) raise clear errors rather than silently
  doing the wrong thing. Keep that behavior.
- **Keep macros patchable.** Each live-server assumption is isolated in a
  single macro so users can override it in their own project; preserve that
  isolation.
- Add or update unit tests for any Python change.
- Update `CHANGELOG.md` under the unreleased version.

## Submitting a pull request

1. Fork the repository and create a topic branch from `main`.
2. Make your changes with tests and changelog entry.
3. Ensure `pytest tests/unit`, `ruff check .`, and `ruff format --check .`
   pass locally.
4. Open a PR using the template. Small, focused PRs are reviewed fastest.

## Release process (maintainers)

1. Update the version in `dbt/adapters/denodo/__version__.py`.
2. Move the changelog's unreleased section to the new version with a date.
3. Merge to `main`, then tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. The `Release` workflow builds and publishes to PyPI (trusted publishing)
   and creates the GitHub release.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
By participating you agree to uphold it.
