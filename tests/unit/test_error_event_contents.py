"""What an error event is allowed to carry (NEU-2544, NEU-2545).

Measured on 2026-11-27 with made-up secrets: a crashed job's event held the
whole `Settings` object, a failed login's held the password, and a failed
password change's held both passwords in its request body. NEU-2545 took the
rest: outbound URLs in breadcrumbs, the query string, `sys.argv` and sampled
transactions. Each test here drives the real code with the real SDK and reads
what the stub transport was handed, so it pins what Bugsink would receive
rather than which options were passed.

No database: `create_app` opens no connection, and nothing here starts the
app's lifespan.
"""

import json
import logging
import re
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import httpx
import pytest
import respx
import sentry_sdk
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from py_vapid.utils import b64urlencode

from tvbf.app.schemas import PasswordChangeRequest
from tvbf.config import get_settings
from tvbf.jobs.scheduled import scheduled_main
from tvbf.llm.client import OpenAICompatClient
from tvbf.llm.registry import DEEPINFRA
from tvbf.llm.types import Prompt, UnsupportedPromptError
from tvbf.main import create_app
from tvbf.push.keys import generate
from tvbf.push.sender import Sent, SubscriptionKeys
from tvbf.push.sender import send as push_send
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


def _fresh_breadcrumbs() -> None:
    """`transport` clears breadcrumbs on its way out, but in its own context: an
    async test runs in the event loop's, which keeps an earlier async test's.
    The SDK puts an outbound request's on the current scope, a log line's on the
    isolation scope."""
    sentry_sdk.get_current_scope().clear_breadcrumbs()
    sentry_sdk.get_isolation_scope().clear_breadcrumbs()


def _http_breadcrumbs(event: Any) -> list[dict[str, Any]]:
    return [b for b in event["breadcrumbs"]["values"] if b.get("category") == "httplib"]


@respx.mock
async def test_an_outbound_requests_breadcrumb_names_its_host_and_not_its_path(transport, caplog):
    """A browser's push endpoint and a Kuma push URL are capabilities, path and
    all. `httpx` also logs the request, whole URL included, at INFO."""
    init_sentry()
    _fresh_breadcrumbs()
    url = "https://push.example/send/endpoint-canary?k=v"
    respx.post(url).mock(return_value=httpx.Response(201))

    with caplog.at_level("INFO", logger="httpx"):
        async with httpx.AsyncClient() as client:
            await client.post(url)
    # The log line really was emitted, or its absence below says nothing.
    assert any("endpoint-canary" in r.getMessage() for r in caplog.records)
    sentry_sdk.capture_message("after an outbound request")
    sentry_sdk.flush()

    [event] = transport.events
    [crumb] = _http_breadcrumbs(event)
    assert crumb["data"] == {
        "http.method": "POST",
        "http.response.status_code": 201,
        "url": "https://push.example",
    }
    assert "endpoint-canary" not in _serialised(event)


class _PushService(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(201)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def push_service() -> Iterator[str]:
    """A push service on loopback: `pywebpush` posts over `requests`, which the
    SDK instruments in the standard library, below anything `respx` can mock."""
    server = HTTPServer(("127.0.0.1", 0), _PushService)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


async def test_a_push_sends_breadcrumb_names_its_host_and_not_the_endpoint(
    transport, push_service, monkeypatch
):
    init_sentry()
    _fresh_breadcrumbs()
    keys = generate("mailto:ops@example.com")
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_private_key", keys["VAPID_PRIVATE_KEY"])
    monkeypatch.setattr(settings, "vapid_public_key", keys["VAPID_PUBLIC_KEY"])
    monkeypatch.setattr(settings, "vapid_subject", keys["VAPID_SUBJECT"])
    browser_key = ec.generate_private_key(ec.SECP256R1())
    subscription = SubscriptionKeys(
        endpoint=f"{push_service}/send/endpoint-canary?k=v",
        p256dh=b64urlencode(
            browser_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        ),
        auth=b64urlencode(b"0" * 16),
    )

    assert await push_send(subscription, {"kind": "test"}) == Sent(status=201)
    sentry_sdk.capture_message("after a push")
    sentry_sdk.flush()

    [event] = transport.events
    [crumb] = _http_breadcrumbs(event)
    assert crumb["data"]["url"] == push_service
    assert crumb["data"]["http.response.status_code"] == 201
    assert "endpoint-canary" not in _serialised(event)


async def test_a_failed_requests_event_names_the_route_and_not_its_query_string(transport):
    """What someone searched for is in the query string, which the SDK sends
    whatever `send_default_pii` says. And no transaction: tracing is off."""
    app = create_app()
    probe = APIRouter()

    @probe.get("/_fails")
    async def _fails():
        raise RuntimeError("the handler blew up")

    app.include_router(probe)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="https://api.test",
    ) as client:
        response = await client.get("/_fails", params={"search": "query-canary"})
    assert response.status_code == 500
    # What uvicorn logs for it in production, which `ASGITransport` skips.
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "203.0.113.7:5000",
        "GET",
        "/_fails?search=query-canary",
        "1.1",
        500,
    )
    sentry_sdk.capture_message("after the access log line")
    sentry_sdk.flush()

    event, _ = transport.events
    assert event["request"]["method"] == "GET"
    assert event["request"]["url"] == "https://api.test/_fails"
    for sent in transport.events:
        assert "query-canary" not in _serialised(sent)
    assert "transaction" not in {item.type for env in transport.envelopes for item in env.items}


def test_a_jobs_event_does_not_carry_its_argv(transport, monkeypatch):
    # Built, not written out: the event quotes this test's source as context.
    canary = "-".join(["argv", "canary"])
    monkeypatch.setattr("sys.argv", ["weekly_recommendations", "--user", canary])

    async def _crashes(settings):
        raise RuntimeError("the guard query blew up")

    assert (
        scheduled_main(
            runner=_crashes, healthcheck_url=lambda s: None, name="test job", job="test_job"
        )
        == 1
    )

    [event] = transport.events
    assert "sys.argv" not in event.get("extra", {})
    assert canary not in _serialised(event)
