"""Build home-departments.json from decisions.py + the capture DB, then re-verify every quote.

usage: build_output.py [--dry]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
import zlib

TOOLS = str(P.HIERARCHY / 'home-dept-tools')
sys.path.insert(0, TOOLS)
import capstore  # noqa: E402
import decisions  # noqa: E402

HIER = str(P.HIERARCHY)
INPUT = HIER + "/home-department-input.json"
OUTPUT = HIER + "/home-departments.json"
WB = re.compile(r"^https://web\.archive\.org/web/(\d+)id_/(.+)$")
SELF = re.compile(r"\b(I am|I’m|I'm|He is|She is)\b")

con = sqlite3.connect(capstore.DB)


def capture(url, ok_only=True):
    q = ("SELECT id, url, final_url, status, sha256, content FROM captures WHERE (url=? OR final_url=?) "
         "AND content IS NOT NULL " + ("AND status=200 " if ok_only else "") + "ORDER BY id DESC LIMIT 1")
    return con.execute(q, (url, url)).fetchone()


def sha_ref(m):
    u = m.group(1)
    row = capture(u) or capture(u, ok_only=False)
    if not row:
        raise SystemExit(f"note reference has no capture: {u}")
    tag = "" if row[3] == 200 else f", HTTP {row[3]}"
    return f"sha256 {row[4][:16]}{tag}"


def nfc(s):
    return unicodedata.normalize("NFC", s) if s else s


def main(dry=False):
    rows_in = json.load(open(INPUT))
    by_key = {(d["school"], d["name"]): d for d in decisions.D}
    assert len(by_key) == len(decisions.D), "duplicate decision keys"
    missing = [(r["school"], r["name"]) for r in rows_in if (r["school"], r["name"]) not in by_key]
    extra = set(by_key) - {(r["school"], r["name"]) for r in rows_in}
    if missing or extra:
        raise SystemExit(f"missing decisions: {missing}\nextra decisions: {extra}")

    out, problems = [], []
    for r in rows_in:
        d = by_key[(r["school"], r["name"])]
        row = capture(d["url"])
        if not row:
            problems.append(f"{d['name']}: no 200 capture for {d['url']}"); continue
        cid, url, final_url, status, sha, blob = row
        text = capstore.page_text(zlib.decompress(blob))
        base = 0
        if d.get("q_after"):
            base = text.find(d["q_after"])
            if base < 0:
                problems.append(f"{d['name']}: q_after not found"); continue
        i = text.find(d["q_start"], base)
        if i < 0:
            problems.append(f"{d['name']}: q_start not found: {d['q_start']!r}"); continue
        j = text.find(d["q_end"], i)
        if j < 0:
            problems.append(f"{d['name']}: q_end not found after start: {d['q_end']!r}"); continue
        quote = text[i:j + len(d["q_end"])]
        if len(quote) > 300:
            problems.append(f"{d['name']}: quote too long ({len(quote)}): {quote[:120]}..."); continue
        if d.get("name_tok") and d["name_tok"] not in quote:
            problems.append(f"{d['name']}: name token {d['name_tok']!r} missing")
        if d.get("own_page_sentence") and not SELF.search(quote):
            problems.append(f"{d['name']}: own-page sentence lacks I am/He is/She is")
        if not d.get("name_tok") and not d.get("own_page_sentence"):
            problems.append(f"{d['name']}: neither name token nor own-page sentence")
        for t in d["dept_toks"]:
            if t not in quote:
                problems.append(f"{d['name']}: dept token {t!r} missing from quote")
        if d["status"] == "accepted" and not d["dept_toks"]:
            problems.append(f"{d['name']}: accepted without a department token")
        m = WB.match(url)
        ev = {"url": m.group(2) if m else (final_url or url)}
        if m:
            ev["capture_url"] = url
        ev["sha256"] = sha
        ev["quote"] = quote
        note = re.sub(r"\{sha:([^}]+)\}", sha_ref, d.get("note", ""))
        o = {
            "school": r["school"],
            "name": r["name"],
            "home_department": d["home_department"],
            "also": d["also"],
            "no_academic_department": bool(d["no_academic_department"]),
            "status": d["status"],
            "evidence": ev,
            "note": note,
        }
        if d["status"] == "hold":
            o["reason"] = re.sub(r"\{sha:([^}]+)\}", sha_ref, d["reason"])
        out.append(o)

    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  ", p)
        raise SystemExit(1)
    if not dry:
        with open(OUTPUT, "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("wrote", OUTPUT, len(out))
    verify(out)


def verify(out):
    """Independent re-check: sha256 of stored bytes == recorded sha; quote is a substring of stored text."""
    bad = 0
    for o in out:
        ev = o["evidence"]
        rows = con.execute("SELECT content, sha256 FROM captures WHERE sha256=? AND content IS NOT NULL", (ev["sha256"],)).fetchall()
        if not rows:
            print("VERIFY FAIL no stored bytes", o["name"]); bad += 1; continue
        ok_any = False
        for blob, stored_sha in rows:
            raw = zlib.decompress(blob)
            if hashlib.sha256(raw).hexdigest() != ev["sha256"] or stored_sha != ev["sha256"]:
                continue
            if ev["quote"] in capstore.page_text(raw):
                ok_any = True
                break
        if not ok_any:
            print("VERIFY FAIL", o["name"]); bad += 1
        if o["status"] == "accepted" and len(ev["quote"]) > 300:
            print("VERIFY FAIL length", o["name"]); bad += 1
    print(f"verified {len(out) - bad}/{len(out)} rows (sha256 matches stored bytes; quote is substring of stored page text)")
    if bad:
        raise SystemExit(2)


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
