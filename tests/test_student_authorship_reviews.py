import copy
import json
from collections import Counter
from types import SimpleNamespace

import pytest

from pihier import member_paper_reviews as legacy
from pihier import student_authorship_reviews as R

REAL_PDF_TEXT = R.original_pdf_text


DIRECTORY = '<h2 id="pi123">Prof. Example PI</h2><ul><li id="s-js123"><b><a href="/~js123/">Jane Student</a></b> (2020-10-01 – 2024-06-01)</li></ul>'.encode()
POLICY = b'<p>Your email address is your CRSid + @cam.ac.uk.</p>'
PDF_TEXT = """A real paper
Jane Student and Example PI
Jane Student: University of Cambridge; js123@cam.ac.uk
Example PI University of Cambridge
DOI: 10.1234/paper
Copyright 2022
Abstract
A scientific abstract.\f"""


def native_source():
    return dict(id='W1',doi='https://doi.org/10.1234/paper',authorships=[dict(raw_author_name=n) for n in ['Jane Student','Example PI']])


def check(d,m,p,pi,school='cambridge',**kw):
    return R.proof_error(d,m,p,pi,school,**(dict(source=native_source(),directory_raw=DIRECTORY,policy_raw=POLICY,pdf_text=PDF_TEXT)|kw))


@pytest.fixture(autouse=True)
def original_sources(monkeypatch):
    def raw(school,sha256,**kw):
        return {R.hashlib.sha256(DIRECTORY).hexdigest():DIRECTORY,R.hashlib.sha256(POLICY).hexdigest():POLICY}.get(sha256)
    monkeypatch.setattr(R,'evidence_bytes',raw)
    monkeypatch.setattr(R,'original_pdf_text',lambda *a,**kw:PDF_TEXT)


def fixture():
    ds=R.hashlib.sha256(DIRECTORY).hexdigest();ps=R.hashlib.sha256(POLICY).hexdigest()
    quote = 'Prof. Example PI Jane Student (2020-10-01 – 2024-06-01)'
    member = dict(person='native-person', name='Jane Student', roles=['phd'],
                  sourceRecordKey='cambridge-phd-directory:pi123:s-js123',
                  relations=[dict(type='researched_advising', role='phd', years=[2024],
                                  sources=[dict(url='https://example.cam.ac.uk/supervisors', sha256=ds, quote=quote)])])
    paper = dict(pi='Example PI', oa='W1', work=None, title='A real paper', doi='10.1234/paper',
                 date='2022-03-01', year=2022, identity='pi_orcid', appointment={'year':2022},
                 editions=[], byline=['Jane Student','Example PI'])
    pi = dict(pi='Example PI', names=['Example PI'], oaAuthorIds=[],latinAliases=['Example PI'],dblpPids=[],orcidIds=[],openalexIds=[],lab=dict(url='https://www.cst.cam.ac.uk/people/pi123'))
    directory = dict(url='https://example.cam.ac.uk/supervisors', sha256=ds, quote=quote,
                     pi='Example PI', student_name='Jane Student', crsid='js123', record_id='s-js123',
                     supervisor_id='pi123', source_record_key=member['sourceRecordKey'],
                     profile_url='https://www.cl.cam.ac.uk/~js123/')
    pdf = dict(url='https://publisher.example/paper.pdf',sha256='b'*64,text_sha256=R.hashlib.sha256(PDF_TEXT.encode()).hexdigest(),bytes=2000,pages=1,
               parse_returncode=0,complete_body=True,title=paper['title'],doi=paper['doi'],date='2022',
               title_quote='A real paper',identifier_quote='DOI: 10.1234/paper',date_quote='Copyright 2022',
               authors=paper['byline'],author_index=0,member_name='Jane Student',mailbox='js123@cam.ac.uk',
               byline_quote='Jane Student and Example PI',
               author_binding_quote='Jane Student: University of Cambridge; js123@cam.ac.uk',
               affiliation_quote='University of Cambridge',mapping='named_author_address')
    proof = dict(directory=directory,mail_policy=dict(url='https://policy.cam.ac.uk/email',sha256=ps,
                 quote='Your email address is your CRSid + @cam.ac.uk.',domain='cam.ac.uk'),
                 student_period=dict(role='phd',start='2020-10-01',end='2024-06-01',end_basis='stated_end',source_sha256=ds,quote='Jane Student (2020-10-01 – 2024-06-01)'),
                 mailbox='js123@cam.ac.uk',timing='within_stated_student_period',pdf=pdf,
                 authors=[dict(native=n,printed=n,member=member['person'] if i==0 else None,mailbox='js123@cam.ac.uk' if i==0 else None,affiliations=['University of Cambridge'],source_quote=n+(': University of Cambridge; js123@cam.ac.uk' if i==0 else ' University of Cambridge')) for i,n in enumerate(paper['byline'])])
    d = dict(id='review-1',school='cambridge',pi=pi['pi'],member=member['person'],reviewed_by='fresh-reviewer',reviewed_at='2026-11-23',
             match=dict(oa='W1',work=None),preimages=R.preimages(member,paper,pi,native_source()),proof=proof)
    return member,paper,pi,d


