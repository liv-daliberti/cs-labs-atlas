# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_arxiv_pi_identity.py (sha256 f290606c416112025872653f7de733873efaf7185138ff6cd580fee13e815021); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Four source-reviewed owner chains; identity only, with no automatic lab links."""
import hashlib, importlib.util, json, tempfile
from functools import lru_cache
from pathlib import Path
from publications import ROOT, CUTOFF, sid, read_csv

PACKAGE = 'cs17_arxiv_PI_identity_followup'
PIN = '217ef7b2c23c069533e60070cd246bc227523dfb0387af9a64698b6b3fd0722e'
FORMAT = 'reviewed_official_owner_identity_v1'

def require(value, message):
    if not value: raise ValueError(message)

def read(path): return json.loads(path.read_text())
def digest(raw): return hashlib.sha256(raw).hexdigest()

def verify_package():
    folder = ROOT / 'data/reviews' / PACKAGE
    manifest = folder / 'freeze_manifest.json'
    require(digest(manifest.read_bytes()) == PIN, 'Owner identity manifest changed')
    for item in read(manifest)['files']:
        path = (folder / item['path']).resolve()
        require(path.is_relative_to(folder.resolve()), 'Owner identity package path escape')
        raw = path.read_bytes()
        require(digest(raw) == item['sha256'] and len(raw) == item.get('size', item.get('bytes')), 'Owner identity package bytes changed: ' + item['path'])
    return folder

def helper(folder):
    spec = importlib.util.spec_from_file_location('reviewed_four_owner_identity', folder / 'prepare.py')
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result

@lru_cache(maxsize=1)
def replay_package():
    folder = verify_package(); module = helper(folder)
    with tempfile.TemporaryDirectory(prefix='science-four-owner-replay-', dir='/tmp') as tmp:
        dest = Path(tmp); module.build(folder=folder, out=dest)
        for name in module.OUTS:
            require((dest / name).read_bytes() == (folder / name).read_bytes(), 'Owner identity replay differs: ' + name)
    return True

def proof(review):
    require(review.get('identity_evidence_format') == FORMAT and review.get('review_status') == 'accepted', 'Unaccepted owner identity review')
    require(review.get('owner_evidence_package') == PACKAGE and review.get('owner_evidence_manifest_sha256') == PIN, 'Unreviewed owner identity package')
    folder = verify_package(); replay_package()
    matches = [r for r in read(folder / 'identity_reviews_proposed.json') if r['lab_id'] == review['lab_id'] and r['pi_name'] == review['pi_name']]
    require(len(matches) == 1, 'Owner identity candidate is not unique')
    proposal = matches[0]
    for key, value in proposal.items():
        if key not in {'identity_evidence_format', 'review_status', 'adapter_status', 'notes'}:
            require(review.get(key) == value, 'Owner identity review changed: ' + key)
    chain = next(r for r in read(folder / 'owner_chain_proofs.json') if r['lab_id'] == review['lab_id'] and r['pi_name'] == review['pi_name'])
    candidate = next(r for r in read(folder / 'identity_proposals.json') if r['lab_id'] == review['lab_id'] and r['pi_name'] == review['pi_name'])
    return folder, chain, candidate

def verify_cached_source(meta, expected_hash):
    require(meta['sha256'] == expected_hash, 'Current owner identity source differs from reviewed snapshot')
    require(digest((ROOT / meta['snapshot_path']).read_bytes()) == expected_hash, 'Current owner identity source bytes changed')

def identity_row(review, lab, lab_evidence, client):
    folder, chain, candidate = proof(review)
    require(lab['lab_id'] == chain['lab_id'] and lab['university_id'] == chain['university_id'], 'Current unit differs from owner chain')
    role = chain['leadership']
    require(role in read_csv(ROOT / 'data/processed/leadership_evidence.csv'), 'Reviewed owner role is not integrated')
    require(lab_evidence['pi_lab_evidence_source_id'] == role['source_id'] and lab_evidence['pi_lab_evidence_sha256'] == role['source_sha256'], 'Current leadership source differs from owner chain')
    _, owner = client.fetch(review['identity_evidence_url'])
    verify_cached_source(owner, review['identity_profile_sha256'])
    content, source = client.fetch(candidate['author_source']['source']['requested_url'])
    verify_cached_source(source, review['author_profile_sha256'])
    author = json.loads(content)
    names = helper(folder).validate_author(chain, author, review['openalex_author_id'])
    owned_orcid = chain['method'] == 'explicit_owned_orcid'
    require(bool(review['orcid']) == owned_orcid, 'Metadata ORCID must not become an owner claim')
    key = review['orcid'] if owned_orcid else author['id']
    return dict(identity_id=sid('pi', lab['lab_id'] + '|' + key), lab_id=lab['lab_id'], university_id=lab['university_id'],
                pi_name=review['pi_name'], openalex_author_id=author['id'], orcid='https://orcid.org/' + review['orcid'] if owned_orcid else '',
                openalex_author_aliases=json.dumps([author['id']]), author_alias_review_scope='reviewed_owner_chain_single_exact_profile_only',
                openalex_name_evidence=json.dumps({author['id']: names}, ensure_ascii=False), openalex_institution_id=review['openalex_institution_id'],
                identity_status='verified_official_owner_orcid' if owned_orcid else 'verified_official_owner_bibliography',
                identity_method='reviewed_explicit_lab_leader_to_named_owner_and_owned_ORCID_exact_profile' if owned_orcid else 'reviewed_explicit_lab_leader_to_named_owner_and_five_independent_full_name_publications',
                **lab_evidence, identity_evidence_url=review['identity_evidence_url'], identity_evidence_snapshot=owner['snapshot_path'],
                identity_registry_url='', identity_registry_snapshot='', identity_registry_sha256='', author_evidence_snapshot=source['snapshot_path'],
                observed_on=CUTOFF, notes=review['notes'])
