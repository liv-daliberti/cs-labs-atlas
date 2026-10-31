"""usage: match.py URL-LIKE [idx...]: contexts where each candidate's family name + given initial occur in matching stored pages."""
import re, sys
from lib import *
like = sys.argv[1]; only = {int(x) for x in sys.argv[2:]}
P = pages(like)
for i, c in enumerate(CANDS):
    if only and i not in only: continue
    for url, sha, text, fa in P:
        T = fold(text)
        for first, last in forms(c):
            for m in re.finditer(r'\b' + re.escape(last) + r'\b', T, re.I):
                ctx = T[max(0, m.start()-40):m.end()+60]
                if re.search(r'\b' + re.escape(first[:1]), ctx, re.I) and first[:3].lower() in ctx.lower():
                    print(i, c['name'], '|', url[:70], '|', ctx); break
            else: continue
            break
