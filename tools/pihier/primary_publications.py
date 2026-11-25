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
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

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
        if any(v in text for v in ['Verify you are human', 'Security Verification', 'Just a moment...', '安全验证', '完成安全验证后继续访问']):
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


def linked_frontmatter(publication, school, cache):
    """The exact TUP edition's own linked author biography/preface, never a related book."""
    if publication['type'] != 'book' or publication['source']['format'] != 'html':
        return False
    source, target = publication['source'], school['source']
    edition = re.search(r'/book_(\d+)\.html$', urlsplit(source['url']).path, re.I)
    page = urlsplit(target['url'])
    if (not edition or page.hostname != urlsplit(source['url']).hostname
            or not re.search(r'/book(?:authorbrief|preface)$', page.path, re.I)
            or parse_qs(page.query).get('id') != [edition[1]]):
        return False
    capture(source, cache)
    soup = BeautifulSoup(Path(source['source_file']).read_bytes(), 'html.parser')
    return target['url'] in {urljoin(source['url'], a['href']) for a in soup.select('a[href]')}


def publication_date(pub, cache):
    """Keep original issue years when a reviewed, linked printed article proves them.

    A website's upload/migration timestamp is never a substitute publication year.
    The optional issue mode needs the complete own-article citation and its actual
    linked PDF, with matching printed title, authors, volume, issue and year.
    It yields year precision only; ordinary appointment/window gates still run.
    """
    date = str(pub['date'])
    if not re.fullmatch(r'\d{4}(?:-\d{2}-\d{2})?', date) or type(pub['year']) is not int or int(date[:4]) != pub['year']:
        raise ValueError('invalid_publication_date')
    if len(date) == 10:
        datetime.date.fromisoformat(date)
    source = pub['source']
    date_quote = quote(source, pub['publication_quote'], cache)
    basis = pub.get('publication_date_basis', 'explicit_publication_label')
    if basis == 'arxiv_first_submission':
        page = urlsplit(source['url'])
        identifier = re.fullmatch(r'/abs/(\d{4}\.\d{4,5})(?:v1)?', page.path)
        if (page.scheme != 'https' or page.hostname != 'arxiv.org' or page.query or page.fragment
                or not identifier or pub['type'] != 'preprint'
                or ndoi(pub.get('doi')) != '10.48550/arxiv.' + identifier[1]):
            raise ValueError('invalid_arxiv_submission_source')
        submitted = datetime.date.fromisoformat(date)
        expected = f'Submitted on {submitted.day} {submitted.strftime("%b %Y")}'
        text = capture(source, cache)
        if (date_quote != expected or f'[v1] {submitted.strftime("%a")}, {submitted.day} '
                + submitted.strftime('%b %Y') not in text):
            raise ValueError('arxiv_first_submission_unproven')
        return date
    if basis == 'explicit_publication_label':
        label = pub.get('publication_date_label')
        if label not in {'出版日期', '出版时间', '发布日期', 'Published', 'Publication date'}:
            raise ValueError('publication_date_not_attested')
        if not re.fullmatch(re.escape(label) + r'\s*[:：]?\s*' + re.escape(date), date_quote, re.I):
            raise ValueError('publication_date_not_attested')
        return date
    if basis != 'publisher_issue_citation' or pub['type'] != 'article' or date != str(pub['year']):
        raise ValueError('publication_date_not_attested')
    issue = pub['issue_date_review']
    volume, number, pages = (str(issue[k]) for k in ('volume', 'issue', 'pages'))
    if (issue.get('decision') != 'confirmed_original_issue' or not issue.get('why')
            or not re.fullmatch(r'[1-9]\d*', volume) or not re.fullmatch(r'[1-9]\d*', number)
            or not re.fullmatch(r'[1-9]\d*-[1-9]\d*', pages)
            or int(pages.split('-')[0]) > int(pages.split('-')[1])):
        raise ValueError('original_issue_unproven')
    authors = r'\s*[,，]\s*'.join(re.escape(n) for n in pub['byline'])
    citation = (authors + r'\.\s*' + re.escape(pub['title']) + r'\s*\[J\]\.\s*'
                + re.escape(pub['venue']) + r',\s*' + date + r',\s*' + volume + r'\(' + number
                + r'\):\s*' + re.escape(pages) + r'\.\s*https?://doi\.org/' + re.escape(ndoi(pub['doi'])))
    if not re.fullmatch(citation, date_quote, re.I):
        raise ValueError('own_article_issue_citation_unproven')
    printed = issue['source']
    if (source['format'] != 'html' or printed['format'] != 'pdf'
            or urlsplit(printed['url']).hostname != urlsplit(source['url']).hostname):
        raise ValueError('original_issue_pdf_not_linked')
    soup = BeautifulSoup(Path(source['source_file']).read_bytes(), 'html.parser')
    if printed['url'] not in {urljoin(source['url'], a['href']) for a in soup.select('a[href]')}:
        raise ValueError('original_issue_pdf_not_linked')
    printed_text = capture(printed, cache)
    header = quote(printed, issue['printed_issue_quote'], cache)
    if not printed_text.startswith(header):
        raise ValueError('printed_issue_header_unproven')
    compact = lambda value: re.sub(r'\s+', '', unicodedata.normalize('NFKC', value))
    head = compact(header)
    chinese = f'第{volume}卷第{number}期{date}年'
    english = rf'Vol\.?{volume}No\.?{number}(?:Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)?{date}(?![0-9])'
    if not (head.startswith(chinese) or re.match(english, head, re.I)):
        raise ValueError('printed_issue_header_unproven')
    first = compact(printed_text[:2500])
    if compact(pub['title']) not in first or any(compact(name) not in first for name in pub['byline']):
        raise ValueError('printed_issue_other_article')
    return date


