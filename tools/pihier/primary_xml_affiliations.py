"""Reviewed complete Europe PMC CORE author affiliations affect derived flags only.

This is bibliographic XML for a named MED record, not publisher JATS or a PDF.
Every raw observation must have an explicit, complete source-author mapping.
Repeated observations remain separate; this adapter never merges author IDs.
"""
import collections
import datetime
import hashlib
import json
import re
import sqlite3
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

TABLE = 'author_review_xml'
FORMAT = 'EPMC_CORE_bibliographic_XML'
LIMIT = 8 << 20
JSON_LIMIT = 2 << 20
APPROVAL_KEYS = {'version', 'decision', 'purpose', 'school', 'review_id', 'work', 'reviewed_by', 'reviewed_at',
                 'source_packet_sha256', 'source_replay_sha256', 'source_work_sha256',
                 'source_authorships_sha256', 'source_xml_sha256', 'metadata_sha256'}
METADATA_KEYS = {'source_format', 'source_url', 'source_id', 'raw_to_source_author', 'duplicate_raw_observations'}


def load(con):
    """Load only the dedicated reviewed table, preserving an absent table as None."""
    if not con.execute("select 1 from sqlite_master where type='table' and name=?", (TABLE,)).fetchone():
        return None
    records, errors, total = collections.defaultdict(list), [], 0
    try:
        rows = con.execute('''select substr(review_id,1,2001),substr(work,1,2001),
            substr(approval,1,?),substr(metadata,1,?),substr(document,1,?)
            from author_review_xml order by review_id,work limit 10001''',
                           (JSON_LIMIT + 1, JSON_LIMIT + 1, LIMIT + 1))
        for number, (rid, wid, approval, metadata, document) in enumerate(rows):
            total += sum(len(x) for x in (rid, wid, approval, metadata, document) if isinstance(x, (str, bytes)))
            if number == 10000 or total > 32 << 20:
                return {}, [dict(status='held', reason='author_xml_review_table_too_large', input_table=TABLE)]
            if any(not isinstance(x, str) or not x.strip() or len(x) > 2000 for x in (rid, wid)):
                errors.append(dict(status='held', reason='invalid_author_xml_selector', input_table=TABLE))
                continue
            records[wid].append(dict(review_id=rid, work=wid, approval=approval, metadata=metadata,
                                     document=document, source_format=FORMAT))
    except sqlite3.DatabaseError:
        return {}, [dict(status='held', reason='malformed_author_xml_table', input_table=TABLE)]
    return dict(records), errors


def _json(value):
    if not isinstance(value, str) or len(value.encode()) > JSON_LIMIT:
        raise ValueError('invalid XML review JSON')
    return json.loads(value)


def _document(value):
    if not isinstance(value, bytes) or len(value) > LIMIT:
        raise ValueError('invalid XML document')
    dec = zlib.decompressobj()
    body = dec.decompress(value, LIMIT + 1)
    if len(body) > LIMIT or not dec.eof or dec.unused_data or dec.unconsumed_tail:
        raise ValueError('invalid XML compression')
    text = body.decode('utf-8-sig')
    # CORE does not need a DTD. Reject declarations before parsing; no external
    # resources, entities, source URLs or processing instructions are executed.
    if '\x00' in text or re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', text, re.I):
        raise ValueError('XML declarations are not supported')
    return body, ET.fromstring(text)


def _text(node, path):
    found = node.findall(path)
    if len(found) != 1:
        raise ValueError('missing or ambiguous XML field')
    return ' '.join(''.join(found[0].itertext()).split())


def _key(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


def _title(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split()).rstrip('.')


def _doi(text):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(text or '').strip(), flags=re.I).casefold()


def _raw_matches(raw, given, family):
    if not isinstance(raw, str) or not raw.strip():
        return False
    # Structural family,given order is allowed. There is no initials, display
    # name, nearby-institution, author-ID or surname-only fallback.
    if ',' in raw:
        pair = raw.split(',')
        return len(pair) == 2 and _key(pair[0]) == _key(family) and _key(pair[1]) == _key(given)
    return _key(raw) == _key(given + family)


def _source_url(metadata):
    u = urllib.parse.urlsplit(metadata['source_url'])
    q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
    return (u.scheme == 'https' and u.netloc == 'www.ebi.ac.uk'
            and u.path == '/europepmc/webservices/rest/search' and not u.fragment
            and q == {'query': ['EXT_ID:'+metadata['source_id']+' AND SRC:MED'],
                      'resultType': ['core'], 'format': ['xml']})


