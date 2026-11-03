#!/usr/bin/env python3
"""Build versioned metadata downloads; paper copies remain exact admitted public URLs."""
import argparse, hashlib, io, json, tarfile, tempfile
from pathlib import Path
from bootstrap import digest
ROOT=Path(__file__).resolve().parents[1]
def package(tag,origin):
    manifest=json.loads((ROOT/'deployment/asset-manifest.json').read_text())
    manifest['files']={n:e for n,e in manifest['files'].items() if not n.startswith('downloads/publications/')}
    output=ROOT/'atlas/downloads/publications'/tag
    if output.exists():raise ValueError('Publication tag already exists')
    output.mkdir(parents=True)
    raw=json.dumps(manifest,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
    pin=json.loads((ROOT/'deployment/release.json').read_text());config={'schema':1,'release':pin['release'],'manifestSha256':sha}
    objects={}
    for name,entry in manifest['files'].items():
        if entry.get('chunks'):
            for c in entry['chunks']:objects[c['sha256']]=ROOT/'atlas-storage/chunks'/c['sha256']
        else:objects[entry['sha256']]=ROOT/'atlas'/name
    with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as tmp:
        archive=Path(tmp)/'metadata.tar.gz'
        with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
            def inline(name,value):
                info=tarfile.TarInfo(name);info.size=len(value);info.mtime=0;info.mode=0o644;tar.addfile(info,io.BytesIO(value))
            inline('config.json',json.dumps(config).encode());inline('bundle.json',json.dumps({'mode':'copy','complete':False}).encode());inline('objects/'+sha,raw)
            for key,source in sorted(objects.items()):
                if digest(source)!=key:raise ValueError('Source changed while packaging')
                info=tar.gettarinfo(str(source),'objects/'+key);info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
                with source.open('rb') as f:tar.addfile(info,f)
        parts=[]
        with archive.open('rb') as f:
            while block:=f.read(32*2**20):
                name=f'metadata.part{len(parts):03d}';(output/name).write_bytes(block);parts.append({'url':origin+'/downloads/publications/'+tag+'/'+name,'sha256':hashlib.sha256(block).hexdigest(),'bytes':len(block)})
    index=json.loads((ROOT/'atlas/data/reader-objects.json').read_text())
    papers=[{'sha256':key,'bytes':size,'url':origin+'/papers/'+key+'.'+index.get('formats',{}).get(key,'pdf'),**({'chunks':index['chunks'][key]} if key in index.get('chunks',{}) else {})} for key,size in index['files'].items()]
    catalog=output/'catalog.json';catalog.write_text(json.dumps({'schema':1,'tag':tag,'config':config,'parts':parts,'papers':papers,'paperAvailability':'Only currently admitted files are served; withdrawals remain effective.'},separators=(',',':'))+'\n')
    bootstrap={'schema':1,'tag':tag,'url':origin+'/downloads/publications/'+tag+'/catalog.json','sha256':digest(catalog)}
    (ROOT/'deployment/bootstrap.json').write_text(json.dumps(bootstrap,indent=2)+'\n');print(json.dumps(bootstrap))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--origin',required=True);a=p.parse_args();package(a.tag,a.origin.rstrip('/'))
