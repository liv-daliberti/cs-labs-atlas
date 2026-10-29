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
usage: sample.py
"""
import gzip, hashlib, json, random, re
from pathlib import Path

SEED = 20261029
ROOT = Path('/n/fs/resemble/cs-atlas/work')
H = ROOT / 'hierarchy'
OUT = ROOT / 'accuracy' / 'sample.json'
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']
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
    s = gzip.open(H / 'dblp-dump-persons.json.gz', 'rt').read()
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


def thesis_relation(rel, school):
    """A relation documented by a thesis or dissertation source; returns its PhD year (or None)."""
    for so in rel.get('sources') or []:
        kind, url, quote = str(so.get('kind') or ''), str(so.get('url') or ''), str(so.get('quote') or '')
        t = ' '.join((kind, url, quote))
        if MASTER.search(quote) and not PHD.search(quote):
            continue
        ok = rel.get('type') == 'thesis_adviser' or kind in ('phd_thesis', 'epfl_thesis') or kind.startswith('dept_thesis') \
            or 'Doctoral Dissertation Advisor' in quote or re.search(r'Degree:\s*PhD', quote) \
            or (school == 'princeton' and re.search(r'arks\.princeton\.edu|dataspace', url)) \
            or (school == 'mit' and 'dspace.mit.edu/server/api/core/items' in url)
        if not ok:
            continue
        m = re.search(r'Degree:\s*PhD,\s*(\d{4})', quote)
        ys = [int(m.group(1))] if m else [int(y) for y in rel.get('years') or [] if str(y).isdigit()]
        if ys:
            return max(ys)
    return None


def main():
    out = {'seed': SEED, 'date': '2026-10-29', 'schools': {}, 'files': {}}
    for school in SCHOOLS:
        rng = random.Random(SEED)
        d = H / school
        out['files'][school] = {f: sha(d / f) for f in FILES}
        # 1. lab papers
        meta = []
        for i, line in enumerate(gzip.open(d / 'lab_papers.jsonl.gz', 'rt')):
            r = json.loads(line)
            via = (r['authorship'].get('school_via') or [''])[0]
            meta.append(dict(i=i, key=f"{r['pi']}|{r['work']}|{r['oa']}", adv=via.startswith('advisee on an unaffiliated byline'),
                             listing='listing' in (r.get('appointment') or {}), nonrev=r.get('identity') != 'reviewed_openalex_author_id'))
        lab = []
        taken = set(rng.sample(range(len(meta)), 25))
        lab += [dict(stratum='uniform', i=i, key=meta[i]['key']) for i in sorted(taken)]
        for st, f in (('advisee_unaffiliated', 'adv'), ('listing', 'listing'), ('identity_not_reviewed', 'nonrev')):
            pool = [m['i'] for m in meta if m[f] and m['i'] not in taken]
            pick = rng.sample(pool, min(5, len(pool)))
            taken |= set(pick)
            lab += [dict(stratum=st, i=i, key=meta[i]['key']) for i in sorted(pick)]
        # 2. student papers
        sm = []
        for i, line in enumerate(gzip.open(d / 'student_papers.jsonl.gz', 'rt')):
            r = json.loads(line)
            sm.append(dict(i=i, key=f"{r['pi']}|{r['student']}|{r['oa']}", basis=r.get('basis')))
        stu = []
        taken = set(rng.sample(range(len(sm)), 25))
        stu += [dict(stratum='uniform', i=i, key=sm[i]['key']) for i in sorted(taken)]
        short = 0
        for st in ('within_lab_byline_match', 'advisee_name_on_lab_paper_byline', 'full_name_on_lab_paper_byline'):
            pool = [m['i'] for m in sm if m['basis'] == st and m['i'] not in taken]
            pick = rng.sample(pool, min(5, len(pool)))
            short += 5 - len(pick)
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
        cov = [dict(stratum='dblp_person_page', **pool[i]) for i in sorted(rng.sample(range(len(pool)), min(15, len(pool))))]
        del pages
        # 4. student coverage candidates
        stj = json.load(open(d / 'students.json'))
        cands = []
        for p in pis:
            for s in stj.get(p['pi']) or []:
                ys = [y for rel in s.get('relations') or [] for y in [thesis_relation(rel, school)] if y]
                if ys and max(ys) >= 2018:
                    cands.append(dict(key=f"{p['pi']}|{s['person']}", pi=p['pi'], person=s['person'], name=s['name'], phd_year=max(ys)))
        rng.shuffle(cands)
        out['schools'][school] = dict(n_lab_papers=len(meta), n_student_papers=len(sm), n_coverage_pool=len(pool),
                                      n_student_candidates=len(cands), lab_precision=lab, student_precision=stu,
                                      lab_coverage=cov, student_coverage_order=cands[:40])
        del stj, pis, meta, sm, pool
        print(school, len(lab), len(stu), len(cov), len(cands), flush=True)
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
