"""Reviewed metadata cannot become identity, repair contradictions or merge same-title works."""
import copy
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

import atlas_paths as P
import test_build_rules as T
from pihier import identity, title_enrichment as E

PID = 'https://dblp.org/pid/example/AdaLovelace'


def work(title=None):
    return T.work('W501', title, 2020, [T.au('Ada Lovelace', 'A1'), T.au('Alan Turing', 'A9')], doi='10.9/source')


def row(w):
    return dict(pi='Ada Lovelace', oa=w['id'], work=None, doi=w['doi'], title=w['title'], year=2020,
                date=w['publication_date'], byline=['Ada Lovelace', 'Alan Turing'], byline_school=['Ada Lovelace'],
                identity='reviewed_openalex', appointment={'periodId': 'p'}, editions=[])


def review(w, title='A Complete Research Article', r=None):
    r = r or row(w)
    pub = dict(url='https://publisher.example/article.pdf', sha256='a' * 64, bytes=1000, pages=10,
               complete_body=True, full_parse_returncode=0, doi=w['doi'], title=title, year=2020,
               byline=['Ada Lovelace', 'Alan Turing'], title_quote=title,
               publication_quote='Published 2020', byline_quote='Ada Lovelace Alan Turing')
    return dict(id='review:1', pi='Ada Lovelace', reviewed_by='reviewer', reviewed_at='2026-11-08',
                match={k: r[k] for k in ('oa', 'work', 'doi')}, title=title, edition_binding='exact_doi',
                edition_preimage_sha256=E.preimage_sha256(r['editions']), publisher=pub,
                owned_dblp=dict(pid=PID, key='journals/example/Ada20', sha256='b' * 64, doi=w['doi'], title=title,
                                year=2020, byline=pub['byline']),
                source_preimages=[dict(work_sha256=E.preimage_sha256(w), capture_sha256='c' * 64,
                                       origin='reviewed original source', original_title=w['title'],
                                       byline=[a['raw_author_name'] for a in w['authorships']])])


def context(tmp_path, w, reviews):
    ctx = SimpleNamespace(here=tmp_path, school=T.SCHOOL, n=Counter(),
                          pid0={'Ada Lovelace': dict(dblp=[PID])})
    P.data_w('paper-title-review.json', T.SCHOOL, root=tmp_path).write_text(json.dumps(
        dict(version=1, school=T.SCHOOL, reviews=reviews)))
    E.remember(ctx, row(w), w)
    return ctx


def apply(ctx, r):
    return E.apply(ctx, [r], lambda w, title, row: row['date'])[0][0]


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('old', [None, '', ' \t\n'])
def test_missing_only_fill_preserves_raw_and_every_other_scientific_field(tmp_path, old):
    w = work(old); r = row(w); before_w, before_r = copy.deepcopy(w), copy.deepcopy(r)
    ctx = context(tmp_path, w, [review(w)])
    result = apply(ctx, r)
    assert result['title'] == 'A Complete Research Article'
    assert result['titleEnrichment']['status'] == 'filled'
    assert {k: v for k, v in result.items() if k not in ('title', 'titleEnrichment')} == {k: v for k, v in before_r.items() if k != 'title'}
    assert w == before_w and r == before_r


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('field,value,reason', [
    ('publisher.byline', [], 'missing_or_changed_byline'),
    ('publisher.complete_body', False, 'incomplete_source_proof'),
    ('publisher.doi', '10.9/another', 'edition_or_doi_mismatch'),
    ('owned_dblp.byline', ['Alan Turing', 'Ada Lovelace'], 'publisher_dblp_byline_mismatch'),
    ('owned_dblp.pid', 'https://dblp.org/pid/another', 'not_owned_dblp'),
    ('publisher.year', 2019, 'source_year_mismatch'),
    ('publisher.title', 'A Different Paper', 'competing_source_titles'),
    ('edition_binding', None, 'edition_or_doi_mismatch'),
    ('edition_preimage_sha256', None, 'edition_preimage_mismatch'),
    ('publisher.title_quote', None, 'missing_frontmatter_quotes'),
    ('publisher.publication_quote', 'No publication date given', 'missing_frontmatter_quotes'),
    ('publisher.byline_quote', 'Ada Lovelace', 'missing_byline_quote'),
    ('publisher.byline_quote', 'Alan Turing Ada Lovelace', 'publisher_byline_quote_order'),
])
def test_source_quality_and_identity_ambiguities_hold(tmp_path, field, value, reason):
    w = work(); d = review(w); parts = field.split('.');target = d
    for p in parts[:-1]:
        target = target[p]
    target[parts[-1]] = value
    ctx = context(tmp_path, w, [d]); result = apply(ctx, row(w))
    assert result['title'] is None and reason in result['titleEnrichment']['reasons']


@pytest.mark.usefixtures('layout')
def test_nonempty_dense_hmm_metadata_is_never_overwritten(tmp_path):
    w = work('A Contradictory Nonempty Dense Model Title'); d = review(w, 'A Hidden Markov Model Paper')
    ctx = context(tmp_path, w, [d]); r = apply(ctx, row(w))
    assert r['title'] == w['title'] and r['titleEnrichment']['status'] == 'unchanged_nonempty'


