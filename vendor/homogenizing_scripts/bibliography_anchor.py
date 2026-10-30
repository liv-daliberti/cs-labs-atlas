# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/bibliography_anchor.py (sha256 4e075a5e82bdbc0b82eb8bf0d81018a5a2f995ffbd94891b95beb2de38683dd8); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Identify a named lab leader's OpenAlex author from the lab's own official publication list.

Bibliography-based identity evidence is separately labelled from institutional
ORCID verification. An OpenAlex-reported ORCID is metadata, not an owner assertion.
The reviewed list is a hash-pinned official lab bibliography bounded by a selector, read exactly
as review_bibliographies reads it. Each anchor DOI is resolved through the free OpenAlex
singleton route. The leader's profile is the author ID whose byline name carries every token
of the officially recorded leader name and which appears on at least ANCHOR_MIN_SHARE (and
at least ANCHOR_MIN_WORKS) of the resolved works. Surname or initial matches never count. A
second full-name-compatible profile on many listed works is a split profile or a homonym, so
the anchor is refused for review. The anchored profile must carry the selected university in
its institution history. Its OpenAlex ORCID is recorded when present and is not required.
This establishes an author identity only; author-order and publication-time affiliation
guards on every paper are unchanged.

A list can span several official pages (pagination, or the lab site plus the institute page):
bibliography_pages adds pages, each hash-pinned with its own selector. With pubmed_links, a
PubMed link inside the selector also identifies a listed work through the free OpenAlex
pmid: singleton, recorded as "pmid:<number>". With text_identifiers, a DOI or "PMID: n"
printed (not linked) inside the selector counts the same way. Titles are never matched.
Works listed twice (DOI and PubMed) count once.
"""
import json
import hashlib
import re
from collections import Counter
from urllib.parse import quote, urlsplit

from bs4 import BeautifulSoup

from arxiv_identifiers import arxiv_doi
from author_name_matching import name_tokens as unicode_name_tokens, match_name, requirements
from publications import (ROOT, CUTOFF, author_name_evidence, bibliography_doi, institution_ids,
                          normalize_doi, normalize_name, sid)

FORMAT = 'official_lab_bibliography_anchor'
ANCHOR_MIN_WORKS = 5
ANCHOR_MIN_SHARE = 0.5
COMPETITOR_MAX_SHARE = 0.2
TEXT_DOI = re.compile(r'\b(10\.\d{4,9}/[^\s<>"]+)')
TEXT_PMID = re.compile(r'\bPMID:?\s*(\d{5,9})(?!\d)')
PUBMED = re.compile(r'(?:pubmed\.ncbi\.nlm\.nih\.gov/|ncbi\.nlm\.nih\.gov/pubmed/|ncbi-nlm-nih-gov[\w.-]*/pubmed/|[?&]list_uids=)(\d{5,9})(?!\d)')


def fail_unless(condition, message):
    if not condition:
        raise ValueError(message)


def listed_dois(text, selector, pubmed=False, text_ids=False):
    """The identifiers review_bibliographies would record for this source and selector."""
    content = BeautifulSoup(text, 'html.parser').select_one(selector)
    fail_unless(content is not None, 'Bibliography selector no longer matches')
    found = set()
    if text_ids:
        visible = content.get_text(' ')
        found |= {d for d in (normalize_doi(m.rstrip('.,;:)]}')) for m in TEXT_DOI.findall(visible)) if d}
        found |= {'pmid:' + m for m in TEXT_PMID.findall(visible)}
    for anchor in content.find_all('a', href=True):
        doi = bibliography_doi(anchor['href']) or arxiv_doi(anchor['href'])
        if doi:
            found.add(doi)
        elif pubmed and PUBMED.search(anchor['href']):
            found.add('pmid:' + PUBMED.search(anchor['href']).group(1))
    return sorted(found)


def name_tokens(tokens):
    return list(unicode_name_tokens(' '.join(tokens)))


def byline_matches(work, tokens):
    """Author IDs on this work whose byline display name carries every leader-name token."""
    required, error = requirements(tokens)
    if error:
        return set()
    ids = set()
    for authorship in work.get('authorships', []):
        author = authorship.get('author') or {}
        if author.get('id') and match_name(author.get('display_name') or '', tokens):
            ids.add(author['id'])
    return ids


def work_by_doi(client, doi):
    if doi.startswith('pmid:'):
        work, meta = client.api('works/' + doi)
        fail_unless((work.get('ids') or {}).get('pmid', '').rsplit('/', 1)[-1] == doi[5:], 'PMID lookup returned a different record: ' + doi)
        return work, meta
    work, meta = client.api('works/doi:' + quote(doi, safe='/'))
    fail_unless(normalize_doi(work.get('doi')) == doi, 'DOI lookup returned a different DOI: ' + doi)
    return work, meta


def unique_works(works):
    """A work listed by both its DOI and its PubMed link counts once."""
    return list({w['id']: w for w in works}.values())


def tally(works, tokens):
    counts = Counter()
    for work in works:
        counts.update(byline_matches(work, tokens))
    return counts.most_common()


def verify_institution_review(review):
    """Replay optional exact institution metadata and the reviewed cohort domain."""
    path = review.get('institution_evidence_snapshot')
    if not path:
        return
    raw = (ROOT / path).read_bytes()
    fail_unless(hashlib.sha256(raw).hexdigest() == review['institution_evidence_sha256'], 'Institution source bytes changed')
    record = json.loads(raw)
    fail_unless(record['id'] == review['openalex_institution_id'], 'Institution identifier mismatch')
    host = (urlsplit(record.get('homepage_url') or '').hostname or '').lower().removeprefix('www.')
    official = review['institution_expected_homepage_domain'].lower().removeprefix('www.')
    fail_unless(bool(official) and (host == official or host.endswith('.' + official)), 'Institution homepage differs from reviewed cohort university')


def anchor_author(review, client):
    """Re-derive the anchored author from preserved bytes; raise on any changed or weak evidence."""
    fail_unless(review.get('identity_evidence_format') == FORMAT, 'Not a bibliography-anchor review')
    verify_institution_review(review)
    pages = [dict(url=review['identity_evidence_url'], sha256=review['identity_profile_sha256'],
                  selector=review['bibliography_selector'])] + review.get('bibliography_pages', [])
    listed, meta = set(), None
    for page in pages:
        text, page_meta = client.fetch(page['url'])
        fail_unless(page_meta['sha256'] == page['sha256'], 'Reviewed bibliography bytes changed: ' + page['url'])
        listed |= set(listed_dois(text, page['selector'], review.get('pubmed_links', False), review.get('text_identifiers', False)))
        meta = meta or page_meta
    used = review['anchor_dois']
    fail_unless(used and set(used) <= listed, 'Anchor identifiers must come from the reviewed bibliography selectors')
    works = unique_works([work_by_doi(client, doi)[0] for doi in used])
    ranked = tally(works, review['profile_name_tokens'])
    fail_unless(ranked, 'No full-name byline on the listed works')
    primary, hits = ranked[0]
    fail_unless(primary == review['openalex_author_id'], 'Anchored author differs from the review')
    fail_unless(hits >= ANCHOR_MIN_WORKS and hits / len(works) >= ANCHOR_MIN_SHARE,
                f'Anchor too weak: {hits} of {len(works)} listed works')
    fail_unless(all(n / len(works) < COMPETITOR_MAX_SHARE for _, n in ranked[1:]),
                'A competing full-name author profile appears on the listed works')
    author, source = client.api('authors/' + primary.rsplit('/', 1)[-1])
    fail_unless(author['id'] == primary, 'Author lookup returned a different profile')
    fail_unless(author_name_evidence(author, review['profile_name_tokens']), 'Author profile name is incompatible')
    fail_unless(review['openalex_institution_id'] in institution_ids(author), 'University absent from author history')
    fail_unless((author.get('orcid') or '').rsplit('/', 1)[-1] == review.get('orcid', ''),
                'OpenAlex ORCID differs from the review')
    stats = dict(anchor_works=len(works), anchor_hits=hits, competitors=ranked[1:4])
    return author, source, meta, stats


def identity_row(review, lab, lab_evidence, client):
    author, source, meta, stats = anchor_author(review, client)
    orcid = review.get('orcid', '')
    return {'identity_id': sid('pi', lab['lab_id'] + '|' + (orcid or author['id'])),
            'lab_id': lab['lab_id'], 'university_id': lab['university_id'],
            'pi_name': review['pi_name'], 'openalex_author_id': author['id'],
            'orcid': 'https://orcid.org/' + orcid if orcid else '',
            'openalex_author_aliases': json.dumps([author['id']]),
            'author_alias_review_scope': 'bibliography_anchor_primary_profile_only',
            'openalex_name_evidence': json.dumps({author['id']: author_name_evidence(author, review['profile_name_tokens'])}, ensure_ascii=False),
            'openalex_institution_id': review['openalex_institution_id'],
            'identity_status': 'verified_official_lab_bibliography_anchor',
            'identity_method': 'reviewed_official_lab_leader_and_official_lab_bibliography_anchor_matches_OpenAlex',
            **lab_evidence,
            'identity_evidence_url': review['identity_evidence_url'],
            'identity_evidence_snapshot': meta['snapshot_path'],
            'identity_registry_url': '', 'identity_registry_snapshot': '', 'identity_registry_sha256': '',
            'author_evidence_snapshot': source['snapshot_path'], 'observed_on': review.get('reviewed_on', CUTOFF),
            'notes': review.get('notes', '') or f"Anchor: {stats['anchor_hits']} of {stats['anchor_works']} listed works."}
