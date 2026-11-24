"""Paper claim reviews: an OpenAlex-id-only selector holds every copy of the work, whatever DOI the copy carries; a selector naming oa AND doi
holds only the copy with that DOI (SJTU 2026-11-10: the sweep copy and the pi-works copy of one work carried different DOIs)."""
from pihier import reviewed_claims as R


def test_oa_only_selector_matches_both_doi_copies():
    sel = R._selector({'oa': 'https://openalex.org/W1'})
    assert R.matches({'oa': 'https://openalex.org/W1', 'doi': '10.1/a'}, sel)
    assert R.matches({'oa': 'https://openalex.org/W1', 'doi': '10.1/b'}, sel)
    assert R.matches({'id': 'https://openalex.org/W1'}, sel)


def test_oa_plus_doi_selector_misses_the_other_doi_copy():
    sel = R._selector({'oa': 'https://openalex.org/W1', 'doi': '10.1/a'})
    assert R.matches({'oa': 'https://openalex.org/W1', 'doi': '10.1/a'}, sel)
    assert not R.matches({'oa': 'https://openalex.org/W1', 'doi': '10.1/b'}, sel)
