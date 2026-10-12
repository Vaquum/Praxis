'''Validate the wiki's structural claims.

Checks only what a machine can decide. Whether an article is true, and
whether the register missed a behaviour, stay with the reviewer.
'''

from __future__ import annotations

import ast
import builtins
import bisect
import functools
import itertools
import operator
import re
import shutil
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterable
import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ['main']

WIKI = Path('docs/wiki')
REGISTER = WIKI / 'register.md'
README = WIKI / 'README.md'
UNCHECKED = 'unchecked'
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
COMMIT_ID = re.compile(r'[0-9a-f]{7,40}')
ROW_OPENING = re.compile(r'^\|\s*(P\d+-\d{2})\s*\|', re.MULTILINE)
BANNED_HEADINGS = ('## What it is', '## Overview', '## Introduction')
NEGATIVE_DEF = re.compile(r',\s+not\s+(?:a|an|the|yet|by|its|one)\b', re.IGNORECASE)
DOUBLE_NEGATIVE = re.compile(
    r'(?:\bnot\b|\bnever\b|n[\'\u2019]t\b)'
    r'[^.;:]{0,40}\b(?:nothing|no one|nobody|never|none)\b',
    re.IGNORECASE,
)
HEADING_NEGATION = re.compile(r',\s+not\b', re.IGNORECASE)
def _held_among(left: Any, right: Any) -> bool:

    """Whether the left stands among the right.

    Args:
        left (Any): What to look for.
        right (Any): What to look in.

    Returns:
        bool: True where it is there.
    """

    return left in right


def _held_apart(left: Any, right: Any) -> bool:

    """Whether the left stands outside the right.

    Args:
        left (Any): What to look for.
        right (Any): What to look in.

    Returns:
        bool: True where it is not there.
    """

    return left not in right


_COMPARISONS: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: _held_among,
    ast.NotIn: _held_apart,
}
_BUILT_WITH = 3
_LINE_DIGITS = 9
_ROWS_AT_MOST = 1000
_PAST_EVERY_FILE: int = 10 ** _LINE_DIGITS
_GROUPED_ERRORS = ('ExceptionGroup', 'BaseExceptionGroup')
_CARRIES_ON = 'carries on'
_GONE_OVER = (str, bytes, list, tuple, set, frozenset, dict)
_ENDLESS = 'endless'
_RAISE = 'raise'
_KNOWN_ERRORS = frozenset(
    name for name, held in vars(builtins).items()
    if isinstance(held, type) and issubclass(held, BaseException)
)
_COVERED_BY = {
    name: frozenset(
        under for under, each in vars(builtins).items()
        if isinstance(each, type) and issubclass(each, held)
    )
    for name, held in vars(builtins).items()
    if isinstance(held, type) and issubclass(held, BaseException)
}
APPARATUS = ('## Evidence', '| Claim | Source |')
CODE_LABEL = re.compile(r'`([^`]+)`')
RATIONALE = re.compile(
    r'\b(to allow for|in order to|for the sake of|by design|deliberately so|'
    r'the reason being|precisely so|the point being|the idea being)\b',
    re.IGNORECASE,
)
_HOLDERS = (
    ast.If, ast.Try, ast.TryStar, ast.With, ast.AsyncWith,
    ast.For, ast.AsyncFor, ast.While, ast.Match,
)
OWNED_TERMS = {
    'what-a-trade-is.md': ('trade name', 'request name'),
    'how-waiting-work-is-drained.md': ('account\'s worker',),
    'the-priority-line.md': ('priority line',),
    'how-a-trade-is-cancelled.md': ('cancellation',),
    'how-an-order-is-placed.md': ('submitted work',),
    'how-the-likely-price-is-checked.md': ('likely-price check',),
    'the-order-book.md': ('order book',),
}
LINE_REF = re.compile(r'(?<![-\w.])(\d+)(?:-(\d+))?\b')
FILE_REF = re.compile(r'`([A-Za-z_][A-Za-z0-9_/]*\.py)`')
LINK_ONLY = re.compile(r'-\s*\[[^]]+\]\([^)]+\.md\)')
_TITLE = (
    r'(?:\s+(?:"(?:[^"\\]|\\.)*"'
    r"|'(?:[^'\\]|\\.)*'"
    r'|\((?:[^)\\]|\\.)*\)))?'
)
MD_LINK = re.compile(r'\]\(\s*<?([^)\s>]+)>?' + _TITLE + r'\s*\)')
REF_LINK = re.compile(r'\[([^\]]+)\]\[([^\]]*)\]')
REF_SHORTCUT = re.compile(r'\[([^\]]+)\](?![(\[])')
REF_DEF = re.compile(r'^ {0,3}\[([^\]]+)\]:\s*<?([^\s>]+)>?', re.MULTILINE)
HEADING = re.compile(r'^#{1,6}\s+(.+?)\s*$', re.MULTILINE)
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
PROSE_WORD_CAP = 300
BASELINE = '49aa659'
NEXUS_ROOT = Path('../Nexus')
NEXUS_BASELINE = '953477a'
CREATED_RE = re.compile(r'^created:\s*(.+?)\s*$', re.MULTILINE)
SEARCH_PREFIXES = ('praxis/', 'nexus/', 'scripts/', 'tests/')
LEDGER = WIKI / 'ledger.md'
LEDGER_PATH_RE = re.compile(r'`((?:praxis|nexus)/[^`]*\.py)`')
LEDGER_HEADING_RE = re.compile(r'^## (Praxis|Nexus) — (\d+) modules$', re.MULTILINE)
LEDGER_GROUP_RE = re.compile(r'^\| (?:all|the other) (\d+) \|', re.MULTILINE)
LEDGER_ROW_RE = re.compile(r'^\| `([^`]+)` \| (\w+) \| ([^|]*) \|$', re.MULTILINE)
REGISTER_ROW_RE = re.compile(r'^\|\s*(P\d+-\d{2})\s*\|[^|]*\|[^|]*\|[^(]*\((atoms/[^)]+)\)',
                             re.MULTILINE)
ROW_SPAN_RE = re.compile(r'^(P\d+)-(\d{2}) to P\d+-(\d{2})$')
STATE_COUNT_RE = re.compile(
    r'(\d+) are `full`, (\d+) `partial` and (\d+) `uncovered`',
)
ARTICLE_COUNT_RE = re.compile(r'(\d+) articles\b')
NEXUS_COUNT_RE = re.compile(r'(\d+) are cited in passing')
NEXUS_TOTAL_RE = re.compile(r'(?:the|its) (\d+) (?:in Nexus|modules)')
NEXUS_UNTOUCHED_RE = re.compile(r'(\d+) untouched')
CHANGELOG = Path('CHANGELOG.md')
RELEASE_RE = re.compile(r'^## v\d+\.\d+\.\d+', re.MULTILINE)
EVIDENCE_COUNT_RE = re.compile(r'(\d[\d,]*) line references across (\d[\d,]*) claims')
FINDING_COUNT_RE = re.compile(r'Record (\d[\d,]*) findings')
FINDING_ROW_RE = re.compile(r'^\| H-\d+ \|', re.MULTILINE)
ARTICLE_LINK_RE = re.compile(r'\((atoms/[a-z0-9-]+\.md)\)')
REFUSAL_RE = re.compile(
    r'\b(refus\w+|rejec\w+|turned away|forbidd\w+)\b', re.IGNORECASE,
)
UNRESOLVED_RE = re.compile(r'\bU-\d+\b')
PINNED_ROW_RE = re.compile(r'^\| (Praxis|Nexus) \| `([0-9a-f]{7,40})` \|', re.MULTILINE)
_SEVERAL = (
    r'two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    r'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|'
    r'twenty|twenty-one|thirty'
)
TEASED_COUNT_RE = re.compile(
    rf'\b(?:the (?:one|{_SEVERAL}) (?=[a-z])|(?:{_SEVERAL}) of\b)',
)
INDEX_ENTRY_RE = re.compile(
    r'^- \[[^]]*\]\(atoms/([a-z0-9-]+\.md)\) — (.*)$', re.MULTILINE,
)
FINDING_CELLS_RE = re.compile(r'^\| ([HU]-\d+) \|([^|]*)\|(.*)\|$', re.MULTILINE)
FINDING_ROW_CELLS_RE = re.compile(
    r'^\| ([HU]-\d+) \|[^|]*\|([^|]*)\|[^|]*\|([^|]*)\|', re.MULTILINE,
)
UNNAMED = 'cited with no file named before it'
LINE_COUNT_RE = re.compile(r'`([a-z_/]+\.py)`[,]? (?:is|at) (\d[\d,]*) lines')
_MARKER_REACH = 40
ABSENCE_WORDS = ('nothing further', 'nowhere', 'absent from', 'no such')
GIT = shutil.which('git')


@functools.cache
def _repo_root() -> Path | None:

    '''Return the repository root, or None where git cannot say.

    Returns:
        Path | None: The root directory, or None.
    '''

    if GIT is None:
        return None

    result = subprocess.run(  # noqa: S603
        [GIT, 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, check=False,
    )

    if result.returncode != 0:
        return None

    return Path(result.stdout.strip())


class BaselineReadError(OSError):

    '''A cited file could not be read at the baseline it is pinned to.'''


def _pins() -> list[tuple[Path, str]]:

    '''Return each pinned repository root with the commit it is pinned to.

    Returns:
        list[tuple[Path, str]]: Root and commit, one per repository.
    '''

    roots = [(_repo_root(), BASELINE)]

    if NEXUS_ROOT.is_dir():
        roots.append((NEXUS_ROOT.resolve(), NEXUS_BASELINE))

    return [(root, commit) for root, commit in roots if root is not None]


def _pin(path: Path) -> tuple[Path, str, Path] | None:

    '''Return the deepest pinned repository containing `path`, and its commit.'''

    resolved = path.resolve()
    matches: list[tuple[Path, str, Path]] = []

    for root, commit in _pins():

        try:
            matches.append((root, commit, resolved.relative_to(root)))
        except ValueError:
            continue

    if not matches:
        return None

    return max(matches, key=lambda match: len(match[0].parts))


@functools.cache
def _pinned_paths(root: Path, commit: str) -> tuple[str, ...]:

    '''Return every path in a repository at one commit.

    Args:
        root (Path): The repository root to list.
        commit (str): The commit to list it at.

    Returns:
        tuple[str, ...]: The paths in that tree.
    '''

    if GIT is None:
        msg = 'git is unavailable, so no pinned tree can be listed'
        raise BaselineReadError(msg)

    result = subprocess.run(  # noqa: S603
        [GIT, 'ls-tree', '-r', '--name-only', commit],
        capture_output=True, text=True, check=False, cwd=root,
    )

    if result.returncode != 0:
        msg = f'{root}: cannot list the tree at {commit}'
        raise BaselineReadError(msg)

    return tuple(result.stdout.splitlines())


@functools.cache
def _source_text(path: Path) -> str:

    '''Return the file's content at the baseline its repository is pinned to.'''

    if GIT is None:
        msg = f'{path}: git is unavailable, so no baseline can be read'
        raise BaselineReadError(msg)

    pinned = _pin(path)

    if pinned is None:
        msg = f'{path}: lies outside every pinned repository'
        raise BaselineReadError(msg)

    root, commit, relative = pinned
    result = subprocess.run(  # noqa: S603
        [GIT, 'show', f'{commit}:{relative.as_posix()}'],
        capture_output=True, text=True, check=False, cwd=root,
    )

    if result.returncode != 0:
        msg = f'{path}: absent from {commit}'
        raise BaselineReadError(msg)

    return result.stdout


def _blank_lines(path: Path) -> set[int]:

    '''Return the lines of a file holding nothing but space.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers.
    '''

    return {
        number
        for number, line in enumerate(_source_text(path).splitlines(), 1)
        if not line.strip()
    }


def _comment_lines(path: Path) -> set[int]:

    '''Return the lines of a file holding nothing but a comment.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers.
    '''

    return {
        number
        for number, line in enumerate(_source_text(path).splitlines(), 1)
        if line.strip().startswith('#')
    }


def _docstring_lines(path: Path) -> set[int]:

    '''Return the lines of a file that sit inside a docstring.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers.
    '''

    try:
        tree = ast.parse(_source_text(path))
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


_METADATA_KEYS = ('row', 'baseline', 'created', 'modified', 'evidence')
_PARTING = ' | '
_SHOWS_NOTHING = frozenset({'Cc', 'Cf'})
_UNPRINTABLE = re.compile(
    '[^\t\x20-\x7e\x85\xa0-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]',
)
EVIDENCE_LINE = re.compile(
    r'^(  - claim: "[^"\\\x00-\x1f\x7f]*"'
    r'|    source: "[^"\\\x00-\x1f\x7f]*")$',
)
_REFERENCES_AT_MOST = 100
ALTERNATION_WORDS = (
    'or', 'either', 'otherwise', 'instead', 'rather than', 'unless',
    'against', 'need not', 'not both', 'alternative',
)


@dataclass(frozen=True)
class _RowMarks:

    '''Where one evidence row holds its citations and its marker words.

    Args:
        starts (tuple[int, ...]): Where each citation starts, in order.
        ends (tuple[int, ...]): Where each of those citations ends.
        marks (tuple[tuple[int, int], ...]): Each marker word's span.
    '''

    starts: tuple[int, ...]
    ends: tuple[int, ...]
    marks: tuple[tuple[int, int], ...]


@functools.cache
def _row_marks(source: str) -> _RowMarks:

    '''Read one row's citations and marker words, once for every pair.

    A row is asked about every pair of citations it carries, so reading
    it again for each pair would cost the cube of what it holds.

    Args:
        source (str): The source half of the evidence row.

    Returns:
        _RowMarks: Those positions.
    '''

    refs = list(LINE_REF.finditer(source))
    lowered = source.lower()
    marks = sorted(
        (match.start(), match.end())
        for word in ALTERNATION_WORDS
        for match in re.finditer(rf'\b{re.escape(word)}\b', lowered)
    )

    return _RowMarks(
        tuple(match.start() for match in refs),
        tuple(match.end() for match in refs),
        tuple(marks),
    )


def _marks_within(
    marks: tuple[tuple[int, int], ...], start: int, end: int,
) -> bool:

    '''Whether a marker word stands wholly inside one stretch.

    Args:
        marks (tuple[tuple[int, int], ...]): Each marker word's span.
        start (int): Where the stretch starts.
        end (int): Where it ends.

    Returns:
        bool: True where one of them lies inside it.
    '''

    at = bisect.bisect_left(marks, (start, start))

    return at < len(marks) and marks[at][1] <= end


def _marked_between(source: str, first: int, second: int) -> bool:

    '''Whether the row names the citations on either side as alternatives.

    The marker must sit between the two citations, or just before the
    earlier of them without reaching past the citation before that. A
    marker after the later one counts only where nothing is cited beyond
    it, since otherwise it belongs to the pair that follows — which is
    where an author writes `either X or Y`, or `X, Y otherwise`. A
    marker further off governs some other pair, so the stretch after the
    later citation is read only where no other citation lies there. A
    marker anywhere between the pair governs it, which is how a run of
    alternatives marks each pair it holds, and one standing before the
    row's first citation declares the whole row's list alternative.

    Between two citations of one file, `or` reads as alternation where
    `and` reads as sequence, so it counts as a marker there.

    Args:
        source (str): The source half of the evidence row.
        first (int): Where the earlier citation starts.
        second (int): Where the later one starts.

    Returns:
        bool: True where a marker governs this pair.
    '''

    low, high = sorted((first, second))
    held = _row_marks(source)
    opening = held.ends[bisect.bisect_left(held.starts, low)]
    first_ref = held.starts[0]

    if _marks_within(held.marks, opening, high) or _marks_within(
        held.marks, max(first_ref - _MARKER_REACH, 0), first_ref,
    ):
        return True

    if held.starts[-1] > high:
        return False

    closing = held.ends[bisect.bisect_right(held.starts, high) - 1]

    return _marks_within(held.marks, closing, closing + _MARKER_REACH)


@dataclass(frozen=True)
class _Block:

    '''A block that runs after a branch, and the construct holding both.

    Args:
        lines (frozenset[int]): The block's own lines.
        start (int): Where the construct holding it starts.
        end (int): Where that construct ends.
    '''

    lines: frozenset[int]
    start: int
    end: int

    def skipped_by(self, line: int) -> bool:

        '''Whether a branch on a line leaves this block unrun.

        Args:
            line (int): Where the branch sits.

        Returns:
            bool: True where the block does not run after it.
        '''

        return line not in range(self.start, self.end + 1) or line in self.lines


@dataclass(frozen=True)
class _Scopes:

    '''What a branch leaving the path skips, and what it cannot skip.

    Args:
        ends (dict[int, int]): Where each function starts and ends.
        loops (dict[int, int]): Where each loop starts and ends.
        tries (dict[int, int]): Where each handled block starts, and where
            what a raise in its body skips ends.
        helds (dict[int, int]): Where each `with` statement starts and ends.
        handlers (tuple[_Block, ...]): Every `except` body.
        settled (tuple[_Block, ...]): Every `try` statement's `else` body.
        overrides (tuple[tuple[_Block, str], ...]): Every `finally` that
            leaves, with the way it leaves, empty where it leaves by
            more than one way.
        regardless (tuple[_Block, ...]): Every `finally` body.
        after_a_loop (tuple[_Block, ...]): Every loop's `else` body.
        alone (frozenset[int]): Where each `with` starts that holds one
            manager, whose ending nothing of its own could swallow.
        cleaned (dict[int, int]): Where each `try` starts and ends whose
            `finally` could raise as it runs.
    '''

    ends: dict[int, int]
    loops: dict[int, int]
    tries: dict[int, int]
    helds: dict[int, int]
    handlers: tuple[_Block, ...]
    settled: tuple[_Block, ...]
    overrides: tuple[tuple[_Block, str], ...]
    regardless: tuple[_Block, ...]
    after_a_loop: tuple[_Block, ...]
    alone: frozenset[int]
    cleaned: dict[int, int]


_TAKEN_OVER: frozenset[str] = frozenset()


def _taken_over(tree: ast.AST) -> frozenset[str]:

    """Return the error names this file gives some other value.

    A plain name is read as the error the language carries under it,
    which holds only while the file has not bound that name itself. A
    parameter, an import, an assignment or a loop target of the same
    name leaves nothing weighable, so every such name is kept and the
    kind helpers abstain on it. A wildcard import could have brought
    any of those names, so a file holding one has all of them kept.

    Args:
        tree (ast.AST): The parsed file.

    Returns:
        frozenset[str]: Those names.
    """

    if _has_wildcard_import(tree):
        return _KNOWN_ERRORS

    return frozenset(_rebound_names(tree) & _KNOWN_ERRORS)


def _kind_named(held: ast.expr | None) -> str | None:

    """Return the kind a piece of a raise or a handler names, weighably.

    A kind is weighable where it is written as a plain name the file
    has not bound itself: an attribute, a call's result or a name the
    file gives some other value says nothing a handler can be matched
    against.

    Args:
        held (ast.expr | None): What was written, or nothing.

    Returns:
        str | None: That name, or None where nothing is weighable.
    """

    if not isinstance(held, ast.Name) or held.id in _TAKEN_OVER:
        return None

    return held.id


def _reading(tree: ast.AST) -> None:

    """Note which error names the file being read has taken over.

    Args:
        tree (ast.AST): The parsed file.
    """

    global _TAKEN_OVER  # noqa: PLW0603

    _TAKEN_OVER = _taken_over(tree)


def _exclusive_spans(path: Path) -> list[tuple[set[int], set[int]]]:

    '''Return pairs of line sets that cannot both run for one input.

    An arm with no line of its own — its whole body written on the line
    heading it — is an alternative to nothing, and is left out.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        list[tuple[set[int], set[int]]]: Each pair of arms.
    '''

    try:
        text = _source_text(path)
        tree = ast.parse(text)
    except (OSError, SyntaxError):
        return []

    _reading(tree)
    scopes = _scopes(tree, text.splitlines())
    pairs: list[tuple[set[int], set[int]]] = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.Try, ast.TryStar)):
            pairs.extend(_handler_arms(node))

        if isinstance(node, ast.Match):
            pairs.extend(_case_arms(node))

        if isinstance(node, ast.If) and node.body:
            pairs.extend(_branch_arms(node, scopes))

    return [(first, second) for first, second in pairs if first and second]


