"""A generic institution extension is discovery, not permission to credit excluded child-only affiliations."""
import collections
import copy
import gzip
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace
import zlib

import pytest

from pihier import common as C, identity, papers
from test_build_rules import au, work, put, write_school, run_stages, INST, OA

CHILD = OA + 'I999999'


def child(name='Ada Lovelace', aid='A1', raw=None):
    a = au(name, aid, school=False, raw=raw or ['Excluded research facility'])
    a['institutions'] = [dict(id=CHILD, display_name='Excluded research facility', type='facility', lineage=[CHILD, INST])]
    return a


@pytest.fixture
def excluded(monkeypatch):
    original = C._S.get

    def cfg(k):
        x = original(k)
        return dict(x, ids=dict(x['ids'], openalex_excluded=['I999999'])) if k == 'princeton' else x
    monkeypatch.setattr(C._S, 'get', cfg)
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)


def test_real_snapshot_child_only_affiliation_is_not_the_primary_school():
    receipt = json.loads((Path(__file__).resolve().parent / 'fixtures/tsinghua-excluded-child-1108.json').read_text())
    original = receipt['original_work']; before = copy.deepcopy(original)
    a = original['authorships'][0]
    assert papers._authorship_school_via(original, a, OA + 'I99065089', C._S.aff_rx('tsinghua'))
    scoped = C.school_scope_work(original, 'tsinghua')
    assert not papers._authorship_school_via(scoped, scoped['authorships'][0], OA + 'I99065089', C._S.aff_rx('tsinghua'))
    assert original == before and scoped is not original


def test_exclusion_cannot_be_overridden_by_a_joint_related_appointment():
    gate = ({'I999999'}, re.compile('Princeton University'), INST, {'I999999'})
    source = work('W1', 'Excluded joint', 2020, [child()])
    scoped = C.gate_related(source, gate, {'ada lovelace': {'I999999'}})
    assert INST not in scoped['authorships'][0]['institutions'][0]['lineage']
    assert INST in source['authorships'][0]['institutions'][0]['lineage']


def variant(kind):
    a = child()
    if kind == 'raw':
        a['raw_affiliation_strings'] = ['Excluded research facility; Princeton University']
    if kind == 'mixed':
        a['institutions'].extend(au('Ada Lovelace', 'A1')['institutions'])
    authors = [a]
    if kind == 'coauthor':
        authors.append(au('Alan Turing', 'A9'))
    return work('W100', 'A Source Scope Paper', 2020, authors)


@pytest.mark.usefixtures('layout', 'excluded')
@pytest.mark.parametrize('route', ['sweep', 'pi_works'])
@pytest.mark.parametrize('kind,keep', [('excluded', False), ('coauthor', False), ('raw', True), ('mixed', True)])
def test_native_anchor_and_outside_sweep_routes_keep_own_authorship_scope(tmp_path, route, kind, keep):
    # Two real school works make the existing cross-affiliation fallback eligible; a child-only facility still cannot borrow a coauthor.
    anchors = [work('W11', 'An Anchor One', 2020, [au('Ada Lovelace', 'A1')]),
               work('W12', 'An Anchor Two', 2020, [au('Ada Lovelace', 'A1')])]
    source = variant(kind); before = copy.deepcopy(source)
    write_school(tmp_path, sweep=anchors + ([source] if route == 'sweep' else []))
    if route == 'pi_works':
        con = sqlite3.connect(put(tmp_path, 'pi-works.sqlite'))
        con.execute('create table works(body blob)')
        con.execute('insert into works values (?)', (zlib.compress(json.dumps(source).encode()),))
        con.execute('create table pages(work text,quote text,url text,pdf_sha256 text,school_named int,status text,page1 text)')
        con.commit(); con.close()
    ctx = run_stages(tmp_path, upto='papers')
    assert bool(ctx.anchored['Ada Lovelace'][OA + 'A1'])
    assert any(r['oa'] == source['id'] for r in ctx.rows) is keep
    assert source == before
    hit = next(h for h in ctx.hits if h[1]['id'] == source['id'])
    assert INST not in hit[2]['institutions'][0]['lineage']
    if route == 'pi_works':
        con = sqlite3.connect(put(tmp_path, 'pi-works.sqlite'))
        assert json.loads(zlib.decompress(con.execute('select body from works').fetchone()[0])) == source
        con.close()