def route(tmp_path,monkeypatch):
    monkeypatch.setattr(R.P,'data',lambda name,*a,**kw:tmp_path/('reviews.json' if name=='student-authorship-review.json' else name))


def context(tmp_path,m,p,pi):
    return SimpleNamespace(school='cambridge',here=tmp_path,stu={'Example PI':{'native-person':m}},rows=[p],pis=[pi],sp=[],n=Counter(),hits=[('Example PI',native_source())])


def test_precise_source_identifier_proof_and_no_input_mutation():
    m,p,pi,d=fixture();before=copy.deepcopy((m,p,pi,d))
    assert check(d,m,p,pi,'cambridge') is None
    assert (m,p,pi,d)==before


@pytest.mark.parametrize('mutation',[
    lambda d:d['proof'].update(mailbox='other@cam.ac.uk'),
    lambda d:d['proof']['directory'].update(source_record_key='other-profile'),
    lambda d:d['proof']['directory'].update(record_id='s-other'),
    lambda d:d['proof']['directory'].update(profile_url='https://attacker.example/~js123/'),
    lambda d:d['proof']['directory'].update(sha256='f'*64),
    lambda d:d['proof']['mail_policy'].update(domain='cl.cam.ac.uk'),
    lambda d:d['proof']['mail_policy'].update(quote='Emails are sometimes forwarded.'),
    lambda d:d['proof']['pdf'].update(mailbox='other@cam.ac.uk'),
    lambda d:d['proof']['pdf'].update(member_name='Another Student'),
    lambda d:d['proof']['pdf'].update(author_binding_quote='Correspondence to Example PI: js123@cam.ac.uk; University of Cambridge'),
    lambda d:d['proof']['pdf'].update(affiliation_quote='Another University'),
    lambda d:d['proof']['pdf'].update(authors=['Jane Student']),
    lambda d:d['proof']['pdf'].update(byline_quote='Example PI and Jane Student'),
    lambda d:d['proof']['pdf'].update(author_index=1),
    lambda d:d['proof']['pdf'].update(doi='10.1234/other'),
    lambda d:d['proof']['pdf'].update(title='Another paper'),
    lambda d:d['proof']['pdf'].update(identifier_quote='An unrelated DOI'),
    lambda d:d['proof']['pdf'].update(complete_body=False),
    lambda d:d['proof']['pdf'].update(parse_returncode=1),
    lambda d:d['proof']['pdf'].update(date='2019',date_quote='Copyright 2019'),
    lambda d:d['proof']['student_period'].update(end='2020-11-01'),
    lambda d:d['proof']['student_period'].update(start='2023-10-01'),
    lambda d:d['proof']['student_period'].update(end_basis='current_capture'),
    lambda d:d['proof']['authors'][1].update(member='other-member'),
])
def test_incomplete_conflicting_or_out_of_period_proof_stays_held(mutation):
    m,p,pi,d=fixture();mutation(d)
    assert check(d,m,p,pi,'cambridge') is not None


@pytest.mark.parametrize('kind',['member','paper','pi'])
def test_changed_scientific_preimages_are_not_reused(kind):
    m,p,pi,d=fixture();{'member':m,'paper':p,'pi':pi}[kind]['new_scientific_claim']='changed'
    assert check(d,m,p,pi,'cambridge')=='stale_scientific_preimage'


def test_nonempty_edition_group_needs_further_proof():
    m,p,pi,d=fixture();p['editions']=[{'oa':'W2'}];d['preimages']=R.preimages(m,p,pi,native_source())
    assert check(d,m,p,pi,'cambridge')=='edition_group_requires_separate_proof'