def _scopes(tree: ast.AST, lines: list[str]) -> _Scopes:

    '''Return what a branch leaving the path can and cannot skip.

    Args:
        tree (ast.AST): The parsed module.
        lines (list[str]): Its lines, read for the line heading a block.

    Returns:
        _Scopes: Where each kind of block ends, and the lines that run
            whatever a branch does.
    '''

    loops = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While))
    ]
    tries = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.Try, ast.TryStar))
    ]

    return _Scopes(
        ends=_spans_of(tree, (ast.FunctionDef, ast.AsyncFunctionDef)),
        loops={node.lineno: node.end_lineno or node.lineno for node in loops},
        tries={
            node.lineno: _skipped_by_a_raise(node)
            for node in tries if node.handlers and node.body
        },
        helds=_spans_of(tree, (ast.With, ast.AsyncWith)),
        handlers=_blocks(
            ((node, handler.body) for node in tries for handler in node.handlers),
            lines,
        ),
        settled=_blocks(((node, node.orelse) for node in tries), lines),
        regardless=_blocks(((node, node.finalbody) for node in tries), lines),
        overrides=tuple(
            (block, _one_leave(node.finalbody))
            for node in tries
            if node.finalbody and _can_leave(node.finalbody)
            for block in _blocks([(node, node.finalbody)], lines)
        ),
        after_a_loop=_blocks(((node, node.orelse) for node in loops), lines),
        alone=frozenset(
            node.lineno for node in ast.walk(tree)
            if isinstance(node, (ast.With, ast.AsyncWith)) and len(node.items) == 1
        ),
        cleaned={
            node.lineno: node.end_lineno or node.lineno
            for node in tries
            if node.finalbody and _may_raise(node.finalbody)
        },
    )


def _skipped_by_a_raise(node: ast.Try | ast.TryStar) -> int:

    '''Return where what a raise in a `try` body skips ends.

    A raise skips the rest of the body and the `else`, which runs only
    where the body came through. The handlers run, and are taken out
    separately.

    Args:
        node (ast.Try): The statement to read.

    Returns:
        int: That last line.
    '''

    last = node.orelse[-1] if node.orelse else node.body[-1]

    return last.end_lineno or node.lineno


def _spans_of(
    tree: ast.AST,
    kinds: tuple[type[ast.stmt], ...],
) -> dict[int, int]:

    '''Return where each statement of the given kinds starts and ends.

    Args:
        tree (ast.AST): The parsed module.
        kinds (tuple[type[ast.stmt], ...]): The statement types to find.

    Returns:
        dict[int, int]: First line to last, one entry per statement.
    '''

    return {
        node.lineno: node.end_lineno or node.lineno
        for node in ast.walk(tree)
        if isinstance(node, kinds)
    }


def _bare_comment(line: str) -> bool:

    '''Whether a line holds nothing but a comment.

    Args:
        line (str): The line to read.

    Returns:
        bool: True where it is blank or starts with a `#`.
    '''

    stripped = line.strip()

    return not stripped or stripped.startswith('#')


def _without_a_comment(line: str) -> str:

    '''Return a line's code, the comment on its end taken off.

    A `#` inside a string is left alone: the line is read letter by
    letter, and a quote is closed only by the same quote that opened
    it, so an apostrophe inside double quotes closes nothing. A
    backslash takes the letter after it with no meaning of its own.

    Args:
        line (str): The line to read.

    Returns:
        str: What is left, stripped.
    '''

    opened = ''
    escaped = False

    for position, letter in enumerate(line):

        if escaped:
            escaped = False
        elif letter == '\\':
            escaped = True
        elif opened:
            opened = '' if letter == opened else opened
        elif letter in '\'"':
            opened = letter
        elif letter == '#':
            return line[:position].strip()

    return line.strip()


def _blocks(
    found: Iterable[tuple[ast.stmt, list[ast.stmt]]],
    lines: list[str],
) -> tuple[_Block, ...]:

    '''Return each block with the construct that holds it.

    The line heading a block belongs to it, so citing `finally:` is not
    an alternative to anything. That line counts only where it holds
    the keyword alone; where the body starts on it, there is no line to
    take, and taking the one above would take a statement with it.

    Args:
        found (Iterable[tuple[ast.stmt, list[ast.stmt]]]): Each construct
            with the block hanging off it.
        lines (list[str]): The module's lines, read for the heading.

    Returns:
        tuple[_Block, ...]: One entry per block that has statements.
    '''

    return tuple(
        _Block(
            frozenset(range(_heading(body[0].lineno, lines), (body[-1].end_lineno or 0) + 1)),
            node.lineno,
            node.end_lineno or node.lineno,
        )
        for node, body in found if body
    )


def _heading(first: int, lines: list[str]) -> int:

    '''Return where a block starts, counting the line heading it.

    Args:
        first (int): The line its first statement starts on.
        lines (list[str]): The module's lines.

    Returns:
        int: That line, or the heading line above it where one heads
            the block, an `except` of its own among those headings.
            Comments between the two are passed over, and a comment
            on the heading itself is read past.
    '''

    number = first - 1

    while number > 1 and _bare_comment(lines[number - 1]):
        number -= 1

    above = _without_a_comment(lines[number - 1]) if number >= 1 else ''
    heads = above in ('finally:', 'else:') or (
        above.startswith(('except ', 'except:', 'except*')) and above.endswith(':')
    )

    return number if heads else first


def _handler_arms(node: ast.Try | ast.TryStar) -> list[tuple[set[int], set[int]]]:

    '''Return each pair of arms a `try` statement has.

    Two handler bodies cannot both run for one raise, and the `else`
    runs only where none of them did, so each pair of them is a pair
    of arms. The kind a handler catches is worked out while the later
    handlers are still candidates, so that line is left out. An `except*` is different: one exception group can carry
    several kinds and run several of those handlers, so only the
    `else` is an alternative to them.

    Args:
        node (ast.Try): The try statement to read.

    Returns:
        list[tuple[set[int], set[int]]]: Each pair of handler spans.
    '''

    spans = [
        _own_lines(h.body, _asked_of(h.type, h.lineno))
        for h in node.handlers
        if h.body
    ]
    settled = _else_lines(node)

    if isinstance(node, ast.TryStar):
        return [(span, settled) for span in spans] if settled else []

    if settled:
        spans.append(settled)

    return [
        (spans[i], spans[j])
        for i in range(len(spans))
        for j in range(i + 1, len(spans))
    ]


def _case_arms(node: ast.Match) -> list[tuple[set[int], set[int]]]:

    '''Return each pair of cases a `match` statement has.

    One value takes one case, so no two of their bodies run for one
    input. A pattern and a guard are tried until one matches, so those
    lines run on the paths of later cases too and are left out.

    Args:
        node (ast.Match): The statement to read.

    Returns:
        list[tuple[set[int], set[int]]]: Each pair of case spans.
    '''

    spans = [
        _own_lines(case.body, _asked_of(case.guard, _asked_of(case.pattern, 0)))
        for case in node.cases
        if case.body
    ]

    return [
        (spans[i], spans[j])
        for i in range(len(spans))
        for j in range(i + 1, len(spans))
    ]


def _else_lines(node: ast.Try | ast.TryStar) -> set[int]:

    '''Return the lines of a `try` statement's `else`, where it has one.

    Args:
        node (ast.Try): The `try` statement to read.

    Returns:
        set[int]: Those lines, or none where there is no `else`.
    '''

    if not node.orelse:
        return set()

    return set(range(node.orelse[0].lineno, (node.orelse[-1].end_lineno or 0) + 1))


def _asked_of(held: ast.expr | ast.pattern | None, default: int) -> int:

    '''Return the last line what a heading asks for reaches.

    Args:
        held (ast.expr | ast.pattern | None): What the heading asks
            for, or nothing where it asks for nothing.
        default (int): The line to answer with where it asks nothing.

    Returns:
        int: That line.
    '''

    if held is None:
        return default

    return held.end_lineno or held.lineno


def _own_lines(body: list[ast.stmt], header: int) -> set[int]:

    '''Return the lines a block holds to itself.

    A block whose first statement begins on a line the heading runs to
    shares that line with what the heading works out — a condition, a
    kind, a pattern — and that runs whether the block does or not, so
    the line is no part of the alternative. A heading written over
    several lines is read to the last of them.

    Args:
        body (list[ast.stmt]): The block's statements.
        header (int): The last line the heading reaches.

    Returns:
        set[int]: Those lines, the shared one left out.
    '''

    first = body[0].lineno
    held = set(range(first, (body[-1].end_lineno or first) + 1))

    return held - {first} if first == header else held


def _else_arm(node: ast.If) -> set[int]:

    '''Return the lines of an `if` statement's `else`, where it has one.

    Args:
        node (ast.If): The `if` statement to read.

    Returns:
        set[int]: Those lines, or none where there is no `else`.
    '''

    if not node.orelse:
        return set()

    return set(range(node.orelse[0].lineno, (node.orelse[-1].end_lineno or 0) + 1))


def _branch_arms(node: ast.If, scopes: _Scopes) -> list[tuple[set[int], set[int]]]:

    '''Return the arms of one `if`, where it has two.

    An `if` with an `else` has two arms outright, and where its own body
    leaves the path it is an alternative to the lines after the whole
    statement as well. One without an `else` makes an arm
    of the code after it where its body leaves the path having done
    something — a return, or a raise or continue after some act. A body
    that only builds a message and raises is a guard, and the code after
    it is the ordinary path rather than an alternative.

    Args:
        node (ast.If): The `if` statement to read.
        scopes (_Scopes): What a branch leaving the path can skip.

    Returns:
        list[tuple[set[int], set[int]]]: The one pair found, or none.
    '''

    body = _own_lines(node.body, node.test.end_lineno or node.lineno)

    pairs: list[tuple[set[int], set[int]]] = []

    other = _else_arm(node)

    if other:
        pairs.append((body, other))

    for arm, statements in ((body, node.body), (other, node.orelse)):

        if not arm or not statements or not _leaves_the_path(statements):
            continue

        after = _after_the_branch(node, statements, scopes)

        if after:
            pairs.append((arm, after))

    return pairs


def _innermost(scope: dict[int, int], line: int) -> int:

    '''Return where the innermost block of a kind holding a line ends.

    Args:
        scope (dict[int, int]): Where each block of one kind starts and ends.
        line (int): The line to find a block around.

    Returns:
        int: That block's last line, or 0 where none holds the line.
    '''

    return min((end for start, end in scope.items() if start <= line <= end), default=0)


def _after_the_branch(
    node: ast.If,
    statements: list[ast.stmt],
    scopes: _Scopes,
) -> set[int]:

    '''Return the lines an arm that leaves the path is an alternative to.

    How far that reaches depends on how the arm leaves. A continue or a
    break skips the rest of its loop alone. A raise with a handler above
    it reaches the end of the guarded block. A return reaches the end of
    the function. A `finally` runs whatever happens, and a loop's `else`
    runs after a continue, so neither is an alternative to anything —
    unless the arm itself never ends at all, an endless loop being
    where even a `finally` does not run — a `finally` that never ends
    is running, and is no alternative to what entered it.
    Where a `finally` is what takes the branch out, how far that reaches
    is measured from the `finally` rather than from the branch, and a
    `finally` leaving by more than one way reaches nothing. So does an
    arm leaving by more than one way, every statement of it that can
    leave being read rather than the last alone. An arm that could
    raise where it stands reaches no further than such a raise would,
    since a handler or a context manager between the arm and the end
    carries that run on past it — and the handlers it could reach run
    on that raise, so they are no alternative to it either, however
    the arm leaves on its other paths. A `finally` that could raise as it
    runs bounds it the same way, and so does a `with` whose own ending
    could: both run on the way out, and such a raise leaves the
    construct it came from rather than being caught by it.

    Args:
        node (ast.If): The `if` the arm belongs to.
        statements (list[ast.stmt]): The arm's statements.
        scopes (_Scopes): What a branch leaving the path can skip.

    Returns:
        set[int]: Those lines, or none where there are none.
    '''

    own = _one_leave(statements)
    override = _overridden(scopes, node.lineno, own)
    kind = override[0] if override is not None else own
    measured = override[1] if override is not None else node.lineno
    reach = _as_far_as(kind, scopes, measured)

    if not reach:
        return set()

    raising = _may_raise(statements)

    if raising:
        reach &= _as_far_as('raise', scopes, measured)

    cleanup = _cleaned_up(scopes, node.lineno)

    if cleanup is not None:
        reach &= _as_far_as('raise', _without(scopes, cleanup), measured)

    after = {
        line for line in reach if line > (node.end_lineno or node.lineno)
    }
    running = () if own == _ENDLESS else scopes.regardless

    if kind == 'continue':
        running += scopes.after_a_loop

    if own == _RAISE or raising or cleanup is not None:
        running += scopes.handlers

    return after - _still_runs(running, node.lineno)


def _cleaned_up(scopes: _Scopes, line: int) -> int | None:

    '''Return where the nearest ending that could raise starts.

    A `finally` that could raise as it runs is one, and so is a `with`,
    whose own ending could raise whatever its body did. Both run on
    the way out of the construct that holds them, and only within the
    function the branch sits in: one further out runs after the call
    rather than inside it.

    Args:
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where the branch sits.

    Returns:
        int | None: Where the nearest such construct starts, or None
            where none stands around the line.
    '''

    floor = _function_floor(scopes, line)

    return max(
        (
            start
            for spans in (scopes.cleaned, scopes.helds)
            for start, end in spans.items()
            if start <= line <= end and start >= floor
        ),
        default=None,
    )


def _without(scopes: _Scopes, start: int) -> _Scopes:

    '''Return the scopes with the construct starting on one line left out.

    A raise an ending takes leaves the construct whose ending it is, so
    that construct cannot be what catches or bounds it — nor can
    anything inside it, every handler and every ending in there having
    had its turn before that ending ran. A `with` holding more than
    one manager keeps its place: an ending of one could be swallowed by
    another in the same statement, and what follows the `with` run
    after all.

    Args:
        scopes (_Scopes): What a branch leaving the path can skip.
        start (int): Where that construct starts.

    Returns:
        _Scopes: The same, with that construct dropped.
    '''

    if start not in scopes.cleaned and start not in scopes.alone:
        return scopes

    end = max(
        (
            held_end
            for spans in (scopes.cleaned, scopes.helds)
            for held, held_end in spans.items()
            if held == start
        ),
        default=start,
    )

    return dataclasses.replace(
        scopes,
        tries={
            held: held_end
            for held, held_end in scopes.tries.items()
            if not start <= held <= end
        },
        helds={
            held: held_end
            for held, held_end in scopes.helds.items()
            if not start <= held <= end
        },
    )


def _as_far_as(kind: str, scopes: _Scopes, line: int) -> set[int]:

    '''Return every line up to where a branch leaving one way reaches.

    Args:
        kind (str): The way it leaves.
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where that way out is measured from.

    Returns:
        set[int]: Those lines, or none where the way out names no
            block to reach the end of.
    '''

    tried = _reach_of(kind, scopes, line)

    if not tried:
        return set()

    stop = next(
        (found for scope in tried if (found := _innermost(scope, line))), 0,
    )

    return set(range(stop + 1))


def _overridden(scopes: _Scopes, line: int, own: str) -> tuple[str, int] | None:

    '''Return the way a `finally` around a branch takes it out instead.

    A `finally` runs after whatever the branch did and can leave by its
    own way, so a return under a `finally` that breaks is a break. One
    outside the function the branch sits in takes out the call, not the
    branch, and is passed over. So is one the branch never reaches: a
    break or a continue bound for a loop inside the `try` stays in
    there, and the `finally` has not run when what follows the loop
    does. The nearest `finally` is read first, and the way it leaves by
    is what the one around it is asked about, since that is the way the
    branch is on by then.

    Args:
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where the branch sits.
        own (str): The way the branch leaves by itself.

    Returns:
        tuple[str, int] | None: The way it leaves and where its `try`
            starts, or None where no `finally` around the branch leaves.
    '''

    floor = _function_floor(scopes, line)
    found: tuple[str, int] | None = None
    way = own

    for block, kind in sorted(scopes.overrides, key=lambda held: -held[0].start):

        if block.start < floor or block.skipped_by(line):
            continue

        if not _leaves_the_try(way, scopes, line, block.start):
            break

        found = kind, block.start
        way = kind

    return found


def _leaves_the_try(own: str, scopes: _Scopes, line: int, start: int) -> bool:

    '''Whether a branch's own way out crosses a `try` to reach its end.

    A return or a raise leaves whatever holds it, so it crosses. A
    break or a continue reaches the loop around it — a loop whose
    `else` holds the line having finished already — and crosses only
    where that loop is outside the `try`. A branch leaving by nothing
    nameable crosses nothing.

    Args:
        own (str): The way the branch leaves by itself.
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where the branch sits.
        start (int): Where the `try` holding the `finally` starts.

    Returns:
        bool: True where the `finally` runs on that way out.
    '''

    if own in {'return', 'raise'}:
        return True

    if own not in {'break', 'continue'}:
        return False

    return not any(
        start < held <= line <= end
        for held, end in _loops_around(scopes, line).items()
    )


def _can_leave(body: list[ast.stmt]) -> bool:

    '''Whether any path through a block can take the path out.

    Args:
        body (list[ast.stmt]): The block's statements.

    Returns:
        bool: True where the block ends by some way out.
    '''

    return bool(_block_ways(body) - {_CARRIES_ON})


_WAYS_READ: dict[int, tuple[ast.stmt, set[str]]] = {}
_RAISE_READ: dict[int, tuple[ast.stmt, bool]] = {}


def _block_ways(body: list[ast.stmt]) -> set[str]:

    '''Return the ways a block can end, by name.

    A block ends by each way a statement of it takes out, and by
    carrying on where every statement of it can. Nothing past the first
    statement that always leaves is read, nothing there running.

    Args:
        body (list[ast.stmt]): The block's statements.

    Returns:
        set[str]: `return`, `raise`, `continue`, `break` and
            `carries on`, as the block has them.
    '''

    ways: set[str] = set()

    for statement in body:
        found = _statement_ways(statement)
        ways |= found - {_CARRIES_ON}

        if _CARRIES_ON not in found:
            return ways

    return ways | {_CARRIES_ON}


def _statement_ways(statement: ast.stmt) -> set[str]:

    '''Return the ways one statement can end, by name.

    The answer is read once per statement and kept. A `try` is asked
    about several times over — for its own ways, for the handlers that
    run, and for whether it could raise — so a nest of them would
    otherwise be read again at every level.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        set[str]: Those ways.
    '''

    held = _WAYS_READ.get(id(statement))

    if held is None:
        held = statement, _ways_read(statement)
        _WAYS_READ[id(statement)] = held

    return held[1]


def _ways_read(statement: ast.stmt) -> set[str]:

    '''Return the ways one statement can end, read afresh.

    Nothing is read inside a function, a way out written there waiting
    on a call, nor inside anything else that holds no block of its own.
    A class body runs where it stands, so the class ends the way that
    body does. An `if` with no `else` can carry on.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        set[str]: Those ways.
    '''

    if isinstance(statement, ast.Raise):
        return {_raise_way(statement)}

    if isinstance(statement, ast.Assert):
        answer = _assert_answer(statement)

        if answer is not None:
            return {_CARRIES_ON} if answer else {f'{_RAISE}:AssertionError'}

    plain = _plainly_leaves(statement)

    if plain:
        return {plain}

    if isinstance(statement, ast.ClassDef):
        return _block_ways(statement.body)

    if isinstance(statement, ast.If):
        return _branch_ways(statement)

    return _holder_ways(statement)


def _branch_ways(statement: ast.If) -> set[str]:

    '''Return the ways an `if` statement can end.

    A condition written out so that its answer is known leaves only
    one arm to read; otherwise either arm can run, and an `if` with no
    `else` can carry on.

    Args:
        statement (ast.If): The statement to read.

    Returns:
        set[str]: Those ways.
    '''

    answer = _written_truth(statement.test)
    otherwise = (
        _block_ways(statement.orelse) if statement.orelse else {_CARRIES_ON}
    )

    if answer is True:
        return _block_ways(statement.body)

    if answer is False:
        return otherwise

    return _block_ways(statement.body) | otherwise


