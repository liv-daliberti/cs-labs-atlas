# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_wallraven_profile.py (sha256 bd3778dd10ddc3c0406b292a09e23e8ee0bc2802c168a49c840133b1f3e8612b); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Validate one reviewed Korea University owner profile against preserved evidence.

This is deliberately not a generic Google Sites ORCID decoder. Its only accepted
input is the source-reviewed Christian Wallraven PI page and institutional chain
bound by the manifest below. It returns an owner heading for the existing name
guard only after every independent condition passes.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib,json,re,sys
from pathlib import Path
from urllib.parse import parse_qsl,urljoin,urlsplit,unquote
from bs4 import BeautifulSoup
ROOT=P.WORLD_ATLAS
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import clean
from publications import author_name_evidence,institution_ids

MANIFEST_SHA256='10c9372ab5a658670b127bc16245bdebb9d8abfa36ca1c1f01fa2d4f1e90ad67'
PROFILE_SHA256='a95f0c9eb4cfc3835e33d8569c700bb42cc5ee868c226b681252c110a41e7f0d'
FORMAT='official_ku_wallraven_google_sites_v1'
OWNER='Christian Wallraven'
ORCID='0000-0002-2604-9115'
TARGET='https://orcid.org/'+ORCID
LAB='lab_74bd907e5a110140'

def require(condition,message):
    if not condition:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def manifest():
    raw=(ROOT/'data/reviews/cs13_asia_followup/evidence_manifest.json').read_bytes()
    require(digest(raw)==MANIFEST_SHA256,'Frozen Wallraven manifest changed')
    return json.loads(raw)

def strict_owner_redirect(href):
    """Accept only this exact canonical ORCID in a singly encoded Google wrapper."""
    require(isinstance(href,str) and href.strip()==href,'Invalid owner redirect type/whitespace')
    try:u=urlsplit(href);port=u.port
    except ValueError:raise ValueError('Malformed owner redirect')
    require(u.scheme=='https' and u.netloc=='www.google.com' and u.hostname=='www.google.com'
      and not u.username and not u.password and port is None and u.path=='/url'
      and not u.fragment,'Owner redirect host/path mismatch')
    require(re.search(r'%(?![0-9A-Fa-f]{2})',u.query) is None,'Malformed redirect percent encoding')
    try:pairs=parse_qsl(u.query,keep_blank_values=True,strict_parsing=True)
    except ValueError:raise ValueError('Malformed owner redirect query')
    require(len(pairs)==4 and len({k for k,v in pairs})==4,'Duplicate or additional owner redirect parameter')
    query=dict(pairs)
    require(set(query)=={'q','sa','sntz','usg'},'Unexpected owner redirect parameter')
    require(query['q']==TARGET,'Owner ORCID is not the exact canonical target')
    target=urlsplit(query['q'])
    require(target.scheme=='https' and target.netloc=='orcid.org' and target.path=='/'+ORCID
      and not target.query and not target.fragment,'Noncanonical owner ORCID target')
    require(query['sa']=='D' and query['sntz']=='1'
      and query['usg']=='AOvVaw1MOSDOkIKCdHzjbabduxph','Owner redirect tracking context changed')
    return TARGET

def _profile_facts(text,proof):
    """Structural checks are independently testable; public entry also pins bytes."""
    soup=BeautifulSoup(text,'html.parser')
    require(soup.title is not None and clean(soup.title.get_text())==proof['expected_title'],'Owner profile title mismatch')
    nodes={}
    for label,spec in proof['sections'].items():
        selected=soup.select(spec['selector'])
        require(len(selected)==1,'Owner section not unique: '+label)
        node=selected[0];nodes[label]=node
        require(clean(node.get_text(' ',strip=True))==spec['text'],'Owner section text changed: '+label)
        require(digest(str(node).encode())==spec['html_sha256'],'Owner section HTML changed: '+label)
    require(clean(nodes['role_heading'].get_text())=='Principal Investigator','Explicit PI heading missing')
    require(clean(nodes['contact'].get_text(' ',strip=True))=='Contact Christian Wallraven at wallraven@korea.ac.kr','Full owner contact name mismatch')
    biography=clean(nodes['biography'].get_text(' ',strip=True))
    require(biography.startswith('Christian Wallraven received a Ph.D.')
      and 'He then moved to Korea University in 2010' in biography
      and 'He is PI of the Cognitive Systems Lab' in biography,'Full owner name, university or PI role missing')
    require(clean(nodes['links_label'].get_text(' ',strip=True))=='Links to google scholar, ResearchGate, LinkedIn, and Orcid below:','Owner link-context label changed')
    anchor=nodes['orcid_widget']
    require(anchor.name=='a' and anchor.get('href')==proof['raw_redirect_href'],'Owner ORCID widget changed')
    all_orcid=[a for a in soup.select('a[href]') if 'orcid.org' in unquote(a['href']).casefold()]
    require(len(all_orcid)==1 and all_orcid[0] is anchor,'Ambiguous owner ORCID links')
    require(strict_owner_redirect(anchor['href'])==TARGET,'Owner redirect mismatch')
    return OWNER

