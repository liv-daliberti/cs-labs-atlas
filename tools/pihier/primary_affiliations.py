"""Complete primary-author records may correct derived byline flags, never paper admission or raw records."""
import copy
import collections
import datetime
import hashlib
import json
import math
import re
import sqlite3
import unicodedata
import zlib

AUTHOR_REVIEW_TABLE = 'author_review_pages'
AUTHOR_REVIEW_PURPOSE = 'derived_author_affiliation_flags_only'
_REVIEW_LIMIT = 2 << 20
_APPROVAL_KEYS = {'version', 'decision', 'purpose', 'school', 'review_id', 'work', 'reviewed_by', 'reviewed_at',
                  'source_packet_sha256', 'source_replay_sha256', 'source_work_sha256', 'source_authorships_sha256',
                  'metadata_sha256', 'page1_text_sha256', 'pdf_sha256', 'pdf_url'}


def _load_pdf_author_review_pages(con):
    """Read only the explicitly reviewed table, NEVER proposals or ordinary works/pages.

    None means an absent table and exact legacy behavior. The caller keeps this
    snapshot separate from admission metadata. Invalid selectors/table structure
    become input diagnostics; scoped malformed payloads are held when consulted.
    """
    if not con.execute("select 1 from sqlite_master where type='table' and name=?", (AUTHOR_REVIEW_TABLE,)).fetchone():
        return None
    records, errors, total = collections.defaultdict(list), [], 0
    try:
        rows = con.execute('''select substr(review_id,1,2001),substr(work,1,2001),
            substr(approval,1,?),substr(metadata,1,?),substr(page1,1,?)
            from author_review_pages order by review_id,work limit 10001''', (_REVIEW_LIMIT + 1,) * 3)
        for number, row in enumerate(rows):
            if number == 10000:
                return {}, [dict(status='held', reason='author_review_table_too_large', input_table=AUTHOR_REVIEW_TABLE)]
            rid, wid, approval, metadata, page1 = row
            total += sum(len(x) for x in row if isinstance(x, (str, bytes)))
            if total > 32 << 20:
                return {}, [dict(status='held', reason='author_review_table_too_large', input_table=AUTHOR_REVIEW_TABLE)]
            if (not isinstance(wid, str) or not wid.strip() or len(wid) > 2000
                    or not isinstance(rid, str) or not rid.strip() or len(rid) > 2000):
                errors.append(dict(status='held', reason='invalid_author_review_selector', input_table=AUTHOR_REVIEW_TABLE))
                continue
            records[wid].append(dict(review_id=rid, work=wid, approval=approval, metadata=metadata, page1=page1))
    except sqlite3.DatabaseError:
        return {}, [dict(status='held', reason='malformed_author_review_table', input_table=AUTHOR_REVIEW_TABLE)]
    return dict(records), errors


def load_author_review_pages(con):
    """Keep typed PDF and XML reviews separate from admission and raw sources."""
    from . import primary_xml_affiliations as X
    pdf, xml = _load_pdf_author_review_pages(con), X.load(con)
    if pdf is None:
        return xml
    if xml is None:
        return pdf
    records = {k: list(v) for k, v in pdf[0].items()}
    for work, rows in xml[0].items():
        records.setdefault(work, []).extend(rows)
    return records, pdf[1] + xml[1]


def _review_json(value):
    if not isinstance(value, str) or len(value.encode()) > _REVIEW_LIMIT:
        raise ValueError('invalid or oversized review JSON')
    return json.loads(value)


def _review_text(value):
    if not isinstance(value, bytes) or len(value) > _REVIEW_LIMIT:
        raise ValueError('invalid or oversized review text')
    dec = zlib.decompressobj()
    body = dec.decompress(value, _REVIEW_LIMIT + 1)
    if len(body) > _REVIEW_LIMIT or not dec.eof or dec.unused_data or dec.unconsumed_tail:
        raise ValueError('invalid or oversized decompressed review text')
    return body.decode('utf-8')


def author_review_signature(records):
    """Cache only this exact read-only row snapshot, including compressed text bytes."""
    return digest([{k: ['bytes', hashlib.sha256(v).hexdigest()] if isinstance(v, bytes) else ['json', v]
                    for k, v in row.items()} for row in records])


