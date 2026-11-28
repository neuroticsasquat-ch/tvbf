"""The wait: a flow holds its command while a flow it runs after is in flight (project
spec §4.6, ADR-0016 decision 5).

New here: ss.fm has no order between chains to hold. Four jobs read what an earlier job
wrote, and before this only gaps on a clock kept them in order, gaps the delta's
3-hour timeout does not respect. So a flow whose row names flows under `runs_after`
asks Prefect's API whether any of them has a run in flight, and sleeps while one does.

The job runs whatever happened upstream. A job that runs out of order is a night late
on some data, which the guide already bounds; a job that does not run at all is worse,
since an airs-today push is worthless a day later. So the wait is capped, a failed read
ends it, and an upstream's end state is not consulted. Every job keeps its own cron and
its own deadman, so an upstream that fails, is missed or crashes never silences one.

**The wait sees only runs Prefect started.** A delta started by `task`, `docker exec`
or the admin trigger is invisible to it, as it is to the clock today.
"""

import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta

from prefect import get_client
from prefect.client.schemas.filters import (
    FlowFilter,
    FlowFilterName,
    FlowRunFilter,
    FlowRunFilterExpectedStartTime,
    FlowRunFilterState,
    FlowRunFilterStateType,
)
from prefect.client.schemas.objects import StateType

from flows.command import run_logger
from flows.deployments import DEFAULT_TOLERANCE_MINUTES, Deployment

# How long the flow sleeps between two reads of the API.
POLL_SECONDS = 30.0
# The cap on the wait. A daily Kuma monitor's interval is 25 hours, so a job's ping can
# move one hour later before its monitor fires (spec §3.2). The reconcile's worst run
# in the 30 days to 2026-11-27 was 13 minutes, so a 45-minute wait still pings inside
# that hour; a longer one would fire the waiting job's monitor before its ping arrived.
MAX_WAIT_SECONDS = 45 * 60.0
# A `Scheduled` run whose expected start is at most this far in the past is a late run
# not yet picked up, and is waited for. One later than this is Missed when a worker
# picks it up (spec §4.4) and runs no command, so there is nothing to wait for.
LATE_LOOKBACK = timedelta(minutes=DEFAULT_TOLERANCE_MINUTES)

Reader = Callable[[Iterable[str]], set[str]]


def flows_in_flight(flow_names: Iterable[str], *, now: datetime | None = None) -> set[str]:
    """The names, among `flow_names`, of flows with a run in flight.

    In flight is `Pending` or `Running`, or `Scheduled` with an expected start in the
    last `LATE_LOOKBACK` (Prefect calls that state `Late`). A run scheduled for later
    today is not in flight.
    """
    now = now or datetime.now(UTC)
    started = FlowRunFilter(
        state=FlowRunFilterState(
            type=FlowRunFilterStateType(any_=[StateType.PENDING, StateType.RUNNING])
        )
    )
    late = FlowRunFilter(
        state=FlowRunFilterState(type=FlowRunFilterStateType(any_=[StateType.SCHEDULED])),
        # Validated rather than constructed: the fields are typed as Prefect's own
        # `DateTime`, which pydantic builds from a stdlib datetime but pyright will not.
        expected_start_time=FlowRunFilterExpectedStartTime.model_validate(
            {"after_": now - LATE_LOOKBACK, "before_": now}
        ),
    )
    live: set[str] = set()
    with get_client(sync_client=True) as client:
        for name in flow_names:
            flow_filter = FlowFilter(name=FlowFilterName(any_=[name]))
            if any(
                client.read_flow_runs(flow_filter=flow_filter, flow_run_filter=run_filter, limit=1)
                for run_filter in (started, late)
            ):
                live.add(name)
    return live


def wait_for_upstream(
    row: Deployment,
    *,
    read: Reader = flows_in_flight,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Return once no flow `row` runs after is in flight, or at the cap, or on a failed read.

    Never raises: whatever happens here, the flow goes on to run its command.
    """
    if not row.runs_after:
        return
    log = run_logger()
    start = clock()
    waited_for: set[str] = set()
    while True:
        try:
            live = read(row.runs_after)
        # Any failure, not a list of them: the read crosses an HTTP client, a server
        # and a schema, and every way it fails means the same thing here.
        except Exception:
            log.warning(
                "%s: could not read the runs of %s; running without waiting",
                row.flow,
                ", ".join(row.runs_after),
                exc_info=True,
            )
            return
        waited = clock() - start
        if not live:
            if waited_for:
                log.info(
                    "%s: waited %d s for %s",
                    row.flow,
                    round(waited),
                    ", ".join(sorted(waited_for)),
                )
            else:
                log.info("%s: nothing it runs after is in flight", row.flow)
            return
        waited_for |= live
        if waited >= MAX_WAIT_SECONDS:
            log.warning(
                "%s: waited %d s for %s, still in flight; running anyway",
                row.flow,
                round(waited),
                ", ".join(sorted(live)),
            )
            return
        sleep(min(POLL_SECONDS, MAX_WAIT_SECONDS - waited))
