"""arxiv_bulk.match: title + same authors, with the arXiv families normalized like the byline's (2026-11-06: raw 'Lee' never equalled 'lee', 0 matches for every school)."""
from collections import defaultdict

import ftp_common as F
from channels import arxiv_bulk as A


def _ix(fams, year):
    rec = ('1612.01507', "Eldan's Stochastic Localization and the KLS Conjecture: Isoperimetry, Concentration and Mixing", tuple(fams), year)
    by_t = defaultdict(list)
    by_t[F.nt(rec[1])].append(rec)
    return dict(by_doi={}, by_t=by_t, by_id={})


def test_title_and_authors_match_with_a_publication_lag_of_five_years():
    import arxiv_oai as ao
    ix = _ix([ao.fam(x) for x in ('Lee', 'Vempala')], 2019)
    r = dict(title="Eldan's stochastic localization and the KLS conjecture: Isoperimetry, concentration and mixing", year=2024,
             byline=['Yin Tat Lee', 'Santosh S. Vempala'], pis=['Santosh Vempala'])
    how, rec = A.match(r, ix)
    assert how == 'title_author' and rec[0] == '1612.01507'


def test_other_authors_do_not_match():
    import arxiv_oai as ao
    ix = _ix([ao.fam(x) for x in ('Lee', 'Vempala')], 2019)
    r = dict(title="Eldan's stochastic localization and the KLS conjecture: Isoperimetry, concentration and mixing", year=2024,
             byline=['A. Nother', 'B. Person'], pis=[])
    assert A.match(r, ix)[0] is None