@pytest.mark.usefixtures('layout')
def test_same_title_or_doi_on_another_work_is_not_a_selector(tmp_path):
    w = work(); d = review(w); d['match']['oa'] = T.OA + 'W999'
    ctx = context(tmp_path, w, [d]); assert apply(ctx, row(w)) == row(w)


@pytest.mark.usefixtures('layout')
def test_all_exact_candidates_checked_competing_review_cannot_hide_behind_first(tmp_path):
    w = work(); a = review(w); b = review(w, 'A Different Wrong DOI Work'); b['id'] = 'review:2'; b['match']['doi'] = '10.9/wrong'
    ctx = context(tmp_path, w, [a, b]); r = apply(ctx, row(w))
    assert r['title'] is None and set(r['titleEnrichment']['reasons']) == {'doi_mismatch', 'competing_reviews'}


@pytest.mark.usefixtures('layout')
def test_source_capture_or_preimage_change_and_new_edition_are_held(tmp_path):
    w = work(); d = review(w); ctx = context(tmp_path, w, [d]); ctx._title_sources[E._key(row(w))] = dict(w, publication_date='2020-08-03')
    assert 'source_preimage_mismatch' in apply(ctx, row(w))['titleEnrichment']['reasons']
    ctx = context(tmp_path, w, [review(w)]); r = row(w); r['editions'] = [dict(oa=T.OA + 'W777', doi='10.9/other')]
    assert 'edition_preimage_mismatch' in apply(ctx, r)['titleEnrichment']['reasons']
    d = review(w);d['source_preimages'][0]['capture_sha256']='bad';ctx=context(tmp_path,w,[d])
    assert 'source_preimage_mismatch' in apply(ctx,row(w))['titleEnrichment']['reasons']


@pytest.mark.usefixtures('layout')
def test_approved_existing_alias_and_reviewed_spelling_never_change_output_byline(tmp_path):
    w = work();w['authorships'][1]['raw_author_name']='Alan Typo';r=row(w);r['byline'][1]='Alan Typo';r['editions']=[dict(oa=T.OA+'W777',doi=w['doi'])]
    d=review(w,r=r);d['reviewed_spelling_bindings']=[dict(source='Alan Typo',publisher='Alan Turing',evidence_sha256='a'*64)]
    ctx=context(tmp_path,w,[d]);E.remember(ctx,r,w);out=apply(ctx,r)
    assert out['titleEnrichment']['status']=='filled' and out['editions']==r['editions'] and out['byline']==r['byline']


@pytest.mark.usefixtures('layout')
def test_title_cannot_change_publication_date_or_bypass_an_identity_hold(tmp_path):
    w=work();ctx=context(tmp_path,w,[review(w)])
    out=E.apply(ctx,[row(w)],lambda w,t,r:'2004')[0][0];assert out['title'] is None and 'would_change_date' in out['titleEnrichment']['reasons']
    ctx=context(tmp_path,w,[review(w)]);ctx.pid0['Ada Lovelace']['identityHold']={'reason':'unresolved'}
    assert 'not_eligible_identity' in apply(ctx,row(w))['titleEnrichment']['reasons']


@pytest.mark.usefixtures('layout')
def test_native_enrichment_after_grouping_cannot_create_alias_or_verified_member(tmp_path,monkeypatch):
    monkeypatch.setattr(identity,'DUMP_PERSONS',None)
    w=work();other=T.work('W502','A Complete Research Article',2020,[T.au('Ada Lovelace','A1'),T.au('Alan Turing','A9')],doi='10.9/different')
    T.write_school(tmp_path,sweep=[w,other]);d=review(w)
    overrides=copy.deepcopy(T.OVERRIDES);overrides[T.SCHOOL]['Ada Lovelace']['dblp']=[PID]
    T.put(tmp_path,'census-overrides.json',None).write_text(json.dumps(overrides))
    P.data_w('paper-title-review.json',T.SCHOOL,root=tmp_path).write_text(json.dumps(dict(version=1,school=T.SCHOOL,reviews=[d])))
    input_path=P.data('paper-title-review.json',T.SCHOOL,root=tmp_path)
    saved=input_path.read_bytes();input_path.unlink()
    before=T.run_stages(tmp_path,upto='links')
    input_path.write_bytes(saved)
    ctx=T.run_stages(tmp_path,upto='links');rows=[r for r in ctx.rows if r['pi']=='Ada Lovelace']
    assert ctx.sp==before.sp and any(s['status']=='candidate' for s in ctx.sp)
    assert len(rows)==2 and not any(r.get('editions') for r in rows)
    assert next(r for r in rows if r['oa']==w['id'])['title']=='A Complete Research Article'


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('title,kind', [('Obituary: Remembering a Colleague','article'),('Einführung der Algorithmen','book')])
def test_native_reruns_ordinary_quality_after_title_recovery(tmp_path,monkeypatch,title,kind):
    monkeypatch.setattr(identity,'DUMP_PERSONS',None);w=work();w['type']=kind;T.write_school(tmp_path,sweep=[w]);d=review(w,title)
    overrides=copy.deepcopy(T.OVERRIDES);overrides[T.SCHOOL]['Ada Lovelace']['dblp']=[PID];T.put(tmp_path,'census-overrides.json',None).write_text(json.dumps(overrides))
    P.data_w('paper-title-review.json',T.SCHOOL,root=tmp_path).write_text(json.dumps(dict(version=1,school=T.SCHOOL,reviews=[d])))
    ctx=T.run_stages(tmp_path,upto='papers');assert not T.rows_of(ctx,'Ada Lovelace') and ctx.n['title_enrichment_quality_dropped']==1
    assert ctx.paper_title_review['decisions'][0]['quality_status']=='rejected'
    if kind=='book':
        assert ctx.n['translated_editions_dropped']==1


