# Agent quickstart

`obi` was designed to work reliably in AI-agent and automation workflows. This page documents the
machine-facing contract an agent can depend on.

For an offline copy of this guide, run:

```bash
obi quickstart
```

Use `obi --help-json` to inspect the complete command tree and option metadata as JSON.

## 1. Discover the API

Search the bundled OpenAPI contract before constructing a request:

```bash
obi schema tags --json
obi schema list --grep session --json
obi schema list --tag "Session endpoint" --json
obi schema show /v1/training/sessions -X GET --json
obi schema show /v1/stats/activity/weekly --json
```

`schema show` returns the operation's parameters, request-body schema, response schemas, and all
referenced component definitions. Concrete paths resolve to their OpenAPI path template.

## 2. Authenticate without persistence

For an agent or CI job, prefer an ephemeral token:

```bash
export OBI_TOKEN="<api token>"
export OBI_BASE_URL="https://api.obitrain.com"   # optional
obi api /v1/user --json
```

`OBI_TOKEN` is used for the current process and is not written to disk. A user can instead run
`obi auth login` and approve the device code in the Obitrain app, or store an existing token with
`obi auth set <token>`.

## 3. Call the API

```bash
obi api /v1/training/sessions -q limit=5 --json
```

`/v1/training/sessions` returns the authenticated user's own sessions; `/v1/activities` is the
friends feed (other users' sessions) — don't use it to answer questions about the user's training.

Endpoints that can return other users' data take a `scope` parameter (`me`, `all_visible`,
`friends`, `groups`) — always pass it explicitly, `scope=me` for the user's own data. Never rely
on the defaults: with `scope` omitted, `/v1/search/session` searches **all users'** visible
sessions. The booleans `all_users`, `user_only`, `friends` and `only_groups` are deprecated.

Multiple query params can be passed space-separated after one `-q` (`-q from_date=2026-07-01
limit=5`) or by repeating the flag (`-q from_date=2026-07-01 -q limit=5`); both send every pair.

Use `--json` explicitly even though `obi` automatically selects plain JSON when stdout is not a
TTY or a supported agent environment is detected.

- Successful response bodies are written to stdout.
- HTTP error response bodies are still written to stdout.
- Diagnostics are written to stderr as one-line JSON.

Keep stdout and stderr separate when invoking the command so both payloads remain parseable.

## 4. Branch on exit codes

| Exit | Meaning | Agent action |
|------|---------|--------------|
| `0` | Success | Parse stdout as the result. |
| `1` | Usage error | Fix the command arguments. |
| `4` | Authentication error | Obtain a valid token or ask the user to authenticate. |
| `5` | Network error | Retry with backoff. |
| `6` | Server error (5xx) | Retry later. |
| `7` | Client error (4xx) | Inspect the stderr diagnostic and fix the request. |
| `130` | Cancelled (Ctrl-C / SIGINT) | Treat as user-aborted; do not retry automatically. |

For `429`, the diagnostic includes `retry_after` when the server provides it.

## 5. Repair invalid requests

For `404`, `405`, and `422`, the stderr diagnostic can include a `hint` generated from the bundled
API contract:

```json
{
  "error": "http_error",
  "status": 422,
  "method": "GET",
  "path": "/v1/stats/activity/weekly",
  "hint": "required params: ...; see `obi schema show '/v1/stats/activity/{range_type}'`"
}
```

On exit `7`, read `status` and `hint`, inspect the suggested operation with `obi schema show`, and
retry only after correcting the request.

## 6. Dry-run mutations

```bash
obi api /v1/user -X PATCH -d '{"lang":"fr"}' -n --json
```

Dry-run prints the resolved method, URL, query, headers, and body without sending the request. The
authorization token is redacted.

The recommended loop is:

```text
schema list -> schema show -> api --dry-run -> api -> inspect exit code and diagnostic
```

## 7. Create or plan a training session

`POST /v1/training/session` covers both planning and logging: `status` 0 = planned (the default;
`ts_start` may be in the future or omitted), 1 = done. The sport is derived server-side —
`sport_id` and `icon` are read-only, so convey the activity through `name`, `notes` and `tags`.
`visibility`: 0 private / 1 public / 2 friends (default).

