"""Exact full-source title authority repairs R16 identity without borrowing metadata or admitting a source."""
import copy
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

import atlas_paths as P
import test_build_rules as T
from pihier import identity, papers, source_metadata as M, title_enrichment

FIXTURE = Path(__file__).parent / 'fixtures/source_metadata_review.json'


def cases():
    d = json.loads(FIXTURE.read_text())
    assert M.digest(d['cases']) == d['projection_sha256']
    for c in d['cases']:
        assert M.digest(c['owned_publication']) == c['production_owned_publication_sha256']
    return copy.deepcopy(d['cases'])


def row(c):
    w = c['source_projection']
    return dict(pi=c['pi'], oa=w['id'], work=None, doi=w['doi'].removeprefix('https://doi.org/'),
                title=w['title'], year=w['publication_year'], date=w['publication_date'], type=w['type'],
                byline=[a['raw_author_name'] for a in w['authorships']], byline_school=['Zhenhua Li'],
                authorship=dict(raw_name='Zhenhua Li'), identity='dblp_person_page_doi', appointment={'periodId': 'reviewed'})


def review(c):
    w = c['source_projection']; pub = c['owned_publication']
    return dict(id='review:'+pub['key'], pi=c['pi'], decision='owned_publication_title', reviewed_by='reviewer',
                reviewed_at='2026-11-08', match=dict(oa=w['id'], doi=w['doi'].removeprefix('https://doi.org/'), work=None),
                source=dict(work_sha256=M.digest(w), original_title=w['title'], ordered_byline=row(c)['byline']),
                owned_dblp=dict(pid=c['pid'], key=pub['key'], record_sha256=M.digest(pub)),
                changes=dict(title=c['expected_title']), evidence={})


def context(tmp_path, cs, reviews=None):
    by_pi = {c['pi']: dict(pi=c['pi'], dblp=[c['pid']]) for c in cs}
    persons = {}
    for c in cs:
        persons.setdefault(c['pid'], dict(pubs=[]))['pubs'].append(c['owned_publication'])
    ctx = SimpleNamespace(here=tmp_path, school='tsinghua', pid0=by_pi, n=Counter(),
                          dblp_persons=dict(persons=persons), hits=[(c['pi'], c['source_projection']) for c in cs])
    P.data_w('paper-source-review.json', ctx.school, root=tmp_path).write_text(json.dumps(dict(
        version=1, school=ctx.school, reviews=reviews if reviews is not None else [review(c) for c in cs])))
    return ctx


@pytest.mark.usefixtures('layout')
def test_actual_two_experience_sources_split_before_fixed_r16_components_and_preserve_whole_sources(tmp_path):
    cs = cases(); rows = [row(c) for c in cs]; before = copy.deepcopy((cs, rows)); ctx = context(tmp_path, cs)
    old = papers.merge_editions(papers.collapse_eligible_sources(copy.deepcopy(rows), Counter()), Counter())
    assert len(old) == 1 and len(old[0]['editions']) == 1
    corrected = M.apply(ctx, rows, lambda w, title, r: r['date'])
    out = papers.merge_editions(papers.collapse_eligible_sources(corrected, Counter()), Counter())
    assert len(out) == 2 and not any(r['editions'] for r in out)
    assert {r['title'] for r in out} == {c['expected_title'] for c in cs}
    assert (cs, rows) == before
    for oldrow, newrow, decision in zip(rows, corrected, ctx.paper_source_review['decisions']):
        assert decision['status'] == 'projected'
        assert decision['original_complete_source'] == next(c['source_projection'] for c in cs if c['pi'] == oldrow['pi'] and c['source_projection']['id'] == oldrow['oa'])
        assert decision['original_eligible_row'] == oldrow
        assert {k: v for k, v in newrow.items() if k not in ('title', 'sourceMetadataReviews')} == {k: v for k, v in oldrow.items() if k != 'title'}


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('fault,reason', [
    ('source_hash', 'missing_complete_source'), ('doi', 'selector_mismatch'), ('pid', 'not_owned_pid'),
    ('key', 'owned_publication_preimage_changed'), ('record_hash', 'owned_publication_preimage_changed'),
    ('title', 'owned_publication_title_mismatch'), ('reorder', 'owned_ordered_byline_mismatch'),
    ('wrong_author', 'owned_ordered_byline_mismatch'), ('raw_change', 'missing_complete_source'),
    ('identity_hold', 'not_eligible_identity_or_appointment'), ('missing_original', 'missing_complete_source'),
    ('date', 'would_change_ordinary_date'),
])
def test_exact_source_and_owned_publication_guards_hold_without_changing_original_or_lending_fields(tmp_path, fault, reason):
    c = cases()[0]; d = review(c); r = row(c); date = r['date']
    if fault == 'source_hash': d['source']['work_sha256'] = '0' * 64
    elif fault == 'doi': d['match']['doi'] = '10.9/unrelated'
    elif fault == 'pid': d['owned_dblp']['pid'] = 'https://dblp.org/pid/unowned'
    elif fault == 'key': d['owned_dblp']['key'] = 'conf/other/Another'
    elif fault == 'record_hash': d['owned_dblp']['record_sha256'] = '0' * 64
    elif fault == 'title': d['changes']['title'] = 'An Unrelated Research Title'
    elif fault in ('reorder', 'wrong_author'):
        if fault == 'reorder': c['source_projection']['authorships'][:2] = list(reversed(c['source_projection']['authorships'][:2]))
        else: c['source_projection']['authorships'][0]['raw_author_name'] = 'Entirely Different'
        r = row(c);d['source']['work_sha256'] = M.digest(c['source_projection']);d['source']['ordered_byline'] = r['byline']
    ctx = context(tmp_path, [c], [d])
    if fault == 'raw_change': c['source_projection']['publication_date'] = '2001-01-01'
    if fault == 'identity_hold': ctx.pid0[c['pi']]['identityHold'] = {'reason': 'unresolved person'}
    if fault == 'missing_original': ctx.hits = []
    before = copy.deepcopy((c, r))
    got = M.apply(ctx, [r], lambda w, title, row: '2001' if fault == 'date' else date)
    assert got == [r] and (c, r) == before
    assert ctx.paper_source_review['decisions'][0]['status'] == 'held'
    assert ctx.paper_source_review['decisions'][0]['reason'] == reason


