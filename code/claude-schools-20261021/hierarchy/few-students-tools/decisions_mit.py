"""MIT few-students decisions (17 PIs), 2026-10-22.

Every row is built by fsev (exact substring of a stored capture in hierarchy/mit/few-students-captures.sqlite, all name
tokens in the quote). DSpace@MIT rows come from four discover searches by dc.contributor.advisor, 2016-2026
(dspace_mit.py; one of them is the sister gap investigation's stored query, copied unchanged). Students already held are
kept only when the source is new (not the DSpace record they were taken from).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fsev  # noqa: E402

M = "mit"
D = {}


def S(*a, **k):
    return fsev.S(M, *a, **k)


def dq(q):
    from urllib.parse import urlencode
    return ("https://dspace.mit.edu/server/api/discover/search/objects?" +
            urlencode({"query": q, "dsoType": "ITEM", "size": 100, "page": 0,
                       "f.dateIssued": "[2016 TO 2026],equals", "sort": "dc.date.issued,ASC"}))


DS_SISTER = dq("dc.contributor.advisor:(Terman OR Sipser OR Berners OR Goemans OR Sussman OR Cheng-Zhi OR (Huang AND Anna))")
DS_JAILLET = dq("dc.contributor.advisor:(Jaillet)")
DS_GROUP = dq("dc.contributor.advisor:(Corrigan OR Hopkins OR Huttenlocher OR Magnanti OR Micali OR Wainwright OR Bucinca OR Ghaffari)")
DS_OLD = dq("dc.contributor.advisor:(Zue OR Rosenholtz OR Peh OR Moshkovitz OR (Jack AND Dennis))")


def clean_author(au):
    s = re.sub(r"\s*\([^)]*\)", "", au)
    s = re.sub(r",\s*(Ph\.\s?D\.|S\.M\.|M\.\s?Eng\.|M\.B\.A\.|Sc\.\s?D\.)\s*(Massachusetts Institute of Technology|Sloan School of Management)?\.?\s*$",
               "", s)
    return fsev.nat(s.strip().rstrip("."))


def role_of(md):
    deg = " ".join(md.get("thesis.degree.name", []) + md.get("dc.description.degree", []) + md.get("mit.thesis.degree", []) +
                   md.get("dc.description", []))
    if re.search(r"Doctor|Ph\.\s?D|Sc\.\s?D|Doctoral", deg):
        return "phd"
    if re.search(r"Master|S\.M\.|M\.\s?Eng|M\.B\.A|M\.C\.P", deg):
        return "masters"
    if re.search(r"Bachelor|S\.B\.|B\.S\.", deg):
        return "undergraduate"
    return "other"


def ds(url, advisor_rx, held=(), skip=(), exclude=()):
    """DSpace thesis rows (clean names, roles from the degree fields); held students and names in skip are dropped."""
    meta = {}
    for it, md in fsev.dspace_items(M, url):
        au = (md.get("dc.contributor.author") or [""])[0]
        meta[fsev.nat(au)] = (au, md)
    out = []
    for r in fsev.dspace_theses(url, advisor_rx, school=M, exclude=exclude):
        au, md = meta[r["name"]]
        name = clean_author(au)
        if not fsev.has_name(r["quote"], name):
            raise ValueError(f"clean name {name} not in quote")
        k = _key(name)
        if k in {_key(h) for h in held} or k in {_key(s) for s in skip}:
            continue
        r["name"] = name
        r["role"] = role_of(md)
        out.append(r)
    return out


def _key(n):
    t = [x for x in re.split(r"[^a-z]+", fsev.fold(re.sub(r"\([^)]*\)", " ", n))) if x]
    return (t[0], t[-1]) if t else ("", "")


def held_names(pi):
    import json
    inp = json.load(open("/n/fs/resemble/cs-atlas/work/hierarchy/mit/few-students-input.json"))
    r = next(x for x in inp if x["pi"] == pi)
    return list(r["students_already"])  # compared by (first, last) token, as build.py does


# ============================================================================ Henry Corrigan-Gibbs
HCG_23 = "https://web.archive.org/web/20230313163025id_/https://people.csail.mit.edu/henrycg/"
HCG_25 = "https://web.archive.org/web/20250415163153id_/https://people.csail.mit.edu/henrycg/"
HCG_AL = "https://web.archive.org/web/20251014125502id_/https://people.csail.mit.edu/henrycg/alums/"
AL_H = "Past students and researchers"
D["Henry Corrigan-Gibbs"] = dict(
    students=[
        S("Alexandra Henzinger", "phd", [2023, 2025], HCG_23, start="students PhD students:", end="students PhD students: Alexandra Henzinger",
          note="PhD student on the MIT-hosted home page (2023-03 through 2025-12 captures)"),
        S("Ryan Lehmkuhl", "phd", [2023, 2025], HCG_23, start="students PhD students:", end="Alexandra Henzinger Ryan Lehmkuhl",
          note="PhD student on the MIT-hosted home page (2023-03 through 2025-12 captures)"),
        S("Emma Dauterman", "postdoc", [2025, 2025], HCG_25, start="students Postdocs:", end="Postdocs: Emma Dauterman",
          note="postdoc on the MIT-hosted home page (2025-04 capture); later listed under past postdocs"),
        S("Julia Len", "postdoc", [2025, 2025], HCG_25, start="students Postdocs:", end="Emma Dauterman Julia Len",
          note="postdoc on the MIT-hosted home page (2025-04 capture); later listed under past postdocs"),
        S("Kevin Liao", "other", None, HCG_AL, start=AL_H, end="ms/ph.d Kevin Liao → PhD student, Internet Policy Research Initiative",
          note="listed under 'ms/ph.d' on the MIT-hosted past-students page (degree not stated); now a PhD student at MIT IPRI"),
        S("Katarina Cheng", "undergraduate", [2023, 2025], HCG_AL, start=AL_H, end="Katarina Cheng (Fall 2023–Spring 2025)"),
        S("Megha Hegde", "undergraduate", [2025, 2025], HCG_AL, start=AL_H, end="Megha Hegde (IAP 2025)"),
        S("Togzhan Shyntay", "undergraduate", [2024, 2024], HCG_AL, start=AL_H, end="Togzhan Shyntay (Summer 2024)"),
        S("Serena Li", "undergraduate", [2024, 2024], HCG_AL, start=AL_H, end="Serena Li (Spring 2024)"),
        S("Amy He", "undergraduate", [2023, 2024], HCG_AL, start=AL_H, end="Amy He (Fall 2023, Spring 2024)"),
        S("Arvid Lunnemark", "undergraduate", [2021, 2022], HCG_AL, start=AL_H, end="Arvid Lunnemark (Fall 2021–Spring 2022)"),
        S("Rene Reyes", "undergraduate", [2021, 2021], HCG_AL, start=AL_H, end="Rene Reyes (Spring 2021)"),
    ],
    lab_note="Security/cryptography group in CSAIL (PDOS/CSS) 2020-2025. Corrigan-Gibbs moved to UC Berkeley EECS in January "
             "2026: people.csail.mit.edu/henrycg/ now redirects to people.eecs.berkeley.edu/~henrycg/. All rows here come "
             "from MIT-hosted Wayback captures (home page 2023-03, 2025-04; past-students page 2025-10).",
    notes="Sources: Wayback captures of people.csail.mit.edu/henrycg/ (students section) and /alums/; DSpace@MIT advisor "
          "search (Henzinger SM 2022, Lehmkuhl SM 2024, both already held). Excluded: Shinwon Lee (current student on the "
          "Berkeley page only), visitor Inès Bichon (Spring 2026, Berkeley).",
)

# ============================================================================ Sam Hopkins
SBH = "https://www.samuelbhopkins.com/"
SBH_H = "My group:"
D["Sam Hopkins"] = dict(
    students=[S(n, r, [2026, 2026], SBH, start=SBH_H, end=e, note="current group member on the PI's home page (2026)") for n, r, e in [
        ("Prashanti Anderson", "phd", "Prashanti Anderson (PhD)"),
        ("Amit Rajaraman", "phd", "Amit Rajaraman (PhD)"),
        ("Ittai Rubinstein", "phd", "Ittai Rubinstein (PhD)"),
        ("Inimai Subramanian", "masters", "Inimai Subramanian (MEng)"),
        ("Sofia Dominguez", "undergraduate", "Sofia Dominguez (Undergraduate)"),
        ("Amy He", "undergraduate", "Amy He (Undergraduate)"),
        ("Dheepthi Mohanraj", "undergraduate", "Dheepthi Mohanraj (Undergraduate)"),
        ("Vaidehi Srinivas", "postdoc", "Vaidehi Srinivas (Postdoc)"),
        ("Stefan Tiegel", "postdoc", "Stefan Tiegel (Postdoc)"),
    ]] + [S(n, r, None, SBH, start=SBH_H, end=e, note="alumnus on the PI's home page (years not stated)") for n, r, e in [
        ("Arushi Mantri", "masters", "Arushi Mantri (MEng)"),
        ("Chris Ge", "undergraduate", "Chris Ge (Undergraduate)"),
        ("Sidhanth Mohanty", "postdoc", "Sidhanth Mohanty (Postdoc; Now: Assistant Professor at Northwestern University)"),
    ]],
    lab_note="Theory group (algorithms, learning theory) in EECS/CSAIL since 2021; the home page lists the full group.",
    notes="Source: samuelbhopkins.com 'My group' (current and alumni). DSpace advisor search: only Amit Rajaraman (SM 2025, "
          "held); other 'Hopkins' hits are Michael J. Hopkins (Mathematics), not this PI.",
)

# ============================================================================ Anna Huang
D["Cheng Zhi (Anna) Huang"] = dict(
    students=[],
    lab_note="New lab: joined MIT in Fall 2024 (shared EECS / Music and Theater Arts appointment). No group roster is "
             "published on her home page or on the Music Technology site.",
    notes="Searched czhuang.github.io (recruiting text only, no student list), musictech.mit.edu people and her profile "
          "(program students are not attributed to faculty), and DSpace@MIT by advisor (Huang AND Anna / Cheng-Zhi): only "
          "Heidi Lei (MEng 2026-02), already held. Nothing more found; the lab is two years old and lists no members.",
)

# ============================================================================ Daniel Huttenlocher
D["Daniel Huttenlocher"] = dict(
    students=[],
    lab_note="Huttenlocher has been Dean of the MIT Schwarzman College of Computing since 2019; his page says leadership roles "
             "leave 'more limited time for research'. No group page.",
    notes="Searched web.mit.edu/hutt/www/ (no students section), the EECS profile, and DSpace@MIT by advisor: only Liang Lyu "
          "(SM 2023, co-advised with Asu Ozdaglar), already held. Nothing more found: a dean with a very small advising load.",
)

# ============================================================================ Patrick Jaillet
JR = "https://www.mit.edu/~jaillet/research/"
JH = "research group:"
J_PAGE = [
    ("Yan Dai", "phd", [2024, 2026], "Yan Dai, doctoral student, MIT ORC, 2024-now"),
    ("Rafael Hanashiro", "phd", [2021, 2026], "Rafael Hanashiro, doctoral student, MIT EECS, 2021-now"),
    ("Owen (Wenchen) Shen", "phd", [2023, 2026], "Owen (Wenchen) Shen, doctoral student, MIT ORC, 2023-now"),
    ("Ashkan Soleymani", "phd", [2021, 2026], "Ashkan Soleymani, doctoral student, MIT EECS, 2021-now"),
    ("Jack (Daihan) Zhang", "phd", [2023, 2026], "Jack (Daihan) Zhang, doctoral student, MIT ORC, 2023-now"),
    ("Junhui Zhang", "phd", [2021, 2026], "Junhui Zhang, doctoral student, MIT ORC, 2021-26"),
    ("Jerry (Zijie) Zhou", "phd", [2021, 2025], "Jerry (Zijie) Zhou, doctoral student, MIT ORC, 2021-25"),
    ("Victor Gonzalez", "phd", [2019, 2025], "Victor Gonzalez, doctoral student, MIT ORC, 2019-25"),
    ("Moise Blanchard", "phd", [2019, 2024], "Moise Blanchard, doctoral student, MIT ORC, 2019-24"),
    ("Sohil Shah", "phd", [2018, 2024], "Sohil Shah, doctoral student, MIT ORC, 2018-24"),
    ("Zhongxiang Dai", "postdoc", [2024, 2024], "Zhongxiang Dai, post-doc, MIT EECS, 2024"),
    ("Phong Nguyen", "postdoc", [2023, 2024], "Phong Nguyen, post-doc, MIT EECS, 2023-24"),
    ("Samuel Gilmour", "phd", [2018, 2023], "Samuel Gilmour, doctoral student, MIT ORC, 2018-23"),
    ("Jason Liang", "phd", [2018, 2023], "Jason Liang, doctoral student, MIT ORC, 2018-23"),
    ("Gauthier Guinet", "masters", [2020, 2022], "Gauthier Guinet, master student, MIT ORC, 2020-22"),
    ("Phil Chodrow", "phd", [2015, 2020], "Phil Chodrow, doctoral student, MIT ORC, 2015-20"),
    ("Julia Gaudio", "phd", [2016, 2020], "Julia Gaudio, doctoral student, MIT ORC, 2016-20"),
    ("Maximilien Burq", "phd", [2014, 2019], "Maximilien Burq, doctoral student, MIT ORC, 2014-19"),
    ("Sebastien Martin", "phd", [2014, 2019], "Sebastien Martin, doctoral student, MIT ORC, 2014-19"),
    ("Konstantina Mellou", "phd", [2014, 2019], "Konstantina Mellou, doctoral student, MIT ORC, 2014-19"),
    ("Virgile Galle", "phd", [2013, 2018], "Virgile Galle, doctoral student, MIT ORC, 2013-18"),
    ("Chong-Yang Goh", "phd", [2012, 2018], "Chong-Yang Goh, doctoral student, MIT ORC, 2012-18"),
    ("Arthur Flajolet", "phd", [2013, 2017], "Arthur Flajolet, doctoral student, MIT ORC, 2013-17"),
    ("Swati Gupta", "phd", [2011, 2017], "Swati Gupta, doctoral student, MIT ORC, 2011-17"),
    ("Nikita Korolko", "phd", [2012, 2017], "Nikita Korolko, doctoral student, MIT ORC, 2012-17"),
]
J_ROWS = [S(n, r, y, JR, start=JH, end=e, note="research group list on the PI's MIT research page") for n, r, y, e in J_PAGE]
# DSpace thesis advisees not on the page (LGO MBA/SM, MS in OR, co-advised theses); page entries win on duplicates
J_SKIP = ["Swati Gupta", "Nikita Korolko", "Arthur Flajolet", "Chong Yang Goh", "Virgile Galle", "Konstantina Mellou",
          "Sebastien Martin", "Maximilien Burq", "Philip Chodrow", "Julia Gaudio", "Gauthier Guinet", "Samuel Gilmour",
          "Jason Liang", "Ashkan Soleymani", "Sohil Shah", "Moise Blanchard", "Victor Gonzalez", "Zijie Zhou"]
J_DS = ds(DS_JAILLET, r"Jaillet", held=held_names("Patrick Jaillet") + ["Daw-sen Hwang"], skip=J_SKIP)
D["Patrick Jaillet"] = dict(
    students=J_ROWS + J_DS,
    lab_note="Online optimization / learning group in EECS, LIDS and the Operations Research Center. The PI's research page "
             "lists the group since 2009 with institution and years; most doctoral students are in the ORC.",
    notes="Sources: mit.edu/~jaillet/research/ (group list) and DSpace@MIT advisor search (34 theses 2016-2026, incl. LGO "
          "MBA/SM and MS in OR theses he co-supervised). Excluded by the at-MIT rule: students and postdocs listed at NUS, NTU, "
          "SMU (Singapore) and SMART postdocs (Rachael Sim, Thanh Chi Lam, Meghna Lowalekar, Anatoliy Prokhorchuk, Haibin "
          "Yu, Chunling Luo, Tien Mai, Supriyo Ghosh, Jie Chen, Sanjay Jena, Zhongxiang Dai's and Phong Nguyen's NUS PhDs); "
          "pre-2016 members (Le Nguyen Hoang 2015 and earlier). Dawsen Hwang (MIT EECS 2011-16) is the held 'Daw-sen Hwang'.",
)

# ============================================================================ Thomas Magnanti
D["Thomas Magnanti"] = dict(
    students=ds(DS_GROUP, r"Magnanti", held=held_names("Thomas Magnanti")),
    lab_note="Institute Professor (operations research); no group page. Advising in the window is thesis co-supervision.",
    notes="Searched the EECS profile (links only to an old CSAIL user page) and DSpace@MIT by advisor: Yaron Shaposhnik (PhD "
          "2016, ORC, with Retsef Levi) is new; Regina Ceballos Mondragón (SM/MBA 2024) is already held.",
)

# ============================================================================ Silvio Micali
D["Silvio Micali"] = dict(
    students=[],
    lab_note="Cryptography; Micali founded Algorand (2017). No group page (people.csail.mit.edu/silvio/ is a file index).",
    notes="Searched his CV (people.csail.mit.edu/silvio/CV.pdf, Nov 2024): the 'Doctoral Students' list ends with Zeyuan "
          "Allen-Zhu (PhD 2015), so no PhD graduates in the window. DSpace@MIT by advisor: Atalay Ileri (SM 2016) and "
          "Georgios Vlachos (MEng 2017), both already held. Nothing more found.",
)

# ============================================================================ Martin Wainwright
WG = "https://wainwrigwork.github.io/group.html"
WGH = "Current graduate students"
D["Martin Wainwright"] = dict(
    students=[
        S("Fathima Faizal", "phd", [2026, 2026], WG, start=WGH, end="Fathima Faizal (Joint with Asu Ozdaglar )",
          note="current graduate student (MIT; co-advised with Asu Ozdaglar)"),
        S("Kakei Yamamoto", "phd", [2026, 2026], WG, start=WGH, end="Kakei Yamamoto", note="current graduate student"),
        S("Flora Shi", "phd", [2026, 2026], WG, start=WGH, end="Flora Shi (Joint with Stephen Bates )",
          note="current graduate student (MIT; co-advised with Stephen Bates)"),
        S("Jia Wan", "phd", [2026, 2026], WG, start=WGH, end="Jia Wan (Joint with Devavrat Shah )",
          note="current graduate student (MIT; co-advised with Devavrat Shah)"),
        S("Yuchen Hu", "postdoc", [2026, 2026], WG, start="Current post-doctoral associates", end="Current post-doctoral associates Yuchen Hu"),
    ],
    lab_note="Statistics / ML theory group; Wainwright moved from UC Berkeley to MIT (EECS, Mathematics, LIDS, IDSS) in 2022-23. "
             "The MIT group page (wainwrigwork.github.io/group.html) lists current students and an alumni list that is almost "
             "entirely from Berkeley.",
    notes="Sources: wainwrigwork.github.io/group.html and DSpace@MIT by advisor (Eric Xia PhD 2025, Kakei Yamamoto SM 2026, "
          "both held; 'Wainwright, Haruko Murakami' hits are a different person). Excluded: Reese Pathak (co-advised with "
          "Michael Jordan, a Berkeley student) and the alumni list (no institution or years; nearly all Berkeley). "
          "'Erix Xia' on the page is a typo for the held Eric Xia.",
)

# ============================================================================ Zana Bucinca
D["Zana Bucinca"] = dict(
    students=[],
    lab_note="New lab: assistant professor at MIT (Sloan and EECS) from 2026; previously a Microsoft postdoc and Harvard PhD.",
    notes="Searched zbucinca.github.io and her CV (zbucinca_cv.pdf): its 'Students Mentored' are all Harvard students "
          "(2023-2024), so out under the at-MIT rule; the site says she is unlikely to take PhD students for Fall 2027. "
          "Nothing at MIT yet. Surprise: the held student Yi-Hao Peng is not named on any of her pages.",
)

# ============================================================================ Mohsen Ghaffari
GH = "https://people.csail.mit.edu/ghaffari/"
GC, GP, GU = "Current members:", "Past members:", "UROPs and MEng:"
D["Mohsen Ghaffari"] = dict(
    students=[
        S("Sijin Peng", "phd", [2025, 2026], GH, start=GC, end="Sijin Peng , PhD student @ MIT, 2025--"),
        S("Jaehyun Koo", "phd", [2023, 2026], GH, start=GC, end="Jaehyun Koo , PhD student @ MIT, 2023--"),
        S("Cheng Jiang", "undergraduate", [2026, 2026], GH, start=GC, end="UROP: Cheng Jiang", note="current UROP"),
        S("Christoph Grunau", "phd", [2020, 2024], GH, start=GP, end="Christoph Grunau , PhD student @ ETH and MIT, 2020—2024",
          note="PhD student at ETH and MIT (followed Ghaffari to MIT in 2022)"),
        S("Vaclav Rozhon", "phd", [2020, 2024], GH, start=GP, end="Vaclav Rozhon , PhD student @ ETH and MIT, 2020—2024",
          note="PhD student at ETH and MIT (followed Ghaffari to MIT in 2022)"),
    ] + [S(n, "other", None, GH, start=GU, end=e, after=GU, note="listed under 'UROPs and MEng' (MIT; which of the two is not stated)")
         for n, e in [("Jiangqi Dai", "UROPs and MEng: Jiangqi Dai"), ("Anton Trygub", "Anton Trygub"),
                      ("Brandon Wang", "Brandon Wang"), ("Zi Song Yeoh", "Zi Song Yeoh")]],
    lab_note="Distributed/parallel algorithms group; Ghaffari was ETH Zurich faculty 2016-2022 and joined MIT EECS in 2022.",
    notes="Source: people.csail.mit.edu/ghaffari/ 'Research Group'. Excluded under the at-MIT rule: ETH-only students and "
          "postdocs (Saeed Ilchi, Julian Portmann, Manuela Fischer, Michal Dory, Goran Zuzic, Yi-Jun Chang, Sebastian Brandt, "
          "Jara Uitto). DSpace: Jaehyun Koo SM 2025 (held).",
)

# ============================================================================ Victor Zue
D["Victor Zue"] = dict(
    students=[],
    lab_note="Professor emeritus (spoken language systems); no active group page.",
    notes="DSpace@MIT advisor search 2016-2026: only Shang-Wen Li (PhD 2017), already held. EECS profile links only to an "
          "old CSAIL user page. Nothing more found: emeritus with his last advisee graduating in 2017.",
)

# ============================================================================ Tim Berners-Lee
D["Tim Berners-Lee"] = dict(
    students=[],
    lab_note="Decentralized Information Group (DIG, CSAIL) is co-led by Berners-Lee and Lalana Kagal; Solid project.",
    notes="DSpace@MIT advisor search (Berners): only Nicola Greco (SM 2017), already held. The DIG roster "
          "(dig.csail.mit.edu/diggers, last updated 2017) lists students for the whole co-led group without naming an "
          "advisor (e.g. Alec Heifetz, SparkDP), so none can be attributed to Berners-Lee. Nothing more found.",
)

# ============================================================================ Michael Sipser
D["Michael Sipser"] = dict(
    students=[],
    lab_note="Theory of computation; Dean of Science 2014-2020. No group page.",
    notes="His CV (math.mit.edu/~sipser/CV2026.pdf, Aug 2026) lists 19 PhD students; the last is Zachary Remscrim (2016, "
          "already held). Masters and bachelors theses listed end in 2004. DSpace: only Remscrim. Nothing more in the window.",
)

# ============================================================================ Jack Dennis
D["Jack Dennis"] = dict(
    students=[],
    lab_note="Professor emeritus (dataflow / Fresh Breeze architecture); no live CSAIL person page (404) and no group page.",
    notes="DSpace@MIT advisor search (Jack AND Dennis): only Mo Zhou (SM 2016), already held. people.csail.mit.edu/dennis/ "
          "is 403 with no Wayback captures since 2016. Nothing more found.",
)

# ============================================================================ Ruth Rosenholtz
RR = "https://web.archive.org/web/20260121163631id_/https://persci.mit.edu/people/rosenholtz"
KOV = "https://web.archive.org/web/20260121164809id_/https://persci.mit.edu/people/christian/"
D["Ruth Rosenholtz"] = dict(
    students=ds(DS_OLD, r"Rosenholtz", held=held_names("Ruth Rosenholtz")) + [
        S("Vasha DuTell", "postdoc", [2024, 2026], "http://www.vashadutell.com", start="Dr. Vasha DuTell",
          end="advised by Ruth Rosenholtz and Bill Freeman",
          note="METEOR postdoctoral fellow at MIT CSAIL advised by Rosenholtz and Freeman (own site); listed as postdoc on "
               "the Perceptual Science group page in the 2024-2026 captures"),
        S("Christian Kovesdi", "other", [2024, 2026], KOV, start="Christian Kovesdi Graduate Student",
          end="visiting student researcher in Dr. Ruth Rosenholtz’s lab",
          note="visiting student researcher (ETH Zurich MSc) in Rosenholtz's lab; on the group page from 2024"),
        S("Benjamin Wolfe", "postdoc", [2018, 2021], RR, start="Students and collaborators:", end="Benjamin Wolfe",
          note="'Students and collaborators' on the PI's page; listed as postdoctoral scholar on the Perceptual Science group "
               "page in the 2018 and 2021 captures"),
    ],
    lab_note="Principal Research Scientist (BCS / CSAIL) in the Perceptual Science Group, which she co-leads with Edward "
             "Adelson; her personal page (persci.mit.edu/people/rosenholtz) lists 'Students and collaborators'.",
    notes="Sources: DSpace@MIT advisor search (Shaiyan Keshvari PhD 2016, Julia Litman-Cleper SM 2016 co-advised with Terry "
          "Knight; Michael Shumikhin MEng 2020 held), Wayback captures of her page and group member pages, Vasha DuTell's site. "
          "The shared group roster (persci.mit.edu/people) does not say which PI advises whom, so members only it lists are "
          "left out: Anne Harrington (graduate student, 2024-2026), Dian Yu, Jennifer Corbett (research scientist), and "
          "Adelson's tactile-sensing students. Derya Akkaynak-Yellin appears under 'Students and collaborators' but her "
          "relation is unclear; left out. Her CV has no advising section.",
)

# ============================================================================ Li-Shiuan Peh
D["Li-Shiuan Peh"] = dict(
    students=ds(DS_OLD, r"\bPeh\b", held=held_names("Li-Shiuan Peh")),
    lab_note="Computer architecture / networks-on-chip group; Peh left MIT for NUS in 2016, so the MIT lab only wound down "
             "2016-2019 (remaining PhD students graduating).",
    notes="DSpace@MIT advisor search: Jason Hao Gao (PhD 2016, co-advised with Anantha Chandrakasan) is new; Chia-Hsin Owen "
          "Chen (2017) and Woo Cheol Kwon (2018) are held. Her NUS page is behind a bot challenge live and in recent Wayback "
          "captures (not pursued); the 2017 capture lists appointments only. No MIT group page found in the archive.",
)

# ============================================================================ Dana Moshkovitz
DM = "https://www.cs.utexas.edu/~danama/students/index.html"
D["Dana Moshkovitz"] = dict(
    students=[
        S("Henry Yuen", "phd", [2012, 2016], DM, start="PhD students:", end="Henry Yuen , MIT, 2012-2016"),
        S("Govind Ramnarayan", "masters", [2015, 2016], DM, start="Masters students:", end="Masters students: Govind Ramnarayan , MIT 2015-2016"),
        S("Bristy Sikder", "undergraduate", [2016, 2016], DM, start="Undergraduates:", end="Bristy Sikder, MIT, Spring 2016"),
        S("Yinzhan Xu", "undergraduate", [2016, 2016], DM, start="Undergraduates:", end="Yinzhan Xu , MIT, Spring-Summer 2016"),
    ],
    lab_note="Complexity theory (PCPs); Moshkovitz moved from MIT to UT Austin in 2017. Her UT page lists everyone who worked "
             "with her, with institution and years.",
    notes="Source: cs.utexas.edu/~danama/students/ (MIT entries only; UT Austin students and postdocs excluded, and MIT "
          "students whose years end before 2016: Pasin Manurangsi, Ofer Grossman, Lena Abdalla, Kevin Tian, Kai Xiao and "
          "earlier). DSpace: Henry Yuen PhD 2016 and Govind Ramnarayan SM 2016, both held (page rows give a new source).",
)
