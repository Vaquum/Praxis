'''Tests for Launcher JSON log format (Render.5).

Runs the launcher entrypoint's logging setup in a subprocess so that
configure_logging can mutate the root logger without leaking into
other tests.
'''

from __future__ import annotations

import json
import subprocess
import sys


_JSON_LOGGING_SCRIPT = '''
import logging
from praxis.infrastructure.observability import bind_context, configure_logging

configure_logging(log_level="INFO")
bind_context(epoch_id=42)

log = logging.getLogger("praxis.launcher")
log.info("launching praxis", extra={"accounts": ["acct-001"]})
'''

_TEXT_LOGGING_SCRIPT = '''
import logging

logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("praxis.launcher")
log.info("launching praxis")
'''


def _run(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - test-controlled args
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        check=True,
    )


class TestJsonLogging:

    def test_json_format_is_parseable(self) -> None:
        '''Each stdout line parses as JSON with expected keys.'''

        result = _run(_JSON_LOGGING_SCRIPT)
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        assert lines, f'no stdout output: stderr={result.stderr!r}'

        for line in lines:
            record = json.loads(line)
            assert 'event' in record
            assert 'timestamp' in record
            assert 'level' in record

    def test_json_format_includes_bound_context(self) -> None:
        '''bind_context fields appear on every record.'''

        result = _run(_JSON_LOGGING_SCRIPT)
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        records = [json.loads(ln) for ln in lines]
        launching = [r for r in records if r.get('event') == 'launching praxis']
        assert launching, f'launching record not emitted: {records}'
        assert launching[0]['epoch_id'] == 42

    def test_text_format_is_not_json(self) -> None:
        '''LOG_FORMAT=text (default stdlib) is human-readable, not JSON.'''

        result = _run(_TEXT_LOGGING_SCRIPT)
        stderr_lines = [
            ln for ln in result.stderr.splitlines() if 'launching praxis' in ln
        ]
        assert stderr_lines

        for line in stderr_lines:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                pass
            else:
                msg = f'text log line unexpectedly parsed as JSON: {line!r}'
                raise AssertionError(msg)
