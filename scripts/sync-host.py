#!/usr/bin/env python3
"""Copy canonical GitHub website code into a hosting adapter, refusing local conflicts."""
import argparse,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sync(destination):
    if destination.resolve()==ROOT:raise ValueError('Source and host must differ')
    selected=[]
    for name in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'):
        if name and (name.startswith(('atlas/','lib/','portable/','scripts/','schemas/')) or name in ('deployment/release.json','deployment/bootstrap.json')):
            if name.startswith(('atlas/data/','atlas/downloads/')):continue
            selected.append(name)
    dirty=subprocess.check_output(['git','status','--porcelain','--',*selected],cwd=destination).decode()
    if dirty.strip():raise ValueError('Host has uncommitted changes in shared source; commit or reconcile them first')
    for name in selected:
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_name(target.name+'.sync-tmp');shutil.copyfile(ROOT/name,temp);temp.replace(target)
    # Provider-specific package.json, lockfile, routes and hosting identity stay in the adapter.
    print(json.dumps({'sourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'copiedFiles':len(selected),'host':str(destination)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('host',type=Path);sync(p.parse_args().host.resolve())
