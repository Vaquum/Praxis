'''Minimal alert routing: a structured log line plus an optional webhook.

Emits one greppable `ALERT` log line per event (the reliable routing
primitive an external log pipeline pages on) and, when a webhook is
configured, best-effort POSTs the same payload. A webhook failure is
logged and never propagates, so alerting can never break trading.
'''

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

__all__ = ['AlertSink']

_log = logging.getLogger(__name__)

_SEVERITIES = frozenset({'info', 'warning', 'critical'})


class AlertSink:
    '''Route operational alerts to a structured log line and an optional webhook.

    Args:
        webhook_url: Destination for the optional POST, or `None` to log only.
        post: Async `(url, payload) -> None` used to deliver the webhook;
            injected so callers own the HTTP client and tests can stub it.
    '''

    def __init__(
        self,
        webhook_url: str | None = None,
        post: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._post = post

    def alert(self, event: str, severity: str = 'warning', **detail: Any) -> str:
        '''Emit a structured alert log line. Safe from any thread.

        Returns:
            The severity actually used, normalised to `warning` when the
            argument is not a known severity.
        '''

        if severity not in _SEVERITIES:
            severity = 'warning'

        _log.warning('ALERT event=%s severity=%s detail=%s', event, severity, json.dumps(detail, default=str))

        return severity

    async def notify(self, event: str, severity: str = 'warning', **detail: Any) -> None:
        '''Log the alert and best-effort POST it to the webhook when configured.'''

        severity = self.alert(event, severity, **detail)

        if self._webhook_url is None or self._post is None:
            return

        payload = json.loads(
            json.dumps({'event': event, 'severity': severity, **detail}, default=str),
        )

        try:
            await self._post(self._webhook_url, payload)
        except Exception:  # noqa: BLE001 - alerting must never break the caller
            _log.exception('alert webhook failed: event=%s', event)
