# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_owner_bibliography.py (sha256 4e8940f399512ea772204647f57178be5935361fd7f379231a065a44493d46f2); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Reviewed personal-owner bibliographies identify PIs without asserting a public ORCID.

Frozen, source-bound unit-role -> named owner -> own citations are replayed offline.
At least five distinct DOI/work/title components across two metadata publication years
must identify one full-name author, with two target-university papers and compatible
exact author history. Source dates remain separate; old papers may establish identity
but never extend the collection window. Personal bibliographies do not establish lab
membership or enter the broader reviewed-lab view automatically.
"""
import hashlib, importlib.util, json, shutil, tempfile
from functools import lru_cache
from pathlib import Path
from publications import ROOT, CUTOFF, author_name_evidence, institution_ids, sid

FORMAT = 'official_personal_bibliography_anchor_v1'
PINS = {
 'cs16_uk_bibliography_identity_review': 'e319d83825675d281bdc79d4f900a27cc5cac332fbb17dc00f87d29b607a61d1',
 'cs16_americas_bibliography_identity_review': '46fcc33da7f46ead575c163967fa3347256072195c7bf120b064b6b66b979717',
 'cs17_uk_owner_bibliography_extension': '97bc5fe148dbbe795563fed19eac0993eb92a5bac8e0d5756d6884416e68de40',
}
MIN_WORKS = 5
MIN_YEARS = 2
MIN_TARGET_WORKS = 2

def require(condition, message):
 if not condition: raise ValueError(message)

def read(path): return json.loads(path.read_text())
def digest(data): return hashlib.sha256(data).hexdigest()
def module(path):
 spec=importlib.util.spec_from_file_location('frozen_owner_replay_'+digest(str(path).encode())[:12],path)
 result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def verify_package(name):
 require(name in PINS,'Unreviewed owner bibliography package')
 folder=ROOT/'data/reviews'/name;manifest=folder/'freeze_manifest.json'
 require(digest(manifest.read_bytes())==PINS[name],'Owner package manifest changed')
 for f in read(manifest)['files']:
  path=folder/f['path'];require(path.resolve().is_relative_to(folder.resolve()),'Package path escapes source folder')
  raw=path.read_bytes();require(digest(raw)==f['sha256'] and len(raw)==f.get('size',f.get('bytes')),'Owner package bytes changed: '+f['path'])
 return folder

@lru_cache(maxsize=8)
def replay_package(name):
 """Reproduce frozen proposal outputs without writing into the source package."""
 folder=verify_package(name)
 with tempfile.TemporaryDirectory(prefix='science-owner-replay-',dir='/tmp') as temp:
  dest=Path(temp)
  if name=='cs17_uk_owner_bibliography_extension':
   parent=verify_package('cs16_uk_bibliography_identity_review')
   replay_package('cs16_uk_bibliography_identity_review')
   require((folder/'input_chain_reviews.json').read_bytes()==(parent/'chain_reviews.json').read_bytes(),'Extension owner chain differs from original proof')
   require((folder/'input_cs16_work_evidence.json').read_bytes()==(parent/'work_identity_evidence.json').read_bytes(),'Extension baseline differs from original replay')
   copy=dest/'inputs';shutil.copytree(folder,copy,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
   helper=module(copy/'build.py');helper.build();result=copy;outputs=helper.OUTS
  elif name.startswith('cs16_uk_'):
   copy=dest/'inputs';shutil.copytree(folder,copy,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
   helper=module(copy/'review.py');helper.build();result=copy
   outputs=helper.OUTPUTS
  else:
   helper=module(folder/'prepare.py');helper.build(dest);result=dest
   outputs=['held_identity_candidates.json','doi_work_reviews.json','owner_coverage.json','returned_doi_holds.json','institution_mapping_reviews.json','candidate_summary.csv','summary.json']
  for output in outputs:
   require((result/output).read_bytes()==(folder/output).read_bytes(),'Owner proof offline replay differs: '+output)
 return read(folder/('candidate_proposals.json' if name=='cs17_uk_owner_bibliography_extension' else 'held_identity_candidates.json'))

def candidate_proof(review):
 require(review.get('identity_evidence_format')==FORMAT and review.get('review_status')=='accepted','Not an accepted personal-owner review')
 name=review['owner_evidence_package'];folder=verify_package(name)
 require(review['owner_evidence_manifest_sha256']==PINS[name],'Review refers to another owner package')
 candidates=replay_package(name)
 key='pi_name' if name.startswith('cs16_uk_') else 'person_name'
 selected=[c for c in candidates if c['lab_id']==review['lab_id'] and c[key]==review['pi_name']]
 require(len(selected)==1,'Personal owner candidate is not unique')
 c=selected[0];require(c['university_id']==review['university_id'],'Owner university mismatch')
 if name=='cs17_uk_owner_bibliography_extension':
  require(not c['split_author_ids'] and c['observed_author_ids']==[c['openalex_author_id']],'Split personal-owner author profiles')
  aid=c['openalex_author_id'];count=c['distinct_confirmations'];years=c['metadata_years'];target=c['own_target_university_count'];source_years=c['source_years'];doi_evidence=c['confirmations']
  require(count==len(doi_evidence)==len({x['doi'] for x in doi_evidence})==len({x['work_id'] for x in doi_evidence})==len({x['normalized_title'] for x in doi_evidence}),'Dependent publication confirmations')
  require(all(x['owner_author_id']==aid for x in doi_evidence),'Mixed owner confirmation author IDs')
  require(target==sum(x['own_target_university_supported'] for x in doi_evidence),'University confirmation count differs')
  chain=next(x['original_chain'] for x in read(folder/'input_chain_reviews.json') if x['lab_id']==review['lab_id'] and x['pi_name']==review['pi_name'])
  role=chain['explicit_leadership'];owner=chain['owner_source'];iid=c['target_institution_id']
 elif key=='pi_name':
  require(not c['split_author_ids'] and len(c['author_id_groups'])==1,'Split personal-owner author profiles')
  group=c['author_id_groups'][0];aid=group['author_id'];count=group['distinct_owner_research_papers'];years=group['publication_years'];target=group['target_university_papers']
  chain=next(x['original_chain'] for x in read(folder/'chain_reviews.json') if x['lab_id']==review['lab_id'] and x['pi_name']==review['pi_name'])
  role=chain['explicit_leadership'];owner=chain['owner_source'];doi_evidence=group['doi_evidence'];source_years=group['citation_years']
  mapping=next(x for x in read(folder/'university_mapping_evidence.json') if x['university_id']==c['university_id'])
  iid=mapping['expected_openalex_institution_id']
 else:
  require(not c['split_author_id_hold'] and c['observed_owner_author_ids']==[c['candidate_author_id']],'Split personal-owner author profiles')
  aid=c['candidate_author_id'];count=c['distinct_own_papers'];years=c['metadata_publication_years'];target=c['in_window_exact_target_university_papers'];source_years=c['source_supported_publication_years'];doi_evidence=c['supporting_dois']
  require(count==c['distinct_dois']==c['distinct_work_ids']==c['distinct_normalized_titles'],'Dependent publication confirmations')
  chain=next(x for x in read(folder/'inputs/owner_chain_specs.json') if x['lab_id']==review['lab_id'] and x['person_name']==review['pi_name']);role=chain['leadership']
  helper=module(folder/'prepare.py');owner,_=helper.source(chain['named_owner_proofs'][-1]['source_url'])
  iid=next(x['openalex_institution_id'] for x in read(folder/'institution_mapping_reviews.json') if x['university_id']==c['university_id'])
 require(count>=MIN_WORKS and len(set(years))>=MIN_YEARS,'Insufficient independent owner publications')
 require(target>=MIN_TARGET_WORKS,'Insufficient owner publication-time university corroboration')
 require(aid==review['openalex_author_id'] and iid==review['openalex_institution_id'],'Review author or institution mismatch')
 require(review['pi_lab_evidence_source_id']==role['source_id'],'Reviewed role source mismatch')
 require(review['identity_evidence_url']==owner['requested_url'] and review['identity_profile_sha256']==owner['sha256'],'Named owner page mismatch')
 require(not review.get('orcid'),'Personal-owner method must not promote metadata ORCIDs to public owner claims')
 require(review['profile_name_tokens']==review['pi_name'].split(),'Owner full-name tokens altered')
 return dict(role=role,owner=owner,author_id=aid,independent_works=count,metadata_years=years,source_years=source_years,target_university_works=target,doi_evidence=doi_evidence)

def verify_author(review, author):
 require(author.get('id')==review['openalex_author_id'],'Exact author lookup returned another profile')
 names=author_name_evidence(author,review['profile_name_tokens'])
 require(names,'Author profile full name incompatible with reviewed owner')
 require(review['openalex_institution_id'] in institution_ids(author),'Target university absent from exact author history')
 return names

def identity_row(review, lab, lab_evidence, client):
 proof=candidate_proof(review)
 require(lab['lab_id']==review['lab_id'] and lab['university_id']==review['university_id'],'Current lab differs from reviewed ownership')
 role=proof['role']
 require(lab_evidence['pi_lab_evidence_source_id']==role['source_id'] and lab_evidence['pi_lab_evidence_sha256']==role['source_sha256'],'Current leadership source differs from owner chain')
 # Also require the exact reviewed person/role row in the current integrated ledger.
 from publications import read_csv
 require(role in read_csv(ROOT/'data/processed/leadership_evidence.csv'),'Explicit named owner leadership is not integrated')
 _,owner=client.fetch(review['identity_evidence_url']);require(owner['sha256']==review['identity_profile_sha256'],'Cached named-owner page differs')
 author,source=client.api('authors/'+review['openalex_author_id'].rsplit('/',1)[-1]);names=verify_author(review,author)
 require(source['sha256']==review['author_profile_sha256'],'Reviewed exact author profile changed')
 return dict(identity_id=sid('pi',lab['lab_id']+'|'+author['id']),lab_id=lab['lab_id'],university_id=lab['university_id'],pi_name=review['pi_name'],openalex_author_id=author['id'],orcid='',openalex_author_aliases=json.dumps([author['id']]),author_alias_review_scope='reviewed_personal_bibliography_single_profile_only',openalex_name_evidence=json.dumps({author['id']:names},ensure_ascii=False),openalex_institution_id=review['openalex_institution_id'],identity_status='verified_official_personal_bibliography_anchor',identity_method='reviewed_explicit_lab_leader_named_owner_chain_and_five_independent_personal_publications',**lab_evidence,identity_evidence_url=review['identity_evidence_url'],identity_evidence_snapshot=owner['snapshot_path'],identity_registry_url='',identity_registry_snapshot='',identity_registry_sha256='',author_evidence_snapshot=source['snapshot_path'],observed_on=CUTOFF,notes=review['notes'])