def _holder_ways(statement: ast.stmt) -> set[str]:

    '''Return the ways a `match`, a `with`, a `try` or a loop can end.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        set[str]: Those ways, or carrying on for anything else.
    '''

    if isinstance(statement, ast.Match):
        return _match_ways(statement)

    if isinstance(statement, (ast.With, ast.AsyncWith)):
        return _held_ways(
            _block_ways(statement.body),
            could_raise=_may_raise(statement.body) or _held_could_swallow(statement),
        )

    if isinstance(statement, (ast.Try, ast.TryStar)):
        return _try_ways(statement)

    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        return _loop_ways(statement)

    return {_CARRIES_ON}


def _match_ways(statement: ast.Match) -> set[str]:

    '''Return the ways a `match` statement can end.

    One that does not take every value falls past all of its cases, and
    so carries on. A case whose guard is written out as one that never
    holds cannot run, and nothing after a case that takes every value
    with a guard that always holds can run either.

    Args:
        statement (ast.Match): The statement to read.

    Returns:
        set[str]: Those ways.
    '''

    ways: set[str] = set()

    for case in statement.cases:
        answer = True if case.guard is None else _written_truth(case.guard)

        if answer is False:
            continue

        ways |= _block_ways(case.body)

        if answer is True and _takes_anything(case.pattern):
            return ways

    return ways if _covers_everything(statement) else ways | {_CARRIES_ON}


def _held_could_swallow(statement: ast.With | ast.AsyncWith) -> bool:

    '''Whether a `with` could swallow a raise of its own making.

    A statement holding more than one manager can swallow the ending
    of another in it, and handing what a manager gives back to
    anything but a plain name could raise where that happens, which
    the managers are there to swallow.

    Args:
        statement (ast.With): The statement to read.

    Returns:
        bool: True where such a raise could be swallowed.
    '''

    if len(statement.items) > 1:
        return True

    return any(
        item.optional_vars is not None
        and not isinstance(item.optional_vars, ast.Name)
        for item in statement.items
    )


def _held_ways(ways: set[str], *, could_raise: bool) -> set[str]:

    '''Return the ways a `with` ends, given the ways its body can.

    A context manager can swallow a raise, so what follows the `with`
    may run after all — and may not, so the raise stands as a way out
    beside carrying on. A raise the body could take without saying so,
    out of a call or a name or a sum, is swallowed the same way, and
    carrying on stands beside the body's own ways for it. A `with`
    holding more than one manager can swallow the ending of another in
    the same statement, so carrying on stands there whatever its body
    does.

    Args:
        ways (set[str]): The ways its body can end.
        could_raise (bool): Whether anything the body runs could raise
            without that being one of those ways, or the statement
            holds a manager that could swallow another's ending.

    Returns:
        set[str]: Those ways, with carrying on where a raise could be
            swallowed.
    '''

    if not could_raise and not any(way.startswith(_RAISE) for way in ways):
        return ways

    return ways | {_CARRIES_ON}


def _plain_ways(ways: set[str]) -> set[str]:

    '''Return the ways with every raise read as a raise alone.

    A raise is held with the kind it names, so that a handler can be
    asked whether it catches that one. Where the ways are weighed
    against each other the kind is set aside: two raises of different
    kinds leave by the same way.

    Args:
        ways (set[str]): The ways a block or statement can end.

    Returns:
        set[str]: Those ways, each raise named plainly.
    '''

    return {_RAISE if way.startswith(_RAISE) else way for way in ways}


def _raise_way(statement: ast.Raise) -> str:

    '''Return the way a raise leaves, with the kind it names.

    A raise naming nothing carries whatever is already being handled,
    and a raise naming something other than a plain name says nothing
    a handler can be matched against; both are left unnamed.

    Args:
        statement (ast.Raise): The statement to read.

    Returns:
        str: `raise`, with the kind after it where one is named.
    '''

    named = statement.exc

    if isinstance(named, ast.Call):
        named = named.func

    kind = _kind_named(named)

    return _RAISE if kind is None else f'{_RAISE}:{kind}'


def _caught_by(node: ast.Try | ast.TryStar, ways: set[str]) -> set[str]:

    '''Return the raises a `try`'s own handlers certainly catch.

    A handler naming no kind catches anything, as does one naming
    `BaseException`. Any other handler catches a raise of the kind it
    names and of every kind the language carries under that one, so
    `LookupError` catches a `KeyError`. A kind the language carries
    nowhere is left uncaught, standing where it stands being the
    project's own affair, and so is a raise of a kind named through
    something else, or one naming nothing at all.

    Args:
        node (ast.Try): The statement to read.
        ways (set[str]): The ways its body can end.

    Returns:
        set[str]: The ways of that set those handlers catch.
    '''

    if not node.handlers:
        return set()

    raises = {way for way in ways if way.startswith(_RAISE)}

    if _catches_anything(node):
        return raises

    named = _covered_kinds(_handler_kinds(node))

    return {way for way in raises if way.partition(':')[2] in named}


def _catches_anything(node: ast.Try | ast.TryStar) -> bool:

    '''Whether a handler of a `try` catches every raise.

    Args:
        node (ast.Try): The statement to read.

    Returns:
        bool: True where one handler names no kind, or names every
            error there is.
    '''

    return any(
        handler.type is None or _names_every_error(handler.type)
        for handler in node.handlers
    )


def _names_every_error(named: ast.expr) -> bool:

    '''Whether what a handler names covers every error.

    `Exception` does not: three kinds stand outside it, so a handler
    naming it is read for the kinds it does cover rather than as a
    catch-all.

    Args:
        named (ast.expr): The kind the handler names.

    Returns:
        bool: True for `BaseException`, or a tuple holding it.
    '''

    if isinstance(named, ast.Tuple):
        return any(_names_every_error(held) for held in named.elts)

    return _kind_named(named) == 'BaseException'


def _handler_kinds(node: ast.Try | ast.TryStar) -> set[str]:

    '''Return the kinds a `try`'s handlers name.

    Args:
        node (ast.Try): The statement to read.

    Returns:
        set[str]: Each plain name they name, a tuple read through.
    '''

    kinds: set[str] = set()

    for handler in node.handlers:
        kinds |= _named_kinds(handler.type)

    return kinds


def _try_ways(statement: ast.Try | ast.TryStar) -> set[str]:

    '''Return the ways a `try` statement can end.

    A raise in the body is read as a way out unless a handler of its
    own certainly catches it, the handlers' ways standing beside it
    wherever the body raises at all, said or unsaid. Handlers are read in the
    order they are written, and one naming every error is the last that
    can run, so nothing after it is read — a handler naming no kind at
    all can only be written last anyway. The `else` runs where
    the body reaches its end. A `finally` runs last, so
    where it always leaves it is the only way the statement ends, and
    where it leaves on some paths those ways are added to the rest.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        set[str]: Those ways.
    '''

    held = _block_ways(statement.body)
    ways = held - {_CARRIES_ON} - _caught_by(statement, held)

    if _CARRIES_ON in held:
        ways |= _block_ways(statement.orelse) if statement.orelse else {_CARRIES_ON}

    if _may_raise(statement.body) or any(
        way.startswith(_RAISE) for way in held
    ):
        ways |= _handler_ways(statement)

    if not statement.finalbody:
        return ways

    done = _block_ways(statement.finalbody)

    return ways | (done - {_CARRIES_ON}) if _CARRIES_ON in done else done


def _handler_ways(statement: ast.Try | ast.TryStar) -> set[str]:

    '''Return the ways the handlers of a `try` can end.

    Only the handlers something could reach are read: one whose every
    kind an earlier handler already catches cannot run, nor can one no
    raise of the body could arrive at, nor anything after a handler
    naming every error.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        set[str]: Those ways.
    '''

    return {
        way
        for handler in _handlers_that_run(statement)
        for way in _block_ways(handler.body)
    }


def _handlers_tried(statement: ast.Try | ast.TryStar) -> list[ast.ExceptHandler]:

    '''Return the handlers whose kinds could be worked out.

    The kinds are worked out in the order they are written, until one
    catches what arrived; a raise the body could take without saying so
    could be of any kind, so every kind is worked out for it. A `try`
    taking errors in groups weighs every kind against the group, so
    none of them is passed over. Where nothing can arrive, no kind is
    worked out at all, and nothing written after a handler naming
    every error is worked out either, that handler having caught
    whatever arrived.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        list[ast.ExceptHandler]: Those handlers, in order.
    '''

    held = _block_ways(statement.body)
    left = {way for way in held if way.startswith(_RAISE)}
    unsaid = _may_raise(statement.body)

    if not left and not unsaid:
        return []

    found: list[ast.ExceptHandler] = []

    for handler in statement.handlers:
        found.append(handler)
        left -= _caught_by_handler(handler, left)

        if handler.type is not None and _names_every_error(handler.type):
            break

        if not unsaid and not left and not isinstance(statement, ast.TryStar):
            break

    return found


def _handlers_that_run(statement: ast.Try | ast.TryStar) -> list[ast.ExceptHandler]:

    '''Return the handlers of a `try` something could reach.

    Handlers are read in the order they are written. A raise the body
    says it takes arrives at the first handler naming its kind, and at
    none after that; a raise the body could take without saying so
    could arrive anywhere, and so could one still looking for a handler
    when a kind named through anything but a plain name is reached, and
    so could one naming no kind at all — a bare raise carries whatever
    is already being handled, which any handler could catch. One whose
    every kind an earlier handler
    already catches cannot run, and nothing after a handler naming
    every error can.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        list[ast.ExceptHandler]: Those handlers, in order.
    '''

    return [
        handler for handler, _tried, runs in _handler_reach(statement) if runs
    ]


def _handler_reach(
    statement: ast.Try | ast.TryStar,
) -> list[tuple[ast.ExceptHandler, bool, bool]]:

    '''Return what can reach each handler of a `try`, in order.

    A handler is tried where a raise reaches it looking for one, which
    works out the kind it names whether or not that kind then catches.
    Nothing is tried once every raise the body can take is certainly
    caught, nor where the body takes none at all, and nothing written
    after a handler naming every error is tried or run either.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        list[tuple[ast.ExceptHandler, bool, bool]]: Each handler, with
            whether it is tried at all and whether its body runs.
    '''

    held = _block_ways(statement.body)
    left = {way for way in held if way.startswith(_RAISE)}
    unsaid = _may_raise(statement.body)
    seen: set[str] = set()
    found: list[tuple[ast.ExceptHandler, bool, bool]] = []

    for handler in statement.handlers:
        caught = _caught_by_handler(handler, left)
        unread = handler.type is not None and not _every_part_named(handler.type)
        unnamed = any(not way.partition(':')[2] for way in left)
        tried = bool(unsaid or left)
        runs = bool(
            (unsaid or caught or unnamed or (unread and left))
            and not _covered_already(handler, seen),
        )
        found.append((handler, tried, runs))
        seen |= _named_kinds(handler.type)
        left -= caught

        if handler.type is not None and _names_every_error(handler.type):
            after = statement.handlers[statement.handlers.index(handler) + 1:]
            found += [(held_after, False, False) for held_after in after]
            break

    return found


def _caught_by_handler(handler: ast.ExceptHandler, ways: set[str]) -> set[str]:

    '''Return the raises one handler certainly catches.

    Args:
        handler (ast.ExceptHandler): The handler to read.
        ways (set[str]): The raise ways still looking for a handler.

    Returns:
        set[str]: Those of them it catches.
    '''

    if handler.type is None or _names_every_error(handler.type):
        return set(ways)

    covered = _covered_kinds(_named_kinds(handler.type))

    return {way for way in ways if way.partition(':')[2] in covered}


def _covered_kinds(kinds: set[str]) -> frozenset[str]:

    '''Return every kind a set of named kinds catches between them.

    A handler catches a raise of the kind it names and of every kind
    the language carries under that one, so `LookupError` catches a
    `KeyError` and `Exception` catches whatever stands under it.

    Args:
        kinds (set[str]): The kinds named.

    Returns:
        frozenset[str]: Those kinds and everything under them.
    '''

    return frozenset(kinds).union(*(
        _COVERED_BY.get(kind, frozenset()) for kind in kinds
    )) if kinds else frozenset()


def _covered_already(handler: ast.ExceptHandler, seen: set[str]) -> bool:

    '''Whether earlier handlers already catch everything one names.

    A handler naming nothing catches anything, and can only be written
    last, so nothing it would shadow is read after it either way. One
    naming a kind through something else — an attribute, a call — says
    nothing that can be weighed against what came before, so it is
    read as able to run.

    Args:
        handler (ast.ExceptHandler): The handler to read.
        seen (set[str]): The kinds the handlers before it name.

    Returns:
        bool: True where it cannot run.
    '''

    kinds = _named_kinds(handler.type)

    if not kinds or not _every_part_named(handler.type):
        return False

    covered = _covered_kinds(seen)

    return all(kind in covered for kind in kinds)


def _every_part_named(named: ast.expr | None) -> bool:

    '''Whether every kind an `except` names is a plain name.

    Args:
        named (ast.expr | None): What the handler names, or nothing.

    Returns:
        bool: True where each part can be weighed by name.
    '''

    if named is None:
        return False

    held = named.elts if isinstance(named, ast.Tuple) else [named]

    return all(_kind_named(part) is not None for part in held)


def _named_kinds(named: ast.expr | None) -> set[str]:

    '''Return the plain names an `except` kind holds.

    Args:
        named (ast.expr | None): What the handler names, or nothing.

    Returns:
        set[str]: Each plain name in it, a tuple read through.
    '''

    if named is None:
        return set()

    held = named.elts if isinstance(named, ast.Tuple) else [named]

    return {kind for part in held if (kind := _kind_named(part)) is not None}


def _loop_ways(statement: ast.For | ast.AsyncFor | ast.While) -> set[str]:

    '''Return the ways a loop can end.

    A loop written to go over what no turn can be taken from ends by
    the raise that takes, nothing in it running. A break lands on the
    line after the loop, so the loop carries on; a continue goes round
    again and ends nothing. A break need not be
    taken, though, so any loop but an endless `while` can also finish
    and run its `else`, a `for` over something empty included. An
    endless `while` is finished by a break alone, so without one it
    reaches neither its `else` nor anything after it, and ends by
    nothing at all. A loop written so that its body never runs — a
    condition that never holds, or nothing to go over — is read for
    its `else` alone, and one written so that its body runs at least
    once never finishes where that body always leaves.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        set[str]: Those ways.
    '''

    if _raises_before_a_turn(statement):
        return {_RAISE}

    if _runs_nothing(statement):
        return _block_ways(statement.orelse) if statement.orelse else {_CARRIES_ON}

    inside = _block_ways(statement.body)
    ways = inside - {_CARRIES_ON, 'break', 'continue'}

    if 'break' in inside:
        ways |= {_CARRIES_ON}

    if not _reaches_its_else(statement):
        if isinstance(statement, ast.While) and _endless(statement.test):
            return ways or {_ENDLESS}

        return ways

    return ways | (
        _block_ways(statement.orelse) if statement.orelse else {_CARRIES_ON}
    )


def _child_blocks(statement: ast.stmt) -> list[list[ast.stmt]]:

    '''Return every statement list a statement holds.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        list[list[ast.stmt]]: Its body, its `else`, its `finally`, and
            each handler's or case's body, as it has them.
    '''

    blocks = [
        getattr(statement, name, []) or []
        for name in ('body', 'orelse', 'finalbody')
    ]
    blocks += [
        handler.body for handler in getattr(statement, 'handlers', []) or []
    ]
    blocks += [case.body for case in getattr(statement, 'cases', []) or []]

    return [block for block in blocks if isinstance(block, list)]


def _one_leave(body: list[ast.stmt]) -> str:

    '''Return the single way a block leaves, where it leaves by one.

    A block that leaves on some paths and not others, or by more than
    one way, names none: what follows the branch it takes out cannot be
    told from what does not.

    Args:
        body (list[ast.stmt]): The block's statements.

    Returns:
        str: That way, or an empty string.
    '''

    ways = _plain_ways(_block_ways(body))

    if _CARRIES_ON in ways or len(ways) != 1:
        return ''

    return ways.pop()


def _loops_around(scopes: _Scopes, line: int) -> dict[int, int]:

    '''Return the loops a continue or break on one line belongs to.

    A loop's `else` runs after that loop has finished, so a continue
    written there carries on the loop outside it.

    Args:
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where the branch sits.

    Returns:
        dict[int, int]: Where each usable loop starts and ends.
    '''

    finished = {
        block.start for block in scopes.after_a_loop if line in block.lines
    }

    return {
        start: end for start, end in scopes.loops.items() if start not in finished
    }


def _function_floor(scopes: _Scopes, line: int) -> int:

    '''Return where the innermost function holding a line starts.

    Args:
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): The line to find a function around.

    Returns:
        int: That function's first line, or 0 where none holds it.
    '''

    return max(
        (start for start, end in scopes.ends.items() if start <= line <= end),
        default=0,
    )


def _handled_here(scopes: _Scopes, line: int) -> dict[int, int]:

    '''Return the handled blocks that catch a raise on one line.

    A `try` outside the function the raise sits in catches the call,
    not the raise, so what runs after that call is no alternative to
    the branch and such a block is left out. So is the `try` whose own
    handler or `else` the raise sits in, which has had its turn. A
    `with` around the raise bounds it too: its context manager may
    swallow the raise, so nothing past the `with` can be called an
    alternative to the branch.

    Args:
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where the branch sits.

    Returns:
        dict[int, int]: Where each usable block starts and ends.
    '''

    floor = _function_floor(scopes, line)
    had_its_turn = {
        block.start
        for blocks in (scopes.handlers, scopes.settled)
        for block in blocks
        if line in block.lines
    }

    held = {
        start: end for start, end in scopes.helds.items()
        if start >= floor and start <= line <= end
    }

    return held | {
        start: end for start, end in scopes.tries.items()
        if start >= floor and start not in had_its_turn
    }


def _reach_of(
    kind: str,
    scopes: _Scopes,
    line: int,
) -> tuple[dict[int, int], ...]:

    '''Return the blocks a branch leaving one way can reach the end of.

    Args:
        kind (str): The way it leaves.
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where that way out is measured from.

    Returns:
        tuple[dict[int, int], ...]: Where to look, nearest kind first,
            or nothing where the way out names no block.
    '''

    if kind in {'continue', 'break'}:
        return (_loops_around(scopes, line),)

    if kind == 'raise':
        return (_handled_here(scopes, line), scopes.ends)

    if kind in {'return', _ENDLESS}:
        return (scopes.ends,)

    return ()


def _still_runs(blocks: tuple[_Block, ...], line: int) -> set[int]:

    '''Return the lines that run whatever a branch on one line does.

    Args:
        blocks (tuple[_Block, ...]): The blocks to weigh.
        line (int): Where the branch sits.

    Returns:
        set[int]: The lines of every block the branch does not skip.
    '''

    kept: set[int] = set()

    for block in blocks:

        if not block.skipped_by(line):
            kept |= block.lines

    return kept


def _plainly_leaves(statement: ast.stmt) -> str:

    '''Return the way a statement leaves, where it is one itself.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        str: That way, or an empty string for anything else.
    '''

    for kind, node_type in (
        ('return', ast.Return), ('raise', ast.Raise),
        ('continue', ast.Continue), ('break', ast.Break),
    ):

        if isinstance(statement, node_type):
            return kind

    return ''


def _covers_everything(node: ast.Match) -> bool:

    '''Whether a `match` statement has a case for every value.

    A `match` with no catch-all can fall past all of its cases, so what
    follows it runs and it leaves by nothing. A guard on that case
    holds it back, unless the guard is written out as one that holds.

    Args:
        node (ast.Match): The statement to read.

    Returns:
        bool: True where its last case takes anything.
    '''

    if not node.cases:
        return False

    last = node.cases[-1]

    held = last.guard is None or _written_truth(last.guard) is True

    return held and _takes_anything(last.pattern)


def _takes_anything(pattern: ast.pattern) -> bool:

    '''Whether a pattern matches every value.

    A bare capture does, and so does an alternative holding one. A
    pattern naming a kind does not, whatever that kind is: the name
    could be bound to anything by the time the `match` runs.

    Args:
        pattern (ast.pattern): The pattern to read.

    Returns:
        bool: True where nothing falls past it.
    '''

    if isinstance(pattern, ast.MatchAs):
        return pattern.pattern is None or _takes_anything(pattern.pattern)

    if isinstance(pattern, ast.MatchOr):
        return any(_takes_anything(held) for held in pattern.patterns)

    return False


