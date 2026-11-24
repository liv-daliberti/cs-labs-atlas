"""A reviewed `dblp_drop` removes a conflated namesake pid from the PI's census ids (2026-11-19)."""
import inspect
import collections
import copy
import gzip
import json

import pytest

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


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('rejected', ['0000-0002-8648-8718', 'https://orcid.org/0000-0002-8648-8718/'])
def test_rejected_census_orcid_stays_excluded_through_native_dump_inheritance(tmp_path, rejected):
    import test_build_rules as B
    from test_reviewed_dblp_orcids import A, B_ID, dump

    B.write_school(tmp_path)
    cf = B.put(tmp_path, 'census-faculty.json')
    faculty = json.loads(cf.read_text())
    faculty[0]['orcid'] = 'https://orcid.org/' + A
    cf.write_text(json.dumps(faculty))
    op = B.put(tmp_path, 'census-overrides.json', None)
    overrides = json.loads(op.read_text())
    overrides[B.SCHOOL]['Ada Lovelace']['orcid_drop'] = [rejected]
    op.write_text(json.dumps(overrides))
    dp = B.put(tmp_path, 'dblp-dump-persons.json.gz', None)
    dp.write_bytes(gzip.compress(json.dumps(dump()).encode()))
    before = {p:p.read_bytes() for p in [cf, op, dp]}
    ctx = B.run_stages(tmp_path)
    pi = next(p for p in ctx.pis if p['pi'] == 'Ada Lovelace')
    assert pi['orcid'] == [B_ID] and pi['orcidFromDblp'] == [B_ID]
    assert pi['dblp'] and ctx.dblp_doi['Ada Lovelace'] == {'10.1/exact'}
    assert before == {p:p.read_bytes() for p in before}


def test_rejected_orcid_does_not_remove_another_pi_or_mutate_original_dump():
    from test_reviewed_dblp_orcids import A, B_ID, PID, dump

    source = dump(); before = copy.deepcopy(source)
    pi = dict(pi='Ada Lovelace', names=['Ada Lovelace'], dblp=[PID], orcid=[A])
    other = dict(pi='Augusta Lovelace', names=['Ada Lovelace'], dblp=[PID], orcid=[])
    identity.apply_dump([pi, other], source, collections.defaultdict(set), collections.defaultdict(dict), collections.Counter(),
                        excluded_orcids={'Ada Lovelace': {A}})
    assert pi['orcid'] == [B_ID] and other['orcid'] == [A, B_ID] and source == before
