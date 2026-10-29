from dhelp import M, PUB, WB
D = {}

# ---------------------------------------------------------------- Kun Zhang
KZ = "https://www.cmu.edu/dietrich/causality/people/index.html"
KZ22 = WB + "20220620191634id_/https://www.cmu.edu/dietrich/causality/people/"
D["Kun Zhang"] = dict(
    lab_site="https://www.cmu.edu/dietrich/causality/",
    people_page=KZ,
    people_pages=[KZ, KZ22],
    members=[
        M("Xiangchen Song", "phd", None, KZ, near="Students"),
        M("Haoyue Dai", "phd", None, KZ, near="Students"),
        M("Yewen Fan", "phd", None, KZ, near="Students"),
        M("Namrata Deka", "phd", None, KZ, near="Students"),
        M("Xinshuai Dong", "phd", None, KZ, near="Students"),
        M("Jianle Sun", "phd", None, KZ, near="Students"),
        M("Jiaqi Sun", "phd", None, KZ, near="Students"),
        M("Zichuan Liu", "phd", None, KZ, near="Students"),
        M("Xuanzhi Chen", "masters", None, KZ, near="Students"),
        M("Mantej Gill", "staff", None, KZ, near="Research Engineers"),
        M("Vishal Verma", "staff", None, KZ, near="Research Engineers"),
        M("Wai-Yin Lam", "phd", None, KZ22, near="Students"),
        M("Shuyan Wang", "phd", None, KZ22, near="Students"),
        M("Victor Akinwande", "phd", None, KZ22, near="Students"),
        M("Weiran Yao", "phd", None, KZ22, near="Students"),
        M("Shaoan Xie", "phd", None, KZ22, near="Students"),
        M("Ignavier Ng", "phd", None, KZ22, near="Students"),
        M("Zeyu Tang", "phd", None, KZ22, near="Students"),
        M("Biwei Huang", "phd", None, KZ22, near="Students"),
        M("Lingjing Kong", "phd", None, KZ22, near="Students"),
        M("Yujia Zheng", "masters", None, KZ22, near="Students"),
        M("Bryan Andrews", "postdoc", None, KZ22, near="Postdoc Researchers"),
        M("Guangyi Chen", "postdoc", None, KZ22, near="Postdoc Researchers"),
    ],
    pubs=[PUB("https://www.cmu.edu/dietrich/causality/publications/", mode="auto"),
          PUB("https://www.andrew.cmu.edu/user/kunz1/Publications.html", mode="auto")],
    notes="Group site is the CMU CLeaR-Aether Group (Dietrich philosophy). Live people page lists current students/RE plus undated alumni; Wayback 2022-06 capture of /people/ gave the 2022 roster (the only archived capture of that page; other Wayback fetches failed with connection errors). Undated alumni not seen as current in a 2016+ capture skipped: Mingming Gong, Petar Stojanov (held) = 2. Other faculty (Spirtes, Glymour, Ramsey, Biwei Huang as faculty now) are not members. Pubs: group page (2019+) and PI Publications.html (pre-2019 and recent).",
    blocked=[],
)

