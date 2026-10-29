from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Jeremy Avigad
JA = "https://www.andrew.cmu.edu/user/avigad/students.html"
JA_CSD = "https://www.csd.cs.cmu.edu/people/faculty/jeremy-avigad"
D["Jeremy Avigad"] = dict(
    lab_site="https://www.andrew.cmu.edu/user/avigad/",
    people_page=JA,
    people_pages=[JA, JA_CSD],
    members=[
        # PhD students
        M("Xinrui (Henry) Li", "phd", None, JA, near="PhD students"),
        M("Sidharth Hariharan", "phd", None, JA, q="Sidharth Hariharan (Mathematical Sciences, current)",
          note="PhD student (listed under PhD students)"),
        M("Chase Norman", "phd", None, JA, near="PhD students"),
        M("Cayden Codel", "phd", None, JA, near="PhD students", note="co-advised with Marijn Heule"),
        M("Hannah Fechtner", "phd", None, JA, near="PhD students",
          note="PhD in Logic, Computation, and Methodology (Philosophy)"),
        M("Joshua Clune", "phd", None, JA, near="PhD students"),
        M("Wojciech Nawrocki", "phd", [None, 2026], JA,
          q="Wojciech Nawrocki (PhD Logic, Computation, and Methodology, May 2026)"),
        M("Mario Carneiro", "phd", [None, 2022], JA, q="Mario Carneiro (PhD Pure and Applied Logic, August 2022)",
          note="then postdoc with Avigad 2022-2024 (Hoskinson Center) per 'Postdocs supervised'"),
        M("Floris van Doorn", "phd", [None, 2018], JA, q="Floris van Doorn (PhD Pure and Applied Logic, May 2018)"),
        M("Robert Lewis", "phd", [None, 2018], JA, q="Robert Lewis (PhD Pure and Applied Logic, May 2018)"),
        # MS students
        M("Tianxiang Gao", "masters", None, JA, q="Tianxiang Gao (MS Logic, Computation, and Methodology, current)"),
        M("Tate Rowney", "masters", None, JA,
          q="Tate Rowney (MS Mathematical Sciences, co-advised with Sean Welleck, current)"),
        M("Riyaz Ahuja", "masters", [None, 2026], JA,
          q="Riyaz Ahuja (MS Mathematical Sciences, co-advised with Prasad Tetali and Sean Welleck, 2026)"),
        M("James Gallicchio", "masters", [None, 2026], JA, near="MS students",
          note="'(Computer Science, co-advised with Marijn Heule, May 2026)' under MS students"),
        M("Shuge Rong", "masters", [None, 2026], JA, q="Shuge Rong (MS Logic, Computation, and Methodology, May 2026)"),
        M("Thomas Zhu", "masters", [None, 2026], JA,
          q="Thomas Zhu (MS Language Technologies Institute, co-advised with Sean Welleck, May 2026)"),
        M("Aeacus (Zhaobo) Sheng", "masters", [None, 2025], JA,
          q="Aeacus (Zhaobo) Sheng (MS Logic, Computation, and Methodology, 2025)"),
        M("Paula Neeley", "masters", [None, 2020], JA,
          q="Paula Neeley (MS Logic, Computation, and Methodology, December 2020)"),
        M("Andrew Warren", "masters", [None, 2019], JA, q="Andrew Warren (MS, Mathematical Sciences, 2019)"),
        M("Seulkee Baek", "masters", [None, 2017], JA, q="Seulkee Baek (MS Logic, Computation, and Methodology, 2017)"),
        M("Minchao Wu", "masters", [None, 2017], JA,
          q="Minchao Wu (MS Logic, Computation, and Methodology, August 2017)"),
        M("Andrew Zipperer", "masters", [None, 2016], JA,
          q="Andrew Zipperer (MS Logic, Computation, and Methodology, August, 2016)"),
        M("Sebastian Ullrich", "visitor", [2016, 2016], JA,
          q="Sebastian Ullrich (Masters' degree from Karlsruhe Institute of Technology, fall 2016; visited Carnegie "
            "Mellon under the InterACT program)",
          note="KIT master's student who wrote his thesis while visiting CMU (InterACT), fall 2016"),
        # undergraduates
        M("Peter Khoudary", "undergraduate", [None, 2025], JA, q="Peter Khoudary (BS in Logic and Computation, May 2025)"),
        M("Alex Gillon", "undergraduate", [None, 2024], JA, q="Alex Gillon (BS in Logic and Computation, May 2024)"),
        M("Minsung Cho", "undergraduate", [None, 2022], JA, q="Minsung Cho (BS in Logic and Computation, May 2022)"),
        M("Ashley Watt", "undergraduate", [None, 2019], JA, q="Ashley Watt (BS in Logic and Computation, May 2019)"),
        # postdocs
        M("Tomáš Sk&rcaron;ivan", "postdoc", [2022, 2025], JA, near="Postdocs supervised",
          note="page has a broken HTML entity; the name is Tomáš Skřivan"),
        M("Ali Mohammed Nezhad", "postdoc", [2022, 2023], JA, near="Postdocs supervised"),
        M("Edward Ayers", "postdoc", [2022, 2022], JA, near="Postdocs supervised"),
        M("Gabriel Ebner", "postdoc", [2021, 2022], JA, near="Postdocs supervised"),
        M("Bruno Bentzen", "postdoc", [2019, 2020], JA, near="Postdocs supervised"),
        M("Simon Hudon", "postdoc", [2019, 2020], JA, near="Postdocs supervised"),
        M("Johannes Hölzl", "postdoc", [2017, 2017], JA, near="Postdocs supervised"),
    ],
    pubs=[PUB("https://www.andrew.cmu.edu/user/avigad/papers.html", mode="li", title_css="mybold")],
    notes=("Avigad is in Philosophy/Math (CSD courtesy). His homepage students.html lists PhD, MS, undergraduate "
           "and postdoc advisees with degree dates; CSD profile lists advisees Clune, Codel, Norman (all on "
           "students.html). Skipped as pre-2016: Rebecca Morris (2015), Jason Rute, Sicun Gao, Yimu Yin, Henry "
           "Towsner, Kerry Ojakian, Ksenija Simic-Muller, Luke Serafin (Dec 2015), Jakob von Raumer (KIT, 2015), "
           "Northrop, Breiner, Dean, Kieffer, Hertz, White, Berkelhammer, Stonestreet, Kelvin Rojas (BS 2015), "
           "Erin Korber, postdocs Cody Roux (2012-14) and Philipp Gerhardy. PhD/MS committee lists are not "
           "advisees (skipped)."),
    blocked=[],
)

