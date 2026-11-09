"""Exact source-bound title or type projections on complete eligible originals, before edition identity."""
import copy
import datetime
import hashlib
import json
import re
import sqlite3
import zlib
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

import atlas_paths as P
from .common import ndoi
from .names import Name, byline_name, names_full_form

LIMIT = 5 << 20


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _title(value):
    return ' '.join(str(value or '').split()).rstrip('.').casefold()


def prepare(ctx):
    if hasattr(ctx, '_source_metadata_reviews'):
        return ctx._source_metadata_reviews
    path = P.data('paper-source-review.json', ctx.school, root=ctx.here)
    if not path.exists():
        ctx._source_metadata_reviews = []
        return []
    if path.stat().st_size > LIMIT:
        raise ValueError('paper source review exceeds 5 MB')
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('school') != ctx.school or not isinstance(data.get('reviews'), list):
        raise ValueError('paper source review needs version 1, this school and reviews')
    ids, selectors = set(), set()
    for d in data['reviews']:
        if not isinstance(d, dict) or not d.get('id') or d['id'] in ids or not d.get('pi'):
            raise ValueError('paper source reviews need unique ID and exact PI')
        if d.get('decision') == 'source_type':
            _prepare_type(d)
        elif d.get('decision') != 'owned_publication_title' or not isinstance(d.get('changes'), dict) or set(d['changes']) != {'title'}:
            raise ValueError('paper source review supports explicit title-only projections')
        m = d.get('match') or {}
        if not m.get('oa') or not ndoi(m.get('doi')):
            raise ValueError('paper source review requires exact OA and DOI selectors')
        selector = (d['pi'], m['oa'], ndoi(m['doi']))
        if selector in selectors:
            raise ValueError('competing paper source reviews')
        selectors.add(selector); ids.add(d['id'])
        datetime.date.fromisoformat(d['reviewed_at'])
        if not d.get('reviewed_by'):
            raise ValueError('paper source review requires reviewer')
    ctx._source_metadata_reviews = data['reviews']
    ctx.paper_source_review = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), decisions=[])
    return ctx._source_metadata_reviews


def _check(ctx, row, source, d, date_check):
    m, proof, db = d['match'], d.get('source') or {}, d.get('owned_dblp') or {}
    if ndoi(m['doi']) != ndoi(row.get('doi')) or any(k in m and m[k] != row.get(k) for k in ('oa', 'work')):
        return 'selector_mismatch'
    if not source or source.get('id') != row.get('oa') or ndoi(source.get('doi')) != ndoi(m['doi']):
        return 'missing_complete_source'
    if digest(source) != proof.get('work_sha256'):
        return 'source_preimage_changed'
    old = source.get('title')
    if not isinstance(old, str) or not old.strip() or old != proof.get('original_title') or row.get('title') != old:
        return 'original_nonempty_title_mismatch'
    authors = [(a.get('raw_author_name') or (a.get('author') or {}).get('display_name')) for a in source.get('authorships') or []]
    if not authors or authors != proof.get('ordered_byline') or authors != row.get('byline'):
        return 'source_ordered_byline_changed'
    p = ctx.pid0.get(row['pi']) or {}
    if p.get('identityHold') or row.get('identity') in (None, '', 'candidate', 'unverified') or not row.get('appointment'):
        return 'not_eligible_identity_or_appointment'
    if db.get('pid') not in (p.get('dblp') or []):
        return 'not_owned_pid'
    person = ((getattr(ctx, 'dblp_persons', {}) or {}).get('persons') or {}).get(db['pid']) or {}
    records = [r for r in person.get('pubs') or [] if r.get('key') == db.get('key')]
    if len(records) != 1 or digest(records[0]) != db.get('record_sha256'):
        return 'owned_publication_preimage_changed'
    record = records[0]
    if ndoi(m['doi']) not in {ndoi(v) for v in record.get('dois') or []}:
        return 'owned_publication_doi_mismatch'
    if record.get('type') not in {'inproceedings', 'article', 'incollection', 'book'}:
        return 'unsupported_owned_publication_kind'
    proposed = d['changes']['title']
    if not isinstance(proposed, str) or not proposed.strip() or _title(proposed) != _title(record.get('title')):
        return 'owned_publication_title_mismatch'
    old_title, full_title = _title(old), _title(proposed)
    if not full_title.startswith(old_title) or len(full_title) <= len(old_title) or full_title[len(old_title)].isalnum():
        return 'not_a_title_completion'
    byline = record.get('authors') or []
    if len(byline) != len(authors) or any(not isinstance(a, (list, tuple)) or not a or not isinstance(a[0], str) for a in byline):
        return 'owned_ordered_byline_mismatch'
    if any(not Name([a[0]]).match(byline_name(raw)) for a, raw in zip(byline, authors)):
        return 'owned_ordered_byline_mismatch'
    # Bibliographic kind/year is not authority to manufacture a publisher date or widen the appointment.
    if date_check(source, proposed, row) != row.get('date'):
        return 'would_change_ordinary_date'
    return None


