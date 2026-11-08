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


def _resolve_v1(work, page1, page1_text):
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



def _space(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).split())


def _printed_suffix(quote, printed):
    text, name = _space(quote), _space(printed).casefold()
    for cut in range(1, len(text) + 1):
        prefix = text[:cut].casefold()
        if prefix == name:
            return text[cut:]
        if len(prefix) > len(name):
            break
    return None


def _box(box):
    return isinstance(box, list) and len(box) == 4 and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in box) and \
        0 <= box[0] < box[2] <= 2000 and 0 <= box[1] < box[3] <= 2000


def _overlap(box, boxes):
    return any(max(box[0], b[0]) < min(box[2], b[2]) and max(box[1], b[1]) < min(box[3], b[3]) for b in boxes)


def _pdf_name(raw, printed):
    """Literal spelling, or an explicit single comma's family/given formatting. No nicknames/fuzzy joins."""
    if not isinstance(printed, str) or not printed.strip():
        return False
    if _flat(raw) == _flat(printed):
        return True
    parts = str(raw).split(',')
    return len(parts) == 2 and all(p.strip() for p in parts) and _flat(parts[1] + ' ' + parts[0]) == _flat(printed)


def _words(text):
    return collections.Counter(re.findall(r'[^\W_]+', _flat(text), re.UNICODE))


def _email_contact(text):
    """A contact tail cannot hide an omitted affiliation group or author."""
    if not text:
        return True
    rest = re.sub(r'\{[^{}\s@]+\}@[\w.-]+\.\w+|[\w.+%~-]+@[\w.-]+\.\w+', '', text)
    return not re.search(r'\w', rest, re.UNICODE) and '@' in text


def _marker(marker):
    return isinstance(marker, str) and bool(re.fullmatch(r'[0-9]+|[^\s,;()0-9]', marker))


def _marker_tokens(suffix):
    return re.findall(r'[0-9]+|[^\s,;()]', suffix)


def _v2_prefix(prefix, title, header, printed_names):
    value = prefix.strip()
    value = re.sub(r'(?i)^published as (?:a )?(?:conference|journal) paper\b.*?\b(?:19|20)\d{2}\b\s*', '', value, count=1)
    split = re.split(r'(?i)(?:[.!⚠]\s*)?warning\s*:', value, maxsplit=1)
    if len(split) == 2:
        warning = split[1].strip()
        # The warning must be one actual source line, not a place to put omitted authors/affiliations.
        if not warning or '@' in warning or any(_flat(n) in _flat(warning) for n in printed_names) or not any(
                re.search(r'(?i)warning\s*:', line) and _flat(line).endswith(_flat(warning)) for line in header.splitlines()):
            return False
        value = split[0].strip()
    return bool(_name_key(title)) and _name_key(value) == _name_key(title)


def _v2_result(work, page1, review, authors):
    return dict(status='accepted', authors=copy.deepcopy(authors), evidence=dict(
        work=work['id'], doi=_doi(work.get('doi')), source_work_sha256=review['source_work_sha256'],
        source_authorships_sha256=review['source_authorships_sha256'], pdf_url=page1['url'], pdf_sha256=review['pdf_sha256'],
        page1_text_sha256=review['page1_text_sha256'], reviewed_by=review['reviewed_by'], reviewed_at=review['reviewed_at'],
        version=2, layout=review['layout'], author_blocks=copy.deepcopy(authors),
        affiliation_groups=copy.deepcopy(review.get('groups', [])), marker_notes=copy.deepcopy(review.get('notes', []))))


