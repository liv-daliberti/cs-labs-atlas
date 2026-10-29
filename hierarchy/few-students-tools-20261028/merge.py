"""Write the 2026-10-28 few-students / zero-paper results into the hierarchy files (backups first, merge, never overwrite)."""
import json, os, shutil
H = "/n/fs/resemble/cs-atlas/work/hierarchy"
LOG = f"{H}/logs"
def backup(path, tag):
    if os.path.exists(path):
        dst = f"{LOG}/{tag}.before-few-students-20261028.json"
        if not os.path.exists(dst): shutil.copy2(path, dst)
        print("backup", dst)

MW = "https://sites.google.com/view/manxi-wu/home"
WB = "https://web.archive.org/web/{}id_/{}"
manxi = {"pi": "Manxi Wu", "note": "Advisees list on her homepage (live 2026-10-28; Wayback 2024-04 to 2026-08). Only UC Berkeley advisees are recorded; the Cornell ORIE PhD advisees on the same list (Haripriya Pulyassary, Zhanhao Zhang, Ruifan Yang) date from her 2022-2024 Cornell appointment and are not Berkeley lab members. The 2024-04-23 capture lists Cornell advisees only; Kaiqi Jiang first appears 2025-03-19, Wolin Jiang 2025-08-07.",
 "students": [
  {"name": "Kaiqi Jiang", "role": "phd", "years": [2025, 2026], "url": MW, "sha256": "b77462728ced746f2d6560e8e001fa5560661c2213b01cbb96627c7318ff0581",
   "quote": "Advisees : Kaiqi Jiang (UC Berkeley Transportation, PhD student)", "note": "homepage advisee list, live 2026-10-28",
   "evidence": [{"capture_url": WB.format("20250319233944", MW), "sha256": "34d6cf3857b7ff9a98d39387b2fcc44168edb3404180b47b52fd7b00f8306f25", "quote": "Advisees : Kaiqi Jiang (UC Berkeley Transportation, PhD student)", "year": 2025}]},
  {"name": "Wolin Jiang", "role": "masters", "years": [2025, 2026], "url": MW, "sha256": "b77462728ced746f2d6560e8e001fa5560661c2213b01cbb96627c7318ff0581",
   "quote": "Wolin Jiang (UC Berkeley, Systems Engineering, MS student)", "note": "homepage advisee list, live 2026-10-28",
   "evidence": [{"capture_url": WB.format("20250807052148", MW), "sha256": "293aef9a3392ab381c96b9bf2c0403f1a678100de1a3e5db592a830848e06e54", "quote": "Kaiqi Jiang (UC Berkeley Transportation, PhD student) Wolin Jiang (UC Berkeley, Systems Engineering, MS student)", "year": 2025}]},
 ]}
OA = "https://oatutor.io/"
oa_ev = [{"capture_url": WB.format("20241205072700", OA), "sha256": "c804f8345d7b3a9a7f2d877852f691a3cf4dd48fdbd129111a05968f0dc4abdd", "year": 2024},
         {"capture_url": WB.format("20250620110542", OA), "sha256": "3c2ea15f9816d203c4183fd17567fd57b0b708badf306368f86952dc6ebef4a2", "year": 2025}]
def oat(name, role, title):
    qq = f"OATutor is developed by the Computational Approaches to Human Learning (CAHL) Research Lab at UC Berkeley's School of Education. Led by Professor Zach Pardos ... {name} {title}"
    return {"name": name, "role": role, "years": [2024, 2025, 2026], "url": OA, "sha256": "c24f3073dbc8b888fe069982408f7dd583c31b92f69e39837e70f352159498d6",
            "quote": qq, "note": f"CAHL lab team list on oatutor.io ('{title}'), live 2026-10-28; identical list in Wayback captures 2024-12-05 and 2025-06-20",
            "evidence": [dict(e, quote=f"Meet Our Team ... CAHL ... {name} {title}") for e in oa_ev]}
pardos = {"pi": "Zachary Pardos", "note": "Members from the CAHL lab's 'Meet Our Team' list on oatutor.io (OATutor is the lab's project; page names the CAHL lab led by Pardos). Natalie Chan ('UI/UX Designer') is staff and not recorded. No other lab roster found: cahl.berkeley.edu refuses connections and has no Wayback captures, cahlr.github.io is 404, zachpardos.com redirects to his BSE profile, his BSE/GSE profiles (live, Wayback 2016-2025) and CV (bse.berkeley.edu/sites/default/files/general/pardos_cv_0.pdf) name no advisees; eScholarship is off limits for this sweep. Earlier (2016-2023) CAHL students are therefore not recorded.",
 "students": [oat("Ioannis Anastasopoulos", "phd", "PhD Student In Education"), oat("Yerin Kwak", "phd", "PhD Student in Education"),
              oat("Shreya Sheel", "phd", "PhD Student in Education"), oat("Shreya Bhandari", "undergraduate", "Undergraduate Student in EECS"),
              oat("Xiaowen Yu", "undergraduate", "Undergraduate Student in CS"), oat("Anirudh Pai", "undergraduate", "Undergraduate Student in EECS")]}
