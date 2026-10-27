from dhelp import M, PUB, WB
D = {}

# ---- Jeff Schneider
S_LIVE = "https://www.cs.cmu.edu/~schneide/"
S17 = WB + "20170114104128id_/http://www.cs.cmu.edu:80/~schneide/"
S20 = WB + "20200129123026id_/http://www.cs.cmu.edu:80/~schneide/"
S23 = WB + "20230205182907id_/https://www.cs.cmu.edu/~schneide/"
D["Jeff Schneider"] = dict(
    lab_site=S_LIVE,
    people_page=S_LIVE,
    people_pages=[S_LIVE, S17, S20, S23],
    members=[
        M("Mineui Hong", "postdoc", [None, None], S_LIVE, near="Current Postdocs"),
        M("Xiaoyan Hu", "postdoc", None, S_LIVE, near="Current Postdocs"),
        M("Brian Yang", "phd", None, S_LIVE, near="Current PhD students"),
        M("Ben Freed", "phd", None, S_LIVE, near="Current PhD students"),
        M("Tejus Gupta", "phd", None, S_LIVE, near="Current PhD students"),
        M("Fahim Tajwar", "phd", None, S_LIVE, near="Current PhD students"),
        M("Namrata Deka", "phd", None, S_LIVE, near="Current PhD students"),
        M("Albert Xu", "phd", None, S_LIVE, near="Current PhD students"),
        M("Aravind Venugopal", "phd", None, S_LIVE, near="Current PhD students"),
        M("Grace Liu", "phd", None, S_LIVE, near="Current PhD students"),
        M("Efe Mert Karagozlu", "phd", None, S_LIVE, near="Current PhD students"),
        M("Anoushka Alavilli", "phd", None, S_LIVE, near="Current PhD students"),
        M("Selina Carter", "phd", None, S_LIVE, near="Current PhD students"),
        M("Rohit Sonder", "phd", None, S_LIVE, near="Current PhD students"),
        M("Wen-Tse Chen", "phd", None, S_LIVE, near="Current PhD students"),
        M("Vincent Lin", "masters", None, S_LIVE, near="Current MS students"),
        M("Shrinivas Ramasubramanian", "masters", None, S_LIVE, near="Current MS students"),
        M("Raymond Song", "masters", None, S_LIVE, near="Current MS students"),
        M("Yiqi Wang", "masters", None, S_LIVE, near="Current MS students"),
        M("Arsh Verma", "masters", None, S_LIVE, near="Current MS students"),
        M("Eric Zhu", "masters", None, S_LIVE, near="Current MS students"),
        M("Haoran Hao", "masters", None, S_LIVE, near="Current MS students"),
        M("Robin Sabhnani", "phd", [None, 2017], S17, near="Current PhD students", note="listed current in 2017 capture"),
        M("Yifei Ma", "phd", [None, 2017], S17, near="Current PhD students", note="listed current in 2017 capture"),
        M("Dougal Sutherland", "phd", [None, 2017], S17, near="Current PhD students", note="listed current in 2017 capture"),
        M("Xuezhi Wang", "phd", [None, 2017], S17, near="Current PhD students", note="listed current in 2017 capture"),
        M("Junier Oliva", "phd", [None, 2017], S17, near="Current PhD students", note="listed current in 2017 capture"),
        M("Kirthevasan Kandasamy", "phd", None, S17, near="Current PhD students", note="current in 2017 and 2020 captures"),
        M("Chun-Liang Li", "phd", [None, 2017], S17, near="Current PhD students", note="listed current in 2017 capture"),
        M("Sibi Venkatesan", "phd", [None, 2017], S17, near="Current PhD students", note="listed current in 2017 capture"),
        M("Ian Char", "phd", None, S20, near="Current PhD students", note="current in 2020 and 2023 captures"),
        M("Theo Gervet", "phd", None, S20, near="Current PhD students", note="listed current in 2020 capture"),
        M("Ramina Ghods", "postdoc", None, S23, near="Current Postdocs"),
        M("Viraj Mehta", "phd", None, S23, near="Current PhD students"),
        M("Conor Igoe", "phd", None, S23, near="Current PhD students"),
        M("Adam Villaflor", "phd", None, S23, near="Current PhD students"),
        M("Arundhati Bannerjee", "phd", None, S23, near="Current PhD students"),
        M("Yeeho Song", "phd", None, S23, near="Current PhD students"),
        M("Swapnil Pande", "masters", None, S23, near="Current MS students"),
        M("Zhe Huang", "masters", None, S23, near="Current MS students"),
        M("Divam Gupta", "masters", None, S23, near="Current MS students"),
        M("Nikhil Bakshi", "masters", None, S23, near="Current MS students"),
    ],
    pubs=[],
    notes="PI homepage www.cs.cmu.edu/~schneide/ lists current postdocs/PhD/MS; live plus 2017/2020/2023 Wayback captures read (no alumni list on the page). The Auton Lab people page (autonlab.org/people.html) mixes students of Dubrawski/Poczos/Schneider without advisor attribution so it was not used for members. Publications: only a Google Scholar link on the homepage (off limits) and autonlab.org/publications.html is JavaScript-loaded with no data file in the HTML, so no pubs page added. Co-faculty Dubrawski, Poczos, Moore not recorded.",
    blocked=["https://scholar.google.com/citations?user=3bSbb20AAAAJ&hl=en"],
)

