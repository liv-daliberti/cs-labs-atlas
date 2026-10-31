"""OpenAlex author lookup (key read from ~/.config/cs-atlas/openalex.env, never printed or stored; stored URLs omit it)."""
import hashlib, json, os, re, sys, time, zlib, requests
from datetime import datetime, timezone
from cap import con, UA
INST = {"princeton": "I20089843", "stanford": "I97018004", "mit": "I63966007", "cmu": "I74973139", "berkeley": "I95457486", "epfl": "I5124864"}
def _key():
    for l in open(os.path.expanduser("~/.config/cs-atlas/openalex.env")):
        m = re.match(r"\s*(?:export\s+)?\w*KEY\w*\s*=\s*['\"]?([^'\"\s]+)", l, re.I)
        if m: return m.group(1)
KEY = _key()
def get(path, **params):
    url = "https://api.openalex.org/" + path + ("?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else "")
    c = con()
    r = c.execute("select text from captures where url=? and status=200 order by id desc limit 1", (url,)).fetchone()
    if r: return json.loads(r[0])
    time.sleep(0.25)
    p = dict(params); p["api_key"] = KEY
    for i in range(4):
        try:
            resp = requests.get("https://api.openalex.org/" + path, params=p, headers={"User-Agent": UA}, timeout=60); break
        except requests.RequestException:
            time.sleep(5 * (i + 1))
    else:
        return {}
    body = resp.content
    c.execute("insert into captures(url,final_url,fetched_at,status,sha256,text,raw,error) values(?,?,?,?,?,?,?,?)",
              (url, url, datetime.now(timezone.utc).isoformat(timespec="seconds"), resp.status_code, hashlib.sha256(body).hexdigest(), body.decode("utf-8", "replace"), zlib.compress(body), None))
    c.commit()
    return resp.json()
def authors(name, school=None):
    params = {"search": name, "per-page": "8", "select": "id,display_name,works_count,last_known_institutions,topics,affiliations"}
    if school: params["filter"] = f"affiliations.institution.id:{INST[school]}"
    return get("authors", **params).get("results", [])
def summary(name, school=None, n=4):
    out = []
    for a in authors(name, school)[:n]:
        inst = [i.get("display_name") for i in (a.get("last_known_institutions") or [])][:2]
        aff = [(x["institution"]["display_name"], min(x["years"]), max(x["years"])) for x in (a.get("affiliations") or []) if x.get("years")][:4]
        tops = [t["display_name"] for t in (a.get("topics") or [])[:5]]
        out.append(f'{a["id"].split("/")[-1]} {a["display_name"]} w={a["works_count"]} last={inst} aff={aff}\n      topics={tops}')
    return out
if __name__ == "__main__":
    school = sys.argv[1]
    for nm in sys.argv[2:]:
        print("##", nm)
        for l in summary(nm, school): print("   ", l)
