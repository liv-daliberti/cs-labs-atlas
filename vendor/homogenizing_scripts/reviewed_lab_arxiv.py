# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_lab_arxiv.py (sha256 bcf2fb73b2672a45f8c4468f09b3c977fa31fd6bebf1cfc8219c9c21f71e1bec); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Exact lab-listed arXiv preprints with verified PIs and missing affiliations.

This narrow broader-view rule never changes the strict last-author rule, resolves
names by themselves, or substitutes present-day affiliation for historical data.
Explicit contrary/undecoded affiliation evidence is held for separate review.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib, html, json, re, unicodedata, xml.etree.ElementTree as ET
from datetime import date
from functools import lru_cache
from pathlib import Path
from bs4 import BeautifulSoup
from author_name_matching import name_tokens, full_atom, match_name
from arxiv_identifiers import arxiv_doi
ROOT = P.WORLD_ATLAS  # vendored: the data root (was Path(__file__).resolve().parents[1])
PACKAGE = 'data/reviews/cs20_arxiv_bibliography_integration'
MANIFEST_SHA256 = '93abccf436e5d86f971a638e39c34de75e4f55e2476f2b83d13a18c07c0fe23e'
PINS = {PACKAGE: MANIFEST_SHA256, 'data/reviews/cs21_arxiv_new_pi_reviews': '2c8973e48a27ab3c70703209a2c468320f521e440b128fb592772fe3b5fbb7e1', 'data/reviews/cs22_arxiv_new_pi_reviews': 'f675f9bea80843834e57486a96cdfbfd5bc651eca734acbe05d31e2afb2d0f1c'}
PINS['data/reviews/arxiv_pi_lab_crosscheck_20261014'] = '4dde54b38c9b3b1ffc4234640f1bcbb1d988bf12c2c42228c2aa5ec3f667ff3b'
REASON = 'reviewed_exact_lab_arxiv_bibliography_verified_PI_missing_affiliation'
FORMAT = 'reviewed_exact_lab_arxiv_bibliography_v1'
A = '{http://www.w3.org/2005/Atom}'
X = '{http://arxiv.org/schemas/atom}'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def name_order(value):
    """Only an explicit single comma licenses surname-first inversion."""
    if value.count(',') == 1:
        family, given = value.split(',')
        if not family.strip() or not given.strip():
            return ()
        value = given + ' ' + family
    elif ',' in value:
        return ()
    return name_tokens(value)


def title_tokens(value):
    value = html.unescape(re.sub(r'<[^>]*>', '', value or ''))
    value = unicodedata.normalize('NFKC', value).casefold()
    return tuple(''.join(c if c.isalnum() or unicodedata.category(c).startswith('M') else ' ' for c in value).split())


def full_name(value):
    tokens = name_order(value)
    return (len(tokens) >= 2 and sum(full_atom(t) for t in tokens) >= 2
            and not any(any(c.isdigit() for c in t) for t in tokens)
            and not re.search(r'\b(consortium|collaboration|study group|working group|committee|investigators|collaborators)\b', value, re.I))


def compare(identity, work, entry, canonical_id):
    """Pure evidence checks; an empty result means the narrow rule is eligible."""
    holds = []
    doi = (work.get('doi') or '').lower().removeprefix('https://doi.org/')
    if doi != entry['doi'] or canonical_id != 'doi:' + entry['doi']:
        holds.append('exact_preprint_DOI_required')
    if not identity.get('identity_status', '').startswith('verified'):
        holds.append('unverified_PI')
    if not title_tokens(entry['title']) or title_tokens(entry['title']) != title_tokens(work.get('display_name') or work.get('title')):
        holds.append('title_mismatch')
    pd = work.get('publication_date', '')
    try:
        valid_date = date.fromisoformat(pd) and '2016-01-01' <= pd <= '2026-10-12' and str(work.get('publication_year')) == pd[:4] and pd == entry['published'][:10]
    except (ValueError, TypeError):
        valid_date = False
    if not valid_date:
        holds.append('publication_date_mismatch_or_outside_window')
    authors = work.get('authorships') or []
    if not authors or len(authors) >= 100:
        holds.append('empty_or_potentially_truncated_byline')
    for key, value in work.items():
        if 'truncat' in key.lower() and ('author' in key.lower() or key == 'is_truncated') and value not in (False, None, 0, '', 'false', '0'):
            holds.append('truncated_byline')
    for key in ('authors_count', 'author_count', 'authorships_count'):
        if key in work and work[key] is not None:
            value = work[key]
            if isinstance(value, bool) or str(value) != str(len(authors)):
                holds.append('declared_author_count_mismatch')
    source_names = [a['name'] for a in entry['authors']]
    for names in (source_names, [(a.get('author') or {}).get('display_name', '') for a in authors], [a.get('raw_author_name') or '' for a in authors]):
        if not names or not all(full_name(n) for n in names):
            holds.append('full_named_byline_required')
        if [name_order(n) for n in names] != [name_order(n) for n in source_names]:
            holds.append('ordered_full_byline_mismatch')
    try:
        aliases = {identity['openalex_author_id'], *json.loads(identity.get('openalex_author_aliases') or '[]')}
    except (KeyError, ValueError, TypeError):
        aliases = set()
    matches = [(i, a) for i, a in enumerate(authors) if (a.get('author') or {}).get('id') in aliases]
    if len(matches) != 1:
        holds.append('PI_ID_not_uniquely_present')
    else:
        i, own = matches[0]
        if i >= len(source_names) or not match_name(source_names[i], name_tokens(identity.get('pi_name', ''))):
            holds.append('PI_full_name_mismatch')
        if own.get('institutions') or own.get('raw_affiliation_strings') or own.get('affiliations'):
            holds.append('explicit_affiliation_requires_existing_or_manual_review')
        if i < len(entry['authors']) and entry['authors'][i].get('affiliations'):
            holds.append('arxiv_affiliation_requires_manual_review')
    return sorted(set(holds))


