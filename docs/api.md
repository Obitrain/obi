# Making requests

`obi api` sends an authenticated request to any path on the Obitrain API, in the spirit of
`gh api` / `gcx api`. Bearer authentication is added for you.

```text
obi api <PATH> [-X METHOD] [-d DATA] [-q k=v ...] [-H k:v ...] [-o FORMAT] [--json] [-n]
```

## Examples

```bash
obi api /v1/activities -q size=1                 # GET with a query param
obi api /v1/training/sessions -q limit=10 from_offset=0
obi api /v1/user -X PATCH -d '{"lang":"fr"}'     # JSON body
obi api /v1/user -X PATCH -d @patch.json         # body from a file
printf '%s\n' '{"lang":"fr"}' | obi api /v1/user -X PATCH -d @-
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
| `-o, --output` | `pretty` (default), `json`, `raw`, or `yaml`. Pretty output falls back to JSON off-TTY. |
| `--json` | Shorthand for `-o json`. |
| `-n, --dry-run` | Print the resolved request (token redacted) without sending it. |
| `--profile` | Use a named credential profile. |
| `--token` | Use an ephemeral API token without persisting it. |
| `--base-url` | Override the API base URL. |

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
| `4` | Authentication required or failed. |
| `5` | Network error (connection, timeout). |
| `6` | Server error (5xx). |
| `7` | Other client error (4xx, including 429 — `Retry-After` is surfaced in the diagnostic). |
| `130` | Cancelled (Ctrl-C / SIGINT). |

Use `obi schema show <PATH>` to inspect the expected parameters and payload before making a
request. See [Discovering the API](schema.md).
