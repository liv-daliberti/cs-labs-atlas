"""Independent re-verification of hierarchy/<school>/thesis-evidence.json against hierarchy/<school>/thesis-captures.sqlite.

Checks, for every row: keys and types (name, role in phd|masters|undergraduate|other, years [int, int] with y0 <= y1 in
2016-2026, url, sha256, quote, optional capture_url/note); the PI is in pis.json; the cited sha256 is a stored status-200,
error-free capture whose url (and capture_url, when cited) match and whose bytes re-hash to that sha256; the quote is
whitespace-collapsed and an exact substring of one whitespace-collapsed text view of those bytes; the quote names the
student (every name token) and the PI (the family name of one of the PI's name forms); the student is not already one of
the PI's students in students.json; no (PI, student) pair is listed twice.
usage: verify.py [--draft] [SCHOOL ...]   (--draft checks thesis-tools/out/<school>-thesis-evidence.json) ; exit 1 on failure
"""
import hashlib
import json
import os
import sqlite3
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import names  # noqa: E402
import tcap  # noqa: E402

ROOT = names.ROOT
ROLES = {"phd", "masters", "undergraduate", "other"}
draft = "--draft" in sys.argv
schools = [a for a in sys.argv[1:] if not a.startswith("--")] or ["princeton", "cmu", "epfl", "mit", "berkeley"]
total_bad = 0
for school in schools:
    path = (f"{os.path.dirname(os.path.abspath(__file__))}/out/{school}-thesis-evidence.json" if draft
            else f"{ROOT}/{school}/thesis-evidence.json")
    if not os.path.exists(path):
        print(f"{school}: no {path}")
        continue
    ev = json.load(open(path))
    # students.json is rebuilt by tools/pi_hierarchy.py from the final thesis-evidence.json: a student held only through
    # that file (every source sha256 is one of its rows) is not 'already held' (the same rule as build.py)
    final = f"{ROOT}/{school}/thesis-evidence.json"
    own = {s_["sha256"] for r_ in (json.load(open(final)) if os.path.exists(final) else []) for s_ in r_["students"]}

    def independent(s_):
        srcs = [src for rel in s_.get("relations") or [] for src in rel.get("sources") or []]
        return not srcs or not all(src.get("sha256") in own for src in srcs)
    pis = {p["pi"]: p for p in json.load(open(f"{ROOT}/{school}/pis.json"))}
    stu = json.load(open(f"{ROOT}/{school}/students.json"))
    con = sqlite3.connect(f"file:{tcap.DBS[school]}?mode=ro", uri=True, timeout=120)
    cache, bad, n, seen, seen_hy = {}, [], 0, set(), set()

    def stored(sha):
        if sha not in cache:
            rs = con.execute("SELECT url, capture_url, status, error, content, content_type FROM captures WHERE sha256=? AND content IS NOT NULL",
                             (sha,)).fetchall()
            if not rs:
                cache[sha] = None
            else:
                c = zlib.decompress(rs[0][4])
                if hashlib.sha256(c).hexdigest() != sha:
                    bad.append(f"stored bytes do not re-hash to {sha}")
                cache[sha] = ({(u, cu, st, er) for u, cu, st, er, _, _ in rs}, tcap.texts(c, rs[0][5]))
            if len(cache) > 200:
                k0 = next(iter(cache))
                if k0 != sha:
                    del cache[k0]
        return cache[sha]

    # plus, where build.HELD_YEARS writes one, thesis-held-years-evidence.json: the same checks, except that each row's
    # student must ALREADY be one of the PI's students (it only carries earlier years)
    hy_path = (f"{os.path.dirname(os.path.abspath(__file__))}/out/{school}-thesis-held-years-evidence.json" if draft
               else f"{ROOT}/{school}/thesis-held-years-evidence.json")
    batches = [(ev, False)] + ([(json.load(open(hy_path)), True)] if os.path.exists(hy_path) else [])
    for r, held_file in [(r_, hf_) for ev_, hf_ in batches for r_ in ev_]:
        if held_file and not seen_hy:
            seen_hy.add("start"); seen = set()
        if set(r) != {"pi", "students", "notes"}:
            bad.append(f"{r.get('pi')}: keys {sorted(r)}")
        pi = r.get("pi")
        if pi not in pis:
            bad.append(f"{pi}: not in pis.json")
            continue
        fams = names.pi_family_names(pi, pis[pi].get("names"), school)
        held = [names.Name([s["name"]]) for s in stu.get(pi, []) if independent(s)]
        for s in r.get("students", []):
            n += 1
            tag = f"{pi} / {s.get('name')}"
            extra = set(s) - {"name", "role", "years", "url", "capture_url", "sha256", "quote", "note"}
            if extra:
                bad.append(f"{tag}: unexpected keys {sorted(extra)}")
            for k in ("name", "role", "years", "url", "sha256", "quote"):
                if not s.get(k):
                    bad.append(f"{tag}: missing {k}")
            if s.get("role") not in ROLES:
                bad.append(f"{tag}: role {s.get('role')}")
            y = s.get("years")
            if not (isinstance(y, list) and len(y) == 2 and all(isinstance(v, int) for v in y) and 2016 <= y[0] <= y[1] <= 2026):
                bad.append(f"{tag}: years {y}")
            key = (pi, names.fold(s.get("name", "")))
            if key in seen:
                bad.append(f"{tag}: duplicate pair")
            seen.add(key)
            if not held_file and any(h.match(s.get("name", "")) for h in held):
                bad.append(f"{tag}: already one of the PI's students in students.json")
            if held_file and not any(h.match(s.get("name", "")) or names.Name([s.get("name", "")]).match(x["name"]) for h, x in
                                     [(names.Name([x_["name"]]), x_) for x_ in stu.get(pi, [])]):
                bad.append(f"{tag}: held-years row whose student is not held")
            st = stored(s.get("sha256"))
            if st is None:
                bad.append(f"{tag}: sha256 {str(s.get('sha256'))[:12]} not in store")
                continue
            meta, tv = st
            if not any(u == s["url"] and (cu or None) == (s.get("capture_url") or None) and code == 200 and er is None
                       for u, cu, code, er in meta):
                bad.append(f"{tag}: url/capture_url do not match a stored 200 row")
            qq = s["quote"]
            if qq != tcap.collapse(qq):
                bad.append(f"{tag}: quote is not whitespace-collapsed")
            if not any(qq in t for t in tv.values()):
                bad.append(f"{tag}: quote not an exact substring: {qq[:120]}")
            if not names.has_tokens(qq, s["name"]):
                bad.append(f"{tag}: quote lacks the student's name: {qq[:120]}")
            if not names.names_pi(qq, fams):
                bad.append(f"{tag}: quote does not name the PI: {qq[:120]}")
    con.close()
    print(f"{school}: {len(ev)} PIs, {n} student rows (incl. held-years rows), {len(bad)} problems")
    for b in bad[:40]:
        print("  BAD", b)
    total_bad += len(bad)
sys.exit(1 if total_bad else 0)
