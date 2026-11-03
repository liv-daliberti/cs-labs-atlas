"""identity_rule.judge_meta: the PDF's own title metadata as identity evidence (ROADMAP #25)."""
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
import identity_rule as R  # noqa: E402

TITLE = 'Efficient Estimation of Word Representations in Vector Space'


def test_matching_metadata_title_with_the_author_on_page_one_passes():
    v, ev = R.judge_meta('Efficient Estimation of Word Representations in Vector Space', [TITLE], 'Tomas Mikolov Kai Chen ...' * 5, 'mikolov', None)
    assert v == 'pass_meta' and ev['known_in_meta'] == 1.0


def test_no_author_or_doi_on_page_one_is_not_a_pass():
    assert R.judge_meta(TITLE, [TITLE], 'Someone Else wrote this page', 'mikolov', None)[0] == 'undecided'


def test_a_generic_or_short_metadata_title_never_passes():
    for meta in ('Microsoft Word - paper.doc', 'Untitled', 'Vector Space', ''):
        assert R.judge_meta(meta, [TITLE], 'Mikolov', 'mikolov', None)[0] == 'undecided'


def test_a_metadata_title_with_extra_words_needs_to_be_mostly_the_known_title():
    assert R.judge_meta('Word Representations in Vector Space: proceedings front matter volume cover', [TITLE], 'Mikolov', 'mikolov', None)[0] == 'undecided'
