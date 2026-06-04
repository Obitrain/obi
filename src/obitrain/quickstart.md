# Agent quickstart

`obi` is designed to be driven by AI agents and scripts. This page is the contract you can rely on.

## 1. Discover the API

```bash
obi schema tags                         # tags and operation counts
obi schema list --grep session          # find operations by path / id
obi schema list --tag "Session endpoint"
obi schema show /v1/training/sessions -X GET
obi schema show /v1/stats/activity/weekly   # concrete paths resolve to their template
```

`obi schema show` prints an operation's parameters (with types), request-body schema, response
schemas, and the full definitions of every referenced component schema. The spec is bundled in the
package, so discovery needs no network.

## 2. Authenticate

For non-interactive environments, pass a token via the environment — it is ephemeral and never
written to disk:

```bash
export OBI_TOKEN="<api token>"
export OBI_BASE_URL="https://api.obitrain.com"   # optional override
obi api /v1/user
```

Interactively, `obi auth login` runs a device-code flow: it prints a short code, the user approves
it in the Obitrain app (Account → Link a device), and a long-lived API token is stored in the
active profile. `obi auth set <token>` stores a token generated from the Account page instead.

## 3. Call the API

```bash
obi api /v1/activities -q size=5
```

- **Output is JSON by default** and forced to JSON (no color) when an agent environment is detected
  (`CLAUDECODE`, `CLAUDE_CODE`, `CURSOR_AGENT`, `GITHUB_COPILOT`, `AMAZON_Q`, `OBI_AGENT_MODE`),
  when `NO_COLOR` is set, or when stdout is not a TTY.
- **Successful bodies → stdout.** Parse them directly.
- **Errors → stderr** as one-line JSON, with a deterministic exit code.

## 4. Branch on exit codes

| Exit | Do |
|------|----|
| `0` | Parse stdout as the result. |
| `4` | Re-authenticate (`obi auth login`) or refresh the `OBI_TOKEN`. |
| `5` | Transient network issue — retry with backoff. |
| `6` | Server error — retry later. |
| `7` | Client error — inspect the stderr JSON (`status`, `hint`, `retry_after`) and fix the request. |

## 5. Repair from the `hint` field

On `404`, `405` and `422` the stderr diagnostic includes a `hint` built from the bundled spec —
usually enough to fix the request without further discovery:

```bash
$ obi api /v1/stats/activity/weekly
{"error": "http_error", "status": 422, ..., "hint": "required params: range_type (path, enum:
daily|weekly|monthly), from_date (query, date), to_date (query, date); see `obi schema show
'/v1/stats/activity/{range_type}'`"}

$ obi api /v1/stats/activity/weekly -q from_date=2026-01-01 -q to_date=2026-06-01   # repaired
```

## 6. Dry-run before mutating

```bash
obi api /v1/user -X PATCH -d '{"lang":"fr"}' -n
```

Prints the exact request (with the token redacted) so an agent can confirm before sending.
