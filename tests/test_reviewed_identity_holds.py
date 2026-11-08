"""Reviewed unresolved bibliography identity decisions block attribution, retaining the PI and members."""
import collections
import copy
import gzip
import json
from pathlib import Path

import pytest
import schema_check
from pihier import identity, papers
import test_build_rules as B

REASON = 'Reviewed ambiguous bibliography identity; source-bound person resolution is still needed.'
HOLD = dict(status='reviewed_no_identity', reason=REASON)


def set_review(root, enabled=True, reason=REASON):
    p = B.put(root, 'census-overrides.json', None)
    data = json.loads(p.read_text())
    data[B.SCHOOL]['Ada Lovelace'].update(no_identity=enabled)
    if reason is not None:
        data[B.SCHOOL]['Ada Lovelace']['why_no_identity'] = reason
    p.write_text(json.dumps(data))


@pytest.mark.usefixtures('layout')
def test_native_hold_retains_PI_members_and_other_labs_but_no_papers_or_links(tmp_path, monkeypatch):
    B.write_school(tmp_path)
    before = B.run_stages(tmp_path)
    source_paths = [B.put(tmp_path, n) for n in ['census-faculty.json', 'collection.json.gz', 'openalex-sweep.sqlite']]
    originals = {p: p.read_bytes() for p in source_paths}
    set_review(tmp_path)
    held = B.run_stages(tmp_path)
    before_pis = {p['pi']: p for p in before.pis}
    held_pis = {p['pi']: p for p in held.pis}
    assert held_pis.keys() == before_pis.keys()
    # Counts of admitted papers change; faculty role, lab, appointment and explicit source identifiers do not.
    assert held_pis['Ada Lovelace']['identityHold'] == HOLD
    for field in ['pi', 'personIds', 'names', 'lab', 'departments', 'piBasis', 'periods', 'listings',
                  'dblp', 'reviewedOpenAlex', 'orcid']:
        assert held_pis['Ada Lovelace'][field] == before_pis['Ada Lovelace'][field]
    assert held.stu == before.stu
    assert any(r['pi'] == 'Ada Lovelace' for r in before.rows)
    assert not any(r['pi'] == 'Ada Lovelace' for r in held.rows)
    assert not any(r['pi'] == 'Ada Lovelace' for r in held.sp)
    assert [r for r in held.rows if r['pi'] != 'Ada Lovelace'] == [r for r in before.rows if r['pi'] != 'Ada Lovelace']
    assert held.n['pis_with_reviewed_identity_hold'] == 1
    assert originals == {p: p.read_bytes() for p in source_paths}
    schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/pis.schema.json').read_text())
    import provenance
    from pihier import build
    held.out = tmp_path / 'held-package'
    held.out.mkdir()
    monkeypatch.setattr(provenance, 'block', lambda school: {})
    build.write(held)
    assert schema_check.validate_file(held.out / 'pis.json', schema) == []


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('enabled,reason', [(False, REASON), (True, None), (True, '')])
def test_only_an_active_explicit_reasoned_hold_changes_admission(tmp_path, enabled, reason):
    B.write_school(tmp_path)
    set_review(tmp_path, enabled, reason)
    ctx = B.run_stages(tmp_path)
    assert any(r['pi'] == 'Ada Lovelace' for r in ctx.rows)
    assert not next(p for p in ctx.pis if p['pi'] == 'Ada Lovelace').get('identityHold')


@pytest.mark.usefixtures('layout')
def test_resolving_review_restores_ordinary_native_rules(tmp_path):
    B.write_school(tmp_path)
    original = B.run_stages(tmp_path)
    set_review(tmp_path)
    assert not any(r['pi'] == 'Ada Lovelace' for r in B.run_stages(tmp_path).rows)
    set_review(tmp_path, False)
    restored = B.run_stages(tmp_path)
    assert restored.rows == original.rows and restored.sp == original.sp and restored.stu == original.stu


