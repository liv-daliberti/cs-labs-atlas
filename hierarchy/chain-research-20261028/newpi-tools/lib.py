"""Helpers for the 2026-10-28 coverage review: copy existing verified captures into captures.sqlite,
name index over census + additions + pis per school, input/listing join."""
import hashlib, json, re, sqlite3, zlib, unicodedata
from cap import con, to_text, fetch, ctx
ROOT = "/n/fs/resemble/cs-atlas/work"
H = ROOT + "/hierarchy"
SRC_DBS = [ROOT + f"/listings/{s}/captures.sqlite" for s in ["princeton", "stanford", "cmu", "mit", "berkeley", "epfl"]] + [
    H + f"/cs-related-captures-{s}.sqlite" for s in ["stanford", "mit", "epfl", "princeton", "berkeley"]] + [
    H + "/cs-related-captures.sqlite", H + "/missing-pi-captures.sqlite", H + "/period-captures.sqlite",
    H + "/home-departments-captures.sqlite", H + "/chain-research-20261028/pi-basis-tools/captures.sqlite", H + "/chain-research-20261028/coverage-tools/captures.sqlite"] + [
    H + f"/{s}/cs-related-captures.sqlite" for s in ["princeton", "cmu", "mit", "berkeley", "epfl"]] + [
    H + f"/{s}/gap-captures.sqlite" for s in ["princeton", "cmu", "mit", "berkeley", "epfl"]] + [
    H + f"/{s}/few-students-captures.sqlite" for s in ["princeton", "cmu", "mit", "berkeley", "epfl"]] + [
    H + f"/{s}/thesis-captures.sqlite" for s in ["princeton", "stanford", "cmu", "mit", "berkeley", "epfl"]] + [
    H + f"/{s}/labpage-captures.sqlite" for s in ["princeton", "stanford", "cmu", "mit", "berkeley", "epfl"]]

def _raw_from(db, sha):
    try:
        s = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        tabs = [r[0] for r in s.execute("select name from sqlite_master where type='table'")]
    except Exception:
        return None
    for t in tabs:
        cols = [r[1] for r in s.execute(f"pragma table_info({t})")]
        if "sha256" not in cols: continue
        rc = next((c for c in ["raw_zlib", "raw", "content", "body"] if c in cols), None)
        if not rc: continue
        uc = [c for c in ["capture_url", "url", "final_url", "page_url"] if c in cols]
        fc = "fetched_at" if "fetched_at" in cols else ("at" if "at" in cols else "null")
        try:
            rows = s.execute(f"select {rc}, {', '.join(uc)}, {fc} from {t} where sha256=? limit 3", (sha,)).fetchall()
        except Exception:
            continue
        for r in rows:
            body = r[0]
            if body is None: continue
            if isinstance(body, str): body = body.encode()
            for cand in (body,):
                try: b2 = zlib.decompress(cand)
                except Exception: b2 = cand
                if hashlib.sha256(b2).hexdigest() == sha:
                    return b2, [u for u in r[1:-1] if u], r[-1]
    return None

def import_sha(url, sha, note=""):
    """Ensure a capture of `url` with raw sha256 `sha` is in captures.sqlite (copied from an existing verified store)."""
    c = con()
    row = c.execute("select text from captures where sha256=? and url=?", (sha, url)).fetchone()
    if row: return row[0]
    for db in SRC_DBS:
        got = _raw_from(db, sha)
        if got:
            body, urls, fat = got
            c.execute("insert into captures(url,final_url,fetched_at,status,sha256,text,raw,error) values(?,?,?,?,?,?,?,?)",
                      (url, urls[0] if urls else url, fat, 200, sha, to_text(body), zlib.compress(body), "copied_from " + db + " " + note))
            c.commit()
            return to_text(body)
    return None

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(dr|prof|jr|iii|ii)\b\.?", " ", s)
    return re.sub(r"[^a-z ]+", " ", s).split()

def key(s):
    t = norm(s)
    return (t[-1], t[0][0]) if t else None

def school_people(school):
    out = []
    try:
        c = json.load(open(f"{ROOT}/census/{school}-faculty.json"))
        rows = c if isinstance(c, list) else c["faculty"]
        for r in rows: out.append(("census", r["name"], [r["name"]] + (r.get("aliases") or [])))
    except FileNotFoundError: pass
    try:
        a = json.load(open(f"{ROOT}/census/{school}-additions.json"))
        a = a if isinstance(a, list) else a.get("additions", a.get("faculty", []))
        for r in a: out.append(("additions", r["name"], [r["name"]] + (r.get("aliases") or [])))
    except FileNotFoundError: pass
    for r in json.load(open(f"{H}/{school}/pis.json")):
        out.append(("pis", r["pi"], [r["pi"]] + (r.get("names") or [])))
    return out

def matches(school, name, people=None):
    people = people or school_people(school)
    k = key(name); nn = " ".join(norm(name))
    hits = []
    for src, nm, al in people:
        for a in al:
            if " ".join(norm(a)) == nn: hits.append((src, nm, "exact")); break
            if k and key(a) == k: hits.append((src, nm, "last+initial")); break
            t = norm(a)
            if k and t and t[-1] == k[0] and len(k[0]) > 3: hits.append((src, nm, "last")); break
    return hits

def listed(school):
    return {x["name"]: x for x in json.load(open(f"{H}/{school}/listed-not-in-census.json"))}
