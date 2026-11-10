'''
Tests for scripts.check_wiki.

Each check in the wiki gate was added after a defect of its kind reached a
finished article. These lock every one of them by presenting the defect and
asserting the refusal, so a check that stops refusing fails here.
'''

from __future__ import annotations

import ast
import datetime
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
            pytest.param(
                'from typing import Protocol\nfrom typing import Protocol as Protocol\n'
                'class A(Protocol):\n' + _STUB,
                id='imported-twice-from-typing',
            ),
            pytest.param(
                'from typing import Protocol\nProtocol: type\n'
                'class A(Protocol):\n' + _STUB,
                id='annotated-with-no-value',
            ),
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
                'from typing import Protocol as P, Any as P\nclass A(P):\n' + _STUB,
                id='two-aliases-of-one-name',
            ),
            pytest.param(
                'from typing import Protocol\nProtocol: type\n'
                'from abc import ABC as Protocol\nclass A(Protocol):\n' + _STUB,
                id='annotated-then-replaced',
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
                'from typing import Protocol\ntry:\n    pass\n'
                'except Exception as Protocol:\n    pass\n'
                'class A(Protocol):\n' + _STUB,
                id='an-except-target',
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


class TestObligedPurpose:
    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param(
                'A send raising anything is passed over, because a venue that '
                'cannot be reached must not leave the host unable to stop.',
                id='venue-the-code-never-identifies',
            ),
            pytest.param(
                'The five are skipped so that an action cutting exposure '
                'should not be stopped.',
                id='purpose-the-bypass-never-tests',
            ),
            pytest.param(
                'skipped so that a well-placed order should not be stopped',
                id='a-hyphenated-word-inside-the-window',
            ),
            pytest.param(
                'It is refused because the host must agree.',
                id='one-subject',
            ),
            pytest.param(
                'It is held lest the order should fill.',
                id='lest-and-should',
            ),
            pytest.param(
                'It is refused on the grounds that the row ought to name a '
                'version.',
                id='on-the-grounds-that-and-ought',
            ),
            pytest.param(
                'It waits because the account needs to settle first.',
                id='needs-to',
            ),
            pytest.param(
                'It waits because the account has to settle first.',
                id='has-to',
            ),
            pytest.param(
                'It waits because the two have to agree first.',
                id='have-to',
            ),
            pytest.param(
                'It is held because the order cannot be allowed to fill.',
                id='cannot-be-allowed',
            ),
            pytest.param(
                'It is refused so  that the host must agree.',
                id='a-connective-spaced-wide',
            ),
            pytest.param(
                'It waits because the account has  to settle first.',
                id='an-obligation-spaced-wide',
            ),
            pytest.param(
                'It is refused because ' + 'x' * 78 + ' must agree.',
                id='an-obligation-at-the-window-edge',
            ),
        ],
    )
    def test_a_purpose_carrying_an_obligation_is_refused(
        self, sentence: str,
    ) -> None:
        assert check_wiki._obliged_purpose(sentence)

    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param(
                'An order the venue rejects is recorded as a success, '
                'because the venue answered.',
                id='cause-with-no-obligation',
            ),
            pytest.param(
                'A refusal must name the stage that made it, a reason code '
                'and a message.',
                id='obligation-with-no-purpose',
            ),
            pytest.param(
                'The sign is reversed first, so that either way a worse '
                'price gives a bigger number.',
                id='purpose-reporting-arithmetic',
            ),
            pytest.param(
                'Nothing sweeps them because time passed.',
                id='bare-cause',
            ),
        ],
    )
    def test_reporting_a_cause_or_a_requirement_passes(
        self, sentence: str,
    ) -> None:
        assert not check_wiki._obliged_purpose(sentence)

    def test_a_heading_is_not_read_for_it(self) -> None:
        heading = '## Passed over because a venue must answer'
        assert check_wiki._obliged_purpose(heading.lstrip('# '))
        assert not check_wiki._obliged_purpose(heading)

    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param(
                'It returns because the venue sent a response that the caller '
                'must acknowledge.',
                id='a-that-clause',
            ),
            pytest.param(
                'A fill is kept because the size the position must release '
                'has moved.',
                id='a-clause-with-no-marker',
            ),
        ],
    )
    def test_an_obligation_inside_a_noun_phrase_is_read(
        self, sentence: str,
    ) -> None:
        assert check_wiki._obliged_purpose(sentence), (
            'a known false positive: the defect this check exists for carries '
            'a relative clause of its own, so one cannot open an exemption'
        )

    def test_an_obligation_on_a_which_clause_is_not(self) -> None:
        said = (
            'It returns because the venue answered which the caller must '
            'acknowledge.'
        )
        assert not check_wiki._obliged_purpose(said)

    def test_an_emphasised_connective_is_still_read(self) -> None:
        said = 'passed over *because* a venue that cannot be reached must not stop'
        assert check_wiki._obliged_purpose(said)

    _STOPPERS = (
        'and', 'but', 'yet', 'or', 'although', 'though', 'while', 'whereas',
        'before', 'after', 'when', 'whenever', 'unless', 'until', 'if',
        'once', 'where', 'whether', 'which', 'who', 'whom', 'whose',
    )

    def test_the_stopper_list_is_the_one_written_here(self) -> None:
        assert tuple(check_wiki._OPENS_A_CLAUSE.split('|')) == self._STOPPERS

    @pytest.mark.parametrize('stopper', _STOPPERS)
    def test_every_clause_opener_stops_the_window(self, stopper: str) -> None:
        said = f'It returns because the venue answered {stopper} it must stop.'
        assert not check_wiki._obliged_purpose(said)

    @pytest.mark.parametrize(
        'obligation',
        ['must', 'should', 'ought', 'need to', 'needs to', 'has to',
         'have to', 'cannot be allowed'],
    )
    def test_every_obligation_is_read(self, obligation: str) -> None:
        assert check_wiki._obliged_purpose(
            f'It is refused because the host {obligation} agree.',
        )

    @pytest.mark.parametrize(
        'reason', ['because', 'so that', 'lest', 'on the grounds that'],
    )
    def test_every_reason_is_read(self, reason: str) -> None:
        assert check_wiki._obliged_purpose(
            f'It is refused {reason} the host must agree.',
        )

    def test_a_reason_opening_a_sentence_is_read(self) -> None:
        assert check_wiki._obliged_purpose('Because the host must agree.')

    def test_a_hyphenated_word_holding_a_modal_passes(self) -> None:
        said = 'It is held because the must-have field is missing.'
        assert not check_wiki._obliged_purpose(said)

    @pytest.mark.parametrize('rule', ['***', '---', '___', '* * *'])
    def test_a_break_between_them_is_not_read_as_one(self, rule: str) -> None:
        broken = (
            f'It returned because the venue answered\n{rule}\n'
            'A refusal must name its stage.'
        )
        assert not check_wiki._obliged_purpose(broken)

    def test_prose_and_a_quote_after_it_are_not_read_as_one(self) -> None:
        joined = 'It returns because the flag is set\n> The caller must retry.'
        assert not check_wiki._obliged_purpose(joined)

    def test_two_quoted_paragraphs_are_not_read_as_one(self) -> None:
        quoted = (
            '> It returns because the venue answered\n>\n'
            '> A refusal must name its stage'
        )
        assert not check_wiki._obliged_purpose(quoted)

    def test_a_bracketed_requirement_passes(self) -> None:
        said = 'It returns because the venue answered [the caller must retry].'
        assert not check_wiki._obliged_purpose(said)

    def test_a_wrapped_purpose_is_still_read(self) -> None:
        assert check_wiki._obliged_purpose('passed over because a venue\nmust answer')

    @pytest.mark.parametrize('mark', ['*', '+', '> *', '> +'])
    def test_two_list_items_are_not_read_as_one(self, mark: str) -> None:
        listed = (
            f'{mark} It returns because the venue answered\n'
            f'{mark} A refusal must name its stage'
        )
        assert not check_wiki._obliged_purpose(listed)

    def test_a_wrapped_list_item_is_still_one(self) -> None:
        listed = (
            '- It is refused because a venue that cannot be reached\n'
            '  must not stop the host'
        )
        assert check_wiki._obliged_purpose(listed)

    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param(
                'It returned because the venue answered. A refusal must name '
                'its stage.',
                id='split-by-a-full-stop',
            ),
            pytest.param(
                'It returned because the venue answered! A refusal must name '
                'its stage.',
                id='split-by-an-exclamation',
            ),
            pytest.param(
                'Did it return because the venue answered? A refusal must '
                'name its stage.',
                id='split-by-a-question',
            ),
            pytest.param(
                'It returned because the venue answered; a refusal must name '
                'its stage.',
                id='split-by-a-semicolon',
            ),
            pytest.param(
                'It returns because the venue answered (the caller must still '
                'retry).',
                id='set-apart-in-brackets',
            ),
            pytest.param(
                'It returns because the venue answered although the caller '
                'must retry.',
                id='a-clause-opened-by-although',
            ),
            pytest.param(
                'It returns because the venue answered while the caller must '
                'retry.',
                id='a-clause-opened-by-while',
            ),
            pytest.param(
                'It returns because the venue answered before the caller has '
                'to retry.',
                id='a-clause-opened-by-before',
            ),
            pytest.param(
                'It returns because the venue answered when the caller must '
                'retry.',
                id='a-clause-opened-by-when',
            ),
            pytest.param(
                'It returns because the venue answered unless the caller must '
                'retry.',
                id='a-clause-opened-by-unless',
            ),
            pytest.param(
                'It is refused because ' + 'x' * 79 + ' must agree.',
                id='an-obligation-one-past-the-window',
            ),
            pytest.param(
                'It returned because the venue answered, and a refusal must '
                'name its stage.',
                id='split-by-a-comma',
            ),
            pytest.param(
                'It returned because the venue answered \u2014 a refusal must '
                'name its stage.',
                id='split-by-an-em-dash',
            ),
            pytest.param(
                'It returned because the venue answered \u2013 a refusal must '
                'name its stage.',
                id='split-by-an-en-dash',
            ),
            pytest.param(
                'It returned because the venue answered -- a refusal must '
                'name its stage.',
                id='split-by-a-double-hyphen',
            ),
            pytest.param(
                'It returned because the venue answered - a refusal must '
                'name its stage.',
                id='split-by-a-hyphen',
            ),
            pytest.param(
                'Nothing has moved since Monday and the book must be fetched '
                'again.',
                id='a-temporal-since',
            ),
            pytest.param(
                'Since Monday the book has to be fetched again.',
                id='a-temporal-since-alone',
            ),
            pytest.param(
                'It returns because the venue answered and the caller must '
                'retry.',
                id='a-coordinated-clause',
            ),
            pytest.param(
                'It returns because the venue answered but the caller must '
                'retry.',
                id='a-clause-coordinated-by-but',
            ),
            pytest.param(
                'It is refused because the host and venue must agree.',
                id='a-compound-subject-goes-unread',
            ),
        ],
    )
    def test_a_cause_and_a_separate_requirement_pass(
        self, sentence: str,
    ) -> None:
        assert not check_wiki._obliged_purpose(sentence)


_REGISTER_RULE = re.compile(
    r'carrying an obligation:(.*?)\.\s', re.DOTALL,
)

_ITALIC = re.compile(r'\*([a-z\s]+?)\*')


def _register_terms() -> tuple[tuple[str, ...], tuple[str, ...]]:
    '''Return the causes and the obligations the register names.

    Reads the whole sentence rather than one run of italics in it, a
    word appended after the last `or` having gone unread.

    Returns:
        tuple[tuple[str, ...], tuple[str, ...]]: The causes, then the
            obligations.
    '''

    said = _REGISTER_RULE.search(
        (check_wiki.WIKI / 'register.md').read_text(encoding='utf-8'),
    )

    if said is None:
        return (), ()

    before, _, after = said.group(1).partition('and then')

    return tuple(
        tuple(' '.join(word.split()) for word in _ITALIC.findall(half))
        for half in (before, after)
    )


_UNREADABLE = frozenset('.+*{}[]^$')


