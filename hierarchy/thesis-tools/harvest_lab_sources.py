"""Lab / PI page harvest for PIs whose advisees no thesis catalogue shows (2026-10-27), for MIT, CMU, EPFL and Princeton,
into hierarchy/<school>/thesis-captures.sqlite (single writer per school; Berkeley has its own harvest_berkeley_depts.py).

Stores every capture named in lab_sources.SOURCES[school] (live URLs and Wayback id_ URLs). Pages already stored by the
school's cs-related review, labpage, few-students or gap investigations are copied in unchanged (same fetched_at,
sha256 and bytes; copied_from set) instead of being fetched again. robots.txt is honoured (tcap), one request per 2 s per
host, Wayback <= 1 request per 2 s; escholarship.org, dblp and Google Scholar are refused; bot challenges are stored and
never retried.

usage: harvest_lab_sources.py SCHOOL all                      (every capture of the spec; resumable)
       harvest_lab_sources.py SCHOOL fetch [--grep RX] URL...  (one-off pages, printed as text; for discovery)
       harvest_lab_sources.py SCHOOL cdx URL [FROM TO]         (Wayback captures of URL, distinct digests)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402

SCHOOLS = ("mit", "cmu", "epfl", "princeton", "stanford")


def sisters(school):
    b = f"{tcap.ROOT}/{school}"
    extra = [f"{b}/cs-related-captures.sqlite", f"{b}/labpage-captures.sqlite", f"{tcap.ROOT}/cs-related-captures-{school}.sqlite"]
    tcap.SISTER[school] = list(dict.fromkeys(tcap.SISTER[school] + [p for p in extra if os.path.exists(p)]))


def show(r, n=2500, grep=None):
    print(json.dumps({k: r.get(k) for k in ("url", "capture_url", "status", "http_status", "sha256", "error", "cached")}), flush=True)
    if r.get("content"):
        t = tcap.page_text(r["content"], r.get("content_type"))
        print("  [len %d]" % len(t))
        if grep:
            for m in list(re.finditer(grep, t, re.I))[:15]:
                print("  ...", t[max(0, m.start() - 300):m.end() + 300])
        else:
            print(" ", t[:n])


def run_all(school):
    import lab_sources as ls
    for src in ls.SOURCES.get(school, []):
        for u in src["captures"]:
            r = tcap.fetch(school, u)
            print(json.dumps({"pi": src["pi"], "url": u, "status": r.get("status"), "error": r.get("error"),
                              "cached": r.get("cached"), "sha256": r.get("sha256")}), flush=True)
    print("ALLDONE", flush=True)


if __name__ == "__main__":
    school = sys.argv[1]
    if school not in SCHOOLS:
        raise SystemExit(f"school must be one of {SCHOOLS}")
    sisters(school)
    cmd = sys.argv[2] if len(sys.argv) > 2 else "all"
    if cmd == "all":
        run_all(school)
    elif cmd == "fetch":
        grep = None
        args = sys.argv[3:]
        if args and args[0] == "--grep":
            grep, args = args[1], args[2:]
        for u in args:
            show(tcap.fetch(school, u), grep=grep)
    elif cmd == "cdx":
        a = sys.argv[3:]
        frm, to = (a[1], a[2]) if len(a) >= 3 else (2016, 2026)
        for ts, orig, dig in tcap.wayback_cdx(school, a[0], frm=frm, to=to):
            print(ts, orig, dig)
