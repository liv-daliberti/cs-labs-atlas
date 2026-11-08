"""Optional flag correction flows through normal native eligibility, campus guards and candidate links."""
import collections
import copy
import gzip
import hashlib
import json
import re
import sqlite3
import types
import zlib

import pytest

import test_build_rules as T
from pihier import build, common, identity, papers, primary_affiliations as A


def native_source(root, *, review=True, wrong_source=False, year=2020, typ='article'):
    work = T.work('W701', 'Primary Block Research', year,
                  [T.au('Ada Lovelace', 'A1', school=False), T.au('Alan Turing', 'A9', school=False), T.au('Outside Person', 'A700')],
                  typ=typ, doi='10.1000/primary-block')
    T.write_school(root, sweep=[work])
    names = [a['raw_author_name'] for a in work['authorships']]
    affs = ['Princeton University', 'Princeton University', 'University of Vienna']
    text = '\n'.join(n+'\n'+a for n,a in zip(names,affs))+'\nAbstract\nResearch body.'
    page = dict(url='https://proceedings.example/paper.pdf', pdf_sha256='a'*64, how='near', quotes=['Ada Lovelace Princeton University'])
    if review:
        page['author_affiliation_review'] = dict(version=1,work=work['id'],doi=work['doi'],source_work_sha256=A.digest(work),
            source_authorships_sha256=A.digest(work['authorships']),pdf_sha256=page['pdf_sha256'],pdf_url=page['url'],
            page1_text_sha256=hashlib.sha256(text.encode()).hexdigest(),byline_names=names,reviewed_by='reviewer',reviewed_at='2026-11-08',
            blocks=[dict(index=i,raw_name=n,author_id=work['authorships'][i]['author']['id'],affiliations=[aff],block_text=n+'\n'+aff,bbox=[i*100,0,i*100+90,40])for i,(n,aff)in enumerate(zip(names,affs))])
        if wrong_source: page['author_affiliation_review']['source_work_sha256']='0'*64
    db = sqlite3.connect(T.put(root,'pi-works.sqlite'))
    db.executescript('create table works(id text primary key,body blob);create table pages(work text primary key,arxiv text,url text,status text,pdf_sha256 text,page1 blob,school_named int,quote text,fetched_at text);')
    db.execute('insert into works values(?,?)',(work['id'],zlib.compress(json.dumps(work).encode())))
    db.execute('insert into pages values(?,?,?,?,?,?,?,?,?)',(work['id'],None,page['url'],'ok',page['pdf_sha256'],zlib.compress(text.encode()),1,json.dumps({k:v for k,v in page.items()if k not in['url','pdf_sha256']}),'2026-11-08'))
    db.commit();db.close();return work,page,text


