"""Verify an OpenAlex author id against the PI's own publication list: fetch the author's 2016+ works (OpenAlex) and find
their titles in a stored page (homepage / CV / lab publications). Prints matches with a quote window containing the title
and, where near, the PI's surname.

usage: match_works.py SCHOOL A123 PAGE_URL SURNAME [--from 2016] [--n 200]
"""
import argparse
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gapcap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("school")
ap.add_argument("aid")
ap.add_argument("page")
ap.add_argument("surname")
ap.add_argument("--from", dest="frm", type=int, default=2016)
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--span", type=int, default=250)
a = ap.parse_args()


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


res, j = gapcap.oa_author_works(a.school, a.aid, a.frm)
works = (j or {}).get("results", [])
print("openalex works", len(works), "of", (j or {}).get("meta", {}).get("count"), "sha", res.get("sha256"))
cap = gapcap.cached(a.school, a.page)
if not cap:
    print("page not stored"); sys.exit(1)
views = gapcap.texts(cap["content"], cap["content_type"])
t = views.get("pdf") or views.get("html") or views.get("raw")
# map normalized text positions back to original
idx, nt = [], []
for i, ch in enumerate(t):
    for c in norm(ch):
        nt.append(c); idx.append(i)
nts = "".join(nt)
n = 0
for w in works:
    title = w.get("title") or ""
    k = norm(title)
    if len(k) < 20:
        continue
    p = nts.find(k)
    if p < 0:
        continue
    s, e = idx[p], idx[p + len(k) - 1] + 1
    sur = gapcap.collapse(a.surname).lower()
    lo = max(0, s - a.span)
    hi = min(len(t), e + a.span)
    win = t[lo:hi]
    sp = [m.start() + lo for m in re.finditer(re.escape(sur), win.lower())]
    if sp:
        nearest = min(sp, key=lambda x: min(abs(x - s), abs(x - e)))
        qs, qe = min(s, nearest), max(e, nearest + len(sur))
    else:
        qs, qe = s, e
    n += 1
    print(f"MATCH {w['publication_year']} {w['id'].rsplit('/',1)[-1]} | {title[:90]}")
    print("   QUOTE:", t[qs:qe][:700])
print("matches:", n)
