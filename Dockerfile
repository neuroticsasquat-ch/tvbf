FROM python:3.13-slim AS base

# UV_PROJECT_ENVIRONMENT: `uv sync` installs into the image's system Python, as
# `uv pip install --system` did, rather than a .venv.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_PYTHON_DOWNLOADS=never

# tini: for the Prefect worker to run under as PID 1 (its start script comes with
# project spec §4.8), so a flow run's child processes are reaped and a stop signal
# reaches the worker (ADR-0016).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install from uv.lock, the set CI tests, not from pyproject.toml's ranges: those
# resolve to whatever is newest at build time, so prod drifted from CI unnoticed
# (sqlalchemy 2.1.5 vs the locked 2.0.52 silently dropped every SQL span).
# --locked fails the build when the lockfile is stale, as it fails CI. --inexact
# keeps what the lockfile doesn't list -- pip and uv itself -- in /usr/local.
COPY pyproject.toml uv.lock ./

# Prefect's own environment (ADR-0016; project spec §4.2): Prefect pins a FastAPI older
# than the app's, so it cannot share the system Python. `uv` builds a virtualenv at
# /opt/prefect-venv on the image's own Python 3.13, which is not on PATH: `python` stays
# the app's, and Prefect is always called by its full path, /opt/prefect-venv/bin/prefect.
# Its dev group (pytest) is the dev stage's.
COPY orchestration/pyproject.toml orchestration/uv.lock orchestration/
RUN UV_PROJECT_ENVIRONMENT=/opt/prefect-venv \
    uv sync --locked --no-cache --no-dev --project orchestration

# The dev dependency group is installed by default; prod leaves it out with --no-dev.
FROM base AS dev

RUN uv sync --locked --inexact --no-cache --no-install-project

COPY src/ src/
COPY alembic.ini alembic.ini
COPY migrations/ migrations/

RUN uv sync --locked --inexact --no-cache \
    && UV_PROJECT_ENVIRONMENT=/opt/prefect-venv \
       uv sync --locked --no-cache --project orchestration

COPY orchestration/ orchestration/

EXPOSE 8000

CMD ["uvicorn", "tvbf.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS prod

RUN uv sync --locked --inexact --no-cache --no-dev --no-install-project

COPY src/ src/
COPY alembic.ini alembic.ini
COPY migrations/ migrations/

RUN uv sync --locked --inexact --no-cache --no-dev --no-editable

COPY orchestration/ orchestration/

# Not root (ops: Shared CI workflows, Decision 13; CI's image job checks it). Nothing in
# the image is written at runtime: no volume, no bytecode (PYTHONDONTWRITEBYTECODE), and
# migrations and the scheduled jobs only talk to Postgres. Everything above stays
# root-owned, which the user only needs to read.
RUN useradd --system --create-home --uid 10001 tvbf
USER tvbf

EXPOSE 8000

# opentelemetry-distro defaults the OTLP protocol to gRPC, but we install only
# the HTTP exporter. Pin http/protobuf so the absent grpc exporter is never
# looked up. Endpoint + service.name come from the deploy env (Coolify).
ENV OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# Run migrations on startup, then exec uvicorn (wrapped by opentelemetry-instrument
# to auto-instrument FastAPI/SQLAlchemy/asyncpg/httpx) so signals reach the server.
CMD ["sh", "-c", "alembic upgrade head && exec opentelemetry-instrument uvicorn tvbf.main:app --host 0.0.0.0 --port 8000"]
