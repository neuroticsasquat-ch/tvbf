"""The wait (project spec §4.6), against Prefect's in-process test server."""

import functools
import logging
import uuid
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from prefect import Flow, get_client
from prefect.client.schemas.objects import FlowRun, State, StateType
from prefect.states import Completed, Crashed, Failed, Pending, Running, Scheduled

from flows import jobs, wait
from flows.deployments import BY_FLOW
from flows.wait import MAX_WAIT_SECONDS, POLL_SECONDS, flows_in_flight, wait_for_upstream

DELTA = "tvbf-catalog-delta"
RECONCILE = BY_FLOW["tvbf-airdate-reconcile"]

MakeRun = Callable[[State], FlowRun]


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs: object) -> State:
        self.calls.append(argv)
        return State(type=StateType.COMPLETED)


class FakeClock:
    """A monotonic clock that only moves when the wait sleeps."""

    def __init__(self, on_sleep: Callable[[], None] | None = None) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self.on_sleep = on_sleep

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        if self.on_sleep is not None:
            self.on_sleep()


class RecordingReader:
    """Answers each read with the next of `outcomes`, then with nothing in flight."""

    def __init__(self, *outcomes: set[str] | Exception) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.outcomes = list(outcomes)

    def __call__(self, flow_names: Iterable[str]) -> set[str]:
        self.calls.append(tuple(flow_names))
        outcome = self.outcomes.pop(0) if self.outcomes else set()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> FakeRunner:
    fake = FakeRunner()
    monkeypatch.setattr(jobs, "run_command", fake)
    return fake


@pytest.fixture
def upstream_run() -> Iterator[MakeRun]:
    """Make a run of the catalog delta in a given state; delete it after the test.

    The server lives for the whole session, so a run left in flight would hold every
    later test's reconcile.
    """
    made: list[uuid.UUID] = []

    def make(state: State) -> FlowRun:
        with get_client(sync_client=True) as client:
            flow_run = client.create_flow_run(jobs.tvbf_catalog_delta, state=state)
        made.append(flow_run.id)
        return flow_run

    yield make
    with get_client(sync_client=True) as client:
        for flow_run_id in made:
            client.delete_flow_run(flow_run_id)


def _set_state(flow_run: FlowRun, state: State) -> None:
    with get_client(sync_client=True) as client:
        client.set_flow_run_state(flow_run.id, state, force=True)


def _waiting_with(monkeypatch: pytest.MonkeyPatch, **kwargs: object) -> Callable[..., None]:
    patched = functools.partial(wait.wait_for_upstream, **kwargs)
    monkeypatch.setattr(jobs, "wait_for_upstream", patched)
    return patched


def _reconcile_flow() -> Flow[[], State]:
    return jobs.tvbf_airdate_reconcile


@pytest.mark.parametrize(
    "end_state",
    [Completed, Failed, Crashed],
    ids=["completed", "failed", "crashed"],
)
def test_a_flow_holds_its_command_until_its_upstream_run_ends(
    end_state: Callable[[], State],
    runner: FakeRunner,
    upstream_run: MakeRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delta = upstream_run(Running())
    commands_started_while_running: list[int] = []

    def upstream_ends_on_the_third_poll() -> None:
        commands_started_while_running.append(len(runner.calls))
        if len(commands_started_while_running) == 3:
            _set_state(delta, end_state())

    clock = FakeClock(on_sleep=upstream_ends_on_the_third_poll)
    _waiting_with(monkeypatch, sleep=clock.sleep, clock=clock)

    state = _reconcile_flow()(return_state=True)

    assert state.is_completed()
    # It slept three polls with the upstream still running and no command started,
    # and ran its command once the upstream ended, whatever state it ended in.
    assert clock.sleeps == [POLL_SECONDS] * 3
    assert commands_started_while_running == [0, 0, 0]
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    ("minutes_from_now", "polls"),
    [(-10, 1), (120, 0)],
    ids=["scheduled-10m-ago-is-waited-for", "scheduled-in-2h-is-not"],
)
def test_a_flow_waits_for_a_late_upstream_run_but_not_a_future_one(
    minutes_from_now: int,
    polls: int,
    runner: FakeRunner,
    upstream_run: MakeRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduled = datetime.now(UTC) + timedelta(minutes=minutes_from_now)
    delta = upstream_run(Scheduled(scheduled_time=scheduled))
    # A worker picks the late run up and it completes while the flow sleeps.
    clock = FakeClock(on_sleep=lambda: _set_state(delta, Completed()))
    _waiting_with(monkeypatch, sleep=clock.sleep, clock=clock)

    state = _reconcile_flow()(return_state=True)

    assert state.is_completed()
    assert clock.sleeps == [POLL_SECONDS] * polls
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    ("state", "in_flight"),
    [
        (lambda: Running(), True),
        (lambda: Pending(), True),
        # A late run not yet picked up.
        (lambda: Scheduled(scheduled_time=datetime.now(UTC) - timedelta(minutes=10)), True),
        # Later today: not in flight.
        (lambda: Scheduled(scheduled_time=datetime.now(UTC) + timedelta(hours=2)), False),
        # Past the tolerance: a worker would record it Missed and run nothing.
        (lambda: Scheduled(scheduled_time=datetime.now(UTC) - timedelta(minutes=40)), False),
        (lambda: Completed(), False),
    ],
    ids=["running", "pending", "late-10m", "scheduled-in-2h", "late-40m", "completed"],
)
def test_which_upstream_runs_are_in_flight(
    state: Callable[[], State], in_flight: bool, upstream_run: MakeRun
) -> None:
    upstream_run(state())

    assert flows_in_flight([DELTA]) == ({DELTA} if in_flight else set())