def test_historical_student_link_does_not_assert_enrollment_at_publication():
    m,p,pi,d=fixture();p.update(date='2025-03-01',year=2025);d['preimages']=R.preimages(m,p,pi,native_source())
    d['proof'].update(timing='historical_student_publication');d['proof']['pdf'].update(date='2025',date_quote='2025')
    assert check(d,m,p,pi,'cambridge',pdf_text=PDF_TEXT.replace('2022','2025')) is None
    p.update(date='2032-03-01',year=2032);d['preimages']=R.preimages(m,p,pi,native_source());d['proof']['pdf'].update(date='2032',date_quote='2032')
    assert check(d,m,p,pi,'cambridge',pdf_text=PDF_TEXT.replace('2022','2032'))=='outside_historical_student_window'


def test_optional_absent_input_and_exact_link_id_validation(tmp_path,monkeypatch):
    route(tmp_path,monkeypatch)
    m,p,pi,d=fixture();ctx=context(tmp_path,m,p,pi)
    R.apply(ctx);assert ctx.sp==[]
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    R.apply(ctx);assert len(ctx.sp)==1 and legacy.work_only(ctx.sp[0])
    assert ctx.sp[0]['institutionalAuthorshipReview']['identity_scope']=='exact_work'
    legacy.validate_scoped('cambridge',{'Example PI':[m]},[p],ctx.sp,pis=[pi])
    p['atlasWorkId']='id-only';m['atlasId']='id-only';pi['atlasId']='id-only'
    legacy.validate_scoped('cambridge',{'Example PI':[m]},[p],ctx.sp,pis=[pi])
    m['relations'][0]['years']=[2025]
    with pytest.raises(ValueError,match='preimage'):
        legacy.validate_scoped('cambridge',{'Example PI':[m]},[p],ctx.sp,pis=[pi])


def test_competing_decisions_and_existing_links_do_not_use_first_row(tmp_path,monkeypatch):
    route(tmp_path,monkeypatch)
    m,p,pi,d=fixture();other=copy.deepcopy(d);other['id']='review-2'
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d,other])))
    ctx=context(tmp_path,m,p,pi)
    R.apply(ctx);assert not ctx.sp and ctx.n['student_authorship_held']==2
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    original=dict(pi='Example PI',student='native-person',oa='W1',work=None,basis='ordinary')
    ctx.sp=[copy.deepcopy(original)];R.apply(ctx);assert ctx.sp==[original]


@pytest.mark.parametrize('field,value',[('name','Another Student'),('byline','Another Author'),('unreviewed_scientific_claim',True)])
def test_retained_link_cannot_change_scientific_fields(tmp_path,monkeypatch,field,value):
    route(tmp_path,monkeypatch)
    m,p,pi,d=fixture()
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    ctx=context(tmp_path,m,p,pi)
    R.apply(ctx);ctx.sp[0][field]=value
    with pytest.raises(ValueError,match='scientific link'):
        legacy.validate_scoped('cambridge',{'Example PI':[m]},[p],ctx.sp,pis=[pi])


@pytest.mark.parametrize('mutation,reason',[
    ('mailbox','unbound_author_mailbox_affiliation'),
    ('name','unbound_complete_affiliation_map'),
    ('date','unsupported_publication_date_precision'),
    ('header','different_complete_primary_title'),
    ('references','primary_proof_outside_publication_header'),
    ('duplicate_directory','competing_original_directory_records'),
    ('wrong_directory_person','different_original_directory_person'),
    ('wrong_policy','unbound_original_university_mail_policy'),
    ('wrong_native','stale_scientific_preimage'),
])
def test_replayed_originals_reject_concrete_counterexamples(mutation,reason):
    m,p,pi,d=fixture();kw={}
    if mutation=='mailbox':
        d['proof']['pdf']['author_binding_quote']=d['proof']['pdf']['author_binding_quote'].replace('js123@',"other'js123@")
        kw['pdf_text']=PDF_TEXT.replace('js123@',"other'js123@")
    if mutation=='name':
        d['proof']['pdf']['author_binding_quote']=d['proof']['pdf']['author_binding_quote'].replace('Jane Student:','Jane Studentish:')
        kw['pdf_text']=PDF_TEXT.replace('Jane Student:','Jane Studentish:')
    if mutation in ['mailbox','name']:
        d['proof']['authors'][0]['source_quote']=d['proof']['pdf']['author_binding_quote']
    if mutation=='date':d['proof']['pdf']['date']='2022-01-01'
    if mutation=='header':kw['pdf_text']=PDF_TEXT.replace('A real paper','Comment on A real paper')
    if mutation=='references':kw['pdf_text']=PDF_TEXT.replace('DOI: 10.1234/paper','References\nDOI: 10.1234/paper')
    if mutation in ['duplicate_directory','wrong_directory_person']:
        raw=DIRECTORY+DIRECTORY if mutation=='duplicate_directory' else DIRECTORY.replace(b'Jane Student',b'Other Student')
        kw['directory_raw']=raw
        d['proof']['directory']['sha256']=R.hashlib.sha256(raw).hexdigest()
    if mutation=='wrong_policy':kw['policy_raw']=POLICY+b'changed'
    if mutation=='wrong_native':kw['source']=native_source()|{'new_scientific_claim':True}
    assert check(d,m,p,pi,**kw)==reason


