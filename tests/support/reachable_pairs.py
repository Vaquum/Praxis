'''Find pairs the gate calls exclusive that one pass through a shape reaches.

A pair of line sets is an alternative only where no single pass through the
file runs a line from both. Shapes are written out from the grammar the gate
reasons about, run under a line trace once for every input, and every pair the
gate offers is weighed against what those runs reached.
'''

from __future__ import annotations

import ast
import random
import sys
from collections.abc import Iterable
from itertools import product
from pathlib import Path
from typing import Any

CONDITIONS = (
    'a', 'b', 'c', 'not a', 'not b', 'True', 'False', '1 < 2', '2 < 1',
    '1 < 2 < 3', "'a' in 'abc'", '0', "''", '(1, 2)', 'a and True',
    'False or b', 'not False',
)
CALLS = ('step()', 'risky()')
HOLDERS = ('kept()', 'swallowed()')
KINDS = (
    'ValueError', 'Exception', 'TypeError', 'KeyError', 'OSError',
    '(ValueError, TypeError)', 'errors.ValueError', 'BaseException',
)
RAISES = (
    'raise ValueError()',
    "raise ValueError('why')",
    "raise OSError(1, 'no')",
    "raise OSError(2, 'missing')",
    "raise SyntaxError('bad', 1)",
    'raise TypeError',
    'raise errors.ValueError()',
    "raise ValueError('why') from None",
)
CASES = ('case True:', 'case 1:', 'case _ if b:', 'case _:', 'case [1, 2]:', 'case str():')
STATEMENTS = ('step()', 'risky()', 'raise ValueError()', 'return 1', 'pass', 'held = 1')
OTHERWISE = ('', 'step()', 'return 2')
WRAPPERS = (
    (),
    ('try:', '...', 'except ValueError:', '    held = 2'),
    ('try:', '...', 'except TypeError:', '    held = 2'),
    (
        'try:', '...', 'except ValueError:', '    held = 2', 'finally:',
        '    return 9',
    ),
    (
        'try:', '...', 'except TypeError:', '    held = 2', 'finally:',
        '    return 9',
    ),
    ('try:', '...', 'finally:', '    return 9'),
    ('try:', '...', 'finally:', '    step()'),
    ('for item in items:', '...'),
    ('while a:', '...', '    break'),
    ('with kept():', '...'),
    ('with swallowed():', '...'),
)
_ARMS = tuple(
    (first,) for first in STATEMENTS
) + tuple(
    (first, second) for first in STATEMENTS for second in STATEMENTS
)
GIVEN = (True, False)
OVER: tuple[list[int], ...] = ([], [1], [1, 2])
AT_MOST = 3000
DEEP = 3
WIDE = 3
BUDGET = 12


class _Enough(BaseException):

    '''Raised into a shape that has run long enough to be read.'''


class _Errors:

    '''A name kinds can be reached through, as a project's own module is.'''

    ValueError = ValueError
    TypeError = TypeError


class _Holder:

    '''A context manager that either swallows what its body raises or does not.'''

    def __init__(self, *, swallows: bool) -> None:
        self.swallows = swallows

    def __enter__(self) -> _Holder:
        return self

    def __exit__(self, kind: object, held: object, trail: object) -> bool:
        return self.swallows


