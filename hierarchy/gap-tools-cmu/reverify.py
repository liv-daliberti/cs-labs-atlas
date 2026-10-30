"""Independent re-verification of gap-evidence.json: every quote must be an exact substring of the whitespace-collapsed
text of the stored bytes it cites, and those bytes must hash to the cited sha256."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib, json, sqlite3, sys, zlib
sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-cmu'))
import capstore
rows = json.load(open(str(P.HIERARCHY / 'cmu/gap-evidence.json')))
con = sqlite3.connect(capstore.DB)
n = bad = 0
for r in rows:
    items = r["status_evidence"] + r["students"] + r["identity"]["evidence"] + r["appointment_notes"]
    for it in items:
        n += 1
        row = con.execute("SELECT content, url, capture_url FROM captures WHERE sha256=? AND url=? AND content IS NOT NULL LIMIT 1", (it["sha256"], it["url"])).fetchone()
        ok = False
        if row:
            c = zlib.decompress(row[0])
            ok = hashlib.sha256(c).hexdigest() == it["sha256"] and (it["quote"] in capstore.page_text(c) or it["quote"] in capstore.raw_text(c))
            ok = ok and (row[1] == it["url"]) and (row[2] == it.get("capture_url"))
        if not ok:
            bad += 1
            print("FAIL", r["pi"], it.get("url"), it["quote"][:80])
print(f"{n - bad}/{n} quotes verified (hash + substring + url/capture_url match)")
