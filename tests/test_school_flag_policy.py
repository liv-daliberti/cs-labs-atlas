"""A reviewed uncertainty class withholds derived flags, never ordinary paper claims."""
import copy
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

import atlas_paths as P
import schema_check
import test_build_rules as T
from pihier import reviewed_claims as R, school_flag_policy as F
from pihier.primary_affiliations import digest

OA = 'https://openalex.org/'


def policy(**changes):
    value = dict(version=1, school=T.SCHOOL, mode=F.MODE, scope=F.SCOPE, min_authorships=100, min_institution_ids=10,
                 why='Primary examples expose collaboration boundary uncertainty, not universal false affiliations.',
                 reviewed_by='independent reviewer', reviewed_at='2026-11-27',
                 evidence=[dict(url='https://example.edu/original.pdf', sha256='a'*64, quote='Literal primary groups', source_kind='primary_pdf')])
    value.update(changes)
    return value


def setup(tmp_path, rows, selected=None, school=None):
    school = school or T.SCHOOL
    path = P.data_w('paper-claim-review.json', school, root=tmp_path)
    data = dict(version=1, school=school, decisions=[])
    if selected is not None:
        data['derived_school_flags_policy'] = selected
    path.write_text(json.dumps(data))
    ctx = SimpleNamespace(here=tmp_path, school=school, pis=[dict(pi='Ada Lovelace')], n=Counter(), rows=copy.deepcopy(rows))
    R.prepare(ctx)
    return ctx


def work(wid='W1', authors=100, institutions=10):
    return dict(id=OA+wid, doi='10.9/'+wid, title='A large collaboration research paper', authorships=[
        dict(raw_author_name='Author '+str(i), author=dict(id=OA+'A'+str(i), display_name='Author '+str(i)),
             institutions=[dict(id=OA+'I'+str(i % institutions))], raw_affiliation_strings=['Source institution '+str(i % institutions)])
        for i in range(authors)])


def row(wid='W1', **changes):
    value = dict(pi='Ada Lovelace', oa=OA+wid, doi='10.9/'+wid, work=None, title='Paper', year=2020,
                 byline=['Ada Lovelace', 'Other Author'], byline_school=['Ada Lovelace', 'Other Author'],
                 identity='reviewed_openalex_author_id', authorship={'school_via':['Ordinary school proof']},
                 appointment={'periodId':'p'}, editions=[])
    value.update(changes)
    return value


@pytest.mark.usefixtures('layout')
def test_R_PAP_67_uncertainty_holds_flags_only_after_ordinary_admission(tmp_path):
    original = row(_bylines=[(['Ada Lovelace','Other Author'],['Other Author'])])
    ctx = setup(tmp_path, [original], policy()); source = work(); before = copy.deepcopy(source)
    F.observe(ctx, source)
    assert source == before and ctx.rows == [original]
    assert not R.excluded(ctx, 'Ada Lovelace', source)
    R.apply(ctx)
    actual = ctx.rows[0]
    assert actual['byline_school'] == [] and actual['_bylines'] == [(original['byline'], [])]
    assert {k:v for k,v in actual.items() if k not in ('byline_school','_bylines','byline_affiliation_review')} == {
        k:v for k,v in original.items() if k not in ('byline_school','_bylines','byline_affiliation_review')}
    evidence = actual['byline_affiliation_review']
    assert evidence['status'] == 'held' and evidence['scope'] == F.SCOPE
    assert evidence['matched_sources'][0]['source_work_sha256'] == digest(source)
    assert ctx.n['derived_school_flag_policy_claims_held'] == 1
    assert not ctx.n['paper_review_rows_held'] and not ctx.n['paper_review_hits_withheld_before_identity']
    schema = json.loads((Path(__file__).resolve().parents[1]/'schemas/lab_papers.schema.json').read_text())['properties']['byline_affiliation_review']
    assert schema_check.validate(evidence, schema) == []
    for field in ('scope','mode','policy','matched_sources','input_sha256'):
        bad = dict(evidence); del bad[field]
        assert schema_check.validate(bad, schema), field
    report_schema = json.loads((Path(__file__).resolve().parents[1]/'schemas/report.schema.json').read_text())['properties']['derivedSchoolFlagPolicy']
    assert schema_check.validate(ctx.school_flag_policy_summary, report_schema) == []


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('authors,institutions', [(99,10),(100,9),(99,9)])
def test_thresholds_are_count_boundaries_not_a_positive_certification(tmp_path, authors, institutions):
    original = row(); ctx = setup(tmp_path, [original], policy())
    F.observe(ctx, work(authors=authors, institutions=institutions)); R.apply(ctx)
    assert ctx.rows == [original] and not ctx.school_flag_policy_summary['held_claims']