class _Writer:

    '''Write out a shape from the grammar the gate reasons about.'''

    def __init__(self, rng: random.Random, budget: int) -> None:
        self.rng = rng
        self.budget = budget

    def block(
        self, indent: int, *, loop: bool, depth: int, handler: bool = False,
    ) -> list[str]:

        '''Return the rows of one block.

        Args:
            indent (int): How far in the block sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper a statement of it may go.
            handler (bool): Whether an `except` holds it.

        Returns:
            list[str]: Those rows.
        '''

        rows: list[str] = []

        for _ in range(self.rng.randint(1, WIDE)):

            if self.budget <= 0:
                break

            rows += self.statement(indent, loop=loop, depth=depth, handler=handler)

        return rows or ['    ' * indent + 'pass']

    def statement(
        self, indent: int, *, loop: bool, depth: int, handler: bool = False,
    ) -> list[str]:

        '''Return the rows of one statement.

        Args:
            indent (int): How far in the statement sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper it may go.
            handler (bool): Whether an `except` holds it.

        Returns:
            list[str]: Those rows.
        '''

        self.budget -= 1
        plain = self.plain(indent, loop=loop, handler=handler)

        if depth <= 0:
            return [self.rng.choice(plain)]

        written = {
            'if': self.if_, 'try': self.try_, 'with': self.with_,
            'for': self.for_, 'while': self.while_, 'match': self.match,
            'held': self.held,
        }
        kind = self.rng.choice(['plain', 'plain', *written])

        if kind == 'plain':
            return [self.rng.choice(plain)]

        return written[kind](indent, loop=loop, depth=depth)

    def plain(self, indent: int, *, loop: bool, handler: bool) -> list[str]:

        '''Return the statements that hold no block of their own.

        Args:
            indent (int): How far in they sit.
            loop (bool): Whether a loop holds them.
            handler (bool): Whether an `except` holds them.

        Returns:
            list[str]: One row each.
        '''

        pad = '    ' * indent
        rows = [
            f'{pad}pass',
            f'{pad}held = 1',
            f'{pad}held, other = 1, 2',
            f'{pad}held: int = 1',
            f'{pad}held = step',
            f'{pad}{self.rng.choice(CALLS)}',
            f'{pad}return 1',
            f'{pad}return',
            f'{pad}{self.rng.choice(RAISES)}',
            f'{pad}assert a',
            f'{pad}del held',
        ]

        if loop:
            rows += [f'{pad}break', f'{pad}continue']

        if handler:
            rows += [f'{pad}raise']

        return rows

    def held(
        self, indent: int, *, loop: bool, depth: int,  # noqa: ARG002
    ) -> list[str]:

        '''Return a function or a class written where the shape stands.

        Args:
            indent (int): How far in it sits.
            loop (bool): Whether a loop holds it, which a block written
                inside a function or a class is read without.
            depth (int): How much deeper its body may go.

        Returns:
            list[str]: Those rows.
        '''

        pad = '    ' * indent
        name = f'held_{self.budget}'
        rows = [f'{pad}def {name}():' if self.rng.random() < 0.5 else f'{pad}class {name.title()}:']

        return [*rows, *self.block(indent + 1, loop=False, depth=depth - 1)]

    def match(self, indent: int, *, loop: bool, depth: int) -> list[str]:

        '''Return a `match` statement over a name the shape binds.

        Args:
            indent (int): How far in it sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper a case may go.

        Returns:
            list[str]: Those rows.
        '''

        pad = '    ' * indent
        rows = [f'{pad}match {self.rng.choice(["a", "item", "held"])}:']
        cases = list(CASES)
        self.rng.shuffle(cases)

        for case in cases[: self.rng.randint(1, 3)]:
            rows += [f'{pad}    {case}']
            rows += self.block(indent + 2, loop=loop, depth=depth - 1)

        return rows

    def with_(self, indent: int, *, loop: bool, depth: int) -> list[str]:

        '''Return a `with` statement holding one manager or two.

        Args:
            indent (int): How far in it sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper its body may go.

        Returns:
            list[str]: Those rows.
        '''

        pad = '    ' * indent
        held = self.rng.choice(HOLDERS)

        if self.rng.random() < 0.3:
            held = f'{held}, {self.rng.choice(HOLDERS)}'

        return [
            f'{pad}with {held}:',
            *self.block(indent + 1, loop=loop, depth=depth - 1),
        ]

    def if_(self, indent: int, *, loop: bool, depth: int) -> list[str]:

        '''Return an `if` statement, with an `else` or without.

        Args:
            indent (int): How far in it sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper an arm may go.

        Returns:
            list[str]: Those rows.
        '''

        pad = '    ' * indent
        rows = [f'{pad}if {self.rng.choice(CONDITIONS)}:']
        rows += self.block(indent + 1, loop=loop, depth=depth - 1)

        if self.rng.random() < 0.6:
            rows += [f'{pad}else:']
            rows += self.block(indent + 1, loop=loop, depth=depth - 1)

        return rows

    def try_(self, indent: int, *, loop: bool, depth: int) -> list[str]:

        '''Return a `try` statement, taking errors one by one or in groups.

        Args:
            indent (int): How far in it sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper a block of it may go.

        Returns:
            list[str]: Those rows.
        '''

        pad = '    ' * indent
        star = '*' if self.rng.random() < 0.2 else ''
        rows = [
            f'{pad}try:',
            *self.block(indent + 1, loop=loop, depth=depth - 1),
        ]
        bare = not star and self.rng.random() < 0.15
        rows += [f'{pad}except:' if bare else f'{pad}except{star} {self.rng.choice(KINDS)}:']
        rows += self.block(indent + 1, loop=loop, depth=depth - 1, handler=True)

        if not bare and self.rng.random() < 0.3:
            rows += [f'{pad}except{star} {self.rng.choice(KINDS)}:']
            rows += self.block(indent + 1, loop=loop, depth=depth - 1, handler=True)

        if not star and self.rng.random() < 0.3:
            rows += [
                f'{pad}else:',
                *self.block(indent + 1, loop=loop, depth=depth - 1),
            ]

        if self.rng.random() < 0.4:
            rows += [
                f'{pad}finally:',
                *self.block(indent + 1, loop=loop, depth=depth - 1),
            ]

        return rows

    def for_(self, indent: int, *, loop: bool, depth: int) -> list[str]:

        '''Return a `for` loop over something that may be empty.

        Args:
            indent (int): How far in it sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper its body may go.

        Returns:
            list[str]: Those rows.
        '''

        pad = '    ' * indent
        over = self.rng.choice(['items', '[1]', '[]'])
        rows = [
            f'{pad}for item in {over}:',
            *self.block(indent + 1, loop=True, depth=depth - 1),
        ]

        if self.rng.random() < 0.4:
            rows += [
                f'{pad}else:',
                *self.block(indent + 1, loop=loop, depth=depth - 1),
            ]

        return rows

    def while_(self, indent: int, *, loop: bool, depth: int) -> list[str]:

        '''Return a `while` loop bounded by the turns the shape counts.

        Args:
            indent (int): How far in it sits.
            loop (bool): Whether a loop holds it.
            depth (int): How much deeper its body may go.

        Returns:
            list[str]: Those rows.
        '''

        pad = '    ' * indent
        held = self.rng.choice(['turns < 2', 'turns < 2 and a', 'False'])
        rows = [f'{pad}while {held}:', f'{pad}    turns = turns + 1']
        rows += self.block(indent + 1, loop=True, depth=depth - 1)

        if self.rng.random() < 0.4:
            rows += [
                f'{pad}else:',
                *self.block(indent + 1, loop=loop, depth=depth - 1),
            ]

        return rows


