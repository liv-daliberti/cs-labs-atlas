"""Princeton few-students decisions (13 PIs), 2026-10-22. Built by build.py princeton; every row is resolved against
hierarchy/princeton/few-students-captures.sqlite by fsev (exact-substring quote that contains every name token).

Sources: DataSpace OAI-PMH (doctoral-dissertations community, master's community, department senior-thesis
collections; contributor.advisor), lab/group pages and their Wayback captures, ECE profile 'Advisee(s)' lists (several
Wayback captures), CS 'Researchers' and graduate-student rosters (adviser fields), and the PI's CV.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fsev import S as _S, oai_students  # noqa: E402

SCH = "princeton"
D = {}


def S(name, role, years, src, **kw):
    return _S(SCH, name, role, years, src, **kw)


# DataSpace sets
DOCS = "com_88435_dsp01td96k251d"      # Princeton University Doctoral Dissertations, 2011-2025 (all departments)
MASTERS = "com_88435_dsp01kh04ds925"   # Princeton University Master's Theses, 2022-2024
ORFE_SR = "col_88435_dsp011r66j119j"   # ORFE senior theses 2000-2024
ECE_SR = "col_88435_dsp0100000007x"    # ECE senior theses 1932-2024
CS_SR = "col_88435_dsp01mp48sc83w"     # CS senior theses 1987-2024
MAE_SR = "col_88435_dsp01t722h887x"    # MAE senior theses 1924-2024
MUS_SR = "col_88435_dsp019593tv19m"    # Music senior theses 1948-2024
MATH_SR = "col_88435_dsp01z029p4795"   # Mathematics senior theses 1934-2024
SR_ROLE = "undergraduate"


def oai(variants, sets_roles, exact=None, exclude=()):
    rows = oai_students(variants, sets_roles, exclude=exclude)
    if exact:  # prefix matching could catch a longer surname/given name: keep rows whose advisor list has an exact form
        rows = [r for r in rows if any(f"'{e}'" in r["note"] for e in exact)]
    return rows


def without(rows, *names):
    drop = set(names)
    return [r for r in rows if r["name"] not in drop]


# ------------------------------------------------------------------ shared pages
CS_RESEARCH = "https://www.cs.princeton.edu/people/research"          # live 2026-10-22, 'Advisers' per researcher
ECE = "https://web.archive.org/web/{}id_/https://ece.princeton.edu/people/{}"

# ============================================================================ Abhishek Bhattacharjee
D["Abhishek Bhattacharjee"] = dict(
    students=[
        S("Harsh Desai", "postdoc", [2026, 2026], CS_RESEARCH,
          quote="Harsh Desai Postdoctoral Research Associate Advisers Abhishek Bhattacharjee",
          note="Princeton CS 'Researchers' page lists him with adviser Bhattacharjee (he was the PI's Yale postdoc before)"),
    ],
    lab_note=("New lab: Bhattacharjee joined Princeton CS on 2026-07-01 from Yale (CS news 2026-09-16). At Princeton the "
              "group is so far one postdoc (Harsh Desai, moved from Yale). His Yale group page (Wayback 2026-01-13) lists "
              "PhD students Michael Wu, Nick Lindsay, Muhammed Ugur and undergraduate Rohan Thakur, but none appears on "
              "the Princeton CS graduate roster (2026-10-22), so they stay Yale students."),
    notes=("Searched: Princeton CS graduate roster and Researchers page (adviser fields), his CS profile (no homepage; "
           "~abhattac 404s), the CS news article, the Yale homepage capture, and DataSpace OAI (all doctoral "
           "dissertations, CS senior theses): DataSpace 'Bhattacharjee' advisor hits are all Amitava Bhattacharjee "
           "(PPPL plasma physics), not him. Nothing more is expected until his first Princeton students enrol."),
)

# ============================================================================ Bartolomeo Stellato
STG = "https://stella.to/group"   # stellato.io redirects here; live 2026-10-22, 'Last updated: 2026-10-21'
st_oai = oai(["Stellato, Bartolomeo"], {DOCS: "phd", ORFE_SR: SR_ROLE, ECE_SR: SR_ROLE})
D["Bartolomeo Stellato"] = dict(
    students=[
        S("Jisun Park", "postdoc", [2026, 2026], STG, start="Postdocs", end="Jisun Park Postdoctoral Research Fellow Princeton ORFE"),
        S("Daniel Deza", "phd", [2026, 2026], STG, start="Graduate students", end="Daniel Deza PhD Candidate Princeton ORFE"),
        S("Pranav Reddy", "phd", [2026, 2026], STG, start="Graduate students", end="Pranav Reddy PhD candidate Princeton ORFE"),
        S("Alec Zhu", "phd", [2026, 2026], STG, start="Graduate students", end="Alec Zhu PhD candidate Princeton ORFE"),
        S("Liubomir Maxim Baicev", "other", [2026, 2026], STG, start="Postgraduate Researchers",
          end="Liubomir Maxim Baicev Postgraduate Research Assistant Princeton ORFE", note="postgraduate research assistant"),
        S("Connor Buck", SR_ROLE, [2026, 2026], STG, start="Undergraduate students", end="Connor Buck Senior Thesis Student Princeton ORFE"),
        S("Patrick Chen", SR_ROLE, [2026, 2026], STG, start="Undergraduate students", end="Patrick Chen Senior Thesis Student Princeton ORFE"),
        S("Allison Lee", SR_ROLE, [2026, 2026], STG, start="Undergraduate students", end="Allison Lee Senior Thesis Student Princeton ORFE"),
        S("Coco Xu", SR_ROLE, [2026, 2026], STG, start="Undergraduate students", end="Coco Xu Senior Thesis Student Princeton ORFE"),
        S("Aras Selvi", "postdoc", None, STG, start="Alumni Postdocs", end="Aras Selvi (Postdoctoral Research Associate, Princeton)",
          note="alumni list gives no years"),
        S("Gabriele Dragotto", "postdoc", None, STG, start="Alumni Postdocs",
          end="Gabriele Dragotto (Postdoctoral Research Associate, Princeton)", note="alumni list gives no years"),
        S("Stefan Clarke", "phd", [2026, 2026], STG, start="Alumni", end="Stefan Clarke (PhD '26, Princeton)", note="graduation year"),
        S("Vinit Ranjan", "phd", [2026, 2026], STG, start="Alumni", end="Vinit Ranjan (PhD '26, Princeton)", note="graduation year"),
        S("Irina Wang", "phd", [2026, 2026], STG, start="Alumni", end="Irina Wang (PhD '26, Princeton)", note="graduation year"),
        S("Cole Becker", "masters", [2022, 2023], STG, start="Alumni", end="Cole Becker (BSE '22 and MSE '23, Princeton)",
          note="BSE 2022 (ECE senior thesis advised by Stellato in DataSpace) and MSE 2023"),
        S("Zach Yaninek", SR_ROLE, [2026, 2026], STG, start="Undergraduate students", after="Alumni", end="Zach Yaninek (BSE `26, Princeton)"),
        S("Allen Shen", SR_ROLE, [2026, 2026], STG, start="Undergraduate students", after="Alumni", end="Allen Shen (BSE `26, Princeton)"),
        S("Elliot Lee", SR_ROLE, [2026, 2026], STG, start="Undergraduate students", after="Alumni", end="Elliot Lee (BSE `26, Princeton)"),
        S("Shlok Patel", SR_ROLE, [2025, 2025], STG, start="Undergraduate students", after="Alumni", end="Shlok Patel (BSE `25, Princeton)"),
        S("Harit Raghunathan", SR_ROLE, [2025, 2025], STG, start="Undergraduate students", after="Alumni", end="Harit Raghunathan (BSE `25, Princeton)"),
        S("Kaan Odabas", SR_ROLE, [2024, 2024], STG, start="Undergraduate students", after="Alumni", end="Kaan Odabas (Independent Work `24, Princeton)",
          note="independent work, not a senior thesis"),
        S("Claudio Vestini", "other", None, STG, start="Undergraduate students", after="Alumni",
          end="Claudio Vestini (Visiting senior thesis student, University of Oxford)", note="visiting senior-thesis student from Oxford"),
        S("Paul Häusner", "other", [2025, 2025], STG, start="Visiting students", end="Paul Häusner (Visiting Research Student '25, Uppsala University)",
          note="visiting research student"),
    ] + without(st_oai, "Cole Becker"),
    lab_note=("Stellato's group (ORFE, since 2020). His own Group page (stella.to/group, updated 2026-10-21) lists 1 "
              "postdoc, 5 PhD students (2 co-advised with Ahmadi and already held), a postgraduate RA, 4 senior-thesis "
              "students, and alumni: 2 postdocs, 4 PhDs (Sambharya '24; Clarke, Ranjan, Wang '26), an MSE and 16 BSE "
              "advisees. DataSpace confirms the 2021-2024 senior theses and Sambharya's 2024 dissertation."),
    notes=("Sources: group page (live) and DataSpace OAI (doctoral community, ORFE and ECE senior theses, advisor "
           "'Stellato, Bartolomeo'). Left out: Luca Mingardi (MIT Master of Business Analytics, not Princeton) and the "
           "research software engineer. Held students Yanjun Liu and Yixuan Hua are on the group page too."),
)

# ============================================================================ Brenden Lake
LAKE = "https://lake-lab.github.io/people/"   # live 2026-10-22
D["Brenden Lake"] = dict(
    students=[
        S("Simon Schug", "postdoc", [2026, 2026], LAKE, start="Postdoctoral researchers",
          end="Simon Schug. Simon is a postdoctoral research associate in the Department of Computer Science at Princeton", max_span=3000),
        S("Phoebe Zeng", "phd", [2026, 2026], LAKE, start="Ph.D. students",
          end="Phoebe Zeng . I am a Ph.D. student at Princeton’s Department of Computer Science", max_span=3000,
          note="the CS roster lists Tom Griffiths as her adviser; the lab page lists her among Lake's PhD students"),
        S("Grace Hu", "phd", [2026, 2026], LAKE, start="Ph.D. students",
          end="Grace Hu . Grace is a Ph.D. student in the Department of Psychology at Princeton", max_span=3000),
        S("Siyuan Song", "phd", [2026, 2026], LAKE, start="Ph.D. students",
          end="Siyuan Song . Siyuan is a Ph.D. student in the Department of Psychology at Princeton University", max_span=3500),
        S("Akshay K. Jagadish", "other", [2026, 2026], LAKE, start="Lab affiliates",
          end="Akshay K. Jagadish Akshay is a postdoctoral research fellow at the Princeton AI Lab", max_span=3000,
          note="lab affiliate (Princeton AI Lab postdoctoral fellow), not a Lake advisee"),
        S("Gabriel Sarch", "other", [2026, 2026], LAKE, start="Lab affiliates",
          end="Gabriel Sarch. Gabriel is a Postdoctoral Research Fellow in Princeton Language and Intelligence", max_span=3000,
          note="lab affiliate (PLI postdoctoral fellow), not a Lake advisee"),
    ],
    lab_note=("New at Princeton: the Human & Machine Intelligence lab moved from NYU in 2025 (lab page: 'officially "
              "reopened at Princeton University' 7/2025), joint CS and Psychology. Princeton members on the people page: "
              "3 CS postdocs (Shin and Malik held, Schug), 3 Princeton PhD students (Zeng in CS; Hu and Song in "
              "Psychology) and 2 Princeton postdoctoral-fellow affiliates."),
    notes=("Sources: lab people page (live), CS Researchers page (Shin and Malik with adviser Lake), CS graduate roster "
           "(no student lists Lake as adviser). Left out as advised elsewhere: Solim LeGris and Wentao Wang (NYU PhD "
           "students), Guangyuan Jiang (MIT), and every alumnus listed (all from the NYU years 2017-2025). DataSpace "
           "has no Lake-advised thesis (he arrived 2025)."),
)

# ============================================================================ Christine Allen-Blanchette
cab_oai = oai(["Allen-Blanchette, Christine"], {DOCS: "phd", MAE_SR: SR_ROLE, CS_SR: SR_ROLE})
D["Christine Allen-Blanchette"] = dict(
    students=cab_oai,
    lab_note=("CAB Lab (MAE), founded 2022 (CV: 'CAB Lab Founder and Director 2022 - Present'). No public lab members "
              "page: her homepage and CV list publications and an outreach 'Mentorship' list only. DataSpace adds a "
              "co-advised MAE PhD (Justice Mason, 2025, with Naomi Leonard) and senior theses (2023)."),
    notes=("Sources: DataSpace OAI (doctoral community, MAE and CS senior theses, advisor 'Allen-Blanchette, "
           "Christine'), MAE profile (Wayback 2025-09; no advisee field), homepage cablanc.github.io and CV (2025). "
           "Not added: the CV 'Mentorship' list (URM mentoring; e.g. Promise Ekpo, whose master's thesis was advised by "
           "Jaime Fisac) and frequent co-author Yulong Yang (no source states the advising relation). The MAE graduate "
           "directory has no adviser field."),
)

# ============================================================================ Dan Trueman
tr_oai = oai(["Trueman", "TruemanMackey", "Mackey Trueman", "TruemanTymoczko"], {DOCS: "phd", MUS_SR: SR_ROLE})
D["Dan Trueman"] = dict(
    students=tr_oai,
    lab_note=("Not a lab in the lab-page sense: Trueman (Music, composition; department chair) advises composition PhD "
              "dissertations and music senior theses. DataSpace records 12 Music PhD dissertations (2016-2025) and 6 "
              "senior theses (2017-2023) with him as adviser or co-adviser."),
    notes=("Sources: DataSpace OAI (doctoral community, Music senior theses). Three dissertation records carry merged "
           "co-adviser strings ('TruemanMackey, DanielSteven', 'Mackey Trueman, Steven Dan', 'TruemanTymoczko, "
           "DanielDmitri'), i.e. Trueman with Steven Mackey or Dmitri Tymoczko as co-adviser; they are kept. His Music "
           "department profile (Wayback 2025-06) lists no students."),
)

# ============================================================================ Han Liu
hl_oai = oai(["Liu, Han"], {DOCS: "phd", ORFE_SR: SR_ROLE, CS_SR: SR_ROLE, MATH_SR: SR_ROLE}, exact=["Liu, Han"])
D["Han Liu"] = dict(
    students=hl_oai,
    lab_note=("Statistical Machine Learning Lab (ORFE); Liu left Princeton for Northwestern in 2018, so the lab is "
              "listed only 2016-2017. DataSpace records 7 PhD dissertations (2016-2020; those after 2018 finished under "
              "him after the move) and 12 senior theses (2016-2017)."),
    notes=("Sources: DataSpace OAI (doctoral community incl. PACM, ORFE/CS/Math senior theses; advisor exactly 'Liu, "
           "Han'). His lab People page (Wayback 2017-05) lists only 'Former Lab Members' (Battey, Fang, Han, Gu, Ning, "
           "Zhao) with no years or institution, mostly pre-2016 postdocs and his Johns Hopkins-era students; only "
           "Ethan Xingyuan Fang is kept, through his 2016 ORFE dissertation."),
)

# ============================================================================ Mengdi Wang
MWG = "https://web.archive.org/web/20250918051234id_/https://mwang.princeton.edu/group/"
MW23 = ECE.format("20230603021214", "mengdi-wang")
MW24 = ECE.format("20240804090013", "mengdi-wang")
MW26 = ECE.format("20261013104516", "mengdi-wang")
mw_oai = oai(["Wang, Mengdi"], {DOCS: "phd", ORFE_SR: SR_ROLE, ECE_SR: SR_ROLE, CS_SR: SR_ROLE, MATH_SR: SR_ROLE})
ADV = "Advisee(s):"
D["Mengdi Wang"] = dict(
    students=mw_oai + [
        S("Minshuo Chen", "postdoc", [2022, 2025], MWG, start="Postdoc Fellows", end="Minshuo Chen, 08/2022 – now"),
        S("Zihao Li", "phd", [2023, 2025], MWG, start="Graduate Students", end="Zihao Li, ECE"),
        S("Kaixuan Huang", "phd", [2023, 2025], MWG, start="Graduate Students", end="Kaixuan Huang, PhD Candidate, ECE"),
        S("Joseph Kim", "phd", [2023, 2025], MWG, start="Graduate Students", end="Joseph Kim, PhD Candidate, ECE"),
        S("Yu Wu", "phd", [2020, 2025], MWG, start="Graduate Students", end="Yu Wu, PhD Candidate, ECE",
          note="also on the 2021 homepage news (first paper, 2020)"),
        S("Jack Zhang", "postdoc", [2021, 2023], MWG, start="Former Lab Members", end="Jack Zhang, 08/2021-07/2023"),
        S("Huazheng Wang", "postdoc", [2021, 2022], MWG, start="Former Lab Members", end="Huazheng Wang, 09/2021- 05/2022"),
        S("Junyu Zhang", "postdoc", [2020, 2021], MWG, start="Former Lab Members", end="Junyu Zhang, 07/2020-08/2021"),
        S("Botao Hao", "postdoc", [2019, 2020], MWG, start="Former Lab Members", end="Botao Hao, 12/2019-12/2020"),
        S("Lin Yang", "postdoc", [2017, 2019], MWG, start="Former Lab Members", end="Lin Yang, 2017/09-2019-06"),
        S("Xudong Li", "postdoc", [2017, 2018], MWG, start="Former Lab Members", end="Xudong Li, 2017/09-2018/08"),
        S("Saeed Ghadimi", "postdoc", [2017, 2018], MWG, start="Former Lab Members", end="Saeed Ghadimi, 2017/09-2018/04"),
        S("Anton Stengel", SR_ROLE, [2021, 2021], MWG, start="Undergraduate Students", end="Anton Stengel"),
        S("Ruiqi Zhang", SR_ROLE, [2021, 2021], MWG, start="Undergraduate Students", end="Ruiqi Zhang(now PhD at Berkeley)"),
        S("Chenyu Wang", SR_ROLE, [2021, 2021], MWG, start="Undergraduate Students", end="Chenyu Wang (now PhD at MIT), 2021"),
        S("Zeyu Jia", SR_ROLE, [2020, 2020], MWG, start="Undergraduate Students", end="Zeyu Jia (now PhD at MIT)"),
        S("Jiaqi Zhang", SR_ROLE, [2020, 2020], MWG, start="Undergraduate Students", end="Jiaqi Zhang (now PhD at MIT), 2020"),
        S("Eliot Tan", SR_ROLE, [2016, 2016], MWG, start="Undergraduate Students", end="Eliot Tan"),
        S("Runzhe Wang", "phd", [2023, 2024], MW23, start=ADV, end="Runzhe Wang", note="ECE profile advisee (2023 and 2024 captures); ECE graduate directory"),
        S("Ming Yin", "member", [2024, 2024], MW24, start=ADV, end="Ming Yin", note="ECE profile advisee (2024 capture); role not stated"),
        S("Jiahao Qiu", "phd", [2024, 2026], MW24, start=ADV, end="Jiahao Qiu", note="ECE profile advisee 2024-2026; ECE graduate directory"),
        S("Jiacheng Guo", "phd", [2024, 2026], MW26, start=ADV, end="Jiacheng Guo", note="ECE profile advisee 2024-2026; ECE graduate directory"),
        S("Yingqing Guo", "phd", [2024, 2026], MW26, start=ADV, end="Yingqing Guo", note="ECE profile advisee 2024-2026; ECE graduate directory"),
        S("Jiawei Guo", "phd", [2026, 2026], MW26, start=ADV, end="Jiawei Guo", note="ECE graduate directory"),
        S("Shuzhen Li", "member", [2026, 2026], MW26, start=ADV, end="Shuzhen Li", note="ECE profile advisee; role not stated"),
        S("Yifu Lu", "member", [2026, 2026], MW26, start=ADV, end="Yifu Lu", note="ECE profile advisee; role not stated"),
        S("Yukang Yang", "phd", [2026, 2026], MW26, start=ADV, end="Yukang Yang", note="ECE graduate directory"),
        S("Ling Yang", "other", [2026, 2026], MW26, start=ADV, end="Ling Yang",
          note="ECE profile advisee; the ECE research-staff page lists a Ling Yang as Research Software Engineer"),
        S("Yifan Zhang", "member", [2026, 2026], MW26, start=ADV, end="Yifan Zhang", note="ECE profile advisee; role not stated"),
    ],
    lab_note=("Wang Lab (ECE/CSML; now 'Princeton AI Lab - AI for Accelerating Invention'). A large, long-running "
              "group: the 2024-2025 Group page lists postdocs, 6 PhD students, 13 former members with dates and "
              "undergraduates by year; ECE profile captures (2023, 2024, 2026) list 9-11 current advisees each; "
              "DataSpace has 10 dissertations (2019-2025) and ~20 senior theses (2016-2024)."),
    notes=("Sources: Group page (Wayback 2025-09-18; the live site is a client-rendered app whose people list is not in "
           "the HTML), ECE profile 'Advisee(s)' (Wayback 2023-06, 2024-08, 2026-10), DataSpace OAI (doctoral "
           "community; ORFE, ECE, CS, Math senior theses; advisor 'Wang, Mengdi'). Duplicates resolved to the "
           "DataSpace spelling: Group page 'Yu Zheng' = Zheng Yu (PhD 2022), 'Galen Cho' = Woon Sang Cho, 'Jack Ji' = "
           "Xiang Ji, 'Ben Wolfsen' = Ben Wolfson, 'Joy Zhou' = Joy Zou, 'Mona Ye' = Naimeng Ye. Undergraduates of 2015 "
           "and earlier are outside the window. Held Niranjani Prasad has no Wang source here."),
)

# ============================================================================ Paul Seymour
CV_PS = "https://web.math.princeton.edu/~pds/papers/vita/vita.pdf"   # dated April 7, 2026
GS = "Graduate students:"
D["Paul Seymour"] = dict(
    students=[
        S("Ringi Kim", "phd", [2011, 2016], CV_PS, start=GS, end="Ringi Kim (2011–2016)", max_span=3000,
          note="PACM dissertation 2016 in DataSpace"),
        S("Gregory Gauthier", "phd", [2012, 2017], CV_PS, start=GS, end="Gregory Gauthier (2012–2017)", max_span=3000),
        S("Sophie Spirkl", "phd", [2014, 2018], CV_PS, start=GS, end="Sophie Spirkl (2014–2018, joint with Maria Chudnovsky)", max_span=3000),
        S("Linda Cook", "phd", [2016, 2021], CV_PS, start=GS, end="Linda Cook (2016–2021)", max_span=3000),
        S("Tung Nguyen", "phd", [2020, 2025], CV_PS, start=GS, end="Tung Nguyen (2020–2025)", max_span=3000,
          note="DataSpace: 'Nguyen, Huy Tung' (2025)"),
        S("Yaqian Tang", "phd", [2022, 2023], CV_PS, start=GS, end="Yaqian Tang (2022–2023, joint with M. Chudnovsky)", max_span=3000),
        S("Alex Divoux", "phd", [2025, 2026], CV_PS, start=GS, end="Alex Divoux (2025–present)", max_span=3000),
    ] + oai(["Seymour, Paul"], {MATH_SR: SR_ROLE, CS_SR: SR_ROLE}),
    lab_note=("Not a lab-page group: Seymour (Mathematics and PACM) supervises graph-theory PhD students and senior "
              "theses. His CV (2026-04-07) lists graduate students with dates: 8 in or overlapping the window "
              "(Katherine Edwards held), the newest starting 2025."),
    notes=("Sources: CV 'Graduate students' list, DataSpace OAI (the CV's PhDs are also dissertations in the "
           "doctoral community; Math and CS senior theses, advisor 'Seymour, Paul'). Senior theses of 2014-2015 are "
           "outside the window."),
)

# ============================================================================ Pramod Viswanath
PV23 = ECE.format("20231210062659", "pramod-viswanath")
PV25 = ECE.format("20250113035345", "pramod-viswanath")
PV26 = ECE.format("20261003125229", "pramod-viswanath")
D["Pramod Viswanath"] = dict(
    students=[
        S("Kellen Cheng", "member", [2023, 2025], PV23, start=ADV, end="Kellen Cheng", note="ECE profile advisee 2023-2025; role not stated"),
        S("Ashwin Hebbar", "member", [2023, 2025], PV23, start=ADV, end="Ashwin Hebbar", note="ECE profile advisee 2023-2025; role not stated"),
        S("Viraj Nadkarni", "phd", [2023, 2026], PV23, start=ADV, end="Viraj Nadkarni", note="ECE profile advisee 2023-2026; ECE graduate directory"),
        S("Mahsa Bastankhah", "phd", [2025, 2025], PV25, start=ADV, end="Mahsa Bastankhah", note="ECE graduate directory"),
        S("Zerui Cheng", "phd", [2025, 2026], PV26, start=ADV, end="Zerui Cheng", note="ECE profile advisee 2025-2026; ECE graduate directory"),
        S("Niusha Moshrefi", "phd", [2025, 2026], PV26, start=ADV, end="Niusha Moshrefi", note="ECE profile advisee 2025-2026; ECE graduate directory"),
        S("Jianzhu Yao", "phd", [2025, 2026], PV26, start=ADV, end="Jianzhu Yao", note="ECE profile advisee 2025-2026; ECE graduate directory"),
        S("Atharv Patlan", "phd", [2026, 2026], PV26, start=ADV, end="Atharv Patlan", note="ECE graduate directory"),
        S("Esin Türeci", "member", [2026, 2026], PV26, start=ADV, end="Esin Türeci", note="ECE profile advisee; role not stated"),
        S("Peiyang Xu", "member", [2026, 2026], PV26, start=ADV, end="Peiyang Xu", note="ECE profile advisee; role not stated"),
    ],
    lab_note=("Viswanath moved from UIUC to Princeton ECE in 2021 (blockchains, deep learning for communication). His "
              "ECE profile lists 3 advisees in 2023, 7 in 2025 and 7 in 2026 (10 distinct people); no separate group "
              "page."),
    notes=("Sources: ECE profile 'Advisee(s)' (Wayback 2023-12, 2025-01, 2026-10; the 2021-2022 captures use an older "
           "template without the field), ECE graduate directory (roles). DataSpace has only the held CS senior thesis "
           "(Christopher Aubin, 2023) with advisor 'Viswanath, Pramod'; no Princeton dissertation names him yet. "
           "UIUC-era students are out."),
)

# ============================================================================ Warren Powell
C19 = "https://web.archive.org/web/20190720080334id_/https://castlelab.princeton.edu/people/"
CGS = "Current graduate students:"
pw_oai = oai(["Powell, Warren"], {DOCS: "phd", ORFE_SR: SR_ROLE, ECE_SR: SR_ROLE, CS_SR: SR_ROLE, MATH_SR: SR_ROLE})
D["Warren Powell"] = dict(
    students=pw_oai + [
        S("Lina al-Kanj", "postdoc", [2019, 2019], C19, start="Post-doctoral associates:", end="Lina al-Kanj – Ph.D. Electrical Engineering, American University of Beirut"),
        S("Kenza Hamidouche", "postdoc", [2019, 2019], C19, start="Post-doctoral associates:", end="Kenza Hamidouche – Ph.D. Electrical Engineering, Rutgers University"),
        S("Brian Cheung", "phd", [2019, 2019], C19, start=CGS, end="Brian Cheung (ORFE)", note="also 'Current graduate students' in the 2023 capture"),
        S("Yura Oh", "phd", [2019, 2019], C19, start=CGS, end="Yura Oh (EE)"),
        S("Andy Su", "phd", [2019, 2019], C19, start=CGS, end="Andy Su (EE)"),
        S("Grace Lee", "phd", [2019, 2019], C19, start=CGS, end="Grace Lee (ORFE)"),
        S("Onat Aydinhan", "phd", [2019, 2019], C19, start=CGS, end="Onat Aydinhan (ORFE)"),
        S("Tony Ye", "phd", [2019, 2019], C19, start=CGS, end="Tony Ye (ORFE)"),
    ],
    lab_note=("CASTLE Labs (ORFE); Powell retired on 2020-09-01 (emeritus). The lab page (Wayback 2019 and 2023) lists "
              "current graduate students and post-docs and 58 past students/post-docs with placement. In the window: "
              "13 PhD dissertations (2016-2023), ~40 ORFE/Math senior theses (2016-2020), 2 post-docs and 6 more "
              "graduate students current in 2019."),
    notes=("Sources: DataSpace OAI (doctoral community; ORFE, ECE, CS, Math senior theses; advisor 'Powell, Warren'), "
           "CASTLE Labs People page (Wayback 2019-07-20; 2023-03-22 checked). Its 'Past ... post-docs' list has no "
           "years and is mostly pre-2016, so only the 2019 current post-docs are added. 'Kobby Aboagye' on the lab "
           "page is DataSpace's Nana Aboagye (2018)."),
)

# ============================================================================ Yasaman Ghasempour
YG26 = ECE.format("20260728085526", "yasaman-ghasempour")
YM25 = "https://web.archive.org/web/20250805231628id_/https://ghasempour.princeton.edu/members"
YM22 = "https://web.archive.org/web/20220928191035id_/https://ghasempour.princeton.edu/members"
GP = "Graduate Students and Postdocs"
UG = "Undergraduate Students"
yg_oai = oai(["Ghasempour, Yasaman"], {DOCS: "phd", ECE_SR: SR_ROLE, CS_SR: SR_ROLE})
D["Yasaman Ghasempour"] = dict(
    students=yg_oai + [
        S("Atsutse Kludze", "phd", [2022, 2026], YM22, start=GP, end="Atsutse Kludze PhD student", note="members page 2022-2025; ECE profile 2026"),
        S("Haoze Chen", "phd", [2022, 2025], YM22, start=GP, end="Haoze Chen PhD student", note="members page 2022-2025"),
        S("Subhajit Karmakar", "postdoc", [2022, 2025], YM22, start=GP, end="Subhajit Karmakar Postdoc", note="members page 2022-2025"),
        S("Ruiyi Shen", "phd", [2022, 2026], YM22, start=GP, end="Ruiyi Shen PhD student", note="members page 2022-2025; ECE profile 2026"),
        S("Poorya Mollahosseini", "phd", [2022, 2026], YM22, start=GP, end="Poorya Mollahosseini PhD student", note="members page 2022-2025; ECE profile 2026"),
        S("Sayed Saad Afzal", "other", [2022, 2024], YM22, start=GP, end="Sayed Saad Afzal Visiting graduate student (MIT, MSR)",
          note="visiting graduate student from MIT"),
        S("Christopher Roberts", SR_ROLE, [2022, 2025], YM22, start=UG, end="Christopher Roberts ECE Department"),
        S("Heyu Guo", "phd", [2024, 2026], YM25, start=GP, end="Heyu Guo PhD student"),
        S("Yuhao Chen", "phd", [2025, 2026], YM25, start=GP, end="Yuhao Chen PhD student"),
        S("Vahid Yazdnian Kashani", "phd", [2024, 2026], YG26, start=ADV, end="Vahid Yazdnian Kashani"),
        S("Qiufeng Rui", "phd", [2025, 2026], YG26, start=ADV, end="Qiufeng (Bill) Rui", note="'Bill Rui' on the members page"),
        S("Ran Ji", "member", [2026, 2026], YG26, start=ADV, end="Ran Ji", note="ECE profile advisee; role not stated"),
        S("Chandler Stevenson", "member", [2026, 2026], YG26, start=ADV, end="Chandler Stevenson", note="ECE profile advisee; role not stated"),
        S("Andrew He", SR_ROLE, [2024, 2025], YM25, start=UG, end="Andrew He ECE Department"),
        S("Rayan Elahmadi", SR_ROLE, [2024, 2025], YM25, start=UG, end="Rayan Elahmadi ECE Department"),
        S("Callista Chong", SR_ROLE, [2025, 2025], YM25, start=UG, end="Callista Chong ECE Department"),
        S("Ashley Novat", SR_ROLE, [2025, 2025], YM25, start=UG, end="Ashley Novat ECE Department"),
        S("David Lee", SR_ROLE, [2025, 2025], YM25, start=UG, end="David Lee ECE Department"),
        S("Lara Danisman", SR_ROLE, [2025, 2025], YM25, start=UG, end="Lara Danisman ECE Department"),
        S("Chern Yang", SR_ROLE, [2025, 2025], YM25, start=UG, end="Chern Yang ECE Department"),
        S("Jerry Rivera", SR_ROLE, [2025, 2025], YM25, start=UG, end="Jerry Rivera ECE Department"),
        S("James Ding", SR_ROLE, None, YM25, start="Alumni", end="James Ding Former undergraduate student"),
        S("Sebastian Fisher", SR_ROLE, [2024, 2024], YM25, start="Alumni", end="Sebastian Fisher Former undergraduate student"),
        S("Aphia Ishimwe", SR_ROLE, [2024, 2024], YM25, start="Alumni", end="Aphia Ishimwe Former undergraduate student"),
        S("Florian Kosterhon", "other", None, YM25, start="Alumni", end="Florian Kosterhon Former visiting graduate student (TU Darmstadt)",
          note="former visiting graduate student"),
    ],
    lab_note=("Smart Wireless Agile Networks (SWAN) Lab, ECE, started Spring 2021. Members pages (Wayback 2022-2025) "
              "and the ECE profile (2026) give 11 PhD students, 1 postdoc, 2 visiting graduate students and about 16 "
              "undergraduates; DataSpace has 4 ECE senior theses (2022-2024)."),
    notes=("Sources: lab Members page (Wayback 2022-09-28, 2024-03-05, 2025-08-05; live site answers only via the "
           "archive), ECE profile 'Advisee(s)' (Wayback 2022-09, 2023-10, 2025-02, 2026-07), DataSpace OAI (ECE senior "
           "theses; no dissertation yet). Held Abhishek Kumar Singh and Sai Srikar Kasi appear on none of these pages "
           "(Kasi is not a SWAN member on any capture); they may be co-authors rather than advisees."),
)

# ============================================================================ Yuxin Chen
YC23 = ECE.format("20230204220536", "yuxin-chen")
yc_oai = oai(["Chen, Yuxin", "ChenPoor, Yuxin", "ChenFan, Yuxin"],
             {DOCS: "phd", ORFE_SR: SR_ROLE, ECE_SR: SR_ROLE, CS_SR: SR_ROLE, MATH_SR: SR_ROLE},
             exact=["Chen, Yuxin", "ChenPoor, YuxinVincent", "ChenFan, YuxinJianqing"])
D["Yuxin Chen"] = dict(
    students=yc_oai + [
        S("Eshaan Nichani", "phd", [2023, 2026], YC23, start=ADV, end="Eshaan Nichani",
          note="ECE profile advisee 2023 and 2026 (Wayback 2026-02); his group page lists him as a PhD alumnus"),
        S("Wenhao Zhan", "phd", [2023, 2026], YC23, start=ADV, end="Wenhao Zhan",
          note="ECE profile advisee 2023 and 2026 (Wayback 2026-02); his group page lists him as a PhD alumnus"),
    ],
    lab_note=("Chen was ECE assistant professor at Princeton 2017-2021 and moved to Wharton (UPenn) in 2022; he remains "
              "a Princeton ECE visiting research scholar advising two students. Princeton students: 5 PhD dissertations "
              "(2020-2025, mostly co-advised), 2 more PhD advisees, and 9 senior theses (2018-2020)."),
    notes=("Sources: DataSpace OAI (doctoral community; ORFE, ECE, CS, Math senior theses; advisor 'Chen, Yuxin' or "
           "the merged co-adviser strings 'ChenPoor, YuxinVincent' and 'ChenFan, YuxinJianqing'), ECE profile "
           "'Advisee(s)' (Wayback 2023-02 and 2026-02). His current group page (yuxinchen2020.github.io/Group.html) "
           "mixes Princeton and Penn people without saying which; its postdocs (e.g. Gen Li, Yuchen Zhou) are Penn-era "
           "and are not added."),
)

# ============================================================================ Victoria Dean
D["Victoria Dean"] = dict(
    students=[],
    lab_note=("Teaching faculty (teaching professor) in Princeton CS since summer 2025, previously at Olin College; "
              "she advises theses rather than running a research lab. One advisee so far (Anha Khan, held)."),
    notes=("Searched: CS graduate roster (only Anha Khan lists her as adviser), CS Researchers page, her homepage "
           "vdean.github.io (mentions only thesis student Anha Khan), DataSpace OAI (CS senior theses end in 2024, "
           "before she arrived; no dissertation). Nothing more exists yet; her 2025-26 senior-thesis advisees are not "
           "published anywhere we may read."),
)