def test_shared_block_cannot_reverse_explicit_named_contacts():
    m,p,pi,d=fixture();block='Jane Student and Example PI. University of Cambridge. Correspondence to Example PI: js123@cam.ac.uk; Other contact Jane Student: pi123@cam.ac.uk'
    d['proof']['pdf'].update(mapping='shared_campus_block',author_binding_quote=block)
    d['proof']['authors'][1]['mailbox']='pi123@cam.ac.uk'
    assert check(d,m,p,pi,pdf_text=PDF_TEXT.replace('Abstract',block+'\nAbstract'))=='competing_named_contacts_in_shared_block'


def test_pi_crsid_requires_own_profile_never_adjacent_listing_quote():
    assert not R.pi_identifier({'piBasis':dict(quote='Prof Example PI pi123 Other Professor other456')},'other456')
    assert not R.pi_identifier({'lab':dict(url='https://www.cst.cam.ac.uk/people/pi123')},'pi12')
    assert not R.pi_identifier({'lab':dict(url='https://other.example/people/pi123')},'pi123')
    assert R.pi_identifier({'lab':dict(url='https://www.cst.cam.ac.uk/people/pi123')},'pi123')


def test_active_exclusion_and_competing_native_sources_are_held(tmp_path,monkeypatch):
    route(tmp_path,monkeypatch);m,p,pi,d=fixture();ctx=context(tmp_path,m,p,pi)
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    exclude=tmp_path/'student-link-exclusions.json'
    exclude.write_text(json.dumps(dict(version=1,school='cambridge',exclusions=[dict(pi=pi['pi'],student=m['name'],oa=p['oa'])])))
    R.apply(ctx);assert ctx.student_authorship_review['decisions'][0]['reason']=='active_link_exclusion' and not ctx.sp
    exclude.unlink();ctx.hits.append((pi['pi'],native_source()|{'different_version':True}))
    R.apply(ctx);assert ctx.student_authorship_review['decisions'][0]['reason']=='missing_or_ambiguous_native_target' and not ctx.sp


def test_removed_weak_member_cannot_be_rescued_by_exact_work_input(tmp_path,monkeypatch):
    from pihier import students
    route(tmp_path,monkeypatch);m,p,pi,d=fixture();ctx=context(tmp_path,m,p,pi)
    m['relations'][0]['weak']='program_adviser'
    d['preimages']=R.preimages(m,p,pi,native_source())
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    students.drop_weak(ctx,ctx.sp);assert not ctx.stu[pi['pi']]
    R.apply(ctx);assert not ctx.sp


@pytest.mark.parametrize('ordinary_twin',[False,True])
def test_actual_new_marker_guards_both_atlasid_bridges(tmp_path,monkeypatch,ordinary_twin):
    import atlas_ids as A
    from test_atlas_ids import pi as make_pi, stu, write
    route(tmp_path,monkeypatch);m,p,pi,d=fixture();pi=make_pi(pi['pi'],**{k:v for k,v in pi.items() if k not in ['pi','names']})
    d['preimages']=R.preimages(m,p,pi,native_source());ctx=context(tmp_path,m,p,pi)
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    R.apply(ctx);assert len(ctx.sp)==1
    members=[m];links=ctx.sp
    if ordinary_twin:
        twin=stu('ext:cambridge:other-jane','Jane Student',['https://other.cam.ac.uk/roster']);members.append(twin)
        links.append(dict(pi=pi['pi'],student=twin['person'],name=twin['name'],oa=p['oa'],work=None,byline='Jane Student',status='candidate'))
    source=native_source();source['authorships'][0]['author']=dict(id='https://openalex.org/A123')
    fx=dict(cambridge=dict(pis=[pi],students={pi['pi']:members},papers=[p],links=links,sweep=[source]),example=dict(pis=[make_pi('Jane Student',oa=['https://openalex.org/A123'])],students={},papers=[],links=[],sweep=[]))
    # Isolate this marker's guarantee from the independent source-record guard.
    monkeypatch.setattr(A,'source_record_anchor',lambda *a:None)
    root=tmp_path/'package';write(root,fx)
    db=A.open_registry(tmp_path/'registry.sqlite',seed=False)
    try:A.run(['cambridge','example'],root,db,today='2026-11-23')
    finally:db.close()
    people=json.loads((root/'cambridge/students.json').read_text())[pi['pi']]
    target=json.loads((root/'example/pis.json').read_text())[0]['atlasId']
    assert people[0]['atlasId']!=target
    if ordinary_twin:assert people[1]['atlasId']==target


