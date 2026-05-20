'''Binsim service entrypoint with `register` admin subcommand.

Default invocation runs the HTTP+WS server:

    python -m praxis.binsim

The `register` subcommand mints an api_key for a new account, prints
it on stdout, and exits. The server MUST be stopped before running
`register` — both processes write the same ledger snapshot file and
have no inter-process lock:

    python -m praxis.binsim register --account-id acc-1 --initial-usdt 10000
'''

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

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


def _parse_env(env: dict[str, str]) -> _Config:

    '''Build a `_Config` from env vars; raise `RuntimeError` on bad input.

    Required:
        BINSIM_DEPTH_TOKEN      Bearer token for the hosted depth-20 endpoint.
        BINSIM_STATE_DIR        Directory for the ledger snapshot (created if missing).

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

    host = env.get('BINSIM_HOST', _DEFAULT_HOST).strip() or _DEFAULT_HOST
    port = _parse_int_env(env, 'BINSIM_PORT', _DEFAULT_PORT, min_value=0, max_value=65535)
    depth_url = env.get('BINSIM_DEPTH_URL', _DEFAULT_DEPTH_URL).strip() or _DEFAULT_DEPTH_URL
    staleness_threshold_ms = _parse_int_env(
        env, 'BINSIM_STALENESS_MS', _DEFAULT_STALENESS_MS, min_value=1,
    )
    poll_interval_ms = _parse_int_env(
        env, 'BINSIM_POLL_INTERVAL_MS', _DEFAULT_POLL_INTERVAL_MS, min_value=1,
    )

    return _Config(
        host=host,
        port=port,
        depth_url=depth_url,
        depth_token=depth_token,
        state_dir=Path(state_dir_raw),
        staleness_threshold_ms=staleness_threshold_ms,
        poll_interval_ms=poll_interval_ms,
    )


def _parse_int_env(
    env: dict[str, str],
    name: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:

    raw = env.get(name, '').strip()

    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        msg = f'{name} must be an integer, got {raw!r}'
        raise RuntimeError(msg) from exc

    if min_value is not None and value < min_value:
        msg = f'{name} must be >= {min_value}, got {value}'
        raise RuntimeError(msg)

    if max_value is not None and value > max_value:
        msg = f'{name} must be <= {max_value}, got {value}'
        raise RuntimeError(msg)

    return value


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
    )

    # Register signal handlers BEFORE any long-lived component starts.
    # If SIGTERM/SIGINT arrives during startup, the handler is already
    # in place and the finally block runs the intended cleanup.
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    try:
        # The poller's background loop primes the book on its first
        # iteration — no separate `poll_once` call is needed here, so
        # there is no race between a manual prime and the loop.
        await poller.start()
        await server.start()

        log.info(
            'binsim ready',
            host=config.host,
            port=config.port,
            depth_url=config.depth_url,
            staleness_threshold_ms=config.staleness_threshold_ms,
            poll_interval_ms=config.poll_interval_ms,
            accounts=sorted(await ledger.accounts()),
        )

        await stop.wait()

    finally:
        log.info('binsim shutting down')
        await server.stop()
        await poller.stop()
        log.info('binsim stopped')


async def _register(
    state_dir: Path,
    account_id: str,
    initial_usdt: Decimal,
    initial_btc: Decimal,
) -> str:

    ledger = Ledger(state_dir)
    await ledger.load()

    return await ledger.register_account(account_id, initial_usdt, initial_btc)


def _parse_decimal_arg(name: str, raw: str) -> Decimal:

    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        msg = f'--{name} must be a valid decimal, got {raw!r}'
        raise SystemExit(msg) from exc


def main(argv: list[str] | None = None) -> None:

    configure_logging()

    parser = argparse.ArgumentParser(prog='praxis.binsim')
    sub = parser.add_subparsers(dest='command')

    register = sub.add_parser('register', help='Register an account and print its assigned api_key')
    register.add_argument('--account-id', required=True)
    register.add_argument('--initial-usdt', required=True)
    register.add_argument('--initial-btc', default='0')

    args = parser.parse_args(argv)

    if args.command == 'register':
        state_dir_raw = os.environ.get('BINSIM_STATE_DIR', '').strip()

        if not state_dir_raw:
            msg = 'BINSIM_STATE_DIR is required for `register`'
            raise SystemExit(msg)

        initial_usdt = _parse_decimal_arg('initial-usdt', args.initial_usdt)
        initial_btc = _parse_decimal_arg('initial-btc', args.initial_btc)

        minted = asyncio.run(
            _register(Path(state_dir_raw), args.account_id, initial_usdt, initial_btc),
        )
        # Intended: print the minted api_key on stdout so the operator
        # can capture it. The ledger only persists a SHA-256 hash, so
        # this is the operator's one chance to grab it.
        sys.stdout.write(minted + '\n')

        return

    config = _parse_env(dict(os.environ))
    asyncio.run(_run(config))


if __name__ == '__main__':
    log = get_logger(__name__)

    try:
        main()
    except Exception:  # noqa: BLE001 - top-level entrypoint, log and exit non-zero
        log.exception('binsim failed')
        sys.exit(1)
