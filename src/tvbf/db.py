from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from tvbf.config import get_settings

_settings = get_settings()

# `hide_parameters`: a failed statement's message otherwise quotes everything
# bound to it, and an unhandled database error reaches the error tracker as that
# message — an email address and a password hash, on a failed insert into
# `app.user` (NEU-2544). Logs lose the values too, which is the cost. It does
# not cover what Postgres itself says: a unique violation's DETAIL line names
# the key that collided.
engine = create_async_engine(_settings.database_url, pool_pre_ping=True, hide_parameters=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