@lru_cache(maxsize=2048)
def source_bytes(root, path, expected):
    root = Path(root).resolve()
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('Source path escapes project')
    raw = resolved.read_bytes()
    if digest(raw) != expected:
        raise ValueError('Reviewed arXiv source bytes changed: ' + path)
    return raw


@lru_cache(maxsize=64)
def atom_entries(root, path, expected):
    raw = source_bytes(root, path, expected)
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unexpected XML declaration')
    tree = ET.fromstring(raw)
    if tree.tag != A + 'feed':
        raise ValueError('Expected Atom feed')
    result = {}
    for node in tree.findall(A + 'entry'):
        url = node.findtext(A + 'id', '')
        doi = arxiv_doi(url)
        if not doi or doi in result:
            raise ValueError('Invalid or duplicate arXiv entry')
        result[doi] = dict(doi=doi, title=' '.join(node.findtext(A+'title', '').split()), published=node.findtext(A+'published', ''), authors=[dict(name=' '.join(a.findtext(A+'name', '').split()), affiliations=[' '.join(x.itertext()).strip() for x in a.findall(X+'affiliation')]) for a in node.findall(A+'author')])
    return result


@lru_cache(maxsize=256)
def anchors(root, path, expected, selector):
    section = BeautifulSoup(source_bytes(root, path, expected), 'html.parser').select_one(selector)
    if section is None:
        raise ValueError('Reviewed bibliography selector missing')
    return {(a.get('href'), a.get_text(' ', strip=True)) for a in section.select('a[href]')}


def bibliography_anchors(root, listing, bibliography):
    """Replay the reviewed source format; never parse structured data as HTML."""
    source_format = bibliography.get('source_format')
    if not source_format:
        return anchors(str(root), listing['source_snapshot'], listing['source_sha256'],
                       bibliography.get('selector', 'body'))
    from reviewed_rail_bibliography import FORMAT as RAIL_FORMAT, extract_links
    if source_format != RAIL_FORMAT:
        raise ValueError('Unsupported reviewed arXiv bibliography format')
    raw = source_bytes(str(root), listing['source_snapshot'], listing['source_sha256'])
    meta_path = (Path(root) / listing['source_snapshot']).with_suffix('.meta.json')
    meta = json.loads(meta_path.read_text())
    if meta['snapshot_path'] != listing['source_snapshot']:
        raise ValueError('Structured bibliography snapshot path mismatch')
    links = extract_links(bibliography, raw.decode('utf-8'), meta, root)
    return {(href, title) for title, href, method in links.values()}


def validate_record(record, identity, work, canonical_id, root=ROOT):
    if record['identity'] != identity:
        return ['reviewed_PI_identity_changed']
    listing, bib = record['listing'], record['bibliography']
    if listing['lab_id'] != identity['lab_id'] or bib['lab_id'] != identity['lab_id']:
        return ['wrong_lab']
    if listing['review_status'] != 'accepted' or bib['review_status'] != 'accepted_official_lab_bibliography' or listing['source_url'] != bib['source_url']:
        return ['unreviewed_lab_bibliography']
    if bib.get('source_sha256') and bib['source_sha256'] != listing['source_sha256']:
        return ['bibliography_source_hash_mismatch']
    exact_anchors = bibliography_anchors(root, listing, bib)
    if (listing['anchor_href'], listing.get('anchor_text', '')) not in exact_anchors or arxiv_doi(listing['anchor_href']) != listing['doi']:
        return ['exact_lab_anchor_missing']
    proof = record['arxiv_source']
    entry = atom_entries(str(root), proof['path'], proof['sha256']).get(listing['doi'])
    if entry is None:
        return ['exact_arxiv_record_missing']
    meta = record['openalex_source']
    payload = json.loads(source_bytes(str(root), meta['path'], meta['sha256']))
    originals = [w for w in payload.get('results', [payload]) if w.get('id') == record['openalex_id']]
    if len(originals) != 1 or work.get('id') != record['openalex_id']:
        return ['exact_OpenAlex_record_missing']
    return sorted(set(compare(identity, originals[0], entry, canonical_id) + compare(identity, work, entry, canonical_id)))


@lru_cache(maxsize=1)
def context():
    index = {}
    for package, pin in PINS.items():
        folder = ROOT / package
        raw = (folder / 'review_manifest.json').read_bytes()
        if digest(raw) != pin:
            raise ValueError('Reviewed arXiv bibliography manifest changed')
        manifest = json.loads(raw)
        rows = json.loads(source_bytes(str(ROOT), package+'/accepted_reviews.json', manifest['reviews_sha256']))
        for record in rows:
            key = (record['identity']['identity_id'], 'doi:' + record['listing']['doi'])
            if key in index:
                raise ValueError('Duplicate reviewed PI/preprint')
            index[key] = record
    return index


def reviewed_link(identity, work, canonical_id):
    if not canonical_id.startswith('doi:10.48550/arxiv.'):
        return None
    record = context().get((identity['identity_id'], canonical_id))
    if not record or validate_record(record, identity, work, canonical_id):
        return None
    return dict(lab_id=identity['lab_id'], doi=record['listing']['doi'], source_url=record['listing']['source_url'], review_status='accepted', evidence_format=FORMAT)
