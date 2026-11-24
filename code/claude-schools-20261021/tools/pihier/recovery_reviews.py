"""Complete publisher projections of exact existing recoveries; ordinary admission gates still apply."""
import collections
import copy
import datetime
import hashlib
import json
import re
import unicodedata

import atlas_paths as P
import school_config as S
from .common import excluded_school_only, ndoi, norm_title
from .names import Name, byline_name

LIMIT = 5 << 20


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _key(value):
    return re.sub(r'^https?://dblp[.]org/rec/', '', str(value or ''))


def _author(value):
    value = re.sub(r'\s+\d{4}$', '', str(value or ''))
    return ' '.join(unicodedata.normalize('NFC', value).replace('’', "'").casefold().split())


def prepare(ctx):
    if hasattr(ctx, '_recovery_reviews'):
        return ctx._recovery_reviews
    ctx._recovery_reviews = []
    path = P.data('recovery-source-review.json', ctx.school, root=ctx.here)
    if not path.exists():
        return []
    if path.stat().st_size > LIMIT:
        raise ValueError('recovery source review exceeds 5 MB')
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('school') != ctx.school or not isinstance(data.get('reviews'), list):
        raise ValueError('recovery source review needs version 1, this school and reviews')
    ids = set()
    for d in data['reviews']:
        if not isinstance(d, dict) or not d.get('id') or d['id'] in ids or not d.get('pi') or d.get('kind') != 'dblp' or not d.get('dblp_key'):
            raise ValueError('recovery source review requires unique ID, PI and exact DBLP source key')
        ids.add(d['id'])
        datetime.date.fromisoformat(d['reviewed_at'])
        if not d.get('reviewed_by'):
            raise ValueError('recovery source review requires reviewer')
    ctx._recovery_reviews = data['reviews']
    ctx.recovery_source_review = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), decisions=[])
    return ctx._recovery_reviews


def _check(ctx, p, x, d):
    if d.get('decision') != 'reviewed_complete_publisher_projection':
        return 'not_explicitly_reviewed'
    if d.get('source_sha256') != digest(x):
        return 'source_preimage_changed'
    db, pub = d.get('owned_dblp') or {}, d.get('publisher') or {}
    key = _key(x.get('dblp_key'))
    if db.get('pid') not in (p.get('dblp') or []) or db.get('key') != key:
        return 'not_exact_owned_publication'
    person = ((getattr(ctx, 'dblp_persons', {}) or {}).get('persons') or {}).get(db['pid']) or {}
    records = [r for r in person.get('pubs') or [] if r.get('key') == key]
    if len(records) != 1 or digest(records[0]) != db.get('record_sha256'):
        return 'owned_publication_preimage_changed'
    record = records[0]
    if (pub.get('complete_body') is not True or pub.get('full_parse_returncode') != 0
            or type(pub.get('bytes')) is not int or pub['bytes'] <= 0
            or type(pub.get('pages')) is not int or pub['pages'] <= 0
            or not str(pub.get('url') or '').startswith('https://')):
        return 'incomplete_publisher_proof'
    if any(not re.fullmatch('[0-9a-f]{64}', str(v or '')) for v in
           [pub.get('sha256'), pub.get('page1_text_sha256'), pub.get('full_text_sha256'), db.get('capture_sha256')]):
        return 'invalid_source_hash'
    doi = ndoi(pub.get('doi'))
    if not doi or ndoi(x.get('doi')) != doi or doi not in {ndoi(v) for v in record.get('dois') or []}:
        return 'edition_doi_mismatch'
    title = norm_title(pub.get('title'))
    if not title or any(norm_title(t) != title for t in [x.get('title'), record.get('title'), pub.get('title_quote')]):
        return 'edition_title_mismatch'
    if type(pub.get('year')) is not int or str(pub['year']) != str(record.get('year')):
        return 'publisher_dblp_year_mismatch'
    if record.get('type') not in {'inproceedings', 'article', 'incollection'}:
        return 'unsupported_owned_publication_kind'
    excerpt = pub.get('page1_excerpt')
    if not isinstance(excerpt, str) or digest(excerpt) != pub.get('excerpt_sha256'):
        return 'publisher_excerpt_changed'
    for field in ['title_quote', 'publication_quote', 'doi_quote', 'venue_quote']:
        quote = pub.get(field)
        if not isinstance(quote, str) or not quote.strip() or quote not in excerpt:
            return 'missing_frontmatter_quote'
    if (str(pub['year']) not in pub['publication_quote'] or doi not in pub['doi_quote'].lower()
            or not pub.get('venue') or pub['venue'] not in pub['venue_quote']):
        return 'missing_publication_metadata_quote'
    blocks = pub.get('authors')
    if not isinstance(blocks, list) or not blocks:
        return 'missing_complete_author_blocks'
    names = [a.get('name') for a in blocks if isinstance(a, dict)]
    if len(names) != len(blocks) or any(not isinstance(a, str) or not a.strip() for a in names):
        return 'missing_complete_author_blocks'
    byline = [_author(a) for a in names]
    if len(set(byline)) != len(byline) or byline != [_author(a[0]) for a in record.get('authors') or []]:
        return 'publisher_dblp_ordered_byline_mismatch'
    if collections.Counter(byline) != collections.Counter(_author(a) for a in x.get('byline') or []):
        return 'original_author_set_changed'
    own, positions = [], []
    for block in blocks:
        quote, affiliation = block.get('quote'), block.get('affiliation')
        if (not isinstance(quote, str) or not isinstance(affiliation, str) or not affiliation.strip()
                or quote not in excerpt or block['name'] not in quote or affiliation not in quote):
            return 'incomplete_author_affiliation_block'
        # A complete individual block cannot silently attribute a neighbour's affiliation.
        if any(other != block['name'] and other in quote for other in names):
            return 'ambiguous_author_affiliation_block'
        positions.append(excerpt.index(quote))
        if Name(p.get('names') or [p['pi']]).match(byline_name(block['name'])):
            auth = dict(raw_affiliation_strings=[affiliation], institutions=[])
            if re.search(S.aff(ctx.school), affiliation, re.I) and not excluded_school_only(auth, ctx.school):
                own.append(block)
    if positions != sorted(positions):
        return 'publisher_block_order_mismatch'
    if len(own) != 1:
        return 'pi_own_school_block_unproven'
    return None


