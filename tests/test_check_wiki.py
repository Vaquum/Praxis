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
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_wiki.py'
_STUB = '''    def m(
        self,
    ) -> int:
        ...
'''


def _load() -> ModuleType:
    '''Load the gate as a module, it being a script rather than a package.

    Returns:
        ModuleType: The loaded `check_wiki` module.
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
    def _spans(source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)

        return check_wiki._exclusive_spans(path)

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
        assert any(2 in first and 9 in second for first, second in spans)

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
        assert notes == ['order.py:16 (blank line)']

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

    def test_an_absence_claim_still_needs_the_file_to_exist(self) -> None:
        row = 'a claim | `order.py` 30, with nothing further in `nonesuch.py`'
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
    def _spans(source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list:
        path = tmp_path / 'sample.py'
        path.write_text(source)
        monkeypatch.setattr(check_wiki, '_source_text', lambda _p: source)

        return check_wiki._exclusive_spans(path)

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
@pytest.mark.skipif(
    not (check_wiki.NEXUS_ROOT / '.git').exists(),
    reason='the gate resolves citations in both repositories, and Nexus is absent',
)
class TestTheWikiItself:
    def test_the_gate_passes(self) -> None:
        assert check_wiki.main() == 0
