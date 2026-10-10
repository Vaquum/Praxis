'''Validate the wiki's structural claims.

Checks only what a machine can decide. Whether an article is true, and
whether the register missed a behaviour, stay with the reviewer.
'''

from __future__ import annotations

import ast
import functools
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

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
ROW_OPENING = re.compile(r'^\|\s*(P\d+-\d{2})\s*\|', re.MULTILINE)
BANNED_HEADINGS = ('## What it is', '## Overview', '## Introduction')
NEGATIVE_DEF = re.compile(r',\s+not\s+(?:a|an|the|yet|by|its|one)\b', re.IGNORECASE)
DOUBLE_NEGATIVE = re.compile(
    r'(?:\bnot\b|\bnever\b|n[\'\u2019]t\b)'
    r'[^.;:]{0,40}\b(?:nothing|no one|nobody|never|none)\b',
    re.IGNORECASE,
)
HEADING_NEGATION = re.compile(r',\s+not\b', re.IGNORECASE)
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
LINE_REF = re.compile(r'(?<![-\w.])(\d{1,7})(?:-(\d{1,7}))?\b')
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
BASELINE_RE = re.compile(r'^baseline:\s*(\S+)\s*$', re.MULTILINE)
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
EVIDENCE_COUNT_RE = re.compile(r'([\d,]+) line references across ([\d,]+) claims')
FINDING_COUNT_RE = re.compile(r'Record ([\d,]+) findings')
FINDING_ROW_RE = re.compile(r'^\| H-\d+ \|', re.MULTILINE)
ARTICLE_LINK_RE = re.compile(r'\((atoms/[a-z0-9-]+\.md)\)')
UNASSIGNED_RE = re.compile(r'^\|([^|]*\([^|]*\))?[^|]*\|[^|]*\| unassigned \|$', re.MULTILINE)
UNRESOLVED_RE = re.compile(r'\bU-\d+\b')
PINNED_ROW_RE = re.compile(r'^\| (Praxis|Nexus) \| `([0-9a-f]{7,40})` \|', re.MULTILINE)
TEASED_COUNT_RE = re.compile(
    r'\bthe (two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    r'twenty|twenty-one|thirty) [a-z]',
)
INDEX_ENTRY_RE = re.compile(
    r'^- \[[^]]*\]\(atoms/([a-z0-9-]+\.md)\) — (.*)$', re.MULTILINE,
)
FINDING_CELLS_RE = re.compile(r'^\| ([HU]-\d+) \|([^|]*)\|(.*)\|$', re.MULTILINE)
FINDING_ROW_CELLS_RE = re.compile(
    r'^\| ([HU]-\d+) \|[^|]*\|([^|]*)\|[^|]*\|([^|]*)\|', re.MULTILINE,
)
UNNAMED = 'cited with no file named before it'
LINE_COUNT_RE = re.compile(r'`([a-z_/]+\.py)`[,]? (?:is|at) ([\d,]+) lines')
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


ALTERNATION_WORDS = (
    'or', 'either', 'otherwise', 'instead', 'rather than', 'unless',
    'against', 'need not', 'not both', 'alternative',
)


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
    refs = list(LINE_REF.finditer(source))
    within = [match for match in refs if low <= match.start() <= high]
    inner = source[within[0].end():high]
    lead = source[max(refs[0].start() - _MARKER_REACH, 0):refs[0].start()]
    trail = '' if any(match.start() > high for match in refs) else source[
        within[-1].end():within[-1].end() + _MARKER_REACH
    ]

    return _marks(inner) or _marks(lead) or _marks(trail)


def _marks(stretch: str) -> bool:

    '''Whether a stretch of a source half holds an alternation marker.

    Args:
        stretch (str): The stretch to read.

    Returns:
        bool: True where a marker word stands in it.
    '''

    lowered = stretch.lower()

    return any(
        re.search(rf'\b{re.escape(word)}\b', lowered) for word in ALTERNATION_WORDS
    )


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


