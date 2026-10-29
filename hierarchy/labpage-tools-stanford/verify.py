"""Independent re-verification of hierarchy/stanford/labpage-pubs.jsonl.gz against labpage-captures.sqlite.
Per row: pi is a pis.json PI; year is an int in 2016-2026; sha256 names a stored 200 capture whose zlib bytes re-hash to
it; url is that capture's Wayback id_ URL (capture_url) or, for a live capture, its url, and page_url is the stored
original url; the quote is whitespace-collapsed, an exact substring of one text view (lpcap.texts) of those bytes, and
contains the normalized title; no (pi, normalized title) twice. Also checks the report's per-PI missing counts.
usage: verify.py    (exit 1 on any failure)"""
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stcap  # noqa: E402,F401
import lpcap  # noqa: E402
import lpdom  # noqa: E402

R = lpcap.ROOT + "/stanford"
pis = {p["pi"] for p in json.load(open(f"{R}/pis.json"))}
rows = [json.loads(l) for l in gzip.open(f"{R}/labpage-pubs.jsonl.gz", "rt")]
rep = json.load(open(f"{R}/labpage-pubs-report.json"))
con = sqlite3.connect(f"file:{R}/labpage-captures.sqlite?mode=ro", uri=True)
cache, bad, seen = {}, [], set()


def stored(sha):
    if sha not in cache:
        rs = con.execute("SELECT url, capture_url, status, error, content, content_type FROM captures WHERE sha256=? "
                         "AND content IS NOT NULL", (sha,)).fetchall()
        if not rs:
            cache[sha] = None
        else:
            body = zlib.decompress(rs[0][4])
            ok = hashlib.sha256(body).hexdigest() == sha
            cache[sha] = (ok, {(u, cu, st, er) for u, cu, st, er, _, _ in rs}, lpcap.texts(body, rs[0][5]))
    return cache[sha]


for i, r in enumerate(rows):
    tag = f"row {i} {r.get('pi')} | {str(r.get('title'))[:60]}"
    if r.get("pi") not in pis:
        bad.append(f"{tag}: pi not in pis.json")
    if not isinstance(r.get("year"), int) or not 2016 <= r["year"] <= 2026:
        bad.append(f"{tag}: year {r.get('year')!r} not an int in 2016-2026")
    st = stored(r.get("sha256"))
    if st is None:
        bad.append(f"{tag}: sha256 not in store")
        continue
    ok, meta, views = st
    if not ok:
        bad.append(f"{tag}: stored bytes do not re-hash")
    cu = r.get("capture_url")
    want_url = cu or r.get("page_url")
    if r.get("url") != want_url:
        bad.append(f"{tag}: url {r.get('url')} != capture_url/page_url")
    if not any(u == r.get("page_url") and (c or None) == (cu or None) and s == 200 and e is None for u, c, s, e in meta):
        bad.append(f"{tag}: no stored 200 row with url={r.get('page_url')} capture_url={cu}")
    q = r.get("quote") or ""
    if not q or q != lpcap.collapse(q):
        bad.append(f"{tag}: empty or uncollapsed quote")
    elif not any(q in v for v in views.values()):
        bad.append(f"{tag}: quote not an exact substring of the stored text views")
    if lpdom.norm_title(r.get("title")) not in lpdom.norm_title(q):
        bad.append(f"{tag}: quote lacks the title")
    k = (r.get("pi"), lpdom.norm_title(r.get("title")))
    if k in seen:
        bad.append(f"{tag}: duplicate (pi, title)")
    seen.add(k)
cnt = {}
for r in rows:
    cnt[r["pi"]] = cnt.get(r["pi"], 0) + 1
for pi, v in rep["pis"].items():
    if v.get("status") == "pubs_page" and v.get("missing", 0) != cnt.get(pi, 0):
        bad.append(f"report: {pi} missing={v.get('missing')} but {cnt.get(pi, 0)} rows")
if rep.get("rows") != len(rows):
    bad.append(f"report rows {rep.get('rows')} != {len(rows)}")
print(f"{len(rows)} rows, {len(cnt)} PIs, {len(cache)} distinct captures; {len(bad)} problems")
for b in bad[:50]:
    print("  BAD", b)
sys.exit(1 if bad else 0)