def apply(ctx, rows, date_check):
    """Project eligible row copies only; preserve complete original work+row in report, then ordinary quality runs."""
    reviews = prepare(ctx)
    if not reviews:
        return rows
    wanted = {(d['pi'], d['match']['oa']) for d in reviews}
    for d in reviews:
        if d.get('decision') == 'source_type' and d['authority']['kind'] == 'owned_monograph_chapter':
            wanted.add((d['pi'], d['authority']['book']['oa']))
    eligible = {}
    for row in rows:
        eligible.setdefault((row['pi'], row.get('oa')), []).append(row)
    sources = {}
    for pi, work, *_ in getattr(ctx, 'hits', []):
        if (pi, work['id']) in wanted:
            sources.setdefault((pi, work['id']), {})[digest(work)] = work
    output, seen = [], set()
    for row in rows:
        candidates = [d for d in reviews if (d['pi'], d['match']['oa']) == (row['pi'], row.get('oa'))]
        if not candidates:
            output.append(row); continue
        exact = [d for d in candidates if ndoi(d['match']['doi']) == ndoi(row.get('doi'))]
        d = exact[0] if len(exact) == 1 else candidates[0]
        seen.add(d['id'])
        source = sources.get((row['pi'], row['oa']), {}).get((d.get('source') or {}).get('work_sha256'))
        typed = d.get('decision') == 'source_type'
        reason = (_check_type(ctx, row, source, d, date_check, sources, eligible) if typed
                  else _check(ctx, row, source, d, date_check))
        status = 'held' if reason else 'projected'
        decision = dict(id=d['id'], pi=row['pi'], oa=row['oa'], doi=row.get('doi'), status=status,
                        reason=reason, source_work_sha256=(d.get('source') or {}).get('work_sha256'),
                        owned_dblp=copy.deepcopy(d.get('owned_dblp')), original_eligible_row=copy.deepcopy(row),
                        original_complete_source=copy.deepcopy(source),
                        available_complete_sources=copy.deepcopy(list(sources.get((row['pi'], row['oa']), {}).values())),
                        **({'proposed_type': d['changes']['type'], 'authority': copy.deepcopy(d['authority'])} if typed
                           else {'proposed_title': d['changes']['title']}))
        if typed and d['authority']['kind'] == 'owned_monograph_chapter':
            key = (row['pi'], d['authority']['book']['oa'])
            decision['available_complete_book_sources'] = copy.deepcopy(list(sources.get(key, {}).values()))
            decision['available_eligible_book_rows'] = copy.deepcopy(eligible.get(key, []))
        ctx.paper_source_review['decisions'].append(decision)
        ctx.n['source_metadata_' + status] += 1
        if reason:
            # A positive corrective selector identifies a known unsafe original.
            # Keeping that row would silently restore the very merge being repaired.
            # Preserve diagnostics and all available originals, then stop before grouping.
            raise ValueError(f"source metadata review {d['id']} requires renewed proof for "
                             f"{row['pi']} / {row['oa']}: {reason}")
        if typed:
            result = dict(row, type=d['changes']['type'])
            marker = dict(id=d['id'], input_sha256=ctx.paper_source_review['sha256'],
                          source_work_sha256=d['source']['work_sha256'], review_kind='source_type',
                          eligible_row_sha256=d['source']['eligible_row_sha256'], original_type=row['type'],
                          type=result['type'], authority=copy.deepcopy(d['authority']))
            result['sourceMetadataReviews'] = list(row.get('sourceMetadataReviews') or []) + [marker]
            output.append(result)
            continue
        result = dict(row, title=d['changes']['title'])
        result['sourceMetadataReviews'] = list(row.get('sourceMetadataReviews') or []) + [dict(
            id=d['id'], input_sha256=ctx.paper_source_review['sha256'], source_work_sha256=d['source']['work_sha256'],
            owned_dblp_pid=d['owned_dblp']['pid'], owned_dblp_key=d['owned_dblp']['key'],
            owned_publication_sha256=d['owned_dblp']['record_sha256'], original_title=row['title'], title=result['title'])]
        output.append(result)
    for d in reviews:
        if d['id'] not in seen:
            ctx.paper_source_review['decisions'].append(dict(id=d['id'], pi=d['pi'], oa=d['match']['oa'],
                doi=d['match']['doi'], status='no_eligible_source', reason='not_present_after_ordinary_identity_school_appointment_gates'))
    return output


