"""What an error event is allowed to carry (NEU-2544).

Measured on 2026-11-27 with made-up secrets: a crashed job's event held the
whole `Settings` object, a failed login's held the password, and a failed
password change's held both passwords in its request body. Each test here drives
the real code with the real SDK and reads what the stub transport was handed, so
it pins what Bugsink would receive rather than which options were passed.

No database: `create_app` opens no connection, and nothing here starts the
app's lifespan.
"""

import json
import re
from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from tvbf.app.schemas import PasswordChangeRequest
from tvbf.config import get_settings
from tvbf.jobs.scheduled import scheduled_main
from tvbf.llm.client import OpenAICompatClient
from tvbf.llm.registry import DEEPINFRA
from tvbf.llm.types import Prompt, UnsupportedPromptError
from tvbf.main import create_app
from tvbf.rate_budget import RateLimiter
from tvbf.telemetry import init_sentry

SECRETS = {
    "ADMIN_TOKEN": "admin-token-canary-1111",
    "DEEPINFRA_API_KEY": "deepinfra-canary-2222",
    "VAPID_PRIVATE_KEY": "vapid-canary-3333",
    "TMDB_READ_ACCESS_TOKEN": "tmdb-canary-4444",
    "RESEND_API_KEY": "resend-canary-5555",
    "LINEAR_API_KEY": "linear-canary-6666",
    "TURNSTILE_SECRET_KEY": "turnstile-canary-7777",
    "HEALTHCHECK_CATALOG_URL": "https://kuma.example/api/push/push-token-canary-8888",
    "DATABASE_URL": "postgresql+asyncpg://someone:db-password-canary-9999@db.example:5432/tvbf",
}
"""The secrets `Settings` holds as plain strings, and one of its six push URLs,
each carrying a marker nothing else in the suite uses."""

CANARY = re.compile(r"canary-\d{4}")
"""What every value in `SECRETS` carries. Matched as a marker rather than as the
whole value, so a secret that reaches an event truncated or inside a URL is
still found."""


@pytest.fixture
def secrets(monkeypatch, transport):
    """A deployment whose every secret is a canary.

    After `transport`, which clears the settings cache on its way in and out, so
    the canaries are what `get_settings` reads and nothing later inherits them.
    """
    for name, value in SECRETS.items():
        assert CANARY.search(value), name
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()


def _frames(event: Any) -> Iterator[dict[str, Any]]:
    for value in event["exception"]["values"]:
        yield from (value.get("stacktrace") or {}).get("frames", [])


def _serialised(event: Any) -> str:
    return json.dumps(event, default=str)


def test_a_crashed_jobs_event_carries_none_of_the_deployments_secrets(transport, secrets):
    """`scheduled_main` and the runner it awaits both hold `settings`, and the
    SDK's default sends the local variables of every frame it reports."""

    held: list[str] = []

    async def _crashes(settings):
        held.append(repr(settings))
        raise RuntimeError("the guard query blew up")

    assert (
        scheduled_main(
            runner=_crashes,
            healthcheck_url=lambda s: None,
            name="test job",
            job="test_job",
        )
        == 1
    )

    # Every canary really was in the frame, or its absence below says nothing.
    [settings_as_held] = held
    assert [name for name, value in SECRETS.items() if value not in settings_as_held] == []
    [event] = transport.events
    assert [value["type"] for value in event["exception"]["values"]] == ["RuntimeError"]
    frames = list(_frames(event))
    # The stack is still there; only what the frames held is gone.
    assert {"scheduled_main", "_crashes"} <= {frame["function"] for frame in frames}
    assert [frame["function"] for frame in frames if "vars" in frame] == []
    assert CANARY.findall(_serialised(event)) == []


async def test_a_refused_prompts_event_carries_none_of_the_users_watch_history(transport):
    """The one failure of the weekly pass that leaves it through a user's turn:
    its traceback runs through frames whose locals are that user's payload."""
    init_sentry(job="weekly_recommendations")
    payload = json.dumps({"liked": [["A Canary Among Shows", 2019, 100, 5.0]]})

    async with OpenAICompatClient(
        provider=DEEPINFRA,
        api_key="test-key",
        model="vendor/Some-Model",
        rate_calls=5,
        rate_window=1,
        limiter=RateLimiter(20, 1),
    ) as client:
        with pytest.raises(UnsupportedPromptError) as refused:
            # No "json" in the instruction, which the client refuses before sending.
            await client.complete_json(Prompt(system="Answer tersely.", user=payload))
    sentry_sdk.capture_exception(refused.value)
    sentry_sdk.flush()

    [event] = transport.events
    assert "complete_json" in {frame["function"] for frame in _frames(event)}
    assert "A Canary Among Shows" not in _serialised(event)


async def test_a_failed_requests_event_carries_neither_its_body_nor_its_csrf_token(transport):
    """A request body is credentials as often as not, and the SDK's own scrubber
    hides a key named `password` while leaving `current_password` and
    `new_password` in the clear. The header is this API's own name for a token
    the scrubber knows under two others."""
    app = create_app()
    probe = APIRouter()

    @probe.post("/_fails")
    async def _fails(payload: PasswordChangeRequest):
        raise RuntimeError("the handler blew up")

    app.include_router(probe)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="https://api.test",
    ) as client:
        response = await client.post(
            "/_fails",
            json={
                "current_password": "current-password-canary",
                "new_password": "new-password-canary",
            },
            headers={
                "X-CSRF-Token": "csrf-token-canary",
                "Cookie": "tvbf_session=session-cookie-canary",
            },
        )
    assert response.status_code == 500
    sentry_sdk.flush()

    [event] = transport.events
    # What an event is for is still there.
    assert [value["type"] for value in event["exception"]["values"]] == ["RuntimeError"]
    assert event["request"]["method"] == "POST"
    assert event["request"]["url"] == "https://api.test/_fails"
    # And what it is not for is not. The SDK leaves the key, emptied.
    assert not event["request"].get("data")
    assert [frame["function"] for frame in _frames(event) if "vars" in frame] == []
    sent = _serialised(event)
    for canary in (
        "current-password-canary",
        "new-password-canary",
        "csrf-token-canary",
        "session-cookie-canary",
    ):
        assert canary not in sent
