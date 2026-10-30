#!/usr/bin/env python3
# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/collect_princeton_fulltext_expanded.py (sha256 0d2a191e5bb75272e1d3e651cec43dd8c2581d55f8cf744c32d0b695efb2ca65); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Exhaust evidence-backed public full-text candidates; one writer, per-host throttling."""
import argparse
import collections
import concurrent.futures
import datetime as dt
import fcntl
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import threading
import time
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs
import xml.etree.ElementTree as ET

from protego import Protego
import requests
import collect_princeton_fulltext as base

CORPUS=base.DEFAULT_OUT
STAGE=CORPUS/'discovery/expanded-20261015'
S3='pmc-oa-opendata.s3.amazonaws.com'
CDNS={'images.squarespace-cdn.com','static1.squarespace.com','dl.dropboxusercontent.com','www.dropbox.com','www.dropboxusercontent.com'}
# Public file/repository destinations observed in redirects from source-listed URLs.
# Authentication providers and local/private destinations remain excluded.
PUBLIC_REDIRECT_HOSTS={'watermark02.silverchair.com','rscj.silverchair-cdn.com',
    'assets-eu.researchsquare.com','api.repository.cam.ac.uk','pure.mpg.de','files.osf.io',
    'www.chimia.ch','www.bnl.gov','raw.githubusercontent.com','nbn-resolving.org',
    'access.archive-ouverte.unige.ch'}


def nonarticle_reason(loc):
    source=Path(loc.get('metadata_source') or '')
    label=''
    if source.is_file() and source.suffix=='.json':
        proof=json.loads(source.read_text())
        label=proof.get('anchor_text','').strip().lower()
    url=loc.get('url','').lower()
    if label in {'si','esi','supp','supporting information','explanatory slide','slides','poster'}:
        return 'supplementary or presentation file explicitly labeled in source'
    if re.search(r'(?:/suppl/|/suppl_file/|downloadsupplement|supinfo/|[._-]si(?:_\d+)?\.pdf|\.s\d{3}\.pdf|\.sapp\.pdf)',url):
        return 'supplementary file identified by publisher or author URL'
    return None


def reclassify_nonarticles(db,out):
    changed=[]
    rows=db.execute("SELECT * FROM assets WHERE kind='pdf'").fetchall()
    for row in rows:
        reason=nonarticle_reason({'url':row['url'],'metadata_source':row['metadata_source']})
        if not reason:continue
        db.execute("UPDATE assets SET kind='supplement_pdf',identity_check='supplement_not_primary_article' WHERE work_id=? AND kind='pdf' AND url=?",(row['work_id'],row['url']))
        current=db.execute('SELECT * FROM works WHERE id=?',(row['work_id'],)).fetchone()
        if current and current['sha256']==row['sha256']:
            db.execute("UPDATE works SET status='queued',file_path=NULL,sha256=NULL,byte_count=NULL,pages=NULL,download_url=NULL,downloaded_at=NULL,identity_check=NULL WHERE id=?",(row['work_id'],))
            for link in (out/'by_lab').glob('*/'+str(current['year'])+'--'+row['work_id']+'.pdf'):
                if link.is_symlink() and link.resolve()==(out/row['path']).resolve():link.unlink()
        db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',(row['work_id'],row['url'],base.now(),'excluded_nonarticle',reason))
        changed.append({'work_id':row['work_id'],'path':row['path'],'reason':reason})
    db.commit()
    if changed:
        (out/'supplementary-file-review.json').write_text(json.dumps(changed,indent=2)+'\n')
    return changed


