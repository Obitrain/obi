<div class="obi-hero">
  <img src="assets/images/logo.png" alt="Obitrain" />
  <h1>obi</h1>
  <p>The agent-first CLI for the <strong>Obitrain API</strong> — authenticate once,
  call any endpoint, discover the contract offline.</p>
</div>

```bash
uv tool install obitrain      # exposes the `obi` binary

obi auth login                # approve a short code in the Obitrain app — no password
obi api /v1/training/sessions -q limit=5
```

<div class="obi-cards">
  <a href="auth/">
    <strong>Authentication</strong>
    Device-code login, API tokens, profiles, and headless usage with <code>OBI_TOKEN</code>.
  </a>
  <a href="api/">
    <strong>Making requests</strong>
    One generic <code>obi api</code> command: methods, query params, bodies, dry-run.
  </a>
  <a href="agent-quickstart/">
    <strong>Agent quickstart</strong>
    The contract for LLMs: JSON output, exit codes, and self-repairing error hints.
  </a>
</div>

## Why it fits agents

- **Deterministic output.** Bodies on stdout, one-line JSON diagnostics on stderr; plain JSON
  whenever output is piped or an agent environment is detected (`--json` to force it).
- **Deterministic exit codes.** `0` ok, `4` auth, `5` network, `6` server (5xx), `7` client (4xx).
- **Errors carry their own fix.** `404`/`405`/`422` diagnostics include a `hint` with the missing
  parameters and the exact `obi schema show` command to run.
- **Self-describing.** `obi schema` exposes the API contract from the bundled OpenAPI spec, and
  `obi quickstart` prints the full agent guide — no web access needed.

## Why it fits humans

- **Readable by default.** Tables and highlighted output on a TTY, with enum codes labeled
  (`friends (2)`, not `2`).
- **One command for everything.** No per-endpoint wrappers to learn or maintain.
- **Safe by design.** Tokens stored per profile with `0600` permissions, revocable from the app;
  `-n` dry-runs any request before sending it.
