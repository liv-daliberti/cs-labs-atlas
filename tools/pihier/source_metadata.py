"""Exact owned-publication title projections on complete eligible originals, before edition identity."""
import copy
import datetime
import hashlib
import json

import atlas_paths as P
from .common import ndoi
from .names import Name, byline_name

LIMIT = 5 << 20


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _title(value):
    return ' '.join(str(value or '').split()).rstrip('.').casefold()


def prepare(ctx):
    if hasattr(ctx, '_source_metadata_reviews'):
        return ctx._source_metadata_reviews
    ctx._source_metadata_reviews = []
    path = P.data('paper-source-review.json', ctx.school, root=ctx.here)
    if not path.exists():
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
        if d.get('decision') != 'owned_publication_title' or not isinstance(d.get('changes'), dict) or set(d['changes']) != {'title'}:
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
        reason = _check(ctx, row, source, d, date_check)
        status = 'held' if reason else 'projected'
        decision = dict(id=d['id'], pi=row['pi'], oa=row['oa'], doi=row.get('doi'), status=status,
                        reason=reason, source_work_sha256=(d.get('source') or {}).get('work_sha256'),
                        owned_dblp=copy.deepcopy(d.get('owned_dblp')), original_eligible_row=copy.deepcopy(row),
                        original_complete_source=copy.deepcopy(source), proposed_title=d['changes']['title'])
        ctx.paper_source_review['decisions'].append(decision)
        ctx.n['source_metadata_' + status] += 1
        if reason:
            output.append(row); continue
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