def _raises_before_a_turn(statement: ast.For | ast.AsyncFor | ast.While) -> bool:

    '''Whether a loop raises before it takes a turn at all.

    Going over what is written out as something no turn can be taken
    from raises there, and so does asking for each turn to be awaited
    where what is gone over is written out, nothing written out being
    something to await.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        bool: True where nothing in it runs.
    '''

    if isinstance(statement, ast.While):
        return False

    if _goes_over_nothing(statement.iter):
        return True

    return isinstance(statement, ast.AsyncFor) and _written_as(
        statement.iter,
    ) is not None


def _reaches_its_else(statement: ast.For | ast.AsyncFor | ast.While) -> bool:

    '''Whether a loop can reach the `else` written after it.

    The `else` runs where the loop is finished rather than broken out
    of. An endless `while` is never finished, and a loop written to
    take a turn whose body always leaves on it never gets to a second,
    so neither reaches its `else`.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        bool: True where the `else` can run.
    '''

    if isinstance(statement, ast.While) and _endless(statement.test):
        return False

    inside = _block_ways(statement.body)

    return not (_runs_once(statement) and not {_CARRIES_ON, 'continue'} & inside)


def _runs_once(statement: ast.For | ast.AsyncFor | ast.While) -> bool:

    '''Whether a loop is written so that its body runs at least once.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        bool: True for an endless `while`, and for a `for` over
            something written out that gives a turn.
    '''

    if isinstance(statement, ast.While):
        return _endless(statement.test)

    turns = _written_turns(statement.iter) if isinstance(statement, ast.For) else None

    return turns is not None and turns > 0


def _runs_nothing(statement: ast.For | ast.AsyncFor | ast.While) -> bool:

    '''Whether a loop is written so that its body never runs.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        bool: True where its condition never holds, or where what it
            goes over is written out with nothing in it.
    '''

    if isinstance(statement, ast.While):
        return _never_holds(statement.test)

    return _iterates_nothing(statement.iter)


def _written_turns(gone_over: ast.expr) -> int | None:

    '''Return how many turns what a loop goes over gives, as written.

    A list, tuple, set or mapping written out gives one turn per thing
    in it, and a string of letters or bytes one per letter. An `and`
    or an `or` of such is weighed down to the part that stands. Where
    something is unpacked in, or the thing is not written out, or what
    is written is nothing to go over at all, no number is given.

    Args:
        gone_over (ast.expr): The expression the loop goes over.

    Returns:
        int | None: That number, or None where it is not known.
    '''

    if isinstance(gone_over, ast.BoolOp):
        return _written_turns_of_both(gone_over)

    held = _written_as(gone_over)

    if held is None or not isinstance(held[0], _GONE_OVER):
        return None

    return len(held[0])


def _written_turns_of_both(gone_over: ast.BoolOp) -> int | None:

    '''Return the turns an `and` or an `or` of written-out parts gives.

    An `and` stands as its last part where every part before it holds,
    and as the first that fails; an `or` the other way about.

    Args:
        gone_over (ast.BoolOp): The expression the loop goes over.

    Returns:
        int | None: That number, or None where it is not known.
    '''

    stands = _part_that_stands(gone_over)

    return None if stands is None else _written_turns(stands)


def _part_that_stands(held: ast.BoolOp) -> ast.expr | None:

    '''Return the part an `and` or an `or` of written-out parts stands as.

    An `and` stands as the first part that fails, or as its last part
    where every part before it holds; an `or` the other way about.

    Args:
        held (ast.BoolOp): The expression to read.

    Returns:
        ast.expr | None: That part, or None where it is not known.
    '''

    wanted = isinstance(held.op, ast.Or)

    for part in held.values[:-1]:
        answer = _written_truth(part)

        if answer is None:
            return None

        if answer is wanted:
            return part

    return held.values[-1]


def _goes_over_nothing(gone_over: ast.expr) -> bool:

    '''Whether what is written out is nothing a loop can go over.

    A number, a boolean and nothing at all are not: going over one
    raises before any turn is taken. An `and` or an `or` is read as
    the part it stands as.

    Args:
        gone_over (ast.expr): The expression the loop goes over.

    Returns:
        bool: True where it is written out and cannot be gone over.
    '''

    if isinstance(gone_over, ast.UnaryOp) and isinstance(gone_over.op, ast.Not):
        return True

    if isinstance(gone_over, ast.BoolOp):
        stands = _part_that_stands(gone_over)

        return stands is not None and _goes_over_nothing(stands)

    if isinstance(gone_over, ast.Compare):
        return _written_comparison(gone_over) is not None

    held = _written_as(gone_over)

    return held is not None and not isinstance(held[0], _GONE_OVER)


def _never_holds(test: ast.expr) -> bool:

    '''Whether a `while` condition is written as one that never holds.

    Args:
        test (ast.expr): The condition.

    Returns:
        bool: True where it is written out and does not hold.
    '''

    return _written_truth(test) is False


def _written_as(held: ast.expr) -> tuple[Any] | None:

    '''Return what an expression is written out as, in a tuple of one.

    A value written out in full — a constant, or a list, tuple, set or
    mapping of such — is that value. Anything read at the time is
    written out as nothing: a name may be bound to anything, and a
    call is a call even where it is spelled as something empty. So is
    anything that would raise in the writing, such as a set holding
    what cannot be hashed.

    Args:
        held (ast.expr): The expression to read.

    Returns:
        tuple[Any] | None: That value alone in a tuple, so that a
            value which is itself nothing can be told from none.
    '''

    if any(isinstance(part, (ast.Call, ast.Name, ast.Attribute)) for part in ast.walk(held)):
        return None

    try:
        return (ast.literal_eval(held),)

    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return None


def _written_truth(test: ast.expr) -> bool | None:

    '''Whether a condition is written so that its answer is known.

    A constant answers for itself, as does a list, tuple, set or
    mapping written out, by whether anything is in it — unless
    something is unpacked into it, which could be anything. A `not`
    turns the answer of what it holds around, an `and` or an `or` is
    weighed part by part, and a comparison of constants is weighed as
    written. Anything else is read at the time and is
    not known here.

    Args:
        test (ast.expr): The condition.

    Returns:
        bool | None: True where it always holds, False where it never
            holds, None where it is not written out.
    '''

    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        answer = _written_truth(test.operand)

        return None if answer is None else not answer

    if isinstance(test, ast.BoolOp):
        return _written_truth_of_both(test)

    if isinstance(test, ast.Compare):
        return _written_comparison(test)

    held = _written_as(test)

    return None if held is None else bool(held[0])


def _written_comparison(test: ast.Compare) -> bool | None:

    '''Whether a comparison of constants answers for itself.

    Each side against the next, with signs the two can be weighed by,
    and each side written out as a value of its own. A chain stops at
    the first pair that fails, as Python does, so a side after that is
    never read, never written out, and could not raise. A comparison
    of two things that cannot be weighed against each other raises
    where it stands, and answers nothing here.

    Args:
        test (ast.Compare): The comparison.

    Returns:
        bool | None: Its answer, or None where it is not known.
    '''

    held = _written_as(test.left)

    if held is None:
        return None

    standing = held[0]

    for sign, beside in zip(test.ops, test.comparators, strict=True):
        written = _written_as(beside)

        if written is None:
            return None

        answer = _weighed_pair(sign, standing, written[0])

        if answer is None:
            return None

        if not answer:
            return False

        standing = written[0]

    return True


def _weighed_pair(sign: ast.cmpop, left: Any, right: Any) -> bool | None:

    '''Weigh one side of a comparison against the next.

    Whether one thing is another is weighed only where both are
    written out as what stands alone — nothing at all, or either
    answer — since two written the same way may be one thing or two,
    and which they are is settled where the file is compiled. A pair
    the sign refuses answers nothing: looking for a number outside a
    byte among bytes is refused as surely as weighing a number against
    a word.

    Args:
        sign (ast.cmpop): The sign between them.
        left (Any): What the near side is written as.
        right (Any): What the far side is written as.

    Returns:
        bool | None: Its answer, or None where it cannot be weighed.
    '''

    weigh = _COMPARISONS.get(type(sign))

    if weigh is None:
        return None

    if isinstance(sign, (ast.Is, ast.IsNot)) and not (
        _stands_alone(left) and _stands_alone(right)
    ):
        return None

    try:
        return bool(weigh(left, right))

    except (TypeError, ValueError, OverflowError):
        return None


def _stands_alone(value: Any) -> bool:

    '''Whether a value written out is one of a kind.

    Nothing at all and either answer are each one object, so two
    written the same way are the same thing.

    Args:
        value (Any): The value written out.

    Returns:
        bool: True where it is one of those.
    '''

    return value is None or isinstance(value, bool)


def _written_truth_of_both(test: ast.BoolOp) -> bool | None:

    '''Whether an `and` or an `or` of written-out answers is known.

    The parts are read in order, as Python reads them. An `and` fails
    at the first part that fails and an `or` holds at the first that
    holds, so the last part answers for the rest; a part that is not
    written out leaves the answer unknown, whatever stands after it.

    Args:
        test (ast.BoolOp): The condition.

    Returns:
        bool | None: True, False, or None where it is not known.
    '''

    wanted = isinstance(test.op, ast.Or)

    for part in test.values[:-1]:
        answer = _written_truth(part)

        if answer is None:
            return None

        if answer is wanted:
            return wanted

    return _written_truth(test.values[-1])


def _iterates_nothing(gone_over: ast.expr) -> bool:

    '''Whether what a loop goes over is written out with nothing in it.

    Args:
        gone_over (ast.expr): The expression the loop goes over.

    Returns:
        bool: True where what is written out gives no turns at all.
    '''

    return _written_turns(gone_over) == 0


def _may_raise(body: list[ast.stmt]) -> bool:

    '''Whether anything in a block could raise.

    Only the plainest statements are read as unable to: a pass, a
    break, a continue, a return or a statement of nothing but a value
    written out, such a value given to plain names, a loop whose body
    never runs, and a `try` nothing in which could raise. A call of any kind, a name looked up,
    a subscript or a sum could raise, so everything else is read as
    able to. Nothing past a statement that always leaves is read, that
    being unreachable.

    Args:
        body (list[ast.stmt]): The block's statements.

    Returns:
        bool: True where a handler of the block could run.
    '''

    for statement in body:

        if _could_raise(statement):
            return True

        if _CARRIES_ON not in _statement_ways(statement):
            return False

    return False


def _could_raise(statement: ast.stmt) -> bool:

    '''Whether one statement could raise where it stands.

    The answer is read once per statement and kept, for the reason
    `_statement_ways` keeps its own.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: Whether that statement could raise.
    '''

    held = _RAISE_READ.get(id(statement))

    if held is None:
        held = statement, _raise_read(statement)
        _RAISE_READ[id(statement)] = held

    return held[1]


def _raise_read(statement: ast.stmt) -> bool:

    '''Whether one statement could raise where it stands, read afresh.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: False for a pass, a break, a continue, a return or a
            statement of nothing but a value written out, a value
            written out given to plain names, a raise of an error the
            language carries, and a loop, an `if`, a `match` or a
            `try` nothing in which could raise; True for everything
            else.
    '''

    if isinstance(statement, (ast.Pass, ast.Break, ast.Continue)):
        return False

    if isinstance(statement, ast.Return):
        return statement.value is not None and not _quiet_expression(statement.value)

    if isinstance(statement, ast.Expr):
        return not _quiet_expression(statement.value)

    if isinstance(statement, ast.Raise):
        return not _raised_quietly(statement)

    if isinstance(statement, ast.Assert):
        return _assert_answer(statement) is None

    return _written_could_raise(statement)


def _assert_answer(statement: ast.Assert) -> bool | None:

    '''Return what an assert does where that is known where it stands.

    An assert raises `AssertionError` where its test is falsy and
    nothing else, so a test written out with its answer known says
    which of those happens. A test that always holds settles it: the
    message is never worked out. Where the test fails or is read at
    the time, a message that could raise as it is worked out leaves
    the answer unknown.

    Args:
        statement (ast.Assert): The statement to read.

    Returns:
        bool | None: True where it never raises, False where it always
            does, None where neither is known.
    '''

    answer = _written_truth(statement.test)

    if answer:
        return True

    if statement.msg is not None and not _quiet_expression(statement.msg):
        return None

    return answer


def _written_could_raise(statement: ast.stmt) -> bool:

    '''Whether giving a value a name, or a `try`, could raise.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: Whether that statement could raise where it stands, and
            whether a statement holding a block of its own could.
    '''

    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
        return _given_could_raise(statement)

    if isinstance(statement, (ast.Try, ast.TryStar)):
        return _tried_could_raise(statement)

    return _holder_could_raise(statement)


@functools.cache
def _plain_errors() -> frozenset[str]:

    '''Return the errors the language carries that any call can build.

    Most take whatever they are given. A group and the errors about
    letters ask for an exact number of values and refuse the call
    otherwise, and the errors about the system around the program are
    chosen by the number they are given, so a raise of any of those
    takes something other than what it names.

    Returns:
        frozenset[str]: The names of the rest.
    '''

    return frozenset(
        name
        for name, held in vars(builtins).items()
        if isinstance(held, type)
        and issubclass(held, BaseException)
        and _built_as_itself(held)
        and _built_from_anything(held)
    )


def _built_as_itself(held: type) -> bool:

    '''Whether building an error always gives that very error.

    The errors about the system around the program are chosen by the
    number they are given: asking for one by name can hand back
    another, and some of them refuse values the rest take. None of
    that family is read as built plainly.

    Args:
        held (type): The error to build.

    Returns:
        bool: True where the name written is the error built.
    '''

    return not issubclass(held, OSError)


def _built_from_anything(held: type) -> bool:

    '''Whether an error can be built from any number of values.

    Args:
        held (type): The error to build.

    Returns:
        bool: True where it takes none, one and two without refusing.
    '''

    for count in range(_BUILT_WITH):

        try:
            held(*([None] * count))

        except TypeError:
            return False

    return True


def _as_line(written: str) -> int:

    '''Return a line number as written, or one past every file.

    A number too long to turn into one at all is answered with a line
    no file reaches, so the citation is refused for running past the
    end rather than ending the run.

    Args:
        written (str): The number as the row wrote it.

    Returns:
        int: That number, or one past every file.
    '''

    if len(written) > _LINE_DIGITS:
        return _PAST_EVERY_FILE

    return int(written)


def _as_count(written: str) -> int:

    '''Return a count as written, or one no count reaches.

    A number too long to turn into one at all is answered with a figure
    nothing counted could match, so the claim is reported as wrong
    rather than ending the run.

    Args:
        written (str): The number as the page wrote it, commas and all.

    Returns:
        int: That number, or one past every count.
    '''

    return _as_line(written.replace(',', ''))


def _nothing_written(held: ast.expr) -> bool:

    '''Whether an expression is written out as nothing at all.

    Args:
        held (ast.expr): The expression to read.

    Returns:
        bool: True where it is nothing.
    '''

    return isinstance(held, ast.Constant) and held.value is None


def _error_written_quietly(held: ast.expr) -> bool:

    '''Whether what is written as an error is worked out without raising.

    An error the language carries, named plainly or called with values
    written out, is — so long as any number of values will build it; a
    group and the errors about letters ask for an exact number and
    refuse the call otherwise. A word named in that call is not: the
    errors the language carries take none, and refuse the call where
    one is given.

    Args:
        held (ast.expr): What is written.

    Returns:
        bool: True where working it out could not raise.
    '''

    named = held
    given: list[ast.expr] = []

    if isinstance(named, ast.Call):
        if named.keywords:
            return False

        given = list(named.args)
        named = named.func

    return (
        _kind_named(named) in _plain_errors()
        and all(_quiet_expression(part) for part in given)
    )


def _raised_quietly(statement: ast.Raise) -> bool:

    '''Whether working out what a raise takes could not itself raise.

    A bare raise works nothing out. An error the language carries,
    named plainly or called with values written out and nothing named
    by word, is worked out without raising anything but itself; the
    raise is then the way out it says it is, and nothing more. What a
    raise names as its cause is worked out too, and must be nothing at
    all or such an error.

    Args:
        statement (ast.Raise): The statement to read.

    Returns:
        bool: True where nothing but the raise itself could come of it.
    '''

    if statement.cause is not None and not (
        _nothing_written(statement.cause) or _error_written_quietly(statement.cause)
    ):
        return False

    return statement.exc is None or _error_written_quietly(statement.exc)


def _given_could_raise(statement: ast.Assign | ast.AnnAssign) -> bool:

    '''Whether giving a value a name could raise where it stands.

    Working out the value could, and so could handing it to anything
    but a plain name: an attribute or a subscript asks the thing it
    sits on, and several names at once ask the value to come apart.
    A name given no value at all is still worked out where it is more
    than a name.

    Args:
        statement (ast.Assign): The statement to read.

    Returns:
        bool: True where it could raise.
    '''

    given: list[ast.expr] = []

    if isinstance(statement, ast.AnnAssign):
        if not _quiet_expression(statement.annotation):
            return True

        given = [statement.target]

    else:
        given = list(statement.targets)

    if statement.value is None:
        return any(not isinstance(name, ast.Name) for name in given)

    if not _quiet_expression(statement.value):
        return True

    return any(not _takes_the_value(name, statement.value) for name in given)


def _takes_the_value(name: ast.expr, value: ast.expr) -> bool:

    '''Whether what a value is given to can take it without raising.

    A plain name takes anything. Names written out together take a
    value written out with one thing for each of them, whatever holds
    those things; where one of the names is starred it takes what is
    left over, so there need only be enough to go round. An `and` or
    an `or` is read as the part it stands as. Anything else asks the
    value or the thing it sits on something, and could raise.

    Args:
        name (ast.expr): What the value is given to.
        value (ast.expr): The value being given.

    Returns:
        bool: True where handing it over could not raise.
    '''

    if isinstance(name, ast.Name):
        return True

    if not isinstance(name, (ast.Tuple, ast.List)):
        return False

    if isinstance(value, ast.BoolOp):
        stands = _part_that_stands(value)

        return stands is not None and _takes_the_value(name, stands)

    return _enough_to_go_round(name, _written_as(value))


def _plainly_named(part: ast.expr) -> bool:

    '''Whether one of several names a value is given to is a plain one.

    A starred name takes what is left over, and is read for the name
    it holds.

    Args:
        part (ast.expr): One of the names written out.

    Returns:
        bool: True where it is a name and nothing more.
    '''

    if isinstance(part, ast.Starred):
        return isinstance(part.value, ast.Name)

    return isinstance(part, ast.Name)


def _enough_to_go_round(name: ast.Tuple | ast.List, held: tuple[Any] | None) -> bool:

    '''Whether a value written out has a thing for each name in a row.

    Where one of the names is starred it takes whatever is left over,
    so there need only be enough for the rest.

    Args:
        name (ast.Tuple): The names the value is given to.
        held (tuple[Any] | None): The value written out, or None.

    Returns:
        bool: True where handing it over could not raise.
    '''

    if held is None or not isinstance(held[0], _GONE_OVER):
        return False

    if any(not _plainly_named(part) for part in name.elts):
        return False

    wanted = [part for part in name.elts if not isinstance(part, ast.Starred)]

    if len(wanted) < len(name.elts):
        return len(held[0]) >= len(wanted)

    return len(held[0]) == len(wanted)


def _tried_could_raise(statement: ast.Try | ast.TryStar) -> bool:

    '''Whether a `try` statement could raise where it stands.

    A body nothing in which could raise reaches no handler, so only
    its `else` and its `finally` are left to ask — and the `else` only
    where the body reaches its end. Otherwise the handlers are tried:
    the kind each names is worked out, and a handler that runs could
    raise of its own. A raise the handlers do not catch is a way out
    of the statement rather than something it could raise unsaid, and
    is read as that.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        bool: True where it could raise.
    '''

    if _may_raise(statement.finalbody):
        return True

    held = _block_ways(statement.body)
    unsaid = _may_raise(statement.body)

    grouped = isinstance(statement, ast.TryStar)

    if any(
        _kind_could_raise(handler, grouped=grouped)
        for handler in _handlers_tried(statement)
    ):
        return True

    if any(_may_raise(handler.body) for handler in _handlers_that_run(statement)):
        return True

    if unsaid and not _catches_anything(statement):
        return True

    return _CARRIES_ON in held and _may_raise(statement.orelse)


