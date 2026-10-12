'''
Tests for scripts.check_wiki.

Each check in the wiki gate was added after a defect of its kind reached a
finished article. These lock every one of them by presenting the defect and
asserting the refusal, so a check that stops refusing fails here.
'''

from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.support.reachable_pairs import (
    reachable_pairs,
    settled_shapes,
    written_shapes,
)

_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_wiki.py'
_SHAPES = 2000
_PAIRS = 1000
_SETTLED_PAIRS = 4000
_STUB = '''    def m(
        self,
    ) -> int:
        ...
'''


def _load() -> Any:

    '''Load the gate as a module, it being a script rather than a package.

    Returns:
        Any: The loaded `check_wiki` module.
    '''

    spec = importlib.util.spec_from_file_location('check_wiki', _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules['check_wiki'] = module
    spec.loader.exec_module(module)

    return module


check_wiki = _load()


def _baseline_is_reachable() -> bool:

    '''Whether the commit every citation is resolved against is fetched.

    Returns:
        bool: True where the pinned Praxis tree can be listed.
    '''

    try:
        check_wiki._pinned_paths.cache_clear()
        root = check_wiki._repo_root()

        if root is None:
            return False

        return bool(check_wiki._pinned_paths(root, check_wiki.BASELINE))
    except check_wiki.BaselineReadError:
        return False


_HAS_BASELINE = _baseline_is_reachable()
_NEEDS_BASELINE = pytest.mark.skipif(
    not _HAS_BASELINE,
    reason='the pinned baseline is not in this checkout, so no citation resolves',
)


class TestLineReferences:
    def test_single_digit_line_is_read(self) -> None:
        assert [m.group(0) for m in check_wiki.LINE_REF.finditer('`a.py` 1-9')] == ['1-9']

    def test_negative_number_is_not_a_line(self) -> None:
        found = [m.group(0) for m in check_wiki.LINE_REF.finditer('code -1 at 1143-1145')]
        assert found == ['1143-1145']

    def test_a_six_digit_line_is_read(self) -> None:
        found = [m.group(0) for m in check_wiki.LINE_REF.finditer('`order.py` 100000')]

        assert found == ['100000']

    def test_version_is_not_a_line(self) -> None:
        assert not list(check_wiki.LINE_REF.finditer('v0.100.0'))


class TestGuardsAndArms:
    @staticmethod
    def _spans(
        source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> list[tuple[set[int], set[int]]]:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        return spans

    def test_every_header_a_statement_is_given_is_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'condition': "        if reject(x):\n            pass\n",
            'context manager': "        with reject(x):\n            pass\n",
            'iterated': "        for item in reject(x):\n            pass\n",
            'match subject': (
                "        match reject(x):\n            case _:\n                pass\n"
            ),
            'case guard': (
                "        match x:\n            case _ if reject(x):\n"
                "                pass\n"
            ),
        }
        missed = []

        for name, held in shapes.items():
            source = (
                f"def f(x):\n    if x:\n{held}        raise ValueError()\n    submit(x)\n"
            )
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(3 in first for first, _ in spans):
                missed.append(name)

        assert missed == []

    def test_an_or_pattern_holding_a_wildcard_takes_everything(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        match x:\n            case 1 | _:\n"
            "                return 1\n    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 6 in second for first, second in spans)

    def test_an_or_pattern_without_one_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        match x:\n            case 1 | 2:\n"
            "                return 1\n    go(x)\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_raise_inside_an_async_with_reaches_nothing_past_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "async def f(flag):\n    async with suppress(ValueError):\n"
            "        if flag:\n            mark()\n            raise ValueError()\n\n"
            "    after()\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_case_guard_is_no_alternative_to_a_later_case(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    match x:\n        case _ if reject(x):\n            one()\n"
            "        case _:\n            submit(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 6 in second for first, second in spans)
        assert not any(3 in first or 3 in second for first, second in spans)

    def test_an_acting_context_manager_makes_an_arm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        with reject(x):\n            pass\n"
            "        raise ValueError()\n    submit(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 6 in second for first, second in spans)

    def test_a_call_in_a_nested_condition_makes_an_arm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        if reject(x):\n            pass\n"
            "        raise ValueError()\n    submit(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 6 in second for first, second in spans)

    def test_a_match_holding_only_a_guard_is_a_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        match x:\n            case _:\n"
            "                raise ValueError('a')\n    submit(x)\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_guard_wrapped_in_a_try_is_still_a_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        try:\n"
            "            raise Error('only a message')\n        finally:\n"
            "            pass\n    after()\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_guard_wrapped_in_a_with_is_still_a_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        with lock:\n"
            "            raise Error('only a message')\n    after()\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_an_act_wrapped_in_a_try_is_still_an_arm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        try:\n            act(x)\n"
            "            raise Error('a')\n        finally:\n            pass\n"
            "    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 8 in second for first, second in spans)

    def test_a_branch_acting_before_it_raises_is_an_arm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(x):\n    if x:\n        reject(x)\n        raise ValueError(x)\n'
            '    submit(x)\n'
        )
        assert self._spans(source, tmp_path, monkeypatch)

    def test_a_branch_only_building_a_message_is_a_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        msg = 'bad'\n        raise ValueError(msg)\n"
            '    submit(x)\n'
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_an_act_disguised_as_an_assignment_is_still_an_act(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(x):\n    if x:\n        msg = reject(x)\n'
            '        raise ValueError(msg)\n    submit(x)\n'
        )
        assert self._spans(source, tmp_path, monkeypatch)

    def test_a_message_built_from_a_template_is_still_a_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        msg = f'bad {x}'\n"
            '        raise ValueError(msg)\n    submit(x)\n'
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_call_inside_the_raise_is_an_act(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = 'def f(x):\n    if x:\n        raise ValueError(reject(x))\n    submit(x)\n'
        assert self._spans(source, tmp_path, monkeypatch)

    def test_a_call_in_the_raises_cause_is_an_act(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        raise ValueError('b') from reject(x)\n"
            '    submit(x)\n'
        )
        assert self._spans(source, tmp_path, monkeypatch)

    def test_setting_an_attribute_is_an_act(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        s.failed = True\n"
            "        raise ValueError('b')\n    submit(x)\n"
        )
        assert self._spans(source, tmp_path, monkeypatch)

    def test_a_break_leaves_the_path_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(xs):\n    for x in xs:\n        if x:\n            mark(x)\n'
            '            break\n        inside(x)\n'
        )
        assert self._spans(source, tmp_path, monkeypatch)

    def test_a_branch_ending_in_an_if_that_always_leaves_is_an_arm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(x):\n    if x:\n        reject(x)\n        if y:\n'
            "            raise ValueError('b')\n        else:\n"
            "            raise KeyError('c')\n    submit(x)\n"
        )
        assert self._spans(source, tmp_path, monkeypatch)

    def test_a_returning_arm_is_also_opposed_to_what_follows_the_if(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = 'def f(x):\n    if x:\n        return 1\n    else:\n        a = 2\n    return 3\n'
        assert len(self._spans(source, tmp_path, monkeypatch)) > 1

    def test_a_break_reaches_only_to_the_end_of_its_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(xs):\n    for x in xs:\n        if x:\n            mark(x)\n'
            '            break\n        inside(x)\n    after(xs)\n'
        )
        spans = self._spans(source, tmp_path, monkeypatch)
        assert spans
        assert all(7 not in second for _first, second in spans)

    def test_an_act_nested_in_an_inner_branch_still_counts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        if y:\n            reject(x)\n"
            "            raise ValueError('a')\n        else:\n"
            "            reject(x)\n            raise KeyError('b')\n    submit(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)
        assert any(3 in first and 9 in second for first, second in spans)

    def test_a_continue_reaches_only_to_the_end_of_its_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(xs):\n    for x in xs:\n        if x:\n            mark(x)\n'
            '            continue\n        inside(x)\n    after(xs)\n'
        )
        spans = self._spans(source, tmp_path, monkeypatch)
        assert spans
        assert all(7 not in second for _first, second in spans)


@_NEEDS_BASELINE
class TestImpossibleLines:
    def test_line_zero_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `order.py` 0|', check_wiki._SourceFacts(),
        )
        assert notes == ['order.py:0 (no such line)']

    def test_a_line_with_no_file_named_before_it_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | 42|', check_wiki._SourceFacts(),
        )
        assert notes == ['42 (cited with no file named before it)']

    def test_each_shape_of_negative_definition_is_refused(self) -> None:
        shapes = (
            'A name, not an object.',
            'A request, not a command.',
            'The worker, not the queue.',
            'Asked for, not yet placed.',
            'Recorded, not by the venue.',
            'A copy, not its original.',
            'A pair, not one order.',
        )
        caught = [
            shape for shape in shapes if check_wiki._negative_definitions(shape)
        ]

        assert caught == list(shapes)

    def test_a_blank_line_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `order.py` 16|', check_wiki._SourceFacts(),
        )
        assert notes == ['order.py:16 (no executable line)']

    @_NEEDS_BASELINE
    def test_a_range_ending_before_it_starts_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `order.py` 125-119|', check_wiki._SourceFacts(),
        )

        assert notes == ['order.py:125-119 (a range ending before it starts)']

    @_NEEDS_BASELINE
    def test_a_reversed_range_past_the_file_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|the docstring says it | `order.py` 999999-1|',
            check_wiki._SourceFacts(),
        )

        assert notes == ['order.py:999999-1 (a range ending before it starts)']

    def test_a_span_of_blank_and_signature_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `order.py` 85-87|', check_wiki._SourceFacts(),
        )
        assert notes == ['order.py:85-87 (no executable line)']

    def test_a_comment_only_line_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `execution_manager.py` 765|', check_wiki._SourceFacts(),
        )
        assert notes == ['execution_manager:765 (no executable line)']

    def test_a_name_inside_a_longer_name_is_not_an_alias(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `missing_execution_manager.py` 205|', check_wiki._SourceFacts(),
        )
        assert notes == ['missing_execution_manager.py:205 (unresolved source file)']

    def test_a_line_past_the_end_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `order.py` 99999|', check_wiki._SourceFacts(),
        )
        assert notes and 'past end of file' in notes[0]


class TestUncitedClaims:
    def test_claim_with_no_source_is_refused(self) -> None:
        assert check_wiki._uncited_claims(['a claim standing alone'])

    def test_claim_whose_source_names_no_line_is_refused(self) -> None:
        assert check_wiki._uncited_claims(['a claim | prose with no citation'])

    def test_source_naming_a_file_but_no_line_is_refused(self) -> None:
        assert check_wiki._uncited_claims(['a claim | `order.py`'])

    def test_source_whose_only_number_is_negative_is_refused(self) -> None:
        assert check_wiki._uncited_claims(['a claim | `order.py` -1'])

    def test_a_named_file_with_no_line_of_its_own_is_refused(self) -> None:
        assert check_wiki._unlined_sources(['a claim | `order.py` 30, and `fill.py`'])

    def test_an_absence_claim_may_name_a_file_without_a_line(self) -> None:
        row = 'a claim | `order.py` 30, with nothing further in `fill.py`'
        assert not check_wiki._unlined_sources([row])

    @_NEEDS_BASELINE
    def test_an_absence_claim_still_needs_the_file_to_exist(self) -> None:
        row = 'a claim | `order.py` 30, with nothing further in `nonesuch.py`'
        assert check_wiki._unlined_sources([row])

    @_NEEDS_BASELINE
    def test_a_path_that_is_not_in_the_tree_is_refused(self) -> None:
        row = 'a claim | `order.py` 18, nothing further in `not/a/real/order.py`'
        assert check_wiki._unlined_sources([row])

    def test_an_absence_phrase_does_not_reach_a_later_file(self) -> None:
        row = 'a claim | nothing further in `order.py` 30, `fill.py`'
        assert check_wiki._unlined_sources([row])

    def test_every_absence_phrase_excuses_an_uncited_file(self) -> None:
        phrases = ('nothing further', 'nowhere', 'absent from', 'no such')
        excused = [
            phrase for phrase in phrases
            if not check_wiki._unlined_sources([f'a claim | {phrase} `order.py`'])
        ]

        assert excused == list(phrases)

    def test_a_plain_phrase_excuses_nothing(self) -> None:
        assert check_wiki._unlined_sources(['a claim | plainly `order.py`'])

    def test_every_message_word_is_read_as_one(self) -> None:
        words = ('log line', 'warning', 'logged', 'message')
        claimed = [
            word for word in words
            if check_wiki._claims_a_message(f'the {word} it writes | `order.py` 30')
        ]

        assert claimed == list(words)

    def test_a_row_naming_no_message_claims_none(self) -> None:
        assert not check_wiki._claims_a_message('the order it sends | `order.py` 30')

    def test_every_named_file_carrying_a_line_passes(self) -> None:
        assert not check_wiki._unlined_sources(['a claim | `order.py` 30, `fill.py` 4'])

    def test_cited_claim_passes(self) -> None:
        assert not check_wiki._uncited_claims(['a claim | `order.py` 30-32'])


class TestAlternationMarkers:
    def test_a_marker_between_the_pair_exempts_it(self) -> None:
        source = '`order.py` 30 or 40'
        assert check_wiki._marked_between(source, source.index('30'), source.index('40'))

    def test_a_marker_before_the_pair_exempts_it(self) -> None:
        source = 'either `order.py` 30, 40'
        assert check_wiki._marked_between(source, source.index('30'), source.index('40'))

    def test_a_marker_governing_another_pair_does_not_reach(self) -> None:
        source = (
            '`order.py` 30 and 40, then a long stretch of ordinary prose standing '
            'between them and the next, either `fill.py` 3 or 4'
        )
        assert not check_wiki._marked_between(
            source, source.index('30'), source.index('40'),
        )

    def test_a_marker_past_another_citation_does_not_reach(self) -> None:
        source = '`order.py` 30 and 40; `fill.py` 90 or 92'
        assert not check_wiki._marked_between(
            source, source.index('30'), source.index('40'),
        )

    def test_a_marker_in_the_gap_before_the_pair_does_not_reach(self) -> None:
        source = '`order.py` 30 or 40 and 50'
        assert not check_wiki._marked_between(
            source, source.index('40'), source.index('50'),
        )

    def test_a_run_of_alternatives_marks_each_pair_it_holds(self) -> None:
        source = '`order.py` 94, or 100, or 104'
        assert check_wiki._marked_between(
            source, source.index('94'), source.index('104'),
        )

    def test_a_marker_opening_the_row_governs_its_run(self) -> None:
        source = 'either `order.py` 30, 40, 50'
        assert check_wiki._marked_between(
            source, source.index('40'), source.index('50'),
        )

    def test_a_marker_after_the_pair_exempts_it(self) -> None:
        source = '`order.py` 30, 40 otherwise'
        assert check_wiki._marked_between(source, source.index('30'), source.index('40'))

    def test_and_between_the_pair_is_not_a_marker(self) -> None:
        source = '`order.py` 30 and 40'
        assert not check_wiki._marked_between(source, source.index('30'), source.index('40'))

    def test_neither_does_not_count_as_either(self) -> None:
        source = '`order.py` 30, neither of which matters, 40'
        assert not check_wiki._marked_between(source, source.index('30'), source.index('40'))


class TestProtocolExemption:
    @pytest.mark.parametrize(
        'source',
        [
            pytest.param('from typing import Protocol\nclass A(Protocol):\n' + _STUB, id='stub'),
            pytest.param('from typing import Protocol as P\nclass A(P):\n' + _STUB, id='alias'),
        ],
    )
    def test_protocol_stub_signature_is_citable(self, source: str) -> None:
        assert check_wiki._protocol_lines(ast.parse(source))

    @pytest.mark.parametrize(
        'source',
        [
            pytest.param(
                'from typing import Protocol\nclass A(Protocol):\n'
                '    def m(\n        self,\n    ) -> int:\n        return 1\n',
                id='concrete-method',
            ),
            pytest.param(
                'from typing import Protocol\nclass A(Protocol):\n    class B:\n'
                '        def m(\n            self,\n        ) -> int:\n            ...\n',
                id='nested-class',
            ),
            pytest.param(
                'from .typing import Protocol\nclass A(Protocol):\n' + _STUB,
                id='relative-import',
            ),
            pytest.param(
                'def f():\n    from typing import Protocol\nclass A(Protocol):\n' + _STUB,
                id='function-local-import',
            ),
            pytest.param(
                'from typing import Protocol\nProtocol = object\nclass A(Protocol):\n' + _STUB,
                id='rebound',
            ),
            pytest.param(
                'from typing import Protocol\nfrom abc import ABC as Protocol\n'
                'class A(Protocol):\n' + _STUB,
                id='replacement-import',
            ),
            pytest.param(
                'from typing import Protocol\nclass Protocol:\n    pass\n'
                'class A(Protocol):\n' + _STUB,
                id='rebound-by-a-class',
            ),
            pytest.param(
                'from typing import Protocol\ndef Protocol():\n    pass\n'
                'class A(Protocol):\n' + _STUB,
                id='rebound-by-a-function',
            ),
            pytest.param(
                'from typing import Protocol\nasync def Protocol():\n    pass\n'
                'class A(Protocol):\n' + _STUB,
                id='rebound-by-an-awaited-function',
            ),
            pytest.param(
                'from typing import Protocol\nProtocol, other = object, None\n'
                'class A(Protocol):\n' + _STUB,
                id='unpacking',
            ),
            pytest.param(
                'from typing import Protocol\nProtocol: type = object\n'
                'class A(Protocol):\n' + _STUB,
                id='annotated-reassignment',
            ),
            pytest.param(
                'from typing import Protocol\nProtocol += replacement\n'
                'class A(Protocol):\n' + _STUB,
                id='augmented-reassignment',
            ),
            pytest.param(
                'from typing import Protocol\nmatch held:\n'
                '    case {"a": 1, **Protocol}:\n        pass\n'
                'class A(Protocol):\n' + _STUB,
                id='mapping-rest',
            ),
            pytest.param(
                'from typing import Protocol\nfor Protocol in [object]:\n    pass\n'
                'class A(Protocol):\n' + _STUB,
                id='loop-target',
            ),
            pytest.param(
                'from typing import Protocol\nfrom abc import ABC\n_ = (Protocol := ABC)\n'
                'class A(Protocol):\n' + _STUB,
                id='named-expression',
            ),
            pytest.param(
                'from typing import Protocol\nmatch object():\n    case Protocol:\n        pass\n'
                'class A(Protocol):\n' + _STUB,
                id='match-capture',
            ),
            pytest.param(
                'from typing import Protocol as ABC\nfrom abc import *\nclass A(ABC):\n' + _STUB,
                id='wildcard-import',
            ),
            pytest.param(
                'from typing import Protocol\nclass A(Protocol):\n'
                '    def m(\n        self,\n    ) -> int:\n        ...\n        "trailing"\n',
                id='ellipsis-then-string',
            ),
        ],
    )
    def test_everything_else_keeps_the_signature_rule(self, source: str) -> None:
        assert not check_wiki._protocol_lines(ast.parse(source))