def _exclusive_spans(path: Path) -> list[tuple[set[int], set[int]]]:

    '''Return pairs of line sets that cannot both run for one input.

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

    scopes = _scopes(tree, text.splitlines())
    pairs: list[tuple[set[int], set[int]]] = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.Try, ast.TryStar)):
            pairs.extend(_handler_arms(node))

        if isinstance(node, ast.Match):
            pairs.extend(_case_arms(node))

        if isinstance(node, ast.If) and node.body:
            pairs.extend(_branch_arms(node, scopes))

    return pairs


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
        set(range(h.body[0].lineno, (h.body[-1].end_lineno or h.lineno) + 1))
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
        set(range(case.body[0].lineno, (case.body[-1].end_lineno or 0) + 1))
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

    body = set(range(node.body[0].lineno, (node.body[-1].end_lineno or 0) + 1))

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
    runs after a continue, so neither is an alternative to anything.
    Where a `finally` is what takes the branch out, how far that reaches
    is measured from the `finally` rather than from the branch, and a
    `finally` leaving by more than one way reaches nothing.

    Args:
        node (ast.If): The `if` the arm belongs to.
        statements (list[ast.stmt]): The arm's statements.
        scopes (_Scopes): What a branch leaving the path can skip.

    Returns:
        set[int]: Those lines, or none where there are none.
    '''

    override = _overridden(scopes, node.lineno)
    kind = override[0] if override is not None else _how_it_leaves(statements[-1])
    measured = override[1] if override is not None else node.lineno
    tried = _reach_of(kind, scopes, measured)

    if not tried:
        return set()

    stop = next(
        (found for scope in tried if (found := _innermost(scope, measured))), 0,
    )
    after = set(range((node.end_lineno or node.lineno) + 1, stop + 1))
    running = scopes.regardless

    if kind == 'continue':
        running += scopes.after_a_loop

    if kind == 'raise':
        running += scopes.handlers

    return after - _still_runs(running, node.lineno)


def _overridden(scopes: _Scopes, line: int) -> tuple[str, int] | None:

    '''Return the way a `finally` around a branch takes it out instead.

    A `finally` runs after whatever the branch did and can leave by its
    own way, so a return under a `finally` that breaks is a break. One
    outside the function the branch sits in takes out the call, not the
    branch, and is passed over.

    Args:
        scopes (_Scopes): What a branch leaving the path can skip.
        line (int): Where the branch sits.

    Returns:
        tuple[str, int] | None: The way it leaves and where its `try`
            starts, or None where no `finally` around the branch leaves.
    '''

    floor = _function_floor(scopes, line)

    for block, kind in scopes.overrides:

        if block.start >= floor and not block.skipped_by(line):
            return kind, block.start

    return None


def _can_leave(body: list[ast.stmt]) -> bool:

    '''Whether any path through a block can take the path out.

    A way out written inside a function or a loop of the block's own
    leaves that, not the block, and is passed over.

    Args:
        body (list[ast.stmt]): The block's statements.

    Returns:
        bool: True where a return, raise, continue or break is reachable.
    '''

    return any(
        _leaves_this_block(statement, within_loop=False) for statement in body
    )


