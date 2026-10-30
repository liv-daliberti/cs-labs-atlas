# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_arxiv_relations.py (sha256 ca850725bcfc5ad597a8826c6a543aa5293b779c8562996f3afd2f26a5a68d25); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Reviewed lab arXiv listings can corroborate separately identified publisher works.

The lab anchor, exact arXiv identifier and declared publisher DOI are replayed from
pinned bytes. Current complete titles/bylines, verified PI identity, and the PI's
own publication-time university must still match. Document IDs are never merged.
"""
import hashlib,importlib.util,json
from functools import lru_cache
from pathlib import Path
from common import ROOT
PACKAGE='cs17_arxiv_publisher_relation_review'
MANIFEST_SHA256='956058ee42235257b39ef5f20a18ea75f189199bff549469abdead74f0d88c02'
PINS={PACKAGE:MANIFEST_SHA256, 'cs18_arxiv_publisher_relation_review':'1c66f8f5f9b5445c818a7147b75eb2a99fe2b215a7279e809d8562d4670f4019'}
FORMAT='reviewed_lab_arxiv_publisher_relation_v1'
REASON='reviewed_lab_arxiv_listing_with_verified_publisher_relation'

@lru_cache(maxsize=4)
def context(package=PACKAGE):
    pin=PINS[package]
    folder=ROOT/'data/reviews'/package
    manifest=folder/'manifest.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!=pin:
        raise ValueError('Reviewed arXiv relation manifest changed')
    for record in json.loads(manifest.read_text())['files']:
        path=(folder/record['path']).resolve()
        if not path.is_relative_to(folder.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Reviewed arXiv relation package changed')
    spec=importlib.util.spec_from_file_location('frozen_arxiv_relation_replay',folder/'replay.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    replay=module.ReviewReplay(folder,pin)
    proposals=json.loads((folder/'results/broader_pair_proposals.json').read_text())
    index={}
    for proposal in proposals:
        index.setdefault((proposal['lab_id'],proposal['publisher_doi']),[]).append(proposal)
    return replay,index

def reviewed_link(identity,work,canonical_id):
    from publications import normalize_doi
    outcomes=[]
    for package in PINS:
        replay,index=context(package)
        proposals=index.get((identity['lab_id'],normalize_doi(work.get('doi'))),[])
        for proposal in proposals:
            result=replay.validate_current(identity['lab_id'],proposal['publisher_doi'],proposal['arxiv_id'],work,identity,canonical_id)
            outcomes.append(result)
            if result['eligible']:
                return dict(lab_id=identity['lab_id'],doi=proposal['publisher_doi'],review_status='accepted',source_url=result['review_source_url'],evidence_format=FORMAT,arxiv_id=proposal['arxiv_id'],relation_manifest_sha256=replay.pin),outcomes
    return None,outcomes
