# obi

Public, agent-first CLI for the **Obitrain API**. `obi` handles authentication (with transparent
token refresh) and lets you call any endpoint through one generic command, so humans and AI agents
can drive the API without per-endpoint wrappers.

## Install

```bash
uv tool install obitrain      # exposes the `obi` binary
uvx --from obitrain obi --help
```

## Usage

```bash
obi auth login                             # device-code login: approve in the Obitrain app
obi api /v1/activities -q size=1           # call any endpoint
obi schema list --grep activities          # discover endpoints from the bundled OpenAPI spec
obi auth token                             # print the access token for scripting
```

- **Output:** JSON by default (`-o pretty|raw|yaml` for alternatives); forced to JSON in agent
  environments / non-TTY / `NO_COLOR`.
- **Exit codes:** `0` ok · `1` usage · `4` auth · `5` network · `6` server (5xx) · `7` client (4xx).
- **Profiles:** `--profile <name>` (or `OBI_PROFILE`) for multiple accounts.
- **Base URL:** defaults to `https://api.obitrain.com`; override with `--base-url` or `OBI_BASE_URL`.

## For agents

The CLI is self-documenting: `obi quickstart` prints the full agent contract (discovery → auth →
calls → error repair) to stdout. The short loop:

```bash
obi schema list --grep stats               # 1. find the operation
obi schema show /v1/stats/activity/weekly  # 2. required params, types, body & response schemas
obi api '/v1/stats/activity/weekly' -q from_date=2026-01-01 -q to_date=2026-06-01
```

Errors are one-line JSON on stderr with deterministic exit codes, and 404/405/422 diagnostics
include a `hint` field with the missing parameters and the exact `obi schema show` command to run.

Full docs: <https://obitrain.github.io/obi/>.

## Development

```bash
uv sync --all-groups
uv run ruff check src tests && uv run ruff format --check src tests
uv run pyright
uv run pytest
```

### Generated models

`src/obitrain/api/models.py` holds `TypedDict`s generated from `static/openapi.json` (the vendored
OpenAPI 3.1 spec). Regenerate after updating the spec:

```bash
sh bin/codegen.sh
git diff --exit-code src/obitrain/api/models.py   # CI fails if these drift
```

To refresh the spec from upstream, replace `static/openapi.json` and rerun codegen.

### Docs

```bash
uv run --group docs zensical serve   # live preview
uv run --group docs zensical build   # static site -> ./site
```
