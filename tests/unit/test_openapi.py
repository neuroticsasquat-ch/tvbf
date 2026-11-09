"""`python -m tvbf.openapi`, the export behind the committed `openapi.json` (NEU-2261)."""

import json
import os
import subprocess
import sys

from tvbf.main import app
from tvbf.openapi import openapi_json


def _export(hash_seed: str) -> bytes:
    result = subprocess.run(
        [sys.executable, "-m", "tvbf.openapi"],
        capture_output=True,
        check=True,
        env={**os.environ, "PYTHONHASHSEED": hash_seed},
    )
    return result.stdout


def test_stdout_is_the_document_and_nothing_else():
    # The task redirects stdout into the file, so a log line on it would corrupt the snapshot.
    document = json.loads(_export("0"))

    assert document["info"]["title"] == "tvbf-backend"
    assert "/healthz" in document["paths"]
    assert "ShowSummary" in document["components"]["schemas"]


def test_the_export_is_byte_identical_across_interpreter_runs():
    # A set iterated into the document would reorder under a different hash seed, and CI's drift
    # check would then fail on a contract nobody changed.
    assert _export("1") == _export("2")


def test_the_document_ends_with_a_newline():
    assert openapi_json(app).endswith("}\n")
