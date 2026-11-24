"""Replay an original publisher issue date when an index uses platform creation.

This changes an eligible hit's date only. Identity, school, appointment, genre
and edition checks still run; the original index work is never edited.
"""
import datetime
import hashlib
import re
import sqlite3
import zlib
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import pymupdf

import atlas_paths as P
from . import source_metadata as M
from .common import ndoi, norm_title
from .names import Name

LIMIT = 24 << 20


def validate(review):
    changes = review.get('changes') or {}
    if set(changes) != {'publication_date'}:
        raise ValueError('publisher date review changes only publication_date')
    datetime.date.fromisoformat(changes['publication_date'])
    for proof in [review.get('source') or {}, review.get('publisher') or {}, review.get('pdf') or {}]:
        field = 'work_sha256' if 'work_sha256' in proof else 'sha256'
        if not re.fullmatch('[0-9a-f]{64}', str(proof.get(field))):
            raise ValueError('publisher date needs exact original source hashes')
    if not review.get('why') or not review.get('independent_reviewer'):
        raise ValueError('publisher date needs an independent source review')


def original(ctx, proof):
    """Fixed registered cache, bounded decompression, and exact original bytes."""
    url = proof['url']
    if urlsplit(url).scheme not in {'http', 'https'}:
        raise ValueError('invalid publisher source URL')
    path = P.data('school-captures.sqlite', ctx.school, root=ctx.here)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        row = db.execute('select status,sha256,raw_zlib from live where url=?', (url,)).fetchone()
    if not row or row[0] != 200 or row[1] != proof['sha256'] or not row[2]:
        raise ValueError('missing publisher original')
    dec = zlib.decompressobj(); raw = dec.decompress(row[2], LIMIT + 1)
    if len(raw) > LIMIT or not dec.eof or dec.unconsumed_tail or dec.unused_data:
        raise ValueError('invalid publisher original body')
    if hashlib.sha256(raw).hexdigest() != proof['sha256']:
        raise ValueError('changed publisher original')
    return raw


def _names_match(a, b):
    return (isinstance(a, list) and isinstance(b, list) and bool(a) and len(a) == len(b)
            and all(isinstance(x, str) and isinstance(y, str) and Name([x]).match(y) for x, y in zip(a, b)))


def check(ctx, pi, work, review):
    proof, publisher, printed = (review[k] for k in ('source', 'publisher', 'pdf'))
    date = review['changes']['publication_date']; year = int(date[:4]); selector = review['match']
    names = M._source_names(work)
    if (selector['oa'] != work.get('id') or ndoi(selector['doi']) != ndoi(work.get('doi'))
            or M.digest(work) != proof['work_sha256'] or names != proof.get('ordered_byline')
            or work.get('publication_date') != proof.get('original_publication_date')
            or work.get('title') != proof.get('original_title')):
        raise ValueError('publisher date source preimage mismatch')
    p = ctx.pid0[pi]; db = review['owned_dblp']
    if db['pid'] not in p.get('dblp', []) or p.get('identityHold'):
        raise ValueError('publisher date has no owned publication record')
    person = ctx.dblp_persons.get('persons', {}).get(db['pid'], {})
    pubs = [r for r in person.get('pubs', []) if r.get('key') == db['key']]
    if len(pubs) != 1 or M.digest(pubs[0]) != db['record_sha256']:
        raise ValueError('publisher date owned record changed')
    pub = pubs[0]
    if (pub.get('type') not in {'article', 'inproceedings'} or pub.get('year') != year
            or norm_title(pub.get('title')) != norm_title(work['title'])
            or not _names_match([a[0] for a in pub.get('authors', [])], names)
            or (pub.get('dois') and ndoi(work['doi']) not in {ndoi(v) for v in pub['dois']})):
        raise ValueError('publisher date owned edition mismatch')
    soup = BeautifulSoup(original(ctx, publisher), 'html.parser')
    meta = {}
    for tag in soup.select('meta[name][content]'):
        meta.setdefault(tag['name'].casefold(), []).append(tag['content'].strip())
    def single(key):
        values = meta.get(key.casefold(), [])
        if len(values) != 1:
            raise ValueError('missing or ambiguous publisher metadata')
        return values[0]
    if (single('DC.Date.issued') != date or single('DC.Date.created') != work['publication_date']
            or single('citation_date') != str(year) or date >= work['publication_date']
            or norm_title(single('citation_title')) != norm_title(work['title'])
            or ndoi(single('citation_doi')) != ndoi(work['doi'])
            or not _names_match(meta.get('citation_author'), names)
            or single('citation_pdf_url') != printed['url']
            or urlsplit(printed['url']).hostname != urlsplit(publisher['url']).hostname
            or (work.get('primary_location') or {}).get('pdf_url') != printed['url']):
        raise ValueError('publisher issue and creation dates or article binding disagree')
    raw = original(ctx, printed)
    if not raw.startswith(b'%PDF'):
        raise ValueError('printed original is not a PDF')
    with pymupdf.open(stream=raw, filetype='pdf') as doc:
        page = doc[0]
        text = ' '.join(page.get_text().split())
        # PDF stream order can put the physical running header after the body.
        # Read its actual top-of-page region instead of rewriting extracted text.
        top = ' '.join(page.get_text(clip=pymupdf.Rect(0, 0, page.rect.width,
                                                     min(100, page.rect.height / 5))).split())
    header = ' '.join(printed['printed_issue_quote'].split())
    if (not header or header not in top or not re.search(r'\b' + str(year) + r'\b', header)
            or not re.search(r'(?i)proceedings|conference|journal|vol(?:ume)?\b', header)
            or norm_title(work['title']) not in norm_title(text[:3000])
            or not _names_match(printed.get('printed_names'), names)
            or any(' '.join(n.split()) not in text[:3000] for n in printed['printed_names'])):
        raise ValueError('printed original issue, title or byline not proved')
    return date


def resolve(ctx, pi, work, ordinary_date, ordinary_basis):
    reviews = [d for d in M.prepare(ctx) if d.get('decision') == 'publisher_issued_date'
               and d['pi'] == pi and d['match']['oa'] == work.get('id')]
    if not reviews:
        return ordinary_date, ordinary_basis
    review = reviews[0]
    try:
        if len(reviews) != 1 or ordinary_date != work.get('publication_date') or ordinary_basis:
            raise ValueError('competing ordinary date authority')
        date = check(ctx, pi, work, review)
        result = dict(status='projected', publication_date=date)
    except (KeyError, TypeError, ValueError, OSError, sqlite3.Error, zlib.error) as error:
        result = dict(status='held', reason=str(error))
    ctx.paper_source_review['decisions'].append(dict(id=review['id'], pi=pi, oa=work['id'],
        source_work_sha256=M.digest(work), original_publication_date=ordinary_date, **result))
    if result['status'] == 'held':
        raise ValueError(f"publisher date review {review['id']} requires renewed proof: {result['reason']}")
    return date, dict(oa_date=ordinary_date, venue_year=int(date[:4]),
                      dblp_key=review['owned_dblp']['key'], publisher_date_review=review['id'],
                      publisher_sha256=review['publisher']['sha256'], printed_pdf_sha256=review['pdf']['sha256'])
