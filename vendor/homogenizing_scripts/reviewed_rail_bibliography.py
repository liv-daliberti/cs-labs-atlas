# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_rail_bibliography.py (sha256 857f45251bab0f425a86479015f5f2e596ce3019ce870908b2cbdc91ba629dce); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Replay the official RAIL publication widget's JSON without executing JavaScript.

Only linked DOI/arXiv identifiers establish bibliography membership. Publication
order, affiliation, identity, dates and acceptance remain separate checks.
"""
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup

FORMAT = 'rail_publications_json_v1'
PAGE = 'https://rail.eecs.berkeley.edu/publications.html'
SCRIPT = 'https://rail.eecs.berkeley.edu/bundle.js'
DATA = 'https://rail.eecs.berkeley.edu/data/pubs.json'
HOME = 'https://rail.eecs.berkeley.edu/'


def checked_bytes(meta, expected_url, root):
    if (meta.get('requested_url') != expected_url or meta.get('final_url') != expected_url
            or int(meta.get('http_status', 0)) != 200):
        raise ValueError('Official RAIL source URL/status mismatch')
    raw = (Path(root) / meta['snapshot_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != meta['sha256']:
        raise ValueError('Official RAIL source bytes changed')
    return raw


def extract_links(source, text, meta, root):
    from publications import sid, bibliography_doi
    from arxiv_identifiers import arxiv_doi
    if (source.get('source_format') != FORMAT or source.get('source_url') != DATA
            or source.get('lab_id') != sid('lab', 'university-of-california-berkeley|' + HOME)):
        raise ValueError('Unreviewed structured bibliography or lab')
    raw = checked_bytes(meta, DATA, root)
    if raw.decode('utf-8') != text or source.get('source_sha256') != meta['sha256']:
        raise ValueError('Structured bibliography payload mismatch')
    widget = source['widget_evidence']
    page = checked_bytes(widget['page'], PAGE, root).decode('utf-8')
    script = checked_bytes(widget['script'], SCRIPT, root).decode('utf-8')
    soup = BeautifulSoup(page, 'html.parser')
    if len(soup.select('script[src="bundle.js"]')) != 1 or not soup.select_one('#rail-pub-widget'):
        raise ValueError('Official page no longer selects the reviewed widget')
    if "pub_url: './data/pubs.json'" not in script:
        raise ValueError('Official widget no longer selects the reviewed data')
    records = json.loads(text)
    if not isinstance(records, dict) or not records:
        raise ValueError('Invalid publication map')
    found = {}
    for key, item in records.items():
        if (not isinstance(key, str) or not isinstance(item, dict)
                or not isinstance(item.get('title'), str) or not item['title'].strip()
                or not isinstance(item.get('authors'), list) or not item['authors']
                or any(not isinstance(a, str) or not a.strip() for a in item['authors'])
                or not isinstance(item.get('hlinks'), list)):
            raise ValueError('Invalid publication entry')
        title = BeautifulSoup(item['title'], 'html.parser').get_text(' ', strip=True)
        for link in item['hlinks']:
            if not isinstance(link, list) or len(link) != 2 or any(not isinstance(v, str) for v in link):
                raise ValueError('Invalid publication link')
            href = link[1]
            doi = bibliography_doi(href)
            method = 'DOI_link_in_reviewed_official_lab_JSON_bibliography'
            if not doi:
                doi = arxiv_doi(href)
                method = 'canonical_arXiv_DOI_from_link_in_reviewed_official_lab_JSON_bibliography'
            if doi and (doi not in found or method.startswith('DOI_link')):
                found[doi] = (title, href, method)
    return found
