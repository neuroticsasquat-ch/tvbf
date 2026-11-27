"""Scheduled jobs report their own failure to the error tracker, and nothing else (NEU-1622).

The SDK is real and only its transport is fake (`tests/fixtures/sentry.py`), so
these pin what Bugsink would actually receive: the integrations
`init_sentry(job=…)` chooses, the `pipeline_mode` tag, and the flush before
`main()` returns.
"""

import logging

import sentry_sdk

from tests.fixtures.sentry import SHA
from tvbf.config import get_settings
from tvbf.jobs import raise_test_error
from tvbf.jobs.scheduled import report_down, scheduled_main
from tvbf.telemetry import init_sentry


def test_a_job_crash_is_one_event_tagged_with_the_job_and_the_build(transport):
    assert raise_test_error.main() == 1

    # Already in the transport when `main()` returns: the process exits next.
    [event] = transport.events
    [exc] = event["exception"]["values"]
    assert exc["type"] == "JobTestError"
    assert event["tags"]["pipeline_mode"] == "raise_test_error"
    # The tag every backend's scheduled jobs use (NEU-1634), and only that one.
    assert "job" not in event["tags"]
    assert event["release"] == SHA
    assert event["environment"] == "production"


def test_the_crash_log_line_is_a_breadcrumb_not_a_second_event(transport):
    raise_test_error.main()

    [event] = transport.events
    messages = [b.get("message") for b in event["breadcrumbs"]["values"]]
    assert "raise test error job crashed" in messages


def test_a_job_that_logs_an_error_and_carries_on_reports_nothing(transport):
    log = logging.getLogger("tvbf.jobs.test_job")

    async def _tolerates_one_bad_item(settings):
        try:
            raise ValueError("one show failed upstream")
        except ValueError:
            log.exception("show 42 failed; carrying on")
        log.error("1 of 20 shows failed")
        return True

    assert (
        scheduled_main(
            runner=_tolerates_one_bad_item,
            healthcheck_url=lambda s: None,
            name="test job",
            job="test_job",
        )
        == 0
    )
    assert transport.events == []


def test_without_a_dsn_the_sdk_stays_off(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    get_settings.cache_clear()
    try:
        assert raise_test_error.main() == 1
        assert not sentry_sdk.get_client().is_active()
    finally:
        get_settings.cache_clear()


async def test_a_failed_run_without_an_exception_groups_on_its_stable_text(transport):
    """A run row ending `failed` has no exception left to send. The event's text
    must not carry the run id, or every failed night would open a new issue."""
    init_sentry(job="catalog_update")
    await report_down(
        None, "catalog delta run 42 ended failed", event="catalog delta run ended failed"
    )
    sentry_sdk.flush()

    [event] = transport.events
    assert event["message"] == "catalog delta run ended failed"
    assert event["level"] == "error"
    assert event["extra"]["detail"] == "catalog delta run 42 ended failed"
    assert event["tags"]["pipeline_mode"] == "catalog_update"
