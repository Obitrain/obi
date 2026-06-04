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
obi auth login --email you@example.com     # authenticate (prompts for password)
obi api /v1/activities -q size=1           # call any endpoint
obi schema list --grep activities          # discover endpoints from the bundled OpenAPI spec
obi auth token                             # print the access token for scripting
```

- **Output:** JSON by default (`-o pretty|raw|yaml` for alternatives); forced to JSON in agent
  environments / non-TTY / `NO_COLOR`.
- **Exit codes:** `0` ok · `1` usage · `4` auth · `5` network · `6` server (5xx) · `7` client (4xx).
- **Profiles:** `--profile <name>` (or `OBI_PROFILE`) for multiple accounts.
- **Base URL:** defaults to `https://api.obitrain.com`; override with `--base-url` or `OBI_BASE_URL`.

Full docs: <https://obitrain.github.io/obi/>.

## Development

```bash
uv sync --all-groups
uv run ruff check src tests && uv run ruff format --check src tests
uv run pyright
uv run pytest
```

### Generated models

`src/obitrain/models.py` holds `TypedDict`s generated from `src/obitrain/openapi.json` (the vendored
OpenAPI 3.1 spec). Regenerate after updating the spec:

```bash
sh bin/codegen.sh
git diff --exit-code src/obitrain/models.py   # CI fails if these drift
```

To refresh the spec from upstream, replace `src/obitrain/openapi.json` and rerun codegen.

### Docs

```bash
uv run --group docs zensical serve   # live preview
uv run --group docs zensical build   # static site -> ./site
```
