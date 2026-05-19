'''Binsim service entrypoint.

Reads its config from environment variables (no CLI flags) so the
operator can drop a single block into `docker-compose.yml` without
having to massage command lines. Required vs optional vars are
documented in `_parse_env` below; bad values exit non-zero with a
clear message.
'''

from __future__ import annotations

import asyncio
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

import aiohttp

from praxis.binsim.book import OrderBook
from praxis.binsim.feed import DepthPoller
from praxis.binsim.ledger import Ledger
from praxis.binsim.server import BinsimServer
from praxis.infrastructure.observability import configure_logging, get_logger


__all__ = ['main']


_DEFAULT_HOST = '0.0.0.0'  # noqa: S104 — container service binds to all interfaces by design
_DEFAULT_PORT = 8081
_DEFAULT_DEPTH_URL = 'https://binance-spot-depth20-1000ms.onrender.com/top20'
_DEFAULT_STALENESS_MS = 5000
_DEFAULT_POLL_INTERVAL_MS = 1000


@dataclass(frozen=True)
class _Config:

    host: str
    port: int
    depth_url: str
    depth_token: str
    state_dir: Path
    staleness_threshold_ms: int
    poll_interval_ms: int
    api_keys: dict[str, str]


def _parse_env(env: dict[str, str]) -> _Config:

    '''Build a `_Config` from env vars; raise `RuntimeError` on bad input.

    Required:
        BINSIM_DEPTH_TOKEN      Bearer token for the hosted depth-20 endpoint.
        BINSIM_STATE_DIR        Directory for the ledger snapshot (created if missing).
        BINSIM_API_KEYS         `apikey1=accountid1,apikey2=accountid2` mapping.

    Optional:
        BINSIM_HOST             Bind host (default 0.0.0.0).
        BINSIM_PORT             Bind port (default 8081).
        BINSIM_DEPTH_URL        Hosted depth source (default vaquum-hosted URL).
        BINSIM_STALENESS_MS     Order-rejection threshold in ms (default 5000).
        BINSIM_POLL_INTERVAL_MS Poll cadence in ms (default 1000).
    '''

    depth_token = env.get('BINSIM_DEPTH_TOKEN', '').strip()

    if not depth_token:
        msg = 'BINSIM_DEPTH_TOKEN is required'
        raise RuntimeError(msg)

    state_dir_raw = env.get('BINSIM_STATE_DIR', '').strip()

    if not state_dir_raw:
        msg = 'BINSIM_STATE_DIR is required'
        raise RuntimeError(msg)

    api_keys_raw = env.get('BINSIM_API_KEYS', '').strip()

    if not api_keys_raw:
        msg = 'BINSIM_API_KEYS is required (format: apikey1=accountid1,apikey2=accountid2)'
        raise RuntimeError(msg)

    api_keys = _parse_api_keys(api_keys_raw)

    host = env.get('BINSIM_HOST', _DEFAULT_HOST).strip() or _DEFAULT_HOST
    port = _parse_int_env(env, 'BINSIM_PORT', _DEFAULT_PORT)
    depth_url = env.get('BINSIM_DEPTH_URL', _DEFAULT_DEPTH_URL).strip() or _DEFAULT_DEPTH_URL
    staleness_threshold_ms = _parse_int_env(env, 'BINSIM_STALENESS_MS', _DEFAULT_STALENESS_MS)
    poll_interval_ms = _parse_int_env(env, 'BINSIM_POLL_INTERVAL_MS', _DEFAULT_POLL_INTERVAL_MS)

    return _Config(
        host=host,
        port=port,
        depth_url=depth_url,
        depth_token=depth_token,
        state_dir=Path(state_dir_raw),
        staleness_threshold_ms=staleness_threshold_ms,
        poll_interval_ms=poll_interval_ms,
        api_keys=api_keys,
    )


def _parse_api_keys(raw: str) -> dict[str, str]:

    '''Parse `apikey1=accountid1,apikey2=accountid2` into a dict.

    Empty entries are skipped (trailing commas are ignored). Duplicate
    api_keys raise — the same key can't map to two accounts.
    '''

    result: dict[str, str] = {}

    for chunk in raw.split(','):
        entry = chunk.strip()

        if not entry:
            continue

        if '=' not in entry:
            msg = f'BINSIM_API_KEYS entry {entry!r} is missing `=` separator'
            raise RuntimeError(msg)

        api_key, account_id = entry.split('=', 1)
        api_key = api_key.strip()
        account_id = account_id.strip()

        if not api_key or not account_id:
            msg = f'BINSIM_API_KEYS entry {entry!r} has empty api_key or account_id'
            raise RuntimeError(msg)

        if api_key in result:
            msg = f'BINSIM_API_KEYS contains duplicate api_key {api_key!r}'
            raise RuntimeError(msg)

        result[api_key] = account_id

    if not result:
        msg = 'BINSIM_API_KEYS parsed to an empty mapping'
        raise RuntimeError(msg)

    return result


def _parse_int_env(env: dict[str, str], name: str, default: int) -> int:

    raw = env.get(name, '').strip()

    if not raw:
        return default

    try:
        return int(raw)
    except ValueError as exc:
        msg = f'{name} must be an integer, got {raw!r}'
        raise RuntimeError(msg) from exc


async def _run(config: _Config) -> None:

    log = get_logger(__name__)

    book = OrderBook()

    ledger = Ledger(config.state_dir)
    await ledger.load()

    poller = DepthPoller(
        book,
        config.depth_url,
        config.depth_token,
        poll_interval_ms=config.poll_interval_ms,
    )

    server = BinsimServer(
        config.host,
        config.port,
        book,
        ledger,
        poller,
        config.staleness_threshold_ms,
        config.api_keys,
    )

    await poller.start()

    try:

        try:
            await poller.poll_once()
        except (aiohttp.ClientError, TimeoutError, RuntimeError, ValueError, OSError) as exc:
            log.warning(
                'binsim initial depth poll failed; staleness gate will trip until poller recovers',
                error=str(exc),
                error_type=type(exc).__name__,
            )

        await server.start()

        log.info(
            'binsim ready',
            host=config.host,
            port=config.port,
            depth_url=config.depth_url,
            staleness_threshold_ms=config.staleness_threshold_ms,
            poll_interval_ms=config.poll_interval_ms,
            accounts=sorted(await ledger.accounts()),
            api_keys=sorted(config.api_keys.keys()),
        )

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)

        await stop.wait()

    finally:
        log.info('binsim shutting down')
        await server.stop()
        await poller.stop()
        log.info('binsim stopped')


def main() -> None:

    configure_logging()
    config = _parse_env(dict(os.environ))
    asyncio.run(_run(config))


if __name__ == '__main__':
    log = get_logger(__name__)

    try:
        main()
    except Exception:
        log.exception('binsim failed')
        sys.exit(1)