@pytest.mark.usefixtures('layout')
def test_other_school_without_opt_in_keeps_its_ordinary_flags(tmp_path):
    original = row(); ctx = setup(tmp_path, [original], school='mit')
    F.observe(ctx, work()); R.apply(ctx)
    assert ctx.rows == [original] and ctx.school_flag_policy_summary is None


@pytest.mark.usefixtures('layout')
def test_no_policy_and_no_claim_cannot_admit_a_paper(tmp_path):
    ctx = setup(tmp_path, [], policy()); F.observe(ctx, work()); R.apply(ctx)
    assert ctx.rows == [] and not ctx.school_flag_policy_summary['held_claims']


@pytest.mark.usefixtures('layout')
def test_folded_eligible_source_holds_entire_unmapped_claim_without_rekeying(tmp_path):
    original = row('W2', editions=[{'oa':OA+'W1','doi':'10.9/W1'}],
                   _bylines=[(['Lead'],['Lead']),(['Earlier'],['Earlier'])])
    ctx = setup(tmp_path, [original], policy()); F.observe(ctx, work()); R.apply(ctx)
    assert ctx.rows[0]['oa'] == OA+'W2' and ctx.rows[0]['editions'] == original['editions']
    assert ctx.rows[0]['byline_school'] == [] and all(flags == [] for _,flags in ctx.rows[0]['_bylines'])


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('folded', [False,True])
@pytest.mark.parametrize('small_authors,small_institutions', [(2,2),(1,0)])
def test_complete_bound_primary_mapping_survives_and_other_transient_positives_do_not(tmp_path, folded, small_authors, small_institutions):
    source = work(); lead = 'W2' if folded else 'W1'
    lead_source = work(lead,authors=small_authors,institutions=max(1,small_institutions)) if folded else source
    if folded and not small_institutions:
        for a in lead_source['authorships']:a['institutions']=[]
    review = dict(status='accepted',work=OA+lead,source_work_sha256=digest(lead_source),
                  source_authorships_sha256=digest(lead_source['authorships']),pdf_sha256='b'*64,author_blocks=[{'raw_name':'Ada Lovelace'}])
    actual_names = [a['raw_author_name'] for a in lead_source['authorships']]
    original = row(lead, byline=actual_names, byline_school=['Author 0'], byline_affiliation_review=review,
                   editions=[{'oa':OA+'W1'}] if folded else [], _bylines=[(['Earlier'],['Foreign Wrong Positive'])])
    ctx = setup(tmp_path,[original],policy()); F.observe(ctx,source)
    F.record_primary(ctx,lead_source,review,['Author 0']); R.apply(ctx)
    actual = ctx.rows[0]
    assert actual['byline_school'] == ['Author 0'] and actual['byline_affiliation_review'] == review
    assert actual['_bylines'] == [(['Earlier'],[]),(original['byline'],['Author 0'])]
    assert ctx.n['derived_school_flag_policy_primary_mappings_preserved'] == 1


@pytest.mark.usefixtures('layout')
def test_stale_or_incomplete_positive_review_cannot_bypass_uncertainty(tmp_path):
    ctx=setup(tmp_path,[row(byline_affiliation_review={'status':'accepted','work':OA+'W1'})],policy())
    F.observe(ctx,work()); R.apply(ctx)
    assert ctx.rows[0]['byline_school'] == []
    assert ctx.rows[0]['byline_affiliation_review']['prior_derivation']['status'] == 'accepted'


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('change',[{'school':'wrong'},{'scope':'admission'},{'mode':'admit_all'},
    {'min_authorships':True},{'min_institution_ids':0},{'evidence':[]},{'reviewed_at':'yesterday'}])
def test_bad_reviewed_policy_fails_closed(tmp_path,change):
    with pytest.raises(ValueError):setup(tmp_path,[row()],policy(**change))


