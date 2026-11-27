"""A stub transport for the real Sentry SDK, and the build it is told to report.

The SDK is real and only its transport is fake, so a test using these pins what
Bugsink would actually receive. The fixture that installs it is `transport`, in
`tests/unit/conftest.py`.
"""

from typing import TYPE_CHECKING, Any

from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

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
