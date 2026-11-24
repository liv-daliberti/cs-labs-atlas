"""Independent re-verification of hierarchy/<school>/labpage-evidence.json and labpage-pubs.jsonl.gz against the
school's capture store (hierarchy/<school>/labpage-captures.sqlite only; worker-local stores are ignored).

Checks: one evidence row per input PI in input order; every member row (and every `also` source) has
name/role/url/sha256/quote, a valid role and years ([first,last] ints or null); the cited sha256 is a stored status-200
row whose url (and capture_url, when cited) match and whose bytes re-hash to that sha256; the quote is whitespace-
collapsed, an exact substring of one text view of those bytes, and contains every token of the name. Pub lines: the
same capture checks, the quote contains the title (first 40 chars of the folded alphanumeric key), year in 2016-2026 or null, pi in the input.
usage: verify.py SCHOOL [SCHOOL ...]     (exit 1 on any failure)
"""
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import zlib

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
os.environ.pop("LPCAP_LOCAL", None)
import lpcap  # noqa: E402
import lpev  # noqa: E402

bad_total = 0
for school in sys.argv[1:]:
    bad = []
    inp = json.load(open(lpcap.data("labpage-input.json", school)))
    ev = json.load(open(lpcap.data("labpage-evidence.json", school)))
    con = sqlite3.connect(f"file:{lpcap.DBS[school]}?mode=ro", uri=True)
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
                views[sha] = ({(u, cu, st, er) for u, cu, st, _, _, er in rows}, lpcap.texts(c, rows[0][4]))
        return views[sha]

    def check_src(tag, s):
        st = stored(s.get("sha256"))
        if st is None:
            bad.append(f"{tag}: sha256 {str(s.get('sha256'))[:12]} not in store")
            return None
        meta, tv = st
        if not any(u == s["url"] and (cu or None) == (s.get("capture_url") or None) and code == 200 and er is None
                   for u, cu, code, er in meta):
            bad.append(f"{tag}: url/capture_url do not match a stored 200 row ({s['url']} {s.get('capture_url')})")
        qq = s.get("quote") or ""
        if not qq:
            bad.append(f"{tag}: empty quote")
        if qq != lpcap.collapse(qq):
            bad.append(f"{tag}: quote is not whitespace-collapsed")
        if not any(qq in t for t in tv.values()):
            bad.append(f"{tag}: quote not an exact substring: {qq[:100]}")
        return tv

    if [r["pi"] for r in ev] != [r["pi"] for r in inp]:
        bad.append("PI list/order differs from labpage-input.json")
    n = nalso = 0
    for r in ev:
        for k in ("pi", "lab_site", "people_page", "students", "notes"):
            if k not in r:
                bad.append(f"{r.get('pi')}: missing key {k}")
        for s in r.get("students", []):
            n += 1
            for src in [s] + s.get("also", []):
                tag = f"{r['pi']} / {src.get('name')}"
                if src is not s:
                    nalso += 1
                for k in ("name", "role", "url", "sha256", "quote"):
                    if not src.get(k):
                        bad.append(f"{tag}: missing {k}")
                if src.get("role") not in lpev.ROLES:
                    bad.append(f"{tag}: role {src.get('role')}")
                y = src.get("years")
                if y is not None and not (isinstance(y, list) and len(y) == 2 and all(v is None or isinstance(v, int) for v in y)
                                          and (None in y or y[0] <= y[1])):
                    bad.append(f"{tag}: years {y}")
                if check_src(tag, src) is not None and not lpev.has_name(src["quote"], src["name"]):
                    bad.append(f"{tag}: quote lacks the name: {src['quote'][:100]}")
            if s.get("already_held") and not s.get("held_name"):
                bad.append(f"{r['pi']} / {s['name']}: already_held without held_name")
    pis = {r["pi"] for r in inp}
    npub = 0
    with gzip.open(lpcap.data("labpage-pubs.jsonl.gz", school), "rt", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            npub += 1
            tag = f"pub {p.get('pi')} / {str(p.get('title'))[:60]}"
            if p.get("pi") not in pis:
                bad.append(f"{tag}: pi not in input")
            for k in ("title", "url", "sha256", "quote"):
                if not p.get(k):
                    bad.append(f"{tag}: missing {k}")
            if p.get("year") is not None and not (2016 <= p["year"] <= 2026):
                bad.append(f"{tag}: year {p['year']}")
            if check_src(tag, p) is not None and lpev.norm(p["title"])[:40] not in lpev.norm(p["quote"]):
                bad.append(f"{tag}: quote does not contain the title")
    con.close()
    print(f"{school}: {len(ev)} labs, {n} member rows (+{nalso} extra sources), {npub} missing-pub lines, {len(bad)} problems")
    for b in bad[:80]:
        print("  BAD", b)
    bad_total += len(bad)
sys.exit(1 if bad_total else 0)