def _names_known_errors(named: ast.expr) -> bool:

    '''Whether what is named is nothing but errors the language carries.

    Such a name is bound wherever the file runs, so working it out
    raises nothing. A name the project binds itself could be anything
    by then, and anything else named is worked out as it stands.

    Args:
        named (ast.expr): The kinds named, one or several.

    Returns:
        bool: True where each is an error the language carries.
    '''

    held = named.elts if isinstance(named, ast.Tuple) else [named]

    return all(_kind_named(part) in _KNOWN_ERRORS for part in held)


def _kind_could_raise(handler: ast.ExceptHandler, *, grouped: bool) -> bool:

    '''Whether working out the kind a handler names could raise.

    The kind is worked out as a raise arrives, whether or not the
    handler then runs, and raises nothing of its own only where every
    kind named is an error the language itself carries. A handler of a
    `try` that takes errors in groups cannot name a group itself, and
    is refused where it does.

    Args:
        handler (ast.ExceptHandler): The handler to read.
        grouped (bool): Whether its `try` takes errors in groups.

    Returns:
        bool: True where working its kind out could raise.
    '''

    if handler.type is None:
        return False

    if grouped and _names_a_group(handler.type):
        return True

    return not _names_known_errors(handler.type)


def _names_a_group(named: ast.expr) -> bool:

    '''Whether what a handler names is a group of errors.

    Args:
        named (ast.expr): The kinds named, one or several.

    Returns:
        bool: True where one of them is such a group.
    '''

    held = named.elts if isinstance(named, ast.Tuple) else [named]

    return any(
        isinstance(part, ast.Name) and part.id in _GROUPED_ERRORS for part in held
    )


def _holder_could_raise(statement: ast.stmt) -> bool:

    '''Whether a statement holding a block of its own could raise.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: Whether a loop, an `if` or a `match` could raise where it
            stands; True for anything else.
    '''

    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        return _loop_could_raise(statement)

    if isinstance(statement, ast.If):
        return _branch_could_raise(statement)

    if isinstance(statement, ast.Match):
        return _match_could_raise(statement)

    return True


def _branch_could_raise(statement: ast.If) -> bool:

    '''Whether an `if` statement could raise where it stands.

    Working out the condition could, and so could the arm that runs.
    Where the condition is not written out, either arm could.

    Args:
        statement (ast.If): The statement to read.

    Returns:
        bool: True where it could raise.
    '''

    if not _quiet_expression(statement.test):
        return True

    answer = _written_truth(statement.test)

    if answer is None:
        return _may_raise(statement.body) or _may_raise(statement.orelse)

    return _may_raise(statement.body if answer else statement.orelse)


def _pattern_could_raise(pattern: ast.pattern) -> bool:

    '''Whether weighing a pattern against a value could raise.

    A pattern naming a kind looks that name up, and one written as a
    value through something else — an attribute, say — looks that up
    too; either could raise before anything is matched. The
    alternatives of an `|` are tried from the left, so each is read,
    however wide the one after it; so is what a name is bound to, and
    so is every part of a sequence or a mapping written out.

    Args:
        pattern (ast.pattern): The pattern to read.

    Returns:
        bool: True where weighing it could raise.
    '''

    if isinstance(pattern, ast.MatchClass):
        return True

    if isinstance(pattern, ast.MatchValue):
        return not _quiet_expression(pattern.value)

    if isinstance(pattern, ast.MatchMapping) and any(
        not _quiet_expression(key) for key in pattern.keys
    ):
        return True

    return any(_pattern_could_raise(held) for held in _held_patterns(pattern))


def _held_patterns(pattern: ast.pattern) -> list[ast.pattern]:

    '''Return the patterns a pattern holds.

    Args:
        pattern (ast.pattern): The pattern to read.

    Returns:
        list[ast.pattern]: Its alternatives, its parts, or what it
            binds; nothing for a pattern holding none.
    '''

    if isinstance(pattern, ast.MatchAs):
        return [pattern.pattern] if pattern.pattern is not None else []

    if isinstance(pattern, ast.MatchOr):
        return list(pattern.patterns)

    if isinstance(pattern, (ast.MatchSequence, ast.MatchMapping)):
        return list(pattern.patterns)

    return []


def _match_could_raise(statement: ast.Match) -> bool:

    '''Whether a `match` statement could raise where it stands.

    Working out the subject could, and so could a pattern looking a
    name up, a guard that is not written out, and the body of a case
    that runs. A pattern is weighed before its guard is read, so
    a guard that never holds keeps back the body alone. By the time a
    case that takes every value is reached its guard has held, a guard
    that failed having been passed over and one not written out having
    answered the question already, so nothing after such a case is
    read; a case taking less than every value leaves what stands after
    it to be read, the value reaching those cases.

    Args:
        statement (ast.Match): The statement to read.

    Returns:
        bool: True where it could raise.
    '''

    if not _quiet_expression(statement.subject):
        return True

    for case in statement.cases:

        if _pattern_could_raise(case.pattern):
            return True

        answer = True if case.guard is None else _written_truth(case.guard)

        if case.guard is not None and not _quiet_expression(case.guard):
            return True

        if answer is False:
            continue

        if _may_raise(case.body):
            return True

        if _takes_anything(case.pattern):
            return False

    return False


def _loop_could_raise(statement: ast.For | ast.AsyncFor | ast.While) -> bool:

    '''Whether a loop could raise where it stands.

    Working out what it goes over could raise, and so could its body
    where that runs, and its `else` where the loop reaches it. Going over something with `async
    for` asks the thing itself for each turn, which could raise before
    the body runs at all, and so does going over what is written out
    as something no turn can be taken from. Handing each turn to
    anything but a plain name could raise as well, what comes out
    having to come apart to fit — though a loop that takes no turn
    hands nothing over, and reads for its `else` alone.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        bool: True where it could raise.
    '''

    gone_over = (
        statement.test if isinstance(statement, ast.While) else statement.iter
    )

    if not _quiet_expression(gone_over) or isinstance(statement, ast.AsyncFor):
        return True

    if _runs_nothing(statement):
        return _may_raise(statement.orelse)

    if not isinstance(statement, ast.While) and (
        _goes_over_nothing(gone_over) or not isinstance(statement.target, ast.Name)
    ):
        return True

    if not _reaches_its_else(statement):
        return _may_raise(statement.body)

    return _may_raise(statement.body) or _may_raise(statement.orelse)


def _quiet_expression(held: ast.expr) -> bool:

    '''Whether working out an expression could not raise.

    A constant could not, nor a list or tuple written out of such, nor
    `not` over them, nor a comparison of constants that answers. An
    `and` or an `or` is read in the parts that are worked out. A set and a mapping ask what they hold to be
    hashable. Everything else is read as able to: a name may be
    unbound, a call may raise, and a sum may refuse what it is given.

    Args:
        held (ast.expr): The expression to read.

    Returns:
        bool: True where it could not raise.
    '''

    if _written_as(held) is not None:
        return True

    if isinstance(held, ast.UnaryOp) and isinstance(held.op, ast.Not):
        return _quiet_expression(held.operand)

    if isinstance(held, ast.BoolOp):
        return _quiet_both(held)

    return isinstance(held, ast.Compare) and _written_comparison(held) is not None


def _quiet_both(held: ast.BoolOp) -> bool:

    '''Whether working out an `and` or an `or` could not raise.

    Only the parts that are worked out are read: a part after one that
    settles the answer is never reached. A part that could not raise
    is written out, and so settles its own answer, which is why no
    part after an unknown one need be weighed.

    Args:
        held (ast.BoolOp): The expression to read.

    Returns:
        bool: True where it could not raise.
    '''

    wanted = isinstance(held.op, ast.Or)

    for part in held.values[:-1]:

        if not _quiet_expression(part):
            return False

        if _written_truth(part) is wanted:
            return True

    return _quiet_expression(held.values[-1])


def _endless(test: ast.expr) -> bool:

    '''Whether a loop's condition is written as one that always holds.

    Args:
        test (ast.expr): The condition.

    Returns:
        bool: True where it is written out and holds.
    '''

    return _written_truth(test) is True


def _leaves_the_path(body: list[ast.stmt]) -> bool:

    '''Whether a branch body makes an alternative of the code after it.

    Leaving by return always does, whether the return is written there
    or reached through an `if`, a `try` or a `match` that returns on
    every path. Any other way of leaving does so only where the body
    also acts: one that merely builds a message and raises is a guard,
    and citing it beside later code describes an order of checks.

    A call that raises inside a helper cannot be told from one that
    returns, so a branch leaving only that way reads as a guard.

    Args:
        body (list[ast.stmt]): The statements of the branch.

    Returns:
        bool: True where the branch is an arm rather than a guard.
    '''

    ways = _plain_ways(_block_ways(body))

    if _CARRIES_ON in ways:
        return False

    if ways == {'return'}:
        return True

    return _body_acts(body)


def _body_acts(body: list[ast.stmt]) -> bool:

    '''Whether a branch body does anything besides leave the path.

    Every statement is read, nested ones included, since a branch whose
    whole body is an inner `if` still acts inside its arms.

    Args:
        body (list[ast.stmt]): The statements of the branch.

    Returns:
        bool: True where the branch acts before leaving.
    '''

    return any(_statement_acts(statement) for statement in body)


def _statement_acts(statement: ast.stmt) -> bool:

    '''Whether one statement does something beyond leaving or naming.

    A statement holding others acts where one of those does, or where
    what it is given to work on acts: a guard wrapped in a `try`, an
    `if` or a loop is still a guard, while `with reject(x):` acts
    before anything in its body.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: True where it acts.
    '''

    if isinstance(statement, (ast.Return, ast.Continue, ast.Break, ast.Pass)):
        return False

    if isinstance(statement, ast.Raise):
        return any(isinstance(node, ast.Call) for node in _raised_parts(statement))

    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
        return not _only_builds_a_message(statement)

    if isinstance(statement, _HOLDERS):
        return _header_acts(statement) or any(
            _body_acts(block) for block in _child_blocks(statement)
        )

    return True


def _header_acts(statement: ast.stmt) -> bool:

    '''Whether what a statement is given to work on acts.

    A context manager, a condition, a subject, a thing iterated over
    or a case's guard is worked out before the body runs, so a call
    there is an act. A pattern is not among them: it tests a value
    and holds no call of its own.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: True where one of those holds a call.
    '''

    given: list[ast.AST] = []

    for name in ('test', 'subject', 'iter'):
        found = getattr(statement, name, None)

        if found is not None:
            given.append(found)

    given += [
        item.context_expr for item in getattr(statement, 'items', []) or []
    ]
    given += [
        case.guard for case in getattr(statement, 'cases', []) or []
        if case.guard is not None
    ]

    return any(
        isinstance(node, ast.Call) for held in given for node in ast.walk(held)
    )


def _raised_parts(statement: ast.Raise) -> list[ast.AST]:

    '''Return the nodes a raise evaluates beyond naming its exception.

    Args:
        statement (ast.Raise): The raise to read.

    Returns:
        list[ast.AST]: Every node inside its arguments and its cause.
    '''

    inner: list[ast.expr] = [statement.cause] if statement.cause else []
    raised = statement.exc

    if isinstance(raised, ast.Call):
        inner.extend(raised.args)
        inner.extend(word.value for word in raised.keywords)
    elif raised is not None:
        inner.append(raised)

    return [node for part in inner for node in ast.walk(part)]


def _only_builds_a_message(statement: ast.stmt) -> bool:

    '''Whether a statement does nothing but make a value to raise with.

    An assignment qualifies only where it names a plain local and nothing
    in it is called: a call may act however its result is stored, and an
    assignment to an attribute or an item changes something outside.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: True where the statement merely builds a value.
    '''

    if isinstance(statement, ast.AnnAssign):
        targets: list[ast.expr] = [statement.target]
    elif isinstance(statement, ast.Assign):
        targets = list(statement.targets)
    else:
        return False

    if any(not isinstance(target, ast.Name) for target in targets):
        return False

    return not any(isinstance(node, ast.Call) for node in ast.walk(statement))


def _identity(name: str) -> str | None:

    '''Return one name for a cited file, whatever spelling reached it.

    A nickname resolves to a path written relative to its repository,
    a bare name to one under a pinned root. Both are cut back to the
    path inside the repository, so the two spellings meet.

    Args:
        name (str): The name a citation used.

    Returns:
        str | None: That path, or None where the name resolves to none.
    '''

    path = _resolve_source(name)

    if path is None:
        return None

    inside = _tree_relative(path)

    return inside[len('../Nexus/'):] if inside.startswith('../Nexus/') else inside


def _one_file(name: str, other: str) -> bool:

    '''Whether two citation names reach the same file in a pinned tree.

    Args:
        name (str): One name, as a row wrote it.
        other (str): The other name.

    Returns:
        bool: True where both resolve to one path.
    '''

    if name == other:
        return True

    try:
        here, there = _identity(name), _identity(other)
    except BaselineReadError:
        return False

    return here is not None and here == there


def _exclusive_citations(
    cited: list[tuple[str, int, int, int]],
    cache: _SourceFacts,
    row: str,
) -> str | None:

    '''Report two citations landing on both sides of a branch.

    Each citation's whole range is compared, and must sit wholly inside
    one arm — a range reaching past its arm is a citation of the wider
    construct, not of that arm. A range containing the other is passed
    over for the same reason. A branch that only builds a message and
    raises is a guard, and citing it beside later code describes an
    order of checks; one that acts before leaving is an arm.

    Args:
        cited (list[tuple[str, int, int, int]]): Each citation as its
            source name, first line, last line, and where it sits in the
            source half.
        cache (_SourceFacts): Where the branch spans are read from.
        row (str): The evidence row, read for a marker between a pair.

    A row carrying more references than can be weighed is reported as
    that rather than weighed, every pair of them being read.

    Returns:
        str | None: The clash found, or None where there is none.
    '''

    if len(cited) > _REFERENCES_AT_MOST:
        return (
            f'cites {len(cited)} line references, past the '
            f'{_REFERENCES_AT_MOST} a row is weighed in pairs over'
        )

    source = row.split(' | ', 1)[1] if ' | ' in row else row

    for index, (key, start, end, at) in enumerate(cited):
        facts = cache.peek(key)

        if facts is None:
            continue

        for other_key, other_start, other_end, other_at in cited[index + 1:]:

            if not _one_file(key, other_key) or _marked_between(source, at, other_at):
                continue

            if _opposed(_spans(start, end), _spans(other_start, other_end), facts):
                return f'{key}:{start} and {other_start} are mutually exclusive branches'

    return None


def _opposed(here: set[int], there: set[int], facts: _FileFacts) -> bool:

    '''Whether two cited ranges sit wholly in opposite arms of one branch.

    Args:
        here (set[int]): The lines one citation covers.
        there (set[int]): The lines the other covers.
        facts (_FileFacts): The branch arms of the file they cite.

    Returns:
        bool: True where each sits wholly inside a different arm.
    '''

    if here <= there or there <= here:
        return False

    return any(
        (here <= first and there <= second) or (here <= second and there <= first)
        for first, second in facts.exclusive
    )


def _spans(start: int, end: int) -> set[int]:

    '''Return every line a citation covers.

    The whole range is kept. A range cut short would stop containing
    what it contains, and a citation of a wider construct would read
    as a citation of one arm of it.

    Args:
        start (int): The first line cited.
        end (int): The last line cited.

    Returns:
        set[int]: Those lines.
    '''

    return set(range(start, max(start, end) + 1))


def _resolve_source(name: str) -> Path | None:

    '''Resolve a cited name against the pinned trees, not the working one.

    A name carrying a directory is looked for at that exact path. A bare
    name is looked for across every pinned tree at once and refused
    where more than one file answers to it, whether in one tree or in
    two, so a name both repositories hold has to be written as a path.
    '''

    if name in SOURCE_FILES:
        return SOURCE_FILES[name]

    if '/' in name:

        for root, commit in _pins():

            if name in _pinned_paths(root, commit):
                return root / name

        return None

    stem = name[:-3] if name.endswith('.py') else name
    wanted = f'{stem}.py'

    found = [
        (root, entry)
        for root, commit in _pins()
        for entry in _pinned_paths(root, commit)
        if entry.startswith(SEARCH_PREFIXES) and entry.rsplit('/', 1)[-1] == wanted
    ]

    if len(found) != 1:
        return None

    root, entry = found[0]

    return root / entry


def _row_sources(row: str) -> list[tuple[int, str]]:

    '''Return where each source name appears in a row, in order.

    Args:
        row (str): One evidence row, as `claim | source`.

    Returns:
        list[tuple[int, str]]: Position and name, earliest first.
    '''

    hits = [
        (m.start(), key)
        for key in SOURCE_FILES
        for m in re.finditer(rf'(?<![\w/]){re.escape(key)}(?![\w])', row)
    ]
    hits += [(m.start(), m.group(1)) for m in FILE_REF.finditer(row)]

    return sorted(hits)


def _has_wildcard_import(tree: ast.AST) -> bool:

    '''Whether the module imports everything from somewhere.

    A star import can rebind any name, so no binding can be trusted.
    '''

    return any(
        isinstance(node, ast.ImportFrom)
        and any(alias.name == '*' for alias in node.names)
        for node in ast.walk(tree)
    )


def _protocol_names(tree: ast.AST) -> set[str]:

    '''Return the module-level names bound to `typing.Protocol`.'''

    names: set[str] = set()

    if not isinstance(tree, ast.Module) or _has_wildcard_import(tree):
        return names

    for node in tree.body:

        if isinstance(node, ast.ImportFrom) and node.module == 'typing' and not node.level:
            names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == 'Protocol'
            )

    return names - _rebound_names(tree)


def _bound_names(node: ast.AST) -> set[str]:

    '''Return every name a target expression binds, unpacking included.'''

    if isinstance(node, ast.Name):
        return {node.id}

    if isinstance(node, (ast.Tuple, ast.List)):
        return {name for element in node.elts for name in _bound_names(element)}

    if isinstance(node, ast.Starred):
        return _bound_names(node.value)

    return set()


def _imported_names(node: ast.Import | ast.ImportFrom) -> set[str]:

    '''Return the names one import binds, bar `Protocol` from `typing`.

    Args:
        node (ast.Import | ast.ImportFrom): The import to read.

    Returns:
        set[str]: The names it binds.
    '''

    withheld = (
        isinstance(node, ast.ImportFrom) and node.module == 'typing' and not node.level
    )

    return {
        alias.asname or alias.name.split('.')[0]
        for alias in node.names
        if not (withheld and alias.name == 'Protocol')
    }


def _taken_names(args: ast.arguments) -> set[str]:

    """Return the names a signature binds.

    Args:
        args (ast.arguments): The signature to read.

    Returns:
        set[str]: Every name it binds, starred ones included.
    """

    held = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    held += [one for one in (args.vararg, args.kwarg) if one is not None]

    return {one.arg for one in held}


def _rebound_names(tree: ast.AST) -> set[str]:

    '''Return names given some other value anywhere in the module.'''

    rebound: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            rebound.add(node.name)

            if not isinstance(node, ast.ClassDef):
                rebound.update(_taken_names(node.args))

        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            rebound.update(_imported_names(node))

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                rebound.update(_bound_names(target))

        elif isinstance(
            node, (ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor),
        ):
            rebound.update(_bound_names(node.target))

        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:

                if item.optional_vars is not None:
                    rebound.update(_bound_names(item.optional_vars))

        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            rebound.add(node.name)

        elif isinstance(node, ast.NamedExpr):
            rebound.update(_bound_names(node.target))

        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name is not None:
            rebound.add(node.name)

        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            rebound.add(node.rest)

    return rebound


def _is_protocol(node: ast.ClassDef, protocol_names: set[str]) -> bool:

    '''Whether a class lists an imported `typing.Protocol` among its bases.'''

    return any(
        isinstance(base, ast.Name) and base.id in protocol_names
        for base in node.bases
    )


def _is_stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:

    '''Whether a method's whole body is a docstring and an ellipsis.'''

    body = list(node.body)

    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]

    return len(body) == 1 and (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is Ellipsis
    )


def _protocol_lines(tree: ast.AST) -> set[int]:

    '''Return the signature lines of a Protocol's own stub methods.

    A stub's body is `...`, so its signature is the whole of what it
    states. Citing one cites the declaration. Nothing with a body is
    exempted, and nothing nested inside the class.
    '''

    protocol_names = _protocol_names(tree)
    lines: set[int] = set()

    if not protocol_names or not isinstance(tree, ast.Module):
        return lines

    for node in tree.body:

        if not (isinstance(node, ast.ClassDef) and _is_protocol(node, protocol_names)):
            continue

        for member in node.body:

            if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if not _is_stub(member):
                continue

            lines.update(range(member.lineno, member.body[0].lineno))

    return lines


