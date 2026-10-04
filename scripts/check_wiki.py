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
from dataclasses import dataclass
from pathlib import Path

__all__ = ['main']

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
    r'\b(?:not|never|n\'t)\b[^.;:]{0,40}\b(?:nothing|no one|nobody|never|none)\b',
    re.IGNORECASE,
)
APPARATUS = ('## Evidence', '| Claim | Source |')
OWNED_TERMS = {
    'what-a-trade-is.md': ('trade name', 'request name'),
    'how-waiting-work-is-drained.md': ('account\'s worker',),
    'the-priority-line.md': ('priority line',),
    'how-a-trade-is-cancelled.md': ('cancellation',),
    'how-an-order-is-placed.md': ('submitted work',),
    'how-the-likely-price-is-checked.md': ('likely-price check',),
    'the-order-book.md': ('order book',),
}
LINE_REF = re.compile(r'(?<![-\w.])(\d{1,5})(?:-(\d{1,5}))?\b')
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
DEFAULT_SOURCE = 'execution_manager'
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
_MAX_SPAN = 60
GIT = shutil.which('git')


@functools.cache
def _repo_root() -> Path | None:

    """Return the repository root, or None where git cannot say.

    Returns:
        Path | None: The root directory, or None.
    """

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

    """Return each pinned repository root with the commit it is pinned to.

    Returns:
        list[tuple[Path, str]]: Root and commit, one per repository.
    """

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

    """Return every path in a repository at one commit.

    Args:
        root (Path): The repository root to list.
        commit (str): The commit to list it at.

    Returns:
        tuple[str, ...]: The paths in that tree.
    """

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


def _docstring_lines(path: Path) -> set[int]:

    """Return the lines of a file that sit inside a docstring.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers.
    """

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
    'need not', 'instead', 'rather than', 'either', 'otherwise',
    'not both', 'alternative', 'unless',
)


def _alternative_sources(row: str) -> set[str]:
    """Return the source names whose own citations a row marks as alternatives.

    A row citing one file is exempted by a marker anywhere in it, claim
    included, since there is no other file the marker could be about.
    A row citing several is exempted only for the file whose own stretch
    of the source half carries the marker — that stretch running from the
    end of the previous file's name to the start of the next, since the
    marker usually sits just before the name it governs. One file's
    alternation therefore cannot excuse another file's pair.

    Args:
        row (str): One evidence row, as `claim | source`.

    Returns:
        set[str]: The source names exempted from the branch check.
    """

    if ' | ' not in row:
        return set()

    source = row.split(' | ', 1)[1]
    names = list(FILE_REF.finditer(source))
    cited = {match.group(1) for match in names} | {
        key for key in SOURCE_FILES if key in source
    }

    if len(cited) <= 1:
        return cited | {Path(name).stem for name in cited} if _marked(row) else set()

    marked: set[str] = set()

    for index, match in enumerate(names):
        start = names[index - 1].end() if index else 0
        end = names[index + 1].start() if index + 1 < len(names) else len(source)

        if _marked(source[start:end]):
            marked.add(match.group(1))
            marked.add(Path(match.group(1)).stem)

    return marked


def _marked(text: str) -> bool:
    """Whether a stretch of a row names its citations as alternatives.

    Args:
        text (str): The stretch to read.

    Returns:
        bool: True where it carries one of the alternation words.
    """

    lowered = text.lower()

    return any(word in lowered for word in ALTERNATION_WORDS)


def _exclusive_spans(path: Path) -> list[tuple[set[int], set[int]]]:

    """Return pairs of line sets that cannot both run for one input.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        list[tuple[set[int], set[int]]]: Each pair of arms.
    """

    try:
        tree = ast.parse(_source_text(path))
    except (OSError, SyntaxError):
        return []

    ends = {
        node.lineno: node.end_lineno or node.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    pairs: list[tuple[set[int], set[int]]] = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Try):
            pairs.extend(_handler_arms(node))

        if isinstance(node, ast.If) and node.body:
            pairs.extend(_branch_arms(node, ends))

    return pairs


def _handler_arms(node: ast.Try) -> list[tuple[set[int], set[int]]]:
    """Return each pair of sibling except handlers as two arms.

    Args:
        node (ast.Try): The try statement to read.

    Returns:
        list[tuple[set[int], set[int]]]: Each pair of handler spans.
    """

    spans = [
        set(range(h.lineno, (h.body[-1].end_lineno or h.lineno) + 1))
        for h in node.handlers
        if h.body
    ]

    return [
        (spans[i], spans[j])
        for i in range(len(spans))
        for j in range(i + 1, len(spans))
    ]


