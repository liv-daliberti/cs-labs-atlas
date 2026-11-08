"""Exact publisher projections repair the whole source without lending another edition's identity."""
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

import atlas_paths as P
from pihier import papers, recovery_reviews as R

FIXTURE = Path(__file__).parent / 'fixtures/recovery-review-ryan.json'


def case():
    value = json.loads(FIXTURE.read_text())
    assert R.digest({k: v for k, v in value.items() if k != 'projection_sha256'}) == value['projection_sha256']
    return value


def context(tmp_path, c):
    p = dict(pi=c['source']['pi'], names=[c['source']['pi']], dblp=[c['pid']],
             periods=[dict(id='source-period', start='2016', end=None, asof='2026-11-08')], listings=[])
    ctx = SimpleNamespace(school='cmu', here=tmp_path, n=Counter(), _recovery_reviews=[copy.deepcopy(c['review'])],
                          dblp_persons=dict(persons={c['pid']: copy.deepcopy(c['person'])}),
                          dblp_page_ranges={c['review']['dblp_key']: '34:1-34:12'}, hits=[], pid0={p['pi']: p},
                          cwork=lambda w: 'conference-cw' if w.get('doi') == '10.4230/lipics.itcs.2019.34' else None)
    return ctx, p


def test_actual_full_publisher_projection_preserves_history_and_exact_identity(tmp_path):
    c = case(); ctx, p = context(tmp_path, c); original = copy.deepcopy((c, p, ctx.dblp_persons))
    result = R.project(ctx, p, c['source'], 'dblp')
    assert (c, p, ctx.dblp_persons) == original
    assert result['year'] == 2019 and c['source']['year'] == 2018
    assert result['byline'] == ['Yuval Filmus', 'Ryan O’Donnell', 'Xinyu Wu']
    assert result['doi'] == '10.4230/lipics.itcs.2019.34'
    assert result['dblp_key'] == 'https://dblp.org/rec/conf/innovations/FilmusOW19'
    assert 'oa' not in result['evidence']  # journal OA is historical evidence, not a conference alias
    assert result['evidence']['basis'] == 'page1_open'
    assert result['evidence']['quotes'] == [c['review']['publisher']['authors'][1]['quote']]
    assert result['arxiv'] == '1809.03546'  # actual publisher Related Version, not an invented provider record
    report = ctx.recovery_source_review['decisions'][0]
    assert report['original'] == c['source'] and report['projected'] == result
    assert report['original_sha256'] == R.digest(c['source'])


@pytest.mark.parametrize('fault', ['source', 'pid', 'pubkey', 'pubrecord', 'doi', 'title', 'year', 'order', 'missing_author',
                                  'duplicate_author', 'wrong_school', 'coherent_wrong_school', 'borrowed_block', 'missing_block', 'partial_pdf',
                                  'pdf_hash', 'excerpt', 'unapproved', 'competing'])
def test_changed_wrong_or_partial_proof_holds_only_targeted_source(tmp_path, fault):
    c = case(); ctx, p = context(tmp_path, c); d = ctx._recovery_reviews[0]; pub = d['publisher']
    if fault == 'source':
        c['source']['evidence']['school_via'].append('different observation')
    elif fault == 'pid':
        p['dblp'] = ['https://dblp.org/pid/someone-else']
    elif fault == 'pubkey':
        d['owned_dblp']['key'] = 'conf/other/Other'
    elif fault == 'pubrecord':
        ctx.dblp_persons['persons'][c['pid']]['pubs'][0]['year'] = 2022
    elif fault in {'doi', 'title', 'year'}:
        pub[fault] = {'doi': '10.1214/22-ejp749', 'title': 'Different publication', 'year': 2018}[fault]
    elif fault == 'order':
        pub['authors'].reverse()
    elif fault == 'missing_author':
        pub['authors'].pop()
    elif fault == 'duplicate_author':
        pub['authors'].append(copy.deepcopy(pub['authors'][0]))
    elif fault == 'wrong_school':
        pub['authors'][1]['affiliation'] = 'Technion – Israel Institute of Technology'
    elif fault == 'coherent_wrong_school':
        old = pub['authors'][1]['affiliation']; new = 'Department of Computer Science, Technion, Haifa, Israel'
        original_quote = pub['authors'][1]['quote']
        pub['authors'][1]['affiliation'] = new
        pub['authors'][1]['quote'] = original_quote.replace(old, new)
        pub['page1_excerpt'] = pub['page1_excerpt'].replace(original_quote, pub['authors'][1]['quote'])
        pub['excerpt_sha256'] = R.digest(pub['page1_excerpt'])
    elif fault == 'borrowed_block':
        pub['authors'][1]['quote'] = '\n'.join(b['quote'] for b in pub['authors'])
    elif fault == 'missing_block':
        pub['authors'][1]['quote'] = pub['authors'][1]['name']
    elif fault == 'partial_pdf':
        pub['complete_body'] = False
    elif fault == 'pdf_hash':
        pub['sha256'] = 'not a hash'
    elif fault == 'excerpt':
        pub['page1_excerpt'] += 'unreviewed'
    elif fault == 'unapproved':
        d['decision'] = 'proposal'
    else:
        ctx._recovery_reviews.append(copy.deepcopy(d))
    original = copy.deepcopy((c['source'], p, ctx.dblp_persons, ctx._recovery_reviews))
    assert R.project(ctx, p, c['source'], 'dblp') is None
    assert (c['source'], p, ctx.dblp_persons, ctx._recovery_reviews) == original
    assert ctx.recovery_source_review['decisions'][0]['status'] == 'held'
    if fault == 'coherent_wrong_school':
        assert ctx.recovery_source_review['decisions'][0]['reason'] == 'pi_own_school_block_unproven'
    unrelated = dict(c['source'], dblp_key='conf/other/Unrelated')
    assert R.project(ctx, p, unrelated, 'dblp') is unrelated


