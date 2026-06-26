'''HTTP surface for launching and polling replay runs.

`POST /replay` accepts a run request, slices the requested `[start, end]`
window out of the mounted projection frames into a `ReplayScenario`, and
schedules `run_replay` on a single-worker executor off the aiohttp event
loop (so a multi-second run never blocks the listener). It returns a
`run_id` immediately; `GET /replay/{run_id}` reports the run's status and,
once finished, its result summary.

Runs are serialized (one worker) for phase one: `run_replay` writes a
strategy module per run and the launcher imports it by name, so
concurrent runs would collide in the module cache. Parallelism is a
later step gated on per-run module isolation.
'''

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from aiohttp import web

from praxis.infrastructure.venue_adapter import SymbolFilters
from praxis.replay.load_replay_bars import load_replay_bars
from praxis.replay.replay_scenario import ReplayScenario
from praxis.replay.replay_report import ReplayMetrics, Trade
from praxis.replay.run_replay import ReplayResult, run_replay

__all__ = ['build_replay_app', 'serve_replay_app']

_STATUS_RUNNING = 'running'
_STATUS_DONE = 'done'
_STATUS_FAILED = 'failed'
_LOOPBACK_HOSTS = frozenset({'127.0.0.1', '::1'})
_DEFAULT_MAX_BARS = 50_000

_Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def _is_loopback(remote: str | None) -> bool:
    '''Return whether a peer address is the loopback interface.'''

    return remote in _LOOPBACK_HOSTS


@web.middleware
async def _loopback_only(request: web.Request, handler: _Handler) -> web.StreamResponse:
    '''Reject any request whose peer is not the loopback interface.

    Defense in depth behind the loopback bind: the replay API accepts a
    strategy module and executes it, so it must never serve a non-local
    peer even if mounted on a misconfigured listener.
    '''

    if not _is_loopback(request.remote):
        return web.json_response({'error': 'forbidden'}, status=403)

    return await handler(request)


@dataclass
class _RunRecord:
    '''Mutable status of one replay run.'''

    status: str
    result: ReplayResult | None = None
    error: str | None = None


