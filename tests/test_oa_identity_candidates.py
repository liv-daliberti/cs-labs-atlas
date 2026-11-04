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
