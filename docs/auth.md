# Authentication

`obi` targets the Obitrain **v2** auth flow: a login returns a short-lived access token plus a
refresh token. The client attaches the access token as a bearer header and refreshes it
automatically — proactively when the token is a JWT nearing expiry, and reactively on a `401`.

## Logging in

```bash
obi auth login --email you@example.com           # prompts for the password
obi auth login --username jo --password "$PW"    # non-interactive
obi auth login-google   --token-value <id_token>
obi auth login-facebook --token-value <token>
obi auth login-apple    --token-value <token>
obi auth login-token    --token-value <login_token>
obi auth register --email you@example.com --username jo
```

Credentials are written to `~/.config/obi/profiles/<profile>.json` with `0600` permissions
(override the directory with `OBI_CONFIG_DIR`, or follow `XDG_CONFIG_HOME`).

## Managing the session

```bash
obi auth status              # profile, base URL, login state, refresh expiry, source
obi auth status --show-token # include the access token
obi auth whoami              # the authenticated user (GET /v1/user)
obi auth refresh             # rotate the refresh token now
obi auth token               # print ONLY the access token, for scripting
obi auth logout              # revoke server-side + clear local credentials
```

Use `obi auth token` to feed other tools:

```bash
curl -H "Authorization: Bearer $(obi auth token)" https://api.obitrain.com/v1/user
```

## Profiles (multiple accounts)

Every command accepts `--profile <name>` (or the `OBI_PROFILE` env var). Each profile is an isolated
credential file, so you can stay logged into several accounts or environments at once.

```bash
obi auth login --profile work  --email work@example.com
obi auth login --profile perso --email me@example.com
obi api /v1/user --profile work
obi auth profiles              # list known profiles
```

## Environment variables

| Variable | Effect |
|----------|--------|
| `OBI_BASE_URL` | Override the API base URL (default `https://api.obitrain.com`). |
| `OBI_TOKEN` | Use this bearer token directly. **Ephemeral**: nothing is persisted and refresh is disabled. |
| `OBI_PROFILE` | Select the credential profile. |
| `OBI_CONFIG_DIR` | Override where credentials are stored. |

Precedence is per field: command flag > environment variable > stored credentials > built-in default.