class PublicClient:
    def __init__(self,out,allowed):
        self.out=out;self.allowed=set(allowed)|CDNS|PUBLIC_REDIRECT_HOSTS|{S3}
        self.local=threading.local();self.guard=threading.Lock()
        self.locks={};self.last={};self.rules={};self.blocked={};self.failures=collections.Counter()

    def get_lock(self,host):
        # arXiv's two public hostnames share a throttle.
        key='arxiv.org' if host in {'arxiv.org','export.arxiv.org'} else host
        with self.guard:return self.locks.setdefault(key,threading.Lock()),key

    def session(self):
        if not hasattr(self.local,'session'):
            self.local.session=requests.Session();self.local.session.trust_env=False
            self.local.session.headers['User-Agent']=base.UA
        return self.local.session

    def pause(self,key,delay):
        time.sleep(max(0,delay-(time.monotonic()-self.last.get(key,0))))
        self.last[key]=time.monotonic()

    def get(self,url,limit=100*1024*1024):
        for _ in range(8):
            u=urlsplit(url);host=u.hostname or ''
            if u.scheme=='http':url='https:'+url[5:];u=urlsplit(url)
            approved=host in self.allowed or host.endswith('.princeton.edu') or host in {'princeton.edu','pppl.gov'} or host.endswith('.pppl.gov')
            if u.scheme!='https' or not approved or u.username or u.password or u.port not in {None,443}:
                raise ValueError('Redirect or URL outside the evidence-approved public hosts: '+host)
            try:
                if ipaddress.ip_address(host).is_private:raise ValueError('Private address rejected')
            except ValueError:
                if re.fullmatch(r'[0-9.:]+',host):raise ValueError('IP-literal URL rejected')
            lock,key=self.get_lock(host)
            with lock:
                if key in self.blocked:raise RuntimeError('source_paused: '+self.blocked[key])
                delay=0.2 if host==S3 else 3.0
                if host!=S3 and host not in self.rules:
                    self.pause(key,delay)
                    try:
                        r=self.session().get('https://'+host+'/robots.txt',timeout=(10,25))
                        if r.status_code not in {200,401,403,404}:r.raise_for_status()
                    except requests.RequestException:
                        self.blocked[key]='robots policy unavailable; retry later'
                        raise
                    if r.status_code==404:robots=''
                    elif r.status_code in {401,403}:robots='User-agent: *\nDisallow: /\n'
                    else:r.raise_for_status();robots=r.text
                    p=self.out/'sources'/(host+'-robots.txt');p.write_text(robots)
                    self.rules[host]=Protego.parse(robots)
                if host!=S3:
                    if not self.rules[host].can_fetch(url,base.UA):raise ValueError('robots.txt disallows URL')
                    delay=max(delay,float(self.rules[host].crawl_delay(base.UA) or 0))
                self.pause(key,delay)
                try:
                    with self.session().get(url,timeout=(12,40),allow_redirects=False,stream=True) as r:
                        if r.status_code==429:
                            self.blocked[key]='HTTP 429; retry later per server guidance'
                            raise RuntimeError('source_paused: '+self.blocked[key])
                        if r.is_redirect:
                            url=urljoin(url,r.headers['Location']);continue
                        r.raise_for_status()
                        chunks=[];size=0
                        for chunk in r.iter_content(131072):
                            size+=len(chunk)
                            if size>limit:raise ValueError('Response exceeds 100 MiB size limit')
                            chunks.append(chunk)
                        self.failures[key]=0
                        return b''.join(chunks),url,r.headers.get('Content-Type','')
                except requests.RequestException as exc:
                    code=getattr(exc.response,'status_code',None)
                    if code in {403,429,500,502,503,504} or code is None:
                        self.failures[key]+=1
                        if self.failures[key]>=3:self.blocked[key]='Repeated access or network failures'
                    raise
        raise ValueError('Too many redirects')


