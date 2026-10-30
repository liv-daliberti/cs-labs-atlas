#!/usr/bin/env python3
# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/discover_princeton_fulltext.py (sha256 a8b044cd6ef038c55e4b132446ccd725a694e6b9a1166a10385825a1c2fed418); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Prepare evidence-backed full-text candidates without changing the live catalog."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import argparse
import collections
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
import unicodedata
from urllib.parse import urljoin, urlsplit, urlencode
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import requests

ROOT=P.WORLD_ATLAS
CORPUS=ROOT/'data/fulltext/princeton'
SOURCE=P.SWEEPS / 'claude-princeton-20261015'
STAGE=CORPUS/'discovery/expanded-20261015'
S3='https://pmc-oa-opendata.s3.amazonaws.com/'
UA='HomogenizingScienceResearch/0.1 (local academic paper collection)'
LOCAL=threading.local()


def norm(s):
    s=BeautifulSoup(s or '', 'html.parser').get_text(' ',strip=True)
    return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s).lower())


def doi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/','',s or '',flags=re.I).lower().strip()


def digest(b):return hashlib.sha256(b).hexdigest()


def evidence(key,data):
    p=STAGE/'evidence'/(digest(key.encode())+'.json')
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return str(p)



def merge_jsonl(path, rows, keys):
    """Keep prior discovery evidence when a later pass has fewer unresolved works."""
    previous=[json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    combined=list({tuple(r[k] for k in keys):r for r in previous+rows}.values())
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in combined))
    return combined


def fetch(url):
    p=STAGE/'responses'/(digest(url.encode())+'.body')
    if p.exists():return p.read_bytes(),str(p)
    if not hasattr(LOCAL,'session'):
        LOCAL.session=requests.Session();LOCAL.session.trust_env=False;LOCAL.session.headers['User-Agent']=UA
    r=LOCAL.session.get(url,timeout=(10,35))
    if r.status_code==429:raise RuntimeError('Rate limit encountered; stop this source')
    r.raise_for_status()
    p.write_bytes(r.content)
    (p.with_suffix('.json')).write_text(json.dumps({'url':url,'final_url':r.url,'sha256':digest(r.content),'retrieved_at':time.time(),'status':r.status_code}))
    return r.content,str(p)


def candidate(wid,url,landing,license,version,source):
    return dict(work_id=wid,url=url,landing_url=landing,license=license,version=version,metadata_source=source)


def local_bibliographies(db,landing=False):
    works={r['id']:dict(r) for r in db.execute('SELECT id,title,doi,graph_json FROM works')}
    by_source=collections.defaultdict(dict)
    for row in db.execute("SELECT source,record_json FROM edges WHERE kind='listed_by'"):
        if row['source'] not in works:continue
        for u in json.loads(row['record_json']).get('sourceUrls',[]):
            by_source[u.rstrip('/')][row['source']]=works[row['source']]
    candidates=[];scanned=0
    for manifest in sorted(SOURCE.glob('*/source_manifest.jsonl')):
        for line in manifest.read_text().splitlines():
            rec=json.loads(line);p=Path(rec.get('path',''))
            requested=rec.get('requested_url','');final=rec.get('final_url',requested)
            selected=by_source.get(requested.rstrip('/')) or by_source.get(final.rstrip('/'))
            if not selected or not p.is_file() or p.suffix!='.html':continue
            raw=p.read_bytes()
            if rec.get('sha256') and digest(raw)!=rec['sha256']:continue
            scanned+=1;soup=BeautifulSoup(raw,'html.parser')
            titles={i:norm(w['title']) for i,w in selected.items() if len(norm(w['title']))>=24}
            for a in soup.find_all('a',href=True):
                href=a['href'];label=a.get_text(' ',strip=True).lower()
                is_file=bool(re.search(r'\.pdf(?:[?#]|$)',href,re.I) or ('arxiv.org/' in href and ('/abs/' in href or '/pdf/' in href)))
                is_landing=urlsplit(urljoin(final,href)).hostname in {'openreview.net','proceedings.mlr.press','openaccess.thecvf.com','aclanthology.org','proceedings.neurips.cc','papers.nips.cc','roboticsproceedings.org','www.roboticsproceedings.org','jmlr.org','www.jmlr.org'}
                if (landing and (not is_landing or is_file)) or (not landing and not is_file):continue
                if re.search(r'supplement|commentary|slides|poster|erratum|appendix',label):continue
                url=urljoin(final,href)
                if urlsplit(url).hostname=='web.archive.org':continue
                for parent in [a]+list(a.parents)[:5]:
                    text=parent.get_text(' ',strip=True)
                    if len(text)>6000:break
                    n=norm(text)
                    matches=[i for i,t in titles.items() if t in n]
                    if len(matches)>1:break
                    if len(matches)!=1:continue
                    wid=matches[0]
                    # Match only inside the original bibliography entry, never across unrelated pages.
                    source=evidence(wid+'|'+url,{'method':'unique exact title within original sourced bibliography entry',
                      'work_id':wid,'title':selected[wid]['title'],'bibliography_url':requested,'pdf_url':url,
                      'source_snapshot':str(p),'source_sha256':digest(raw),'entry_text':text,'anchor_text':label,
                      'qualification':'Bibliography listing only; no inferred historical lab authorship.'})
                    candidates.append(candidate(wid,url,requested,None,'author_linked_version_unspecified',source));break
    print(json.dumps({'bibliography_pages_read':scanned,'explicit_file_links':len(candidates)}),flush=True)
    return candidates