def _signature_lines(path: Path) -> set[int]:

    '''Return the lines of a declaration that has a body below it.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers, Protocol stubs excepted.
    '''

    try:
        tree = ast.parse(_source_text(path))
    except (OSError, SyntaxError):
        return set()

    lines: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        if not node.body:
            continue

        lines.update(range(node.lineno, node.body[0].lineno))

    return lines - _protocol_lines(tree)


def _prose_words(text: str) -> int:

    '''Return the words a page spends on prose and headings.

    Args:
        text (str): The rows to scan, one per line.

    Returns:
        int: The count, navigation links and tables excluded.
    '''

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


def _claims_a_message(claim: str) -> bool:

    '''Whether a claim says something about a logged message.

    The claim alone is read. A source saying the word would otherwise
    exempt whatever the claim beside it says.

    Args:
        claim (str): The claim half of an evidence row.

    Returns:
        bool: True where it names a log line, a warning or a message.
    '''

    lowered = claim.lower()

    return any(word in lowered for word in ('log line', 'warning', 'logged', 'message'))


def _claims_a_docstring(claim: str) -> bool:

    '''Whether a claim says something about a docstring itself.

    The claim alone is read. A source saying the word would otherwise
    exempt whatever the claim beside it says.

    Args:
        claim (str): The claim half of an evidence row.

    Returns:
        bool: True where it says the subject is a docstring.
    '''

    return 'docstring' in claim.lower()


def _log_lines(path: Path) -> set[int]:

    '''Return every line a logging call covers.

    A call spread over several lines is logging on all of them, so the
    message it is built from cannot be cited as the thing happening.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers.
    '''

    try:
        tree = ast.parse(_source_text(path))
    except (OSError, SyntaxError):
        return set()

    lines: set[int] = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Call) and _is_a_log_call(node):
            lines |= set(range(node.lineno, (node.end_lineno or node.lineno) + 1))

    return lines


def _is_a_log_call(node: ast.Call) -> bool:

    '''Whether a call is made on the module's logger.

    Args:
        node (ast.Call): The call to read.

    Returns:
        bool: True where it calls a method on `_log`.
    '''

    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == '_log'
    )


@dataclass(frozen=True)
class _FileFacts:

    '''Hold what one cited file states, read once at its pinned commit.

    Args:
        length (int): Number of lines in the file.
        blanks (set[int]): Lines holding nothing but space.
        comments (set[int]): Lines holding nothing but a comment.
        docstrings (set[int]): Lines inside a docstring.
        logs (set[int]): Lines opening a logging call.
        signatures (set[int]): Lines of a declaration with a body below it.
        exclusive (list[tuple[set[int], set[int]]]): Pairs of line sets that
            cannot both run for one input.
        before_a_raise (dict[int, frozenset[int]]): Where a statement ends
            with a raise standing next after it in the same block, that
            ending line against the raise's own lines.
        unreachable (set[int]): Lines of a handler nothing can arrive at.
        missed (dict[int, int]): Where each handler whose body cannot run
            starts and ends, its own line included.
    '''

    length: int
    blanks: set[int]
    comments: set[int]
    docstrings: set[int]
    logs: set[int]
    signatures: set[int]
    exclusive: list[tuple[set[int], set[int]]]
    before_a_raise: dict[int, frozenset[int]]
    unreachable: set[int]
    missed: dict[int, int]


class _SourceFacts:

    '''Read each cited file once and answer from memory thereafter.'''

    def __init__(self) -> None:

        '''Start with nothing read.'''

        self._known: dict[str, _FileFacts] = {}

    def peek(self, key: str) -> _FileFacts | None:

        '''Return what is already known of a file, without reading it.

        Args:
            key (str): The name the citation used.

        Returns:
            _FileFacts | None: What that file states, or None where it has
                not been read.
        '''

        return self._known.get(key)

    def of(self, key: str, path: Path) -> _FileFacts:

        '''Return what a cited file states, reading it on first ask.

        Args:
            key (str): The name the citation used.
            path (Path): The file that name resolved to.

        Returns:
            _FileFacts: What that file states.

        Raises:
            BaselineReadError: The file cannot be read at its pinned commit.
        '''

        if key not in self._known:
            self._known[key] = _FileFacts(
                length=len(_source_text(path).splitlines()),
                blanks=_blank_lines(path),
                comments=_comment_lines(path),
                docstrings=_docstring_lines(path),
                logs=_log_lines(path),
                signatures=_signature_lines(path),
                exclusive=_exclusive_spans(path),
                before_a_raise=_before_a_raise(path),
                unreachable=_unreachable_lines(path),
                missed=_missed_handlers(path),
            )

        return self._known[key]


def _unreachable_lines(path: Path) -> set[int]:

    '''Return the lines of every handler nothing can arrive at.

    A handler whose every kind an earlier handler already catches
    cannot run, and nor can one of a `try` whose body raises nothing at
    all. Citing the body of such a handler cites lines no input
    reaches. Its own line goes with the body only where nothing is
    tried against it — where no raise reaches it looking for a handler
    — since a handler that is tried and misses still has the kind it
    names worked out.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers.
    '''

    held: set[int] = set()

    try:
        tree = ast.parse(_source_text(path))
    except SyntaxError:
        return held

    _reading(tree)

    for node in ast.walk(tree):

        if not isinstance(node, (ast.Try, ast.TryStar)):
            continue

        for handler, tried, runs in _handler_reach(node):

            if runs:
                continue

            closing = handler.body[-1].end_lineno or handler.lineno
            opening = handler.body[0].lineno if tried else handler.lineno
            held |= set(range(opening, closing + 1))

    return held


def _missed_handlers(path: Path) -> dict[int, int]:

    """Return where each handler whose body cannot run starts and ends.

    A handler that is tried and misses has the kind it names worked
    out and its body passed over, so a citation taking in that line
    and the body below it is citing lines that do not run together.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        dict[int, int]: That handler's own line against its last.
    """

    held: dict[int, int] = {}

    try:
        tree = ast.parse(_source_text(path))
    except SyntaxError:
        return held

    _reading(tree)

    for node in ast.walk(tree):

        if not isinstance(node, (ast.Try, ast.TryStar)):
            continue

        for handler, _tried, runs in _handler_reach(node):

            if not runs:
                held[handler.lineno] = (
                    handler.body[-1].end_lineno or handler.lineno
                )

    return held


def _before_a_raise(path: Path) -> dict[int, frozenset[int]]:

    '''Return where a statement stands immediately before a raise.

    A claim of a refusal cites the guard that refuses. Where the range
    stops on the line before the raise, it cites the condition and the
    message the raise is given and leaves out the refusal itself, so the
    lines cited do not show it. A range ending on a raise of its own is
    not short of one: the raise standing next after it is a second way
    out rather than the one cited.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        dict[int, frozenset[int]]: The ending line of each statement a
            raise stands next after, against that raise's lines.
    '''

    found: dict[int, frozenset[int]] = {}

    try:
        tree = ast.parse(_source_text(path))
    except SyntaxError:
        return found

    raising = {
        line
        for node in ast.walk(tree)
        if isinstance(node, ast.Raise)
        for line in range(node.lineno, (node.end_lineno or node.lineno) + 1)
    }

    for node in ast.walk(tree):

        if not isinstance(node, ast.stmt):
            continue

        for body in _child_blocks(node):

            for before, statement in itertools.pairwise(body):

                if not isinstance(statement, ast.Raise):
                    continue

                ending = before.end_lineno or before.lineno

                if ending in raising:
                    continue

                found[ending] = frozenset(
                    range(statement.lineno, (statement.end_lineno or statement.lineno) + 1),
                )

    return found


def _cut_short_of_a_raise(
    claim: str, cited: list[tuple[str, int, int, int]], cache: _SourceFacts,
) -> str | None:

    '''Return a complaint where a refusal claim stops short of its raise.

    Args:
        claim (str): The claim as the row wrote it.
        cited (list[tuple[str, int, int, int]]): Each citation as file,
            first line, last line and where it was written.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        str | None: The complaint, or None where nothing is cut short.
    '''

    if not REFUSAL_RE.search(claim):
        return None

    taken = {
        (key, line) for key, start, end, _ in cited for line in range(start, end + 1)
    }

    for key, _, end, _ in cited:
        facts, note = _facts_for(key, cache)

        if facts is None or note is not None:
            continue

        raised = facts.before_a_raise.get(end)

        if raised is not None and not any((key, line) in taken for line in raised):
            return (
                f'cites `{key}` up to {end}, stopping on the line before the '
                f'raise at {min(raised)} that does the refusing'
            )

    return None


def _docstring_citations(text: str, cache: _SourceFacts) -> list[str]:

    '''Return the citations that land on prose rather than on code.

    Args:
        text (str): The rows to scan, one per line.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per bad citation.
    '''

    return [
        note
        for whole in text.splitlines()
        if whole.startswith('|')
        for note in _row_citations(whole, cache)
    ]


def _impossible_line(match: re.Match[str], facts: _FileFacts) -> str | None:

    '''Return why a cited range cannot exist in the file, where it cannot.

    A range running backwards covers nothing, so what it lands on
    cannot be read: it is refused before anything else is asked of it.

    Args:
        match (re.Match[str]): The line reference as the row wrote it.
        facts (_FileFacts): What was read of the cited file.

    Returns:
        str | None: The reason, or None where the line is in range.
    '''

    start = _as_line(match.group(1))
    end = _as_line(match.group(2) or match.group(1))

    if start < 1:
        return 'no such line'

    if end < start:
        return 'a range ending before it starts'

    if end > facts.length:
        return f'past end of file, {facts.length} lines'

    return None


def _citation_facts(
    match: re.Match[str],
    sources: list[tuple[int, str]],
    cache: _SourceFacts,
) -> tuple[str | None, _FileFacts | None, str | None]:

    '''Return the file a citation belongs to and what was read of it.

    Args:
        match (re.Match[str]): The line reference as the row wrote it.
        sources (list[tuple[int, str]]): Where each file is named in the row.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        tuple[str | None, _FileFacts | None, str | None]: The file name,
            what was read of it, and why neither could be had.
    '''

    before = [key for pos, key in sources if pos < match.start()]

    if not before:
        return None, None, UNNAMED

    facts, note = _facts_for(before[-1], cache)

    return before[-1], facts, note


def _citation_note(key: str | None, match: re.Match[str], note: str) -> str:

    '''Return one complaint, named for the file where one is known.

    Args:
        key (str | None): The file name the citation used, where it had one.
        match (re.Match[str]): The line reference as the row wrote it.
        note (str): What is wrong with it.

    Returns:
        str: The complaint.
    '''

    if key is None:
        return f'{match.group(0)} ({note})'

    return f'{key}:{match.group(0)} ({note})'


def _row_citations(whole: str, cache: _SourceFacts) -> list[str]:

    '''Return what one evidence row's citations land on, where not on code.

    Args:
        whole (str): The row, as `claim | source`.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per bad citation, and any branch clash.
    '''

    bad: list[str] = []

    row = whole.split(' | ', 1)[1] if ' | ' in whole else whole
    sources = _row_sources(row)
    cited: list[tuple[str, int, int, int]] = []

    for match in LINE_REF.finditer(row):
        key, facts, note = _citation_facts(match, sources, cache)

        if note is UNCHECKED:
            continue

        if facts is None:
            bad.append(_citation_note(key, match, note or 'unread'))
            continue

        assert key is not None
        note = _impossible_line(match, facts)
        start = _as_line(match.group(1))
        end = _as_line(match.group(2) or match.group(1))

        if note is None:
            cited.append((key, start, end, match.start()))
            note = _what_a_citation_lands_on(start, end, facts, whole)

        if note is not None:
            bad.append(_citation_note(key, match, note))

    clash = _exclusive_citations(cited, cache, whole)

    if clash is not None:
        bad.append(clash)

    cut = _cut_short_of_a_raise(whole.split(' | ', 1)[0], cited, cache)

    if cut is not None:
        bad.append(cut)

    return bad


def _nexus_names() -> set[str]:

    '''Return the file names the ledger attributes to Nexus.

    These are read from the ledger rather than the tree, so a citation
    into Nexus is known for one even where that tree is not checked out.

    Returns:
        set[str]: Those names, each as a bare file name.
    '''

    body = _ledger_sections(LEDGER.read_text(encoding='utf-8')).get('Nexus', '')

    return {Path(named).name for named in LEDGER_PATH_RE.findall(body)}


def _reaches_absent_nexus(key: str) -> bool:

    '''Whether a citation names a Nexus file with no Nexus to read.

    A name carrying a directory is read as written, so only a name
    under `nexus/` is Nexus's; a bare file name is looked for among the
    names the ledger gives Nexus. A Praxis path whose last part happens
    to be one of those is a Praxis path, and is read as one.

    Args:
        key (str): The name the citation used.

    Returns:
        bool: True where the name is Nexus's and that tree is absent.
    '''

    if NEXUS_ROOT.is_dir():
        return False

    named = SOURCE_FILES.get(key)

    if named is not None:
        return str(named).startswith('../Nexus/')

    if '/' in key:
        return key.startswith('nexus/')

    return key in _nexus_names()


def _facts_for(key: str, cache: _SourceFacts) -> tuple[_FileFacts | None, str | None]:

    '''Return what a cited file states, or why it cannot be read.

    Args:
        key (str): The name the citation used.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        tuple[_FileFacts | None, str | None]: What the file states, or the
            reason it could not be read.
    '''

    if _reaches_absent_nexus(key):
        return None, UNCHECKED

    try:
        path = _resolve_source(key)
    except BaselineReadError as exc:
        return None, str(exc)

    if path is None:
        return None, 'unresolved source file'

    try:
        return cache.of(key, path), None
    except BaselineReadError as exc:
        return None, str(exc)


def _what_a_citation_lands_on(
    start: int, end: int, facts: _FileFacts, row: str,
) -> str | None:

    '''Return what a citation lands on, where it is not executable code.

    The whole range is read. A citation refused for its first lines and
    kept for its last would depend on where the reading stopped. A
    range holding nothing but logging, blank lines and comments is
    logging, whichever of them it opens on. Blank lines and comments
    are passed over in weighing whether a range stands inside a
    handler nothing arrives at, since padding a citation with them
    would otherwise answer for the lines that do run.

    Args:
        start (int): The first line cited.
        end (int): The last line cited.
        facts (_FileFacts): What the cited file states.
        row (str): The whole evidence row, whose claim is read for a
            claim about a logged message or about a docstring.

    Returns:
        str | None: What it landed on, or None where it landed on code.
    '''

    span = list(range(start, end + 1))
    bare = facts.blanks | facts.comments | facts.docstrings | facts.signatures
    claim = row.split(_PARTING, 1)[0]

    if _only_says(span, facts):
        return None if _claims_a_docstring(claim) else 'docstring'

    if all(n in bare for n in span):
        return 'no executable line'

    inside = [n for n in span if n in facts.docstrings]

    if start in facts.docstrings or (inside and len(inside) * 2 > len(span)):
        return 'docstring'

    if _only_logs(span, facts) and not _claims_a_message(claim):
        return 'log call'

    if _nothing_arrives_at(span, facts):
        return 'a handler nothing arrives at'

    return None


def _nothing_arrives_at(span: list[int], facts: _FileFacts) -> bool:

    '''Whether a cited range stands in a handler nothing arrives at.

    Every line of it may be such a handler's, blank lines and comments
    padding it answering for nothing. A range inside one handler that
    takes in a line of its body does too, that body never running
    whether or not the kind above it is worked out.

    Args:
        span (list[int]): The lines cited.
        facts (_FileFacts): What the cited file states.

    Returns:
        bool: True where the range is in such a handler.
    '''

    standing = {n for n in span if n not in facts.blanks | facts.comments}

    if not standing:
        return False

    if standing <= facts.unreachable:
        return True

    return bool(standing & facts.unreachable) and any(
        start <= min(standing) and max(standing) <= end
        for start, end in facts.missed.items()
    )


def _only_says(span: list[int], facts: _FileFacts) -> bool:

    '''Whether a cited range is docstring and nothing else that runs.

    A range holding a docstring and nothing but blank lines and
    comments besides is the docstring. One running on into code is
    citing the code, whatever the row says it is quoting.

    Args:
        span (list[int]): The lines the citation covers.
        facts (_FileFacts): What was read of the cited file.

    Returns:
        bool: True where the range is docstring alone.
    '''

    quiet = facts.docstrings | facts.blanks | facts.comments

    return any(line in facts.docstrings for line in span) and all(
        line in quiet for line in span
    )


def _only_logs(span: list[int], facts: _FileFacts) -> bool:

    '''Whether a cited range says nothing but a logged message.

    A range is logging where it holds a logging call and nothing else
    but blank lines and comments. One that opens on a logging call and
    runs on into code is citing the code.

    Args:
        span (list[int]): The lines the citation covers.
        facts (_FileFacts): What was read of the cited file.

    Returns:
        bool: True where the range is logging.
    '''

    if not span:
        return False

    quiet = facts.logs | facts.blanks | facts.comments

    return any(line in facts.logs for line in span) and all(
        line in quiet for line in span
    )


def _write(line: str) -> None:

    '''Write one line of output.

    Args:
        line (str): The line to write.
    '''

    sys.stdout.write(f'{line}\n')


def _register_ids() -> set[str]:

    '''Return every row identifier the register carries.

    Only an identifier opening a table row counts; one written in the
    register's prose is a reference to a row, not a row.

    Returns:
        set[str]: The identifiers.
    '''

    if not REGISTER.exists():
        return set()

    return set(ROW_OPENING.findall(REGISTER.read_text()))


def _last_commit_date(path: Path) -> str | None:

    '''Return the UTC date a path was last committed on.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        str | None: The date, or None where git cannot say.
    '''

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


def _unspaced_headings(body: str) -> list[str]:

    '''Return headings that run straight on from the line above.'''

    lines = body.splitlines()

    return [
        f'heading runs on from the line above: "{line.strip()}"'
        for index, line in enumerate(lines)
        if index > 0 and line.startswith('#') and lines[index - 1].strip()
    ] + [
        f'heading sits mid-line: "{line.strip()}"'
        for line in lines
        if re.search(r'\S\s+#{1,6} ', line)
    ]


def _negative_definitions(body: str) -> list[str]:

    '''Return the sentences defining something by what it is not.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: One complaint per sentence.
    '''

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

    '''Return the paragraph following the title.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        str | None: That paragraph, or None where there is none.
    '''

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

    '''Return the terms another article owns that are first met unlinked.

    A reader meets a term once and needs the link there, so the first
    mention in the prose must carry it. Later mentions are free. A link
    sitting only in the navigation list at the foot does not count, since
    that list is a fallback rather than the way a reader is meant to
    travel.

    Args:
        page (Path): The page being read, which owns its own terms.
        body (str): The page's prose, navigation list included.

    Returns:
        list[str]: One complaint per term first met without its link.
    '''

    prose = body.split('## Related', 1)[0]
    missing: list[str] = []

    for owner, terms in OWNED_TERMS.items():

        if owner == page.name:
            continue

        for term in terms:
            first = prose.lower().find(term.lower())

            if first >= 0 and not _within_link(prose, first, owner):
                missing.append(f'first mentions "{term}" without linking {owner}')

    return missing


def _within_link(body: str, position: int, owner: str) -> bool:

    '''Whether a mention sits inside the text of a link to its owner.

    Args:
        body (str): The page's prose.
        position (int): Where the mention starts.
        owner (str): The file the link must point at.

    Returns:
        bool: True where the mention is the linked text itself.
    '''

    for match in re.finditer(r'\[([^\]]*)\]\(' + re.escape(owner) + r'[^)]*\)', body):

        if match.start(1) <= position < match.end(1):
            return True

    return False


def _label(name: str) -> str:

    '''Return a link label reduced to its comparable form.

    Args:
        name (str): The link target or label to reduce.

    Returns:
        str: The label, case-folded and its spacing normalised.
    '''

    return ' '.join(name.split()).casefold()


def _anchors(text: str) -> set[str]:

    '''Return the anchors a page offers, one per heading.

    Args:
        text (str): The rows to scan, one per line.

    Returns:
        set[str]: Those anchors.
    '''

    slugs = set()

    for heading in HEADING.findall(text):
        slug = re.sub(r'[^a-z0-9 -]', '', heading.lower()).replace(' ', '-')
        slugs.add(slug)

    return slugs


