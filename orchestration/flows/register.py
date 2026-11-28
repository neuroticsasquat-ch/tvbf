"""Register the work pool's deployments from the table in code (project spec §4.7).

    /opt/prefect-venv/bin/python -m flows.register --pool tvbf-jobs

Ported from ss.fm's `orchestration/flows/register.py` as NEU-2543 left it for a shared
server. Nothing lives only in Prefect's database: every worker runs this at start, and
it puts its pool back exactly as `flows/deployments.py` declares it. Prefect's own
tools cannot. `prefect deploy` prunes nothing and keeps a schedule paused in the UI
paused. So:

- the work pool is created if it is missing, type `process`;
- every row of the pool is upserted as `<flow>/scheduled`, with one UTC cron
  schedule whose `active` is set explicitly, so the table wins over a toggle made
  in the UI. `TVBF_SCHEDULES_ACTIVE=false` registers every schedule inactive,
  whatever the table says: the quick way back during the cutover;
- a deployment on the pool that the table no longer names is deleted. Another
  pool's deployments are never changed;
- a row whose name another pool already holds is refused before anything is
  written. The server is ops' and shared by every app on the box, and names are
  looked up across the whole server, so without this tvbf's register would move
  another app's deployment onto its own pool.

Register makes no automation and changes none. The heartbeat automation that marks
a run `Crashed` when its worker stops without ending it (Prefect issue 16746)
covers every run on the server, so it is the server's and lives in the ops
repository with it.

Running it twice changes nothing the second time: a deployment is written only
when it differs from the table, and its schedule keeps its id through its slug.
"""

import argparse
import asyncio
import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from prefect import get_client
from prefect._internal.versioning import VersionType
from prefect.client.orchestration import PrefectClient
from prefect.client.schemas.actions import (
    DeploymentScheduleCreate,
    DeploymentScheduleUpdate,
    WorkPoolCreate,
)
from prefect.client.schemas.filters import WorkPoolFilter, WorkPoolFilterName
from prefect.client.schemas.objects import DeploymentSchedule
from prefect.client.schemas.responses import DeploymentResponse
from prefect.deployments.runner import RunnerDeployment
from prefect.exceptions import ObjectAlreadyExists, ObjectNotFound
from prefect.flows import Flow
from prefect.schedules import Cron
from prefect.workers.process import ProcessWorker

from flows.deployments import DEPLOYMENTS, Deployment

# Where the image puts this project. The flows run from here (spec §4.7).
SOURCE = Path("/app/orchestration")
POOL_TYPE = "process"
SCHEDULES_ACTIVE_ENV = "TVBF_SCHEDULES_ACTIVE"
# The one schedule each deployment has. The slug lets a re-register update that
# schedule in place, so it keeps its id.
SCHEDULE_SLUG = "cron"
TIMEZONE = "UTC"

# How often every flow run beats. The server's heartbeat automation, kept in the
# ops repository, marks a run Crashed after 540 s without a beat: three missed.
HEARTBEAT_FREQUENCY_SECONDS = 180

logger = logging.getLogger("flows.register")


class RegisterError(RuntimeError):
    """Registering cannot go on safely. Nothing further was changed."""


@dataclass(frozen=True)
class Registered:
    """What one register left on the server for its pool."""

    deployment_ids: Mapping[str, UUID]
    # The deployments this register wrote: those that were missing or differed.
    written: tuple[str, ...]
    deleted: tuple[str, ...]


def schedules_forced_off(environ: Mapping[str, str]) -> bool:
    """True when `TVBF_SCHEDULES_ACTIVE=false` (any case). Unset or empty: False.

    Any other value is refused: a typo must not leave a schedule live.
    """
    value = environ.get(SCHEDULES_ACTIVE_ENV, "").strip().lower()
    if value in ("", "true"):
        return False
    if value == "false":
        return True
    given = environ[SCHEDULES_ACTIVE_ENV]
    raise RegisterError(f"{SCHEDULES_ACTIVE_ENV} must be true or false, not {given!r}")


async def ensure_work_pool(client: PrefectClient, pool: str) -> None:
    """Create the pool, type `process`, if it is missing. Refuse one of another type."""
    try:
        existing = await client.read_work_pool(pool)
    except ObjectNotFound:
        try:
            await client.create_work_pool(
                WorkPoolCreate(
                    name=pool,
                    type=POOL_TYPE,
                    base_job_template=ProcessWorker.get_default_base_job_template(),
                )
            )
            logger.info("created work pool %s", pool)
        except ObjectAlreadyExists:
            # Another worker made it in between.
            pass
        return
    if existing.type != POOL_TYPE:
        raise RegisterError(f"work pool {pool} is of type {existing.type!r}, not {POOL_TYPE!r}")


def _matches(existing: DeploymentResponse, desired: RunnerDeployment) -> bool:
    """True when the server already holds `desired`, so it need not be written.

    Every update of a deployment deletes its future scheduled runs, even an update
    that changes nothing, so a register that rewrote each deployment would not be a
    no-op the second time. The flow's version is a hash of its file, so a change to
    a flow's code or signature is a difference here.
    """
    pull_steps = desired.storage.to_pull_step() if desired.storage else None
    if pull_steps is not None and not isinstance(pull_steps, list):
        pull_steps = [pull_steps]
    return (
        existing.work_pool_name == desired.work_pool_name
        and existing.entrypoint == desired.entrypoint
        and existing.pull_steps == pull_steps
        and existing.version == desired.version
        and existing.description == desired.description
        and existing.job_variables == desired.job_variables
        and existing.parameters == desired.parameters
        and existing.tags == desired.tags
        and existing.paused == desired.paused
        and existing.enforce_parameter_schema == desired.enforce_parameter_schema
        and _schedules(existing.schedules) == _schedules(desired.schedules or [])
    )


