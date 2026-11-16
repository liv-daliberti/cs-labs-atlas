"""A dynamic or reviewed provider ID does not prove a different full given name."""
import collections
import json
import sqlite3
import zlib
from types import SimpleNamespace

import pytest

import atlas_paths as P
import test_build_rules as T
from pihier import identity, names


@pytest.mark.parametrize('forms,raw,conflict', [
    (['李国良', 'Guoliang Li'], 'Guanghao Li', True),
    (['陈渝', 'Yu Chen'], 'Yating Chen', True),
    (['张松海', 'Song-Hai Zhang'], 'Shan Zhang', True),
    (['李国良', 'Guoliang Li', 'G. Li'], 'Guanghao Li', True),
    (['李国良', 'Guoliang Li'], 'G. Li', False),
    (['Steven Wu'], 'Zhiwei Steven Wu', False),
    (['Steven Wu'], 'Steve Wu', False),
    (['M. Frans Kaashoek'], 'Frans Kaashoek', False),
    (['Song-Hai Zhang'], 'Songhai Zhang', False),
    (['Song-Hai Zhang'], 'Zhang Songhai', False),
    (['G. Li'], 'Guanghao Li', False),
    (['李国良'], 'Guanghao Li', False),
])
def test_provider_id_full_given_name_conflict(forms, raw, conflict):
    assert identity.author_id_name_conflict(forms, raw) is conflict


def context(tmp_path, pi_names):
    pi = pi_names[0]
    p = dict(pi=pi, names=pi_names, reviewedOpenAlex=[], orcid=[], notOpenAlex=[], mixedOpenAlex=[])
    by_sur = collections.defaultdict(list)
    for _, family in names.Name(pi_names).forms:
        by_sur[family].append(pi)
    return SimpleNamespace(here=tmp_path, school=T.SCHOOL, pis=[p], pid0={pi: p}, n=collections.Counter(),
                           nm={pi: names.Name(pi_names)}, cwork=lambda w: None, by_sur=by_sur, by_mono={})


@pytest.mark.parametrize('pi_names,wrong', [(['Guoliang Li', '李国良'], 'Guanghao Li'),
                                        (['Yu Chen', '陈渝'], 'Yating Chen'),
                                        (['Song-Hai Zhang', '张松海'], 'Shan Zhang')])
@pytest.mark.usefixtures('layout')
def test_sweep_surname_fallback_cannot_reuse_an_anchor_for_conflicting_given_name(tmp_path, monkeypatch, pi_names, wrong):
    ctx = context(tmp_path, pi_names)
    seed = T.work('W1', 'A genuinely source-anchored work', 2020, [T.au(pi_names[0], 'A1')])
    other = T.work('W2', 'A conflicting authorship under that provider ID', 2021, [T.au(wrong, 'A1')])
    monkeypatch.setattr(identity, 'sweep_works', lambda *args: iter([seed, other]))
    monkeypatch.setattr(identity, 'authorship_identity', lambda ctx, pi, w, a, cw: 'dblp_person_page_doi' if w == seed else None)
    identity.hits(ctx)
    assert [(h[1]['id'], h[2]['raw_author_name']) for h in ctx.hits] == [(seed['id'], pi_names[0])]
    assert ctx.n['author_id_full_given_name_conflicts'] == 1
    assert ctx.anchored[pi_names[0]][T.OA + 'A1'] == 1


@pytest.mark.usefixtures('layout')
def test_sweep_anchor_keeps_supported_extra_given_name(tmp_path, monkeypatch):
    ctx = context(tmp_path, ['Steven Wu'])
    seed = T.work('W1', 'A genuinely source-anchored work', 2020, [T.au('Steven Wu', 'A1')])
    other = T.work('W2', 'A supported full-name variant', 2021, [T.au('Zhiwei Steven Wu', 'A1')])
    monkeypatch.setattr(identity, 'sweep_works', lambda *args: iter([seed, other]))
    monkeypatch.setattr(identity, 'authorship_identity', lambda ctx, pi, w, a, cw: 'dblp_person_page_doi' if w == seed else None)
    identity.hits(ctx)
    assert {h[1]['id'] for h in ctx.hits} == {seed['id'], other['id']}


@pytest.mark.usefixtures('layout')
def test_own_works_id_fallback_cannot_use_an_initial_alias_to_override_full_name(tmp_path, monkeypatch):
    ctx = context(tmp_path, ['Guoliang Li', '李国良', 'G. Li'])
    seed = T.work('W1', 'A genuinely source-anchored work', 2020, [T.au('Guoliang Li', 'A1')])
    other = T.work('W2', 'A conflicting authorship outside the sweep', 2021, [T.au('Guanghao Li', 'A1')])
    db = sqlite3.connect(P.data_w('pi-works.sqlite', T.SCHOOL, root=tmp_path))
    db.execute('create table works (id text primary key, body blob)')
    db.execute('create table pages (work text,url text,status text,pdf_sha256 text,page1 blob,school_named int,quote text)')
    db.execute('insert into works values (?,?)', (other['id'], zlib.compress(json.dumps(other).encode())))
    db.commit()
    db.close()
    monkeypatch.setattr(identity, 'sweep_works', lambda *args: iter([seed]))
    monkeypatch.setattr(identity, 'authorship_identity', lambda *args: 'dblp_person_page_doi')
    identity.hits(ctx)
    assert [h[1]['id'] for h in ctx.hits] == [seed['id']]
    assert ctx.n['author_id_full_given_name_conflicts'] == 1


@pytest.mark.usefixtures('layout')
def test_initial_alias_in_sweep_cannot_bypass_conflict_on_reviewed_provider_id(tmp_path, monkeypatch):
    ctx = context(tmp_path, ['Guoliang Li', '李国良', 'G. Li'])
    ctx.pis[0]['reviewedOpenAlex'] = [T.OA + 'A1']
    other = T.work('W2', 'A conflicting authorship under a reviewed provider ID', 2021, [T.au('Guanghao Li', 'A1')])
    monkeypatch.setattr(identity, 'sweep_works', lambda *args: iter([other]))
    monkeypatch.setattr(identity, 'authorship_identity', lambda *args: 'reviewed_openalex_author_id')
    identity.hits(ctx)
    assert not ctx.hits and not ctx.anchored['Guoliang Li']
    assert ctx.n['author_id_full_given_name_conflicts'] == 1


@pytest.mark.usefixtures('layout')
def test_conflicting_earlier_authorship_does_not_suppress_later_actual_pi_on_same_work(tmp_path, monkeypatch):
    ctx = context(tmp_path, ['Guoliang Li', '李国良', 'G. Li'])
    ctx.pis[0]['reviewedOpenAlex'] = [T.OA + 'A1', T.OA + 'A2']
    work = T.work('W2', 'Both a conflicting name and the actual PI', 2021,
                  [T.au('Guanghao Li', 'A1'), T.au('Guoliang Li', 'A2')])
    monkeypatch.setattr(identity, 'sweep_works', lambda *args: iter([work]))
    monkeypatch.setattr(identity, 'authorship_identity', lambda *args: 'reviewed_openalex_author_id')
    identity.hits(ctx)
    assert [(h[1]['id'], h[2]['raw_author_name']) for h in ctx.hits] == [(work['id'], 'Guoliang Li')]
    assert ctx.n['author_id_full_given_name_conflicts'] == 1