def _resolve_v2(work, page1, page1_text):
    review = page1['author_affiliation_review']
    def held(reason):
        return dict(status='held', reason=reason, work=work.get('id'))
    # The v1 source/PDF/edition/page1 bindings are retained in full.
    if not work.get('id') or review.get('work') != work['id'] or 'doi' not in review or _doi(review['doi']) != _doi(work.get('doi')):
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
    authors = work.get('authorships') or []; names = [raw_name(a) for a in authors]
    keys = [_name_key(n) for n in names]
    if not names or not all(keys) or len(set(keys)) != len(keys):
        return held('ambiguous_raw_byline')
    if review.get('byline_names') != names:
        return held('incomplete_or_changed_byline')
    if not review.get('reviewed_by') or not review.get('reviewed_at'):
        return held('missing_review_provenance')
    header = re.split(r'\babstract\b', page1_text, maxsplit=1, flags=re.I)[0]
    boxes, used = [], collections.Counter()
    def add_box(box):
        if not _box(box):
            return 'invalid_author_block_coordinates'
        if _overlap(box, boxes):
            return 'overlapping_author_blocks'
        boxes.append(box)
        return None
    if review.get('layout') == 'inline':
        blocks = review.get('blocks')
        if not isinstance(blocks, list) or len(blocks) != len(authors):
            return held('incomplete_or_changed_byline')
        for i, (a, block) in enumerate(zip(authors, blocks)):
            if not isinstance(block, dict) or block.get('index') != i or block.get('raw_name') != names[i] or block.get('author_id') != (a.get('author') or {}).get('id'):
                return held('wrong_author_block')
            printed = block.get('pdf_name'); text = block.get('block_text'); affs = block.get('affiliations')
            if not _pdf_name(names[i], printed):
                return held('unattested_name_format')
            if not isinstance(text, str) or not isinstance(affs, list) or not affs or not all(isinstance(s, str) and s.strip() for s in affs):
                return held('missing_author_affiliation_block')
            if _flat(printed) not in _flat(text) or _flat(text) not in _flat(header) or any(_flat(s) not in _flat(text) for s in affs):
                return held('block_quotes_not_on_page1')
            if _words(text) - _words(printed) - _words(' '.join(affs)):
                return held('incomplete_affiliation_statement')
            reason = add_box(block.get('bbox'))
            if reason:
                return held(reason)
            used.update(_words(text))
        if used - _words(header):
            return held('block_words_missing_from_author_header')
        return _v2_result(work, page1, review, blocks)
    if review.get('layout') != 'footnotes':
        return held('unsupported_review_layout')
    blocks, groups, notes = review.get('authors'), review.get('groups'), review.get('notes')
    if not isinstance(blocks, list) or len(blocks) != len(authors) or not isinstance(groups, list) or not groups or not isinstance(notes, list):
        return held('incomplete_shared_affiliation_review')
    by_id, by_marker, note_by_marker = {}, {}, {}
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get('id'), str) or not group['id'] or group['id'] in by_id:
            return held('ambiguous_affiliation_group')
        marker, text, quote = group.get('marker'), group.get('text'), group.get('quote')
        if not isinstance(marker, str) or (marker and not _marker(marker)) or marker in by_marker or not isinstance(text, str) or not text.strip() or not isinstance(quote, str):
            return held('ambiguous_affiliation_marker')
        flat_quote = _space(quote)
        if marker:
            match = re.match(r'[0-9]+|[^\s]', flat_quote)
            if not match or match[0] != marker or _flat(flat_quote[match.end():].strip()) != _flat(text):
                return held('affiliation_marker_quote_mismatch')
        elif _flat(flat_quote) != _flat(text):
            return held('affiliation_marker_quote_mismatch')
        if flat_quote not in _space(header):
            return held('affiliation_quote_not_in_header')
        reason = add_box(group.get('bbox'))
        if reason:
            return held(reason)
        by_id[group['id']] = group; by_marker[marker] = group['id']; used.update(_words(quote))
    for note in notes:
        if not isinstance(note, dict) or not _marker(note.get('marker')) or note['marker'] in by_marker or note['marker'] in note_by_marker:
            return held('contradictory_or_duplicate_marker_note')
        quote = note.get('quote')
        if not isinstance(quote, str) or not quote or _space(quote) not in _space(page1_text):
            return held('marker_note_not_on_page1')
        if note.get('kind') == 'equal_contribution':
            proved = _space(quote).startswith(note['marker']) and bool(re.search(r'(?i)\bequal(?:ly)?\b', quote)) and bool(re.search(r'(?i)\bcontribut', quote))
        elif note.get('kind') == 'correspondence':
            proved = (_space(quote).startswith(note['marker']) and bool(re.search(r'(?i)correspond', quote))) or (note.get('display_symbol') == 'envelope' and note.get('extraction_note') and note['marker'] in {'B', '✉'} and _email_contact(quote))
        else:
            proved = False
        if not proved:
            return held('unproven_non_affiliation_marker')
        reason = add_box(note.get('bbox'))
        if reason:
            return held(reason)
        note_by_marker[note['marker']] = note
    accepted, seen_groups, seen_notes, author_quotes, printed_names = [], set(), set(), [], []
    for i, (a, block) in enumerate(zip(authors, blocks)):
        if not isinstance(block, dict) or block.get('index') != i or block.get('raw_name') != names[i] or block.get('author_id') != (a.get('author') or {}).get('id'):
            return held('wrong_author_block')
        printed, quote, markers, gids = block.get('pdf_name'), block.get('quote'), block.get('markers'), block.get('affiliation_ids')
        if not _pdf_name(names[i], printed):
            return held('unattested_name_format')
        if not isinstance(quote, str) or _printed_suffix(quote, printed) is None or _space(quote) not in _space(header) or not isinstance(markers, list) or not all(_marker(m) for m in markers) or len(set(markers)) != len(markers):
            return held('invalid_author_marker_quote')
        suffix = _printed_suffix(quote, printed)
        if _marker_tokens(suffix) != markers:
            return held('unaccounted_author_markers')
        if any(m not in by_marker and m not in note_by_marker for m in markers):
            return held('undefined_author_marker')
        expected = [by_marker[m] for m in markers if m in by_marker]
        if not expected and '' in by_marker:
            expected = [by_marker['']]
        if not expected or not isinstance(gids, list) or gids != expected:
            return held('contradictory_affiliation_links')
        reason = add_box(block.get('bbox'))
        if reason:
            return held(reason)
        seen_groups.update(gids); seen_notes.update(m for m in markers if m in note_by_marker); used.update(_words(quote))
        author_quotes.append(quote); printed_names.append(printed)
        accepted.append(dict(block, affiliations=[by_id[g]['text'] for g in gids], block_text=quote))
    if seen_groups != set(by_id) or seen_notes != set(note_by_marker):
        return held('unused_affiliation_or_note_marker')
    for marker, note in note_by_marker.items():
        if note.get('display_symbol') == 'envelope' and sum(marker in b['markers'] for b in blocks) != 1:
            return held('ambiguous_correspondence_symbol')
    byline, region, contact, prefix = (review.get(k) for k in ('byline_quote', 'affiliation_region_quote', 'contact_quote', 'prefix_quote'))
    if not all(isinstance(s, str) for s in (byline, region, contact, prefix)) or _space(' '.join((prefix, byline, region, contact))) != _space(header):
        return held('incomplete_author_header_partition')
    tail = _space(byline)
    for quote in author_quotes:
        tail = tail.lstrip(' ,;')
        if not tail.startswith(_space(quote)):
            return held('incomplete_or_reordered_PDF_byline')
        tail = tail[len(_space(quote)):]
    if tail.strip(' ,;') or _space(region) != _space(' '.join(g['quote'] for g in groups)) or not _email_contact(contact):
        return held('unaccounted_header_or_affiliation_text')
    if not _v2_prefix(prefix, work.get('title'), header, printed_names):
        return held('unaccounted_header_prefix')
    if used - _words(header) or (used + sum((_words(n['quote']) for n in notes), collections.Counter())) - _words(page1_text):
        return held('block_words_missing_from_author_header')
    return _v2_result(work, page1, review, accepted)


def resolve(work, page1, page1_text):
    """Versioned explicit complete reviews. Unknown, incomplete or contradictory evidence never substitutes flags."""
    review = (page1 or {}).get('author_affiliation_review')
    if isinstance(review, dict) and type(review.get('version')) is int and review.get('version') == 2:
        return _resolve_v2(work, page1, page1_text)
    return _resolve_v1(work, page1, page1_text)

def school_flags(work, resolved, school_via):
    """Use the existing school/campus predicate on a derived view; None means retain existing source-derived flags."""
    if resolved.get('status') != 'accepted':
        return None
    effective = copy.deepcopy(work)
    for a, block in zip(effective['authorships'], resolved['authors']):
        a['institutions'] = []
        a['raw_affiliation_strings'] = list(block['affiliations'])
    return [raw_name(a) for a in effective['authorships'] if school_via(effective, a)]
