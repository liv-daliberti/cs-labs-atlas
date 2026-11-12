"""Student candidates for the self-declared (OpenReview) route, R-STU-27: the frozen 7-feature candidate rule of the 2026-11-13 pilot,
as a reusable generator over a school's derived lab_papers / pis / students.

A candidate is a non-PI co-author with a school-affiliated byline (`byline_school`) on lab papers of a PI, 2016-2025, at most 15 authors.
Seven features per (candidate, PI): n3 (papers with the PI last author, capped 6, /6), share (those papers over all the candidate's papers),
excl (this PI has strictly the most last-author papers), early (first lab paper within a year of the candidate's first paper), cont (last-author
span 1-7 years), pos (first or second author once), nonfac (not a faculty name of the school). Logistic weights and threshold are FROZEN from
scratch/selfdeclared-pilot-1113/results2.json (tuning PIs only; F0.5 .48, thr -0.642); a candidate is only a name to look up, never evidence.

  selfdeclared_candidates.py <school> [--all] [--out FILE]    candidates, student-less and few-student PIs first
"""
import argparse
import collections
import gzip
import json
import re
import sys
import unicodedata
from pathlib import Path

import atlas_paths as P  # noqa: E402
from pihier.names import toks  # noqa: E402

YEARS = (2016, 2025)
MAX_AUTHORS = 15
FEW = 3   # a PI with fewer students than this is a priority target
FEATS = ('n3', 'share', 'excl', 'early', 'cont', 'pos', 'nonfac')
WEIGHTS = dict(n3=0.661, share=0.267, excl=0.615, early=0.277, cont=0.723, pos=0.928, nonfac=0.458, bias=-3.51)   # frozen 2026-11-13
THRESHOLD = -0.642


def latin(name):
    """The Latin-letter reading of a (possibly bilingual) name: accents folded, CJK and other scripts dropped; '' when nothing is left."""
    s = unicodedata.normalize('NFKD', str(name or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(re.sub(r"[^A-Za-z' .-]", ' ', s).replace('.', ' ').split())


def key(name):
    return ' '.join(sorted(toks(name)))


def pi_latin_names(pi):
    out = []
    for n in list(pi.get('names') or []) + [pi.get('pi')]:
        s = latin(n)
        if len(s.split()) >= 2 and s not in out:
            out.append(s)
    return out


def pi_window(pi):
    """(first, last) year of the PI's appointment here: the periods, else the listing years, else open."""
    ys = []
    for q in pi.get('periods') or []:
        s = str(q.get('start') or '')[:4]
        e = str(q.get('end') or '')[:4]
        if s.isdigit():
            ys.append((int(s), int(e) if e.isdigit() else 2026))
    if ys:
        return min(a for a, _ in ys), max(b for _, b in ys)
    ls = [x['year'] for x in pi.get('listings') or [] if isinstance(x, dict) and x.get('year')]
    return (min(ls), max(ls)) if ls else (1990, 2026)


def score(feat):
    z = WEIGHTS['bias'] + sum(WEIGHTS[f] * (min(feat['n3'], 6) / 6 if f == 'n3' else feat[f]) for f in FEATS)
    return z


def features(papers, pi_keys):
    """Per (candidate key, PI): the feature dict. `papers` are lab_papers rows."""
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    allp = collections.defaultdict(set)
    for x in papers:
        if not (YEARS[0] <= (x.get('year') or 0) <= YEARS[1]) or len(x.get('byline') or []) > MAX_AUTHORS:
            continue
        au = x.get('authorship') or {}
        raw = au.get('raw_name') or ''
        bl = x['byline']
        last = au.get('position') == 'last' or (au.get('position') is None and bool(bl) and key(bl[-1]) == key(raw))
        for n in x.get('byline_school') or []:
            if key(n) == key(raw):
                continue
            k = key(n)
            idx = next((i for i, b in enumerate(bl) if b == n), 99)
            per[k][x['pi']].append((x['year'], idx, last, n))
            allp[k].add((x.get('oa') or x.get('title'), x['year']))
    rows = []
    for k, d in per.items():
        lastcnt = {pi: sum(1 for r in v if r[2]) for pi, v in d.items()}
        top = sorted(lastcnt.values(), reverse=True)
        first_all = min(y for _, y in allp[k])
        for pi, v in d.items():
            yrs = sorted(r[0] for r in v)
            ls = sorted(r[0] for r in v if r[2])
            n3 = len(ls)
            span = (ls[-1] - ls[0]) if ls else (yrs[-1] - yrs[0])
            f = dict(n3=n3, share=n3 / max(len(allp[k]), 1),
                     excl=int(lastcnt[pi] == top[0] and (len(top) == 1 or top[0] > top[1]) and top[0] > 0),
                     early=int(yrs[0] - first_all <= 1), cont=int(1 <= span <= 7 or (n3 >= 2 and span <= 7)),
                     pos=int(any(r[1] in (0, 1) for r in v)), nonfac=int(k not in pi_keys))
            rows.append(dict(pi=pi, name=v[0][3], key=k, feat=f, score=round(score(f), 3), first=yrs[0], last=yrs[-1]))
    return rows


def generate(school, include_all=False, base=None):
    """Candidates >= threshold, ordered: PIs with no student first, then fewer than FEW, then the rest (with include_all=False the rest is
    dropped), higher score first. Names need two Latin tokens. `base` overrides the data reader (tests)."""
    rd = base or (lambda n: _read(P.data(n, school)))
    pis = rd('pis.json')
    stu = rd('students.json') or {}
    papers = rd('lab_papers.jsonl.gz')
    by_pi = {p['pi']: p for p in pis}
    pi_keys = {key(n) for p in pis for n in list(p.get('names') or []) + [p['pi']]}
    out = []
    for r in features(papers, pi_keys):
        p = by_pi.get(r['pi'])
        nm = latin(r['name'])
        if not p or r['score'] < THRESHOLD or len(nm.split()) < 2:
            continue
        pn = pi_latin_names(p)
        if not pn:
            continue
        ns = len({key(x['name']) for x in stu.get(r['pi']) or []})
        if ns >= FEW and not include_all:
            continue
        out.append(dict(school=school, pi=r['pi'], pinames=pn, window=list(pi_window(p)), name=nm, score=r['score'], feat=r['feat'],
                        n_students=ns, years=[r['first'], r['last']]))
    out.sort(key=lambda c: (c['n_students'] > 0, c['n_students'], -c['score'], c['pi'], c['name']))
    return out


def _read(path):
    path = Path(path)
    if not path.exists():
        return None
    b = path.read_bytes()
    if path.suffix == '.gz':
        b = gzip.decompress(b)
        return [json.loads(line) for line in b.decode().splitlines() if line.strip()]
    return json.loads(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('school')
    ap.add_argument('--all', action='store_true', help='also PIs with >= 3 students')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    c = generate(a.school, a.all)
    out = Path(a.out) if a.out else P.SCRATCH / 'openreview-students' / f'candidates-{a.school}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(school=a.school, threshold=THRESHOLD, rows=c), ensure_ascii=False))
    print(a.school, 'candidates', len(c), 'unique names', len({x['name'] for x in c}), 'pis', len({x['pi'] for x in c}), '->', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