holmes = {"pi": "Ian Holmes", "note": "Holmes is still Berkeley faculty (bioeng.berkeley.edu/people/ian-holmes, live 2026-10-28: 'Office hours : Fall 2026'; '2020-present Professor, Department of Bioengineering'). The lab roster (biowiki.org/HolmesLab) is offline; its last Wayback capture (2016-02-05) shows a page last edited 2012-02-10 ('Main.HolmesLab r173 - 2012-02-10'), so its members (PhD Oscar Westesson, programmer Robert Buels) are not dated evidence for 2016-2026 and are not recorded. Found one dissertation advisee in the window via the Center for Computational Biology Designated-Emphasis alumni list.",
 "students": [
  {"name": "Jordi Silvestre-Ryan", "role": "phd", "years": [2022], "url": "https://ccb.berkeley.edu/people/alumni/de-alumni",
   "sha256": "3427bb281d57acf9677af4e480b93f3a7e369e1d29b58803b645efc6a3f87fee",
   "quote": "DE Alumni Name Degree Year Program Current Position Berkeley Advisor(s) ... Jordi Silvestre-Ryan 2022 Bioengineering Senior Scientist, Numerion Labs Ian Holmes",
   "note": "Bioengineering PhD 2022 (Computational Biology Designated Emphasis), Berkeley advisor Ian Holmes; year is the stated degree year",
   "evidence": [{"url": "https://docs.google.com/spreadsheets/d/1Eg_2jqCW_5b133AWxHkOiKt4F3LkVC9vzuaKr3gmKec/export?format=csv&gid=0",
                 "sha256": "ea76becf4b5d23529e6d1892e1a8a91cf3b0d84ee0bfd5194a996f79cfdf2be4",
                 "quote": "Jordi Silvestre-Ryan,2022,Bioengineering,\"Scientist, Atomwise\",Ian Holmes", "year": 2022,
                 "note": "full DE alumni sheet linked from the CCB page ('Click here to see the full list of DE alumni.')"}]}]}

# --- Stanford few-students evidence (new file) and Berkeley (append)
st = json.load(open("entries_stanford.json"))
for school, entries in (("stanford", st), ("berkeley", [manxi, pardos, holmes])):
    p = f"{H}/{school}/few-students-evidence.json"
    backup(p, f"{school}-few-students-evidence")
    cur = json.load(open(p)) if os.path.exists(p) else []
    have = {e["pi"] for e in cur}
    add = [e for e in entries if e["pi"] not in have]
    json.dump(cur + add, open(p, "w"), indent=1, ensure_ascii=False)
    print(school, "appended", [e["pi"] for e in add], "skipped(existing)", [e["pi"] for e in entries if e["pi"] in have])

# --- Tobagi
PROF = "https://profiles.stanford.edu/fouad-tobagi"
ev = [PROF,
      "https://web.archive.org/web/20160312110517id_/https://profiles.stanford.edu/fouad-tobagi",
      "https://web.archive.org/web/20191014140744id_/https://profiles.stanford.edu/fouad-tobagi",
      "https://web.archive.org/web/20230330093400id_/https://profiles.stanford.edu/fouad-tobagi",
      "https://web.archive.org/web/20250420174548id_/https://profiles.stanford.edu/fouad-tobagi",
      "https://api.openalex.org/works?filter=author.id:A5031990068&group_by=publication_year",
      "https://api.openalex.org/works?filter=author.id:A5031990068,from_publication_date:2016-01-01&per-page=100&select=id,display_name,publication_year,type,authorships,primary_location",
      "https://link.springer.com/article/10.1007/s12243-018-0651-6"]