def _link_targets(body: str) -> tuple[list[str], list[str]]:

    '''Return every link target a page names, and the references that miss.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        tuple[list[str], list[str]]: The targets, and one complaint per
            reference whose definition is absent.
    '''

    broken: list[str] = []
    definitions: dict[str, str] = {}
    spans: list[tuple[int, int]] = []

    for match in REF_DEF.finditer(body):
        spans.append((match.start(), match.end()))
        definitions.setdefault(_label(match.group(1)), match.group(2))

    targets = list(MD_LINK.findall(body))

    for match in REF_LINK.finditer(body):
        text, label = match.groups()
        key = _label(label or text)

        if key not in definitions:
            broken.append(f'refers to [{label or text}], which is never defined')
            continue

        targets.append(definitions[key])

    for match in REF_SHORTCUT.finditer(body):
        key = _label(match.group(1))

        if key in definitions and not any(
            start <= match.start() < end for start, end in spans
        ):
            targets.append(definitions[key])

    return targets, broken


def _resolved(target: Path) -> Path | None:

    '''Return a link target as a whole path, where one can be worked out.

    Args:
        target (Path): The path a link names, read from the page.

    Returns:
        Path | None: The whole path, and None where the name holds a
            character no path can, and where the links along it lead
            back to where they started.
    '''

    try:
        return target.resolve()

    except (ValueError, RuntimeError):
        return None


def _found(target: Path) -> bool:

    '''Whether a link target is there to be read.

    Args:
        target (Path): The path a link names.

    Returns:
        bool: True where it exists, False where it does not and where
            the name is one no filesystem will take.
    '''

    try:
        return target.exists()

    except OSError:
        return False


def _rows_of(target: Path) -> str | None:

    '''Return a link target's rows, where they can be read as text.

    Args:
        target (Path): The file or folder a link names.

    Returns:
        str | None: The rows, empty where the target holds none, and None
            where the target is not written in text.
    '''

    if not target.is_file():
        return ''

    try:
        return target.read_text()

    except (UnicodeDecodeError, OSError):
        return None


def _broken_links(page: Path, body: str) -> list[str]:

    '''Return the links pointing at a page or anchor that is absent.

    Args:
        page (Path): The page being read.
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: One complaint per broken link.
    '''

    targets, broken = _link_targets(body)

    for target in targets:
        if target.startswith(('http://', 'https://', 'mailto:')):
            continue

        path, _, anchor = target.partition('#')

        if path:
            resolved = _resolved(page.parent / path)

            if resolved is None or not _found(resolved):
                broken.append(f'links to {path}, which does not exist')
                continue

            rows = _rows_of(resolved) if anchor else ''

            if rows is None:
                broken.append(f'links to {target}, which is not written in text')
                continue

            text = rows
        else:
            text = body

        if anchor and anchor not in _anchors(text):
            broken.append(f'links to {target}, whose heading does not exist')

    return broken


def _split_front_matter(text: str) -> tuple[str, str]:

    '''Split a page into its metadata block and its body.

    Args:
        text (str): The whole page.

    Returns:
        tuple[str, str]: The metadata and the body.
    '''

    if not text.startswith('---\n'):
        return '', text

    end = text.find('\n---\n', 4)

    if end == -1:
        return '', text

    return text[4:end], text[end + 5:]


def _evidence_rows(meta: str) -> list[str]:

    '''Return each evidence row as its claim and source joined.

    A claim given no source comes back alone, so the caller can refuse it.

    Args:
        meta (str): The page's metadata block.

    Returns:
        list[str]: One entry per claim, as `claim | source` where a source
            was given and as the claim alone where none was.
    '''

    rows: list[str] = []

    for line in meta.splitlines():
        stripped = line.strip()

        if stripped.startswith('- claim:'):
            rows.append(stripped[len('- claim:'):].strip().strip('"'))

        elif stripped.startswith('source:') and rows:
            rows[-1] += ' | ' + stripped[len('source:'):].strip().strip('"')

    return rows


def _unlined_sources(rows: list[str]) -> list[str]:

    '''Return the files a row names without citing a line of their own.

    Naming a file and citing none of it leans on the name. The exception
    is a claim about what a file does not hold, which has no line to
    point at; such a row says so in words beside the name.

    Args:
        rows (list[str]): The evidence rows of one page.

    Returns:
        list[str]: One complaint per file named but not cited.
    '''

    notes: list[str] = []

    for row in rows:

        if ' | ' not in row:
            continue

        source = row.split(' | ', 1)[1]
        names = list(FILE_REF.finditer(source))

        for index, match in enumerate(names):
            end = names[index + 1].start() if index + 1 < len(names) else len(source)
            stretch = source[match.end():end]

            if LINE_REF.search(stretch):
                continue

            behind = names[index - 1].end() if index else 0
            nearby = source[
                max(match.start() - _MARKER_REACH, behind):match.end()
            ].lower()

            if not any(word in nearby for word in ABSENCE_WORDS):
                notes.append(f'names `{match.group(1)}` and cites no line of it')
                continue

            if _unresolvable(match.group(1)):
                notes.append(f'names `{match.group(1)}`, which is not in the tree')

    return notes


def _unresolvable(name: str) -> bool:

    '''Whether a named file is absent from the tree it would be read in.

    A name carrying a directory must exist at that exact path; a bare
    name is looked for by itself in each pinned tree.

    Args:
        name (str): The file name as the row wrote it.

    Returns:
        bool: True where no pinned tree holds it.
    '''

    if _reaches_absent_nexus(name):
        return False

    if '/' in name:

        try:
            return not any(
                name in _pinned_paths(root, commit) for root, commit in _pins()
            )
        except BaselineReadError:
            return False

    try:
        return _resolve_source(Path(name).stem) is None
    except BaselineReadError:
        return False


def _uncited_claims(rows: list[str]) -> list[str]:

    '''Return the claims carrying no source at all.

    Args:
        rows (list[str]): The evidence rows of one page.

    Returns:
        list[str]: One complaint per claim with nothing behind it. A
            source naming a file but no line counts as nothing.
    '''

    return [
        f'claim carries no source: "{row[:60]}"'
        for row in rows
        if ' | ' not in row or not LINE_REF.search(row.split(' | ', 1)[1])
    ]


@functools.cache
def _uncommitted_pages() -> frozenset[Path]:

    '''Return each wiki page holding an edit that is not yet committed.

    A page git does not track yet has no committed self to compare, so
    it is not here; its stamp comes under the committed-date rule from
    its first commit onward.

    Returns:
        frozenset[Path]: Those pages.
    '''

    if GIT is None:
        return frozenset()

    result = subprocess.run(  # noqa: S603
        [GIT, 'diff', '--name-only', 'HEAD', '--', str(WIKI)],
        capture_output=True, text=True, check=False,
    )

    if result.returncode != 0:
        return frozenset()

    return frozenset(
        Path(name) for name in result.stdout.split() if name.endswith('.md')
    )


def _edited_since(page: Path) -> str | None:

    '''Return the stamp a page carried when it was last committed.

    A page differing from its committed self has been edited, and its
    stamp has to differ too. The committed stamp is what that is
    measured against: a file's own date would count a copy as an edit.

    Args:
        page (Path): The page being read.

    Returns:
        str | None: That stamp, or None where nothing is uncommitted.
    '''

    if page not in _uncommitted_pages() or GIT is None:
        return None

    result = subprocess.run(  # noqa: S603
        [GIT, 'show', f'HEAD:{page.as_posix()}'],
        capture_output=True, text=True, check=False,
    )

    if result.returncode != 0:
        return None

    meta, text = _split_front_matter(result.stdout)
    stamp = META_STAMP.search(meta) if meta else STAMP.search(text)

    return stamp.group(2) if stamp is not None else None


def _check_stamps(page: Path, text: str, meta: str) -> list[str]:

    '''Return what a page's timestamps get wrong.

    A stamp may run ahead of the last commit, the page having been edited
    and not yet committed. One running behind it is stale: the page
    changed and its stamp did not. A page carrying an edit that is not
    yet committed must carry a stamp later than the one it was committed
    with, so a stamp left unbumped fails before the commit rather than
    after it. A stamp bumped and then edited past again is beyond what
    comparing the two can see.

    Args:
        page (Path): The page being read.
        text (str): Its whole content.
        meta (str): Its metadata block, empty where it has none.

    Returns:
        list[str]: One complaint per failure, each naming the page.
    '''

    rel = page.as_posix()
    stamp = META_STAMP.search(meta) if meta else STAMP.search(text)

    if stamp is None:
        return [f'{rel}: missing or malformed UTC timestamps']

    failures = _stale_stamp(rel, page, stamp.group(2))
    made = CREATED_RE.search(meta) if meta else None

    if made is not None and made.group(1) > stamp.group(2):
        failures.append(
            f'{rel}: created {made.group(1)} is after last modified '
            f'{stamp.group(2)}',
        )

    return failures


def _stale_stamp(rel: str, page: Path, modified: str) -> list[str]:

    '''Return where a page's own stamp is older than the page.

    Args:
        rel (str): The page's path, as it is written in a complaint.
        page (Path): The page being read.
        modified (str): The stamp it carries.

    Returns:
        list[str]: One complaint per way the stamp is behind.
    '''

    failures = []
    committed = _last_commit_date(page)

    if committed is not None and modified[:len(committed)] < committed:
        failures.append(
            f'{rel}: last modified {modified} is older than its last '
            f'commit, {committed}',
        )

    committed_stamp = _edited_since(page)

    if committed_stamp is not None and modified <= committed_stamp:
        failures.append(
            f'{rel}: holds an edit that is not yet committed while its last '
            f'modified still reads {modified}, as it did when committed',
        )

    return failures


def _check_voice(body: str) -> list[str]:

    '''Return what a page's prose gets wrong in how it is written.

    A reason why the code does the thing is a claim about intent, which
    a body never states; it comes from a docstring or from the writer.
    A heading naming what its section is not is refused outright, a
    heading being a name rather than a sentence that can contrast.
    A consequence drawn from a cited fact is not that, and is left
    alone. An implementation name is not prose either: the reader of an
    article has the code withheld from them on purpose, so a name they
    cannot resolve belongs in the metadata with the lines it cites.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: One complaint per failure.
    '''

    notes: list[str] = []
    lead = _lead_paragraph(body)

    if lead is None:
        notes.append(
            'no lead paragraph; the title must be followed by a sentence '
            'defining the subject, not a heading',
        )

    elif lead.startswith('**') or ' is about ' in lead or lead.startswith('This '):
        notes.append(f'lead does not open by defining the subject: "{lead[:60]}"')

    notes.extend(
        f'"{banned}" is a prompt, not a section heading'
        for banned in BANNED_HEADINGS
        if banned in body
    )
    notes.extend(
        f'"{part}" is in the article; apparatus belongs in metadata'
        for part in APPARATUS
        if part in body
    )
    told = RATIONALE.search(body)

    if told is not None:
        notes.append(
            f'gives a reason the code does not state, at "{told.group(0)}"',
        )

    notes.extend(
        f'defines a section by negation: "{heading}"'
        for heading in re.findall(r'^#+ .*', body, re.MULTILINE)
        if HEADING_NEGATION.search(heading)
    )
    labelled = CODE_LABEL.search(body)

    if labelled is not None:
        notes.append(
            f'names the code in its prose, at "{labelled.group(1)}"; '
            'an implementation name belongs in the metadata',
        )

    return notes


def _written_under(key: str, meta: str) -> str | None:

    '''Return what one metadata key holds, read from that key's own line.

    Searching the block instead would take a row identifier or a commit
    written anywhere in it — inside a claim, say — for the value of the
    key that should carry it.

    Args:
        key (str): The key to read.
        meta (str): The page's metadata block.

    Returns:
        str | None: Its value, or None where the key is not a line of
            the block's own.
    '''

    for row in meta.splitlines():

        if row.startswith(f'{key}:'):
            return row[len(key) + 1:].strip()

    return None


def _metadata_shape(meta: str) -> list[str]:

    '''Return what a page's metadata block gets wrong in its shape.

    The keys are read by name and by position rather than by searching
    the block, so a row identifier or a baseline standing under some
    other key, or an evidence list written as one string, is refused
    rather than read as though it were in its place. What the keys hold
    is read beside this rather than instead of it, so a block both
    misshapen and wrong about its baseline is told both.

    Args:
        meta (str): The page's metadata block.

    Returns:
        list[str]: One complaint per way the block is misshapen.
    '''

    rows = meta.splitlines()
    named = [row for row in rows if row and not row.startswith((' ', '\t'))]
    keys = [row.split(':', 1)[0] for row in named]

    if keys != list(_METADATA_KEYS):
        return [
            'metadata names ' + (', '.join(keys) or 'nothing')
            + ', rather than ' + ', '.join(_METADATA_KEYS) + ' in that order',
        ]

    notes = [
        f'metadata writes {key} as nothing'
        for key, row in zip(_METADATA_KEYS[:-1], named, strict=False)
        if not row[len(key) + 1:].strip()
    ]

    written = dict(row.split(':', 1) for row in named[:-1])

    if not COMMIT_ID.fullmatch(written['baseline'].strip()):
        notes.append('metadata writes a baseline that is not a commit')

    if not ROW_ID.fullmatch(written['row'].strip()):
        notes.append('metadata writes a row that is not a register row')

    if named[-1].strip() != 'evidence:':
        notes.append('metadata writes evidence as a value rather than a list')

    opened = rows.index(named[-1])
    notes.extend(
        f'metadata holds a line before its evidence: "{row.strip()}"'
        for row in rows[:opened]
        if row.startswith((' ', '\t'))
    )
    held = rows[opened + 1:]

    if held and not held[0].strip().startswith('- claim:'):
        notes.append('the evidence list opens on something other than a claim')

    notes.extend(
        f'evidence holds a line that is neither a claim nor a source: "{row.strip()}"'
        for row in held
        if not EVIDENCE_LINE.match(row)
    )
    notes.extend(
        'evidence holds a character the YAML behind it cannot carry: '
        f'"{row.strip()[:40]}"'
        for row in held
        if _UNPRINTABLE.search(row)
    )

    return notes + _evidence_pairs(held)


def _said(value: str) -> str:

    '''Return what a claim or a source says, blanks of every kind removed.

    A space, a tab and a mark that shows nothing at all each leave a
    value that reads as written and says nothing, so every character
    Unicode files as a format or a control mark is taken off, along
    with the whitespace around what is left, before asking whether
    anything is left at all.

    Args:
        value (str): The value as the block wrote it.

    Returns:
        str: What is left of it.
    '''

    held = ''.join(
        letter for letter in value
        if unicodedata.category(letter) not in _SHOWS_NOTHING
    )

    return held.strip()


def _evidence_pairs(held: list[str]) -> list[str]:

    '''Return what an evidence list gets wrong about its claim and source pairs.

    Each claim carries one source and says something. A claim written
    empty cites lines for nothing, and a second source under one claim
    is a line a reader of the block sees and a reader of its YAML does
    not, the later one standing alone there.

    Args:
        held (list[str]): The lines of the evidence list.

    Returns:
        list[str]: One complaint per claim that is not a pair.
    '''

    pairs: list[tuple[str, int]] = []
    empty: list[str] = []

    for row in held:
        stripped = row.strip()

        if stripped.startswith('- claim:'):
            pairs.append((stripped[len('- claim:'):].strip().strip('"'), 0))

        elif stripped.startswith('source:') and pairs:
            claim, sources = pairs[-1]
            pairs[-1] = (claim, sources + 1)

            if not _said(stripped[len('source:'):].strip().strip('"')):
                empty.append(claim)

    notes = [
        'evidence holds a claim that says nothing'
        for claim, _ in pairs if not _said(claim)
    ]
    notes += [
        f'the claim "{claim[:40]}" holds the mark that parts a claim from its source'
        for claim, _ in pairs if _PARTING in claim
    ]

    notes += [
        f'the claim "{claim[:40]}" carries a source that names nothing'
        for claim in empty
    ]

    return notes + [
        f'the claim "{claim[:40]}" carries {sources} sources '
        'where it must carry one'
        for claim, sources in pairs if sources != 1
    ]


def _check_metadata(meta: str, ids: set[str]) -> list[str]:

    '''Return what a page's metadata gets wrong about its pin and its row.

    Args:
        meta (str): The page's metadata block.
        ids (set[str]): Every row identifier the register carries.

    Returns:
        list[str]: One complaint per failure.
    '''

    notes = _metadata_shape(meta)
    baseline = _written_under('baseline', meta)

    if baseline is None:
        notes.append('metadata names no baseline commit')
    elif baseline != BASELINE:
        notes.append(
            f'baseline {baseline} is not {BASELINE}, '
            'which every citation is resolved against',
        )

    claimed = _written_under('row', meta)

    if claimed is None or not ROW_ID.fullmatch(claimed):
        notes.append('claims no register row')
    elif claimed not in ids:
        notes.append(f'claims unknown register row {claimed}')

    return notes


def _check_length(body: str) -> list[str]:

    '''Return a complaint where a page's prose outgrows the word cap.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: The one complaint, or none.
    '''

    words = _prose_words(body)

    if words <= PROSE_WORD_CAP:
        return []

    return [f'{words} words of prose exceeds the {PROSE_WORD_CAP} cap; split it']


def _check_page(
    page: Path,
    ids: set[str],
    cache: _SourceFacts,
) -> list[str]:

    '''Return everything one page gets wrong.

    Args:
        page (Path): The page being read.
        ids (set[str]): Every row identifier the register carries.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per failure, each naming the page.
    '''

    text = page.read_text()
    rel = page.as_posix()
    meta, body = _split_front_matter(text)
    failures = _check_stamps(page, text, meta)
    failures.extend(
        f'{rel}: {note}' for note in _broken_links(page, body if meta else text)
    )

    if page.parent.name != 'atoms':
        return failures

    rows = _evidence_rows(meta)

    for notes in (
        ([] if meta else ['has no metadata block; evidence belongs there']),
        ([] if rows else ['metadata carries no evidence']),
        _check_voice(body),
        _uncited_claims(rows),
        _unlined_sources(rows),
        _unlinked_terms(page, body),
        _negative_definitions(body),
        _unspaced_headings(body),
        _check_length(body),
        _check_metadata(meta, ids),
        _check_citations(rows, cache),
    ):
        failures.extend(f'{rel}: {note}' for note in notes)

    return failures


def _check_citations(rows: list[str], cache: _SourceFacts) -> list[str]:

    '''Return what a page's citations land on, where not on code.

    Args:
        rows (list[str]): The page's evidence rows.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per bad citation.
    '''

    return [
        f'evidence {ref}'
        for ref in _docstring_citations(
            '\n'.join(f'|{row}|' for row in rows if ' | ' in row), cache,
        )
    ]


def _modules(root: Path, commit: str, package: str) -> set[str]:

    '''Return the package's non-init modules in the pinned tree.'''

    return {
        name
        for name in _pinned_paths(root, commit)
        if name.startswith(f'{package}/')
        and name.endswith('.py')
        and not name.endswith('__init__.py')
    }


def _ledger_sections(text: str) -> dict[str, str]:

    '''Return each package heading's body, keyed by the package name.'''

    headings = list(LEDGER_HEADING_RE.finditer(text))
    sections: dict[str, str] = {}

    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections[heading.group(1)] = text[heading.end():end]

    return sections


def _ledger_package(
    package: str,
    modules: set[str],
    commit: str,
    body: str,
    counted: int | None,
) -> list[str]:

    '''Return one package's disagreements with its pinned tree.

    Args:
        package (str): The package name, as written in a path.
        modules (set[str]): Its modules in the pinned tree.
        commit (str): The commit the tree is pinned to.
        body (str): The ledger section for the package.
        counted (int | None): The count its heading claims.

    Returns:
        list[str]: One failure per disagreement.
    '''

    named = {
        name for name in LEDGER_PATH_RE.findall(body) if name.startswith(f'{package}/')
    }
    failures = [
        f'{LEDGER}: a row names {absent}, which is not in the tree at {commit}'
        for absent in sorted(named - modules)
    ]

    if counted != len(modules):
        failures.append(
            f'{LEDGER}: the {package} heading says {counted} modules, '
            f'the tree at {commit} has {len(modules)}',
        )

    remainder = len(modules) - len(named & modules)
    grouped = sum(_as_count(count) for count in LEDGER_GROUP_RE.findall(body))

    if grouped != remainder:
        failures.append(
            f'{LEDGER}: {package} names {len(named & modules)} of {len(modules)} modules '
            f'and groups {grouped}, leaving {remainder - grouped} unaccounted for',
        )

    return failures


