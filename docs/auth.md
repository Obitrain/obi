# Authentication

`obi` authenticates requests with an Obitrain API token. You can create one through the
device-code login flow, store an existing token in a named profile, or provide an ephemeral token
for a single process.

## Logging in

```bash
obi auth login
```

The command prints a short code and waits. In the Obitrain mobile app, open **Account -> Link a
device**, enter the code, and approve the request. The resulting token is long-lived and can be
revoked from the app.

Use `--description` to choose the label shown for the token:

```bash
obi auth login --description "Laptop CLI"
```

If you already generated an API token from your Account page, store it directly:

```bash
obi auth set <token>
```

Credentials are written to `~/.config/obi/profiles/<profile>.json` with `0600` permissions.
`OBI_CONFIG_DIR` overrides the directory; otherwise `XDG_CONFIG_HOME` is respected.

## Managing the session

```bash
obi auth status              # profile, base URL, login state, source
obi auth status --show-token # include the access token
obi auth whoami              # the authenticated user (GET /v1/user)
obi auth token               # print ONLY the access token, for scripting
obi auth clear               # remove the active profile's local credentials
```

`auth clear` only removes the local credential file. Revoke the token from the Obitrain app when
it must no longer be valid.

Use `obi auth token` to feed another command without adding formatting:

```bash
curl -H "Authorization: Bearer $(obi auth token)" https://api.obitrain.com/v1/user
```

## Profiles (multiple accounts)

Commands that connect to the API accept `--profile <name>` (or the `OBI_PROFILE` env var). Each
profile is an isolated credential file, so you can stay logged into several accounts or
environments at once.

```bash
obi auth login --profile work
obi auth set <token> --profile personal
obi api /v1/user --profile work
obi auth profiles              # list known profiles
```

## Ephemeral tokens

Use `--token` or `OBI_TOKEN` when credentials should not be written to disk, such as in CI or
another automation process:

```bash
OBI_TOKEN="<api token>" obi api /v1/user --json
obi api /v1/user --token "<api token>" --json
```

An ephemeral token takes precedence over stored credentials.

## Environment variables

| Variable | Effect |
|----------|--------|
| `OBI_BASE_URL` | Override the API base URL (default `https://api.obitrain.com`). |
| `OBI_TOKEN` | Use this bearer token directly without persisting it. |
| `OBI_PROFILE` | Select the credential profile. |
| `OBI_CONFIG_DIR` | Override where credentials are stored. |

Precedence is per field: command flag > environment variable > stored credentials > built-in default.