@pytest.mark.parametrize('kind', ['cached', 'official_dump'])
def test_held_PI_does_not_acquire_automatic_PID_ORCID_or_bibliography_anchors(kind):
    pid = 'https://dblp.org/pid/1/123'
    plain = dict(pi='Ada Lovelace', names=['Ada Lovelace'], dblp=[], orcid=[])
    held = dict(copy.deepcopy(plain), identityHold=HOLD)
    doi, title = collections.defaultdict(set), collections.defaultdict(dict)
    n = collections.Counter()
    if kind == 'cached':
        source = {'paper': dict(authors={pid: 'Ada Lovelace'}, doi='10.1/example', title='Exact Owned Work', year=2020)}
        before = copy.deepcopy(source)
        identity.apply_cached_lists([held], source, doi, title, n)
        assert held['dblp'] == [] and not doi['Ada Lovelace'] and not title['Ada Lovelace']
        identity.apply_cached_lists([plain], source, doi, title, n)
    else:
        source = dict(persons={pid: dict(names=['Ada Lovelace'], orcid=['0000-0000-0000-0001'],
                                       pubs=[dict(dois=['10.1/example'], title='Exact Owned Work', year=2020)])},
                      by_name={'ada lovelace': [pid]})
        before = copy.deepcopy(source)
        identity.apply_dump([held], source, doi, title, n)
        assert held['dblp'] == [] and held['orcid'] == [] and not doi['Ada Lovelace'] and not title['Ada Lovelace']
        identity.apply_dump([plain], source, doi, title, n)
        assert plain['orcid'] == ['0000-0000-0000-0001']
    assert plain['dblp'] == [pid] and doi['Ada Lovelace'] == {'10.1/example'}
    assert source == before


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('kind', ['dblp_recovery', 'labpage_recovery'])
def test_direct_recovery_cannot_bypass_explicit_PI_identity_review(tmp_path, monkeypatch, kind):
    B.write_school(tmp_path)
    set_review(tmp_path)
    source = dict(pi='Ada Lovelace', year=2020, title='A Primary Recovered Paper', byline=['Ada Lovelace'],
                  dblp_key='conf/x/held', evidence=dict(basis='page1_open', how='named byline',
                  quotes=['Ada Lovelace, Princeton University'], url='https://example.edu/paper.pdf',
                  pdf_sha256=B.SHA))
    if kind == 'dblp_recovery':
        B.put(tmp_path, 'dblp-recovered.jsonl.gz').write_bytes(gzip.compress((json.dumps(source)+'\n').encode()))
        ctx = B.run_stages(tmp_path)
        assert not any(r['pi'] == 'Ada Lovelace' for r in ctx.rows)
    else:
        # Every independent recovery adapter shares this boundary; an adapter-provided valid-looking row stays held.
        original = papers.recovered_rows
        def recovered(ctx, rows, seen):
            original(ctx, rows, seen)
            rows.append(dict(source, oa='https://openalex.org/WHELD', source='labpage_addition:LP-PAP-01'))
        monkeypatch.setattr(papers, 'recovered_rows', recovered)
        ctx = B.run_stages(tmp_path)
        assert not any(r['pi'] == 'Ada Lovelace' for r in ctx.rows)
        assert ctx.n['paper_rows_withheld_by_identity_review'] >= 1


@pytest.mark.usefixtures('layout')
def test_secondary_merged_census_name_cannot_lose_explicit_identity_hold(tmp_path):
    B.write_school(tmp_path)
    path = B.put(tmp_path, 'census-overrides.json', None)
    overrides = json.loads(path.read_text())
    overrides[B.SCHOOL]['Daniel Klein'] = dict(no_identity=True, why_no_identity=REASON)
    path.write_text(json.dumps(overrides))
    ctx = B.run_stages(tmp_path, upto='pis')
    pi = next(p for p in ctx.pis if p['pi'] == 'Dan Klein')
    assert pi['mergedCensusRows'] == ['Daniel Klein'] and pi['identityHold'] == HOLD