Plan a cardio session — use the session-level metrics (`distance` in meters, `speed_avg`/`speed_max`
with `speed_unit`, `bpm_avg`/`bpm_max`, `power_avg`/`power_max`, `climb`, `descent`, `calories`)
and put the workout structure in `notes`:

```bash
obi api /v1/training/session -X POST --json -d '{
  "name": "Tempo run — 3×10 min @ 5:15/km",
  "notes": "14min warm-up / 3×(10min tempo + 3min jog) / cool-down",
  "ts_start": "2026-07-20T10:00:00", "tz": "Europe/Paris",
  "tags": ["tempo"], "distance": 10000,
  "exercises": []
}'
```

Build a strength session — reference catalog exercises (ids from `/v1/training/exercises` or
`/v1/search/exercise`), give each a metric as a `{"real", "objective"}` pair (objective = target,
real = achieved, `-1` = "to max"; `bpm` and `vo2max` take `[min, max]` tuples), and group circuit
rounds with `groups` + `group_position` (`nb_reps` = rounds; exercises are duplicated per round
unless `"duplicate": false`):

```bash
obi api /v1/training/session -X POST --json -d '{
  "name": "Pull day",
  "groups": [{"name": "circuit", "nb_reps": 3}],
  "exercises": [
    {"exercise_id": "<uuid>", "group_position": 0,
     "nb_reps": {"real": null, "objective": 10},
     "weight": {"real": null, "objective": 20.0}}
  ]
}'
```

Mark it done afterwards — PATCH is a partial update (only sent fields are applied; `exercises`
are replaced only when provided):

```bash
obi api /v1/training/session -X PATCH --json -d '{"id": "<session id>", "status": 1}'
```

A group's `skip_last` hides the last round's final exercise (typically the trailing rest).
The mobile app treats it as a display flag over fully-expanded rows — so when setting
`skip_last`, send `"duplicate": false` with every round written out (including the trailing
rest); letting the server drop the row (`duplicate` true) makes the app render an empty last
round.

When reading a session back, per-exercise data is under `metrics[]` (with `position` and
`group_id`); `exercises[]` is the deduplicated catalog list.

## Driving obi from a coding agent

Any agent that can run shell commands can use `obi` directly. Because the binary is self-describing,
you rarely need to hand-write API instructions — point the agent at two commands:

- `obi quickstart` prints this guide to stdout.
- `obi --help-json` returns the full command tree and options as JSON.

A short note in the repository's agent-instructions file is usually enough:

```markdown
## Obitrain API
Reach the Obitrain API with the `obi` CLI — run `obi quickstart` for the full guide.
Discover endpoints with `obi schema list --grep <term>` and `obi schema show <path>`,
then call them with `obi api <path> --json`. Authenticate with `OBI_TOKEN` (ephemeral)
or `obi auth login`.
```

Pass the token through the environment so it never lands on disk, and let `obi` pick the machine
output (see [Call the API](#3-call-the-api)).

### Claude Code

Claude Code sets `CLAUDECODE`, so `obi` emits JSON with no flag. Drop the note above into `CLAUDE.md`
or `AGENTS.md` — Claude reads it automatically — and start the session with a token in the
environment:

```bash
OBI_TOKEN="<api token>" claude
```

### OpenAI Codex CLI

Codex reads `AGENTS.md`. It is not auto-detected, so export `OBI_AGENT_MODE=1` to force JSON (piped
output already falls back to JSON, but this is explicit):

```bash
export OBI_AGENT_MODE=1 OBI_TOKEN="<api token>"
codex exec "Use obi to list my last 5 training sessions"
```

`obi schema …` is fully offline and works under a read-only sandbox (`codex exec -s read-only`);
`obi api` needs network and a token, so run it where both are allowed.

### Mistral Vibe

Enable a shell tool and set `OBI_AGENT_MODE=1`. In programmatic mode (`-p`), `--enabled-tools`
disables every other tool, so include the shell glob:

```bash
export OBI_AGENT_MODE=1 OBI_TOKEN="<api token>"
vibe -p "Use obi to fetch /v1/user and summarize the profile" --enabled-tools "bash*"
```
