"""Scan the MIT collection (read-only) for advising contexts whose adviser text mentions a gap PI's surname.
usage: scan_collection.py SURNAME [SURNAME...]"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, re, sys, collections
C = json.loads(gzip.decompress(open(str(P.SITE_ROOT / 'atlas/data/collection-mit.json.gz'), 'rb').read()))
people = C['people'] if isinstance(C['people'], list) else list(C['people'].values())
types = collections.Counter(c.get('type') for p in people for c in p.get('contexts') or [])
print('context types', types.most_common(20))
for sur in sys.argv[1:]:
    rx = re.compile(r'\b' + re.escape(sur) + r'\b', re.I)
    print('=====', sur)
    for p in people:
        for c in p.get('contexts') or []:
            if 'advis' not in (c.get('type') or ''):
                continue
            txt = ' | '.join(str(x) for x in [c.get('advisorName'), c.get('advisor')] + list(c.get('advisors') or []) + [s.get('quote') or '' for s in c.get('sources') or []] if x)
            if rx.search(txt):
                print(json.dumps(dict(person=p['id'], name=p['name'], type=c.get('type'), role=c.get('role'), years=c.get('years') or c.get('year'), adv=[c.get('advisorName'), c.get('advisor'), c.get('advisors')], src=[(s.get('url'), (s.get('quote') or '')[:200]) for s in (c.get('sources') or [])[:2]]))[:700])
