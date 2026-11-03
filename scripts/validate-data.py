#!/usr/bin/env python3
"""Validate the website export boundary independently of the UI."""
import argparse,gzip,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate(root):
    data=json.loads((root/'data.json').read_text())
    if data.get('bundleFormat')!='lazy-atlas-v1' or not isinstance(data.get('universities'),list):raise ValueError('Invalid atlas export')
    if not isinstance(data.get('assets'),dict) or not data.get('csScope',{}).get('rule'):raise ValueError('Missing assets or scope contract')
    ids=[u['id'] for u in data['universities']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate university IDs')
    index=json.loads((root/'data/cs-hierarchy/index.json').read_text());count=0
    for school in index['schools']:
        h=json.loads(gzip.decompress((root/f"data/cs-hierarchy/{school['id']}.json.gz").read_bytes()))
        for key in ['labs','papers','students','departments']:
            if not isinstance(h.get(key),list):raise ValueError('Invalid hierarchy '+key)
        if h['school']['id']!=school['id']:raise ValueError('School identity mismatch')
        for lab in h['labs']:
            if not isinstance(lab.get('id'),str) or not isinstance(lab.get('pi'),dict):raise ValueError('Invalid lab identity')
            for paper in lab['papers']:
                if not isinstance(paper[0],int) or not 0<=paper[0]<len(h['papers']):raise ValueError('Paper index out of bounds')
            for student in lab['students']:
                if not isinstance(student[0],int) or not 0<=student[0]<len(h['students']):raise ValueError('Student index out of bounds')
            for link in lab['links']:
                if not 0<=link[0]<len(h['students']) or not 0<=link[1]<len(h['papers']):raise ValueError('Authorship index out of bounds')
            count+=1
    print(json.dumps({'schools':len(index['schools']),'labsChecked':count,'contract':'website-export-v1'}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--atlas',type=Path,default=ROOT/'atlas');validate(p.parse_args().atlas)