# ---------------------------------------------------------------- Martin Jinye Zhang
MZ = "https://mzhanglab.github.io/people"
D["Martin Jinye Zhang"] = dict(
    lab_site="https://mzhanglab.github.io/",
    people_page=MZ,
    people_pages=[MZ],
    members=[
        M("Alistair Turcan", "phd", [2024, None], MZ, near="Current Team Members"),
        M("Jiwon Lee", "phd", [2024, None], MZ, near="Current Team Members"),
        M("Anatori Prieto", "phd", [2024, None], MZ, near="Current Team Members"),
        M("Boshen Yan", "phd", [2025, None], MZ, near="Current Team Members"),
        M("Jeongho Chae", "phd", [2026, None], MZ, near="Current Team Members"),
        M("Eric Chen", "phd", [2026, None], MZ, near="Current Team Members"),
        M("Kate Zhang", "masters", [2026, None], MZ, near="Current Team Members"),
        M("Ray Liu", "staff", [2025, None], MZ, near="Current Team Members"),
        M("Nicole Sorensen", "staff", [2025, None], MZ, near="Current Team Members"),
        M("Dongbo Sun", "masters", [2023, 2025], MZ, near="Alumni"),
        M("Yuxin Lu", "masters", [2023, 2025], MZ, near="Alumni"),
        M("David Sun", "masters", [2023, 2025], MZ, near="Alumni"),
        M("Johnson Huang", "masters", [2023, 2025], MZ, near="Alumni"),
        M("Grace Du", "masters", [2023, 2025], MZ, near="Alumni"),
        M("Tanush Paradeshi", "undergraduate", [2025, 2025], MZ, near="Alumni"),
        M("Maxwell Soh", "undergraduate", [2023, 2025], MZ, near="Alumni"),
    ],
    pubs=[PUB("https://mzhanglab.github.io/publications", mode="bibtex")],
    notes="Zhang Lab @ CMU site (lab started fall 2023; PI previously Harvard HSPH, so no earlier members). People page lists current members with start dates and dated alumni, so no Wayback captures were needed. Excluded Mo Tiwari (2019-24, Stanford CS PhD, not at CMU). Role of Ray Liu/Nicole Sorensen = Research Assistant (staff). Publications page parsed with bibtex mode (29 entries). Admin Erin Driskill not a member.",
    blocked=[],
)

# ---------------------------------------------------------------- Wenting Zheng
WZ = "https://wzheng.github.io/"
D["Wenting Zheng"] = dict(
    lab_site="https://wzheng.github.io/",
    people_page=WZ,
    people_pages=[WZ],
    members=[
        M("Edward Chen", "phd", None, WZ, near="I'm very fortunate to collaborate with a talented set of students!"),
        M("Andrew Park", "phd", None, WZ, near="I'm very fortunate to collaborate with a talented set of students!"),
        M("Qi Pang", "phd", None, WZ, near="I'm very fortunate to collaborate with a talented set of students!"),
        M("Siddharth Jayashankar", "phd", None, WZ, near="Siddharth Jayashankar (Ph.D."),
        M("Anna Woo", "phd", None, WZ, near="Anna Woo (Ph.D."),
        M("Freya Liu", "phd", None, WZ, near="Freya Liu (Ph.D."),
    ],
    pubs=[PUB("https://wzheng.github.io/", mode="auto")],
    notes="PI homepage (GitHub Pages) has a Group section: current PhD students plus an undated Alum list (Zikai Zhou, Lawrence Feng, Zhengyuan Su, Simon Beyzerov, William Seo, Trevor Leong, Jinhao Zhu, Helen Mollering, Shreya Sharma = 9 undated, skipped unless seen current in a capture). Papers are on the homepage (no separate page); parse is imperfect (author text trails titles).",
    blocked=[],
)

# ---------------------------------------------------------------- Ryan Tibshirani
RT = "https://www.stat.cmu.edu/~ryantibs/group.html"
_AL = "the headings refer to their graduation dates"
D["Ryan Tibshirani"] = dict(
    lab_site="https://www.stat.cmu.edu/~ryantibs/",
    people_page=RT,
    people_pages=[RT],
    members=[
        M("Logan Brooks", "postdoc", None, RT, near="I am lucky to advise the following great students and postdocs:"),
        M("Addison Hu", "phd", None, RT, near="I am lucky to advise the following great students and postdocs:"),
        M("Pratik Patil", "phd", None, RT, near="I am lucky to advise the following great students and postdocs:"),
        M("Maria Jahja", "phd", [None, 2022], RT, near=_AL),
        M("Natalia Oliveira", "phd", [None, 2022], RT, near=_AL),
        M("Alden Green", "phd", [None, 2021], RT, near=_AL),
        M("Collin Politsch", "postdoc", [None, 2021], RT, near=_AL),
        M("Alnur Ali", "phd", [None, 2019], RT, near=_AL),
        M("Sangwon (Justin) Hyun", "phd", [None, 2019], RT, near=_AL),
        M("Veeranjaneyulu Sadhanala", "phd", [None, 2019], RT, near=_AL),
        M("Yu-Xiang Wang", "phd", [None, 2018], RT, near=_AL),
    ],
    pubs=[PUB("https://www.stat.cmu.edu/~ryantibs/research.html", mode="auto")],
    notes="Archived CMU Statistics site (PI moved to UC Berkeley 2022); live CMU group page lists 2022 members and alumni grouped by graduation year (2018-2022); all are CMU students/postdocs, none predate 2016 except none. Research page (list of papers, anchor-titled) added. Wayback captures of earlier group page versions (2016-2018) not read: archive.org in back-off.",
    blocked=[],
)

