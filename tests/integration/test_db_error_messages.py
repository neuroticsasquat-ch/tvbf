"""What a failed statement's error message says (NEU-2544).

An unhandled database error reaches the error tracker as its message, and
SQLAlchemy's default message quotes the statement's bound parameters: an email
address and a password hash, on a failed insert into `app.user`.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tvbf.db import engine


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
