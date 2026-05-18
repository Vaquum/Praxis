FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY praxis ./praxis

RUN pip install .

RUN useradd --create-home --uid 1000 praxis \
    && mkdir -p /var/lib/praxis \
    && chown -R praxis:praxis /var/lib/praxis

USER praxis

# `start-period` is 10m to cover the first-ever boot's synchronous
# Limen HF snapshot download (TD-061). After that, healthz takes
# milliseconds; --interval 30s + --retries 3 means a hang surfaces
# as `unhealthy` within ~90s of the first failed probe.
#
# Port resolution mirrors the launcher (`praxis/launcher.py:2021`
# reads `PORT` first, falls back to `HEALTHZ_PORT`, defaults to
# 8080), so the probe stays in sync with whichever env var the
# operator / platform actually sets.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10m --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-${HEALTHZ_PORT:-8080}}/healthz" || exit 1

ENTRYPOINT ["python", "-m", "praxis.launcher"]
