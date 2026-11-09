#!/bin/sh
# Write src/api/schema.d.ts from the API's OpenAPI document, read on stdin (NEU-2261):
#
#   task fe:generate    # exports openapi.json from the backend, then runs this on it
#
# Both files are committed, and CI's `api-types` job regenerates them and fails if either
# changed, so a response model the SPA hasn't followed fails before merge. `src/api/types.ts`
# names the generated schemas the rest of the app imports.
set -eu

cd "$(dirname "$0")/.."

dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
cat > "$dir/openapi.json"

# From tools/openapi-types, where the generator has the TypeScript 5 it needs (see
# pnpm-workspace.yaml); paths are absolute because `--dir` moves the working directory.
pnpm --dir tools/openapi-types exec openapi-typescript "$dir/openapi.json" \
  --output "$PWD/src/api/schema.d.ts"

# The app's prettier, so the committed file is what the fe-format hook expects.
pnpm exec prettier --log-level warn --write src/api/schema.d.ts
