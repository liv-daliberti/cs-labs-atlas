"""Read shared and school-local department decisions from one selected hierarchy.

A local hold cannot revive an old shared assignment. Explicit local reviews win;
otherwise retain shared reviews and expose disagreements in the separate audit.
Never fall back to live data when reading a dated release.
"""
import json
import re

import atlas_paths as P


def valid_evidence(row):
    e = (row or {}).get('evidence') or {}
    return bool(e.get('url') and re.fullmatch(r'[0-9a-f]{64}', str(e.get('sha256') or ''))
                and str(e.get('quote') or '').strip())


def merge_rows(shared, local, school):
    """One decision per exact school/name; retain holds and primary ambiguity."""
    out = {}
    for rows, is_local in ((shared, False), (local, True)):
        seen = {}
        for r in rows:
            if r.get('school', school) != school:
                continue
            name = r['name']
            if name in seen:
                keys = ('status', 'home_department', 'home_basis', 'also', 'primary_unresolved', 'no_academic_department')
                if any(seen[name].get(k) != r.get(k) for k in keys):
                    raise ValueError(f'conflicting duplicate home department decision: {school}/{name}')
                if valid_evidence(seen[name]):
                    continue
            seen[name] = r
            old = out.get(name)
            explicit = r.get('reviewed_home_evidence') or r.get('home_basis') == 'primary_stated'
            if not is_local or old is None or r.get('status') != 'accepted' or explicit:
                out[name] = dict(r, school=school)
    return list(out.values())


def load(school, hierarchy=None, reader=None):
    """All decisions from this hierarchy only (live or release)."""
    hierarchy = hierarchy if hierarchy is not None else P.HIERARCHY
    reader = reader or (lambda path: json.loads(path.read_text()))
    shared = P.hfile(hierarchy, 'home-departments.json')
    local = P.hfile(hierarchy, 'home-departments-school.json', school)
    return merge_rows(reader(shared) if shared.exists() else [], reader(local) if local.exists() else [], school)


def accepted(school, hierarchy=None, reader=None):
    """Accepted homes with complete recorded evidence; primary may be unresolved."""
    return {r['name']: r for r in load(school, hierarchy, reader)
            if r.get('status') == 'accepted' and r.get('home_department') and valid_evidence(r)}


def review(row):
    """Portable decision metadata, including unresolved primary appointments."""
    if not row:
        return dict(status='missing', home_department=None, home_basis=None, primary_resolved=False)
    return {**{k: row.get(k) for k in ('status', 'home_department', 'home_basis', 'evidence', 'note')},
            'also': row.get('also') or [], 'primary_unresolved': row.get('primary_unresolved') or [],
            'primary_resolved': bool(row.get('status') == 'accepted' and row.get('home_department')
                                     and row.get('home_basis') in ('primary_stated', 'listed_title')
                                     and not row.get('primary_unresolved') and valid_evidence(row)),
            'no_academic_department': bool(row.get('no_academic_department'))}
