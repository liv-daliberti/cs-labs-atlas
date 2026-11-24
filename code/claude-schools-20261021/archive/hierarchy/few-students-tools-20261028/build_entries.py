"""Build few-students evidence entries (2026-10-28) from profile_scan.json (Stanford profiles + Wayback) and the
Berkeley captures in captures.sqlite. Writes entries_stanford.json / entries_berkeley.json next to this script;
merge.py appends them to the school files."""
import json, re
from cap import fetch, ctx  # noqa: F401  (kept: a project module; possibly a re-export or a side effect)

def q(s):
    return re.sub(r"\s+,", ",", re.sub(r"\s+", " ", s)).strip()

SLUG = {"Iro Armeni": "iro-armeni", "Julian Nyarko": "julian-nyarko", "Sergios Gatidis": "sergios-gatidis",
        "Candace Thille": "candace-thille", "Somil Bansal": "somil-bansal", "Tijana Zrnic": "tijana-zrnic",
        "Harikesh S. Nair": "harikesh-nair"}
ROLE = {"Doctoral Dissertation Advisor (AC)": "phd", "Doctoral Dissertation Co-Advisor (AC)": "phd", "Postdoctoral Faculty Sponsor": "postdoc"}
scan = json.load(open("profile_scan.json"))
NOTES = {
 "Iro Armeni": "Stanford Profiles advisee lists (Doctoral Dissertation Advisor (AC), Postdoctoral Faculty Sponsor), live 2026-10-28 plus every distinct Wayback capture 2022-2026; captures before 2025 list only Doctoral (Program) / Master's Program / Reader roles, which are not counted.",
 "Julian Nyarko": "Stanford Profiles Doctoral Dissertation Advisor (AC) list, live 2026-10-28 plus every distinct Wayback capture 2021-2026 (Josh Grossman appears 2023-2024 only).",
 "Sergios Gatidis": "Stanford Profiles Postdoctoral Faculty Sponsor list, live 2026-10-28 plus every distinct Wayback capture 2023-2026 (Jiaming Liu and Amin Ranem appear in captures only).",
 "Candace Thille": "Stanford Profiles: Doctoral Dissertation Advisor (AC) on the live profile 2026-10-28; Postdoctoral Faculty Sponsor in Wayback captures 2024-2026 (not on the live page). Doctoral (Program), Reader and Master's Program advisees not counted.",
 "Somil Bansal": "Stanford Profiles Doctoral Dissertation Advisor (AC) list, live 2026-10-28 plus every distinct Wayback capture 2024-2026; the first 2024 capture lists none. Reader / Orals / Master's / Doctoral (Program) lists not counted.",
 "Tijana Zrnic": "Stanford Profiles Postdoctoral Faculty Sponsor, live 2026-10-28. Captures 2023-2025 show Zrnic herself as a Postdoctoral Scholar (sponsor Emmanuel Candes), so no earlier advisees; Puheng Li (Reader) and Wenlong Ji (Orals Evaluator) not counted.",
 "Harikesh S. Nair": "No lab/member page exists: the Computational Marketing Lab page (gsb.stanford.edu/faculty-research/centers-initiatives/cml) now redirects to the GSB labs index, and his personal site (gsb-faculty.stanford.edu/harikesh-nair, Wayback 2021-2022) names no students; SearchWorks returned a bot challenge and was not pursued. Advisees come from Wayback captures of profiles.stanford.edu/harikesh-nair 2018-2026 (live 2026 profile lists none). Excluded: Doctoral Dissertation Reader (AC) Michelle Song, Charles Zhang; Doctoral (Program) Konstantin Korotkiy; 'Postdoctoral Research Mentor' Fengshi Niu (2021-2022; not a Faculty Sponsor role).",
}
out = []
for pi, slug in SLUG.items():
    caps = scan[slug]
    agg = {}
    for c in caps:
        if c["status"] != 200:
            continue
        live = c["capture_url"] is None
        y = 2026 if live else int(c["ts"][:4])
        for role, lst in c["sections"].items():
            for names, quote in lst:
                for n in names:
                    a = agg.setdefault((n, role), {"years": set(), "caps": {}, "live": None})
                    a["years"].add(y)
                    ev = {"url": f"https://profiles.stanford.edu/{slug}", "capture_url": c["capture_url"], "sha256": c["sha256"], "quote": q(quote), "observed": c["ts"][:10] if live else c["ts"]}
                    if live:
                        a["live"] = ev
                    elif y not in a["caps"]:
                        a["caps"][y] = ev
    studs = []
    for (n, role), a in sorted(agg.items(), key=lambda kv: (ROLE[kv[0][1]], min(kv[1]["years"]), kv[0][0])):
        prim = a["live"] or a["caps"][min(a["caps"])]
        s = {"name": n, "role": ROLE[role], "years": sorted(a["years"]), "url": prim["url"]}
        if prim["capture_url"]:
            s["capture_url"] = prim["capture_url"]
        s.update({"sha256": prim["sha256"], "quote": prim["quote"], "advising_role": role,
                  "note": f"Stanford Profiles '{role}' list" + (" (live profile, fetched 2026-10-28)" if a["live"] else f" (Wayback capture {prim['observed']})")})
        extra = [v for y, v in sorted(a["caps"].items()) if v is not prim]
        if extra:
            s["evidence"] = [{"capture_url": v["capture_url"], "sha256": v["sha256"], "quote": v["quote"], "year": int(v["observed"][:4])} for v in extra]
        studs.append(s)
    out.append({"pi": pi, "students": studs, "note": NOTES[pi]})
json.dump(out, open("entries_stanford.json", "w"), indent=1, ensure_ascii=False)
for e in out:
    print(e["pi"], len(e["students"]), [(s["name"], s["role"], s["years"]) for s in e["students"]])
