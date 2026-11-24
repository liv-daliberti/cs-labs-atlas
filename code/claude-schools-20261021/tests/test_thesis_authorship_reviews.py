"""Source-slot and actual PDF-annotation failure cases for exact-work ORCID proofs."""
import copy
import hashlib
import json
import subprocess

import pymupdf
import pytest

from pihier import student_authorship_reviews as V
from schema_check import validate

ITEM='https://www.repository.cam.ac.uk/items/fe4806e8-c88f-440d-90d2-002006447281'
ORCID='https://orcid.org/0000-0002-3933-9904'


def setup(monkeypatch, badge_owner=0):
    name='Jane Student';quote='Authors Student, Jane '+ORCID
    html=('<script type="application/ld+json">'+json.dumps({'url':ITEM})+'</script><div class="simple-view-element"><h2>Authors</h2><ds-orcid-metadata-representation-loader><span>Student, Jane</span><a href="'+ORCID+'">'+ORCID+'</a></ds-orcid-metadata-representation-loader></div>'+''.join('<div class="simple-view-element"><h2>'+k+'</h2>'+v+'</div>' for k,v in [('Date','2024-06-01'),('Advisors','PI, Example'),('Qualification','Doctor of Philosophy (PhD)'),('Awarding Institution','University of Cambridge')])).encode()
    doc=pymupdf.open();page=doc.new_page()
    for point,text in [((70,60),'A real paper'),((70,100),name),((240,100),'Example PI'),((70,140),'University of Cambridge'),((70,20),'DOI: 10.1234/paper'),((70,40),'Copyright 2022'),((70,230),'Abstract'),((70,250),'Scientific body.')]:page.insert_text(point,text)
    words=page.get_text('words');family=next(w for w in words if w[4]==('Student' if badge_owner==0 else 'PI'));rect=pymupdf.Rect(family[2]+3,family[1]+1,family[2]+11,family[3]-1);page.insert_link({'kind':pymupdf.LINK_URI,'from':rect,'uri':ORCID})
    raw=doc.tobytes();doc.close();body=subprocess.run(['pdftotext','-layout','-','-'],input=raw,capture_output=True,check=True).stdout
    h=hashlib.sha256(html).hexdigest();ph=hashlib.sha256(raw).hexdigest();cache={h:html,ph:raw};monkeypatch.setattr(V,'evidence_bytes',lambda school,sha256,**kw:cache.get(sha256));V._PDF_TEXT.clear()
    member=dict(person='native-person',name=name,roles=['phd'],sourceRecordKey='cambridge-thesis:'+ITEM.rsplit('/',1)[1],relations=[dict(type='researched_advising',role='phd',years=[2024],sources=[dict(url=ITEM,sha256=h,quote=quote)])])
    paper=dict(pi='Example PI',oa='W1',work=None,title='A real paper',doi='10.1234/paper',date='2022-03-01',year=2022,identity='pi_orcid',appointment={'year':2022},editions=[],byline=[name,'Example PI'])
    pi=dict(pi='Example PI',names=['Example PI']);source=dict(id='W1',doi='https://doi.org/10.1234/paper',authorships=[dict(raw_author_name=n) for n in paper['byline']]);byline=next(line.strip() for line in body.decode().splitlines() if 'Jane Student' in line)
    pdf=dict(url='https://publisher.example/paper.pdf',sha256=ph,text_sha256=hashlib.sha256(body).hexdigest(),bytes=len(raw),pages=1,parse_returncode=0,complete_body=True,title=paper['title'],doi=paper['doi'],date='2022',title_quote=paper['title'],title_footnote_marker='none',identifier_quote='DOI: 10.1234/paper',date_quote='Copyright 2022',authors=paper['byline'],author_index=0,member_name=name,byline_quote=byline,affiliation_quote='University of Cambridge',mapping='shared_unindexed_affiliation')
    proof=dict(certification='university_thesis_author_orcid',thesis=dict(url=ITEM,sha256=h,quote=quote,date='2024-06-01',advisor='PI, Example',qualification='Doctor of Philosophy (PhD)'),orcid=ORCID,name_variant='exact',pdf=pdf,authors=[dict(native=n,printed=n,member=member['person'] if i==0 else None,mailbox=None,affiliations=['University of Cambridge'],source_quote=byline) for i,n in enumerate(paper['byline'])])
    d=dict(id='review-1',school='cambridge',pi=pi['pi'],member=member['person'],reviewed_by='fresh-reviewer',reviewed_at='2026-11-23',match=dict(oa='W1',work=None),preimages=V.preimages(member,paper,pi,source),proof=proof)
    return d,member,paper,pi,source,cache


