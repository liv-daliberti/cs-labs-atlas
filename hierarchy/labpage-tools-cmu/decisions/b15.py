from dhelp import M, PUB, WB
D = {}

K = "https://iamlab-cmu.github.io/members"
D["Oliver Kroemer"] = dict(
    lab_site="https://iamlab-cmu.github.io/",
    people_page=K,
    people_pages=[K],
    members=[
        M("Mark Lee", "phd", [None, None], K, near="PhD Students"),
        M("Yunus Seker", "phd", [None, None], K, near="PhD Students"),
        M("Zilin Si", "phd", [None, None], K, near="PhD Students"),
        M("Soumojit Bhattacharya", "masters", [None, None], K, near="Master’s Students"),
        M("Xinyi Yang", "masters", [None, None], K, near="Master’s Students"),
        M("Jacky Liang", "phd", [None, 2022], K, q="Jacky Liang Ph.D Thesis Dec. 2022"),
        M("Mohit Sharma", "phd", [None, 2024], K, q="Mohit Sharma Ph.D Thesis Feb. 2024"),
        M("Tabitha Lee", "phd", [None, 2024], K, q="Tabitha Lee Ph.D Thesis Jul. 2024"),
        M("Shivam Vats", "phd", [None, 2024], K, q="Shivam Vats Ph.D Thesis Aug. 2024"),
        M("Alex Lagrassa", "phd", [None, 2025], K, q="Alex Lagrassa Ph.D Thesis Feb. 2025"),
        M("Kevin Zhang", "phd", [None, 2025], K, q="Kevin Zhang Ph.D Thesis Feb. 2025"),
        M("Saumya Saxena", "phd", [None, 2025], K, q="Saumya Saxena Ph.D Thesis Aug. 2025"),
        M("Xinyu Wang", "masters", [None, 2025], K, q="Xinyu Wang (MSR May. 2025"),
        M("Janice Lee", "masters", [None, 2024], K, q="Janice Lee (MSR Dec. 2024"),
        M("Pat Callaghan", "masters", [None, 2024], K, q="Pat Callaghan (MSR Jan. 2024"),
        M("Sarvesh Patil", "masters", [None, 2023], K, q="Sarvesh Patil (MSR May 2023"),
        M("Xiaoyu (Erin) Zhang", "masters", [None, 2022], K, q="Xiaoyu (Erin) Zhang (MSCS May 2022"),
        M("Amrita (Ami) Sawhney", "masters", [None, 2021], K, q="Amrita (Ami) Sawhney (MSR May 2021"),
        M("Steven Lee", "masters", [None, 2021], K, q="Steven Lee (MSR May 2021"),
        M("Rohan Pandya", "masters", [None, 2021], K, q="Rohan Pandya (MRSD May 2021"),
        M("Jialiang (Alan) Zhao", "masters", [None, 2020], K, q="Jialiang (Alan) Zhao (MSR May 2020"),
        M("Wuming Zhang", "masters", [None, 2019], K, q="Wuming Zhang (MSCV Dec. 2019"),
        M("Maximilian Sieb", "masters", [None, 2019], K, q="Maximilian Sieb (MSR Aug. 2019"),
        M("Samuel Clarke", "masters", [None, 2019], K, q="Samuel Clarke (MSR May 2019"),
        M("Austin Wang", "masters", [None, 2019], K, q="Austin Wang (MSME May 2019"),
        M("Michaela Zimova", "visitor", [2025, 2025], K, q="Michaela Zimova (RISS Intern Sep. 2025"),
        M("Lawrence Feng", "undergraduate", [None, 2024], K, q="Lawrence Feng (CMU SCS Undergrad Dec 2024"),
        M("Fabian Hahn", "visitor", [2024, 2024], K, q="Fabian Hahn (RISS Intern Sep. 2024"),
        M("Jan-Malte Giannikos", "visitor", [2022, 2023], K, q="Jan-Malte Giannikos (RISS Intern Aug. 2022 and 2023"),
        M("Siddharth Girdhar", "undergraduate", [None, 2022], K, q="Siddharth Girdhar (CMU SCS Undergrad Dec. 2022"),
        M("Jeff Tan", "undergraduate", [None, 2022], K, q="Jeff Tan (CMU SCS Undergrad May 2022"),
        M("Vicky Zeng", "undergraduate", [None, 2021], K, q="Vicky Zeng (CMU SCS Undergrad Oct. 2021"),
        M("Sophia Wang", "undergraduate", [None, 2021], K, q="Sophia Wang (CMU SCS Undergrad May 2021"),
        M("Christian Eberle", "visitor", [2021, 2021], K, q="Christian Eberle (RISS Intern Aug. 2021"),
        M("Dimitria Silveria", "visitor", [2021, 2021], K, q="Dimitria Silveria (RISS Intern Aug. 2021"),
        M("Skye Thompson", "visitor", [2020, 2020], K, q="Skye Thompson (RISS Intern Aug. 2020"),
        M("Tetsuya Narita", "visitor", [2020, 2020], K, q="Tetsuya Narita (Visiting Researcher from Sony Sep. 2020"),
        M("Julian Zimmer", "visitor", [2018, 2018], K, q="Julian Zimmer (Karlsruhe Institute of Technology Exchange Program Dec. 2018"),
    ],
    pubs=[PUB("https://iamlab-cmu.github.io/publications", mode="bibtex")],
    notes="Lab site iamlab-cmu.github.io members page (live) lists current students plus a full dated alumni list; all dated entries 2019-2025 recorded (alumni entries have graduation/internship dates only; start years unknown). Wayback CDX was in shared back-off so no earlier captures read; alumni list already goes back to 2018. Publications page embeds bibtex (48 entries, mode bibtex).",
    blocked=["https://iam.ri.cmu.edu/people (DNS/connection failure)"],
)