def _hash(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-f]{64}', value))


def _source_names(source):
    return [(a.get('raw_author_name') or (a.get('author') or {}).get('display_name'))
            for a in source.get('authorships') or []]


def _variant_proof(proof):
    values = proof.get('available_work_sha256s')
    return (isinstance(values, list) and bool(values) and all(_hash(v) for v in values)
            and len(values) == len(set(values)))


def _prepare_type(d):
    """Two finite authorities; never accept source paths, dates or author-list changes."""
    if d.get('changes') not in ({'type': 'book-chapter'}, {'type': 'article'}):
        raise ValueError('source type review supports type-only book-chapter/article changes')
    p = d.get('source') or {}
    if (not _hash(p.get('work_sha256')) or not _hash(p.get('eligible_row_sha256')) or not _variant_proof(p)
            or not isinstance(p.get('original_type'), str) or not p['original_type']
            or not isinstance(p.get('ordered_byline'), list) or not p['ordered_byline']
            or not all(isinstance(n, str) and n.strip() for n in p['ordered_byline'])):
        raise ValueError('source type review needs complete source/eligible row/variant/byline preimages')
    a = d.get('authority') or {}
    if a.get('kind') == 'owned_monograph_chapter':
        if set(a) != {'kind', 'book', 'chapter_doi', 'container_title'} or d['changes']['type'] != 'book-chapter':
            raise ValueError('monograph type authority fields changed')
        book = a.get('book') or {}
        if (set(book) != {'oa', 'doi', 'work_sha256', 'eligible_row_sha256', 'available_work_sha256s', 'owned_dblp'}
                or not book.get('oa') or not ndoi(book.get('doi')) or not ndoi(a.get('chapter_doi'))
                or not isinstance(a.get('container_title'), str) or not a['container_title'].strip()
                or not _hash(book.get('work_sha256')) or not _hash(book.get('eligible_row_sha256'))
                or not _variant_proof(book)):
            raise ValueError('monograph needs exact complete book authority')
        db = book.get('owned_dblp') or {}
        if (set(db) != {'pid', 'key', 'record_sha256'} or not db.get('pid') or not db.get('key')
                or not _hash(db.get('record_sha256'))):
            raise ValueError('monograph needs exact owned publication preimage')
    elif a.get('kind') == 'owned_primary_journal_article':
        if set(a) != {'kind', 'homepage', 'publication'} or d['changes']['type'] != 'article':
            raise ValueError('primary article authority fields changed')
        home, pub = a.get('homepage') or {}, a.get('publication') or {}
        if (set(home) != {'url', 'sha256', 'name_quote', 'role_quote', 'publication_href'}
                or set(pub) != {'url', 'sha256', 'citation_quote', 'journal', 'label', 'paper_href', 'paper_label'}
                or not all(isinstance(v, str) and v.strip() for v in [*home.values(), *pub.values()])
                or not _hash(home.get('sha256')) or not _hash(pub.get('sha256'))
                or pub['paper_label'].casefold() not in {'paper', 'full paper', 'article', 'full article'}):
            raise ValueError('primary article needs finite actual ownership/citation preimages')
    else:
        raise ValueError('unsupported source type authority')


