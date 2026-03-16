from __future__ import annotations

from collections.abc import AsyncGenerator

import aiosqlite
import pytest_asyncio

from praxis.infrastructure.event_spine import EventSpine


@pytest_asyncio.fixture
async def spine() -> AsyncGenerator[EventSpine, None]:
    conn = await aiosqlite.connect(':memory:')
    es = EventSpine(conn)
    await es.ensure_schema()
    yield es
    await conn.close()
