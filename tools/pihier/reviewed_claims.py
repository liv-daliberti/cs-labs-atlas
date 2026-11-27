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
from . import school_flag_policy


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
    ctx.school_flag_policy = None
    ctx.school_flag_policy_summary = None
    if not path.exists():
        ctx._paper_claim_reviews = []
        return []
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('reviewed paper input exceeds the reviewed-input 5 MB limit')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('school') != ctx.school or not isinstance(data.get('decisions'), list):
        raise ValueError('paper claim review must name this school, version 1 and decisions')
    school_flag_policy.prepare(ctx, data, path, hashlib.sha256(raw).hexdigest())
    from .students import renamed_pis   # imported here: students imports this package's other modules
    renamed = renamed_pis(ctx.pis, ctx.school, ctx.here)
    ids, signatures, validated = set(), {}, []
    for source in data['decisions']:
        d = copy.deepcopy(source)
        if not isinstance(d, dict) or any(not isinstance(d.get(k), str) or not d[k].strip()
                                          for k in ('id', 'pi', 'why', 'reviewed_by', 'reviewed_at')):
            raise ValueError('paper claim review needs id, pi, why and reviewer/date')
        if d['id'] in ids or d.get('decision') not in ('hold', 'reject', 'merge', 'hold_derived_school_flags'):
            raise ValueError('paper claim review IDs must be unique; only hold/reject/merge/hold_derived_school_flags are permitted')
        datetime.date.fromisoformat(d['reviewed_at'])
        evidence = d.get('evidence')
        if not isinstance(evidence, list) or not evidence or any(
                not isinstance(e, dict) or not e.get('url') or not e.get('quote')
                or not re.fullmatch('[0-9a-f]{64}', str(e.get('sha256') or '')) for e in evidence):
            raise ValueError('paper claim review needs original url, sha256 and quote evidence')
        ids.add(d['id'])
        d['pi'] = renamed.get(d['pi'], d['pi'])
        d['match'] = _selector(d.get('match'))
        if d['decision'] == 'hold_derived_school_flags':
            if set(d['match']) != {'oa', 'doi'} or d.get('scope') != 'derived_school_flags_only':
                raise ValueError('school flag hold needs exact oa+doi and derived_school_flags_only scope')
            if any(e.get('source_kind') not in ('partial_fulltext_jats', 'primary_pdf', 'publisher_author_affiliations')
                   for e in evidence):
                raise ValueError('school flag hold needs an explicit supported primary source kind')
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
    # prepare() freezes the reviews for this build. Index one required identifier
    # from each selector, then keep matches() as the complete-selector check.
    # Build lazily too: a resumed context can contain already validated reviews.
    if not hasattr(ctx, '_paper_claim_exclusion_index'):
        by_pi = {}
        for order, d in enumerate(prepare(ctx)):
            if d['decision'] in ('hold', 'reject'):
                field = next(k for k in ('oa', 'doi', 'work') if k in d['match'])
                by_pi.setdefault(d['pi'], {}).setdefault(field, {}).setdefault(d['match'][field], []).append((order, d))
        ctx._paper_claim_exclusion_index = by_pi
    index = ctx._paper_claim_exclusion_index.get(pi, {})
    candidates = {}
    if index:
        for record in [work] + list(work.get('editions') or []):
            for field, values in index.items():
                value = ((record.get('oa') or record.get('id')) if field == 'oa'
                         else ndoi(record.get('doi')) if field == 'doi' else record.get('work'))
                if isinstance(value, str):
                    candidates.update(values.get(value, ()))
    selected = [d for _, d in sorted(candidates.items()) if matches(work, d['match'])]
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


def _primary_matches(row, selector):
    """Match only this complete eligible record, never a compact folded-edition pointer."""
    return matches(dict(row, editions=[]), selector)


