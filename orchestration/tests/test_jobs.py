"""The jobs' flows (project spec §4.3, §4.4)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from prefect import Flow
from prefect.client.schemas.objects import FlowRun, State, StateType

from flows import command, jobs
from flows.deployments import BY_FLOW, DEPLOYMENTS, Deployment


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(self, argv: list[str], **kwargs: object) -> State:
        self.calls.append((argv, kwargs))
        return State(type=StateType.COMPLETED)


@pytest.fixture(autouse=True)
def no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wait is tested in test_wait.py; here it would read the shared server's runs."""
    monkeypatch.setattr(jobs, "wait_for_upstream", lambda row: None)


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> FakeRunner:
    fake = FakeRunner()
    monkeypatch.setattr(jobs, "run_command", fake)
    return fake


def _flows() -> dict[str, Flow[[], State]]:
    return {v.name: v for v in vars(jobs).values() if isinstance(v, Flow)}


def _late_scheduled_run() -> FlowRun:
    return FlowRun.model_validate(
        {
            "flow_id": uuid.uuid4(),
            "auto_scheduled": True,
            "expected_start_time": datetime.now(UTC) - timedelta(hours=2),
        }
    )


def test_every_table_row_has_a_flow_and_no_flow_retries() -> None:
    flows = _flows()

    assert sorted(flows) == sorted(BY_FLOW)
    assert all(f.retries == 0 for f in flows.values())
    for row in DEPLOYMENTS:
        assert row.entrypoint == f"flows/jobs.py:{flows[row.flow].fn.__name__}"


@pytest.mark.parametrize("row", DEPLOYMENTS, ids=lambda row: row.flow)
def test_a_flow_runs_its_rows_command(row: Deployment, runner: FakeRunner) -> None:
    state = _flows()[row.flow](return_state=True)

    assert state.is_completed()
    assert runner.calls == [
        (
            [command.WRAPPER, command.PYTHON, "-m", row.module],
            {
                "job": row.job,
                "timeout_seconds": row.timeout_seconds,
                "deadman_env": row.deadman_env,
            },
        )
    ]


@pytest.mark.parametrize("row", DEPLOYMENTS, ids=lambda row: row.flow)
def test_a_late_scheduled_run_is_missed_and_runs_nothing(
    row: Deployment, runner: FakeRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "_current_flow_run", _late_scheduled_run)

    state = _flows()[row.flow](return_state=True)

    assert (state.type, state.name) == (StateType.CANCELLED, "Missed")
    assert runner.calls == []


def test_the_job_name_is_the_modules_last_part() -> None:
    assert BY_FLOW["tvbf-catalog-delta"].job == "catalog_update"
