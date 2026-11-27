"""Fixtures the unit suite shares."""

import pytest
import sentry_sdk

from tests.fixtures.sentry import SHA, CapturedTransport
from tvbf.config import get_settings


@pytest.fixture
def transport(monkeypatch):
    """Route the real `sentry_sdk.init` to a transport that keeps what it is sent.

    A test using this pins what Bugsink would actually receive from
    `init_sentry`'s own options (`tests/fixtures/sentry.py`).
    """
    captured = CapturedTransport()
    real_init = sentry_sdk.init
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: real_init(transport=captured, **kw))
    monkeypatch.setenv("SENTRY_DSN", "https://key@bugsink.example/1")
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES",
        f"deployment.environment=production,service.version={SHA}",
    )
    get_settings.cache_clear()
    yield captured
    get_settings.cache_clear()
    sentry_sdk.get_isolation_scope().remove_tag("pipeline_mode")
    # Or the next test's event carries this one's log lines.
    sentry_sdk.get_isolation_scope().clear_breadcrumbs()
    # Not `init()` again: that reads `SENTRY_DSN` back out of the environment.
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)
