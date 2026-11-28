# tvbf: Prefect Adoption — project spec

**Linear project:** tvbf: Prefect Adoption (P-NEU-116) · initiative TV BingeFriend · team Neuroticsasquatch
**Repo:** `tvbf`. Small edits to the `ops` runbooks ride along as ops PRs, named in the tickets that make them.
**Decisions recorded:** [ADR-0016](../adr/0016-prefect-schedules-the-jobs-from-a-worker-on-the-shared-server.md); vocabulary in `CONTEXT.md` § Scheduled jobs.
**Written:** 2026-11-27, from the `/projectit` grilling session. **Verified against:** `main` @ f559903, and Coolify's database on the prod host the same day.
**Ports:** ss.fm's adoption (`music-discovery-engine`: `docs/specs/ss-fm-prefect-adoption-project-spec.md`, ADR-0051, ADR-0052). Where this spec says "ported", that repository's merged code is the starting point.

Every ticket in the project is implemented from this spec plus its milestone's shared
contracts, unless it is labelled `planit`.

## 1. Purpose

tvbf's six job schedules, and the order they must run in, live in the Coolify UI. The
repository cannot see or enforce them:

- The guide said the recommendations task runs Sundays while Coolify runs it Mondays (NEU-2409).
- For the airdate pass, both push tasks and the weekly pass, the guide says "nothing in the
  repo can enforce that order". The order is held by gaps on a clock.
- No one place shows what ran and when.

The project moves every Coolify scheduled task on tvbf onto Prefect, on the shared server
ops runs (NEU-2534). It then sends the weekly recommendations cohort through DeepInfra's
batch API, which bills 20% below real-time, if a probe shows that a batch honours JSON mode.