def import_candidates(db,stage):
    counts=collections.Counter()
    metadata_file=stage/'doi-enrichment-metadata.jsonl'
    if metadata_file.exists():
        for line in metadata_file.read_text().splitlines():
            d=json.loads(line);row=db.execute('SELECT doi,oa_json FROM works WHERE id=?',(d['work_id'],)).fetchone()
            if row is None or row['doi']!=d['requested_doi'] or base.doi(d['metadata'].get('doi'))!=row['doi']:
                raise ValueError('DOI metadata import does not match its original work identifier')
            if row['oa_json'] is None:
                db.execute('UPDATE works SET oa_json=?,metadata_source=? WHERE id=?',(base.dump(d['metadata']),d['source_snapshot'],d['work_id']))
                counts['exact_doi_metadata_added']+=1
    for source_file in sorted(stage.glob('*-doi-verified.jsonl')):
        from discover_princeton_fulltext import norm
        verified=[json.loads(line) for line in source_file.read_text().splitlines()]
        identifiers=collections.defaultdict(set)
        for d in verified:identifiers[d['work_id']].add(d['proposed_doi'])
        for d in verified:
            if len(identifiers[d['work_id']])!=1:
                counts['ambiguous_source_dois_held']+=1;continue
            row=db.execute('SELECT doi,title,oa_json FROM works WHERE id=?',(d['work_id'],)).fetchone()
            if (row is None or row['doi'] not in {d['original_doi'],d['proposed_doi']}
                    or base.doi(d['metadata'].get('doi'))!=d['proposed_doi']
                    or norm(row['title'])!=norm(d['metadata'].get('title'))):
                raise ValueError('Source DOI metadata import failed identifier/title verification')
            if row['oa_json'] is None or row['doi']!=d['proposed_doi']:
                db.execute('UPDATE works SET doi=?,oa_json=?,metadata_source=? WHERE id=?',
                    (d['proposed_doi'],base.dump(d['metadata']),d['metadata_snapshot'],d['work_id']))
                counts['source_verified_metadata_added']+=1
        db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)',('verified_dois:'+source_file.name,base.dump({
            'path':str(source_file),'sha256':base.sha(source_file.read_bytes()),'imported_at':base.now(),
            'original_graph_identifiers_preserved':True})))
    for p in sorted(stage.glob('*-candidates.jsonl')):
        raw=p.read_bytes()
        for line in raw.decode().splitlines():
            row=json.loads(line)
            if not db.execute('SELECT 1 FROM works WHERE id=?',(row['work_id'],)).fetchone():raise ValueError('Unknown candidate work ID')
            proof=Path(row['metadata_source'])
            if not proof.is_file():raise ValueError('Missing candidate evidence')
            db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)',tuple(row[k] for k in ['work_id','url','landing_url','license','version','metadata_source']))
            reason=nonarticle_reason(row)
            if reason and not db.execute("SELECT 1 FROM attempts WHERE work_id=? AND url=? AND status='excluded_nonarticle'",(row['work_id'],row['url'])).fetchone():
                db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',(row['work_id'],row['url'],base.now(),'excluded_nonarticle',reason))
            counts[p.name]+=1
        db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)',('discovery:'+str(p),base.dump({'path':str(p),'sha256':base.sha(raw),'imported_at':base.now()})))
    # NLM distributes some manuscripts only as full-text XML. Preserve those copies too.
    for p in sorted((stage/'evidence').glob('*.json')):
        d=json.loads(p.read_text())
        if d.get('status')!='xml_available_no_pdf_in_distributed_dataset':continue
        m=d['metadata'];url=m.get('xml_url','')
        if not url.startswith('s3://pmc-oa-opendata/'):continue
        url='https://'+S3+'/'+url[len('s3://pmc-oa-opendata/'):]
        db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)',(d['work_id'],url,'https://pmc.ncbi.nlm.nih.gov/articles/'+m['pmcid']+'/',m.get('license_code'),'acceptedVersion' if m.get('is_manuscript') else 'publishedVersion',str(p)))
        counts['xml_candidates']+=1
    db.commit();print(base.dump({'imported_candidate_rows':dict(counts)}),flush=True)


