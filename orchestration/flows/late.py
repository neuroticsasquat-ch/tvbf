"""The missed-run rule (project spec §4.4).

Ported unchanged from ss.fm's `orchestration/flows/late.py` (NEU-2530). Prefect never
expires a late run, and a worker that comes back after an outage runs the whole
backlog: a catalog delta scheduled for 09:00 could start in the afternoon, after the
jobs that read it. So a run the scheduler created that starts later than its tolerance
does nothing and is recorded as missed. The job's deadman then goes silent and fires,
as it does today when a Coolify task is missed. A run started by hand is never missed.
"""

from datetime import UTC, datetime, timedelta

from prefect.client.schemas.objects import FlowRun, State
from prefect.states import Cancelled


def missed_run_state(
    flow_run: FlowRun | None,
    *,
    tolerance_minutes: int | None,
    now: datetime | None = None,
) -> State | None:
    """`Cancelled(name="Missed")` if this run is a missed run, else None.

    `tolerance_minutes` None exempts the deployment (the batch wait, spec §4.14).
    """
    if flow_run is None or not flow_run.auto_scheduled or tolerance_minutes is None:
        return None
    scheduled = flow_run.expected_start_time
    if scheduled is None:
        return None
    lateness = (now or datetime.now(UTC)) - scheduled
    if lateness <= timedelta(minutes=tolerance_minutes):
        return None
    minutes = int(lateness.total_seconds() // 60)
    return Cancelled(
        name="Missed",
        message=(
            f"started {minutes} minutes after its scheduled time "
            f"{scheduled.isoformat()}; the tolerance is {tolerance_minutes}"
        ),
    )
