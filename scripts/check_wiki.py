'''Validate the wiki's structural claims.

Checks only what a machine can decide. Whether an article is true, and
whether the register missed a behaviour, stay with the reviewer.
'''

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path

WIKI = Path('docs/wiki')
REGISTER = WIKI / 'register.md'
STAMP = re.compile(
    r'Created (\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC) · '
    r'Last modified (\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)',
)
META_STAMP = re.compile(
    r'^created: (\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)$.*?'
    r'^modified: (\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)$',
    re.MULTILINE | re.DOTALL,
)
ROW_ID = re.compile(r'\bP\d+-\d{2}\b')
BANNED_HEADINGS = ('## What it is', '## Overview', '## Introduction')
NEGATIVE_DEF = re.compile(r',\s+not\s+(?:a|an|the|yet|by|its|one)\b', re.IGNORECASE)
DOUBLE_NEGATIVE = re.compile(
    r"\b(?:not|never|n't)\b[^.;:]{0,40}\b(?:nothing|no one|nobody|never|none)\b",
    re.IGNORECASE,
)
APPARATUS = ('## Evidence', '| Claim | Source |')
OWNED_TERMS = {
    'what-a-trade-is.md': ('trade name', 'request name'),
    'how-waiting-work-is-drained.md': ("account's worker", 'priority line'),
    'how-a-trade-is-cancelled.md': ('cancellation',),
    'how-an-order-is-placed.md': ('submitted work',),
    'how-the-likely-price-is-checked.md': ('likely price',),
    'how-the-likely-price-is-worked-out.md': ('order book',),
}
LINE_REF = re.compile(r'\b(\d{2,5})(?:-(\d{2,5}))?\b')
FILE_REF = re.compile(r'`([A-Za-z_][A-Za-z0-9_/]*\.py)`')
LINK_ONLY = re.compile(r'-\s*\[[^]]+\]\([^)]+\.md\)')
SOURCE_FILES = {
    'execution_manager': Path('praxis/core/execution_manager.py'),
    'trading_state': Path('praxis/core/trading_state.py'),
    'praxis/trading.py': Path('praxis/trading.py'),
    'launcher': Path('praxis/launcher.py'),
    'validate_trade_abort': Path('praxis/core/validate_trade_abort.py'),
    'action_submit': Path('../Nexus/nexus/strategy/action_submit.py'),
    'praxis_outbound': Path(
        '../Nexus/nexus/infrastructure/praxis_connector/praxis_outbound.py',
    ),
    'order_reject': Path(
        '../Nexus/nexus/core/capital_controller/capital_controller.py',
    ),
    'capital_controller': Path(
        '../Nexus/nexus/core/capital_controller/capital_controller.py',
    ),
}
DEFAULT_SOURCE = 'execution_manager'
PROSE_WORD_CAP = 300
_MAX_SPAN = 60
GIT = shutil.which('git')


def _docstring_lines(path: Path) -> set[int]:

    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return set()

    lines: set[int] = set()

    for node in ast.walk(tree):
        body = getattr(node, 'body', None)

        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ) or not body:
            continue

        first = body[0]

        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))

    return lines


def _claims_alternatives(row: str) -> bool:

    lowered = row.lower()

    return any(
        word in lowered
        for word in (
            'need not', 'instead', 'rather than', 'either', 'otherwise',
            'not both', 'alternative', 'unless',
        )
    )


