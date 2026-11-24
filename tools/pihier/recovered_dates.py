"""Replay an accepted lab-page paper's exact date from original Crossref bytes.

This supplies date precision only. Identity, individual school affiliation,
appointment containment, genre and edition checks remain in recovered_rows.
Rows without this optional proof retain the historical whole-year interval.
"""
import datetime
import hashlib
import json
import re
from urllib.parse import unquote, urlsplit

import atlas_paths as P
from .common import ndoi, norm_title


def publication_date(ctx, row, kind):
    if kind == 'publisher':
        return row['date']
    source = (row.get('evidence') or {}).get('publication_date_source')
    if kind != 'labpage_addition' or source is None:
        return str(row['year'])
    if not isinstance(source, dict) or source.get('http_status') != 200 or not source.get('reviewed_by'):
        raise ValueError('unreviewed_publication_date_source')
    datetime.datetime.fromisoformat(source['captured'])
    filename = source.get('source_file')
    if not isinstance(filename, str) or not re.fullmatch(r'[0-9a-f]{64}\.json', filename):
        raise ValueError('invalid_publication_date_source_file')
    path = P.data('labpage-additions.json', ctx.school, root=ctx.here).parent / 'publication-date-sources' / filename
    if not path.is_file() or path.stat().st_size > 2 << 20:
        raise ValueError('missing_publication_date_capture')
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != source.get('sha256') or filename != sha + '.json':
        raise ValueError('publication_date_capture_changed')
    response = json.loads(raw)
    if response.get('status') != 'ok' or response.get('message-type') != 'work':
        raise ValueError('not_crossref_work_response')
    work = response['message']
    doi = ndoi(row.get('doi'))
    url = urlsplit(source['url'])
    if (not doi or ndoi(work.get('DOI')) != doi or url.scheme != 'https'
            or url.netloc != 'api.crossref.org' or url.query or url.fragment
            or unquote(url.path).casefold() != '/works/' + doi):
        raise ValueError('publication_date_doi_mismatch')
    titles = work.get('title') or []
    if not norm_title(row.get('title')) or norm_title(row['title']) not in [norm_title(t) for t in titles]:
        raise ValueError('publication_date_title_mismatch')
    field = source.get('date_field')
    if field not in {'published-online', 'published-print', 'published'}:
        raise ValueError('not_publication_date_field')
    parts = work[field]['date-parts']
    if not isinstance(parts, list) or len(parts) != 1 or len(parts[0]) != 3 or any(type(v) is not int for v in parts[0]):
        raise ValueError('publication_date_not_day_precise')
    date = datetime.date(*parts[0]).isoformat()
    if date != row.get('date') or date[:4] != str(row['year']):
        raise ValueError('publication_date_mismatch')
    return date