def resolve(work, school, row):
    """Replay one independently approved CORE record, never ordinary admission."""
    from . import primary_affiliations as A

    def held(reason):
        return dict(status='held', reason=reason, work=work.get('id'), input_table=TABLE,
                    review_ids=[row.get('review_id')])

    try:
        approval, metadata = _json(row['approval']), _json(row['metadata'])
        if not isinstance(approval, dict) or set(approval) != APPROVAL_KEYS:
            return held('invalid_author_xml_approval')
        if (type(approval['version']) is not int or approval['version'] != 1
                or approval['decision'] != 'reviewed' or approval['purpose'] != A.AUTHOR_REVIEW_PURPOSE):
            return held('not_reviewed_for_derived_flags')
        if (approval['review_id'] != row['review_id'] or approval['work'] != row['work']
                or row['work'] != work.get('id') or approval['school'] != school):
            return held('wrong_author_xml_selector')
        if not isinstance(approval['reviewed_by'], str) or not approval['reviewed_by'].strip():
            return held('missing_author_xml_reviewer')
        if not isinstance(approval['reviewed_at'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', approval['reviewed_at']):
            return held('invalid_author_xml_date')
        datetime.date.fromisoformat(approval['reviewed_at'])
        if any(not re.fullmatch('[0-9a-f]{64}', str(approval[k])) for k in APPROVAL_KEYS if k.endswith('_sha256')):
            return held('invalid_author_xml_hash')
        if (approval['source_work_sha256'] != A.digest(work)
                or approval['source_authorships_sha256'] != A.digest(work.get('authorships') or [])):
            return held('author_xml_source_changed')
        if (not isinstance(metadata, dict) or set(metadata) != METADATA_KEYS
                or metadata['source_format'] != FORMAT or not isinstance(metadata['source_url'], str)
                or not isinstance(metadata['source_id'], str) or not metadata['source_id'].isdigit()
                or not _source_url(metadata)
                or approval['metadata_sha256'] != A.digest(metadata)):
            return held('invalid_author_xml_metadata')
        body, root = _document(row['document'])
        if approval['source_xml_sha256'] != hashlib.sha256(body).hexdigest():
            return held('author_xml_document_changed')
        results = root.findall('./resultList/result')
        if root.tag != 'responseWrapper' or len(results) != 1:
            return held('wrong_core_xml_envelope')
        record = results[0]
        if _text(record, 'source') != 'MED' or _text(record, 'id') != metadata['source_id']:
            return held('wrong_core_xml_record')
        if (_doi(_text(record, 'doi')) != _doi(work.get('doi'))
                or not work.get('doi') or _title(_text(record, 'title')) != _title(work.get('title') or '')
                or _text(record, 'pubYear') != str(work.get('publication_year'))):
            return held('wrong_core_xml_publication')
        source = record.findall('./authorList/author')
        raw = work.get('authorships') or []
        mapping = metadata['raw_to_source_author']
        if (not source or len(source) > 5000 or not raw or not isinstance(mapping, list)
                or len(mapping) != len(raw) or any(type(i) is not int or not 0 <= i < len(source) for i in mapping)
                or set(mapping) != set(range(len(source)))):
            return held('incomplete_author_xml_mapping')
        people, seen = [], set()
        for index, author in enumerate(source):
            given, family = _text(author, 'firstName'), _text(author, 'lastName')
            tokens = re.findall(r'[^\W\d_]+', given, re.UNICODE)
            if (not given or not family or not tokens or all(len(t) == 1 for t in tokens)
                    or given.isupper() and len(given) <= 3):
                return held('source_given_name_is_incomplete')
            name = _key(given + family)
            if name in seen:
                return held('ambiguous_source_author_name')
            seen.add(name)
            affiliations = author.findall('./authorAffiliationDetailsList/authorAffiliation/affiliation')
            affs = [' '.join(''.join(a.itertext()).split()) for a in affiliations]
            if not affs or len(affs) > 100 or not all(affs):
                return held('source_author_affiliation_missing')
            people.append(dict(index=index, given=given, family=family, affiliations=affs))
        by_source = collections.defaultdict(list)
        for i, target in enumerate(mapping):
            by_source[target].append(i)
        duplicates = [indices for _, indices in sorted(by_source.items()) if len(indices) > 1]
        if metadata['duplicate_raw_observations'] != duplicates:
            return held('undeclared_repeated_raw_observations')
        accepted = []
        for i, (author, target) in enumerate(zip(raw, mapping)):
            person = people[target]
            name = author.get('raw_author_name')
            if not _raw_matches(name, person['given'], person['family']):
                return held('raw_name_does_not_match_source_author')
            accepted.append(dict(index=i, raw_name=name, author_id=(author.get('author') or {}).get('id'),
                                 source_author_index=target, source_role='named_author',
                                 affiliations=person['affiliations']))
        return dict(status='accepted', authors=accepted, evidence=dict(
            work=work['id'], doi=_doi(work['doi']), input_table=TABLE, source_format=FORMAT,
            source_url=metadata['source_url'], source_id=metadata['source_id'],
            source_xml_sha256=approval['source_xml_sha256'], source_work_sha256=approval['source_work_sha256'],
            source_authorships_sha256=approval['source_authorships_sha256'], metadata_sha256=approval['metadata_sha256'],
            purpose=A.AUTHOR_REVIEW_PURPOSE, review_id=row['review_id'], approved_by=approval['reviewed_by'],
            approved_at=approval['reviewed_at'], approval_sha256=A.digest(approval),
            source_packet_sha256=approval['source_packet_sha256'], source_replay_sha256=approval['source_replay_sha256'],
            duplicate_raw_observations=duplicates, author_blocks=accepted))
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError, zlib.error,
            RecursionError, ET.ParseError):
        return held('malformed_author_xml_payload')
