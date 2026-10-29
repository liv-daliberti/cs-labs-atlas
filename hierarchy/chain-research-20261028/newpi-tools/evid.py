"""Evidence helper: every quote is verified verbatim against the stored capture text before it is written."""
import re, json, os
from cap import con
def _norm(s): return re.sub(r"\s+", " ", s).strip()
def ev(url, quote, observed=None, **extra):
    c = con()
    r = c.execute("select url, final_url, fetched_at, status, sha256, text from captures where url=? and status=200 order by id desc limit 1", (url,)).fetchone()
    if not r: raise KeyError("no capture " + url)
    if _norm(quote) not in _norm(r[5]): raise ValueError(f"quote not in capture {url}: {quote[:80]}")
    m = re.match(r"https://web\.archive\.org/web/(\d{14})id_/(.*)", url)
    out = {"url": m.group(2) if m else url}
    if m:
        out["capture_url"] = url
        ts = m.group(1); obs = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
    else:
        obs = r[2][:10]
    out.update({"sha256": r[4], "quote": _norm(quote), "observed": observed or obs, "fetched_at": r[2]})
    out.update(extra)
    return out
def adv(url, name, role, years, quote, **extra):
    e = ev(url, quote)
    d = {"name": name, "role": role, "years": years}
    d.update({k: e[k] for k in ["url", "capture_url", "sha256", "quote", "observed"] if k in e})
    d.update(extra)
    return d
def save(path, rows):
    tmp = path + ".tmp"
    json.dump(rows, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, path)