def _ledger_coverage() -> list[str]:

    '''Return the ledger's disagreements with the pinned trees.

    A package whose tree is not checked out is passed over, so the gate
    checks everything the checkout it has can account for.

    Returns:
        list[str]: One failure per disagreement.
    '''

    text = LEDGER.read_text(encoding='utf-8')
    counts = {
        name: _as_count(count) for name, count in LEDGER_HEADING_RE.findall(text)
    }
    sections = _ledger_sections(text)
    failures: list[str] = []

    for package, root_commit in (
        ('praxis', _pin(Path('praxis'))),
        ('nexus', _pin(NEXUS_ROOT / 'nexus')),
    ):

        if root_commit is None:
            continue

        root, commit, _ = root_commit
        heading = package.capitalize()
        failures += _ledger_package(
            package, _modules(root, commit, package), commit,
            sections.get(heading, ''), counts.get(heading),
        )

    return failures


def _tree_relative(path: Path) -> str:

    '''Return a resolved source path as it is written in the ledger.

    Args:
        path (Path): A path under one of the pinned roots.

    Returns:
        str: The path relative to its root, or the path as given.
    '''

    for root, _ in _pins():

        if str(path).startswith(str(root)):
            return str(path.relative_to(root))

    return str(path)


def _row_file_citations() -> dict[str, set[str]]:

    '''Return which register rows cite each file, by ledger path.

    A row naming an article that is not there, or one whose rows cannot
    be read, cites nothing: the row is reported by the check that reads
    the set as a whole, and this one carries on so that it can be.

    Returns:
        dict[str, set[str]]: Path to the rows citing it.
    '''

    cited: dict[str, set[str]] = {}

    text = REGISTER.read_text(encoding='utf-8')
    sources = [
        (row, _split_front_matter(_rows_of(WIKI / article) or '')[0])
        for row, article in REGISTER_ROW_RE.findall(text)
    ]

    for row, meta in sources:

        for whole in _evidence_rows(meta):
            _note_cited(cited, row, whole.split(' | ', 1)[1] if ' | ' in whole else '')

    return cited


def _finding_file_citations() -> dict[str, set[str]]:

    '''Return which findings cite each file, by ledger path.

    Returns:
        dict[str, set[str]]: Path to the findings citing it.
    '''

    cited: dict[str, set[str]] = {}

    for row, _, source in FINDING_CELLS_RE.findall(
        REGISTER.read_text(encoding='utf-8'),
    ):
        _note_cited(cited, row, source)

    return cited


def _note_cited(cited: dict[str, set[str]], row: str, source: str) -> None:

    '''Record which file each name in one source half reaches.

    Args:
        cited (dict[str, set[str]]): What has been recorded so far.
        row (str): The row or finding the source belongs to.
        source (str): The source half, as the row wrote it.
    '''

    for _, name in _row_sources(source):
        path = _resolve_source(name)

        if path is not None:
            cited.setdefault(_identity(name) or _tree_relative(path), set()).add(row)


def _named_between(package: str, first: str, last: str) -> set[str]:

    '''Return the row identifiers a span of one package names.

    A span reaching past any number a register row could carry names
    nothing, the rows of a package being counted in tens. One running
    backwards names nothing either, there being no row between its
    ends.

    Args:
        package (str): The package the rows belong to.
        first (str): Where the span starts, as the cell wrote it.
        last (str): Where it ends.

    Returns:
        set[str]: Each identifier in the span.
    '''

    opening, closing = _as_count(first), _as_count(last)

    if closing >= _ROWS_AT_MOST:
        return set()

    return {f'{package}-{held:02d}' for held in range(opening, closing + 1)}


def _ledger_listed(column: str) -> set[str]:

    '''Return the row identifiers a ledger cell names, spans expanded.

    Args:
        column (str): The cell's text, as `P4-01, P4-03 to P4-05`.

    Returns:
        set[str]: The identifiers.
    '''

    listed: set[str] = set()

    for part in (piece.strip() for piece in column.split(',')):
        span = ROW_SPAN_RE.match(part)

        if span is not None:
            package, first, last = span.groups()
            listed |= _named_between(package, first, last)

        elif ROW_ID.fullmatch(part):
            listed.add(part)

    return listed


def _nexus_ledger_rows(
    cited: dict[str, set[str]],
    found: dict[str, set[str]],
) -> list[str]:

    '''Check the ledger's Nexus rows against the files the wiki cites.

    The rows there carry no identifiers, so membership is what is
    checked: a file a row or a finding cites is named, and a file named
    there is cited. Without that tree nothing resolves into it, so the
    check is passed over.

    Args:
        cited (dict[str, set[str]]): Which rows cite each file.
        found (dict[str, set[str]]): Which findings cite each file.

    Returns:
        list[str]: One failure per file on one side only.
    '''

    if not NEXUS_ROOT.is_dir():
        return []

    body = _ledger_sections(LEDGER.read_text(encoding='utf-8')).get('Nexus', '')
    named = {name for name, _, _ in LEDGER_ROW_RE.findall(body)}
    reached = {name for name in (cited | found) if name.startswith('nexus/')}

    return [
        f'{LEDGER}: {name} is cited but not named in the Nexus rows'
        for name in sorted(reached - named)
    ] + [
        f'{LEDGER}: {name} is named in the Nexus rows but nothing cites it'
        for name in sorted(named - reached)
    ]


def _unresolved_questions(text: str) -> set[str]:

    '''Return the questions the register carries with nobody to answer them.

    A row is read by its last cell rather than matched whole, so a row
    written with any number of brackets in its first cell is answered
    as quickly as any other.

    Args:
        text (str): The register.

    Returns:
        set[str]: The identifiers those questions name.
    '''

    return {
        found
        for row in text.splitlines()
        if row.endswith('| unassigned |')
        for found in UNRESOLVED_RE.findall(row)
    }


def _open_candidates(cited: dict[str, set[str]]) -> list[str]:

    '''Check that no module carrying an open candidate reads as `full`.

    The ledger reaches `full` only where nothing is left hanging over a
    module. A finding is left hanging where its disposition calls it a
    candidate, or where it names a question still carried with nobody
    to answer it, so every file such a finding cites stays short of
    `full`.

    Args:
        cited (dict[str, set[str]]): Which findings cite each file.

    Returns:
        list[str]: One failure per module `full` with a candidate on it.
    '''

    text = REGISTER.read_text(encoding='utf-8')
    hanging = _unresolved_questions(text)
    open_rows = {
        row for row, _, disposition in FINDING_ROW_CELLS_RE.findall(text)
        if 'candidate' in disposition.lower()
        or hanging & set(UNRESOLVED_RE.findall(disposition))
    }
    body = _ledger_sections(LEDGER.read_text(encoding='utf-8')).get('Praxis', '')

    return [
        f'{LEDGER}: `{name}` is `full` while '
        f'{sorted(open_rows & cited.get(name, set()))} leave a question on it'
        for name, state, _ in LEDGER_ROW_RE.findall(body)
        if state == 'full' and open_rows & cited.get(name, set())
    ]


def _ledger_rows() -> list[str]:

    '''Check each Praxis ledger row against the rows that cite its file.

    A cell may name only rows whose article cites the file, and must
    name every one of them. A file no row cites is `uncovered`, and a
    file some row cites is not. A cited file must have a row of its
    own: counted among the grouped remainder, its state would go
    unstated.

    Returns:
        list[str]: One failure per row that disagrees with the articles.
    '''

    try:
        cited = _row_file_citations()
    except BaselineReadError as error:
        return [f'{LEDGER}: {error}']

    found = _finding_file_citations()
    failures = _nexus_ledger_rows(cited, found) + _open_candidates(found)
    body = _ledger_sections(LEDGER.read_text(encoding='utf-8')).get('Praxis', '')
    named = {name for name, _, _ in LEDGER_ROW_RE.findall(body)}
    failures += [
        f'{LEDGER}: nothing names `{name}`, which {sorted(cited[name] | found.get(name, set()))} cite'
        for name in sorted(cited)
        if name.startswith('praxis/') and name not in named
    ]

    for name, state, column in LEDGER_ROW_RE.findall(body):
        rows, listed = cited.get(name, set()), _ledger_listed(column)

        if rows != listed:
            failures.append(
                f'{LEDGER}: `{name}` names {sorted(listed) or "no row"}; '
                f'the rows citing it are {sorted(rows) or "none"}',
            )

        elif not rows and state != 'uncovered':
            failures.append(f'{LEDGER}: `{name}` is `{state}` with no row citing it')

        elif rows and state == 'uncovered':
            failures.append(
                f'{LEDGER}: `{name}` is `uncovered` while {sorted(rows)} cite it',
            )

    return failures


def _nexus_counts() -> tuple[int, int]:

    '''Return how many Nexus modules the ledger names and how many it holds.

    Returns:
        tuple[int, int]: The rows naming a module, and every module.
    '''

    body = _ledger_sections(LEDGER.read_text(encoding='utf-8')).get('Nexus', '')
    named = len(LEDGER_ROW_RE.findall(body))
    grouped = sum(_as_count(count) for count in LEDGER_GROUP_RE.findall(body))

    return named, named + grouped


def _counted_lines(page: Path, text: str) -> list[str]:

    '''Check each claim about a file's length against the pinned file.

    Args:
        page (Path): The page the claims are written on.
        text (str): Its text.

    Returns:
        list[str]: One failure per length that disagrees.
    '''

    failures = []

    for written in LINE_COUNT_RE.finditer(text):
        name, said = written.group(1), _as_count(written.group(2))

        if _reaches_absent_nexus(name):
            continue

        path = _resolve_source(name)

        if path is None:
            failures.append(f'{page}: "{written.group(0)}" names no file in the tree')
            continue

        length = len(_source_text(path).splitlines())

        if said != length:
            failures.append(f'{page}: "{written.group(0)}" against {length:,}')

    return failures


def _counted_states() -> list[str]:

    '''Check every count written about the ledger against the ledger.

    The states are counted in the Praxis table, and the article count
    against the articles themselves, wherever either is written down.
    The changelog is left out: its entries describe the release they
    were written for, not the wiki as it stands.

    Returns:
        list[str]: One failure per count that disagrees.
    '''

    body = _ledger_sections(LEDGER.read_text(encoding='utf-8')).get('Praxis', '')
    states = [state for _, state, _ in LEDGER_ROW_RE.findall(body)]
    counted = (states.count('full'), states.count('partial'), states.count('uncovered'))
    articles = len(list((WIKI / 'atoms').glob('*.md')))
    nexus_named, nexus_total = _nexus_counts()
    failures = []

    for page in (README, LEDGER, REGISTER):
        text = page.read_text(encoding='utf-8')
        failures += _counted_lines(page, text)

        for written in STATE_COUNT_RE.finditer(text):

            if tuple(_as_count(n) for n in written.groups()) != counted:
                failures.append(
                    f'{page}: "{written.group(0)}" against {counted[0]} full, '
                    f'{counted[1]} partial and {counted[2]} uncovered in the ledger',
                )

        for pattern, truth, what in (
            (ARTICLE_COUNT_RE, articles, 'articles in the wiki'),
            (NEXUS_COUNT_RE, nexus_named, 'Nexus rows in the ledger'),
            (NEXUS_TOTAL_RE, nexus_total, 'Nexus modules in the ledger'),
            (
                NEXUS_UNTOUCHED_RE, nexus_total - nexus_named,
                'Nexus modules the ledger names no row for',
            ),
        ):

            for written in pattern.finditer(text):

                if _as_count(written.group(1)) != truth:
                    failures.append(
                        f'{page}: "{written.group(0)}" against {truth} {what}',
                    )

    return failures


def _unchecked_trees() -> list[str]:

    '''Return a note for each pinned tree that is not checked out.

    Returns:
        list[str]: One note per absent tree.
    '''

    if NEXUS_ROOT.is_dir():
        return []

    return [
        f'the Nexus tree is not checked out at {NEXUS_ROOT}, '
        'so citations into it are not read',
    ]


def _evidence_totals() -> tuple[int, int]:

    '''Count the claims every article makes and the lines they cite.

    Returns:
        tuple[int, int]: The line references, and the claims carrying them.
    '''

    claims = references = 0

    for page in sorted((WIKI / 'atoms').glob('*.md')):
        meta, _ = _split_front_matter(page.read_text(encoding='utf-8'))

        for whole in _evidence_rows(meta):
            claims += 1
            source = whole.split(' | ', 1)[1] if ' | ' in whole else ''
            named = _row_sources(source)
            references += sum(
                1 for match in LINE_REF.finditer(source)
                if any(pos < match.start() for pos, _ in named)
            )

    return references, claims


def _latest_release_counts() -> list[str]:

    '''Check the newest changelog entry's counts against the wiki.

    Only the newest entry is read. An entry already released describes
    the wiki as it stood then, and is left alone.

    Returns:
        list[str]: One failure per count that disagrees.
    '''

    headings = list(RELEASE_RE.finditer(CHANGELOG.read_text(encoding='utf-8')))

    if not headings:
        return []

    entry = CHANGELOG.read_text(encoding='utf-8')[headings[-1].start():]
    references, claims = _evidence_totals()
    findings = len(FINDING_ROW_RE.findall(REGISTER.read_text(encoding='utf-8')))
    failures = []

    for written in EVIDENCE_COUNT_RE.finditer(entry):
        said = tuple(_as_count(number) for number in written.groups())

        if said != (references, claims):
            failures.append(
                f'{CHANGELOG}: "{written.group(0)}" against {references:,} '
                f'references across {claims:,} claims',
            )

    for pattern, truth, what in (
        (ARTICLE_COUNT_RE, len(list((WIKI / 'atoms').glob('*.md'))), 'articles'),
        (FINDING_COUNT_RE, findings, 'findings in the register'),
    ):

        for written in pattern.finditer(entry):

            if _as_count(written.group(1)) != truth:
                failures.append(
                    f'{CHANGELOG}: "{written.group(0)}" against {truth} {what}',
                )

    return failures


def _index_coverage() -> list[str]:

    '''Check that the register, the index and the articles are one set.

    Every register row names an article that exists, every article is
    named by one row and listed in the index, no two rows name the same
    article, and each article's own row is the row that names it.

    Returns:
        list[str]: One failure per article unaccounted for.
    '''

    written = {f'atoms/{page.name}' for page in (WIKI / 'atoms').glob('*.md')}
    named = REGISTER_ROW_RE.findall(REGISTER.read_text(encoding='utf-8'))
    per_article = _rows_per_article(named)
    listed = set(ARTICLE_LINK_RE.findall(README.read_text(encoding='utf-8')))
    failures = [
        f'{REGISTER}: row {row} names {article}, which does not exist'
        for row, article in named if article not in written
    ]
    failures += [
        f'{REGISTER}: {article} is named by rows {sorted(rows)}'
        for article, rows in per_article.items() if len(rows) > 1
    ]
    failures += [
        f'{REGISTER}: names no row for {article}'
        for article in sorted(written - set(per_article))
    ]
    failures += [
        f'{README}: {article} is not listed' for article in sorted(written - listed)
    ]
    failures += [
        f'{README}: lists {article}, which does not exist'
        for article in sorted(listed - written)
    ]

    return failures + _owned_rows(per_article)


def _owned_rows(per_article: dict[str, list[str]]) -> list[str]:

    '''Check each article's own row against the row that names it.

    Args:
        per_article (dict[str, list[str]]): The rows naming each article.

    Returns:
        list[str]: One failure per article claiming another's row.
    '''

    failures = []

    for article, rows in per_article.items():
        page = WIKI / article

        if len(rows) != 1 or not page.exists():
            continue

        meta, _ = _split_front_matter(page.read_text(encoding='utf-8'))
        claimed = ROW_ID.search(meta)

        if claimed is not None and claimed.group(0) != rows[0]:
            failures.append(
                f'{page}: carries row {claimed.group(0)}, '
                f'while the register names it for {rows[0]}',
            )

    return failures


def _rows_per_article(named: list[tuple[str, str]]) -> dict[str, list[str]]:

    '''Return which register rows name each article.

    Args:
        named (list[tuple[str, str]]): Each row with the article it names.

    Returns:
        dict[str, list[str]]: The rows naming each article.
    '''

    rows: dict[str, list[str]] = {}

    for row, article in named:
        rows.setdefault(article, []).append(row)

    return rows


def _finding_citations(cache: _SourceFacts) -> list[str]:

    '''Check the citations the register's own findings carry.

    A finding names its file the way an article's evidence does, and
    every cell after its claim is read the same way, a disposition
    carrying evidence of its own included, a line given with no file
    before it included, a file named with no line of it cited, and a
    finding naming no file at all — unless it says that what it asks
    is not established, there being no line to point at for that. A
    figure a finding means as a figure is written in words, so that
    every number left is a line.

    Args:
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One failure per citation that does not hold.
    '''

    text = REGISTER.read_text(encoding='utf-8')

    rows = [
        (row, f'{claim.strip()} | {source.strip()}')
        for row, claim, source in FINDING_CELLS_RE.findall(text)
    ]
    failures = [
        f'{REGISTER}: {row} {note}'
        for row, whole in rows
        for note in _row_citations(whole, cache) + _unlined_sources([whole])
    ]

    return failures + [
        f'{REGISTER}: {row} cites nothing'
        for row, whole in rows
        if not _row_sources(whole.split(' | ', 1)[1])
        and 'not established' not in whole.lower()
    ]


def _index_vocabulary() -> list[str]:

    '''Check that no index entry leans on a term the wiki owns.

    An entry is read before the article defining its words, so a term
    another article owns is opaque there however clear it is in place.
    A count stands in the same way where it is teased rather than
    spent: `the six ceilings` names none of them, and neither does
    `the one fee` or `two of an outcome's figures`. One thing taken out
    of several is no count, so `take one of` and `any one of` stand.

    Returns:
        list[str]: One failure per entry using such a term.
    '''

    owned = {term for terms in OWNED_TERMS.values() for term in terms}
    entries = INDEX_ENTRY_RE.findall(README.read_text(encoding='utf-8'))
    failures = [
        f'{README}: the entry for {article} leans on "{term}", '
        'which another article owns'
        for article, description in entries
        for term in sorted(owned)
        if re.search(rf'\b{re.escape(term)}\b', description.lower())
    ]

    return failures + [
        f'{README}: the entry for {article} counts rather than describes, '
        f'at "{teased.group(0).strip()}"'
        for article, description in entries
        if (teased := TEASED_COUNT_RE.search(description)) is not None
    ]


def _pinned_table() -> list[str]:

    '''Check the commits the baseline page names against the ones used.

    The page tells a reader which source supports the wiki. A commit
    written there and not read is a false account of it.

    Returns:
        list[str]: One failure per commit that disagrees.
    '''

    page = WIKI / 'BASELINE.md'

    if not page.exists():
        return [f'{page}: the baseline page is missing']

    written = dict(PINNED_ROW_RE.findall(page.read_text(encoding='utf-8')))
    used = {'Praxis': BASELINE, 'Nexus': NEXUS_BASELINE}

    return [
        f'{page}: names {name} at {written.get(name) or "no commit"}, '
        f'while citations are read at {commit}'
        for name, commit in used.items()
        if written.get(name) != commit
    ]


def main() -> int:

    '''Check every wiki page and report structural failures.'''

    pages = sorted(WIKI.rglob('*.md'))
    ids = _register_ids()
    cache = _SourceFacts()
    failures = [f for page in pages for f in _check_page(page, ids, cache)]
    failures += _ledger_coverage()
    failures += _ledger_rows()
    failures += _counted_states()
    failures += _latest_release_counts()
    failures += _index_coverage()
    failures += _index_vocabulary()
    failures += _pinned_table()
    failures += _finding_citations(cache)

    for note in _unchecked_trees():
        _write(f'note: {note}')

    for failure in failures:
        _write(f'FAIL {failure}')

    if failures:
        _write(f'{len(failures)} problem(s).')

        return 1

    _write(f'ok: {len(pages)} page(s), {len(ids)} register row(s)')

    return 0


if __name__ == '__main__':
    sys.exit(main())