@pytest.mark.usefixtures('layout')
def test_ordinary_rejection_still_wins_without_policy_admission(tmp_path):
    ctx = setup(tmp_path, [row()], policy())
    path = P.data('paper-claim-review.json', T.SCHOOL, root=tmp_path)
    data = json.loads(path.read_text())
    data['decisions'] = [dict(id='reject',pi='Ada Lovelace',decision='reject',match={'oa':OA+'W1'},
        why='Ordinary source-proven rejection',reviewed_by='reviewer',reviewed_at='2026-11-27',
        evidence=[dict(url='https://example.edu/original',sha256='c'*64,quote='Exact source')])]
    path.write_text(json.dumps(data))
    ctx = SimpleNamespace(here=tmp_path,school=T.SCHOOL,pis=[dict(pi='Ada Lovelace')],n=Counter(),rows=[row()])
    R.prepare(ctx); F.observe(ctx,work()); R.apply(ctx)
    assert not ctx.rows and ctx.n['paper_review_rows_rejected'] == 1
    assert not ctx.school_flag_policy_summary['held_claims']


@pytest.mark.usefixtures('layout')
def test_exact_reviewed_flags_hold_remains_last_and_keeps_policy_provenance(tmp_path):
    ctx = setup(tmp_path,[row()],policy())
    path = P.data('paper-claim-review.json', T.SCHOOL, root=tmp_path)
    data = json.loads(path.read_text())
    data['decisions'] = [dict(id='exact',pi='Ada Lovelace',decision='hold_derived_school_flags',scope=F.SCOPE,
        match={'oa':OA+'W1','doi':'10.9/W1'},why='Exact primary uncertainty reason',reviewed_by='reviewer',reviewed_at='2026-11-27',
        evidence=[dict(url='https://example.edu/original.pdf',sha256='c'*64,quote='Exact source',source_kind='primary_pdf')])]
    path.write_text(json.dumps(data))
    ctx = SimpleNamespace(here=tmp_path,school=T.SCHOOL,pis=[dict(pi='Ada Lovelace')],n=Counter(),rows=[row()])
    R.prepare(ctx); F.observe(ctx,work()); R.apply(ctx)
    assert ctx.rows[0]['byline_school'] == []
    ev = ctx.rows[0]['byline_affiliation_review']
    assert ev['id'] == 'exact' and ev['prior_derivation']['mode'] == F.MODE


@pytest.mark.usefixtures('layout')
def test_changed_review_input_stops_before_any_policy_row_changes(tmp_path):
    original = row(); ctx = setup(tmp_path,[original],policy()); F.observe(ctx,work())
    path = P.data('paper-claim-review.json', T.SCHOOL, root=tmp_path)
    data=json.loads(path.read_text());data['derived_school_flags_policy']['why']='Changed after freeze';path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='changed during the build'):R.apply(ctx)
    assert ctx.rows == [original]


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('mismatch', ['no_resolver_proof','wrong_source_work_digest','wrong_authorship_digest','changed_review','changed_byline','changed_flags'])
def test_folded_class_cannot_trust_stale_or_forged_accepted_small_lead(tmp_path, mismatch):
    big=work();small=work('W2',authors=2,institutions=2)
    review=dict(status='accepted',work=small['id'],source_work_sha256=digest(small),
                source_authorships_sha256=digest(small['authorships']),pdf_sha256='d'*64,author_blocks=[{'raw_name':'Author 0'}])
    names=[a['raw_author_name'] for a in small['authorships']]
    original=row('W2',byline=names,byline_school=['Author 0'],byline_affiliation_review=copy.deepcopy(review),editions=[{'oa':big['id']}])
    ctx=setup(tmp_path,[original],policy());F.observe(ctx,big)
    if mismatch=='wrong_source_work_digest':review['source_work_sha256']='e'*64
    if mismatch=='wrong_authorship_digest':review['source_authorships_sha256']='e'*64
    if mismatch!='no_resolver_proof':F.record_primary(ctx,small,review,['Author 0'])
    if mismatch=='changed_review':ctx.rows[0]['byline_affiliation_review']['pdf_sha256']='f'*64
    if mismatch=='changed_byline':ctx.rows[0]['byline']=['Different Author']
    if mismatch=='changed_flags':ctx.rows[0]['byline_school']=['Foreign Author']
    R.apply(ctx)
    assert ctx.rows[0]['byline_school']==[]
    assert ctx.rows[0]['byline_affiliation_review']['status']=='held'
