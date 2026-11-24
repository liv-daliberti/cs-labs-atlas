import json, re, sys
from cap import fetch
ROLES = ["Doctoral Dissertation Advisor (AC)", "Doctoral Dissertation Co-Advisor (AC)", "Postdoctoral Faculty Sponsor"]
STOP = r"(Doctoral Dissertation Reader|Doctoral Dissertation Advisor|Doctoral Dissertation Co-Advisor|Postdoctoral Faculty Sponsor|Orals Chair|Orals Evaluator|Master's Program Advisor|Doctoral \(Program\)|Undergraduate Major Advisor|Undergraduate Advisor|Postdoctoral Research Mentor|Postdoctoral|All Publications|Report Accessibility|Graduate and Fellowship Programs|Contact|Publications|Program Affiliations|Teaching|Research & Scholarship|Bio|Projects|Professional|Current Research|Courses|Advisor|Undergraduate|Master's)"
def sections(text):
    out = {}
    for role in ROLES:
        for m in re.finditer(re.escape(role), text):
            rest = text[m.end():m.end()+800]
            s = re.search(STOP, rest)
            seg = rest[:s.start()] if s else rest[:300]
            names = [n.strip() for n in seg.split(",") if n.strip()]
            out.setdefault(role, []).append((names, (role + " " + seg).strip()))
    return out
def cdx(slug):
    r = fetch(f"https://web.archive.org/cdx/search/cdx?url=profiles.stanford.edu/{slug}&output=json&from=2015&to=2026&filter=statuscode:200&collapse=timestamp:6&fl=timestamp,original", gap=3)
    try: rows = json.loads(r["text"])[1:]
    except Exception: return []
    return rows
if __name__ == "__main__":
    slug = sys.argv[1]
    rows = cdx(slug)
    byyear = {}
    for ts, orig in rows: byyear.setdefault(ts[:4], []).append(ts)
    print(slug, {y: len(v) for y, v in sorted(byyear.items())})
    for y, tss in sorted(byyear.items()):
        for ts in sorted(set([tss[0], tss[-1]])):
            u = f"https://web.archive.org/web/{ts}id_/https://profiles.stanford.edu/{slug}"
            r = fetch(u, gap=3)
            sec = sections(r["text"])
            print(ts, r["status"], r["sha256"][:12], json.dumps({k: [x[0] for x in v] for k, v in sec.items()}))
