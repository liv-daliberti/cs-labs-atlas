"""Fetch the Wayback captures of event/news/directory pages that look like dissertation defenses or PhD student lists, and write the PI-name contexts to a JSON file for a hand read.
Every request goes through listings/scripts/wb.py, which takes its slot from host_throttle's shared web.archive.org clock and waits out the shared 429 cooldown.
usage: defense_scan.py <school> '<[[url prefix, "event"|"news"|"dir"], ...]>' <max fetches> <out.json>   (run with the tools/ directory on PYTHONPATH; fulltext-push/defense-scan.slurm)"""
import json, re, sys
import school_web as W
import atlas_paths as P
school = sys.argv.pop(1)
c = W.con(school)
pis = json.loads(P.data('pis.json', school).read_text())
forms = []
for p in pis:
    for n in dict.fromkeys([p['pi']] + list(p.get('names') or [])):
        n = re.sub(r'\s*\([^)]*\)\s*', ' ', n).strip()
        if len(n.split()) >= 2:
            forms.append((p['pi'], n))
EV = re.compile(r'defen[cs]e|dissertation|thesis|ph-?d|doctoral|candidacy|proposal', re.I)
NW = re.compile(r'ph-?d|doctoral|dissertation|defend|graduat|alumn|commencement|degree|student|award|prize|fellow', re.I)
prefixes = json.loads(sys.argv[1]); cap = int(sys.argv[2]); out = sys.argv[3]
cands = []
for pre, kind in prefixes:
    rows = W.cdx_rows(c, pre, exact=False, collapse='urlkey')
    rx = EV if kind == 'event' else NW if kind == 'news' else re.compile('.')
    for r in rows:
        u = r['original']
        if u.rstrip('/').endswith('/embed') or '/embed/' in u or re.search(r'\.(jpg|png|gif|css|js|pdf|ics)(\?|$)', u, re.I):
            continue
        if rx.search(u):
            cands.append((kind, r['timestamp'], u))
print('candidates', len(cands), flush=True)
res = []
bad = 0
for kind, ts, u in cands[:cap]:
    cp, st, sha, b = W.capture(c, ts, u, u, 'defense-scan')
    if st != 200:
        bad += 1
        if bad >= 8:
            print('stopping: 8 non-200 captures', flush=True); break
        continue
    t = W.flat(b)
    hits = []
    for pi, f in forms:
        for m in re.finditer(re.escape(f) + r'(?![\w-])', t):
            hits.append(dict(pi=pi, ctx=t[max(0, m.start() - 220):m.end() + 160])); break
    res.append(dict(kind=kind, url=u, capture=cp, sha=sha, ts=ts, n=len(t), head=t[:240], hits=hits))
    json.dump(res, open(out, 'w'), indent=1)
print('fetched', len(res), flush=True)
