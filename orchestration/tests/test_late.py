"""The missed-run rule (project spec §4.4)."""

import uuid
from datetime import UTC, datetime, timedelta

from prefect.client.schemas.objects import FlowRun, StateType

from flows.late import missed_run_state

NOW = datetime(2026, 12, 3, 9, 0, tzinfo=UTC)
TOLERANCE = 30


def _flow_run(*, minutes_late: float, auto_scheduled: bool) -> FlowRun:
    return FlowRun.model_validate(
        {
            "flow_id": uuid.uuid4(),
            "auto_scheduled": auto_scheduled,
            "expected_start_time": NOW - timedelta(minutes=minutes_late),
        }
    )


def test_a_scheduled_run_31_minutes_late_is_missed() -> None:
    flow_run = _flow_run(minutes_late=31, auto_scheduled=True)

    state = missed_run_state(flow_run, tolerance_minutes=TOLERANCE, now=NOW)

    assert state is not None
    assert (state.type, state.name) == (StateType.CANCELLED, "Missed")


def test_a_scheduled_run_29_minutes_late_is_not_missed() -> None:
    flow_run = _flow_run(minutes_late=29, auto_scheduled=True)

    assert missed_run_state(flow_run, tolerance_minutes=TOLERANCE, now=NOW) is None


def test_a_run_started_by_hand_an_hour_late_is_not_missed() -> None:
    flow_run = _flow_run(minutes_late=60, auto_scheduled=False)

    assert missed_run_state(flow_run, tolerance_minutes=TOLERANCE, now=NOW) is None


def test_a_deployment_with_no_tolerance_is_never_missed() -> None:
    flow_run = _flow_run(minutes_late=5 * 60, auto_scheduled=True)

    assert missed_run_state(flow_run, tolerance_minutes=None, now=NOW) is None


def test_a_run_outside_any_flow_run_is_not_missed() -> None:
    assert missed_run_state(None, tolerance_minutes=TOLERANCE, now=NOW) is None
