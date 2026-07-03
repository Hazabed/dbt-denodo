# Security Policy

## Supported versions

Only the latest released version of `dbt-denodo` receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security vulnerabilities.

Instead, report privately via
[GitHub Security Advisories](https://github.com/Hazabed/dbt-denodo/security/advisories/new)
("Report a vulnerability" on the repository's Security tab).

Include:

- A description of the vulnerability and its impact
- Steps to reproduce, ideally with a minimal example
- Affected versions

You can expect an acknowledgement within a few days. Please allow time for a
fix to be released before public disclosure.

## Scope notes

- `dbt-denodo` connects to Denodo VDP with the credentials in your dbt
  profile; it never stores credentials itself. Use `env_var()` in
  `profiles.yml` and keep `test.env` out of version control (it is
  gitignored).
- Vulnerabilities in Denodo Platform itself should be reported to
  [Denodo](https://www.denodo.com/), not to this project.