def project(ctx, p, x, kind):
    """No review means exact legacy behavior. A stale targeted review holds only that source."""
    reviews = prepare(ctx)
    candidates = [d for d in reviews if d['pi'] == p['pi'] and d['kind'] == kind and _key(d['dblp_key']) == _key(x.get('dblp_key'))]
    if not candidates:
        return x
    reason = 'competing_source_reviews' if len(candidates) != 1 else None
    if reason is None:
        try:
            reason = _check(ctx, p, x, candidates[0])
        except (KeyError, TypeError, ValueError, IndexError):
            reason = 'malformed_source_proof'
    report = getattr(ctx, 'recovery_source_review', None)
    if report is None:
        report = ctx.recovery_source_review = dict(decisions=[])
    decision = dict(pi=p['pi'], kind=kind, dblp_key=_key(x.get('dblp_key')), review_ids=[d['id'] for d in candidates],
                    original=copy.deepcopy(x), original_sha256=digest(x), status='held' if reason else 'projected', reason=reason)
    if reason:
        ctx.n['recovery_source_review_held:' + reason] += 1
        report['decisions'].append(decision)
        return None
    d = candidates[0]; pub = d['publisher']
    blocks = pub['authors']
    own = next(b for b in blocks if Name(p.get('names') or [p['pi']]).match(byline_name(b['name']))
               and re.search(S.aff(ctx.school), b['affiliation'], re.I)
               and not excluded_school_only(dict(raw_affiliation_strings=[b['affiliation']], institutions=[]), ctx.school))
    target = dict(pi=p['pi'], dblp_key='https://dblp.org/rec/' + _key(x['dblp_key']), title=pub['title'], year=pub['year'],
                  doi=ndoi(pub['doi']), venue=pub['venue'], byline=[b['name'] for b in blocks],
                  evidence=dict(basis='page1_open', how='near', quotes=[own['quote']], url=pub['url'], pdf_sha256=pub['sha256']))
    # The provider OA ID belongs to its original observation, not automatically to this publisher edition.
    # Keep an actual publisher-attested arXiv relation only; it is not an invented OpenAlex alias.
    arxiv = x.get('arxiv')
    related = pub.get('related_version_quote')
    if arxiv and isinstance(related, str) and related in pub['page1_excerpt'] and ('/abs/' + str(arxiv)) in related:
        target['arxiv'] = arxiv
    decision.update(projected=copy.deepcopy(target), projected_sha256=digest(target), publisher_sha256=pub['sha256'],
                    page1_text_sha256=pub['page1_text_sha256'], owned_record_sha256=d['owned_dblp']['record_sha256'])
    report['decisions'].append(decision)
    ctx.n['recovery_source_review_projected'] += 1
    return target