def process_work(work,client,out):
    attempts=[];xml_result=None
    for loc in work['locations']:
        tmp=out/'objects'/('.'+base.sha(work['id'].encode())+'.expanded.part')
        try:
            reason=nonarticle_reason(loc)
            if reason:
                attempts.append((loc['url'],'excluded_nonarticle',reason));continue
            request_url=loc['url'];parsed=urlsplit(request_url)
            if parsed.hostname in {'arxiv.org','export.arxiv.org'} and parsed.path.startswith('/abs/'):
                request_url=urlunsplit((parsed.scheme,parsed.netloc,'/pdf/'+parsed.path[len('/abs/'):],parsed.query,''))
            data,final,ctype=client.get(request_url)
            xml=urlsplit(final).path.lower().endswith('.xml')
            if xml:
                root=ET.fromstring(data)
                if root.tag.split('}')[-1]!='article' or root.find('.//body') is None:raise ValueError('XML is not a complete JATS article')
                ids={base.doi(x.text) for x in root.findall('.//article-id') if x.attrib.get('pub-id-type')=='doi'}
                if work['doi'] and work['doi'] not in ids:raise ValueError('Full-text XML DOI mismatch')
                identity='doi_in_jats_article_metadata' if work['doi'] else 'exact_pmc_dataset_identifier'
                pages=None;ext='xml'
            else:
                if not data.lstrip().startswith(b'%PDF-'):
                    if b'<' not in data[:512]:raise ValueError('Response is neither a PDF nor an HTML landing page')
                    parser=base.Links();parser.feed(data.decode('utf-8',errors='replace'))
                    urls=list(dict.fromkeys(parser.citations or parser.pdfs))
                    if len(urls)!=1:raise ValueError('Response has no unambiguous primary PDF link')
                    (out/'sources'/(base.sha(data)+'.html')).write_bytes(data)
                    data,final,ctype=client.get(urljoin(final,urls[0]))
                pages=base.validate_pdf(data,tmp);ext='pdf'
            expected=parse_qs(urlsplit(final).query).get('md5',[None])[0]
            if expected and hashlib.md5(data).hexdigest()!=expected:raise ValueError('Publisher-provided MD5 mismatch')
            digest=base.sha(data);path=out/'objects'/(digest+'.'+ext)
            if ext=='xml':tmp.write_bytes(data)
            if path.exists():
                if base.sha(path.read_bytes())!=digest:raise ValueError('Existing object checksum mismatch')
                tmp.unlink()
            else:tmp.replace(path)
            if ext=='pdf':
                identity=base.check_identity(work,path)
                if identity=='provider_link_only_review_pending' and urlsplit(final).hostname==S3 and work['doi']:
                    proof=json.loads(Path(loc['metadata_source']).read_text())
                    if base.doi(proof.get('metadata',{}).get('doi'))==work['doi']:identity='doi_in_nlm_dataset_metadata'
            result={'work_id':work['id'],'kind':ext,'file_path':str(path.relative_to(out)),'sha256':digest,
                    'bytes':len(data),'pages':pages,'download_url':final,'downloaded_at':base.now(),'identity_check':identity,
                    'license':loc['license'],'version':loc['version'],'metadata_source':loc['metadata_source']}
            attempts.append((loc['url'],'downloaded' if ext=='pdf' else 'fulltext_xml',base.dump({
                'final_url':final,'sha256':digest,'content_type':ctype,'license_as_listed':loc['license'],
                'version_as_listed':loc['version'],'metadata_source':loc['metadata_source'],'format':ext})))
            result['attempts']=attempts
            return result
        except (requests.RequestException,ValueError,RuntimeError,AssertionError,subprocess.SubprocessError,ET.ParseError) as exc:
            attempts.append((loc['url'],'unavailable',str(exc)))
        finally:
            if tmp.exists():tmp.unlink()
    return {'work_id':work['id'],'kind':None,'attempts':attempts}


def save_result(db,r):
    wid=r['work_id']
    for url,status,detail in r['attempts']:
        db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',(wid,url,base.now(),status,detail))
    if r['kind']:
        db.execute('INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?)',(
            wid,r['kind'],r['download_url'],r['file_path'],r['sha256'],r['bytes'],r['version'],r['license'],r['metadata_source'],r['downloaded_at'],r['identity_check']))
        if r['kind']=='pdf':
            db.execute('UPDATE works SET status=?,file_path=?,sha256=?,byte_count=?,pages=?,download_url=?,downloaded_at=?,identity_check=? WHERE id=?',
                ('downloaded',r['file_path'],r['sha256'],r['bytes'],r['pages'],r['download_url'],r['downloaded_at'],r['identity_check'],wid))
        else:db.execute('UPDATE works SET status=? WHERE id=?',('fulltext_xml',wid))
    else:db.execute('UPDATE works SET status=? WHERE id=?',('needs_access_review',wid))
    db.commit()


