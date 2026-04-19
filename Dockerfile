FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY praxis ./praxis

RUN pip install .

RUN useradd --create-home --uid 1000 praxis \
    && mkdir -p /var/lib/praxis \
    && chown -R praxis:praxis /var/lib/praxis

USER praxis

ENTRYPOINT ["python", "-m", "praxis.launcher"]
