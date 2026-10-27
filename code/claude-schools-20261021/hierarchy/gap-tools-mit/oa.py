"""OpenAlex API helper (1 request/s, key from $OPENALEX_API_KEY, never logged: the stored URL omits it).
usage:
  oa.py author A123...                      -> author record summary
  oa.py works A123... [FROM_YEAR]           -> the author's works since FROM_YEAR (default 2016), title/year/affiliation
  oa.py search "Name"                       -> author search
  oa.py work W123...                        -> one work's authorships
"""
import json
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-mit")
import capstore  # noqa: E402

BASE = "https://api.openalex.org/"


def get(path, params=None):
    params = dict(params or {})
    pub = BASE + path + ("?" + urlencode(params) if params else "")
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        params["api_key"] = key
    real = BASE + path + "?" + urlencode(params)
    r = capstore.fetch(real, log_url=pub, check_robots=False)
    if r.get("status") != 200:
        raise SystemExit(f"OpenAlex {r.get('status')} {r.get('error')} for {pub}")
    return json.loads(r["content"]), r


def author(aid):
    d, r = get("authors/" + aid)
    return d, r


def works(aid, since=2016, per_page=200):
    out, cursor = [], "*"
    while cursor:
        d, r = get("works", {"filter": f"author.id:{aid},from_publication_date:{since}-01-01", "per-page": per_page, "cursor": cursor,
                             "select": "id,doi,title,publication_year,type,authorships"})
        out += d["results"]
        cursor = d["meta"].get("next_cursor") if d["results"] else None
    return out


if __name__ == "__main__":
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "author":
        d, r = author(arg)
        print(json.dumps({k: d.get(k) for k in ("id", "display_name", "orcid", "works_count", "display_name_alternatives",
                                                 "last_known_institutions", "affiliations")}, ensure_ascii=False)[:3000])
        print("sha256", r["sha256"])
    elif cmd == "works":
        since = int(sys.argv[3]) if len(sys.argv) > 3 else 2016
        for w in sorted(works(arg, since), key=lambda w: w.get("publication_year") or 0):
            me = [a for a in w.get("authorships") or [] if ((a.get("author") or {}).get("id") or "").endswith(arg)]
            insts = [i.get("display_name") for a in me for i in a.get("institutions") or []]
            raws = [z for a in me for z in a.get("raw_affiliation_strings") or []]
            print(w.get("publication_year"), w["id"][21:], (w.get("doi") or "")[16:], "|", (w.get("title") or "")[:90], "|",
                  [a.get("raw_author_name") for a in me], insts[:2], [z[:60] for z in raws[:1]])
    elif cmd == "search":
        d, r = get("authors", {"search": arg, "per-page": 25})
        for a in d["results"]:
            print(a["id"][21:], a["display_name"], a.get("orcid"), a.get("works_count"),
                  [i.get("display_name") for i in a.get("last_known_institutions") or []][:2])
    elif cmd == "work":
        d, r = get("works/" + arg)
        print(d.get("title"), d.get("publication_year"), d.get("doi"))
        for a in d.get("authorships") or []:
            print("  ", (a.get("author") or {}).get("id"), (a.get("author") or {}).get("display_name"), a.get("raw_author_name"),
                  [i.get("display_name") for i in a.get("institutions") or []], (a.get("raw_affiliation_strings") or [])[:1])
