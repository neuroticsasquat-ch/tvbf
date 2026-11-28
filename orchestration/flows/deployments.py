"""The deployments table: one row per scheduled job (project spec §4.5).

Standard library only. The app's suite loads this file by its path and checks that
every row's module imports and has a `main` (`tests/unit/test_orchestration_deployments.py`),
and the app's environment has no Prefect.

Once a job's cutover is done, this table is the one place in the repository its
schedule is written; until then Coolify runs it and the guide still states it. Ported
from ss.fm's `orchestration/flows/deployments.py` (NEU-2531). Each row is a job's
existing command, `python -m <module>` behind the OpenTelemetry wrapper (spec §4.3);
no tvbf deployment takes a parameter (§4.9), so there is nothing to validate here.

Every row is inactive until its cutover ticket. The timeouts are Coolify's, as read on
2026-11-27, trending's 10 hours for a 7-second job included: the port moves where a
number lives, not what it is. A timeout covers the command, not the wait before it.
`runs_after` is recorded here and acted on by the wait (§4.6).
"""

from collections.abc import Mapping
from dataclasses import dataclass

# The one work pool every tvbf deployment is on.
POOL = "tvbf-jobs"

# A scheduled run that starts later than this is a missed run (spec §4.4).
DEFAULT_TOLERANCE_MINUTES = 30


@dataclass(frozen=True)
class Deployment:
    """One deployment of one job's flow."""

    flow: str
    # The job's module, after `python -m`.
    module: str
    # UTC.
    cron: str
    timeout_seconds: int
    # The environment variable that holds the job's deadman URL.
    deadman_env: str
    # The flows this one waits for (spec §4.6), by flow name.
    runs_after: tuple[str, ...] = ()
    active: bool = False
    tolerance_minutes: int | None = DEFAULT_TOLERANCE_MINUTES
    pool: str = POOL
    deployment: str = "scheduled"
    # The file that defines the row's flow, relative to orchestration/. The flow's
    # function is its name with `-` as `_`.
    file: str = "flows/jobs.py"

    @property
    def name(self) -> str:
        return f"{self.flow}/{self.deployment}"

    @property
    def entrypoint(self) -> str:
        """Where Prefect finds the flow: `<file>:<function>` (spec §4.7)."""
        return f"{self.file}:{self.flow.replace('-', '_')}"

    @property
    def job(self) -> str:
        """The name the job gives itself (`tvbf/jobs/scheduled.py`), for a deadman message."""
        return self.module.rsplit(".", 1)[-1]


DEPLOYMENTS: tuple[Deployment, ...] = (
    Deployment(
        flow="tvbf-catalog-delta",
        module="tvbf.jobs.catalog_update",
        cron="0 9 * * *",
        timeout_seconds=10800,
        deadman_env="HEALTHCHECK_CATALOG_URL",
    ),
    Deployment(
        flow="tvbf-airdate-reconcile",
        module="tvbf.jobs.airdate_reconcile",
        cron="0 11 * * *",
        timeout_seconds=10800,
        deadman_env="HEALTHCHECK_AIRDATE_URL",
        runs_after=("tvbf-catalog-delta",),
    ),
    Deployment(
        flow="tvbf-push-airs-today",
        module="tvbf.jobs.push_airs_today",
        cron="0 13 * * *",
        timeout_seconds=900,
        deadman_env="HEALTHCHECK_PUSH_AIRS_TODAY_URL",
        runs_after=("tvbf-catalog-delta", "tvbf-airdate-reconcile"),
    ),
    # Follows nothing, deliberately (NEU-1055): an entry TMDB created this morning is
    # dropped from today's snapshot whichever runs first.
    Deployment(
        flow="tvbf-trending-snapshot",
        module="tvbf.jobs.trending_snapshot",
        cron="15 13 * * *",
        timeout_seconds=36000,
        deadman_env="HEALTHCHECK_TRENDING_URL",
    ),
    Deployment(
        flow="tvbf-push-events",
        module="tvbf.jobs.push_events",
        cron="0 17 * * *",
        timeout_seconds=300,
        deadman_env="HEALTHCHECK_PUSH_EVENTS_URL",
        runs_after=("tvbf-catalog-delta", "tvbf-airdate-reconcile"),
    ),
    Deployment(
        flow="tvbf-weekly-recommendations",
        module="tvbf.jobs.weekly_recommendations",
        cron="15 12 * * 1",
        timeout_seconds=36000,
        deadman_env="HEALTHCHECK_RECOMMENDATIONS_URL",
        runs_after=("tvbf-catalog-delta",),
    ),
)

BY_FLOW: Mapping[str, Deployment] = {row.flow: row for row in DEPLOYMENTS}
