"""Upload immutable release assets through the site's protected maintenance API.
Credentials arrive through secret environment variables or hidden stdin.
Receipts contain the destination, hashes and sizes, never credentials.
"""
from pathlib import Path
import argparse, concurrent.futures, csv, hashlib, json, re, threading, time
import requests
from publication_io import credentials, headers as credential_headers, origin, scoped_receipts
parser=argparse.ArgumentParser();parser.add_argument('--only-unverified',action='store_true');parser.add_argument('--paper-objects',type=Path);parser.add_argument('--reader-release',type=Path);parser.add_argument('--stores',type=Path);parser.add_argument('--workers',type=int,choices=range(1,33),default=8);parser.add_argument('--papers-only',action='store_true',help='Stage admitted immutable files without publishing an asset manifest');args=parser.parse_args()
if args.papers_only and not (args.paper_objects or args.reader_release):parser.error('--papers-only requires --paper-objects or --reader-release')
if args.reader_release and not args.stores:parser.error('--reader-release requires --stores')
ROOT=Path(__file__).resolve().parents[1]
plan=json.loads((ROOT/'atlas-storage/upload-plan.json').read_text())
base=origin(json.loads((ROOT/'deployment/release.json').read_text())['origin'])
try: values=credentials(update=True)
except ValueError as error: raise SystemExit(str(error)) from None
unauthenticated=requests.head(base+'/api/atlas-storage/'+'0'*64,timeout=30,allow_redirects=False)
assert unauthenticated.status_code in [401,403],'Protected update boundary was not confirmed; upload stopped'
headers=credential_headers(values,update=True)
probe=requests.head(base+'/api/atlas-storage/'+'0'*64,headers=headers,timeout=30,allow_redirects=False)
if probe.status_code not in (200,404):
    raise SystemExit('Maintenance authentication probe failed with HTTP '+str(probe.status_code)+'; no assets were uploaded.')
local=threading.local()
def session():
    if not hasattr(local,'session'):
        local.session=requests.Session();local.session.headers.update(headers)
    return local.session
receipt_path=ROOT/'atlas-storage/upload-receipts.json'
receipts=scoped_receipts(json.loads(receipt_path.read_text()),base) if receipt_path.exists() else {}
objects={}
if not args.papers_only:
    for name,entry in plan['files'].items():
        if entry.get('storage') == 'chunks-v1':
            assert sum(c['size'] for c in entry['chunks']) == entry['size']
            for chunk in entry['chunks']:
                objects.setdefault(chunk['sha256'],(ROOT/'atlas-storage/chunks'/chunk['sha256'],chunk['size']))
        else:
            objects.setdefault(entry['sha256'],(Path(plan['sourceDirectory'])/name,entry['size']))
# Reader-index PDFs use the existing content-addressed private-bucket route.
# Their bytes stay local to the collection without becoming oversized Git blobs.
if args.paper_objects:
    index=json.loads((Path(plan['sourceDirectory'])/'data/local-papers.json').read_text())
    admitted={f['sha256']:f for f in index.get('files',{}).values()}
    for file in args.paper_objects.iterdir():
        if not re.fullmatch(r'[a-f0-9]{64}\.pdf',file.name):continue
        meta=admitted.get(file.stem)
        if not meta or meta.get('path')!='papers/'+file.name:raise RuntimeError('PDF is not admitted by the current reader index')
        if file.stat().st_size!=meta['bytes']:raise RuntimeError('PDF byte count differs from reader index')
        objects.setdefault(file.stem,(file,meta['bytes']))
