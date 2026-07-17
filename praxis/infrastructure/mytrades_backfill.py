'''
Paginated Binance myTrades backfill.

Loop the venue `query_trades` endpoint from a REST cursor, advancing
`fromId` page by page until a short page drains the stream or a page cap
bounds the pass. The first page re-fetches the cursor inclusively so a
reconnect overlaps by one trade — the Event Spine dedup absorbs the
boundary — while later pages advance exclusively to avoid re-fetching.
'''

from __future__ import annotations

import logging
from datetime import datetime

from praxis.infrastructure.venue_adapter import VenueAdapter, VenueTrade

__all__ = ['paginate_my_trades', 'venue_trade_id_int']

_log = logging.getLogger(__name__)

_PAGE_LIMIT = 1000
_MAX_PAGES = 50


def venue_trade_id_int(venue_trade_id: str) -> int | None:

    '''
    Parse a venue trade id to int, returning None when it is not numeric.

    Args:
        venue_trade_id (str): The venue-assigned trade id.

    Returns:
        int | None: The integer id, or None if non-numeric.
    '''

    try:
        return int(venue_trade_id)
    except ValueError:
        return None


async def paginate_my_trades(
    adapter: VenueAdapter,
    account_id: str,
    symbol: str,
    *,
    from_id: int | None = None,
    start_time: datetime | None = None,
    page_limit: int = _PAGE_LIMIT,
    max_pages: int = _MAX_PAGES,
) -> tuple[list[VenueTrade], bool]:

    '''
    Paginate myTrades from a cursor, or from a bootstrap time window.

    The first page queries by `from_id` (the durable cursor, inclusive) or,
    when there is no cursor, by `start_time`; subsequent pages always
    advance by `from_id = max(page) + 1`.

    Args:
        adapter (VenueAdapter): Venue adapter exposing query_trades.
        account_id (str): Account identifier.
        symbol (str): Trading pair symbol.
        from_id (int | None): Inclusive starting trade id (the cursor).
        start_time (datetime | None): Bootstrap window start, used only for
            the first page when from_id is None.
        page_limit (int): Trades per page (venue max 1000).
        max_pages (int): Page cap; on reaching it the pass returns
            incomplete rather than looping unbounded.

    Returns:
        tuple[list[VenueTrade], bool]: Collected trades, and True when the
        stream was fully drained (False when the page cap or a non-numeric
        page boundary truncated the pass, in which case a WARNING is logged).
    '''

    collected: list[VenueTrade] = []
    cursor = from_id

    for _ in range(max_pages):
        if cursor is not None:
            page = await adapter.query_trades(
                account_id, symbol, from_id=cursor, limit=page_limit,
            )
        else:
            page = await adapter.query_trades(
                account_id, symbol, start_time=start_time, limit=page_limit,
            )

        if not page:
            return collected, True

        collected.extend(page)

        if len(page) < page_limit:
            return collected, True

        page_ids = [
            parsed
            for trade in page
            if (parsed := venue_trade_id_int(trade.venue_trade_id)) is not None
        ]
        if not page_ids:
            _log.warning(
                'myTrades page has no numeric trade ids; cannot advance cursor',
                extra={'account_id': account_id, 'symbol': symbol},
            )
            return collected, False

        cursor = max(page_ids) + 1

    _log.warning(
        'myTrades backfill hit the page cap; pass incomplete',
        extra={'account_id': account_id, 'symbol': symbol, 'max_pages': max_pages},
    )

    return collected, False
