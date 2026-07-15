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

from praxis.infrastructure.venue_adapter import VenueAdapter, VenueTrade

__all__ = ['paginate_my_trades']

_log = logging.getLogger(__name__)

_PAGE_LIMIT = 1000
_MAX_PAGES = 50


async def paginate_my_trades(
    adapter: VenueAdapter,
    account_id: str,
    symbol: str,
    *,
    from_id: int | None = None,
    page_limit: int = _PAGE_LIMIT,
    max_pages: int = _MAX_PAGES,
) -> tuple[list[VenueTrade], bool]:

    '''
    Paginate myTrades from a cursor.

    Args:
        adapter (VenueAdapter): Venue adapter exposing query_trades.
        account_id (str): Account identifier.
        symbol (str): Trading pair symbol.
        from_id (int | None): Inclusive starting trade id (the cursor);
            None starts from the venue's most recent trades.
        page_limit (int): Trades per page (venue max 1000).
        max_pages (int): Page cap; on reaching it the pass returns
            incomplete rather than looping unbounded.

    Returns:
        tuple[list[VenueTrade], bool]: Collected trades, and True when the
        stream was fully drained (False when the page cap truncated the
        pass, in which case a WARNING is logged).
    '''

    collected: list[VenueTrade] = []
    cursor = from_id

    for _ in range(max_pages):
        page = await adapter.query_trades(
            account_id, symbol, from_id=cursor, limit=page_limit,
        )
        if not page:
            return collected, True

        collected.extend(page)

        if len(page) < page_limit:
            return collected, True

        cursor = max(int(trade.venue_trade_id) for trade in page) + 1

    _log.warning(
        'myTrades backfill hit the page cap; pass incomplete',
        extra={'account_id': account_id, 'symbol': symbol, 'max_pages': max_pages},
    )

    return collected, False