def _read_bound_source(record,root):
    root=root.resolve();paths=[]
    for key in ['snapshot_path','metadata_path']:
        path=(root/record[key]).resolve()
        require(path.is_relative_to(root),'Evidence path escaped project')
        paths.append(path)
    raw=paths[0].read_bytes();metaraw=paths[1].read_bytes()
    require(digest(raw)==record['sha256'],'Institutional/author source bytes changed')
    require(digest(metaraw)==record['metadata_sha256'],'Institutional/author metadata changed')
    meta=json.loads(metaraw)
    require(meta['source_id']==record['source_id'] and meta['sha256']==record['sha256']
      and meta['snapshot_path']==record['snapshot_path'] and meta['requested_url']==record['source_url']
      and meta.get('final_url',meta['requested_url'])==record['final_url']
      and meta['http_status']==200,'Source provenance mismatch')
    return raw,meta

def validate_wallraven_profile(review,text,root=ROOT):
    """Fail closed on any review, profile, institutional-link or author mismatch."""
    data=manifest();proof=data['wallraven'];leader=proof['leadership_evidence']
    expected=dict(identity_evidence_format=FORMAT,review_status='accepted',lab_id=LAB,
      university_id='korea-university',pi_name='Christian wallraven',orcid=ORCID,
      profile_name_tokens=['Christian','Wallraven'],identity_evidence_url=proof['profile']['source_url'],
      identity_evidence_source_id=proof['profile']['source_id'],identity_evidence_sha256=PROFILE_SHA256,
      identity_evidence_snapshot=proof['profile']['snapshot_path'],openalex_author_id=proof['openalex_author_id'],
      openalex_author_aliases=[proof['openalex_author_id']],openalex_institution_id=proof['openalex_institution_id'],
      author_alias_review_scope='single_profile_only_alias_review_pending',author_evidence_snapshot=proof['author']['snapshot_path'],
      author_evidence_sha256=proof['author']['sha256'],pi_lab_evidence_source_id=leader['source_id'],
      pi_lab_evidence_url=leader['source_url'],pi_lab_evidence_sha256=leader['source_sha256'],pi_lab_evidence_quote=leader['evidence_quote'])
    for key,value in expected.items():require(review.get(key)==value,'Wallraven proposal field mismatch: '+key)
    require(isinstance(text,str) and digest(text.encode('utf-8'))==PROFILE_SHA256,'Frozen owner profile bytes changed')
    root=Path(root)
    for path,sha in data['pinned_inputs'].items():
        resolved=(root/path).resolve();require(resolved.is_relative_to(root.resolve()),'Input path escaped project')
        require(digest(resolved.read_bytes())==sha,'Frozen inventory/proposal input changed')
    bound={}
    for key in proof['source_keys']:
        raw,meta=_read_bound_source(data['sources'][key],root)
        bound[meta['source_id']]=(raw,meta)
    profile_raw,_=bound[proof['profile']['source_id']]
    require(profile_raw==text.encode('utf-8'),'Supplied profile differs from original capture')
    for edge in proof['institutional_link_chain']:
        left,lm=bound[edge['source_id']];right,rm=bound[edge['target_source_id']]
        require(lm['sha256']==edge['source_sha256'] and lm['snapshot_path']==edge['source_snapshot']
          and lm['requested_url']==edge['source_url'],'Institutional chain source mismatch')
        soup=BeautifulSoup(left,'html.parser')
        matches=[a for a in soup.select('a[href]') if str(a)==edge['anchor_html']
          and urljoin(lm.get('final_url',lm['requested_url']),a['href'])==edge['target_url']]
        require(matches,'Exact institutional owner-profile link missing')
        require(edge['target_url'].rstrip('/') in {rm['requested_url'].rstrip('/'),rm.get('final_url','').rstrip('/')},'Institutional chain target mismatch')
    raw,_=bound[leader['source_id']];txt=clean(BeautifulSoup(raw,'html.parser').get_text(' ',strip=True))
    context=proof['lab_context']['context']
    require(context in txt and leader['evidence_quote'] in context
      and leader['person_name'] in context and proof['lab_name'] in context,'Unit-local named PI role missing')
    author=json.loads(bound[proof['author']['source_id']][0])
    require(author.get('id')==proof['openalex_author_id'] and author.get('orcid')==TARGET,'Singleton author identity changed')
    require(author_name_evidence(author,['Christian','Wallraven']),'Singleton full name mismatch')
    require(proof['openalex_institution_id'] in institution_ids(author),'Singleton university mismatch')
    require(any(x['institution']['id']==proof['openalex_institution_id'] and x['institution']['display_name']=='Korea University' for x in author.get('affiliations',[])),'Singleton exact university label mismatch')
    return _profile_facts(text,proof)
