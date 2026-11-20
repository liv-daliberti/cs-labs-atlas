"""A reviewed `dblp_drop` removes a conflated namesake pid from the PI's census ids (2026-11-19)."""
import inspect
import collections

from pihier import census, identity


def test_dblp_drop_is_wired():
    assert 'dblp_drop' in inspect.getsource(census)


def test_excluded_cached_identity_cannot_return_by_exact_name():
    p = dict(pi='Alice Smith', names=['Alice Smith'], dblp=['bad'], orcid=[])
    pubs = {'paper': dict(authors={'bad': 'Alice Smith'}, title='A namesake paper', year=2020, doi='10.1/wrong')}
    dois, titles = collections.defaultdict(set), collections.defaultdict(dict)
    identity.apply_cached_lists([p], pubs, dois, titles, collections.Counter(), excluded_pids={'Alice Smith': {'bad'}})
    assert p['dblp'] == [] and not dois['Alice Smith'] and not titles['Alice Smith']


def test_excluded_dump_identity_cannot_return_despite_school_signal():
    p = dict(pi='Alice Smith', names=['Alice Smith'], dblp=[], orcid=[])
    record = dict(names=['Alice Smith'], urls=['https://mit.edu/alice'], affiliations=[], pubs=[], orcid=[])
    dump = dict(persons={'bad': record}, by_name={'alice smith': ['bad']})
    identity.apply_dump([p], dump, collections.defaultdict(set), collections.defaultdict(dict), collections.Counter(),
                        school='mit', excluded_pids={'Alice Smith': {'bad'}})
    assert p['dblp'] == [] and 'dblpBasis' not in p


def test_exclusion_does_not_block_an_independently_supported_identity():
    p = dict(pi='Alice Smith', names=['Alice Smith'], dblp=[], orcid=[])
    record = dict(names=['Alice Smith'], urls=['https://mit.edu/alice'], affiliations=[], pubs=[], orcid=[])
    dump = dict(persons={'bad': record, 'good': record}, by_name={'alice smith': ['bad', 'good']})
    identity.apply_dump([p], dump, collections.defaultdict(set), collections.defaultdict(dict), collections.Counter(),
                        school='mit', excluded_pids={'Alice Smith': {'bad'}})
    assert p['dblp'] == ['good'] and p['dblpSignal']['kind'] == 'homepage'