def build_replay_app(
    *,
    arrow_dir: Path,
    conduit_dir: Path,
    work_root: Path,
    max_bars: int = _DEFAULT_MAX_BARS,
) -> web.Application:
    '''Build the aiohttp app exposing the replay run endpoints.

    The app is loopback-only (a middleware rejects non-local peers) since
    a request carries a strategy module that the run executes; serve it
    via `serve_replay_app`, which binds to 127.0.0.1.

    Args:
        arrow_dir: Read-only mount holding per-series OHLCV frames.
        conduit_dir: Read-only mount holding per-series prediction frames.
        work_root: Directory under which each run gets its own work dir.
        max_bars: Reject a request whose range resolves to more bars than
            this, to bound a single synchronous run.

    Returns:
        An aiohttp application with `POST /replay` and
        `GET /replay/{run_id}` wired.
    '''

    registry: dict[str, _RunRecord] = {}
    lock = threading.Lock()
    executor = ThreadPoolExecutor(max_workers=1)

    def _execute(run_id: str, scenario: ReplayScenario) -> None:
        try:
            result = run_replay(scenario, work_dir=work_root / run_id)
        except Exception as exc:  # noqa: BLE001 - surfaced via the run record
            with lock:
                registry[run_id] = _RunRecord(status=_STATUS_FAILED, error=str(exc))
            return

        with lock:
            registry[run_id] = _RunRecord(status=_STATUS_DONE, result=result)

    async def post_replay(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return web.json_response({'error': 'body is not valid JSON'}, status=400)

        if not isinstance(payload, dict):
            return web.json_response({'error': 'body must be a JSON object'}, status=400)

        try:
            scenario = _scenario_from_request(payload, arrow_dir, conduit_dir)
        except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
            return web.json_response({'error': str(exc)}, status=400)

        if not scenario.bars:
            return web.json_response(
                {'error': 'no usable bars in the requested range'}, status=400,
            )

        if len(scenario.bars) > max_bars:
            return web.json_response(
                {
                    'error': (
                        f'range resolves to {len(scenario.bars)} bars, '
                        f'over the {max_bars} limit'
                    ),
                },
                status=400,
            )

        run_id = uuid.uuid4().hex

        with lock:
            registry[run_id] = _RunRecord(status=_STATUS_RUNNING)

        executor.submit(_execute, run_id, scenario)

        return web.json_response({'run_id': run_id}, status=202)

    async def get_replay(request: web.Request) -> web.Response:
        run_id = request.match_info['run_id']

        with lock:
            record = registry.get(run_id)

        if record is None:
            return web.json_response({'error': 'unknown run_id'}, status=404)

        return web.json_response(_record_json(run_id, record))

    async def _shutdown_executor(_app: web.Application) -> None:
        executor.shutdown(wait=True, cancel_futures=True)

    app = web.Application(middlewares=[_loopback_only])
    app.router.add_post('/replay', post_replay)
    app.router.add_get('/replay/{run_id}', get_replay)
    app.on_cleanup.append(_shutdown_executor)

    return app


def serve_replay_app(app: web.Application, *, port: int) -> None:
    '''Serve the replay app on the loopback interface only.

    Args:
        app: The application from `build_replay_app`.
        port: TCP port to bind on 127.0.0.1.
    '''

    web.run_app(app, host='127.0.0.1', port=port)


def _scenario_from_request(
    payload: dict[str, Any],
    arrow_dir: Path,
    conduit_dir: Path,
) -> ReplayScenario:
    '''Build a ReplayScenario from a request payload and the mounts.'''

    series = str(payload['series'])
    interval_seconds = int(payload['interval_seconds'])

    if interval_seconds <= 0:
        msg = f'interval_seconds must be positive: {interval_seconds}'
        raise ValueError(msg)

    start = _parse_ts(payload['start'])
    end = _parse_ts(payload['end'])

    if start > end:
        msg = f'start must not be after end: {start} > {end}'
        raise ValueError(msg)

    bars = load_replay_bars(
        arrow_dir=arrow_dir,
        conduit_dir=conduit_dir,
        series=series,
        interval_seconds=interval_seconds,
        start=start,
        end=end,
    )

    return ReplayScenario(
        account_id=str(payload['account_id']),
        series=series,
        interval_seconds=interval_seconds,
        symbol=str(payload['symbol']),
        capital_pool=_positive_decimal(payload['capital_pool'], 'capital_pool'),
        filters=_filters_from_request(str(payload['symbol']), payload['filters']),
        strategy_source=str(payload['strategy_source']),
        bars=bars,
    )


def _positive_decimal(raw: Any, name: str) -> Decimal:
    '''Parse a finite, strictly-positive Decimal or raise ValueError.'''

    value = Decimal(str(raw))

    if not value.is_finite() or value <= 0:
        msg = f'{name} must be a finite positive number: {raw!r}'
        raise ValueError(msg)

    return value


def _filters_from_request(symbol: str, raw: dict[str, Any]) -> SymbolFilters:
    '''Build SymbolFilters from a request's filter payload, all positive.'''

    return SymbolFilters(
        symbol=symbol,
        tick_size=_positive_decimal(raw['tick_size'], 'tick_size'),
        lot_step=_positive_decimal(raw['lot_step'], 'lot_step'),
        lot_min=_positive_decimal(raw['lot_min'], 'lot_min'),
        lot_max=_positive_decimal(raw['lot_max'], 'lot_max'),
        min_notional=_positive_decimal(raw['min_notional'], 'min_notional'),
    )


def _parse_ts(raw: str) -> datetime:
    '''Parse an ISO8601 timestamp, accepting a trailing Z as UTC.'''

    normalized = f'{raw[:-1]}+00:00' if raw.endswith('Z') else raw

    return datetime.fromisoformat(normalized)


def _record_json(run_id: str, record: _RunRecord) -> dict[str, Any]:
    '''Render a run record as a JSON-serialisable dict.'''

    body: dict[str, Any] = {'run_id': run_id, 'status': record.status}

    if record.result is not None:
        result = record.result
        body['result'] = {
            'bars': result.bars,
            'fills': result.fills,
            'buy_qty': str(result.buy_qty),
            'sell_qty': str(result.sell_qty),
            'fees': str(result.fees),
            'realized_pnl': str(result.realized_pnl),
            'outcome_status_counts': result.outcome_status_counts,
            'metrics': _metrics_json(result.metrics),
            'trades': [_trade_json(trade) for trade in result.trades],
        }

    if record.error is not None:
        body['error'] = record.error

    return body


def _optional_decimal(value: Decimal | None) -> str | None:

    return None if value is None else str(value)


def _metrics_json(metrics: ReplayMetrics) -> dict[str, Any]:
    '''Render `ReplayMetrics` as a JSON-serialisable dict.'''

    return {
        'trade_count': metrics.trade_count,
        'win_count': metrics.win_count,
        'loss_count': metrics.loss_count,
        'win_rate': _optional_decimal(metrics.win_rate),
        'gross_pnl': str(metrics.gross_pnl),
        'net_pnl': str(metrics.net_pnl),
        'total_fees': str(metrics.total_fees),
        'pnl_pct': str(metrics.pnl_pct),
        'avg_win': _optional_decimal(metrics.avg_win),
        'avg_loss': _optional_decimal(metrics.avg_loss),
        'profit_factor': _optional_decimal(metrics.profit_factor),
        'max_drawdown_pct': str(metrics.max_drawdown_pct),
        'sharpe': _optional_decimal(metrics.sharpe),
        'exposure_pct': str(metrics.exposure_pct),
        'final_equity': str(metrics.final_equity),
        'open_position_qty': str(metrics.open_position_qty),
    }


def _trade_json(trade: Trade) -> dict[str, Any]:
    '''Render a `Trade` as a JSON-serialisable dict.'''

    return {
        'entry_ts': trade.entry_ts.isoformat(),
        'exit_ts': trade.exit_ts.isoformat(),
        'entry_price': str(trade.entry_price),
        'exit_price': str(trade.exit_price),
        'qty': str(trade.qty),
        'gross_pnl': str(trade.gross_pnl),
        'fees': str(trade.fees),
        'net_pnl': str(trade.net_pnl),
        'return_pct': str(trade.return_pct),
        'bars_held': trade.bars_held,
    }