detail = [
 {"url": PROF, "sha256": "35ce54d623967815b6326ade60e7c166c8d014c9118e707ca201e4ba9c096be4", "quote": "Fouad Tobagi Professor of Electrical Engineering ... Academic Appointments Professor, Electrical Engineering ... 2026-27 Courses Internet Switching and Routing Protocols EE 384A (Win) Introduction to Computer Networks EE 284 (Aut)", "observed": "2026-10-28"},
 {"url": PROF, "sha256": "35ce54d623967815b6326ade60e7c166c8d014c9118e707ca201e4ba9c096be4", "quote": "Stanford Advisees Doctoral Dissertation Reader (AC) Jasmin Falconer Master's Program Advisor Annie Peng, Yongjiang Wu, Nika Zahedi", "observed": "2026-10-28"},
 {"url": ev[1], "sha256": "99805520160e19f3eb5f60a458d8d4d8704ef27b6e7b05b0cddc9bb1d2c4910c", "quote": "Fouad Tobagi Professor of Electrical Engineering and, by courtesy, of Computer Science", "observed": "20160312"},
 {"url": ev[2], "sha256": "2181aa0cbe68e7e5378b5a6021e3075b1daeb8ad1095e2ca68b8d27f3c811019", "quote": "Stanford Advisees Master's Program Advisor Rob Jones, Saelig Khattar, Ryan Stocking Doctoral (Program) Sid Assawaworrarit, Nandita Bhaskhar", "observed": "20191014"},
 {"url": ev[3], "sha256": "be8103ac5661b70bdb2d5665196fb8367b16ddacf9b2a387a8dd6f9d2d480452", "quote": "Stanford Advisees Master's Program Advisor Audrey Lee, Alex Lin Doctoral (Program) Nandita Bhaskhar", "observed": "20230330"},
 {"url": ev[4], "sha256": "f76d1f1b8423efc1bab582d9d385024a7650c5d4f8478e7a8294e11518517df6", "quote": "Stanford Advisees Doctoral Dissertation Reader (AC) Jasmin Falconer Master's Program Advisor Sylvia Chin, Longling Geng, Fan Nie, Haoming Zou", "observed": "20250420"},
 {"url": ev[5], "sha256": "8c1e48cf0257b6415aac8873a3fe626caef880c1a50808b42adf64398004fd9a", "quote": "group_by publication_year: ... 2009: 2, 2010: 2, 2018: 1 (no other year >= 2011)", "observed": "2026-10-28"},
 {"url": ev[6], "sha256": "c4db10e056730276e3253916825a0d72e2b99074c6fd3f491b5f4907b80637b2", "quote": "count 1: 2018 'Cloud edge computing in the IoT' (Annals of Telecommunications), Ilhem Fajjari, Fouad A. Tobagi, Yutaka Takahashi; Tobagi institution Stanford University", "observed": "2026-10-28"},
 {"url": ev[7], "sha256": "3deee3c062b59296679eadf4ca0838fb8fbd688ca0f5cf3fda81bc34775e7c21", "quote": "Cloud edge computing in the IoT Editorial Published: 03 August 2018 ... The focus of this special issue is on the Internet of Things (IoT)", "observed": "2026-10-28"},
]
reason = ("Not emeritus: Stanford Profiles still lists 'Professor of Electrical Engineering' (live 2026-10-28; 'and, by courtesy, of Computer Science' in 2016, dropped by 2019) with 2026-27 courses. "
          "But he is not a PI in 2016-2026: in all 43 distinct Wayback captures of his profile (2015-2026) and the live page there is no Doctoral Dissertation Advisor/Co-Advisor (AC) or Postdoctoral Faculty Sponsor entry; "
          "the only roles are Doctoral (Program) (program advising: Sid Assawaworrarit 2019-2021, Nandita Bhaskhar 2019-2023), Master's Program Advisor, and Doctoral Dissertation Reader (AC) Jasmin Falconer (2025-2026). "
          "The piBasis quote 'Doctoral (Program) Nandita Bhaskhar' is program advising, not dissertation advising (her dissertation advisor in students.json is Daniel Rubin). "
          "OpenAlex A5031990068 (212 works, Stanford) has no work 2011-2017 or 2019-2026; the single 2016-2026 hit is a 2018 guest Editorial for an Annals of Telecommunications special issue, not research output. "
          "Zero lab papers is right; the lab should be dropped from the census for the window.")
p = f"{H}/zero-paper-review.json"; backup(p, "zero-paper-review")
z = json.load(open(p)); z.setdefault("stanford", {})
if "Fouad A. Tobagi" in z["stanford"]:
    print("zero-paper-review already has Tobagi; left untouched:", z["stanford"]["Fouad A. Tobagi"])
else:
    z["stanford"]["Fouad A. Tobagi"] = {"verdict": "zero_is_right", "reason": reason, "evidence": ev, "evidence_detail": detail, "reviewed": "2026-10-28"}
    json.dump(z, open(p, "w"), indent=1, ensure_ascii=False); print("zero-paper-review: added Tobagi")
p = f"{H}/stanford/tobagi-review.json"; backup(p, "stanford-tobagi-review")
tr = json.load(open(p)) if os.path.exists(p) else []
if not any(e.get("pi") == "Fouad A. Tobagi" for e in tr):
    tr.append({"pi": "Fouad A. Tobagi", "verdict": "not_pi_in_window", "reason": reason, "evidence": ev, "evidence_detail": detail,
               "students_json_note": "students.json attaches Nandita Bhaskhar and Sid Assawaworrarit to this lab from 'Doctoral (Program)' listings only (role recorded as phd); neither is a dissertation advisee.",
               "reviewed": "2026-10-28"})
    json.dump(tr, open(p, "w"), indent=1, ensure_ascii=False); print("tobagi-review written")
