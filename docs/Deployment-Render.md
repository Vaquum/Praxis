# Deployment On Render

This page describes how Praxis is deployed as a long-running service on Render — the Docker image, the `render.yaml` blueprint, the environment contract, how manifests and strategies are supplied to a running container, and the operator workflow for a first verify.

## What Ships In The Image

`Dockerfile` at the repo root builds a container image:

- base: `python:3.12-slim`
- installs `git` (required for the git-sourced `pyproject.toml` deps — Binancial, Limen, Nexus)
- installs the Praxis package with `pip install .` (pulls in all transitive deps)
- runs as a non-root `praxis` user (uid 1000)
- entrypoint: `python -m praxis.launcher`

`.dockerignore` strips `.venv/`, `tests/`, `docs/`, `docs-site/`, journals, and caches so the image stays lean.

The image deliberately does **not** carry per-account manifests or strategy `.py` files. Those are operator-managed on the persistent disk (see [Manifests And Strategies](#manifests-and-strategies)).

## render.yaml Blueprint

`render.yaml` at the repo root describes a single Render Web Service:

| Setting | Value | Why |
|---|---|---|
| `type` | `web` | Exposes an HTTPS URL so Render can probe `/healthz` |
| `runtime` | `docker` | Builds from our `Dockerfile`, not Render's native Python runtime |
| `region` | `frankfurt` | Render POP for the deployment |
| `plan` | `starter` | Explicit so dashboard misclicks can't silently up-plan |
| `numInstances` | `1` | Two instances would double-submit every order |
| `autoDeploy` | `false` | Pushing to `main` does not auto-deploy; operators trigger deploys manually |
| `healthCheckPath` | `/healthz` | Render restarts on stuck processes, not only on crashes |

Environment variables break into three groups:

1. **Literal in blueprint** (committed, non-sensitive): `EPOCH_ID`, `VENUE_REST_URL`, `VENUE_WS_URL`, `MANIFESTS_DIR`, `STRATEGIES_BASE_PATH`, `STATE_BASE`, `STRATEGY_STATE_BASE`, `SHUTDOWN_TIMEOUT`, `LOG_FORMAT`, `LOG_LEVEL`, `HEALTHZ_PORT`
2. **`sync: false`** (value entered in Render dashboard, per account): `BINANCE_API_KEY_<ACCOUNT_ID>`, `BINANCE_API_SECRET_<ACCOUNT_ID>`. The blueprint declares one example pair for `ACCT_001`; add more as accounts onboard.
3. **Injected by Render**: `PORT` (used by `/healthz` when present, overrides `HEALTHZ_PORT`).

A persistent `disk:` block (`praxis-state`, mounted at `/var/lib/praxis`, 10 GB) holds the Event Spine SQLite file, per-account state, and operator-managed manifests/strategies. It survives restarts and is resizable up without downtime.

## Environment Contract

See [Launcher](Launcher.md#env-driven-entrypoint) for the complete list. In short:

- **Required shared**: `EPOCH_ID`, `VENUE_REST_URL`, `VENUE_WS_URL`, `MANIFESTS_DIR`, `STRATEGIES_BASE_PATH`, `STATE_BASE`
- **Per-account secrets**: `BINANCE_API_KEY_<ACCOUNT_ID>`, `BINANCE_API_SECRET_<ACCOUNT_ID>` where `<ACCOUNT_ID>` is the manifest's `account_id:` normalized (non-alphanumeric → `_`, uppercased)
- **Manifest-sourced** (not env): `account_id`, `allocated_capital`, `capital_pool`, `strategies`

## Manifests And Strategies

Manifests and strategy `.py` files live on the persistent disk, not in the image. The current deployment model (MMVP Option B) is operator-seeded:

```
/var/lib/praxis/
├── event_spine.sqlite     (created by Praxis on first successful boot)
├── manifests/             (operator-seeded; one YAML per account)
│   └── acct-001.yaml
├── strategies/            (operator-seeded; Python files referenced from manifests)
│   └── strat.py
├── <account_id>/          (Praxis-owned per-account state and WAL)
└── strategy_state/        (Praxis-owned strategy state blobs)
    └── <account_id>/
```

**Trade-offs accepted for MMVP**:

- no git history for manifest/strategy edits
- operator-sync across environments is manual
- disk loss wipes both state AND config

Future option to revisit before live: bake manifests/strategies from a separate deployment repo baked into the image at build time, or cloned at boot via a Render pre-deploy step.

## `/healthz` Contract

See [Launcher §Healthz](Launcher.md#healthz) for the response shape and failure conditions. Key operational consequences on Render:

- Render polls `/healthz` every few seconds; non-2xx triggers a container restart.
- On `SIGTERM` the launcher closes the healthz listener first, so Render sees the service unhealthy immediately and begins the replacement before the shutdown-timeout elapses.
- If a Nexus thread crashes, `/healthz` flips to 503 listing which account's thread died; Render then restarts, and recovery replays the Event Spine to rebuild state.

## Log Shipping

The launcher writes JSON log lines to stdout (via `observability.configure_logging`). Render captures stdout into its Log Stream. Render's default retention (~7 days) is too short for trading audit, so operators should configure an external Log Stream sink in the Render dashboard:

- Settings → Log Streams → point at Better Stack, Axiom, or an S3-backed log-drain service.
- The JSON shape allows the sink to index by structured fields (`epoch_id`, `account_id`, `command_id`, etc.) rather than regex-parsing human text.

## Operator Workflow — First Verify

Pre-requisites: `Vaquum/Praxis` `main` contains the latest launcher, Render workspace has a `Vaquum` GitHub App connection, operator has at least the `Developer` role.

1. Render dashboard → **Blueprints → New Blueprint Instance** from `Vaquum/Praxis` `main`. Render reads `render.yaml` and shows the service + disk that will be created.
2. First boot will fail at startup with `RuntimeError: no manifest files (*.yaml/*.yml) found in /var/lib/praxis/manifests` — **this is expected**. The persistent disk exists but is empty.
3. Open the service shell (Render dashboard → Shell), then:
   ```
   mkdir -p /var/lib/praxis/manifests /var/lib/praxis/strategies
   ```
   Upload the per-account manifest YAML(s) and referenced strategy `.py` file(s) using `render cp`, Render disk-detach + local mount, or an `scp`-like flow.
4. Service → Environment → enter `BINANCE_API_KEY_ACCT_<id>` and `BINANCE_API_SECRET_ACCT_<id>` (Binance Spot testnet keys for the initial verify). `sync: false` means these values are not committed to git.
5. **Manual Deploy → Deploy latest commit** (autoDeploy is off).
6. Watch the Log Stream: successful boot ends with `launching praxis` followed by per-account `nexus instance running`. `/healthz` flips to 200 shortly after.
7. Verification criteria:
   - Container status in Render UI: **Healthy**
   - `/var/lib/praxis/event_spine.sqlite` exists on the disk and grows with trading activity
   - JSON log lines carry `epoch_id` on every record
   - Manual **Restart Service** → container gracefully shuts down within `SHUTDOWN_TIMEOUT`, then comes back healthy with state intact

## Rotating Binance Credentials

1. Generate the new key pair on Binance.
2. Render dashboard → Service → Environment → edit `BINANCE_API_KEY_<ACCOUNT_ID>` and `BINANCE_API_SECRET_<ACCOUNT_ID>`. Render automatically redeploys on save.
3. After the replacement container is healthy, revoke the old key on Binance.

## Read Next

- [Launcher](Launcher.md)
- [Event Spine](Event-Spine.md)
- [Recovery And Reconciliation](Recovery-And-Reconciliation.md)
- [Health](Health.md)
