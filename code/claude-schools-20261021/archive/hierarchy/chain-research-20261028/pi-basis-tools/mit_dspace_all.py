"""For each MIT input person: DSpace@MIT discover query on dc.contributor.advisor, keep doctoral theses whose advisor
string names the person; emit advisee records with a verbatim quote from the captured JSON text. -> mit_dspace_hits.json"""
import json, re, sqlite3, zlib, sys
from cap import fetch, DB
from dspace import q
PEOPLE = {
 "Dirk Englund": ("englund", ["dirk"], r"Englund"),
 "Jing Kong": ("kong", ["jing"], r"Jing Kong|Kong, Jing"),
 "Yury Polyanskiy": ("polyanskiy", ["yury"], r"Polyanskiy"),
 "Sangeeta Bhatia": ("bhatia", ["sangeeta"], r"Sangeeta"),
 "YuFeng (Kevin) Chen": ("chen", ["yufeng"], r"Yu[Ff]eng"),
 "William D. Oliver": ("oliver", ["william", "will"], r"(William|Will)( D\.)? Oliver|Oliver, (William|Will)"),
 "Rajeev Ram": ("ram", ["rajeev"], r"Rajeev"),
 "Luca Daniel": ("daniel", ["luca"], r"Luca Daniel|Daniel, Luca"),
 "Munther Dahleh": ("dahleh", ["munther"], r"Dahleh"),
 "Jeffrey Shapiro": ("shapiro", ["jeffrey"], r"Jeffrey H\.? Shapiro|Shapiro, Jeffrey|Jeffrey Shapiro"),
 "Elfar Adalsteinsson": ("adalsteinsson", ["elfar"], r"Adalsteinsson"),
 "Thomas Heldt": ("heldt", ["thomas"], r"Heldt"),
 "Lizhong Zheng": ("zheng", ["lizhong"], r"Lizhong"),
 "George Verghese": ("verghese", ["george"], r"Verghese"),
 "Vincent Chan": ("chan", ["vincent"], r"Vincent W\.? ?S\.? Chan|Chan, Vincent|Vincent Chan"),
 "Dennis Freeman": ("freeman", ["dennis"], r"Dennis M\.? Freeman|Freeman, Dennis|Dennis Freeman"),
 "Alexandre Megretski": ("megretski", ["alexandre", "alexander"], r"Megretski"),
 "Priya Donti": ("donti", ["priya"], r"Donti"),
 "Jae Lim": ("lim", ["jae"], r"Jae S\.? Lim|Lim, Jae|Jae Lim"),
}
out = {}
only = sys.argv[1:]
for pi, (last, firsts, pat) in PEOPLE.items():
    if only and pi not in only: continue
    u = q(last, firsts)
    r = fetch(u, gap=8)
    raw = zlib.decompress(sqlite3.connect(DB).execute("select raw from captures where sha256=? order by id desc limit 1", (r["sha256"],)).fetchone()[0])
    d = json.loads(raw); text = r["text"]
    sr = d["_embedded"]["searchResult"]
    recs = []
    for o in sr["_embedded"]["objects"]:
        m = o["_embedded"]["indexableObject"]["metadata"]
        g = lambda k: [x["value"] for x in m.get(k, [])]
        adv = g("dc.contributor.advisor"); auth = g("dc.contributor.author")
        if not any(re.search(pat, a) for a in adv): continue
        deg = " ".join(g("dc.description.degree") + g("dc.description") + g("dc.type") + g("thesis.degree.level") + g("thesis.degree.name"))
        doctoral = bool(re.search(r"Ph\.? ?D|Sc\.? ?D|Doctoral|Doctor of", deg))
        a0, au0 = adv[0], auth[0] if auth else ""
        # verbatim quote: from the advisor value through the author value in the captured text
        i = text.find(json.dumps(a0)[1:-1]); quote = None
        while i >= 0:
            j = text.find(json.dumps(au0)[1:-1], i)
            if 0 <= j - i < 400: quote = text[max(0, i - 40): j + len(json.dumps(au0)) - 2 + 1]; break
            i = text.find(json.dumps(a0)[1:-1], i + 1)
        recs.append({"author": au0, "advisor": adv, "issued": g("dc.date.issued"), "degree": deg[:200], "doctoral": doctoral,
                     "uri": g("dc.identifier.uri"), "dept": g("dc.contributor.department"), "title": g("dc.title"), "quote": quote})
    out[pi] = {"url": u, "sha256": r["sha256"], "fetched_at": r["fetched_at"], "total": sr["page"]["totalElements"], "records": recs}
    print(pi, sr["page"]["totalElements"], len(recs), sum(x["doctoral"] for x in recs), flush=True)
prev = {}
try: prev = json.load(open("mit_dspace_hits.json"))
except Exception: pass
prev.update(out)
json.dump(prev, open("mit_dspace_hits.json", "w"), indent=1)