if args.reader_release:
    release=json.loads((args.reader_release/'MANIFEST.json').read_text())
    table=(args.reader_release/'reader/hosted-files.tsv').read_bytes()
    expected=release['files']['reader/hosted-files.tsv']
    assert len(table)==expected['bytes'] and hashlib.sha256(table).hexdigest()==expected['sha256'],'Release hosted-file list changed'
    index=json.loads((Path(plan['sourceDirectory'])/'data/local-papers.json').read_text())
    assert index['release']==release['release'],'Reader index is for another release'
    admitted=index['files'];listed={}
    for row in csv.DictReader(table.decode().splitlines(),delimiter='\t'):
        sha=row['sha256'];size=int(row['bytes']);file=(args.stores/row['school']/row['path']).resolve()
        assert file.is_relative_to(args.stores.resolve()),'Store path escapes the stores directory'
        assert sha in admitted and admitted[sha]['bytes']==size and admitted[sha]['path']=='papers/'+file.name,'File not admitted by the reader index'
        assert file.stat().st_size==size,'Stored file size changed'
        listed[sha]=size
        if admitted[sha].get('chunks'):
            chunks=admitted[sha]['chunks'];assert sum(c['size'] for c in chunks)==size
            for chunk in chunks:objects.setdefault(chunk['sha256'],(ROOT/'atlas-storage/chunks'/chunk['sha256'],chunk['size']))
        else:objects.setdefault(sha,(file,size))
    assert set(listed)==set(admitted),'Reader allowlist differs from release'
manifest=(ROOT/plan['manifestFile'],(ROOT/plan['manifestFile']).stat().st_size)
all_object_count=len(objects)
if args.only_unverified:
    objects={sha:entry for sha,entry in objects.items() if not (receipts.get(sha,{}).get('verified') and receipts[sha].get('size')==entry[1])}
def upload(item):
    sha,(file,size)=item;url=base+'/api/atlas-storage/'+sha
    data=file.read_bytes()
    assert len(data)==size and hashlib.sha256(data).hexdigest()==sha,'Source changed after manifest preparation'
    for attempt in range(3):
        try:
            if args.only_unverified or sha in receipts or attempt:
                r=session().head(url,timeout=60,allow_redirects=False)
                if r.status_code==200 and r.headers.get('X-Atlas-Sha256')==sha and int(r.headers.get('Content-Length','-1'))==size:return sha,dict(size=size,verified=True,already_present=True)
                if r.status_code in [401,403]:raise RuntimeError('Site rejected upload access')
            r=session().put(url,data=data,headers={'Content-Type':'application/octet-stream'},timeout=(30,180),allow_redirects=False)
            if r.status_code in [200,201]:
                v=r.json()
                if v.get('sha256')==sha and v.get('size')==size:return sha,dict(size=size,verified=True,already_present=v.get('already_present',False))
                raise RuntimeError('Upload acknowledgement does not match source')
            if r.status_code in [401,403]:raise RuntimeError('Site rejected upload access')
            if r.status_code not in [408,429,500,502,503,504]:raise RuntimeError('Upload failed with HTTP '+str(r.status_code))
        except requests.RequestException:
            if attempt==2:raise RuntimeError('Upload transport failed after bounded retries') from None
        time.sleep(2**attempt)
    raise RuntimeError('Upload did not complete')
def persist():
    tmp=receipt_path.with_suffix('.tmp');tmp.write_text(json.dumps({'schema':2,'origin':base,'objects':receipts},sort_keys=True)+'\n');tmp.replace(receipt_path)
failures=[];done=0
with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
    pending={pool.submit(upload,item):item[0] for item in objects.items()}
    for future in concurrent.futures.as_completed(pending):
        try:sha,r=future.result();receipts[sha]=r
        except Exception as exc:failures.append({'sha256':pending[future],'error':str(exc)[:160]})
        done+=1
        if done%100==0 or done==len(pending):
            persist();(ROOT/'atlas-storage/upload-failures.json').write_text(json.dumps(failures,indent=2)+'\n');print(json.dumps({'completed':done,'total':len(pending),'failures':len(failures)}),flush=True)
if failures:
    (ROOT/'atlas-storage/upload-failures.json').write_text(json.dumps(failures,indent=2)+'\n');raise SystemExit('Some objects failed; release manifest was not uploaded.')
if args.papers_only:
    print(json.dumps({'stagedPaperObjects':all_object_count,'allUploadsVerified':True,'manifestPublished':False}),flush=True)
    raise SystemExit(0)
sha,r=upload((plan['manifestSha256'],manifest));receipts[sha]=r;persist()
result={'origin':base,'manifestSha256':sha,'uniqueObjects':all_object_count+1,'logicalFiles':len(plan['files']),'sourceBytes':sum(v['size'] for v in plan['files'].values()),'allUploadsVerified':True}
(ROOT/'atlas-storage/upload-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
