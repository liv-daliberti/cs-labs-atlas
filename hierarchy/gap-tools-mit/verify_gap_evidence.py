"""Re-verify gap-evidence.json against the stored bytes in gap-captures.sqlite.

For every quote (status_evidence, students, identity.evidence, appointment_notes): the capture with that sha256 exists in the
store, sha256(zlib-decompressed bytes) equals the recorded sha256, the quote is an exact substring of the page's
whitespace-collapsed text, and the quote contains the person's name (all name tokens, case/diacritics-insensitive).
Also checks that no stored URL carries an API key.
usage: verify_gap_evidence.py [PATH]"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib
import json
import sqlite3
import sys
import zlib

sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-mit'))
import capstore  # noqa: E402
from evlib import has_name  # noqa: E402

DB = capstore.DB


def verify(path):
    rows = json.load(open(path))
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    texts = {}

    def text_of(sha):
        if sha not in texts:
            r = con.execute("SELECT content FROM captures WHERE sha256=? AND content IS NOT NULL LIMIT 1", (sha,)).fetchone()
            if not r:
                texts[sha] = None
            else:
                b = zlib.decompress(r[0])
                texts[sha] = capstore.page_text(b) if hashlib.sha256(b).hexdigest() == sha else "<<sha mismatch>>"
        return texts[sha]

    bad, n = [], 0
    for row in rows:
        pi = row["pi"]
        items = [("status", e, e.get("name_check") or pi) for e in row.get("status_evidence") or []]
        items += [("student", s, s["name"]) for s in row.get("students") or []]
        items += [("identity", e, e.get("name_check") or pi) for e in (row.get("identity") or {}).get("evidence") or []]
        items += [("appointment", e, None) for e in row.get("appointment_notes") or []]
        for kind, e, name in items:
            n += 1
            t = text_of(e.get("sha256"))
            q = e.get("quote") or ""
            if t is None:
                bad.append((pi, kind, "no capture for sha", e.get("sha256")))
            elif t == "<<sha mismatch>>":
                bad.append((pi, kind, "sha mismatch", e.get("sha256")))
            elif not q or q not in t:
                bad.append((pi, kind, "quote not in page", q[:80]))
            elif name and not has_name(q, name):
                bad.append((pi, kind, "quote lacks name", name, q[:80]))
    leaks = con.execute("SELECT count(*) FROM captures WHERE url LIKE '%api_key%' OR final_url LIKE '%api_key%' OR capture_url LIKE '%api_key%' "
                        "OR error LIKE '%api_key%'").fetchone()[0]
    if leaks:
        bad.append(("*", "store", "api_key present in stored URLs", leaks))
    print(f"checked {n} quotes in {len(rows)} rows; {len(bad)} failures")
    for b in bad:
        print("  FAIL", b)
    return len(bad)


if __name__ == "__main__":
    verify(sys.argv[1] if len(sys.argv) > 1 else str(P.HIERARCHY / 'mit/gap-evidence.json'))
