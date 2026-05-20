'''Per-account balance + fill ledger with atomic snapshot persistence.'''

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from praxis.core.domain.enums import OrderSide
from praxis.infrastructure.observability import get_logger


__all__ = [
    'Account',
    'DuplicateClientOrderIdError',
    'InsufficientBalanceError',
    'Ledger',
    'LedgerFill',
]


_log = get_logger(__name__)

_SNAPSHOT_FILENAME = 'binsim_ledger.json'
_QUOTE_ASSET = 'USDT'
_BASE_ASSET = 'BTC'
_ZERO = Decimal(0)
_API_KEY_BYTES = 32


class InsufficientBalanceError(Exception):

    '''Raised when an `apply_fill` would drive a balance below zero.'''


class DuplicateClientOrderIdError(Exception):

    '''Raised when `apply_order` is called with a `client_order_id`
    already seen for the same account. Mirrors Binance's rejection of
    duplicate `newClientOrderId` submissions so Praxis-side dedup
    semantics survive the swap from testnet to binsim.'''


@dataclass(frozen=True)
class LedgerFill:

    '''Single fill recorded against an account.

    Mirrors the subset of Binance's `fills[]` payload the ledger
    actually owns (trade id, side, qty, price, fee) plus the wall-clock
    timestamp. Order-level identifiers (client_order_id, command_id,
    venue_order_id) are the caller's responsibility — they live in
    Praxis's event_spine, not in the binsim ledger.
    '''

    trade_id: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    fee: Decimal
    fee_asset: str
    timestamp: datetime


@dataclass
class Account:

    '''In-memory per-account snapshot owned by `Ledger`.

    Stores the **SHA-256 hash** of the api_key, never the raw key.
    The plaintext key is returned exactly once from
    `Ledger.register_account()` — operators capture it then and the
    binsim cannot recover it later. Subsequent `account_for_api_key`
    lookups hash the incoming `X-MBX-APIKEY` and compare to the
    stored hash.
    '''

    account_id: str
    api_key_hash: str
    usdt: Decimal
    btc: Decimal
    fills: list[LedgerFill]
    seen_client_order_ids: set[str] = field(default_factory=set)


