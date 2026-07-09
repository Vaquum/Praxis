'''Tests for the AlertSink.'''

from __future__ import annotations

import logging
from typing import Any

import pytest

from praxis.infrastructure.alert_sink import AlertSink


def test_alert_emits_structured_log_line(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        AlertSink().alert('mode_halted', severity='critical', account_id='a1')

    assert any(
        'ALERT event=mode_halted' in record.message and 'severity=critical' in record.message
        for record in caplog.records
    )


def test_invalid_severity_coerced_to_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        AlertSink().alert('x', severity='bogus')

    assert any('severity=warning' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_notify_posts_to_webhook() -> None:
    posted: list[tuple[str, dict[str, Any]]] = []

    async def post(url: str, payload: dict[str, Any]) -> None:
        posted.append((url, payload))

    sink = AlertSink(webhook_url='http://hook', post=post)
    await sink.notify('breaker_tripped', severity='critical', account_id='a1')

    assert posted == [
        ('http://hook', {'event': 'breaker_tripped', 'severity': 'critical', 'account_id': 'a1'}),
    ]


@pytest.mark.asyncio
async def test_notify_log_only_without_webhook(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        await AlertSink().notify('x')

    assert any('ALERT event=x' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_notify_swallows_webhook_failure(caplog: pytest.LogCaptureFixture) -> None:
    async def post(_url: str, _payload: dict[str, Any]) -> None:
        raise RuntimeError('hook down')

    sink = AlertSink(webhook_url='http://hook', post=post)

    with caplog.at_level(logging.WARNING):
        await sink.notify('x')

    assert any('alert webhook failed' in record.message for record in caplog.records)