def test_at_the_cap_the_command_runs_and_a_warning_names_the_upstream(
    runner: FakeRunner,
    upstream_run: MakeRun,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    upstream_run(Running())
    clock = FakeClock()
    _waiting_with(monkeypatch, sleep=clock.sleep, clock=clock)

    with caplog.at_level(logging.WARNING):
        state = jobs.run_job(RECONCILE)

    assert clock.now == MAX_WAIT_SECONDS == 45 * 60
    assert state.is_completed()
    assert len(runner.calls) == 1
    assert any(
        "still in flight" in record.getMessage() and DELTA in record.getMessage()
        for record in caplog.records
    )


def test_the_wait_logs_how_long_it_waited_and_for_which_flow(
    upstream_run: MakeRun, caplog: pytest.LogCaptureFixture
) -> None:
    delta = upstream_run(Running())
    clock = FakeClock(on_sleep=lambda: _set_state(delta, Completed()))

    with caplog.at_level(logging.INFO):
        wait_for_upstream(RECONCILE, sleep=clock.sleep, clock=clock)

    assert f"tvbf-airdate-reconcile: waited 30 s for {DELTA}" in caplog.messages


def test_a_row_that_runs_after_nothing_makes_no_api_read(
    runner: FakeRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    read = RecordingReader()
    _waiting_with(monkeypatch, read=read)

    state = jobs.tvbf_trending_snapshot(return_state=True)

    assert state.is_completed()
    assert read.calls == []
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    ("outcomes", "polls"),
    [
        ((RuntimeError("the server is down"),), 0),
        (({DELTA}, RuntimeError("the server went down mid-wait")), 1),
    ],
    ids=["first-read", "a-later-read"],
)
def test_when_the_api_read_raises_the_command_still_runs_and_it_is_logged(
    outcomes: tuple[set[str] | Exception, ...],
    polls: int,
    runner: FakeRunner,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    read = RecordingReader(*outcomes)
    clock = FakeClock()
    _waiting_with(monkeypatch, read=read, sleep=clock.sleep, clock=clock)

    with caplog.at_level(logging.WARNING):
        state = jobs.run_job(RECONCILE)

    assert state.is_completed()
    assert read.calls == [(DELTA,)] * len(outcomes)
    assert clock.sleeps == [POLL_SECONDS] * polls
    assert len(runner.calls) == 1
    assert any(
        "could not read the runs of" in record.getMessage() and record.exc_info
        for record in caplog.records
    )


def test_a_scheduled_run_31_minutes_late_is_missed_before_any_wait(
    runner: FakeRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    late = FlowRun.model_validate(
        {
            "flow_id": uuid.uuid4(),
            "auto_scheduled": True,
            "expected_start_time": datetime.now(UTC) - timedelta(minutes=31),
        }
    )
    monkeypatch.setattr(jobs, "_current_flow_run", lambda: late)
    read = RecordingReader()
    _waiting_with(monkeypatch, read=read)

    state = _reconcile_flow()(return_state=True)

    assert (state.type, state.name) == (StateType.CANCELLED, "Missed")
    assert read.calls == []
    assert runner.calls == []
