"""Exact, reviewed publisher records absent from bibliographic indexes.

A record owns no author cluster. Original captured bytes, literal metadata,
complete credited byline, faculty identity and the PI's own school evidence
are required. The ordinary appointment, genre and edition gates run afterward.
"""
import datetime
import hashlib
import json
import re
import subprocess
import zlib
from pathlib import Path

from bs4 import BeautifulSoup

import atlas_paths as P
import school_config as S
from .common import excluded_school_only, ndoi
from .names import Name, literal_cjk_name, toks

MAX_BYTES = 24 << 20


def normalize(text):
    return ' '.join(str(text or '').split())


def capture(source, cache):
    """Rehash original bytes and replay their declared text extraction offline."""
    url, sha = source['url'], source['sha256']
    if not str(url).startswith(('https://', 'http://')) or not re.fullmatch('[0-9a-f]{64}', str(sha)):
        raise ValueError('invalid_capture_reference')
    path = Path(source['source_file'])
    key = (str(path), sha, source['format'])
    if key not in cache:
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError('missing_or_oversized_original_capture')
        raw = path.read_bytes()
        if not raw or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('original_capture_changed')
        if raw.startswith(b'\x1f\x8b'):
            decoder = zlib.decompressobj(31)
            raw = decoder.decompress(raw, MAX_BYTES + 1)
            if len(raw) > MAX_BYTES or not decoder.eof or decoder.unused_data:
                raise ValueError('invalid_compressed_original_capture')
        if source['format'] == 'html':
            soup = BeautifulSoup(raw, 'html.parser')
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            text = soup.get_text(' ', strip=True)
        elif source['format'] == 'pdf' and raw.startswith(b'%PDF'):
            text = subprocess.check_output(['pdftotext', '-raw', str(path), '-'], timeout=90, text=True)
        else:
            raise ValueError('unsupported_original_capture_format')
        text = normalize(text)
        if any(v in text for v in ['Verify you are human', 'Security Verification', 'Just a moment...']):
            raise ValueError('access_challenge')
        cache[key] = text
    return cache[key]


def quote(source, field, cache):
    value = normalize(field)
    if not value or value not in capture(source, cache):
        raise ValueError('literal_source_quote_missing')
    return value


def full_name(name, p):
    if not Name(p.get('names') or [p['pi']]).match(name):
        return False
    han = literal_cjk_name(name)
    return bool(han and len(han) >= 2) or (len(toks(name)) >= 2 and all(len(t) > 1 for t in toks(name)))


def own_school(school, affiliation):
    # The charter already spells out native-script school names for faculty
    # periods. Reuse only those literal names, not its looser Latin abbreviations.
    native = re.findall(r'[㐀-鿿]{2,}', S.field(S.get(school), 'periods.school_regex') or '')
    return bool(re.search(S.aff(school), affiliation, re.I) or any(n in affiliation for n in native))