@pytest.mark.usefixtures('layout')
def test_review_input_uses_standard_path_and_hash_bound_report(tmp_path):
    c = case(); ctx, p = context(tmp_path, c); del ctx._recovery_reviews
    path = P.data('recovery-source-review.json', 'cmu', root=tmp_path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(version=1, school='cmu', reviews=[c['review']])))
    assert R.project(ctx, p, c['source'], 'dblp')['year'] == 2019
    assert ctx.recovery_source_review['path'] == str(path)
    assert len(ctx.recovery_source_review['sha256']) == 64


@pytest.mark.parametrize('fault', [None, 'appointment', 'window', 'identity_owner', 'nonpaper_pages'])
def test_native_recovery_still_obeys_ordinary_gates(tmp_path, monkeypatch, fault):
    c = case(); ctx, p = context(tmp_path, c)
    if fault == 'appointment':
        p['periods'][0]['start'] = '2020'
    elif fault == 'window':
        monkeypatch.setattr(papers, 'WINDOW_START', 2020)
    elif fault == 'identity_owner':
        p['dblp'] = []
    elif fault == 'nonpaper_pages':
        ctx.dblp_page_ranges[c['review']['dblp_key']] = '1'
        # This source remains multi-author under ordinary controls. Force an independently
        # source-backed known nonpaper type to ensure the new projection cannot bypass it.
        c['person']['pubs'][0]['type'] = 'phdthesis'
        ctx.dblp_persons['persons'][c['pid']] = c['person']
    monkeypatch.setattr(papers, 'recovered_source', lambda ctx, kind: [c['source']] if kind == 'dblp' else [])
    rows = []
    papers.recovered_rows(ctx, rows, set())
    assert bool(rows) is (fault is None)
    if rows:
        assert rows[0]['year'] == 2019 and rows[0]['date'] == '2019'
        assert rows[0]['oa'] == 'https://dblp.org/rec/conf/innovations/FilmusOW19'
        assert rows[0]['work'] == 'conference-cw'
        assert rows[0]['authorship']['page1']['pdf_sha256'] == c['review']['publisher']['sha256']
        assert rows[0]['byline'] == ['Yuval Filmus', 'Ryan O’Donnell', 'Xinyu Wu']
        assert papers.drop_not_papers(rows, defaultdict(dict), ctx.n)[0]


def test_no_review_does_not_change_legacy_rows_and_no_journal_merge(tmp_path):
    c = case(); ctx, p = context(tmp_path, c); ctx._recovery_reviews = []
    assert R.project(ctx, p, c['source'], 'dblp') is c['source']
    ctx._recovery_reviews = [c['review']]; conf = R.project(ctx, p, c['source'], 'dblp')
    conf.update(work='conference-cw', oa=conf['dblp_key'], date='2019', type='conference-paper', byline_school=[],
                authorship={}, identity='dblp_person_page', appointment=dict(periodId='source-period'))
    conf.pop('dblp_key'); conf.pop('evidence')
    journal = dict(conf, work='journal-cw', oa='https://openalex.org/W2889877476', year=2022, date='2022',
                   title='Log-Sobolev inequality for the multislice, with applications',
                   doi='10.1214/22-ejp749', type='article')
    original = copy.deepcopy([journal, conf]); n = Counter()
    rows = papers.merge_editions(papers.collapse_eligible_sources([journal, conf], n), n)
    assert len(rows) == 2 and [journal, conf] == original
    assert {r['work'] for r in rows} == {'conference-cw', 'journal-cw'}
    assert all(not r['editions'] for r in rows)
