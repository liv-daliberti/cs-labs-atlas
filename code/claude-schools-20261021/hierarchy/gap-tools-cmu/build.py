"""Build hierarchy/cmu/gap-evidence.json from decisions.py + the gap capture DB, then re-verify every quote.

Evidence specs (see decisions.py):
  dict(url=U, q=QUOTE)              exact quote (must be a substring of the capture's collapsed text)
  dict(url=U, s=START, e=END)       quote = text from the first START up to and including the first END after it
  optional: after=STR (search START after the first STR), must=[tokens] (all must be in the quote), raw=True
U is either a live URL (matches captures.url with capture_url NULL, else any capture of that url) or a Wayback
id_ URL (matches captures.capture_url). The latest status-200 capture is used.

usage: build.py [--dry]
"""
import json
import re
import sqlite3
import sys
import zlib

TOOLS = "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-cmu"
sys.path.insert(0, TOOLS)
import capstore  # noqa: E402
import decisions  # noqa: E402

HIER = "/n/fs/resemble/cs-atlas/work/hierarchy/cmu"
INPUT = HIER + "/gap-input.json"
OUTPUT = HIER + "/gap-evidence.json"
MAXQ_HTML = 700
MAXQ_RAW = 1600

con = sqlite3.connect(capstore.DB)
_text_cache = {}


def capture(url):
    if capstore.WAYBACK_RX.match(url):
        row = con.execute("SELECT id,url,capture_url,sha256,content FROM captures WHERE capture_url=? AND status=200 "
                          "AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    else:
        row = con.execute("SELECT id,url,capture_url,sha256,content FROM captures WHERE url=? AND capture_url IS NULL "
                          "AND status=200 AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (url,)).fetchone()
        if not row:
            row = con.execute("SELECT id,url,capture_url,sha256,content FROM captures WHERE (url=? OR final_url=?) "
                              "AND status=200 AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (url, url)).fetchone()
    return row


def texts(row):
    if row[0] not in _text_cache:
        c = zlib.decompress(row[4])
        _text_cache[row[0]] = (capstore.page_text(c), capstore.raw_text(c))
    return _text_cache[row[0]]


problems = []


def resolve(spec, who, default_must):
    row = capture(spec["url"])
    if not row:
        problems.append(f"{who}: no 200 capture for {spec['url']}")
        return None
    pt, rt = texts(row)
    srcs = [rt] if spec.get("raw") else [pt, rt]
    quote = None
    for t in srcs:
        if "q" in spec:
            if spec["q"] in t:
                quote = spec["q"]
                break
        else:
            base = 0
            if spec.get("after"):
                base = t.find(spec["after"])
                if base < 0:
                    continue
            i = t.find(spec["s"], base)
            if i < 0:
                continue
            j = t.find(spec["e"], i + len(spec["s"]) if spec["e"] != spec["s"] else i)
            if j < 0:
                continue
            quote = t[i:j + len(spec["e"])]
            break
    if quote is None:
        problems.append(f"{who}: quote not found in {spec['url']}: {spec.get('q') or (spec.get('s'), spec.get('e'))!r}")
        return None
    lim = MAXQ_RAW if (spec.get("raw") or spec.get("long") or quote not in pt) else MAXQ_HTML
    if len(quote) > lim:
        problems.append(f"{who}: quote too long ({len(quote)}) in {spec['url']}: {quote[:100]}...")
    for tok in (spec.get("must") or default_must):
        if tok not in quote:
            problems.append(f"{who}: token {tok!r} missing from quote: {quote[:160]}")
    out = {"url": row[1]}
    if row[2]:
        out["capture_url"] = row[2]
    out["sha256"] = row[3]
    out["quote"] = quote
    return out


def surname_tokens(name):
    return [name.split()[-1]]


def main(dry=False):
    gap = json.load(open(INPUT))
    D = decisions.D
    names = [r["pi"] for r in gap]
    missing = [n for n in names if n not in D]
    extra = [n for n in D if n not in names]
    if missing or extra:
        print("missing decisions:", missing)
        print("extra decisions:", extra)
    out = []
    for r in gap:
        pi = r["pi"]
        d = D.get(pi)
        if d is None:
            continue
        pmust = d.get("pi_must") or surname_tokens(pi)
        row = {"pi": pi, "status": d["status"]}
        row["status_evidence"] = [x for x in (resolve(s, f"{pi}/status", pmust) for s in d.get("status_ev", [])) if x]
        studs = []
        for st in d.get("students", []):
            ev = resolve(st["ev"], f"{pi}/student {st['name']}", st.get("must") or surname_tokens(st["name"]))
            if not ev:
                continue
            o = {"name": st["name"], "role": st["role"], "years": st.get("years")}
            o.update(ev)
            if st.get("note"):
                o["note"] = st["note"]
            studs.append(o)
        row["students"] = studs
        ident = d.get("identity", {})
        iev = []
        for e in ident.get("evidence", []):
            x = resolve(e["ev"], f"{pi}/identity {e['kind']}", e["ev"].get("must") or pmust)
            if x:
                y = {"kind": e["kind"]}
                y.update(x)
                y["note"] = e.get("note", "")
                iev.append(y)
        row["identity"] = {"dblp": ident.get("dblp", []), "orcid": ident.get("orcid", []),
                           "openalex": ident.get("openalex", []), "evidence": iev}
        cp = r.get("collection_person_ids") or []
        row["collection_person_id"] = d.get("collection_person_id", cp[0] if cp else None)
        row["appointment_notes"] = [x for x in (resolve(s, f"{pi}/appointment", pmust) for s in d.get("appt", [])) if x]
        row["notes"] = d.get("notes", "")
        if d["status"] not in ("pi", "not_pi_in_window"):
            problems.append(f"{pi}: bad status {d['status']}")
        if not row["status_evidence"]:
            problems.append(f"{pi}: no status evidence")
        for st in studs:
            if st["role"] not in ("phd", "postdoc", "masters", "undergraduate", "member", "other"):
                problems.append(f"{pi}: bad role {st['role']} for {st['name']}")
        out.append(row)
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
    if not dry:
        with open(OUTPUT, "w") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)
        print("wrote", OUTPUT, len(out), "rows")
    verify(out if dry else json.load(open(OUTPUT)))
    return out


def verify(rows):
    """Re-verify every quote against the stored bytes it cites (by sha256)."""
    n = bad = 0
    for r in rows:
        items = list(r["status_evidence"]) + list(r["students"]) + list(r["identity"]["evidence"]) + list(r["appointment_notes"])
        for it in items:
            n += 1
            c = capstore.get_by_sha(it["sha256"])
            ok = c is not None and (it["quote"] in capstore.page_text(c) or it["quote"] in capstore.raw_text(c))
            if not ok:
                bad += 1
                print("VERIFY FAIL", r["pi"], it.get("url"), it["quote"][:80])
    print(f"verified {n - bad}/{n} quotes against stored bytes")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