class TestExclusiveBranches:
    @staticmethod
    def _spans(
        source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> list[tuple[set[int], set[int]]]:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        return spans

    def test_an_if_else_makes_two_arms(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = 'def f(x):\n    if x:\n        a = 1\n    else:\n        a = 2\n    return a\n'
        assert self._spans(source, tmp_path, monkeypatch)

    def test_an_early_return_makes_an_alternative_of_what_follows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = 'def f(x):\n    if x:\n        return 1\n    a = 2\n    return a\n'
        assert self._spans(source, tmp_path, monkeypatch)

    def test_a_finally_body_is_no_alternative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            act(x)\n"
            "            return 1\n        go(x)\n    finally:\n"
            "        close()\n    return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert spans
        assert not any(8 in second or 7 in second for _, second in spans)

    def test_a_branch_inside_a_finally_still_pairs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        go()\n    finally:\n        if x:\n"
            "            act(x)\n            return 1\n        submit()\n    return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in first and 8 in second for first, second in spans)

    def test_an_inner_loops_else_is_skipped_by_an_outer_continue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs, ys):\n    for x in xs:\n        if x:\n            act(x)\n"
            "            continue\n        for y in ys:\n            go(y)\n"
            "        else:\n            done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(9 in second for _, second in spans)

    def test_a_loop_else_survives_a_continue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        if x:\n            act(x)\n"
            "            continue\n        go(x)\n    else:\n        done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert spans
        assert not any(8 in second for _, second in spans)

    def test_a_loop_else_does_not_survive_a_break(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        if x:\n            act(x)\n"
            "            break\n        go(x)\n    else:\n        done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(8 in second for _, second in spans)

    def test_arms_leaving_different_ways_pair_with_nothing_after(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            if y:\n"
            "                return 1\n            else:\n"
            "                raise E('a')\n        go(x)\n    except E:\n"
            "        recover()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 10 in second for first, second in spans)

    def test_a_raise_outside_any_handler_reaches_the_function(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        g()\n    except KeyError:\n        pass\n"
            "\n\ndef h(x):\n    if x:\n        reject(x)\n"
            "        raise ValueError('a')\n    accept(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(10 in first and 12 in second for first, second in spans)

    def test_the_condition_is_in_neither_arm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = 'def f(x):\n    if x:\n        return 1\n    a = 2\n    return a\n'
        spans = self._spans(source, tmp_path, monkeypatch)

        assert spans
        assert not any(2 in first or 2 in second for first, second in spans)

    def test_a_guard_that_raises_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = 'def f(x):\n    if x:\n        raise ValueError(x)\n    a = 2\n    return a\n'
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_guard_that_continues_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = 'def f(xs):\n    for x in xs:\n        if x:\n            continue\n        g(x)\n'
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_sibling_handlers_make_arms(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        g()\n    except KeyError:\n        a = 1\n'
            '    except ValueError:\n        a = 2\n    return a\n'
        )
        assert self._spans(source, tmp_path, monkeypatch)


class TestHeadings:
    def test_heading_running_on_from_the_line_above_is_refused(self) -> None:
        assert check_wiki._unspaced_headings('text\n## A heading\n')

    def test_heading_mid_line_is_refused(self) -> None:
        assert check_wiki._unspaced_headings('text. ## A heading\n')

    def test_spaced_heading_passes(self) -> None:
        assert not check_wiki._unspaced_headings('text\n\n## A heading\n')


class TestVoice:
    def test_definition_by_negation_is_refused(self) -> None:
        assert check_wiki._negative_definitions('A name, not an object.')

    def test_double_negative_is_refused(self) -> None:
        assert check_wiki._negative_definitions('A send that fails does not mean nothing happened.')

    def test_plain_definition_passes(self) -> None:
        assert not check_wiki._negative_definitions('A name supplied from outside.')


class TestOwnedTerms:
    def test_first_prose_mention_must_carry_its_link(self, tmp_path: Path) -> None:
        page = tmp_path / 'other.md'
        body = '# Other\n\nA cancellation happens here.\n'
        assert check_wiki._unlinked_terms(page, body)

    def test_linked_first_mention_passes(self, tmp_path: Path) -> None:
        page = tmp_path / 'other.md'
        body = '# Other\n\nA [cancellation](how-a-trade-is-cancelled.md) happens.\n'
        assert not check_wiki._unlinked_terms(page, body)

    def test_a_link_only_in_the_navigation_list_does_not_count(self, tmp_path: Path) -> None:
        page = tmp_path / 'other.md'
        body = (
            '# Other\n\nA cancellation happens here.\n\n'
            '## Related\n\n- [How a trade is cancelled](how-a-trade-is-cancelled.md)\n'
        )
        assert check_wiki._unlinked_terms(page, body)

    def test_a_page_owning_the_term_is_exempt(self, tmp_path: Path) -> None:
        page = tmp_path / 'how-a-trade-is-cancelled.md'
        assert not check_wiki._unlinked_terms(page, '# Cancelling\n\nA cancellation is this.\n')


class TestProseWords:
    def test_navigation_links_are_not_counted(self) -> None:
        plain = '# Title\n\nOne two three.\n'
        listed = plain + '\n## Related\n\n- [A](a.md)\n- [B](b.md)\n'
        assert check_wiki._prose_words(listed) == check_wiki._prose_words(plain) + 1

    def test_headings_are_counted(self) -> None:
        assert check_wiki._prose_words('# Title\n\n## A heading here\n\nOne.\n') > 1


class TestLeadParagraph:
    def test_a_lead_that_is_about_its_subject_is_refused(self) -> None:
        assert check_wiki._check_voice('# Title\n\nThis is about orders.\n')

    def test_a_lead_opening_with_this_is_refused(self) -> None:
        notes = check_wiki._check_voice('# Title\n\nThis order is a send.\n')

        assert any('does not open by defining' in note for note in notes)

    def test_a_lead_saying_it_is_about_is_refused(self) -> None:
        notes = check_wiki._check_voice(
            '# Title\n\nAn order is about to be sent.\n',
        )

        assert any('does not open by defining' in note for note in notes)

    def test_a_lead_in_bold_is_refused(self) -> None:
        assert check_wiki._check_voice('# Title\n\n**An order** is a thing.\n')

    def test_a_heading_where_the_lead_belongs_is_refused(self) -> None:
        assert check_wiki._check_voice('# Title\n\n## A heading\n\nText.\n')

    def test_a_prompt_heading_is_refused(self) -> None:
        assert check_wiki._check_voice('# Title\n\nAn order is a thing.\n\n## What it is\n')

    def test_an_evidence_table_in_the_body_is_refused(self) -> None:
        body = '# Title\n\nAn order is a thing.\n\n## Evidence\n'
        assert check_wiki._check_voice(body)

    def test_a_plain_lead_passes(self) -> None:
        assert not check_wiki._check_voice('# Title\n\nAn order is a thing.\n')


class TestStamps:
    def test_a_stamp_older_than_the_last_commit_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, '_last_commit_date', lambda _p: '2026-10-04')
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-02 09:00 UTC\n'
        assert check_wiki._check_stamps(tmp_path / 'a.md', '', meta)

    def test_a_stamp_ahead_of_the_last_commit_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, '_last_commit_date', lambda _p: '2026-10-04')
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-05 09:00 UTC\n'
        assert not check_wiki._check_stamps(tmp_path / 'a.md', '', meta)

    def test_a_page_created_after_it_was_modified_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, '_last_commit_date', lambda _p: None)
        meta = 'created: 2026-10-06 09:00 UTC\nmodified: 2026-10-05 09:00 UTC\n'
        assert check_wiki._check_stamps(tmp_path / 'a.md', '', meta)

    def test_a_page_with_no_stamps_is_refused(self, tmp_path: Path) -> None:
        assert check_wiki._check_stamps(tmp_path / 'a.md', 'no stamps here', '')


@_NEEDS_BASELINE
class TestLedgerCoverage:
    def test_every_module_is_named_or_grouped(self) -> None:
        assert not [
            note for note in check_wiki._ledger_coverage() if 'unaccounted for' in note
        ]

    def test_no_row_names_a_module_outside_the_pinned_tree(self) -> None:
        assert not [
            note for note in check_wiki._ledger_coverage() if 'which is not in the tree' in note
        ]

    def test_each_heading_count_matches_its_tree(self) -> None:
        assert not [note for note in check_wiki._ledger_coverage() if 'heading says' in note]

    @_NEEDS_BASELINE
    def test_a_row_naming_a_module_outside_the_tree_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch,
            '| `praxis/core/health_tracker.py` | full | P3-15 |',
            '| `praxis/core/nonesuch.py` | full | P3-15 |',
        )

        assert any('which is not in the tree' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_heading_count_that_disagrees_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch, '## Praxis — 88 modules', '## Praxis — 87 modules',
        )

        assert any('heading says 87 modules' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_module_neither_named_nor_grouped_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch,
            '| `praxis/core/health_tracker.py` | full | P3-15 |\n', '',
        )

        assert any('unaccounted for' in f for f in failures)

    @staticmethod
    def _doctored(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        before: str,
        after: str,
    ) -> list[str]:
        text = check_wiki.LEDGER.read_text(encoding='utf-8')
        assert before in text
        ledger = tmp_path / 'ledger.md'
        ledger.write_text(text.replace(before, after), encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'LEDGER', ledger)
        failures: list[str] = check_wiki._ledger_coverage()

        return failures


@_NEEDS_BASELINE
class TestTheWikiItself:
    def test_the_gate_passes(self) -> None:
        assert check_wiki.main() == 0

    def test_the_gate_passes_without_the_nexus_checkout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'NEXUS_ROOT', tmp_path / 'absent')

        assert check_wiki.main() == 0

    def test_a_nexus_citation_is_unchecked_without_that_checkout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'NEXUS_ROOT', tmp_path / 'absent')
        notes = check_wiki._docstring_citations(
            '|a claim | `outcome_processor.py` 999999|', check_wiki._SourceFacts(),
        )

        assert notes == []


class TestTheLedgerRows:

    def test_a_span_expands(self) -> None:
        assert check_wiki._ledger_listed('P4-01, P4-03 to P4-05') == {
            'P4-01', 'P4-03', 'P4-04', 'P4-05',
        }

    def test_a_phrase_names_no_row(self) -> None:
        assert check_wiki._ledger_listed('cited, not traced') == set()

    def test_a_dash_names_no_row(self) -> None:
        assert check_wiki._ledger_listed('—') == set()

    @_NEEDS_BASELINE
    def test_the_ledger_agrees_with_the_articles(self) -> None:
        assert check_wiki._ledger_rows() == []

    @_NEEDS_BASELINE
    def test_a_cell_naming_a_row_that_does_not_cite_it_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch,
            '| `praxis/core/domain/fill.py` | uncovered | — |',
            '| `praxis/core/domain/fill.py` | full | P2-15 |',
        )

        assert any('fill.py` names' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_cell_omitting_a_row_that_cites_it_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch,
            '| `praxis/core/domain/position.py` | full | P2-33, P4-12 |',
            '| `praxis/core/domain/position.py` | full | P4-12 |',
        )

        assert any('position.py` names' in f for f in failures)

    @_NEEDS_BASELINE
    def test_an_uncited_file_not_marked_uncovered_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch,
            '| `praxis/core/domain/fill.py` | uncovered | — |',
            '| `praxis/core/domain/fill.py` | full | — |',
        )

        assert any('is `full` with no row citing it' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_cited_module_with_no_row_of_its_own_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch,
            '| `praxis/core/health_tracker.py` | full | P3-15 |\n', '',
        )

        assert any('nothing names `praxis/core/health_tracker.py`' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_cited_file_marked_uncovered_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch,
            '| `praxis/core/health_tracker.py` | full | P3-15 |',
            '| `praxis/core/health_tracker.py` | uncovered | P3-15 |',
        )

        assert any('is `uncovered` while' in f for f in failures)

    @staticmethod
    def _doctored(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        before: str,
        after: str,
    ) -> list[str]:
        text = check_wiki.LEDGER.read_text(encoding='utf-8')
        assert before in text
        ledger = tmp_path / 'ledger.md'
        ledger.write_text(text.replace(before, after), encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'LEDGER', ledger)
        failures: list[str] = check_wiki._ledger_rows()

        return failures


class TestTheCountedStates:

    @_NEEDS_BASELINE
    def test_the_counts_written_down_hold(self) -> None:
        assert check_wiki._counted_states() == []

    def test_a_drifted_article_count_is_caught(self, tmp_path: Path) -> None:
        page = tmp_path / 'README.md'
        page.write_text('108 articles are written.', encoding='utf-8')
        kept = check_wiki.README
        check_wiki.README = page

        try:
            failures = check_wiki._counted_states()
        finally:
            check_wiki.README = kept

        assert any('108 articles' in f for f in failures)

    def test_a_drifted_state_count_is_caught(self, tmp_path: Path) -> None:
        assert self._written(
            tmp_path, '1 are `full`, 2 `partial` and 3 `uncovered`.',
            '1 are `full`, 2 `partial` and 3 `uncovered`',
        )

    def test_a_drifted_nexus_total_is_caught(self, tmp_path: Path) -> None:
        assert self._written(
            tmp_path, 'Of the 71 in Nexus, nothing else.', 'the 71 in Nexus',
        )

    def test_a_drifted_untouched_count_is_caught(self, tmp_path: Path) -> None:
        assert self._written(tmp_path, 'and 52 untouched.', '52 untouched')

    @staticmethod
    def _written(tmp_path: Path, text: str, wanted: str) -> bool:
        page = tmp_path / 'README.md'
        page.write_text(text, encoding='utf-8')
        kept = check_wiki.README
        check_wiki.README = page

        try:
            failures = check_wiki._counted_states()
        finally:
            check_wiki.README = kept

        return any(wanted in failure for failure in failures)

    def test_a_drifted_nexus_count_is_caught(self, tmp_path: Path) -> None:
        page = tmp_path / 'README.md'
        page.write_text('13 are cited in passing.', encoding='utf-8')
        kept = check_wiki.README
        check_wiki.README = page

        try:
            failures = check_wiki._counted_states()
        finally:
            check_wiki.README = kept

        assert any('13 are cited in passing' in f for f in failures)

    def test_one_file_under_two_names_is_still_one_file(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `validate_trade_command.py` 137 and '
            '`praxis/core/validate_trade_command.py` 139|',
            check_wiki._SourceFacts(),
        )
        assert notes == [
            'validate_trade_command.py:137 and 139 are mutually exclusive branches',
        ]


