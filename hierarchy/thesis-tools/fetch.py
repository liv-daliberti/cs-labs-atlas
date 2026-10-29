"""Fetch URLs into a school's thesis capture store (tcap) and print status + a text window.
usage: fetch.py SCHOOL [--grep RX] [--head N] [--force] URL...   (one writer per store: do not run while that school's
harvester writes the store directly; set TCAP_LOCAL to a scratch file and merge.py it afterwards)"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("school", choices=tcap.SCHOOLS)
ap.add_argument("--grep", default=None)
ap.add_argument("--head", type=int, default=1500)
ap.add_argument("--chars", type=int, default=400)
ap.add_argument("--force", action="store_true")
ap.add_argument("urls", nargs="+")
a = ap.parse_args()
for u in a.urls:
    r = tcap.fetch(a.school, u, force=a.force)
    print(json.dumps({k: r.get(k) for k in ("url", "final_url", "capture_url", "status", "http_status", "sha256", "error", "cached", "retry_after")}), flush=True)
    if r.get("content"):
        t = tcap.page_text(r["content"], r.get("content_type"))
        print("  [len %d]" % len(t))
        if a.grep:
            for m in list(re.finditer(a.grep, t, re.I))[:12]:
                print("  ...", t[max(0, m.start() - a.chars):m.end() + a.chars], "...")
        else:
            print(" ", t[:a.head])
