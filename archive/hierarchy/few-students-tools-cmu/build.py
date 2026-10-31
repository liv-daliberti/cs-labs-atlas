"""Build hierarchy/cmu/few-students-evidence.json from decisions_*.py + few-students-captures.sqlite, then
re-verify every quote against the stored bytes (sha256 + exact substring + url/capture_url match).

usage: build.py [--dry] [--only decisions_a,decisions_b]   (--dry: resolve + verify, do not write the output)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import hashlib
import importlib
import json
import re
import sqlite3
import sys
import unicodedata
import zlib

TOOLS = str(P.HIERARCHY / 'few-students-tools-cmu')
sys.path.insert(0, TOOLS)
import capstore  # noqa: E402

HIER = str(P.HIERARCHY / 'cmu')
INPUT = HIER + "/few-students-input.json"
OUTPUT = HIER + "/few-students-evidence.json"
MODULES = ["decisions_a", "decisions_b", "decisions_c", "decisions_d"]
MAXQ = 700
MAXQ_LONG = 4000
ROLES = ("phd", "postdoc", "masters", "undergraduate", "member", "other")

_text_cache = {}
problems = []


def con():
    return sqlite3.connect(capstore.DB, timeout=120)


def capture(c, url):
    cols = "id,url,capture_url,sha256,content"
    if capstore.WAYBACK_RX.match(url):
        row = c.execute(f"SELECT {cols} FROM captures WHERE capture_url=? AND status=200 AND content IS NOT NULL "
                        "ORDER BY id DESC LIMIT 1", (url,)).fetchone()
    else:
        row = c.execute(f"SELECT {cols} FROM captures WHERE url=? AND capture_url IS NULL AND status=200 "
                        "AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (url,)).fetchone()
        if not row:
            row = c.execute(f"SELECT {cols} FROM captures WHERE (url=? OR final_url=?) AND capture_url IS NULL "
                            "AND status=200 AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (url, url)).fetchone()
    return row


def texts(row):
    if row[0] not in _text_cache:
        b = zlib.decompress(row[4])
        _text_cache[row[0]] = (capstore.page_text(b), capstore.raw_text(b))
    return _text_cache[row[0]]


def resolve(c, spec, who, must):
    row = capture(c, spec["url"])
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
            j = t.find(spec["e"], i + len(spec["s"]))
            if j < 0:
                continue
            quote = t[i:j + len(spec["e"])]
            break
    if quote is None:
        problems.append(f"{who}: quote not found in {spec['url']}: {spec.get('q') or (spec.get('s'), spec.get('e'))!r}")
        return None
    lim = MAXQ_LONG if (spec.get("long") or spec.get("raw")) else MAXQ
    if len(quote) > lim:
        problems.append(f"{who}: quote too long ({len(quote)}) in {spec['url']}: {quote[:100]}...")
    for tok in must:
        if tok not in quote:
            problems.append(f"{who}: token {tok!r} missing from quote: {quote[:160]}")
    out = {"url": row[1]}
    if row[2]:
        out["capture_url"] = row[2]
    out["sha256"] = row[3]
    out["quote"] = quote
    return out


def norm(name):
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return " ".join(s.split())


def load(only=None):
    D = {}
    for m in (only or MODULES):
        try:
            mod = importlib.import_module(m)
        except ModuleNotFoundError:
            print("module not present yet:", m)
            continue
        for k, v in mod.D.items():
            if k in D:
                problems.append(f"{k}: decided in more than one module ({m})")
            D[k] = v
    return D


def main(dry=False, only=None):
    inp = json.load(open(INPUT))
    D = load(only)
    names = [r["pi"] for r in inp]
    extra = [n for n in D if n not in names]
    if extra:
        problems.append(f"decisions for PIs not in input: {extra}")
    c = con()
    out = []
    for r in inp:
        pi = r["pi"]
        d = D.get(pi)
        if d is None:
            if not only:
                problems.append(f"{pi}: no decision")
            continue
        held = {norm(x) for x in r.get("students_already", [])}
        studs, seen = [], {}
        for st in d.get("students", []):
            who = f"{pi}/student {st['name']}"
            if st["role"] not in ROLES:
                problems.append(f"{who}: bad role {st['role']}")
            y = st.get("years")
            if y is not None and not (isinstance(y, list) and len(y) == 2 and all(v is None or isinstance(v, int) for v in y)):
                problems.append(f"{who}: bad years {y!r}")
            ev = resolve(c, st["ev"], who, st.get("must") or [st["name"]])
            if not ev:
                continue
            o = {"name": st["name"], "role": st["role"], "years": y}
            o.update(ev)
            if st.get("note"):
                o["note"] = st["note"]
            if norm(st["name"]) in held:
                o["already_held"] = True
            k = norm(st["name"])
            if k in seen:
                problems.append(f"{who}: duplicate student row (keep one row per student; put extra sources in note)")
            seen[k] = 1
            studs.append(o)
        row = {"pi": pi, "students": studs, "lab_note": d.get("lab_note", ""), "notes": d.get("notes", "")}
        if not row["lab_note"]:
            problems.append(f"{pi}: empty lab_note")
        out.append(row)
    c.close()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
    if not dry:
        with open(OUTPUT, "w") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)
        print("wrote", OUTPUT, len(out), "rows")
        out = json.load(open(OUTPUT))
    verify(out)
    summary(inp, out)
    return out


def verify(rows):
    """Independent re-check: stored bytes hash to sha256, quote is an exact substring of their collapsed text,
    url/capture_url match the stored row, and the quote contains the student's name tokens."""
    c = con()
    n = bad = 0
    for r in rows:
        for it in r["students"]:
            n += 1
            q = ("SELECT content, url, capture_url FROM captures WHERE sha256=? AND url=? AND content IS NOT NULL "
                 + ("AND capture_url=? " if it.get("capture_url") else "AND capture_url IS NULL ") + "LIMIT 1")
            args = (it["sha256"], it["url"]) + ((it["capture_url"],) if it.get("capture_url") else ())
            row = c.execute(q, args).fetchone()
            ok = False
            if row:
                b = zlib.decompress(row[0])
                ok = (hashlib.sha256(b).hexdigest() == it["sha256"]
                      and (it["quote"] in capstore.page_text(b) or it["quote"] in capstore.raw_text(b)))
            if not ok:
                bad += 1
                print("VERIFY FAIL", r["pi"], it["name"], it.get("url"), it["quote"][:80])
    c.close()
    print(f"verified {n - bad}/{n} quotes against stored bytes")


def summary(inp, rows):
    by = {r["pi"]: r for r in rows}
    for r in inp:
        o = by.get(r["pi"])
        if not o:
            continue
        held = {norm(x) for x in r["students_already"]}
        new = {norm(s["name"]) for s in o["students"]} - held
        # students_already may hold one person twice (spelling variants); count distinct held names as given
        print(f"  {r['pi']:<32} before {len(r['students_already'])}  new {len(new):>3}  rows {len(o['students'])}")


if __name__ == "__main__":
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")
    main(dry="--dry" in sys.argv or only is not None, only=only)