def _owned_book(ctx, pi, source, binding):
    db = binding.get('owned_dblp') or {}
    if db.get('pid') not in (ctx.pid0[pi].get('dblp') or []):
        return 'not_owned_book_pid'
    person = ((getattr(ctx, 'dblp_persons', {}) or {}).get('persons') or {}).get(db['pid']) or {}
    pubs = [p for p in person.get('pubs') or [] if p.get('key') == db.get('key')]
    if len(pubs) != 1 or digest(pubs[0]) != db.get('record_sha256'):
        return 'owned_book_publication_preimage_changed'
    p = pubs[0]
    short, full = _title(source.get('title')), _title(p.get('title'))
    title_bound = full == short or (full.startswith(short) and len(full) > len(short)
                                   and not full[len(short)].isalnum())
    if (p.get('type') != 'book' or p.get('year') != source.get('publication_year')
            or ndoi(source.get('doi')) not in {ndoi(d) for d in p.get('dois') or []}
            or not title_bound):
        return 'owned_book_publication_mismatch'
    authors, names = p.get('authors') or [], _source_names(source)
    if (len(authors) != len(names) or any(not isinstance(a, (list, tuple)) or not a or not isinstance(a[0], str)
                                       for a in authors)
            or any(not Name([a[0]]).match(byline_name(n)) for a, n in zip(authors, names))):
        return 'owned_book_ordered_byline_mismatch'
    return None


def _monograph_type(ctx, row, source, d, sources, eligible):
    a = d['authority']; b = a['book']; key = (row['pi'], b['oa'])
    variants = sources.get(key, {})
    book = variants.get(b['work_sha256'])
    rows = [r for r in eligible.get(key, []) if digest(r) == b['eligible_row_sha256']]
    if not book or len(rows) != 1 or sorted(variants) != sorted(b['available_work_sha256s']):
        return 'missing_or_changed_complete_eligible_book'
    br = rows[0]; location = source.get('primary_location') or {}
    if br.get('identity') in (None, '', 'candidate', 'unverified') or not br.get('appointment'):
        return 'book_not_independently_eligible'
    if (book.get('id') != b['oa'] or ndoi(book.get('doi')) != ndoi(b['doi']) or br.get('oa') != b['oa']
            or ndoi(br.get('doi')) != ndoi(b['doi']) or book.get('type') != 'book' or br.get('type') != 'book'
            or _source_names(book) != br.get('byline') or _source_names(source) != _source_names(book)
            or source.get('publication_year') != book.get('publication_year') or row.get('year') != br.get('year')):
        return 'monograph_source_or_ordered_byline_mismatch'
    if (ndoi(a['chapter_doi']) != ndoi(source.get('doi'))
            or not re.fullmatch(re.escape(ndoi(b['doi'])) + r'_[1-9][0-9]*', ndoi(a['chapter_doi']))
            or location.get('raw_type') != 'book-chapter'
            or (location.get('source') or {}).get('type') not in {'ebook platform', 'book'}
            or _title(location.get('raw_source_name')) != _title(a['container_title'])
            or _title(a['container_title']) != _title(book.get('title'))):
        return 'exact_monograph_container_mismatch'
    return _owned_book(ctx, row['pi'], book, b)


def _inflate(blob, wbits=zlib.MAX_WBITS):
    stream = zlib.decompressobj(wbits)
    raw = stream.decompress(blob, LIMIT + 1)
    if len(raw) > LIMIT or stream.unconsumed_tail or not stream.eof:
        raise ValueError('primary source body exceeds finite bound or is incomplete')
    return raw


def _cached_primary(ctx, url, expected):
    """Only the registered school cache and fixed live table; no reviewer filesystem paths."""
    path = P.data('school-captures.sqlite', ctx.school, root=ctx.here)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as cache:
        row = cache.execute('SELECT status,sha256,raw_zlib FROM live WHERE url=?', (url,)).fetchone()
    if not row or row[0] != 200 or row[1] != expected or not row[2]:
        raise ValueError('missing primary body preimage')
    raw = _inflate(row[2])
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('changed primary body bytes')
    if raw.startswith(b'\x1f\x8b'):
        raw = _inflate(raw, 31)
    soup = BeautifulSoup(raw.decode('utf-8-sig'), 'html.parser')
    for node in soup(['script', 'style']):
        node.decompose()
    return soup


def _origin(url):
    p = urlsplit(url)
    if p.scheme not in {'http', 'https'} or not p.netloc or p.username or p.password or p.query or p.fragment:
        return None
    return p.scheme, p.netloc


def _ordered_literal_names(text, names):
    offset = 0
    for name in names:
        match = re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text[offset:], re.I)
        if not match:
            return False
        offset += match.end()
    return True