def _branch_arms(
    node: ast.If, ends: dict[int, int],
) -> list[tuple[set[int], set[int]]]:
    """Return the arms of one `if`, where it has two.

    An `if` with an `else` has two arms outright. One without, whose body
    ends in a return, makes an arm of the code after it. One ending in a
    raise or a continue is a guard rather than an arm.

    Args:
        node (ast.If): The `if` statement to read.
        ends (dict[int, int]): Where each enclosing function ends.

    Returns:
        list[tuple[set[int], set[int]]]: The one pair found, or none.
    """

    body = set(range(node.lineno, (node.body[-1].end_lineno or 0) + 1))

    if node.orelse:
        return [(
            body,
            set(range(node.orelse[0].lineno, (node.orelse[-1].end_lineno or 0) + 1)),
        )]

    if not isinstance(node.body[-1], ast.Return):
        return []

    stop = max(
        (end for start, end in ends.items() if start <= node.lineno <= end),
        default=0,
    )
    after = set(range((node.end_lineno or node.lineno) + 1, stop + 1))

    return [(body, after)] if after else []


def _exclusive_citations(
    cited: list[tuple[str, int, int]],
    cache: _SourceFacts,
    row: str,
) -> str | None:
    """Report two citations landing on both sides of a branch.

    Each citation's whole range is compared, and must sit wholly inside
    one arm — a range reaching past its arm is a citation of the wider
    construct, not of that arm. A range containing the other is passed
    over for the same reason. Only an `if` whose body ends in a return
    makes an alternative of the code after it; one ending in a raise or a
    continue is a guard, and citing it beside later code is ordinary.

    Args:
        cited (list[tuple[str, int, int]]): Each citation as its source
            name, first line and last line.
        cache (_SourceFacts): Where the branch spans are read from.
        row (str): The evidence row, read for a marker exempting one file.

    Returns:
        str | None: The clash found, or None where there is none.
    """

    exempt = _alternative_sources(row)

    for index, (key, start, end) in enumerate(cited):

        if key in exempt:
            continue

        facts = cache.peek(key)

        if facts is None:
            continue

        for other_key, other_start, other_end in cited[index + 1:]:

            if other_key != key or other_key in exempt:
                continue

            if _opposed(_spans(start, end), _spans(other_start, other_end), facts):
                return f'{key}:{start} and {other_start} are mutually exclusive branches'

    return None


def _opposed(here: set[int], there: set[int], facts: _FileFacts) -> bool:
    """Whether two cited ranges sit wholly in opposite arms of one branch.

    Args:
        here (set[int]): The lines one citation covers.
        there (set[int]): The lines the other covers.
        facts (_FileFacts): The branch arms of the file they cite.

    Returns:
        bool: True where each sits wholly inside a different arm.
    """

    if here <= there or there <= here:
        return False

    return any(
        (here <= first and there <= second) or (here <= second and there <= first)
        for first, second in facts.exclusive
    )


def _spans(start: int, end: int) -> set[int]:
    """Return the lines a citation covers, bounded against a runaway range."""

    return set(range(start, min(end, start + _MAX_SPAN) + 1))


def _resolve_source(name: str) -> Path | None:
    '''Resolve a cited basename against the pinned trees, not the working one.'''

    if name in SOURCE_FILES:
        return SOURCE_FILES[name]

    stem = name[:-3] if name.endswith('.py') else name
    wanted = f'{stem}.py'

    for prefix in SEARCH_PREFIXES:

        for root, commit in _pins():
            found = sorted(
                entry for entry in _pinned_paths(root, commit)
                if entry.startswith(prefix) and entry.rsplit('/', 1)[-1] == wanted
            )

            if len(found) == 1:
                return root / found[0]

            if found:
                return None

    return None