CK = "http://www.cs.cmu.edu/~chinmayk/"
D["Chinmay Kulkarni"] = dict(
    lab_site=CK,
    people_page=CK,
    people_pages=[CK],
    members=[
        M("Yasmine Kotturi", "phd", None, CK, q="Students PhD Yasmine Kotturi"),
        M("Julia Cambre", "phd", None, CK, s="Students PhD", e="Julia Cambre"),
        M("Pranav Khadpe", "phd", None, CK, s="Students PhD", e="Pranav Khadpe"),
        M("Sayan Chaudhry", "masters", None, CK, s="Masters (thesis)", e="Sayan Chaudhry", note="master's thesis student"),
    ],
    pubs=[PUB(CK, mode="anchor")],
    notes="PI homepage has no separate people page; only a Students list in the footer (3 PhD, 1 master's thesis; page copyright 2021). No lab site beyond the homepage (HCII profile has no lab link). Wayback not read (CDX was in shared back-off). Publications are on the homepage (anchor mode, 11 missing).",
    blocked=[],
)

AP = "https://cmu-aire.github.io/pages/people.html"
D["Aviral Kumar"] = dict(
    lab_site="https://cmu-aire.github.io/",
    people_page=AP,
    people_pages=[AP],
    members=[
        M("Bhavya Agrawalla", "phd", None, AP, near="Ph.D. Students"),
        M("Zheyuan Hu", "phd", None, AP, near="Ph.D. Students"),
        M("Max Sobol Mark", "phd", None, AP, near="Ph.D. Students"),
        M("Yuxiao Qu", "phd", None, AP, near="Ph.D. Students"),
        M("Khush Agrawal", "masters", None, AP, near="Masters & Undergraduate Students", note="listed under Masters & Undergraduate"),
        M("Matthew Y.R. Yang", "masters", None, AP, near="Masters & Undergraduate Students", note="listed under Masters & Undergraduate"),
    ],
    pubs=[PUB("https://aviralkumar2907.github.io/pubs/", mode="auto")],
    notes="AIRe lab site people page (live). 'Close Collaborators' (Amrith Setlur, Fahim Tajwar CMU PhD students of other advisors; others at Berkeley/Stanford etc.) not recorded as members. Lab publications page cmu-aire.github.io/pages/publications.html is JS-loaded with no data file, not added; PI's own pubs page added (25 missing). Wayback not used (back-off; site is new, started 2024).",
    blocked=[],
)