# ---------------------------------------------------------------- J. Andrew (Drew) Bagnell
BG = "http://robotwhisperer.org/lairlab-team/"
BG16 = WB + "20160127211102id_/http://robotwhisperer.org/lairlab-team/"
BGRI = "https://www.ri.cmu.edu/ri-faculty/j-andrew-drew-bagnell/"
BGRI23 = WB + "20230131024628id_/https://www.ri.cmu.edu/ri-faculty/j-andrew-drew-bagnell/"
D["J. Andrew (Drew) Bagnell"] = dict(
    lab_site="http://robotwhisperer.org/",
    people_page=BG,
    people_pages=[BG, BG16, BGRI, BGRI23],
    members=[
        M("Katherina Muelling", "postdoc", None, BG, near="PostDocs",
          note="spelled Katharina Muelling in the site's news posts; listed as current postdoc on live page and 2016 capture"),
        M("Shreyansh Daftry", "masters", None, BG, near="Current Students"),
        M("Allie Del Giorno", "phd", None, BG, near="Current Students"),
        M("Hanzhang Hu", "phd", None, BG, near="Current Students"),
        M("Shervin Javdani", "phd", None, BG, near="Current Students"),
        M("Wen Sun", "phd", None, BG, near="Current Students"),
        M("Arun Venkatraman", "phd", None, BG, near="Current Students"),
        M("Jiaji (Robin) Zhou", "phd", None, BG, near="Current Students"),
        M("Kevin Waugh", "phd", None, BG16, near="Current Students",
          note="current PhD student on the Jan 2016 capture; moved to Former Students on the live page"),
        M("Eric Haywiser", "staff", None, BG, near="Staff", note="listed under Staff on live page and Jan 2016 capture"),
        M("Matt Powers", "staff", None, BG, near="Staff", note="listed under Staff on live page and Jan 2016 capture"),
        M("Moslem Kazemi", "staff", None, BG, near="Staff", note="listed under Staff on live page and Jan 2016 capture"),
        M("Gokul Swamy", "phd", None, BGRI23, near="current phd students",
          note="RI profile Jan 2023 capture: the only current PhD student; past PhD on the live RI profile"),
        M("Anirudh Vemula", "phd", None, BGRI, near="past phd students",
          note="RI profile past PhD students (undated; already held)"),
    ],
    pubs=[],
    notes=("Lab site robotwhisperer.org (LAIRLab) has not been updated since ~2016: the team page is the same as the "
           "Jan 2016 capture except that Kevin Waugh moved to Former Students, so its 'Current'/'Staff'/'PostDocs' "
           "entries reflect 2016. Staff (Haywiser, Powers, Kazemi) and Muelling are only known from that frozen list. "
           "Later students come from the RI profile (live past PhD/MS lists, Jan 2023 capture 'current phd students: "
           "Gokul Swamy'); the 2017 and 2020 RI captures carry no student list. Skipped as pre-2016/undated alumni not "
           "seen as current in 2016+: former students Dey, Rhinehart (MS), Kumar Shaurya Shankar (MS), Sofman, "
           "Ziebart, N. Ratliff, Bradley, Maas, Ellie Lin Ratliff, Gallagher, Grubb, Tommy Liu, Munoz, Ross, Waliany, "
           "Low (16); former postdocs Dov Katz, Paul Vernaza and faculty Kris Kitani; visitor Andreas Wendel (2012 "
           "arrival per news post); lab-affiliated Pivtoraiko, Silver, Zucker. Pubs: the site's 'Preprints' page only "
           "lists 2010-2011 papers and its 'Publications' link redirects to the RI profile, whose 168 publications are "
           "embedded JSON that no pubx mode parses, so no PUB added. Bagnell is now a Consulting Professor (Aurora)."),
    blocked=[],
)

# ---------------------------------------------------------------- Andrea Bajcsy
AB = "https://cmu-intentlab.github.io/people.html"
ABRI = "https://www.ri.cmu.edu/ri-faculty/andrea-bajcsy/"
D["Andrea Bajcsy"] = dict(
    lab_site="https://cmu-intentlab.github.io/",
    people_page=AB,
    people_pages=[AB, ABRI],
    members=[
        M("Divyam Goel", "phd", [2026, None], AB, near="PhD Students"),
        M("Hyun Joe Jeong", "phd", [2025, None], AB, near="PhD Students"),
        M("Junwon Seo", "phd", [2024, None], AB, near="PhD Students"),
        M("Kensuke Nakamura", "phd", [2023, None], AB, near="PhD Students"),
        M("Yilin Wu", "phd", [2023, None], AB, near="PhD Students"),
        M("Shrita Singh", "masters", [2026, None], AB, near="Masters Students"),
        M("Linh-Co Bui", "masters", [2026, None], AB, near="Masters Students"),
        M("Sunny Agrawal", "masters", [2026, None], AB, near="Masters Students",
          note="RI MSR co-advised with Max Simchowitz; RI profile lists 'Sankalp Agrawal' as current masters; "
               "previously a RISS undergrad (Ohio State) in 2025"),
        M("Sanjit Sarda", "masters", [2026, None], AB, near="Masters Students", note="ECE MS"),
        M("Atiksh Bhardwaj", "masters", [2026, None], AB, near="Masters Students"),
        M("Andrew Li", "masters", [2025, None], ABRI, near="current masters students",
          note="lab page writes 'Andrew Z. Li' (RI MSR, Fall 2025); cited from RI profile so the builder does not "
               "merge him with the 2024 visiting undergrad Zirui Li"),
        M("Cheryl Li", "undergraduate", None, AB, near="Undergraduate Students", note="RISS visiting undergrad (Princeton)"),
        M("Quinn Pfeifer", "undergraduate", None, AB, near="Undergraduate Students",
          note="RISS visiting undergrad (UW), with Max Simchowitz"),
        M("Mijin Koo", "visitor", None, AB, near="Collaborators & Visiting Students",
          note="visiting student (Seoul National University)"),
        M("Ravi Pandya", "phd", [2023, 2025], AB, near="Previous PhD Students"),
        M("Surgan Jandial", "masters", [2024, 2026], AB, near="Previous Masters Students", note="CMU MSR"),
        M("Rosy Chen", "masters", [2026, 2026], AB, near="Previous Masters Students", note="CMU MsCS"),
        M("Evolone Layne", "masters", [2024, 2025], AB, near="Previous Masters Students", note="CMU HCII MS"),
        M("Vibhakar Mohta", "masters", [2024, 2024], AB, near="Previous Masters Students", note="CMU MRSD"),
        M("Matthew Kim", "undergraduate", [2025, 2026], AB, near="Previous Undergraduates", note="RISS (UC San Diego)"),
        M("Alina Du", "undergraduate", [2026, 2026], AB, near="Previous Undergraduates", note="RISS (USC)"),
        M("Jessie Yuan", "undergraduate", [2025, 2025], AB, near="Previous Undergraduates", note="CMU undergrad"),
        M("Eric Hu", "undergraduate", [2025, 2025], AB, near="Previous Undergraduates",
          note="visiting undergrad (Cornell), now RI MSR at CMU"),
        M("Leonardo Santos", "undergraduate", [2024, 2024], AB, near="Previous Undergraduates", note="RISS (UFMG, Brazil)"),
        M("Zirui Li", "undergraduate", [2024, 2024], AB, near="Previous Undergraduates", note="visiting undergrad"),
        M("Abigail Defranco", "undergraduate", [2024, 2025], AB, near="Previous Undergraduates", note="CMU undergrad"),
        M("Sandeep Reddy Baddam", "other", [2023, 2023], AB, near="Previous Undergraduates", note="listed as Intern, 2023"),
        M("Dingding Chen", "member", None, ABRI, near="current affiliates",
          note="RI profile 'current affiliates' (with Divyam Goel and Sanjit Sarda); not on the lab page"),
    ],
    pubs=[PUB("https://cmu-intentlab.github.io/publications.html", mode="css:td", title_css="papertitle")],
    notes=("Bajcsy joined CMU RI in Sept 2023 (from UC Berkeley). Intent Lab site people.html lists current members "
           "and dated alumni; no Wayback captures exist of the lab site (cdx returned 0). RI profile current/past "
           "lists agree with the lab page. Skipped: Ran (Thomas) Tian (UC Berkeley MechE PhD 2022-2025, Berkeley "
           "student, not placed at CMU); 'Collaborators' Parv Kapoor, Pranay Gupta, Reece Keller (CMU PhD students of "
           "other groups) and Lasse Peters (TU Delft PhD collaborator)."),
    blocked=[],
)

