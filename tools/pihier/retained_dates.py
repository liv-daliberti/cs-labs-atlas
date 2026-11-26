"""Correct dates of already eligible, unmerged conference records from exact publisher proof.

This cannot admit a missing work. The indexed original remains immutable; the
publisher must name the same DOI, title and PI at this school, and the corrected
venue year must independently fit an existing appointment before links are built.
"""
import copy
import datetime
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import atlas_paths as P
import school_config as S
from .common import TODAY, WINDOW_START, excluded_school_only, ndoi, norm_title
from .names import Name
from .periods import contains

LIMIT = 2 << 20


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def prepare(ctx):
    path = P.data('paper-claim-review.json', ctx.school, root=ctx.here)
    if not path.exists():
        return [], None
    raw = path.read_bytes()
    if len(raw) > 5 << 20:
        raise ValueError('retained date review exceeds size limit')
    data = json.loads(raw)
    reviews = data.get('conference_dates', [])
    if data.get('version') != 1 or data.get('school') != ctx.school or not isinstance(reviews, list):
        raise ValueError('invalid retained date review')
    ids, selectors = set(), set()
    for d in reviews:
        m = d.get('match') or {}
        selector = (d.get('pi'), m.get('oa'), ndoi(m.get('doi')))
        if (not all(selector) or set(m) != {'oa', 'doi'} or not d.get('id') or d['id'] in ids
                or selector in selectors or d.get('decision') != 'confirmed_conference_year'
                or not d.get('reviewed_by') or not d.get('independent_reviewer') or not d.get('why')
                or d['reviewed_by'] == d['independent_reviewer']
                or set(d.get('changes') or {}) != {'year'} or type(d['changes']['year']) is not int):
            raise ValueError('retained date needs unique exact selectors and independent review')
        datetime.date.fromisoformat(d['reviewed_at'])
        ids.add(d['id']); selectors.add(selector)
    return reviews, hashlib.sha256(raw).hexdigest()


def publisher(ctx, d):
    proof = d['publisher']; sha = proof['sha256']; url = urlsplit(proof['url'])
    if (proof.get('http_status') != 200 or not re.fullmatch('[0-9a-f]{64}', sha)
            or proof.get('format') != 'json' or url.scheme != 'https'
            or url.netloc != 'api.crossref.org' or url.query or url.fragment
            or unquote(url.path).casefold() != '/works/' + ndoi(d['match']['doi'])):
        raise ValueError('invalid retained date publisher reference')
    datetime.datetime.fromisoformat(proof['captured'])
    relative = Path(proof['source_file'])
    if (relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] != 'metadata'
            or relative.name not in {sha + '.json', sha + '.html'}):
        raise ValueError('invalid retained date source path')
    path = P.store(ctx.school) / relative
    if not path.resolve().is_relative_to((P.store(ctx.school) / 'metadata').resolve()):
        raise ValueError('retained date source leaves registered metadata store')
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('missing retained date original')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('retained date original changed')
    response = json.loads(raw)
    if response.get('status') != 'ok' or response.get('message-type') != 'work':
        raise ValueError('not an original Crossref work response')
    return response['message']


def event_date(part):
    values = part['date-parts']
    if (not isinstance(values, list) or len(values) != 1 or len(values[0]) != 3
            or any(type(v) is not int for v in values[0])):
        raise ValueError('conference event date not explicit')
    return datetime.date(*values[0])


