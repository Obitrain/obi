set quiet

# List available recipes
default:
    @just --list

# Lint
[group('dev')]
lint:
    uv run ruff check src tests
    uv run ruff format --check src tests

# Format and auto-fix
[group('dev')]
fmt:
    uv run ruff format src tests
    uv run ruff check --fix src tests

# Type check
[group('dev')]
check:
    uv run pyright

# Run tests
[group('dev')]
test *args:
    uv run pytest "$@"

# Lint + type check + test
[group('dev')]
ci: lint check test drift

# Regenerate src/obitrain/api/models.py from static/openapi.json
[group('codegen')]
codegen:
    sh bin/codegen.sh

# Fetch the spec from an obitrain-api release tag (latest by default) and regenerate models (GITLAB_TOKEN required)
[group('codegen')]
refresh tag="":
    bin/fetch-spec.sh {{ tag }}
    bin/codegen.sh

# Fail if generated files drifted from the spec
[group('codegen')]
drift: codegen
    git diff --exit-code src/obitrain/api/models.py src/obitrain/api/openapi.json

# Bump version (commitizen — updates pyproject.toml and CHANGELOG)
[group('release')]
bump *args:
    uv run --group bump cz bump {{ args }}

# Serve docs with live preview
[group('docs')]
docs:
    uv run --group docs zensical serve

# Build the static docs site -> ./site
[group('docs')]
docs-build:
    uv run --group docs zensical build
