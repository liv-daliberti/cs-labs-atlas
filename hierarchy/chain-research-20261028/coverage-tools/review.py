"""Decision store for the coverage review. decisions.json (keyed school|name) -> ../coverage-review.json (input order).
Every evidence/advisee quote is cut verbatim from a capture row in captures.sqlite (sha256 of raw bytes)."""
import json, os, re, sqlite3
from datetime import date
from lib import fetch, import_sha, con, H
D = os.path.dirname(os.path.abspath(__file__)) + "/decisions.json"
OUT = H + "/chain-research-20261028/coverage-review.json"
INP = H + "/chain-research-20261028/coverage-input.json"

def load():
    return json.load(open(D)) if os.path.exists(D) else {}

def _wb_observed(u):
    m = re.search(r"web\.archive\.org/web/(\d{8})", u)
    return f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:8]}" if m else None

def quote_from(text, pat, w=0, maxlen=400):
    m = re.search(pat, text)
    if not m: return None
    q = text[max(0, m.start() - w): m.end() + w]
    return q[:maxlen]

def ev(url, pat, capture_url=None, sha=None, w=0, gap=2.0, observed=None):
    """Evidence from a capture: fetch (or copy existing by sha) and cut a verbatim quote by regex."""
    cu = capture_url or url
    if sha:
        text = import_sha(cu, sha)
        if text is None: raise KeyError(("no stored capture", cu, sha))
    else:
        r = fetch(cu, gap=gap)
        if r["status"] != 200 or r.get("error"): raise RuntimeError((cu, r["status"], r.get("error")))
        text, sha = r["text"], r["sha256"]
        observed = observed or _wb_observed(cu) or r["fetched_at"][:10]
    q = quote_from(text, pat, w)
    if q is None: raise ValueError(("pattern not found", cu, pat))
    e = {"url": url, "sha256": sha, "quote": q, "observed": observed or _wb_observed(cu) or str(date.today())}
    if capture_url and capture_url != url: e["capture_url"] = capture_url
    return e

def adv(e, name, role, years=None):
    return {"name": name, "role": role, "years": years, "url": e["url"], "sha256": e["sha256"], "quote": e["quote"], **({"capture_url": e["capture_url"]} if "capture_url" in e else {})}

def decide(school, name, verdict, area, dept, rank, reason, evidence, period_hint=None, advisees=None, openalex=None, **extra):
    d = load()
    d[f"{school}|{name}"] = {"school": school, "name": name, "verdict": verdict, "computing_area": area, "home_department": dept,
        "rank": rank, "reason": reason, "period_hint": period_hint, "evidence": evidence,
        "advisees": advisees or [], "openalex": openalex or [], **extra}
    json.dump(d, open(D, "w"), indent=1, ensure_ascii=False)
    write()

def write():
    d = load(); inp = json.load(open(INP))
    out = [d[f"{x['school']}|{x['name']}"] for x in inp if f"{x['school']}|{x['name']}" in d]
    json.dump(out, open(OUT + ".tmp", "w"), indent=1, ensure_ascii=False); os.replace(OUT + ".tmp", OUT)
    return len(out), len(inp)

def verify():
    c = con(); bad = n = 0
    for r in json.load(open(OUT)):
        for e in r["evidence"] + r["advisees"]:
            n += 1
            row = c.execute("select text from captures where sha256=? and url=?", (e["sha256"], e.get("capture_url", e["url"]))).fetchone()
            if not row or e["quote"] not in row[0]:
                bad += 1; print("BAD", r["school"], r["name"], e["url"], e["quote"][:60])
    print({"people": len(json.load(open(OUT))), "quotes": n, "bad": bad})

def listing_ev(school, name, which="example"):
    """Evidence from the listed-not-in-census example capture (copied by sha)."""
    x = {y["name"]: y for y in json.load(open(f"{H}/{school}/listed-not-in-census.json"))}[name]
    ex = x["example"]
    try:
        return ev(ex["capture_url"], re.escape(ex["quote"]), sha=ex["sha256"], observed=_wb_observed(ex["capture_url"]))
    except ValueError:
        return ev(ex["capture_url"], r"\W*".join(re.escape(t) for t in ex["quote"].split()), sha=ex["sha256"], observed=_wb_observed(ex["capture_url"]))


def _raw_text(url, sha):
    import zlib, gzip
    row = con().execute("select raw from captures where url=? and sha256=?", (url, sha)).fetchone()
    b = zlib.decompress(row[0])
    if b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
    return b.decode("utf-8", "replace")

def ev_raw(e, pat):
    """Quote cut from the raw HTML (markup) of an already-captured evidence row e; marked quote_source=raw_html."""
    u = e.get("capture_url", e["url"])
    q = quote_from(_raw_text(u, e["sha256"]), pat)
    if q is None: raise ValueError(("raw pattern not found", u, pat))
    return {**{k: v for k, v in e.items() if k != "quote"}, "quote": q, "quote_source": "raw_html"}