@pytest.mark.usefixtures('layout')
def test_compact_edition_pointer_cannot_reconstruct_absent_source_or_admit_ineligible_paper(tmp_path):
    c = cases()[0];ctx = context(tmp_path, [c]);ctx.hits = []
    r = row(c);r['editions'] = [dict(oa=r['oa'], doi=r['doi'])]
    assert M.apply(ctx, [r], lambda w, t, r: r['date']) == [r]
    ctx = context(tmp_path, [c]);assert M.apply(ctx, [], lambda w, t, r: '') == []
    assert ctx.paper_source_review['decisions'][0]['status'] == 'no_eligible_source'


@pytest.mark.usefixtures('layout')
def test_title_only_contract_and_nonempty_boundary_leave_v1_unchanged(tmp_path):
    c = cases()[0];d = review(c);d['changes']['type'] = 'book'
    ctx = context(tmp_path, [c], [d])
    with pytest.raises(ValueError, match='title-only'): M.apply(ctx, [row(c)], lambda w, t, r: r['date'])
    assert not title_enrichment.missing(c['source_projection']['title'])


def native_setup(tmp_path):
    pid = 'https://dblp.org/pid/example/Ada'; ws=[];cs=[]
    for i in range(2):
        w=T.work('W900'+str(i),'Truncated Header',2020,[T.au('Ada Lovelace','A1'),T.au('Alan Turing','A9')],doi='10.9/source'+str(i))
        pub=dict(key='conf/example/Ada20'+str(i),dois=[w['doi']],title='Truncated Header: A Specific Research Article '+str(i),type='inproceedings',year=2020,authors=[['Ada Lovelace',None],['Alan Turing',None]])
        cs.append(dict(pi='Ada Lovelace',pid=pid,source_projection=w,owned_publication=pub,expected_title=pub['title']));ws.append(w)
    T.write_school(tmp_path,sweep=ws);over=copy.deepcopy(T.OVERRIDES);over[T.SCHOOL]['Ada Lovelace']['dblp']=[pid]
    T.put(tmp_path,'census-overrides.json',None).write_text(json.dumps(over))
    P.data_w('dblp-dump-persons-school.json.gz',T.SCHOOL,root=tmp_path).write_bytes(__import__('gzip').compress(json.dumps(dict(persons={pid:dict(names=['Ada Lovelace'],pubs=[c['owned_publication'] for c in cs])},by_name={})).encode()))
    return cs


