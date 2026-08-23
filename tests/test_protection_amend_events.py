'''
Tests for the bracket protective-OCO amend events and status enum.
'''

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal

import pytest

from praxis.core.domain.enums import BracketProtectionStatus
from praxis.core.domain.events import (
    Event,
    ProtectionActive,
    ProtectionAmendRequested,
    ProtectionCancelConfirmed,
    ProtectionFailed,
    ProtectionReplaceSubmitted,
    ProtectionStateUnknown,
)
from praxis.core.trading_state import TradingState
from praxis.infrastructure import event_spine
from praxis.infrastructure.event_spine import EventSpine

_TS = datetime(2026, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_CMD = 'cmd-1'
_NEW_LIST = 'oco-new-1'
_OLD_LIST = 'oco-old-1'
_EPOCH = 1

_AMEND_REQUESTED = ProtectionAmendRequested(
    account_id=_ACCT, timestamp=_TS,
    command_id=_CMD, protection_version=1,
    new_list_client_order_id=_NEW_LIST,
    old_list_client_order_id=_OLD_LIST,
    take_profit_price=Decimal('52000.50'),
    stop_loss_price=Decimal('48000.00'),
    stop_loss_limit_price=Decimal('47900.25'),
)

_CANCEL_CONFIRMED = ProtectionCancelConfirmed(
    account_id=_ACCT, timestamp=_TS,
    command_id=_CMD, protection_version=1,
)

_STATE_UNKNOWN = ProtectionStateUnknown(
    account_id=_ACCT, timestamp=_TS,
    command_id=_CMD, protection_version=1, reason='venue timeout',
)

_REPLACE_SUBMITTED = ProtectionReplaceSubmitted(
    account_id=_ACCT, timestamp=_TS,
    command_id=_CMD, protection_version=1,
    new_list_client_order_id=_NEW_LIST,
)

_ACTIVE = ProtectionActive(
    account_id=_ACCT, timestamp=_TS,
    command_id=_CMD, protection_version=1,
    new_list_client_order_id=_NEW_LIST,
)

_FAILED = ProtectionFailed(
    account_id=_ACCT, timestamp=_TS,
    command_id=_CMD, protection_version=1, reason='no protection live',
)

_ALL_EVENTS: list[Event] = [
    _AMEND_REQUESTED,
    _CANCEL_CONFIRMED,
    _STATE_UNKNOWN,
    _REPLACE_SUBMITTED,
    _ACTIVE,
    _FAILED,
]


@pytest.mark.parametrize(
    'name',
    [
        'ProtectionAmendRequested',
        'ProtectionCancelConfirmed',
        'ProtectionStateUnknown',
        'ProtectionReplaceSubmitted',
        'ProtectionActive',
        'ProtectionFailed',
    ],
)
def test_events_registered(name: str) -> None:

    assert event_spine._EVENT_REGISTRY[name].__name__ == name
    assert name in event_spine._TYPE_HINTS


@pytest.mark.parametrize(
    'event',
    _ALL_EVENTS,
    ids=[type(e).__name__ for e in _ALL_EVENTS],
)
def test_event_constructs_cleanly(event: Event) -> None:

    assert event.command_id == _CMD
    assert event.protection_version == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'event',
    _ALL_EVENTS,
    ids=[type(e).__name__ for e in _ALL_EVENTS],
)
async def test_event_round_trips_through_spine(event: Event, spine: EventSpine) -> None:

    seq = await spine.append(event, epoch_id=_EPOCH)
    results = await spine.read(epoch_id=_EPOCH)
    assert len(results) == 1
    assert results[0][0] == seq
    hydrated = results[0][1]
    assert type(hydrated) is type(event)
    assert hydrated == event


@pytest.mark.parametrize(
    'event',
    _ALL_EVENTS,
    ids=[type(e).__name__ for e in _ALL_EVENTS],
)
def test_trading_state_no_ops_event(event: Event) -> None:

    state = TradingState(account_id=_ACCT)
    state.apply(event)
    assert state.orders == {}
    assert state.positions == {}


def test_amend_requested_rejects_empty_command_id() -> None:

    with pytest.raises(ValueError, match='command_id'):
        ProtectionAmendRequested(
            account_id=_ACCT, timestamp=_TS,
            command_id='', protection_version=1,
            new_list_client_order_id=_NEW_LIST,
            old_list_client_order_id=_OLD_LIST,
            take_profit_price=Decimal('52000.50'),
            stop_loss_price=Decimal('48000.00'),
        )