def _primary_article_type(ctx, row, source, d):
    a = d['authority']; home, pub = a['homepage'], a['publication']; p = ctx.pid0[row['pi']]
    lab = p.get('lab') or {}; e = lab.get('evidence') or {}; location = source.get('primary_location') or {}
    if not isinstance(e, dict):
        return 'primary_owner_binding_mismatch'
    if (home['url'] != lab.get('url') or home['url'] != e.get('url') or home['sha256'] != e.get('sha256')
            or home['role_quote'] != e.get('quote') or not names_full_form(home['name_quote'], p.get('names') or [])
            or not _origin(home['url']) or _origin(home['url']) != _origin(pub['url'])
            or urljoin(home['url'], home['publication_href']) != pub['url']):
        return 'primary_owner_binding_mismatch'
    if (location.get('provenance') != 'crossref' or location.get('raw_type') != 'journal-article'
            or (location.get('source') or {}).get('type') != 'journal'
            or ndoi(location.get('doi')) != ndoi(row.get('doi'))
            or _title(location.get('raw_source_name')) != _title(pub['journal'])):
        return 'primary_journal_source_kind_mismatch'
    try:
        hs = _cached_primary(ctx, home['url'], home['sha256'])
        ps = _cached_primary(ctx, pub['url'], pub['sha256'])
    except (OSError, sqlite3.Error, ValueError, UnicodeError, zlib.error):
        return 'primary_original_bytes_missing_or_changed'
    text = ' '.join(hs.get_text(' ', strip=True).split())
    if (home['name_quote'] not in text or home['role_quote'] not in text
            or not any(a.get('href') == home['publication_href'] for a in hs.select('a[href]'))):
        return 'primary_owner_literal_chain_missing'
    matches = [li for li in ps.select('li') if ' '.join(li.get_text(' ', strip=True).split()) == pub['citation_quote']]
    if len(matches) != 1:
        return 'primary_exact_citation_missing_or_ambiguous'
    li = matches[0]; quote = pub['citation_quote']; doi = ndoi(row.get('doi'))
    if (str(row.get('title') or '') not in quote or pub['journal'] not in quote or pub['label'] not in quote
            or not re.search(re.escape(doi) + r'(?![a-z0-9./_()-])', quote, re.I)
            or not _ordered_literal_names(quote, d['source']['ordered_byline'])
            or not any(a.get('href') == pub['paper_href'] and a.get_text(' ', strip=True) == pub['paper_label']
                       for a in li.select('a[href]'))):
        return 'primary_complete_research_citation_mismatch'
    return None


def _check_type(ctx, row, source, d, date_check, sources, eligible):
    m, proof = d['match'], d['source']
    if ndoi(m['doi']) != ndoi(row.get('doi')) or any(k in m and m[k] != row.get(k) for k in ('oa', 'work')):
        return 'selector_mismatch'
    if not source or source.get('id') != row.get('oa') or ndoi(source.get('doi')) != ndoi(m['doi']):
        return 'missing_complete_source'
    if (digest(source) != proof['work_sha256'] or digest(row) != proof['eligible_row_sha256']
            or sorted(sources.get((row['pi'], row['oa']), {})) != sorted(proof['available_work_sha256s'])):
        return 'source_or_eligible_row_or_variants_changed'
    if (source.get('type') != proof['original_type'] or row.get('type') != proof['original_type']
            or _source_names(source) != proof['ordered_byline'] or row.get('byline') != proof['ordered_byline']
            or row.get('type') == d['changes']['type']):
        return 'source_type_or_ordered_byline_mismatch'
    p = ctx.pid0.get(row['pi']) or {}
    if p.get('identityHold') or row.get('identity') in (None, '', 'candidate', 'unverified') or not row.get('appointment'):
        return 'not_eligible_identity_or_appointment'
    if date_check(source, row['title'], row) != row.get('date'):
        return 'would_change_ordinary_date'
    if d['authority']['kind'] == 'owned_monograph_chapter':
        b = d['authority']['book']; bs = sources.get((row['pi'], b['oa']), {}).get(b['work_sha256'])
        brs = [r for r in eligible.get((row['pi'], b['oa']), []) if digest(r) == b['eligible_row_sha256']]
        if bs and len(brs) == 1 and date_check(bs, brs[0]['title'], brs[0]) != brs[0].get('date'):
            return 'would_change_ordinary_book_date'
        return _monograph_type(ctx, row, source, d, sources, eligible)
    return _primary_article_type(ctx, row, source, d)
