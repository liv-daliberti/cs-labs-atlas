# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_lab_citations.py (sha256 a34f827bf955a2c8abaaea9682ace8f19e8ed12847df31e43a8c5d590104a716); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Replay explicit group leadership and exact, independently resolved lab citations.

Search results are discovery only. Every accepted citation is resolved again by
exact DOI, and checked against the preserved group page. Five independent papers
across two years and two PI-specific university affiliations anchor an identity.
Metadata ORCIDs and unreviewed author aliases are never promoted to owner claims.
"""
import hashlib,json,re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

FORMAT='official_lab_citation_anchor_v1'

def require(value,message):
    if not value:raise ValueError(message)

def key(value):return ''.join(c for c in (value or '').casefold() if c.isalnum())
def digest(raw):return hashlib.sha256(raw).hexdigest()

def source(root,meta):
    path=(root/meta['snapshot_path']).resolve()
    require(path.is_relative_to(root.resolve()),'Evidence path escapes project')
    raw=path.read_bytes()
    require(meta['http_status']==200 and digest(raw)==meta['sha256'],'Evidence bytes/status changed')
    return raw

def package(review,root):
    path=(root/review['citation_evidence_package']).resolve()
    require(path.is_relative_to(root.resolve()),'Package path escapes project')
    raw=path.read_bytes();require(digest(raw)==review['citation_evidence_sha256'],'Citation package changed')
    data=json.loads(raw);require(data['schema']=='reviewed_lab_citations_v1','Unknown citation package')
    require(data['lab_id']==review['lab_id'] and data['university_id']==review['university_id'],'Lab scope mismatch')
    return data

def work_check(spec,work):
    require(work.get('id')==spec['work_id'],'Work identifier mismatch')
    require((work.get('doi') or '').lower()=='https://doi.org/'+spec['doi'],'DOI lookup mismatch')
    require(key(work.get('title'))==key(re.sub(r'\s*\[[A-Za-z]+\]\s*$','',spec['title'])),'Citation title mismatch')
    require(work.get('type') in {'article','review','conference-paper','proceedings-article'},'Unsupported citation type')
    require(not work.get('is_retracted') and not work.get('is_paratext'),'Retracted/paratext citation')
    authors=work.get('authorships',[])
    require(0<len(authors)<100,'Empty or possibly truncated byline')
    require(not any(v for k,v in work.items() if 'truncat' in k.lower() and ('author' in k.lower() or k in {'truncated','is_truncated'})),'Explicitly truncated byline')
    require(not any(isinstance(work.get(k),int) and work[k]>len(authors) for k in ['authors_count','author_count','authorships_count','total_authors']),'Byline count mismatch')
    try: date.fromisoformat(work.get('publication_date',''))
    except (TypeError,ValueError):raise ValueError('Invalid publication date')
    require(work.get('publication_date','')[:4]==str(work.get('publication_year')),'Publication year/date mismatch')
    return work

def verify(review,root):
    from author_name_matching import match_name,author_name_evidence
    from publications import institution_ids
    require(review.get('identity_evidence_format')==FORMAT and review.get('review_status')=='accepted','Unreviewed identity')
    data=package(review,root)
    person=next((p for p in data['people'] if p['name']==review['pi_name']),None)
    require(person is not None and person['author_id']==review['openalex_author_id'],'Person/author scope mismatch')
    # The university profile explicitly binds each native-name leader to this lab site.
    profile=BeautifulSoup(source(root,person['official_profile']),'html.parser').select_one('.article')
    require(profile is not None,'Official profile selector missing')
    ptext=profile.get_text(' ',strip=True)
    require(person['native_name'] in ptext and data['homepage'] in ptext,'Official person-to-group binding missing')
    host=(urlsplit(person['official_profile']['requested_url']).hostname or '')
    require(host.endswith('.whut.edu.cn'),'Unexpected institutional source host')
    home=BeautifulSoup(source(root,data['homepage_source']),'html.parser')
    require(data['unit_native_name'] in home.get_text(' ',strip=True),'Group name missing from home page')
    require(any((urlsplit(a['href']).hostname or '')=='www.whut.edu.cn' for a in home.select('a[href]')),'Group university binding missing')
    people=BeautifulSoup(source(root,data['leadership_source']),'html.parser')
    groups=[g for g in people.select('.user-group-row') if g.select_one('h2') and g.select_one('h2').get_text(' ',strip=True)=='课题组负责人']
    require(len(groups)==1,'Leader section ambiguous')
    names=[n.get_text(' ',strip=True) for n in groups[0].select('.portrait-title h2')]
    require(names==data['leader_names_native'] and person['native_name'] in names,'Explicit leader list differs')
    institution=json.loads(source(root,data['institution_source']))
    require(institution['id']==review['openalex_institution_id']==data['institution_id'],'University ID mismatch')
    require((urlsplit(institution['homepage_url']).hostname or '').removeprefix('www.')=='whut.edu.cn','University domain mismatch')
    soup=BeautifulSoup(source(root,data['bibliography_source']),'html.parser')
    cards=soup.select('.publication-card');works=[]
    for spec in data['citations']:
        require(spec['card_index']<len(cards),'Citation index missing')
        card=cards[spec['card_index']]
        for selector,field in [('.publication-title','title'),('.publication-authors','authors'),('.publication-venue','venue')]:
            node=card.select_one(selector);require(node is not None and node.get_text(' ',strip=True)==spec[field],'Citation source text changed')
        require(int(card['data-year'])==spec['source_year'],'Citation source year changed')
        require('Patent' not in card.get_text(' ',strip=True),'Patent listed as academic paper')
        require(spec['metadata_source']['requested_url'].startswith('https://api.openalex.org/works/doi:'),'Metadata is not exact DOI lookup')
        work=work_check(spec,json.loads(source(root,spec['metadata_source'])))
        works.append((spec,work))
    anchors=[(s,w) for s,w in works if s['doi'] in person['anchor_dois']]
    require(len(anchors)==len(person['anchor_dois'])>=5,'Insufficient exact anchor papers')
    require(len({s['doi'] for s,w in anchors})==len({w['id'] for s,w in anchors})==len({key(w['title']) for s,w in anchors})==len(anchors),'Dependent/duplicate anchors')
    require(len({w['publication_year'] for s,w in anchors})>=2,'Insufficient anchor years')
    target=0
    for spec,w in anchors:
        require(spec['source_year']==w['publication_year'],'Anchor source year differs; review print/online dating separately')
        require(key(person['name']) in key(spec['authors']),'Full owner name absent from group citation')
        matches=[a for a in w['authorships'] if match_name(a.get('raw_author_name') or '',person['name'].split())]
        require(len(matches)==1 and matches[0]['author']['id']==person['author_id'],'Anchor raw full-name/author-ID ambiguity')
        require(match_name(matches[0]['author'].get('display_name',''),person['name'].split()),'Anchor display name mismatch')
        target+=any(i['id']==data['institution_id'] for i in matches[0].get('institutions',[]))
    require(target>=2,'Too few target-university affiliations on the PI authorship')
    # Assess every resolved citation, not only the chosen anchors, for a competing ID.
    counts={};total=len(works)
    for spec,w in works:
        ids={a['author']['id'] for a in w['authorships'] if a['author'].get('id') and match_name(a.get('raw_author_name') or '',person['name'].split())}
        for aid in ids:counts[aid]=counts.get(aid,0)+1
    require(counts.get(person['author_id'],0)/total>=.5,'Primary identity lacks majority bibliography support')
    require(all(n/total<.2 for aid,n in counts.items() if aid!=person['author_id']),'Competing author profile requires split/homonym review')
    author=json.loads(source(root,person['author_source']))
    require(author['id']==person['author_id'] and author_name_evidence(author,person['name'].split()),'Author record mismatch')
    require(data['institution_id'] in institution_ids(author),'University missing from author history')
    require(not review.get('orcid'),'Metadata ORCID cannot become an owner assertion')
    return data,person,{'independent_anchors':len(anchors),'anchor_years':sorted({w['publication_year'] for s,w in anchors}),
        'target_university_anchor_works':target,'all_citation_author_counts':counts,'resolved_citations':total}

def identity_row(review,lab,lab_evidence,client):
    from publications import ROOT,CUTOFF,sid
    from author_name_matching import author_name_evidence
    data,person,stats=verify(review,ROOT)
    require(lab['lab_id']==data['lab_id'] and lab['university_id']==data['university_id'],'Current inventory differs')
    require(lab_evidence['pi_lab_evidence_sha256']==data['leadership_source']['sha256'],'Leadership source differs')
    author=json.loads(source(ROOT,person['author_source']))
    return dict(identity_id=sid('pi',lab['lab_id']+'|'+author['id']),lab_id=lab['lab_id'],university_id=lab['university_id'],
        pi_name=person['name'],openalex_author_id=author['id'],orcid='',openalex_author_aliases=json.dumps([author['id']]),
        author_alias_review_scope='single_profile_only_alias_review_pending',
        openalex_name_evidence=json.dumps({author['id']:author_name_evidence(author,person['name'].split())},ensure_ascii=False),
        openalex_institution_id=data['institution_id'],identity_status='verified_official_lab_citation_anchor',
        identity_method='official_native_name_leader_and_institutional_group_link_plus_five_independent_exact_citations',
        **lab_evidence,identity_evidence_url=data['bibliography_source']['requested_url'],
        identity_evidence_snapshot=data['bibliography_source']['snapshot_path'],identity_registry_url='',identity_registry_snapshot='',identity_registry_sha256='',
        author_evidence_snapshot=person['author_source']['snapshot_path'],observed_on=CUTOFF,
        notes=review['notes'])

def extract_links(spec,text,meta,root):
    """Replay the complete source proof when normal bibliography exports rebuild."""
    require(spec.get('source_format')=='reviewed_lab_citations_v1','Wrong bibliography format')
    reviews=spec.get('citation_identity_reviews') or []
    require(reviews,'Bibliography lacks reviewed identity chain')
    data=None
    for review in reviews:
        current,person,proof=verify(review,root)
        require(current['lab_id']==spec['lab_id'],'Bibliography lab differs')
        require(data is None or current==data,'Mixed bibliography packages')
        data=current
    require(meta['sha256']==data['bibliography_source']['sha256']==spec['source_sha256'],'Bibliography source differs')
    require(meta['requested_url']==data['bibliography_source']['requested_url']==spec['source_url'],'Bibliography URL differs')
    require(digest(text.encode('utf-8'))==meta['sha256'],'Bibliography decoded bytes differ')
    return {c['doi']:(c['title'],'https://doi.org/'+c['doi'],'reviewed_group_citation_resolved_by_exact_title_and_DOI_metadata') for c in data['citations']}
