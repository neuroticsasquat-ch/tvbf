"""run_command: a job's exit becomes the flow run's state (project spec §4.3).

The stand-in commands are this test run's interpreter running `-c`, behind `env` as a
stand-in wrapper: `env` execs its argument, as `opentelemetry-instrument` does, so the
command's pid, exit code and signals are the interpreter's. CI runs these tests with no
`/app` and no app interpreter, so the module's wrapper, interpreter and working
directory are pointed at this test run's own for every test here.
"""

import os
import shutil
import signal
import sys
import threading
import time
import uuid
from pathlib import Path

import httpx
import pytest
from prefect import flow
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import LogFilter, LogFilterFlowRunId
from prefect.client.schemas.objects import State, StateType
from prefect.logging.handlers import APILogWorker

from flows import command
from flows.command import ping_down, run_command

DEADMAN = "TEST_DEADMAN_PING_URL"
URL = "https://kuma.example/api/push/token"
ENVIRON = {**os.environ, DEADMAN: URL}
# Read before the autouse fixture patches them: these are what ships.
SHIPPED = (command.WRAPPER, command.PYTHON)


class FakePinger:
    def __init__(self) -> None:
        self.pings: list[tuple[str, str]] = []

    def __call__(self, url: str, message: str) -> None:
        self.pings.append((url, message))


@pytest.fixture(autouse=True)
def stand_in_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env = shutil.which("env")
    assert env is not None
    monkeypatch.setattr(command, "WRAPPER", env)
    monkeypatch.setattr(command, "PYTHON", sys.executable)
    monkeypatch.setattr(command, "WORKING_DIRECTORY", str(tmp_path))


def _run(
    code: str,
    pinger: command.Pinger,
    *,
    job: str = "catalog_update",
    timeout_seconds: float = 30,
    grace_seconds: float = command.TERM_GRACE_SECONDS,
    stop_grace_seconds: float = command.STOP_GRACE_SECONDS,
    environ: dict[str, str] = ENVIRON,
) -> State:
    return run_command(
        [command.WRAPPER, command.PYTHON, "-c", code],
        job=job,
        timeout_seconds=timeout_seconds,
        deadman_env=DEADMAN,
        grace_seconds=grace_seconds,
        stop_grace_seconds=stop_grace_seconds,
        pinger=pinger,
        environ=environ,
    )


@flow
def exits_with(code: int, pinger: FakePinger) -> State:
    """A flow whose command exits with `code`, so the state is the run's own."""
    return _run(f"raise SystemExit({code})", pinger)


@pytest.mark.parametrize(
    ("code", "state_type"),
    [(0, StateType.COMPLETED), (1, StateType.FAILED), (7, StateType.FAILED)],
)
def test_an_exit_code_becomes_the_runs_state(code: int, state_type: StateType) -> None:
    pinger = FakePinger()

    state = exits_with(code, pinger, return_state=True)

    assert state.type == state_type
    # A command that exits by itself pings for itself, or stays silent on purpose:
    # the flow sends nothing.
    assert pinger.pings == []


def test_a_command_past_its_timeout_is_terminated_then_killed(tmp_path: Path) -> None:
    termed = tmp_path / "termed"
    pid_file = tmp_path / "pid"
    # Ignores SIGTERM after noting it, so only SIGKILL ends it.
    code = (
        "import os, signal, time, pathlib\n"
        f"p = pathlib.Path({str(termed)!r})\n"
        "signal.signal(signal.SIGTERM, lambda *a: p.write_text('yes'))\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "while True: time.sleep(0.05)\n"
    )
    pinger = FakePinger()

    state = _run(code, pinger, job="airdate_reconcile", timeout_seconds=1, grace_seconds=0.5)

    assert pid_file.exists(), "the command never started"
    assert termed.read_text() == "yes"
    assert (state.type, state.name) == (StateType.FAILED, "Timed out")
    # The command led its own session, so its process group's id is its pid.
    with pytest.raises(ProcessLookupError):
        os.killpg(int(pid_file.read_text()), 0)
    assert pinger.pings == [
        (URL, "airdate_reconcile: killed by the flow's timeout after 1 s"),
    ]


