#!/usr/bin/env python3
"""Check the CS departments data (atlas/data/cs-hierarchy) against the owner rules it implements (AGENTS.md, 2026-10-21).

- school -> department -> lab: every lab sits in exactly one department list, has exactly one PI, and is no collective
  (centre, initiative, consortium, programme, project, cluster);
- papers: each lab paper retains the source package's school connection (direct affiliation, reviewed first-page
  evidence, or the upstream advisee-coauthor rules) and its appointment basis holds:
  a faculty period, or a listing of the PI from the paper's own calendar year, carried on the lab;
- students and links: every link joins a student of that lab to a paper of that lab;
- the labs CSV and index agree with the per-school files;
- hidden labs (owner 2026-10-22, "PI labs with papers only"): hidden-labs.json lists exactly the labs with zero lab
  papers, each with a ledger category and reason, and its counts agree with index.json.
"""
import csv, gzip, json, re, sys
from collections import Counter
from pathlib import Path
from release_inputs import HIERARCHY

R = Path(__file__).resolve().parents[1]; D = R / 'atlas/data/cs-hierarchy'
H = HIERARCHY
AFF = {'princeton': r'princeton', 'cmu': r'carnegie|cmu', 'epfl': r'epfl|lausanne|polytechnique', 'mit': r'massachusetts institute|\bmit\b|csail', 'berkeley': r'berkeley', 'stanford': r'stanford'}
COLLECTIVE = re.compile(r'\b(cent(er|re)|initiative|consortium|program(me)?|project|cluster|institute)\b', re.I)
LABWORD = re.compile(r'\b(lab|laboratory|group)\b', re.I)


def read(p):
    b = Path(p).read_bytes(); return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


idx = read(D / 'index.json'); fails = []; out = {}
for s in idx['schools']:
    x = read(D / f"{s['id']}.json.gz"); sid = s['id']
    assert x['counts'] == s['counts'], sid
    seen = Counter(i for d in x['departments'] for i in d['labs'])
    if sorted(seen) != list(range(len(x['labs']))) or max(seen.values()) != 1:
        fails.append((sid, 'a lab is in no department or in two'))
    rows = {}
    with gzip.open(H / sid / 'lab_papers.jsonl.gz', 'rt') as f:
        for line in f:
            r = json.loads(line); rows[(r['pi'], r['work'] or r['oa'])] = r
    for l in x['labs']:
        if not l['pi'].get('name'):
            fails.append((sid, l['id'], 'no PI'))
        if COLLECTIVE.search(l['name']) and not LABWORD.search(l['name']):
            fails.append((sid, l['name'], 'collective listed as a lab'))
        years = {y['y'] for y in l['listings']}
        for pi, ident, ap, date in l['papers']:
            p = x['papers'][pi]; r = rows.get((l['pi']['name'], p['w'] or p['oa']))
            if r is None:
                fails.append((sid, l['name'], p['t'], 'paper not in the package')); continue
            a = r['authorship']; txt = ' '.join(a['institutions'] + a['raw_affiliations'])
            if not a.get('school_via'):  # an institution whose OpenAlex lineage is the school, or affiliation text naming it
                fails.append((sid, l['name'], p['t'], 'missing source package school connection', txt[:120]))
            if ap != 'P':
                y = int(ap[1:])
                if y not in years or str(date or '')[:4] != str(y) or len(str(date or '')) < 4:
                    fails.append((sid, l['name'], p['t'], 'listing year does not match', ap, date))
            elif not l['periods']:
                fails.append((sid, l['name'], p['t'], 'period basis without a period'))
        own_p = {p[0] for p in l['papers']}; own_s = {st[0] for st in l['students']}
        for st, pi, k, basis in l['links']:
            if pi not in own_p or st not in own_s:
                fails.append((sid, l['name'], 'link outside the lab'))
    report = read(H / sid / 'report.json')['counts']
    actual = dict(pis_with_lab_papers=x['counts']['labsWithPapers'],
                  lab_papers=sum(len(l['papers']) for l in x['labs']),
                  student_paper_links=sum(len(l['links']) for l in x['labs']))
    for key, value in actual.items():
        if value != report[key]:
            fails.append((sid, 'source report count mismatch', key, value, report[key]))
    if sid == 'berkeley':
        by_name = {l['pi']['name']: l for l in x['labs']}
        for name in ['Zaijun Chen', 'Alex Dimakis', 'Pierluigi Nuzzo', 'Lior Pachter', 'Elchanan Mossel', 'Tapan S. Parikh']:
            lab = by_name.get(name)
            dept = 'School of Information' if name == 'Tapan S. Parikh' else 'Electrical Engineering and Computer Sciences'
            coverage = 'affiliated' if name == 'Tapan S. Parikh' else 'full'
            if not lab or (lab['dept'], lab['coverage']) != (dept, coverage):
                fails.append((sid, name, 'new PI home department mismatch'))
    out[sid] = dict(labs=len(x['labs']), papers=actual['lab_papers'], complete=x['counts']['labsComplete'])
n = Counter(r['school'] for r in csv.DictReader(open(R / 'atlas/downloads/cs-hierarchy-labs.csv')))
for s in idx['schools']:
    if n[s['name']] != s['counts']['labs']:
        fails.append((s['id'], 'labs CSV row count', n[s['name']], s['counts']['labs']))
hid = read(R / 'atlas' / idx['hiddenLabsFile']); ids_seen = set()
for s in idx['schools']:
    x = read(D / f"{s['id']}.json.gz"); sid = s['id']
    zero = {i: l for i, l in enumerate(x['labs']) if not l['papers']}
    rows = hid['schools'].get(sid, [])
    if {r['index'] for r in rows} != set(zero) or len(rows) != len(zero):
        fails.append((sid, 'hidden-labs.json does not list exactly the zero-paper labs'))
    for r in rows:
        l = zero.get(r['index'])
        if not l or l['id'] != r['id'] or l['pi']['name'] != r['pi']:
            fails.append((sid, r['pi'], 'hidden lab does not match the school file'))
        if r['category'] not in hid['categories'] or not (r.get('reason') or '').strip():
            fails.append((sid, r['pi'], 'hidden lab without a reason category or text'))
    c = hid['counts'][sid]
    if c['hidden'] != len(zero) or s.get('hiddenLabs') != len(zero) or c['shown'] != s['counts']['labsWithPapers']:
        fails.append((sid, 'hidden counts', c, s.get('hiddenLabs')))
    out[sid].update(hidden=len(zero), hiddenCategories=c['byCategory'])
print(json.dumps(dict(passed=not fails, schools=out, failures=len(fails), first=fails[:10]), ensure_ascii=False, indent=1))
sys.exit(1 if fails else 0)