class Ledger:

    '''Per-account balance + fill history with atomic disk snapshot.

    State is held in-memory and replicated to a single JSON file via
    tempfile-plus-rename after every mutation. On `load()` the file is
    read back to restore prior state, so the same Ledger survives a
    process restart.

    Concurrency: a single `asyncio.Lock` serialises every mutation.
    The ledger is the binsim's authoritative balance state — the
    single-writer model keeps balance math obviously correct under the
    HTTP server's concurrent request handlers.

    Fee model (MMVP): fees are debited from the quote asset (USDT).
    `apply_fill` raises if `fee_asset` is anything other than `USDT`.
    '''

    def __init__(self, state_dir: Path) -> None:

        if not isinstance(state_dir, Path):
            raise TypeError(f'state_dir must be a Path, got {type(state_dir).__name__}')

        self._state_dir = state_dir
        self._snapshot_path = state_dir / _SNAPSHOT_FILENAME
        self._accounts: dict[str, Account] = {}
        self._api_key_index: dict[str, str] = {}
        self._next_trade_id = 1
        self._next_order_id = 1
        self._lock = asyncio.Lock()

    async def load(self) -> None:

        '''Restore from `<state_dir>/binsim_ledger.json` if it exists.

        Safe to call before `register_account`. A missing file is a
        no-op (fresh install). A corrupt or unparseable file raises
        so the operator notices before fills land on top of mangled
        state.
        '''

        async with self._lock:
            if not self._snapshot_path.exists():
                return

            raw = self._snapshot_path.read_text()
            payload = json.loads(raw)

            self._next_trade_id = int(payload['next_trade_id'])
            self._next_order_id = int(payload.get('next_order_id', 1))
            self._accounts = {
                account_id: _account_from_dict(account_id, data)
                for account_id, data in payload['accounts'].items()
            }
            self._api_key_index = {
                account.api_key_hash: account.account_id
                for account in self._accounts.values()
            }

    async def register_account(
        self,
        account_id: str,
        initial_usdt: Decimal,
        initial_btc: Decimal = _ZERO,
    ) -> str:

        '''Create an account with starting balances and assign an api_key.

        The api_key is generated server-side via `secrets.token_hex` so
        the operator never picks (or types) one. Returned to the caller
        so it can be copied into Praxis's `BINANCE_API_KEY_<acct>`
        env var; binsim's signed endpoints use this api_key (sent in
        the `X-MBX-APIKEY` header) to resolve the calling account.

        Raises:
            ValueError: account_id is empty or whitespace-only, initial
                balance is negative, or account already exists.
        '''

        account_id = (account_id or '').strip()

        if not account_id:
            raise ValueError('account_id cannot be empty or whitespace-only')

        if not initial_usdt.is_finite() or not initial_btc.is_finite():
            raise ValueError(
                f'initial balances must be finite, got initial_usdt={initial_usdt} '
                f'initial_btc={initial_btc}'
            )

        if initial_usdt < _ZERO:
            raise ValueError(f'initial_usdt must be non-negative, got {initial_usdt}')

        if initial_btc < _ZERO:
            raise ValueError(f'initial_btc must be non-negative, got {initial_btc}')

        async with self._lock:
            if account_id in self._accounts:
                raise ValueError(f'account already registered: {account_id}')

            api_key = self._mint_unique_api_key_locked()
            api_key_hash = _hash_api_key(api_key)

            self._accounts[account_id] = Account(
                account_id=account_id,
                api_key_hash=api_key_hash,
                usdt=initial_usdt,
                btc=initial_btc,
                fills=[],
            )
            self._api_key_index[api_key_hash] = account_id

            self._snapshot_locked()

            return api_key

    def _mint_unique_api_key_locked(self) -> str:

        '''Generate a fresh 64-hex-char api_key whose hash is not in the index.

        Collision is astronomically unlikely with 256 bits of entropy
        but the retry loop makes the post-condition trivially provable.
        '''

        while True:
            candidate = secrets.token_hex(_API_KEY_BYTES)

            if _hash_api_key(candidate) not in self._api_key_index:
                return candidate

    def account_for_api_key(self, api_key: object) -> str | None:

        '''Look up the `account_id` controlled by `api_key`, or `None`.

        Hashes the incoming key and compares against the stored
        `api_key_hash` — the plaintext is never persisted, so this
        is the only way to resolve a lookup.

        Synchronous because it's a single dict read against state that
        only mutates under `register_account` (which holds the lock).
        Signed-request handlers call this from inside a request — no
        await overhead on the hot path.

        Returns `None` for any non-string or whitespace-only input
        without raising — caller decides how to translate the miss
        (typically a 401/-1022 frame). This guards against malformed
        JSON payloads in upstream handlers (e.g. `{"apiKey": 123}`)
        that would otherwise crash at `_hash_api_key().encode()`.
        '''

        if not isinstance(api_key, str):
            return None

        stripped = api_key.strip()

        if not stripped:
            return None

        return self._api_key_index.get(_hash_api_key(stripped))

    async def apply_fill(
        self,
        account_id: str,
        side: OrderSide,
        qty: Decimal,
        price: Decimal,
        fee: Decimal,
        fee_asset: str = _QUOTE_ASSET,
        timestamp: datetime | None = None,
    ) -> LedgerFill:

        '''Settle one fill against an account: debit/credit, append, snapshot.

        Returns the recorded `LedgerFill` with the ledger-assigned
        `trade_id` so the HTTP layer can echo it back in the
        Binance-shaped `POST /api/v3/order` response.

        Raises:
            KeyError: account not registered.
            ValueError: qty/price/fee non-positive (fee may be zero),
                fee_asset is not USDT, or timestamp is naive.
            InsufficientBalanceError: settling the fill would drive a
                balance below zero.
        '''

        if not qty.is_finite() or not price.is_finite() or not fee.is_finite():
            raise ValueError(
                f'qty/price/fee must all be finite, got qty={qty} price={price} fee={fee}'
            )

        if qty <= _ZERO:
            raise ValueError(f'qty must be positive, got {qty}')

        if price <= _ZERO:
            raise ValueError(f'price must be positive, got {price}')

        if fee < _ZERO:
            raise ValueError(f'fee must be non-negative, got {fee}')

        if fee_asset != _QUOTE_ASSET:
            raise ValueError(
                f'fee_asset must be {_QUOTE_ASSET} for MMVP, got {fee_asset!r}'
            )

        ts = _resolve_timestamp(timestamp)
        notional = qty * price

        async with self._lock:
            if account_id not in self._accounts:
                raise KeyError(f'account not registered: {account_id}')

            account = self._accounts[account_id]
            new_usdt, new_btc = _settle(account, side, qty, notional, fee)

            fill = LedgerFill(
                trade_id=str(self._next_trade_id),
                side=side,
                qty=qty,
                price=price,
                fee=fee,
                fee_asset=fee_asset,
                timestamp=ts,
            )

            account.usdt = new_usdt
            account.btc = new_btc
            account.fills.append(fill)
            self._next_trade_id += 1

            self._snapshot_locked()

            return fill

    async def apply_order(
        self,
        account_id: str,
        side: OrderSide,
        fills: list[tuple[Decimal, Decimal, Decimal]],
        client_order_id: str,
        timestamp: datetime | None = None,
    ) -> tuple[int, list[LedgerFill]]:

        '''Settle a multi-level market order atomically with dedup.

        `fills` is a list of `(price, qty, fee)` per level produced by
        walking the order book. All settlement happens under the
        ledger lock: balances reflect the aggregate notional + fees,
        each level becomes its own `LedgerFill` with a fresh monotonic
        `trade_id`, the assigned `order_id` is returned for the
        Binance-shaped POST response, and the `client_order_id` is
        recorded so a duplicate submit raises rather than double-fills.

        Returns:
            `(order_id, recorded_fills)` — `order_id` is monotonically
            assigned and unique per call; `recorded_fills` preserves
            the input order with each entry carrying its assigned
            `trade_id`.

        Raises:
            KeyError: account not registered.
            ValueError: fills empty, client_order_id empty, qty/price/fee
                non-positive (fee may be zero), or timestamp naive.
            DuplicateClientOrderIdError: `client_order_id` already
                recorded against this account.
            InsufficientBalanceError: settling the aggregate would
                drive a balance below zero.
        '''

        if not fills:
            raise ValueError('fills cannot be empty')

        client_order_id = (client_order_id or '').strip()

        if not client_order_id:
            raise ValueError('client_order_id cannot be empty or whitespace-only')

        for price, qty, fee in fills:
            if not price.is_finite() or not qty.is_finite() or not fee.is_finite():
                raise ValueError(
                    f'fill must have finite (price, qty, fee), got ({price}, {qty}, {fee})'
                )

            if price <= _ZERO:
                raise ValueError(f'price must be positive, got {price}')

            if qty <= _ZERO:
                raise ValueError(f'qty must be positive, got {qty}')

            if fee < _ZERO:
                raise ValueError(f'fee must be non-negative, got {fee}')

        ts = _resolve_timestamp(timestamp)

        async with self._lock:
            if account_id not in self._accounts:
                raise KeyError(f'account not registered: {account_id}')

            account = self._accounts[account_id]

            if client_order_id in account.seen_client_order_ids:
                raise DuplicateClientOrderIdError(
                    f'account {account_id}: client_order_id {client_order_id!r} already recorded'
                )

            new_usdt = account.usdt
            new_btc = account.btc

            for price, qty, fee in fills:
                notional = qty * price

                if side is OrderSide.BUY:
                    new_usdt -= notional + fee
                    new_btc += qty
                else:
                    new_usdt += notional - fee
                    new_btc -= qty

            if new_usdt < _ZERO:
                raise InsufficientBalanceError(
                    f'account {account_id} USDT would be {new_usdt} (current {account.usdt}, '
                    f'side {side.value}, {len(fills)} fills)'
                )

            if new_btc < _ZERO:
                raise InsufficientBalanceError(
                    f'account {account_id} BTC would be {new_btc} (current {account.btc}, '
                    f'side {side.value}, {len(fills)} fills)'
                )

            records: list[LedgerFill] = []
            for price, qty, fee in fills:
                record = LedgerFill(
                    trade_id=str(self._next_trade_id),
                    side=side,
                    qty=qty,
                    price=price,
                    fee=fee,
                    fee_asset=_QUOTE_ASSET,
                    timestamp=ts,
                )
                records.append(record)
                self._next_trade_id += 1

            order_id = self._next_order_id
            self._next_order_id += 1

            account.usdt = new_usdt
            account.btc = new_btc
            account.fills.extend(records)
            account.seen_client_order_ids.add(client_order_id)

            self._snapshot_locked()

            return order_id, records

    async def balance(self, account_id: str) -> tuple[Decimal, Decimal]:

        '''Return `(usdt, btc)` for `account_id`.

        Raises:
            KeyError: account not registered.
        '''

        async with self._lock:
            if account_id not in self._accounts:
                raise KeyError(f'account not registered: {account_id}')

            account = self._accounts[account_id]

            return account.usdt, account.btc

    async def fills(self, account_id: str) -> list[LedgerFill]:

        '''Return a copy of the fill history for `account_id`.

        Raises:
            KeyError: account not registered.
        '''

        async with self._lock:
            if account_id not in self._accounts:
                raise KeyError(f'account not registered: {account_id}')

            return list(self._accounts[account_id].fills)

    async def accounts(self) -> list[str]:

        '''Return all registered account ids (snapshot at call time).'''

        async with self._lock:
            return list(self._accounts.keys())

    def _snapshot_locked(self) -> None:

        payload = {
            'next_trade_id': self._next_trade_id,
            'next_order_id': self._next_order_id,
            'accounts': {
                account_id: _account_to_dict(account)
                for account_id, account in self._accounts.items()
            },
        }

        self._state_dir.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            prefix=self._snapshot_path.name + '.', suffix='.tmp',
            dir=self._snapshot_path.parent,
        )
        os.close(fd)
        tmp = Path(tmp_path)

        try:
            tmp.write_text(json.dumps(payload))
            tmp.replace(self._snapshot_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise


def _settle(
    account: Account,
    side: OrderSide,
    qty: Decimal,
    notional: Decimal,
    fee: Decimal,
) -> tuple[Decimal, Decimal]:

    '''Compute post-fill (usdt, btc); raise if either would go negative.'''

    if side is OrderSide.BUY:
        new_usdt = account.usdt - notional - fee
        new_btc = account.btc + qty
    else:
        new_usdt = account.usdt + notional - fee
        new_btc = account.btc - qty

    if new_usdt < _ZERO:
        raise InsufficientBalanceError(
            f'account {account.account_id} USDT would be {new_usdt} (current {account.usdt}, '
            f'side {side.value}, notional {notional}, fee {fee})'
        )

    if new_btc < _ZERO:
        raise InsufficientBalanceError(
            f'account {account.account_id} BTC would be {new_btc} (current {account.btc}, '
            f'side {side.value}, qty {qty})'
        )

    return new_usdt, new_btc


def _resolve_timestamp(timestamp: datetime | None) -> datetime:

    if timestamp is None:
        return datetime.now(UTC)

    if timestamp.tzinfo is None:
        raise ValueError(f'timestamp must be timezone-aware, got naive: {timestamp}')

    return timestamp.astimezone(UTC)


def _account_to_dict(account: Account) -> dict[str, object]:

    return {
        'api_key_hash': account.api_key_hash,
        'usdt': str(account.usdt),
        'btc': str(account.btc),
        'fills': [_fill_to_dict(f) for f in account.fills],
        'seen_client_order_ids': sorted(account.seen_client_order_ids),
    }


def _account_from_dict(account_id: str, data: dict[str, Any]) -> Account:

    raw_fills = cast(list[dict[str, str]], data['fills'])
    raw_cids = cast(list[str], data.get('seen_client_order_ids', []))

    return Account(
        account_id=account_id,
        api_key_hash=str(data['api_key_hash']),
        usdt=Decimal(str(data['usdt'])),
        btc=Decimal(str(data['btc'])),
        fills=[_fill_from_dict(f) for f in raw_fills],
        seen_client_order_ids=set(raw_cids),
    )


def _hash_api_key(api_key: str) -> str:

    '''SHA-256 of the api_key, hex-encoded. The ledger never persists
    the plaintext — it only stores + indexes by this hash.

    SHA-256 (not bcrypt/argon2) is correct here: api_keys are
    256-bit random tokens minted via `secrets.token_hex(32)`, not
    user-chosen passwords. Brute-forcing a 256-bit random key is
    infeasible regardless of the hash speed, so the
    "slow-hash-for-password-storage" rule does not apply.
    '''

    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()  # lgtm[py/weak-sensitive-data-hashing]


def _fill_to_dict(fill: LedgerFill) -> dict[str, str]:

    return {
        'trade_id': fill.trade_id,
        'side': fill.side.value,
        'qty': str(fill.qty),
        'price': str(fill.price),
        'fee': str(fill.fee),
        'fee_asset': fill.fee_asset,
        'timestamp': fill.timestamp.isoformat(),
    }


def _fill_from_dict(data: dict[str, str]) -> LedgerFill:

    return LedgerFill(
        trade_id=data['trade_id'],
        side=OrderSide(data['side']),
        qty=Decimal(data['qty']),
        price=Decimal(data['price']),
        fee=Decimal(data['fee']),
        fee_asset=data['fee_asset'],
        timestamp=datetime.fromisoformat(data['timestamp']),
    )