def _phrases(source: str) -> tuple[str, ...]:
    r"""Return every phrase an alternation can match, spelt out.

    Reads the alternation, the `(?:a|b)` groups inside it, a `?` on
    either, and `\s+` as one space. Anything else stops it: `\s*`
    was read as one space and so answered that a pattern accepting
    `needto` named the same words the register did.

    Args:
        source (str): The inside of an alternation group.

    Returns:
        tuple[str, ...]: One phrase per thing it matches.
    """

    def run(place: int) -> tuple[list[str], int]:
        grown = ['']

        while place < len(source) and source[place] not in '|)':
            mark = source[place]

            if mark == '(':
                if source[place:place + 3] != '(?:':
                    msg = f'unreadable group at {place} in {source!r}'
                    raise ValueError(msg)

                unit, place = branches(place + 3)
                place += 1

            elif mark == '\\':
                if source[place:place + 3] != '\\s+':
                    msg = f'unreadable escape at {place} in {source!r}'
                    raise ValueError(msg)

                place += 3
                unit = [' ']

            elif mark in _UNREADABLE:
                msg = f'unreadable mark {mark!r} at {place} in {source!r}'
                raise ValueError(msg)

            else:
                place += 1
                unit = [mark]

            if source[place:place + 1] == '?':
                place += 1
                unit = [*unit, '']

            grown = [held + one for held in grown for one in unit]

        return grown, place

    def branches(place: int) -> tuple[list[str], int]:
        grown, place = run(place)

        while source[place:place + 1] == '|':
            more, place = run(place + 1)
            grown += more

        return grown, place

    grown, place = branches(0)

    if place != len(source):
        msg = f'stopped at {place} in {source!r}'
        raise ValueError(msg)

    return tuple(grown)


class TestTheRegisterNamesWhatTheGateRefuses:

    '''The register's account of a rule and the rule itself.

    Two of these drifted apart at once: the register named four
    obligation words where the pattern matched eight, and a docstring
    promised one complaint per line where the code walks paragraphs.
    Prose about a check is unread by the check, so it rots silently.

    The two sides answer each other here with nothing in between: a
    list kept in this file would drift with whichever side it was
    written beside.
    '''

    CAUSES = re.compile(r'\\b\(\?:([^)]*)\)\\b')
    OBLIGED = re.compile(
        r'\\b\(\?:([^()]*(?:\([^)]*\)[^()]*)*)\)\\b\(\?!-\)',
    )

    def _inside(self, which: re.Pattern[str]) -> str:
        found = which.search(check_wiki.OBLIGED_PURPOSE.pattern)

        assert found is not None

        return found.group(1)

    def test_the_register_names_the_causes_the_pattern_reads(self) -> None:
        assert sorted(_phrases(self._inside(self.CAUSES))) == sorted(
            _register_terms()[0],
        )

    def test_the_register_names_what_the_pattern_matches(self) -> None:
        assert sorted(_phrases(self._inside(self.OBLIGED))) == sorted(
            _register_terms()[1],
        )

    @pytest.mark.parametrize('word', _register_terms()[1])
    def test_each_word_the_register_names_is_refused(self, word: str) -> None:
        said = f'It is refused because the host {word} answer.'

        assert check_wiki._obliged_purpose(said)

    @pytest.mark.parametrize('cause', _register_terms()[0])
    def test_each_cause_the_register_names_is_read(self, cause: str) -> None:
        said = f'It is refused {cause} the host must answer.'

        assert check_wiki._obliged_purpose(said)

    def test_the_register_names_some_of_each(self) -> None:
        causes, obliged = _register_terms()

        assert len(causes) > 1
        assert len(obliged) > 1

    @pytest.mark.parametrize(
        'source',
        [
            pytest.param(r'needs?\s*to', id='a-space-that-may-be-absent'),
            pytest.param(r'needs?\s{1,2}to', id='a-counted-space'),
            pytest.param(r'need\d+', id='an-escape-it-does-not-know'),
            pytest.param(r'need.to', id='a-mark-for-anything'),
            pytest.param(r'needs+ to', id='a-repeated-letter'),
            pytest.param(r'need[s] to', id='a-set'),
            pytest.param(r'(need|needs) to', id='a-group-that-remembers'),
        ],
    )
    def test_what_it_cannot_read_stops_it(self, source: str) -> None:
        with pytest.raises(ValueError):
            _phrases(source)

    def test_what_it_can_read_it_spells_out(self) -> None:
        assert sorted(_phrases(r'ha(?:s|ve)\s+to|must')) == [
            'has to', 'have to', 'must',
        ]