def test_pdf_consumption_rehashes_original_and_complete_parsed_body(monkeypatch):
    raw=b'%PDF fixture original bytes';body=b'First page\fSecond page\f'
    sha=R.hashlib.sha256(raw).hexdigest();pdf=dict(sha256=sha,bytes=len(raw),text_sha256=R.hashlib.sha256(body).hexdigest(),pages=2)
    monkeypatch.setattr(R,'evidence_bytes',lambda *a,**kw:raw)
    def parse(cmd,**kw):
        assert kw['input']==raw and cmd==['pdftotext','-layout','-','-']
        return SimpleNamespace(returncode=0,stdout=body)
    monkeypatch.setattr(R.subprocess,'run',parse)
    R._PDF_TEXT.pop(sha,None)
    assert REAL_PDF_TEXT('cambridge',pdf)==body.decode()
    assert REAL_PDF_TEXT('cambridge',pdf|{'pages':1}) is None
    assert REAL_PDF_TEXT('cambridge',pdf|{'text_sha256':'0'*64}) is None
    monkeypatch.setattr(R,'evidence_bytes',lambda *a,**kw:raw+b'changed')
    assert REAL_PDF_TEXT('cambridge',pdf) is None


def test_output_schema_and_export_preserve_typed_new_certificate(tmp_path,monkeypatch):
    from pathlib import Path
    from schema_check import validate
    route(tmp_path,monkeypatch);m,p,pi,d=fixture();ctx=context(tmp_path,m,p,pi)
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    R.apply(ctx);assert len(ctx.sp)==1
    schema=json.loads((Path(__file__).parents[1]/'schemas/student_papers.schema.json').read_text())
    assert not validate(ctx.sp[0],schema)
    exported=legacy.export_fields(ctx.sp[0])
    assert exported['identity_scope']=='exact_work'
    assert exported['institutional_authorship_review']==ctx.sp[0][R.MARKER]


def test_actual_build_writer_roundtrip_binds_final_scientific_pi_fields(tmp_path,monkeypatch):
    from collections import defaultdict
    from pihier import build, match_ids
    route(tmp_path,monkeypatch);m,p,pi,d=fixture();ctx=context(tmp_path,m,p,pi)
    # Reproduce census's pre-write form, which lacks these scientific fields.
    for key in ['latinAliases','dblpPids','orcidIds','openalexIds']:pi.pop(key)
    ctx.anchored=defaultdict(Counter);ctx.anchored[pi['pi']]['https://openalex.org/A12345']=3
    final=copy.deepcopy(pi);final['oaAuthorIds']=['https://openalex.org/A12345'];match_ids.add([final])
    d['preimages']=R.preimages(m,p,final,native_source())
    (tmp_path/'reviews.json').write_text(json.dumps(dict(version=1,school='cambridge',reviews=[d])))
    before=copy.deepcopy(pi);R.apply(ctx);assert len(ctx.sp)==1 and pi==before
    ctx.out=tmp_path/'written';ctx.out.mkdir()
    for key in ['funnel','dblp_title','dblp_doi','verified']:setattr(ctx,key,defaultdict(Counter))
    for key in ['excluded','nick_merges','weak_dropped','self_listed','guard_samples','guard_kept_samples','not_paper_samples','page1_samples','listing_review','unevidenced','labpage_set_aside','initials_merges','typo_pairs']:setattr(ctx,key,[])
    monkeypatch.setattr(build.provenance,'block',lambda school:dict(test_fixture=True))
    build.write(ctx)
    written=json.loads((ctx.out/'pis.json').read_text())
    legacy.validate_scoped('cambridge',{pi['pi']:[m]},[p],ctx.sp,pis=written)
    assert json.loads((ctx.out/'report.json').read_text())['studentAuthorshipReview']['decisions'][0]['status']=='verified'