@pytest.mark.usefixtures('layout')
def test_full_native_flags_correct_while_PI_admission_raw_source_and_candidate_status_stay_standard(tmp_path,monkeypatch):
    monkeypatch.setattr(identity,'DUMP_PERSONS',None)
    work,page,text=native_source(tmp_path);raw_before=T.put(tmp_path,'pi-works.sqlite').read_bytes()
    monkeypatch.setattr(build,'HERE',tmp_path)
    monkeypatch.setattr(build,'Ctx',lambda school,out:common.Ctx(school,here=tmp_path,site=tmp_path,out=out))
    monkeypatch.setattr(build.provenance,'block',lambda school:{})
    monkeypatch.setenv('PI_HIERARCHY_OUT',str(tmp_path/'trial'))
    build.build(T.SCHOOL);out=tmp_path/'trial'/T.SCHOOL
    rows=[json.loads(x)for x in gzip.open(out/'lab_papers.jsonl.gz','rt')]
    row=next(r for r in rows if r['oa']==work['id'])
    assert row['byline_school']==['Ada Lovelace','Alan Turing']
    assert row['authorship']['institutions']==[] and row['authorship']['raw_affiliations']==[]
    assert row['authorship']['school_via']==['page 1 (near): Ada Lovelace Princeton University']
    assert row['byline_affiliation_review']['status']=='accepted'
    report=json.loads((out/'report.json').read_text())
    assert report['counts']['primary_pdf_affiliation_review_accepted']==1
    assert report['primaryPDFAffiliationReviews'][0]['source_work_sha256']==A.digest(work)
    links=[json.loads(x)for x in gzip.open(out/'student_papers.jsonl.gz','rt')]
    link=next(l for l in links if l['student']=='p_alan'and l['oa']==work['id'])
    assert link['status']=='candidate'and link['basis']=='byline_name_with_school_affiliation'
    assert T.put(tmp_path,'pi-works.sqlite').read_bytes()==raw_before


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('wrong_source',[False,True])
def test_unrequested_or_held_review_keeps_original_flags_and_normal_PI_page1_route(tmp_path,monkeypatch,wrong_source):
    monkeypatch.setattr(identity,'DUMP_PERSONS',None)
    work,_,_=native_source(tmp_path,review=wrong_source,wrong_source=wrong_source)
    ctx=T.run_stages(tmp_path,upto='links');row=next(r for r in ctx.rows if r['oa']==work['id'])
    assert row['byline_school']==['Outside Person']
    assert row['authorship']['school_via']==['page 1 (near): Ada Lovelace Princeton University']
    if wrong_source:
        assert row['byline_affiliation_review']['status']=='held'
        assert ctx.n['primary_pdf_affiliation_review_held']==1
    else:
        assert 'byline_affiliation_review'not in row and not getattr(ctx,'primary_affiliation_reviews',None)
    assert all(l['status']!='verified'for l in ctx.sp if l['oa']==work['id'])


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('year,typ',[(2014,'article'),(2020,'dataset')])
def test_review_cannot_admit_outside_appointment_or_nonpaper_record(tmp_path,monkeypatch,year,typ):
    monkeypatch.setattr(identity,'DUMP_PERSONS',None)
    work,_,_=native_source(tmp_path,year=year,typ=typ)
    ctx=T.run_stages(tmp_path,upto='papers')
    assert not any(r['oa']==work['id']for r in ctx.rows)
    assert not ctx.n['primary_pdf_affiliation_review_accepted']


def test_native_derived_flags_consult_landed_campus_guard_without_lending_old_primary_IDs():
    names=['First Author','Second Author'];affs=['The Hong Kong University of Science and Technology (Guangzhou )','The Hong Kong University of Science and Technology, Hong Kong']
    work=T.work('W702','A Research Paper',2020,[T.au(n,'A70'+str(i))for i,n in enumerate(names)],doi='10.1000/campus')
    for a in work['authorships']:
        a['institutions']=[dict(id='https://openalex.org/I200769079',lineage=['https://openalex.org/I200769079'])]
        a['raw_affiliation_strings']=[]
    text='\n'.join(n+'\n'+aff for n,aff in zip(names,affs))+'\nAbstract'
    r=dict(version=1,work=work['id'],doi=work['doi'],source_work_sha256=A.digest(work),source_authorships_sha256=A.digest(work['authorships']),pdf_sha256='a'*64,pdf_url='https://example.edu/p.pdf',page1_text_sha256=hashlib.sha256(text.encode()).hexdigest(),byline_names=names,reviewed_by='reviewer',reviewed_at='2026-11-08',blocks=[dict(index=i,raw_name=n,author_id=work['authorships'][i]['author']['id'],affiliations=[aff],block_text=n+'\n'+aff,bbox=[i*100,0,i*100+90,40])for i,(n,aff)in enumerate(zip(names,affs))])
    ctx=types.SimpleNamespace(school='hkust',inst=common.INST['hkust'],aff=re.compile(common.AFF['hkust'],re.I),tied={work['id']:dict(url=r['pdf_url'],pdf_sha256=r['pdf_sha256'],author_affiliation_review=r)},page_read={work['id']:('ok',zlib.compress(text.encode()),r['pdf_url'])},n=collections.Counter())
    original=copy.deepcopy(work);flags,info=papers.reviewed_byline_school(ctx,work)
    assert flags==['Second Author'] and info['status']=='accepted'
    assert papers.reviewed_byline_school(ctx,work)==(flags,info)and ctx.n['primary_pdf_affiliation_review_accepted']==1
    assert work==original
