# obi

`obi` is a small, agent-first command-line client for the **Obitrain API**. It handles
authentication (including transparent token refresh) and lets you call any endpoint with a single
generic command, so both humans and AI agents can drive the API without bespoke per-endpoint tooling.

## Install

```bash
uv tool install obitrain      # exposes the `obi` binary
# or run without installing:
uvx --from obitrain obi --help
```

## At a glance

```bash
obi auth login --email you@example.com          # authenticate (prompts for password)
obi api /v1/activities -q size=1                # call any endpoint
obi schema list --grep activities               # discover endpoints from the bundled OpenAPI spec
```

## Why it fits agents

- **JSON by default.** Output is machine-readable unless you ask for `pretty`/`yaml`.
- **Deterministic exit codes.** `0` ok, `4` auth, `5` network, `6` server (5xx), `7` client (4xx).
- **Self-describing.** `obi schema` exposes the API contract from the OpenAPI spec shipped in the package.
- **No memorized URLs required**, but no hand-written wrappers to maintain either.

See [Authentication](auth.md), [Making requests](api.md) and the [Agent quickstart](agent-quickstart.md).