class TestTheLatestRelease:

    @_NEEDS_BASELINE
    def test_the_newest_entry_agrees_with_the_wiki(self) -> None:
        assert check_wiki._latest_release_counts() == []

    def test_a_drifted_claim_count_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = tmp_path / 'CHANGELOG.md'
        log.write_text(
            '## v1.0.0 on 1st of January, 2026\n\n'
            '- Add 1 line references across 1 claims\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'CHANGELOG', log)
        failures = check_wiki._latest_release_counts()

        assert any('1 line references across 1 claims' in f for f in failures)

    def test_a_drifted_claim_half_alone_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        references, claims = check_wiki._evidence_totals()
        log = tmp_path / 'CHANGELOG.md'
        log.write_text(
            '## v1.0.0 on 1st of January, 2026\n\n'
            f'- Add {references:,} line references across {claims + 1:,} claims\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'CHANGELOG', log)
        failures = check_wiki._latest_release_counts()

        assert any(f'across {claims + 1:,} claims' in f for f in failures)

    def test_a_drifted_findings_count_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = tmp_path / 'CHANGELOG.md'
        log.write_text(
            '## v1.0.0 on 1st of January, 2026\n\n- Record 1 findings\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'CHANGELOG', log)
        failures = check_wiki._latest_release_counts()

        assert any('Record 1 findings' in f for f in failures)

    def test_a_drifted_article_count_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = tmp_path / 'CHANGELOG.md'
        log.write_text(
            '## v1.0.0 on 1st of January, 2026\n\n- Add 1 articles\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'CHANGELOG', log)
        failures = check_wiki._latest_release_counts()

        assert any('1 articles' in f for f in failures)

    def test_an_older_entry_is_left_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        references, claims = check_wiki._evidence_totals()
        log = tmp_path / 'CHANGELOG.md'
        log.write_text(
            '## v0.9.0 on 1st of January, 2026\n\n'
            '- Add 1 line references across 1 claims\n\n'
            '## v1.0.0 on 2nd of January, 2026\n\n'
            f'- Add {references:,} line references across {claims:,} claims\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'CHANGELOG', log)

        assert check_wiki._latest_release_counts() == []


class TestTheIndex:

    @_NEEDS_BASELINE
    def test_the_register_the_index_and_the_articles_are_one_set(self) -> None:
        assert check_wiki._index_coverage() == []

    def test_an_article_named_by_two_rows_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        (wiki / 'atoms').mkdir(parents=True)
        (wiki / 'atoms' / 'one.md').write_text(
            '---\nrow: P1-01\n---\n# One\n', encoding='utf-8',
        )
        (wiki / 'register.md').write_text(
            '| P1-01 | One | written | [one.md](atoms/one.md) |\n'
            '| P1-02 | One again | written | [one.md](atoms/one.md) |\n',
            encoding='utf-8',
        )
        (wiki / 'README.md').write_text(
            '- [One](atoms/one.md)\n', encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        monkeypatch.setattr(check_wiki, 'REGISTER', wiki / 'register.md')
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')

        assert check_wiki._index_coverage() == [
            f'{wiki / "register.md"}: atoms/one.md is named by rows '
            "['P1-01', 'P1-02']",
        ]

    def test_an_article_no_row_names_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        (wiki / 'atoms').mkdir(parents=True)
        (wiki / 'atoms' / 'one.md').write_text('# One', encoding='utf-8')
        (wiki / 'register.md').write_text('# Register\n', encoding='utf-8')
        (wiki / 'README.md').write_text(
            '- [One](atoms/one.md)\n', encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        monkeypatch.setattr(check_wiki, 'REGISTER', wiki / 'register.md')
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')

        assert check_wiki._index_coverage() == [
            f'{wiki / "register.md"}: names no row for atoms/one.md',
        ]

    def test_an_article_claiming_another_row_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        (wiki / 'atoms').mkdir(parents=True)
        (wiki / 'atoms' / 'one.md').write_text(
            '---\nrow: P1-02\n---\n# One\n', encoding='utf-8',
        )
        (wiki / 'register.md').write_text(
            '| P1-01 | One | written | [one.md](atoms/one.md) |\n', encoding='utf-8',
        )
        (wiki / 'README.md').write_text(
            '- [One](atoms/one.md)\n', encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        monkeypatch.setattr(check_wiki, 'REGISTER', wiki / 'register.md')
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')

        assert check_wiki._index_coverage() == [
            f'{wiki / "atoms" / "one.md"}: carries row P1-02, '
            'while the register names it for P1-01',
        ]

    def test_an_unlisted_article_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        (wiki / 'atoms').mkdir(parents=True)
        (wiki / 'atoms' / 'one.md').write_text('# One', encoding='utf-8')
        (wiki / 'register.md').write_text(
            '| P1-01 | One | written | [one.md](atoms/one.md) |\n', encoding='utf-8',
        )
        (wiki / 'README.md').write_text('# Index\n', encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        monkeypatch.setattr(check_wiki, 'REGISTER', wiki / 'register.md')
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')

        assert check_wiki._index_coverage() == [
            f'{wiki / "README.md"}: atoms/one.md is not listed',
        ]

    @_NEEDS_BASELINE
    def test_a_drifted_line_count_is_caught(self, tmp_path: Path) -> None:
        page = tmp_path / 'ledger.md'
        failures = check_wiki._counted_lines(
            page, '`execution_manager.py`, at 10,900 lines',
        )

        assert failures == [
            f'{page}: "`execution_manager.py`, at 10,900 lines" against 10,899',
        ]

    @_NEEDS_BASELINE
    def test_a_true_line_count_passes(self, tmp_path: Path) -> None:
        assert check_wiki._counted_lines(
            tmp_path / 'ledger.md', '`execution_manager.py`, at 10,899 lines',
        ) == []


class TestTheFindings:

    @_NEEDS_BASELINE
    def test_every_finding_citation_holds(self) -> None:
        assert check_wiki._finding_citations(check_wiki._SourceFacts()) == []

    @_NEEDS_BASELINE
    def test_a_finding_citing_past_a_file_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch, '`_wait_for_work` 3885-3888',
            '`_wait_for_work` 99999',
        )

        assert any('past end of file' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_finding_naming_a_file_the_tree_lacks_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        failures = self._doctored(
            tmp_path, monkeypatch, '`_wait_for_work` 3885-3888',
            '`nonesuch.py` 12',
        )

        assert any('unresolved source file' in f for f in failures)

    @staticmethod
    def _doctored(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        before: str,
        after: str,
    ) -> list[str]:
        text = check_wiki.REGISTER.read_text(encoding='utf-8')
        assert before in text
        register = tmp_path / 'register.md'
        register.write_text(text.replace(before, after), encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'REGISTER', register)
        failures: list[str] = check_wiki._finding_citations(check_wiki._SourceFacts())

        return failures

    @_NEEDS_BASELINE
    def test_a_finding_naming_a_file_with_no_line_is_refused(self) -> None:
        assert check_wiki._unlined_sources(['a finding | `missing.py`']) == [
            'names `missing.py` and cites no line of it',
        ]

    @_NEEDS_BASELINE
    def test_a_finding_citing_a_line_with_no_file_is_refused(self) -> None:
        notes = check_wiki._row_citations(
            'a finding | 6545-6551 in the drain', check_wiki._SourceFacts(),
        )
        assert notes == ['6545-6551 (cited with no file named before it)']

    @_NEEDS_BASELINE
    def test_a_finding_citing_a_docstring_as_one_is_allowed(self) -> None:
        notes = check_wiki._row_citations(
            'the docstring claims it | `praxis/core/domain/trade_outcome.py` 6-7',
            check_wiki._SourceFacts(),
        )
        assert notes == []

    @_NEEDS_BASELINE
    def test_a_finding_citing_a_docstring_as_behaviour_is_refused(self) -> None:
        notes = check_wiki._row_citations(
            'the body does it | `praxis/core/domain/trade_outcome.py` 6-7',
            check_wiki._SourceFacts(),
        )
        assert notes == ['praxis/core/domain/trade_outcome.py:6-7 (docstring)']

    @_NEEDS_BASELINE
    def test_a_source_saying_docstring_exempts_nothing(self) -> None:
        notes = check_wiki._row_citations(
            'the body does it | the docstring at '
            '`praxis/core/domain/trade_outcome.py` 6-7',
            check_wiki._SourceFacts(),
        )
        assert notes == ['praxis/core/domain/trade_outcome.py:6-7 (docstring)']

    @_NEEDS_BASELINE
    def test_a_source_saying_warning_exempts_nothing(self) -> None:
        notes = check_wiki._row_citations(
            'the account is held | the warning at `execution_manager.py` 3986-3991',
            check_wiki._SourceFacts(),
        )
        assert notes == ['execution_manager:3986-3991 (log call)']

    @_NEEDS_BASELINE
    def test_a_claim_about_a_logged_message_may_cite_it(self) -> None:
        notes = check_wiki._row_citations(
            'the log line names the account | `execution_manager.py` 3986-3991',
            check_wiki._SourceFacts(),
        )
        assert notes == []


class TestWholeRanges:

    @_NEEDS_BASELINE
    def test_a_range_containing_another_is_no_pair(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `execution_manager.py` 1668-1751 together with 1743|',
            check_wiki._SourceFacts(),
        )
        assert notes == []

    @_NEEDS_BASELINE
    def test_one_file_under_two_spellings_is_one_file(self) -> None:
        assert check_wiki._one_file(
            'execution_manager', 'praxis/core/execution_manager.py',
        )

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_cited_nexus_file_no_row_names_is_caught(self) -> None:
        failures = check_wiki._nexus_ledger_rows(
            {'nexus/core/domain/capital_state.py': {'P2-11'}}, {},
        )

        assert any(
            'nexus/core/domain/capital_state.py is cited but not named' in f
            for f in failures
        )

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_nexus_row_naming_an_uncited_file_is_caught(self) -> None:
        failures = check_wiki._nexus_ledger_rows(
            {'nexus/strategy/loader.py': {'P2-11'}}, {},
        )

        assert any('is named in the Nexus rows but nothing cites it' in f
                   for f in failures)
        assert not any('nexus/strategy/loader.py is cited but not named' in f
                       for f in failures)


class TestAmbiguousNames:

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='both trees must be present for a name to be held by two',
    )
    def test_a_name_both_trees_hold_is_refused(self) -> None:
        assert check_wiki._resolve_source('enums.py') is None

    @_NEEDS_BASELINE
    def test_the_same_name_as_a_path_resolves(self) -> None:
        assert check_wiki._resolve_source('praxis/core/domain/enums.py') is not None

    @_NEEDS_BASELINE
    def test_a_name_one_tree_holds_resolves(self) -> None:
        assert check_wiki._resolve_source('fill.py') is not None


class TestTryStatements:

    @staticmethod
    def _spans(
        source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> list[tuple[set[int], set[int]]]:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        return spans

    def test_a_handler_and_the_else_are_two_arms(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        act(x)\n    except E:\n        recover()\n"
            "    else:\n        done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 7 in second for first, second in spans)

    def test_a_try_leaving_on_every_path_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        try:\n            act(x)\n"
            "            return 1\n        except E:\n            recover()\n"
            "            return 2\n    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 9 in second for first, second in spans)

    def test_a_try_falling_through_a_handler_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        try:\n            act(x)\n"
            "            return 1\n        except E:\n            recover()\n    go(x)\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_raise_in_a_nested_function_keeps_to_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def outer(x):\n    try:\n        made = build(x)\n\n        def inner(y):\n"
            "            if y:\n                act(y)\n                raise E('a')\n"
            "            go(y)\n\n        inner(made)\n    except E:\n        recover()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in second or 11 in second for _, second in spans)


class TestTheStamps:

    def test_an_unbumped_stamp_on_an_edit_is_caught(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = Path('docs/wiki/atoms/one.md')
        monkeypatch.setattr(
            check_wiki, '_edited_since', lambda _p: '2026-10-09 07:31 UTC',
        )
        monkeypatch.setattr(check_wiki, '_last_commit_date', lambda _p: None)
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-09 07:31 UTC\n'
        failures = check_wiki._check_stamps(page, meta, meta)

        assert failures == [
            f'{page.as_posix()}: holds an edit that is not yet committed while '
            'its last modified still reads 2026-10-09 07:31 UTC, as it did '
            'when committed',
        ]

    def test_a_bumped_stamp_on_an_edit_passes(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = Path('docs/wiki/atoms/one.md')
        monkeypatch.setattr(
            check_wiki, '_edited_since', lambda _p: '2026-10-09 07:31 UTC',
        )
        monkeypatch.setattr(check_wiki, '_last_commit_date', lambda _p: None)
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-09 07:41 UTC\n'

        assert check_wiki._check_stamps(page, meta, meta) == []


class TestTheFinallyClause:

    @staticmethod
    def _spans(
        source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> list[tuple[set[int], set[int]]]:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        return spans

    def test_a_finally_that_breaks_beats_a_return(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        if x:\n            act(x)\n"
            "            try:\n                return 1\n            finally:\n"
            "                break\n        go(x)\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert spans
        assert not any(10 in second for _, second in spans)

    def test_a_finally_that_returns_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        try:\n            act(x)\n"
            "        finally:\n            return 1\n    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(7 in second for _, second in spans)

    def test_a_raise_inside_a_with_reaches_nothing_past_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    with suppress(ValueError):\n        if flag:\n"
            "            mark()\n            raise ValueError()\n\n    after()\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_raise_with_no_with_around_it_still_pairs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n"
            "        raise ValueError()\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 5 in second for first, second in spans)

    def test_a_raise_in_a_nested_loop_leaves_the_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        try:\n            if flag:\n"
            "                mark()\n                return\n        finally:\n"
            "            for x in [1]:\n                raise ValueError()\n"
            "    except ValueError:\n        handled()\n    after()\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_continue_in_a_loop_else_leaves_a_finally_around_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs, ys):\n    for x in xs:\n        try:\n            if x:\n"
            "                mark(x)\n                return 1\n            work()\n"
            "        finally:\n            for y in ys:\n                pass\n"
            "            else:\n                continue\n        after()\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 7 in second for first, second in spans)
        assert not any(5 in first and 14 in second for first, second in spans)

    _CAUGHT_RAISE = (
        "def f(x):\n    try:\n        if x:\n            mark(x)\n"
        "            raise E('a')\n        more(x)\n    except E:\n"
        "        recover()\n    else:\n        fine()\n    after()\n"
    )

    def test_an_except_header_belongs_to_its_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spans = self._spans(self._CAUGHT_RAISE, tmp_path, monkeypatch)
        reached = next(second for first, second in spans if 4 in first)

        assert reached == {6, 9, 10}

    def test_sibling_except_star_handlers_are_no_arms(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        work()\n    except* ValueError:\n"
            "        one()\n    except* TypeError:\n        two()\n    else:\n"
            "        fine()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 7 in second for first, second in spans)
        assert not any(7 in first and 5 in second for first, second in spans)
        assert any(5 in first and 9 in second for first, second in spans)

    def test_a_handler_type_is_no_arm_against_a_later_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        work()\n    except probe():\n"
            "        one()\n    except ValueError:\n        recover()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 7 in second for first, second in spans)
        assert not any(4 in first or 4 in second for first, second in spans)

    def test_a_loop_whose_break_a_finally_overrides_still_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        mark()\n        while True:\n"
            "            try:\n                go()\n                break\n"
            "            finally:\n                return 1\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_break_that_may_not_be_taken_keeps_the_loops_else(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs, flag, hit):\n    for outer in xs:\n        if flag:\n"
            "            for inner in xs:\n                if hit:\n"
            "                    break\n            else:\n                mark()\n"
            "                continue\n            return\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(8 in first and 11 in second for first, second in spans)
        assert not any(8 in second and 11 in first for first, second in spans)

    def test_a_raise_no_handler_names_still_carries_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise ValueError()\n"
            "            except TypeError:\n                return 1\n"
            "        later()\n    except ValueError:\n        handle()\n"
            "    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 11 in second for first, second in spans)
        assert not any(5 in first and 12 in second for first, second in spans)

    def test_a_handler_naming_every_error_catches_the_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise TypeError()\n"
            "            except Exception:\n                return 1\n"
            "        later()\n    except TypeError:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 9 in second for first, second in spans)

    def test_a_raise_inside_a_with_may_still_carry_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            mark()\n"
            "            with held():\n                raise ValueError()\n"
            "        later()\n    except ValueError:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 9 in second for first, second in spans)

    def test_a_handler_naming_a_tuple_catches_a_kind_in_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise ValueError()\n"
            "            except (ValueError, TypeError):\n                return 1\n"
            "        later()\n    except ValueError:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 9 in second for first, second in spans)

    def test_a_tuple_naming_every_error_catches_anything(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise errors.Failed()\n"
            "            except (BaseException,):\n                return 1\n"
            "        later()\n    except Exception:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 9 in second for first, second in spans)

    def test_a_kind_outside_exception_is_no_catch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise KeyboardInterrupt()\n"
            "            except Exception:\n                return 1\n"
            "        later()\n    except BaseException:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 11 in second for first, second in spans)

    def test_every_kind_outside_exception_is_no_catch(self) -> None:
        kinds = (
            'BaseException',
            'BaseExceptionGroup',
            'KeyboardInterrupt',
            'SystemExit',
            'GeneratorExit',
        )
        covered = [
            kind for kind in kinds
            if check_wiki._under_exception(f'raise:{kind}')
        ]

        assert covered == []

    def test_a_kind_inside_exception_is_covered(self) -> None:
        assert check_wiki._under_exception('raise:ValueError')

    def test_dead_code_after_a_plain_return_raises_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            return 1\n            work()\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 9 in second for first, second in spans)

    def test_a_skipped_loops_else_can_still_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            while False:\n                pass\n            else:\n"
            "                return work()\n        except ValueError:\n"
            "            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 11 in second for first, second in spans)

    def test_a_case_a_guard_holds_back_is_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, x):\n    if flag:\n        mark()\n        match x:\n"
            "            case _ if False:\n                pass\n"
            "            case _:\n                return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 9 in second for first, second in spans)

    def test_a_kind_named_through_something_else_may_catch_a_said_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a kind on something': '        except errors.ValueError:\n',
            'a kind looked up': "        except errors['ValueError']:\n",
            'a kind called for': "        except errors.get('ValueError'):\n",
            'a kind chosen between': (
                '        except (ValueError if flag else TypeError):\n'
            ),
        }
        unpaired = []

        for label, handler in shapes.items():
            source = (
                "def f(flag):\n    if flag:\n        mark()\n        try:\n"
                "            raise ValueError()\n" + handler
                + "            pass\n    later()\n"
            )
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(3 in first and 8 in second for first, second in spans):
                unpaired.append(label)

        assert unpaired == list(shapes)

    def test_a_raise_reaches_its_handler_under_a_finally_that_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, step):\n    try:\n        if flag:\n"
            "            raise ValueError()\n            step()\n"
            "    except Exception:\n        pass\n    finally:\n"
            "        return 1\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 7 in second for first, second in spans)

    def test_a_raise_reaches_a_handlers_own_line_under_such_a_finally(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, other, step):\n    try:\n        try:\n"
            "            if flag:\n                raise ValueError()\n"
            "                step()\n        except TypeError:\n"
            "            held = 1\n        finally:\n            if other:\n"
            "                step()\n            if True:\n"
            "                return 1\n    finally:\n        pass\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 7 in second for first, second in spans)

    @pytest.mark.parametrize(
        ('raised', 'caught'),
        [
            pytest.param('KeyError', 'LookupError', id='a-lookup'),
            pytest.param('ZeroDivisionError', 'ArithmeticError', id='an-arithmetic'),
            pytest.param('IndexError', 'LookupError', id='an-index'),
            pytest.param('KeyError', 'Exception', id='an-exception'),
            pytest.param('KeyError', 'KeyError', id='the-kind-itself'),
        ],
    )
    def test_a_handler_catches_the_kinds_it_covers(
        self, raised: str, caught: str, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            f'def f(flag, step):\n    if flag:\n        step()\n        try:\n'
            f'            raise {raised}()\n        except {caught}:\n'
            f'            pass\n    return 1\n'
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 8 in second for first, second in spans)

    def test_a_kind_the_handler_does_not_cover_still_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag, step):\n    if flag:\n        step()\n        try:\n'
            '            raise KeyError()\n        except ArithmeticError:\n'
            '            pass\n    return 1\n'
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 8 in second for first, second in spans)

    def test_a_finally_that_could_raise_reaches_the_handlers_around_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag, a):\n    try:\n        try:\n            if flag:\n'
            '                return 1\n            held = 2\n'
            '        finally:\n            assert a\n    except Exception:\n'
            '        held = 3\n'
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 10 in second for first, second in spans)

    def test_an_unread_kind_past_the_last_said_raise_cannot_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            raise ValueError()\n        except ValueError:\n"
            "            return 1\n        except errors.Other:\n"
            "            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_an_unread_kind_a_body_cannot_reach_cannot_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            kept = 1\n"
            "            try:\n                return 1\n"
            "            except errors.ValueError:\n                work()\n"
            "        kept = 2\n    except ValueError:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 11 in second for first, second in spans)

    def test_a_handler_naming_a_kind_through_something_else_still_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            work()\n            return 1\n        except ValueError:\n"
            "            return 2\n        except (ValueError, builtins.TypeError):\n"
            "            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 11 in second for first, second in spans)

    def test_a_tuple_a_set_holds_could_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            for part in {(): 1, (1,): 2}:\n                return 1\n"
            "        except TypeError:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 9 in second for first, second in spans)

    def test_what_a_set_or_a_mapping_cannot_hold_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a set holding a list': '            for part in {[]}:\n',
            'a mapping keyed on a list': '            for part in {[]: 1}:\n',
        }
        unpaired = [
            label for label, loop in shapes.items()
            if not any(
                3 in first and 10 in second
                for first, second in self._spans(
                    "def f(flag):\n    if flag:\n        mark()\n        try:\n"
                    + loop + "                pass\n            return 1\n"
                    "        except TypeError:\n            pass\n    later()\n",
                    tmp_path,
                    monkeypatch,
                )
            )
        ]

        assert unpaired == list(shapes)

    def test_going_over_what_gives_no_turn_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            for part in 1:\n                pass\n            return 1\n"
            "        except TypeError:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 10 in second for first, second in spans)

    def test_a_turn_handed_to_more_than_a_name_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            for first, second in [1]:\n                pass\n"
            "            return 1\n        except TypeError:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 10 in second for first, second in spans)

    def test_what_an_and_stands_as_is_what_is_gone_over(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'an and standing as a number': '            for part in 1 and 2:\n',
            'an or standing as a number': '            for part in [] or 1:\n',
            'a comparison gone over': '            for part in (1 < 2):\n',
        }
        unpaired = [
            label for label, loop in shapes.items()
            if not any(
                3 in first and 10 in second
                for first, second in self._spans(
                    "def f(flag):\n    if flag:\n        mark()\n        try:\n"
                    + loop + "                pass\n            return 1\n"
                    "        except TypeError:\n            pass\n    later()\n",
                    tmp_path,
                    monkeypatch,
                )
            )
        ]

        assert unpaired == list(shapes)

    def test_a_part_an_and_never_reaches_could_raise_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            if True or work():\n                pass\n            return 1\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_raise_a_with_is_not_told_of_may_still_be_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        with held():\n            mark()\n"
            "            return work()\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 6 in second for first, second in spans)

    def test_a_part_before_one_that_settles_it_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'an or settled after a call': '            if work() or True:\n',
            'an and settled after a call': '            if work() and False:\n',
        }
        unpaired = [
            label for label, branch in shapes.items()
            if not any(
                3 in first and 9 in second
                for first, second in self._spans(
                    "def f(flag):\n    if flag:\n        mark()\n        try:\n"
                    + branch + "                return 1\n"
                    "        except Exception:\n            pass\n    later()\n",
                    tmp_path,
                    monkeypatch,
                )
            )
        ]

        assert unpaired == list(shapes)

    def test_an_and_settles_only_where_what_runs_first_is_written_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        if work() and False:\n"
            "            pass\n        else:\n            return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 7 in second for first, second in spans)

    def test_what_a_match_is_given_and_asks_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a subject worked out': (
                "            match work():\n                case _:\n"
                "                    return 1\n"
            ),
            'a guard worked out': (
                "            match 1:\n                case _ if work() or True:\n"
                "                    return 1\n"
            ),
            'a body that acts': (
                "            match 1:\n                case _:\n"
                "                    work()\n            return 1\n"
            ),
        }
        unpaired = []

        for label, held in shapes.items():
            source = (
                "def f(flag):\n    if flag:\n        mark()\n        try:\n"
                + held + "        except Exception:\n            pass\n"
                "    later()\n"
            )
            last = source.splitlines().index('    later()') + 1
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(3 in first and last in second for first, second in spans):
                unpaired.append(label)

        assert unpaired == list(shapes)

    def test_a_call_spelled_as_something_empty_is_written_out_as_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        if not set():\n"
            "            return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 6 in second for first, second in spans)

    def test_a_kind_the_language_does_not_carry_is_no_catch_for_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            raise Stop()\n        except Exception:\n            return 1\n"
            "        except Stop:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 10 in second for first, second in spans)

    def test_an_else_a_loop_never_reaches_raises_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            for part in (1,):\n                return 1\n            else:\n"
            "                work()\n        except Exception:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 11 in second for first, second in spans)

    def test_an_else_a_loop_reaches_could_still_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            for part in (1,):\n                pass\n            else:\n"
            "                return work()\n        except Exception:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 11 in second for first, second in spans)

    def test_every_alternative_of_a_pattern_is_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a kind beside a wildcard': (
                '                case Missing() | _ if False:\n'
            ),
            'a kind bound by a name': (
                '                case (Missing() | _) as held if False:\n'
            ),
            'a value named through something': (
                '                case math.tau | _ if False:\n'
            ),
            'a mapping keyed through something': (
                '                case {math.tau: _} | _ if False:\n'
            ),
            'a kind inside a sequence': (
                '                case [Missing()] | _ if False:\n'
            ),
            'a kind inside a mapping': (
                '                case {1: Missing()} | _ if False:\n'
            ),
        }
        unpaired = []

        for label, case in shapes.items():
            source = (
                "def f(flag):\n    if flag:\n        mark()\n        try:\n"
                "            match 1:\n" + case
                + "                    pass\n                case _:\n"
                "                    return 1\n        except NameError:\n"
                "            pass\n    later()\n"
            )
            last = source.splitlines().index('    later()') + 1
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(3 in first and last in second for first, second in spans):
                unpaired.append(label)

        assert unpaired == list(shapes)

    def test_a_pattern_is_read_before_its_guard_holds_it_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            match 1:\n                case Missing() if False:\n"
            "                    pass\n                case _:\n"
            "                    return 1\n        except NameError:\n"
            "            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 12 in second for first, second in spans)

    def test_a_loop_taking_no_turn_hands_nothing_over(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            for first, second in []:\n                pass\n"
            "            return 1\n        except ValueError:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_loop_raising_before_a_turn_runs_nothing_in_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'nothing to take a turn from': '        for part in 1:\n',
            'an answer to take a turn from': '        for part in (1 < 2):\n',
            'the other answer to take a turn from': '        for part in (not 1):\n',
            'a turn awaited from what is written out': (
                '        async for part in (1,):\n'
            ),
        }
        paired = [
            label for label, loop in shapes.items()
            if any(
                3 in first and 6 in second
                for first, second in self._spans(
                    "async def f(flag):\n    if flag:\n        mark()\n" + loop
                    + "            return 1\n    later()\n",
                    tmp_path,
                    monkeypatch,
                )
            )
        ]

        assert paired == list(shapes)

    def test_an_ending_that_could_raise_bounds_the_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a context manager ending': (
                "        with held():\n            if flag:\n                return 1\n"
            ),
            'a context manager awaited': (
                "        async with held():\n            if flag:\n"
                "                return 1\n"
            ),
        }
        unpaired = []

        for label, inner in shapes.items():
            source = (
                "async def f(flag):\n    try:\n" + inner
                + "    except ValueError:\n        pass\n    after()\n"
            )
            last = source.splitlines().index('    after()') + 1
            held = source.splitlines().index('                return 1') + 1
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(held in first and last in second for first, second in spans):
                unpaired.append(label)

        assert unpaired == list(shapes)

    def test_one_manager_may_swallow_the_ending_of_another(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    with held(), also():\n        if flag:\n"
            "            return 1\n    return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 5 in second for first, second in spans)

    def test_what_a_with_hands_over_may_come_apart(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        with held() as (first, second):\n"
            "            return 1\n    return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 5 in second for first, second in spans)

    def test_a_with_of_many_managers_inside_a_branch_may_carry_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        with held(), also():\n"
            "            return 1\n    return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 5 in second for first, second in spans)

    def test_a_with_of_one_manager_inside_a_branch_still_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        with held():\n"
            "            return 1\n    return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 5 in second for first, second in spans)

    def test_a_handler_inside_the_ending_had_its_turn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    with held():\n        try:\n            if flag:\n"
            "                return 1\n            inside()\n"
            "        except Exception:\n            handled()\n"
            "        after_handler()\n    after_with()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 9 in second for first, second in spans)
        assert any(5 in first and 10 in second for first, second in spans)

    def test_the_nearest_ending_is_the_one_a_raise_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        with held():\n            if flag:\n"
            "                return 1\n    finally:\n        risky()\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 8 in second for first, second in spans)

    def test_a_finally_on_the_same_try_is_caught_nowhere_in_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            return 1\n"
            "        inside()\n    except ValueError:\n        handled()\n"
            "    finally:\n        risky()\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 10 in second for first, second in spans)

    def test_an_ending_outside_the_function_bounds_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def outer(x):\n    try:\n        def inner(y):\n            try:\n"
            "                if y:\n                    return 1\n"
            "            except ValueError:\n                pass\n"
            "            later()\n        inner(x)\n    finally:\n        risky()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in first and 9 in second for first, second in spans)

    def test_a_finally_a_loop_exit_never_reaches_overrides_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a break bound for a loop inside': '                break\n',
            'a continue bound for one': '                continue\n',
        }
        unpaired = []

        for label, leaving in shapes.items():
            source = (
                "def f(flag):\n    try:\n        for x in [1]:\n"
                "            if flag:\n                mark()\n" + leaving
                + "            other()\n        after_loop()\n    finally:\n"
                "        return\n"
            )
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(5 in first and 8 in second for first, second in spans):
                unpaired.append(label)

        assert unpaired == list(shapes)

    def test_a_heading_written_over_several_lines_shares_its_last(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(check, hit):\n    if (\n            check()): hit('arm')\n"
            "    else:\n        hit('else')\n"
        )

        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_later_grouped_kind_is_weighed_after_an_earlier_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            value = 1\n"
            "            try:\n                raise ValueError()\n"
            "            except* ValueError:\n                value = 2\n"
            "            except* boom():\n                value = 3\n"
            "            return 1\n        value = 4\n    except RuntimeError:\n"
            "        value = 5\n    return 0\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 14 in second for first, second in spans)
        assert any(4 in first and 12 in second for first, second in spans)

    def test_every_kind_a_grouped_try_names_is_worked_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                raise ValueError\n            except* ValueError:\n"
            "                pass\n            except* missing:\n"
            "                pass\n            return\n    except NameError:\n"
            "        pass\n    marker()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 13 in second for first, second in spans)

    def test_a_kind_written_over_several_lines_shares_its_last(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(seen):\n    try:\n        raise ValueError()\n    except (\n"
            "            ValueError,\n            KeyError): seen('a')\n"
            "    except TypeError:\n        seen('b')\n"
        )

        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_guard_written_over_several_lines_shares_its_last(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(seen, x):\n    match x:\n        case 1 if (\n"
            "                seen('g')): pass\n        case _:\n            seen('b')\n"
        )

        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_finally_that_never_ends_is_what_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            return 1\n"
            "    finally:\n        while True:\n            seen()\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 8 in second for first, second in spans)
        assert not any(4 in first and 7 in second for first, second in spans)

    def test_a_loop_written_later_holds_no_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, items):\n    for x in items:\n        try:\n"
            "            if flag:\n                mark()\n                break\n"
            "        finally:\n            return 1\n        after_try()\n"
            "    later()\n\ndef other(ys):\n    for y in ys:\n        pass\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 10 in second for first, second in spans)

    def test_a_finally_an_endless_arm_never_reaches_is_an_alternative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            mark()\n"
            "            while True:\n                pass\n    finally:\n"
            "        cleanup()\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 8 in second for first, second in spans)

    def test_a_line_a_heading_shares_is_no_alternative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a condition on the line': (
                "def f(seen):\n    if seen.append('c'): pass\n"
                "    else: seen.append('b')\n"
            ),
            'a kind on the line': (
                "def f(seen):\n    try:\n        raise ValueError()\n"
                "    except named(): pass\n"
                "    except ValueError: seen.append('b')\n"
            ),
            'a guard on the line': (
                "def f(seen, x):\n    match x:\n"
                "        case 1 if seen.append('g'): pass\n"
                "        case _: seen.append('b')\n"
            ),
        }
        unpaired = [
            label for label, source in shapes.items()
            if not self._spans(source, tmp_path, monkeypatch)
        ]

        assert unpaired == list(shapes)

    def test_the_nearest_finally_is_what_the_branch_is_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    for outer in [0]:\n        try:\n"
            "            for inner in [0]:\n                try:\n"
            "                    if flag:\n                        return 1\n"
            "                finally:\n                    break\n"
            "            reached()\n        finally:\n            return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(7 in first and 10 in second for first, second in spans)

    def test_a_nearer_finally_hands_its_way_to_the_one_around_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        for x in [0]:\n            try:\n"
            "                if flag:\n                    mark()\n"
            "                    break\n            finally:\n"
            "                return 1\n        after_loop()\n    finally:\n"
            "        return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in first and 10 in second for first, second in spans)

    def test_a_jump_in_a_loops_else_reaches_the_loop_outside(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    for outer in [0]:\n        try:\n"
            "            for inner in []:\n                pass\n"
            "            else:\n                if flag:\n"
            "                    marked()\n                    break\n"
            "        finally:\n            continue\n    else:\n"
            "        reached()\n    return 1\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(8 in first and 13 in second for first, second in spans)

    def test_a_finally_overrides_no_arm_that_names_no_way(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, stop):\n    try:\n        if flag:\n            mark()\n"
            "            if stop:\n                raise ValueError()\n"
            "            return 1\n        other()\n    finally:\n        return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 8 in second for first, second in spans)

    def test_a_pair_the_sign_refuses_answers_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        if -1 in b'ab':\n"
            "            return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 6 in second for first, second in spans)

    def test_a_finally_that_could_raise_bounds_the_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        try:\n            if x:\n"
            "                return 1\n            pass\n        finally:\n"
            "            return risky()\n    except ValueError:\n        pass\n"
            "    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 11 in second for first, second in spans)

    def test_a_return_of_nothing_could_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'nothing at all': '            return\n',
            'a tuple written out': '            return (1, 2)\n',
            'an answer written out': '            return not True\n',
            'a comparison written out': '            return 1 < 2\n',
            'a value written out on its own': (
                '            (1, 2)\n            return 1\n'
            ),
        }
        paired = []

        for label, leaving in shapes.items():
            source = (
                "def f(x):\n    try:\n        if x:\n" + leaving
                + "    except ValueError:\n        pass\n    two()\n"
            )
            last = source.splitlines().index('    two()') + 1
            spans = self._spans(source, tmp_path, monkeypatch)

            if any(4 in first and last in second for first, second in spans):
                paired.append(label)

        assert paired == list(shapes)

    def test_a_case_taking_less_than_every_value_reads_what_follows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a narrow case, guarded': '                case 0 if True:\n',
            'a narrow case': '                case 0:\n',
        }
        unpaired = []

        for label, case in shapes.items():
            source = (
                "def f(flag):\n    if flag:\n        mark()\n        try:\n"
                "            match 1:\n" + case
                + "                    return 1\n                case _:\n"
                "                    return work()\n        except Exception:\n"
                "            pass\n    later()\n"
            )
            last = source.splitlines().index('    later()') + 1
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(3 in first and last in second for first, second in spans):
                unpaired.append(label)

        assert unpaired == list(shapes)

    def test_nothing_after_a_case_that_always_matches_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            match 1:\n                case _ if True:\n"
            "                    return 1\n                case 2:\n"
            "                    work()\n        except Exception:\n"
            "            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 12 in second for first, second in spans)

    def test_a_case_a_guard_holds_back_raises_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            match 1:\n                case _ if False:\n"
            "                    work()\n                case _:\n"
            "                    return 1\n        except Exception:\n"
            "            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 12 in second for first, second in spans)

    def test_a_comparison_that_refuses_answers_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        if 1 < 'a':\n"
            "            raise ValueError()\n        return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 7 in second for first, second in spans)

    def test_a_pattern_asking_something_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            match 1:\n                case Held():\n                    pass\n"
            "            return 1\n        except Exception:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 11 in second for first, second in spans)

    def test_a_branch_written_out_raises_only_where_its_arm_does(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            if False:\n                work()\n            return 1\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_match_asking_nothing_raises_only_where_a_body_does(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            match 1:\n                case other:\n                    return 1\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_branch_that_never_holds_holds_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        if False:\n"
            "            raise ValueError()\n        return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 7 in second for first, second in spans)

    def test_a_loop_a_continue_carries_round_can_still_finish(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, cond):\n    if flag:\n        mark()\n"
            "        for part in (1,):\n            if cond:\n"
            "                continue\n            return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 8 in second for first, second in spans)

    def test_a_body_gone_over_a_turn_at_a_time_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            for part in (1,):\n                work()\n            return 1\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 10 in second for first, second in spans)

    def test_an_endless_loop_doing_nothing_reaches_no_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            while True:\n                pass\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 9 in second for first, second in spans)

    def test_a_condition_that_could_raise_reaches_its_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            while not [work()]:\n                pass\n            return 1\n"
            "        except ValueError:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 10 in second for first, second in spans)

    def test_going_over_something_a_turn_at_a_time_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "async def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            async for part in []:\n                pass\n            return 1\n"
            "        except TypeError:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 10 in second for first, second in spans)

    def test_a_handler_an_earlier_one_covers_is_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            raise ValueError()\n        except Exception:\n"
            "            return 1\n        except TypeError:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_loop_that_runs_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, xs):\n    if flag:\n        mark()\n        try:\n"
            "            for part in xs:\n                work()\n            return 1\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 10 in second for first, second in spans)

    def test_nothing_after_a_handler_catching_everything_is_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            raise ValueError()\n        except BaseException:\n"
            "            return 1\n        except ValueError:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_body_that_never_runs_raises_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            while False:\n                work()\n            return 1\n"
            "        except Exception:\n            pass\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_a_raise_naming_nothing_plain_is_no_catch_for_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise errors.Failed()\n"
            "            except Exception:\n                return 1\n"
            "        later()\n    except BaseException:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 11 in second for first, second in spans)

    def test_a_kind_under_exception_is_caught_by_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise ValueError()\n"
            "            except Exception:\n                return 1\n"
            "        later()\n    except ValueError:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 9 in second for first, second in spans)

    def test_a_body_that_cannot_raise_reaches_no_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            return 1\n        except ValueError:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 8 in second for first, second in spans)

    def test_a_body_that_could_raise_reaches_its_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            return work()\n        except ValueError:\n            pass\n"
            "    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 8 in second for first, second in spans)

    def test_every_loop_written_to_run_nothing_holds_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'a condition that never holds': '        while not True:\n',
            'both parts failing': '        while False or False:\n',
            'one part failing an and': '        while True and False:\n',
            'a full list said not to hold': '        while not [1]:\n',
            'an empty mapping to go over': '        for part in {}:\n',
            'an empty string to go over': "        for part in '':\n",
            'empty bytes to go over': "        for part in b'':\n",
            'nothing to go over': '        for part in ():\n',
            'an empty list to go over': '        for part in []:\n',
            'an empty mapping as a condition': '        while {}:\n',
        }
        paired = [
            label for label, loop in shapes.items()
            if any(
                3 in first and 7 in second
                for first, second in self._spans(
                    "def f(flag):\n    if flag:\n        mark()\n" + loop
                    + "            raise ValueError()\n        return 1\n    later()\n",
                    tmp_path,
                    monkeypatch,
                )
            )
        ]

        assert paired == list(shapes)

    def test_a_loop_that_never_runs_holds_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        while False:\n"
            "            raise ValueError()\n        return\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 7 in second for first, second in spans)

    def test_a_handler_naming_no_kind_catches_the_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            try:\n"
            "                mark()\n                raise TypeError()\n"
            "            except:\n                return 1\n"
            "        later()\n    except TypeError:\n        handle()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 9 in second for first, second in spans)

    def test_a_raise_a_with_may_swallow_names_no_single_way(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        with held():\n"
            "            raise errors.Failed()\n        return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(3 in first and 7 in second for first, second in spans)

    def test_an_endless_loop_that_never_leaves_reaches_the_rest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(ready):\n    if ready:\n        do()\n        while True:\n"
            "            work()\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 6 in second for first, second in spans)

    def test_a_loop_else_that_returns_leaves_the_endless_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(ready, ys, cond):\n    if ready:\n        do()\n"
            "        while True:\n            for y in ys:\n"
            "                if cond:\n                    break\n"
            "            else:\n                return 1\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 10 in second for first, second in spans)

    def test_an_arm_raising_then_returning_reaches_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(cond, other):\n    try:\n        if cond:\n"
            "            if other:\n                raise E()\n            return 1\n"
            "        tail()\n    except E:\n        handle()\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 9 in second for first, second in spans)
        assert not any(5 in second and 9 in first for first, second in spans)

    def test_an_arm_leaving_by_two_ways_reaches_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, stop):\n    for item in [1]:\n        if flag:\n"
            "            mark()\n            if stop:\n                break\n"
            "            return\n        inside()\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 9 in second for first, second in spans)
        assert not any(4 in second and 9 in first for first, second in spans)

    def test_an_earlier_exit_in_a_finally_names_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, stop):\n    for x in [1]:\n        try:\n"
            "            if flag:\n                mark()\n                return\n"
            "        finally:\n            if stop:\n                break\n"
            "            return\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 11 in second for first, second in spans)
        assert not any(5 in second and 11 in first for first, second in spans)

    def test_a_body_leaving_on_some_paths_names_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag, leave):\n    for item in [1]:\n        if flag:\n"
            "            try:\n                if leave:\n                    break\n"
            "            except ValueError:\n                return\n"
            "            else:\n                return\n        other()\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(6 in first and 11 in second for first, second in spans)
        assert not any(6 in first and 12 in second for first, second in spans)

    def test_a_body_that_leaves_skips_its_else(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            mark()\n"
            "            break\n        except ValueError:\n            return 1\n"
            "        else:\n            return 2\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 10 in second for first, second in spans)
        assert not any(4 in second and 10 in first for first, second in spans)

    def test_a_break_in_a_caught_try_still_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            if x:\n"
            "                mark()\n                return 1\n        finally:\n"
            "            try:\n                break\n"
            "            except ValueError:\n                pass\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first and 12 in second for first, second in spans)
        assert not any(5 in second and 12 in first for first, second in spans)

    def test_a_return_in_a_caught_try_still_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            return 1\n"
            "        two()\n    except ValueError:\n        pass\n"
            "    three()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 8 in second for first, second in spans)

    def test_a_value_written_out_given_a_name_could_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'one name': '            held = 1\n',
            'two names at once': '            held = kept = 1\n',
            'names written out together': '            held, kept = 1, 2\n',
            'a name with a kind written out': '            held: 1 = 2\n',
            'a value spelled out in letters': '            held, kept = "ab"\n',
            'a value held in a set': '            held, kept = {1, 2}\n',
            'a value keyed by name': (
                "            held, kept = {'a': 1, 'b': 2}\n"
            ),
            'a value an and stands as': '            held, kept = True and (1, 2)\n',
            'a name taking what is left': '            held, *kept = (1, 2, 3)\n',
            'a kind no raise of the body reaches': (
                '            try:\n                return 1\n'
                '            except (1 / 0):\n                pass\n'
            ),
            'a handler no raise of the body reaches': (
                '            try:\n                raise ValueError()\n'
                '            except ValueError:\n                return 3\n'
                '            except named():\n                pass\n'
            ),
            'an else the body never reaches': (
                '            try:\n                return 1\n'
                '            except ValueError:\n                pass\n'
                '            else:\n                work()\n'
            ),
            'a raise its handler catches': (
                '            try:\n                raise ValueError("no")\n'
                '            except ValueError:\n                pass\n'
            ),
            'a try nothing in which could raise': (
                '            try:\n                return 1\n'
                '            finally:\n                pass\n'
            ),
            'a handler no quiet body reaches': (
                '            try:\n                return 1\n'
                '            except ValueError:\n                return work()\n'
            ),
        }
        paired = []

        for label, held in shapes.items():
            source = (
                "def f(x):\n    try:\n        if x:\n" + held
                + "            return 2\n    except ValueError:\n        pass\n"
                "    two()\n"
            )
            last = source.splitlines().index('    two()') + 1
            spans = self._spans(source, tmp_path, monkeypatch)

            if any(4 in first and last in second for first, second in spans):
                paired.append(label)

        assert paired == list(shapes)

    def test_no_handler_runs_after_one_naming_every_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            try:\n"
            "                work()\n                raise ValueError()\n"
            "            except BaseException:\n                return 3\n"
            "            except ValueError:\n                pass\n"
            "    except ValueError:\n        pass\n    two()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 13 in second for first, second in spans)

    def test_a_handler_an_earlier_one_took_the_raise_from_never_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            try:\n"
            "                raise ValueError()\n"
            "            except ValueError:\n                return 3\n"
            "            except Exception:\n                pass\n"
            "    except ValueError:\n        pass\n    two()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 12 in second for first, second in spans)

    def test_a_handler_naming_another_kind_never_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    if flag:\n        mark()\n        try:\n"
            "            raise ValueError('no')\n        except TypeError:\n"
            "            return 3\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 8 in second for first, second in spans)

    def test_a_value_coming_apart_could_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        shapes = {
            'too few things to go round': '            held, kept = (1,)\n',
            'a name on something else': '            held.part = 1\n',
            'a starred name on something else': '            *held.part, = [1]\n',
            'too few things for the names left': '            held, *kept, last = (1,)\n',
            'a group named by a handler taking groups': (
                '            try:\n                raise ValueError()\n'
                '            except* ExceptionGroup:\n                pass\n'
                '            except* ValueError:\n                pass\n'
            ),
            'a kind worked out by a handler that never runs': (
                '            try:\n                raise ValueError()\n'
                '            except (1 / 0):\n                pass\n'
                '            except ValueError:\n                return 3\n'
            ),
            'a value not written out': '            held = work()\n',
            'a kind named by a name': '            held: int = 2\n',
            'an ending that acts': (
                '            try:\n                pass\n'
                '            finally:\n                work()\n'
            ),
            'a name beyond a name given nothing': '            held.part: 1\n',
            'a kind named by a handler': (
                '            try:\n                raise ValueError()\n'
                '            except (BaseException, named()):\n                pass\n'
            ),
            'a raise no handler catches': (
                '            try:\n                raise ValueError("no")\n'
                '            except TypeError:\n                pass\n'
            ),
            'a body that could raise unsaid': (
                '            try:\n                work()\n'
                '            except ValueError:\n                pass\n'
            ),
            'a handler body that acts': (
                '            try:\n                raise ValueError()\n'
                '            except BaseException:\n                work()\n'
            ),
            'an else that acts': (
                '            try:\n                pass\n'
                '            except ValueError:\n                pass\n'
                '            else:\n                work()\n'
            ),
        }
        unpaired = []

        for label, held in shapes.items():
            source = (
                "def f(x):\n    try:\n        if x:\n" + held
                + "            return 2\n    except ValueError:\n        pass\n"
                "    two()\n"
            )
            last = source.splitlines().index('    two()') + 1
            spans = self._spans(source, tmp_path, monkeypatch)

            if not any(4 in first and last in second for first, second in spans):
                unpaired.append(label)

        assert unpaired == list(shapes)

    def test_a_handler_an_arm_could_raise_into_is_no_alternative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    try:\n        if flag:\n            mark()\n"
            "            return\n        other()\n    except ValueError:\n"
            "        recover()\n    else:\n        fine()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 8 in second for first, second in spans)
        assert any(4 in first and 6 in second for first, second in spans)

    def test_an_arm_that_could_raise_reaches_no_further_than_the_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            one()\n"
            "            return 1\n    except ValueError:\n        pass\n"
            "    two()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 8 in second for first, second in spans)

    def test_a_with_around_a_branch_bounds_what_it_reaches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(flag):\n    with held():\n        if flag:\n            mark()\n"
            "            return work()\n    later()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(4 in first and 6 in second for first, second in spans)

    def test_a_raise_caught_inside_a_finally_is_no_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            return 1\n"
            "        return 2\n    finally:\n        try:\n"
            "            raise ValueError()\n        except ValueError:\n"
            "            pass\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 5 in second for first, second in spans)

    def test_sibling_except_handlers_are_arms(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        work()\n    except ValueError:\n"
            "        one()\n    except TypeError:\n        two()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 7 in second for first, second in spans)

    def test_a_header_with_a_comment_belongs_to_its_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = self._CAUGHT_RAISE.replace('except E:', 'except E:  # the only kind')
        spans = self._spans(source, tmp_path, monkeypatch)
        reached = next(second for first, second in spans if 4 in first)

        assert reached == {6, 9, 10}

    def test_a_comment_above_a_handler_body_is_passed_over(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            mark(x)\n"
            "            raise E('a')\n        more(x)\n    except E:\n"
            "        # why\n        recover()\n    else:\n        fine()\n"
            "    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)
        reached = next(second for first, second in spans if 4 in first)

        assert reached == {6, 10, 11}

    def test_an_except_star_handler_is_read_as_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = self._CAUGHT_RAISE.replace('except E:', 'except* E:')
        spans = self._spans(source, tmp_path, monkeypatch)
        reached = next(second for first, second in spans if 4 in first)

        assert reached == {6, 9, 10}
        assert any(8 in first and 10 in second for first, second in spans)

    def test_a_caught_raise_reaches_no_further_than_its_try(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            act(x)\n"
            "            raise E('a')\n        more(x)\n    except E:\n"
            "        recover()\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 6 in second for first, second in spans)
        assert not any(9 in second for _, second in spans)

    def test_a_raise_in_the_else_reaches_past_the_try(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        start(x)\n    except E:\n        recover()\n"
            "    else:\n        if x:\n            mark(x)\n            raise F('a')\n"
            "        more(x)\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(8 in first and 11 in second for first, second in spans)

    def test_a_raise_skips_the_trys_else(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            act(x)\n"
            "            raise E('a')\n        more(x)\n    except E:\n"
            "        recover()\n    else:\n        done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 10 in second for first, second in spans)
        assert not any(8 in second for _, second in spans)

    def test_a_match_break_in_a_finally_is_a_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            if x:\n"
            "                act(x)\n                return 1\n            go(x)\n"
            "        finally:\n            match x:\n                case _:\n"
            "                    break\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert spans
        assert not any(12 in second for _, second in spans)

    def test_a_nested_function_in_a_finally_is_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            return 1\n        work()\n"
            "    finally:\n        def unused():\n            return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 5 in second for first, second in spans)

    def test_a_loop_in_a_finally_is_no_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            return 1\n        work()\n"
            "    finally:\n        for item in [1]:\n            break\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 5 in second for first, second in spans)

    def test_a_one_sided_finally_inside_a_branch_reaches_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        if x:\n            try:\n"
            "                act(x)\n                return 1\n            finally:\n"
            "                if flag:\n                    break\n        go(x)\n"
            "    done()\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_nested_return_under_an_outer_finally_keeps_to_its_function(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            def inner(y):\n"
            "                if y:\n                    act(y)\n                    return 1\n"
            "                return go(y)\n\n            inner(x)\n        finally:\n"
            "            break\n    after()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in first and 8 in second for first, second in spans)
        assert not any(13 in second or 10 in second for _, second in spans)

    def test_a_conditional_finally_reaches_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            if x:\n"
            "                record(x)\n                return 1\n            go(x)\n"
            "        finally:\n            if x:\n                break\n    after()\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_continue_in_a_loop_else_carries_on_the_outer_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs, ys):\n    for x in xs:\n        for y in ys:\n            pass\n"
            "        else:\n            if x:\n                record(x)\n"
            "                continue\n        after(x)\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(7 in first and 9 in second for first, second in spans)

    def test_a_finally_breaking_an_outer_loop_reaches_past_the_inner_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs, ys):\n    for x in xs:\n        try:\n"
            "            for y in ys:\n                if y:\n                    act(y)\n"
            "                    return 1\n            between()\n        finally:\n"
            "            break\n        after()\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in first and 8 in second and 11 in second
                   for first, second in spans)

    def test_a_finally_leaving_two_ways_reaches_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            if x:\n"
            "                act(x)\n                return 1\n            go(x)\n"
            "        finally:\n            if x:\n                break\n"
            "            else:\n                return 2\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(5 in first for first, _ in spans)

    def test_a_finally_that_breaks_overrides_an_inner_return(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            if x:\n"
            "                act(x)\n                return 1\n            go(x)\n"
            "        finally:\n            break\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert spans
        assert not any(10 in second for _, second in spans)

    def test_a_raise_in_a_handler_passes_its_own_try(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        start(x)\n    except E:\n        if x:\n"
            "            act(x)\n            raise F('a')\n        inner(x)\n"
            "    else:\n        fine()\n    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in first and 11 in second for first, second in spans)

    def test_a_same_line_finally_takes_no_line_above_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            act(x)\n"
            "            return 1\n        go(x)\n    finally: close()\n    return 2\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in second for _, second in spans)
        assert not any(7 in second for _, second in spans)

    def test_a_same_line_loop_else_takes_no_line_above_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        if x:\n            act(x)\n"
            "            continue\n        go(x)\n    else: done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(6 in second for _, second in spans)
        assert not any(7 in second for _, second in spans)


class TestOpenCandidates:

    @_NEEDS_BASELINE
    def test_no_full_module_carries_an_open_candidate(self) -> None:
        assert check_wiki._open_candidates(
            check_wiki._finding_file_citations(),
        ) == []

    @_NEEDS_BASELINE
    def test_a_full_module_under_an_unanswered_question_is_caught(self) -> None:
        failures = check_wiki._open_candidates(
            {'praxis/core/health_tracker.py': {'H-050'}},
        )

        assert failures == [
            "docs/wiki/ledger.md: `praxis/core/health_tracker.py` is `full` "
            "while ['H-050'] leave a question on it",
        ]

    @_NEEDS_BASELINE
    def test_a_full_module_with_a_candidate_is_caught(self) -> None:
        failures = check_wiki._open_candidates(
            {'praxis/core/health_tracker.py': {'H-064'}},
        )
        assert failures == [
            "docs/wiki/ledger.md: `praxis/core/health_tracker.py` is `full` "
            "while ['H-064'] leave a question on it",
        ]


class TestMatchStatements:

    @staticmethod
    def _spans(
        source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> list[tuple[set[int], set[int]]]:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        return spans

    def test_a_with_that_returns_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        with lock:\n            return 1\n    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 5 in second for first, second in spans)

    def test_an_async_with_that_returns_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "async def f(x):\n    if x:\n        async with lock:\n"
            "            return 1\n    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 5 in second for first, second in spans)

    def test_a_with_that_raises_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        with suppress(E):\n"
            "            raise E('a')\n    go(x)\n"
        )
        assert not self._spans(source, tmp_path, monkeypatch)

    def test_a_match_that_returns_on_every_case_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        match x:\n            case 1:\n"
            "                return 1\n            case _:\n                return 2\n"
            "    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(3 in first and 8 in second for first, second in spans)

    def test_a_guarded_catch_all_is_no_catch_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        match x:\n            case 1:\n"
            "                return 1\n            case _ if flag:\n"
            "                return 2\n    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(8 in second for _, second in spans)

    def test_a_narrowing_last_case_is_no_catch_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        match x:\n            case 1:\n"
            "                return 1\n            case int() as n:\n"
            "                return n\n    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(8 in second for _, second in spans)

    def test_a_match_with_no_catch_all_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    if x:\n        match x:\n            case 1:\n"
            "                return 1\n            case 2:\n                return 2\n"
            "    go(x)\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert not any(8 in second for _, second in spans)

    def test_two_cases_are_two_arms(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    match x:\n        case 1:\n            one()\n"
            "        case 2:\n            two()\n        case _:\n            rest()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(4 in first and 6 in second for first, second in spans)
        assert any(4 in first and 8 in second for first, second in spans)
        assert any(6 in first and 8 in second for first, second in spans)


class TestTheIndexVocabulary:

    @_NEEDS_BASELINE
    def test_no_entry_leans_on_an_owned_term(self) -> None:
        assert check_wiki._index_vocabulary() == []

    def test_an_entry_teasing_a_count_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = tmp_path / 'README.md'
        page.write_text(
            '- [One](atoms/one.md) — the six ceilings on what a host may do.\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'README', page)

        assert check_wiki._index_vocabulary() == [
            f'{page}: the entry for one.md counts rather than describes, '
            'at "the six"',
        ]

    @pytest.mark.parametrize(
        ('described', 'teased'),
        [
            pytest.param('the six ceilings on what a host may do.', 'the six', id='the-six'),
            pytest.param('the one fee it nets off.', 'the one', id='the-one'),
            pytest.param("two of an outcome's figures differ.", 'two of', id='two-of'),
            pytest.param('the thirty names a venue answers to.', 'the thirty', id='the-thirty'),
        ],
    )
    def test_every_way_of_teasing_a_count_is_caught(
        self, described: str, teased: str, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = tmp_path / 'README.md'
        page.write_text(f'- [One](atoms/one.md) — {described}\n', encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'README', page)

        assert check_wiki._index_vocabulary() == [
            f'{page}: the entry for one.md counts rather than describes, '
            f'at "{teased}"',
        ]

    @pytest.mark.parametrize(
        'described',
        [
            pytest.param('a permit most calls take one of; asking the time takes none.', id='take-one-of'),
            pytest.param('the checks a host is read through, any one of which ends the start.', id='any-one-of'),
        ],
    )
    def test_one_taken_out_of_several_is_no_count(
        self, described: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = tmp_path / 'README.md'
        page.write_text(f'- [One](atoms/one.md) — {described}\n', encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'README', page)

        assert check_wiki._index_vocabulary() == []

    def test_an_entry_using_an_owned_term_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = tmp_path / 'README.md'
        page.write_text(
            '- [One](atoms/one.md) — read from the order book.\n', encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'README', page)

        assert check_wiki._index_vocabulary() == [
            f'{page}: the entry for one.md leans on "order book", '
            'which another article owns',
        ]


class TestACountBeyondCounting:
    def test_a_length_beyond_counting_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        (wiki / 'atoms').mkdir(parents=True)
        (wiki / 'README.md').write_text(
            f"`order.py` is {'9' * 4301} lines\n", encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        failures = check_wiki._counted_states()

        assert any('order.py' in failure for failure in failures)

    def test_references_beyond_counting_are_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = tmp_path / 'CHANGELOG.md'
        log.write_text(
            '## v1.0.0 on 1st of January, 2026\n\n'
            f"- Add {'9' * 4301} line references across 1 claims\n",
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'CHANGELOG', log)
        failures = check_wiki._latest_release_counts()

        assert any('line references' in failure for failure in failures)

    def test_states_beyond_counting_are_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        (wiki / 'atoms').mkdir(parents=True)
        held = '9' * 4301
        (wiki / 'README.md').write_text(
            f'{held} are `full`, {held} `partial` and {held} `uncovered`\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        failures = check_wiki._counted_states()

        assert any('full' in failure for failure in failures)

    @_NEEDS_BASELINE
    def test_a_grouped_ledger_count_beyond_counting_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ledger = tmp_path / 'ledger.md'
        ledger.write_text(
            '## Praxis — 1 modules\n\n'
            f"| all {'9' * 4301} | full |\n",
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'LEDGER', ledger)
        failures = check_wiki._ledger_coverage()

        assert failures

    @_NEEDS_BASELINE
    def test_a_ledger_count_beyond_counting_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ledger = tmp_path / 'ledger.md'
        ledger.write_text(
            f"## Praxis — {'9' * 4301} modules\n\n| a.py | full |\n",
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'LEDGER', ledger)
        failures = check_wiki._ledger_coverage()

        assert any('modules' in failure for failure in failures)

    def test_an_article_count_on_a_page_beyond_counting_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        (wiki / 'atoms').mkdir(parents=True)
        (wiki / 'README.md').write_text(
            f"{'9' * 4301} articles\n", encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        failures = check_wiki._counted_states()

        assert any('articles in the wiki' in failure for failure in failures)

    def test_an_article_count_beyond_counting_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = tmp_path / 'CHANGELOG.md'
        log.write_text(
            '## v1.0.0 on 1st of January, 2026\n\n'
            f"- Add {'9' * 4301} articles\n",
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'CHANGELOG', log)
        failures = check_wiki._latest_release_counts()

        assert any('articles' in failure for failure in failures)


class TestThePinnedTable:

    def test_the_table_names_the_commits_that_are_read(self) -> None:
        assert check_wiki._pinned_table() == []

    def test_a_missing_table_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        wiki.mkdir()
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)

        assert check_wiki._pinned_table() == [
            f'{wiki / "BASELINE.md"}: the baseline page is missing',
        ]

    def test_a_table_naming_another_nexus_commit_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        wiki.mkdir()
        (wiki / 'BASELINE.md').write_text(
            f'| Praxis | `{check_wiki.BASELINE}` |\n| Nexus | `0000000` |\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)

        assert check_wiki._pinned_table() == [
            f'{wiki / "BASELINE.md"}: names Nexus at 0000000, '
            f'while citations are read at {check_wiki.NEXUS_BASELINE}',
        ]

    def test_a_table_naming_another_commit_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = tmp_path / 'wiki'
        wiki.mkdir()
        (wiki / 'BASELINE.md').write_text(
            '| Praxis | `0000000` |\n| Nexus | `953477a` |\n', encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        failures = check_wiki._pinned_table()

        assert failures == [
            f'{wiki / "BASELINE.md"}: names Praxis at 0000000, '
            f'while citations are read at {check_wiki.BASELINE}',
        ]


class TestThePageChecks:

    def test_prose_past_the_cap_is_refused(self) -> None:
        body = '# One\n\n' + ' '.join(['word'] * 300)
        failures = check_wiki._check_length(body)

        assert failures == ['301 words of prose exceeds the 300 cap; split it']

    def test_prose_at_the_cap_passes(self) -> None:
        assert check_wiki._check_length(' '.join(['word'] * 300)) == []
        assert check_wiki._check_length(' '.join(['word'] * 301)) == [
            '301 words of prose exceeds the 300 cap; split it',
        ]

    def test_another_baseline_in_the_metadata_is_refused(self) -> None:
        meta = (
            'row: P1-01\nbaseline: 0000000\n'
            'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-01 09:00 UTC\n'
        )
        failures = check_wiki._check_metadata(meta, {'P1-01'})

        assert any('0000000' in failure for failure in failures)

    def test_metadata_with_no_row_is_refused(self) -> None:
        meta = (
            f'baseline: {check_wiki.BASELINE}\n'
            'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-01 09:00 UTC\n'
        )
        failures = check_wiki._check_metadata(meta, {'P1-01'})

        assert any('row' in failure for failure in failures)

    def test_metadata_with_no_baseline_is_refused(self) -> None:
        meta = (
            'row: P1-01\n'
            'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-01 09:00 UTC\n'
        )
        failures = check_wiki._check_metadata(meta, {'P1-01'})

        assert any('baseline' in failure for failure in failures)

    def test_an_unknown_row_in_the_metadata_is_refused(self) -> None:
        meta = (
            f'row: P9-99\nbaseline: {check_wiki.BASELINE}\n'
            'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-01 09:00 UTC\n'
        )
        failures = check_wiki._check_metadata(meta, {'P1-01'})

        assert any('P9-99' in failure for failure in failures)

    @_NEEDS_BASELINE
    def test_a_citation_past_a_file_is_refused_by_the_page_check(self) -> None:
        failures = check_wiki._check_citations(
            ['a claim | `order.py` 99999'], check_wiki._SourceFacts(),
        )

        assert any('past end of file' in failure for failure in failures)

    def test_a_link_to_a_missing_page_is_refused(self, tmp_path: Path) -> None:
        page = tmp_path / 'one.md'
        page.write_text('# One\n', encoding='utf-8')
        failures = check_wiki._broken_links(page, 'see [two](two.md)')

        assert any('two.md' in failure for failure in failures)

    def test_a_link_to_a_missing_anchor_is_refused(self, tmp_path: Path) -> None:
        page = tmp_path / 'one.md'
        page.write_text('# One\n\n## Here\n', encoding='utf-8')
        failures = check_wiki._broken_links(page, 'see [there](one.md#there)')

        assert any('there' in failure for failure in failures)


@_NEEDS_BASELINE
class TestTheGateOverACopiedWiki:

    @staticmethod
    def _copied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        wiki = tmp_path / 'docs' / 'wiki'
        wiki.parent.mkdir()
        shutil.copytree(check_wiki.WIKI, wiki)
        (tmp_path / 'scripts').mkdir()
        (tmp_path / 'scripts' / 'check_wiki.py').touch()
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        monkeypatch.setattr(check_wiki, 'REGISTER', wiki / 'register.md')
        monkeypatch.setattr(check_wiki, 'README', wiki / 'README.md')
        monkeypatch.setattr(check_wiki, 'LEDGER', wiki / 'ledger.md')
        check_wiki._uncommitted_pages.cache_clear()

        return wiki

    def test_a_faithful_copy_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self._copied(tmp_path, monkeypatch)

        assert check_wiki.main() == 0

    def test_an_article_citing_past_a_file_fails_the_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = self._copied(tmp_path, monkeypatch)
        page = wiki / 'atoms' / 'what-a-fill-is.md'
        page.write_text(
            page.read_text(encoding='utf-8').replace(
                '`events.py` 585-595', '`events.py` 99999',
            ),
            encoding='utf-8',
        )

        assert check_wiki.main() == 1

    def test_a_row_naming_a_missing_article_fails_the_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = self._copied(tmp_path, monkeypatch)
        register = wiki / 'register.md'
        register.write_text(
            register.read_text(encoding='utf-8').replace(
                'atoms/what-a-fill-is.md', 'atoms/what-a-fill-was.md', 1,
            ),
            encoding='utf-8',
        )

        assert check_wiki.main() == 1

    def test_an_article_over_the_cap_fails_the_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = self._copied(tmp_path, monkeypatch)
        page = wiki / 'atoms' / 'what-a-fill-is.md'
        page.write_text(
            page.read_text(encoding='utf-8')
            + '\n' + ' '.join(['word'] * 301) + '\n',
            encoding='utf-8',
        )

        assert check_wiki.main() == 1

    def test_an_article_naming_another_baseline_fails_the_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        wiki = self._copied(tmp_path, monkeypatch)
        page = wiki / 'atoms' / 'what-a-fill-is.md'
        page.write_text(
            page.read_text(encoding='utf-8').replace(
                f'baseline: {check_wiki.BASELINE}', 'baseline: 0000000',
            ),
            encoding='utf-8',
        )

        assert check_wiki.main() == 1

    @_NEEDS_BASELINE
    def test_a_line_inside_a_log_call_is_a_log_line(self) -> None:
        failures = check_wiki._check_citations(
            ['An order is recorded as refused | `execution_manager.py` 5526'],
            check_wiki._SourceFacts(),
        )

        assert any('log call' in failure for failure in failures)

    @_NEEDS_BASELINE
    def test_a_claim_about_the_message_may_cite_it(self) -> None:
        assert check_wiki._check_citations(
            ['The warning says it | `execution_manager.py` 5526'],
            check_wiki._SourceFacts(),
        ) == []

    def test_a_handler_name_rebinds_the_protocol(self) -> None:
        source = (
            'from typing import Protocol\n\n'
            'try:\n    work()\nexcept Exception as Protocol:\n    pass\n\n'
            'class Venue(Protocol):\n\n'
            '    def submit(self) -> None:\n        ...\n'
        )
        rebound = check_wiki._rebound_names(ast.parse(source))

        assert 'Protocol' in rebound

    def test_a_with_target_rebinds_the_protocol(self) -> None:
        source = (
            'from typing import Protocol\n\n'
            'with open("x") as Protocol:\n    pass\n\n'
            'class Venue(Protocol):\n\n'
            '    def submit(self) -> None:\n        ...\n'
        )

        assert 'Protocol' in check_wiki._rebound_names(ast.parse(source))

    def test_an_async_with_target_rebinds_the_protocol(self) -> None:
        source = (
            'from typing import Protocol\n\n'
            'async def f():\n    async with cm() as Protocol:\n        pass\n'
        )

        assert 'Protocol' in check_wiki._rebound_names(ast.parse(source))


class TestEveryListedShape:

    def test_every_banned_heading_is_refused(self) -> None:
        headings = ('## What it is', '## Overview', '## Introduction')
        refused = [
            heading for heading in headings
            if check_wiki._check_voice(f'# Title\n\nA thing is a thing.\n\n{heading}\n')
        ]

        assert refused == list(headings)

    def test_every_apparatus_shape_is_refused(self) -> None:
        parts = ('## Evidence', '| Claim | Source |')
        refused = [
            part for part in parts
            if check_wiki._check_voice(f'# Title\n\nA thing is a thing.\n\n{part}\n')
        ]

        assert refused == list(parts)

    def test_every_double_negative_tail_is_refused(self) -> None:
        tails = ('nothing', 'no one', 'nobody', 'never', 'none')
        refused = [
            tail for tail in tails
            if check_wiki._negative_definitions(f'It does not leave {tail} behind.')
        ]

        assert refused == list(tails)

    def test_a_heading_defining_by_negation_is_refused(self) -> None:
        headings = ('## One table, not two', '## A spread, not an average')
        refused = [
            heading for heading in headings
            if check_wiki._check_voice(f'# Title\n\nA thing is a thing.\n\n{heading}\n')
        ]

        assert refused == list(headings)

    def test_a_heading_naming_its_subject_passes(self) -> None:
        assert not check_wiki._check_voice(
            '# Title\n\nA thing is a thing.\n\n## Where the keys come from\n',
        )

    def test_every_double_negative_opening_is_refused(self) -> None:
        openings = ('does not leave', 'never leaves', "doesn't leave")
        refused = [
            opening for opening in openings
            if check_wiki._negative_definitions(f'It {opening} nothing behind.')
        ]

        assert refused == list(openings)

    def test_a_curly_apostrophe_opening_is_refused(self) -> None:
        assert check_wiki._negative_definitions(
            'It doesn\u2019t leave nothing behind.',
        )

    def test_every_counting_word_is_refused(self) -> None:
        numbers = (
            'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
            'ten', 'eleven', 'twelve', 'twenty', 'twenty-one', 'thirty',
        )
        refused = [
            number for number in numbers
            if check_wiki.TEASED_COUNT_RE.search(f'the {number} ceilings')
        ]

        assert refused == list(numbers)

    def test_a_hash_inside_a_string_is_no_comment(self) -> None:
        assert check_wiki._without_a_comment("    msg = 'a # b'") == "msg = 'a # b'"

    def test_a_comment_after_a_string_is_cut(self) -> None:
        assert check_wiki._without_a_comment("    msg = 'a'  # b") == "msg = 'a'"

    def test_a_bare_comment_is_one(self) -> None:
        assert check_wiki._bare_comment('   # why')
        assert check_wiki._bare_comment('')
        assert not check_wiki._bare_comment('    work()')


class TestRationale:

    def test_every_rationale_marker_is_refused(self) -> None:
        markers = (
            'to allow for', 'in order to', 'for the sake of', 'by design',
            'deliberately so', 'the reason being', 'precisely so',
            'the point being', 'the idea being',
        )
        refused = [
            marker for marker in markers
            if any(
                'reason the code does not state' in note
                for note in check_wiki._check_voice(
                    f'# T\n\nA thing is a thing.\n\nIt is skipped {marker} something.\n',
                )
            )
        ]

        assert refused == list(markers)

    def test_a_consequence_of_a_cited_fact_passes(self) -> None:
        notes = check_wiki._check_voice(
            '# T\n\nA thing is a thing.\n\n'
            'Some lists are shared, which is why a name in use is refused.\n',
        )

        assert not [note for note in notes if 'reason' in note]

    @_NEEDS_BASELINE
    def test_a_range_of_nothing_but_logging_is_a_log_call(self) -> None:
        failures = check_wiki._check_citations(
            ['The order is saved | `execution_manager.py` 5543-5552'],
            check_wiki._SourceFacts(),
        )

        assert any('log call' in failure for failure in failures)

    @_NEEDS_BASELINE
    def test_a_range_opening_on_a_comment_is_still_a_log_call(self) -> None:
        failures = check_wiki._check_citations(
            ['a claim | `execution_manager.py` 2482-2487'],
            check_wiki._SourceFacts(),
        )

        assert any('log call' in failure for failure in failures)

    @_NEEDS_BASELINE
    def test_a_range_running_from_a_log_into_code_is_code(self) -> None:
        assert check_wiki._check_citations(
            ['a claim | `execution_manager.py` 5544-5553'],
            check_wiki._SourceFacts(),
        ) == []

    @_NEEDS_BASELINE
    def test_a_claim_about_that_message_may_cite_the_range(self) -> None:
        assert check_wiki._check_citations(
            ['The warning says it | `execution_manager.py` 5543-5552'],
            check_wiki._SourceFacts(),
        ) == []

    def test_an_apostrophe_inside_double_quotes_closes_nothing(self) -> None:
        assert check_wiki._without_a_comment(
            'except errors["can\'t"]:  # handled',
        ) == 'except errors["can\'t"]:'

    def test_an_escaped_quote_keeps_the_string_open(self) -> None:
        assert check_wiki._without_a_comment(
            'except Error("a\\"#"):  # note',
        ) == 'except Error("a\\"#"):'

    def test_a_header_with_an_apostrophe_is_still_a_header(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(x):\n    try:\n        if x:\n            mark(x)\n"
            "            raise E('a')\n        more(x)\n"
            '    except Error("it\'s"):  # the only kind\n'
            "        recover()\n    else:\n        fine()\n    after()\n"
        )
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans = check_wiki._exclusive_spans(path)
        reached = next(second for first, second in spans if 4 in first)

        assert reached == {6, 9, 10}


class TestCodeLabels:

    def test_an_implementation_name_in_prose_is_refused(self) -> None:
        notes = check_wiki._check_voice(
            '# T\n\nA fill is a report.\n\nThe `Fill` type checks it.\n',
        )

        assert notes == [
            'names the code in its prose, at "Fill"; '
            'an implementation name belongs in the metadata',
        ]

    def test_prose_without_one_passes(self) -> None:
        notes = check_wiki._check_voice(
            '# T\n\nA fill is a report.\n\nThe record checks it.\n',
        )

        assert notes == []

    @_NEEDS_BASELINE
    def test_a_docstring_range_running_into_code_is_code(self) -> None:
        notes = check_wiki._check_citations(
            ['the docstring says so | `praxis/core/domain/trade_outcome.py` 1-30'],
            check_wiki._SourceFacts(),
        )

        assert any('docstring' in note for note in notes)

    @_NEEDS_BASELINE
    def test_a_range_opening_in_a_docstring_is_a_docstring(self) -> None:
        notes = check_wiki._check_citations(
            ['the body does it | `praxis/core/domain/trade_outcome.py` 1-12'],
            check_wiki._SourceFacts(),
        )

        assert any('docstring' in note for note in notes)

    @_NEEDS_BASELINE
    def test_a_range_mostly_docstring_is_a_docstring(self) -> None:
        notes = check_wiki._check_citations(
            ['a claim | `order.py` 30-37'], check_wiki._SourceFacts(),
        )

        assert any('docstring' in note for note in notes)


class TestEveryAlternationMarker:

    @_NEEDS_BASELINE
    def test_every_marker_excuses_a_pair(self) -> None:
        markers = (
            'or', 'either', 'otherwise', 'instead', 'rather than', 'unless',
            'against', 'need not', 'not both', 'alternative',
        )
        cache = check_wiki._SourceFacts()
        unexcused = [
            marker for marker in markers
            if check_wiki._docstring_citations(
                f'|a claim | `validate_trade_command.py` 137 {marker} 139|', cache,
            )
        ]

        assert unexcused == []

    @_NEEDS_BASELINE
    def test_a_pair_with_no_marker_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `validate_trade_command.py` 137 and 139|',
            check_wiki._SourceFacts(),
        )

        assert notes == [
            'validate_trade_command.py:137 and 139 are mutually exclusive branches',
        ]



class TestWhatAlwaysLeaves:
    @staticmethod
    def _last(source: str) -> ast.stmt:
        held = ast.parse(source).body[0]
        assert isinstance(held, ast.FunctionDef)

        return held.body[-1]

    def test_every_shape_that_leaves_on_every_path_is_read_as_one(self) -> None:
        shapes = {
            'return': 'def f(x):\n    return 1\n',
            'raise': 'def f(x):\n    raise ValueError()\n',
            'both arms': (
                'def f(x):\n    if x:\n        return 1\n'
                '    else:\n        raise ValueError()\n'
            ),
            'finally leaves': (
                'def f(x):\n    try:\n        one()\n    finally:\n        return 1\n'
            ),
            'every case': (
                'def f(x):\n    match x:\n        case 1:\n            return 1\n'
                '        case _:\n            return 2\n'
            ),
            'held return': 'def f(x):\n    with lock():\n        return 1\n',
            'class body raises': (
                'def f(x):\n    class A:\n        raise ValueError()\n'
            ),
            'endless loop leaves': 'def f(x):\n    while True:\n        return 1\n',
            'endless by not': 'def f(x):\n    while not False:\n        return 1\n',
            'endless by a full list': 'def f(x):\n    while [1]:\n        return 1\n',
            'endless by either part': (
                'def f(x):\n    while False or True:\n        return 1\n'
            ),
            'endless by both parts': (
                'def f(x):\n    while True and True:\n        return 1\n'
            ),
            'a turn over something written out': (
                'def f(x):\n    for part in (1,):\n        return 1\n'
            ),
            'a condition written out': 'def f(x):\n    if [1]:\n        return 1\n',
            'a guard that never holds': (
                'def f(x):\n    match x:\n        case _ if False:\n            pass\n'
                '        case _:\n            return 1\n'
            ),
            'a comparison written out': 'def f(x):\n    if 1 < 2:\n        return 1\n',
            'a comparison in a chain': (
                'def f(x):\n    if 1 < 2 < 3:\n        return 1\n'
            ),
            'a thing among others': 'def f(x):\n    if 1 in (1,):\n        return 1\n',
            'a thing outside others': (
                'def f(x):\n    if 1 not in (2,):\n        return 1\n'
            ),
            'one thing being another': (
                'def f(x):\n    if None is None:\n        return 1\n'
            ),
            'a chain failing before an unwritten side': (
                'def f(x, name):\n    if 1 < 0 < name:\n        return 1\n'
                '    return 2\n'
            ),
            'one thing not being another': (
                'def f(x):\n    if None is not True:\n        return 1\n'
            ),
            'a set written out': 'def f(x):\n    for part in {1}:\n        return 1\n',
            'both parts of an and gone over': (
                'def f(x):\n    for part in [1] and [2]:\n        return 1\n'
            ),
            'the part of an or that holds': (
                'def f(x):\n    for part in [1] or []:\n        return 1\n'
            ),
            'a guard written out': (
                'def f(x):\n    match x:\n        case _ if True:\n            return 1\n'
                '        case 1:\n            pass\n'
            ),
            'loop else leaves': (
                'def f(xs):\n    for x in xs:\n        pass\n    else:\n        return 1\n'
            ),
            'else leaves': (
                'def f(x):\n    try:\n        one()\n'
                '    except ValueError:\n        return 2\n    else:\n        return 3\n'
            ),
            'else skipped': (
                'def f(x):\n    try:\n        return 1\n'
                '    except ValueError:\n        return 2\n    else:\n        one()\n'
            ),
        }
        read = {
            label: check_wiki._CARRIES_ON not in check_wiki._statement_ways(self._last(source))
            for label, source in shapes.items()
        }

        assert read == dict.fromkeys(shapes, True)

    def test_every_shape_that_may_carry_on_is_read_as_one(self) -> None:
        shapes = {
            'call': 'def f(x):\n    one()\n',
            'one arm': 'def f(x):\n    if x:\n        return 1\n',
            'handler carries on': (
                'def f(x):\n    try:\n        raise ValueError()\n'
                '    except ValueError:\n        one()\n'
            ),
            'else carries on': (
                'def f(x):\n    try:\n        one()\n'
                '    except ValueError:\n        return 2\n    else:\n        two()\n'
            ),
            'uncovered match': (
                'def f(x):\n    match x:\n        case 1:\n            return 1\n'
            ),
            'held raise': 'def f(x):\n    with lock():\n        raise ValueError()\n',
            'class body carries on': 'def f(x):\n    class A:\n        field = 1\n',
            'loop may be empty': 'def f(xs):\n    for x in xs:\n        return 1\n',
            'loop that never runs': 'def f(x):\n    while False:\n        return 1\n',
            'loop over nothing': 'def f(x):\n    for part in []:\n        return 1\n',
            'two written the same way': (
                'def f(x):\n    if 257 is 257:\n        return 1\n'
            ),
            'two written the same way apart': (
                'def f(x):\n    if (1,) is not (1,):\n        return 1\n'
            ),
            'a chain whose last pair fails': (
                'def f(x):\n    while 1 < 2 < 0:\n        return 1\n'
            ),
            'a list unpacked into one': (
                'def f(xs):\n    while [*xs]:\n        return 1\n'
            ),
            'a mapping unpacked into one': (
                'def f(xs):\n    while {**xs}:\n        return 1\n'
            ),
            'nothing left of an and to go over': (
                'def f(x):\n    for part in [1] and ():\n        return 1\n'
            ),
            'the part of an and that fails': (
                'def f(x):\n    for part in () and [1]:\n        return 1\n'
            ),
            'a guard not written out': (
                'def f(x, cond):\n    match x:\n        case _ if cond:\n'
                '            return 1\n'
            ),
            'condition that never holds': (
                'def f(x):\n    while not True:\n        return 1\n'
            ),
            'loop over nothing written out': (
                "def f(x):\n    for part in ():\n        return 1\n"
            ),
            'break carries on past a loop': (
                'def f(xs):\n    while True:\n        if xs:\n            break\n'
                '        return 1\n'
            ),
            'loop else carries on': (
                'def f(xs):\n    for x in xs:\n        return 1\n    else:\n        one()\n'
            ),
        }
        read = {
            label: check_wiki._CARRIES_ON not in check_wiki._statement_ways(self._last(source))
            for label, source in shapes.items()
        }

        assert read == dict.fromkeys(shapes, False)


class TestOneFile:
    @_NEEDS_BASELINE
    def test_two_spellings_of_one_file_are_one(self) -> None:
        assert check_wiki._one_file('launcher.py', 'praxis/launcher.py')

    @_NEEDS_BASELINE
    def test_two_files_are_not_one(self) -> None:
        assert not check_wiki._one_file('praxis/trading.py', 'praxis/launcher.py')

    @_NEEDS_BASELINE
    def test_a_name_outside_the_tree_is_no_file(self) -> None:
        assert not check_wiki._one_file('nowhere.py', 'praxis/launcher.py')


class TestWhatCountsAsAProtocol:
    def test_a_plain_class_beside_a_protocol_import_is_no_protocol(self) -> None:
        source = 'from typing import Protocol\nclass A:\n' + _STUB
        assert not check_wiki._protocol_lines(ast.parse(source))


class TestReferenceLinks:
    def test_an_undefined_full_reference_is_refused(self) -> None:
        _targets, broken = check_wiki._link_targets('see [details][missing] for more\n')

        assert broken == ['refers to [missing], which is never defined']

    def test_an_undefined_collapsed_reference_is_refused(self) -> None:
        _targets, broken = check_wiki._link_targets('see [details][] for more\n')

        assert broken == ['refers to [details], which is never defined']

    def test_a_defined_full_reference_is_a_target(self) -> None:
        targets, broken = check_wiki._link_targets(
            'see [details][here]\n\n[here]: a-page.md\n',
        )

        assert broken == [] and 'a-page.md' in targets

    def test_a_web_address_is_no_broken_link(self, tmp_path: Path) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the venue](https://example.com/docs)\n')

        assert check_wiki._broken_links(page, page.read_text()) == []

    def test_a_missing_page_is_a_broken_link(self, tmp_path: Path) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the other](b.md)\n')

        assert check_wiki._broken_links(page, page.read_text()) == [
            'links to b.md, which does not exist',
        ]

    def test_a_link_to_a_drawing_is_left_alone(self, tmp_path: Path) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the drawing](shape.png)\n')
        (tmp_path / 'shape.png').write_bytes(b'\x89PNG\r\n\x1a\n\xff\xfe')

        assert check_wiki._broken_links(page, page.read_text()) == []

    def test_an_anchor_in_a_drawing_is_refused(self, tmp_path: Path) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the drawing](shape.png#here)\n')
        (tmp_path / 'shape.png').write_bytes(b'\x89PNG\r\n\x1a\n\xff\xfe')

        assert check_wiki._broken_links(page, page.read_text()) == [
            'links to shape.png#here, which is not written in text',
        ]

    def test_a_name_no_filesystem_takes_is_a_broken_link(self, tmp_path: Path) -> None:
        page = tmp_path / 'a.md'
        held = 'b' * 300 + '.md'
        page.write_text(f'see [the other]({held})\n')

        assert check_wiki._broken_links(page, page.read_text()) == [
            f'links to {held}, which does not exist',
        ]

    def test_a_name_holding_nothing_is_a_broken_link(self, tmp_path: Path) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the other](b\x00c.md)\n')

        assert check_wiki._broken_links(page, page.read_text()) == [
            'links to b\x00c.md, which does not exist',
        ]

    def test_a_name_whose_links_lead_back_is_a_broken_link(
        self, tmp_path: Path,
    ) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the other](b.md)\n')
        (tmp_path / 'b.md').symlink_to(tmp_path / 'c.md')
        (tmp_path / 'c.md').symlink_to(tmp_path / 'b.md')

        assert check_wiki._broken_links(page, page.read_text()) == [
            'links to b.md, which does not exist',
        ]

    def test_an_anchor_in_a_page_that_cannot_be_opened_is_refused(
        self, tmp_path: Path,
    ) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the other](b.md#here)\n')
        held = tmp_path / 'b.md'
        held.write_text('# B\n')
        held.chmod(0o000)

        try:
            assert check_wiki._broken_links(page, page.read_text()) == [
                'links to b.md#here, which is not written in text',
            ]
        finally:
            held.chmod(0o644)

    def test_an_anchor_in_a_folder_is_a_missing_heading(self, tmp_path: Path) -> None:
        page = tmp_path / 'a.md'
        page.write_text('see [the folder](atoms#here)\n')
        (tmp_path / 'atoms').mkdir()

        assert check_wiki._broken_links(page, page.read_text()) == [
            'links to atoms#here, whose heading does not exist',
        ]

    def test_a_defined_shortcut_reference_is_a_target(self) -> None:
        targets, broken = check_wiki._link_targets('see [here]\n\n[here]: a-page.md\n')

        assert broken == [] and targets.count('a-page.md') == 1


class TestBlockHeadings:
    def test_every_heading_is_counted_with_its_block(self) -> None:
        lines = [
            'try:',
            '    one()',
            'except ValueError:',
            '    two()',
            'else:',
            '    three()',
            'finally:',
            '    four()',
        ]
        read = {
            'except': check_wiki._heading(4, lines),
            'else': check_wiki._heading(6, lines),
            'finally': check_wiki._heading(8, lines),
        }

        assert read == {'except': 3, 'else': 5, 'finally': 7}

    def test_a_statement_above_a_block_is_no_heading(self) -> None:
        lines = ['if x:', '    one()', '    two()']

        assert check_wiki._heading(3, lines) == 3


class TestWhatAClassBodyLeaves:
    def test_a_raise_in_a_class_body_leaves_the_block(self) -> None:
        source = 'def f(x):\n    class A:\n        raise ValueError()\n'
        held = ast.parse(source).body[0]
        assert isinstance(held, ast.FunctionDef)

        assert check_wiki._can_leave(held.body)

    def test_a_raise_in_a_defined_function_leaves_nothing(self) -> None:
        source = 'def f(x):\n    def inner():\n        raise ValueError()\n'
        held = ast.parse(source).body[0]
        assert isinstance(held, ast.FunctionDef)

        assert not check_wiki._can_leave(held.body)


class TestCatchAllPatterns:
    @staticmethod
    def _match(source: str) -> ast.Match:
        held = ast.parse(source).body[0]
        assert isinstance(held, ast.Match)

        return held

    def test_every_catch_all_pattern_takes_every_value(self) -> None:
        shapes = {
            'bare capture': 'match x:\n    case other:\n        pass\n',
            'wildcard': 'match x:\n    case _:\n        pass\n',
            'bound capture': 'match x:\n    case value as bound:\n        pass\n',
            'bound wildcard in an or': 'match x:\n    case 1 | _ as name:\n        pass\n',
        }
        read = {
            label: check_wiki._covers_everything(self._match(source))
            for label, source in shapes.items()
        }

        assert read == dict.fromkeys(shapes, True)

    def test_a_narrowing_pattern_takes_only_its_own(self) -> None:
        shapes = {
            'bound kind': 'match x:\n    case int() as n:\n        pass\n',
            'values in an or': 'match x:\n    case 1 | 2:\n        pass\n',
            'a kind named': 'match x:\n    case object(real=1):\n        pass\n',
            'a kind asked for': 'match x:\n    case object():\n        pass\n',
            'a kind with a sub-pattern': (
                'match x:\n    case object(1):\n        pass\n'
            ),
        }
        read = {
            label: check_wiki._covers_everything(self._match(source))
            for label, source in shapes.items()
        }

        assert read == dict.fromkeys(shapes, False)


class TestWhatAClassBodyOverrides:
    def test_a_class_body_raise_in_a_finally_takes_the_branch_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "def f(xs):\n    for x in xs:\n        try:\n            if x:\n"
            "                act(x)\n                return 1\n            go(x)\n"
            "        finally:\n            class A:\n                raise ValueError()\n"
            "    done()\n"
        )
        spans = self._spans(source, tmp_path, monkeypatch)

        assert any(5 in first and 7 in second for first, second in spans)

    @staticmethod
    def _spans(
        source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> list[tuple[set[int], set[int]]]:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        return spans


class TestWhatABreakLeaves:
    @staticmethod
    def _body(source: str) -> list[ast.stmt]:
        held = ast.parse(source).body[0]
        assert isinstance(held, ast.FunctionDef)
        loop = held.body[0]
        assert isinstance(loop, (ast.For, ast.While))

        return loop.body

    def test_a_break_in_a_branch_leaves_the_loop(self) -> None:
        source = 'def f(xs, flag):\n    for x in xs:\n        if flag:\n            break\n'

        assert 'break' in check_wiki._block_ways(self._body(source))

    def test_a_break_a_finally_overrides_reaches_nothing(self) -> None:
        source = (
            'def f(x):\n    while True:\n        try:\n            mark()\n'
            '            break\n        finally:\n            return 1\n'
        )

        assert 'break' not in check_wiki._block_ways(self._body(source))

    def test_a_break_a_finally_leaving_two_ways_overrides_reaches_nothing(self) -> None:
        source = (
            'def f(cond):\n    while True:\n        try:\n            break\n'
            '        finally:\n            if cond:\n                return 1\n'
            '            else:\n                raise E()\n'
        )

        assert 'break' not in check_wiki._block_ways(self._body(source))

    def test_a_break_under_a_finally_that_carries_on_still_reaches(self) -> None:
        source = (
            'def f(x):\n    while True:\n        try:\n            break\n'
            '        finally:\n            shut()\n'
        )

        assert 'break' in check_wiki._block_ways(self._body(source))

    def test_a_break_under_a_finally_that_breaks_still_reaches(self) -> None:
        source = (
            'def f(x):\n    while True:\n        try:\n            mark()\n'
            '            break\n        finally:\n            break\n'
        )

        assert 'break' in check_wiki._block_ways(self._body(source))

    def test_a_break_in_a_nested_loop_leaves_that_loop(self) -> None:
        source = (
            'def f(xs, ys):\n    for x in xs:\n        for y in ys:\n            break\n'
        )

        assert 'break' not in check_wiki._block_ways(self._body(source))

    def test_a_break_in_a_nested_loops_else_reaches_past_its_body(self) -> None:
        source = (
            'def f(xs, ys, flag):\n    for x in xs:\n        for y in ys:\n'
            '            if flag:\n                break\n        else:\n'
            '            break\n'
        )

        assert 'break' in check_wiki._block_ways(self._body(source))

    def test_a_break_in_a_nested_loops_else_leaves_the_loop_outside(self) -> None:
        source = (
            'def f(xs, ys):\n    for x in xs:\n        for y in ys:\n            pass\n'
            '        else:\n            break\n'
        )

        assert 'break' in check_wiki._block_ways(self._body(source))


class TestTheGateWiring:
    CHECKS = (
        '_ledger_coverage',
        '_ledger_rows',
        '_counted_states',
        '_latest_release_counts',
        '_index_coverage',
        '_index_vocabulary',
        '_pinned_table',
        '_finding_citations',
    )

    def _stub(
        self, wiki: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'WIKI', wiki)
        monkeypatch.setattr(check_wiki, '_register_ids', lambda: set())

        for named in self.CHECKS:
            monkeypatch.setattr(check_wiki, named, lambda *_a: [])

    @pytest.mark.parametrize('named', CHECKS)
    def test_every_check_the_gate_runs_reaches_its_report(
        self,
        named: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        wiki = tmp_path / 'wiki'
        wiki.mkdir()
        self._stub(wiki, monkeypatch)
        monkeypatch.setattr(check_wiki, named, lambda *_a: [f'{named} said so'])

        assert check_wiki.main() == 1
        assert f'FAIL {named} said so' in capsys.readouterr().out

    def test_a_page_failure_reaches_the_report(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        wiki = tmp_path / 'wiki'
        wiki.mkdir()
        (wiki / 'one.md').write_text('# One\n', encoding='utf-8')
        self._stub(wiki, monkeypatch)
        monkeypatch.setattr(check_wiki, '_check_page', lambda *_a: ['a page said so'])

        assert check_wiki.main() == 1
        assert 'FAIL a page said so' in capsys.readouterr().out

    def test_a_clean_run_reports_what_it_read(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        wiki = tmp_path / 'wiki'
        wiki.mkdir()
        self._stub(wiki, monkeypatch)

        assert check_wiki.main() == 0
        assert 'ok: 0 page(s), 0 register row(s)' in capsys.readouterr().out


class TestWhatReachesAnAbsentNexus:
    def test_a_bare_nexus_name_reaches_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'NEXUS_ROOT', tmp_path / 'absent')

        assert check_wiki._reaches_absent_nexus('outcome_processor.py')

    def test_a_nexus_path_reaches_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'NEXUS_ROOT', tmp_path / 'absent')

        assert check_wiki._reaches_absent_nexus('nexus/core/outcome_processor.py')

    def test_a_praxis_path_ending_in_a_nexus_name_is_read_as_praxis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'NEXUS_ROOT', tmp_path / 'absent')

        assert not check_wiki._reaches_absent_nexus(
            'praxis/not_real/outcome_processor.py',
        )


class TestWhatOnePassCanReach:
    def test_no_settled_shape_offers_a_pair_one_pass_reaches(self) -> None:
        weighed, found = reachable_pairs(check_wiki, settled_shapes())

        assert found == []
        assert weighed >= _SETTLED_PAIRS

    def test_no_written_shape_offers_a_pair_one_pass_reaches(self) -> None:
        weighed, found = reachable_pairs(
            check_wiki, written_shapes(seed=0, runs=_SHAPES),
        )

        assert found == []
        assert weighed >= _PAIRS


class TestWhatADeepNestCosts:
    @staticmethod
    def _nested(level: int, indent: int) -> str:
        pad = ' ' * indent

        if level == 0:
            return f'{pad}pass\n'

        return (
            f'{pad}try:\n'
            + TestWhatADeepNestCosts._nested(level - 1, indent + 4)
            + f'{pad}except Exception:\n{pad}    pass\n'
        )

    def test_a_nest_of_tries_is_read_once_over(self, tmp_path: Path) -> None:
        sample = tmp_path / 'sample.py'
        sample.write_text(
            'def f(flag):\n    if flag:\n'
            + self._nested(22, 8)
            + '        return 1\n    after()\n',
        )
        script = (
            'import importlib.util\n'
            'import sys\n'
            'from pathlib import Path\n'
            f'spec = importlib.util.spec_from_file_location("gate", {str(_SCRIPT)!r})\n'
            'gate = importlib.util.module_from_spec(spec)\n'
            'sys.modules["gate"] = gate\n'
            'spec.loader.exec_module(gate)\n'
            f'held = Path({str(sample)!r})\n'
            'gate._source_text = lambda _p: held.read_text()\n'
            'print(len(gate._exclusive_spans(held)))\n'
        )
        held = subprocess.run(  # noqa: S603
            [sys.executable, '-c', script],
            capture_output=True, text=True, timeout=60, check=False,
        )

        assert held.returncode == 0
        assert held.stdout.strip() == '1'


class TestWhatAnAbsentTreeIsSaid:
    def test_an_absent_tree_is_noted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'NEXUS_ROOT', tmp_path / 'nowhere')

        assert check_wiki._unchecked_trees() == [
            f'the Nexus tree is not checked out at {tmp_path / "nowhere"}, '
            'so citations into it are not read',
        ]

    def test_a_tree_that_is_there_is_not_noted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, 'NEXUS_ROOT', tmp_path)

        assert check_wiki._unchecked_trees() == []


class TestWhatTheMetadataMustLookLike:
    _GOOD = (
        'row: P1-01\nbaseline: 49aa659\ncreated: 2099-01-01 00:00 UTC\n'
        'modified: 2099-01-01 00:00 UTC\nevidence:\n'
        '  - claim: "A thing is so"\n    source: "`order.py` 3"'
    )

    def test_the_shape_the_wiki_writes_passes(self) -> None:
        assert check_wiki._metadata_shape(self._GOOD) == []

    @pytest.mark.parametrize(
        ('meta', 'wanted'),
        [
            pytest.param(
                _GOOD.replace('evidence:', 'evidence: |'),
                'writes evidence as a value',
                id='evidence-as-a-string',
            ),
            pytest.param(
                _GOOD.replace('row: P1-01', 'arbitrary: P1-01'),
                'rather than row, baseline',
                id='row-under-another-key',
            ),
            pytest.param(
                _GOOD.replace(
                    'row: P1-01\nbaseline: 49aa659',
                    'baseline: 49aa659\nrow: P1-01',
                ),
                'in that order',
                id='keys-out-of-order',
            ),
            pytest.param(
                _GOOD + '\nextra: here',
                'in that order',
                id='a-stray-key',
            ),
            pytest.param(
                _GOOD.replace('row: P1-01', 'row:'),
                'writes row as nothing',
                id='an-empty-key',
            ),
            pytest.param(
                _GOOD.replace('  - claim: "A thing is so"\n', ''),
                'opens on something other than a claim',
                id='a-source-with-no-claim',
            ),
            pytest.param(
                _GOOD + '\n  - note: "something"',
                'neither a claim nor a source',
                id='a-stray-evidence-line',
            ),
        ],
    )
    def test_a_misshapen_block_is_refused(self, meta: str, wanted: str) -> None:
        held = check_wiki._metadata_shape(meta)

        assert any(wanted in note for note in held), held

    @pytest.mark.parametrize(
        ('meta', 'wanted'),
        [
            pytest.param(
                _GOOD.replace('"A thing is so"', '""'),
                'a claim that says nothing',
                id='an-empty-claim',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"A "quoted" thing"'),
                'neither a claim nor a source',
                id='a-claim-quoting-inside-itself',
            ),
            pytest.param(
                _GOOD + '\n    source: "`order.py` 2"',
                'carries 2 sources',
                id='two-sources-under-one-claim',
            ),
            pytest.param(
                _GOOD + '\n  - claim: "Another thing"',
                'carries 0 sources',
                id='a-claim-with-no-source',
            ),
            pytest.param(
                _GOOD.replace(
                    '  - claim: "A thing is so"\n    source: "`order.py` 3"',
                    '  - claim: "A thing is so | `order.py` 3"\n    source: ""',
                ),
                'holds the mark that parts a claim from its source',
                id='a-citation-smuggled-into-the-claim',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"\\q"'),
                'neither a claim nor a source',
                id='a-claim-with-a-bad-escape',
            ),
            pytest.param(
                _GOOD.replace('source: "`order.py` 3"', 'source: ""'),
                'carries a source that names nothing',
                id='a-source-naming-nothing',
            ),
            pytest.param(
                _GOOD.replace(
                    'source: "`order.py` 3"', 'source: "`order.py` 3, the "only" line"',
                ),
                'neither a claim nor a source',
                id='a-source-quoting-inside-itself',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"   "'),
                'a claim that says nothing',
                id='a-claim-of-spaces',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"\t"'),
                'a claim that says nothing',
                id='a-claim-of-one-tab',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"\u200b"'),
                'a claim that says nothing',
                id='a-claim-of-a-mark-that-shows-nothing',
            ),
            pytest.param(
                _GOOD.replace('source: "`order.py` 3"', 'source: "\u200b"'),
                'carries a source that names nothing',
                id='a-source-of-a-mark-that-shows-nothing',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"\u200e"'),
                'a claim that says nothing',
                id='a-claim-of-a-mark-outside-the-five',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"A thing\x00is so"'),
                'neither a claim nor a source',
                id='a-claim-holding-a-control-character',
            ),
            pytest.param(
                _GOOD.replace('source: "`order.py` 3"', 'source: "`order\x01.py` 3"'),
                'neither a claim nor a source',
                id='a-source-holding-a-control-character',
            ),
            pytest.param(
                'row: P1-01\nbaseline: 49aa659\ncreated: 2099-01-01 00:00 UTC\n'
                '\t- claim: "smuggled"\n\tsource: "`order.py` 3"\n'
                'modified: 2099-01-01 00:00 UTC\nevidence:',
                'holds a line before its evidence',
                id='a-pair-smuggled-above-evidence-with-tabs',
            ),
        ],
    )
    def test_a_claim_that_is_not_one_pair_is_refused(
        self, meta: str, wanted: str,
    ) -> None:
        held = check_wiki._metadata_shape(meta)

        assert any(wanted in note for note in held), held

    @pytest.mark.parametrize(
        ('meta', 'wanted'),
        [
            pytest.param(
                'row: P1-01\nbaseline: 49aa659\ncreated: 2099-01-01 00:00 UTC\n'
                '  - claim: "A thing is so"\n    source: "`order.py` 3"\n'
                'modified: 2099-01-01 00:00 UTC\nevidence:',
                'holds a line before its evidence',
                id='a-pair-smuggled-above-evidence',
            ),
            pytest.param(
                _GOOD.replace('row: P1-01', 'row: banana').replace(
                    '"A thing is so"', '"A thing is so, see P1-01"',
                ),
                'claims no register row',
                id='a-row-value-that-is-not-an-id',
            ),
            pytest.param(
                _GOOD.replace('baseline: 49aa659', 'baseline: nothing').replace(
                    '"A thing is so"', '"A thing is so at 49aa659"',
                ),
                'baseline nothing is not 49aa659',
                id='a-baseline-only-inside-a-claim',
            ),
            pytest.param(
                _GOOD.replace('baseline: 49aa659', 'xbaseline: 49aa659'),
                'names no baseline commit',
                id='a-baseline-under-a-longer-key',
            ),
            pytest.param(
                _GOOD.replace('row: P1-01', 'arow: P1-01'),
                'claims no register row',
                id='a-row-under-a-longer-key',
            ),
            pytest.param(
                _GOOD.replace('baseline: 49aa659', 'baseline:'),
                'writes baseline as nothing',
                id='a-baseline-written-as-nothing',
            ),
            pytest.param(
                _GOOD.replace('baseline: 49aa659', 'baseline: nothing'),
                'writes a baseline that is not a commit',
                id='a-baseline-that-is-not-a-commit',
            ),
            pytest.param(
                _GOOD.replace('baseline: 49aa659', 'baseline: 49aa659 extra'),
                'writes a baseline that is not a commit',
                id='a-baseline-with-more-after-it',
            ),
            pytest.param(
                _GOOD.replace('row: P1-01', 'row: banana'),
                'writes a row that is not a register row',
                id='a-row-that-is-not-a-row',
            ),
            pytest.param(
                _GOOD.replace('row: P1-01', 'row: P9-99'),
                'unknown register row P9-99',
                id='a-row-no-register-carries',
            ),
        ],
    )
    def test_a_key_read_from_elsewhere_is_refused(
        self, meta: str, wanted: str,
    ) -> None:
        held = check_wiki._check_metadata(meta, {'P1-01'})

        assert any(wanted in note for note in held), held

    def test_the_block_the_wiki_writes_passes_the_key_check(self) -> None:
        assert check_wiki._check_metadata(self._GOOD, {'P1-01'}) == []

    def test_a_misshapen_block_is_refused_by_the_page_check(self) -> None:
        held = check_wiki._check_metadata(
            self._GOOD.replace('evidence:', 'evidence: |'), {'P1-01'},
        )

        assert any('writes evidence as a value' in note for note in held)


class TestWhatManyReferencesCost:
    @staticmethod
    def _held(count: int, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        monkeypatch.setattr(
            check_wiki, '_source_text', lambda _p: 'def f():\n    work()\n',
        )
        monkeypatch.setattr(
            check_wiki, '_resolve_source', lambda _k: Path('order.py'),
        )
        row = 'a claim | `order.py` ' + ', '.join(['2'] * count)
        found: list[str] = check_wiki._row_citations(row, check_wiki._SourceFacts())

        return found

    def test_a_row_past_the_bound_says_so(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(check_wiki._REFERENCES_AT_MOST + 1, monkeypatch)

        assert any('a row is weighed in pairs over' in note for note in held)

    def test_a_row_at_the_bound_is_weighed(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assert self._held(check_wiki._REFERENCES_AT_MOST, monkeypatch) == []

    def test_a_row_of_many_references_is_answered_at_once(self) -> None:
        script = (
            'import importlib.util\n'
            'import sys\n'
            'from pathlib import Path\n'
            f'spec = importlib.util.spec_from_file_location("gate", {str(_SCRIPT)!r})\n'
            'gate = importlib.util.module_from_spec(spec)\n'
            'sys.modules["gate"] = gate\n'
            'spec.loader.exec_module(gate)\n'
            'gate._source_text = lambda _p: "def f():\\n    work()\\n"\n'
            'gate._resolve_source = lambda _k: Path("order.py")\n'
            'row = "a claim | `order.py` " + ", ".join(["2"] * 20000)\n'
            'print(len(gate._row_citations(row, gate._SourceFacts())))\n'
        )
        held = subprocess.run(  # noqa: S603
            [sys.executable, '-c', script],
            capture_output=True, text=True, timeout=60, check=False,
        )

        assert held.returncode == 0
        assert held.stdout.strip() == '1'


class TestEveryRuleThePageWalkRuns:
    _GOOD = (
        '---\nrow: P1-01\nbaseline: 49aa659\n'
        'created: 2099-01-01 00:00 UTC\nmodified: 2099-01-01 00:00 UTC\n'
        'evidence:\n  - claim: "A thing is so"\n'
        '    source: "`order.py` 3"\n---\n'
        '# One\n\nA thing that is so.\n'
    )

    @staticmethod
    def _walked(
        tmp_path: Path, text: str, monkeypatch: pytest.MonkeyPatch,
        named: str = 'one.md', committed: str | None = None,
    ) -> list[str]:
        atoms = tmp_path / 'atoms'
        atoms.mkdir(exist_ok=True)
        page = atoms / named
        page.write_text(text, encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'WIKI', tmp_path)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: 'a\nb\nwork()\n')
        monkeypatch.setattr(
            check_wiki, '_resolve_source', lambda _k: Path('order.py'),
        )
        monkeypatch.setattr(
            check_wiki, '_last_commit_date', lambda _p: committed,
        )
        monkeypatch.setattr(check_wiki, '_edited_since', lambda _p: None)
        held: list[str] = check_wiki._check_page(
            page, {'P1-01'}, check_wiki._SourceFacts(),
        )

        return held

    @pytest.mark.parametrize(
        ('name', 'broken', 'wanted'),
        [
            pytest.param(
                'one.md',
                _GOOD.replace('2099-01-01', '2000-01-01'),
                'older than its last commit',
                id='stale-stamp',
            ),
            pytest.param(
                'one.md',
                _GOOD.replace(
                    'A thing that is so.',
                    'A thing that is so, said [elsewhere](nowhere-at-all.md).',
                ),
                'which does not exist',
                id='broken-link',
            ),
        ],
    )
    def test_a_rule_run_for_every_page_is_run(
        self, name: str, broken: str, wanted: str, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._walked(
            tmp_path, broken, monkeypatch, named=name, committed='2026-01-01',
        )

        assert any(wanted in note for note in held), held

    def test_a_page_outside_the_atoms_is_still_walked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, '_last_commit_date', lambda _p: '2026-01-01')
        page = tmp_path / 'README.md'
        page.write_text(
            '# Index\n\nA list, said [elsewhere](nowhere-at-all.md).\n\n'
            '---\n\nCreated 2099-01-01 00:00 UTC · Last modified 2099-01-01 00:00 UTC\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', tmp_path)
        held = check_wiki._check_page(page, {'P1-01'}, check_wiki._SourceFacts())

        assert any('which does not exist' in note for note in held), held

    def test_a_page_breaking_no_rule_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assert self._walked(tmp_path, self._GOOD, monkeypatch) == []

    @pytest.mark.parametrize(
        ('broken', 'wanted'),
        [
            pytest.param(
                '# One\n\nA thing that is so.\n',
                'has no metadata block',
                id='no-metadata',
            ),
            pytest.param(
                _GOOD.replace(
                    'evidence:\n  - claim: "A thing is so"\n    source: "`order.py` 3"\n',
                    'evidence: []\n',
                ),
                'carries no evidence',
                id='no-evidence',
            ),
            pytest.param(
                _GOOD.replace('A thing that is so.', 'This is about a thing.'),
                'lead',
                id='voice',
            ),
            pytest.param(
                _GOOD.replace('    source: "`order.py` 3"\n', '    source: ""\n'),
                'claim',
                id='uncited-claim',
            ),
            pytest.param(
                _GOOD.replace('`order.py` 3', '`order.py`'),
                'cites no line of it',
                id='unlined-source',
            ),
            pytest.param(
                _GOOD.replace(
                    'A thing that is so.',
                    'A thing that is so, not a thing that is not.',
                ),
                'negation',
                id='negative-definition',
            ),
            pytest.param(
                _GOOD.replace(
                    'A thing that is so.',
                    'A thing that is so, read from the order book.',
                ),
                'order book',
                id='owned-term-unlinked',
            ),
            pytest.param(
                _GOOD.replace(
                    'A thing that is so.\n',
                    'A thing that is so.\n## Two\n\nAnother thing so.\n',
                ),
                'heading',
                id='unspaced-heading',
            ),
            pytest.param(
                _GOOD.replace(
                    'A thing that is so.',
                    'A thing that is so. ' + ' '.join(['word'] * 301),
                ),
                'exceeds the 300 cap',
                id='over-the-cap',
            ),
            pytest.param(
                _GOOD.replace('row: P1-01', 'row: P9-99'),
                'P9-99',
                id='unknown-row',
            ),
            pytest.param(
                _GOOD.replace('`order.py` 3', '`order.py` 99'),
                'past end of file',
                id='citation-past-the-end',
            ),
        ],
    )
    def test_every_rule_is_run_by_the_page_walk(
        self, broken: str, wanted: str, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._walked(tmp_path, broken, monkeypatch)

        assert any(wanted in note for note in held), held


class TestWhatARunWithoutNexusSays:
    @_NEEDS_BASELINE
    def test_the_gate_writes_the_note(self, tmp_path: Path) -> None:
        script = (
            'import importlib.util\n'
            'import sys\n'
            'from pathlib import Path\n'
            f'spec = importlib.util.spec_from_file_location("gate", {str(_SCRIPT)!r})\n'
            'gate = importlib.util.module_from_spec(spec)\n'
            'sys.modules["gate"] = gate\n'
            'spec.loader.exec_module(gate)\n'
            f'gate.NEXUS_ROOT = Path({str(tmp_path / "nowhere")!r})\n'
            'sys.exit(gate.main())\n'
        )
        held = subprocess.run(  # noqa: S603
            [sys.executable, '-c', script],
            capture_output=True, text=True, timeout=600, check=False,
            cwd=_SCRIPT.parent.parent,
        )

        assert held.returncode == 0
        assert 'note: the Nexus tree is not checked out' in held.stdout


class TestWhatAnUncommittedEditNeeds:
    @staticmethod
    def _committed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stamp: str,
    ) -> Path:
        atoms = tmp_path / 'docs' / 'wiki' / 'atoms'
        atoms.mkdir(parents=True)
        page = atoms / 'one.md'
        page.write_text(
            '---\ncreated: 2099-01-01 00:00 UTC\n'
            f'modified: {stamp}\n---\n# One\n\nAs committed.\n',
            encoding='utf-8',
        )

        for held in (
            ['init', '-q'],
            ['add', 'docs'],
            [
                '-c', 'user.email=one@example.com', '-c', 'user.name=One',
                'commit', '-qm', 'one',
            ],
        ):
            subprocess.run(  # noqa: S603
                [check_wiki.GIT, *held], cwd=tmp_path, check=True,
                capture_output=True,
            )

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(check_wiki, 'WIKI', Path('docs/wiki'))
        check_wiki._uncommitted_pages.cache_clear()

        return page

    @staticmethod
    def _complaints(page: Path) -> list[str]:
        rel = Path('docs/wiki/atoms/one.md')
        text = page.read_text(encoding='utf-8')
        meta, _ = check_wiki._split_front_matter(text)
        held: list[str] = check_wiki._check_stamps(rel, text, meta)

        return held

    @_NEEDS_BASELINE
    def test_an_edit_left_unstamped_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = self._committed(tmp_path, monkeypatch, '2099-01-01 00:00 UTC')
        page.write_text(
            '---\ncreated: 2099-01-01 00:00 UTC\n'
            'modified: 2099-01-01 00:00 UTC\n---\n# One\n\nEdited.\n',
            encoding='utf-8',
        )
        check_wiki._uncommitted_pages.cache_clear()

        assert any(
            'holds an edit that is not yet committed' in note
            for note in self._complaints(page)
        )

    @_NEEDS_BASELINE
    def test_an_edit_stamped_later_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = self._committed(tmp_path, monkeypatch, '2099-01-01 00:00 UTC')
        page.write_text(
            '---\ncreated: 2099-01-01 00:00 UTC\n'
            'modified: 2099-01-02 00:00 UTC\n---\n# One\n\nEdited.\n',
            encoding='utf-8',
        )
        check_wiki._uncommitted_pages.cache_clear()

        assert self._complaints(page) == []

    @_NEEDS_BASELINE
    def test_a_page_as_committed_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = self._committed(tmp_path, monkeypatch, '2099-01-01 00:00 UTC')

        assert self._complaints(page) == []


class TestWhatAnUnassignedRowCosts:
    def test_a_row_of_brackets_is_answered_at_once(self) -> None:
        text = '| ' + '()' * 20000 + ' | why | unassigned |\n'
        script = (
            'import importlib.util\n'
            'import sys\n'
            f'spec = importlib.util.spec_from_file_location("gate", {str(_SCRIPT)!r})\n'
            'gate = importlib.util.module_from_spec(spec)\n'
            'sys.modules["gate"] = gate\n'
            'spec.loader.exec_module(gate)\n'
            f'print(sorted(gate._unresolved_questions({text!r})))\n'
        )
        held = subprocess.run(  # noqa: S603
            [sys.executable, '-c', script],
            capture_output=True, text=True, timeout=60, check=False,
        )

        assert held.returncode == 0
        assert held.stdout.strip() == '[]'

    def test_a_question_in_a_bracketed_row_is_still_found(self) -> None:
        text = '| H-01 | [a page](atoms/one.md) raises U-09 | why | unassigned |'

        assert check_wiki._unresolved_questions(text) == {'U-09'}

    def test_an_answered_row_carries_no_question(self) -> None:
        text = '| H-01 | [a page](atoms/one.md) raises U-09 | why | P1-01 |'

        assert check_wiki._unresolved_questions(text) == set()


class TestWhatARefusalMustCite:
    @staticmethod
    def _held(source: str, row: str, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        monkeypatch.setattr(
            check_wiki, '_resolve_source', lambda _k: Path('order.py'),
        )

        held: list[str] = check_wiki._row_citations(row, check_wiki._SourceFacts())

        return held

    def test_a_refusal_stopping_before_its_raise_is_refused(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(qty):\n\n    if qty < 0:\n        msg = "no"\n'
            '        raise ValueError(msg)\n'
        )
        held = self._held(source, 'An amount below nought is refused | `order.py` 3-4', monkeypatch)

        assert any('stopping on the line before the raise at 5' in note for note in held)

    def test_a_refusal_citing_its_raise_stands(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(qty):\n\n    if qty < 0:\n        msg = "no"\n'
            '        raise ValueError(msg)\n'
        )
        held = self._held(source, 'An amount below nought is refused | `order.py` 3-5', monkeypatch)

        assert held == []

    def test_a_claim_of_no_refusal_stands(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(qty):\n\n    if qty < 0:\n        msg = "no"\n'
            '        raise ValueError(msg)\n'
        )
        held = self._held(source, 'The message names the amount | `order.py` 3-4', monkeypatch)

        assert held == []

    def test_a_range_ending_on_a_raise_stands(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(qty):\n\n    try:\n        work()\n    except KeyError:\n'
            '        if qty < 0:\n            raise ValueError from None\n'
            '        raise\n'
        )
        held = self._held(source, 'An amount below nought is refused | `order.py` 6-7', monkeypatch)

        assert held == []

    def test_a_raise_cited_elsewhere_in_the_row_stands(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(qty):\n\n    if qty < 0:\n        msg = "no"\n'
            '        raise ValueError(msg)\n'
        )
        held = self._held(
            source,
            'An amount below nought is refused | `order.py` 3-4, raised at 5',
            monkeypatch,
        )

        assert held == []


class TestLinkLabels:
    def test_a_label_reads_past_case_and_spacing(self) -> None:
        assert check_wiki._label('  Some   Ref ') == 'some ref'

    def test_two_labels_are_not_one(self) -> None:
        assert check_wiki._label('here') != check_wiki._label('there')


class TestWhenAPageWasCommitted:
    @_NEEDS_BASELINE
    def test_a_committed_file_has_a_date(self) -> None:
        held = check_wiki._last_commit_date(check_wiki.CHANGELOG)

        assert held is not None
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', held)

    def test_a_file_outside_the_tree_has_none(self, tmp_path: Path) -> None:
        held = tmp_path / 'nowhere.md'
        held.write_text('# Nowhere\n', encoding='utf-8')

        assert check_wiki._last_commit_date(held) is None


class TestWhatARaiseWorksOut:
    @staticmethod
    def _raised(source: str) -> ast.Raise:
        held = ast.parse(source).body[0]
        assert isinstance(held, ast.Raise)

        return held

    def test_every_raise_that_works_nothing_out_is_read_as_one(self) -> None:
        shapes = {
            'nothing at all': 'raise\n',
            'an error the language carries': 'raise ValueError\n',
            'one called with nothing': 'raise ValueError()\n',
            'one called with a value written out': "raise ValueError('no')\n",
            'one with nothing named as its cause': 'raise ValueError() from None\n',
        }
        quiet = [
            label for label, source in shapes.items()
            if check_wiki._raised_quietly(self._raised(source))
        ]

        assert quiet == list(shapes)

    def test_every_raise_that_works_something_out_is_read_as_one(self) -> None:
        shapes = {
            'an error the project names': 'raise Failure()\n',
            'one named through something else': 'raise errors.Failure()\n',
            'one called with a name': 'raise ValueError(text)\n',
            'one called with a word named': 'raise ValueError(part=text)\n',
            'one with a cause worked out': 'raise ValueError() from fail()\n',
            'one with a cause that is no error': 'raise ValueError() from 1\n',
            'nothing at all taken': 'raise None\n',
            'an error asking for an exact number': 'raise UnicodeDecodeError()\n',
            'a group of errors': 'raise ExceptionGroup\n',
            'an error asking a shape of its values': "raise SyntaxError('bad', 1)\n",
            'an error the system chooses': "raise OSError(1, 'no')\n",
            'one of that family refusing a value': (
                'raise BlockingIOError(None, None, 1.2)\n'
            ),
            'one called with a word named and a value written out': (
                'raise ValueError(bad=1)\n'
            ),
        }
        noisy = [
            label for label, source in shapes.items()
            if not check_wiki._raised_quietly(self._raised(source))
        ]

        assert noisy == list(shapes)


class TestWhatACitationMayName:
    def test_a_reference_of_any_length_is_read(self) -> None:
        held = [
            match.group(0)
            for match in check_wiki.LINE_REF.finditer('`events.py` 585-595, 10000000')
        ]

        assert held == ['585-595', '10000000']

    @_NEEDS_BASELINE
    def test_a_number_too_long_to_read_is_refused_as_a_citation(self) -> None:
        held = '9' * 4301
        notes = check_wiki._row_citations(
            f'a claim | `praxis/trading.py` {held}', check_wiki._SourceFacts(),
        )

        assert len(notes) == 1
        assert 'past end of file' in notes[0]

    @_NEEDS_BASELINE
    def test_a_number_too_long_to_read_is_refused_in_a_range(self) -> None:
        held = '9' * 4301
        notes = check_wiki._docstring_citations(
            f'|a claim | `praxis/trading.py` 1-{held}|', check_wiki._SourceFacts(),
        )

        assert len(notes) == 1
        assert 'past end of file' in notes[0]

    def test_a_number_too_long_to_read_runs_past_every_file(self) -> None:
        held = check_wiki._as_line('9' * 4301)

        assert held == check_wiki._PAST_EVERY_FILE

    def test_a_count_too_long_to_read_reaches_no_count(self) -> None:
        assert check_wiki._as_count('9,' + '9' * 4301) == check_wiki._PAST_EVERY_FILE

    def test_a_count_of_a_readable_length_is_read(self) -> None:
        assert check_wiki._as_count('2,204') == 2204

    def test_a_span_of_rows_beyond_counting_names_nothing(self) -> None:
        assert check_wiki._named_between('P4', '1', '5000') == set()

    def test_a_span_of_rows_running_backwards_names_nothing(self) -> None:
        assert check_wiki._named_between('P4', '5', '3') == set()

    def test_a_span_of_rows_names_each_one(self) -> None:
        assert check_wiki._named_between('P4', '1', '3') == {'P4-01', 'P4-02', 'P4-03'}

    def test_a_number_of_a_readable_length_is_read(self) -> None:
        assert check_wiki._as_line('585') == 585

    def test_a_count_with_no_number_is_no_count(self) -> None:
        assert not check_wiki.EVIDENCE_COUNT_RE.search(
            ', line references across , claims',
        )
        assert not check_wiki.FINDING_COUNT_RE.search('Record , findings')
        assert not check_wiki.LINE_COUNT_RE.search('`order.py` is , lines')

    def test_a_count_with_a_number_is_one(self) -> None:
        held = check_wiki.EVIDENCE_COUNT_RE.search(
            '2,204 line references across 1,203 claims',
        )

        assert held is not None
        assert held.groups() == ('2,204', '1,203')


class TestWhatTheGateLeavesUnreached:

    @staticmethod
    def _written(tree: ast.Module) -> dict[str, int]:
        held: dict[str, int] = {}

        for node in tree.body:

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                held[node.name] = node.lineno

            elif isinstance(node, ast.Assign):
                held.update({
                    target.id: node.lineno
                    for target in node.targets
                    if isinstance(target, ast.Name)
                })

            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                held[node.target.id] = node.lineno

        return held

    @staticmethod
    def _read(tree: ast.Module) -> set[str]:
        return {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }

    def test_every_name_the_gate_writes_is_read_in_it(self) -> None:
        tree = ast.parse(_SCRIPT.read_text(encoding='utf-8'))
        read = self._read(tree)
        unreached = {
            name: line for name, line in self._written(tree).items()
            if not name.startswith('__') and name not in read
        }

        assert unreached == {}, unreached

    def test_a_name_nothing_reads_is_found(self) -> None:
        tree = ast.parse(
            'KEPT = 1\n\n\ndef _held() -> int:\n    return KEPT\n\n\n'
            'def _stranded() -> int:\n    return 2\n',
        )
        read = self._read(tree)
        unreached = [name for name in self._written(tree) if name not in read]

        assert '_stranded' in unreached
        assert 'KEPT' not in unreached