def resolve_author_review(work, school, records):
    """One approved source-bound flag review, with no identity/eligibility authority."""
    def held(reason):
        return dict(status='held', reason=reason, work=work.get('id'), input_table=AUTHOR_REVIEW_TABLE,
                    review_ids=[r.get('review_id') for r in records])
    if len(records) != 1:
        return held('competing_author_review_records')
    row = records[0]
    if row.get('source_format') == 'EPMC_CORE_bibliographic_XML':
        from . import primary_xml_affiliations as X
        return X.resolve(work, school, row)
    try:
        approval = _review_json(row['approval'])
        if not isinstance(approval, dict) or set(approval) != _APPROVAL_KEYS:
            return held('invalid_author_review_approval')
        if (type(approval['version']) is not int or approval['version'] != 1
                or approval['decision'] != 'reviewed' or approval['purpose'] != AUTHOR_REVIEW_PURPOSE):
            return held('not_explicitly_reviewed_for_derived_flags')
        if (approval['review_id'] != row['review_id'] or approval['work'] != row['work']
                or row['work'] != work.get('id') or approval['school'] != school):
            return held('wrong_author_review_selector')
        if not isinstance(approval['reviewed_by'], str) or not approval['reviewed_by'].strip():
            return held('missing_author_review_reviewer')
        if not isinstance(approval['reviewed_at'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', approval['reviewed_at']):
            return held('invalid_author_review_date')
        datetime.date.fromisoformat(approval['reviewed_at'])
        if any(not re.fullmatch('[0-9a-f]{64}', str(approval[k])) for k in _APPROVAL_KEYS if k.endswith('_sha256')):
            return held('invalid_author_review_hash')
        if (approval['source_work_sha256'] != digest(work)
                or approval['source_authorships_sha256'] != digest(work.get('authorships') or [])):
            return held('author_review_source_changed')
        metadata, text = _review_json(row['metadata']), _review_text(row['page1'])
        if not isinstance(metadata, dict) or set(metadata) != {'url', 'pdf_sha256', 'author_affiliation_review'}:
            return held('author_review_contains_unexpected_metadata')
        review = metadata['author_affiliation_review']
        if not isinstance(review, dict) or type(review.get('version')) is not int or review['version'] not in (1, 2):
            return held('invalid_complete_author_review')
        if (approval['metadata_sha256'] != digest(metadata)
                or approval['page1_text_sha256'] != hashlib.sha256(text.encode()).hexdigest()
                or approval['pdf_sha256'] != metadata.get('pdf_sha256') or approval['pdf_url'] != metadata.get('url')):
            return held('author_review_payload_changed')
        result = resolve(work, metadata, text)
        if result.get('status') != 'accepted':
            if result.get('status') != 'held':
                return held('missing_complete_author_review')
            result.update(input_table=AUTHOR_REVIEW_TABLE, review_ids=[row['review_id']])
            return result
        result['evidence'].update(input_table=AUTHOR_REVIEW_TABLE, purpose=AUTHOR_REVIEW_PURPOSE,
                                  approval_sha256=digest(approval), review_id=row['review_id'],
                                  approved_by=approval['reviewed_by'], approved_at=approval['reviewed_at'],
                                  source_packet_sha256=approval['source_packet_sha256'],
                                  source_replay_sha256=approval['source_replay_sha256'])
        return result
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError, zlib.error, RecursionError):
        return held('malformed_author_review_payload')


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
    text = re.sub(r'(?i)^\s*Correspondence\s+to\s+', '', text)
    rest = re.sub(r'\{\s*[\w.+%~-]+(?:\s*,\s*[\w.+%~-]+)*\s*\}@[\w.-]+\.\w+|[\w.+%~-]+@[\w.-]+\.\w+', '', text)
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
        affiliation_groups=copy.deepcopy(review.get('groups', [])), marker_notes=copy.deepcopy(review.get('notes', [])),
        unresolved_markers=copy.deepcopy(review.get('unresolved_markers', []))))


