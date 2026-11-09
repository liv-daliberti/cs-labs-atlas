"""Missed-labs leads (coordinator brief 2026-11-09): people tied to a school by the held data who are NOT in its census.

sources, all already held (no crawling, no OpenAlex credits):
  oa       hierarchy/<school>/derived/oa-author-stats.json.gz: OpenAlex author ids with 3+ school works; kept when >= MIN_CS of
           them are DBLP-indexed (the CS-venue test of cs_related_candidates.py) and the author is not matched to the census
  dblp     derived/dblp-affiliated.json persons (affiliation note names the school, 5+ records 2016-2026) not in the census
  listed   derived/listed-not-in-census.json (names a captured department listing calls faculty)
excluded: anyone matching a census row or alias, a student / postdoc / member of any PI in derived/students.json.
-> prints / writes a JSON list of {name, sources, oa_ids, cs, works, last, years, prior_decision}; ranking is by cs count then recency.
CSRankings is never read here (licence: discovery lead only, by hand).
usage: missed_labs_leads.py <school> [--min-cs 5] [--out FILE]
"""
import argparse, gzip, json, sys
from collections import defaultdict
from pathlib import Path

import atlas_paths as P  # noqa: E402
from pi_hierarchy import Name, toks  # noqa: E402


def load(p, gz=False):
    p = Path(p)
    if not p.exists():
        return None
    return json.load(gzip.open(p, 'rt') if gz else open(p))


def best_name(raw):
    """The fullest 'First Last' spelling among an author's raw names (initial-only forms last)."""
    def key(item):
        n, c = item
        t = toks(n)
        return (sum(1 for x in t if len(x) > 1), c)
    n = max(raw.items(), key=key)[0]
    if ',' in n and n.count(',') == 1:
        a, b = n.split(','); n = f'{b.strip()} {a.strip()}'
    return n


def build(school, min_cs=5):
    d = P.data  # layout-aware
    cen = load(d('census-faculty.json', school))['faculty']
    census = [Name([r['name'], *r.get('aliases', [])]) for r in cen]
    by_last = defaultdict(list)
    for r, nm in zip(cen, census):
        for _, last in nm.forms:
            by_last[last].append((r['name'], nm))

    def in_census(raw):
        t = toks(raw)
        if len(t) < 2:
            return None
        for cand in {t[-1], ''.join(t[1:]), ''.join(t[-2:])}:
            for who, nm in by_last.get(cand, []):
                if nm.match(raw):
                    return who
        return None

    stu = load(d('students.json', school)) or {}
    stu_names = {p['name'] for v in stu.values() for p in v if p.get('name')}
    stu_by = defaultdict(list)
    for n in stu_names:
        t = toks(n)
        if len(t) >= 2:
            stu_by[t[-1]].append(Name([n]))

    def is_student(raw):
        t = toks(raw)
        return len(t) >= 2 and any(nm.match(raw) for nm in stu_by.get(t[-1], []))

    prior = {}
    for f in ('cs-related-review.json',):
        r = load(Path(P.data('reviewed/' + f, school)) if False else Path(P.CODE) / 'hierarchy' / school / 'reviewed' / f)
        for x in (r or {}).get('decisions', []):
            for n in [x['name'], *x.get('aliases', [])]:
                prior[n] = x['decision']
    prior_by = defaultdict(list)
    for n, dec in prior.items():
        t = toks(n)
        if len(t) >= 2:
            prior_by[t[-1]].append((Name([n]), dec))

    def prior_of(raw):
        t = toks(raw)
        for nm, dec in prior_by.get(t[-1] if t else '', []):
            if nm.match(raw):
                return dec
        return None

    leads = {}

    def add(name, src, **kw):
        k = ' '.join(toks(name))
        e = leads.setdefault(k, {'name': name, 'sources': [], 'oa_ids': [], 'cs': 0, 'works': 0, 'last': 0, 'years': [], 'dblp': []})
        if src not in e['sources']:
            e['sources'].append(src)
        for key in ('oa_ids', 'dblp'):
            for v in kw.get(key, []):
                if v not in e[key]:
                    e[key].append(v)
        for key in ('cs', 'works', 'last'):
            e[key] = max(e[key], kw.get(key, 0))
        if kw.get('years'):
            e['years'] = [min(e['years'] + [kw['years'][0]]), max(e['years'] + [kw['years'][-1]])]

    stats = load(d('oa-author-stats.json.gz', school), gz=True)
    n_oa = 0
    for aid, a in (stats or {}).get('authors', {}).items():
        if a.get('cs', 0) < min_cs:
            continue
        nm = best_name(a['raw'])
        if len(toks(nm)) < 2 or in_census(nm) or any(in_census(r) for r in a['raw']):
            continue
        n_oa += 1
        add(nm, 'oa', oa_ids=[aid], cs=a['cs'], works=a['n'], last=a['last'], years=a.get('years') or [])
    n_db = 0
    for p in (load(d('dblp-affiliated.json', school)) or {}).get('persons', []):
        names = p.get('names') or ([p['name']] if p.get('name') else [])
        if not names or p.get('disambiguation') or any(in_census(a) for a in names) or len(toks(names[0])) < 2:
            continue
        if p.get('n_window', 0) < min_cs:
            continue
        n_db += 1
        yrs = sorted(int(y) for y in (p.get('pubs_by_year') or {}))
        add(names[0], 'dblp', dblp=[p['pid']], cs=p.get('n_window', 0), works=p.get('n_window', 0), years=yrs)
    n_ls = 0
    for p in load(d('listed-not-in-census.json', school)) or []:
        n_ls += 1
        add(p['name'], 'listed', years=sorted(p.get('years') or []))
    out = []
    for e in leads.values():
        e['student_or_member'] = is_student(e['name'])
        e['prior_decision'] = prior_of(e['name'])
        out.append(e)
    out.sort(key=lambda e: (-e['cs'], -(e['years'][-1] if e['years'] else 0)))
    return out, {'oa': n_oa, 'dblp': n_db, 'listed': n_ls}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('school'); ap.add_argument('--min-cs', type=int, default=5); ap.add_argument('--out')
    a = ap.parse_args()
    out, n = build(a.school, a.min_cs)
    print(a.school, 'candidates per source (before dedupe):', n, '| distinct leads:', len(out),
          '| student/member:', sum(e['student_or_member'] for e in out))
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1, ensure_ascii=False)