def _row_sources(row: str) -> list[tuple[int, str]]:

    """Return where each source name appears in a row, in order.

    Args:
        row (str): One evidence row, as `claim | source`.

    Returns:
        list[tuple[int, str]]: Position and name, earliest first.
    """

    hits = [
        (m.start(), key)
        for key in SOURCE_FILES
        for m in re.finditer(re.escape(key), row)
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


def _rebound_names(tree: ast.AST) -> set[str]:
    '''Return names given some other value anywhere in the module.'''

    rebound: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            rebound.add(node.name)

        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            rebound.update(
                alias.asname or alias.name.split('.')[0]
                for alias in node.names
                if not (
                    isinstance(node, ast.ImportFrom)
                    and node.module == 'typing'
                    and not node.level
                    and alias.name == 'Protocol'
                )
            )

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

    """Return the lines of a declaration that has a body below it.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers, Protocol stubs excepted.
    """

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

    """Return the words a page spends on prose and headings.

    Args:
        text (str): The rows to scan, one per line.

    Returns:
        int: The count, navigation links and tables excluded.
    """

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

    """Whether a row claims something about a logged message.

    Args:
        row (str): One evidence row, as `claim | source`.

    Returns:
        bool: True where it names a log line, a warning or a message.
    """

    lowered = row.lower()

    return any(word in lowered for word in ('log line', 'warning', 'logged', 'message'))


def _log_lines(path: Path) -> set[int]:

    """Return the lines of a file that open a logging call.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        set[int]: Those line numbers.
    """

    lines: set[int] = set()

    try:
        source = _source_text(path).splitlines()
    except OSError:
        return lines

    for number, line in enumerate(source, 1):
        if line.strip().startswith('_log.'):
            lines.add(number)

    return lines


@dataclass(frozen=True)
class _FileFacts:
    """Hold what one cited file states, read once at its pinned commit.

    Args:
        length (int): Number of lines in the file.
        docstrings (set[int]): Lines inside a docstring.
        logs (set[int]): Lines opening a logging call.
        signatures (set[int]): Lines of a declaration with a body below it.
        exclusive (list[tuple[set[int], set[int]]]): Pairs of line sets that
            cannot both run for one input.
    """

    length: int
    docstrings: set[int]
    logs: set[int]
    signatures: set[int]
    exclusive: list[tuple[set[int], set[int]]]


class _SourceFacts:
    """Read each cited file once and answer from memory thereafter."""

    def __init__(self) -> None:
        """Start with nothing read."""

        self._known: dict[str, _FileFacts] = {}

    def peek(self, key: str) -> _FileFacts | None:
        """Return what is already known of a file, without reading it.

        Args:
            key (str): The name the citation used.

        Returns:
            _FileFacts | None: What that file states, or None where it has
                not been read.
        """

        return self._known.get(key)

    def of(self, key: str, path: Path) -> _FileFacts:
        """Return what a cited file states, reading it on first ask.

        Args:
            key (str): The name the citation used.
            path (Path): The file that name resolved to.

        Returns:
            _FileFacts: What that file states.

        Raises:
            BaselineReadError: The file cannot be read at its pinned commit.
        """

        if key not in self._known:
            self._known[key] = _FileFacts(
                length=len(_source_text(path).splitlines()),
                docstrings=_docstring_lines(path),
                logs=_log_lines(path),
                signatures=_signature_lines(path),
                exclusive=_exclusive_spans(path),
            )

        return self._known[key]


def _docstring_citations(text: str, cache: _SourceFacts) -> list[str]:

    """Return the citations that land on prose rather than on code.

    Args:
        text (str): The rows to scan, one per line.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per bad citation.
    """

    return [
        note
        for whole in text.splitlines()
        if whole.startswith('|')
        for note in _row_citations(whole, cache)
    ]


def _row_citations(whole: str, cache: _SourceFacts) -> list[str]:
    """Return what one evidence row's citations land on, where not on code.

    Args:
        whole (str): The row, as `claim | source`.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per bad citation, and any branch clash.
    """

    bad: list[str] = []

    row = whole.split(' | ', 1)[1] if ' | ' in whole else whole
    sources = _row_sources(row)
    cited: list[tuple[str, int, int]] = []

    for match in LINE_REF.finditer(row):
        before = [key for pos, key in sources if pos < match.start()]
        key = before[-1] if before else DEFAULT_SOURCE
        facts, note = _facts_for(key, cache)

        if note is not None:
            bad.append(f'{key}:{match.group(0)} ({note})')
            continue

        assert facts is not None

        if int(match.group(2) or match.group(1)) > facts.length:
            bad.append(
                f'{key}:{match.group(0)} (past end of file, '
                f'{facts.length} lines)',
            )
            continue

        start = int(match.group(1))
        end = int(match.group(2) or start)
        cited.append((key, start, end))
        note = _what_a_citation_lands_on(start, end, facts, whole)

        if note is not None:
            bad.append(f'{key}:{match.group(0)} ({note})')

    clash = _exclusive_citations(cited, cache, whole)

    if clash is not None:
        bad.append(clash)

    return bad


def _facts_for(key: str, cache: _SourceFacts) -> tuple[_FileFacts | None, str | None]:
    """Return what a cited file states, or why it cannot be read.

    Args:
        key (str): The name the citation used.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        tuple[_FileFacts | None, str | None]: What the file states, or the
            reason it could not be read.
    """

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
    """Return what a citation lands on, where it is not executable code.

    Args:
        start (int): The first line cited.
        end (int): The last line cited.
        facts (_FileFacts): What the cited file states.
        row (str): The whole evidence row, read for a message claim.

    Returns:
        str | None: What it landed on, or None where it landed on code.
    """

    span = list(range(start, min(end, start + _MAX_SPAN) + 1))
    inside = [n for n in span if n in facts.docstrings]

    if start in facts.docstrings or (inside and len(inside) * 2 > len(span)):
        return 'docstring'

    if start in facts.logs and not _claims_a_message(row):
        return 'log call'

    if all(n in facts.signatures for n in span):
        return 'signature only'

    return None


def _write(line: str) -> None:

    """Write one line of output.

    Args:
        line (str): The line to write.
    """

    sys.stdout.write(f'{line}\n')


def _register_ids() -> set[str]:

    """Return every row identifier the register carries.

    Returns:
        set[str]: The identifiers.
    """

    if not REGISTER.exists():
        return set()

    return set(ROW_ID.findall(REGISTER.read_text()))


def _last_commit_date(path: Path) -> str | None:

    """Return the UTC date a path was last committed on.

    Args:
        path (Path): The file to read, at its pinned commit.

    Returns:
        str | None: The date, or None where git cannot say.
    """

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

    """Return the sentences defining something by what it is not.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: One complaint per sentence.
    """

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

    """Return the paragraph following the title.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        str | None: That paragraph, or None where there is none.
    """

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
    """Return the terms another article owns that are first met unlinked.

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
    """

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
    """Whether a mention sits inside the text of a link to its owner.

    Args:
        body (str): The page's prose.
        position (int): Where the mention starts.
        owner (str): The file the link must point at.

    Returns:
        bool: True where the mention is the linked text itself.
    """

    for match in re.finditer(r'\[([^\]]*)\]\(' + re.escape(owner) + r'[^)]*\)', body):

        if match.start(1) <= position < match.end(1):
            return True

    return False


def _label(name: str) -> str:

    """Return a link label reduced to its comparable form.

    Args:
        name (str): The link target or label to reduce.

    Returns:
        str: The label, case-folded and its spacing normalised.
    """

    return ' '.join(name.split()).casefold()


def _anchors(text: str) -> set[str]:

    """Return the anchors a page offers, one per heading.

    Args:
        text (str): The rows to scan, one per line.

    Returns:
        set[str]: Those anchors.
    """

    slugs = set()

    for heading in HEADING.findall(text):
        slug = re.sub(r'[^a-z0-9 -]', '', heading.lower()).replace(' ', '-')
        slugs.add(slug)

    return slugs


def _link_targets(body: str) -> tuple[list[str], list[str]]:
    """Return every link target a page names, and the references that miss.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        tuple[list[str], list[str]]: The targets, and one complaint per
            reference whose definition is absent.
    """

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

    """Return the links pointing at a page or anchor that is absent.

    Args:
        page (Path): The page being read.
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: One complaint per broken link.
    """

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

    """Split a page into its metadata block and its body.

    Args:
        text (str): The rows to scan, one per line.

    Returns:
        tuple[str, str]: The metadata and the body.
    """

    if not text.startswith('---\n'):
        return '', text

    end = text.find('\n---\n', 4)

    if end == -1:
        return '', text

    return text[4:end], text[end + 5:]


def _evidence_rows(meta: str) -> list[str]:
    """Return each evidence row as its claim and source joined.

    A claim given no source comes back alone, so the caller can refuse it.

    Args:
        meta (str): The page's metadata block.

    Returns:
        list[str]: One entry per claim, as `claim | source` where a source
            was given and as the claim alone where none was.
    """

    rows: list[str] = []

    for line in meta.splitlines():
        stripped = line.strip()

        if stripped.startswith('- claim:'):
            rows.append(stripped[len('- claim:'):].strip().strip('"'))

        elif stripped.startswith('source:') and rows:
            rows[-1] += ' | ' + stripped[len('source:'):].strip().strip('"')

    return rows


def _uncited_claims(rows: list[str]) -> list[str]:
    """Return the claims carrying no source at all.

    Args:
        rows (list[str]): The evidence rows of one page.

    Returns:
        list[str]: One complaint per claim with nothing behind it.
    """

    return [
        f'claim carries no source: "{row[:60]}"'
        for row in rows
        if ' | ' not in row or not _row_sources(row.split(' | ', 1)[1])
    ]


def _check_stamps(page: Path, text: str, meta: str) -> list[str]:
    """Return what a page's timestamps get wrong.

    Args:
        page (Path): The page being read.
        text (str): Its whole content.
        meta (str): Its metadata block, empty where it has none.

    Returns:
        list[str]: One complaint per failure, each naming the page.
    """

    rel = page.as_posix()
    stamp = META_STAMP.search(meta) if meta else STAMP.search(text)

    if stamp is None:
        return [f'{rel}: missing or malformed UTC timestamps']

    failures: list[str] = []
    committed = _last_commit_date(page)

    if committed is not None and not stamp.group(2).startswith(committed):
        failures.append(
            f'{rel}: last modified {stamp.group(2)} disagrees with '
            f'last commit {committed}',
        )

    made = CREATED_RE.search(meta) if meta else None

    if made is not None and made.group(1) > stamp.group(2):
        failures.append(
            f'{rel}: created {made.group(1)} is after last modified '
            f'{stamp.group(2)}',
        )

    return failures


def _check_voice(body: str) -> list[str]:
    """Return what a page's prose gets wrong in how it is written.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: One complaint per failure.
    """

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

    return notes


def _check_metadata(meta: str, ids: set[str]) -> list[str]:
    """Return what a page's metadata gets wrong about its pin and its row.

    Args:
        meta (str): The page's metadata block.
        ids (set[str]): Every row identifier the register carries.

    Returns:
        list[str]: One complaint per failure.
    """

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
    """Return a complaint where a page's prose outgrows the word cap.

    Args:
        body (str): The page's prose, its metadata removed.

    Returns:
        list[str]: The one complaint, or none.
    """

    words = _prose_words(body)

    if words <= PROSE_WORD_CAP:
        return []

    return [f'{words} words of prose exceeds the {PROSE_WORD_CAP} cap; split it']


def _check_page(
    page: Path,
    ids: set[str],
    cache: _SourceFacts,
) -> list[str]:

    """Return everything one page gets wrong.

    Args:
        page (Path): The page being read.
        ids (set[str]): Every row identifier the register carries.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per failure, each naming the page.
    """

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
    """Return what a page's citations land on, where not on code.

    Args:
        rows (list[str]): The page's evidence rows.
        cache (_SourceFacts): Where each cited file is read once and kept.

    Returns:
        list[str]: One complaint per bad citation.
    """

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


def _ledger_coverage() -> list[str]:
    '''Return the ledger's disagreements with the pinned trees.'''

    text = LEDGER.read_text(encoding='utf-8')
    counts = {name: int(count) for name, count in LEDGER_HEADING_RE.findall(text)}
    sections = _ledger_sections(text)
    failures: list[str] = []

    for package, root_commit in (
        ('praxis', _pin(Path('praxis'))),
        ('nexus', _pin(NEXUS_ROOT / 'nexus')),
    ):

        if root_commit is None:
            failures.append(
                f'{LEDGER}: the {package} tree is not checked out, '
                'so its half of the ledger cannot be checked',
            )
            continue

        root, commit, _ = root_commit
        modules = _modules(root, commit, package)
        heading = package.capitalize()
        body = sections.get(heading, '')
        named = {
            name for name in LEDGER_PATH_RE.findall(body)
            if name.startswith(f'{package}/')
        }

        for absent in sorted(named - modules):
            failures.append(
                f'{LEDGER}: a row names {absent}, which is not in the tree at {commit}',
            )

        if counts.get(heading) != len(modules):
            failures.append(
                f'{LEDGER}: the {heading} heading says {counts.get(heading)} modules, '
                f'the tree at {commit} has {len(modules)}',
            )

        remainder = len(modules) - len(named & modules)
        grouped = sum(int(count) for count in LEDGER_GROUP_RE.findall(body))

        if grouped != remainder:
            failures.append(
                f'{LEDGER}: {heading} names {len(named & modules)} of {len(modules)} modules '
                f'and groups {grouped}, leaving {remainder - grouped} unaccounted for',
            )

    return failures


def main() -> int:

    '''Check every wiki page and report structural failures.'''

    pages = sorted(WIKI.rglob('*.md'))
    ids = _register_ids()
    cache = _SourceFacts()
    failures = [f for page in pages for f in _check_page(page, ids, cache)]
    failures += _ledger_coverage()

    for failure in failures:
        _write(f'FAIL {failure}')

    if failures:
        _write(f'{len(failures)} problem(s).')

        return 1

    _write(f'ok: {len(pages)} page(s), {len(ids)} register row(s)')

    return 0


if __name__ == '__main__':
    sys.exit(main())
