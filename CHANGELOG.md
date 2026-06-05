# Changelog

## 0.1.0

Initial release of `obi`, the command-line client for the Obitrain API.

- **Authentication** — device-code login (`obi auth login`), token storage (`auth set`/`auth clear`),
  per-profile `0600` credential files, and ephemeral `--token`/`OBI_TOKEN` for store-less use.
- **Generic requests** — one `obi api <PATH>` passthrough with `-X/-d/-q/-H/-o/--json/-n` instead of
  per-endpoint commands; bodies from inline JSON, files (`@file`), or stdin (`@-`).
- **Offline discovery** — `obi schema` searches a bundled OpenAPI contract and `obi schema show`
  renders parameters, payloads, responses, and referenced component schemas without network access.
- **Agent-friendly output** — bodies to stdout, one-line JSON diagnostics to stderr, stable exit
  codes (`0/1/4/5/6/7`), and `404/405/422` repair hints.
- **Docs** — published documentation site with user and agent quickstarts.
