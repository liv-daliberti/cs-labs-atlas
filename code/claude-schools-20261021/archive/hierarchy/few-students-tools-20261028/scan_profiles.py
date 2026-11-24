"""Scan every distinct Wayback capture (2015-2026) plus the live page of each Stanford profile; record the dissertation
advisor / co-advisor / postdoctoral faculty sponsor lists per capture into profile_scan.json."""
import json, sys
from cap import fetch
from wbprof import sections
SLUGS = sys.argv[1:]
out = {}
try: out = json.load(open("profile_scan.json"))
except Exception: pass
for slug in SLUGS:
    rows = json.loads(fetch(f"https://web.archive.org/cdx/search/cdx?url=profiles.stanford.edu/{slug}&output=json&from=2015&to=2026&filter=statuscode:200&fl=timestamp,original&collapse=digest", gap=3)["text"])[1:]
    caps = []
    for ts, o in rows:
        u = f"https://web.archive.org/web/{ts}id_/https://profiles.stanford.edu/{slug}"
        r = fetch(u, gap=3)
        caps.append({"ts": ts, "capture_url": u, "status": r["status"], "sha256": r["sha256"], "sections": sections(r["text"])})
    r = fetch(f"https://profiles.stanford.edu/{slug}")
    caps.append({"ts": r["fetched_at"], "capture_url": None, "status": r["status"], "sha256": r["sha256"], "sections": sections(r["text"])})
    out[slug] = caps
    json.dump(out, open("profile_scan.json", "w"), indent=1)
    print(slug, len(caps), flush=True)
