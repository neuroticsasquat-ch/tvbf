# Prefect schedules the jobs, from a worker on the shared server

**Status:** accepted (2026-11-27). Not yet built: nothing changes in production until the
*tvbf: Prefect Adoption* project lands.
**Context:** the project spec (`docs/specs/tvbf-prefect-adoption-project-spec.md`); the
analysis comments on NEU-2412, NEU-2411 and NEU-2410; `music-discovery-engine`'s ADR-0051
and ADR-0052, which this record follows; ops `docs/runbooks/prefect-server.md`.

tvbf's six scheduled jobs run as Coolify scheduled tasks that exec into the API container.
Their schedules, and the order they must run in, exist only in the Coolify UI. The guide
drifted from it once already (it said Sundays; Coolify ran Mondays), and for four jobs it
says nothing in the repository can enforce the order.

Six cron lines would not justify an orchestrator on their own. The shared Prefect server
exists anyway, for ss.fm (NEU-2534), and tvbf becomes its second tenant.

## Decision

1. **Prefect schedules and runs the six jobs.** Each becomes a deployment registered from a
   table in code, and its Coolify task is deleted. The table is the one place in the
   repository a schedule is written.
2. **tvbf is a tenant of the shared server and runs none of its own.** Its worker is a
   resource of its own, `tvbf-worker`, built from the API's image, on work pool `tvbf-jobs`.
   Flow names carry a `tvbf-` prefix, because a flow's name is unique across the server.
3. **Prefect has its own Python environment, and a flow runs the job's existing command.**
   Prefect 3.9.5 pins FastAPI below the version the app runs. The app never imports
   Prefect, and a flow never imports `tvbf` or reads its tables. A flow maps the command's
   exit code to the run's state.
4. **Prefect records and does not react.** No flow retries, no Prefect notifications, no
   Prefect concurrency limits. The Kuma deadmans stay the only alerts. The in-flight guard
   and the weekly pass's advisory lock stay the only guards against two runs. The
   `ingest_run` rows stay the record the app reads.
5. **Order is held by schedules that wait.** Each job keeps its own cron and its own
   deadman. A flow waits while a run of the flows it follows is pending, running or late,
   for at most 45 minutes, and then runs.
6. **The weekly cohort goes through DeepInfra's batch API** if a probe shows a batch
   honours JSON mode, one user per request. The admin trigger and `--user` stay synchronous.

## Where this departs from ss.fm

ss.fm's build is ported, not redesigned. Four things differ, each for a reason that is
tvbf's:

- **The command is wrapped in `opentelemetry-instrument`.** Coolify runs tvbf's jobs that
  way today (NEU-1625), and the wrapper is what gives a run its `job <name>` span.
- **A wait exists.** ss.fm has no order between chains to hold. tvbf has four jobs that
  read what an earlier job wrote.
- **There is no `Refused` state.** A tvbf job that finds a run of its kind in flight exits 0
  and pings nothing, on purpose, so Prefect shows it `Completed`.
- **No deployment takes parameters.** The weekly pass's `--dry-run` prints a user's watch
  history, and Prefect's database must never hold it.

## Considered options

- **A worker resource that runs the six Coolify tasks, before Prefect** (NEU-2547 as
  written). Rejected: it recreates six tasks for the cutover to delete again, to fix a
  fault nobody has observed. No deploy has been seen to end a run.
- **Chained flows**, each job starting the next. Rejected: a downstream job would lose its
  own cron, so one upstream crash would silence two or three monitors a day later, and the
  push times would move with the delta's duration.
- **Timeouts shorter than the gaps between jobs.** Rejected: a slow delta would be killed
  instead of waited for.
- **Building the batch adapter here first.** Rejected: ss.fm plans the same adapter, its
  deletion and its rescue. tvbf's saving is about two cents per user per year, so it can wait.

## Consequences

- **The worker's environment is a second copy of the API's.** A variable added to one
  resource and not the other breaks a job at its next run.
- **Job telemetry moves** from `service.name=tvbf-backend` to `tvbf-worker` in SigNoz.
- **Until the deploy gate lands (NEU-2548), the worker is deployed by hand**, and
  redeployed after any merge that carries a migration.
- **A crashed run is rerun by hand.** The jobs resume by design; a push run cut short is
  the one case where a late rerun is worth less.
- **A wait sees only runs Prefect started.** A job started by `task`, `docker exec` or an
  admin trigger is invisible to it.
- **A Prefect upgrade is ops' procedure:** the server first, then `orchestration/uv.lock`.
