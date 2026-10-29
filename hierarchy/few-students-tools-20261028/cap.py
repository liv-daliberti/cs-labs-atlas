"""Polite fetcher + capture store for the 2026-10-28 few-students / zero-paper investigation.
Every page relied on is a row in captures.sqlite: url, final_url, fetched_at, status, sha256 (raw bytes), text, raw (zlib).
Off limits: dblp.org, scholar.google.*. Bot challenges are stored and never worked around. API keys never stored."""
import hashlib, re, sqlite3, sys, time, zlib, html
from datetime import datetime, timezone
from urllib.parse import urlsplit
import requests

DB = "/n/fs/resemble/cs-atlas/work/hierarchy/few-students-tools-20261028/captures.sqlite"
UA = "princeton-cs-research-sweep/1.0 (faculty lab membership research; academic, non-commercial; polite 1 req/2s/host)"
BLOCKED = re.compile(r"(^|\.)(dblp\.org|dblp\.uni-trier\.de)$|(^|\.)scholar\.google\.", re.I)
CHAL = re.compile(rb"(<title>\s*Just a moment|cf_chl_opt|cf-browser-verification|Attention Required! \| Cloudflare|Checking your browser|_Incapsula_Resource|px-captcha|Verifying you are human|Pardon Our Interruption|/TSPD/|bobcmn)", re.I)
_last = {}
S = requests.Session(); S.headers.update({"User-Agent": UA, "Accept-Language": "en"})

def con():
    c = sqlite3.connect(DB)
    c.execute("create table if not exists captures(id integer primary key, url text, final_url text, fetched_at text, status int, sha256 text, text text, raw blob, error text)")
    return c

def to_text(b):
    if b[:5] == b"%PDF-":
        import subprocess
        p = subprocess.run(["pdftotext", "-layout", "-", "-"], input=b, capture_output=True, timeout=120)
        return re.sub(r"[ \t]+", " ", p.stdout.decode("utf-8", "replace"))
    s = b.decode("utf-8", "replace")
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def fetch(url, force=False, gap=2.0):
    host = urlsplit(url).hostname or ""
    if BLOCKED.search(host) or ("web.archive.org" in host and re.search(r"dblp\.(org|uni-trier)", url)):
        raise RuntimeError("blocked host " + url)
    c = con()
    if not force:
        r = c.execute("select url,final_url,fetched_at,status,sha256,text from captures where url=? and status=200 order by id desc limit 1", (url,)).fetchone()
        if r: return dict(zip(["url","final_url","fetched_at","status","sha256","text"], r))
    w = _last.get(host, 0) + gap - time.time()
    if w > 0: time.sleep(w)
    err = None
    try:
        resp = S.get(url, timeout=(10, 60)); _last[host] = time.time()
        body, status, final = resp.content, resp.status_code, resp.url
    except Exception as e:
        _last[host] = time.time(); body, status, final, err = b"", 0, url, repr(e)[:300]
    if CHAL.search(body[:200000]): err = "bot-challenge"
    sha = hashlib.sha256(body).hexdigest()
    txt = to_text(body) if body else ""
    t = datetime.now(timezone.utc).isoformat(timespec="seconds")
    c.execute("insert into captures(url,final_url,fetched_at,status,sha256,text,raw,error) values(?,?,?,?,?,?,?,?)", (url, final, t, status, sha, txt, zlib.compress(body), err))
    c.commit()
    return {"url": url, "final_url": final, "fetched_at": t, "status": status, "sha256": sha, "text": txt, "error": err}

def ctx(text, pat, w=300):
    out = []
    for m in re.finditer(pat, text):
        out.append(text[max(0, m.start()-w): m.end()+w])
    return out

if __name__ == "__main__":
    r = fetch(sys.argv[1], force="-f" in sys.argv)
    print(r["status"], r["sha256"], r.get("error"), len(r["text"]))
    for p in sys.argv[2:]:
        if p != "-f":
            for x in ctx(r["text"], p): print("...", x, "...")