def linked_arxiv(publication, school, cache):
    """The original abstract links the same version's HTML with its author affiliations."""
    source, target = publication['source'], school['source']
    page, full = urlsplit(source['url']), urlsplit(target['url'])
    identifier = re.fullmatch(r'/abs/(\d{4}\.\d{4,5})(?:v1)?', page.path)
    if (publication.get('publication_date_basis') != 'arxiv_first_submission'
            or publication['type'] != 'preprint' or not identifier
            or page.scheme != 'https' or page.hostname != 'arxiv.org' or page.query or page.fragment
            or full.scheme != 'https' or full.hostname != 'arxiv.org' or full.query or full.fragment
            or full.path != '/html/' + identifier[1] + 'v1'
            or source['format'] != 'html' or target['format'] != 'html'):
        return False
    capture(source, cache)
    text = capture(target, cache)
    soup = BeautifulSoup(Path(source['source_file']).read_bytes(), 'html.parser')
    return (target['url'] in {urljoin(source['url'], a['href']) for a in soup.select('a[href]')}
            and normalize(publication['title']) in text
            and all(name in text for name in publication['byline'])
            and 'arXiv:' + identifier[1] + 'v1' in text)


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
    if (school['source']['sha256'] != source['sha256']
            and not linked_frontmatter(pub, school, cache) and not linked_arxiv(pub, school, cache)):
        raise ValueError('school_proof_not_this_publisher_record')
    school_quote = quote(school['source'], school['quote'], cache)
    affiliation = school['affiliation']
    if re.search(r'出版社|出版公司|\b(?:press|publishing)\b', affiliation, re.I):
        raise ValueError('publisher_imprint_is_not_author_affiliation')
    if (school['name'] != name or name not in school_quote or affiliation not in school_quote
            or not own_school(ctx.school, affiliation)
            or excluded_school_only(dict(raw_affiliation_strings=[affiliation], institutions=[]), ctx.school)):
        raise ValueError('pi_own_school_authorship_unproven')
    if school.get('assignment') == 'all_authors_single_affiliation':
        if any(n not in school_quote for n in byline) or school.get('single_affiliation_reviewed') is not True:
            raise ValueError('shared_affiliation_assignment_unproven')
    elif school.get('assignment') != 'individual_author_block' or any(n != name and n in school_quote for n in byline):
        raise ValueError('ambiguous_author_affiliation_block')
    date = publication_date(pub, cache)
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
    return dict(pi=p['pi'], key=key, title=pub['title'], year=pub['year'], date=date, doi=doi or None, type=pub['type'],
                venue=pub['venue'], byline=list(byline), evidence=dict(basis='reviewed_primary_publisher', url=source['url'],
                sha256=source['sha256'], school_via=['primary publisher [' + school['source']['sha256'] + '] '
                            + school['source']['url'] + ': ' + school_quote],
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
