"""Add/replace one pair's verdict in same-name-review.json (whole file rewritten each time).
Evidence items give url + quote (+ observed); sha256/capture info is filled from captures.sqlite and the quote is
checked verbatim against the captured text (whitespace-normalized) or raw bytes. Pre-existing evidence from the
input records can be passed with an explicit sha256 and 'from_input': true (not re-verified here)."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[3] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, sys, re, sqlite3, zlib, os, html
from cap import DB
OUT = str(P.HIERARCHY / 'chain-research-20261028/same-name-review.json')
INP = str(P.HIERARCHY / 'chain-research-20261028/same-name-input.json')
norm = lambda s: re.sub(r"\s+", " ", s).strip()
def main():
    e = json.load(sys.stdin)
    c = sqlite3.connect(DB)
    for ev in e["evidence"]:
        if ev.get("from_input"):
            continue
        r = c.execute("select final_url,fetched_at,status,sha256,text,raw from captures where url=? and status=200 order by id desc limit 1", (ev["url"],)).fetchone()
        assert r, "no capture for " + ev["url"]
        fu, ft, st, sha, txt, rw = r
        rawtxt = zlib.decompress(rw).decode("utf-8", "replace")
        q = norm(ev["quote"])
        ok = q in norm(txt) or q in norm(rawtxt) or q in norm(html.unescape(rawtxt))
        if not ok:
            try:
                ok = q in norm(json.dumps(json.loads(rawtxt), ensure_ascii=False))
            except Exception:
                pass
        assert ok, "quote not verbatim in capture: " + ev["url"] + " :: " + q[:120]
        ev["sha256"] = sha; ev["fetched_at"] = ft; ev["status"] = st
        if fu != ev["url"]: ev["final_url"] = fu
        ev["capture_db"] = DB
    data = json.load(open(OUT)) if os.path.exists(OUT) else []
    key = lambda x: (x["school"], x["pi"], x["a"][0], x["b"][0])
    data = [x for x in data if key(x) != key(e)] + [e]
    order = [(i["school"], i["pi"], i["a"][0], i["b"][0]) for i in json.load(open(INP))]
    data.sort(key=lambda x: order.index(key(x)) if key(x) in order else 999)
    tmp = OUT + ".tmp"; json.dump(data, open(tmp, "w"), indent=1, ensure_ascii=False); os.replace(tmp, OUT)
    print("wrote", len(data), "entries;", e["verdict"], e["a"][1], "|", e["b"][1])
main()
