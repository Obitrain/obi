#!/usr/bin/env bash
set -euo pipefail

# DESCRIPTION: Refresh static/openapi.json from an obitrain-api release tag on GitLab
#              (latest by default); exports API_TAG to $GITHUB_ENV when running in CI.
# USAGE: GITLAB_TOKEN=<token with read_api> bin/fetch-spec.sh [tag]
# EXAMPLES:
#   GITLAB_TOKEN=... bin/fetch-spec.sh          # latest release tag
#   GITLAB_TOKEN=... bin/fetch-spec.sh v1.95.0  # pin a specific tag

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

api='https://gitlab.com/api/v4/projects/obitrain%2Fobitrain-api'
tag="${1:-}"
if [ -z "$tag" ]; then
  tag=$(curl -fsS --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    "$api/repository/tags?order_by=version&sort=desc&per_page=1" | jq -r '.[0].name')
fi
echo "Fetching openapi.json @ $tag"
curl -fsS --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$api/repository/files/static%2Fopenapi.json/raw?ref=$tag" -o static/openapi.json

if [ -n "${GITHUB_ENV:-}" ]; then
  echo "API_TAG=$tag" >>"$GITHUB_ENV"
fi
