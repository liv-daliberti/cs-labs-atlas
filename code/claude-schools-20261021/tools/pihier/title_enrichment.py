"""Reviewed missing titles enrich eligible output only; never identity, dates or edition joins."""
import copy
import datetime
import hashlib
import html
import json
import re
import unicodedata

import atlas_paths as P
from .common import ndoi


def preimage_sha256(work):
    """Canonical JSON of the complete unmodified native source work, before enrichment."""
    return hashlib.sha256(json.dumps(work, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def missing(title):
    return title is None or isinstance(title, str) and not title.strip()


def _title(value):
    return ' '.join(html.unescape(str(value or '')).split()).rstrip('.').casefold()


def _author(value, dblp=False):
    value = unicodedata.normalize('NFC', str(value)).replace('’', "'")
    if dblp:
        value = re.sub(r' \d{4}$', '', value)  # official DBLP disambiguation label, never an output rename
    return ' '.join(value.split()).casefold()


def _sha(value):
    return bool(re.fullmatch('[0-9a-f]{64}', str(value or '')))


def _key(row):
    return row.get('pi'), row.get('oa'), row.get('work'), ndoi(row.get('doi'))


def remember(ctx, row, source):
    """Only retain an already eligible source; no title is changed before edition grouping."""
    if missing(row.get('title')):
        if not hasattr(ctx, '_title_sources'):
            ctx._title_sources = {}
        ctx._title_sources[_key(row)] = source


def prepare(ctx):
    if hasattr(ctx, '_title_reviews'):
        return ctx._title_reviews
    path = P.data('paper-title-review.json', ctx.school, root=ctx.here)
    ctx._title_reviews = []
    if not path.exists():
        return []
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('paper title review exceeds 5 MB')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('school') != ctx.school or not isinstance(data.get('reviews'), list):
        raise ValueError('paper title review needs version 1, this school and reviews')
    ids = set()
    for d in data['reviews']:
        if not isinstance(d, dict) or not d.get('id') or d['id'] in ids or not d.get('pi'):
            raise ValueError('paper title reviews need unique IDs and exact PI names')
        ids.add(d['id'])
        datetime.date.fromisoformat(d['reviewed_at'])
        if not d.get('reviewed_by'):
            raise ValueError('paper title review needs a reviewer')
    ctx._title_reviews = data['reviews']
    ctx.paper_title_review = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), decisions=[])
    return ctx._title_reviews


def _candidate(d, row):
    m = d.get('match') or {}
    return d['pi'] == row['pi'] and (bool(m.get('oa')) and m['oa'] == row.get('oa')
                                   or bool(m.get('work')) and m['work'] == row.get('work'))


