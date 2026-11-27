"""Stage 5: proposed OpenAlex author ids for PIs without a DBLP id or ORCID."""
import oa_identity_candidates as C


def A(raw, n=10, years=(2016, 2024), orcids=None, last=5):
    return dict(n=n, last=last, years=list(years), raw=raw, orcids=orcids or {}, venues={'CHI': n})


def test_name_match_needs_family_and_first_given_name():
    assert C.name_match('Gregory Abowd', 'Gregory D. Abowd') and C.name_match('Gregory Abowd', 'G. Abowd')
    assert C.name_match('J. Smith', 'John Smith') and not C.name_match('John Smith', 'Jane Smith')
    assert not C.name_match('John A. Smith', 'John B. Smith')    # conflicting middle initials
    assert C.name_match('Jose Pérez', 'Jose Perez') and C.name_match('Jean-Luc Picard', 'Jean Luc Picard')


def test_unique_match_is_accepted_namesakes_and_several_are_not():
    authors = {'A1': A({'Ann Lee': 12}), 'A2': A({'Ann Lee': 5}, orcids={'0000-0001-0000-0001': 5}), 'A3': A({'Bo Kim': 9}), 'A4': A({'Bo Kim': 7}), 'A5': A({'Cy Wu': 4}, years=(2010, 2012))}
    pis = [dict(name='Ann Lee', orcid=['0000-0002-0000-0002'], years_listed=[2016]),     # A1 (no orcid) vs A2 (other ORCID: namesake)
           dict(name='Bo Kim', years_listed=[2016]), dict(name='Cy Wu', years_listed=[2018]), dict(name='Di Xu', years_listed=[2016])]
    auto, amb, un = C.propose(pis, authors)
    assert list(auto) == ['Ann Lee'] and auto['Ann Lee']['openalex'] == ['A1'] and auto['Ann Lee']['auto'] is True
    assert list(amb) == ['Bo Kim', 'Cy Wu'] and un == ['Di Xu']


def test_dominant_author_wins_and_initial_only_matches_do_not_count():
    authors = {'B1': A({'Eva K. Lee': 52}, n=52), 'B2': A({'Eva Lee': 8}, n=8), 'C1': A({'Michael Hunter': 40}, n=40), 'C2': A({'Michael Hunter': 10}, n=10),
               'D1': A({'J.-Y. Kim': 30, 'Jin-Yeon Kim': 5}, n=35)}
    pis = [dict(name='Eva Lee', years_listed=[2016]), dict(name='Michael Hunter', years_listed=[2016]), dict(name='Jennifer Kim', years_listed=[2016])]
    auto, amb, un = C.propose(pis, authors)
    assert list(auto) == ['Eva Lee'] and auto['Eva Lee']['openalex'] == ['B1'] and list(amb) == ['Michael Hunter', 'Jennifer Kim'] and un == []   # an initial-only raw name never auto-accepts


def test_a_low_volume_author_with_an_orcid_is_proposed_in_the_second_pass_only():
    few = {'Z1': A({'Zia Khan': 2}, n=2, years=(2017, 2017), orcids={'0000-0002-7859-3489': 2}), 'Z2': A({'Zia Khan': 1}, n=1, orcids={}),
           'Z3': A({'Z. Khan': 2}, n=2, orcids={'0000-0001-0000-0003': 2})}
    pis = [dict(name='Zia Khan', years_listed=[2016, 2017])]
    assert C.propose(pis, few)[0] == {}                                   # below MIN_WORKS: the first pass never sees them
    auto, amb, un = C.propose(pis, few, min_works=1, need_orcid=True, strict_name=True)
    assert list(auto) == ['Zia Khan'] and auto['Zia Khan']['openalex'] == ['Z1'] and not amb   # no ORCID (Z2) and an initial-only name (Z3) do not count


def test_written_identity_review_keeps_school_and_manual_decisions():
    import pytest
    import json
    import schema_check
    from pathlib import Path
    manual = dict(openalex=['A123'], why='Manually verified identity.')
    proposed = dict(openalex=['A456'], why='New proposed identity.', auto=True)
    doc = C.updated_review({'decisions': {'Known PI': manual}}, 'gatech', {'Known PI': proposed, 'New PI': proposed})
    assert doc['school'] == 'gatech' and doc['decisions']['Known PI'] == manual
    shape = json.loads((Path(C.__file__).parents[1] / 'schemas/openalex-identity-review.schema.json').read_text())
    assert schema_check.validate(doc, shape) == []
    with pytest.raises(ValueError, match='school does not match'):
        C.updated_review(doc, 'other', {})