class TestEveryPageCheckIsWired:

    '''What `_check_page` runs for an atom and for a spine.

    A check was once added to this list at the wrong indentation: it
    landed in the spines branch twice and in the atoms branch not at
    all, which is valid Python and ran green for a day. Reading the
    source for the shape of those two branches was the first answer,
    and it could not tell a guard that is always false from one that
    holds — so each check answers here instead, and the folder the
    page sits in is the only thing that decides who hears it.
    '''

    SHARED = (
        '_check_voice',
        '_uncited_claims',
        '_unlined_sources',
        '_negative_definitions',
        '_obliged_purpose',
        '_bare_ordinals',
        '_unspaced_headings',
        '_check_metadata',
        '_check_citations',
    )

    ATOMS_ALONE = ('_unlinked_terms', '_check_length')
    SPINES_ALONE = ('_spine_steps',)

    @staticmethod
    def _times(
        monkeypatch: pytest.MonkeyPatch, folder: str, root: Path, named: str,
    ) -> int:
        '''How often `_check_page` calls one check for a page in one folder.'''

        page = root / folder / 'a-page.md'
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            '---\nrow: P1-01\n---\n# A page\n\nIt is read.\n',
            encoding='utf-8',
        )
        called = []
        monkeypatch.setattr(
            check_wiki, named,
            lambda *_, **__: called.append(named) or [],
            raising=True,
        )
        check_wiki._check_page(page, set(), check_wiki._SourceFacts())

        return len(called)

    @classmethod
    def _heard(
        cls, monkeypatch: pytest.MonkeyPatch, folder: str, root: Path,
        named: str,
    ) -> bool:
        return cls._times(monkeypatch, folder, root, named) > 0

    @pytest.mark.parametrize('named', SHARED + ATOMS_ALONE)
    def test_an_atom_is_held_to_it(
        self, named: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        assert self._heard(monkeypatch, 'atoms', tmp_path, named)

    @pytest.mark.parametrize('named', SHARED + SPINES_ALONE)
    def test_a_spine_is_held_to_it(
        self, named: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        assert self._heard(monkeypatch, 'spines', tmp_path, named)

    @pytest.mark.parametrize('named', ATOMS_ALONE)
    def test_a_spine_is_spared_the_atom_checks(
        self, named: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        assert not self._heard(monkeypatch, 'spines', tmp_path, named)

    @pytest.mark.parametrize('named', SPINES_ALONE)
    def test_an_atom_is_spared_the_spine_checks(
        self, named: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        assert not self._heard(monkeypatch, 'atoms', tmp_path, named)

    @pytest.mark.parametrize('named', SHARED + ATOMS_ALONE + SPINES_ALONE)
    def test_a_page_in_neither_folder_is_held_to_nothing(
        self, named: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        assert not self._heard(monkeypatch, 'elsewhere', tmp_path, named)

    @pytest.mark.parametrize('named', SHARED + ATOMS_ALONE)
    def test_an_atom_hears_it_once(
        self, named: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        assert self._times(monkeypatch, 'atoms', tmp_path, named) == 1

    @pytest.mark.parametrize('named', SHARED + SPINES_ALONE)
    def test_a_spine_hears_it_once(
        self, named: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        assert self._times(monkeypatch, 'spines', tmp_path, named) == 1


class TestAStampInTheProse:

    def test_a_moment_in_a_sentence_is_refused(self) -> None:
        said = 'It asked for the `Created … Last modified 2026-10-18 11:00 UTC'
        assert check_wiki._stamps_in_prose(said)

    def test_a_pinning_prefix_on_a_sentence_is_refused(self) -> None:
        said = 'Pinned at the venue on 2026-10-02 00:00 UTC the order left.'
        assert check_wiki._stamps_in_prose(said)

    def test_a_moment_wrapped_across_two_lines_is_refused(self) -> None:
        said = 'It asked for the footer of 2026-10-18\n11:00 UTC gone.'
        assert check_wiki._stamps_in_prose(said)

    _SHOWN = 'It asked for 2026-10-01 00:00 UTC here.'

    @pytest.mark.parametrize(
        'fence', ['```', '~~~', '````'],
        ids=['backticks', 'tildes', 'four-backticks'],
    )
    def test_a_moment_inside_a_fence_is_passed_over(self, fence: str) -> None:
        fenced = f'{fence}\n{self._SHOWN}\n{fence}\n\nProse here.'
        assert not check_wiki._stamps_in_prose(fenced)

    @pytest.mark.parametrize(
        'fence', ['```', '~~~', '````'],
        ids=['backticks', 'tildes', 'four-backticks'],
    )
    def test_a_moment_outside_that_fence_is_still_refused(
        self, fence: str,
    ) -> None:
        fenced = f'{fence}\nnothing here\n{fence}\n\n{self._SHOWN}'
        assert check_wiki._stamps_in_prose(fenced)

    def test_a_shorter_fence_inside_a_longer_one_does_not_close_it(
        self,
    ) -> None:
        nested = f'````\n```\n{self._SHOWN}\n```\n````\n\nProse.'
        assert not check_wiki._stamps_in_prose(nested)

    def test_a_fence_naming_a_language_does_not_close_one(self) -> None:
        tagged = f'```\n```python\n{self._SHOWN}\n```\n\nProse.'
        assert not check_wiki._stamps_in_prose(tagged)

    @pytest.mark.parametrize(
        'after', ['', '## Next'], ids=['a-blank-line', 'a-heading'],
    )
    def test_a_quote_ending_closes_the_fence_it_opened(
        self, after: str,
    ) -> None:
        ended = f'> ```\n> example\n{after}\n\n{self._SHOWN}'
        assert check_wiki._stamps_in_prose(ended)

    def test_a_backtick_run_opening_a_list_item_is_not_a_fence(self) -> None:
        listed = f'- ```\n- {self._SHOWN}\n- ```\n\nProse.'
        assert check_wiki._stamps_in_prose(listed), (
            'three list items, not one fenced block: reading the run as a '
            'fence hid the middle item'
        )

    def test_prose_after_a_list_holding_a_run_is_still_read(self) -> None:
        listed = f'- ```\n  example\n\n{self._SHOWN}'
        assert check_wiki._stamps_in_prose(listed)

    def test_a_fence_inside_a_quote_is_still_a_fence(self) -> None:
        quoted = f'> ```\n> {self._SHOWN}\n> ```\n\nProse.'
        assert not check_wiki._stamps_in_prose(quoted)

    def test_a_fence_of_the_other_mark_does_not_close_one(self) -> None:
        crossed = f'```\n~~~\n{self._SHOWN}\n~~~\n```\n\nProse.'
        assert not check_wiki._stamps_in_prose(crossed)

    def test_a_longer_closer_of_the_same_mark_does_close_one(self) -> None:
        shut = f'```\nnothing here\n````\n\n{self._SHOWN}'
        assert check_wiki._stamps_in_prose(shut)

    def test_a_whole_footer_quoted_in_a_sentence_is_refused(self) -> None:
        footer = (
            'Created 2026-10-01 00:00 UTC \u00b7 Last modified '
            '2026-10-02 00:00 UTC'
        )
        assert check_wiki._stamps_in_prose(f'It quoted {footer} in a sentence.')

    @pytest.mark.parametrize(
        'line',
        [
            pytest.param(
                'Created 2026-10-01 00:00 UTC \u00b7 Last modified '
                '2026-10-02 00:00 UTC',
                id='the-footer',
            ),
            pytest.param('modified: 2026-10-02 00:00 UTC', id='metadata'),
            pytest.param('reviewed: 2026-10-02 00:00 UTC', id='a-review-stamp'),
            pytest.param(
                '| P1-01 | 2026-10-02 00:00 UTC | one |', id='a-table-row',
            ),
            pytest.param(
                'Pinned at 2026-10-02 00:00 UTC', id='a-pinning-line',
            ),
        ],
    )
    def test_a_moment_where_it_belongs_passes(self, line: str) -> None:
        assert not check_wiki._stamps_in_prose(line)


class TestBareOrdinals:
    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param(
                'The fourth goes the other way: no release is worked out.',
                id='renumbered-three-rounds-running',
            ),
            pytest.param('The third keeps it alone.', id='the-third'),
            pytest.param('The third is refused.', id='the-third-is'),
        ],
    )
    def test_an_ordinal_standing_for_a_thing_is_refused(
        self, sentence: str,
    ) -> None:
        assert check_wiki._bare_ordinals(sentence)

    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param('The fourth stage is capital.', id='qualifying-a-noun'),
            pytest.param(
                'A second walk comes back with nothing.',
                id='qualifying-a-noun-before-a-verb',
            ),
            pytest.param(
                'The third figure the fill reports is its value.',
                id='qualifying-a-noun-with-a-clause',
            ),
        ],
    )
    def test_an_ordinal_qualifying_a_noun_passes(self, sentence: str) -> None:
        assert not check_wiki._bare_ordinals(sentence)

    def test_an_ordinal_past_the_seventh_is_read(self) -> None:
        assert check_wiki._bare_ordinals('The eighth is a single figure.')

    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param(
                'A second is enough for the retry.', id='indefinite',
            ),
            pytest.param('The second goes by.', id='definite'),
            pytest.param(
                'Until the second has elapsed, nothing is sent.', id='clause',
            ),
        ],
    )
    def test_a_second_of_time_is_left_alone(self, sentence: str) -> None:
        assert not check_wiki._bare_ordinals(sentence)

    def test_a_month_in_that_slot_is_left_alone(self) -> None:
        assert not check_wiki._bare_ordinals('The third May is the deadline.')

    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param(
                'The third pass checks the ledger.', id='noun-ending-in-s',
            ),
            pytest.param(
                'The fourth process writes the record.', id='another-such-noun',
            ),
        ],
    )
    def test_a_noun_ending_in_s_is_not_read_as_a_verb(
        self, sentence: str,
    ) -> None:
        assert not check_wiki._bare_ordinals(sentence)

    def test_a_first_earlier_on_the_same_line_anchors_it(self) -> None:
        line = 'The first weighs the order. The third weighs the budget.'
        assert not check_wiki._bare_ordinals(line)

    def test_a_first_later_on_the_same_line_does_not(self) -> None:
        line = 'The third weighs the budget. The first weighs the order.'
        assert check_wiki._bare_ordinals(line)

    def test_a_heading_is_not_read_for_it(self) -> None:
        heading = '## The fourth is refused'
        assert check_wiki._bare_ordinals(heading.lstrip('# '))
        assert not check_wiki._bare_ordinals(heading)

    def test_an_ordinal_after_a_first_in_the_same_section_passes(self) -> None:
        body = (
            '## Four limits\n\nThe first weighs the order.\n\n'
            'The third weighs the budget.\n'
        )
        assert not check_wiki._bare_ordinals(body)

    def test_an_ordinal_whose_first_is_in_another_section_is_refused(
        self,
    ) -> None:
        body = (
            '## The order\n\nThe first keeps the order.\n\n'
            '## The money\n\nThe third keeps the money.\n'
        )
        assert check_wiki._bare_ordinals(body)

    @pytest.mark.parametrize(
        'noun', ['hold', 'holds', 'read', 'reads', 'leave', 'leaves'],
    )
    def test_an_ordinal_qualifying_a_noun_or_its_plural_passes(
        self, noun: str,
    ) -> None:
        assert not check_wiki._bare_ordinals(f'The third {noun} keeps it.')

    _VERBS = (
        'is', 'was', 'does', 'has', 'can', 'will', 'comes', 'goes', 'takes',
        'keeps', 'weighs', 'gives', 'adds', 'refuses',
    )
    _ORDINALS = (
        'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth',
        'tenth',
    )

    def test_the_verb_list_is_the_one_written_here(self) -> None:
        assert tuple(check_wiki._STANDS_ALONE.split('|')) == self._VERBS

    def test_the_ordinal_list_is_the_one_written_here(self) -> None:
        assert tuple(check_wiki._ORDINALS.split('|')) == self._ORDINALS

    @pytest.mark.parametrize('verb', _VERBS)
    def test_every_verb_in_the_list_is_read(self, verb: str) -> None:
        assert check_wiki._bare_ordinals(f'The third {verb} it.')

    @pytest.mark.parametrize('ordinal', _ORDINALS)
    def test_every_ordinal_in_the_list_is_read(self, ordinal: str) -> None:
        assert check_wiki._bare_ordinals(f'The {ordinal} is refused.')

    def test_a_wrapped_ordinal_is_still_read(self) -> None:
        assert check_wiki._bare_ordinals('The third\nkeeps the money.')

    def test_a_first_in_another_list_item_still_anchors_it(self) -> None:
        listed = '- The first weighs it\n- The third weighs it'
        assert not check_wiki._bare_ordinals(listed)


    def test_an_emphasised_first_still_anchors_it(self) -> None:
        said = 'The *first* weighs the order. The third weighs the budget.'
        assert not check_wiki._bare_ordinals(said)

    def test_a_first_wrapped_before_it_still_anchors_it(self) -> None:
        body = '## A\n\nThe\nfirst weighs the order. The third weighs it.\n'
        assert not check_wiki._bare_ordinals(body)

    @pytest.mark.parametrize(
        'sentence',
        [
            pytest.param('A third is held in reserve.', id='a-fraction'),
            pytest.param('A fourth is refused.', id='another-one'),
            pytest.param(
                'It failed. A fourth goes the other way.', id='after-a-stop',
            ),
        ],
    )
    def test_an_indefinite_ordinal_goes_unread(self, sentence: str) -> None:
        assert not check_wiki._bare_ordinals(sentence)


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

    @pytest.mark.parametrize(
        'line',
        [
            pytest.param('---one two three four.', id='dashes'),
            pytest.param('| one two three four.', id='a-pipe'),
            pytest.param('Created in haste, the Last modified one two.', id='the-stamp'),
            pytest.param('- [one](a.md) two three four five.', id='a-link'),
        ],
    )
    def test_prose_shaped_like_something_else_is_counted(self, line: str) -> None:
        held = check_wiki._prose_words(f'# Title\n\n{line}\n')

        assert held > 1, line

    def test_words_written_between_cell_marks_are_counted(self) -> None:
        page = (
            '# Title\n\n| ID | Topic |\n|---|---|\n'
            '| P1-01 | one two three four five six seven |\n'
        )

        assert check_wiki._prose_words(page) > 6

    def test_the_pages_own_stamp_is_not_counted(self) -> None:
        plain = '# Title\n\nOne two three.\n'
        stamped = plain + (
            '\n---\n\nCreated 2026-01-01 00:00 UTC · '
            'Last modified 2026-01-02 00:00 UTC\n'
        )

        assert check_wiki._prose_words(stamped) == check_wiki._prose_words(plain)

    def test_a_divider_is_not_counted(self) -> None:
        plain = '# Title\n\nOne two three.\n'
        ruled = plain + '\n---\n'

        assert check_wiki._prose_words(ruled) == check_wiki._prose_words(plain)

    def test_a_paragraph_opening_on_dashes_is_counted(self) -> None:
        held = check_wiki._prose_words('# Title\n\n---one two three four.\n')

        assert held == 5


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
    def test_a_stamp_before_the_last_commit_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            check_wiki, '_last_commit_stamp', lambda _p: '2026-10-04 09:00 UTC',
        )
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-02 09:00 UTC\n'
        assert not check_wiki._check_stamps(tmp_path / 'a.md', '', meta)

    def test_a_stamp_ahead_of_the_last_commit_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            check_wiki, '_last_commit_stamp', lambda _p: '2026-10-04 09:00 UTC',
        )
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-05 09:00 UTC\n'
        assert check_wiki._check_stamps(tmp_path / 'a.md', '', meta)

    def test_a_page_created_after_it_was_modified_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(check_wiki, '_last_commit_stamp', lambda _p: None)
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
        name, state, column = self._a_praxis_cell()
        failures = self._doctored(
            tmp_path, monkeypatch,
            f'| `{name}` | {state} | {column} |',
            f'| `praxis/core/nonesuch.py` | {state} | {column} |',
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
        name, state, column = self._a_praxis_cell()
        failures = self._doctored(
            tmp_path, monkeypatch,
            f'| `{name}` | {state} | {column} |\n', '',
        )

        assert any('unaccounted for' in f for f in failures)

    @staticmethod
    def _a_praxis_cell() -> tuple[str, str, str]:
        body = check_wiki._ledger_sections(
            check_wiki.LEDGER.read_text(encoding='utf-8'),
        ).get('Praxis', '')

        for name, state, column in check_wiki.LEDGER_ROW_RE.findall(body):
            if check_wiki._ledger_listed(column):
                return name, state, column.strip()

        pytest.skip('no Praxis cell names a row')
        raise AssertionError

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

    def test_a_span_across_two_series_names_nothing(self) -> None:
        assert check_wiki._ledger_listed('N2-01 to P2-03') == set()

    def test_a_span_across_two_packages_names_nothing(self) -> None:
        assert check_wiki._ledger_listed('N2-01 to N3-03') == set()

    def test_a_span_expands(self) -> None:
        assert check_wiki._ledger_listed('P4-01, P4-03 to P4-05') == {
            'P4-01', 'P4-03', 'P4-04', 'P4-05',
        }

    def test_a_nexus_span_expands_too(self) -> None:
        assert check_wiki._ledger_listed('N2-01 to N2-03') == {
            'N2-01', 'N2-02', 'N2-03',
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
        name, state, column = self._a_full_praxis_cell()
        stranger = self._a_row_citing_nothing_in(name)
        failures = self._doctored(
            tmp_path, monkeypatch,
            f'| `{name}` | {state} | {column} |',
            f'| `{name}` | {state} | {stranger}, {column} |',
        )

        assert any(f'`{name}` names' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_cell_omitting_a_row_that_cites_it_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        row = self._a_praxis_cell_with_two_rows()
        name, state, column = row
        kept = ', '.join(column.split(', ')[:-1])
        failures = self._doctored(
            tmp_path, monkeypatch,
            f'| `{name}` | {state} | {column} |',
            f'| `{name}` | {state} | {kept} |',
        )

        assert any(f'`{name}` names' in f for f in failures)

    @staticmethod
    def _a_full_praxis_cell() -> tuple[str, str, str]:
        body = check_wiki._ledger_sections(
            check_wiki.LEDGER.read_text(encoding='utf-8'),
        ).get('Praxis', '')

        for name, state, column in check_wiki.LEDGER_ROW_RE.findall(body):
            if state == 'full' and check_wiki._ledger_listed(column):
                return name, state, column.strip()

        pytest.skip('no Praxis cell reads `full` with a row named')
        raise AssertionError

    @staticmethod
    def _a_row_citing_nothing_in(name: str) -> str:
        cited = check_wiki._row_file_citations()
        every = {row for rows in cited.values() for row in rows}

        for row in sorted(every - cited.get(name, set())):
            return row

        pytest.skip(f'every register row cites `{name}`')
        raise AssertionError

    @staticmethod
    def _a_praxis_cell_with_two_rows() -> tuple[str, str, str]:
        body = check_wiki._ledger_sections(
            check_wiki.LEDGER.read_text(encoding='utf-8'),
        ).get('Praxis', '')

        for name, state, column in check_wiki.LEDGER_ROW_RE.findall(body):
            if len(check_wiki._ledger_listed(column)) > 1:
                return name, state, column.strip()

        pytest.skip('no Praxis cell names more than one row')
        raise AssertionError

    @_NEEDS_BASELINE
    def test_an_uncited_file_not_marked_uncovered_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ledger = tmp_path / 'ledger.md'
        ledger.write_text(
            '## Praxis — 1 modules\n\n'
            '| `praxis/core/health_tracker.py` | full | — |\n',
            encoding='utf-8',
        )
        register = tmp_path / 'register.md'
        register.write_text('# register\n', encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'LEDGER', ledger)
        monkeypatch.setattr(check_wiki, 'REGISTER', register)

        failures = check_wiki._ledger_rows()

        assert any('is `full` with no row citing it' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_cited_module_with_no_row_of_its_own_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        name, state, column = self._a_full_praxis_cell()
        failures = self._doctored(
            tmp_path, monkeypatch,
            f'| `{name}` | {state} | {column} |\n', '',
        )

        assert any(f'nothing names `{name}`' in f for f in failures)

    @_NEEDS_BASELINE
    def test_a_cited_file_marked_uncovered_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        name, state, column = self._a_full_praxis_cell()
        failures = self._doctored(
            tmp_path, monkeypatch,
            f'| `{name}` | {state} | {column} |',
            f'| `{name}` | uncovered | {column} |',
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
        page.write_text('13 are named.', encoding='utf-8')
        kept = check_wiki.README
        check_wiki.README = page

        try:
            failures = check_wiki._counted_states()
        finally:
            check_wiki.README = kept

        assert any('13 are named' in f for f in failures)

    @pytest.mark.parametrize(
        ('written', 'quoted'),
        [
            pytest.param('99 carry a row.', '99 carry a row', id='owned'),
            pytest.param(
                '99 are reached by an article.', '99 are reached by an',
                id='cited-only',
            ),
            pytest.param(
                'The other 99 carry a row.', 'The other 99 carry a row',
                id='owned-as-the-ledger-writes-it',
            ),
            pytest.param(
                '99 of the modules listed are cited.',
                '99 of the modules listed', id='cited-as-the-ledger-writes-it',
            ),
            pytest.param(
                'The 99 with no row are next.', 'The 99 with no row',
                id='unowned',
            ),
        ],
    )
    def test_a_drifted_nexus_subtotal_is_caught(
        self, tmp_path: Path, written: str, quoted: str,
    ) -> None:
        page = tmp_path / 'README.md'
        page.write_text(written, encoding='utf-8')
        kept = check_wiki.README
        check_wiki.README = page

        try:
            failures = check_wiki._counted_states()
        finally:
            check_wiki.README = kept

        assert any(quoted in f for f in failures), failures

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
        unrowed = 'nexus/__init__.py'
        failures = check_wiki._nexus_ledger_rows({unrowed: {'P2-11'}}, {})

        assert any(f'{unrowed} is cited but not named' in f for f in failures)

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

    @staticmethod
    def _a_nexus_cell() -> tuple[str, set[str]]:
        '''Return a Nexus file the ledger names and every row it lists.

        The cell carrying the most is taken: one carrying a single row
        cannot tell a check that reports every offender from one that
        reports the first.
        '''

        body = check_wiki._ledger_sections(
            check_wiki.LEDGER.read_text(encoding='utf-8'),
        ).get('Nexus', '')

        return max(
            (
                (name, check_wiki._ledger_listed(column))
                for name, _, column in check_wiki.LEDGER_ROW_RE.findall(body)
            ),
            key=lambda cell: len(cell[1]),
        )

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_nexus_row_naming_an_article_that_does_not_cite_it_is_caught(
        self,
    ) -> None:
        named, rows = self._a_nexus_cell()
        failures = check_wiki._nexus_ledger_rows({named: {'N9-99'}}, {})

        assert len(rows) > 1

        for row in rows:
            assert any(
                f'the row for {named} names {row}, which does not cite it' in f
                for f in failures
            )

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_nexus_row_the_article_does_cite_is_left_alone(self) -> None:
        named, rows = self._a_nexus_cell()
        failures = check_wiki._nexus_ledger_rows({named: set(rows)}, {})

        assert not any(f'the row for {named}' in f for f in failures)

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_cell_carrying_rows_is_owned_whatever_else_it_says(self) -> None:
        assert check_wiki._ledger_listed(
            'N3-01, N3-02, cited, not traced',
        ) == {'N3-01', 'N3-02'}
        assert check_wiki._ledger_listed('cited, not traced') == set()
        assert check_wiki._ledger_listed('N1-01, N2-07') == {'N1-01', 'N2-07'}

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_cell_saying_both_is_counted_by_its_rows(self) -> None:
        body = (
            '| File | State | Rows |\n'
            '|---|---|---|\n'
            '| `nexus/a.py` | partial | N1-01, cited, not traced |\n'
            '| `nexus/b.py` | partial | cited, not traced |\n'
        )
        named, owned, total = check_wiki._nexus_counts(body)

        assert (named, owned, total) == (2, 1, 2)

    def test_the_ledger_as_it_stands_draws_no_row_complaint(self) -> None:
        failures = check_wiki._nexus_ledger_rows(
            check_wiki._row_file_citations(),
            check_wiki._finding_file_citations(),
        )

        assert not any('the row for' in f for f in failures)

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_row_citing_a_named_nexus_file_answers_for_it(self) -> None:
        named, rows = self._a_nexus_cell()
        failures = check_wiki._nexus_ledger_rows({named: set(rows)}, {})

        assert not any(
            f'{named} is named in the Nexus rows but nothing cites it' in f
            for f in failures
        )

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_finding_citing_a_named_nexus_file_answers_for_it(self) -> None:
        named, _ = self._a_nexus_cell()
        failures = check_wiki._nexus_ledger_rows({}, {named: {'H-001'}})

        assert not any(
            f'{named} is named in the Nexus rows but nothing cites it' in f
            for f in failures
        )

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_nexus_cell_missing_a_row_that_cites_it_is_caught(self) -> None:
        named, rows = self._a_nexus_cell()
        failures = check_wiki._nexus_ledger_rows(
            {named: {*rows, 'N9-99'}}, {},
        )

        assert any(
            f'the row for {named} carries rows but not N9-99' in f
            for f in failures
        )

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the Nexus rows are checked only where that tree is present',
    )
    def test_a_nexus_cell_carrying_none_is_held_to_neither(self) -> None:
        body = check_wiki._ledger_sections(
            check_wiki.LEDGER.read_text(encoding='utf-8'),
        ).get('Nexus', '')
        named = next(
            name for name, _, column in check_wiki.LEDGER_ROW_RE.findall(body)
            if not check_wiki._ledger_listed(column)
        )
        failures = check_wiki._nexus_ledger_rows({named: {'N9-99'}}, {})

        assert not any(f'the row for {named} carries rows' in f
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
        monkeypatch.setattr(check_wiki, '_last_commit_stamp', lambda _p: None)
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
        monkeypatch.setattr(check_wiki, '_last_commit_stamp', lambda _p: None)
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-09 07:41 UTC\n'

        assert check_wiki._check_stamps(page, meta, meta) == []

    @staticmethod
    def _at(offset: datetime.timedelta) -> str:
        return (datetime.datetime.now(tz=datetime.UTC) + offset).strftime(
            '%Y-%m-%d %H:%M UTC',
        )

    def test_a_stamp_put_back_on_an_edit_passes(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = Path('docs/wiki/atoms/one.md')
        monkeypatch.setattr(
            check_wiki, '_edited_since', lambda _p: '2026-11-16 15:30 UTC',
        )
        monkeypatch.setattr(check_wiki, '_last_commit_stamp', lambda _p: None)
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-11-09 14:49 UTC\n'

        assert check_wiki._check_stamps(page, meta, meta) == []

    def test_a_stamp_after_now_is_refused(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = Path('docs/wiki/atoms/one.md')
        monkeypatch.setattr(check_wiki, '_edited_since', lambda _p: None)
        monkeypatch.setattr(check_wiki, '_last_commit_stamp', lambda _p: None)
        ahead = self._at(datetime.timedelta(days=7))
        meta = f'created: 2026-10-01 09:00 UTC\nmodified: {ahead}\n'
        failures = check_wiki._check_stamps(page, meta, meta)

        assert len(failures) == 1
        assert 'is a time that has not arrived' in failures[0]

    def test_a_stamp_at_this_minute_passes(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = Path('docs/wiki/atoms/one.md')
        monkeypatch.setattr(check_wiki, '_edited_since', lambda _p: None)
        monkeypatch.setattr(check_wiki, '_last_commit_stamp', lambda _p: None)
        meta = (
            f'created: 2026-10-01 09:00 UTC\n'
            f'modified: {self._at(datetime.timedelta())}\n'
        )

        assert check_wiki._check_stamps(page, meta, meta) == []

    def test_a_stamp_after_the_commit_that_recorded_it_is_refused(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = Path('docs/wiki/atoms/one.md')
        monkeypatch.setattr(check_wiki, '_edited_since', lambda _p: None)
        monkeypatch.setattr(
            check_wiki, '_last_commit_stamp', lambda _p: '2026-10-09 07:01 UTC',
        )
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-09 07:31 UTC\n'
        failures = check_wiki._check_stamps(page, meta, meta)

        assert failures == [
            f'{page.as_posix()}: last modified 2026-10-09 07:31 UTC is after '
            'the commit that recorded it, 2026-10-09 07:01 UTC',
        ]

    def test_a_stamp_before_the_commit_that_recorded_it_passes(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = Path('docs/wiki/atoms/one.md')
        monkeypatch.setattr(check_wiki, '_edited_since', lambda _p: None)
        monkeypatch.setattr(
            check_wiki, '_last_commit_stamp', lambda _p: '2026-10-20 11:00 UTC',
        )
        meta = 'created: 2026-10-01 09:00 UTC\nmodified: 2026-10-09 07:31 UTC\n'

        assert check_wiki._check_stamps(page, meta, meta) == []

    def test_no_page_in_the_wiki_claims_a_time_yet_to_come(self) -> None:
        now = self._at(datetime.timedelta())
        ahead = [
            f'{page.as_posix()}: {key} {when}'
            for page in sorted(check_wiki.WIKI.rglob('*.md'))
            for key, when in re.findall(
                r'^(created|modified|reviewed): '
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)$',
                page.read_text(encoding='utf-8'),
                re.MULTILINE,
            )
            if when > now
        ]

        assert ahead == []


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
            if kind in check_wiki._covered_kinds({'Exception'})
        ]

        assert covered == []

    def test_a_kind_inside_exception_is_covered(self) -> None:
        assert 'ValueError' in check_wiki._covered_kinds({'Exception'})

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

    @staticmethod
    def _a_full_praxis_module() -> str:
        body = check_wiki._ledger_sections(
            check_wiki.LEDGER.read_text(encoding='utf-8'),
        ).get('Praxis', '')

        for name, state, _ in check_wiki.LEDGER_ROW_RE.findall(body):
            if state == 'full':
                return name

        raise AssertionError('no Praxis cell reads `full`')

    @_NEEDS_BASELINE
    def test_a_full_module_under_an_unanswered_question_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        name = self._a_full_praxis_module()
        register, row = _an_unassigned_question(tmp_path)
        monkeypatch.setattr(check_wiki, 'REGISTER', register)

        assert check_wiki._open_candidates({name: {row}}) == [
            f'{check_wiki.LEDGER}: `{name}` is `full` '
            f"while ['{row}'] leave a question on it",
        ]

    @_NEEDS_BASELINE
    def test_a_full_module_with_a_candidate_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        name = self._a_full_praxis_module()
        register, row = _an_unsettled_candidate(tmp_path)
        monkeypatch.setattr(check_wiki, 'REGISTER', register)

        assert check_wiki._open_candidates({name: {row}}) == [
            f'{check_wiki.LEDGER}: `{name}` is `full` '
            f"while ['{row}'] leave a question on it",
        ]


_REGISTER_HEAD = (
    '# Register\n\n'
    '## Package 1\n\n'
    '| Row | Cites | Finding | Reading | Disposition |\n'
    '| --- | --- | --- | --- | --- |\n'
)
_SYNTHETIC_ROW = 'H-9001'


def _a_register(tmp_path: Path, rows: str, name: str) -> Path:

    '''Write a register carrying only the rows a test needs.

    A fixture that edits a copy of the real register stops working
    once the register stops carrying the row it looks for, and one
    that skips in that case stops testing without saying so: two such
    fixtures left the open-candidate check unexercised while reading
    as passing. Rows built outright keep the check exercised whatever
    the register comes to hold.

    Args:
        tmp_path (Path): Where to write it
        rows (str): The table rows, each ending in a newline
        name (str): The file name to write under

    Returns:
        Path: The register written
    '''

    register = tmp_path / name
    register.write_text(_REGISTER_HEAD + rows, encoding='utf-8')

    return register


def _an_unassigned_question(tmp_path: Path) -> tuple[Path, str]:

    '''Return a register leaving a question unanswered, and the row on it.

    Args:
        tmp_path (Path): Where to write the register

    Returns:
        tuple[Path, str]: The register, and the harvest row naming the
            question nobody is assigned
    '''

    register = _a_register(
        tmp_path,
        f'| {_SYNTHETIC_ROW} | `order.py` 1 | a finding | read | held by U-99 |\n'
        '| Is the question answered? | U-99 | nowhere | unassigned |\n',
        'asking-register.md',
    )

    return register, _SYNTHETIC_ROW


def _an_unsettled_candidate(tmp_path: Path) -> tuple[Path, str]:

    '''Return a register whose candidate no merge table settles, and its row.

    Args:
        tmp_path (Path): Where to write the register

    Returns:
        tuple[Path, str]: The register, and the harvest row reading
            `candidate` with no merge row over it
    '''

    register = _a_register(
        tmp_path,
        f'| {_SYNTHETIC_ROW} | `order.py` 1 | a finding | read | candidate |\n',
        'open-register.md',
    )

    return register, _SYNTHETIC_ROW


def _a_lagged_cell() -> str:

    '''Return a Praxis module whose cell the ledger could lag on.

    The module is found rather than named. A cell named outright stops
    serving once it is no longer fully cited, and a cell in the Nexus
    tree leaves the check unexercised wherever only Praxis is checked
    out, which is how this test came to fail on a host holding one
    tree rather than two.

    Returns:
        str: The ledger's own name for that module
    '''

    text = check_wiki.REGISTER.read_text(encoding='utf-8')
    hanging = check_wiki._unresolved_questions(text)
    open_rows = {
        row for row, _, disposition in check_wiki.FINDING_ROW_CELLS_RE.findall(text)
        if 'candidate' in disposition.lower()
        or hanging & set(check_wiki.UNRESOLVED_RE.findall(disposition))
    }
    found = check_wiki._finding_file_citations()
    cited = check_wiki._cited_lines()
    body = check_wiki._ledger_sections(
        check_wiki.LEDGER.read_text(encoding='utf-8'),
    ).get('Praxis', '')

    for name, state, cell in check_wiki.LEDGER_ROW_RE.findall(body):

        if state != 'full' or 'shape only' in cell:
            continue

        path = check_wiki._resolve_source(name)

        if path is None:
            continue

        statements = check_wiki._statement_lines(path)

        if (
            statements
            and not statements - cited.get(name, set())
            and not open_rows & found.get(name, set())
        ):
            return name

    raise AssertionError('no Praxis cell reads `full` with every statement cited')


def _lagged_ledger(tmp_path: Path, name: str) -> Path:

    '''Write a ledger reading `partial` where the real one reads `full`.

    Args:
        tmp_path (Path): Where to write it
        name (str): The module whose cell to put back

    Returns:
        Path: The ledger written
    '''

    lagged = tmp_path / 'ledger.md'
    lagged.write_text(
        check_wiki.LEDGER.read_text(encoding='utf-8').replace(
            f'| `{name}` | full |',
            f'| `{name}` | partial |',
        ),
        encoding='utf-8',
    )

    return lagged


class TestLaggingCells:

    @_NEEDS_BASELINE
    def test_no_fully_cited_module_reads_partial(self) -> None:
        assert check_wiki._lagging_cells(
            check_wiki._finding_file_citations(),
        ) == []

    @_NEEDS_BASELINE
    def test_a_fully_cited_partial_cell_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        name = _a_lagged_cell()
        lagged = _lagged_ledger(tmp_path, name)
        monkeypatch.setattr(check_wiki, 'LEDGER', lagged)

        assert check_wiki._lagging_cells(
            check_wiki._finding_file_citations(),
        ) == [
            f'{lagged}: `{name}` is `partial` '
            'with every statement cited and no candidate left on it',
        ]

    @_NEEDS_BASELINE
    def test_a_partial_cell_with_a_candidate_on_it_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        name = _a_lagged_cell()
        lagged = _lagged_ledger(tmp_path, name)
        monkeypatch.setattr(check_wiki, 'LEDGER', lagged)
        register, row = _an_unsettled_candidate(tmp_path)
        monkeypatch.setattr(check_wiki, 'REGISTER', register)

        found = check_wiki._finding_file_citations()
        found[name] = {row}

        assert check_wiki._lagging_cells(found) == []

    @staticmethod
    def test_a_declaration_is_no_statement(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            "class C:\n    a: int\n\n    def f(self) -> None:\n        '''Doc.'''\n\n"
            "        self.a = 1\n"
        )
        monkeypatch.setattr(check_wiki, '_source_text', lambda _: source)

        assert check_wiki._statement_lines(tmp_path / 'm.py') == {7}


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
        rebound = check_wiki._name_bindings(ast.parse(source))

        assert 'Protocol' in rebound

    def test_a_with_target_rebinds_the_protocol(self) -> None:
        source = (
            'from typing import Protocol\n\n'
            'with open("x") as Protocol:\n    pass\n\n'
            'class Venue(Protocol):\n\n'
            '    def submit(self) -> None:\n        ...\n'
        )

        assert 'Protocol' in check_wiki._name_bindings(ast.parse(source))

    def test_an_async_with_target_rebinds_the_protocol(self) -> None:
        source = (
            'from typing import Protocol\n\n'
            'async def f():\n    async with cm() as Protocol:\n        pass\n'
        )

        assert 'Protocol' in check_wiki._name_bindings(ast.parse(source))


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
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the second logger name lives in the Nexus tree',
    )
    def test_a_logger_under_another_name_is_a_log_call(self) -> None:
        failures = check_wiki._check_citations(
            ['a claim | `nexus/core/capital_controller/capital_controller.py`'
             ' 250-257'],
            check_wiki._SourceFacts(),
        )

        assert any('log call' in failure for failure in failures)

    @_NEEDS_BASELINE
    @pytest.mark.skipif(
        not (check_wiki.NEXUS_ROOT / '.git').exists(),
        reason='the second logger name lives in the Nexus tree',
    )
    def test_a_bare_else_does_not_save_a_range_of_logging(self) -> None:
        failures = check_wiki._check_citations(
            ['a claim | `nexus/core/capital_controller/capital_controller.py`'
             ' 249-257'],
            check_wiki._SourceFacts(),
        )

        assert any('log call' in failure for failure in failures)

    def test_what_the_module_calls_its_logger_is_read_off_it(self) -> None:
        import ast

        named = check_wiki._logger_names(
            ast.parse('import logging\n_logger = logging.getLogger(__name__)\n'),
        )

        assert named == frozenset({'_logger'})
        assert check_wiki._logger_names(ast.parse('_logger = 1\n')) == frozenset()
        assert check_wiki._logger_names(
            ast.parse('import structlog\n_log = structlog.get_logger()\n'),
        ) == frozenset({'_log'})

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


def _gate_checks() -> tuple[str, ...]:

    '''Return the name of every check `main` adds to its failures.

    The list of checks the wiring tests cover was written by hand, and
    three checks had been added to the gate without reaching it. Reading
    it off `main` is what stops a fourth.

    Returns:
        tuple[str, ...]: Each name, in the order the gate runs it.
    '''

    tree = ast.parse(Path(check_wiki.__file__).read_text(encoding='utf-8'))
    main = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == 'main'
    )

    return tuple(
        node.value.func.id
        for node in ast.walk(main)
        if isinstance(node, ast.AugAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == 'failures'
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
    )


class TestTheGateWiring:
    CHECKS = _gate_checks()

    def test_the_gates_checks_were_found(self) -> None:
        assert len(self.CHECKS) == len(set(self.CHECKS))
        assert set(self.CHECKS) >= {
            '_ledger_coverage',
            '_ledger_rows',
            '_counted_states',
            '_latest_release_counts',
            '_index_coverage',
            '_index_vocabulary',
            '_index_sections',
            '_pinned_table',
            '_finding_citations',
            '_review_states',
            '_reviewed_versions',
        }

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

    def test_a_claim_reaching_past_the_basic_plane_passes(self) -> None:
        held = self._GOOD.replace(
            '"A thing is so"', '"A thing \U00020000 is so"',
        )
        assert check_wiki._metadata_shape(held) == []

    @pytest.mark.parametrize(
        'before',
        ['baseline:', 'created:', 'modified:', 'evidence:'],
        ids=['second', 'third', 'fourth', 'before-the-evidence'],
    )
    def test_a_review_stamp_passes_wherever_it_sits(self, before: str) -> None:
        stamped = self._GOOD.replace(
            before, 'reviewed: 2099-01-01 00:00 UTC\n' + before, 1,
        )
        assert check_wiki._metadata_shape(stamped) == []

    def test_a_review_stamp_past_the_evidence_list_passes(self) -> None:
        stamped = self._GOOD + '\nreviewed: 2099-01-01 00:00 UTC'
        assert check_wiki._metadata_shape(stamped) == []

    def test_a_review_stamp_inside_the_evidence_list_is_refused(self) -> None:
        stamped = self._GOOD.replace(
            '    source:', 'reviewed: 2099-01-01 00:00 UTC\n    source:', 1,
        )
        notes = check_wiki._metadata_shape(stamped)
        assert any('middle of its evidence' in note for note in notes), notes

    @pytest.mark.parametrize(
        'written', ['reviewed', 'reviewed:', 'reviewed:   '],
        ids=['no-colon', 'colon-alone', 'only-spaces'],
    )
    def test_a_review_stamp_with_no_version_is_refused(
        self, written: str,
    ) -> None:
        stamped = self._GOOD.replace('evidence:', written + '\nevidence:', 1)
        notes = check_wiki._metadata_shape(stamped)
        assert any('without a value' in note for note in notes), notes

    def test_two_review_stamps_are_refused(self) -> None:
        both = (
            'reviewed: 2099-01-01 00:00 UTC\n'
            'reviewed: 2099-01-02 00:00 UTC\nevidence:'
        )
        notes = check_wiki._metadata_shape(
            self._GOOD.replace('evidence:', both, 1),
        )
        assert any('more than once' in note for note in notes), notes

    def test_a_printable_character_outside_ascii_passes(self) -> None:
        held = check_wiki._metadata_shape(
            self._GOOD.replace('"A thing is so"', '"A thing is s\u00f8"'),
        )

        assert held == []

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
                _GOOD.replace('"A thing is so"', '"\u00ad"'),
                'a claim that says nothing',
                id='a-claim-of-a-soft-hyphen',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"A thing\u0080is so"'),
                'a character the YAML behind it cannot carry',
                id='a-claim-holding-a-c1-control',
            ),
            pytest.param(
                _GOOD.replace('source: "`order.py` 3"', 'source: "`order\u009f.py` 3"'),
                'a character the YAML behind it cannot carry',
                id='a-source-holding-a-c1-control',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"A thing\ufffe is so"'),
                'a character the YAML behind it cannot carry',
                id='a-claim-holding-a-noncharacter',
            ),
            pytest.param(
                _GOOD.replace('"A thing is so"', '"A thing\ud800 is so"'),
                'a character the YAML behind it cannot carry',
                id='a-claim-holding-a-surrogate',
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
        'created: 2026-10-01 00:00 UTC\nmodified: 2026-10-01 00:00 UTC\n'
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
            check_wiki, '_last_commit_stamp', lambda _p: committed,
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
                _GOOD.replace('2026-10-01', '2099-01-01'),
                'is a time that has not arrived',
                id='stamp-yet-to-come',
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
            tmp_path, broken, monkeypatch, named=name,
            committed='2026-12-01 00:00 UTC',
        )

        assert any(wanted in note for note in held), held

    def test_a_page_outside_the_atoms_is_still_walked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            check_wiki, '_last_commit_stamp', lambda _p: '2026-12-01 00:00 UTC',
        )
        page = tmp_path / 'README.md'
        page.write_text(
            '# Index\n\nA list, said [elsewhere](nowhere-at-all.md).\n\n'
            '---\n\nCreated 2026-10-01 00:00 UTC · Last modified 2026-10-01 00:00 UTC\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', tmp_path)
        held = check_wiki._check_page(page, {'P1-01'}, check_wiki._SourceFacts())

        assert any('which does not exist' in note for note in held), held

    def test_a_moment_on_a_page_outside_the_atoms_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            check_wiki, '_last_commit_stamp', lambda _p: '2026-12-01 00:00 UTC',
        )
        page = tmp_path / 'register.md'
        page.write_text(
            '# Register\n\nIt asked for the `Created … Last modified '
            '2026-10-18 11:00 UTC\n\n---\n\nCreated 2026-10-01 00:00 UTC '
            '\u00b7 Last modified 2026-10-01 00:00 UTC\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'WIKI', tmp_path)
        held = check_wiki._check_page(page, {'P1-01'}, check_wiki._SourceFacts())

        assert any('prose carries a moment' in note for note in held), held

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
            pytest.param(
                _GOOD.replace(
                    'A thing that is so.',
                    'It asked for the footer of 2026-10-18 11:00 UTC gone.',
                ),
                'prose carries a moment',
                id='a-moment-in-the-prose',
            ),
            pytest.param(
                _GOOD.replace(
                    'A thing that is so.',
                    'It is refused because the host must agree.',
                ),
                'under no obligation to serve',
                id='a-purpose-the-code-is-not-under',
            ),
            pytest.param(
                _GOOD.replace('A thing that is so.', 'The third is refused.'),
                'ordinal stands in for a thing',
                id='an-ordinal-standing-alone',
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
            '---\ncreated: 2026-10-01 00:00 UTC\n'
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
        page = self._committed(tmp_path, monkeypatch, '2026-10-01 00:00 UTC')
        page.write_text(
            '---\ncreated: 2026-10-01 00:00 UTC\n'
            'modified: 2026-10-01 00:00 UTC\n---\n# One\n\nEdited.\n',
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
        page = self._committed(tmp_path, monkeypatch, '2026-10-01 00:00 UTC')
        page.write_text(
            '---\ncreated: 2026-10-01 00:00 UTC\n'
            'modified: 2026-10-02 00:00 UTC\n---\n# One\n\nEdited.\n',
            encoding='utf-8',
        )
        check_wiki._uncommitted_pages.cache_clear()

        assert self._complaints(page) == []

    @_NEEDS_BASELINE
    def test_a_page_as_committed_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = self._committed(tmp_path, monkeypatch, '2026-10-01 00:00 UTC')

        assert self._complaints(page) == []

    @_NEEDS_BASELINE
    def test_a_stamp_put_right_on_its_own_is_not_an_edit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = self._committed(tmp_path, monkeypatch, '2026-10-02 00:00 UTC')
        page.write_text(
            '---\ncreated: 2026-10-01 00:00 UTC\n'
            'modified: 2026-10-01 00:00 UTC\n---\n# One\n\nAs committed.\n',
            encoding='utf-8',
        )
        check_wiki._uncommitted_pages.cache_clear()

        assert self._complaints(page) == []

    @_NEEDS_BASELINE
    def test_a_rewritten_page_still_has_to_be_restamped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page = self._committed(tmp_path, monkeypatch, '2026-10-01 00:00 UTC')
        page.write_text(
            '---\ncreated: 2026-10-01 00:00 UTC\n'
            'modified: 2026-10-01 00:00 UTC\n---\n# One\n\nSaid again.\n',
            encoding='utf-8',
        )
        check_wiki._uncommitted_pages.cache_clear()

        assert any(
            'holds an edit that is not yet committed' in note
            for note in self._complaints(page)
        )


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
    def test_a_committed_file_has_a_stamp(self) -> None:
        held = check_wiki._last_commit_stamp(check_wiki.CHANGELOG)

        assert held is not None
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC', held)

    def test_a_file_outside_the_tree_has_none(self, tmp_path: Path) -> None:
        held = tmp_path / 'nowhere.md'
        held.write_text('# Nowhere\n', encoding='utf-8')

        assert check_wiki._last_commit_stamp(held) is None


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


class TestHowTheIndexGroups:
    @staticmethod
    def _held(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, heading: str,
    ) -> list[str]:
        register = tmp_path / 'register.md'
        register.write_text(
            '# The register\n\n## Package 1\n\n## Package 2 — the vocabulary\n',
            encoding='utf-8',
        )
        readme = tmp_path / 'README.md'
        readme.write_text(
            f'# How it works\n\n{heading}\n\n- [One](atoms/one.md) — a thing.\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'REGISTER', register)
        monkeypatch.setattr(check_wiki, 'README', readme)
        held: list[str] = check_wiki._index_sections()

        return held

    def test_a_section_named_after_a_package_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(tmp_path, monkeypatch, '## The vocabulary')

        assert any('register package' in note for note in held), held

    def test_a_section_named_for_its_subject_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(tmp_path, monkeypatch, '## The words a reader needs')

        assert held == []


class TestHowACountIsRead:

    @pytest.mark.parametrize(
        'written',
        [
            '120 articles exist.',
            'Of these, 120\narticles exist.',
            'Of these, 120\n   articles exist.',
        ],
    )
    def test_a_count_is_read_across_a_wrap(self, written: str) -> None:
        found = check_wiki.ARTICLE_COUNT_RE.search(written)

        assert found is not None, written
        assert found.group(1) == '120'

    @pytest.mark.parametrize(
        'pattern, written, number',
        [
            (
                'STATE_COUNT_RE',
                '46 are `full`, 38\n`partial` and 4 `uncovered`',
                '46',
            ),
            ('NEXUS_COUNT_RE', '21 are\nnamed', '21'),
            ('NEXUS_OWNED_RE', '12 carry a\nrow', '12'),
            ('NEXUS_OWNED_ALT_RE', 'The other 12\ncarry a row', '12'),
            ('NEXUS_CITED_ALT_RE', '9 of the\nmodules listed', '9'),
            ('NEXUS_UNOWNED_RE', 'The 9 with\nno row', '9'),
            ('NEXUS_CITED_RE', '9 are reached by\nan', '9'),
            ('NEXUS_TOTAL_RE', 'the 70\nin Nexus', '70'),
            ('NEXUS_UNTOUCHED_RE', '49\nuntouched', '49'),
            (
                'EVIDENCE_COUNT_RE',
                '2,474 line references\nacross 1,293 claims',
                '2,474',
            ),
            ('FINDING_COUNT_RE', 'Record 70\nfindings', '70'),
            (
                'LINE_COUNT_RE',
                '`execution_manager.py`, at 10,899\nlines',
                'execution_manager.py',
            ),
        ],
    )
    def test_every_count_is_read_across_a_wrap(
        self, pattern: str, written: str, number: str,
    ) -> None:
        found = getattr(check_wiki, pattern).search(written)

        assert found is not None, written
        assert found.group(1) == number

    def test_a_count_of_something_else_is_left_alone(self) -> None:
        assert check_wiki.ARTICLE_COUNT_RE.search('12 articled pages') is None


class TestWhichWordCarriesATerm:

    @staticmethod
    def _held(
        page: str, body: str, monkeypatch: pytest.MonkeyPatch,
    ) -> list[str]:
        monkeypatch.setattr(
            check_wiki, 'OWNED_TERMS', {'the-order-book.md': ('order book',)},
        )
        held: list[str] = check_wiki._unlinked_terms(Path(page), body)

        return held

    def test_a_longer_word_is_not_the_term(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            'one.md', 'A name an order booked under is refused.\n', monkeypatch,
        )

        assert held == []

    def test_the_term_itself_still_wants_its_link(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held('one.md', 'The order book is read.\n', monkeypatch)

        assert any('order book' in note for note in held), held

    def test_the_term_linked_where_it_is_met_stands(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            'one.md', 'The [order book](the-order-book.md) is read.\n', monkeypatch,
        )

        assert held == []

    def test_a_term_carried_across_a_wrap_still_wants_its_link(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held('one.md', 'The order\nbook is read.\n', monkeypatch)

        assert any('order book' in note for note in held), held

    def test_a_term_wrapped_inside_its_link_stands(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            'one.md', 'The [order\nbook](the-order-book.md) is read.\n', monkeypatch,
        )

        assert held == []

class TestWhatARowsStateMeans:

    @staticmethod
    def _held(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        rows: str,
        index: str = '# How it works\n',
    ) -> list[str]:
        register = tmp_path / 'register.md'
        register.write_text(rows, encoding='utf-8')
        readme = tmp_path / 'README.md'
        readme.write_text(index, encoding='utf-8')
        monkeypatch.setattr(check_wiki, 'REGISTER', register)
        monkeypatch.setattr(check_wiki, 'README', readme)
        held: list[str] = check_wiki._review_states()

        return held

    def test_the_two_states_stand(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        rows = (
            '| P1-01 | One | written | [a](atoms/a.md) |\n'
            '| P1-02 | Two | reviewed | [b](atoms/b.md) |\n'
            '**1 of them reviewed, 1 not.**\n'
        )

        assert self._held(tmp_path, monkeypatch, rows) == []

    @pytest.mark.parametrize(
        ('said', 'quoted'),
        [
            pytest.param(
                '**9 of them reviewed, 1 not.**', '9 of them reviewed, 1 not',
                id='the-reviewed-count-adrift',
            ),
            pytest.param(
                '**1 of them reviewed, 9 not.**', '1 of them reviewed, 9 not',
                id='the-unreviewed-count-adrift',
            ),
        ],
    )
    def test_either_count_adrift_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        said: str, quoted: str,
    ) -> None:
        rows = (
            '| P1-01 | One | written | [a](atoms/a.md) |\n'
            '| P1-02 | Two | reviewed | [b](atoms/b.md) |\n'
            f'{said}\n'
        )
        held = self._held(tmp_path, monkeypatch, rows)

        assert any(quoted in note for note in held), held

    def test_a_word_running_on_from_not_is_not_the_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        rows = (
            '| P1-01 | One | written | [a](atoms/a.md) |\n'
            '| P1-02 | Two | reviewed | [b](atoms/b.md) |\n'
            '**9 of them reviewed, 9 notes.**\n'
        )

        assert self._held(tmp_path, monkeypatch, rows) == []

    @pytest.mark.parametrize(
        'state', ['done', 'Reviewed', 'REVIEWED', 'in-review', ' '],
        ids=['a-word', 'capitalised', 'shouted', 'hyphenated', 'nothing'],
    )
    def test_any_other_word_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str,
    ) -> None:
        rows = (
            f'| P1-01 | One | {state} | [a](atoms/a.md) |\n'
            '**0 of them reviewed, 1 not.**\n'
        )
        held = self._held(tmp_path, monkeypatch, rows)

        assert any('neither written nor reviewed' in note for note in held), held

    def test_a_count_on_the_index_is_read_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        rows = (
            '| P1-01 | One | written | [a](atoms/a.md) |\n'
            '**0 of them reviewed, 1 not.**\n'
        )
        held = self._held(
            tmp_path, monkeypatch, rows,
            index='**9 of them reviewed, 9 not.**\n',
        )

        assert any('9 of them reviewed' in note for note in held), held

    def test_a_count_disagreeing_with_the_table_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        rows = (
            '| P1-01 | One | written | [a](atoms/a.md) |\n'
            '**1 of them reviewed, 0 not.**\n'
        )
        held = self._held(tmp_path, monkeypatch, rows)

        assert any('against 0 reviewed and 1 not' in note for note in held), held

    def test_a_register_stating_no_count_is_left_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        rows = '| P1-01 | One | written | [a](atoms/a.md) |\n'

        assert self._held(tmp_path, monkeypatch, rows) == []


class TestWhichVersionWasReviewed:

    @staticmethod
    def _held(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, stamps: str,
    ) -> list[str]:
        atoms = tmp_path / 'atoms'
        atoms.mkdir()
        (atoms / 'a.md').write_text(
            f'---\nrow: N1-01\nbaseline: 49aa659\n'
            f'created: 2026-10-01 00:00 UTC\n{stamps}'
            'evidence:\n  - claim: "A thing"\n    source: "`a.py` 1"\n'
            '---\n# A\n\nProse.\n',
            encoding='utf-8',
        )
        register = tmp_path / 'register.md'
        register.write_text(
            f'| N1-01 | A | {state} | [a.md](atoms/a.md) |\n', encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'REGISTER', register)
        monkeypatch.setattr(check_wiki, 'WIKI', tmp_path)
        held: list[str] = check_wiki._reviewed_versions()

        return held

    def test_a_written_row_needs_no_version(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            tmp_path, monkeypatch, 'written', 'modified: 2026-10-02 00:00 UTC\n',
        )

        assert held == []

    def test_a_reviewed_row_naming_no_version_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            tmp_path, monkeypatch, 'reviewed', 'modified: 2026-10-02 00:00 UTC\n',
        )

        assert any('names no version reviewed' in note for note in held), held

    def test_a_review_older_than_the_article_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            tmp_path, monkeypatch, 'reviewed',
            'modified: 2026-10-02 00:00 UTC\nreviewed: 2026-10-01 00:00 UTC\n',
        )

        assert any('no longer covers it' in note for note in held), held

    def test_a_review_of_what_is_there_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            tmp_path, monkeypatch, 'reviewed',
            'modified: 2026-10-02 00:00 UTC\nreviewed: 2026-10-02 00:00 UTC\n',
        )

        assert held == []

    def test_a_reviewed_row_naming_no_change_at_all_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            tmp_path, monkeypatch, 'reviewed', 'reviewed: 2026-10-02 00:00 UTC\n',
        )

        assert any('no version at all' in note for note in held), held

    def test_a_review_newer_than_the_article_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held = self._held(
            tmp_path, monkeypatch, 'reviewed',
            'modified: 2026-10-02 00:00 UTC\nreviewed: 2026-10-03 00:00 UTC\n',
        )

        assert any('never existed' in note for note in held), held

    def test_a_reviewed_row_whose_article_is_gone_is_passed_over(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        register = tmp_path / 'register.md'
        register.write_text(
            '| N1-01 | A | reviewed | [a.md](atoms/a.md) |\n', encoding='utf-8',
        )
        monkeypatch.setattr(check_wiki, 'REGISTER', register)
        monkeypatch.setattr(check_wiki, 'WIKI', tmp_path)

        assert check_wiki._reviewed_versions() == []


class TestWhatASpineProves:

    @staticmethod
    def _spine(tmp_path: Path, meta: str) -> list[str]:
        spines = tmp_path / 'spines'
        spines.mkdir()
        page = spines / 'a-route.md'
        page.write_text(
            f'---\n{meta}---\n# A route\n\n'
            '1. A step — [One](../atoms/one.md).\n',
            encoding='utf-8',
        )

        return check_wiki._evidence_rows(
            check_wiki._split_front_matter(page.read_text(encoding='utf-8'))[0],
        )

    def test_a_spine_carrying_evidence_has_rows(self, tmp_path: Path) -> None:
        meta = (
            'row: S-01\nbaseline: 49aa659\n'
            'created: 2026-10-15 00:00 UTC\nmodified: 2026-10-15 00:00 UTC\n'
            'evidence:\n'
            '  - claim: "One thing happens before another"\n'
            '    source: "`trading.py` 1 before 2"\n'
        )

        assert self._spine(tmp_path, meta)

    def test_a_spine_carrying_none_has_no_rows(self, tmp_path: Path) -> None:
        meta = (
            'row: S-01\nbaseline: 49aa659\n'
            'created: 2026-10-15 00:00 UTC\nmodified: 2026-10-15 00:00 UTC\n'
        )

        assert self._spine(tmp_path, meta) == []

    def test_a_spine_row_is_a_row_identifier(self) -> None:
        assert check_wiki.ROW_ID.fullmatch('S-01')
        assert check_wiki.ROW_ID.fullmatch('P4-58')

    def test_the_register_reads_a_spine_row(self) -> None:
        row = (
            '| S-02 | A route | written | '
            '[a-route.md](spines/a-route.md) |'
        )

        assert check_wiki.REGISTER_ROW_RE.findall(row) == [
            ('S-02', 'spines/a-route.md'),
        ]

    def test_the_index_reads_a_spine_link(self) -> None:
        found = check_wiki.ARTICLE_LINK_RE.findall('- [A](spines/a-route.md)')

        assert found == ['spines/a-route.md']


class TestHowASpineIsOwned:

    @pytest.mark.parametrize(
        'body, expected',
        [
            (
                '1. First [One](../atoms/one.md).\n\n2. Then [Two](../atoms/two.md).\n',
                [],
            ),
            (
                '1. First, and the owner is\n   [One](../atoms/one.md).\n',
                [],
            ),
        ],
    )
    def test_a_sequence_of_owned_steps_stands(
        self, body: str, expected: list[str],
    ) -> None:
        assert check_wiki._spine_steps(body) == expected

    def test_a_step_naming_no_article_is_refused(self) -> None:
        body = '1. First [One](../atoms/one.md).\n\n2. Then it is dropped.\n'
        held = check_wiki._spine_steps(body)

        assert any('step 2 says' in note for note in held), held

    def test_a_step_linking_off_the_articles_is_refused(self) -> None:
        held = check_wiki._spine_steps('1. First [Elsewhere](../README.md).\n')

        assert any('step 1 says' in note for note in held), held

    def test_a_link_under_a_later_heading_does_not_own_a_step(self) -> None:
        body = (
            '1. It drops every order.\n\n'
            '## Related\n\n'
            '[One](../atoms/one.md)\n'
        )
        held = check_wiki._spine_steps(body)

        assert any('step 1 says' in note for note in held), held

    def test_a_second_sentence_riding_on_the_first_link_is_refused(self) -> None:
        body = '1. It drops them — [One](../atoms/one.md). It also waits.\n'
        held = check_wiki._spine_steps(body)

        assert any('names no article for it' in note for note in held), held

    def test_each_sentence_naming_its_own_article_stands(self) -> None:
        body = (
            '1. It drops them — [One](../atoms/one.md). '
            'It waits — [Two](../atoms/two.md).\n'
        )

        assert check_wiki._spine_steps(body) == []

    def test_a_trailing_run_of_links_needs_no_owner(self) -> None:
        body = '1. It drops them — [One](../atoms/one.md), [Two](../atoms/two.md).\n'

        assert check_wiki._spine_steps(body) == []

    def test_a_bold_label_needs_no_owner_of_its_own(self) -> None:
        body = '1. **Arm one.** It drops them — [One](../atoms/one.md).\n'

        assert check_wiki._spine_steps(body) == []

    def test_a_setext_heading_closes_a_step(self) -> None:
        body = (
            '1. It drops every order.\n\n'
            'Related\n'
            '-------\n\n'
            '[One](../atoms/one.md)\n'
        )
        held = check_wiki._spine_steps(body)

        assert any('step 1 says' in note for note in held), held

    def test_a_bullet_asserting_a_route_alone_is_refused(self) -> None:
        body = (
            '1. A [One](../atoms/one.md).\n\n'
            '- A host stopping does it differently.\n'
        )
        held = check_wiki._spine_steps(body)

        assert any('names no article' in note for note in held), held

    def test_a_bullet_naming_its_article_stands(self) -> None:
        body = (
            '1. A [One](../atoms/one.md).\n\n'
            '- Not here — [Two](../atoms/two.md).\n'
        )

        assert check_wiki._spine_steps(body) == []

    def test_a_page_with_no_route_is_refused(self) -> None:
        held = check_wiki._spine_steps('# A spine\n\nProse and [One](../atoms/one.md).\n')

        assert held == ['carries no numbered route']

    def test_a_lost_step_is_refused(self) -> None:
        body = '1. First [One](../atoms/one.md).\n\n3. Then [Two](../atoms/two.md).\n'
        held = check_wiki._spine_steps(body)

        assert any('numbered 1, 3' in note for note in held), held




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


class TestWhatAHandlerNothingArrivesAtCosts:

    @staticmethod
    def _landed(
        source: str, start: int, end: int,
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> str | None:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        facts = check_wiki._SourceFacts().of('sample.py', path)
        held: str | None = check_wiki._what_a_citation_lands_on(
            start, end, facts, 'a claim',
        )

        return held

    def test_a_handler_an_earlier_one_covers_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        work()\n'
            '    except LookupError:\n        held = 3\n'
            '    except KeyError:\n        held = 4\n    return 5\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_the_except_line_of_a_handler_covered_earlier_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        work()\n'
            '    except LookupError:\n        held = 3\n'
            '    except KeyError:\n        held = 4\n    return 5\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held is None

    def test_the_except_line_of_a_live_handler_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        work()\n'
            '    except LookupError:\n        held = 3\n'
            '    except KeyError:\n        held = 4\n    return 5\n'
        )
        held = self._landed(source, 4, 5, tmp_path, monkeypatch)

        assert held is None

    def test_the_except_line_of_a_handler_tried_and_missed_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 4, 4, tmp_path, monkeypatch)

        assert held is None

    def test_the_body_of_a_handler_tried_and_missed_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_the_except_line_of_a_handler_nothing_reaches_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        pass\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 4, 4, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_handler_after_one_naming_every_error_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(impossible):\n    try:\n        raise ValueError()\n'
            '    except BaseException:\n        pass\n'
            '    except KeyError:\n        impossible()\n    return 1\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_citation_taking_in_a_missed_handler_whole_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 4, 5, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_citation_of_the_whole_try_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 2, 6, tmp_path, monkeypatch)

        assert held is None

    def test_a_kind_worked_out_after_a_catch_all_reaches_no_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(work, boom, dead):\n    try:\n        try:\n'
            '            work()\n'
            '        except BaseException:\n            return 1\n'
            '        except boom():\n            return 2\n'
            '    except KeyError:\n        dead()\n    return 3\n'
        )
        held = self._landed(source, 10, 10, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_the_except_line_after_one_naming_every_error_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(impossible):\n    try:\n        raise ValueError()\n'
            '    except BaseException:\n        pass\n'
            '    except KeyError:\n        impossible()\n    return 1\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_protocol_imported_under_an_error_name_is_weighed_against_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'from typing import Protocol as ValueError\n\n\n'
            'def f():\n    try:\n        raise ValueError()\n'
            '    except TypeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_a_type_alias_takes_is_weighed_against_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'type ValueError = int\n\n\ndef f(flag, mark, after):\n    if flag:\n'
            '        mark()\n        try:\n            raise ValueError()\n'
            '        except TypeError:\n            pass\n    after()\n'
        )
        held = self._landed(source, 10, 10, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_a_type_parameter_takes_is_weighed_against_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f[ValueError](flag, mark, after):\n    if flag:\n'
            '        mark()\n        try:\n            raise ValueError()\n'
            '        except TypeError:\n            pass\n    after()\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held is None

    def test_the_same_shapes_under_the_builtin_are_weighed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag, mark, after):\n    if flag:\n'
            '        mark()\n        try:\n            raise ValueError()\n'
            '        except TypeError:\n            pass\n    after()\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_name_declared_inside_a_function_is_weighed_against_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    ValueError: type\n    try:\n'
            '        raise ValueError()\n'
            "    except UnboundLocalError:\n        return 'runs'\n"
            "    except ValueError:\n        return 'never'\n"
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_declared_in_a_class_inside_a_function_is_weighed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    class Held:\n        ValueError: type\n    try:\n'
            '        raise ValueError()\n'
            '    except TypeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_an_ordinary_handler_after_one_that_caught_loses_its_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except ValueError:\n        held = 1\n'
            '    except KeyError:\n        held = 2\n    return 3\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_grouped_handler_after_a_catch_all_keeps_its_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except* BaseException:\n        pass\n'
            '    except* missing:\n        pass\n    return 1\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held is None

    def test_a_kind_worked_out_past_a_grouped_catch_all_reaches_the_handlers_round_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(boom):\n    try:\n        try:\n            raise ValueError()\n'
            '        except* BaseException:\n            pass\n'
            '        except* boom():\n            pass\n'
            '    except RuntimeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 10, 10, tmp_path, monkeypatch)

        assert held is None

    def test_a_grouped_handler_naming_a_group_reaches_nothing_after_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    held = 0\n    try:\n        raise KeyError()\n'
            '    except* ExceptionGroup:\n        held = 3\n'
            '    except* KeyError:\n        held = 2\n    return held\n'
        )
        held = self._landed(source, 7, 8, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    @pytest.mark.parametrize(
        ('named', 'line'),
        [
            pytest.param('ExceptionGroup', 5, id='the-group'),
            pytest.param('BaseExceptionGroup', 5, id='the-other-group'),
            pytest.param('(ValueError, ExceptionGroup)', 5, id='a-group-in-a-tuple'),
        ],
    )
    def test_every_group_a_grouped_handler_can_name_stops_it(
        self, named: str, line: int,
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(work):\n    try:\n        work()\n'
            f'    except* {named}:\n        held = 3\n    return 1\n'
        )
        held = self._landed(source, line, line, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_group_the_file_binds_again_stops_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class Boom(ExceptionGroup):\n    pass\n\n\nBoom = ValueError\n\n\n'
            'def f():\n    try:\n        raise ValueError()\n'
            '    except* Boom:\n        held = 3\n    return 1\n'
        )
        held = self._landed(source, 12, 12, tmp_path, monkeypatch)

        assert held is None

    def test_a_group_the_file_writes_stops_it_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class Boom(ExceptionGroup):\n    pass\n\n\ndef f(work):\n    try:\n'
            '        work()\n    except* Boom:\n        held = 3\n    return 1\n'
        )
        held = self._landed(source, 9, 9, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_an_ordinary_kind_in_a_grouped_handler_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(work):\n    try:\n        work()\n'
            '    except* ValueError:\n        held = 3\n    return 1\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_bound_inside_an_if_is_the_scope_s_own(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    if True:\n        ValueError = TypeError\n    try:\n'
            '        raise ValueError()\n    except TypeError:\n        return 1\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held is None

    def test_a_group_name_a_parameter_holds_is_no_group(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(ExceptionGroup):\n    try:\n        raise ValueError()\n'
            '    except* ExceptionGroup:\n        result = 1\n    return result\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_a_method_takes_leaves_another_function_weighed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class C:\n    def m(self, ValueError):\n        return 1\n\n\n'
            "def f():\n    try:\n        raise ValueError('x')\n"
            '    except TypeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 10, 10, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_class_body_name_is_no_part_of_its_methods(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class C:\n    ValueError = TypeError\n\n'
            '    def m(self):\n        try:\n'
            "            raise ValueError('x')\n"
            '        except TypeError:\n            return 2\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_class_body_name_is_no_part_of_a_class_inside_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class C:\n    ValueError = TypeError\n\n    class D:\n        try:\n'
            "            raise ValueError('x')\n"
            '        except TypeError:\n            held = 2\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_function_name_is_read_inside_a_function_it_holds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    ValueError = TypeError\n\n    def g():\n        try:\n'
            "            raise ValueError('x')\n"
            '        except TypeError:\n            return 2\n\n    return g\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_a_class_body_takes_holds_inside_that_body(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class C:\n    ValueError = TypeError\n    try:\n'
            "        raise ValueError('x')\n"
            '    except TypeError:\n        held = 2\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held is None

    def test_a_group_base_the_module_rebinds_makes_no_group(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'ExceptionGroup = ValueError\n\n\nclass Boom(ExceptionGroup):\n'
            '    pass\n\n\ndef f(work):\n    try:\n        work()\n'
            '    except* Boom:\n        held = 3\n    return 1\n'
        )
        held = self._landed(source, 12, 12, tmp_path, monkeypatch)

        assert held is None

    def test_a_group_name_the_module_rebinds_is_no_group(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'ExceptionGroup = ValueError\n\n\ndef f(work):\n    try:\n'
            '        work()\n    except* ExceptionGroup:\n'
            '        held = 3\n    return 1\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held is None

    def test_a_group_written_under_the_language_s_own_name_is_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class ExceptionGroup(BaseExceptionGroup):\n    pass\n\n\n'
            'def f(work):\n    try:\n        work()\n'
            '    except* ExceptionGroup:\n        held = 3\n    return 1\n'
        )
        held = self._landed(source, 9, 9, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_name_assigned_in_a_class_body_is_that_class_s_own(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class C:\n    ValueError = int\n\n\ndef f():\n    try:\n'
            "        raise ValueError('x')\n"
            '    except TypeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 9, 9, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_the_body_of_a_handler_naming_a_group_cannot_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(work):\n    held = 0\n    try:\n        work()\n'
            '    except* ExceptionGroup:\n        held = 3\n'
            '    except* KeyError:\n        held = 2\n    return held\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_that_groups_own_line_still_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    held = 0\n    try:\n        raise KeyError()\n'
            '    except* ExceptionGroup:\n        held = 3\n'
            '    except* KeyError:\n        held = 2\n    return held\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held is None

    def test_a_type_written_in_a_class_body_is_that_class_s_own(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'class C:\n    type ValueError = int\n\n\ndef f():\n    try:\n'
            "        raise ValueError('x')\n"
            '    except TypeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 9, 9, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_body_sharing_the_handler_line_is_kept_with_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except TypeError: pass\n'
            '    except ValueError: pass\n    return 1\n'
        )
        held = self._landed(source, 4, 4, tmp_path, monkeypatch)

        assert held is None

    def test_a_body_sharing_the_line_of_a_handler_nothing_reaches_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        pass\n'
            '    except TypeError: pass\n    return 1\n'
        )
        held = self._landed(source, 4, 4, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_an_ordinary_handler_after_a_catch_all_loses_its_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except BaseException:\n        pass\n'
            '    except KeyError:\n        pass\n    return 1\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_grouped_handler_after_one_that_caught_keeps_its_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except* ValueError:\n        held = 1\n'
            '    except* KeyError:\n        held = 2\n    return 3\n'
        )
        held = self._landed(source, 6, 6, tmp_path, monkeypatch)

        assert held is None

    def test_that_grouped_handlers_body_is_still_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError()\n'
            '    except* ValueError:\n        held = 1\n'
            '    except* KeyError:\n        held = 2\n    return 3\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_name_carrying_only_a_type_is_weighed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'ValueError: int\n\n\ndef f():\n    try:\n'
            '        raise ValueError()\n'
            '    except TypeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_name_given_a_value_with_its_type_is_weighed_against_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'ValueError: int = 1\n\n\ndef f():\n    try:\n'
            '        raise ValueError()\n'
            '    except TypeError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_the_file_deletes_is_weighed_against_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError\n'
            '    except UnboundLocalError:\n        return 2\n'
            '    del ValueError\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held is None

    def test_the_same_shape_without_the_deletion_is_weighed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise ValueError\n'
            '    except UnboundLocalError:\n        return 2\n    return 1\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_file_with_a_wildcard_import_weighs_no_kind(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'from provider import *\n\n\ndef f():\n    try:\n'
            '        raise ValueError()\n    except KeyError:\n'
            '        held = 1\n    return 2\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held is None

    def test_the_same_file_without_one_weighs_its_kinds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'from provider import held_elsewhere\n\n\ndef f():\n    try:\n'
            '        raise ValueError()\n    except KeyError:\n'
            '        held = 1\n    return 2\n'
        )
        held = self._landed(source, 8, 8, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_kind_the_file_took_over_could_raise_as_it_is_matched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(ValueError):\n    try:\n        try:\n'
            '            raise KeyError()\n'
            '        except ValueError:\n            pass\n'
            '        except BaseException:\n            pass\n'
            '    except TypeError:\n        return 42\n    return 1\n'
        )
        held = self._landed(source, 10, 10, tmp_path, monkeypatch)

        assert held is None

    def test_a_dead_handler_padded_with_a_blank_line_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        pass\n'
            '    except KeyError:\n        held = 1\n'
            '\n    return 2\n'
        )
        held = self._landed(source, 4, 6, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_range_running_out_of_a_dead_handler_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        pass\n'
            '    except KeyError:\n        held = 1\n'
            '\n    return 2\n'
        )
        held = self._landed(source, 4, 7, tmp_path, monkeypatch)

        assert held is None

    def test_an_error_name_the_file_takes_over_is_weighed_against_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag, ValueError):\n    if flag:\n        try:\n'
            '            assert True\n            raise ValueError()\n'
            '        except KeyError:\n            pass\n    return 42\n'
        )
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert spans == []
        assert held is None

    def test_a_handler_naming_a_name_the_file_takes_over_stays_live(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(work, KeyError):\n    try:\n        work()\n'
            '    except LookupError:\n        held = 1\n'
            '    except (LookupError, KeyError):\n        held = 2\n    return 3\n'
        )
        held = self._landed(source, 6, 7, tmp_path, monkeypatch)

        assert held is None

    def test_a_name_the_file_takes_over_covers_no_later_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(work, LookupError):\n    try:\n        work()\n'
            '    except LookupError:\n        held = 1\n'
            '    except KeyError:\n        held = 2\n    return 3\n'
        )
        held = self._landed(source, 6, 7, tmp_path, monkeypatch)

        assert held is None

    def test_the_same_shape_under_the_language_s_own_error_is_weighed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag):\n    if flag:\n        try:\n'
            '            assert True\n            raise ValueError()\n'
            '        except KeyError:\n            pass\n    return 42\n'
        )
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert any(3 in first and 8 in second for first, second in spans), spans
        assert held == 'a handler nothing arrives at'

    def test_a_handler_the_earlier_one_leaves_alone_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        work()\n'
            '    except KeyError:\n        held = 3\n'
            '    except LookupError:\n        held = 4\n    return 5\n'
        )
        held = self._landed(source, 7, 7, tmp_path, monkeypatch)

        assert held is None

    def test_a_handler_of_a_try_that_raises_nothing_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        held = 1\n'
            '    except KeyError:\n        held = 2\n    return 3\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_handler_for_an_asserts_own_error_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        assert 2 < 1\n'
            '    except AssertionError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held is None

    def test_a_handler_an_assert_cannot_reach_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        assert 2 < 1\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_a_handler_for_an_assert_that_always_holds_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        assert 1 < 2\n'
            '    except AssertionError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_an_assert_whose_message_could_raise_reaches_any_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(why):\n    try:\n        assert 2 < 1, why\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held is None

    def test_an_assert_that_holds_never_works_its_message_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(why):\n    try:\n        assert 1 < 2, why\n'
            '    except KeyError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held == 'a handler nothing arrives at'

    def test_an_arm_ending_in_an_assert_that_holds_can_carry_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag, step, later):\n    if flag:\n        step()\n'
            '        assert 1 < 2\n    later()\n'
        )
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        assert spans == []

    def test_an_arm_ending_in_an_assert_that_never_holds_leaves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag, step, later):\n    if flag:\n        step()\n'
            '        assert 2 < 1\n    later()\n'
        )
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        assert any(3 in first and 5 in second for first, second in spans), spans

    def test_a_handler_a_bare_raise_could_reach_stands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f():\n    try:\n        raise\n'
            '    except RuntimeError:\n        held = 1\n    return 2\n'
        )
        held = self._landed(source, 5, 5, tmp_path, monkeypatch)

        assert held is None

    def test_an_arm_whose_bare_raise_is_caught_is_no_alternative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = (
            'def f(flag, mark, after):\n    if flag:\n        mark()\n        try:\n'
            '            raise\n        except RuntimeError:\n'
            '            pass\n    after()\n'
        )
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)
        spans: list[tuple[set[int], set[int]]] = check_wiki._exclusive_spans(path)

        assert spans == []

