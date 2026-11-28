"""Run a job's command and map its exit to the flow run's state (project spec §4.3).

Ported from ss.fm's `orchestration/flows/command.py` (NEU-2530), with tvbf's exit codes
and tvbf's wrapper. A job reports through its exit code and its own deadman ping
(`tvbf/jobs/scheduled.py`). Prefect records the first and leaves the second alone,
except where the job cannot ping: killed by the flow's timeout, or dead by a signal, or
stopped with the flow's own process. Then the flow pings the job's deadman down itself.

The flow never imports `tvbf`: it meets the job at an argument list and an exit code
(spec §4.1). The command's stdout and stderr are inherited, so they reach the
container's log and SigNoz, never Prefect's database: the weekly pass logs per user.
"""

import contextlib
import logging
import os
import signal
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence

import httpx
from prefect.client.schemas.objects import State
from prefect.exceptions import MissingContextError
from prefect.logging import get_run_logger
from prefect.states import Completed, Failed

# The command Coolify runs today, wrapper included (spec §3.1). The wrapper is what
# gives a run its `job <name>` root span in SigNoz (NEU-1625), so it is not optional.
WRAPPER = "/usr/local/bin/opentelemetry-instrument"
# The app's interpreter: the image's system Python, never /opt/prefect-venv's.
PYTHON = "/usr/local/bin/python"
WORKING_DIRECTORY = "/app"
# How long a command has to stop after SIGTERM before it is sent SIGKILL.
TERM_GRACE_SECONDS = 30.0
# The same, when the flow's own process is being stopped. Shorter, because the worker
# SIGKILLs the flow itself 30 s after its SIGTERM, and the command must be killed
# before then or it is orphaned.
STOP_GRACE_SECONDS = 10.0
# The deadman protocol of tvbf/jobs/scheduled.py (spec §3.2).
MAX_PING_MESSAGE = 250
PING_TIMEOUT_SECONDS = 10

# A job's `main()` returns 0 or 1. A job that finds a run of its kind in flight exits 0
# and pings nothing, on purpose, so there is no "refused" code to map (unlike ss.fm).
EXIT_OK = 0

Pinger = Callable[[str, str], None]


def ping_down(url: str, message: str) -> None:
    """Ping a deadman down. An empty URL is a no-op; a failed ping is swallowed.

    The parameters replace any query string on the URL, as the job's own ping does.
    """
    if not url:
        return
    params = {"status": "down", "msg": message[:MAX_PING_MESSAGE]}
    # The missed ping is itself what the monitor alerts on, so nothing here may raise
    # into the flow. InvalidURL is not an HTTPError.
    with contextlib.suppress(httpx.HTTPError, httpx.InvalidURL):
        httpx.get(httpx.URL(url).copy_with(params=params), timeout=PING_TIMEOUT_SECONDS)


def run_logger() -> logging.Logger | logging.LoggerAdapter[logging.Logger]:
    """The flow run's logger, or a plain one outside a run (a direct call in a test)."""
    try:
        return get_run_logger()
    except MissingContextError:
        return logging.getLogger(__name__)


def state_for_exit(code: int) -> State:
    """The flow run's state for a command that exited by itself with `code`.

    1 is the job's own failure, and the job pinged down. Any other non-zero code (the
    weekly pass's usage error is 2) is a failure nobody pinged for.
    """
    if code == EXIT_OK:
        return Completed()
    return Failed(message=f"the command exited {code}")


def _stop_group(proc: subprocess.Popen[bytes], grace_seconds: float) -> None:
    """SIGTERM the command's process group, then SIGKILL it after the grace.

    The SIGKILL goes to the group whether or not the command itself has exited, so a
    child that ignored SIGTERM goes too; and it goes even if the wait is cut short by
    the flow being stopped. The group's id is not reused while any member lives.
    """
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        pass
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def _ping(pinger: Pinger, url: str, message: str) -> None:
    """Ping, and never let the ping change the run's state."""
    with contextlib.suppress(Exception):
        pinger(url, message)


def run_command(
    argv: Sequence[str],
    *,
    job: str,
    timeout_seconds: float,
    deadman_env: str,
    grace_seconds: float = TERM_GRACE_SECONDS,
    stop_grace_seconds: float = STOP_GRACE_SECONDS,
    pinger: Pinger = ping_down,
    environ: Mapping[str, str] = os.environ,
) -> State:
    """Run `argv` to its end and return the state its exit maps to.

    `argv` is a list built in code, beginning with the wrapper and the app's
    interpreter; nothing is ever joined into a shell string. The command runs in a
    session of its own, so the flow can stop it and everything it started as one
    process group. `deadman_env` names the variable holding the job's deadman URL.
    """
    if list(argv[:2]) != [WRAPPER, PYTHON]:
        raise ValueError(f"a flow runs only {WRAPPER} {PYTHON}, not {list(argv[:2])}")
    logger = run_logger()
    url = environ.get(deadman_env, "")
    logger.info("Running %s", list(argv))
    started = time.monotonic()
    proc = subprocess.Popen(
        list(argv), cwd=WORKING_DIRECTORY, env=dict(environ), start_new_session=True
    )
    try:
        code = proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        code = None
    except BaseException:
        # The flow's own process was told to stop (Prefect raises its SIGTERM as an
        # exception). The worker stops only the flow's process group, not the
        # command's session, so the command is stopped here before the flow exits.
        # The ping goes first: the stop may not finish before the worker's SIGKILL.
        # The job's run row goes stale and the API's startup sweep cancels it (§3.2).
        message = f"{job}: stopped with the flow's process"
        _ping(pinger, url, message)
        logger.warning("%s after %s s", message, round(time.monotonic() - started))
        _stop_group(proc, stop_grace_seconds)
        raise
    if code is None:
        _stop_group(proc, grace_seconds)
        message = f"{job}: killed by the flow's timeout after {timeout_seconds:g} s"
        logger.error(message)
        _ping(pinger, url, message)
        return Failed(name="Timed out", message=message)
    elapsed = round(time.monotonic() - started)
    logger.info("%s exited %s after %s s", job, code, elapsed)
    if code < 0:
        message = f"{job}: died by signal {-code}"
        logger.error(message)
        _ping(pinger, url, message)
        return Failed(name="Killed", message=message)
    return state_for_exit(code)