# ---- Guanya Shi
GS = "https://lecar-lab.github.io/people.html"
D["Guanya Shi"] = dict(
    lab_site="https://lecar-lab.github.io/",
    people_page=GS,
    people_pages=[GS],
    members=[
        M("Xiaoxuan Ma", "postdoc", None, GS, near="Postdocs"),
        M("Eliot Xing", "phd", [2022, None], GS, near="PhD Students", note="entered Fall 2022"),
        M("Chaoyi Pan", "phd", [2023, None], GS, near="PhD Students", note="entered Fall 2023"),
        M("Zeji Yi", "phd", [2023, None], GS, near="PhD Students", note="entered Fall 2023"),
        M("Jin Cheng", "phd", [2023, None], GS, near="PhD Students", note="ETH Zurich PhD (Fall 2023) listed in the lab"),
        M("Giri Anantharaman", "phd", [2024, None], GS, near="PhD Students", note="entered Fall 2024"),
        M("Anoushka Alavilli", "phd", [2024, None], GS, near="PhD Students", note="entered Fall 2024"),
        M("Wenli Xiao", "phd", [2025, None], GS, near="PhD Students", note="MSR 2025 then RI PhD Fall 2025"),
        M("Cunxi Dai", "phd", [2025, None], GS, near="PhD Students", note="entered Fall 2025"),
        M("Alexis Hao", "phd", [2026, None], GS, near="PhD Students", note="entered Fall 2026"),
        M("Tonghe Zhang", "masters", [2025, None], GS, near="Master Students"),
        M("Lingxiao Guo", "masters", [2025, None], GS, near="Master Students"),
        M("Angchen Xie", "masters", [2025, None], GS, near="Master Students"),
        M("Yutong Wang", "masters", [2025, None], GS, near="Master Students"),
        M("Jia Xie", "masters", [2025, None], GS, near="Master Students"),
        M("Xinyao Li", "masters", [2026, None], GS, near="Master Students"),
        M("Chenyuan Hu", "masters", [2026, None], GS, near="Master Students"),
        M("Wen-Han Hsieh", "masters", [2026, None], GS, near="Master Students"),
        M("Ishayu Shikhare", "undergraduate", None, GS, near="Visitors and Undergrads"),
        M("Yi Yang", "visitor", None, GS, near="Visitors and Undergrads", note="visiting undergraduate"),
        M("Tairan He", "phd", [None, 2026], GS, near="Previous PhD students"),
        M("Xiaofeng Guo", "phd", [None, 2026], GS, near="Previous PhD students"),
        M("Haotian Lin", "masters", [None, 2026], GS, near="Previous MS students"),
        M("Chaitanya Chawla", "masters", [None, 2026], GS, near="Previous MS students"),
        M("Yuanhang Zhang", "masters", [None, 2026], GS, near="Previous MS students"),
        M("Nikhil Sobanbabu", "masters", [None, 2026], GS, near="Previous MS students"),
        M("Yogita Choudhary", "masters", [None, 2025], GS, near="Previous MS students"),
        M("Guanqi He", "masters", [None, 2025], GS, near="Previous MS students"),
        M("Dvij Kalaria", "masters", [None, 2024], GS, near="Previous MS students"),
        M("Haoru Xue", "masters", [None, 2024], GS, near="Previous MS students"),
        M("Rwik Rana", "masters", [None, 2023], GS, near="Previous MS students", note="University of Washington MS (2023) per lab page"),
        M("Dongjae Lee", "postdoc", [None, 2026], GS, near="Previous visitors and undergrads", note="visiting postdoc"),
        M("Narek Harutyunyan", "visitor", [None, 2026], GS, near="Previous visitors and undergrads", note="visiting undergrad, RISS"),
        M("Huanyu Li", "visitor", [None, 2026], GS, near="Previous visitors and undergrads", note="visiting undergrad"),
        M("Yitang Li", "visitor", [None, 2025], GS, near="Previous visitors and undergrads", note="visiting undergrad"),
        M("Haoyang Weng", "visitor", [None, 2025], GS, near="Previous visitors and undergrads", note="visiting undergrad"),
        M("Harsh Gupta", "visitor", [None, 2025], GS, near="Previous visitors and undergrads", note="visiting undergrad, RISS"),
        M("André Gomes", "visitor", [None, 2025], GS, near="Previous visitors and undergrads", note="visiting MS"),
        M("Tony Tao", "undergraduate", [None, 2024], GS, near="Previous visitors and undergrads"),
        M("Micah Reich", "undergraduate", [None, 2024], GS, near="Previous visitors and undergrads"),
        M("Shaofeng Yin", "visitor", [None, 2024], GS, near="Previous visitors and undergrads", note="visiting undergrad"),
        M("Jiawei Gao", "visitor", [None, 2024], GS, near="Previous visitors and undergrads", note="visiting undergrad"),
        M("Yichao Zhong", "visitor", [None, 2024], GS, near="Previous visitors and undergrads", note="visiting undergrad"),
        M("Chong Zhang", "visitor", [None, 2024], GS, near="Previous visitors and undergrads", note="visiting MS"),
        M("Yikai Wang", "visitor", [None, 2023], GS, near="Previous visitors and undergrads", note="visiting undergrad"),
    ],
    pubs=[],
    notes="LeCAR Lab people page read live (all sections: faculty, postdoc, PhD, MS, visitors/undergrads, previous). Years are the entry year (current) or the year they left (alumni) as the page states. Guanya Shi joined CMU RI in 2024 (from Caltech), so the 2022/2023 PhD entry years are the students' program-entry years per the page. Publications page lecar-lab.github.io/publications.html lists only a handful of selected papers and did not parse to real titles (first-sentence/TL;DR text), so not added; full list is Google Scholar (off limits). Wayback captures of the people page not needed (page covers 2023-2026 members and the lab is new).",
    blocked=["https://scholar.google.com/citations?hl=en&user=joR1Z4UAAAAJ&view_op=list_works&sortby=pubdate"],
)

