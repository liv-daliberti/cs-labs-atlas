"""pis.json id-first matching fields (tools/pihier/match_ids.py): keys are only added, ids are normalised, nothing is invented."""
import copy

from pihier import match_ids as M


def row(**kw):
    base = dict(pi='王韫博', names=['王韫博', 'Yunbo Wang'], dblp=['https://dblp.org/pid/84/3894'], orcid=['https://orcid.org/0000-0002-1825-0097'],
                reviewedOpenAlex=['https://openalex.org/A5100713555'], oaAuthorIds=['https://openalex.org/A5100713555', 'https://openalex.org/A5100713554'],
                mixedOpenAlex=['https://openalex.org/A5099282581'], notOpenAlex=['https://openalex.org/A1'], mergedCensusRows=[])
    base.update(kw)
    return base


def test_adds_normalised_ids_and_latin_alias_only():
    before = row()
    [after] = M.add([copy.deepcopy(before)])
    assert {k: v for k, v in after.items() if k in before} == before   # no existing key changes
    assert set(after) - set(before) == {'latinAliases', 'dblpPids', 'orcidIds', 'openalexIds'}
    assert after['latinAliases'] == ['Yunbo Wang']
    assert after['dblpPids'] == ['84/3894']
    assert after['orcidIds'] == ['0000-0002-1825-0097']
    assert after['openalexIds'] == ['A5100713555', 'A5100713554']   # mixed and not-this-person ids never appear


def test_reviewed_pair_supplies_the_latin_spelling_and_nothing_is_transliterated():
    [p] = M.add([row(names=['陈贵海'], pi='陈贵海', dblp=[], orcid=[], reviewedOpenAlex=[], oaAuthorIds=[])], pairs=[('陈贵海', 'Guihai Chen')])
    assert p['latinAliases'] == ['Guihai Chen']
    assert (p['dblpPids'], p['orcidIds'], p['openalexIds']) == ([], [], [])
    [q] = M.add([row(names=['陈贵海'], pi='陈贵海', dblp=[], orcid=[], reviewedOpenAlex=[], oaAuthorIds=[])])
    assert q['latinAliases'] == []


def test_forms():
    assert M.dblp_pid('84/3894') == '84/3894' and M.dblp_pid('https://dblp.org/pid/84/3894.html') == '84/3894'
    assert M.dblp_pid('https://dblp.org/pid/02/5889-27') == '02/5889-27' and M.dblp_pid('junk') is None
    assert M.orcid_id('0000-0000-0000-0000') is None and M.orcid_id('0000-0001-5109-3700') == '0000-0001-5109-3700'
    assert M.latin('Yunbo') is None and M.latin('Jean-Luc de Gispert') == 'Jean-Luc de Gispert' and M.latin('王 旋') is None