def verify2():
    c = con(); bad = n = 0
    for r in json.load(open(OUT)):
        for e in r["evidence"] + r["advisees"] + r.get("advisees_if_admitted", []):
            n += 1
            u = e.get("capture_url", e["url"])
            row = c.execute("select text from captures where sha256=? and url=?", (e["sha256"], u)).fetchone()
            ok = bool(row) and (e["quote"] in (_raw_text(u, e["sha256"]) if e.get("quote_source") == "raw_html" else row[0]))
            if not ok: bad += 1; print("BAD", r["school"], r["name"], u, e["quote"][:60])
    print({"people": len(json.load(open(OUT))), "quotes": n, "bad": bad})

def census_row(school, cname):
    import json
    from lib import ROOT
    for f in [f"{ROOT}/census/{school}-faculty.json", f"{ROOT}/census/{school}-additions.json"]:
        try: c = json.load(open(f))
        except FileNotFoundError: continue
        rows = c if isinstance(c, list) else c.get("faculty", c.get("additions", []))
        for r in rows:
            if r["name"] == cname: return r, f.split("/")[-1]
    return None, None

def census_ev(school, cname, k=1):
    r, f = census_row(school, cname)
    out = []
    for s in (r.get("sources") or []):
        if len(out) >= k: break
        try:
            out.append(ev(s["url"], r"\W*".join(re.escape(t) for t in s["quote"].split()), sha=s["sha256"], observed=s.get("observed")))
        except Exception:
            try: out.append(ev(s["url"], re.escape(s["quote"])))
            except Exception as ex: print("census_ev fail", cname, s["url"], ex)
    return out, r, f

if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["verify"]: verify2()
    else: print(write())

def mit_lev(name):
    """MIT listing evidence; falls back to CSAIL JSON-row patterns when the stored quote is a parsed field join."""
    try:
        return listing_ev("mit", name)
    except ValueError:
        x = {y["name"]: y for y in json.load(open(f"{H}/mit/listed-not-in-census.json"))}[name]
        ex = x["example"]; n = re.escape(name)
        for pat in [r'"ss_name":"[^"]+", "ss_field_title":"[^"]+", "ss_title":"' + n + '"',
                    r'"ss_name":"[^"]+"[^{}]{0,300}?"ss_title":"' + n + '"',
                    r'"label":"' + n + r'", "name":"[^"]+", "email":"[^"]*", "phone":"[^"]*", "url":"[^"]+", "position":"[^"]+"']:
            try: return ev(ex["capture_url"], pat, sha=ex["sha256"], observed=_wb_observed(ex["capture_url"]))
            except ValueError: pass
        raise

def dspace_adv(url, adv, author):
    return ev(url, re.escape(adv) + r'".{0,250}?"dc\.contributor\.author" : \[ \{ "value" : "' + re.escape(author))

def oa_ev(name, school, idx=0, author_id=None):
    """Evidence from an OpenAlex author-search capture: quote the author's display_name and first topic."""
    import oa
    res = oa.authors(name, school)
    a = next((x for x in res if author_id and x["id"].endswith(author_id)), None) if author_id else (res[idx] if len(res) > idx else None)
    if not a: raise KeyError(("no openalex author", name))
    params = {"search": name, "per-page": "8", "select": "id,display_name,works_count,last_known_institutions,topics,affiliations"}
    if school: params["filter"] = f"affiliations.institution.id:{oa.INST[school]}"
    url = "https://api.openalex.org/authors?" + "&".join(f"{k}={v}" for k, v in params.items())
    row = con().execute("select sha256, text from captures where url=? and status=200 order by id desc limit 1", (url,)).fetchone()
    t1 = a["topics"][0]["display_name"] if a.get("topics") else None
    tops = [t["display_name"] for t in (a.get("topics") or [])[:3]]
    m = re.search(re.escape(json.dumps(a["id"])) + r".{0,3000}?" + re.escape(json.dumps(t1)), row[1], re.S) if t1 else None
    q = row[1][m.start(): m.end()] if m and m.end() - m.start() < 3000 else None
    if q is None or len(q) > 600:
        m2 = re.search(r'"display_name":\s*' + re.escape(json.dumps(t1)), row[1]); q = row[1][m2.start(): m2.end()]
    return {"url": url, "sha256": row[0], "quote": q, "observed": "2026-10-28", "note": f"OpenAlex {a['id']} {a['display_name']}; top topics: {tops}"}, a["id"]

def cmu_lev(name):
    try:
        return listing_ev("cmu", name)
    except ValueError:
        x = {y["name"]: y for y in json.load(open(f"{H}/cmu/listed-not-in-census.json"))}[name]
        ex = x["example"]; n = re.escape(name)
        for pat in [r'"n":"' + n + r'","aff":"[^"]+"[^{}]{0,250}?"dept":\["[^"\]]+"\]', r'"n":"' + n + r'"[^{}]{0,300}', r'Business Office \| Institute for Software Research \| > People > Core Faculty']:
            try: return ev(ex["capture_url"], pat, sha=ex["sha256"], observed=_wb_observed(ex["capture_url"]))
            except ValueError: pass
        raise
