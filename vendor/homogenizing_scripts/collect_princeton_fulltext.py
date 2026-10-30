#!/usr/bin/env python3
# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/collect_princeton_fulltext.py (sha256 df47b7370e9a1893cf859fb61ca3626a5900818a674a113fffe6645126186584); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Local, resumable Princeton full-text collection; never publishes or logs in."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import argparse
import collections
import csv
import datetime as dt
import difflib
import fcntl
import gzip
import hashlib
from html.parser import HTMLParser
from html import unescape
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import unicodedata
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

ROOT = P.WORLD_ATLAS
DEFAULT_OUT = ROOT / 'data/fulltext/princeton'
DEFAULT_GRAPH = P.SWEEPS / 'princeton-live-20261015/batches/0007/graph.json.gz'
DEFAULT_CACHE = ROOT / 'data/reviews/unipapers/princeton-university/openalex_institution/pages'
UA = 'HomogenizingScienceResearch/0.1 (local academic paper collection)'
ALLOWED = {'oar.princeton.edu', 'arxiv.org', 'export.arxiv.org'}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def dump(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doi(value):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', value or '', flags=re.I).lower().strip()


def connect(out):
    db = sqlite3.connect(out / 'catalog.sqlite', timeout=120)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS works (
          id TEXT PRIMARY KEY, title TEXT, doi TEXT, year INTEGER,
          graph_json TEXT NOT NULL, oa_json TEXT, metadata_source TEXT,
          status TEXT NOT NULL DEFAULT 'queued', file_path TEXT,
          sha256 TEXT, byte_count INTEGER, pages INTEGER,
          download_url TEXT, downloaded_at TEXT, identity_check TEXT);
        CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT, record_json TEXT);
        CREATE TABLE IF NOT EXISTS edges (id TEXT PRIMARY KEY, source TEXT, target TEXT, kind TEXT, record_json TEXT);
        CREATE INDEX IF NOT EXISTS edges_source ON edges(source);
        CREATE INDEX IF NOT EXISTS edges_target ON edges(target);
        CREATE TABLE IF NOT EXISTS candidates (
          work_id TEXT, url TEXT, landing_url TEXT, license TEXT, version TEXT,
          metadata_source TEXT, PRIMARY KEY(work_id,url));
        CREATE TABLE IF NOT EXISTS attempts (
          id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT,
          status TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY, value TEXT);
    ''')
    return db


def seed(db, args):
    if db.execute('SELECT 1 FROM receipts WHERE key=?', ('seed_complete',)).fetchone():
        print('Seed already complete; preserving existing graph and download state.', flush=True)
        return
    blob = args.graph.read_bytes()
    graph = json.loads(gzip.decompress(blob) if args.graph.suffix == '.gz' else blob)
    nodes = {n['id']: n for n in graph['nodes']}
    paper_ids = {e['source'] for e in graph['edges'] if e['type'] == 'listed_by'
                 and nodes[e['target']]['type'] == 'lab'
                 and nodes[e['source']]['type'] == 'paper'
                 and args.start_year <= int(nodes[e['source']].get('year') or 0) <= args.end_year}
    selected = set(paper_ids)
    # Retain explicit authors and bibliography relationships, then organizational context.
    for e in graph['edges']:
        if (e['source'] in paper_ids or e['target'] in paper_ids) and e['type'] in {'listed_by', 'authored', 'affiliated_with'}:
            selected.update((e['source'], e['target']))
    labs = {i for i in selected if nodes[i]['type'] == 'lab'}
    for e in graph['edges']:
        if e['target'] in labs and e['type'] == 'leads':
            selected.add(e['source'])
    while True:
        before = len(selected)
        for e in graph['edges']:
            if e['type'] == 'same_identity' and (e['source'] in selected or e['target'] in selected):
                selected.update((e['source'], e['target']))
            if e['source'] in selected and e['type'] in {'affiliated_with', 'member_of'}:
                selected.add(e['target'])
        if len(selected) == before:
            break
    for i in selected:
        n = nodes[i]
        db.execute('INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)', (i,n['type'],n['name'],dump(n)))
    for i in sorted(paper_ids):
        n = nodes[i]
        db.execute('INSERT OR IGNORE INTO works(id,title,doi,year,graph_json) VALUES (?,?,?,?,?)',
                   (i,n['name'],doi(n.get('doi')),n.get('year'),dump(n)))
    for e in graph['edges']:
        if e['source'] in selected and e['target'] in selected:
            raw = dump(e)
            db.execute('INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)', (sha(raw.encode()),e['source'],e['target'],e['type'],raw))
    db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)', ('graph',dump({
        'path':str(args.graph),'sha256':sha(blob),'updated_at':graph.get('updatedAt'),
        'window':[args.start_year,args.end_year], 'selection':'explicit lab bibliography listing; no inferred lab authorship',
        'paper_count':len(paper_ids),'imported_at':now()})))
    db.commit()
    del graph, nodes, blob
    by_doi = collections.defaultdict(list)
    by_oa = collections.defaultdict(list)
    for row in db.execute('SELECT id,doi,graph_json FROM works'):
        if row['doi']: by_doi[row['doi']].append(row['id'])
        oid = json.loads(row['graph_json']).get('openalex')
        if oid: by_oa[oid].append(row['id'])
    matched = set()
    paths = sorted(args.cache.glob('*.json.gz'))
    for index, path in enumerate(paths):
        raw = path.read_bytes()
        page = json.loads(gzip.decompress(raw))
        page_matches = 0
        for w in page.get('results', []):
            ids = set(by_doi.get(doi(w.get('doi')), [])) | set(by_oa.get(w.get('id'), []))
            if not ids: continue
            page_matches += len(ids)
            metadata = {k:w.get(k) for k in ['id','doi','title','publication_year','publication_date','type','open_access','authorships','locations','best_oa_location','is_retracted','updated_date']}
            locations = list(w.get('locations') or [])
            if w.get('best_oa_location'): locations.append(w['best_oa_location'])
            for wid in ids:
                # Matching uses identifiers only. A cached alias with a conflicting DOI is held.
                expected = db.execute('SELECT doi FROM works WHERE id=?',(wid,)).fetchone()[0]
                if expected and doi(w.get('doi')) and expected != doi(w['doi']):
                    db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',
                               (wid,w['id'],now(),'identifier_conflict',str(path)))
                    continue
                matched.add(wid)
                db.execute('UPDATE works SET oa_json=?,metadata_source=? WHERE id=?',(dump(metadata),str(path),wid))
                for loc in locations:
                    if not loc.get('is_oa'): continue
                    pdf, landing = loc.get('pdf_url'), loc.get('landing_page_url')
                    url = pdf or landing
                    if url and urlsplit(url).hostname in ALLOWED:
                        db.execute('INSERT OR REPLACE INTO candidates VALUES (?,?,?,?,?,?)',
                                   (wid,url,landing,loc.get('license'),loc.get('version'),str(path)))
        if page_matches:
            db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)', ('cache:'+str(path),dump({'path':str(path),'sha256':sha(raw),'matched_records':page_matches})))
        if index % 50 == 0:
            db.commit()
            print(dump({'cache_pages':index+1,'total_pages':len(paths),'matched_works':len(matched)}),flush=True)
    db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)',('seed_complete',now()))
    db.commit()
    print(dump({'seeded_works':len(paper_ids),'metadata_matched':len(matched),'candidate_locations':db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]}),flush=True)


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.citations=[]; self.pdfs=[]

    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='meta' and a.get('name','').lower()=='citation_pdf_url' and a.get('content'):
            self.citations.append(a['content'])
        if tag=='a' and '.pdf' in a.get('href','').lower() and '/bitstream/' in a.get('href',''):
            self.pdfs.append(a['href'])


class PublicClient:
    def __init__(self,out):
        self.out=out; self.session=requests.Session(); self.session.trust_env=False
        self.session.headers['User-Agent']=UA
        self.rules={}; self.last={}

    def pause(self,host):
        time.sleep(max(0,3-(time.monotonic()-self.last.get(host,0))))
        self.last[host]=time.monotonic()

    def get(self,url,limit=50*1024*1024):
        for redirect in range(6):
            u=urlsplit(url)
            if u.scheme not in {'http','https'} or u.hostname not in ALLOWED or u.username or u.password:
                raise ValueError('URL outside configured public repository scope')
            if u.scheme=='http': url='https:'+url[5:];u=urlsplit(url)
            host=u.hostname
            if host not in self.rules:
                self.pause(host)
                r=self.session.get('https://'+host+'/robots.txt',timeout=25)
                r.raise_for_status()
                (self.out/'sources'/f'{host}-robots.txt').write_text(r.text)
                robot=RobotFileParser();robot.parse(r.text.splitlines());self.rules[host]=robot
            if not self.rules[host].can_fetch(UA,url):
                raise ValueError('robots.txt disallows this URL')
            self.pause(host)
            with self.session.get(url,timeout=(15,45),allow_redirects=False,stream=True) as r:
                if r.status_code==429:
                    raise RuntimeError('rate_limited_stop')
                if r.is_redirect:
                    url=urljoin(url,r.headers['Location']);continue
                r.raise_for_status()
                chunks=[];size=0
                for chunk in r.iter_content(65536):
                    size+=len(chunk)
                    if size>limit:raise ValueError('Response exceeds configured size limit')
                    chunks.append(chunk)
                return b''.join(chunks),url,r.headers.get('Content-Type','')
        raise ValueError('Too many redirects')


def validate_pdf(data,path):
    if not data.lstrip().startswith(b'%PDF-'):
        raise ValueError('Response is not a PDF')
    path.write_bytes(data)
    result=subprocess.run(['pdfinfo',str(path)],capture_output=True,text=True,timeout=30)
    match=re.search(r'^Pages:\s+(\d+)',result.stdout,re.M)
    if result.returncode or not match or int(match[1])<1:
        raise ValueError('PDF failed pdfinfo validation')
    return int(match[1])


def check_identity(row,path):
    text=subprocess.run(['pdftotext','-f','1','-l','3',str(path),'-'],capture_output=True,text=True,timeout=30).stdout
    if (row['doi'] or '').lower().startswith('10.48550/arxiv.'):
        expected=row['doi'].lower().split('arxiv.',1)[1]
        found=re.search(r'arXiv:(\d{4}\.\d{4,5})(?:v\d+)?',text[:1500])
        if found and found[1]!=expected:raise ValueError('Primary arXiv identifier differs from catalog DOI')
    text=re.sub(r'arXiv:[^\n]*','',text)
    def norm(value):
        value=unescape(re.sub(r'<[^>]+>','',value))
        return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',value).lower())
    title=norm(row['title'] or '')
    if len(title)>20 and title in norm(text):return 'title_in_first_three_pages'
    if row['doi'] and row['doi'].lower() in text.lower():return 'doi_in_first_three_pages'
    layout=subprocess.run(['pdftotext','-layout','-f','1','-l','1',str(path),'-'],capture_output=True,text=True,timeout=30).stdout
    layout=re.sub(r'arXiv:[^\n]*','',layout)
    if len(title)>20 and title in norm(layout):return 'title_in_first_page_layout'
    info=subprocess.run(['pdfinfo',str(path)],capture_output=True,text=True,timeout=30).stdout
    embedded=re.search(r'^Title:\s*(.+)$',info,re.M)
    if embedded:
        observed=norm(embedded[1])
        if len(observed)>=40 and len(embedded[1].split())>=5 and observed in norm(layout) and difflib.SequenceMatcher(None,title,observed).ratio()<0.5:
            raise ValueError('Embedded first-page article title differs from catalog title')
    return 'provider_link_only_review_pending'


def collect(db,args):
    client=PublicClient(args.out)
    # Round-robin across bibliography units; newest papers first within each unit.
    rows=db.execute('''SELECT DISTINCT w.id,w.year,e.target AS lab FROM works w
      JOIN candidates c ON c.work_id=w.id JOIN edges e ON e.source=w.id AND e.kind='listed_by'
      WHERE w.status='queued' ORDER BY w.year DESC,w.id''').fetchall()
    grouped=collections.defaultdict(list)
    for row in rows:grouped[row['lab']].append(row['id'])
    queue=[];seen=set()
    while grouped:
        for lab in list(sorted(grouped)):
            wid=grouped[lab].pop(0)
            if wid not in seen:queue.append(wid);seen.add(wid)
            if not grouped[lab]:del grouped[lab]
    acquired=0
    for wid in queue[:args.limit]:
        row=db.execute('SELECT * FROM works WHERE id=?',(wid,)).fetchone()
        locations=db.execute('SELECT * FROM candidates WHERE work_id=? ORDER BY CASE WHEN url LIKE ? THEN 0 ELSE 1 END,url',
                             (wid,'%oar.princeton.edu%')).fetchall()
        success=False
        for loc in locations:
            tmp=args.out/'objects'/f'.{wid}.part'
            try:
                data,final,ctype=client.get(loc['url'])
                if not data.lstrip().startswith(b'%PDF-'):
                    parser=Links();parser.feed(data.decode('utf-8',errors='replace'))
                    urls=list(dict.fromkeys(parser.citations or parser.pdfs))
                    if len(urls)!=1:raise ValueError('Landing page has no unambiguous primary PDF link')
                    page_path=args.out/'sources'/(sha(data)+'.html');page_path.write_bytes(data)
                    data,final,ctype=client.get(urljoin(final,urls[0]))
                pages=validate_pdf(data,tmp)
                digest=sha(data);path=args.out/'objects'/(digest+'.pdf')
                if path.exists():
                    if sha(path.read_bytes())!=digest:raise ValueError('Existing object checksum mismatch')
                    tmp.unlink()
                else:tmp.replace(path)
                identity=check_identity(row,path)
                db.execute('UPDATE works SET status=?,file_path=?,sha256=?,byte_count=?,pages=?,download_url=?,downloaded_at=?,identity_check=? WHERE id=?',
                           ('downloaded',str(path.relative_to(args.out)),digest,len(data),pages,final,now(),identity,wid))
                db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',
                           (wid,loc['url'],now(),'downloaded',dump({'final_url':final,'sha256':digest,'content_type':ctype,'license_as_listed':loc['license'],'version_as_listed':loc['version']})))
                db.commit();acquired+=1;success=True
                print(dump({'downloaded':acquired,'paper':wid,'title':row['title'],'pages':pages,'identity_check':identity}),flush=True)
                break
            except (requests.RequestException,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
                db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',(wid,loc['url'],now(),'unavailable',str(exc)))
                db.commit()
                if str(exc)=='rate_limited_stop':
                    print('Repository rate limited; stopping this pass.',flush=True)
                    return
            finally:
                if tmp.exists():tmp.unlink()
        if not success:
            db.execute('UPDATE works SET status=? WHERE id=?',('needs_access_review',wid));db.commit()
            print(dump({'paper':wid,'status':'needs_access_review'}),flush=True)
    print(dump({'pass_complete':True,'new_downloads':acquired}),flush=True)


def export(db,args):
    fields=['paper_id','title','doi','year','status','local_pdf','sha256','byte_count','pages','identity_check','lab_ids','lab_names','download_url','download_version','license_as_listed']
    with (args.out/'catalog.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in db.execute('SELECT * FROM works ORDER BY year DESC,title'):
            labs=db.execute("SELECT DISTINCT n.id,n.name FROM edges e JOIN nodes n ON n.id=e.target WHERE e.source=? AND e.kind='listed_by' AND n.kind='lab' ORDER BY n.name",(row['id'],)).fetchall()
            attempt=db.execute("SELECT detail FROM attempts WHERE work_id=? AND status='downloaded' ORDER BY id DESC LIMIT 1",(row['id'],)).fetchone()
            details=json.loads(attempt[0]) if attempt else {}
            writer.writerow(dict(zip(fields,[row['id'],row['title'],row['doi'],row['year'],row['status'],row['file_path'],row['sha256'],row['byte_count'],row['pages'],row['identity_check'],'; '.join(x['id'] for x in labs),'; '.join(x['name'] for x in labs),row['download_url'],details.get('version_as_listed'),details.get('license_as_listed')])))
    with gzip.open(args.out/'relationships.jsonl.gz','wt') as f:
        for row in db.execute('SELECT record_json FROM edges ORDER BY id'):f.write(row[0]+'\n')
    with gzip.open(args.out/'entities.jsonl.gz','wt') as f:
        for row in db.execute('SELECT record_json FROM nodes ORDER BY id'):f.write(row[0]+'\n')
    with (args.out/'lab_leadership.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['lab_id','lab_name','person_id','person_name','role_as_listed','status_as_listed','evidence_json'])
        for row in db.execute("SELECT e.record_json,p.id,p.name,l.id,l.name FROM edges e JOIN nodes p ON p.id=e.source JOIN nodes l ON l.id=e.target WHERE e.kind='leads' ORDER BY l.name,p.name"):
            e=json.loads(row[0]);writer.writerow([row[3],row[4],row[1],row[2],e.get('role'),e.get('status'),row[0]])
    # Per-lab folders point to one checksum-addressed copy of each PDF.
    for row in db.execute("SELECT DISTINCT w.id,w.year,w.file_path,n.id,n.name FROM works w JOIN edges e ON e.source=w.id AND e.kind='listed_by' JOIN nodes n ON n.id=e.target AND n.kind='lab' WHERE w.status='downloaded'"):
        name=re.sub(r'[^a-z0-9]+','-',row[4].lower()).strip('-')[:70]
        directory=args.out/'by_lab'/(name+'--'+row[3]);directory.mkdir(parents=True,exist_ok=True)
        link=directory/(str(row[1])+'--'+row[0].replace('/','%2F')+'.pdf')
        target=Path('../..')/row[2]
        if not link.is_symlink() and not link.exists():link.symlink_to(target)
        elif link.resolve()!=(args.out/row[2]).resolve():raise ValueError('Unexpected existing lab PDF link')
    summary={'updated_at':now(),'status_counts':dict(db.execute('SELECT status,COUNT(*) FROM works GROUP BY status').fetchall()),
             'works_with_repository_candidates':db.execute('SELECT COUNT(DISTINCT work_id) FROM candidates').fetchone()[0],
             'download_bytes':db.execute('SELECT COALESCE(SUM(byte_count),0) FROM works').fetchone()[0],
             'labs_with_downloads':db.execute("SELECT COUNT(DISTINCT e.target) FROM edges e JOIN works w ON w.id=e.source WHERE e.kind='listed_by' AND w.status='downloaded'").fetchone()[0],
             'identity_checks':dict(db.execute('SELECT identity_check,COUNT(*) FROM works WHERE status=? GROUP BY identity_check',('downloaded',)).fetchall()),
             'source_graph':json.loads(db.execute('SELECT value FROM receipts WHERE key=?',('graph',)).fetchone()[0]),
             'complete':False,'attribution':'Existing sourced bibliography links; current leadership and paper authorship are separate relations. No new PI/lab attribution is inferred.'}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(dump(summary),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['seed','collect','export','verify'])
    p.add_argument('--out',type=Path,default=DEFAULT_OUT)
    p.add_argument('--graph',type=Path,default=DEFAULT_GRAPH)
    p.add_argument('--cache',type=Path,default=DEFAULT_CACHE)
    p.add_argument('--start-year',type=int,default=2016)
    p.add_argument('--end-year',type=int,default=2026)
    p.add_argument('--limit',type=int,default=50,help='Maximum queued works to attempt in this invocation')
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    for name in ['objects','sources']:(args.out/name).mkdir(exist_ok=True)
    with (args.out/'.collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        db=connect(args.out)
        if args.command=='seed':seed(db,args)
        if args.command=='collect':collect(db,args)
        if args.command=='verify':
            count=0
            for row in db.execute("SELECT * FROM works WHERE status='downloaded'"):
                data=(args.out/row['file_path']).read_bytes()
                assert sha(data)==row['sha256'] and len(data)==row['byte_count']
                assert data.startswith(b'%PDF-')
                info=subprocess.run(['pdfinfo',str(args.out/row['file_path'])],capture_output=True,text=True,timeout=30)
                assert info.returncode==0 and re.search(r'^Pages:\s+'+str(row['pages'])+r'\s*$',info.stdout,re.M)
                if row['identity_check']=='provider_link_only_review_pending':
                    identity=check_identity(row,args.out/row['file_path'])
                    if identity!='provider_link_only_review_pending':
                        db.execute('UPDATE works SET identity_check=? WHERE id=?',(identity,row['id']))
                        db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',
                                   (row['id'],row['download_url'],now(),'identity_rechecked',identity))
                count+=1
            db.commit()
            assert not db.execute('SELECT 1 FROM edges e LEFT JOIN nodes a ON e.source=a.id LEFT JOIN nodes b ON e.target=b.id WHERE a.id IS NULL OR b.id IS NULL LIMIT 1').fetchone()
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            print(dump({'verified_pdfs':count,'all_relationship_endpoints_resolve':True,'sqlite_integrity':'ok'}))
        export(db,args)
        db.close()


if __name__=='__main__':main()