@pytest.mark.usefixtures('layout')
def test_native_pre_group_hook_separates_papers_and_keeps_member_identity_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(identity,'DUMP_PERSONS',None);cs=native_setup(tmp_path)
    before=T.run_stages(tmp_path,upto='links');assert len(before.rows)==1
    path=P.data_w('paper-source-review.json',T.SCHOOL,root=tmp_path);path.write_text(json.dumps(dict(version=1,school=T.SCHOOL,reviews=[review(c) for c in cs])))
    raw=path.read_bytes();ctx=T.run_stages(tmp_path,upto='links')
    assert len(ctx.rows)==2 and all(not r['editions'] for r in ctx.rows)
    assert {r['title'] for r in ctx.rows}=={c['expected_title'] for c in cs}
    assert ctx.n['source_metadata_projected']==2 and ctx.n['source_metadata_held']==0
    assert ctx.stu==before.stu and ctx.sp and all(r['status']=='candidate' for r in ctx.sp)
    assert all(len(r['byline'])==2 and r['appointment']=={'periodId':'reviewed:ada-lovelace:1'} for r in ctx.rows)
    assert path.read_bytes()==raw


@pytest.mark.usefixtures('layout')
def test_review_provenance_survives_when_corrected_full_source_is_not_lead(tmp_path):
    c=cases()[0];ctx=context(tmp_path,[c]);reviewed=M.apply(ctx,[row(c)],lambda w,t,r:r['date'])[0]
    published=dict(row(c),oa='https://openalex.org/W99999',doi='10.9/published',title=c['expected_title'],_edition_source={'is_published':True})
    out=papers.merge_editions(papers.collapse_eligible_sources([reviewed,published],Counter()),Counter())
    assert len(out)==1 and out[0]['oa']==published['oa']
    assert out[0]['sourceMetadataReviews']==reviewed['sourceMetadataReviews']


@pytest.mark.usefixtures('layout')
def test_optional_input_noop_and_schema_contracts(tmp_path):
    from schema_check import validate
    c=cases()[0];r=row(c);ctx=SimpleNamespace(here=tmp_path,school='tsinghua')
    assert M.apply(ctx,[r],lambda w,t,r:r['date'])[0] is r
    ctx=context(tmp_path,[c]);out=M.apply(ctx,[r],lambda w,t,r:r['date'])
    schemas=Path(__file__).parents[1]/'schemas'
    assert validate(json.loads(P.data('paper-source-review.json','tsinghua',root=tmp_path).read_text()),json.loads((schemas/'paper_source_review.schema.json').read_text())) == []
    assert validate(out[0]['sourceMetadataReviews'],json.loads((schemas/'lab_papers.schema.json').read_text())['properties']['sourceMetadataReviews']) == []
    assert validate(ctx.paper_source_review,json.loads((schemas/'report.schema.json').read_text())['properties']['paperSourceReview']) == []


@pytest.mark.usefixtures('layout')
def test_owned_bibliographic_year_cannot_force_an_ordinary_date(tmp_path):
    c=cases()[0];c['owned_publication']['year']=2021;ctx=context(tmp_path,[c]);r=row(c)
    out=M.apply(ctx,[r],lambda w,t,r:r['date'])[0]
    assert out['year']==2022 and out['date']==r['date']
    assert ctx.dblp_persons['persons'][c['pid']]['pubs'][0]['year']==2021
    assert ctx.paper_source_review['decisions'][0]['status']=='projected'


@pytest.mark.usefixtures('layout')
def test_complete_unrelated_nonempty_title_is_not_a_completion_even_with_same_owned_doi(tmp_path):
    c=cases()[0];c['source_projection']['title']='An Entirely Different Study';ctx=context(tmp_path,[c]);r=row(c)
    assert M.apply(ctx,[r],lambda w,t,r:r['date'])==[r]
    assert ctx.paper_source_review['decisions'][0]['reason']=='not_a_title_completion'


@pytest.mark.usefixtures('layout')
def test_native_explicit_person_hold_is_not_rescued_by_owned_title_input(tmp_path, monkeypatch):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None); cs = native_setup(tmp_path)
    P.data_w('paper-source-review.json', T.SCHOOL, root=tmp_path).write_text(json.dumps(dict(version=1, school=T.SCHOOL, reviews=[review(c) for c in cs])))
    ctx = T.run_stages(tmp_path, upto='hits'); ctx.pid0['Ada Lovelace']['identityHold'] = {'reason': 'unresolved namesake'}
    papers.lab_papers(ctx)
    assert not ctx.rows and ctx.n['paper_rows_withheld_by_identity_review'] == 2
    assert all(d['status'] == 'no_eligible_source' for d in ctx.paper_source_review['decisions'])
