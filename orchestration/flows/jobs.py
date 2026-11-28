"""One flow per scheduled job (project spec §4.3 to §4.5).

Ported from ss.fm's `orchestration/flows/chains.py` (NEU-2531). Each flow applies the
missed-run rule, builds its argument list from its row of the deployments table, and
returns the state its command's exit maps to. No flow has retries and none takes a
parameter (spec §4.3, §4.9).
"""

from collections.abc import Callable
from datetime import datetime

from prefect import flow
from prefect.client.schemas.objects import FlowRun, State
from prefect.context import FlowRunContext

from flows import command
from flows.command import run_command, run_logger
from flows.deployments import BY_FLOW, Deployment
from flows.late import missed_run_state


def _current_flow_run() -> FlowRun | None:
    context = FlowRunContext.get()
    return context.flow_run if context is not None else None


def argv_for(row: Deployment) -> list[str]:
    """The command a run of `row` starts: the one Coolify runs today (spec §4.3)."""
    return [command.WRAPPER, command.PYTHON, "-m", row.module]


def run_job(
    row: Deployment,
    *,
    flow_run: FlowRun | None = None,
    now: datetime | None = None,
    runner: Callable[..., State] | None = None,
) -> State:
    """The body every job's flow shares.

    `flow_run` defaults to the current run and `runner` to `run_command`, looked up
    when called so a test can replace it.
    """
    if flow_run is None:
        flow_run = _current_flow_run()
    missed = missed_run_state(flow_run, tolerance_minutes=row.tolerance_minutes, now=now)
    if missed is not None:
        run_logger().warning("%s: missed run, %s", row.name, missed.message)
        return missed
    return (runner or run_command)(
        argv_for(row),
        job=row.job,
        timeout_seconds=row.timeout_seconds,
        deadman_env=row.deadman_env,
    )


@flow(name="tvbf-catalog-delta", retries=0)
def tvbf_catalog_delta() -> State:
    """The nightly TMDB catalog delta (NEU-1035)."""
    return run_job(BY_FLOW["tvbf-catalog-delta"])


@flow(name="tvbf-airdate-reconcile", retries=0)
def tvbf_airdate_reconcile() -> State:
    """The nightly airdate reconciliation against the TV Maze oracle (NEU-1145)."""
    return run_job(BY_FLOW["tvbf-airdate-reconcile"])


@flow(name="tvbf-push-airs-today", retries=0)
def tvbf_push_airs_today() -> State:
    """The daily airs-today push delivery (NEU-1540)."""
    return run_job(BY_FLOW["tvbf-push-airs-today"])


@flow(name="tvbf-trending-snapshot", retries=0)
def tvbf_trending_snapshot() -> State:
    """The daily trending snapshot (NEU-1055)."""
    return run_job(BY_FLOW["tvbf-trending-snapshot"])


@flow(name="tvbf-push-events", retries=0)
def tvbf_push_events() -> State:
    """The daily catalog-event push delivery and the 90-day purge (NEU-1540)."""
    return run_job(BY_FLOW["tvbf-push-events"])


@flow(name="tvbf-weekly-recommendations", retries=0)
def tvbf_weekly_recommendations() -> State:
    """The weekly recommendations pass (NEU-1109)."""
    return run_job(BY_FLOW["tvbf-weekly-recommendations"])