@pytest.mark.parametrize('version', [0, -1])
def test_amend_requested_rejects_non_positive_version(version: int) -> None:

    with pytest.raises(ValueError, match='protection_version'):
        ProtectionAmendRequested(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=version,
            new_list_client_order_id=_NEW_LIST,
            old_list_client_order_id=_OLD_LIST,
            take_profit_price=Decimal('52000.50'),
            stop_loss_price=Decimal('48000.00'),
        )


def test_amend_requested_rejects_bool_version() -> None:

    with pytest.raises(ValueError, match='protection_version'):
        ProtectionAmendRequested(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=True,
            new_list_client_order_id=_NEW_LIST,
            old_list_client_order_id=_OLD_LIST,
            take_profit_price=Decimal('52000.50'),
            stop_loss_price=Decimal('48000.00'),
        )


def test_amend_requested_rejects_same_list_id() -> None:

    with pytest.raises(ValueError, match='must differ'):
        ProtectionAmendRequested(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=1,
            new_list_client_order_id=_NEW_LIST,
            old_list_client_order_id=_NEW_LIST,
            take_profit_price=Decimal('52000.50'),
            stop_loss_price=Decimal('48000.00'),
        )


def test_amend_requested_allows_stop_market_stop_loss() -> None:

    event = ProtectionAmendRequested(
        account_id=_ACCT, timestamp=_TS,
        command_id=_CMD, protection_version=1,
        new_list_client_order_id=_NEW_LIST,
        old_list_client_order_id=_OLD_LIST,
        take_profit_price=Decimal('52000.50'),
        stop_loss_price=Decimal('48000.00'),
    )

    assert event.stop_loss_limit_price is None


@pytest.mark.parametrize('price', [Decimal('0'), Decimal('-1'), Decimal('NaN')])
def test_amend_requested_rejects_non_positive_take_profit_price(price: Decimal) -> None:

    with pytest.raises(ValueError, match='take_profit_price'):
        ProtectionAmendRequested(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=1,
            new_list_client_order_id=_NEW_LIST,
            old_list_client_order_id=_OLD_LIST,
            take_profit_price=price,
            stop_loss_price=Decimal('48000.00'),
        )


@pytest.mark.parametrize('price', [Decimal('0'), Decimal('-1'), Decimal('NaN')])
def test_amend_requested_rejects_non_positive_stop_loss_price(price: Decimal) -> None:

    with pytest.raises(ValueError, match='stop_loss_price'):
        ProtectionAmendRequested(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=1,
            new_list_client_order_id=_NEW_LIST,
            old_list_client_order_id=_OLD_LIST,
            take_profit_price=Decimal('52000.50'),
            stop_loss_price=price,
        )


def test_cancel_confirmed_rejects_zero_version() -> None:

    with pytest.raises(ValueError, match='protection_version'):
        ProtectionCancelConfirmed(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=0,
        )


def test_state_unknown_rejects_empty_reason() -> None:

    with pytest.raises(ValueError, match='reason'):
        ProtectionStateUnknown(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=1, reason='',
        )


def test_replace_submitted_rejects_empty_list_id() -> None:

    with pytest.raises(ValueError, match='new_list_client_order_id'):
        ProtectionReplaceSubmitted(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=1,
            new_list_client_order_id='',
        )


def test_active_rejects_bool_version() -> None:

    with pytest.raises(ValueError, match='protection_version'):
        ProtectionActive(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=False,
            new_list_client_order_id=_NEW_LIST,
        )


def test_failed_rejects_empty_reason() -> None:

    with pytest.raises(ValueError, match='reason'):
        ProtectionFailed(
            account_id=_ACCT, timestamp=_TS,
            command_id=_CMD, protection_version=1, reason='',
        )


def test_bracket_protection_status_values() -> None:

    assert BracketProtectionStatus.ACTIVE.value == 'ACTIVE'
    assert BracketProtectionStatus.AMEND_REQUESTED.value == 'AMEND_REQUESTED'
    assert BracketProtectionStatus.CANCEL_CONFIRMED.value == 'CANCEL_CONFIRMED'
    assert BracketProtectionStatus.STATE_UNKNOWN.value == 'STATE_UNKNOWN'
    assert BracketProtectionStatus.REPLACE_SUBMITTED.value == 'REPLACE_SUBMITTED'
    assert BracketProtectionStatus.FAILED.value == 'FAILED'