def pmc_one(item):
    pmcid,works=item;result=[]
    url=S3+'?'+urlencode({'list-type':'2','prefix':pmcid+'.','delimiter':'/'})
    raw,list_path=fetch(url)
    root=ET.fromstring(raw);ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
    if root.findtext('s:IsTruncated',namespaces=ns)=='true':raise ValueError('Unexpected truncated PMCID version listing')
    versions=[x.text.rstrip('/') for x in root.findall('s:CommonPrefixes/s:Prefix',ns)]
    for version in versions:
        if not re.fullmatch(re.escape(pmcid)+r'\.\d+',version):raise ValueError('Unexpected PMC version key')
        data,path=fetch(S3+'metadata/'+version+'.json');m=json.loads(data)
        if m.get('pmcid')!=pmcid:raise ValueError('PMCID metadata mismatch')
        for w in works:
            if w['doi'] and doi(m.get('doi'))!=w['doi']:continue
            pdf=m.get('pdf_url')
            if pdf:
                if not pdf.startswith('s3://pmc-oa-opendata/'):raise ValueError('Unexpected PMC object bucket')
                pdf=S3+pdf[len('s3://pmc-oa-opendata/'):]
                result.append(candidate(w['id'],pdf,'https://pmc.ncbi.nlm.nih.gov/articles/'+pmcid+'/',m.get('license_code'),
                    'acceptedVersion' if m.get('is_manuscript') else 'publishedVersion',
                    evidence(w['id']+'|'+pdf,{'method':'exact PMCID and DOI in public NLM dataset metadata',
                        'work_id':w['id'],'metadata':m,'metadata_snapshot':path,'metadata_sha256':digest(data),'version_listing_snapshot':list_path})))
            elif m.get('xml_url'):
                evidence(w['id']+'|xml-only|'+version,{'work_id':w['id'],'status':'xml_available_no_pdf_in_distributed_dataset','metadata':m,'metadata_snapshot':path})
    return result


def repositories(db):
    pmcs=collections.defaultdict(dict);out=[]
    for row in db.execute('SELECT id,doi,oa_json FROM works WHERE oa_json IS NOT NULL'):
        w=dict(row)
        for loc in json.loads(w['oa_json']).get('locations') or []:
            if not loc.get('is_oa'):continue
            u=loc.get('pdf_url') or loc.get('landing_page_url') or ''
            host=urlsplit(u).hostname or ''
            if host in {'www.ncbi.nlm.nih.gov','pmc.ncbi.nlm.nih.gov'}:
                m=re.search(r'/articles/(?:PMC)?(\d+)',u)
                if m:pmcs['PMC'+m[1]][w['id']]={'id':w['id'],'doi':w['doi']}
            elif host=='www.osti.gov' and loc.get('pdf_url'):
                source=evidence(w['id']+'|'+u,{'method':'open-access fulltext URL in exact-identifier cached metadata','work_id':w['id'],'location':loc})
                out.append(candidate(w['id'],u,loc.get('landing_page_url'),loc.get('license'),loc.get('version'),source))
            elif loc.get('pdf_url') and (host.endswith('.edu') or host in {'openaccess.thecvf.com','proceedings.mlr.press','proceedings.neurips.cc','papers.nips.cc','openreview.net','eprint.iacr.org','zenodo.org','hal.science','hal.archives-ouvertes.fr'}):
                source=evidence(w['id']+'|'+u,{'method':'open-access fulltext URL in exact-identifier cached metadata','work_id':w['id'],'location':loc})
                out.append(candidate(w['id'],u,loc.get('landing_page_url'),loc.get('license'),loc.get('version'),source))
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(pmc_one,(k,list(v.values()))):k for k,v in pmcs.items()}
        for i,f in enumerate(concurrent.futures.as_completed(futures)):
            try:out.extend(f.result())
            except Exception as e:errors.append({'pmcid':futures[f],'error':str(e)})
            if i%25==0:print(json.dumps({'PMC_records_checked':i+1,'PMC_total':len(pmcs),'repository_candidates':len(out),'errors':len(errors)}),flush=True)
    (STAGE/'repository-errors.json').write_text(json.dumps(errors,indent=2))
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['local','local-landings','repositories']);args=p.parse_args()
    for name in ['evidence','responses']:(STAGE/name).mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect('file:'+str(CORPUS/'catalog.sqlite')+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row
    rows=local_bibliographies(db,args.mode=='local-landings') if args.mode.startswith('local') else repositories(db)
    rows=list({(r['work_id'],r['url']):r for r in rows}.values())
    path=STAGE/(args.mode+'-candidates.jsonl')
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    print(json.dumps({'mode':args.mode,'candidates':len(rows),'works':len({r['work_id'] for r in rows}),'path':str(path)}),flush=True)


if __name__=='__main__':main()