@pytest.mark.usefixtures('excluded')
@pytest.mark.parametrize('kind,keep', [('excluded', False), ('coauthor', False), ('raw', True), ('mixed', True)])
def test_recovered_openalex_sources_replay_the_pi_authorship(kind, keep):
    w = variant(kind); before = copy.deepcopy(w)
    ctx = SimpleNamespace(school='princeton', inst=INST, aff=C._S.aff_rx('princeton'), n=collections.Counter(), hits=[])
    ev = dict(basis='openalex_authorship', oa=w['id'], school_via=['Excluded research facility'], openalex_work=w)
    assert bool(papers.recovered_scope_via(ctx, dict(pi='Ada Lovelace', names=['Ada Lovelace']), ev)) is keep
    assert w == before


@pytest.mark.usefixtures('excluded')
def test_legacy_recovered_display_names_need_a_replayable_source():
    ctx = SimpleNamespace(school='princeton', inst=INST, aff=C._S.aff_rx('princeton'), n=collections.Counter(), hits=[])
    ev = dict(basis='openalex_authorship', oa=OA + 'W100', school_via=['Princeton University'])
    p = dict(pi='Ada Lovelace', names=['Ada Lovelace'])
    assert papers.recovered_scope_via(ctx, p, ev) == []
    assert ctx.n['recovered_school_scope_unreplayable'] == 1
    w = variant('mixed');ctx.hits = [('Ada Lovelace', w)]
    assert papers.recovered_scope_via(ctx, p, ev)
    assert papers.recovered_scope_via(ctx, p, dict(basis='page1_open', how='named PI', quotes=['Ada Lovelace Princeton University'])) is None


@pytest.mark.usefixtures('layout', 'excluded')
def test_recovered_rows_do_not_bypass_scope_or_appointment(tmp_path):
    write_school(tmp_path, sweep=[])
    rows = [dict(pi='Ada Lovelace', year=2020, title='A recovered child only', byline=['Ada Lovelace'], dblp_key='conf/x/1',
                 evidence=dict(basis='openalex_authorship', oa=OA + 'W100', school_via=['Excluded facility'], openalex_work=variant('excluded'))),
            dict(pi='Ada Lovelace', year=2020, title='A recovered own raw school', byline=['Ada Lovelace'], dblp_key='conf/x/2',
                 evidence=dict(basis='openalex_authorship', oa=OA + 'W101', school_via=['Excluded facility'], openalex_work=dict(variant('raw'), id=OA + 'W101')))]
    with gzip.open(put(tmp_path, 'dblp-recovered.jsonl.gz'), 'wt') as f:
        f.write('\n'.join(json.dumps(r) for r in rows) + '\n')
    ctx = run_stages(tmp_path, upto='papers')
    assert {r['title'] for r in ctx.rows} == {'A recovered own raw school'}
    assert ctx.n['recovered_school_scope_not_supported'] == 1


@pytest.mark.usefixtures('excluded')
def test_shared_school_clause_explicitly_names_only_the_coauthor():
    w = variant('coauthor')
    w['authorships'][0]['raw_affiliation_strings'] = ['Princeton University (Dr Turing); Excluded research facility (Dr Lovelace)']
    scoped = C.school_scope_work(w, 'princeton')
    assert papers._authorship_school_via(scoped, scoped['authorships'][0], INST, C._S.aff_rx('princeton')) == []
    ctx = SimpleNamespace(school='princeton', inst=INST, aff=C._S.aff_rx('princeton'), n=collections.Counter(), hits=[])
    ev = dict(basis='openalex_authorship', oa=w['id'], openalex_work=w)
    assert papers.recovered_scope_via(ctx, dict(pi='Ada Lovelace', names=['Ada Lovelace']), ev) == []