def preferred_edition(ctx, group):
    """Resolve exact reviewed merge targets while complete normally eligible edition records still exist.

    This chooses metadata already admitted by native identity/school/time/type gates. It cannot reconstruct a lead
    from compact edition fields, admit a missing target or use a title as an identifier. Other-title merges still run
    in apply(); their native rows remain independently eligible.
    """
    edges, selected = {}, {}

    def find(d, selector):
        found = [i for i, r in enumerate(group) if r['pi'] == d['pi'] and _primary_matches(r, selector)]
        if len(found) > 1:
            raise ValueError('ambiguous preferred edition selector: ' + d['id'])
        return found[0] if found else None

    for d in prepare(ctx):
        if d['decision'] != 'merge':
            continue
        source = find(d, d['match'])
        if source is None:
            continue
        target = find(d, d['into'])
        if target is None:
            continue  # missing/other-group targets are handled conservatively by apply()
        if source in selected:
            raise ValueError('multiple preferred destinations for one eligible claim: ' + d['id'])
        selected[source] = d
        if source != target:
            edges[source] = target
    if not selected:
        return None

    def root(i, trail=()):
        if i in trail:
            raise ValueError('cycle in reviewed preferred editions')
        return root(edges[i], trail + (i,)) if i in edges else i

    roots = {root(i) for i in selected}
    if len(roots) != 1:
        raise ValueError('conflicting reviewed preferred targets in one eligible edition group')
    chosen = group[roots.pop()]
    targets = getattr(ctx, '_paper_preferred_targets', {})
    target = {k: chosen.get(k) for k in ('oa', 'doi', 'work') if chosen.get(k)}
    target = _selector(target)
    for d in selected.values():
        targets[d['id']] = target
    ctx._paper_preferred_targets = targets
    ctx.n['paper_review_preferred_edition_groups'] += 1
    return chosen


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
        if d['decision'] not in ('hold', 'reject'):
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
            preferred = getattr(ctx, '_paper_preferred_targets', {}).get(d['id'])
            if _primary_matches(rows[source], d['into']) or (preferred and _primary_matches(rows[source], preferred)):
                outcomes[d['id']]['outcome'] = 'preferred_edition_selected' if preferred else 'already_merged'
                continue
            # Both identifiers survive only as one folded row, whose lead is not the requested target. The full
            # target metadata is unavailable here; never synthesize an affiliation/appointment from edition fields.
            if source in edges or source in missing:
                raise ValueError('multiple merge destinations for one eligible claim: ' + d['id'])
            merge_sources[source] = d; missing.add(source)
            outcomes[d['id']]['outcome'] = 'held_missing_preferred_target_record'
            continue
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
            if outcomes[d['id']]['outcome'] != 'held_missing_preferred_target_record':
                outcomes[d['id']]['outcome'] = 'held_missing_merge_target'
            held_missing += 1
        else:
            kept[target] = _joined(kept[target], rows[i])
            outcomes[d['id']]['outcome'] = 'merged'; merged += 1
        kept.pop(i, None)
    school_flag_policy.apply(ctx, kept)
    # Apply exact flags-only holds last, after all normal eligibility and edition decisions.
    # Empty flags mean withheld/unknown, never a verified absence of school authors.
    # A matched folded edition withholds the whole claim's derived flags so neither
    # legacy fallback nor another positive derivation can restore an unreliable list.
    for d in decisions:
        if d['decision'] != 'hold_derived_school_flags':
            continue
        i = find(d, d['match'], kept)
        if i is None:
            continue
        row = kept[i]
        row['byline_school'] = []
        if '_bylines' in row:
            row['_bylines'] = [(names, []) for names, _ in row['_bylines']]
        evidence = dict(status='held', scope='derived_school_flags_only', id=d['id'],
                        reason=d['why'], match=copy.deepcopy(d['match']),
                        input_sha256=ctx.paper_claim_review['sha256'],
                        reviewed_by=d['reviewed_by'], reviewed_at=d['reviewed_at'],
                        evidence=copy.deepcopy(d['evidence']))
        if 'byline_affiliation_review' in row:
            evidence['prior_derivation'] = row['byline_affiliation_review']
        row['byline_affiliation_review'] = evidence
        outcomes[d['id']]['outcome'] = 'derived_school_flags_held'
    ctx.rows = [kept[i] for i in sorted(kept)]
    ctx.paper_claim_review['decisions'] = [outcomes[d['id']] for d in decisions]
    n = ctx.n
    n['paper_review_derived_school_flags_held'] = sum(x['outcome'] == 'derived_school_flags_held' for x in outcomes.values())
    n['paper_review_rows_held'] = sum(v == 'hold' for v in actions.values()) + held_missing
    n['paper_review_rows_rejected'] = sum(v == 'reject' for v in actions.values())
    n['paper_review_editions_merged'] = merged
    n['paper_review_preferred_editions_selected'] = sum(x['outcome'] == 'preferred_edition_selected' for x in outcomes.values())
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
