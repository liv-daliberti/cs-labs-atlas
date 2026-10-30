"""Independent re-verification of hierarchy/<school>/few-students-evidence.json against the school's capture store.

Checks: one row per input PI in input order; keys; every student row has name/role/years/url/sha256/quote with a valid
role and years ([first,last] ints or null); the cited sha256 is a stored status-200 row of few-students-captures.sqlite
whose url (and capture_url, when cited) match and whose bytes re-hash to that sha256; the quote is an exact substring
of one whitespace-collapsed text view of those bytes; the quote contains every token of the student's name.
usage: verify.py SCHOOL [SCHOOL ...]     (exit 1 on any failure)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib
import json
import os
import sqlite3
import sys
import zlib

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import fscap  # noqa: E402
import fsev  # noqa: E402

ROOT = str(P.HIERARCHY)
bad_total = 0
for school in sys.argv[1:]:
    bad = []
    inp = json.load(open(f"{ROOT}/{school}/few-students-input.json"))
    ev = json.load(open(f"{ROOT}/{school}/few-students-evidence.json"))
    con = sqlite3.connect(f"file:{fscap.DBS[school]}?mode=ro", uri=True)
    views = {}

    def stored(sha):
        if sha not in views:
            rows = con.execute("SELECT url, capture_url, status, content, content_type, error FROM captures "
                               "WHERE sha256=? AND content IS NOT NULL", (sha,)).fetchall()
            if not rows:
                views[sha] = None
            else:
                c = zlib.decompress(rows[0][3])
                if hashlib.sha256(c).hexdigest() != sha:
                    bad.append(f"stored bytes do not re-hash to {sha}")
                views[sha] = ({(u, cu, st, er) for u, cu, st, _, _, er in rows}, fscap.texts(c, rows[0][4]))
        return views[sha]

    if [r["pi"] for r in ev] != [r["pi"] for r in inp]:
        bad.append("PI list/order differs from few-students-input.json")
    n = 0
    for r in ev:
        if set(r) != {"pi", "students", "lab_note", "notes"}:
            bad.append(f"{r.get('pi')}: keys {sorted(r)}")
        for s in r.get("students", []):
            n += 1
            tag = f"{r['pi']} / {s.get('name')}"
            for k in ("name", "role", "url", "sha256", "quote"):
                if not s.get(k):
                    bad.append(f"{tag}: missing {k}")
            if s.get("role") not in fsev.ROLES:
                bad.append(f"{tag}: role {s.get('role')}")
            y = s.get("years")
            if y is not None and not (isinstance(y, list) and len(y) == 2 and all(isinstance(v, int) for v in y) and y[0] <= y[1]):
                bad.append(f"{tag}: years {y}")
            st = stored(s.get("sha256"))
            if st is None:
                bad.append(f"{tag}: sha256 {str(s.get('sha256'))[:12]} not in store")
                continue
            meta, tv = st
            if not any(u == s["url"] and (cu or None) == (s.get("capture_url") or None) and code == 200 and er is None
                       for u, cu, code, er in meta):
                bad.append(f"{tag}: url/capture_url do not match a stored 200 row ({s['url']} {s.get('capture_url')})")
            qq = s["quote"]
            if qq != fscap.collapse(qq):
                bad.append(f"{tag}: quote is not whitespace-collapsed")
            if not any(qq in t for t in tv.values()):
                bad.append(f"{tag}: quote not an exact substring: {qq[:100]}")
            if not fsev.has_name(qq, s["name"]):
                bad.append(f"{tag}: quote lacks the name: {qq[:100]}")
    con.close()
    print(f"{school}: {len(ev)} PIs, {n} student rows, {len(bad)} problems")
    for b in bad[:60]:
        print("  BAD", b)
    bad_total += len(bad)
sys.exit(1 if bad_total else 0)
