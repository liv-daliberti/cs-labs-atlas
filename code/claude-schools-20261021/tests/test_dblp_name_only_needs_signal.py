"""2026-11-19 namesake audit: a name alone never binds a DBLP record (MIT: 'Rajeev Ram' 212/0844, one 2016 paper, hid 'Rajeev J. Ram' 80/6881)."""
import collections

from pihier import identity

COUNT = collections.Counter


def run(person, persons, school='mit'):
    pis = [person]
    dump = dict(persons=persons, by_name={'rajeev ram': ['p/ns']})
    n = COUNT()
    identity.apply_dump(pis, dump, collections.defaultdict(set), collections.defaultdict(dict), n, school=school)
    return pis[0], n


def pi(**kw):
    return dict(pi='Rajeev Ram', names=['Rajeev Ram'], dblp=[], orcid=[], **kw)


def test_bare_namesake_record_is_held_not_bound():
    p, n = run(pi(), {'p/ns': dict(names=['Rajeev Ram'], urls=[], affiliations=[], pubs=[dict(title='X.', year=2016, dois=['10.1/x'])])})
    assert p['dblp'] == [] and 'dblpBasis' not in p and p['dblpHeld'][0]['pid'] == 'p/ns' and n['dblp_name_only_held'] == 1


def test_school_affiliation_note_binds():
    p, n = run(pi(), {'p/ns': dict(names=['Rajeev Ram'], urls=[], affiliations=['Massachusetts Institute of Technology, Cambridge, MA, USA'], pubs=[])})
    assert p['dblp'] == ['p/ns'] and p['dblpSignal']['kind'] == 'affiliation' and n['dblp_ids_from_dump_name'] == 1


def test_school_domain_homepage_binds():
    p, _ = run(pi(), {'p/ns': dict(names=['Rajeev Ram'], urls=['https://www.rle.mit.edu/ram/'], affiliations=[], pubs=[])})
    assert p['dblp'] == ['p/ns']


def test_other_institution_does_not_bind_without_coauthors():
    p, _ = run(pi(), {'p/ns': dict(names=['Rajeev Ram'], urls=[], affiliations=['University of Elsewhere'], pubs=[])})
    assert p['dblp'] == []


def test_colleague_coauthorship_binds_a_mover():
    pubs = [dict(title=f'T{i}.', year=2018 + i, dois=[], authors=[['Rajeev Ram', None], ['Colleague A', None]]) for i in range(3)]
    pis = [dict(pi='Rajeev Ram', names=['Rajeev Ram'], dblp=[], orcid=[]), dict(pi='Colleague A', names=['Colleague A'], dblp=['p/ca'], orcid=[])]
    dump = dict(persons={'p/ns': dict(names=['Rajeev Ram'], urls=[], affiliations=['University of Elsewhere'], pubs=pubs),
                         'p/ca': dict(names=['Colleague A'], urls=[], affiliations=[], pubs=[])}, by_name={'rajeev ram': ['p/ns']})
    identity.apply_dump(pis, dump, collections.defaultdict(set), collections.defaultdict(dict), COUNT(), school='mit')
    assert pis[0]['dblp'] == ['p/ns'] and pis[0]['dblpSignal']['kind'] == 'colleague_records'
    assert pis[0]['dblp'] and 'dblpHeld' not in pis[0]
    pis[0]['dblp'] = []                                    # two records are not enough
    dump['persons']['p/ns']['pubs'] = pubs[:2]
    pis[0].pop('dblpBasis', None)
    identity.apply_dump(pis, dump, collections.defaultdict(set), collections.defaultdict(dict), COUNT(), school='mit')
    assert pis[0]['dblp'] == []