def report(db,out):
    counts=dict(db.execute('SELECT status,COUNT(*) FROM works GROUP BY status').fetchall())
    r={'updated_at':base.now(),'status_counts':counts,
       'pdf_bytes':db.execute("SELECT COALESCE(SUM(byte_count),0) FROM works WHERE status='downloaded'").fetchone()[0],
       'xml_copies':db.execute("SELECT COUNT(*) FROM assets WHERE kind='xml'").fetchone()[0],
       'pending_identity_review':db.execute("SELECT COUNT(*) FROM works WHERE status='downloaded' AND identity_check='provider_link_only_review_pending'").fetchone()[0]}
    (out/'progress.json').write_text(json.dumps(r,indent=2)+'\n')
    print(base.dump(r),flush=True)
    return r


def finish(db,args):
    base.export(db,args)
    import csv
    with (args.out/'fulltext_assets.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['paper_id','format','source_url','local_path','sha256','bytes','version','license','evidence_path','downloaded_at','identity_check'])
        writer.writerows(db.execute('SELECT * FROM assets ORDER BY work_id,kind,url'))
    for row in db.execute("SELECT a.work_id,a.kind,a.path,w.year,n.id,n.name FROM assets a JOIN works w ON a.work_id=w.id JOIN edges e ON e.source=w.id AND e.kind='listed_by' JOIN nodes n ON n.id=e.target AND n.kind='lab' WHERE a.kind='xml'"):
        name=re.sub(r'[^a-z0-9]+','-',row[5].lower()).strip('-')[:70]
        directory=args.out/'by_lab'/(name+'--'+row[4]);directory.mkdir(parents=True,exist_ok=True)
        link=directory/(str(row[3])+'--'+row[0].replace('/','%2F')+'.xml')
        if not link.exists() and not link.is_symlink():link.symlink_to(Path('../..')/row[2])
    summary=json.loads((args.out/'summary.json').read_text())
    summary.update(report(db,args.out))
    summary['fulltext_works']=db.execute("SELECT COUNT(*) FROM works WHERE status IN ('downloaded','fulltext_xml')").fetchone()[0]
    summary['unique_pdf_files']=db.execute("SELECT COUNT(DISTINCT sha256) FROM works WHERE status='downloaded'").fetchone()[0]
    summary['unique_xml_files']=db.execute("SELECT COUNT(DISTINCT sha256) FROM assets WHERE kind='xml'").fetchone()[0]
    summary['supplement_files_excluded_from_paper_count']=db.execute("SELECT COUNT(*) FROM assets WHERE kind='supplement_pdf'").fetchone()[0]
    summary['labs_with_fulltext']=db.execute("SELECT COUNT(DISTINCT e.target) FROM edges e JOIN works w ON w.id=e.source WHERE e.kind='listed_by' AND w.status IN ('downloaded','fulltext_xml')").fetchone()[0]
    summary['unattempted_candidate_works']=db.execute("SELECT COUNT(DISTINCT c.work_id) FROM candidates c JOIN works w ON w.id=c.work_id WHERE w.status NOT IN ('downloaded','fulltext_xml') AND NOT EXISTS (SELECT 1 FROM attempts a WHERE a.work_id=c.work_id AND a.url=c.url)").fetchone()[0]
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=CORPUS)
    p.add_argument('--work-ids',type=Path,help='Restrict collection to newline-separated catalog work IDs');p.add_argument('--stage',type=Path,default=STAGE);p.add_argument('--workers',type=int,default=6)
    p.add_argument('--skip-candidate-import',action='store_true');p.add_argument('--export-only',action='store_true');p.add_argument('--import-only',action='store_true')
    p.add_argument('--retry-transient-after-hours',type=float,default=None,
                   help='Retry a timed-out/network-failed URL once after this delay; never overrides robots or access denial')
    args=p.parse_args()
    with (args.out/'.collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        db=base.connect(args.out)
        db.execute('CREATE INDEX IF NOT EXISTS attempts_work_url ON attempts(work_id,url)')
        db.execute('CREATE TABLE IF NOT EXISTS assets (work_id TEXT,kind TEXT,url TEXT,path TEXT,sha256 TEXT,bytes INTEGER,version TEXT,license TEXT,metadata_source TEXT,downloaded_at TEXT,identity_check TEXT,PRIMARY KEY(work_id,kind,url))')
        # Bring earlier PDFs into the unified asset manifest without fetching them again.
        for w in db.execute("SELECT * FROM works w WHERE status='downloaded' AND NOT EXISTS (SELECT 1 FROM assets a WHERE a.work_id=w.id AND a.kind='pdf')").fetchall():
            a=db.execute("SELECT detail FROM attempts WHERE work_id=? AND status='downloaded' ORDER BY id DESC LIMIT 1",(w['id'],)).fetchone()
            d=json.loads(a[0]) if a else {}
            db.execute('INSERT OR IGNORE INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?)',(w['id'],'pdf',w['download_url'],w['file_path'],w['sha256'],w['byte_count'],d.get('version_as_listed'),d.get('license_as_listed'),d.get('metadata_source',w['metadata_source']),w['downloaded_at'],w['identity_check']))
        db.commit()
        reclassify_nonarticles(db,args.out)
        if not args.skip_candidate_import:import_candidates(db,args.stage)
        if args.export_only or args.import_only:finish(db,args);return
        rows=db.execute("SELECT c.* FROM candidates c JOIN works w ON w.id=c.work_id WHERE w.status NOT IN ('downloaded','fulltext_xml') AND NOT EXISTS (SELECT 1 FROM attempts a WHERE a.work_id=c.work_id AND a.url=c.url) ORDER BY c.work_id").fetchall()
        limited=set()
        if args.retry_transient_after_hours is not None:
            if args.retry_transient_after_hours<0:raise ValueError('Retry delay must be nonnegative')
            now=dt.datetime.now(dt.timezone.utc)
            cutoff=now-dt.timedelta(hours=args.retry_transient_after_hours)
            for a in db.execute("SELECT url,observed_at,detail FROM attempts WHERE status='unavailable'"):
                if re.search(r'(?:HTTP 429|429 Client Error)',a['detail']) and dt.datetime.fromisoformat(a['observed_at'])>now-dt.timedelta(hours=24):
                    limited.add(urlsplit(a['url']).hostname)
            retries=[];attempt_history=collections.defaultdict(list)
            for attempt in db.execute('SELECT * FROM attempts ORDER BY id DESC'):
                attempt_history[(attempt['work_id'],attempt['url'])].append(attempt)
            for c in db.execute("SELECT c.* FROM candidates c JOIN works w ON w.id=c.work_id WHERE w.status NOT IN ('downloaded','fulltext_xml')"):
                if urlsplit(c['url']).hostname in limited:continue
                attempts=attempt_history[(c['work_id'],c['url'])]
                if len(attempts)!=1:continue
                a=attempts[0]
                if a['status']!='unavailable':continue
                detail=a['detail']
                transient=bool(re.search(r'(?:[Tt]imed? out|RemoteDisconnected|Connection reset|Connection aborted|50[0234] Server Error)',detail))
                corrected_redirect=bool(re.search(r'outside the evidence-approved public hosts: (?:[a-z0-9.-]+\.)?(?:princeton\.edu|pppl\.gov)$',detail))
                corrected_redirect=corrected_redirect or (detail.startswith('Redirect or URL outside the evidence-approved public hosts: ') and detail.rsplit(': ',1)[-1] in PUBLIC_REDIRECT_HOSTS)
                if corrected_redirect or (transient and dt.datetime.fromisoformat(a['observed_at'])<=cutoff):retries.append(c)
            rows+=retries
            print(base.dump({'one_time_transient_retries':len(retries),'recently_rate_limited_hosts_held':sorted(limited)}),flush=True)
        selected_order={}
        if args.work_ids:
            selected_order={wid:i for i,wid in enumerate(args.work_ids.read_text().splitlines())};rows=[r for r in rows if r['work_id'] in selected_order]
        grouped=collections.defaultdict(list)
        for r in rows:grouped[r['work_id']].append(dict(r))
        allowed={urlsplit(r['url']).hostname for r in db.execute('SELECT url FROM candidates')}
        # Author-hosted PDF redirects commonly land on the bibliography origin.
        allowed|={urlsplit(r[0]).hostname for r in db.execute('SELECT landing_url FROM candidates WHERE landing_url IS NOT NULL')}
        client=PublicClient(args.out,allowed)
        for host in limited:
            _,key=client.get_lock(host)
            client.blocked[key]='HTTP 429 recorded within the previous 24 hours; held for later'
        by_host=collections.defaultdict(list)
        def priority(loc):
            host=urlsplit(loc['url']).hostname or ''
            if urlsplit(loc['url']).path.endswith('.xml'):return 9
            if host==S3:return 0
            if host.endswith('.princeton.edu') or host=='princeton.edu':return 1
            if host=='www.osti.gov':return 2
            if host=='arxiv.org':return 4
            return 3
        work_metadata={r['id']:dict(r) for r in db.execute('SELECT id,title,doi,year FROM works')}
        for wid,locations in grouped.items():
            w=work_metadata[wid]
            w['locations']=sorted(locations,key=lambda r:(priority(r),r['url']))
            by_host[urlsplit(w['locations'][0]['url']).hostname].append(w)
        # Within each host, fill low-coverage lab gaps before prolific groups.
        priority_file=args.out/'atlas/princeton-fulltext.json.gz'
        coverage_priority={}
        if priority_file.exists():
            import gzip
            snapshot=json.loads(gzip.decompress(priority_file.read_bytes()))
            coverage={l['id']:l['listedLocal'] for l in snapshot['labs']}
            for p in snapshot['papers']:
                rank=min((coverage.get(l,100000) for l in p['labs']+p['piLabs']),default=100000)
                for alias in p['aliases']:coverage_priority[alias]=rank
            for values in by_host.values():values.sort(key=lambda w:coverage_priority.get(w['id'],100000),reverse=True)
        if selected_order:
            for values in by_host.values():values.sort(key=lambda w:selected_order.get(w['id'],1000000),reverse=True)
        queue=[]
        while by_host:
            for host in list(sorted(by_host)):
                queue.append(by_host[host].pop())
                if not by_host[host]:del by_host[host]
        print(base.dump({'candidate_works_to_attempt':len(queue),'workers':args.workers}),flush=True)
        # Keep one primary-host request in flight. A slow repository must not
        # occupy every worker while independent repositories have queued work.
        hostqueues=collections.defaultdict(collections.deque)
        for w in queue:hostqueues[urlsplit(w['locations'][0]['url']).hostname].append(w)
        ready=collections.deque(hostqueues);completed=0;last_report=time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures={}
            while ready or futures:
                while ready and len(futures)<args.workers:
                    host=ready.popleft();w=hostqueues[host].popleft()
                    futures[pool.submit(process_work,w,client,args.out)]=(host,w)
                finished,_=concurrent.futures.wait(futures,timeout=30,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in finished:
                    host,w=futures.pop(f);wid=w['id']
                    try:r=f.result()
                    except Exception as exc:
                        print(base.dump({'unexpected_work_failure':wid,'error':str(exc)}),flush=True)
                        r={'work_id':wid,'kind':None,'attempts':[(loc['url'],'worker_error',str(exc)) for loc in grouped[wid]]}
                    save_result(db,r);completed+=1
                    if hostqueues[host]:
                        if host in {S3,'arxiv.org','export.arxiv.org'}:ready.appendleft(host)
                        else:ready.append(host)
                    if completed%20==0:report(db,args.out);last_report=time.monotonic()
                if time.monotonic()-last_report>=60:
                    report(db,args.out);last_report=time.monotonic()
                    print(base.dump({'queue_progress':{'completed':completed,'remaining':sum(len(q) for q in hostqueues.values())+len(futures),'active_sources':sorted({host for host,_ in futures.values()}),'paused_sources':client.blocked}}),flush=True)
        print(base.dump({'paused_sources':client.blocked,'queue_exhausted':True}),flush=True)
        finish(db,args);db.close()


if __name__=='__main__':main()
