"""Complete primary-PDF author blocks may correct derived byline flags, never paper admission or raw records."""
import copy
import collections
import hashlib
import json
import math
import re
import unicodedata
import zlib


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def raw_name(authorship):
    return authorship.get('raw_author_name') or (authorship.get('author') or {}).get('display_name') or ''


def _flat(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).split()).casefold()


def _name_key(value):
    return ''.join(c for c in _flat(value) if c.isalnum())


def _doi(value):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(value or '').strip(), flags=re.I).casefold()


def resolve(work, page1, page1_text):
    """Accepted complete mapping or an explicit hold; a hold never substitutes partial/nearby authors' flags."""
    review = (page1 or {}).get('author_affiliation_review')
    if review is None:
        return dict(status='not_requested')
    def held(reason):
        return dict(status='held', reason=reason, work=work.get('id'))
    if not isinstance(review, dict) or review.get('version') != 1:
        return held('invalid_review')
    if not work.get('id') or review.get('work') != work.get('id') or 'doi' not in review or _doi(review['doi']) != _doi(work.get('doi')):
        return held('wrong_work_or_edition')
    try:
        if review.get('source_work_sha256') != digest(work) or review.get('source_authorships_sha256') != digest(work.get('authorships') or []):
            return held('source_work_changed')
    except (TypeError, ValueError):
        return held('unhashable_source_work')
    pdf_sha = page1.get('pdf_sha256') or ''
    if not re.fullmatch('[0-9a-f]{64}', pdf_sha) or review.get('pdf_sha256') != pdf_sha or review.get('pdf_url') != page1.get('url'):
        return held('wrong_PDF_source')
    try:
        if isinstance(page1_text, bytes):
            page1_text = zlib.decompress(page1_text).decode('utf-8')
        if not isinstance(page1_text, str) or hashlib.sha256(page1_text.encode()).hexdigest() != review.get('page1_text_sha256'):
            return held('page1_text_changed')
    except (UnicodeError, zlib.error):
        return held('page1_text_unreadable')
    authors = work.get('authorships') or []
    names = [raw_name(a) for a in authors]
    keys = [_name_key(n) for n in names]
    if not names or not all(keys) or len(set(keys)) != len(keys):
        return held('ambiguous_raw_byline')
    blocks = review.get('blocks')
    if review.get('byline_names') != names or not isinstance(blocks, list) or len(blocks) != len(names):
        return held('incomplete_or_changed_byline')
    if not review.get('reviewed_by') or not review.get('reviewed_at'):
        return held('missing_review_provenance')
    accepted, boxes = [], []
    header = re.split(r'\babstract\b', page1_text, maxsplit=1, flags=re.I)[0]
    words = lambda text: collections.Counter(re.findall(r'[^\W_]+', _flat(text), re.UNICODE))
    used_words = collections.Counter()
    for i, (a, block) in enumerate(zip(authors, blocks)):
        if not isinstance(block, dict) or block.get('index') != i or block.get('raw_name') != names[i] \
                or block.get('author_id') != (a.get('author') or {}).get('id'):
            return held('wrong_author_block')
        text = block.get('block_text') or ''; affiliations = block.get('affiliations')
        if not isinstance(text, str) or not isinstance(affiliations, list) or not affiliations \
                or not all(isinstance(s, str) and s.strip() for s in affiliations):
            return held('missing_author_affiliation_block')
        if _flat(names[i]) not in _flat(text) or _flat(names[i]) not in _flat(header) \
                or any(_flat(s) not in _flat(text) for s in affiliations):
            return held('block_quotes_not_on_page1')
        if words(text) - words(names[i]) - words(' '.join(affiliations)):
            return held('incomplete_affiliation_statement')
        used_words.update(words(text))
        box = block.get('bbox')
        if not isinstance(box, list) or len(box) != 4 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in box) \
                or not (0 <= box[0] < box[2] <= 2000 and 0 <= box[1] < box[3] <= 2000):
            return held('invalid_author_block_coordinates')
        if any(max(box[0], b[0]) < min(box[2], b[2]) and max(box[1], b[1]) < min(box[3], b[3]) for b in boxes):
            return held('overlapping_author_blocks')
        boxes.append(box); accepted.append(copy.deepcopy(block))
    if used_words - words(header):
        return held('block_words_missing_from_author_header')
    return dict(status='accepted', authors=accepted,
                evidence=dict(work=work['id'], doi=_doi(work.get('doi')), source_work_sha256=review['source_work_sha256'],
                              source_authorships_sha256=review['source_authorships_sha256'], pdf_url=page1['url'], pdf_sha256=pdf_sha,
                              page1_text_sha256=review['page1_text_sha256'], reviewed_by=review['reviewed_by'], reviewed_at=review['reviewed_at'],
                              author_blocks=accepted))


def school_flags(work, resolved, school_via):
    """Use the existing school/campus predicate on a derived view; None means retain existing source-derived flags."""
    if resolved.get('status') != 'accepted':
        return None
    effective = copy.deepcopy(work)
    for a, block in zip(effective['authorships'], resolved['authors']):
        a['institutions'] = []
        a['raw_affiliation_strings'] = list(block['affiliations'])
    return [raw_name(a) for a in effective['authorships'] if school_via(effective, a)]