class TestSettledCandidates:

    @staticmethod
    def _settled_as(tmp_path: Path, disposition: str) -> Path:

        '''Write a register whose one candidate a merge row disposes of.

        Args:
            tmp_path (Path): Where to write the register
            disposition (str): What the merge row says became of the row

        Returns:
            Path: The register written
        '''

        return _a_register(
            tmp_path,
            f'| {_SYNTHETIC_ROW} | `order.py` 1 | a finding | read | candidate |\n'
            f'| Row {_SYNTHETIC_ROW} | P1-01 | {disposition} |\n',
            'settled-register.md',
        )

    def test_no_row_reads_candidate_after_it_was_settled(self) -> None:
        assert check_wiki._settled_candidates() == []

    def test_a_stale_candidate_is_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        staled = self._settled_as(tmp_path, 'Promote. It stands alone')
        monkeypatch.setattr(check_wiki, 'REGISTER', staled)
        failures = check_wiki._settled_candidates()

        assert len(failures) == 1
        assert failures[0].startswith(
            f'{staled}: {_SYNTHETIC_ROW} reads `candidate`',
        )

    @pytest.mark.parametrize('settling', ['Promote.', 'Merge with H-9002.',
                                          'Folds into H-9002.', 'Decline.'])
    def test_every_settling_word_is_read(
        self, settling: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        staled = self._settled_as(tmp_path, settling)
        monkeypatch.setattr(check_wiki, 'REGISTER', staled)

        assert len(check_wiki._settled_candidates()) == 1

    def test_a_row_queued_as_its_own_candidate_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        queued = self._settled_as(tmp_path, 'Candidate, to be seeded')
        monkeypatch.setattr(check_wiki, 'REGISTER', queued)

        assert check_wiki._settled_candidates() == []
