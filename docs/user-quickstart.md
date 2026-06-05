# User quickstart

This guide takes you from installation to your first authenticated API requests.

## 1. Install `obi`

Install the CLI as a persistent tool with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install obitrain
obi version
```

You can also run it without installing it:

```bash
uvx --from obitrain obi --help
```

## 2. Sign in

```bash
obi auth login
```

The command prints a short code. In the Obitrain mobile app, open **Account -> Link a device**,
enter the code, and approve the request. The CLI stores the resulting API token in your active
profile.

Confirm the session:

```bash
obi auth status
obi auth whoami
```

See [Authentication](auth.md) for API tokens, multiple profiles, and ephemeral credentials.

## 3. Make a request

`obi api` accepts any Obitrain API path:

```bash
obi api /v1/user
obi api /v1/training/sessions -q limit=5
```

Output is formatted for reading when you use an interactive terminal. Use `--json` when you want
plain JSON:

```bash
obi api /v1/user --json
```

## 4. Discover endpoints

The OpenAPI contract is bundled with `obi`, so these commands work offline:

```bash
obi schema tags
obi schema list --grep session
obi schema show /v1/training/sessions -X GET
```

`schema show` displays parameters, request bodies, responses, and referenced schemas for an
operation.

## 5. Send data

Pass JSON directly or read it from a file. Providing `-d` implies `POST` unless you set a method
with `-X`.

```bash
obi api /v1/user -X PATCH -d '{"lang":"fr"}'
obi api /v1/training/session -d @session.json
```

Use `-n` to inspect the resolved request without sending it:

```bash
obi api /v1/user -X PATCH -d '{"lang":"fr"}' -n
```

The token is redacted from dry-run output. See [Making requests](api.md) for all request and output
options.
