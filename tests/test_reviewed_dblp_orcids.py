"""Owned bibliography bindings do not require inheriting unreviewed person identifiers."""
import collections
import copy
import json
from pathlib import Path

import pytest
import schema_check
from pihier import census, identity
import test_build_rules as B

A = '0000-0002-8648-8718'
B_ID = '0000-0002-8365-4741'
PID = 'https://dblp.org/pid/1/123'


def policy(allowed=()):
    return dict(allowed=list(allowed), why='Only identifiers independently named by the owned source may be inherited.',
                evidence=[dict(orcid=o, url='https://example.edu/owned', sha256='a'*64, quote='My ORCID: '+o) for o in allowed])


def dump():
    return dict(persons={PID: dict(names=['Ada Lovelace'], orcid=[A, B_ID],
                                   pubs=[dict(key='journals/example/Lovelace20', dois=['10.1/exact'], title='A Source-Bound Paper', year=2020, authors=['Ada Lovelace'], pages='1-10')])},
                by_name={'ada lovelace': [PID]})


@pytest.mark.parametrize('allowed', [[], [A]])
def test_owned_PID_and_works_remain_but_unreviewed_ORCIDs_do_not_enter_PI(allowed):
    p = dict(pi='Ada Lovelace', names=['Ada Lovelace'], dblp=[PID], orcid=[], dblpOrcidReview=policy(allowed))
    source = dump(); before = copy.deepcopy(source)
    doi, title = collections.defaultdict(set), collections.defaultdict(dict); n = collections.Counter()
    identity.apply_dump([p], source, doi, title, n)
    assert p['dblp'] == [PID] and p['orcid'] == allowed
    assert p['dblpOrcidsWithheld'] == sorted(set([A, B_ID])-set(allowed))
    assert doi[p['pi']] == {'10.1/exact'} and title[p['pi']]
    assert n['dblp_orcids_withheld_by_review'] == 2-len(allowed)
    once = copy.deepcopy(p); count = n['dblp_orcids_withheld_by_review']
    identity.apply_dump([p], source, doi, title, n)
    assert p == once and n['dblp_orcids_withheld_by_review'] == count and source == before


def test_absent_review_retains_existing_behavior():
    p = dict(pi='Ada Lovelace', names=['Ada Lovelace'], dblp=[PID], orcid=[])
    identity.apply_dump([p], dump(), collections.defaultdict(set), collections.defaultdict(dict), collections.Counter())
    assert p['orcid'] == [A, B_ID] and 'dblpOrcidsWithheld' not in p and 'dblpOrcidReview' not in p


def test_explicit_independent_census_ORCID_is_not_removed_by_inheritance_policy():
    p = dict(pi='Ada Lovelace', names=['Ada Lovelace'], dblp=[PID], orcid=[A], dblpOrcidReview=policy())
    identity.apply_dump([p], dump(), collections.defaultdict(set), collections.defaultdict(dict), collections.Counter())
    assert p['orcid'] == [A] and p['dblpOrcidsWithheld'] == [B_ID]


def test_unresolved_identity_hold_still_dominates_positive_inheritance_review():
    p = dict(pi='Ada Lovelace', names=['Ada Lovelace'], dblp=[PID], orcid=[], dblpOrcidReview=policy([A]),
             identityHold=dict(status='reviewed_no_identity', reason='Person still unresolved'))
    identity.apply_dump([p], dump(), collections.defaultdict(set), collections.defaultdict(dict), collections.Counter())
    assert p['orcid'] == [] and 'dblpOrcidsWithheld' not in p


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('allowed', [[], [A]])
def test_native_review_round_trip_and_source_preservation(tmp_path, monkeypatch, allowed):
    B.write_school(tmp_path)
    op = B.put(tmp_path, 'census-overrides.json', None); ov = json.loads(op.read_text())
    ov[B.SCHOOL]['Ada Lovelace']['dblp_orcid_review'] = policy(allowed); op.write_text(json.dumps(ov))
    dp = B.put(tmp_path, 'dblp-dump-persons.json.gz', None)
    import gzip
    dp.write_bytes(gzip.compress(json.dumps(dump()).encode()))
    original = {p:p.read_bytes() for p in [dp, op, B.put(tmp_path,'census-faculty.json')]}
    ctx = B.run_stages(tmp_path)
    pi = next(p for p in ctx.pis if p['pi']=='Ada Lovelace')
    assert pi['dblpOrcidReview'] == policy(allowed) and pi['orcid'] == allowed and pi['dblp'] == [PID]
    assert pi['dblpOrcidsWithheld'] == sorted(set([A, B_ID])-set(allowed))
    assert any(r['pi']=='Ada Lovelace' for r in ctx.rows)
    assert original == {p:p.read_bytes() for p in original}
    import provenance
    from pihier import build
    ctx.out=tmp_path/'reviewed-output';ctx.out.mkdir();monkeypatch.setattr(provenance,'block',lambda school:{})
    build.write(ctx)
    schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/pis.schema.json').read_text())
    assert schema_check.validate_file(ctx.out/'pis.json',schema)==[]


@pytest.mark.parametrize('bad', [
    dict(allowed=[A],why='Missing positive source',evidence=[]),
    dict(allowed=[A],why='',evidence=[]),
    dict(allowed=A,why='Malformed array',evidence=[]),
    dict(allowed=[A,A],why='Duplicate identifiers',evidence=[]),
    dict(allowed=['bad'],why='Malformed identifier',evidence=[]),
    dict(allowed=[],why='No evidence key'),
    dict(allowed=[A],why='Other person source',evidence=[dict(orcid=B_ID,url='https://example.edu',sha256='a'*64,quote=B_ID)]),
    dict(allowed=[A],why='Invalid source hash',evidence=[dict(orcid=A,url='https://example.edu',sha256='not-a-hash',quote=A)]),
])
def test_malformed_or_unbacked_positive_allowlist_fails_before_admission(bad):
    with pytest.raises(ValueError):
        census.reviewed_dblp_orcids([dict(name='Ada Lovelace')], {'Ada Lovelace':dict(dblp_orcid_review=bad)})


def test_conflicting_merged_name_reviews_are_not_silently_unioned():
    with pytest.raises(ValueError,match='Conflicting'):
        census.reviewed_dblp_orcids([dict(name='Ada Lovelace'),dict(name='A. Lovelace')],
            {'Ada Lovelace':dict(dblp_orcid_review=policy()),'A. Lovelace':dict(dblp_orcid_review=policy([A]))})
