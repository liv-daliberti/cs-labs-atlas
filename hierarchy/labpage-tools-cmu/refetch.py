"""Re-fetch every URL cited by decisions/*.py into labpage-parts/refetch.sqlite (resumable, detached).

The first worker capture stores lived in a login host's local /tmp and were lost when the session moved
hosts; Wayback id_ captures return the same bytes, live pages are fetched again. A URL already stored with
status 200 (in any store capstore can see) is skipped. Honors the shared Wayback back-off by waiting.

usage: LABPAGE_DB=<parts>/refetch.sqlite python -I refetch.py [--only b01 b02 ...]
"""
import argparse
import glob
import importlib
import os
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
sys.path.insert(0, TOOLS + "/decisions")
import capstore  # noqa: E402


def urls_of(only=None):
    out = []
    for p in sorted(glob.glob(TOOLS + "/decisions/b*.py")):
        m = os.path.basename(p)[:-3]
        if only and m not in only:
            continue
        mod = importlib.import_module(m)
        for pi, d in mod.D.items():
            for mm in d.get("members", []):
                out.append(mm["url"])
            for ps in d.get("pubs", []):
                out.append(ps["url"])
    seen, res = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            res.append(u)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    us = urls_of(a.only)
    live = [u for u in us if "web.archive.org" not in u]
    wb = [u for u in us if "web.archive.org" in u]
    print(len(us), "urls:", len(live), "live,", len(wb), "wayback", flush=True)
    for u in live + wb:
        for attempt in range(6):
            r = capstore.fetch(u)
            err = r.get("error") or ""
            if err.startswith("wayback-backoff"):
                time.sleep(max(5, capstore.wayback_backoff_until() - time.time() + 1))
                continue
            break
        print(r.get("status"), (r.get("error") or "")[:80], u, flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
