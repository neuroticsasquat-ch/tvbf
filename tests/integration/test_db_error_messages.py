"""What a failed statement's error message says (NEU-2544, NEU-2545).

An unhandled database error reaches the error tracker as its message, and
SQLAlchemy's default message quotes the statement's bound parameters: an email
address and a password hash, on a failed insert into `app.user`. Postgres's own
text then adds a `DETAIL` line, which on a unique violation names the value.
"""

import json
import re

import pytest
import sentry_sdk
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tvbf.db import engine
from tvbf.telemetry import init_sentry


async def test_a_failed_statement_does_not_quote_what_was_bound_to_it(session):
    """`session` is here for the database it sets up; the engine under test is
    the application's own, because its options are what production runs with."""
    async with engine.connect() as conn:
        with pytest.raises(DBAPIError) as failed:
            await conn.execute(
                text("select 1 from neu_2544_no_such_table where email = :email"),
                {"email": "bound-parameter-canary@example.com"},
            )

    message = str(failed.value)
    # Still says what went wrong, and with which statement.
    assert "neu_2544_no_such_table" in message
    assert "bound-parameter-canary" not in message


async def test_a_unique_violations_event_names_the_constraint_and_not_the_value(
    session, make_user, transport
):
    """The driver's own message carries the `DETAIL` line, and so does every
    exception in the chain that quotes it."""
    init_sentry()
    # Built, not written out: the event quotes this test's source as context.
    canary = "-".join(["unique", "violation", "canary"])
    email = f"{canary}@example.com"
    await make_user(email=email)
    with pytest.raises(IntegrityError) as failed:
        await make_user(email=email)
    await session.rollback()
    # Postgres really did name the value, or its absence below says nothing.
    assert email in str(failed.value)

    sentry_sdk.capture_exception(failed.value)
    sentry_sdk.flush()

    [event] = transport.events
    [top] = [v for v in event["exception"]["values"] if v["type"] == "IntegrityError"]
    # `uq_user_email` as Alembic names it; `create_all` takes Postgres's default,
    # because `app.user.email` declares `unique=True` rather than a named constraint.
    assert re.search(r'unique constraint "(uq_user_email|user_email_key)"', top["value"])
    assert canary not in json.dumps(event, default=str)