W0 = "https://www.witechlab.com/people.html"
W18 = WB + "20180103002508id_/http://www.witechlab.com:80/people.html"
W20 = WB + "20200225033315id_/http://www.witechlab.com:80/people.html"
W22 = WB + "20220525000604id_/https://www.witechlab.com/people.html"
D["Swarun Kumar"] = dict(
    lab_site="https://www.witechlab.com/",
    people_page=W0,
    people_pages=[W0, W18, W20, W22],
    members=[
        M("Yiwen Song", "phd", [None, None], W0, near="Ph.D. Students"),
        M("Kuang Yuan", "phd", [None, None], W0, near="Ph.D. Students"),
        M("Yawen Liu", "phd", [None, None], W0, near="Ph.D. Students"),
        M("Veronica Muriga", "phd", [None, None], W0, near="Ph.D. Students", note="co-advised"),
        M("Jiangyifei Zhu", "phd", [None, None], W0, near="Ph.D. Students", note="co-advised by Justin Chan"),
        M("Freddy Liu", "phd", [None, None], W0, near="Ph.D. Students", note="co-advised by Justin Chan"),
        M("Mohamed Ibrahim Ahmed", "postdoc", [None, None], W0, near="Postdoctoral Alumni"),
        M("Diana Zhang", "phd", [None, None], W0, near="Ph.D. Alumni"),
        M("Haojian Jin", "phd", [None, None], W0, near="Ph.D. Alumni", note="co-advised by Jason Hong"),
        M("Akshay Gadre", "phd", [None, None], W0, near="Ph.D. Alumni"),
        M("Jingxian Wang", "phd", [None, 2023], W0, near="Ph.D. Alumni"),
        M("Vaibhav Singh", "phd", [None, None], W0, near="Ph.D. Alumni"),
        M("Akarsh Prabhakara", "phd", [None, None], W0, near="Ph.D. Alumni"),
        M("Junbo Zhang", "phd", [2018, None], W0, near="Ph.D. Alumni", note="summer intern 2018, then PhD"),
        M("Atul Bansal", "phd", [2017, None], W0, near="Ph.D. Alumni", note="summer intern 2017, then PhD"),
        M("Junsu Jang", "undergraduate", [None, None], W20, near="Undergraduate Students"),
        M("Zhijian Yang", "undergraduate", [2017, 2017], W20, near="Summer 2017 Interns", note="summer 2017 intern"),
        M("Nan Zhou", "undergraduate", [2017, 2017], W20, near="Summer 2017 Interns", note="summer 2017 intern"),
        M("Zijian Chen", "undergraduate", [2016, 2016], W20, near="Summer 2016 Interns", note="summer 2016 intern"),
        M("Zhenyu Song", "undergraduate", [2016, 2016], W20, near="Summer 2016 Interns", note="summer 2016 intern"),
        M("Raghav Sonavane", "undergraduate", [2016, 2016], W20, near="Summer 2016 Interns", note="summer 2016 intern"),
        M("Rajarshi Saha", "undergraduate", [2018, 2018], W20, near="Summer 2018 Interns", note="summer 2018 intern"),
        M("Ke Li", "undergraduate", [2019, 2019], W20, near="Summer 2019 Interns", note="summer 2019 intern"),
        M("Milind Srivastava", "undergraduate", [2019, 2019], W20, near="Summer 2019 Interns", note="summer 2019 intern"),
        M("Yash Jain", "undergraduate", [2019, 2019], W20, near="Summer 2019 Interns", note="summer 2019 intern"),
        M("Riddhiman Lahiri", "undergraduate", [2021, 2021], W22, near="Summer 2021 Interns", note="summer 2021 intern"),
        M("Diksha Agarwal", "undergraduate", [2021, 2021], W22, near="Summer 2021 Interns", note="summer 2021 intern"),
    ],
    pubs=[PUB("https://swarunkumar.com/publications.html", mode="auto"), PUB("http://www.witechlab.com/publications.html", mode="auto")],
    notes="Lab is the WiTech Lab (witechlab.com; PI site swarunkumar.com). Live people page + Wayback captures 2018, 2020, 2022 read. Intern roles recorded as undergraduate (intern level not stated). Graduate collaborators Rashad Eletreby (advisor Osman Yagan) and Revathy Narayanan (IIT Madras) not recorded. 2018 capture's graduate list was truncated in the compact view; 2020 capture covers the same people. wcsng.ece.cmu.edu does not resolve.",
    blocked=["https://wcsng.ece.cmu.edu/ (connection failure)"],
)

