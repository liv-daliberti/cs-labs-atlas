"""Reproducible draw for the CS Labs Atlas accuracy measurement (2026-10-29).

Per school, one random.Random(20261029), consumed in this fixed order:
  1. lab_precision     25 uniform lab_papers rows, then 5 per risky stratum, each drawn from the rows not yet drawn:
                       'advisee_unaffiliated' (authorship.school_via[0] starts with 'advisee on an unaffiliated byline'),
                       'listing' (appointment is a listing, not a periodId), 'identity_not_reviewed' (identity is not
                       'reviewed_openalex_author_id'). A stratum smaller than 5 is taken whole.
  2. student_precision 25 uniform student_papers rows, then 5 each of 'within_lab_byline_match',
                       'advisee_name_on_lab_paper_byline', 'full_name_on_lab_paper_byline'; a stratum with fewer than 5
                       rows left is taken whole and the shortfall is filled uniformly ('fill_uniform').
  3. lab_coverage      15 records drawn uniformly from the pool of (PI, DBLP record) pairs: every record on the PI's own
                       DBLP person pages (hierarchy/dblp-dump-persons.json.gz, read from DBLP's 2026-09-01 dump) of type
                       article or inproceedings, not a CoRR preprint (journals/corr), dated 2016-2026 (the build's sweep
                       window) and inside one of the PI's periods (start year..end year, or the as-of year when open) or a
                       year with a department listing. Pool order: pis.json order, then DBLP key.
  4. student_coverage  the school's students with a documented thesis/dissertation advisor relation to the PI and PhD
                       year >= 2018, shuffled; they are judged in this order and the first 10 confirmed PhD students
                       form the sample (candidates screened out, e.g. a master's thesis, go to screened.jsonl).
Rows are addressed by their position in the file and by a key; the package files' sha256 are recorded with the draw.
-> work/accuracy/sample.json
usage: sample.py [--school <key>] | --round <id> [--school <key>]
  --round r2      the 2026-11-02 round: seed 20261102, 50 uniform rows per school for lab precision, student precision and lab
                  coverage (+ the 5-row risky strata), up to 200 shuffled student-coverage candidates (the judge takes the first 50
                  confirmed PhD students); accuracy/round-r2/sample-<school>.json for the seven released schools. The sizes are
                  ROUNDS in this file; the 2026-10-29 draw (LEGACY, seed 20261029) and its verdicts are history.
  --school <key>  draw one school (any charter, released or onboarding) with the same seed and method into
                  accuracy/sample-<key>.json; sample.json and the six released draws are untouched (tests/test_accuracy_sample_school.py).
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[1] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, hashlib, json, random, re

SEED = 20261029
ROOT = P.CODE
OUT = ROOT / 'accuracy' / 'sample.json'
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']
# The draw's sizes. LEGACY is the 2026-10-29 measurement (25 uniform rows per precision sample, 5 per risky stratum, 15 coverage
# records, the first 40 shuffled student-coverage candidates kept). ROUNDS holds the later ones: r2 (owner 2026-11-02) draws 50
# uniform rows per school for lab precision, student precision and lab coverage, keeps the 5-row risky strata on top of them, and
# keeps up to 200 shuffled student-coverage candidates, of which the judge takes the first 50 confirmed PhD students (a school with
# fewer candidates, or fewer confirmed ones, is judged as far as it goes and reported with its smaller n). A round has its own seed
# and its own files (accuracy/round-<id>/); the 2026-10-29 draws and verdicts are history and are never rewritten.
ACC_DIR = _Path(__file__).resolve().parent
LEGACY = dict(seed=SEED, uniform=25, stratum=5, cov=15, cands=40, schools=SCHOOLS, dir=None)
ROUNDS = {'r2': dict(seed=20261102, uniform=50, stratum=5, cov=50, cands=200,
                     schools=['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan'], dir='round-r2')}
FILES = ['pis.json', 'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'copies.json']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def dblp_persons(wanted):
    """Stream the persons map of dblp-dump-persons.json.gz one record at a time (the file is ~95 MB of JSON; only the
    wanted person pages are kept)."""
    s = gzip.open(P.data('dblp-dump-persons.json.gz'), 'rt').read()
    dec = json.JSONDecoder()
    i = s.index('"persons"'); i = s.index('{', i) + 1
    out = {}
    while True:
        while s[i] in ' \n\r\t,':
            i += 1
        if s[i] == '}':
            break
        key, i = dec.raw_decode(s, i)
        i = s.index(':', i) + 1
        while s[i] in ' \n\r\t':
            i += 1
        obj, i = dec.raw_decode(s, i)
        if key in wanted:
            out[key] = [dict(key=r['key'], type=r['type'], title=r.get('title'), year=r.get('year'), dois=r.get('dois') or [],
                             authors=[a[0] for a in r.get('authors') or []]) for r in obj.get('pubs') or []]
    del s
    return out


def years_in(p):
    ys = set()
    for q in p.get('periods') or []:
        a = int(str(q['start'])[:4]) if q.get('start') else 2016
        b = int(str(q['end'])[:4]) if q.get('end') else int(str(q.get('asof') or '2026')[:4])
        ys |= set(range(max(a, 2016), min(b, 2026) + 1))
    ys |= {l['year'] for l in p.get('listings') or [] if l.get('year')}
    return ys


PHD = re.compile(r'(?i)\bph\.?\s?d\b|doctoral|dissertation')
MASTER = re.compile(r'(?i)master|\bm\.?\s?eng\b|\bs\.?m\.\b|mastersthesis|senior thesis|undergrad|\bb\.?s\.?\b')


def thesis_relation(rel, school, roles=()):
    """A relation documented by a thesis or dissertation source that shows a doctorate (the source itself, the relation
    type, or the student's recorded PhD role); returns its PhD year (or None). Undergraduate senior theses and master's
    theses are left out; an MIT DSpace thesis (degree not recorded in students.json) passes unless the student's roles
    say undergraduate or master's, and is screened at judgment time."""
    phd_role = any(re.search(r'(?i)phd|doctoral', r) for r in roles)
    low_role = any(re.search(r'(?i)undergrad|master', r) for r in roles)
    for so in rel.get('sources') or []:
        kind, url, quote = str(so.get('kind') or ''), str(so.get('url') or ''), str(so.get('quote') or '')
        if MASTER.search(quote) and not PHD.search(quote):
            continue
        thesis = rel.get('type') == 'thesis_adviser' or kind in ('phd_thesis', 'epfl_thesis') or kind.startswith('dept_thesis') \
            or 'Doctoral Dissertation Advisor' in quote or re.search(r'Degree:\s*PhD', quote) \
            or (school == 'princeton' and re.search(r'arks\.princeton\.edu|dataspace', url)) \
            or (school == 'mit' and 'dspace.mit.edu/server/api/core/items' in url)
        if not thesis:
            continue
        doctoral = PHD.search(quote) or kind in ('phd_thesis', 'epfl_thesis') or rel.get('type') == 'thesis_adviser' \
            or phd_role or (school == 'mit' and not low_role)
        if not doctoral or (low_role and not phd_role and not PHD.search(quote)):
            continue
        m = re.search(r'Degree:\s*PhD,\s*(\d{4})', quote)
        ys = [int(m.group(1))] if m else [int(y) for y in rel.get('years') or [] if str(y).isdigit()]
        if ys:
            return max(ys)
    return None


def alumni_relation(rel, roles):
    """Fallback for a school onboarded under the protocol whose build holds no thesis-database source (Michigan: Deep Blue is
    never used, so a relation comes from the lab's own alumni page, a student's homepage or a defense listing): the student's
    recorded role is PhD alumnus, and the relation's last year is returned. Used only for schools outside SCHOOLS, so the six
    released draws cannot change."""
    if not any(r == 'phd_alumnus' for r in roles) or rel.get('type') not in ('researched_advising', 'thesis_adviser'):
        return None
    ys = [int(y) for y in rel.get('years') or [] if str(y).isdigit()]
    return max(ys) if ys else None


def main(schools=None, out_path=None, date='2026-10-29', cfg=None):
    cfg = cfg or LEGACY
    out = {'seed': cfg['seed'], 'date': date, 'sizes': {k: cfg[k] for k in ('uniform', 'stratum', 'cov', 'cands')}, 'schools': {}, 'files': {}}
    if cfg is LEGACY:
        del out['sizes']  # the 2026-10-29 files never carried it
    for school in schools or cfg['schools']:
        rng = random.Random(cfg['seed'])
        d = P.SchoolDir(school)
        out['files'][school] = {f: sha(d / f) for f in FILES}
        # 1. lab papers
        meta = []
        for i, line in enumerate(gzip.open(d / 'lab_papers.jsonl.gz', 'rt')):
            r = json.loads(line)
            via = (r['authorship'].get('school_via') or [''])[0]
            meta.append(dict(i=i, key=f"{r['pi']}|{r['work']}|{r['oa']}", adv=via.startswith('advisee on an unaffiliated byline'),
                             listing='listing' in (r.get('appointment') or {}), nonrev=r.get('identity') != 'reviewed_openalex_author_id'))
        lab = []
        taken = set(rng.sample(range(len(meta)), min(cfg['uniform'], len(meta))))
        lab += [dict(stratum='uniform', i=i, key=meta[i]['key']) for i in sorted(taken)]
        for st, f in (('advisee_unaffiliated', 'adv'), ('listing', 'listing'), ('identity_not_reviewed', 'nonrev')):
            pool = [m['i'] for m in meta if m[f] and m['i'] not in taken]
            pick = rng.sample(pool, min(cfg['stratum'], len(pool)))
            taken |= set(pick)
            lab += [dict(stratum=st, i=i, key=meta[i]['key']) for i in sorted(pick)]
        # 2. student papers
        sm = []
        for i, line in enumerate(gzip.open(d / 'student_papers.jsonl.gz', 'rt')):
            r = json.loads(line)
            sm.append(dict(i=i, key=f"{r['pi']}|{r['student']}|{r['oa']}", basis=r.get('basis')))
        stu = []
        taken = set(rng.sample(range(len(sm)), min(cfg['uniform'], len(sm))))
        stu += [dict(stratum='uniform', i=i, key=sm[i]['key']) for i in sorted(taken)]
        short = 0
        for st in ('within_lab_byline_match', 'advisee_name_on_lab_paper_byline', 'full_name_on_lab_paper_byline'):
            pool = [m['i'] for m in sm if m['basis'] == st and m['i'] not in taken]
            pick = rng.sample(pool, min(cfg['stratum'], len(pool)))
            short += cfg['stratum'] - len(pick)
            taken |= set(pick)
            stu += [dict(stratum=st, i=i, key=sm[i]['key']) for i in sorted(pick)]
        if short:
            pool = [m['i'] for m in sm if m['i'] not in taken]
            pick = rng.sample(pool, short)
            taken |= set(pick)
            stu += [dict(stratum='fill_uniform', i=i, key=sm[i]['key']) for i in sorted(pick)]
        # 3. lab coverage from DBLP person pages
        pis = json.load(open(d / 'pis.json'))
        wanted = {q for p in pis for q in p.get('dblp') or []}
        pages = dblp_persons(wanted)
        pool, seen = [], set()
        for p in pis:
            ys = years_in(p)
            recs = sorted((r for q in p.get('dblp') or [] for r in pages.get(q, [])), key=lambda r: r['key'])
            for r in recs:
                if r['type'] not in ('article', 'inproceedings') or r['key'].startswith('journals/corr/') or not r.get('year'):
                    continue
                if not (2016 <= r['year'] <= 2026) or r['year'] not in ys or (p['pi'], r['key']) in seen:
                    continue
                seen.add((p['pi'], r['key']))
                pool.append(dict(pi=p['pi'], key=f"{p['pi']}|{r['key']}", dblp=r))
        cov = [dict(stratum='dblp_person_page', **pool[i]) for i in sorted(rng.sample(range(len(pool)), min(cfg['cov'], len(pool))))]
        del pages
        # 4. student coverage candidates
        stj = json.load(open(d / 'students.json'))
        cands = []
        for p in pis:
            for s in stj.get(p['pi']) or []:
                ys = [y for rel in s.get('relations') or [] for y in [thesis_relation(rel, school, s.get('roles') or [])] if y]
                if not ys and school not in SCHOOLS:
                    ys = [y for rel in s.get('relations') or [] for y in [alumni_relation(rel, s.get('roles') or [])] if y]
                if ys and max(ys) >= 2018:
                    cands.append(dict(key=f"{p['pi']}|{s['person']}", pi=p['pi'], person=s['person'], name=s['name'], phd_year=max(ys)))
        rng.shuffle(cands)
        out['schools'][school] = dict(n_lab_papers=len(meta), n_student_papers=len(sm), n_coverage_pool=len(pool),
                                      n_student_candidates=len(cands), lab_precision=lab, student_precision=stu,
                                      lab_coverage=cov, student_coverage_order=cands[:cfg['cands']])
        del stj, pis, meta, sm, pool
        print(school, len(lab), len(stu), len(cov), len(cands), flush=True)
    (out_path or OUT).write_text(json.dumps(out, indent=1))
    return out


def draw_round(rnd, schools=None):
    """Draw the schools of round `rnd` (ROUNDS) into accuracy/round-<id>/sample-<school>.json, one file per school (the seed is
    reset per school, so a school's draw does not depend on which others are drawn). An existing draw file is never
    overwritten: a draw is the record the verdicts refer to."""
    import datetime
    cfg = ROUNDS[rnd]
    d = ACC_DIR / cfg['dir']  # beside this file: a worktree's own accuracy/, not the main checkout's
    d.mkdir(exist_ok=True)
    for school in schools or cfg['schools']:
        f = d / f'sample-{school}.json'
        if f.exists():
            _sys.exit(f'{f} exists: a round draw is never overwritten (move it aside by hand to redraw)')
        main([school], f, datetime.date.today().isoformat(), cfg)


if __name__ == '__main__':
    a = _sys.argv[1:]
    if a[:1] == ['--round'] and len(a) in (2, 4) and a[1] in ROUNDS and (len(a) == 2 or a[2] == '--school'):
        draw_round(a[1], a[3:] or None)
    elif len(a) == 2 and a[0] == '--school':
        import datetime
        main([a[1]], _Path(__file__).resolve().parent / f'sample-{a[1]}.json', datetime.date.today().isoformat())
    elif not a:
        main()
    else:
        _sys.exit(__doc__)