def _leaves_this_block(
    statement: ast.stmt, *, within_loop: bool, raising_leaves: bool = True,
) -> bool:

    '''Whether a statement can take the path out of the block holding it.

    A return or a raise leaves whatever holds it, a loop of the block's
    own included. A continue or a break leaves only its own loop, so one
    written inside a nested loop leaves that — though one in that loop's
    `else` carries on the loop outside it, and so leaves the block. A
    function carries its own ways out and is not looked into, since
    they wait on a call; a class body runs where it stands, and a raise
    written there is the only way one can leave, so it is read as any
    other. A raise in the body of a try that has a handler may be
    caught there, so it is taken not to leave; a return, a continue or a
    break in that same body leaves as it would anywhere.

    Args:
        statement (ast.stmt): The statement to read.
        within_loop (bool): Whether a loop of the block's own holds it.
        raising_leaves (bool): Whether a raise here leaves the block,
            which the body of a try with a handler is read without.

    Returns:
        bool: True where the block can be left here.
    '''

    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False

    if isinstance(statement, ast.Return):
        return True

    if isinstance(statement, ast.Raise):
        return raising_leaves

    if isinstance(statement, (ast.Continue, ast.Break)):
        return not within_loop

    caught: list[ast.stmt] = []
    after: list[ast.stmt] = []

    if isinstance(statement, (ast.Try, ast.TryStar)) and statement.handlers:
        caught = statement.body

    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        after = statement.orelse

    loops = isinstance(statement, (ast.For, ast.AsyncFor, ast.While))

    return any(
        _leaves_this_block(
            held,
            within_loop=within_loop or (loops and block is not after),
            raising_leaves=raising_leaves and block is not caught,
        )
        for block in _child_blocks(statement)
        for held in block
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

    '''Return the single way a block leaves, where it always leaves by one.

    A block that leaves on some paths and not others, or by more than
    one way, names none: what follows the branch it takes out cannot be
    told from what does not. Every statement that can leave is read,
    not the last alone, since an earlier one taking a different way out
    is what runs on the paths reaching it.

    Args:
        body (list[ast.stmt]): The block's statements.

    Returns:
        str: That way, or an empty string.
    '''

    if not _always_leaves(body[-1]):
        return ''

    ways = {
        _how_it_leaves(statement) for statement in body
        if _leaves_this_block(statement, within_loop=False)
    }

    return ways.pop() if len(ways) == 1 else ''


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

    if kind == 'return':
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


def _how_it_leaves(statement: ast.stmt) -> str:

    '''Return the way a statement leaves the path.

    Args:
        statement (ast.stmt): The statement to read.

    An `if` whose arms leave by different ways is read as leaving by
    none of them, since no one scope holds what it skips. A `try` whose
    `finally` can leave leaves by that, the `finally` running after the
    rest and overriding it — and by nothing nameable where the
    `finally` leaves on some paths only. A `match` taking every value
    leaves by the way its cases agree on, and a `with` by the way its
    body does, save for a raise its context manager could swallow.

    Returns:
        str: `return`, `raise`, `continue`, `break`, or an empty string.
    '''

    plain = _plainly_leaves(statement)

    if plain:
        return plain

    if isinstance(statement, ast.If) and statement.orelse:
        return _one_way([statement.body[-1], statement.orelse[-1]])

    if isinstance(statement, (ast.Try, ast.TryStar)) and statement.body:
        return _try_leave(statement)

    if isinstance(statement, ast.Match) and _covers_everything(statement):
        return _one_way([case.body[-1] for case in statement.cases if case.body])

    return _held_way_out(statement)


def _held_way_out(statement: ast.stmt) -> str:

    '''Return the way a statement holding one block of its own leaves.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        str: The way its body leaves, a raise a `with` could swallow
            aside, the way its class body leaves, or the way its loop
            and that loop's `else` agree on; an empty string for
            anything else.
    '''

    if isinstance(statement, (ast.With, ast.AsyncWith)) and statement.body:
        return _held_leave(statement.body[-1])

    if isinstance(statement, ast.ClassDef) and statement.body:
        return _how_it_leaves(statement.body[-1])

    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        return _loop_leave(statement)

    return ''


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


def _try_leave(statement: ast.Try | ast.TryStar) -> str:

    '''Return the way a `try` statement leaves the path.

    A body leaving on some paths only takes its own way out on those
    and the `else` on the rest, and the two need not agree, so no one
    way is named.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        str: That way, or an empty string.
    '''

    if statement.finalbody and _can_leave(statement.finalbody):
        return _one_leave(statement.finalbody)

    if _can_leave(statement.body) and not _always_leaves(statement.body[-1]):
        return ''

    return _one_way([path[-1] for path in _try_paths(statement)])


def _held_leave(statement: ast.stmt) -> str:

    '''Return how a `with` body's last statement takes the path out.

    A raise is not counted: a context manager can swallow one, so what
    follows the `with` may run after all.

    Args:
        statement (ast.stmt): The last statement of the body.

    Returns:
        str: That way, or an empty string.
    '''

    held = _how_it_leaves(statement)

    return held if held in {'return', 'continue', 'break'} else ''


def _covers_everything(node: ast.Match) -> bool:

    '''Whether a `match` statement has a case for every value.

    A `match` with no catch-all can fall past all of its cases, so what
    follows it runs and it leaves by nothing.

    Args:
        node (ast.Match): The statement to read.

    Returns:
        bool: True where its last case takes anything.
    '''

    if not node.cases:
        return False

    last = node.cases[-1]

    return last.guard is None and _takes_anything(last.pattern)


def _takes_anything(pattern: ast.pattern) -> bool:

    '''Whether a pattern matches every value.

    A bare capture does, and so does an alternative holding one.

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


def _one_way(statements: list[ast.stmt]) -> str:

    '''Return the way several paths leave, where they all leave the same.

    Args:
        statements (list[ast.stmt]): The last statement of each path.

    Returns:
        str: That way, or an empty string where they differ.
    '''

    ways = {_how_it_leaves(statement) for statement in statements}

    return ways.pop() if len(ways) == 1 else ''


def _always_leaves(statement: ast.stmt) -> bool:

    '''Whether a statement always takes the path out of what follows.

    A return, raise, continue or break does. So does an `if` whose every
    arm does, and a `try` whose body, handlers and `else` all do, since
    no path through either carries on. A `try` whose `finally` leaves
    does too, whatever the rest of it does, the `finally` running last.
    So does a `match` that takes every value and leaves on each case,
    and a `with` whose body returns, continues or breaks — not one
    whose body raises, a context manager being able to swallow that.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: True where nothing after it runs.
    '''

    if _plainly_leaves(statement):
        return True

    if isinstance(statement, ast.If) and statement.orelse:
        return _always_leaves(statement.body[-1]) and _always_leaves(
            statement.orelse[-1],
        )

    if isinstance(statement, (ast.Try, ast.TryStar)) and statement.body:
        return _try_always_leaves(statement)

    if isinstance(statement, ast.Match) and _covers_everything(statement):
        return all(
            case.body and _always_leaves(case.body[-1]) for case in statement.cases
        )

    return _held_always_leaves(statement)


def _held_always_leaves(statement: ast.stmt) -> bool:

    '''Whether a statement holding one block of its own always leaves.

    A `with` leaves where its body returns, continues or breaks, not
    where it raises, a context manager being able to swallow that. A
    class body runs where it stands, so the class leaves where that
    body does. A loop is read for the break that would carry on past
    it, and for its `else`.

    Args:
        statement (ast.stmt): The statement to read.

    Returns:
        bool: True where nothing after it runs.
    '''

    if isinstance(statement, (ast.With, ast.AsyncWith)) and statement.body:
        return bool(_held_leave(statement.body[-1]))

    if isinstance(statement, ast.ClassDef) and statement.body:
        return _always_leaves(statement.body[-1])

    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        return _loop_always_leaves(statement)

    return False


def _loop_always_leaves(statement: ast.For | ast.AsyncFor | ast.While) -> bool:

    '''Whether every path through a loop leaves what follows it.

    A loop a break reaches carries on after it. Otherwise its `else`
    runs once the loop is done, so the loop leaves where that does; and
    an endless `while` whose body leaves never reaches anything after
    it either. A `for` over something that may be empty, and a `while`
    on a condition that may be false, both reach what follows.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        bool: True where nothing after it runs.
    '''

    if _breaks_out(statement.body):
        return False

    if statement.orelse:
        return _always_leaves(statement.orelse[-1])

    return (
        isinstance(statement, ast.While)
        and _endless(statement.test)
        and _always_leaves(statement.body[-1])
    )


def _loop_leave(statement: ast.For | ast.AsyncFor | ast.While) -> str:

    '''Return the way a loop leaves the path.

    The ways its body can leave by are gathered with the way its `else`
    leaves, and the loop leaves by the one they agree on. A loop a
    break reaches leaves by nothing, and so does one that can be left
    without an `else` to finish on, save for an endless `while`.

    Args:
        statement (ast.For): The loop to read.

    Returns:
        str: That way, or an empty string.
    '''

    if _breaks_out(statement.body):
        return ''

    ways = {
        _how_it_leaves(held) for held in statement.body
        if _leaves_this_block(held, within_loop=True)
    }

    if statement.orelse:
        ways.add(_how_it_leaves(statement.orelse[-1]))

    elif not (isinstance(statement, ast.While) and _endless(statement.test)):
        return ''

    return ways.pop() if len(ways) == 1 else ''


def _endless(test: ast.expr) -> bool:

    '''Whether a loop's condition is written as one that always holds.

    Args:
        test (ast.expr): The condition.

    Returns:
        bool: True where it is a constant that holds.
    '''

    return isinstance(test, ast.Constant) and bool(test.value)


def _breaks_out(body: list[ast.stmt]) -> bool:

    '''Whether a break written in a block leaves the loop holding it.

    A break inside a nested loop leaves that loop rather than this one,
    though one in that loop's `else` runs with the nested loop finished
    and so leaves this one. A function and a class carry their own. A
    break under a `finally` that leaves some other way is overridden by
    it and reaches nothing.

    Args:
        body (list[ast.stmt]): The loop body's statements.

    Returns:
        bool: True where a break reaches the loop.
    '''

    for statement in body:

        if isinstance(
            statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            continue

        if isinstance(statement, ast.Break):
            return True

        if isinstance(statement, (ast.Try, ast.TryStar)) and statement.finalbody:
            overridden = _one_leave(statement.finalbody)

            if overridden and overridden != 'break':
                continue

        blocks = (
            [statement.orelse]
            if isinstance(statement, (ast.For, ast.AsyncFor, ast.While))
            else _child_blocks(statement)
        )

        if any(_breaks_out(block) for block in blocks):
            return True

    return False


def _try_always_leaves(statement: ast.Try | ast.TryStar) -> bool:

    '''Whether every path through a `try` statement leaves.

    Args:
        statement (ast.Try): The statement to read.

    Returns:
        bool: True where nothing after it runs.
    '''

    if statement.finalbody and _always_leaves(statement.finalbody[-1]):
        return True

    return all(_always_leaves(path[-1]) for path in _try_paths(statement))


def _try_paths(node: ast.Try | ast.TryStar) -> list[list[ast.stmt]]:

    '''Return each path through a `try` statement that can carry on.

    The `else` runs where the body reaches its end, so a body that
    always leaves skips it and is the path itself.

    Args:
        node (ast.Try): The statement to read.

    Returns:
        list[list[ast.stmt]]: The body or its `else`, and each handler.
    '''

    reaches_else = bool(node.orelse) and not _always_leaves(node.body[-1])
    paths = [node.orelse] if reaches_else else [node.body]
    paths += [handler.body for handler in node.handlers if handler.body]

    return paths


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

    last = body[-1]

    if _how_it_leaves(last) == 'return':
        return True

    if not _always_leaves(last):
        return False

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

    Returns:
        str | None: The clash found, or None where there is none.
    '''

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


def _rebound_names(tree: ast.AST) -> set[str]:

    '''Return names given some other value anywhere in the module.'''

    rebound: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            rebound.add(node.name)

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


def _claims_a_message(row: str) -> bool:

    '''Whether a row claims something about a logged message.

    Args:
        row (str): One evidence row, as `claim | source`.

    Returns:
        bool: True where it names a log line, a warning or a message.
    '''

    lowered = row.lower()

    return any(word in lowered for word in ('log line', 'warning', 'logged', 'message'))


def _claims_a_docstring(row: str) -> bool:

    '''Whether a row claims something about a docstring itself.

    Args:
        row (str): One evidence row, as `claim | source`.

    Returns:
        bool: True where it says the subject is a docstring.
    '''

    return 'docstring' in row.lower()


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
    '''

    length: int
    blanks: set[int]
    comments: set[int]
    docstrings: set[int]
    logs: set[int]
    signatures: set[int]
    exclusive: list[tuple[set[int], set[int]]]


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
            )

        return self._known[key]


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

    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))

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
        start, end = int(match.group(1)), int(match.group(2) or match.group(1))

        if note is None:
            cited.append((key, start, end, match.start()))
            note = _what_a_citation_lands_on(start, end, facts, whole)

        if note is not None:
            bad.append(_citation_note(key, match, note))

    clash = _exclusive_citations(cited, cache, whole)

    if clash is not None:
        bad.append(clash)

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

    return key.startswith('nexus/') or Path(key).name in _nexus_names()


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
    logging, whichever of them it opens on.

    Args:
        start (int): The first line cited.
        end (int): The last line cited.
        facts (_FileFacts): What the cited file states.
        row (str): The whole evidence row, read for a claim about a
            logged message or about a docstring.

    Returns:
        str | None: What it landed on, or None where it landed on code.
    '''

    span = list(range(start, end + 1))
    bare = facts.blanks | facts.comments | facts.docstrings | facts.signatures

    if _only_says(span, facts):
        return None if _claims_a_docstring(row) else 'docstring'

    if all(n in bare for n in span):
        return 'no executable line'

    inside = [n for n in span if n in facts.docstrings]

    if start in facts.docstrings or (inside and len(inside) * 2 > len(span)):
        return 'docstring'

    if _only_logs(span, facts) and not _claims_a_message(row):
        return 'log call'

    return None


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
            resolved = (page.parent / path).resolve()

            if not resolved.exists():
                broken.append(f'links to {path}, which does not exist')
                continue

            text = resolved.read_text() if resolved.is_file() else ''
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


def _check_metadata(meta: str, ids: set[str]) -> list[str]:

    '''Return what a page's metadata gets wrong about its pin and its row.

    Args:
        meta (str): The page's metadata block.
        ids (set[str]): Every row identifier the register carries.

    Returns:
        list[str]: One complaint per failure.
    '''

    notes: list[str] = []
    baseline = BASELINE_RE.search(meta)

    if baseline is None:
        notes.append('metadata names no baseline commit')
    elif baseline.group(1) != BASELINE:
        notes.append(
            f'baseline {baseline.group(1)} is not {BASELINE}, '
            'which every citation is resolved against',
        )

    claimed = ROW_ID.findall(meta)

    if not claimed:
        notes.append('claims no register row')

    notes.extend(
        f'claims unknown register row {row}' for row in claimed if row not in ids
    )

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
        f'evidence cites prose, not code, at {ref}'
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
    grouped = sum(int(count) for count in LEDGER_GROUP_RE.findall(body))

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
    counts = {name: int(count) for name, count in LEDGER_HEADING_RE.findall(text)}
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

    Returns:
        dict[str, set[str]]: Path to the rows citing it.
    '''

    cited: dict[str, set[str]] = {}

    text = REGISTER.read_text(encoding='utf-8')
    sources = [
        (row, _split_front_matter((WIKI / article).read_text(encoding='utf-8'))[0])
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
            listed |= {f'{package}-{n:02d}' for n in range(int(first), int(last) + 1)}

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

    Args:
        text (str): The register.

    Returns:
        set[str]: The identifiers those questions name.
    '''

    return {
        found
        for row in UNASSIGNED_RE.findall(text)
        for found in UNRESOLVED_RE.findall(row)
    } | {
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
    grouped = sum(int(count) for count in LEDGER_GROUP_RE.findall(body))

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
        name, said = written.group(1), int(written.group(2).replace(',', ''))

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

            if tuple(int(n) for n in written.groups()) != counted:
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

                if int(written.group(1)) != truth:
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
        said = tuple(int(number.replace(',', '')) for number in written.groups())

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

            if int(written.group(1).replace(',', '')) != truth:
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
    spent: `the six ceilings` names none of them.

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
        f'at "the {teased.group(1)}"'
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
