"""The API's OpenAPI document, as the committed `openapi.json` holds it (NEU-2261).

    python -m tvbf.openapi > openapi.json    # what `task api:openapi` runs

The SPA's API types are generated from that file (`frontend/scripts/generate-api.sh`), and CI's
`api-types` job regenerates both and fails on any difference, so a response model that changes
without its client following fails before merge rather than in production.

The document goes to stdout and nothing else does: `create_app` logs to stderr, so the redirect
captures the document alone. Building the app opens no connection, which is why CI can export it
without a database.

Keys are left in the order FastAPI emits them (route registration, then field declaration) rather
than sorted, so the generated types read in the same order as the Pydantic models they come from.
That order is a property of the code, so it is as stable as sorting would be, and
`tests/unit/test_openapi.py` asserts it does not vary between interpreter runs.
"""

import json
import sys

from fastapi import FastAPI


def openapi_json(app: FastAPI) -> str:
    """`app`'s OpenAPI document as the bytes `openapi.json` holds, trailing newline included."""
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    from tvbf.main import app

    sys.stdout.buffer.write(openapi_json(app).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