# ---------------------------------------------------------------- Maria Balcan
NB = "http://www.cs.cmu.edu/~ninamf/cv_nina.pdf"
D["Maria Balcan"] = dict(
    lab_site="http://www.cs.cmu.edu/~ninamf/",
    people_page=NB,
    people_pages=[NB],
    members=[
        M("Hedyeh Beyhaghi", "postdoc", [2022, 2024], NB, q="Postdocs mentored 1. Hedyeh Beyhaghi, March 2022 – August 2024"),
        M("Tejas Pagare", "phd", [2026, None], NB, q="Current PhD Students 1. Tejas Pagare. Carnegie Mellon. 2026 – present",
          note="co-advised with Karan Singh"),
        M("Eric Myzelev", "phd", [2026, None], NB, q="Eric Myzelev. Carnegie Mellon. March 2026 – present"),
        M("Andreas Kalavas", "phd", [2025, None], NB, q="Andreas Kalavas. Carnegie Mellon. October 2025 – present",
          note="co-advised with Weina Wang"),
        M("Kiriaki Fragkia", "phd", [2025, None], NB, q="Kiriaki Fragkia. Carnegie Mellon. October 2025 – present"),
        M("Rattana Pukdee", "phd", [2021, 2026], NB, q="Graduated PhD Students 1. Rattana Pukdee. Carnegie Mellon, 2021 – 2026",
          note="co-advised with Pradeep Ravikumar"),
        M("Siddharth Prasad", "phd", [2019, 2025], NB, q="Siddharth Prasad. Carnegie Mellon, Sept. 2019 – 2025",
          note="co-advised with Tuomas Sandholm"),
        M("Keegan Harris", "phd", [2022, 2025], NB, q="Keegan Harris. Carnegie Mellon. 2022 – 2025", note="co-advised with Steven Wu"),
        M("Mikhail Khodak", "phd", [2018, 2024], NB, q="Mikhail Khodak. Carnegie Mellon, 2018 – 2024",
          note="co-advised with Ameet Talwalkar"),
        M("Dravyansh Sharma", "phd", [2019, 2024], NB, q="Dravyansh Sharma. Carnegie Mellon, 2019 – 2024"),
        M("Ellen Vitercik", "phd", [2015, 2021], NB, q="Ellen Vitercik. Carnegie Mellon, 2015 –2021",
          note="co-advised with Tuomas Sandholm"),
        M("Travis Dick", "phd", [2014, 2019], NB, q="Travis Dick: Carnegie Mellon University, 2014 – 2019"),
        M("Hongyang Zhang", "phd", [2015, 2019], NB, q="Hongyang Zhang. Carnegie Mellon, 2015 – 2019",
          note="co-advised with David Woodruff"),
        M("Colin White", "phd", [2014, 2018], NB, q="Colin White, Carnegie Mellon. 2014 – 2018"),
        M("Krishna Pillutla", "masters", [2015, 2016], NB,
          q="Krishna Pillutla: CSD Master student, Carnegie Mellon University, 2015 -- 2016"),
        M("Daniel McNamara", "visitor", [2016, 2017], NB,
          q="Daniel McNamara: visiting PhD student (with a Fulbright Postgraduate Scholarship) from Australian National "
            "University and Data 61. Fall 2016 – Spring 2017"),
        M("Christopher Seiler", "undergraduate", [2021, 2022], NB,
          q="Christopher Seiler, undergraduate student, Carnegie Mellon University, 2021-2022"),
        M("Kai Wen-Wang", "undergraduate", [2019, 2019], NB,
          q="Kai Wen-Wang: undergraduate student, Carnegie Mellon University, Spring 2019"),
        M("Rong He", "undergraduate", [2019, 2019], NB, q="Rong He: undergraduate student, Carnegie Mellon University, Spring 2019"),
        M("Yifan Wang", "undergraduate", [2019, 2019], NB,
          q="Yifan Wang: visiting undergraduate student from Peking University. Summer 2019"),
        M("Yue Wu", "undergraduate", [2018, 2018], NB, q="Yue Wu: visiting undergraduate student from Peking University. Summer 2018"),
        M("Mengxiao Zhang", "undergraduate", [2017, 2017], NB,
          q="Mengxiao Zhang: visiting undergraduate student from Peking University. Summer 2017"),
        M("Wenlong Mou", "undergraduate", [2016, 2016], NB,
          q="Wenlong Mou: visiting undergraduate student from Peking University. Summer 2016"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~ninamf/pubs-by-year.html", mode="auto")],
    notes=("No group page; homepage has no student list, so the advisee lists come from the CV linked from the "
           "homepage ('my resume', cv_nina.pdf: postdocs, current/graduated PhD, MS, visiting and undergraduate "
           "students, all dated). Skipped: Georgia Tech students Shang-Tse Chen, Steven Ehrlich, Chris Berlind, "
           "Yingyu Liang, Pramod Gupta and postdoc Florin Constantin (GT/pre-CMU); pre-2016 Ruth Urner (postdoc "
           "2013-14), Pranjal Awasthi (2012), Ruta Mehta (2011), Jacob Abernethy (MSR 2009), Yu Wang (2014). "
           "PhD examining committee members are not advisees."),
    blocked=[],
)

# ---------------------------------------------------------------- Stephanie Balzer
SB = "http://www.cs.cmu.edu/~balzers/supervision.html"
SBH = "http://www.cs.cmu.edu/~balzers/"
D["Stephanie Balzer"] = dict(
    lab_site="http://www.cs.cmu.edu/~balzers/",
    people_page=SB,
    people_pages=[SB, SBH],
    members=[
        M("Yue Yao", "phd", None, SB, near="Current Group Members"),
        M("Yinsen (Tesla) Zhang", "phd", None, SB, near="Current Group Members"),
        M("Zak Kent", "phd", None, SB, near="Current Group Members", note="co-advised with Guy Blelloch"),
        M("Sonya Simkin", "masters", [None, 2025], SB, near="Current Group Members",
          note="homepage news: defended Master's thesis December 2025"),
        M("Rui Li", "masters", [2024, None], SB, near="Current Group Members",
          note="also 'Former Undergraduate Students: Rui Li (Undergraduate Student). Fall 2024. CMU.'"),
        M("Tucker Beaudin", "masters", None, SB, near="Current Group Members"),
        M("Alex Xu", "undergraduate", [2025, None], SB, near="Current Group Members",
          note="also listed 'Alex Xu (Undergraduate Student). Spring 2025. CMU.'"),
        M("Elisenda Lee-Palou", "undergraduate", None, SB, near="Current Group Members"),
        M("Asher Kornfeld-Narotzky", "undergraduate", None, SBH, near="Current Group Members",
          note="supervision.html spells it 'Asher Kornfel-Narotzky'"),
        M("Anrui Liu", "undergraduate", None, SB, near="Current Group Members"),
        M("Tarakaram Gollamudi", "postdoc", None, SB, near="Graduated Students and Postdoctoral Fellows"),
        M("Farzaneh Derakhshan", "postdoc", [2021, None], SB, near="Graduated Students and Postdoctoral Fellows",
          note="CMU PhD May 2021 (Balzer on committee), then Balzer's postdoc; now Assistant Professor at IIT"),
        M("Yuanchu Xie", "undergraduate", [2020, 2020], SB, q="Yuanchu Xie (Undergraduate Research Project). Spring 2020. CMU."),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~balzers/pubs.html", mode="auto")],
    notes=("Homepage 'Current Group Members' plus the linked supervision.html (current members, graduated "
           "students/postdocs, former undergraduates). Skipped: Jules Jacobs (PhD at Radboud University Nijmegen "
           "co-supervised with Robbert Krebbers, not placed at CMU); Simin Chen (REU 2012, pre-window); ETH Zurich "
           "thesis students 2005-2010; thesis committee members (not advisees); 'Collaborators' (Moine, Westrick, "
           "DeYoung, Harper)."),
    blocked=[],
)

# ---------------------------------------------------------------- Lujo Bauer
LB = "http://users.ece.cmu.edu/~lbauer/"
LBN = "Students, Postdocs, and Staff"
D["Lujo Bauer"] = dict(
    lab_site="http://users.ece.cmu.edu/~lbauer/",
    people_page=LB,
    people_pages=[LB],
    members=[
        M("Hobin Kim", "phd", None, LB, near=LBN, note="Societal Computing PhD, co-advised with Nicolas Christin"),
        M("Ronghao Ni", "phd", None, LB, near=LBN, note="ECE PhD, co-advised with Limin Jia"),
        M("Phyllis Poh", "phd", None, LB, near=LBN, note="ECE PhD"),
        M("Michael Stroucken", "staff", None, LB, q="Michael Stroucken (staff programmer)"),
        M("Jenny Tang", "phd", None, LB, near=LBN, note="Societal Computing PhD, co-advised with Nicolas Christin"),
        M("Rui Wang", "phd", None, LB, near=LBN, note="ECE PhD, co-advised with Limin Jia"),
        M("Ben Weinshel", "phd", None, LB, near=LBN, note="Societal Computing PhD, co-advised with Yuvraj Agarwal"),
        M("Xiaoyuan (Owen) Wu", "phd", None, LB, near=LBN, note="Societal Computing PhD"),
        M("Saranga Komanduri", "phd", [None, 2016], LB, q="Saranga Komanduri (CMU COS, advised by Lorrie Cranor, PhD 2016)",
          note="advised by Cranor; listed among students Bauer 'advised or worked with closely'"),
        M("Keane Lucas", "phd", [None, 2024], LB, q="Keane Lucas (CMU ECE, PhD 2024; now at Anthropic)"),
        M("Blase Ur", "phd", [None, 2016], LB, q="Blase Ur (CMU SC , advised by Lorrie Cranor, PhD 2016",
          note="advised by Cranor; listed among students Bauer 'advised or worked with closely'"),
        M("Yannis Mallios", "phd", [None, 2017], LB, q="Yannis Mallios (CMU ECE, PhD 2017"),
        M("Jassim Aljuraidan", "phd", [None, 2018], LB, q="Jassim Aljuraidan (CMU ECE, PhD 2018"),
        M("Billy Melicher", "phd", [None, 2019], LB, q="Billy Melicher (CMU ECE, PhD 2019"),
        M("Mahmood Sharif", "phd", [None, 2019], LB, q="Mahmood Sharif ( CMU ECE , PhD 2019"),
        M("Josh Tan", "phd", [None, 2020], LB, q="Josh Tan (CMU Societal Computing, PhD 2020"),
        M("Sruti Bhagavatula", "phd", [None, 2021], LB, q="Sruti Bhagavatula ( CMU Societal Computing , PhD 2021"),
        M("Weiran Lin", "phd", [None, 2025], LB, q="Weiran Lin ( CMU ECE , PhD 2025"),
        M("Andy Gallardo", "phd", [None, 2025], LB, q="Andy Gallardo (CMU Societal Computing, PhD 2025)"),
        M("Clement Fung", "phd", [None, 2025], LB, q="Clement Fung (CMU Societal Computing, PhD 2025"),
        M("Nuno Sabino", "phd", [None, 2025], LB,
          q="Nuno Sabino (CMU-Portugal CS PhD 2025, co-advised with Limin Jia, Pedro Adão, Rui Maranhão)"),
        M("Brian Singer", "phd", [None, 2025], LB, q="Brian Singer (CMU ECE, PhD 2025, co-advised with Vyas Sekar)"),
        M("Omer Akgul", "postdoc", [2023, 2024], LB, q="Omer Akgul (S3D postdoc 2023–2024)"),
        M("Camille Cobb", "postdoc", [2019, 2021], LB, q="Camille Cobb (CyLab postdoc 2019–2021"),
        M("McKenna McCall", "postdoc", [2023, 2025], LB, q="McKenna McCall (S3D postdoc 2023–2025"),
        M("Willard Rafnsson", "postdoc", [2015, 2017], LB, q="Willard Rafnsson (CyLab postdoc 2015–2017"),
        M("Eric Zeng", "postdoc", [2022, 2024], LB, q="Eric Zeng (CyLab postdoc 2022–2024)"),
        M("Sean Segreti", "masters", [2015, 2016], LB, q="Sean Segreti (CMU ECE, MS 2016; now KoreLogic)",
          note="listed twice: 'CMU ECE, MS 2016' and 'CMU ECE masters, 2015'"),
    ],
    pubs=[PUB("http://www.ece.cmu.edu/~lbauer/papers/", mode="auto")],
    notes=("Homepage section 'Students, Postdocs, and Staff' lists current advisees plus dated past PhD students, "
           "postdocs and others; the full paper list is at ~lbauer/papers/. Skipped as pre-2016: PhD Garriss (2008), "
           "Reeder (2008), Vaniea (2012), Mazurek (2014); postdoc Beckerle (2014-15); Shaoying Cai (2014), Fragkaki "
           "(2013), Huh (2014), Joel Lee (2013), Brad Miller (2009), Passaro (2014). Undated past entries not placed "
           "in the window by the live page: Xiaoxiao Tang (visiting PhD, SMU), Trevor Kann, Tony Felice, Wataru "
           "Hasegawa, Sudeep Modi, Ariel Rao."),
    blocked=[],
)

# ---------------------------------------------------------------- Nathan Beckmann
NBK = "https://cmu-corgi.github.io/people.html"
D["Nathan Beckmann"] = dict(
    lab_site="https://cmu-corgi.github.io/",
    people_page=NBK,
    people_pages=[NBK],
    members=[
        M("Nathan Serafin", "phd", [2019, None], NBK, near="Current PhD Students"),
        M("Souradip Ghosh", "phd", [2021, None], NBK, near="Current PhD Students"),
        M("Nikhil Agarwal", "phd", [2021, None], NBK, near="Current PhD Students"),
        M("Mitchell Fream", "phd", [2022, None], NBK, near="Current PhD Students"),
        M("Sun A Cho", "phd", [2023, None], NBK, near="Current PhD Students"),
        M("Guy Wilks", "phd", [2024, None], NBK, near="Current PhD Students"),
        M("Sara McAllister", "phd", [2019, 2025], NBK, q="Sara McAllister (2019 – 2025) PhD student in Computer Science"),
        M("Brian Schwedock", "phd", [2017, 2023], NBK, q="Brian Schwedock (2017 – 2023) PhD in Electrical and Computer Engineering"),
        M("Graham Gobieski", "phd", [2017, 2022], NBK, q="Graham Gobieski (2017 – 2022) PhD in Computer Science"),
        M("Lucy Wang", "undergraduate", [2024, 2026], NBK, q="Lucy Wang (2024 – 2026) BS in Electrical and Computer Engineering"),
        M("Sophia (Qingyang) Cao", "undergraduate", [2023, 2026], NBK, q="Sophia (Qingyang) Cao (2023 – 2026) BS in Computer Science"),
        M("Jennifer Brana", "phd", [2022, 2025], NBK, q="Jennifer Brana (2023 – 2025) PhD student in Computer Science",
          note="also 'Jennifer Brana (2022 – 2023) BS in University of Portland. After CORGi: PhD at CMU.' (visiting undergrad)"),
        M("Xuesi Chen", "phd", [2022, 2025], NBK, q="Xuesi Chen (2022 – 2025) PhD student in Electrical and Computer Engineering"),
        M("Sherry (Yucong) Wang", "undergraduate", [2022, 2024], NBK,
          q="Sherry (Yucong) Wang (2022 – 2024) BS in Electrical and Computer Engineering"),
        M("Piratach Yoovidhya", "masters", [2021, 2024], NBK, q="Piratach Yoovidhya (2023 – 2024) MS in Computer Science",
          note="also 'Piratach Yoovidhya (2021 – 2022) BS in Computer Science'"),
        M("Zhengfan Zhang", "masters", [2022, 2023], NBK, q="Zhengfan Zhang (2022 – 2023) MS in Electrical and Computer Engineering"),
        M("Akshath Karanam", "masters", [2022, 2023], NBK, q="Akshath Karanam (2022 – 2023) MS in Electrical and Computer Engineering"),
        M("Karthik Ramanathan", "masters", [2022, 2023], NBK, q="Karthik Ramanathan (2022 – 2023) MS in Computer Science"),
        M("Nishanth Subramanian", "masters", [2022, 2023], NBK, q="Nishanth Subramanian (2022 – 2023) MS in Computer Science"),
        M("Elliot Lockerman", "phd", [2017, 2022], NBK, q="Elliot Lockerman (2017 – 2022) PhD student in Computer Science"),
        M("Anirudh Krishna Villivalam", "masters", [2021, 2022], NBK,
          q="Anirudh Krishna Villivalam (2021 – 2022) MS in Electrical and Computer Engineering"),
        M("Carson Molder", "undergraduate", [2020, 2021], NBK,
          q="Carson Molder (2020 – 2021) BS in Computer Science and Computer Engineering, U. Arkansas",
          note="visiting undergraduate (U. Arkansas)"),
        M("Jennifer Seibert", "undergraduate", [2021, 2021], NBK, q="Jennifer Seibert (2021 – 2021) BS in Binghamton University",
          note="visiting undergraduate (Binghamton)"),
        M("Julian Tutuncu-Macias", "undergraduate", [2020, 2021], NBK, q="Julian Tutuncu-Macias (2020 – 2021) BS in Computer Science"),
        M("Ashish Dwivedi", "masters", [2020, 2021], NBK, q="Ashish Dwivedi (2020 – 2021) MS in Electrical and Computer Engineering"),
        M("Ashwin Itagi", "masters", [2019, 2020], NBK, q="Ashwin Itagi (2019 – 2020) MS in Electrical and Computer Engineering"),
        M("Shashwat Gupta", "masters", [2019, 2020], NBK, q="Shashwat Gupta (2019 – 2020) MS in Electrical and Computer Engineering"),
        M("Mohammad Bakhshalipour", "phd", [2019, 2020], NBK,
          q="Mohammad Bakhshalipour (2019 – 2020) PhD student in Electrical and Computer Engineering"),
        M("Axel Feldmann", "undergraduate", [2017, 2019], NBK, q="Axel Feldmann (2017 – 2019) BS in Computer Science"),
        M("Alexandru Stanescu", "undergraduate", [2018, 2019], NBK, q="Alexandru Stanescu (2018 – 2019) BS in Computer Science"),
        M("Amolak Nagi", "masters", [2017, 2019], NBK, q="Amolak Nagi (2017 – 2019) MS in Electrical and Computer Engineering"),
        M("Haoxian Chen", "phd", [2016, 2017], NBK, q="Haoxian Chen (2016 – 2017) PhD student in Computer Science"),
    ],
    pubs=[],
    notes=("CORGi group people page lists current PhD students and dated graduated/former members back to 2016 "
           "(Beckmann joined CMU in 2016). The 'Current Masters and Undergrad Students' heading is followed only by "
           "'Corgis' (the lab dogs Arya, Baphomet, Lilith) - skipped. Pubs: CORGi publications.html puts each title "
           "in an <h3> with authors/venue in the following sibling <p>; no pubx mode (auto/li/block/anchor/css) "
           "parses it (only project links come out), and the homepage has no paper list, so no PUB added."),
    blocked=[],
)

# ---------------------------------------------------------------- Andrew Begel
BV = "https://cmu-variability.github.io/"
BV23 = WB + "20230926160415id_/https://cmu-variability.github.io/"
D["Andrew Begel"] = dict(
    lab_site="https://cmu-variability.github.io/",
    people_page=BV,
    people_pages=[BV, BV23],
    members=[
        M("JiWoong (Joon) Jang", "phd", None, BV, near="PhD Students"),
        M("Gabrielle Ohlson", "phd", None, BV, near="PhD Students", note="Robotics Institute"),
        M("Kaia Newman", "phd", None, BV, near="PhD Students"),
        M("Ren Butler", "phd", None, BV, near="PhD Students"),
        M("Eryn Ma", "phd", None, BV, near="PhD Students"),
        M("Jule Jensen", "visitor", None, BV, near="PhD Students",
          note="listed under PhD Students with affiliation Technical University of Bremen (external PhD student)"),
        M("Reagan Keeney", "visitor", None, BV, near="PhD Students",
          note="listed under PhD Students with affiliation University of Massachusetts at Amherst (external PhD student)"),
        M("Simran Agrawal", "undergraduate", None, BV, near="Undergraduate Students"),
        M("Adrian Zhuang", "undergraduate", None, BV, near="Undergraduate Students"),
        M("Meera Rajendran", "undergraduate", None, BV, near="Undergraduate Students"),
        M("Allison Xia", "undergraduate", None, BV, near="Undergraduate Students"),
        M("Tammy Pham", "undergraduate", None, BV, near="Undergraduate Students", note="listed with Smith College"),
        M("Andrew Hundt", "postdoc", None, BV, near="Postdoc Alumni", note="Robotics Institute"),
        M("Morgan Evans", "phd", None, BV, near="PhD Alumni",
          note="current PhD student (S3D) on the Sept 2023 capture; PhD Alumni on the live page"),
        M("Simon Chu", "masters", None, BV, near="Masters Alumni"),
        M("Wenxin (Wendy) Ju", "masters", None, BV, near="Masters Alumni"),
        M("Alana Rogers", "masters", None, BV, near="Masters Alumni"),
        M("Manvi Gupta", "masters", None, BV, near="Masters Alumni"),
        M("Mingzhe (Vera) Li", "masters", None, BV, near="Masters Alumni"),
        M("Jin Jin Du", "masters", None, BV, near="Masters Alumni"),
        M("Qiaoqiao Ma", "masters", None, BV, near="Masters Alumni"),
        M("Sri Lakshmi Pakhala", "masters", None, BV, near="Masters Alumni"),
        M("Rebecca Jiang", "masters", None, BV, near="Masters Alumni"),
        M("Siyun Wen", "masters", None, BV, near="Masters Alumni"),
        M("Won (Irene) Choi", "masters", None, BV, near="Masters Alumni"),
        M("Aritra Dutta", "masters", None, BV, near="Masters Alumni"),
        M("Mathilda Chen", "masters", None, BV, near="Masters Alumni"),
        M("Apolline Tardy", "masters", None, BV, near="Masters Alumni"),
        M("Justin Zou", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Meixuan (Lucy) Li", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Raymond Welgosh", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Emily Amspoker", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Justin Hsieh", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("An Tang", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Ireoluwa Alarape", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Zhiheng (Andy) Ye", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Dhruva Reddy", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Mahith Edula", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Adam Bournes", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Sidney Ozcan", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Parishi Jain", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Aditya (Adit) Ganesh", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Zimeng (Ayla) Wang", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Gabriel Aguirre", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Kajal Mehta", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Yiqun (Melody) Zhang", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Saanika Chauk", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Erica Fu", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Baramee (Bing) Bhakdibhumi", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Veronica Pimenova", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Sofia Reyes Franco", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Janise Kim", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Meghana Tera", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Joseph Lee", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Wenjun (Connie) Zhou", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Emily Yu", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Chris Lee", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Octavius Tan", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Amanda Zhu", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Michelle Feng", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Yihan (Hanna) Luo", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Jiachen Liu", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Emma Enkhbold", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Alex Zhu", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Hermosa Huang", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Sonya Karnata", "undergraduate", None, BV, near="Undergraduate Student Alumni"),
        M("Christina Trice", "undergraduate", None, BV23, near="Undergraduate Student Alumni",
          note="listed with University of Maryland at College Park on the Sept 2023 capture"),
        M("Juno Bartsch", "undergraduate", None, BV23, near="Undergraduate Student Alumni",
          note="listed with Haverford College on the Sept 2023 capture"),
        M("Yanzi (Veronica) Lin", "undergraduate", None, BV23, near="Undergraduate Student Alumni",
          note="listed with Wellesley College on the Sept 2023 capture"),
    ],
    pubs=[PUB("https://cmu-variability.github.io/bib/pubs.bib", mode="bibtex"),
          PUB("https://andrewbegel.com/cv.html", mode="auto")],
    notes=("Begel joined CMU (S3D, HCII affiliate) in August 2022 from Microsoft Research; the VariAbility Lab site "
           "started Jan 2023, so every listed student/alumnus is from 2022 onward (alumni lists are undated). The Sept "
           "2023 capture already shows Morgan Evans as current PhD, Jin Jin Du/Apolline Tardy as masters and most "
           "undergraduate alumni as current. Jule Jensen, Reagan Keeney, Tammy Pham, Trice, Bartsch and Lin carry "
           "non-CMU affiliations (recorded with notes). Skipped: 'Collaborators'/'Previous Collaborators' (Edison, "
           "Tavares, Annabi, Dow-Burger, Wessel, Redcay, Boyer, Isaacson, Asadi, Mishra, Le Goues, Brun, Endres, "
           "Rodeghero, Naba Rizvi, Mauli Pandey). Pubs: the lab's publications.html is rendered from bib/pubs.bib (added "
           "as bibtex); Begel's CV page lists all papers with bold titles (auto mode; its grants section also "
           "parses as entries, e.g. NSF award titles)."),
    blocked=[],
)

# ---------------------------------------------------------------- Theophilus Benson
TB = "https://www.andrew.cmu.edu/user/theophib/"
TBC = "https://www.csd.cs.cmu.edu/people/faculty/theophilus-benson"
D["Theophilus Benson"] = dict(
    lab_site="https://www.andrew.cmu.edu/user/theophib/",
    people_page=TB,
    people_pages=[TB, TBC],
    members=[
        M("Lucas Castanheira", "phd", None, TB, near="Current Research Group"),
        M("Isabel Suizo", "phd", None, TB, near="Current Research Group", note="co-advised with Justine Sherry"),
        M("Pragna Mamidipaka", "phd", None, TB, near="Current Research Group"),
        M("Semebia Wurah", "staff", None, TB, near="Current Research Group", note="Research Associate"),
        M("Mike Mwanje", "staff", None, TB, near="Current Research Group", note="Research Associate"),
        M("Heran Equbay", "staff", None, TB, near="Current Research Group", note="Research Associate"),
        M("Hamna Shafqat", "phd", None, TBC, near="Advisees", note="CSD profile advisee; not on the homepage group list"),
    ],
    pubs=[PUB("https://www.andrew.cmu.edu/user/theophib/pubs.html", mode="auto")],
    notes=("Benson moved from Brown to CMU ECE / CMU-Africa (~2023); the CSD profile has no website link, the old "
           "Brown page (cs.brown.edu/~tab) points to the CMU homepage www.andrew.cmu.edu/user/theophib/, whose "
           "'Current Research Group' section lists 3 PhD students and 3 research associates. The publications page "
           "(pubs.html) is a copy of the Brown-era list (2016-2019 papers in window); the homepage 'Selected "
           "Publications' are the same older papers and its other entries are grant titles, so only pubs.html added."),
    blocked=[],
)

# ---------------------------------------------------------------- Yonatan Bisk
YB = "https://talkingtorobots.com/CLAW/"
D["Yonatan Bisk"] = dict(
    lab_site="https://talkingtorobots.com/",
    people_page=YB,
    people_pages=[YB],
    members=[
        M("Maithili Patel", "postdoc", None, YB, near="Postdocs"),
        M("Abitha Thankaraj", "phd", None, YB, near="PhD Students"),
        M("Rosa Vitiello", "phd", None, YB, near="PhD Students", note="'Technically Rosanna'"),
        M("Quanting Xie", "phd", None, YB, near="PhD Students"),
        M("Leena Mathur", "phd", None, YB, near="PhD Students", note="co-advised with LP Morency"),
        M("Haochen Zhang", "phd", None, YB, near="PhD Students"),
        M("Annabella Macaluso", "phd", None, YB, near="PhD Students"),
        M("Wenjie Li", "phd", None, YB, s="Wenjie Li", e="Masters, Independent Studies, and Visitors",
          note="in the PhD Students section; that heading is >1500 chars earlier (research blurbs), so the quote runs from the name to the next heading"),
        M("Jacob Thompson", "phd", None, YB, near="Masters, Independent Studies, and Visitors",
          note="in the PhD Students section; that heading is >1500 chars earlier (research blurbs), so the quote runs from the name to the next heading"),
        M("Ani Kimmel", "phd", None, YB, near="Masters, Independent Studies, and Visitors",
          note="in the PhD Students section; that heading is >1500 chars earlier (research blurbs), so the quote runs from the name to the next heading"),
        M("Soumya Teotia", "masters", None, YB, near="Masters, Independent Studies, and Visitors", note="MSR"),
        M("Yingshan Chang", "phd", [None, 2026], YB, q="Yingshan Chang 常影杉 Ph.D. 2026",
          note="also MLT, alumni table year 2022"),
        M("Jared Fernandez", "phd", [None, 2026], YB, q="Jared Fernandez Jared Fernandez Ph.D. 2026",
          note="co-advised with Emma Strubell"),
        M("Vidhi Jain", "phd", [None, 2025], YB, q="Vidhi Jain विधि जैन Ph.D. 2025"),
        M("So Yeon Min", "phd", [None, 2025], YB, q="So Yeon Min 민소연 Ph.D. 2025", note="co-advised with Rus Salakhutdinov"),
        M("Hao Zhu", "phd", [None, 2024], YB, q="Hao Zhu 朱昊 Ph.D. 2024", note="co-advised with Graham Neubig"),
        M("Yash Jangir", "masters", [None, 2026], YB, q="2026 Yash Jangir MSR"),
        M("Claire Jin", "masters", [None, 2026], YB, q="2026 Claire Jin 5th Year MS"),
        M("Sheryl Mathew", "masters", [None, 2024], YB, q="2024 Sheryl Mathew 5th Year MS"),
        M("Mimo Shirasaka", "other", [None, 2026], YB, q="2026 Mimo Shirasaka Intern", note="intern"),
        M("Minyoung Hwang", "other", [None, 2024], YB, q="2024 Minyoung Hwang Intern", note="intern"),
        M("Su Li", "undergraduate", [None, 2024], YB, q="2024 Su Li Undergrad"),
        M("Maria Yampolsky", "undergraduate", [None, 2024], YB, q="2024 Maria Yampolsky Undergrad"),
        M("Jimin Sun", "masters", [None, 2023], YB, q="2023 Jimin Sun MLT"),
        M("Xiang Fan", "undergraduate", [None, 2022], YB, q="2022 Xiang Fan Undergraduate"),
        M("Andy Liu", "other", [None, 2022], YB, q="2022 Andy Liu Intern", note="intern"),
        M("Deogratias Amani", "other", [None, 2022], YB, q="2022 Deogratias Amani Intern", note="intern"),
        M("Josh Zhanson", "masters", [None, 2022], YB, q="2022 Josh Zhanson MLT"),
        M("Xiaoyu (Erin) Zhang", "masters", [None, 2022], YB, q="2022 Xiaoyu (Erin) Zhang 5th year MS"),
        M("Feiyu (Gavin) Zhu", "undergraduate", [None, 2021], YB, q="2021 Feiyu (Gavin) Zhu Undergrad"),
        M("Blessing Bassey", "other", [None, 2021], YB, q="2021 Blessing Bassey Intern", note="intern"),
        M("Melanie Sclar", "other", [None, 2021], YB, q="2021 Melanie Sclar Intern", note="intern"),
    ],
    pubs=[PUB("https://talkingtorobots.com/publications.html", mode="css:.card")],
    notes=("CSD profile has no link; LTI profile links the CLAW Lab site talkingtorobots.com, whose Group page "
           "(/CLAW/) lists postdoc, PhD and MS members plus PhD alumni and an alumni table (year = year they left, "
           "role, next position). Interns recorded as role 'other'. Skipped: the lab cats (Star, Comet). The group "
           "page also carries a text line addressed to AI assistants about drafting messages to Bisk; ignored. "
           "Pubs: publications.html cards (css:.card; the embedded BibTeX gives the same 128 entries)."),
    blocked=[],
)

# ---------------------------------------------------------------- Mor Harchol-Balter
MH = "http://www.cs.cmu.edu/~harchol/"
MH17 = WB + "20170125081402id_/http://www.cs.cmu.edu:80/~harchol/"
MH20 = WB + "20200218104137id_/http://www.cs.cmu.edu:80/~harchol/"
MH23 = WB + "20230113195925id_/http://www.cs.cmu.edu/~harchol/"
D["Mor Harchol-Balter"] = dict(
    lab_site="http://www.cs.cmu.edu/~harchol/",
    people_page=MH,
    people_pages=[MH, MH17, MH20, MH23],
    members=[
        M("Arthur (Zhouzi) Li", "phd", None, MH, near="Current PhD STUDENTS"),
        M("Ben Berg", "phd", [2016, None], MH17, q="Current PhD STUDENTS Ben Berg (1st year)",
          note="1st-year PhD in Jan 2017; current in 2020; graduated by Jan 2023 (now UNC)"),
        M("Kristy Gardner", "phd", [None, 2017], MH17, q="Kristy Gardner (5th and final year)",
          note="same person as held 'Kristen Gardner' (Kristy = Kristen; builder did not match the variant)"),
        M("Ziv Scully", "phd", [2016, None], MH17, q="Ziv Scully (1st year)",
          note="1st-year PhD in Jan 2017; current in 2020; graduated by Jan 2023 (now Cornell)"),
        M("Timothy Zhu", "phd", [None, 2017], MH17, q="Timothy Zhu (6th and final year)"),
        M("Isaac Grosof", "phd", None, MH20, near="Current PhD STUDENTS",
          note="current on 2020 and Jan 2023 captures; graduated on the live page (now Northwestern)"),
        M("Justin Whitehouse", "phd", None, MH20, near="Current PhD STUDENTS",
          note="current PhD student on the Feb 2020 capture only"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~harchol/Papers/papers.html", mode="auto")],
    notes=("No group site; the homepage lists 'Current PhD STUDENTS' and undated 'Graduated PhD STUDENTS'. Used "
           "captures Jan 2017, Feb 2020, Jan 2023 for who was current when. The full-length CV (cv.pdf) has no "
           "advising section. Skipped as graduated before 2016 / not seen current in 2016+: Doroudi (2016 "
           "dissertation award, already graduated in Jan 2017), Gandhi, Varun Gupta, Osogami, McWherter, "
           "Schroeder, Wierman. Pubs: papers.html has unclosed <p> tags, so some entries merge or carry author "
           "lists in the title; auto mode still gives mostly correct titles (19 of 22 in-window matched)."),
    blocked=[],
)

# ---------------------------------------------------------------- Jeffrey Bigham
JB = "https://www.cs.cmu.edu/~big-lab/team.html"
JBH = "http://www.cs.cmu.edu/~jbigham/"
JBCV = "http://www.cs.cmu.edu/~jbigham/cv.pdf"
D["Jeffrey Bigham"] = dict(
    lab_site="https://www.cs.cmu.edu/~big-lab/",
    people_page=JB,
    people_pages=[JB, JBH, JBCV],
    members=[
        M("Chris Maury", "staff", None, JB, q="Chris Maury Special Faculty Researcher"),
        M("Eric Davidson", "staff", None, JB, q="Eric Davidson Administrative Assistant",
          note="HCII administrative assistant supporting the BIG Lab (listed under Current Members)"),
        M("Atieh Taheri", "postdoc", [2024, None], JBCV, q="Atieh Taheri (2024 – present)",
          note="Presidential Postdoctoral Fellow, co-advised with Patrick Carrington"),
        M("Saelyne Yang", "postdoc", [2026, None], JBCV, q="Saelyne Yang (2026 – present)"),
        M("Peya Mowar", "phd", None, JB, q="Peya Mowar Ph.D. student", note="co-advised with Aaron Steinfeld"),
        M("Hamza El Alaoui", "phd", None, JB, q="Hamza El Alaoui Ph.D. student"),
        M("Christine Mendoza", "phd", None, JB, q="Christine Mendoza Ph.D. student", note="co-advised with Anat Caspi (UW)"),
        M("Lirui (Alex) Liu", "undergraduate", None, JB, q="Lirui (Alex) Liu Research Assistant",
          note="research assistant pursuing a B.S. in AI at CMU"),
        M("Yi-Hao Peng", "phd", [None, 2026], JBCV, q="Yi-Hao Peng (Carnegie Mellon University - HCII), 2026"),
        M("Jessica Yin Huynh", "phd", [None, 2026], JBCV, q="Jessica Yin Huynh (Carnegie Mellon University - LTI), 2026"),
        M("Sara Kingsley", "phd", [None, 2025], JBCV, q="Sara Kingsley (Carnegie Mellon University - HCII), 2025"),
        M("Carla Viegas", "phd", [None, 2024], JBCV, q="Carla Viegas (Carnegie Mellon University - LTI), 2024"),
        M("Jason Wu", "phd", [None, 2024], JBCV, q="Jason Wu (Carnegie Mellon University - HCII), 2024"),
        M("Prakhar Gupta", "phd", [None, 2023], JBCV, q="Prakhar Gupta (Carnegie Mellon University - LTI), 2023"),
        M("Kundan Krishna", "phd", [None, 2024], JBCV, q="Kundan Krishna (Carnegie Mellon University - LTI), 2024"),
        M("Stephanie Valencia-Valencia", "phd", [None, 2023], JBCV,
          q="Stephanie Valencia-Valencia (Carnegie Mellon University - HCII), 2023"),
        M("Cole Gleason", "phd", [None, 2021], JBCV, q="Cole Gleason (Carnegie Mellon University - HCII), 2021"),
        M("Anhong Guo", "phd", [None, 2020], JBCV, q="Anhong Guo (Carnegie Mellon University - HCII), 2020"),
        M("Ting-Hao Kenneth Huang", "phd", [None, 2018], JBCV,
          q="Ting-Hao Kenneth Huang (Carnegie Mellon University - LTI), 2018"),
        M("Sujeath Pareddy", "phd", None, JBH, near="PhD Graduates",
          note="homepage PhD Graduates (undated; not in the CV list)"),
        M("Yasmine Kotturi", "postdoc", [2022, 2025], JBCV, q="Yasmine Kotturi (2022 – 2025)"),
        M("Cynthia Bennett", "postdoc", [2019, 2022], JBCV, q="Cynthia Bennett (2019 – 2022)"),
        M("Yang Zhang", "postdoc", [2020, 2021], JBCV, q="Yang Zhang (2020 – 2021)"),
        M("Amy Pavel", "postdoc", [2018, 2021], JBCV, q="Amy Pavel (2018 – 2021)"),
        M("Patrick Carrington", "postdoc", [2017, 2019], JBCV, q="Patrick Carrington (2017 – 2019)"),
        M("Kotaro Hara", "postdoc", [2016, 2017], JBCV, q="Kotaro Hara (2016 – 2017)"),
        M("Luz Rello", "postdoc", [2014, 2016], JBCV, q="Luz Rello (2014 – 2016)",
          note="'Postdoc & Systems Scientist Alumni' on the team page; first position Systems Scientist at CMU"),
        M("Hernisa Kacorri", "postdoc", None, JB, q="Hernisa Kacorri Postdoc Alumni",
          note="undated on team page and homepage; not in the CV's postdoc list"),
        M("Yue Jiang", "visitor", [2024, 2024], JB, q="Yue Jiang Visiting Ph.D. Student Alumni",
          note="bio: visiting Ph.D. student in the BIG Lab in 2024 (Aalto)"),
        M("Yaxin Hu", "visitor", [2023, 2023], JB, q="Yaxin Hu Visiting Ph.D. Student Alumni",
          note="bio: visiting Ph.D. student working with Bigham in 2023 (UW-Madison)"),
        M("Junhan (Judy) Kong", "masters", [None, 2020], JB, q="Junhan (Judy) Kong M.S. and B.S. Alumni",
          note="bio: B.S./M.S. at CMU, graduated 2020"),
        M("Xin Yue (Amanda) Li", "masters", None, JB, q="Xin Yue (Amanda) Li M.S. and B.S. Alumni",
          note="B.S. and M.S. at CMU (thesis WaybackUI); undated"),
        M("Yi-Ting Yeh", "masters", None, JB, q="Yi-Ting Yeh M.S. Alumni", note="MLT; undated"),
        M("Yashesh (Yash) Gaur", "masters", None, JB, q="Yashesh (Yash) Gaur M.S. Alumni", note="MLT; undated"),
        M("Nyah Rene", "undergraduate", [2025, 2025], JB, q="Nyah Rene REU Alumni",
          note="bio: Summer 2025 REU (Emory University)"),
        M("Quentin Romero Lauro", "undergraduate", None, JB, q="Quentin Romero Lauro REU and RA Alumni",
          note="NSF REU then undergraduate RA, worked with Yasmine Kotturi (postdoc 2022-2025)"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~jbigham/cv.pdf", mode="text")],
    notes=("BIG Lab (Beneficial Intelligence Group) team.html lists current members and undated alumni; Bigham's CV "
           "(cv.pdf, 'Students and Postdoctoral Fellows') gives dated postdocs and PhD graduates; the homepage "
           "People section adds Sujeath Pareddy and undergrad alumni. Skipped: University of Rochester PhDs Erin "
           "Brady and Yu Zhong (2015) and Rochester undergrad Mitchell Gordon; visiting faculty Saiph Savage "
           "(faculty); homepage undergrad alumni Sam White and Kyle Murray (undated, not placed at CMU in "
           "2016+); PhD committee memberships. Pubs: the homepage list is rendered from pubs/pubs.json, which is a "
           "JavaScript literal ('var reflist=[{citationKey:...}]'), not JSON, so pubx json mode returns nothing; "
           "references.bib is on Dropbox; used the CV PDF in text mode (~95 entries, some titles truncated at "
           "quotes)."),
    blocked=[],
)
