"""Fetch Wayback id_ captures for the MIT few-students PIs: wb_mit.py URL PREFIX [PREFIX...] (timestamp prefixes, e.g. 2021 or
20250415); resolves each prefix against the (stored) CDX listing and prints the capture URL and the page text head."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fscap  # noqa: E402

url = sys.argv[1]
rows = fscap.wayback_cdx("mit", url.split("://", 1)[-1], frm=2010)
for pre in sys.argv[2:]:
    hit = [r for r in rows if r[0].startswith(pre)]
    if not hit:
        print("NO CAPTURE", pre); continue
    ts, orig = hit[0][0], hit[0][1]
    cap = fscap.wayback_id(ts, orig)
    r = fscap.fetch("mit", cap, check_robots=False)
    print("CAP", cap, r.get("status"), r.get("error"))
    if r.get("status") == 200:
        print("  ", fscap.page_text(r["content"], r.get("content_type"))[:int(os.environ.get("HEAD", "2500"))])
    print("=" * 80, flush=True)
