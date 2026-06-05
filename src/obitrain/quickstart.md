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
obi api /v1/activities -q size=5 --json
```

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