def _unexplained_markers(review, blocks, by_marker, notes, page1_text):
    """Account for an unexplained repeated asterisk without inventing its meaning.

    Every affected author must also have an explicit affiliation marker. Every
    original-page occurrence must be in those author quotes; a footnote or group
    using the symbol therefore prevents this narrowly bounded treatment.
    """
    rows = review.get('unresolved_markers', [])
    if not isinstance(rows, list):
        return None
    markers = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'marker', 'meaning', 'author_indices'}:
            return None
        marker, indices = row['marker'], row['author_indices']
        if (marker not in {'*', '∗'} or marker in markers or marker in by_marker
                or marker in notes or row['meaning'] != 'unexplained_in_original'
                or not isinstance(indices, list) or len(indices) < 2
                or any(type(i) is not int for i in indices)):
            return None
        actual = [i for i, block in enumerate(blocks) if isinstance(block, dict)
                  and marker in (block.get('markers') or [])]
        if indices != actual or any(not any(m in by_marker for m in blocks[i]['markers']) for i in indices):
            return None
        quotes = [blocks[i].get('quote') for i in indices]
        if (not all(isinstance(q, str) and q.count(marker) == 1 for q in quotes)
                or page1_text.count(marker) != len(indices)):
            return None
        markers.add(marker)
    if markers:
        # The same printed asterisk can extract as ASCII in a footnote and
        # U+2217 in the byline. Account for both forms before accepting either.
        quoted = [b.get('quote', '') for b in blocks if isinstance(b, dict)
                  and any(m in markers for m in b.get('markers', []))]
        if sum(page1_text.count(m) for m in ('*', '∗')) != sum(q.count(m) for q in quoted for m in ('*', '∗')):
            return None
    return markers


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
    # Some originals print an unlabeled abstract. A reviewed literal full prose
    # paragraph may bound the header; it cannot hide an affiliation or byline.
    if 'header_end_quote' in review or 'header_end_bbox' in review:
        quote, box = review.get('header_end_quote'), review.get('header_end_bbox')
        prose = re.findall(r'[^\W\d_]+', quote, re.UNICODE) if isinstance(quote, str) else []
        if (re.search(r'\babstract\b', page1_text, re.I)
                or not isinstance(quote, str) or len(quote) < 100 or len(prose) < 20
                or not quote.rstrip().endswith(('.', '!', '?'))
                or sum(w[0].islower() for w in prose) < len(prose) / 2
                or re.search(r'(?i)\b(?:university|institute|department|laboratory|correspondence)\b|@', quote)
                or page1_text.count(quote) != 1 or not _box(box)):
            return held('invalid_unlabeled_body_boundary')
        offset = page1_text.index(quote)
        if offset == 0 or page1_text[offset - 1] != '\n':
            return held('invalid_unlabeled_body_boundary')
        header = page1_text[:offset]
        boxes.append(box)

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
        elif note.get('kind') == 'author_contribution':
            proved = bool(re.fullmatch(re.escape(note['marker']) +
                                      r'\s*(?:Co[- ]first authors|Second authors|Equal advising|Joint last authors)\.?',
                                      _space(quote), re.I))
        elif note.get('kind') == 'correspondence':
            proved = (_space(quote).startswith(note['marker']) and bool(re.search(r'(?i)correspond', quote))) or (note.get('display_symbol') == 'envelope' and note.get('extraction_note') and note['marker'] in {'B', '✉'} and _email_contact(quote))
        elif note.get('kind') == 'work_during_internship':
            # This note may repeat an affiliation already assigned in the header;
            # it cannot introduce a new institution or supply an author's group.
            group_id = note.get('affiliation_id')
            group = by_id.get(group_id) if isinstance(group_id, str) else None
            printed_marker = note.get('pdf_marker', note['marker'])
            literal_marker = printed_marker == note['marker']
            # Some PDF fonts extract the same asterisk as U+2217 in the
            # byline and ASCII in its footnote. Keep both literal readings;
            # an explicit review may join only this otherwise unused pair.
            if not literal_marker:
                literal_marker = (isinstance(printed_marker, str)
                                  and {printed_marker, note['marker']} == {'*', '∗'}
                                  and isinstance(note.get('extraction_note'), str)
                                  and bool(note['extraction_note'].strip())
                                  and printed_marker not in by_marker
                                  and not any(n.get('marker') == printed_marker for n in notes))
            match = re.fullmatch(re.escape(printed_marker) +
                                 r'\s*Work done while the author was interning at (.+)\.',
                                 _space(quote), re.I) if isinstance(printed_marker, str) else None
            proved = bool(literal_marker and group and match and _flat(match[1]) == _flat(group['text']))
        else:
            proved = False
        if not proved:
            return held('unproven_non_affiliation_marker')
        reason = add_box(note.get('bbox'))
        if reason:
            return held(reason)
        note_by_marker[note['marker']] = note
    unresolved = _unexplained_markers(review, blocks, by_marker, note_by_marker, page1_text)
    if unresolved is None:
        return held('unproven_unexplained_author_marker')
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
        if any(m not in by_marker and m not in note_by_marker and m not in unresolved for m in markers):
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
        if note.get('kind') == 'work_during_internship':
            named = [b for b in blocks if marker in b['markers']]
            if len(named) != 1 or note['affiliation_id'] not in named[0]['affiliation_ids']:
                return held('internship_note_not_assigned_to_existing_author_affiliation')
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
    contact_tail = _space(contact)
    for note in notes:
        if note.get('kind') in {'equal_contribution', 'author_contribution'}:
            contact_tail = contact_tail.replace(_space(note['quote']), '', 1).strip()
    if tail.strip(' ,;') or _space(region) != _space(' '.join(g['quote'] for g in groups)) or not _email_contact(contact_tail):
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
