'''
Tests for scripts.check_wiki.

Each check in the wiki gate was added after a defect of its kind reached a
finished article. These lock every one of them by presenting the defect and
asserting the refusal, so a check that stops refusing fails here.
'''

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_wiki.py'
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

    def test_a_blank_line_is_refused(self) -> None:
        notes = check_wiki._docstring_citations(
            '|a claim | `order.py` 16|', check_wiki._SourceFacts(),
        )
        assert notes == ['order.py:16 (no executable line)']

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
                'from typing import Protocol\nProtocol, other = object, None\n'
                'class A(Protocol):\n' + _STUB,
                id='unpacking',
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
    def test_a_lead_opening_with_this_is_refused(self) -> None:
        assert check_wiki._check_voice('# Title\n\nThis is about orders.\n')

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

    def test_an_article_named_by_two_rows_is_caught(self) -> None:
        rows = check_wiki._rows_per_article(
            [('P1-01', 'atoms/one.md'), ('P1-02', 'atoms/one.md')],
        )
        assert rows['atoms/one.md'] == ['P1-01', 'P1-02']

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
        assert notes == [
            'praxis/core/domain/trade_outcome.py:6-7 (no executable line)',
        ]


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
    def test_a_full_module_with_a_candidate_is_caught(self) -> None:
        failures = check_wiki._open_candidates(
            {'praxis/core/health_tracker.py': {'H-064'}},
        )
        assert failures == [
            "docs/wiki/ledger.md: `praxis/core/health_tracker.py` is `full` "
            "while ['H-064'] name it a candidate",
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


class TestThePinnedTable:

    def test_the_table_names_the_commits_that_are_read(self) -> None:
        assert check_wiki._pinned_table() == []

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
