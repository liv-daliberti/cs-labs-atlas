"""Re-verify every listings.json row of one school against the stored capture bytes.

usage: verify.py <school>
For each row: the capture with that sha256 is loaded from listings/<school>/captures.sqlite, the sha256
of its stored bytes is recomputed, the bytes are re-extracted to text, whitespace is collapsed, and
- `quote` and `section_heading` (when present) must be substrings of that text,
- `quote` must contain `name_as_written`,
- `year` must be the calendar year of `wayback_timestamp`, and `capture_url` must carry that timestamp.
Writes listings/<school>/verify.json.
"""
import hashlib
import json
import os
import sqlite3
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
import extract


def main(school):
    out = wb.school_dir(school)
    rows = json.load(open(os.path.join(out, "listings.json")))
    con = sqlite3.connect("file:" + wb.db_path(school) + "?mode=ro", uri=True)
    cache = {}
    npass = 0
    fails = []
    for r in rows:
        sha = r["sha256"]
        if sha not in cache:
            got = con.execute("select raw_zlib, content_type, capture_url from captures where sha256=? limit 1", (sha,)).fetchone()
            if not got:
                cache[sha] = None
            else:
                raw = zlib.decompress(got[0])
                if hashlib.sha256(raw).hexdigest() != sha:
                    cache[sha] = None
                else:
                    b = extract.blocks(raw, got[1], got[2])
                    cache[sha] = extract.collapse("\n".join(t for _, t in b))
        text = cache[sha]
        why = []
        if text is None:
            why.append("capture bytes missing or hash mismatch")
        else:
            if r["quote"] not in text:
                why.append("quote not in text")
            if r.get("section_heading") and r["section_heading"] not in text:
                why.append("section_heading not in text")
        if r["name_as_written"] not in r["quote"]:
            why.append("name_as_written not in quote")
        if str(r["year"]) != r["wayback_timestamp"][:4] or f"/web/{r['wayback_timestamp']}id_/" not in r["capture_url"]:
            why.append("year/timestamp/capture_url disagree")
        if why:
            fails.append({"pi": r["pi"], "capture_url": r["capture_url"], "quote": r["quote"],
                          "section_heading": r.get("section_heading"), "why": why})
        else:
            npass += 1
    res = {"school": school, "rows": len(rows), "pass": npass, "fail": len(fails), "captures_checked": len(cache),
           "failures": fails[:50]}
    json.dump(res, open(os.path.join(out, "verify.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "failures"}))
    for f in fails[:10]:
        print("FAIL", f)


if __name__ == "__main__":
    main(sys.argv[1])