_AnySchedule = DeploymentSchedule | DeploymentScheduleCreate | DeploymentScheduleUpdate


def _schedules(schedules: Sequence[_AnySchedule]) -> list[tuple[object, ...]]:
    return [
        (s.slug, s.active, s.schedule and s.schedule.model_dump(), s.parameters) for s in schedules
    ]


async def _existing(
    client: PrefectClient, rows: Sequence[Deployment]
) -> dict[str, DeploymentResponse | None]:
    """What the server holds under each row's name. Refuse a name another pool holds.

    Read for every row before any is written, so a clash on the last row leaves the
    first unwritten too.
    """
    found: dict[str, DeploymentResponse | None] = {}
    clashes: list[str] = []
    for row in rows:
        try:
            existing = await client.read_deployment_by_name(row.name)
        except ObjectNotFound:
            existing = None
        if existing is not None and existing.work_pool_name != row.pool:
            pool = existing.work_pool_name or "no pool"
            clashes.append(f"{row.name} ({existing.id}) is on {pool}")
        found[row.name] = existing
    if clashes:
        raise RegisterError(
            "deployment names already held on another pool, so nothing was "
            f"registered: {'; '.join(clashes)}"
        )
    return found


async def _upsert(
    row: Deployment,
    existing: DeploymentResponse | None,
    *,
    source: Path,
    active: bool,
) -> tuple[UUID, bool]:
    """The deployment's id, and whether it had to be written."""
    loaded = await Flow.afrom_source(source=str(source), entrypoint=row.entrypoint)
    if loaded.name != row.flow:
        raise RegisterError(f"{row.entrypoint} is the flow {loaded.name!r}, not {row.flow!r}")
    desired = await loaded.ato_deployment(
        name=row.deployment,
        work_pool_name=row.pool,
        schedules=[Cron(row.cron, timezone=TIMEZONE, active=active, slug=SCHEDULE_SLUG)],
        # The table wins over a deployment paused in the UI, as over a schedule.
        paused=False,
        # The version stays the hash of the flow's file. Otherwise Prefect swaps in
        # a git SHA when it finds one (in CI, always), and the next register sees a
        # difference that is not one. Private, but Prefect is pinned to one version.
        version_type=VersionType.SIMPLE,
        # Every flow run, because the server's heartbeat automation matches every
        # flow run. Pinned rather than left to Prefect's default, which a later
        # Prefect or a worker's environment could raise past its 540 s timeout.
        job_variables={
            "env": {"PREFECT_FLOWS_HEARTBEAT_FREQUENCY": str(HEARTBEAT_FREQUENCY_SECONDS)}
        },
    )
    if existing is not None and _matches(existing, desired):
        return existing.id, False
    return await desired.aapply(), True


async def _prune(client: PrefectClient, pool: str, keep: Mapping[str, UUID]) -> tuple[str, ...]:
    kept = set(keep.values())
    on_pool = await client.read_deployments(
        work_pool_filter=WorkPoolFilter(name=WorkPoolFilterName(any_=[pool]))
    )
    deleted: list[str] = []
    for deployment in on_pool:
        if deployment.id in kept:
            continue
        await client.delete_deployment(deployment.id)
        deleted.append(f"{deployment.name} ({deployment.id})")
        logger.info(
            "deleted deployment %s (%s): not in the table",
            deployment.name,
            deployment.id,
        )
    return tuple(deleted)


async def _register(
    pool: str, rows: Sequence[Deployment], *, source: Path, forced_off: bool
) -> Registered:
    async with get_client() as client:
        existing = await _existing(client, rows)
        await ensure_work_pool(client, pool)
        ids: dict[str, UUID] = {}
        written: list[str] = []
        for row in rows:
            active = row.active and not forced_off
            ids[row.name], wrote = await _upsert(
                row, existing[row.name], source=source, active=active
            )
            if wrote:
                written.append(row.name)
            logger.info(
                "%s %s (%s), schedule active: %s",
                "registered" if wrote else "unchanged",
                row.name,
                ids[row.name],
                active,
            )
        deleted = await _prune(client, pool, ids)
    return Registered(deployment_ids=ids, written=tuple(written), deleted=deleted)


def register(
    pool: str,
    *,
    rows: Sequence[Deployment] = DEPLOYMENTS,
    source: Path = SOURCE,
    environ: Mapping[str, str] | None = None,
) -> Registered:
    """Put `pool`'s deployments on the server exactly as `rows` declares them."""
    forced_off = schedules_forced_off(os.environ if environ is None else environ)
    mine = [row for row in rows if row.pool == pool]
    if not mine:
        # Pruning against an empty table would delete the whole pool.
        raise RegisterError(f"the table has no deployment on pool {pool}")
    return asyncio.run(_register(pool, mine, source=source, forced_off=forced_off))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m flows.register")
    parser.add_argument(
        "--pool",
        required=True,
        choices=sorted({row.pool for row in DEPLOYMENTS}),
        help="the work pool whose deployments to register",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    register(args.pool)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
