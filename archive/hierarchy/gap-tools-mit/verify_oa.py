"""Check an OpenAlex author's works against a stored publication list (MIT gap store; port of gap-tools-cmu/verify_oa.py,
new-PI gap research 2026-10-22).

usage: verify_oa.py AUTHOR_ID PAGE_KEY SURNAME [--from 2016] [--minlen 20] [--show 12]
PAGE_KEY is a live URL or a Wayback id_ capture URL stored in hierarchy/mit/gap-captures.sqlite.
Prints each work whose (normalised) title appears in the page text, with a suggested exact quote: the page-text span
covering the title plus the nearest occurrence of SURNAME (within 400 chars).
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import argparse
import re
import sys

sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-mit'))
import evlib  # noqa: E402
import oa  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("author"); ap.add_argument("page"); ap.add_argument("surname")
ap.add_argument("--from", dest="frm", type=int, default=2016)
ap.add_argument("--minlen", type=int, default=20)
ap.add_argument("--show", type=int, default=12)
a = ap.parse_args()


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z]+", " ", (s or "").lower())).strip()


works = oa.works(a.author, a.frm)
url, cap, sha, text = evlib.row(a.page)
ntext = norm(text)
print(f"author {a.author}: {len(works)} works >= {a.frm}; page sha {sha[:16]} len {len(text)}")
seen, hits = set(), 0
for w in works:
    t = w.get("title") or ""
    nt = norm(t)
    if len(nt) < a.minlen or nt in seen:
        continue
    seen.add(nt)
    if nt in ntext:
        hits += 1
        words = [re.escape(x) for x in re.findall(r"[0-9A-Za-z]+", t)]
        m = re.search(r"\W*".join(words), text, flags=re.I)
        q = None
        if m:
            best = None
            for sm in re.finditer(re.escape(a.surname), text):
                d = min(abs(sm.start() - m.start()), abs(sm.end() - m.end()))
                if d <= 400 and (best is None or d < best[0]):
                    best = (d, sm.start(), sm.end())
            if best:
                s, e = min(best[1], m.start()), max(best[2], m.end())
                q = text[s:e]
        if hits <= a.show:
            print(f"  MATCH {w['publication_year']} {w['id'].rsplit('/',1)[-1]} | {t[:90]}")
            print(f"     quote: {q!r}" if q else "     (no surname within 400 chars)")
print("matches:", hits)