# ---------------------------------------------------------------- Haiyi Zhu
HZ = "https://haiyizhu.com/contact/"
HZ24 = WB + "20240429013521id_/https://haiyizhu.com/contact/"
D["Haiyi Zhu"] = dict(
    lab_site="https://haiyizhu.com/",
    people_page=HZ,
    people_pages=[HZ, HZ24],
    members=[
        M("Seyun Kim", "phd", None, HZ, near="Current PhD advisees"),
        M("Tzu-Sheng Kuo", "phd", None, HZ, near="Current PhD advisees"),
        M("Angela Chen", "phd", None, HZ, near="Graduated PhD advisees"),
        M("Jordan Taylor", "phd", None, HZ, near="Graduated PhD advisees"),
        M("Anna Kawakami", "phd", None, HZ, near="Graduated PhD advisees"),
        M("Anna Fang", "phd", None, HZ, near="Graduated PhD advisees"),
        M("Jane Hsieh", "phd", None, HZ, near="Graduated PhD advisees"),
        M("Zheng Yao", "phd", None, HZ, near="Graduated PhD advisees"),
    ],
    pubs=[PUB("https://haiyizhu.com/publication/", mode="auto")],
    notes="Social AI Group has no separate site; PI homepage haiyizhu.com 'Students' menu points to /contact/, which lists current PhD advisees and undated graduated advisees. The Wayback 2024-04 capture lists the same people as current advisees (plus Logan Stapleton, who is a University of Minnesota PhD student, so skipped as not placed at CMU; Hao-Fei Cheng and Bowen Yu are Minnesota-era graduates, skipped). Wayback 2017 and 2021 captures of /contact/ only had a prospective-students page (2017 was still Minnesota), so no earlier roster exists. Pubs page parses with some author-year noise; 12 of 27 entries are missing from held lab papers.",
    blocked=[],
)

# ---------------------------------------------------------------- Jun-Yan Zhu
JZ = "https://www.cs.cmu.edu/~junyanz/"
D["Jun-Yan Zhu"] = dict(
    lab_site=JZ,
    people_page=JZ,
    people_pages=[JZ, WB + "20240208063330id_/https://www.cs.cmu.edu/~junyanz/"],
    members=[
        M("Ruihan Gao", "phd", None, JZ, near="Carnegie Mellon Computer Vision Group"),
        M("Maxwell Jones", "phd", None, JZ, near="Carnegie Mellon Computer Vision Group"),
        M("Gaurav Parmar", "phd", None, JZ, near="Carnegie Mellon Computer Vision Group"),
        M("Ava Pun", "phd", None, JZ, near="Carnegie Mellon Computer Vision Group"),
        M("Chuhao Chen", "phd", None, JZ, near="Carnegie Mellon Computer Vision Group"),
        M("Eliahu Horwitz", "postdoc", None, JZ, near="Carnegie Mellon Computer Vision Group"),
        M("Sheng-Yu Wang", "phd", None, JZ, near="Former PhD students and postdocs"),
        M("Nupur Kumari", "phd", None, JZ, near="Former PhD students and postdocs"),
        M("Kangle Deng", "phd", None, JZ, near="Former PhD students and postdocs"),
        M("Sean Liu", "postdoc", None, JZ, near="Former PhD students and postdocs"),
        M("Beijia Lu", "masters", None, JZ, near="Former members and visitors"),
        M("Grace Su", "masters", None, JZ, near="Former members and visitors"),
        M("Richa Mishra", "masters", None, JZ, near="Former members and visitors"),
        M("Aniruddha Mahapatra", "masters", None, JZ, near="Former members and visitors"),
        M("Or Patashnik", "visitor", None, JZ, near="Former members and visitors"),
        M("Songwei Ge", "visitor", None, JZ, near="Former members and visitors"),
        M("Chonghyuk (Andrew) Song", "masters", None, JZ, near="Former members and visitors"),
        M("Muyang Li", "masters", None, JZ, near="Former members and visitors"),
        M("Daohan (Fred) Lu", "masters", None, JZ, near="Former members and visitors"),
        M("Mia Tang", "undergraduate", None, JZ, near="Former members and visitors"),
        M("Bingliang Zhang", "undergraduate", None, JZ, near="Former members and visitors"),
        M("Rohan Agarwal", "masters", None, JZ, near="Former members and visitors"),
        M("George Cazenavette", "masters", None, JZ, near="Former members and visitors"),
    ],
    pubs=[],
    notes="Generative Intelligence Lab section of the PI homepage lists current students/postdoc, alumni and undated former members/visitors (all from the CMU era; PI joined CMU 2018). The 2024-02 Wayback capture confirmed the earlier roster (same names, plus Aniruddha Mahapatra and Or Patashnik listed as former); the 2022 capture had no student list. Homepage Selected Publications was tried (142 entries, none with years and 0 matches: bold/anchor noise, links and course titles) so no pubs page added; the lab has no separate publications page (Google Scholar is off limits). Other faculty named as co-advisors (Deva Ramanan, Wenzhen Yuan, Srinivasa Narasimhan, Ruslan Salakhutdinov, Minchen Li) are not members.",
    blocked=[],
)

