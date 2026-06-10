# obi

Command-line client for the **Obitrain API** — one generic, scriptable interface to every
endpoint, for interactive use and automation.

Instead of wrapping each endpoint in its own subcommand, `obi` gives you three primitives:

- `obi auth` — authenticate once, stay authenticated
- `obi api` — call any endpoint (method, query, body, headers)
- `obi schema` — discover endpoints, parameters and payload shapes offline

## Install

```bash
uv tool install obitrain      # exposes the `obi` binary
uvx --from obitrain obi --help
```

## User quickstart

```bash
obi auth login
```

`obi auth login` prints a short code (like `QX2F-LX4T`). Enter it in the Obitrain mobile app under
**Account → Link a device**, and the CLI receives its own API token — no password typed in the
terminal, and it works for Google/Apple accounts too. The token is long-lived and revocable from
the app at any time.

Then call anything:

```bash
obi api /v1/user                                  # your profile
obi api /v1/training/sessions -q limit=5          # last sessions
obi api /v1/user -X PATCH -d '{"lang": "fr"}'     # update a field
obi api /v1/training/session -d @session.json     # body from a file (implies POST)
```

Continue with the [user quickstart](https://obitrain.github.io/obi/user-quickstart/) or see the
[full documentation](https://obitrain.github.io/obi/).

## Authentication

| Command | Purpose |
|---|---|
| `obi auth login` | Device-code login: approve in the app, token stored in the active profile |
| `obi auth set <token>` | Store a token generated from your Account page |
| `obi auth status` / `whoami` | Inspect the active profile / authenticated user |
| `obi auth token` | Print the token, for scripting |
| `obi auth clear` | Remove stored credentials |

- **Profiles** — `--profile work` (or `OBI_PROFILE`) keeps separate accounts; credentials are
  stored per profile with `0600` permissions. `obi auth profiles` lists them.
- **Ephemeral tokens** — `OBI_TOKEN` / `--token` authenticate a single invocation without writing
  anything to disk; ideal for CI.
- **Base URL** — defaults to `https://api.obitrain.com`; override with `--base-url` or
  `OBI_BASE_URL`.

## Calling the API

```bash
obi api <path> [-X METHOD] [-q k=v ...] [-d BODY|@file|@-] [-H k:v ...] [-o json|pretty|raw|yaml] [-n]
```

- `-d` implies `POST` unless `-X` says otherwise; `@file` and `@-` (stdin) are supported.
- `-n` / `--dry-run` prints the fully resolved request (token redacted) without sending it.
- Response bodies always go to **stdout**; diagnostics go to **stderr** as one-line JSON.
- **Output is human-friendly by default** (syntax-highlighted on a TTY) and plain JSON whenever
  output is piped or an agent environment is detected; `--json` (or `-o json|raw|yaml`) forces a
  format explicitly.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — parse stdout |
| `1` | Usage error |
| `4` | Authentication required or failed |
| `5` | Network error (connection, DNS, timeout) |
| `6` | Server error (5xx) |
| `7` | Client error (4xx) |

## Discovering the API

The OpenAPI spec is bundled with the package — discovery works offline:

```bash
obi schema tags                              # tags with operation counts
obi schema list --grep session               # find operations
obi schema show /v1/training/sessions -X GET # params, body & response schemas, inlined models
obi schema show /v1/stats/activity/weekly    # concrete paths resolve to their {template}
```

## Agent quickstart

`obi` was also designed for reliable use by AI agents. The machine-facing contract includes:

- **Self-documenting binary** — `obi quickstart` prints the full agent guide (discovery → auth →
  calls → error repair) to stdout; `obi --help-json` gives the machine-readable command tree.
  No repo or web access needed.
- **Deterministic output** — bodies on stdout, one-line JSON diagnostics on stderr, exit codes
  above. Pass `--json` to force plain JSON; in practice you already get it, since output falls
  back to JSON when an agent environment is detected (`CLAUDECODE`, `CURSOR_AGENT`,
  `GITHUB_COPILOT`, `AMAZON_Q`, `OBI_AGENT_MODE`, …), when `NO_COLOR` is set, or when stdout is
  not a TTY.
- **Errors carry their own fix** — `404`/`405`/`422` diagnostics include a `hint` field built from
  the bundled spec:

  ```bash
  $ obi api /v1/stats/activity/weekly
  {"error": "http_error", "status": 422, "method": "GET", "path": "/v1/stats/activity/weekly",
   "hint": "required params: range_type (path, enum: daily|weekly|monthly), from_date (query, date),
   to_date (query, date); see `obi schema show '/v1/stats/activity/{range_type}'`"}

  $ obi api /v1/stats/activity/weekly -q from_date=2026-01-01 -q to_date=2026-06-01   # repaired
  ```

The recommended loop: `obi schema list --grep …` → `obi schema show <path>` → `obi api … -n`
(optional dry-run) → `obi api …` → on exit 7, read `hint` and retry.

**Works with coding agents.** Any agent that can run a shell can drive `obi` — give it a token via
`OBI_TOKEN` and tell it to run `obi quickstart`. Claude Code is auto-detected (`CLAUDECODE`); for
OpenAI Codex (`AGENTS.md`) and Mistral Vibe, set `OBI_AGENT_MODE=1` to force JSON:

```bash
OBI_TOKEN="<api token>" claude                                   # auto-detected
OBI_AGENT_MODE=1 OBI_TOKEN="<api token>" codex exec "use obi to fetch /v1/user"
OBI_AGENT_MODE=1 OBI_TOKEN="<api token>" vibe -p "use obi to fetch /v1/user" --enabled-tools "bash*"
```

See the [agent quickstart](https://obitrain.github.io/obi/agent-quickstart/) for the complete
workflow, including per-tool setup.

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

Full docs: <https://obitrain.github.io/obi/>.
