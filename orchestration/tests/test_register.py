"""Registering a pool's deployments from the table (spec §4.7)."""

import contextlib
import dataclasses
from datetime import timedelta
from pathlib import Path

import pytest
from prefect import get_client
from prefect.client.orchestration import SyncPrefectClient
from prefect.client.schemas.actions import DeploymentUpdate
from prefect.client.schemas.filters import WorkPoolFilter, WorkPoolFilterName
from prefect.client.schemas.objects import StateType
from prefect.client.schemas.responses import DeploymentResponse
from prefect.events.actions import ChangeFlowRunState
from prefect.events.schemas.automations import (
    Automation,
    AutomationCore,
    EventTrigger,
    Posture,
)
from prefect.events.schemas.events import ResourceSpecification
from prefect.exceptions import ObjectNotFound

from flows import register as reg
from flows.deployments import BY_FLOW, DEPLOYMENTS

# The project's own directory: /app/orchestration in the container, the checkout in CI.
ORCHESTRATION = Path(__file__).resolve().parents[1]
POOL = "tvbf-jobs"
ROWS = [row for row in DEPLOYMENTS if row.pool == POOL]


def _client() -> SyncPrefectClient:
    return get_client(sync_client=True)


def _clear_server() -> None:
    with _client() as client:
        for deployment in client.read_deployments():
            client.delete_deployment(deployment.id)
        for automation in client.read_automations():
            client.delete_automation(automation.id)


def _on_pool(client: SyncPrefectClient, pool: str) -> list[DeploymentResponse]:
    return client.read_deployments(
        work_pool_filter=WorkPoolFilter(name=WorkPoolFilterName(any_=[pool]))
    )


def _servers_automation() -> AutomationCore:
    """One the ops repository could have made: register must leave it as it is."""
    return AutomationCore(
        name="the server's own automation",
        enabled=True,
        trigger=EventTrigger(
            after={"prefect.flow-run.heartbeat"},
            expect={"prefect.flow-run.heartbeat"},
            match=ResourceSpecification({"prefect.resource.id": ["prefect.flow-run.*"]}),
            for_each={"prefect.resource.id"},
            posture=Posture.Proactive,
            threshold=1,
            within=timedelta(seconds=540),
        ),
        actions=[
            ChangeFlowRunState(
                state=StateType.CRASHED, message="no heartbeat", name=None, force=False
            )
        ],
    )


def _register(pool: str, **kwargs: object) -> reg.Registered:
    kwargs.setdefault("environ", {})
    return reg.register(pool, source=ORCHESTRATION, **kwargs)  # type: ignore[arg-type]


def _by_name(client: SyncPrefectClient) -> dict[str, DeploymentResponse]:
    return {row.name: client.read_deployment_by_name(row.name) for row in ROWS}


@pytest.fixture
def clear_server() -> None:
    _clear_server()


@dataclasses.dataclass(frozen=True)
class TwoRegisters:
    first: reg.Registered
    second: reg.Registered
    deployments: list[DeploymentResponse]
    after_first: dict[str, DeploymentResponse]
    by_name: dict[str, DeploymentResponse]
    pool_type: str
    automation_before: Automation
    automations: list[Automation]


@pytest.fixture(scope="module")
def pool_twice() -> TwoRegisters:
    """Pool `tvbf-jobs` registered twice on a server holding one automation."""
    _clear_server()
    with _client() as client:
        automation_id = client.create_automation(_servers_automation())
        automation_before = client.read_automation(automation_id)
    assert automation_before is not None
    first = _register(POOL)
    with _client() as client:
        after_first = _by_name(client)
    second = _register(POOL)
    with _client() as client:
        return TwoRegisters(
            first=first,
            second=second,
            deployments=_on_pool(client, POOL),
            after_first=after_first,
            by_name=_by_name(client),
            pool_type=client.read_work_pool(POOL).type,
            automation_before=automation_before,
            automations=client.read_automations(),
        )


def test_registering_creates_exactly_its_rows_each_inactive(
    pool_twice: TwoRegisters,
) -> None:
    assert pool_twice.pool_type == "process"
    assert len(pool_twice.deployments) == len(ROWS) == 6
    assert {d.id for d in pool_twice.deployments} == {d.id for d in pool_twice.by_name.values()}
    for row in ROWS:
        deployment = pool_twice.by_name[row.name]
        assert row.name == f"{row.flow}/scheduled"
        assert [s.schedule.cron for s in deployment.schedules] == [row.cron]  # type: ignore[union-attr]
        assert [s.schedule.timezone for s in deployment.schedules] == ["UTC"]  # type: ignore[union-attr]
        assert [s.active for s in deployment.schedules] == [False]


def test_registering_twice_keeps_the_ids_and_one_schedule_each(
    pool_twice: TwoRegisters,
) -> None:
    assert pool_twice.second.deployment_ids == pool_twice.first.deployment_ids
    assert pool_twice.second.deleted == ()
    assert all(len(d.schedules) == 1 for d in pool_twice.deployments)