def _written(rng: random.Random) -> str:

    '''Return one shape as a function of the inputs a run hands it.

    Args:
        rng (random.Random): Where the choices come from.

    Returns:
        str: The shape's source.
    '''

    writer = _Writer(rng, budget=BUDGET)
    rows = [
        'def f(a, b, c, items, step, risky, kept, swallowed):',
        '    turns = 0',
        '    held = 1',
        '    item = 1',
    ]
    rows += writer.block(1, loop=False, depth=DEEP)

    return '\n'.join(rows) + '\n'


def _ran(held: Any, given: tuple[object, ...]) -> set[int]:

    '''Return the lines one pass through a shape runs.

    Args:
        held (Any): The shape, as a function.
        given (tuple[object, ...]): What that pass is handed.

    Returns:
        set[int]: The lines it reached, up to the turns read at most.
    '''

    lines: set[int] = set()
    spent = [0]

    def tracer(frame: Any, event: str, _arg: object) -> Any:

        if frame.f_code is held.__code__ and event == 'line':
            lines.add(frame.f_lineno)
            spent[0] += 1

            if spent[0] > AT_MOST:
                raise _Enough

        return tracer

    before = sys.gettrace()
    sys.settrace(tracer)
    try:
        held(*given)

    except BaseException:  # noqa: S110
        pass

    finally:
        sys.settrace(before)

    return lines


