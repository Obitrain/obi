# Agent quickstart

`obi` is designed to be driven by AI agents and scripts. This page is the contract you can rely on.

## 1. Discover the API

```bash
obi schema tags                         # tags and operation counts
obi schema list --grep session          # find operations by path / id
obi schema list --tag "Session endpoint"
obi schema show /v1/training/sessions -X GET
```

`obi schema show` prints an operation's parameters, request-body schema, response schemas, and the
names of the referenced component schemas (the same names generated as `TypedDict`s in
`obitrain.models`). The spec is bundled in the package, so discovery needs no network.

## 2. Authenticate (headless)

For non-interactive environments, pass a token via the environment — it is ephemeral and never
written to disk:

```bash
export OBI_TOKEN="<access token>"
export OBI_BASE_URL="https://api.obitrain.com"   # optional override
obi api /v1/user
```

For an interactive setup, `obi auth login` once, then rely on automatic refresh.

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
| `7` | Client error — inspect the stderr JSON (`status`, `retry_after`) and fix the request. |

## 5. Dry-run before mutating

```bash
obi api /v1/user -X PATCH -d '{"lang":"fr"}' -n
```

Prints the exact request (with the token redacted) so an agent can confirm before sending.