KZ = "https://csd.cmu.edu/people/faculty/william-kuszmaul"
D["William Kuszmaul"] = dict(
    lab_site=None,
    people_page=KZ,
    people_pages=[KZ],
    members=[
        M("Jingxun Liang", "phd", [None, None], KZ, near="Advisees"),
        M("Andrew Krapivin", "phd", [None, None], KZ, near="Advisees"),
    ],
    pubs=[],
    notes="No lab or personal site found (cs.cmu.edu/~kuszmaul 404, people.csail.mit.edu 403, williamkuszmaul.com no DNS, WebSearch found none). Only the CSD profile Advisees list (2 names); a web-search snippet also named Renfei Zhou but he is not on the fetched page, so not recorded. PI joined CMU in 2023 (prior MIT/Harvard). No publications page.",
    blocked=[],
)

AL = "https://www.cs.cmu.edu/~alavie/"
D["Alon Lavie"] = dict(
    lab_site=AL,
    people_page=AL,
    people_pages=[AL],
    members=[
        M("John Mendonca", "phd", [None, 2025], AL, q="My Students that have Graduated John Mendonca (PhD, 2025)"),
        M("Ricardo Rei", "phd", [None, 2024], AL, q="Ricardo Rei (PhD, 2024)", note="co-advised with Luisa Coheur"),
        M("Austin Matthews", "phd", [None, 2019], AL, q="Austin Matthews (PhD, 2019)", note="co-advised with Chris Dyer"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~alavie/publications.html", mode="auto")],
    notes="PI homepage has a 'My Students' graduated list only (no current-student section, no people page). Recorded the three with PhD years 2019-2025; entries with degrees ending 2015 or earlier (Denkowski, Clark, Heafield, Monson, Sagae, Probst, Langley, and 11 MS students) skipped as before the window. Publications page parsed with auto mode (18 missing).",
    blocked=[],
)

AN = "https://www.stat.cmu.edu/~annlee/"
D["Ann Lee"] = dict(
    lab_site=AN,
    people_page=AN,
    people_pages=[AN],
    members=[
        M("James Carzon", "phd", [None, None], AN, near="Current PhD Students"),
        M("Elizabeth Cucuzella", "phd", [None, None], AN, near="Current PhD Students"),
        M("Joshua D. Ingram", "phd", [None, None], AN, near="Current PhD Students"),
        M("Luca Masserano", "phd", [None, 2025], AN, q="Luca Masserano – PhD May 2025"),
        M("David Zhao", "phd", [None, 2023], AN, q="David Zhao – PhD May 2023"),
        M("Trey (Tria) McNeely", "phd", [None, 2022], AN, q="Trey (Tria) McNeely – PhD June 2022"),
        M("Niccolò (Nic) Dalmasso", "phd", [None, 2021], AN, q="Niccolò (Nic) Dalmasso – PhD May 2021"),
        M("Taylor Pospisil", "phd", [None, 2019], AN, q="Taylor Pospisil – PhD May 2019"),
    ],
    pubs=[PUB("https://www.stat.cmu.edu/~annlee/publication/", mode="auto")],
    notes="Group section of PI homepage lists current PhD students and main thesis advisees (graduates). Recorded graduates 2019-2025; Izbicki (2014) and earlier skipped. STAMPS center people page is center-wide (Core members), not recorded. Publications page is the Hugo /publication/ index (anchor parse, 21 missing; includes some workshop entries).",
    blocked=[],
)

LL = "https://llab-cmu.github.io/"
D["Lori Levin"] = dict(
    lab_site=LL,
    people_page=LL,
    people_pages=[LL],
    members=[
        M("Nathan Anderson", "masters", [None, None], LL, q="Nathan Anderson MLT"),
        M("Brendon Boldt", "phd", [None, None], LL, q="Brendon Boldt PhD"),
        M("Kalvin Chang", "masters", [None, None], LL, q="Kalvin Chang MLT"),
        M("Chenxuan Cui", "masters", [None, None], LL, q="Chenxuan Cui MSIIS"),
        M("Yanlin Feng", "masters", [None, None], LL, q="Yanlin Feng MLT"),
        M("Taiqi He", "masters", [None, None], LL, q="Taiqi He MLT"),
        M("Jeffrey Micher", "phd", [None, None], LL, q="Jeffrey Micher PhD"),
        M("Naoki Otani", "phd", [None, None], LL, q="Naoki Otani PhD"),
        M("Satoru Ozaki", "masters", [None, None], LL, q="Satoru Ozaki MLT"),
        M("Nate Robinson", "masters", [None, None], LL, q="Nate Robinson MLT"),
        M("Maria Ryskina", "phd", [None, None], LL, q="Maria Ryskina PhD"),
        M("Xinyu Zhang", "masters", [None, None], LL, q="Xinyu Zhang MLT"),
        M("Katherine J. Zhang", "staff", [None, None], LL, near="Staff", note="research assistant"),
        M("Yue Yin", "masters", [None, 2021], LL, q="Yue Yin MLT 2021"),
        M("Xingyuan Zhao", "masters", [None, 2021], LL, q="Xingyuan Zhao MLT 2021"),
        M("Jong Hyuk (Jay) Park", "masters", [None, 2020], LL, q="Jong Hyuk (Jay) Park MLT 2020"),
        M("Sean Zhang", "masters", [None, 2020], LL, q="Sean Zhang MSCS 2020"),
    ],
    pubs=[PUB("https://llab-cmu.github.io/publications.html", mode="auto")],
    notes="LLab (Lori Levin and David R. Mortensen) site; live page is a 2022-era snapshot (news to Feb 2022). David R. Mortensen (systems scientist, co-PI) not recorded. Names with MLT/MSIIS/MSCS degrees recorded as masters. Wayback not read for older/newer LLab captures (archive.org back-off at time of work).",
    blocked=[],
)

JL = "https://q3r.github.io/"
D["Jason Li"] = dict(
    lab_site=JL,
    people_page=JL,
    people_pages=[JL],
    members=[
        M("Henry Fleischmann", "phd", [None, None], JL, near="Current Students"),
        M("George Li", "phd", [None, None], JL, near="Current Students"),
    ],
    pubs=[],
    notes="PI homepage lists two current students; no alumni section. Publication list is JavaScript-rendered (only course links parse, mode auto gives course titles), so no publications page added. PI joined CMU around 2022-23.",
    blocked=[],
)

AR = "https://arcs-group.github.io/members"
AO = "https://jiaoyangli.me/people/"
D["Jiaoyang Li"] = dict(
    lab_site="https://arcs-group.github.io/",
    people_page=AR,
    people_pages=[AR, AO],
    members=[
        M("Eyal Weiss", "postdoc", [2026, None], AR, q="Eyal Weiss RI Postdoc, Fall 2026"),
        M("Philip Huang", "phd", [2023, None], AR, q="Philip Huang RI PhD, Fall 2023"),
        M("He (Rivers) Jiang", "phd", [2026, None], AR, q="He (Rivers) Jiang RI PhD, Fall 2026", note="MSR class 2025 first (old page)"),
        M("Kallol Saha", "phd", [2026, None], AR, q="Kallol Saha RI PhD, Fall 2026", note="MS Robotics CMU 2026"),
        M("Yorai Shaoul", "phd", [2022, None], AR, q="Yorai Shaoul RI PhD, Fall 2022"),
        M("Jingtian Yan", "phd", [2024, None], AR, q="Jingtian Yan RI PhD, Fall 2024"),
        M("Yulun Zhang", "phd", [2022, None], AR, q="Yulun Zhang RI PhD, Fall 2022"),
        M("Srikar Gouru", "masters", [None, 2027], AR, q="Srikar Gouru Master of Science in Robotics, Class 2027"),
        M("Mehul Menon", "masters", [None, 2027], AR, q="Mehul Menon Master of Science in Robotics, Class 2027"),
        M("Vaibhav Sanjay", "masters", [None, 2027], AR, q="Vaibhav Sanjay Master of Science in Robotics, Class 2027"),
        M("Rishi Veerapaneni", "phd", [2020, 2026], AR, q="Rishi Veerapaneni RI PhD, 2020-2026", note="co-advised with Maxim Likhachev"),
        M("Yimin Tang", "masters", [2022, 2023], AR, q="Yimin Tang Master of Science in Robotics, 2022-2023"),
        M("Cheng Qian", "undergraduate", [None, 2025], AO, q="Cheng Qian (CS undergraduate, Class 2025)"),
        M("Yifan Su", "undergraduate", [None, 2025], AO, q="Yifan Su (CS undergraduate, Class 2025)"),
        M("Ying Feng", "undergraduate", [2022, 2023], AO, q="Ying Feng (CS undergraduate, 2022-2023"),
        M("Adittyo Paul", "undergraduate", [2022, 2023], AO, q="Adittyo Paul (CS undergraduate, 2022-2023)"),
    ],
    pubs=[PUB("https://arcs-group.github.io/publications/", mode="bibtex"), PUB("https://jiaoyangli.me/publications/", mode="bibtex")],
    notes="ARCS Lab: active site arcs-group.github.io/members (live) plus the older jiaoyangli.me/people page (frozen Aug 2024) for 2022-2025 undergraduates and the class-of-2025 master's student He Jiang. Both pubs pages parse as bibtex (53 and 45 missing, overlapping). No Wayback used (back-off; two live pages already cover the lab's whole life since 2022).",
    blocked=[],
)

TL = WB + "20220128165059id_/https://leelab.cnbc.cmu.edu/"
D["Tai-Sing Lee"] = dict(
    lab_site="https://leelab.cnbc.cmu.edu/",
    people_page=TL,
    people_pages=[TL],
    members=[
        M("Yimeng Zhang", "phd", None, TL, q="Yimeng Zhang Ph.D. Student (CSD & CNBC)"),
        M("Ge (Summer) Huang", "phd", None, TL, q="Ge (Summer) Huang Ph.D. Student (CNBC)"),
        M("Zhihao Li", "masters", None, TL, q="Zhihao Li M.S. Student (CSD)"),
        M("Chaitanya Modak", "masters", None, TL, q="Chaitanya Modak M.S. Student (ECE)"),
        M("Allison Fisher", "undergraduate", None, TL, q="Allison Fisher B.S. Student (CSD)"),
        M("Bojian Han", "undergraduate", None, TL, q="Bojian Han B.S. Student (CSD)"),
        M("Chen Liu", "undergraduate", None, TL, q="Chen Liu B.S. Student (CSD)"),
        M("Jessica Lee", "undergraduate", None, TL, q="Jessica Lee B.S. Student (CSD)"),
    ],
    pubs=[],
    notes="Lab site is leelab.cnbc.cmu.edu (live host fails TLS; read via Wayback; PI's cnbc.cmu.edu/~tai also fails live). Team section is identical in 2018, 2020 and 2022 captures; used the 2022 one. The alumni block (postdocs, PhD/MS/undergraduate alumni, ~40 names) carries no dates and was not seen as current, so skipped (postdocs Smith, Yan, Yu, Samonds, Massot; PhDs Yu, Potetz, Stepleton, Kelly, Li; many undergraduates). Active Perception Lab at cs.cmu.edu/~yimengzh/leelab lists only the PI. Publications not added (homepage shows only featured items; Wayback site has per-paper pages).",
    blocked=["https://www.cnbc.cmu.edu/~tai/ and leelab.cnbc.cmu.edu live (SSL certificate verify failed)"],
)

D["Christopher J Langmead"] = dict(
    lab_site="https://sites.google.com/view/langmeadlab/",
    people_page="https://sites.google.com/view/langmeadlab/alumni",
    people_pages=["https://sites.google.com/view/langmeadlab/alumni"],
    members=[],
    pubs=[],
    notes="Lab site (Google Sites) has Alumni page whose 'Current Students' and 'Alumni' lists are Google Drive embeds (robots-disallowed, not fetched); home says the lab no longer recruits (PI is VP at Danaher, adjunct at CMU). Old PI homepage cs.cmu.edu/~cjl captures 2017 and 2020 list no students. AI/ML, Computational Medicine, Computational Biology, Blog pages have no student names. Publications: only a Scholar link and a short recent-papers list, nothing parseable.",
    blocked=["drive.google.com embeds for student/alumni lists (robots-disallowed)"],
)
