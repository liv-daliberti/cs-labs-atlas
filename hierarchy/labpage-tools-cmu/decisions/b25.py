from dhelp import M, PUB, WB

D = {}

# ---------------- Peter Steenkiste ----------------
H = "http://www.cs.cmu.edu/~prs/"
PS = "http://www.cs.cmu.edu/~prs/past_students.html"
H17 = WB + "20170214084459id_/http://www.cs.cmu.edu/~prs/"
H20 = WB + "20200125175044id_/http://www.cs.cmu.edu:80/~prs/"
D["Peter Steenkiste"] = dict(
    lab_site=H,
    people_page=H,
    people_pages=[H, PS, H17, H20],
    members=[
        M("Yuze He", "postdoc", [None, None], H, near="PhD Students and Postdocs"),
        M("Sofia Martins", "phd", None, H, near="PhD Students and Postdocs"),
        M("Shuoshuo (Shawn) Chen", "phd", None, H, near="PhD Students and Postdocs"),
        M("Rawan Al-Shaer", "phd", None, H, near="PhD Students and Postdocs"),
        M("Hun Namkung", "phd", [None, 2023], PS, near="PhD Students", note="thesis Spring 2023, co-advised with Vyas Sekar"),
        M("Rongye Shi", "phd", [None, 2019], PS, near="PhD Students", note="thesis Spring 2019; also current PhD student in 2017 capture"),
        M("Bruno Vavala", "phd", [None, 2017], PS, near="PhD Students", note="thesis Summer 2017"),
        M("David Naylor", "phd", [None, 2017], PS, near="PhD Students", note="thesis Summer 2017"),
        M("Guoyao (Freddie) Feng", "phd", None, H17, near="PhD Students", note="current PhD student in 2017 and 2020 captures"),
        M("Antonio Rodrigues", "phd", None, H17, near="PhD Students", note="current PhD student in 2017 and 2020 captures"),
        M("Sannan Tariq", "phd", None, H20, near="PhD Students", note="current PhD student in 2020 and 2023 captures"),
        M("Raja Sambasivan", "postdoc", [2014, 2016], PS, near="Past Postdocs"),
        M("Ashwin Ashok", "postdoc", [2014, 2016], PS, near="Past Postdocs"),
        M("Ashiwan Sivakumar", "postdoc", [2017, 2019], PS, near="Past Postdocs"),
        M("Kwame-Lante Wright", "postdoc", [2019, 2021], PS, near="Past Postdocs"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~prs/papers.html", mode="auto")],
    notes="Homepage lists current PhD students/postdocs; past_students.html (live, cached 503 earlier, refetched OK) lists graduated PhDs, postdocs with years, and MS theses (all MS theses end <=2016 or are undated, none recorded; ~25 MS entries skipped). Wayback 2017, 2020, 2023 homepage captures read for alumni. 2023 capture spells 'Sofia Martens' (same person as Martins). Pre-2016 PhD grads and postdocs skipped (Meireles, Wang, Nychis, Cooper, Cardote, Jesus, Dogar, Liu, etc.; Edward Segall, Eric Anderson, Suk-Bok Lee, Chenren Xu). papers.html last updated 2015 (only 1 in-window entry); homepage Recent Papers list not parseable. Also lists co-advisors (Sekar, Seshan, Veloso) as collaborators only.",
    blocked=[],
)

# ---------------- Ravi Starzl ----------------
D["Ravi Starzl"] = dict(
    lab_site=None,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="LTI profile (lti.cmu.edu/people/faculty/starzl-ravi.html) lists him as Adjunct Professor with only contact info and education (PhD LTI 2012, immune-signal modeling thesis); no lab website, group or students section. LTI students/alumni index pages do not group by advisor. A WebSearch found only news items describing him as co-director of CMU's biotechnology, innovation and computation program; no lab site or member list exists.",
    blocked=[],
)

# ---------------- Emma Strubell ----------------
SL = "https://strubell.github.io/slab/"
D["Emma Strubell"] = dict(
    lab_site="https://strubell.github.io/slab/",
    people_page=SL,
    people_pages=[SL],
    members=[
        M("Jared Fernandez", "phd", None, SL, near="Current students", note="LTI PhD student; co-advised with Yonatan Bisk"),
        M("Jeremiah Milbauer", "phd", None, SL, near="Current students"),
        M("Clara Na", "phd", None, SL, near="Current students"),
        M("Nupoor Gandhi", "phd", None, SL, near="Current students", note="ML & Public Policy PhD student"),
        M("Sireesh Gururaja", "phd", None, SL, near="Current students"),
        M("Sanket Vaibhav Mehta", "phd", [None, 2023], SL, near="Alumni"),
        M("Zhisong Zhang", "phd", [None, 2023], SL, near="Alumni", note="co-advised with Ed Hovy"),
    ],
    pubs=[PUB("https://strubell.github.io/publications/", mode="auto")],
    notes="SLAB page (strubell.github.io/slab) lists 5 current students and 2 alumni (both LTI PhD 2023); homepage says Strubell is on part-time leave. Wayback captures of the slab page not yet read (see later note if updated).",
    blocked=[],
)

# ---------------- George D Stetten ----------------
VP = "https://web.pitt.edu/vialab/1327-2/"
D["George D Stetten"] = dict(
    lab_site="https://web.pitt.edu/vialab/",
    people_page=VP,
    people_pages=[VP],
    members=[
        M("Zhixuan Yu", "masters", [None, 2016], VP, q="Zhixuan Yu MS, BME, CMU, December 2016", note="MS BME CMU, December 2016"),
        M("Samantha Horvath", "phd", [2016, None], VP, q="Samantha Horvath BS, BioE, Pitt PhD student, Robotics Institute, CMU, 2016", note="BS Pitt; PhD student at CMU Robotics Institute from 2016"),
    ],
    pubs=[PUB("https://web.pitt.edu/vialab/1316-2/", mode="auto")],
    notes="The VIA Lab (vialab.org -> web.pitt.edu/vialab) is based in Pitt Bioengineering; Stetten is Adjunct Research Professor at the CMU RI. Present members are all Pitt undergraduates (Ben Cohen, Jack Lorence, Satyaj Bhargava, Nneji Therese, Jefferson Isaiah III, Anisha Virmani) so not recorded. Past-member list is mostly Pitt people; CMU-linked alumni without dates skipped: Han-Yu Lee (MS ME CMU), Randy Lee (MS BME CMU, PhD Pitt 2017), Jihang Wang (MS BME CMU, PhD Pitt 2016), Tejas Mathai (MS BME CMU, PhD RI), Ada Zhang (PhD RI), Bing Wu (postdoc psych CMU), plus older pre-2016 RI PhDs (Damion Shelton, Sam Clanton, Bert Unger, Robert Tamburo, John Galeotti, Bo Wang) - about 12 undated or pre-window entries in total. Publications page includes Pitt undergrad posters; parsed with auto (bold titles).",
    blocked=[],
)

# ---------------- Joshua S Sunshine ----------------
AD = "http://www.cs.cmu.edu/~jssunshi/advising/"
D["Joshua S Sunshine"] = dict(
    lab_site="http://www.cs.cmu.edu/~jssunshi/",
    people_page=AD,
    people_pages=[AD],
    members=[
        M("Matthew Davis", "phd", None, AD, near="phd students", note="co-advised by Brad Myers"),
        M("Sam Estep", "phd", None, AD, near="phd students"),
        M("Ian McCormack", "phd", None, AD, near="phd students", note="co-advised by Jonathan Aldrich"),
        M("Hwei-Shin Harriman", "phd", None, AD, near="phd students", note="co-advised by Dominik Moritz; undergraduate Summer 2022"),
        M("Yiliang Liang", "phd", None, AD, near="phd students", note="co-advised by Eunsuk Kang; undergraduate Summer 2022"),
        M("Molly MacLaren", "phd", None, AD, near="phd students"),
        M("Prith Sharma", "masters", [2026, 2026], AD, near="masters students"),
        M("Rafayel Amirkhanyan", "undergraduate", [2025, 2026], AD, near="undergraduate students"),
        M("Ryan Hung", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Ethan Chen", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Jose German", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Etash Jhanji", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Gorden Jin", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Sally (Daeun) Lee", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Quyen Tran", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Michael Wu", "undergraduate", [2026, 2026], AD, near="undergraduate students"),
        M("Wode “Nimo” Ni", "phd", None, AD, near="phd alumni", note="co-advised by Ken Koedinger; undergraduate summers 2017, 2018"),
        M("Griffin Teller", "undergraduate", [2024, 2025], AD, near="undergraduate alumni"),
        M("Tai Nguyen", "undergraduate", [2025, 2025], AD, near="undergraduate alumni"),
        M("Avinash Palliyil", "undergraduate", [2024, 2025], AD, near="undergraduate alumni"),
        M("Rijul Jain", "undergraduate", [2023, 2025], AD, near="undergraduate alumni"),
        M("Maggie Hollis", "undergraduate", [2024, 2024], AD, near="undergraduate alumni"),
        M("Yuchen “Rainy” Jin", "undergraduate", [2024, 2024], AD, near="undergraduate alumni"),
        M("Kyle Lee", "undergraduate", [2024, 2024], AD, near="undergraduate alumni"),
        M("Amy Wei", "undergraduate", [2023, 2024], AD, near="undergraduate alumni"),
        M("Raven Rothkopf", "undergraduate", [2023, 2023], AD, near="undergraduate alumni"),
        M("Tomas Dugan", "undergraduate", [2023, 2023], AD, near="undergraduate alumni"),
        M("Yonah Goldberg", "undergraduate", [2023, 2023], AD, near="undergraduate alumni"),
        M("Will Rinkoff", "undergraduate", [2021, 2023], AD, near="undergraduate alumni"),
        M("Sang Choi", "undergraduate", [2022, 2022], AD, near="undergraduate alumni"),
        M("Max Krieger", "undergraduate", [2019, 2022], AD, near="undergraduate alumni"),
        M("Helena Yang", "undergraduate", [2021, 2021], AD, near="undergraduate alumni"),
        M("Lavinia Dunagan", "undergraduate", [2021, 2021], AD, near="undergraduate alumni"),
        M("Hita Kambhamettu", "undergraduate", [2021, 2021], AD, near="undergraduate alumni"),
        M("Xin Ran “Mia” Tang", "undergraduate", [2020, 2021], AD, near="undergraduate alumni"),
        M("Stella Trout", "undergraduate", [2020, 2020], AD, near="undergraduate alumni"),
        M("Courtney Miller", "undergraduate", [2019, 2019], AD, near="undergraduate alumni"),
        M("Anael Kuperwajs Cohen", "undergraduate", [2019, 2019], AD, near="undergraduate alumni"),
        M("Gauri Kambhatla", "undergraduate", [2019, 2019], AD, near="undergraduate alumni"),
        M("Lily Shellhammer", "undergraduate", [2018, 2018], AD, near="undergraduate alumni"),
        M("Miles Baker", "undergraduate", [2018, 2018], AD, near="undergraduate alumni"),
        M("Paulette Koronkevich", "undergraduate", [2018, 2018], AD, near="undergraduate alumni"),
        M("Celeste Barnaby", "undergraduate", [2017, 2017], AD, near="undergraduate alumni"),
        M("Tyler Etzel", "undergraduate", [2016, 2017], AD, near="undergraduate alumni"),
        M("Whitney Nelson", "undergraduate", [2016, 2016], AD, near="undergraduate alumni"),
        M("David Widder", "undergraduate", [2016, 2016], AD, near="undergraduate alumni"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~jssunshi/publications/", mode="li")],
    notes="Advising page lists PhD, MS and undergrad advisees with seasons. Skipped as undated: PhD alumna Jenna DiVincenzo (Wise) (now Purdue ECE), masters alumni Dor Ma'ayan, Johann Thor Mogensen Ingibergsson, Waqar Ahmad, Darpan Saini (4 undated masters alumni, 1 undated PhD alumna). Skipped pre-2016: undergrads Sophie Gairo (2015), Sarah Chasins (2011). PhD thesis-committee members (Michael Coblenz, Zack Coker) are not advisees. Wayback captures of the advising page not read (live page already lists dated alumni back to 2011).",
    blocked=[],
)

# ---------------- Anthony Stentz ----------------
D["Anthony Stentz"] = dict(
    lab_site=None,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="No lab website. RI profile (ri.cmu.edu/ri-people/anthony-tony-stentz/, courtesy faculty, NREC) has only 'past phd students' (22 names) and 'past masters students' (9 names), all undated (e.g. Boris Sofman, David Silver, Carl Wellington, Felix Duvallet, Bradford Neuman) so skipped by the undated rule (31 undated); no current-students section. Profile publications tab loads dynamically ('Displaying 227 Publications') and does not parse. NREC (nrec.ri.cmu.edu) is a center, not his lab. Wayback copy of RI faculty index (lab_url) is only a faculty index.",
    blocked=[],
)

# ---------------- Aaron M Steinfeld ----------------
TP = "https://labs.ri.cmu.edu/tbd/people/"
D["Aaron M Steinfeld"] = dict(
    lab_site="https://labs.ri.cmu.edu/tbd/",
    people_page=TP,
    people_pages=[TP],
    members=[
        M("Liz Carter", "staff", None, TP, near="Staff"),
        M("Anthony Tomasic", "other", None, TP, near="Staff", note="external consultant to the lab; 15 years Senior Systems Scientist at CMU (dates not stated)"),
        M("Avigyan Bhattacharya", "phd", None, TP, near="Advised Graduate Students", note="Master's and PhD student, RI"),
        M("Rayna Hata", "phd", None, TP, near="Advised Graduate Students"),
        M("Peya Mowar", "phd", None, TP, near="Advised Graduate Students"),
        M("Azusa Sawada", "visitor", [2026, 2026], TP, near="Visitors", note="visiting scholar from Keio University"),
        M("Tenma Uchiyama", "visitor", [2026, 2027], TP, near="Visitors", note="visiting PhD from Keio University"),
        M("Ryo Fujii", "visitor", [2025, 2026], TP, near="Visitor Alumni", note="visiting PhD from Keio University"),
        M("Yasuhiro Nitta", "visitor", [2025, 2026], TP, near="Visitor Alumni", note="visiting PhD from Keio University"),
        M("Sikai Chen", "visitor", [2019, 2022], TP, near="Visitor Alumni", note="visiting scholar from Purdue University"),
        M("Alvaro Castro-Gonzales", "visitor", [2017, 2017], TP, near="Visitor Alumni", note="faculty visitor from Universidad Carlos III Madrid"),
    ],
    pubs=[],
    notes="TBD Lab people page (labs.ri.cmu.edu/tbd/people) lists current staff/students/visitors with dates for visitors only. Thesis alumni (18), postdoc/staff alumni (20) and student alumni (about 110 names) are undated, so skipped by rule; many thesis alumni are already held. Publications page (labs.ri.cmu.edu/tbd/publications, 172 numbered APA-style entries) does not parse with any pubs mode (entries are not separate elements; extractor returns 1 entry), so no pubs page added. Wayback captures of tbd.ri.cmu.edu/people (2020, 2021 only) pending Wayback availability.",
    blocked=[],
)

# ---------------- Katia P Sycara ----------------
SY = "https://www.ri.cmu.edu/ri-faculty/katia-sycara/"
SG = "https://www.ri.cmu.edu/robotics-groups/advanced-agent-robotics-technology-lab/"
D["Katia P Sycara"] = dict(
    lab_site="https://www.ri.cmu.edu/robotics-groups/advanced-agent-robotics-technology-lab/",
    people_page=SY,
    people_pages=[SY, SG],
    members=[
        M("Silong Yong", "phd", None, SY, near="current phd students"),
        M("Renos Zabounidis", "phd", None, SY, near="current phd students"),
        M("Ce Zhang", "phd", None, SY, near="current phd students"),
        M("Junyi He", "masters", None, SY, near="current masters students"),
        M("Jinxi He", "masters", None, SY, near="current masters students"),
        M("Zihan Liu", "masters", None, SY, near="current masters students"),
        M("Xinhe Wang", "masters", None, SY, near="current masters students"),
        M("Dana Hughes", "staff", None, SG, near="current staff"),
        M("Woosung Kim", "staff", None, SG, near="current staff"),
        M("Yaqi Xie", "staff", None, SG, near="current staff"),
        M("Sarthak Bhagat", "masters", None, SY, near="current affiliates"),
        M("Yu Quan Chong", "masters", None, SY, near="current affiliates"),
        M("Brandon Rishi", "masters", None, SY, near="current affiliates"),
        M("Shreya Sharma", "masters", None, SY, near="current affiliates"),
        M("Wei-Hao Zeng", "masters", None, SY, near="current affiliates"),
    ],
    pubs=[],
    notes="Lab page softagents (cs.cmu.edu/~softagents) is stale (people page copyright 2006-2014; publications through 2014), so members come from the RI profile and the RI group page (current head/staff/students; the profile lists current affiliates, current PhD and MS students). Not recorded because undated: past PhD students (8: Jyi Shane Liu, Lingzhi Luo, Wenhao Luo, Sasanka Nagavalli, Yuriy Nevmyvaka, Gita Sukthankar, Prasanna Velagapudi, Sha Yi) and past masters students (about 43, e.g. Akshat Agarwal, Seth Karten, Vidhi Jain, Rohit Jena), plus group-page past members Sam Li and Shuyang Shi. RI profile publications tab loads dynamically (584 pubs) and is not parseable. Wayback captures of the RI profile pending Wayback availability.",
    blocked=[],
)

# ---------------- Wennie Tabib ----------------
RP = "https://rislab.org/people"
D["Wennie Tabib"] = dict(
    lab_site="https://rislab.org/",
    people_page=RP,
    people_pages=[RP],
    members=[
        M("Abhishek Rathod", "staff", None, RP, near="Staff"),
        M("John Stecklein", "staff", None, RP, near="Staff"),
        M("Edsel Burkholder", "staff", None, RP, near="Staff"),
        M("Kshitij Goel", "staff", None, RP, near="Staff"),
        M("Nishanth Bobbili", "staff", None, RP, near="Staff"),
        M("Mike Anoruo", "phd", None, RP, near="PhD Students"),
        M("Johnny Tian", "masters", None, RP, near="MS Students"),
        M("Gabriel Rodriguez", "masters", None, RP, near="MS Students"),
        M("Michael Allen", "masters", None, RP, near="MS Students"),
        M("Steven Yang", "undergraduate", None, RP, near="Undergraduate Students"),
        M("Henri Sayag", "undergraduate", None, RP, near="Undergraduate Students"),
        M("Aaron Ding", "undergraduate", None, RP, near="Undergraduate Students"),
        M("Nicole Chan", "masters", [None, 2026], RP, near="Alumni"),
        M("Jonathan Lee", "masters", [None, 2025], RP, near="Alumni"),
        M("Akshay Chekuri", "masters", [2023, 2024], RP, near="Alumni", note="ECE IMB (integrated master's)"),
        M("Lucky Kant Nayak", "staff", [2024, 2025], RP, near="Alumni"),
        M("Ankit Khandelwal", "masters", [2024, 2025], RP, near="Alumni", note="ECE IMB (integrated master's)"),
        M("Rohan Dhesikan", "masters", [None, 2023], RP, near="Alumni"),
    ],
    pubs=[PUB("https://rislab.org/publications.html", mode="auto")],
    notes="rislab.org/people is Tabib's lab page (formerly Nathan Michael's RISLab). Live page read: faculty, 5 staff, 1 PhD, 3 MS, 3 undergrads, 7 alumni (Yves Georgy Daoud undated, skipped; 1 undated). Robots listed (Acerodon, Crazyflie, ...) are not people. Publications page parsed with auto (20 in window, 15 matched, 5 missing, which are 2016-2019 Nathan Michael-era papers). Wayback captures of the people page: see below if added.",
    blocked=[],
)

# ---------------- Ameet Talwalkar ----------------
TG = "http://www.cs.cmu.edu/~atalwalk/group.html"
D["Ameet Talwalkar"] = dict(
    lab_site="http://www.cs.cmu.edu/~atalwalk/",
    people_page=TG,
    people_pages=[TG],
    members=[
        M("Valerie Chen", "phd", None, TG, near="Current"),
        M("Wayne Chi", "phd", None, TG, near="Current", note="joint with Chris Donahue"),
        M("Shanda Li", "phd", None, TG, near="Current", note="joint with Yiming Yang"),
        M("Junhong Shen", "phd", None, TG, near="Current"),
        M("Anna Wei", "phd", None, TG, near="Current", note="joint with Andrej Risteski"),
        M("Stephan Xie", "phd", None, TG, near="Current"),
        M("Tejas Guha", "masters", None, TG, near="Current"),
        M("Ryan Shar", "masters", None, TG, near="Current"),
    ],
    pubs=[],
    notes="placeholder-to-be-replaced",
    blocked=[],
)

# ---------------- Michael Tarr ----------------
TL = "https://sites.google.com/andrew.cmu.edu/tarrlab/people"
D["Michael Tarr"] = dict(
    lab_site="https://sites.google.com/andrew.cmu.edu/tarrlab/",
    people_page=TL,
    people_pages=[TL],
    members=[
        M("Jacob Yeung", "member", None, TL, s="people I am on sabbatical", e="Jacob Yeung"),
    ],
    pubs=[],
    notes="placeholder-to-be-replaced",
    blocked=[],
)

# ---------------- Zeynep Temel ----------------
ZP = "http://zoomlab.ri.cmu.edu/people/"
ZR = "https://www.ri.cmu.edu/robotics-groups/zoom-lab/"
ZF = "https://www.ri.cmu.edu/ri-faculty/zeynep-temel/"
D["Zeynep Temel"] = dict(
    lab_site="http://zoomlab.ri.cmu.edu/",
    people_page=ZP,
    people_pages=[ZP, ZR, ZF],
    members=[
        M("Zilin Si", "phd", None, ZP, near="PhD Students"),
        M("Sarvesh Patil", "phd", None, ZP, near="PhD Students"),
        M("Shashwat Singh", "phd", None, ZP, near="PhD Students"),
        M("Guadalupe Bernal", "phd", None, ZP, near="PhD Students"),
        M("Fokion Sanoudos-Dramaliotis", "phd", None, ZP, near="PhD Students"),
        M("Sidney Nimako", "masters", None, ZP, near="Master’s Students"),
        M("Zhuowei Xu", "masters", None, ZP, near="Master’s Students"),
        M("Kiran Marques", "masters", None, ZP, near="Master’s Students"),
        M("Janice Lee", "masters", None, ZP, near="Master’s Students"),
        M("Isaac Osei", "undergraduate", None, ZP, near="Undergraduate students"),
        M("Tiffany Han", "undergraduate", None, ZP, near="Undergraduate students"),
        M("Maggie Cai", "undergraduate", None, ZP, near="Undergraduate students"),
        M("Olivia Sobek", "undergraduate", None, ZP, near="Undergraduate students"),
        M("Vasilisa Ignatova", "undergraduate", None, ZP, near="Undergraduate students"),
        M("David Ma", "phd", None, ZP, near="Alumni"),
        M("Jennifer Yang", "masters", None, ZP, near="Master Students:"),
        M("Chris Chang", "masters", None, ZP, near="Master Students:"),
        M("Timothy Mayer", "masters", None, ZP, near="Master Students:"),
        M("Yi Zhao", "masters", None, ZP, near="Master Students:"),
        M("Erin Wong", "masters", None, ZP, near="Master Students:"),
        M("Fukang Liu", "masters", None, ZP, near="Master Students:"),
        M("Avi Rudich", "masters", None, ZP, near="Master Students:"),
        M("Tony Tao", "undergraduate", None, ZP, near="Undergraduate Students:"),
        M("James Clinton", "undergraduate", None, ZP, near="Undergraduate Students:"),
        M("Kylie Barber", "undergraduate", None, ZP, near="Undergraduate Students:"),
        M("Sam Alvares", "undergraduate", None, ZP, near="Undergraduate Students:"),
        M("Emily Guo", "undergraduate", None, ZP, near="Undergraduate Students:"),
        M("Max Kramer", "undergraduate", None, ZP, near="Undergraduate Students:"),
        M("Elena Behzadi", "member", None, ZR, near="current student"),
        M("Becca Carpenter", "phd", None, ZF, near="current phd students"),
        M("Johnathon Ciecierski", "member", None, ZF, near="current affiliates"),
        M("Sha Yi", "phd", None, ZF, near="past phd students"),
        M("Chiheb Boussema", "member", None, ZR, near="past members"),
        M("Apple Zhao", "member", None, ZR, near="past members"),
    ],
    pubs=[PUB("http://zoomlab.ri.cmu.edu/publications", mode="auto")],
    notes="placeholder-to-be-replaced",
    blocked=[],
)
