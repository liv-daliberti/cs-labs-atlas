"""Replay reviewed JATS publication dates without altering indexed source records.

The exact work, DOI, title, former date and original article metadata must agree.
This supplies a date to the ordinary appointment check; it grants no authorship,
identity, affiliation, genre or appointment exception.
"""
import datetime
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import atlas_paths as P
from .common import ndoi

MAX_BYTES = 24 << 20


def text(node):
    return ' '.join(' '.join(node.itertext()).split()) if node is not None else ''


def normalized(value):
    return ' '.join(str(value or '').split()).casefold()


def original(school, review):
    source = review['source']
    digest = source['sha256']
    if (source.get('http_status') != 200 or source.get('format') != 'jats_xml'
            or not re.fullmatch('[0-9a-f]{64}', digest)
            or source.get('source_file') != digest + '.xml'
            or urlsplit(source.get('url', '')).scheme != 'https'):
        raise ValueError('invalid_publication_date_source')
    datetime.datetime.fromisoformat(source['captured'])
    path = P.store(school) / 'metadata/publication-date-sources' / source['source_file']
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('missing_publication_date_original')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest or b'<!ENTITY' in raw.upper():
        raise ValueError('invalid_publication_date_original')
    root = ET.fromstring(raw)
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    if root.tag != 'article':
        raise ValueError('publication_date_not_an_original_article')
    meta = root.find('./front/article-meta')
    if meta is None:
        raise ValueError('publication_date_article_metadata_missing')
    dois = {ndoi(text(n)) for n in meta.findall('article-id') if n.get('pub-id-type') == 'doi'}
    title = text(meta.find('./title-group/article-title'))
    if dois != {ndoi(review['match']['doi'])} or normalized(title) != normalized(review['title']):
        raise ValueError('publication_date_wrong_article')
    dates = set()
    for node in meta.findall('pub-date'):
        # History/acceptance, collection, issue-print and migration dates do not
        # substitute for an explicit electronic publication date.
        electronic = (node.get('pub-type') == 'epub' or
                      (node.get('publication-format') == 'electronic' and node.get('date-type') == 'pub'))
        if electronic:
            try:
                dates.add(datetime.date(*(int(text(node.find(k))) for k in ('year', 'month', 'day'))).isoformat())
            except (TypeError, ValueError) as error:
                raise ValueError('publication_date_not_day_precise') from error
    if dates != {review['date']}:
        raise ValueError('publication_date_not_attested')
    return dict(url=source['url'], sha256=digest, source_file=source['source_file'],
                captured=source['captured'], field='front/article-meta/pub-date[epub]')


def prepare(ctx):
    if hasattr(ctx, '_publication_date_reviews'):
        return ctx._publication_date_reviews
    path = P.data('publication-date-review.json', ctx.school, root=ctx.here)
    reviews = {}
    if path.exists():
        if path.stat().st_size > 5 << 20:
            raise ValueError('publication_date_review_too_large')
        doc = json.loads(path.read_text())
        if doc.get('version') != 1 or doc.get('school') != ctx.school or not isinstance(doc.get('decisions'), list):
            raise ValueError('invalid_publication_date_review')
        for decision in doc['decisions']:
            if (decision.get('decision') != 'correct_publication_date' or not decision.get('reviewed_by')
                    or not decision.get('why') or set(decision.get('match', {})) != {'oa', 'doi'}):
                raise ValueError('unreviewed_publication_date')
            datetime.date.fromisoformat(decision['reviewed_on'])
            for field in ('date', 'previous_date'):
                datetime.date.fromisoformat(decision[field])
            if decision['date'][:4] != decision['previous_date'][:4]:
                raise ValueError('publication_date_year_change_requires_review')
            if decision['date'] > datetime.date.today().isoformat():
                raise ValueError('future_publication_date')
            key = decision['match']['oa']
            if not re.fullmatch(r'https://openalex.org/W\d+', key) or key in reviews:
                raise ValueError('duplicate_or_invalid_publication_date_selector')
            reviews[key] = dict(decision, proof=original(ctx.school, decision))
    ctx._publication_date_reviews = reviews
    return reviews


def select(ctx, work):
    """Return a corrected date/proof only for the unchanged exact indexed work."""
    review = prepare(ctx).get(work.get('id'))
    if review is None:
        return None
    if (work.get('type') != 'article' or work.get('publication_year') != int(review['date'][:4])
            or ndoi(work.get('doi')) != ndoi(review['match']['doi'])
            or normalized(work.get('title')) != normalized(review['title'])
            or work.get('publication_date') != review['previous_date']):
        raise ValueError('publication_date_indexed_record_changed')
    return review['date'], dict(kind='reviewed_publisher_publication_date',
                               oa_date=review['previous_date'], source=review['proof'],
                               reviewed_by=review['reviewed_by'], reviewed_on=review['reviewed_on'])
