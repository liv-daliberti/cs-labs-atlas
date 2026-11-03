#!/usr/bin/env python3
"""Download a pinned publication with resumable, SHA-256-checked objects. No credentials."""
import argparse, concurrent.futures, hashlib, json, os, shutil, tarfile, tempfile
from pathlib import Path
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def download(url, target, sha, size=None, byte_range=None):
    if target.is_file() and digest(target)==sha and (size is None or target.stat().st_size==size):return
    if not url.startswith('https://') and not url.startswith('http://127.0.0.1:'):raise ValueError('HTTPS download required')
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.partial')
    headers={'User-Agent':'python-requests/2.32.5'}
    if byte_range: headers['Range']=f'bytes={byte_range[0]}-{byte_range[1]}'
    try:
        with urlopen(Request(url,headers=headers),timeout=120) as r, temp.open('wb') as f:
            if byte_range and r.status!=206:raise ValueError('Server ignored byte range')
            shutil.copyfileobj(r,f,2**20)
        if digest(temp)!=sha or (size is not None and temp.stat().st_size!=size):raise ValueError('Downloaded checksum or size differs: '+target.name)
        temp.replace(target)
    finally:temp.unlink(missing_ok=True)

def extract(archive, output):
    with tarfile.open(archive,'r:gz') as tar:
        for entry in tar:
            dest=output/entry.name
            if entry.name not in ('config.json','bundle.json') and not (entry.name.startswith('objects/') and len(entry.name)==72 and all(c in '0123456789abcdef' for c in entry.name[8:])):raise ValueError('Unexpected archive path')
            if not entry.isfile():raise ValueError('Archive links and special files are forbidden')
            dest.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(entry) as source, dest.open('wb') as target:shutil.copyfileobj(source,target)

def bootstrap(pin, output, papers=True, workers=4):
    cache=output.parent/(output.name+'.downloads');cache.mkdir(parents=True,exist_ok=True)
    catalog=cache/'catalog.json';download(pin['url'],catalog,pin['sha256'])
    meta=json.loads(catalog.read_text());archive=cache/'metadata.tar.gz'
    parts=[]
    for entry in meta['parts']:
        part=cache/entry['sha256'];download(entry['url'],part,entry['sha256'],entry['bytes']);parts.append(part)
    if not output.exists():
        with archive.open('wb') as target:
            for part in parts:
                with part.open('rb') as source:shutil.copyfileobj(source,target)
        stage=Path(tempfile.mkdtemp(prefix='.bootstrap-',dir=output.parent))
        try:
            extract(archive,stage);stage.rename(output)
        except BaseException:shutil.rmtree(stage);raise
    if json.loads((output/'config.json').read_text())!=meta['config']:raise ValueError('Existing output belongs to a different release')
    if papers:
        work={}
        for paper in meta['papers']:
            if paper.get('chunks'):
                offset=0
                for c in paper['chunks']:
                    work[c['sha256']]=(paper['url'],output/'objects'/c['sha256'],c['sha256'],c['size'],(offset,offset+c['size']-1));offset+=c['size']
            else:work[paper['sha256']]=(paper['url'],output/'objects'/paper['sha256'],paper['sha256'],paper['bytes'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for i,_ in enumerate(pool.map(lambda args:download(*args),work.values()),1):
                if i%100==0:print(json.dumps({'paperObjectsDownloaded':i,'total':len(work)}),flush=True)
    receipt={'schema':1,'mode':'copy','release':meta['config']['release'],'manifestSha256':meta['config']['manifestSha256'],'complete':papers,'catalogSha256':pin['sha256']}
    (output/'bundle.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt));return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pin',type=Path,default=ROOT/'deployment/bootstrap.json');p.add_argument('--output',type=Path,default=ROOT/'outputs/publication');p.add_argument('--without-papers',action='store_true');p.add_argument('--workers',type=int,choices=range(1,17),default=4);a=p.parse_args()
    bootstrap(json.loads(a.pin.read_text()),a.output.resolve(),not a.without_papers,a.workers)