# ---------------------------------------------------------------- John D Zimmerman
ZP = "https://hcii.cmu.edu/people/john-zimmerman"
D["John D Zimmerman"] = dict(
    lab_site="http://www.cs.cmu.edu/~johnz/",
    people_page=ZP,
    people_pages=[ZP],
    members=[
        M("Michal Luria", "phd", None, ZP, near="Advisees"),
        M("Hyun Jin (Alicia) Lee", "phd", None, ZP, near="Advisees"),
        M("Ji-Youn Jung", "phd", None, ZP, near="Advisees"),
        M("Minjung Park", "phd", None, ZP, near="Advisees"),
        M("Shixian Xie", "phd", None, ZP, near="Advisees"),
    ],
    pubs=[],
    notes="The PI homepage www.cs.cmu.edu/~johnz/ is a frozen 2011-2012 page (sabbatical notice, Spring 2011 course) with no students; its pubs.html has 98 entries but none dated 2016+ (in_window=0), so it was not added. The only current roster is the Advisees list on the HCII faculty profile (5 names). Wayback captures of the HCII profile could not be read because archive.org was in shared back-off (wayback-backoff). Reenie Kirby is administrative staff, not a member.",
    blocked=[],
)

# ---------------------------------------------------------------- Yuanzhi Li
D["Yuanzhi Li"] = dict(
    lab_site=None,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="No lab site found: ml.cmu.edu profile URLs (people/faculty/yuanzhi-li, people/yuanzhi-li), www.cs.cmu.edu/~yuanzhil/, andrew.cmu.edu/user/yuanzhil/ and yuanzhi-li.github.io all 404; the ML department people index is a JavaScript shell without names; the RI search API returned nothing; a web search found only the 2019 MLD new-faculty announcement. No students list could be read, so members=[] and no publications page exists.",
    blocked=[],
)

# ---------------------------------------------------------------- Alex Smola
D["Alex Smola"] = dict(
    lab_site="http://alex.smola.org/",
    people_page="http://alex.smola.org/alumni.html",
    people_pages=["http://alex.smola.org/alumni.html"],
    members=[],
    pubs=[],
    notes="Smola was a CMU MLD professor 2013-2017 (left for Amazon in 2016). The current alex.smola.org/alumni.html lists PhD alumni, ANU/NICTA staff and Amazon/Yahoo/CMU research staff with current positions only, no CMU dates, so no one can be placed at CMU in 2016-2026 (undated, ~100 names skipped). Wayback captures of /people.html (2016-01 and 2017-05) and the 2016/2017 homepage show a stale 2013 ANU/NICTA alumni list (Le Song listed as a CMU Lane Fellow is 2013 content), with no current CMU students. The /papers.html page is 404, so no pubs page was added.",
    blocked=[],
)

