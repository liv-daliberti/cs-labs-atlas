"""Sourced claim reviews: hold unresolved PI-paper claims and join explicitly identified editions.

Reviews cannot admit a paper or waive normal identity, affiliation, appointment or type gates. Holds and rejections
also stop their matched works from lending new dynamic author-ID anchors. A missing merge target holds its source.
"""
import collections
import copy
import datetime
import hashlib
import json
import re

import atlas_paths as P
from .common import ndoi


def _selector(value):
    if not isinstance(value, dict) or not value or set(value) - {'oa', 'doi', 'work'}:
        raise ValueError('paper claim review needs an explicit oa/doi/work selector')
    if any(not isinstance(v, str) or not v.strip() for v in value.values()):
        raise ValueError('paper claim review identifiers must be nonempty strings')
    return {k: ndoi(v) if k == 'doi' else v.strip() for k, v in value.items()}


def matches(row, selector):
    """All supplied identifiers must agree on one record, including a folded edition; names/titles never identify it."""
    for record in [row] + list(row.get('editions') or []):
        values = dict(oa=record.get('oa') or record.get('id'), doi=ndoi(record.get('doi')), work=record.get('work'))
        if all(values[k] == v for k, v in selector.items()):
            return True
    return False


def prepare(ctx):
    """Validate and freeze this build's review input before identity anchoring. Invalid reviews stop the build."""
    if hasattr(ctx, '_paper_claim_reviews'):
        return ctx._paper_claim_reviews
    path = P.data('paper-claim-review.json', ctx.school, root=ctx.here)
    ctx._paper_claim_review_hits = collections.defaultdict(dict)
    ctx._paper_claim_blocked_hits = set()
    ctx.paper_claim_review = None
    if not path.exists():
        ctx._paper_claim_reviews = []
        return []
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('reviewed paper input exceeds the reviewed-input 5 MB limit')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('school') != ctx.school or not isinstance(data.get('decisions'), list):
        raise ValueError('paper claim review must name this school, version 1 and decisions')
    renamed = {p['censusName']: p['pi'] for p in ctx.pis if p.get('censusName')}
    ids, signatures, validated = set(), {}, []
    for source in data['decisions']:
        d = copy.deepcopy(source)
        if not isinstance(d, dict) or any(not isinstance(d.get(k), str) or not d[k].strip()
                                          for k in ('id', 'pi', 'why', 'reviewed_by', 'reviewed_at')):
            raise ValueError('paper claim review needs id, pi, why and reviewer/date')
        if d['id'] in ids or d.get('decision') not in ('hold', 'reject', 'merge'):
            raise ValueError('paper claim review IDs must be unique; only hold/reject/merge are permitted')
        datetime.date.fromisoformat(d['reviewed_at'])
        evidence = d.get('evidence')
        if not isinstance(evidence, list) or not evidence or any(
                not isinstance(e, dict) or not e.get('url') or not e.get('quote')
                or not re.fullmatch('[0-9a-f]{64}', str(e.get('sha256') or '')) for e in evidence):
            raise ValueError('paper claim review needs original url, sha256 and quote evidence')
        ids.add(d['id'])
        d['pi'] = renamed.get(d['pi'], d['pi'])
        d['match'] = _selector(d.get('match'))
        if d['decision'] == 'merge':
            d['into'] = _selector(d.get('into'))
        elif 'into' in d:
            raise ValueError('only a merge review can name a target')
        signature = (d['pi'], tuple(sorted(d['match'].items())))
        if signature in signatures:
            raise ValueError('multiple active paper reviews for the same PI and selector')
        signatures[signature] = d['id']
        validated.append(d)
    ctx._paper_claim_reviews = validated
    ctx.paper_claim_review = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), decisions=[])
    return validated


def excluded(ctx, pi, work):
    """A held/rejected work cannot become a dynamic author-ID anchor for this PI, including pi-works recovery."""
    selected = [d for d in prepare(ctx) if d['pi'] == pi and d['decision'] != 'merge' and matches(work, d['match'])]
    if len({d['decision'] for d in selected}) > 1:
        raise ValueError('conflicting hold/reject paper reviews for one work')
    for d in selected:
        key = work.get('oa') or work.get('id') or work.get('work') or ndoi(work.get('doi'))
        ctx._paper_claim_review_hits[d['id']][key] = {k: v for k, v in dict(
            oa=work.get('oa') or work.get('id'), work=work.get('work'), doi=ndoi(work.get('doi'))).items() if v}
        pair = (pi, key)
        if pair not in ctx._paper_claim_blocked_hits:
            ctx._paper_claim_blocked_hits.add(pair)
            ctx.n['paper_review_hits_withheld_before_identity'] += 1
    return bool(selected)


