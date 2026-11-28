"""The deployments table (project spec §4.5)."""

import ast
import sys
from pathlib import Path

from flows import deployments
from flows.deployments import BY_FLOW, DEPLOYMENTS


def test_every_flow_name_starts_with_tvbf() -> None:
    # The server is shared by every app on the box: the prefix is tvbf's namespace.
    assert all(row.flow.startswith("tvbf-") for row in DEPLOYMENTS)


def test_flow_names_are_unique() -> None:
    assert len(BY_FLOW) == len(DEPLOYMENTS)


def test_every_row_has_a_timeout() -> None:
    assert all(row.timeout_seconds > 0 for row in DEPLOYMENTS)


def test_every_row_is_inactive() -> None:
    # Each row is set active by its cutover ticket, not before.
    assert [row.flow for row in DEPLOYMENTS if row.active] == []


def test_every_runs_after_name_is_a_flow_in_the_table() -> None:
    for row in DEPLOYMENTS:
        assert set(row.runs_after) <= set(BY_FLOW), row.flow


def test_the_runs_after_graph_has_no_cycle() -> None:
    done: set[str] = set()

    def visit(flow: str, path: tuple[str, ...]) -> None:
        assert flow not in path, f"cycle: {' -> '.join((*path, flow))}"
        if flow in done:
            return
        for upstream in BY_FLOW[flow].runs_after:
            visit(upstream, (*path, flow))
        done.add(flow)

    for row in DEPLOYMENTS:
        visit(row.flow, ())


def test_every_row_is_on_the_one_pool() -> None:
    assert {row.pool for row in DEPLOYMENTS} == {"tvbf-jobs"}


def test_the_table_imports_only_the_standard_library() -> None:
    tree = ast.parse(Path(deployments.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a relative import is not the standard library"
            imported.add((node.module or "").split(".")[0])

    assert imported, "no imports found: the check read the wrong file"
    assert imported <= sys.stdlib_module_names, imported - sys.stdlib_module_names