def test_a_second_register_writes_nothing(pool_twice: TwoRegisters) -> None:
    # Any write would delete each deployment's future scheduled runs. Not checked
    # through `updated`: the server's own services touch that.
    assert pool_twice.first.written == tuple(row.name for row in ROWS)
    assert pool_twice.second.written == ()
    for name, before in pool_twice.after_first.items():
        after = pool_twice.by_name[name]
        assert [s.id for s in after.schedules] == [s.id for s in before.schedules]


def test_each_deployment_runs_its_flow_from_the_project_directory(
    pool_twice: TwoRegisters,
) -> None:
    assert Path("/app/orchestration") == reg.SOURCE
    for row in ROWS:
        deployment = pool_twice.by_name[row.name]
        assert deployment.entrypoint == f"flows/jobs.py:{row.flow.replace('-', '_')}"
        assert deployment.pull_steps == [
            {"prefect.deployments.steps.set_working_directory": {"directory": str(ORCHESTRATION)}}
        ]
        assert deployment.job_variables == {"env": {"PREFECT_FLOWS_HEARTBEAT_FREQUENCY": "180"}}


def test_register_makes_no_automation_and_leaves_the_servers_alone(
    pool_twice: TwoRegisters,
) -> None:
    # The heartbeat automation is the server's, made in the ops repository.
    assert pool_twice.automations == [pool_twice.automation_before]


def test_the_table_wins_over_a_schedule_or_pause_set_through_the_api(
    clear_server: None,
) -> None:
    rows = [BY_FLOW["tvbf-trending-snapshot"]]
    _register(POOL, rows=rows)
    with _client() as client:
        deployment = client.read_deployment_by_name(BY_FLOW["tvbf-trending-snapshot"].name)
        client.update_deployment_schedule(deployment.id, deployment.schedules[0].id, active=True)
        client.update_deployment(deployment.id, DeploymentUpdate(paused=True))

    result = _register(POOL, rows=rows)

    assert result.written == (BY_FLOW["tvbf-trending-snapshot"].name,)

    with _client() as client:
        after = client.read_deployment(deployment.id)
    assert [s.active for s in after.schedules] == [False]
    assert not after.paused


@pytest.mark.parametrize(
    ("environ", "active"),
    [({"TVBF_SCHEDULES_ACTIVE": "false"}, False), ({}, True)],
)
def test_tvbf_schedules_active_false_overrides_an_active_row(
    clear_server: None, environ: dict[str, str], active: bool
) -> None:
    rows = [dataclasses.replace(BY_FLOW["tvbf-trending-snapshot"], active=True)]

    _register(POOL, rows=rows, environ=environ)

    with _client() as client:
        deployment = client.read_deployment_by_name(BY_FLOW["tvbf-trending-snapshot"].name)
    assert [s.active for s in deployment.schedules] == [active]


def test_an_unclear_schedules_flag_is_refused() -> None:
    with pytest.raises(reg.RegisterError, match="TVBF_SCHEDULES_ACTIVE"):
        reg.schedules_forced_off({"TVBF_SCHEDULES_ACTIVE": "no"})


def test_a_row_removed_from_the_table_is_deleted_and_nothing_else_is(
    clear_server: None,
) -> None:
    removed = BY_FLOW["tvbf-push-events"]
    kept = [row for row in ROWS if row != removed]
    elsewhere = dataclasses.replace(
        BY_FLOW["tvbf-catalog-delta"], pool="elsewhere", deployment="kept"
    )
    before = _register(POOL).deployment_ids
    _register("elsewhere", rows=[elsewhere])

    result = _register(POOL, rows=kept)

    with _client() as client:
        assert {d.id for d in _on_pool(client, POOL)} == {before[row.name] for row in kept}
        assert [d.name for d in _on_pool(client, "elsewhere")] == ["kept"]
    assert result.deleted == (f"scheduled ({before[removed.name]})",)
    assert result.written == ()


def test_a_pool_the_table_does_not_name_is_refused_before_anything_changes() -> None:
    with pytest.raises(reg.RegisterError, match="no deployment on pool"):
        _register("nowhere")


def test_the_cli_takes_only_the_tables_pools(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        reg.main(["--pool", "nowhere"])
    assert "invalid choice" in capsys.readouterr().err


def test_a_name_another_pool_holds_is_refused_and_nothing_is_written(
    clear_server: None,
) -> None:
    # Another app on the shared server, holding the name the trending row uses.
    theirs = dataclasses.replace(BY_FLOW["tvbf-trending-snapshot"], pool="another-app")
    [their_id] = _register("another-app", rows=[theirs]).deployment_ids.values()
    # An earlier test made it; without it, the refusal must not make it again.
    with _client() as client, contextlib.suppress(ObjectNotFound):
        client.delete_work_pool(POOL)

    # The clash is on the second row, so the first must not be written either.
    with pytest.raises(
        reg.RegisterError, match=r"tvbf-trending-snapshot/scheduled .* is on another-app"
    ):
        _register(POOL, rows=[BY_FLOW["tvbf-catalog-delta"], BY_FLOW["tvbf-trending-snapshot"]])

    with _client() as client:
        held = client.read_deployment_by_name(BY_FLOW["tvbf-trending-snapshot"].name)
        assert _on_pool(client, POOL) == []
        with pytest.raises(ObjectNotFound):
            client.read_work_pool(POOL)
    assert held.id == their_id
    assert held.work_pool_name == "another-app"
