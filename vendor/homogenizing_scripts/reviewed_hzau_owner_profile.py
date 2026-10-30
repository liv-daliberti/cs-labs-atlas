# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_hzau_owner_profile.py (sha256 f1439f7a3a2822857c698520a4f31157c6126cf86091e2333287f180cc231416); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Replay the reviewed Chinese lab leader → named owner → own ORCID chain.

This format accepts only Wen Zhang's pinned official source chain. Exact author
ORCID/name/university checks and publication-time affiliation remain separate.
"""
import hashlib,importlib.util,json,tempfile
from functools import lru_cache
from pathlib import Path
from publications import ROOT,read_csv
from source_decoding import decode_preserved_text
PACKAGE='cs17_hzau_leader_identity_sources'
PIN='7c2b13fd81c5b9d328491bb9220283cdf1f92bfe5673470b99523bb3ed650752'
FORMAT='official_hzau_owned_orcid_v1'
LAB='lab_23194e7223a5f92d'
ORCID='0000-0001-5221-2628'
INSTITUTION='https://openalex.org/I204823248'
INSTITUTION_PATH='data/reviews/cs19_pi_identity_metadata/raw/src_e1ad48ea4bbaa8d8.body'
INSTITUTION_SHA='b17c9395f9e71a7179cabeb50c43da6c89044a1915723c54d177277b8cb8ba2e'
def require(value,message):
 if not value:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_text())
def verify_package():
 folder=ROOT/'data/reviews'/PACKAGE;manifest=folder/'freeze_manifest.json'
 require(sha(manifest.read_bytes())==PIN,'HZAU owner manifest changed')
 for name,item in read(manifest)['files'].items():
  path=(folder/name).resolve();require(path.is_relative_to(folder.resolve()),'Owner evidence path escaped package')
  raw=path.read_bytes();require(len(raw)==item['bytes'] and sha(raw)==item['sha256'],'HZAU owner evidence bytes changed: '+name)
 return folder
def helper(folder):
 spec=importlib.util.spec_from_file_location('reviewed_hzau_frozen_owner',folder/'prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
@lru_cache(maxsize=1)
def replay_package():
 folder=verify_package();module=helper(folder)
 with tempfile.TemporaryDirectory(prefix='hzau-owner-replay-',dir='/tmp') as tmp:
  dest=Path(tmp);module.build(folder=folder,out=dest)
  for name in module.OUTFILES:require((dest/name).read_bytes()==(folder/name).read_bytes(),'HZAU owner proof replay differs: '+name)
 return True
def validate_hzau_profile(review,text):
 folder=verify_package();replay_package();module=helper(folder);evidence=module.Evidence(folder)
 chain=next(r for r in read(folder/'leader_source_proofs.json') if r['caption_person_name']=='章文');role=chain['leadership_evidence']
 expected={'identity_evidence_format':FORMAT,'review_status':'accepted','owner_evidence_package':PACKAGE,'owner_evidence_manifest_sha256':PIN,'lab_id':LAB,'university_id':'huazhong-agricultural-university','pi_name':'章文','orcid':ORCID,'profile_name_tokens':['Wen','Zhang'],'openalex_institution_id':INSTITUTION,'identity_evidence_url':chain['english_introduction']['source_url'],'pi_lab_evidence_source_id':role['source_id'],'pi_lab_evidence_url':role['source_url'],'pi_lab_evidence_sha256':role['source_sha256'],'pi_lab_evidence_quote':role['evidence_quote'],'institution_evidence_snapshot':INSTITUTION_PATH,'institution_evidence_sha256':INSTITUTION_SHA}
 for key,value in expected.items():require(review.get(key)==value,'HZAU identity review differs: '+key)
 # Current records must still describe the exact reviewed Chinese person and unit.
 labs={r['lab_id']:r for r in read_csv(ROOT/'data/processed/labs.csv')};lab=labs[LAB]
 require(lab['university_id']==expected['university_id'] and lab['lab_name']==chain['lab_name'],'Current HZAU unit differs')
 current=[r for r in read_csv(ROOT/'data/processed/leadership_evidence.csv') if r['lab_id']==LAB and r['person_name']=='章文' and r['source_id']==role['source_id']]
 require(len(current)==1,'Current exact named HZAU leader is missing or ambiguous');leader=current[0]
 for key in ['lab_id','lab_name','university_id','person_name','role','source_id','source_url','source_sha256','evidence_quote']:
  require(leader[key]==role[key],'Current HZAU leader differs: '+key)
 sources={r['source_id']:r for r in read_csv(ROOT/'data/processed/sources.csv')}
 from reviewed_image_leadership import validate
 validate(leader,sources[leader['source_id']],sources,lab)
 module.validate_chain(chain,evidence)
 owned=next(r for r in read(folder/'owner_identifier_links.json') if r['kind']=='orcid')
 require(owned['identifier']==ORCID,'Official owner ORCID differs')
 for proof in owned['proofs']:module.validate_identifier(proof,evidence,chain)
 source=evidence.sources[chain['english_introduction']['source_id']]
 preserved=decode_preserved_text(evidence.raw(source['source_id']),source['content_type'],'.html')
 require(text==preserved,'Supplied owner profile differs from frozen source')
 raw=(ROOT/INSTITUTION_PATH).read_bytes();require(sha(raw)==INSTITUTION_SHA,'Institution metadata changed');institution=json.loads(raw)
 require(institution['id']==INSTITUTION and institution['display_name']=='Huazhong Agricultural University' and institution['homepage_url']=='https://www.hzau.edu.cn' and institution['country_code']=='CN','University mapping differs')
 return evidence.txt(chain['english_introduction'])