On its own, six cron lines would not justify an orchestrator. The case rests on the server
existing anyway for ss.fm (NEU-2412's analysis).

## 2. Scope

**In scope**

- A worker resource for tvbf, registered on the shared server with work pool `tvbf-jobs`.
- One Prefect deployment per scheduled job, registered from a table in code.
- The order between jobs, held in code.
- The cutover of all six jobs, and the deletion of their Coolify tasks.
- The worker's deploy gate and schema check (NEU-2548).
- The weekly cohort through DeepInfra's batch API (NEU-2550), behind a probe.

**Done when**

- Coolify shows no scheduled task on any tvbf resource.
- Every job's Kuma monitor has gone green from a run Prefect started.
- Either a scheduled week's recommendation sets were written from a batch, or the batch
  probe's recorded verdict stopped that story.

**Not in scope**

- A Prefect server for tvbf alone, or any change to the shared server. Ops owns it.
- Any change to a job module, its deadman, its run rows or the advisory lock, other than
  NEU-2548's schema check and the batch story's changes to the weekly pass.
- Prefect retries, notifications or concurrency limits.
- Splitting a job into Prefect tasks.
- Prefect in localdev (§4.11).
- Tightening the timeouts Coolify holds today (§4.5).
- Resource limits on the worker or the API.
- The admin triggers (`POST /admin/catalog-update`, `POST /admin/recommendations`), which
  keep running inside the API process.
- Several users in one prompt; changing what makes a user regenerate; a second model provider.

## 3. Where things stand (verified 2026-11-27)

### 3.1 What Coolify holds

Read from `coolify-db` on the prod host (`ssh hetzner-01`, which is the VM `music-box-dancer`).
The Coolify project `TVBF` holds one application, `tvbf-backend`, and one Postgres resource.
It holds no service. `tvbf-backend` holds six scheduled tasks, all enabled:

| Coolify task | Cron (UTC) | Command | Timeout | Measured over 30 days |
| --- | --- | --- | --- | --- |
| Daily - catalog | `0 9 * * *` | `opentelemetry-instrument python -m tvbf.jobs.catalog_update` | 10800 s | avg 35 min, max 61 min |
| Daily - reconcile | `0 11 * * *` | `opentelemetry-instrument python -m tvbf.jobs.airdate_reconcile` | 10800 s | avg 10.5 min, max 12.5 min |
| Daily - push - airs today | `0 13 * * *` | `opentelemetry-instrument python -m tvbf.jobs.push_airs_today` | 900 s | max 11 s |
| Daily - trending | `15 13 * * *` | `opentelemetry-instrument python -m tvbf.jobs.trending_snapshot` | 36000 s | max 7 s |
| Daily - push - events | `0 17 * * *` | `opentelemetry-instrument python -m tvbf.jobs.push_events` | 300 s | max 12 s |
| Weekly - recommendations | `15 12 * * 1` | `opentelemetry-instrument python -m tvbf.jobs.weekly_recommendations` | 36000 s | max 32 min |

- The six tasks and their schedules match what the repo and the ops runbooks say. There is
  no seventh task, and no task anywhere else whose command names tvbf.
- **Every command is wrapped in `opentelemetry-instrument`** (NEU-1625). The guide shows them bare.
- **The catalog delta's timeout (3 h) is longer than its 2 h gap to the reconcile.** The
  clock does not guarantee the order today. The delta's measured maximum does.
- A scheduled task has an `enabled` flag, so it can be switched off without being deleted.
- The API resource: build pack Docker Compose (`docker-compose.prod.yml`), Auto Deploy on,
  watch path `!frontend/**`, *Connect to Predefined Network* on, no pre- or post-deployment
  command. It migrates in its `CMD` (`alembic upgrade head && exec … uvicorn`).

### 3.2 How a job reports

- Every job's `main()` returns 0 or 1, and the exit code is the result (`jobs/scheduled.py`).
  The weekly pass also parses arguments, so a usage error exits 2.
- A job that finds a run of its own kind in flight, or the weekly pass's advisory lock held,
  **exits 0 and pings nothing**. That is deliberate (`run_scheduled_delta`, `run_pass_if_free`).
- A deadman is an Uptime Kuma push monitor: `GET <url>?status=up&msg=ok&ping=<ms>` on
  success, `GET <url>?status=down&msg=<at most 250 characters>` on failure, no start ping.
  The parameters replace any query string on the URL. An unset URL is a no-op.
- Kuma's interval is the schedule plus grace: 25 h for a daily job, 8 d for the weekly one.
  A daily job's ping can therefore move one hour later before its monitor fires.
- Under the wrapper, each run is one root span, `job <name>`, and its logs reach SigNoz.
- A run row left `running` by a killed process stops counting as live after
  `INGEST_STALE_RUN_MINUTES` (15), and the API's startup sweep marks it `cancelled`.

### 3.3 The image

- `Dockerfile`: stages `base`, `dev`, `prod`, on `python:3.13-slim`. One `uv sync` into the
  system Python (`UV_PROJECT_ENVIRONMENT=/usr/local`). There is no virtual environment.
- `prod` runs as user `tvbf` (uid 10001). The image has no `curl` and no `tini`.
- `pyproject.toml`'s ruff and pyright settings cover `src` and `tests`. `testpaths = ["tests"]`.
- CI is `ci.yml`: a `changes` path filter, then `python`, `js`, `api-types` and `image`,
  gated by `ci`. Dependabot has one `uv` entry at `/`.

### 3.4 The shared server (ops `docs/runbooks/prefect-server.md`)

- Prefect 3.9.5: the tag in ops `prefect/Dockerfile` (`prefecthq/prefect:3.9.5-python3.14`)
  is the version every tenant pins to. A worker never runs a newer Prefect than the server.
- A worker reaches it at `PREFECT_API_URL=http://prefect-server:4200/api` with
  `PREFECT_API_AUTH_STRING` set to the server's credential (vault item `prefect-server`)
  and `PREFECT_API_KEY` unset. The worker's resource must be on the `coolify` network.
- Each app has its own work pools, and a worker registers only its own pools' deployments.
- A flow's name is unique across the server. A later tenant prefixes its pool and flow names.
- One heartbeat automation, the server's: a flow run whose heartbeats stop for 540 s is
  marked `Crashed`. No tenant makes an automation.
- A new tenant adds its row to the runbook's *Tenants* table in the PR that adds its worker.
- The UI is at `https://prefect.tail1afe5a.ts.net`, on the tailnet only.

### 3.5 What ss.fm has built

Merged on `music-discovery-engine` `main`: the orchestration project and its tooling
(NEU-2529), `flows/command.py` and `flows/late.py` (NEU-2530), `flows/deployments.py` and
`flows/register.py` (NEU-2531, made safe on a shared server by NEU-2543), `flows/guard.py`
and `scripts/pipeline-worker.sh` (NEU-2532).

Not built there yet: the worker on the box (NEU-2523), the deploy gate (NEU-2522), the
batch wait (NEU-2535, NEU-2520, NEU-2536), and every DeepInfra batch ticket (NEU-2364,
NEU-2367, NEU-2372). The schema check (NEU-2521) is in progress.

### 3.6 Prefect facts this design leans on (ss.fm spec §2.6)

- Prefect 3.9.5 pins `fastapi<0.151`. tvbf runs 0.164.0, so the two cannot share an environment.
- A process worker runs each flow run as a child process. `--with-healthcheck` serves
  `GET /health` on port 8080.
- Re-registering a deployment is an upsert. Nothing prunes one that is no longer declared.
- A scheduled run that is not picked up turns Late and never expires.
- A worker stopped with SIGTERM kills its flow processes and leaves their runs `Running`.
- A flow's delayed retry sleeps in-process.

## 4. Design

### 4.1 What runs where

| Resource | Image | Process | Auto Deploy |
| --- | --- | --- | --- |
| `tvbf-backend` (the API) | `prod` target | uvicorn | on. No scheduled task once the cutover is done. |
| `tvbf-worker` | the same `prod` target | a Prefect process worker on pool `tvbf-jobs` | off until NEU-2548, then on behind the deploy gate |
| `prefect-server` (shared, ops') | ops `prefect/Dockerfile` | `prefect server start` | off |

The app never imports Prefect and never calls its API. A flow never imports `tvbf` and never
reads the app's tables. They meet at a command's argument list and its exit code. The batch
wait adds one JSON line (§4.14).

### 4.2 The orchestration project and its tooling

Ported from ss.fm's NEU-2529.

```
orchestration/
  pyproject.toml     # requires-python >=3.13; prefect pinned to the exact tag in ops prefect/Dockerfile
  uv.lock
  flows/
    deployments.py   # the table (§4.5). Standard library only.
    command.py       # run a command, map its exit (§4.3)
    late.py          # the missed-run rule (§4.4)
    wait.py          # the wait (§4.6)
    jobs.py          # one flow per job
    guard.py         # the version guard (§4.8)
    register.py      # python -m flows.register --pool tvbf-jobs (§4.7)
  tests/
scripts/tvbf-worker.sh
docker-compose.worker.yml
```

- **The image.** The `base` stage runs a second sync:
  `UV_PROJECT_ENVIRONMENT=/opt/prefect-venv uv sync --locked --no-cache --no-dev --project orchestration`,
  and the `dev` stage syncs it again with its dev group, so pytest stays out of `prod`.
  `uv` builds that environment on the image's own Python 3.13. The app stays in the system
  Python, so `python` is the app's and Prefect is always called by its full path,
  `/opt/prefect-venv/bin/prefect`. The image also installs `tini`. The `dev` and `prod`
  stages copy `orchestration/` and `scripts/tvbf-worker.sh`. The ticket records the size the
  second environment adds.
- **Tasks.** `task test:flows` runs `/opt/prefect-venv/bin/python -m pytest orchestration/tests`
  in the backend container. `task deps:lock:flows` locks `orchestration/`. `task test` does
  not collect `orchestration/tests`.
- **Lint and types.** Ruff's `include` gains `orchestration/**/*.py`. Pyright's root run
  does not cover `orchestration/`; `task typecheck` runs a second pass over it with
  `/opt/prefect-venv`.
- **Pre-commit.** The Python hooks' `files` pattern gains
  `^orchestration/(pyproject\.toml|uv\.lock)$`, and a `test-flows` hook runs `task test:flows`
  after the `test` hook. Hooks run in order, so one test process at a time still holds.
- **CI.** `ci.yml` gains an `orchestration` job written in this repository (`uv sync` of the
  project, ruff, pyright, pytest), added to the `changes` filter and to the `ci` gate's
  `needs`. The shared `python.yml@v1` workflow is not changed.
- **Dependabot.** A second `uv` entry for `/orchestration` that ignores `prefect`. A Prefect
  upgrade follows ops' *Upgrade* procedure: the server first, then this lockfile.
- **Flow tests** use Prefect's in-process test server (`prefect_test_harness`).

### 4.3 The command contract

Ported from ss.fm's NEU-2530, with tvbf's exit codes.

A flow runs the command Coolify runs today, wrapper included:

```
/usr/local/bin/opentelemetry-instrument /usr/local/bin/python -m tvbf.jobs.<module>
```

| Exit | Flow run state | Deadman |
| --- | --- | --- |
| 0 | `Completed` | the job pinged up, or stayed silent because a run was already in flight (§3.2) |
| 1 | `Failed` | the job pinged down |
| killed by the flow's timeout | `Failed(name="Timed out")` | **the flow pings down** |
| died by a signal (negative return code) | `Failed(name="Killed")` | **the flow pings down** |
| any other code | `Failed` | none |

`run_command(argv, *, job, timeout_seconds, deadman_env) -> State` in `flows/command.py`:

- Starts `argv` with `subprocess.Popen`, working directory `/app`, the worker's environment,
  in a new session. It refuses any `argv` that does not begin with the two programs above.
- **`argv` is a list built in code. Nothing is ever joined into a shell string.**
- The command's stdout and stderr are inherited, so they reach the container's log and
  SigNoz, not Prefect. The flow logs the argument list, the exit code and the duration.
  **A job's output is never stored in Prefect**: the weekly pass logs per user.
- At `timeout_seconds` it sends SIGTERM to the command's process group, waits 30 seconds,
  then SIGKILL. It then pings the deadman down with
  `<job>: killed by the flow's timeout after N s`.
- A negative return code pings down with `<job>: died by signal N`.
- When the flow's own process is told to stop, it pings down with
  `<job>: stopped with the flow's process`, then stops the command's process group. The
  job's run row goes stale and is swept as today (§3.2).
- The ping is §3.2's protocol, re-implemented in a few lines with `httpx`.

No flow has `retries`. No deployment takes parameters (§4.9).

A test in the app's suite loads `orchestration/flows/deployments.py` by file path and
asserts that every row's module imports and has a `main`. A typo would otherwise be a
`Failed` run at 09:00.

### 4.4 The missed-run rule

Ported unchanged from ss.fm's `flows/late.py`. Called first by every flow except the batch wait.

- It applies only to a run the scheduler created. A run started by hand is never missed.
- If the run starts more than the row's `tolerance_minutes` (30) after its scheduled time,
  the flow logs it and returns `Cancelled(name="Missed")`. It runs no command and pings
  nothing. The job's deadman goes silent and fires, as it does today when a Coolify task
  is missed.

### 4.5 The deployments table

`flows/deployments.py` holds one row per deployment and imports nothing outside the standard
library. Pool `tvbf-jobs`, deployment name `scheduled`, cron in UTC.

| Flow | Module (after `python -m`) | Cron | Timeout | Deadman variable | Runs after |
| --- | --- | --- | --- | --- | --- |
| `tvbf-catalog-delta` | `tvbf.jobs.catalog_update` | `0 9 * * *` | 10800 s | `HEALTHCHECK_CATALOG_URL` | — |
| `tvbf-airdate-reconcile` | `tvbf.jobs.airdate_reconcile` | `0 11 * * *` | 10800 s | `HEALTHCHECK_AIRDATE_URL` | `tvbf-catalog-delta` |
| `tvbf-push-airs-today` | `tvbf.jobs.push_airs_today` | `0 13 * * *` | 900 s | `HEALTHCHECK_PUSH_AIRS_TODAY_URL` | `tvbf-catalog-delta`, `tvbf-airdate-reconcile` |
| `tvbf-trending-snapshot` | `tvbf.jobs.trending_snapshot` | `15 13 * * *` | 36000 s | `HEALTHCHECK_TRENDING_URL` | — |
| `tvbf-push-events` | `tvbf.jobs.push_events` | `0 17 * * *` | 300 s | `HEALTHCHECK_PUSH_EVENTS_URL` | `tvbf-catalog-delta`, `tvbf-airdate-reconcile` |
| `tvbf-weekly-recommendations` | `tvbf.jobs.weekly_recommendations` | `15 12 * * 1` | 36000 s | `HEALTHCHECK_RECOMMENDATIONS_URL` | `tvbf-catalog-delta` |

- Each row also has `active` (false until its cutover ticket) and `tolerance_minutes` (30).
- **Timeouts are Coolify's values as read on 2026-11-27.** They are written into the table
  when it is created. A timeout covers the command, not the wait before it. Trending's
  10 hours for a 7-second job is carried as read; tightening it is not in scope.
- The trending snapshot follows nothing. The guide records that as deliberate (NEU-1055).
- **This table is the one place in the repository a schedule is written.** The guide and
  the README name a job and point here. Ops' Kuma runbook keeps its *Schedule* column,
  which each cutover ticket checks by hand.
- Tests assert: every active row has a timeout; every *Runs after* name is a flow in the
  table; the *Runs after* graph has no cycle; every flow name starts with `tvbf-`.

### 4.6 The wait

New here: ss.fm has no order between chains to hold. `flows/wait.py`, called by a flow
after the missed-run rule and before its command.

- A row with no *Runs after* does not wait.
- Otherwise the flow asks Prefect's API for flow runs of the named flows that are
  `Pending` or `Running`, or `Scheduled` with an expected start in the last 30 minutes (a
  late run not yet picked up). While any exists, it sleeps 30 seconds and asks again.
- **The wait is capped at 45 minutes.** At the cap the flow logs a warning and runs its
  command anyway. A job that runs out of order is a night late on some data, which the
  guide already bounds. A job that does not run at all is worse.
- **Why 45.** A daily monitor has one hour of slack (§3.2). The reconcile's worst run is
  13 minutes, so a 45-minute wait still pings inside that hour. A longer wait would fire
  the waiting job's monitor before its ping arrived.
- If the API read fails, the flow logs it and runs its command.
- The flow logs how long it waited and for which flow.
- **The wait sees only runs Prefect started.** A delta started by `task`, `docker exec` or
  the admin trigger is invisible to it, as it is to the clock today.
- **What each deadman sees.** Every job keeps its own cron and is still fed only by its own
  command. An upstream that fails, is missed or crashes never silences a downstream: the
  downstream waits until the upstream's run has ended, in any state, and then runs.

### 4.7 Registering

Ported from ss.fm's `flows/register.py` as NEU-2543 left it.
`/opt/prefect-venv/bin/python -m flows.register --pool tvbf-jobs`:

- Makes sure the work pool exists (type `process`).
- Upserts every row, with code located by
  `flow.from_source(source="/app/orchestration", entrypoint="flows/jobs.py:<function>")`.
- Sets each schedule's `active` explicitly, so the table wins over a toggle made in the UI.
  With `TVBF_SCHEDULES_ACTIVE=false` in the environment every schedule is registered
  inactive, whatever the table says. That is the quick way back during the cutover.
- Sets `PREFECT_FLOWS_HEARTBEAT_FREQUENCY=180` for every deployment's runs, so a run beats
  three times inside the server automation's 540 s.
- Deletes any deployment on `tvbf-jobs` that the table no longer names.
- Never touches another pool's deployments. If a deployment of a row's name is on another
  pool, it raises `RegisterError` naming it and its pool, and writes nothing.
- Makes and changes no automation.
- Running it twice changes nothing the second time.

### 4.8 The worker

`scripts/tvbf-worker.sh tvbf-jobs`, ported from ss.fm's `scripts/pipeline-worker.sh`:

1. Wait up to 60 seconds for `GET $PREFECT_API_URL/health`, using the image's Python,
   since the image has no `curl`.
2. **Version guard** (`flows.guard`): exit non-zero if the server is older than the
   installed Prefect. A container that exits never becomes healthy, so Coolify keeps the
   old one.
3. `python -m flows.register --pool tvbf-jobs`.
4. `exec /opt/prefect-venv/bin/prefect worker start --pool tvbf-jobs --type process
   --with-healthcheck`. No `--limit`.

`docker-compose.worker.yml`: one service, `tvbf-worker`, built from the `prod` target.

- Command: `tini -g -- /app/scripts/tvbf-worker.sh tvbf-jobs`.
- No ports, no Traefik labels. It runs no migrations.
- Health check: `GET http://localhost:8080/health`, with the image's Python.
- Environment: every variable `docker-compose.prod.yml` passes, with
  `service.name=tvbf-worker` in `OTEL_RESOURCE_ATTRIBUTES`, plus `PREFECT_API_URL` and
  `PREFECT_API_AUTH_STRING`.

In Coolify (project `TVBF`, environment `production`), by hand:

- A Docker Compose application from this repository, compose file `/docker-compose.worker.yml`.
- No domain. *Connect to Predefined Network* on. *Include SOURCE_COMMIT in build* on.
- **Auto Deploy off** until NEU-2548.
- Its environment variables are the API resource's, including those set only in the Coolify
  UI, plus the two Prefect ones. The ticket checks it by comparing variable **names** between
  the two containers, never values.
- **A variable added to the API later must be added to the worker too.** The guide says so.

Things this changes elsewhere:

- **SigNoz** shows job spans under `tvbf-worker`, not `tvbf-backend`. The alerts in ops
  `signoz-alerts.md` filter on HTTP server spans, which jobs never emit, so no alert changes.
  Ops `scheduled-task-telemetry.md` says "one `service.name` per backend, not per job"; each
  cutover ticket's ops PR records the change for its jobs.
- **Ops `prefect-server.md`** gains tvbf's row in *Tenants*, and tvbf in *Upgrade* step 1's
  check, in the PR that adds the worker.

**Until NEU-2548 lands the worker is deployed by hand**, and redeployed after any merge that
carries a migration. Before a redeploy, check that the Prefect UI shows no `tvbf-` run
`Running`.

### 4.9 Running a job by hand

- **A scheduled job, as scheduled:** *Run* on its deployment in the Prefect UI.
- **With arguments** (`--user`, `--dry-run`): `docker exec` into the `tvbf-worker`
  container, or the admin trigger. **No deployment takes parameters**: `--dry-run` prints a
  user's watch history, and Prefect's database must never hold it.
- The `task` targets in localdev are unchanged.
- After a job's cutover, never start it in the API container: a merge can replace that
  container mid-run.

### 4.10 Retries, timeouts and a replaced worker

Ported from ss.fm's ADR-0052 decision 6: **Prefect records and does not react.**

- No flow retries, no Prefect notifications, no Prefect concurrency limits. Only the jobs
  retry, per item, as today. The in-flight guard and the advisory lock stay the only guards
  against two runs of a job. The deadmans stay the only alerts.
- A flow's timeout is its row's (§4.5).
- **A worker container replaced mid-run:** the worker's SIGTERM stops the flow's process.
  The flow pings the job's deadman down and stops the command (§4.3). The run stays
  `Running` in Prefect until the server's heartbeat automation marks it `Crashed`, about
  9 minutes later. Nothing reruns it. The owner reruns it from the Prefect UI.
- The jobs are built to resume: the delta's cursor advances only on success, the reconcile
  and the backfills resume off watermarks, a push claim is re-claimed after an hour, and
  the weekly pass commits per user.
- NEU-2548's deploy gate makes the case rare once Auto Deploy is on. Until then the only
  thing that replaces the worker is a deploy by hand.

### 4.11 Localdev

Not in scope. ss.fm built opt-in dev services (NEU-2533); tvbf does not port them now.

- Flows are tested against Prefect's in-process test server.
- The first end-to-end run is the trending snapshot, started by hand on the box in M1
  while every schedule is inactive (§6). It is one request and replaces one snapshot.
- If a later ticket needs a dev server, ss.fm's ADR-0052 amendment already names the place:
  a shared one in `tbc-localdev-infra`, built from ops' `prefect/` directory.

### 4.12 The deploy gate and the schema check

NEU-2548, as written. Summary:

- `python -m tvbf.jobs.deploy_gate` exits 1, naming what it found, while any `ingest_run`
  row is live or the weekly pass's advisory lock is held. It is the worker resource's
  pre-deployment command.
- Before a job does any work, `scheduled_main` and `weekly_recommendations.run` compare
  `app.alembic_version` with the image's head. On a mismatch the job pings down and exits 1.
- Then Auto Deploy goes on for the worker, with the API's watch path.

It does not block the cutover. A cutover before it redeploys the worker by hand.

### 4.13 The cutover

Four stages, one ticket each. Upstream moves before downstream, because a flow can only wait
for a run Prefect started.

| Stage | Jobs | Do it | First scheduled run |
| --- | --- | --- | --- |
| 1 | trending snapshot | away from 13:15 UTC | the next 13:15 |
| 2 | catalog delta, airdate reconcile | after 11:30 UTC | the next 09:00 and 11:00 |
| 3 | push airs-today, push events | after 17:00 UTC | the next 13:00 and 17:00 |
| 4 | weekly recommendations | Tuesday to Sunday | the next Monday 12:15 |

Stage 2 moves its two jobs in one PR, so the reconcile's first Prefect run has an upstream
to wait on. Between stages, a job still on Coolify is held by the clock, as today.

Each ticket is a PR, then manual steps.

**The PR**

- Sets `active=True` for the stage's rows.
- Rewrites those jobs' notes in `.claude/CLAUDE.md` and `README.md`, and the comments in
  the job modules and `docker-compose.prod.yml` that say Coolify schedules them. The notes
  say where the job runs, what it waits for, and point at the table for its schedule.

**The steps**

1. Check that no run of the stage's jobs is in flight (`task ingest:status`, or
   `pg_locks` for the weekly pass).
2. **Disable** the stage's scheduled tasks in Coolify. Do not delete them. Confirm
   `enabled = f` in `coolify-db`.
3. Merge. Redeploy the worker (by hand until NEU-2548 lands). It registers the rows active.
4. Confirm in the Prefect UI that each job's next run is scheduled at its cron.
5. **The bar: one green run.** After the first scheduled run of each job, record in the
   ticket: the Prefect run, created by the scheduler and `Completed`; the job's own record
   (a `succeeded` `ingest_run` row, or for the weekly pass the week's sets); and the Kuma
   monitor's up heartbeat at that run's end.
6. **Delete** the Coolify tasks. Confirm in `coolify-db` that their rows are gone.
7. An ops PR changes the jobs' rows in `scheduled-task-telemetry.md` and
   `uptime-kuma-monitors.md` to name the Prefect deployment and the worker, and appends a
   log entry.

- **Roll back** by setting `TVBF_SCHEDULES_ACTIVE=false` on the worker and redeploying it,
  or by reverting the PR, then re-enabling the Coolify tasks.
- One run proves the plumbing: the worker's environment, its network, the command and the
  ping. The job's code has not changed, and its deadman covers every later run.
- **Stage 4 also sweeps.** No text in the repository, outside dated history and this spec,
  says a tvbf job runs as a Coolify scheduled task, and `coolify-db` holds no scheduled
  task for any tvbf resource.

### 4.14 The batch

NEU-2550's design, at the depth this project fixes. Tickets 2 to 5 below are labelled
`planit`: their shapes are ported from ss.fm code that does not exist yet (§3.5).

**Rules that are fixed**

- Batch is the scheduled path. Bounded synchronous calls, through NEU-2546's pool, are
  everything else: the admin trigger, `--user`, the one retry for an answer that cannot be
  believed, and any request a batch ended without answering.
- **One user per request.** A batch is a file of one-user requests.
- Port ss.fm's batch work where it exists. Do not build it first here. The adapter waits on
  NEU-2364 and NEU-2367, the rescue on NEU-2372, and the wait on NEU-2520.
- A flow never reads the app's tables. The wait meets the app at a command's argument
  list, its exit code, and one JSON line an `outstanding` command prints (ss.fm spec §4.11).
- The provider's input and output files are deleted once results are written, and the app
  records when. Files are created with a short expiry as a second line.
- The `tvbf/recommendations` monitor goes up when collect finishes, not when submit does.

**1. The probe, which can stop the story.** It needs no Prefect and runs first.

- A script, `scripts/probe_deepinfra_batch.py`, on the precedent of
  `scripts/probe_deepinfra_capacity.py`: the same instruction, request body and scoring.
- **Payloads:** the three accounts NEU-2409 measured (the owner's, the largest library, a
  small library), compiled locally with the job's `--dry-run`. Payloads and raw answers
  are never committed.
- **One batch** to the model `RECOMMENDATION_MODEL` names in production: each payload three
  times, nine one-user requests, with `response_format` JSON mode as the pass sends it. The
  same nine go synchronously the same day.
- **It passes when** every batch answer parses under the pass's output contract
  (`recommendations/prompt.py`), and for each payload the batch answers' median "usable"
  count (titles not already in the payload, NEU-2409's measure) is no more than 3 below the
  synchronous median.
- **It also records:** the time from submit to completion; the output file's line shape;
  the token usage reported; and that `DELETE` on the input and output files succeeds and a
  later `GET` answers 404.
- **The verdict** is written to `.claude/docs/patterns-recommendations.md`, beside the
  other measured DeepInfra findings, and commented on NEU-2550. On a fail the story stops:
  its other five tickets are cancelled by the owner, and NEU-2546 stands alone.
- Expected spend: under $1.

**2. A batch adapter in `src/tvbf/llm/`:** upload a file, create a batch, read its state,
download its output, delete its files. Shapes in `llm/api_payloads.py`.

**3. Submit and collect.** Submit compiles a payload for each user who needs a call, writes
one file, and records the batch and which users it holds. Collect reads the output and runs
each answer through the parse, resolve and write path the pass uses today, then deletes the
provider's files.

**4. The synchronous side,** through the bounded pool: the cases listed under the rules above.

**5. The wait.** A Prefect flow on `tvbf-jobs` that polls a batch and schedules its own next
poll, with a daily look as the safety net. Nothing polls when no batch is open. It is exempt
from the missed-run rule. Ported from ss.fm's batch wait (its spec §4.12).

**6. The deadman and the privacy policy.** The monitor moves to collect. The policy
(`frontend/src/pages/PrivacyPage.tsx`, *Third-Party Data Sources*) says requests rest on the
provider's disk from submit until collect deletes them, at most the 24-hour window.

**Done when** a scheduled week's recommendation sets are written from a batch, the
provider's files for that batch are deleted, and DeepInfra's usage for the week shows the
batch rate.

## 5. Decisions

Settled before the session, and not re-opened: tvbf joins the shared server; pool
`tvbf-jobs` and the `tvbf-` prefix; port ss.fm's build; Prefect in its own environment; a
flow runs the job's existing command; the deadmans, the advisory lock and the run rows stay;
no interim worker running Coolify tasks; the worker is deployed by hand until NEU-2548;
batch is one user per request.

| # | Decision | Rejected |
| --- | --- | --- |
| D1 | **Three milestones:** stand up and start nothing, the cutover, the batch. | One milestone per story. |
| D2 | **Order is held by schedules that wait** (§4.6). Each job keeps its cron and its deadman. The wait is its own ticket in M1. | Chained flows: one upstream crash silences every downstream monitor, and push times would move. Timeouts shorter than the gaps: a slow delta is killed, not waited for. |
| D3 | **The cutover is four stages, upstream first** (§4.13). | One job a ticket; one window for five jobs. |
| D4 | **A Coolify task is disabled at cutover and deleted after one green Prefect-started run.** | Three green runs: three more weeks for the weekly pass. Deleting at cutover, as ss.fm: a rollback is retyping a command and a timeout. |
| D5 | **The batch probe runs first, unblocked.** The other five batch tickets are created blocked by it. | Creating them after the verdict; leaving the probe behind the Prefect work. |
| D6 | **tvbf's batch tickets are blocked by ss.fm's.** | Building the adapter here first. |
| D7 | **Prefect never retries** (§4.10). A crashed run is rerun by hand. | One automatic rerun; retries for the short jobs only. |
| D8 | **Each cutover ticket rewrites its own jobs' notes**, in this repository and in ops. The last one sweeps. | One docs ticket at the end; rewriting everything up front. |

Settled in the spec, approved with the description:

- A flow runs the wrapped command (§4.3). ss.fm runs its commands bare.
- The wait is capped at 45 minutes and sees only runs Prefect started.
- A tvbf job that finds a run in flight exits 0, so there is no `Refused` state.
- No deployment takes parameters.
- The missed-run rule is ported at 30 minutes.
- Timeouts are Coolify's, as read.
- A job's output is not stored in Prefect.
- No Prefect in localdev.

## 6. Milestones and tickets

Created in Linear on 2026-11-27. Unblocked at creation: NEU-2551 and NEU-2558.

### M1 — Prefect stands up and starts nothing

Done when the `tvbf-worker` container is healthy on the box, the shared server shows pool
`tvbf-jobs` with six deployments whose schedules are all inactive, and a trending snapshot
started by hand from the Prefect UI ended `Completed`, wrote a `succeeded` run row and
pinged its monitor up.

| Ticket | Covers | Blocked by |
| --- | --- | --- |
| NEU-2551 Add the orchestration project: Prefect's environment in the image, and its tooling | §4.2 | — |
| NEU-2552 Run a job's command from a flow and map its exit to the run's state | §4.3, §4.4 | NEU-2551 |
| NEU-2553 Register deployments from a table in code | §4.5, §4.7 | NEU-2552 |
| NEU-2554 Make a flow wait for the flows it runs after | §4.6 | NEU-2553 |
| NEU-2555 Stand up the worker resource: the start script, the version guard and the health check | §4.8, §4.9 | NEU-2553 |
| NEU-2548 Let the worker deploy on merge | §4.12 | NEU-2555 |

### M2 — The cutover

NEU-2549 sits here: it is done when Coolify is empty.

| Ticket | Covers | Blocked by |
| --- | --- | --- |
| NEU-2556 Cut over the trending snapshot to Prefect | §4.13 stage 1 | NEU-2555 |
| NEU-2557 Cut over the catalog delta and the airdate reconcile to Prefect | stage 2 | NEU-2556, NEU-2554 |
| NEU-2559 Cut over the two push tasks to Prefect | stage 3 | NEU-2557 |
| NEU-2561 Cut over the weekly recommendations pass to Prefect, and sweep the docs | stage 4 | NEU-2559 |

### M3 — The batch

NEU-2550 and its six children (§4.14). The story stays blocked by NEU-2549.

| Ticket | Blocked by | `planit` |
| --- | --- | --- |
| NEU-2558 Probe a DeepInfra batch for JSON mode and answer quality | — | no |
| NEU-2560 Add a DeepInfra batch adapter | NEU-2558, NEU-2364, NEU-2367 | yes |
| NEU-2562 Submit the weekly cohort as a batch and collect it | NEU-2560 | yes |
| NEU-2563 Run the synchronous side through the bounded pool | NEU-2562, NEU-2372 | yes |
| NEU-2564 Wait on a batch from a Prefect flow | NEU-2562, NEU-2520, NEU-2561 | yes |
| NEU-2565 Move the deadman to collect and say so in the privacy policy | NEU-2562, NEU-2564 | no |

## 7. Risks

- **The worker's environment drifts from the API's.** A variable added to one resource and
  not the other breaks a job at its next run. The guide carries the rule (§4.8); nothing
  enforces it.
- **A stale worker until NEU-2548.** After a merge with a migration, the worker runs old
  code against a newer schema until it is redeployed by hand.
- **The deploy gate rests on Coolify's documented behaviour**, that a failed pre-deployment
  command stops a deploy. NEU-2548 verifies it on the box. If it does not hold, Auto Deploy
  stays off.
- **A push run cut short is not sent again that day** unless someone reruns it. The down
  ping is what says so.
- **The wait cannot see a hand-started run** outside Prefect.
- **The second environment's weight** in every image, the API's included, is unmeasured.
- **Coolify settings have reverted after upgrades** (ops `backend-telemetry-env.md`). A
  disabled task could come back enabled between steps 2 and 6 of a cutover. Step 6 is not
  left for long: one day for a daily job, one week for the weekly pass.
- **M3 moves at ss.fm's pace** after the probe.
- **Whether a batch honours JSON mode** is not stated in DeepInfra's docs. The probe answers it.
