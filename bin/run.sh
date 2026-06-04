#!/usr/bin/env sh
set -eu

# DESCRIPTION: Run the obi CLI from the source tree.
# USAGE: bin/run.sh <args...>
# EXAMPLES:
#   bin/run.sh --help
#   bin/run.sh api GET /v1/activities -q size=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec uv run obi "$@"