def _joined(target, source):
    """Keep the accepted target's metadata and every eligible source/target edition byline."""
    result = copy.deepcopy(target)
    result['_bylines'] = copy.deepcopy(target.get('_bylines') or [(target.get('byline') or [], target.get('byline_school') or [])])
    result['_bylines'] += copy.deepcopy(source.get('_bylines') or [(source.get('byline') or [], source.get('byline_school') or [])])
    editions = list(target.get('editions') or []) + [{k: source.get(k) for k in ('oa', 'work', 'doi', 'year', 'venue')}] + list(source.get('editions') or [])
    seen = {(target.get('oa'), target.get('work'), ndoi(target.get('doi')))}
    result['editions'] = []
    for e in editions:
        key = (e.get('oa'), e.get('work'), ndoi(e.get('doi')))
        if key not in seen:
            result['editions'].append(copy.deepcopy(e)); seen.add(key)
    return result


def apply(ctx):
    """Review normal eligible rows before student corroboration/links; missing targets never force paper admission."""
    decisions = prepare(ctx)
    if ctx.paper_claim_review is None:
        return
    path = P.data('paper-claim-review.json', ctx.school, root=ctx.here)
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != ctx.paper_claim_review['sha256']:
        raise ValueError('paper claim reviews changed during the build')
    original = {i: r for i, r in enumerate(ctx.rows)}

    def find(d, selector, rows):
        found = [i for i, r in rows.items() if r['pi'] == d['pi'] and matches(r, selector)]
        if len(found) > 1:
            raise ValueError('ambiguous paper claim review selector: ' + d['id'])
        return found[0] if found else None

    # Plan everything before mutating a row, so conflicting reviews or merge cycles cannot publish partial results.
    blocked, actions, outcomes = set(), {}, {}
    for d in decisions:
        hits = list(ctx._paper_claim_review_hits[d['id']].values())
        outcomes[d['id']] = dict(d, matched_before_identity=hits, outcome='no_current_claim')
        if d['decision'] == 'merge':
            continue
        i = find(d, d['match'], original)
        if i is not None:
            if i in actions and actions[i] != d['decision']:
                raise ValueError('conflicting hold/reject paper reviews: ' + d['id'])
            actions[i] = d['decision']; blocked.add(i)
            outcomes[d['id']]['outcome'] = 'held' if d['decision'] == 'hold' else 'rejected'
        elif hits:
            outcomes[d['id']]['outcome'] = 'held_before_identity' if d['decision'] == 'hold' else 'rejected_before_identity'
    rows = {i: r for i, r in original.items() if i not in blocked}
    edges, merge_sources, missing = {}, {}, set()
    for d in decisions:
        if d['decision'] != 'merge':
            continue
        source = find(d, d['match'], rows)
        target = find(d, d['into'], rows)
        if source is None:
            continue
        if source == target:
            outcomes[d['id']]['outcome'] = 'already_merged'; continue
        if source in edges or source in missing:
            raise ValueError('multiple merge destinations for one eligible claim: ' + d['id'])
        merge_sources[source] = d
        if target is None:
            missing.add(source)
        else:
            edges[source] = target

    def root(i, trail=()):
        if i in trail:
            raise ValueError('cycle in reviewed paper edition merges')
        if i in missing:
            return None
        return root(edges[i], trail + (i,)) if i in edges else i

    destinations = {i: root(i) for i in merge_sources}
    kept = {i: copy.deepcopy(r) for i, r in rows.items()}
    merged, held_missing = 0, 0
    for i, target in destinations.items():
        d = merge_sources[i]
        if target is None:
            outcomes[d['id']]['outcome'] = 'held_missing_merge_target'; held_missing += 1
        else:
            kept[target] = _joined(kept[target], rows[i])
            outcomes[d['id']]['outcome'] = 'merged'; merged += 1
        kept.pop(i, None)
    ctx.rows = [kept[i] for i in sorted(kept)]
    ctx.paper_claim_review['decisions'] = [outcomes[d['id']] for d in decisions]
    n = ctx.n
    n['paper_review_rows_held'] = sum(v == 'hold' for v in actions.values()) + held_missing
    n['paper_review_rows_rejected'] = sum(v == 'reject' for v in actions.values())
    n['paper_review_editions_merged'] = merged
    n['paper_review_decisions_without_current_claim'] = sum(x['outcome'] == 'no_current_claim' for x in outcomes.values())
    n['lab_papers'] = len(ctx.rows)
    n['lab_papers_in_collection'] = sum(bool(r.get('work')) for r in ctx.rows)
    n['lab_papers_new'] = n['lab_papers'] - n['lab_papers_in_collection']
    n['lab_papers_by_period'] = sum('periodId' in r.get('appointment', {}) for r in ctx.rows)
    n['lab_papers_by_listing'] = n['lab_papers'] - n['lab_papers_by_period']
    for key in list(n):
        if key.startswith('identity:'):
            del n[key]
    n.update({'identity:' + k: v for k, v in collections.Counter(r['identity'] for r in ctx.rows).items()})
