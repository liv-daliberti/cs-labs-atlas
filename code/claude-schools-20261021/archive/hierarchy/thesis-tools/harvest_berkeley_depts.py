"""Berkeley advisee harvest beyond EECS (2026-10-27) into hierarchy/berkeley/thesis-captures.sqlite (single writer).

The EECS harvest (harvest_berkeley.py) cannot see students of the ~75 CS-related PIs outside EECS (IEOR, ME, CEE, Math,
Statistics, I School, Education, Linguistics, Philosophy, Physics, ChemE, BioE, ESPM). This harvester stores the pages
named in berkeley_depts.py:
  1. department lists that name the adviser of every thesis: Math 'Past PhD Students' (Title / 'Student; Advisor' /
     Year), I School 'Completed Ph.D. Dissertations' ('Advisor(s): ...');
  2. the PIs' own lab / group / homepage rosters (current and alumni students), live and Wayback id_ captures 2016-2026.
Pages already stored by the cs-related, labpage, few-students or gap investigations of Berkeley are copied in unchanged
(same fetched_at, sha256 and bytes; copied_from set) instead of being fetched again. robots.txt is honoured (tcap),
one request per 2 s per host, Wayback <= 1 request per 2 s; escholarship.org, dblp and Google Scholar are refused.

usage: harvest_berkeley_depts.py all                  (every page of the spec; resumable)
       harvest_berkeley_depts.py fetch URL...         (one-off pages, printed as text; for discovery)
       harvest_berkeley_depts.py cdx URL [FROM TO]    (Wayback captures of URL, distinct digests)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402

S = "berkeley"
B = tcap.ROOT + "/berkeley"
# earlier Berkeley investigations whose stored 200 captures are reused (read-only)
tcap.SISTER[S] = list(dict.fromkeys(tcap.SISTER[S] + [f"{B}/cs-related-captures.sqlite", f"{B}/labpage-captures.sqlite"]))


def get(u):
    r = tcap.fetch(S, u)
    return r


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


def wayback_ids(url, frm=2016, to=2026, per_year=True):
    rows = tcap.wayback_cdx(S, url, frm=frm, to=to)
    out, seen = [], set()
    for ts, orig, dig in rows:
        y = ts[:4]
        if per_year and y in seen:
            continue
        seen.add(y)
        out.append(tcap.wayback_id(ts, orig))
    return out


def run_all():
    import berkeley_depts as bd
    for u in bd.dept_urls():
        r = get(u)
        print(json.dumps({"dept": u, "status": r.get("status"), "error": r.get("error"), "cached": r.get("cached")}), flush=True)
    for src in bd.LAB_SOURCES:
        for w in src.get("wayback") or []:
            tcap.wayback_cdx(S, w, frm=2016, to=2026)  # stored; bd.all_captures() reads it back

        def read(u):
            r = tcap.cached(S, u, sister=False)
            return r["content"] if r else None
        for u in bd.all_captures(src, read):
            r = get(u)
            print(json.dumps({"pi": src["pi"], "url": u, "status": r.get("status"), "error": r.get("error"),
                              "cached": r.get("cached")}), flush=True)
    print("ALLDONE", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        run_all()
    elif cmd == "fetch":
        grep = None
        args = sys.argv[2:]
        if args and args[0] == "--grep":
            grep, args = args[1], args[2:]
        for u in args:
            show(get(u), grep=grep)
    elif cmd == "cdx":
        a = sys.argv[2:]
        frm, to = (a[1], a[2]) if len(a) >= 3 else (2016, 2026)
        for ts, orig, dig in tcap.wayback_cdx(S, a[0], frm=frm, to=to):
            print(ts, orig, dig)
