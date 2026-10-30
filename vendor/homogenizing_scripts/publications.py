#!/usr/bin/env python3
# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/publications.py (sha256 807fcdf5b8d7ac1b69619ed1fe818dc890fbabac2296dc33af5d0e19dd956308); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Evidence-backed PI identity, OpenAlex metadata collection and lab-paper views.

Network commands are resumable; build is entirely offline. Full texts are not fetched.
An accepted identity is never inferred from a surname alone. Current affiliations
never substitute for a PI's affiliation on the individual publication.
"""
from __future__ import annotations
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402

import argparse
import csv
import hashlib
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import requests
from bs4 import BeautifulSoup

ROOT = P.WORLD_ATLAS  # vendored: the data root (was Path(__file__).resolve().parents[1])
OUT = ROOT / 'data/publications'
START = '2016-01-01'
CUTOFF = '2026-10-12'
BASE = 'https://api.openalex.org/'
# Current OpenAlex paper categories plus the legacy proceedings label.
PAPER_TYPES = {'article', 'review', 'preprint', 'proceedings-article',
               'conference-paper', 'data-paper', 'software-paper'}
PI_FIELDS = ['identity_id', 'lab_id', 'university_id', 'pi_name', 'openalex_author_id',
             'orcid', 'openalex_author_aliases', 'author_alias_review_scope', 'openalex_name_evidence', 'openalex_institution_id', 'identity_status', 'identity_method',
             'pi_lab_evidence_url', 'pi_lab_evidence_snapshot', 'pi_lab_evidence_source_id', 'pi_lab_evidence_sha256', 'identity_evidence_url',
             'identity_evidence_snapshot', 'identity_registry_url', 'identity_registry_snapshot', 'identity_registry_sha256', 'author_evidence_snapshot', 'observed_on', 'notes']
WORK_FIELDS = ['work_id', 'openalex_id', 'doi', 'title', 'publication_date', 'publication_year',
               'work_type', 'journal', 'is_oa', 'cited_by_count', 'author_count',
               'authorships_returned', 'authorships_truncated', 'countries_distinct_count',
               'primary_topic', 'primary_field', 'primary_domain', 'source_url',
               'source_snapshot', 'metadata_updated_date', 'language', 'is_retracted', 'is_paratext', 'referenced_works_count', 'fwci']
AUTHOR_FIELDS = ['work_id', 'author_order', 'author_id', 'author_name', 'raw_author_name',
                 'orcid', 'raw_orcid', 'author_position', 'is_corresponding',
                 'institution_ids', 'institution_names', 'institution_lineage_ids',
                 'raw_affiliation_strings', 'countries']
LINK_FIELDS = ['lab_id', 'university_id', 'pi_identity_id', 'work_id', 'publication_year',
               'pi_author_id', 'pi_author_position', 'pi_author_order',
               'pi_publication_university_match', 'strict_last_author', 'broader_reviewed', 'strict_plus_reviewed',
               'link_status', 'link_reason', 'lab_temporal_membership_status', 'review_source_url']


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def load_json(path, default):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default


def sid(prefix, text):
    return prefix + '_' + hashlib.sha256(text.encode()).hexdigest()[:16]


def normalize_doi(value):
    value = (value or '').strip().lower()
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value)
    return value if value.startswith('10.') and '/' in value else ''



def bibliography_doi(href):
    """Extract a linked DOI; preprint URL versions are not DOI suffixes."""
    match = re.search(r'(10\.\d{4,9}/[^\s<>"?#]+)', href)
    if not match:
        return ''
    value = match.group(1)
    host = (urlsplit(href).hostname or '').lower()
    if host in {'biorxiv.org', 'www.biorxiv.org', 'medrxiv.org', 'www.medrxiv.org'}:
        value = re.sub(r'(?:\.full(?:\.pdf)?|\.abstract)$', '', value)
        value = re.sub(r'v\d+$', '', value)
    return normalize_doi(value)


def normalize_name(value):
    value = ''.join(' ' if unicodedata.category(c).startswith('P') else c for c in value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


class Client:
    """Cache public metadata with credential-free provenance and bounded retries."""
    def __init__(self, out=OUT, offline=False):
        self.out, self.offline = Path(out), offline
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
        self.last_call = 0.0
        self.request_gate = None

    def fetch(self, url, params=None):
        params = dict(params or {})
        public_url = url + (('?' if '?' not in url else '&') + urlencode(sorted(params.items())) if params else '')
        source_id = sid('src', public_url)
        meta_path = self.out / 'raw' / (source_id + '.meta.json')
        content_path = self.out / 'raw' / (source_id + '.body')
        if meta_path.exists() and content_path.exists():
            from source_decoding import decode_preserved_text
            meta = json.loads(meta_path.read_text())
            return decode_preserved_text(content_path.read_bytes(), meta.get('content_type', '')), meta
        if self.offline:
            raise FileNotFoundError('Missing cached source: ' + public_url)
        request_headers = {}
        if url.startswith(BASE) and os.environ.get('OPENALEX_API_KEY'):
            request_headers['Authorization'] = 'Bearer ' + os.environ['OPENALEX_API_KEY']
        for attempt in range(4):
            time.sleep(max(0, 0.15 - (time.monotonic() - self.last_call)))
            if self.request_gate is not None: self.request_gate()
            try:
                response = self.session.get(url, params=params or None, headers=request_headers, timeout=45)
                self.last_call = time.monotonic()
                if response.status_code >= 400:
                    body = response.text
                    if os.environ.get('OPENALEX_API_KEY'):
                        body = body.replace(os.environ['OPENALEX_API_KEY'], '[redacted]')
                    atomic_json(self.out / 'raw' / (source_id + '.error.json'), {
                        'source_id': source_id, 'requested_url': public_url, 'http_status': response.status_code,
                        'observed_on': CUTOFF, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                        'response_body': body[:10000]})
                    if response.status_code == 429 and 'Insufficient budget' in body:
                        raise RuntimeError('OpenAlex shared-IP daily budget exhausted (HTTP 429); use OPENALEX_API_KEY or resume after reset. Query: ' + public_url)
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        raise RuntimeError('HTTP ' + str(response.status_code) + ': ' + public_url)
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(min(20, float(response.headers.get('Retry-After', 2 ** attempt))))
                    continue
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 3:
                    # Do not print exception URLs: they can contain an optional API key.
                    raise RuntimeError('Request failed after retries: ' + public_url) from None
                time.sleep(2 ** attempt)
        from source_decoding import decode_preserved_text
        raw = response.content
        meta = {'source_id': source_id, 'requested_url': public_url,
                'observed_on': CUTOFF, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                'http_status': response.status_code,
                'sha256': hashlib.sha256(raw).hexdigest(),
                'content_type': response.headers.get('Content-Type', ''),
                'final_url': response.url,
                'snapshot_path': str(content_path.relative_to(ROOT)) if content_path.is_relative_to(ROOT) else str(content_path)}
        content_path.parent.mkdir(parents=True, exist_ok=True)
        content_path.write_bytes(raw)
        atomic_json(meta_path, meta)
        return decode_preserved_text(raw, meta['content_type']), meta

    def api(self, endpoint, params=None):
        content, meta = self.fetch(BASE + endpoint, params)
        return json.loads(content), meta


def institution_ids(author):
    result = set()
    for row in (author.get('affiliations') or []):
        result.add(row.get('institution', {}).get('id', ''))
    for row in (author.get('last_known_institutions') or []):
        result.add(row.get('id', ''))
    return result


def discover(limit=50, only_university=None):
    """Create candidates, never silently promote ambiguous names to verified."""
    client = Client()
    labs = [r for r in read_csv(ROOT / 'data/processed/labs.csv') if r['principal_investigator']]
    if only_university:
        labs = [r for r in labs if r['university_id'] == only_university]
    existing = load_json(OUT / 'identity_candidates.json', [])
    done = {r['lab_id'] for r in existing} | {r['lab_id'] for r in read_csv(OUT / 'pi_identities.csv')}
    for lab in [r for r in labs if r['lab_id'] not in done][:limit]:
        # Multiple PI strings need separate explicit identities; do not turn them into one name.
        if any(x in lab['principal_investigator'] for x in (' & ', ';', '\n')):
            existing.append({'lab_id': lab['lab_id'], 'status': 'multiple_pis_need_review', 'pi_name': lab['principal_investigator']})
            continue
        try:
            result, meta = client.api('authors', {'search': lab['principal_investigator'], 'per_page': 10})
            existing.append({'lab_id': lab['lab_id'], 'university_id': lab['university_id'],
                             'pi_name': lab['principal_investigator'], 'status': 'candidate_needs_review',
                             'source_snapshot': meta['snapshot_path'], 'candidates': result.get('results', [])})
        except RuntimeError as error:
            print(str(error))
            break
        atomic_json(OUT / 'identity_candidates.json', existing)
    atomic_json(OUT / 'identity_candidates.json', existing)
    print(json.dumps({'identity_candidate_labs': len(existing)}))


def review_bibliographies():
    """Record exact identifiers linked inside reviewed official lab bibliographies.

    This establishes a listing, not accepted authorship or historical affiliation.
    arXiv identifiers use its documented DOI mapping, never a journal alias.
    """
    from arxiv_identifiers import arxiv_doi
    client = Client()
    rows = []
    for source in load_json(OUT / 'bibliography_sources.json', []):
        if source.get('review_status') != 'accepted_official_lab_bibliography':
            continue
        text, meta = client.fetch(source['source_url'])
        if source.get('source_sha256') and source['source_sha256'] != meta['sha256']:
            raise ValueError('Reviewed bibliography source hash changed')
        if source.get('source_format') == 'reviewed_lab_citations_v1':
            from reviewed_lab_citations import extract_links
            found = extract_links(source, text, meta, ROOT)
        elif source.get('source_format') == 'rail_publications_json_v1':
            from reviewed_rail_bibliography import extract_links
            found = extract_links(source, text, meta, ROOT)
        elif source.get('source_format'):
            raise ValueError('Unsupported reviewed bibliography format')
        else:
            soup = BeautifulSoup(text, 'html.parser')
            content = soup.select_one(source.get('selector', 'body'))
            if content is None:
                raise ValueError('Bibliography selector no longer matches')
            found = {}
            for anchor in content.find_all('a', href=True):
                doi = bibliography_doi(anchor['href'])
                method = 'DOI_link_in_reviewed_official_lab_bibliography'
                if not doi:
                    doi = arxiv_doi(anchor['href'])
                    method = 'canonical_arXiv_DOI_from_link_in_reviewed_official_lab_bibliography'
                if doi:
                    # Prefer an explicit DOI link when both forms occur on a page.
                    if doi not in found or method.startswith('DOI_link'):
                        found[doi] = (anchor.get_text(' ', strip=True), anchor['href'], method)
        for doi, (title, href, method) in sorted(found.items()):
            rows.append({'lab_id': source['lab_id'], 'doi': doi, 'source_url': source['source_url'],
                         'source_snapshot': meta['snapshot_path'], 'source_sha256': meta['sha256'],
                         'review_status': 'accepted', 'review_method': method,
                         'reviewed_on': CUTOFF, 'anchor_text': title[:300], 'anchor_href': href})
    atomic_json(OUT / 'lab_publication_reviews.json', rows)
    print(json.dumps({'reviewed_lab_bibliography_DOIs': len(rows)}))



def lab_identity_evidence(review, lab, sources, leadership):
    """Retain the reviewed lab-person source, not an unrelated directory page."""
    from author_name_matching import name_tokens
    owner_tokens = name_tokens(review['pi_name'])
    if not owner_tokens:
        raise ValueError('Empty lab-leader name evidence')
    requested = review.get('pi_lab_evidence_source_id')
    matches = [r for r in leadership
               if r['lab_id'] == lab['lab_id']
               and name_tokens(r['person_name']) == owner_tokens
               and (not requested or r['source_id'] == requested)]
    if requested and not matches:
        raise ValueError('Reviewed lab-leader evidence missing for ' + review['pi_name'])
    row = matches[0] if matches else None
    source_id = row['source_id'] if row else lab['directory_source_id']
    source = sources[source_id]
    if row:
        if row['university_id'] != lab['university_id'] or row['source_sha256'] != source['sha256']:
            raise ValueError('Lab-leader source identity/hash mismatch')
        if row['source_url'] not in {source['requested_url'], source.get('final_url')}:
            raise ValueError('Lab-leader source URL mismatch')
        path = ROOT / source['snapshot_path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Lab-leader snapshot hash mismatch')
    return dict(pi_lab_evidence_url=row['source_url'] if row else lab['directory_source_url'],
                pi_lab_evidence_snapshot=source['snapshot_path'],
                pi_lab_evidence_source_id=source_id, pi_lab_evidence_sha256=source['sha256'])

def profile_orcid_links(anchors):
    """Read identifiers from owner-scoped ORCID paths, ignoring locale/query UI state."""
    identifiers = set()
    for anchor in anchors:
        href = anchor.get('href', '')
        parsed = urlsplit(href)
        if (parsed.hostname or '').lower() not in {'orcid.org', 'www.orcid.org'}:
            continue
        match = re.fullmatch(r'/([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])/?', parsed.path)
        if (parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password
                or parsed.port or any(char.isspace() for char in href) or not match):
            raise ValueError('Malformed owner ORCID URL')
        identifiers.add(match.group(1))
    return identifiers


def verify_profile_evidence(review, text):
    from author_name_matching import match_name
    soup = BeautifulSoup(text, 'html.parser')
    heading = soup.title.get_text(' ', strip=True) if soup.title else ''
    fmt = review.get('identity_evidence_format')
    if fmt == 'official_profile_dblp_orcid':
        from dblp_identity_bridge import validate_bridge
        heading = validate_bridge(review, text, ROOT, normalize_name)
    elif fmt == 'official_hzau_owned_orcid_v1':
        from reviewed_hzau_owner_profile import validate_hzau_profile
        heading = validate_hzau_profile(review, text)
    elif fmt == 'official_ku_wallraven_google_sites_v1':
        from reviewed_wallraven_profile import validate_wallraven_profile
        heading = validate_wallraven_profile(review, text, ROOT)
    elif fmt == 'eth_person_json':
        person = json.loads(text)['personData']
        heading = person.get('firstname', '') + ' ' + person.get('lastname', '')
        if person.get('orc-id') != review['orcid']:
            raise ValueError('Institutional JSON ORCID mismatch')
    elif fmt == 'html_title_orcid_widget':
        anchors = soup.select(review['identity_orcid_selector'])
        orcids = profile_orcid_links(anchors)
        if orcids != {review['orcid']}:
            raise ValueError('Institutional profile ORCID widget mismatch')
    elif fmt == 'html_profile_card':
        cards = soup.select(review['identity_profile_selector'])
        if len(cards) != 1:
            raise ValueError('Institutional person card is not unique')
        card = cards[0]
        names, roles = card.select(review['identity_name_selector']), card.select(review['identity_role_selector'])
        if len(names) != 1 or len(roles) != 1 or roles[0].get_text(' ', strip=True) != review['identity_expected_role']:
            raise ValueError('Institutional person name/leadership role mismatch')
        heading = names[0].get_text(' ', strip=True)
        orcids = profile_orcid_links(card.select(review['identity_orcid_selector']))
        if orcids != {review['orcid']}:
            raise ValueError('Institutional person card ORCID mismatch')
    if (fmt != 'official_profile_dblp_orcid' and review['orcid'] not in text) or not match_name(heading, review['profile_name_tokens']):
        raise ValueError('Institutional ORCID evidence changed for ' + review['pi_name'])


def author_name_evidence(candidate, tokens):
    from author_name_matching import author_name_evidence as reviewed_name_evidence
    return reviewed_name_evidence(candidate, tokens)

def author_candidates(client, orcid, singleton_fallback=False):
    params={'filter':'orcid:https://orcid.org/'+orcid,'per_page':100}
    if singleton_fallback:
        try:
            result,source=Client(out=client.out,offline=True).api('authors',params)
            return result,source,'all_exact_ORCID_query_results'
        except FileNotFoundError:
            result,source=client.api('authors/orcid:'+orcid)
            return {'results':[result],'meta':{'count':1}},source,'single_profile_only_alias_review_pending'
    result,source=client.api('authors',params)
    return result,source,'all_exact_ORCID_query_results'


def verify_seeds(singleton_fallback=False):
    """Explicit reviews link institutional PI profiles to ORCIDs, then OpenAlex."""
    client = Client()
    labs = {r['lab_id']: r for r in read_csv(ROOT / 'data/processed/labs.csv')}
    inventory_sources = {r['source_id']: r for r in read_csv(ROOT / 'data/processed/sources.csv')}
    reviews = load_json(OUT / 'identity_reviews.json', [])
    leadership = read_csv(ROOT / 'data/processed/leadership_evidence.csv')
    rows = []
    unresolved = []
    for review in reviews:
        lab = labs[review['lab_id']]
        lab_evidence = lab_identity_evidence(review, lab, inventory_sources, leadership)
        if review.get('identity_evidence_format') in {'epfl_infoscience_person_orcid_v1', 'epfl_infoscience_unit_anchor_v1'}:
            # EPFL unit head -> Infoscience Person (EPFL's institutional repository).
            from epfl_infoscience_review import identity_row
            rows.append(identity_row(review, lab, lab_evidence, client))
            continue
        if review.get('identity_evidence_format') == 'reviewed_official_owner_identity_v1':
            from reviewed_arxiv_pi_identity import identity_row
            rows.append(identity_row(review, lab, lab_evidence, client))
            continue
        if review.get('identity_evidence_format') == 'official_personal_bibliography_anchor_v1':
            from reviewed_owner_bibliography import identity_row
            rows.append(identity_row(review, lab, lab_evidence, client))
            continue
        if review.get('identity_evidence_format') == 'official_lab_citation_anchor_v1':
            from reviewed_lab_citations import identity_row
            rows.append(identity_row(review, lab, lab_evidence, client))
            continue
        if review.get('identity_evidence_format') == 'official_lab_bibliography_anchor':
            # No official ORCID: the lab's own reviewed publication list anchors the author.
            from bibliography_anchor import identity_row
            rows.append(identity_row(review, lab, lab_evidence, client))
            continue
        text, evidence = client.fetch(review['identity_evidence_url'])
        verify_profile_evidence(review, text)
        try:
            payload, source, alias_scope = author_candidates(client, review['orcid'], singleton_fallback)
        except RuntimeError as error:
            if 'HTTP 404:' in str(error):
                unresolved.append({'lab_id':review['lab_id'],'pi_name':review['pi_name'],'reason':'ORCID singleton not indexed'})
                continue
            # Preserve completed verification even when a network source pauses.
            remaining={(r['lab_id'],r['orcid']) for r in reviews[reviews.index(review):]}
            rows.extend(r for r in read_csv(OUT/'pi_identities.csv') if (r['lab_id'],r['orcid'].rsplit('/',1)[-1]) in remaining)
            unresolved.append({'lab_id':review['lab_id'],'pi_name':review['pi_name'],'reason':str(error),'remaining_reviews':len(remaining)})
            break
        if payload.get('meta', {}).get('count', 0) > 100:
            raise ValueError('ORCID resolves to more than 100 profiles; requires manual disambiguation')
        matched = []
        for candidate in payload.get('results', []):
            if (candidate.get('orcid') or '').rsplit('/', 1)[-1] != review['orcid']:
                continue
            if not author_name_evidence(candidate, review['profile_name_tokens']):
                continue
            if review['openalex_institution_id'] not in institution_ids(candidate):
                continue
            matched.append(candidate)
        if not matched:
            unresolved.append({'lab_id': review['lab_id'], 'pi_name': review['pi_name'], 'reason': 'No exact ORCID, compatible full-name and university-history profile found', 'source_snapshot': source['snapshot_path']})
            print('Identity requires affiliation review: ' + review['pi_name'], flush=True)
            continue
        result = max(matched, key=lambda a: a.get('works_count', 0))
        aliases = sorted({a['id'] for a in matched})
        rows.append({'identity_id': sid('pi', lab['lab_id'] + '|' + review['orcid']),
                     'lab_id': lab['lab_id'], 'university_id': lab['university_id'],
                     'pi_name': review['pi_name'], 'openalex_author_id': result['id'],
                     'orcid': 'https://orcid.org/' + review['orcid'], 'openalex_author_aliases': json.dumps(aliases),
                     'author_alias_review_scope': alias_scope,
                     'openalex_name_evidence': json.dumps({a['id']:author_name_evidence(a,review['profile_name_tokens']) for a in matched}, ensure_ascii=False),
                     'openalex_institution_id': review['openalex_institution_id'],
                     'identity_status': ('verified_official_profile_dblp_orcid' if review.get('identity_evidence_format') == 'official_profile_dblp_orcid' else 'verified_institutional_orcid'),
                     'identity_method': ('reviewed_official_lab_PI_link_and_owner_DBLP_PID_registry_ORCID_matches_OpenAlex' if review.get('identity_evidence_format') == 'official_profile_dblp_orcid' else 'reviewed_official_lab_PI_link_and_institutional_profile_ORCID_matches_OpenAlex'),
                     **lab_evidence,
                     'identity_evidence_url': review['identity_evidence_url'],
                     'identity_evidence_snapshot': evidence['snapshot_path'],
                     'identity_registry_url': review.get('identity_registry_evidence', {}).get('source_url', ''),
                     'identity_registry_snapshot': review.get('identity_registry_evidence', {}).get('snapshot_path', ''),
                     'identity_registry_sha256': review.get('identity_registry_evidence', {}).get('sha256', ''),
                     'author_evidence_snapshot': source['snapshot_path'], 'observed_on': CUTOFF,
                     'notes': review.get('notes', '')})
    atomic_json(OUT / 'identity_review_issues.json', unresolved)
    write_csv(OUT / 'pi_identities.csv', rows, PI_FIELDS)
    print(json.dumps({'verified_identities': len(rows)}))


def identity_author_ids(identity):
    aliases = identity.get('openalex_author_aliases')
    if isinstance(aliases, str) and aliases:
        aliases = json.loads(aliases)
    return set(aliases or []) | {identity['openalex_author_id']}


def collect(limit=None, max_pages=None):
    client = Client()
    identities = [r for r in read_csv(OUT / 'pi_identities.csv') if r['identity_status'].startswith('verified')]
    checkpoint = load_json(OUT / 'collection_checkpoint.json', {})
    author_ids = sorted({aid for r in identities for aid in identity_author_ids(r)})
    if limit:
        author_ids = author_ids[:limit]
    for author_id in author_ids:
        key = author_id.rsplit('/', 1)[-1]
        state = checkpoint.setdefault(key, {'cursor': '*', 'pages': [], 'records_fetched': 0, 'complete': False,
                                            'window_start': START, 'window_end': CUTOFF})
        if state['window_start'] != START or state['window_end'] != CUTOFF:
            raise ValueError('Changed date window requires a separate or reset checkpoint')
        if state['complete']:
            continue
        pages_this_run = 0
        while not state['complete'] and (max_pages is None or pages_this_run < max_pages):
            try:
                result, meta = client.api('works', {
                    'filter': f'authorships.author.id:{key},from_publication_date:{START},to_publication_date:{CUTOFF}',
                    'per_page': 100, 'cursor': state['cursor'], 'sort': 'publication_date:asc'})
            except RuntimeError as error:
                state['last_error'] = str(error)
                atomic_json(OUT / 'collection_checkpoint.json', checkpoint)
                print(str(error))
                return
            results = result.get('results', [])
            state['pages'].append(meta['snapshot_path'])
            state['records_fetched'] += len(results)
            state['reported_total'] = result.get('meta', {}).get('count')
            next_cursor = result.get('meta', {}).get('next_cursor')
            if next_cursor == state['cursor'] and results:
                raise RuntimeError('API repeated pagination cursor; refusing endless loop')
            state['cursor'] = next_cursor
            state['complete'] = not results or not next_cursor
            state.pop('last_error', None)
            atomic_json(OUT / 'collection_checkpoint.json', checkpoint)
            pages_this_run += 1
        print(json.dumps({'author': key, 'fetched': state['records_fetched'], 'complete': state['complete']}), flush=True)


def deduplicate(records):
    """Unite DOI/work-ID aliases, including transitive alias bridges."""
    parent = {}
    def find(key):
        parent.setdefault(key, key)
        while key != parent[key]:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    for work, _ in records:
        key = work['id']
        doi = normalize_doi(work.get('doi'))
        if doi:
            parent[find(key)] = find('doi:' + doi)
        else:
            find(key)
    grouped = defaultdict(list)
    for work, snapshot in records:
        grouped[find(work['id'])].append((work, snapshot))
    result, alias_rows = [], []
    for _, group in sorted(grouped.items()):
        # Prefer richest author evidence, then most recently updated metadata.
        work, snapshot = max(group, key=lambda x: (len(x[0].get('authorships', [])), x[0].get('updated_date', '')))
        doi = normalize_doi(work.get('doi')) or next((normalize_doi(w.get('doi')) for w, _ in group if normalize_doi(w.get('doi'))), '')
        canonical = 'doi:' + doi if doi else work['id']
        result.append((canonical, work, snapshot))
        for alias in sorted({w['id'] for w, _ in group}):
            alias_rows.append({'work_id': canonical, 'openalex_alias': alias, 'doi': doi})
    return result, alias_rows


def has_affiliation(authorship, institution_id):
    return any(institution_id == inst.get('id') or institution_id in inst.get('lineage', [])
               for inst in authorship.get('institutions', []))


def classify_link(identity, work, canonical_id, review=None):
    authors = work.get('authorships', [])
    matches = [(idx, a) for idx, a in enumerate(authors) if a.get('author', {}).get('id') in identity_author_ids(identity)]
    if not matches:
        return None
    index, author = matches[0]
    # A repeated ID is an unresolved metadata error, not a confirmed PI byline.
    identity_ok = identity['identity_status'].startswith('verified') and len(matches) == 1
    affiliation_ok = has_affiliation(author, identity['openalex_institution_id'])
    total = work.get('authors_count') or len(authors)
    truncated = bool(work.get('is_authors_truncated')) or total > len(authors) or (len(authors) >= 100 and authors[-1].get('author_position') != 'last')
    # Single-author records are both first and last; otherwise require explicit last.
    last = not truncated and index == len(authors) - 1 and (len(authors) == 1 or author.get('author_position') == 'last')
    strict = identity_ok and affiliation_ok and last
    # Direct source-reviewed arXiv listings can support the broader view when
    # affiliation metadata is absent. Exact DOI/full-byline/PI evidence is replayed;
    # known contrary affiliations remain held and the strict rule is unchanged.
    arxiv_bibliography = None
    if identity_ok and not affiliation_ok and review and review.get('review_status') == 'accepted' and canonical_id.startswith('doi:10.48550/arxiv.'):
        from reviewed_lab_arxiv import reviewed_link
        arxiv_bibliography = reviewed_link(identity, work, canonical_id)
        if arxiv_bibliography: review = arxiv_bibliography
    broader = bool(identity_ok and review and review.get('review_status') == 'accepted' and (affiliation_ok or arxiv_bibliography))
    reasons = []
    if not identity_ok: reasons.append('unverified_or_duplicate_author_identity')
    if not affiliation_ok: reasons.append('PI_publication_university_affiliation_not_confirmed')
    if truncated: reasons.append('author_list_incomplete')
    if strict: reasons.append('verified_PI_last_in_complete_byline_with_publication_time_university')
    elif not last: reasons.append('PI_not_confirmed_last_author')
    relation = bool(review and review.get('evidence_format') == 'reviewed_lab_arxiv_publisher_relation_v1')
    if broader:
        if arxiv_bibliography:
            from reviewed_lab_arxiv import REASON
            reasons.append(REASON)
        else:
            reasons.append('reviewed_lab_arxiv_listing_with_verified_publisher_relation' if relation else 'reviewed_official_lab_publication_list')
    return {'lab_id': identity['lab_id'], 'university_id': identity['university_id'],
            'pi_identity_id': identity['identity_id'], 'work_id': canonical_id,
            'publication_year': work['publication_year'], 'pi_author_id': author['author']['id'],
            'pi_author_position': author.get('author_position', ''), 'pi_author_order': index + 1,
            'pi_publication_university_match': int(affiliation_ok), 'strict_last_author': int(strict),
            'broader_reviewed': int(broader), 'strict_plus_reviewed': int(strict or broader), 'link_status': 'accepted_lab_bibliography' if broader else ('accepted_strict_PI_proxy' if strict else 'candidate'),
            'link_reason': ';'.join(reasons),
            'lab_temporal_membership_status': ('lab_arxiv_listing_not_historical_tenure' if arxiv_bibliography else ('publication_list_relation_evidence' if relation else 'publication_list_evidence')) if broader else 'not_established_by_PI_proxy',
            'review_source_url': review.get('source_url', '') if review else ''}


def annual_metrics(works, links):
    by_id = {r['work_id']: r for r in works}
    rows = []
    for mode in ('strict_last_author', 'broader_reviewed', 'strict_plus_reviewed'):
        for year in range(2016, 2027):
            eligible = [r for r in links if int(r.get(mode, int(r.get('strict_last_author', 0)) or int(r.get('broader_reviewed', 0)))) and int(r['publication_year']) == year]
            # Multiple reviewed PIs in one lab cannot duplicate that lab/work edge.
            edges = {(r['lab_id'], r['work_id']) for r in eligible}
            ids = {w for _, w in edges}
            labs = {lab for lab, _ in edges}
            counts = Counter(w for _, w in edges)
            fractional = sum(1 / counts[w] for _, w in edges)
            papers = {w for w in ids if by_id[w]['work_type'] in PAPER_TYPES}
            per_lab = Counter(lab for lab, _ in edges)
            topics = Counter(by_id[w].get('primary_topic') for w in ids if by_id[w].get('primary_topic'))
            classified = sum(topics.values())
            topic_entropy = -sum((n / classified) * math.log2(n / classified) for n in topics.values()) if classified else ''
            rows.append({'year': year, 'view': mode, 'observed_publishing_labs': len(labs),
                         'unique_scholarly_works': len(ids), 'unique_papers': len(papers),
                         'lab_work_edges': len(edges), 'fractional_work_total': round(fractional, 8),
                         'works_per_observed_publishing_lab': round(len(edges) / len(labs), 6) if labs else '',
                         'mean_current_citations_per_work': round(sum(int(by_id[w]['cited_by_count']) for w in ids) / len(ids), 6) if ids else '',
                         'open_access_share': round(sum(int(by_id[w]['is_oa']) for w in ids) / len(ids), 6) if ids else '',
                         'international_collaboration_share': round(sum(int(by_id[w]['countries_distinct_count']) > 1 for w in ids) / len(ids), 6) if ids else '',
                         'top_lab_share_of_lab_work_edges': round(max(per_lab.values()) / len(edges), 6) if edges else '',
                         'primary_topics_observed': len(topics),
                         'topic_classified_works': classified,
                         'primary_topic_entropy_bits': round(topic_entropy, 6) if classified else '',
                         'lab_output_hhi': round(sum((n / len(edges)) ** 2 for n in per_lab.values()), 6) if edges else '',
                         'coverage_status': 'partial_inventory_and_PI_coverage',
                         'partial_year': int(year == 2026), 'observed_through': CUTOFF})
    return rows


def build():
    identities = read_csv(OUT / 'pi_identities.csv')
    checkpoint = load_json(OUT / 'collection_checkpoint.json', {})
    records = []
    for path in sorted({p for state in checkpoint.values() for p in state['pages']}):
        payload = load_json(ROOT / path, {})
        for work in payload.get('results', []):
            if START <= (work.get('publication_date') or '') <= CUTOFF:
                records.append((work, path))
    reviews = {(r['lab_id'], normalize_doi(r['doi'])): r for r in load_json(OUT / 'lab_publication_reviews.json', [])}
    works, authorships, links = [], [], []
    from reviewed_arxiv_relations import reviewed_link as arxiv_reviewed_link
    arxiv_relation_outcomes = []
    doi_checkpoint=load_json(OUT/'doi_collection_checkpoint.json',{})
    for state in doi_checkpoint.values():
        if state.get('status')!='fetched':continue
        path=state['source_snapshot']
        work=load_json(ROOT/path,{})
        if START <= (work.get('publication_date') or '') <= CUTOFF:
            records.append((work,path))
    canonical, aliases = deduplicate(records)
    by_author = defaultdict(list)
    for identity in identities:
        for author_id in identity_author_ids(identity):
            by_author[author_id].append(identity)
    for work_id, work, snapshot in canonical:
        aa = work.get('authorships', [])
        topic = work.get('primary_topic') or {}
        total = work.get('authors_count') or len(aa)
        truncated = bool(work.get('is_authors_truncated')) or total > len(aa) or (len(aa) >= 100 and aa[-1].get('author_position') != 'last')
        works.append({'work_id': work_id, 'openalex_id': work['id'], 'doi': normalize_doi(work.get('doi')),
                      'title': work.get('display_name') or '', 'publication_date': work.get('publication_date', ''),
                      'publication_year': work['publication_year'], 'work_type': work.get('type', ''),
                      'journal': ((work.get('primary_location') or {}).get('source') or {}).get('display_name', ''),
                      'is_oa': int((work.get('open_access') or {}).get('is_oa', False)),
                      'cited_by_count': work.get('cited_by_count', 0), 'author_count': total,
                      'authorships_returned': len(aa), 'authorships_truncated': int(truncated),
                      'countries_distinct_count': work.get('countries_distinct_count', 0),
                      'primary_topic': topic.get('display_name', ''),
                      'primary_field': (topic.get('field') or {}).get('display_name', ''),
                      'primary_domain': (topic.get('domain') or {}).get('display_name', ''),
                      'source_url': BASE + 'works/' + work['id'].rsplit('/', 1)[-1],
                      'source_snapshot': snapshot, 'metadata_updated_date': work.get('updated_date', ''),
                      'language': work.get('language') or '', 'is_retracted': int(work['is_retracted']) if work.get('is_retracted') is not None else '',
                      'is_paratext': int(work['is_paratext']) if work.get('is_paratext') is not None else '', 'referenced_works_count': work.get('referenced_works_count', 0),
                      'fwci': work.get('fwci') if work.get('fwci') is not None else ''})
        seen_identities = set()
        for index, a in enumerate(aa):
            author = a.get('author') or {}
            institutions = a.get('institutions') or []
            authorships.append({'work_id': work_id, 'author_order': index + 1, 'author_id': author.get('id', ''),
                                'author_name': author.get('display_name', ''), 'raw_author_name': a.get('raw_author_name', ''),
                                'orcid': author.get('orcid', ''), 'raw_orcid': a.get('raw_orcid', ''),
                                'author_position': a.get('author_position', ''), 'is_corresponding': int(a.get('is_corresponding', False)),
                                'institution_ids': json.dumps([i['id'] for i in institutions]),
                                'institution_names': json.dumps([i.get('display_name', '') for i in institutions]),
                                'institution_lineage_ids': json.dumps(sorted({j for i in institutions for j in i.get('lineage', [])})),
                                'raw_affiliation_strings': json.dumps(a.get('raw_affiliation_strings', []), ensure_ascii=False),
                                'countries': json.dumps(a.get('countries', []))})
            for identity in by_author.get(author.get('id'), []):
                if identity['identity_id'] in seen_identities:
                    continue
                seen_identities.add(identity['identity_id'])
                review = reviews.get((identity['lab_id'], normalize_doi(work.get('doi'))))
                if not review or review.get('review_status') != 'accepted':
                    relation_review, outcomes = arxiv_reviewed_link(identity, work, work_id)
                    arxiv_relation_outcomes.extend(dict(result, lab_id=identity['lab_id'], pi_identity_id=identity['identity_id'], work_id=work_id) for result in outcomes)
                    if relation_review: review = relation_review
                link = classify_link(identity, work, work_id, review)
                if link:
                    links.append(link)
    atomic_json(OUT / 'arxiv_publisher_relation_outcomes.json', arxiv_relation_outcomes)
    works.sort(key=lambda r: (r['publication_date'], r['work_id']))
    links.sort(key=lambda r: (r['lab_id'], r['publication_year'], r['work_id']))
    write_csv(OUT / 'works.csv', works, WORK_FIELDS)
    write_csv(OUT / 'authorships.csv', authorships, AUTHOR_FIELDS)
    write_csv(OUT / 'lab_papers.csv', links, LINK_FIELDS)
    write_csv(OUT / 'work_aliases.csv', aliases, ['work_id', 'openalex_alias', 'doi'])
    metrics = annual_metrics(works, links)
    write_csv(OUT / 'annual_metrics.csv', metrics, list(metrics[0]))
    lab_metrics = []
    for mode in ('strict_last_author', 'broader_reviewed', 'strict_plus_reviewed'):
        for year in range(2016, 2027):
            edges = {(r['lab_id'], r['work_id']) for r in links if r[mode] and int(r['publication_year']) == year}
            count = Counter(work_id for _, work_id in edges)
            for lab in sorted({l for l, _ in edges}):
                ids = {w for l, w in edges if l == lab}
                lab_metrics.append({'lab_id': lab, 'year': year, 'view': mode, 'unique_scholarly_works': len(ids),
                                    'fractional_works': round(sum(1 / count[w] for w in ids), 8),
                                    'activity_definition': 'observed_publication_evidence_only'})
    write_csv(OUT / 'lab_year_metrics.csv', lab_metrics, ['lab_id', 'year', 'view', 'unique_scholarly_works', 'fractional_works', 'activity_definition'])
    active_author_keys = {aid.rsplit('/', 1)[-1] for r in identities for aid in identity_author_ids(r)}
    completed_keys = {key for key in active_author_keys if checkpoint.get(key, {}).get('complete')}
    blockers = sorted({r.get('last_error') for r in checkpoint.values() if r.get('last_error')})
    bibliography_dois={normalize_doi(r['doi']) for r in load_json(OUT/'lab_publication_reviews.json',[]) if r.get('review_status')=='accepted'}
    bibliography_checkpoint={d:state for d,state in doi_checkpoint.items() if d in bibliography_dois}
    summary = {'observation_cutoff': CUTOFF, 'window_start': START, 'window_end': CUTOFF,
               'verified_PI_identities': len(identities), 'verified_OpenAlex_author_IDs': len({aid for r in identities for aid in identity_author_ids(r)}), 'labs_with_verified_PI': len({r['lab_id'] for r in identities}),
               'unique_works_collected': len(works), 'candidate_PI_work_edges': len(links),
               'strict_last_author_edges': sum(r['strict_last_author'] for r in links),
               'broader_reviewed_edges': sum(r['broader_reviewed'] for r in links),
               'unique_strict_last_author_works': len({r['work_id'] for r in links if r['strict_last_author']}),
               'unique_broader_reviewed_works': len({r['work_id'] for r in links if r['broader_reviewed']}),
               'strict_plus_reviewed_edges': sum(r['strict_plus_reviewed'] for r in links),
               'unique_strict_plus_reviewed_works': len({r['work_id'] for r in links if r['strict_plus_reviewed']}),
               'authors_api_pagination_complete': len(completed_keys),
               'authors_api_pagination_started': len(active_author_keys & set(checkpoint)),
               'authors_api_pagination_not_started': len(active_author_keys - set(checkpoint)),
               'PIs_all_verified_alias_queries_complete': sum(all(aid.rsplit('/', 1)[-1] in completed_keys for aid in identity_author_ids(r)) for r in identities),
               'identity_candidate_labs_pending_review': len(load_json(OUT / 'identity_candidates.json', [])),
               'identity_reviews_pending': len(load_json(OUT/'identity_review_issues.json',[])),
               'single_profile_alias_reviews_pending': sum(r.get('author_alias_review_scope')=='single_profile_only_alias_review_pending' for r in identities),
               'reviewed_arxiv_publisher_relation_edges': sum(r['broader_reviewed'] and 'reviewed_lab_arxiv_listing_with_verified_publisher_relation' in r['link_reason'] for r in links),
               'reviewed_arxiv_missing_affiliation_edges': sum(r['broader_reviewed'] and 'reviewed_exact_lab_arxiv_bibliography_verified_PI_missing_affiliation' in r['link_reason'] for r in links),
               'reviewed_bibliography_pages': len(load_json(OUT/'bibliography_sources.json',[])),
               'reviewed_bibliography_labs': len({r['lab_id'] for r in load_json(OUT/'bibliography_sources.json',[])}),
               'bibliography_DOI_records_fetched': sum(r.get('status')=='fetched' for r in bibliography_checkpoint.values()),
               'bibliography_DOI_records_in_window': sum(r.get('status')=='fetched' and r.get('inside_window') for r in bibliography_checkpoint.values()),
               'bibliography_DOIs_not_indexed': sum(r.get('status')=='not_indexed' for r in bibliography_checkpoint.values()),
               'bibliography_DOI_lookup_errors': sum(r.get('status')=='error' for r in bibliography_checkpoint.values()),
               'bibliography_DOI_alias_reviews_pending': sum(r.get('status')=='review_required' for r in bibliography_checkpoint.values()),
               'direct_DOI_records_fetched': sum(r.get('status')=='fetched' for r in doi_checkpoint.values()),
               'direct_DOI_records_in_window': sum(r.get('status')=='fetched' and r.get('inside_window') for r in doi_checkpoint.values()),
               'direct_DOIs_not_indexed': sum(r.get('status')=='not_indexed' for r in doi_checkpoint.values()),
               'direct_DOI_lookup_errors': sum(r.get('status')=='error' for r in doi_checkpoint.values()),
               'direct_DOI_alias_reviews_pending': sum(r.get('status')=='review_required' for r in doi_checkpoint.values()),
               'labs_with_accepted_publications': len({r['lab_id'] for r in links if r['strict_plus_reviewed']}),
               'api_collection_blockers': blockers,
               'paper_types': sorted(PAPER_TYPES), 'inventory_complete': False,
               'limitations': ['PI-last-author affiliation is a lab attribution proxy; historical membership in the named lab is not established by this rule.',
                              'Broader reviewed view only accepts works independently present in reviewed official lab publication lists; it may be smaller than the strict view during collection.',
                              'Exact lab-listed arXiv preprints with verified PI IDs and matching complete bylines may enter the broader view when affiliation metadata is absent. Their lab listing does not establish historical lab tenure; strict last-author counts still require publication-time university evidence.',
                              'No publication in a year is not evidence a lab was inactive. Observed publishing labs are a lower bound, not total active labs.',
                              '2026 ends on 2026-10-12 and is incomplete. Citation counts are current snapshots, not annual citation accrual.',
                              'OpenAlex identity, affiliation, document-type and author-list metadata can be wrong or incomplete. Truncated author lists are excluded from strict last-author assignment.',
                              'Deduplication uses DOI and OpenAlex work IDs, not title similarity; preprint and journal versions with distinct identifiers remain separate scholarly works.',
                              'Identities cover only a source-verified subset of leaders. Missing labs and papers are uncollected, not zero.',
                              'Direct DOI lookups supplement author-query pagination and do not establish complete author or lab bibliographies. Singleton ORCID lookups can omit author-profile aliases.']}
    coverage = []
    identities_by_lab, links_by_lab = defaultdict(list), defaultdict(list)
    for row in identities: identities_by_lab[row['lab_id']].append(row)
    for row in links: links_by_lab[row['lab_id']].append(row)
    for lab in read_csv(ROOT / 'data/processed/labs.csv'):
        pi = identities_by_lab[lab['lab_id']]
        edges = links_by_lab[lab['lab_id']]
        completed_pi_count=sum(all(checkpoint.get(aid.rsplit('/',1)[-1],{}).get('complete',False) for aid in identity_author_ids(r)) for r in pi)
        coverage.append({'lab_id': lab['lab_id'], 'university_id': lab['university_id'],
                         'verified_PI_identities': len(pi),
                         'authors_API_complete': completed_pi_count,
                         'strict_last_author_works': len({r['work_id'] for r in edges if r['strict_last_author']}),
                         'broader_reviewed_works': len({r['work_id'] for r in edges if r['broader_reviewed']}),
                         'strict_plus_reviewed_works': len({r['work_id'] for r in edges if r['strict_plus_reviewed']}),
                         'publication_coverage_status': ('verified_PI_API_paginated_metadata_incomplete' if completed_pi_count==len(pi) else 'verified_PI_query_incomplete') if pi else 'PI_identity_not_yet_verified',
                         'lab_publications_complete': 0})
    write_csv(OUT / 'publication_coverage.csv', coverage, ['lab_id', 'university_id', 'verified_PI_identities', 'authors_API_complete', 'strict_last_author_works', 'broader_reviewed_works', 'strict_plus_reviewed_works', 'publication_coverage_status', 'lab_publications_complete'])
    pi_coverage = []
    for pi in identities:
        states = [checkpoint.get(aid.rsplit('/', 1)[-1], {}) for aid in identity_author_ids(pi)]
        state = {'complete': all(x.get('complete', False) for x in states), 'reported_total': sum(x.get('reported_total') or 0 for x in states), 'records_fetched': sum(x.get('records_fetched', 0) for x in states)}
        pi_coverage.append({'identity_id': pi['identity_id'], 'lab_id': pi['lab_id'],
                            'pi_name': pi['pi_name'], 'openalex_author_id': pi['openalex_author_id'],
                            'identity_status': pi['identity_status'], 'API_query_complete': int(state.get('complete', False)),
                            'API_reported_total': state.get('reported_total', ''), 'records_fetched': state.get('records_fetched', 0),
                            'window_start': START, 'window_end': CUTOFF,
                            'coverage_status': 'complete_query_not_complete_real_world_bibliography' if state.get('complete') else 'query_not_complete'})
    write_csv(OUT / 'pi_collection_coverage.csv', pi_coverage, ['identity_id', 'lab_id', 'pi_name', 'openalex_author_id', 'identity_status', 'API_query_complete', 'API_reported_total', 'records_fetched', 'window_start', 'window_end', 'coverage_status'])
    bibliography_coverage=[]
    review_by_doi=defaultdict(list)
    for review in load_json(OUT/'lab_publication_reviews.json',[]):
        if review.get('review_status')=='accepted':review_by_doi[normalize_doi(review['doi'])].append(review)
    work_by_doi={normalize_doi(r['doi']):r for r in works if r['doi']}
    accepted_by_work=defaultdict(set)
    for link in links:
        if link['strict_plus_reviewed']:accepted_by_work[link['work_id']].add(link['lab_id'])
    for doi,review_rows in sorted(review_by_doi.items()):
        work=work_by_doi.get(doi)
        state=doi_checkpoint.get(doi,{})
        status='collected_in_window' if work else ('outside_window' if state.get('status')=='fetched' else state.get('status','not_yet_looked_up'))
        bibliography_coverage.append(dict(doi=doi,listed_lab_ids=json.dumps(sorted({r['lab_id'] for r in review_rows})),source_urls=json.dumps(sorted({r['source_url'] for r in review_rows})),metadata_status=status,work_id=work['work_id'] if work else '',publication_date=work['publication_date'] if work else state.get('publication_date',''),accepted_lab_ids=json.dumps(sorted(accepted_by_work[work['work_id']])) if work else '[]',source_snapshot=work['source_snapshot'] if work else state.get('source_snapshot',''),lookup_error=state.get('last_error','')))
    write_csv(OUT/'bibliography_doi_coverage.csv',bibliography_coverage,['doi','listed_lab_ids','source_urls','metadata_status','work_id','publication_date','accepted_lab_ids','source_snapshot','lookup_error'])
    atomic_json(OUT / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    discovery = sub.add_parser('discover')
    discovery.add_argument('--limit', type=int, default=50)
    discovery.add_argument('--university')
    p = sub.add_parser('verify-seeds'); p.add_argument('--singleton-fallback', action='store_true')
    sub.add_parser('review-bibliographies')
    collection = sub.add_parser('collect')
    collection.add_argument('--limit', type=int)
    collection.add_argument('--max-pages', type=int)
    sub.add_parser('build')
    args = parser.parse_args()
    if args.command == 'discover': discover(args.limit, args.university)
    elif args.command == 'verify-seeds': verify_seeds(args.singleton_fallback)
    elif args.command == 'review-bibliographies': review_bibliographies()
    elif args.command == 'collect': collect(args.limit, args.max_pages)
    elif args.command == 'build': build()


if __name__ == '__main__':
    main()
