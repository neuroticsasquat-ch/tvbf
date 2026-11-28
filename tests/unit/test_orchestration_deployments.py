"""Every row of the Prefect deployments table names a job this app can run.

A typo in a row's module would otherwise be a `Failed` run at 09:00 (project spec §4.3).
The table is loaded by its path: the app's environment has no Prefect, and the table
imports only the standard library so that it can be.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

TABLE = Path(__file__).parents[2] / "orchestration" / "flows" / "deployments.py"


def _load_table() -> ModuleType:
    spec = importlib.util.spec_from_file_location("orchestration_deployments", TABLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # A dataclass resolves its module through sys.modules while it is being built.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


table = _load_table()


def test_the_table_has_rows() -> None:
    assert table.DEPLOYMENTS


@pytest.mark.parametrize("row", table.DEPLOYMENTS, ids=lambda row: row.flow)
def test_a_rows_module_imports_and_has_a_main(row: Any) -> None:
    module = importlib.import_module(row.module)

    assert callable(getattr(module, "main", None)), f"{row.module} has no main()"
