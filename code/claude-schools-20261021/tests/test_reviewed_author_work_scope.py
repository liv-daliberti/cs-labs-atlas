"""A positive authorship review of a mixed provider record cannot approve its namesakes."""
import json
import sqlite3
import zlib
from types import SimpleNamespace

import pytest

import atlas_paths as P
import test_build_rules as T
from pihier import identity
from test_author_id_name_conflicts import context


@pytest.mark.parametrize('scope,accepted', [
    ({T.OA + 'A1': [T.OA + 'W1']}, True),
    ({T.OA + 'A1': [T.OA + 'W2']}, False),
    ({T.OA + 'A2': [T.OA + 'W1']}, False),
    ({}, False), (None, False), ([], False),
    ({T.OA + 'A1': T.OA + 'W1'}, False),
    ({T.OA + 'A1': [T.OA + 'W1', 42]}, False),
    ({T.OA + 'A1': ['W1']}, False),
])
def test_exact_pair_and_malformed_scope(scope, accepted):
    ctx = SimpleNamespace(reviewed_oa={'Ada Lovelace': {T.OA + 'A1'}},
                          ov={'Ada Lovelace': {'openalex_work_scope': scope}})
    assert bool(identity.reviewed_author_matches(ctx, 'Ada Lovelace', {'id': T.OA + 'W1'}, T.OA + 'A1')) is accepted
    assert not identity.reviewed_author_matches(ctx, 'Ada Lovelace', {'id': T.OA + 'W1'}, T.OA + 'A2')


def test_legacy_unscoped_review_still_matches():
    ctx = SimpleNamespace(reviewed_oa={'Ada Lovelace': {T.OA + 'A1'}})
    assert identity.reviewed_author_matches(ctx, 'Ada Lovelace', {'id': T.OA + 'W2'}, T.OA + 'A1')


def test_work_scoped_review_does_not_block_another_pi_from_a_mixed_cluster(tmp_path):
    ctx = context(tmp_path, ['Hao Zhang'])
    ctx.pis[0]['reviewedOpenAlex'] = [T.OA + 'A1']
    ctx.pis.append(dict(pi='Hao Zhang II', reviewedOpenAlex=[], orcid=[], notOpenAlex=[], mixedOpenAlex=[]))
    ctx.ov = {'Hao Zhang': {'openalex_work_scope': {T.OA + 'A1': [T.OA + 'W1']}}}
    identity.id_sets(ctx)
    assert T.OA + 'A1' not in ctx.blocked['Hao Zhang II']
    ctx.ov = {}
    identity.id_sets(ctx)
    assert T.OA + 'A1' in ctx.blocked['Hao Zhang II']


@pytest.mark.usefixtures('layout')
def test_scoped_review_cannot_spread_by_name_surname_or_own_works(tmp_path, monkeypatch):
    ctx = context(tmp_path, ['Hao Zhang'])
    ctx.pis[0]['reviewedOpenAlex'] = [T.OA + 'A1']
    ctx.ov = {'Hao Zhang': {'openalex_work_scope': {T.OA + 'A1': [T.OA + 'W1']}}}
    good = T.work('W1', 'Verified email and named affiliation on this paper', 2020, [T.au('Hao Zhang', 'A1')])
    unreviewed = T.work('W2', 'An unverified same name under this mixed ID', 2021, [T.au('Hao Zhang', 'A1')])
    surname = T.work('W3', 'An unverified surname fallback', 2021, [T.au('H. Zhang', 'A1')])
    own = T.work('W4', 'An unverified work outside the sweep', 2021, [T.au('Hao Zhang', 'A1')])
    db = sqlite3.connect(P.data_w('pi-works.sqlite', T.SCHOOL, root=tmp_path))
    db.execute('create table works (id text primary key, body blob)')
    db.execute('create table pages (work text,url text,status text,pdf_sha256 text,page1 blob,school_named int,quote text)')
    db.execute('insert into works values (?,?)', (own['id'], zlib.compress(json.dumps(own).encode())))
    db.commit()
    db.close()
    monkeypatch.setattr(identity, 'sweep_works', lambda *args: iter([good, unreviewed, surname]))
    monkeypatch.setattr(identity, 'authorship_identity', lambda c, p, w, a, cw:
                        'reviewed_openalex_author_id' if identity.reviewed_author_matches(c, p, w, a['author']['id']) else None)
    identity.hits(ctx)
    assert [(h[1]['id'], h[4]) for h in ctx.hits if h[4]] == [(good['id'], 'reviewed_openalex_author_id')]
    assert not ctx.anchored['Hao Zhang']