def project(ctx, review, cache):
    if review.get('decision') != 'reviewed_primary_publication' or not review.get('reviewed_by') or not review.get('why'):
        raise ValueError('missing_explicit_source_review')
    datetime.date.fromisoformat(review['reviewed_on'])
    p = ctx.pid0[review['pi']]
    if p.get('identityHold'):
        raise ValueError('pi_identity_held')
    pub, own, school = review['publication'], review['ownership'], review['school_authorship']
    source = pub['source']
    title = quote(source, pub['title_quote'], cache)
    if normalize(pub['title']) != title:
        raise ValueError('publisher_title_mismatch')
    byline = pub['byline']
    byline_quote = quote(source, pub['byline_quote'], cache)
    if (pub.get('complete_credited_byline') is not True or not isinstance(byline, list) or not byline
            or any(not isinstance(n, str) or not n.strip() or n not in byline_quote for n in byline)
            or len(set(byline)) != len(byline)):
        raise ValueError('complete_credited_byline_unproven')
    name = own['name']
    if name not in byline or not full_name(name, p):
        raise ValueError('pi_full_byline_name_unproven')
    if own.get('basis') not in {'institutional_publication_list', 'literal_faculty_and_primary_authorship'}:
        raise ValueError('unsupported_identity_basis')
    identity_quote = quote(own['source'], own['quote'], cache)
    if not any(n in identity_quote for n in p.get('names') or [p['pi']]):
        raise ValueError('named_faculty_identity_unproven')
    if own['basis'] == 'institutional_publication_list':
        if title not in identity_quote:
            raise ValueError('personally_owned_title_unproven')
    elif not re.search(r'教授|讲师|研究员|\b(?:professor|lecturer|faculty)\b', identity_quote, re.I):
        raise ValueError('named_faculty_identity_unproven')
    if school['source']['sha256'] != source['sha256']:
        raise ValueError('school_proof_not_this_publisher_record')
    school_quote = quote(school['source'], school['quote'], cache)
    affiliation = school['affiliation']
    if (school['name'] != name or name not in school_quote or affiliation not in school_quote
            or not own_school(ctx.school, affiliation)
            or excluded_school_only(dict(raw_affiliation_strings=[affiliation], institutions=[]), ctx.school)):
        raise ValueError('pi_own_school_authorship_unproven')
    if school.get('assignment') == 'all_authors_single_affiliation':
        if any(n not in school_quote for n in byline) or school.get('single_affiliation_reviewed') is not True:
            raise ValueError('shared_affiliation_assignment_unproven')
    elif school.get('assignment') != 'individual_author_block' or any(n != name and n in school_quote for n in byline):
        raise ValueError('ambiguous_author_affiliation_block')
    date = str(pub['date'])
    if not re.fullmatch(r'\d{4}(?:-\d{2}-\d{2})?', date) or type(pub['year']) is not int or int(date[:4]) != pub['year']:
        raise ValueError('invalid_publication_date')
    if len(date) == 10:
        datetime.date.fromisoformat(date)
    date_quote = quote(source, pub['publication_quote'], cache)
    label = pub.get('publication_date_label')
    if label not in {'出版日期', '出版时间', '发布日期', 'Published', 'Publication date'}:
        raise ValueError('publication_date_not_attested')
    if not re.fullmatch(re.escape(label) + r'\s*[:：]?\s*' + re.escape(date), date_quote, re.I):
        raise ValueError('publication_date_not_attested')
    if pub['type'] not in {'article', 'conference-paper', 'book', 'book-chapter', 'preprint'}:
        raise ValueError('unsupported_publication_kind')
    quote(source, pub['kind_quote'], cache)
    venue = quote(source, pub['venue_quote'], cache)
    if pub['venue'] not in venue:
        raise ValueError('publisher_venue_unproven')
    identifier = quote(source, pub['identifier_quote'], cache)
    doi = ndoi(pub.get('doi'))
    isbn = re.sub(r'[^0-9X]', '', str(pub.get('isbn') or ''))
    if doi and doi not in identifier.lower():
        raise ValueError('publication_doi_not_attested')
    if pub['type'] == 'book':
        if len(isbn) != 13 or sum(int(v) * (1 if i % 2 == 0 else 3) for i, v in enumerate(isbn)) % 10:
            raise ValueError('invalid_book_isbn')
        if isbn not in re.sub(r'[^0-9X]', '', identifier):
            raise ValueError('book_isbn_not_attested')
    elif not doi or doi not in identifier.lower():
        raise ValueError('publication_doi_not_attested')
    # A real source identifier, never a fabricated provider record or a lab-page citation.
    key = 'publisher:' + hashlib.sha1((('doi:' + doi) if doi else ('isbn:' + isbn)).encode()).hexdigest()
    return dict(pi=p['pi'], key=key, title=pub['title'], year=pub['year'], date=date, doi=doi, type=pub['type'],
                venue=pub['venue'], byline=list(byline), evidence=dict(basis='reviewed_primary_publisher', url=source['url'],
                sha256=source['sha256'], school_via=['primary publisher [' + source['sha256'] + ']: ' + school_quote],
                review_id=review['id'], quotes=[school_quote]))


def rows(ctx):
    path = P.data('publisher-publications.json', ctx.school, root=ctx.here)
    if not path.exists():
        return []
    if path.stat().st_size > 5 << 20:
        raise ValueError('publisher publication reviews exceed 5 MB')
    data = json.loads(path.read_text())
    if data.get('version') != 1 or data.get('school') != ctx.school or not isinstance(data.get('publications'), list):
        raise ValueError('publisher reviews require version 1, school and publications')
    out, cache, ids = [], {}, set()
    for review in data['publications']:
        rid = review.get('id')
        if not isinstance(rid, str) or not rid or rid in ids:
            raise ValueError('publisher reviews require unique IDs')
        ids.add(rid)
        try:
            row = project(ctx, review, cache)
        except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError) as exc:
            ctx.n['publisher_review_held:' + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__)] += 1
            continue
        out.append(row)
    return out