@pytest.mark.usefixtures('layout')
def test_native_output_and_report_preserve_validated_enrichment_provenance(tmp_path,monkeypatch):
    import provenance
    import schema_check
    from pihier import build
    monkeypatch.setattr(identity,'DUMP_PERSONS',None);w=work();T.write_school(tmp_path,sweep=[w])
    overrides=copy.deepcopy(T.OVERRIDES);overrides[T.SCHOOL]['Ada Lovelace']['dblp']=[PID]
    T.put(tmp_path,'census-overrides.json',None).write_text(json.dumps(overrides))
    P.data_w('paper-title-review.json',T.SCHOOL,root=tmp_path).write_text(json.dumps(dict(version=1,school=T.SCHOOL,reviews=[review(w)])))
    ctx=T.run_stages(tmp_path);ctx.out=tmp_path/'out';ctx.out.mkdir()
    monkeypatch.setattr(provenance,'block',lambda school:{})
    build.write(ctx)
    schemas=Path(__file__).resolve().parents[1]/'schemas'
    assert schema_check.validate_file(ctx.out/'lab_papers.jsonl.gz',json.loads((schemas/'lab_papers.schema.json').read_text()))==[]
    report=json.loads((ctx.out/'report.json').read_text())
    report_schema=json.loads((schemas/'report.schema.json').read_text())
    # This stage fixture omits unrelated production provenance/count fields. Validate the actual new output subtree.
    assert schema_check.validate(report['paperTitleReview'],report_schema['properties']['paperTitleReview'])==[]
    assert report['paperTitleReview']['decisions'][0]['quality_status']=='passed'
    assert report['counts']['title_enrichment_filled']==1


@pytest.mark.usefixtures('layout')
def test_a_candidate_identity_is_never_upgraded_by_a_title(tmp_path):
    w=work();ctx=context(tmp_path,w,[review(w)]);r=row(w);r['identity']='candidate'
    assert 'not_eligible_identity' in apply(ctx,r)['titleEnrichment']['reasons']


@pytest.mark.nfs
def test_all_eight_reviewed_toc_sources_replay_exactly_without_other_field_changes(tmp_path):
    code=Path(__file__).resolve().parents[1]
    packet=P.SCRATCH/'toc-missing-title-review-1108/local-sources.json'
    variants=P.SCRATCH/'missing-title-enrichment-1108'
    if not packet.exists() or not (variants/'input-preparation.json').exists():
        pytest.skip('original immutable eight-paper source packet not available')
    cases=json.loads(packet.read_text());assert len(cases)==8
    tested=0
    for doi,x in cases.items():
        school=x['input']['school'];pi=x['input']['pi'];oa=x['input']['oa']
        source_path=P.data('paper-title-review.json',school,root=code,layout='split')
        if not source_path.exists():
            pytest.skip('reviewed eight-paper input proposals unavailable')
        data=json.loads(source_path.read_text())
        P.data_w('paper-title-review.json',school,root=tmp_path).write_text(json.dumps(data))
        d=next(r for r in data['reviews'] if r['pi']==pi and r['match']['doi']==doi)
        for w in json.loads((variants/(oa.rsplit('/',1)[-1]+'.source-variants.json')).read_text()):
            r=copy.deepcopy(next(r for r in x['canonical'] if r['pi']==pi))
            r.update(title=w['title'],date=w['publication_date'],year=w['publication_year'],byline=[a.get('raw_author_name') or a['author']['display_name'] for a in w['authorships']])
            ctx=SimpleNamespace(here=tmp_path,school=school,n=Counter(),pid0={pi:dict(dblp=[d['owned_dblp']['pid']])})
            before=copy.deepcopy(r);source_before=copy.deepcopy(w);E.remember(ctx,r,w)
            out=E.apply(ctx,[r],lambda w,t,r:w['publication_date'])[0][0]
            assert out['titleEnrichment']['status']=='filled', (pi,out['titleEnrichment'])
            assert out['title']==d['title']
            assert {k:v for k,v in out.items() if k not in ('title','titleEnrichment')}=={k:v for k,v in before.items() if k!='title'}
            assert w==source_before and r==before
            tested+=1
    assert tested==12