# ---- Hong Shen
HSG = "https://www.andrew.cmu.edu/user/hongs/group.html"
D["Hong Shen"] = dict(
    lab_site="https://www.andrew.cmu.edu/user/hongs/",
    people_page=HSG,
    people_pages=[HSG],
    members=[
        M("Jini Kim", "phd", None, HSG, near="PhD students"),
        M("Ningjing Tang", "phd", None, HSG, near="PhD students"),
        M("Qing Xiao", "phd", None, HSG, near="PhD students"),
        M("Alice Qian", "phd", None, HSG, near="PhD students"),
        M("Chelsea Wang", "postdoc", None, HSG, near="Postdoctoral Researcher"),
    ],
    pubs=[],
    notes="CARE Lab group page (andrew.cmu.edu/user/hongs/group.html) read live: 4 PhD students and 1 postdoc, no alumni section. Wayback not read for this lab (site has no alumni list on the live page and archive.org was in back-off during the pass). Publications: homepage only links Google Scholar (off limits); research page has no paper list, so no pubs page added.",
    blocked=["https://scholar.google.com/citations?hl=en&user=iwytZ2wAAAAJ&view_op=list_works&sortby=pubdate"],
)

# ---- Elaine Shi
ES = "https://www.cs.cmu.edu/~runting/students/"
D["Elaine Shi"] = dict(
    lab_site="https://www.cs.cmu.edu/~runting/",
    people_page=ES,
    people_pages=[ES],
    members=[
        M("Andrew Krapivin", "phd", None, ES, near="Ph.D. students"),
        M("Changrui Mu", "phd", None, ES, near="Ph.D. students"),
        M("Yue Yang", "phd", None, ES, near="Ph.D. students"),
        M("Rose Silver", "phd", None, ES, near="Ph.D. students"),
        M("Tianyao Gu", "phd", None, ES, near="Ph.D. students"),
        M("Andrew Park", "phd", None, ES, near="On leave", note="on leave at MongoDB"),
        M("Afonso Tinoco", "phd", None, ES, near="On leave", note="on leave at Oblivious Labs"),
        M("Hanjun Li", "postdoc", None, ES, near="Postdocs"),
        M("Elisaweta Masserova", "postdoc", None, ES, near="Postdocs"),
        M("Mengqian Zhang", "postdoc", None, ES, near="Postdocs"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~runting/papers/", mode="auto")],
    notes="Students page www.cs.cmu.edu/~runting/students/ read live: current PhD students (5 + 2 on leave) and postdocs (3) recorded. 'Past students' list (15 PhD, 18 postdoc) carries no dates and mixes the UMD/Cornell years before Shi joined CMU, so undated past students are skipped (33).",
    blocked=[],
)

# ---- Nihar Shah
NS = "http://www.cs.cmu.edu/~nihars/"
D["Nihar Shah"] = dict(
    lab_site=NS,
    people_page=NS,
    people_pages=[NS],
    members=[
        M("Justin Payan", "postdoc", None, NS, near="GROUP"),
        M("Balint Gyevnar", "postdoc", None, NS, near="GROUP", note="joint with Atoosa Kasirzadeh"),
        M("Madeline Kitch", "phd", None, NS, near="GROUP"),
        M("Vishisht Rao", "phd", None, NS, near="GROUP"),
        M("Sanan Sharifzade", "masters", None, NS, near="GROUP"),
        M("Kerissa Duliga", "masters", None, NS, near="GROUP"),
        M("Noemi Barbagli", "undergraduate", None, NS, near="GROUP"),
        M("Yiming Shao", "undergraduate", None, NS, near="GROUP"),
        M("Alexander Goldberg", "phd", None, NS, near="ALUMNI", note="listed under alumni, PhD in CS; PI joined CMU 2017"),
        M("Charvi Rastogi", "phd", None, NS, near="ALUMNI", note="PhD MLD; PI joined CMU 2017"),
        M("Steven Jecmen", "phd", None, NS, near="ALUMNI", note="PhD CSD; PI joined CMU 2017"),
        M("Ivan Stelmakh", "phd", None, NS, near="ALUMNI", note="PhD MLD; PI joined CMU 2017"),
        M("Jingyan Wang", "phd", None, NS, near="ALUMNI", note="PhD Robotics Institute; page also says she won AAMAS 2019 best student paper"),
        M("Sarina Xi", "masters", None, NS, near="ALUMNI"),
        M("Arshika Lalan", "masters", None, NS, near="ALUMNI"),
        M("Janet (Jhih-Yi) Hsieh", "masters", None, NS, near="ALUMNI"),
        M("Ziming Luo", "staff", None, NS, near="ALUMNI", note="Research Associate"),
        M("Ryan Liu", "masters", None, NS, near="ALUMNI", note="BS and MS in CS"),
        M("Carmel Baharav", "undergraduate", None, NS, near="ALUMNI"),
        M("Komal Dhull", "undergraduate", None, NS, near="ALUMNI"),
        M("Wenxin Ding", "masters", None, NS, near="ALUMNI", note="MS CS, BS Math/CS"),
        M("Orelia Pi", "undergraduate", None, NS, near="ALUMNI"),
        M("Qiqi Xu", "masters", None, NS, near="ALUMNI"),
    ],
    pubs=[PUB(NS, mode="auto", note="publications list is on the homepage")],
    notes="Group and Alumni sections are on the PI homepage (no separate group page; /group.html 404s). Alumni entries are undated but each names a CMU department/program and the PI joined CMU in 2017, so all are within 2016-2026; recorded with years None.",
    blocked=["https://www.science.org/content/article/ai-conferences-use-ai-assign-papers-reviewers"],
)

# ---- Srinivasan Seshan
SG = "http://www.cs.cmu.edu/~srini/group/"
D["Srinivasan Seshan"] = dict(
    lab_site="http://www.cs.cmu.edu/~srini/",
    people_page=SG,
    people_pages=[SG],
    members=[
        M("Yuze He", "postdoc", None, SG, near="Postdocs"),
        M("Shawn Shuoshuo Chen", "phd", None, SG, near="Current Research group Members"),
        M("Sagar Bharadwaj", "phd", None, SG, near="Current Research group Members"),
        M("Chris Canel", "phd", None, SG, near="Current Research group Members"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~srini/papers/", mode="auto")],
    notes="placeholder",
    blocked=[],
)

# ---- Justine Sherry
JS = "https://www.justinesherry.com/"
D["Justine Sherry"] = dict(
    lab_site=JS,
    people_page=JS,
    people_pages=[JS],
    members=[
        M("Hugo Sadok", "phd", None, JS, near="Research Lab/Team"),
        M("Miguel Ferreira", "phd", None, JS, near="Research Lab/Team"),
        M("Francisco Pereira", "member", None, JS, near="Research Lab/Team"),
        M("Isabel Suizo", "member", None, JS, near="Research Lab/Team"),
        M("Yiran Lei", "member", None, JS, near="Research Lab/Team"),
        M("Emily Spencer", "member", None, JS, near="Research Lab/Team"),
        M("Hamna Shafqat", "member", None, JS, near="Research Lab/Team"),
        M("Ranysha Ware", "phd", [None, 2024], JS, near="Alumni", note="PhD 2024"),
        M("Nirav Atre", "phd", [None, 2024], JS, near="Alumni", note="PhD 2024"),
        M("Adithya Abraham Philip", "phd", [None, 2024], JS, near="Alumni", note="PhD 2024"),
    ],
    pubs=[PUB("https://www.justinesherry.com/papers.html", mode="li")],
    notes="placeholder",
    blocked=[],
)

# ---- Cosma Shalizi
CS = "https://www.stat.cmu.edu/~cshalizi/"
D["Cosma Shalizi"] = dict(
    lab_site=CS,
    people_page=CS,
    people_pages=[CS],
    members=[
        M("George Montañez", "phd", None, CS, q="My student George Montañez"),
    ],
    pubs=[PUB("http://bactra.org/research/", mode="auto", note="PI's own research/papers page (bactra.org)")],
    notes="placeholder",
    blocked=[],
)

# ---- Vyas Sekar
VG = "https://users.ece.cmu.edu/~vsekar/group/"
D["Vyas Sekar"] = dict(
    lab_site="https://users.ece.cmu.edu/~vsekar/",
    people_page=VG,
    people_pages=[VG],
    members=[
        M("Milind Srivastava", "phd", None, VG, near="Current Ph.D Students"),
        M("Steven Dong", "phd", None, VG, near="Current Ph.D Students"),
        M("Peilin Xin", "phd", None, VG, near="Current Ph.D Students"),
        M("Marko Morrison", "phd", None, VG, near="Current Ph.D Students"),
        M("Lakshmi Adiga", "phd", None, VG, near="Current Ph.D Students"),
        M("Hamna Shafqat", "phd", None, VG, near="Current Ph.D Students"),
        M("Glenda Tan", "phd", None, VG, near="Current Ph.D Students"),
        M("Lesley Zhou", "visitor", None, VG, near="Visiting Students and Postdocs", note="visiting PhD student from University of Maryland"),
        M("Yihao Chen", "postdoc", None, VG, near="Visiting Students and Postdocs", note="CBI Fellow"),
    ],
    pubs=[PUB("https://users.ece.cmu.edu/~vsekar/publications/", mode="auto")],
    notes="placeholder",
    blocked=[],
)

# ---- Russell Schwartz ----
RS_LIVE = "https://labs.bio.cmu.edu/schwartz/people/"
RS21 = WB + "20210515014313id_/https://labs.bio.cmu.edu/schwartz/people/"
D["Russell Schwartz"] = dict(
    lab_site="https://labs.bio.cmu.edu/schwartz/",
    people_page=RS_LIVE,
    people_pages=[RS_LIVE, RS21],
    members=[
        M("Nishat Bristy", "phd", None, RS_LIVE, near="Lab Members"),
        M("Lanting Li", "phd", None, RS_LIVE, near="Lab Members", note="co-advised by Oana Carja"),
        M("Thomas Rachman", "phd", None, RS_LIVE, near="Lab Members", note="co-advised by Oana Carja"),
        M("Arjun Srivatsa", "phd", None, RS_LIVE, near="Lab Members"),
        M("Gregory Smith", "phd", None, RS21, q="Gregory Smith Graduate Student", note="2021 Wayback capture of the people page (page footer dated 2014, so possibly stale)"),
        M("Lu Xie", "phd", None, RS21, q="Lu Xie Graduate Student", note="2021 Wayback capture (page footer dated 2014)"),
        M("Salim Chowdhury", "phd", None, RS21, q="Salim Chowdhury Graduate Student", note="2021 Wayback capture (page footer dated 2014)"),
        M("Theodore Roman", "phd", None, RS21, q="Theodore Roman Graduate Student", note="2021 Wayback capture (page footer dated 2014)"),
        M("Rachel Ehrlich", "masters", None, RS21, q="Rachel Ehrlich MS Student", note="2021 Wayback capture (page footer dated 2014)"),
        M("Marcus Thomas", "masters", None, RS21, q="Marcus Thomas MS Student", note="2021 Wayback capture (page footer dated 2014)"),
    ],
    pubs=[],
    notes="Lab site labs.bio.cmu.edu/schwartz (the CBD profile's Lab Members block lists only Bristy and Rachman). Live People page lists 4 PhD "
          "students (Bristy, Li, Rachman, Srivatsa). The 2021 Wayback capture shows an older roster (Smith, Xie, Chowdhury, Roman, Ehrlich, Thomas) "
          "recorded as seen in a 2016+ capture; the 2024 capture is identical to 2021. The 2017 and 2020 captures of the older homepage "
          "cs.cmu.edu/~russells and other years could not be read (archive.org back-off). Publications page (19 selected entries) matches 17 "
          "of the lab's papers already held, the other 2 are page-footer links, so no publications page added.",
    blocked=[],
)

# ---- Mary Shaw ----
D["Mary Shaw"] = dict(
    lab_site="http://www.cs.cmu.edu/~shaw/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="cs.cmu.edu/~shaw only redirects (meta refresh) to spoke.compose.cs.cmu.edu/shaweb/, which is robots-disallowed, so the real "
          "homepage could not be fetched; Wayback was in back-off so no archived copy could be read. The CSD affiliated-faculty profile lists "
          "research interests and 5 recent publications only (no students/advisees); the S3D profile URLs 404. No members or publications "
          "pages recoverable.",
    blocked=["http://spoke.compose.cs.cmu.edu/shaweb/ (robots-disallowed)"],
)

# ---- Yaser Ajmal Sheikh ----
YS = "https://www.ri.cmu.edu/ri-faculty/yaser-ajmal-sheikh/"
_ys = []
for _n, _r, _h in [
    ("Aayush Bansal", "phd", "past phd students"), ("Hanbyul Joo", "phd", "past phd students"),
    ("Natasha Kholgade", "phd", "past phd students"), ("Tomas Simon Kreuz", "phd", "past phd students"),
    ("Varun Ramakrishna", "phd", "past phd students"), ("Minh Vo", "phd", "past phd students"),
    ("Gines Hidalgo Martinez", "masters", "past masters students"), ("Shih-En Wei", "masters", "past masters students"),
    ("Donglai Xiang", "masters", "past masters students"), ("Luona Yang", "masters", "past masters students"),
]:
    _ys.append(M(_n, _r, None, YS, near=_h, note="undated past student on RI profile; recorded because already held from other sources (PI at CMU until 2019)"))
D["Yaser Ajmal Sheikh"] = dict(
    lab_site="http://www.cs.cmu.edu/~yaser/",
    people_page=YS,
    people_pages=[YS],
    members=_ys,
    pubs=[],
    notes="Personal homepage cs.cmu.edu/~yaser is a short bio (Consulting Professor at CMU; Meta VP 2015-2025; CMU RI faculty 2006-2019) with no "
          "students or publication list. The RI faculty profile lists undated past PhD (8) and MS (5) students; only those already held from other "
          "sources were recorded; Ankur Datta and Eakta Jain (PhD, predate 2016) and Fanyi Xiao (undated MS, not held) were skipped. "
          "RI profile publication list (97) is dynamically loaded, nothing parsable. Wayback in back-off, no archived captures read.",
    blocked=[],
)
