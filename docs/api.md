# Making requests

`obi api` sends an authenticated request to any path on the Obitrain API, in the spirit of
`gh api` / `gcx api`. Auth and token refresh are handled for you.

```text
obi api <PATH> [-X METHOD] [-d DATA] [-q k=v ...] [-H k:v ...] [-o FORMAT] [-n]
```

## Examples

```bash
obi api /v1/activities -q size=1                 # GET with a query param
obi api /v1/training/sessions -q limit=10 offset=0
obi api /v2/token/generate -d '{"scope":"read"}' # -d implies POST
obi api /v1/user -X PATCH -d @patch.json         # body from a file
echo '{"x":1}' | obi api /v1/thing -X POST -d @- # body from stdin
obi api /v1/user -o yaml                          # YAML output
obi api /v1/activities -n                         # dry run: print the request, send nothing
```

## Options

| Flag | Meaning |
|------|---------|
| `-X, --method` | HTTP method. Defaults to `GET`, or `POST` when `-d` is given. |
| `-d, --data` | Request body. A leading `@` reads a file; `@-` or `-` reads stdin. Parsed as JSON when possible. |
| `-q, --query` | Query parameters as `k=v` (space-separate several: `-q a=1 b=2`). Repeated keys become a list. |
| `-H, --header` | Extra headers as `k:v` (space-separate several). Merged over the bearer header. |
| `-o, --output` | `json` (default), `pretty`, `raw`, or `yaml`. |
| `-n, --dry-run` | Print the resolved request (token redacted) without sending it. |

`<PATH>` may be a path (`/v1/...`) or an absolute `https://...` URL.

## Output & exit codes

Successful response bodies go to **stdout**. On an HTTP error the body is still printed to stdout,
and a one-line diagnostic JSON is written to **stderr**, e.g.:

```json
{"error": "http_error", "status": 404, "method": "GET", "path": "/v1/missing", "request_id": "…"}
```

| Exit | Meaning |
|------|---------|
| `0` | Success (2xx). |
| `1` | Usage / argument error. |
| `4` | Authentication required or refresh failed. |
| `5` | Network error (connection, timeout). |
| `6` | Server error (5xx). |
| `7` | Other client error (4xx, including 429 — `Retry-After` is surfaced in the diagnostic). |