def test_original_thesis_author_and_original_primary_badge_are_both_required(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch);before=copy.deepcopy((d,m,p,pi,s))
    assert not validate(dict(version=1,school='cambridge',reviews=[d]),V.schema())
    assert V.proof_error(d,m,p,pi,'cambridge',source=s) is None
    assert (d,m,p,pi,s)==before
    cache.pop(d['proof']['thesis']['sha256'])
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='missing_or_changed_original_thesis'


def test_primary_badge_belongs_to_coauthor_not_selected_student(monkeypatch):
    d,m,p,pi,s,_=setup(monkeypatch,badge_owner=1)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_original_primary_author_orcid_badge'


@pytest.mark.parametrize('old,new',[
 ('Student, Jane','Other, Jane'),
 ('<h2>Authors</h2>','<h2>Advisors</h2>'),
 ('<h2>Date</h2>2024','<h2>Date</h2>2023'),
 ('<h2>Advisors</h2>PI, Example','<h2>Advisors</h2>Professor, Other'),
 ('Doctor of Philosophy (PhD)','Master of Science'),
 ('Awarding Institution</h2>University of Cambridge','Awarding Institution</h2>Other University'),
])
def test_actual_university_fields_cannot_be_replaced_by_nearby_assertions(monkeypatch,old,new):
    d,m,p,pi,s,cache=setup(monkeypatch);t=d['proof']['thesis'];raw=cache.pop(t['sha256']);changed=raw.replace(old.encode(),new.encode());assert changed!=raw;t['sha256']=hashlib.sha256(changed).hexdigest();cache[t['sha256']]=changed;m['relations'][0]['sources'][0]['sha256']=t['sha256'];d['preimages']=V.preimages(m,p,pi,s)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)


def test_other_person_orcid_anchor_cannot_supply_author_slot(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch);t=d['proof']['thesis'];raw=cache.pop(t['sha256']);changed=raw.replace(ORCID.encode(),b'https://orcid.org/0000-0001-9979-6456')+('<a href="'+ORCID+'">'+ORCID+'</a>').encode();t['sha256']=hashlib.sha256(changed).hexdigest();cache[t['sha256']]=changed;m['relations'][0]['sources'][0]['sha256']=t['sha256'];d['preimages']=V.preimages(m,p,pi,s)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='different_original_thesis_author_orcid'


def test_native_source_orcid_equality_does_not_override_missing_primary_badge(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch,badge_owner=1)
    s['authorships'][0]['author']={'orcid':ORCID};d['preimages']=V.preimages(m,p,pi,s)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_original_primary_author_orcid_badge'


def replace_pdf(d,cache,change):
    pdf=d['proof']['pdf'];raw=cache[pdf['sha256']]
    with pymupdf.open(stream=raw,filetype='pdf') as doc:
        change(doc[0]);raw=doc.tobytes()
    pdf.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),text_sha256=hashlib.sha256(subprocess.run(['pdftotext','-layout','-','-'],input=raw,capture_output=True,check=True).stdout).hexdigest());cache[pdf['sha256']]=raw