def _runs(source: str) -> list[set[int]]:

    '''Return what every pass through a shape runs, one set per input.

    Args:
        source (str): The shape's source.

    Returns:
        list[set[int]]: The lines each pass reached.
    '''

    namespace: dict[str, object] = {'errors': _Errors()}
    exec(compile(source, 'shape.py', 'exec'), namespace)  # noqa: S102
    held = namespace['f']
    found: list[set[int]] = []

    for a, b, c, items, raises in product(GIVEN, GIVEN, GIVEN, OVER, GIVEN):

        def risky(_raises: bool = raises) -> int:

            if _raises:
                raise ValueError

            return 1

        found.append(_ran(held, (
            a, b, c, items, lambda: 1, risky,
            lambda: _Holder(swallows=False),
            lambda: _Holder(swallows=True),
        )))

    return found


def _within_one_loop(tree: ast.AST, first: set[int], second: set[int]) -> bool:

    '''Whether one loop holds both sides of a pair.

    Two arms inside one loop are read as alternatives for one turn, so a
    pass taking several turns reaching both is no disagreement.

    Args:
        tree (ast.AST): The parsed shape.
        first (set[int]): One side of the pair.
        second (set[int]): The other side.

    Returns:
        bool: True where some loop's body holds every line of both.
    '''

    for node in ast.walk(tree):

        if not isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            continue

        opening = node.body[0].lineno
        closing = node.body[-1].end_lineno or opening

        if all(opening <= line <= closing for line in first | second):
            return True

    return False


def written_shapes(seed: int, runs: int) -> list[str]:

    '''Return shapes written out at random from the whole grammar.

    Args:
        seed (int): Where the choices come from.
        runs (int): How many shapes to write.

    Returns:
        list[str]: One source per shape.
    '''

    rng = random.Random(seed)

    return [_written(rng) for _ in range(runs)]


def settled_shapes() -> list[str]:

    '''Return every small shape of the kind the findings have come from.

    An arm of one or two statements sits inside an `if`, which sits inside
    a construct that takes the way the arm leaves or takes it over, with a
    statement after it for the arm to be paired against. Writing shapes at
    random reaches such a shape only by chance; these are all of them.

    Returns:
        list[str]: One source per shape.
    '''

    return [
        _wrapped(wrapper, arm, otherwise)
        for arm in _ARMS
        for otherwise in OTHERWISE
        for wrapper in WRAPPERS
    ]


def _wrapped(
    wrapper: tuple[str, ...], arm: tuple[str, ...], otherwise: str,
) -> str:

    '''Return one settled shape as a function of the inputs a run hands it.

    Args:
        wrapper (tuple[str, ...]): The construct's rows, written one level
            in, with `...` standing where the `if` goes.
        arm (tuple[str, ...]): The arm's statements.
        otherwise (str): The `else` arm's statement, or nothing for an
            `if` without one.

    Returns:
        str: That shape's source.
    '''

    depth = 2 if wrapper else 1
    inner = [f'{"    " * depth}if a:']
    inner += [f'{"    " * (depth + 1)}{row}' for row in arm]

    if otherwise:
        inner += [f'{"    " * depth}else:', f'{"    " * (depth + 1)}{otherwise}']

    rows = ['def f(a, b, c, items, step, risky, kept, swallowed):', '    held = 0']

    for row in wrapper or ('...',):

        if row == '...':
            rows += inner
            continue

        rows.append(f'    {row}')

    return '\n'.join([*rows, '    after = 1', '    return after']) + '\n'


def reachable_pairs(gate: Any, shapes: Iterable[str]) -> tuple[int, list[str]]:

    '''Return how many pairs were weighed, and which a single pass reaches.

    Args:
        gate (Any): The loaded gate, read for its exclusive spans.
        shapes (Iterable[str]): The sources to weigh.

    Returns:
        tuple[int, list[str]]: The pairs weighed, and one account per pair
            that disagrees with a run — empty where every pair held.
    '''

    found: list[str] = []
    weighed = 0

    for source in shapes:

        try:
            tree = ast.parse(source)
            passes = _runs(source)

        except SyntaxError:
            continue

        gate._source_text = lambda _p, _s=source: _s
        pairs = gate._exclusive_spans(Path('shape.py'))

        for first, second in pairs:

            if _within_one_loop(tree, first, second):
                continue

            weighed += 1

            for lines in passes:

                if lines & first and lines & second:
                    found.append(
                        f'{sorted(first)} and {sorted(second)} both reached by '
                        f'{sorted(lines)} in\n{source}',
                    )
                    break

    return weighed, found