def check(ctx, row, work, d):
    old = d['source']; year = d['changes']['year']; m = d['match']
    if (not work or digest(work) != old['work_sha256'] or work.get('id') != m['oa']
            or ndoi(work.get('doi')) != ndoi(m['doi']) or row.get('oa') != m['oa']
            or ndoi(row.get('doi')) != ndoi(m['doi']) or row.get('pi') != d['pi']
            or row.get('title') != work.get('title') or work.get('title') != old['original_title']
            or row.get('year') != work.get('publication_year') or row.get('year') != old['original_year']
            or row.get('date') != work.get('publication_date') or row.get('date') != old['original_date']
            or row.get('byline') != old['ordered_byline']
            or [a.get('raw_author_name') or (a.get('author') or {}).get('display_name')
                for a in work.get('authorships') or []] != old['ordered_byline']
            or row.get('type') != 'conference-paper' or work.get('type') != 'conference-paper'
            or row.get('editions') or row.get('dated_by') or row.get('retainedDateReviews')
            or row.get('identity') in (None, '', 'candidate', 'unverified') or not row.get('appointment')):
        raise ValueError('retained date eligible source preimage mismatch')
    if not WINDOW_START <= year <= int(TODAY[:4]) or year >= row['year']:
        raise ValueError('retained date is not an earlier in-window venue year')
    w = publisher(ctx, d)
    if (ndoi(w.get('DOI')) != ndoi(m['doi']) or w.get('type') != 'proceedings-article'
            or norm_title(row['title']) not in [norm_title(t) for t in w.get('title') or []]
            or w.get('container-title') != [d['publisher']['container_title']]
            or re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)', w['container-title'][0]) != [str(year)]):
        raise ValueError('publisher conference edition mismatch')
    start, end = event_date(w['event']['start']), event_date(w['event']['end'])
    if start > end or start.year != end.year or start.year != year:
        raise ValueError('publisher conference event year mismatch')
    # Creation/deposit/indexing times never supply publication authority. A real
    # conflicting publication date needs a different review, not this narrow case.
    for field in ('published', 'published-online', 'published-print', 'issued'):
        parts = (w.get(field) or {}).get('date-parts') or []
        for part in parts:
            if part and part[0] is not None and part[0] != year:
                raise ValueError('conflicting explicit publisher publication year')
    p = ctx.pid0[d['pi']]
    if p.get('identityHold'):
        raise ValueError('retained date PI identity held')
    authors = w.get('author') or []
    credited = [' '.join(str(a.get(k) or '') for k in ('given', 'family')).strip() for a in authors]
    if not credited or credited != d['publisher']['ordered_byline'] or any(not n for n in credited):
        raise ValueError('publisher complete credited byline changed')
    own = [a for a, name in zip(authors, credited) if Name(p.get('names') or [p['pi']]).match(name)]
    if len(own) != 1:
        raise ValueError('publisher PI byline not unique')
    affiliations = [a.get('name') or '' for a in own[0].get('affiliation') or []]
    if (not any(re.search(S.aff(ctx.school), a, re.I) for a in affiliations)
            or excluded_school_only(dict(institutions=[], raw_affiliation_strings=affiliations), ctx.school)):
        raise ValueError('publisher PI own school not proved')
    date = str(year)
    per = next((q for q in p.get('periods') or [] if contains(q['start'], q['end'], date,
                q.get('asof') or TODAY) == 'supported'), None)
    listing = next((q for q in p.get('listings') or [] if q['year'] == year), None)
    if per is None and listing is None:
        raise ValueError('corrected venue year outside proven appointment')
    return dict(periodId=per['id']) if per else dict(listing=year)


def apply(ctx):
    reviews, input_sha = prepare(ctx)
    if not reviews:
        return
    outcomes = []; replacements = {}
    for d in reviews:
        selected = [(i, r) for i, r in enumerate(ctx.rows) if r['pi'] == d['pi']
                    and r.get('oa') == d['match']['oa'] and ndoi(r.get('doi')) == ndoi(d['match']['doi'])]
        if len(selected) != 1:
            raise ValueError('retained date requires one already eligible primary record')
        index, row = selected[0]
        if any(other['pi'] == row['pi'] and norm_title(other['title']) == norm_title(row['title'])
               for i, other in enumerate(ctx.rows) if i != index):
            raise ValueError('retained date needs an edition review before changing grouped dates')
        work = next((w for pi, w, *_ in ctx.hits if pi == d['pi'] and w.get('id') == d['match']['oa']
                     and digest(w) == d['source']['work_sha256']), None)
        appointment = check(ctx, row, work, d)
        marker = dict(id=d['id'], input_sha256=input_sha, source_work_sha256=d['source']['work_sha256'],
                      publisher_sha256=d['publisher']['sha256'], original_year=row['year'],
                      original_date=row['date'], year=d['changes']['year'], date=str(d['changes']['year']))
        result = dict(row, year=marker['year'], date=marker['date'], appointment=appointment,
                      retainedDateReviews=[marker])
        replacements[index] = result
        outcomes.append(dict(id=d['id'], pi=d['pi'], status='projected', original_eligible_row=copy.deepcopy(row),
                             original_complete_source=copy.deepcopy(work), projected=copy.deepcopy(result),
                             publisher_sha256=d['publisher']['sha256']))
    # Validate every correction before changing any native row.
    ctx.rows = [replacements.get(i, row) for i, row in enumerate(ctx.rows)]
    ctx.retained_date_review = dict(input_sha256=input_sha, decisions=outcomes)
    ctx.n['retained_conference_dates_corrected'] += len(replacements)
