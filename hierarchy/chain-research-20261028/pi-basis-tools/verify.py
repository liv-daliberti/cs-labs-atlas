"""Re-check every quote in pi-basis-review.json: the sha256 must be a stored capture whose raw bytes hash to it, and the quote must be in its text."""
import hashlib, json, sqlite3, zlib
from cap import DB
c = sqlite3.connect(DB)
d = json.load(open("/n/fs/resemble/cs-atlas/work/hierarchy/chain-research-20261028/pi-basis-review.json"))
bad = n = 0
for r in d:
    for e in r["evidence"] + r["advisees"]:
        n += 1
        row = c.execute("select raw, text, url from captures where sha256=? limit 1", (e["sha256"],)).fetchone()
        ok = row and hashlib.sha256(zlib.decompress(row[0])).hexdigest() == e["sha256"] and e["quote"] in row[1] and row[2] == e.get("capture_url", e["url"])
        if not ok:
            bad += 1; print("BAD", r["pi"], e["url"], e["quote"][:60])
print({"people": len(d), "quotes": n, "bad": bad})