# ---------------------------------------------------------------- Daniel Neill
EP = WB + "20170309203738id_/http://epdlab.heinz.cmu.edu:80/people/"
EP19 = WB + "20190212144218id_/https://epdlab.heinz.cmu.edu/people/"
D["Daniel Neill"] = dict(
    lab_site="http://epdlab.heinz.cmu.edu/",
    people_page=EP,
    people_pages=[EP, EP19],
    members=[
        M("Dylan Fitzpatrick", "phd", None, EP, near="Current lab members:"),
        M("Seth Flaxman", "postdoc", None, EP, q="Seth Flaxman Seth Flaxman grew up outside Chicago, studied computer science and mathematics at Harvard"),
        M("William Herlands", "phd", None, EP, q="William Herlands William Herlands is a joint PhD student in Machine Learning and Public Policy"),
        M("Abhinav Maurya", "phd", None, EP, q="Abhinav Maurya Abhinav Maurya is a graduate student at CMU studying Information Systems"),
        M("Edward McFowland III", "phd", None, EP, q="Edward McFowland III Ed McFowland is a Ph.D. candidate in Information Systems"),
        M("Yun Ni", "masters", None, EP, q="Yun Ni Yun Ni is a master’s student in Information Security Policy Management"),
        M("Mallory Nobles", "phd", None, EP, q="Mallory Nobles Mallory Nobles is a third year Ph.D. student in Information Systems"),
        M("Sriram Somanchi", "phd", None, EP, q="Sriram Somanchi As a doctoral student in the Heinz College, Sriram Somanchi"),
        M("Skyler Speakman", "postdoc", None, EP, q="Skyler Speakman Skyler Speakman ‘s research focuses on developing novel scan statistics"),
        M("Zhe Zhang", "phd", None, EP, q="Zhe Zhang Zhe Zhang is a third year Ph.D. student at CMU’s Heinz College"),
    ],
    pubs=[PUB(WB + "20190212144218id_/https://epdlab.heinz.cmu.edu/publications/", mode="auto")],
    notes="Event and Pattern Detection Laboratory (Heinz College); the live epdlab.heinz.cmu.edu host times out, so Wayback captures were used (2017-03 and 2019-02; the 2019 capture repeats the 2017 roster and notes Neill leaves for NYU 1 July 2018). Roster taken from 'Current lab members' of the 2017 capture; Flaxman and Speakman roles are inferred (listed as researchers, not students) so recorded as postdoc. Undated alumni (Tarun Kumar, Yandong Liu, Kai Liu, Rajas Lonkar, Kenton Murray, Amrut Nagasunder, Kan Shao, Xin Wu, Yating Zhang, Huanian Zheng = 10) skipped. Affiliated faculty (Feng Chen, David Choi, others) are not members. Neill's old CMU homepage www.cs.cmu.edu/~neill/ has no student list.",
    blocked=["http://epdlab.heinz.cmu.edu (live host connection timeout)"],
)

# ---------------------------------------------------------------- Stephen Fienberg
FP = WB + "20160121081223id_/http://www.stat.cmu.edu:80/~fienberg/"
D["Stephen Fienberg"] = dict(
    lab_site="http://www.stat.cmu.edu/~fienberg/",
    people_page=FP,
    people_pages=[FP],
    members=[],
    pubs=[],
    notes="Fienberg (died December 2016) had a personal homepage at www.stat.cmu.edu/~fienberg/ that now returns 404. The Wayback 2016-01 capture is a personal page (education, professional activities, research interests, selected books and papers) with no student, advisee or group list; it only mentions working with unnamed students and colleagues. Other captures (2017-01, 2018-01) were not read because the 2016 capture showed the page structure has no people section. No separate lab site exists, so members=[] and no usable publications page (the homepage lists books and selected papers only).",
    blocked=[],
)
