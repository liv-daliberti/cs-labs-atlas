# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/dblp_identity_bridge.py (sha256 be1d1a450bc3b4cbc92afc9f069fbcc2aa76e5f7d0117da3c96fd6cd3d84e18a); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Validate a reviewed official owner-profile → DBLP PID → ORCID chain.

The owner-link selection is a human review of frozen profile bytes. This is not
an author-name search and never establishes lab membership of any publication.
"""
import hashlib
import json
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup


def fail_unless(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_pid(url):
    parsed = urlsplit(url)
    fail_unless(parsed.scheme == 'https' and parsed.hostname == 'dblp.org'
                and not parsed.query and not parsed.fragment, 'Invalid DBLP owner-link host')
    path = parsed.path.removesuffix('.html')
    fail_unless(re.fullmatch(r'/pid/[A-Za-z0-9_/-]+', path) is not None
                and '..' not in path, 'Invalid canonical DBLP PID')
    return 'https://dblp.org' + path


def validate_bridge(review, text, root, normalize_name):
    fail_unless(review.get('review_status') == 'accepted'
                and review.get('pi_lab_evidence_source_id'), 'DBLP bridge needs reviewed lab-leader evidence')
    fail_unless(hashlib.sha256(text.encode('utf-8')).hexdigest() == review['identity_profile_sha256'],
                'DBLP owner profile bytes changed')
    soup = BeautifulSoup(text, 'html.parser')
    names = soup.select(review['identity_name_selector'])
    fail_unless(len(names) == 1, 'DBLP owner name is not unique')
    heading = names[0].get_text(' ', strip=True)
    required = normalize_name(' '.join(review['profile_name_tokens'])).split()
    fail_unless(required and all(x in normalize_name(heading).split() for x in required),
                'DBLP owner full name mismatch')
    anchors = soup.select(review['identity_dblp_selector'])
    fail_unless(len(anchors) == 1 and anchors[0].name == 'a', 'DBLP owner link is not unique')
    anchor = anchors[0]
    pid = canonical_pid(anchor.get('href', ''))
    fail_unless(pid == canonical_pid(review['identity_dblp_person']), 'DBLP owner PID mismatch')
    fail_unless(hashlib.sha256(str(anchor.parent).encode()).hexdigest() == review['identity_owner_context_sha256'],
                'Reviewed DBLP owner-link context changed')
    registry = review['identity_registry_evidence']
    paths = []
    for key in ['snapshot_path', 'metadata_path']:
        path = (root / registry[key]).resolve()
        fail_unless(path.is_relative_to(root.resolve()), 'DBLP evidence path outside project')
        paths.append(path)
    raw = paths[0].read_bytes()
    meta = json.loads(paths[1].read_bytes())
    fail_unless(hashlib.sha256(raw).hexdigest() == registry['sha256'] == meta['sha256']
                and meta['snapshot_path'] == registry['snapshot_path']
                and meta['source_id'] == registry['source_id']
                and int(meta['http_status']) == 200, 'DBLP registry snapshot mismatch')
    url = urlsplit(meta['requested_url'])
    fail_unless(meta['requested_url'] == registry['source_url'] and url.scheme == 'https'
                and url.hostname == 'sparql.dblp.org' and url.path == '/sparql',
                'DBLP registry source host mismatch')
    bindings = json.loads(raw)['results']['bindings']
    matches = [b for b in bindings if b.get('person', {}).get('type') == 'uri'
               and b['person']['value'] == pid]
    orcids = {b.get('orcid', {}).get('value') for b in matches}
    fail_unless(matches and orcids == {'https://orcid.org/' + review['orcid']}
                and all(b.get('orcid', {}).get('type') == 'uri' for b in matches),
                'DBLP registry ORCID missing or ambiguous')
    fail_unless(all(all(token in normalize_name(b.get('name', {}).get('value', '')).split()
                        for token in required) for b in matches), 'DBLP registry full name mismatch')
    return heading
