"""Which candidates the captured EECS faculty/emeritus/visiting/teaching lists name, by year; EECS dissertation advisers."""
import json, re, collections
from lib import *
out = {}
lists = pages('%eecs.berkeley.edu%Faculty/%')
diss = pages('%Pubs/Dissertations/Years/%')
for i, c in enumerate(CANDS):
    f = forms(c); hits = collections.defaultdict(list); adv = []
    for url, sha, text, fa in lists:
        T = fold(text)
        for first, last in f:
            for m in re.finditer(r'\b' + re.escape(first[:1].upper()) + r'[\w\'-]*\.?(?: [\w\'().-]+){0,3}? ' + re.escape(last.capitalize() if last.islower() else last) + r'\b[^A-Z]{0,3}((?:[A-Z][\w,-]* ?){1,6})', T, re.I):
                if m.group(0).lower().split()[0][:len(first)] != first[:len(m.group(0).split()[0])].lower(): continue
                hits[url].append(m.group(0)[:90])
    for url, sha, text, fa in diss:
        T = fold(text)
        for m in re.finditer(r'\[advisor: ([^\]]+)\]', T):
            a = m.group(1).lower()
            if any(last in a and first[:1] in a for first, last in f):
                pre = T[max(0, m.start()-120):m.end()]
                adv.append((url[-9:-5], pre[-200:]))
    out[c['author']] = dict(i=i, name=c['name'], lists={u: sorted(set(v))[:3] for u, v in hits.items()}, advising=adv)
json.dump(out, open('/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/bk/eecs_index.json', 'w'), indent=1)
for a, r in out.items():
    if r['lists'] or r['advising']:
        yrs = sorted({year_of(u, '0000') for u in r['lists'] if 'web.archive' in u} | ({2026} if any('web.archive' not in u for u in r['lists']) else set()))
        print(r['i'], r['name'], '| lists yrs', yrs, '| sample', list(r['lists'].values())[0][0] if r['lists'] else '', '| adv', len(r['advising']), sorted({y for y, _ in r['advising']}))