def _alive(pid: int) -> bool:
    """Whether `pid` is a live process: a reparented zombie is not."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        # A process reaped mid-read raises ESRCH, not ENOENT.
        return False
    return stat.rsplit(")", 1)[1].split()[0] != "Z"


def test_a_child_that_ignores_sigterm_is_killed_with_its_group(tmp_path: Path) -> None:
    child_pid = tmp_path / "child"
    # The command exits on SIGTERM at once; the child it started ignores SIGTERM.
    child = "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n"
    code = (
        "import subprocess, sys, time, pathlib\n"
        f"c = subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        f"pathlib.Path({str(child_pid)!r}).write_text(str(c.pid))\n"
        "time.sleep(60)\n"
    )

    state = _run(code, FakePinger(), timeout_seconds=1, grace_seconds=0.5)

    assert state.name == "Timed out"
    pid = int(child_pid.read_text())
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(pid)


_DIE_BY_SIGKILL = "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"


def test_a_command_that_dies_by_a_signal_pings_down() -> None:
    pinger = FakePinger()

    state = _run(_DIE_BY_SIGKILL, pinger)

    assert (state.type, state.name) == (StateType.FAILED, "Killed")
    assert pinger.pings == [(URL, "catalog_update: died by signal 9")]


class _Stop(Exception):
    """Stands in for Prefect's TerminationSignal, raised on the flow's SIGTERM."""


def test_a_stopped_flow_pings_down_and_stops_its_command(tmp_path: Path) -> None:
    pid_file = tmp_path / "pid"
    code = (
        "import os, time, pathlib\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(60)\n"
    )
    pinger = FakePinger()

    def raise_stop(*_: object) -> None:
        raise _Stop

    previous = signal.signal(signal.SIGTERM, raise_stop)
    timer = threading.Timer(1.0, os.kill, (os.getpid(), signal.SIGTERM))
    timer.start()
    try:
        with pytest.raises(_Stop):
            _run(code, pinger, stop_grace_seconds=1)
    finally:
        timer.cancel()
        signal.signal(signal.SIGTERM, previous)

    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)
    assert pinger.pings == [(URL, "catalog_update: stopped with the flow's process")]


@pytest.mark.parametrize(
    "argv",
    [
        ["/bin/sh", "-c", "true"],
        [command.PYTHON, "-m", "tvbf.jobs.catalog_update"],
        [command.WRAPPER, "/bin/sh", "-c", "true"],
        [],
    ],
)
def test_only_the_wrapped_app_interpreter_is_run(argv: list[str]) -> None:
    with pytest.raises(ValueError, match="runs only"):
        run_command(argv, job="catalog_update", timeout_seconds=1, deadman_env=DEADMAN)


def test_the_real_wrapper_and_interpreter_are_the_ones_coolify_runs() -> None:
    assert SHIPPED == ("/usr/local/bin/opentelemetry-instrument", "/usr/local/bin/python")


def test_an_unset_deadman_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[httpx.URL] = []
    monkeypatch.setattr(command.httpx, "get", lambda url, timeout: sent.append(url))
    environ = {k: v for k, v in os.environ.items() if k != DEADMAN}

    state = _run(_DIE_BY_SIGKILL, ping_down, environ=environ)

    assert state.name == "Killed"
    assert sent == []


def test_a_ping_that_raises_does_not_change_the_state(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(url: httpx.URL, timeout: int) -> None:
        raise httpx.ConnectError("refused")

    def broken(url: str, message: str) -> None:
        raise RuntimeError("a pinger that breaks its own contract")

    monkeypatch.setattr(command.httpx, "get", refuse)

    assert _run(_DIE_BY_SIGKILL, ping_down).name == "Killed"
    assert _run(_DIE_BY_SIGKILL, broken).name == "Killed"


@flow
def prints(reversed_marker: str) -> State:
    # The command prints the marker the right way round, so the line it prints is in
    # no argument list the flow logs.
    return _run(f"print({reversed_marker!r}[::-1], flush=True)", FakePinger())


def test_a_commands_output_stays_out_of_prefects_logs() -> None:
    marker = f"user-{uuid.uuid4()}@example.com"

    state = prints(marker[::-1], return_state=True)
    APILogWorker.instance().drain()

    assert state.is_completed()
    flow_run_id = state.state_details.flow_run_id
    assert flow_run_id is not None
    with get_client(sync_client=True) as client:
        logs = client.read_logs(
            log_filter=LogFilter(flow_run_id=LogFilterFlowRunId(any_=[flow_run_id]))
        )
    messages = [log.message for log in logs]
    # The flow's own lines are there, so the logs were read.
    assert any("exited 0" in message for message in messages), messages
    assert not any(marker in message for message in messages)


def test_a_ping_down_carries_its_message_cut_to_250_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[httpx.URL] = []
    monkeypatch.setattr(command.httpx, "get", lambda url, timeout: sent.append(url))

    ping_down(f"{URL}?status=up&msg=stale", "x" * 300)
    ping_down("", "an unset deadman pings nothing")

    assert len(sent) == 1
    # The parameters replace the URL's own query string, as the job's ping does.
    assert dict(sent[0].params) == {"status": "down", "msg": "x" * 250}


def test_a_ping_that_cannot_reach_kuma_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(url: httpx.URL, timeout: int) -> None:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(command.httpx, "get", refuse)

    ping_down(URL, "down")
    ping_down("not a url at all ://", "down")
