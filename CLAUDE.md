# obi — Obitrain API CLI

Public CLI (`obi`, PyPI package `obitrain`) wrapping the Obitrain HTTP API. It supports interactive,
scripted, and agent use through authentication, offline schema discovery, and a generic `obi api`
passthrough rather than per-endpoint commands.

## Layout

- `src/obitrain/client.py` — async `ObiClient` over `niquests.AsyncSession`; bearer injection.
- `src/obitrain/auth.py` — `obi auth` group (login/set/clear/status/whoami/token/profiles).
- `src/obitrain/api/cmd.py` — generic `obi api <PATH>` (`-X/-d/-q/-H/-o/-n`).
- `src/obitrain/api/schema.py` — `obi schema` discovery; reads the packaged `src/obitrain/api/openapi.json`.
- `src/obitrain/api/models.py` — **generated** TypedDicts (do not edit; `sh bin/codegen.sh`).
- `src/obitrain/{config,creds,output,errors,runner,options}.py` — config resolution, 0600 per-profile
  credential store, output rendering, error/exit-code mapping, command dispatch helpers, shared piou options.
- `src/obitrain/quickstart.md` — packaged agent guide printed by `obi quickstart`; linked from
  `docs/agent-quickstart.md`.
- `static/openapi.json` — vendored source of truth; `bin/codegen.sh` copies it into the package and
  regenerates `src/obitrain/api/models.py`.

## Conventions

- Python 3.14, `uv` + `uv_build`, src layout. Absolute imports only (ruff `ban-relative-imports`).
- Single quotes inline, double for docstrings; `ruff format` with `quote-style = "single"`. Line length 120.
- Prose docstrings (no Args/Returns). `collections.abc` for abstract types, builtins for concrete generics.
- Tests: pytest only; HTTP stubbed via a niquests `AsyncBaseAdapter` (see `tests/conftest.py` `StubAdapter`),
  not pytest-httpserver. Parametrize with `pytest.param(..., id=...)`.

## Commands

```bash
uv sync --all-groups
uv run ruff check src tests && uv run ruff format --check src tests
uv run pyright
uv run pytest
sh bin/codegen.sh && git diff --exit-code src/obitrain/api/models.py   # model drift gate
uv run --group docs zensical serve   # docs preview
```

## Exit codes

`0` ok · `1` usage · `4` auth · `5` network · `6` server (5xx) · `7` client (4xx). Errors emit a
one-line JSON diagnostic to stderr; response bodies always go to stdout.