def _exclusive_spans(path: Path) -> list[tuple[set[int], set[int]]]:

    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return []

    ends = {
        node.lineno: node.end_lineno or node.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    pairs: list[tuple[set[int], set[int]]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and len(node.handlers) > 1:
            spans = [
                set(range(h.lineno, (h.body[-1].end_lineno or h.lineno) + 1))
                for h in node.handlers
                if h.body
            ]
            pairs.extend(
                (spans[i], spans[j])
                for i in range(len(spans))
                for j in range(i + 1, len(spans))
            )

        if not isinstance(node, ast.If) or not node.body:
            continue

        body = set(range(node.lineno, (node.body[-1].end_lineno or 0) + 1))

        if node.orelse:
            other = set(
                range(node.orelse[0].lineno, (node.orelse[-1].end_lineno or 0) + 1),
            )
            pairs.append((body, other))
            continue

        if not isinstance(node.body[-1], (ast.Return, ast.Raise, ast.Continue)):
            continue

        stop = max(
            (end for start, end in ends.items() if start <= node.lineno <= end),
            default=0,
        )
        after = set(range((node.end_lineno or node.lineno) + 1, stop + 1))

        if after:
            pairs.append((body, after))

    return pairs


def _exclusive_citations(starts: list[tuple[str, int]], cache: dict) -> str | None:

    for i, (key, a) in enumerate(starts):
        for other_key, b in starts[i + 1:]:
            if other_key != key:
                continue

            for first, second in cache[f'{key}#exc']:
                if (a in first and b in second) or (a in second and b in first):
                    return f'{key}:{a} and {b} are mutually exclusive branches'

    return None


def _resolve_source(name: str) -> Path | None:

    if name in SOURCE_FILES:
        return SOURCE_FILES[name]

    stem = name[:-3] if name.endswith('.py') else name

    for root in (Path('praxis'), Path('../Nexus/nexus'), Path('scripts')):
        if not root.is_dir():
            continue

        found = sorted(root.rglob(f'{stem}.py'))

        if len(found) == 1:
            return found[0]

        if found:
            return None

    return None


def _row_sources(row: str) -> list[tuple[int, str]]:

    hits = [
        (m.start(), key)
        for key in SOURCE_FILES
        for m in re.finditer(re.escape(key), row)
    ]
    hits += [(m.start(), m.group(1)) for m in FILE_REF.finditer(row)]

    return sorted(hits)


def _signature_lines(path: Path) -> set[int]:

    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return set()

    lines: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        if not node.body:
            continue

        lines.update(range(node.lineno, node.body[0].lineno))

    return lines


def _prose_words(text: str) -> int:

    words = 0

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith(('|', '---')):
            continue

        if stripped.startswith('#'):
            words += len(stripped.lstrip('# ').split())
            continue

        if stripped.startswith('Created ') and 'Last modified' in stripped:
            continue

        if LINK_ONLY.fullmatch(stripped):
            continue

        words += len(stripped.split())

    return words


def _claims_a_message(row: str) -> bool:

    lowered = row.lower()

    return any(word in lowered for word in ('log line', 'warning', 'logged', 'message'))


def _log_lines(path: Path) -> set[int]:

    lines: set[int] = set()

    try:
        source = path.read_text().splitlines()
    except OSError:
        return lines

    for number, line in enumerate(source, 1):
        if line.strip().startswith('_log.'):
            lines.add(number)

    return lines


def _docstring_citations(text: str, cache: dict[str, set[int]]) -> list[str]:

    bad: list[str] = []

    for row in text.splitlines():
        if not row.startswith('|'):
            continue

        sources = _row_sources(row)
        starts: list[tuple[str, int]] = []

        for match in LINE_REF.finditer(row):
            before = [key for pos, key in sources if pos < match.start()]
            key = before[-1] if before else DEFAULT_SOURCE
            path = _resolve_source(key)

            if path is None or not path.exists():
                bad.append(f'{key}:{match.group(0)} (unresolved source file)')
                continue

            if f'{key}#len' not in cache:
                cache[f'{key}#len'] = len(path.read_text().splitlines())

            if int(match.group(2) or match.group(1)) > cache[f'{key}#len']:
                bad.append(
                    f'{key}:{match.group(0)} (past end of file, '
                    f'{cache[f"{key}#len"]} lines)',
                )
                continue

            if key not in cache:
                cache[key] = _docstring_lines(path)
                cache[f'{key}#log'] = _log_lines(path)
                cache[f'{key}#sig'] = _signature_lines(path)
            cache[f'{key}#exc'] = _exclusive_spans(path)

            known = cache[key]
            logs = cache[f'{key}#log']
            sigs = cache[f'{key}#sig']
            start = int(match.group(1))
            starts.append((key, start))
            end = int(match.group(2) or start)
            span = list(range(start, min(end, start + _MAX_SPAN) + 1))
            inside = [n for n in span if n in known]

            if start in known or (inside and len(inside) * 2 > len(span)):
                bad.append(f'{key}:{match.group(0)} (docstring)')

            elif start in logs and not _claims_a_message(row):
                bad.append(f'{key}:{match.group(0)} (log call)')

            elif all(n in sigs for n in span):
                bad.append(f'{key}:{match.group(0)} (signature only)')

        clash = _exclusive_citations(starts, cache)

        if clash is not None and not _claims_alternatives(row):
            bad.append(clash)

    return bad


def _write(line: str) -> None:

    sys.stdout.write(f'{line}\n')


def _register_ids() -> set[str]:

    if not REGISTER.exists():
        return set()

    return set(ROW_ID.findall(REGISTER.read_text()))


def _last_commit_date(path: Path) -> str | None:

    if GIT is None:
        return None

    result = subprocess.run(  # noqa: S603
        [
            GIT,
            'log',
            '-1',
            '--format=%cd',
            '--date=format-local:%Y-%m-%d',
            '--',
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={'TZ': 'UTC'},
    )

    return result.stdout.strip() or None


def _negative_definitions(body: str) -> list[str]:

    found: list[str] = []

    for line in body.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith('#'):
            continue

        prose = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', stripped)

        found.extend(
            f'defines by negation: "{m.group(0).strip()}"'
            for m in NEGATIVE_DEF.finditer(prose)
        )
        found.extend(
            f'double negative: "{m.group(0).strip()}"'
            for m in DOUBLE_NEGATIVE.finditer(prose)
        )

    return found


def _lead_paragraph(body: str) -> str | None:

    lines = body.splitlines()

    try:
        start = next(i for i, line in enumerate(lines) if line.startswith('# '))
    except StopIteration:
        return None

    for line in lines[start + 1:]:
        stripped = line.strip()

        if not stripped:
            continue

        return None if stripped.startswith('#') else stripped

    return None


def _unlinked_terms(page: Path, body: str) -> list[str]:

    lowered = body.lower()
    missing: list[str] = []

    for owner, terms in OWNED_TERMS.items():
        if owner == page.name or f'({owner})' in body:
            continue

        missing.extend(
            f'mentions "{term}" without linking {owner}'
            for term in terms
            if term.lower() in lowered
        )

    return missing


def _split_front_matter(text: str) -> tuple[str, str]:

    if not text.startswith('---\n'):
        return '', text

    end = text.find('\n---\n', 4)

    if end == -1:
        return '', text

    return text[4:end], text[end + 5:]


def _evidence_rows(meta: str) -> list[str]:

    rows: list[str] = []

    for line in meta.splitlines():
        stripped = line.strip()

        if stripped.startswith('- claim:'):
            rows.append(stripped[len('- claim:'):].strip().strip('"'))

        elif stripped.startswith('source:') and rows:
            rows[-1] += ' | ' + stripped[len('source:'):].strip().strip('"')

    return rows


def _check_page(
    page: Path,
    ids: set[str],
    cache: dict[str, set[int]],
) -> list[str]:

    text = page.read_text()
    rel = page.as_posix()
    failures: list[str] = []
    meta, body = _split_front_matter(text)
    stamp = META_STAMP.search(meta) if meta else STAMP.search(text)

    if stamp is None:
        failures.append(f'{rel}: missing or malformed UTC timestamps')
    else:
        committed = _last_commit_date(page)

        if committed is not None and not stamp.group(2).startswith(committed):
            failures.append(
                f'{rel}: last modified {stamp.group(2)} disagrees with '
                f'last commit {committed}',
            )

    if page.parent.name != 'atoms':
        return failures

    if not meta:
        failures.append(f'{rel}: has no metadata block; evidence belongs there')

    lead = _lead_paragraph(body)

    if lead is None:
        failures.append(
            f'{rel}: no lead paragraph; the title must be followed by a sentence '
            'defining the subject, not a heading',
        )

    elif lead.startswith('**') or ' is about ' in lead or lead.startswith('This '):
        failures.append(f'{rel}: lead does not open by defining the subject: "{lead[:60]}"')

    for banned in BANNED_HEADINGS:
        if banned in body:
            failures.append(f'{rel}: "{banned}" is a prompt, not a section heading')

    for part in APPARATUS:
        if part in body:
            failures.append(
                f'{rel}: "{part}" is in the article; apparatus belongs in metadata',
            )

    rows = _evidence_rows(meta)

    if not rows:
        failures.append(f'{rel}: metadata carries no evidence')

    failures.extend(f'{rel}: {note}' for note in _unlinked_terms(page, body))
    failures.extend(f'{rel}: {note}' for note in _negative_definitions(body))

    words = _prose_words(body)

    if words > PROSE_WORD_CAP:
        failures.append(
            f'{rel}: {words} words of prose exceeds the {PROSE_WORD_CAP} cap; split it',
        )

    claimed = ROW_ID.findall(meta)

    if not claimed:
        failures.append(f'{rel}: claims no register row')

    failures.extend(
        f'{rel}: claims unknown register row {row}'
        for row in claimed
        if row not in ids
    )
    failures.extend(
        f'{rel}: evidence cites prose, not code, at {ref}'
        for ref in _docstring_citations('\n'.join(f'|{row}|' for row in rows), cache)
    )

    return failures


def main() -> int:

    '''Check every wiki page and report structural failures.'''

    pages = sorted(WIKI.rglob('*.md'))
    ids = _register_ids()
    cache: dict[str, set[int]] = {}
    failures = [f for page in pages for f in _check_page(page, ids, cache)]

    for failure in failures:
        _write(f'FAIL {failure}')

    if failures:
        _write(f'{len(failures)} problem(s).')

        return 1

    _write(f'ok: {len(pages)} page(s), {len(ids)} register row(s)')

    return 0


if __name__ == '__main__':
    sys.exit(main())