def test_primary_badge_cannot_extend_over_another_author(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def widen(page):
        link=page.get_links()[0];rect=link['from'];rect.x1=300;page.delete_link(link);page.insert_link({'kind':pymupdf.LINK_URI,'from':rect,'uri':ORCID})
    replace_pdf(d,cache,widen)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_original_primary_author_orcid_badge'


def test_reference_doi_cannot_replace_conflicting_actual_article_doi(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def references(page):
        for rect in page.search_for('DOI: 10.1234/paper'):page.add_redact_annot(rect)
        page.apply_redactions();page.insert_text((70,170),'DOI: 10.1234/other');page.insert_text((70,280),'References');page.insert_text((70,300),'DOI: 10.1234/paper')
    replace_pdf(d,cache,references)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_primary_article_doi'


def test_university_in_other_authors_column_is_not_shared_affiliation(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def separate(page):
        for rect in page.search_for('University of Cambridge'):page.add_redact_annot(rect)
        page.apply_redactions();page.insert_text((70,140),'Acme Research');page.insert_text((240,140),'University of Cambridge')
    replace_pdf(d,cache,separate)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='ambiguous_shared_thesis_primary_affiliation'


def test_named_paragraph_requires_an_explicit_affiliation_statement(monkeypatch):
    from pihier import thesis_authorship_reviews as T
    d,m,p,pi,s,cache=setup(monkeypatch);proof=d['proof'];proof['affiliation_groups']=[dict(authors=[0],affiliations=['University of Cambridge'],quote='Jane Student thanks University of Cambridge for helpful comments.'),dict(authors=[1],affiliations=['University of Cambridge'],quote='Example PI is with University of Cambridge.')]
    paragraphs=[V.norm(g['quote']) for g in proof['affiliation_groups']]
    assert not T.named_affiliations(proof,'',paragraphs)
    proof['affiliation_groups'][0]['quote']='Jane Student is with University of Cambridge.';paragraphs=[V.norm(g['quote']) for g in proof['affiliation_groups']]
    assert T.named_affiliations(proof,'',paragraphs)


def test_exact_orcid_printed_initials_never_become_name_only_aliases():
    from pihier import thesis_authorship_reviews as T
    assert T.printed_name('Matheus Henrique Nunes','M H Nunes','given_initials')
    assert not T.printed_name('Matheus Henrique Nunes','M X Nunes','given_initials')
    assert not T.printed_name('Matheus Henrique Nunes','M H Other','given_initials')
    assert not V.name_variant_ok('Matheus Henrique Nunes','M H Nunes','middle_names')


def indexed_setup(monkeypatch):
    from pihier import thesis_authorship_reviews as T
    d,m,p,pi,s,cache=setup(monkeypatch)
    def indexed(page):
        for text in ['Jane Student','Example PI','University of Cambridge']:
            for rect in page.search_for(text):page.add_redact_annot(rect)
        page.apply_redactions()
        for link in page.get_links():page.delete_link(link)
        page.insert_text((70,100),'Jane Student1,2');page.insert_text((240,100),'Example PI2')
        page.insert_text((70,140),'1 University of Cambridge');page.insert_text((70,160),'2 Acme Research')
        word=next(w for w in page.get_text('words') if w[4]=='Student1,2');page.insert_link({'kind':pymupdf.LINK_URI,'from':pymupdf.Rect(word[2]+3,word[1]+1,word[2]+11,word[3]-1),'uri':ORCID})
    replace_pdf(d,cache,indexed);pdf=d['proof']['pdf'];raw=cache[pdf['sha256']];body=V.original_pdf_text('cambridge',pdf);byline=next(line.strip() for line in body.splitlines() if 'Jane Student1,2' in line);pdf.update(mapping='indexed_affiliations',byline_quote=byline)
    proof=d['proof'];defs=T.numbered_blocks(raw,pdf);assert set(defs)=={'1','2'},defs
    proof['affiliation_blocks']=[dict(marker=k,quote=v,affiliations=['University of Cambridge'] if k=='1' else ['Acme Research']) for k,v in defs.items()]
    for a,q,marks,aff in zip(proof['authors'],['Jane Student1,2','Example PI2'],[['1','2'],['2']],[['University of Cambridge','Acme Research'],['Acme Research']]):a.update(marker_quote=q,affiliation_markers=marks,affiliations=aff,source_quote=q)
    return d,m,p,pi,s,cache


def test_complete_numeric_affiliation_tail_cannot_be_clipped_at_comma(monkeypatch):
    d,m,p,pi,s,cache=indexed_setup(monkeypatch)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s) is None
    a=d['proof']['authors'][0];a.update(marker_quote='Jane Student1,',affiliation_markers=['1'],affiliations=['University of Cambridge'])
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_indexed_primary_affiliations'


def test_numbered_definition_cannot_be_cropped_inside_complete_original_block(monkeypatch):
    d,m,p,pi,s,cache=indexed_setup(monkeypatch)
    d['proof']['affiliation_blocks'][0]['quote']='1 University of'
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_indexed_primary_affiliations'


def test_complete_name_orcid_link_has_exact_name_bounds(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def whole(page):
        for link in page.get_links():page.delete_link(link)
        page.insert_link({'kind':pymupdf.LINK_URI,'from':page.search_for('Jane Student')[0],'uri':ORCID})
    replace_pdf(d,cache,whole);d['proof']['pdf']['orcid_mapping']='whole_author_name'
    assert V.proof_error(d,m,p,pi,'cambridge',source=s) is None
    def clip(page):
        for link in page.get_links():page.delete_link(link)
        page.insert_link({'kind':pymupdf.LINK_URI,'from':page.search_for('Jane')[0],'uri':ORCID})
    replace_pdf(d,cache,clip)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_original_primary_author_orcid_badge'


def test_body_citation_doi_cannot_replace_missing_actual_article_identifier(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def body_only(page):
        for rect in page.search_for('DOI: 10.1234/paper'):page.add_redact_annot(rect)
        page.apply_redactions();page.insert_text((70,300),'Comparison with previous work. DOI: 10.1234/paper')
    replace_pdf(d,cache,body_only)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_primary_article_doi'


def test_formal_publisher_doi_footer_is_replayed_from_whole_original_line(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def footer(page):
        for rect in page.search_for('DOI: 10.1234/paper'):page.add_redact_annot(rect)
        page.apply_redactions();page.insert_text((70,740),'Digital Object Identifier 10.1234/paper')
    replace_pdf(d,cache,footer);d['proof']['pdf']['identifier_quote']='10.1234/paper'
    assert V.proof_error(d,m,p,pi,'cambridge',source=s) is None


def test_acm_imprint_footer_requires_own_column_publisher_and_year(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def footer(page):
        for rect in page.search_for('DOI: 10.1234/paper'):page.add_redact_annot(rect)
        page.apply_redactions();page.insert_text((70,700),'Copyright 2022 held by owner.');page.insert_text((70,720),'ACM ISBN 979-0-0000');page.insert_text((70,740),'https://doi.org/10.1234/paper')
    replace_pdf(d,cache,footer);d['proof']['pdf']['identifier_quote']='10.1234/paper'
    assert V.proof_error(d,m,p,pi,'cambridge',source=s) is None
    def other_column(page):
        for rect in page.search_for('ACM ISBN 979-0-0000'):page.add_redact_annot(rect)
        page.apply_redactions();page.insert_text((340,720),'ACM ISBN 979-0-0000')
    replace_pdf(d,cache,other_column)
    assert V.proof_error(d,m,p,pi,'cambridge',source=s)=='unbound_primary_article_doi'


def test_literal_repeated_doi_org_prefix_in_real_publisher_imprint(monkeypatch):
    d,m,p,pi,s,cache=setup(monkeypatch)
    def footer(page):
        for rect in page.search_for('DOI: 10.1234/paper'):page.add_redact_annot(rect)
        page.apply_redactions();page.insert_text((70,700),'Copyright 2022 held by owner.');page.insert_text((70,720),'ACM ISBN 979-0-0000');page.insert_text((70,740),'https://doi.org/doi.org/10.1234/paper')
    replace_pdf(d,cache,footer);d['proof']['pdf']['identifier_quote']='10.1234/paper'
    assert V.proof_error(d,m,p,pi,'cambridge',source=s) is None