def _check(ctx, d, row, source):
    m = d.get('match') or {}
    if not m.get('doi') or ndoi(m['doi']) != ndoi(row.get('doi')) or not ndoi(row.get('doi')):
        return 'doi_mismatch'
    if any(k in m and m[k] != row.get(k) for k in ('oa', 'work')):
        return 'selector_mismatch'
    if not source or source.get('id') != row.get('oa') or ndoi(source.get('doi')) != ndoi(row.get('doi')):
        return 'missing_source_binding'
    preimages = d.get('source_preimages') or []
    bound = [p for p in preimages if p.get('work_sha256') == preimage_sha256(source) and _sha(p.get('capture_sha256'))]
    if len(bound) != 1:
        return 'source_preimage_mismatch'
    if not missing(source.get('title')) or source.get('title') != bound[0].get('original_title'):
        return 'original_title_mismatch'
    pub, db = d.get('publisher') or {}, d.get('owned_dblp') or {}
    pid = (getattr(ctx, 'pid0', {}).get(row['pi']) or {})
    if pid.get('identityHold') or not row.get('identity') or str(row['identity']).startswith(('candidate', 'unverified', 'unknown')) or not row.get('appointment'):
        return 'not_eligible_identity'
    if not db.get('pid') or db['pid'] not in (pid.get('dblp') or []):
        return 'not_owned_dblp'
    if d.get('edition_preimage_sha256') != preimage_sha256(row.get('editions') or []):
        return 'edition_preimage_mismatch'
    if d.get('edition_binding') != 'exact_doi' or any(ndoi(x.get('doi')) != ndoi(row['doi']) for x in (pub, db)):
        return 'edition_or_doi_mismatch'
    if not (_sha(pub.get('sha256')) and _sha(db.get('sha256')) and pub.get('complete_body') is True
            and pub.get('full_parse_returncode') == 0 and pub.get('bytes', 0) > 0 and pub.get('pages', 0) > 0
            and pub.get('url') and db.get('key')):
        return 'incomplete_source_proof'
    title = d.get('title')
    if not isinstance(title, str) or not title.strip() or not _title(title) or any(_title(x.get('title')) != _title(title) for x in (pub, db)):
        return 'competing_source_titles'
    if pub.get('year') != row.get('year') or db.get('year') != row.get('year') or source.get('publication_year') != row.get('year'):
        return 'source_year_mismatch'
    pb, dbb, target = pub.get('byline'), db.get('byline'), bound[0].get('byline')
    actual = [a.get('raw_author_name') or (a.get('author') or {}).get('display_name') for a in source.get('authorships') or []]
    if any(not isinstance(v, list) or not v or any(not isinstance(a, str) or not a.strip() for a in v) for v in (pb, dbb, target)) or target != actual or len(pb) != len(target):
        return 'missing_or_changed_byline'
    if [_author(a, True) for a in dbb] != [_author(a) for a in pb]:
        return 'publisher_dblp_byline_mismatch'
    if _title(pub.get('title_quote')) != _title(title) or str(pub['year']) not in str(pub.get('publication_quote') or ''):
        return 'missing_frontmatter_quotes'
    quote = _author(pub.get('byline_quote') or '')
    try:
        positions = [quote.index(_author(a)) for a in pb]
    except ValueError:
        return 'missing_byline_quote'
    if positions != sorted(positions):
        return 'publisher_byline_quote_order'
    spelling = d.get('reviewed_spelling_bindings') or []
    for a, b in zip(actual, pb):
        if _author(a) != _author(b) and not any(x.get('source') == a and x.get('publisher') == b
                                             and x.get('evidence_sha256') == pub['sha256'] for x in spelling):
            return 'unreviewed_byline_difference'
    return None


def apply(ctx, rows, date_check):
    """Post-group metadata only. Caller reruns ordinary quality on filled rows, without any new edition grouping."""
    reviews = prepare(ctx)
    filled, output = [], []
    for row in rows:
        ds = [d for d in reviews if _candidate(d, row)]
        if not ds:
            output.append(row); continue
        result = copy.copy(row)
        source = getattr(ctx, '_title_sources', {}).get(_key(row))
        reasons = [] if missing(row.get('title')) else ['nonempty_title_preserved']
        if not reasons:
            reasons = [why for d in ds if (why := _check(ctx, d, row, source))]
            if len({_title(d.get('title')) for d in ds}) != 1:
                reasons.append('competing_reviews')
        if not reasons and date_check(source, ds[0]['title'], row) != row.get('date'):
            reasons.append('would_change_date')
        status = 'held' if reasons else 'filled'
        if reasons == ['nonempty_title_preserved']:
            status = 'unchanged_nonempty'
        provenance = dict(status=status, review_ids=[d['id'] for d in ds], input_sha256=ctx.paper_title_review['sha256'],
                          original_title=row.get('title'), reasons=sorted(set(reasons)))
        if status == 'filled':
            d = ds[0]
            result['title'] = d['title']
            provenance.update(source_work_sha256=preimage_sha256(source), publisher_pdf_sha256=d['publisher']['sha256'],
                              owned_dblp_pid=d['owned_dblp']['pid'], owned_dblp_key=d['owned_dblp']['key'])
            filled.append(result)
        result['titleEnrichment'] = provenance
        ctx.paper_title_review['decisions'].append(dict(pi=row['pi'], oa=row.get('oa'), work=row.get('work'), doi=row.get('doi'), **provenance))
        ctx.n['title_enrichment_' + status] += 1
        output.append(result)
    return output, filled
