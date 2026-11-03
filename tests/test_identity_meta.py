"""identity_rule.judge_meta: the PDF's own title metadata as identity evidence (ROADMAP #25)."""
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
import identity_rule as R  # noqa: E402

TITLE = 'Efficient Estimation of Word Representations in Vector Space'


def test_matching_metadata_title_with_the_author_on_page_one_passes():
    v, ev = R.judge_meta('Efficient Estimation of Word Representations in Vector Space', [TITLE], TITLE + ' Tomas Mikolov Kai Chen', 'mikolov', None)
    assert v == 'pass_meta' and ev['known_in_meta'] == 1.0


def test_no_author_or_doi_on_page_one_is_not_a_pass():
    assert R.judge_meta(TITLE, [TITLE], TITLE + ' Someone Else wrote this page', 'mikolov', None)[0] == 'undecided'


def test_a_generic_or_short_metadata_title_never_passes():
    for meta in ('Microsoft Word - paper.doc', 'Untitled', 'Vector Space', ''):
        assert R.judge_meta(meta, [TITLE], 'Mikolov', 'mikolov', None)[0] == 'undecided'


def test_a_metadata_title_with_extra_words_needs_to_be_mostly_the_known_title():
    assert R.judge_meta('Word Representations in Vector Space: proceedings front matter volume cover', [TITLE], 'Mikolov', 'mikolov', None)[0] == 'undecided'


def test_the_metadata_title_must_be_the_title_on_page_one():
    # hand check 2026-11-02: reused metadata (equal to the catalog title) on another paper must not pass
    meta = 'Formality Style Transfer for Noisy, User-generated Conversations: Extracting labeled, parallel data from unlabeled corpora'
    p1 = 'Formality Style Transfer for Noisy Text: Leveraging Out-of-Domain Parallel Data for In-Domain Training via POS Masking Isak Etinger Alan Black'
    assert not R.meta_describes_page(meta, p1)
    assert R.judge_meta(meta, [meta], p1, 'etinger', None)[0] == 'undecided'
    ok = 'Ten Simple Rules for AI-Assisted Coding in Science'
    assert R.meta_describes_page(ok, ok + ' arXiv:2510.22254v2 Eric Bridgeford')
