"""A stub transport for the real Sentry SDK, and the build it is told to report.

The SDK is real and only its transport is fake, so a test using these pins what
Bugsink would actually receive. The fixture that installs it is `transport`,
registered for the whole suite through `pytest_plugins` in `tests/conftest.py`,
because the database's own error text is only reachable from the integration
suite (NEU-2545).
"""

from typing import TYPE_CHECKING, Any

import pytest
import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from tvbf.config import get_settings

if TYPE_CHECKING:
    from sentry_sdk._types import Event  # a TypedDict that exists only for type checkers

SHA = "0123456789abcdef0123456789abcdef01234567"
"""The build the `transport` fixture reports, so a test can assert an event names it."""


class CapturedTransport(Transport):
    """Holds envelopes until `flush()`, as the real transport's background queue
    does — so an event `main()` forgot to flush is an event these tests miss."""

    def __init__(self) -> None:
        super().__init__()
        self.queued: list[Envelope] = []
        self.envelopes: list[Envelope] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        self.queued.append(envelope)

    def flush(self, timeout: float, callback: Any | None = None) -> None:
        self.envelopes += self.queued
        self.queued.clear()

    @property
    def events(self) -> list["Event"]:
        return [e for env in self.envelopes if (e := env.get_event()) is not None]


@pytest.fixture
def transport(monkeypatch):
    """Route the real `sentry_sdk.init` to a transport that keeps what it is sent.

    A test using this pins what Bugsink would actually receive from
    `init_sentry`'s own options.
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
    # Or the next test's event carries this one's log lines and requests.
    sentry_sdk.get_isolation_scope().clear_breadcrumbs()
    sentry_sdk.get_current_scope().clear_breadcrumbs()
    # Not `init()` again: that reads `SENTRY_DSN` back out of the environment.
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)
