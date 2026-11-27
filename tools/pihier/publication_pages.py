"""Replay publisher page ranges when DBLP supplies only an article number.

An exact reviewed metadata fact changes page extent only. It grants no identity,
affiliation, appointment or publication-type exception.
"""
import datetime
import hashlib
import json
import re
from urllib.parse import unquote, urlsplit

import atlas_paths as P
from .common import ndoi


def normalized(value):
    return ' '.join(str(value or '').split()).casefold()


def extent(value):
    match = re.fullmatch(r'(\d+)[-–](\d+)', str(value))
    if not match or not 0 < int(match[1]) <= int(match[2]) < 100000:
        raise ValueError('invalid_publisher_page_range')
    return int(match[2]) - int(match[1]) + 1


def original(school, review):
    source = review['source']
    digest = source['sha256']
    url = urlsplit(source.get('url', ''))
    doi = ndoi(review['match']['doi'])
    if (source.get('http_status') != 200 or source.get('format') != 'crossref_json'
            or not re.fullmatch('[0-9a-f]{64}', digest)
            or source.get('source_file') != digest + '.json'
            or url.scheme != 'https' or url.netloc != 'api.crossref.org' or url.query or url.fragment
            or unquote(url.path).casefold() != '/works/' + doi):
        raise ValueError('invalid_publication_page_source')
    datetime.datetime.fromisoformat(source['captured'])
    path = P.school_part(school, 'raw') / 'publication-page-sources' / source['source_file']
    if not path.is_file() or path.stat().st_size > 2 << 20:
        raise ValueError('missing_publication_page_original')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('invalid_publication_page_original')
    doc = json.loads(raw)
    message = doc.get('message') or {}
    titles = message.get('title') or []
    parts = (message.get('published') or {}).get('date-parts') or []
    if (doc.get('status') != 'ok' or doc.get('message-type') != 'work'
            or ndoi(message.get('DOI')) != doi or len(titles) != 1
            or normalized(titles[0]) != normalized(review['title'])
            or not parts or not parts[0] or parts[0][0] != review['year']
            or message.get('page') != review['pages'] or not message.get('publisher')):
        raise ValueError('publication_page_wrong_article')
    return extent(message['page'])


def prepare(ctx):
    if hasattr(ctx, '_publication_page_reviews'):
        return ctx._publication_page_reviews
    path = P.data('publication-page-review.json', ctx.school, root=ctx.here)
    reviews = {}
    if path.exists():
        if path.stat().st_size > 5 << 20:
            raise ValueError('publication_page_review_too_large')
        doc = json.loads(path.read_text())
        if doc.get('version') != 1 or doc.get('school') != ctx.school or not isinstance(doc.get('decisions'), list):
            raise ValueError('invalid_publication_page_review')
        for decision in doc['decisions']:
            if (decision.get('decision') != 'confirm_publisher_page_range' or not decision.get('reviewed_by')
                    or not decision.get('why') or set(decision.get('match', {})) != {'oa', 'doi'}):
                raise ValueError('unreviewed_publication_page')
            datetime.date.fromisoformat(decision['reviewed_on'])
            key = decision['match']['oa']
            if not re.fullmatch(r'https://openalex.org/W\d+', key) or key in reviews:
                raise ValueError('duplicate_or_invalid_publication_page_selector')
            reviews[key] = dict(decision, count=original(ctx.school, decision))
    ctx._publication_page_reviews = reviews
    return reviews


def select(reviews, row):
    review = (reviews or {}).get(row.get('oa'))
    if review is None:
        return None
    if (ndoi(row.get('doi')) != ndoi(review['match']['doi'])
            or normalized(row.get('title')) != normalized(review['title'])
            or row.get('year') != review['year']):
        raise ValueError('publication_page_indexed_record_changed')
    return review['count']
