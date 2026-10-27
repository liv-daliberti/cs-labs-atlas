"""List Wayback URLs under a prefix (one row per urlkey, status 200), optionally filtered by regex.

usage: d_cdx.py PREFIX [--rx REGEX] [--from YYYY] [--to YYYY] [--limit N]
Prints: first-timestamp last-timestamp original  (first/last from a collapse=urlkey listing + its own row)
"""
import argparse
import json
import re
import sys

sys.path.insert(0, "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/few-students-tools-cmu")
import capstore  # noqa: E402
import requests  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("prefix")
ap.add_argument("--rx", default=None)
ap.add_argument("--frm", default="2015")
ap.add_argument("--to", default="2026")
ap.add_argument("--limit", type=int, default=3000)
a = ap.parse_args()
q = ("https://web.archive.org/cdx/search/cdx?url=" + requests.utils.quote(a.prefix, safe="")
     + f"&matchType=prefix&output=json&filter=statuscode:200&fl=timestamp,original&collapse=urlkey&from={a.frm}&to={a.to}&limit={a.limit}")
r = capstore.fetch(q, check_robots=False)
try:
    rows = json.loads(r["content"] or b"[]")[1:]
except Exception as e:
    print("parse error", e, r.get("status"), (r.get("content") or b"")[:200])
    rows = []
n = 0
for ts, orig in rows:
    if a.rx and not re.search(a.rx, orig, re.I):
        continue
    if re.search(r"\.(css|js|png|jpe?g|gif|svg|woff2?|ico|ttf)(\?|$)", orig, re.I):
        continue
    n += 1
    print(ts, orig)
print(n, "of", len(rows))
