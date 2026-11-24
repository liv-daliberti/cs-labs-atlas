"""Independent re-verification of hierarchy/<school>/labpage-evidence.json and labpage-pubs.jsonl.gz.

Checks: one evidence row per labpage-input PI, in input order, with keys pi/lab_site/people_page/students/notes;
every student row (and every entry of its other_sources) cites a sha256 stored with status 200 in
labpage-captures.sqlite whose url (and capture_url when cited) match and whose bytes re-hash to that sha256; the quote
is whitespace-collapsed and an exact substring of one whitespace-collapsed text view of those bytes; the quote
contains every token of the name as written; roles are in the vocabulary; already_held rows name a held string of
that PI and no held person appears twice. Every missing-publication row cites a stored capture the same way and its
quote is an exact substring that contains the title (normalized).
usage: verify.py SCHOOL [SCHOOL ...]     (exit 1 on any failure)
"""
import gzip
import hashlib
import json
import os
import re
import sqlite3
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for k in list(os.environ):
    if k.startswith("LPCAP_LOCAL"):
        os.environ.pop(k)
import lpcap  # noqa: E402
import lpdom  # noqa: E402
import lpnames  # noqa: E402

ROLES = {"phd", "postdoc", "masters", "undergraduate", "research_staff", "visitor", "intern", "member", "other"}


def has_name(quote, name):
    q = lpnames.fold(quote)
    toks = [t for t in re.split(r"[^a-z0-9]+", lpnames.fold(re.sub(r"\([^)]*\)", " ", name))) if len(t) > 1]
    return bool(toks) and all(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", q) for t in toks)


bad_total = 0
for school in sys.argv[1:]:
    bad = []
    inp = json.load(open(lpcap.data("labpage-input.json", school)))
    ev = json.load(open(lpcap.data("labpage-evidence.json", school)))
    con = sqlite3.connect(f"file:{lpcap.DBS[school]}?mode=ro", uri=True)
    cache = {}

    def stored(sha):
        if sha not in cache:
            rows = con.execute("SELECT url, capture_url, status, content, content_type, error FROM captures "
                               "WHERE sha256=? AND content IS NOT NULL", (sha,)).fetchall()
            if not rows:
                cache[sha] = None
            else:
                c = zlib.decompress(rows[0][3])
                if hashlib.sha256(c).hexdigest() != sha:
                    bad.append(f"stored bytes do not re-hash to {sha}")
                cache[sha] = ({(u, cu, st, er) for u, cu, st, _, _, er in rows}, lpcap.texts(c, rows[0][4]))
        return cache[sha]

    def check_src(tag, s, name=None, title=None):
        st = stored(s.get("sha256"))
        if st is None:
            bad.append(f"{tag}: sha256 {str(s.get('sha256'))[:12]} not in store")
            return
        meta, tv = st
        if not any(u == s["url"] and (cu or None) == (s.get("capture_url") or None) and code == 200 and er is None
                   for u, cu, code, er in meta):
            bad.append(f"{tag}: url/capture_url do not match a stored 200 row ({s['url']} {s.get('capture_url')})")
        qq = s.get("quote") or ""
        if not qq:
            bad.append(f"{tag}: empty quote")
            return
        if qq != lpcap.collapse(qq):
            bad.append(f"{tag}: quote is not whitespace-collapsed")
        if not any(qq in t for t in tv.values()):
            bad.append(f"{tag}: quote not an exact substring: {qq[:100]}")
        if name and not has_name(qq, name):
            bad.append(f"{tag}: quote lacks the name: {qq[:100]}")
        if title and lpdom.norm_title(title) not in lpdom.norm_title(qq):
            bad.append(f"{tag}: quote lacks the title: {qq[:100]}")

    if [r["pi"] for r in ev] != [r["pi"] for r in inp]:
        bad.append("PI list/order differs from labpage-input.json")
    held_by_pi = {r["pi"]: set(r.get("students_held") or []) for r in inp}
    n = ns = 0
    for r in ev:
        if set(r) != {"pi", "lab_site", "people_page", "students", "notes"}:
            bad.append(f"{r.get('pi')}: keys {sorted(r)}")
        seen_held = set()
        seen_names = set()
        for s in r.get("students", []):
            n += 1
            tag = f"{r['pi']} / {s.get('name')}"
            for k in ("name", "role", "url", "sha256", "quote"):
                if not s.get(k):
                    bad.append(f"{tag}: missing {k}")
            if s.get("role") not in ROLES:
                bad.append(f"{tag}: role {s.get('role')}")
            y = s.get("years")
            if y is not None and not (isinstance(y, list) and len(y) == 2 and
                                      all(v is None or isinstance(v, int) for v in y) and
                                      (None in y or y[0] <= y[1])):
                bad.append(f"{tag}: years {y}")
            if s.get("already_held"):
                if s.get("held_name") not in held_by_pi[r["pi"]]:
                    bad.append(f"{tag}: held_name {s.get('held_name')!r} not in students_held")
                if s.get("held_name") in seen_held:
                    bad.append(f"{tag}: held person {s.get('held_name')!r} appears twice")
                seen_held.add(s.get("held_name"))
            k = lpnames.fold(s.get("name", ""))
            if k in seen_names:
                bad.append(f"{tag}: name appears twice")
            seen_names.add(k)
            check_src(tag, s, name=s["name"])
            for o in s.get("other_sources", []):
                ns += 1
                check_src(tag + " (other source)", o, name=o.get("name_as_written") or s["name"])
    pubs = []
    p = lpcap.data("labpage-pubs.jsonl.gz", school)
    if os.path.exists(p):
        with gzip.open(p, "rt") as f:
            pubs = [json.loads(l) for l in f]
    for i, pb in enumerate(pubs):
        tag = f"pub {i} {pb.get('pi')} / {str(pb.get('title'))[:50]}"
        for k in ("pi", "title", "year", "url", "sha256", "quote"):
            if pb.get(k) in (None, ""):
                bad.append(f"{tag}: missing {k}")
        if pb.get("year") is not None and not (2016 <= pb["year"] <= 2026):
            bad.append(f"{tag}: year {pb['year']}")
        check_src(tag, pb, title=pb.get("title"))
    con.close()
    print(f"{school}: {len(ev)} labs, {n} member rows (+{ns} other sources), {len(pubs)} missing pubs, "
          f"{len(bad)} problems")
    for b in bad[:60]:
        print("  BAD", b)
    bad_total += len(bad)
sys.exit(1 if bad_total else 0)
