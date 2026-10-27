from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Vipul Goyal
VG = "https://vipulgoyal.org/"
D["Vipul Goyal"] = dict(
    lab_site=VG,
    people_page=VG,
    people_pages=[VG],
    members=[
        M("Alper Cakan", "phd", [None, None], VG, near="PhD Students", note="listed 'Current PhD student'"),
        M("Justin Raizes", "phd", None, VG, near="PhD Students", note="'Now a postdoc at NTT Research'; undated"),
        M("Elisa Masserova", "phd", None, VG, near="PhD Students", note="co-advised with Bryan Parno; now a postdoc at CMU"),
        M("Yifan Song", "phd", None, VG, near="PhD Students", note="now Assistant Professor at Tsinghua"),
        M("Yibin Yang", "postdoc", [2025, None], VG, near="Postdocs", note="August 2025 - Present"),
        M("Amit Behera", "postdoc", [2025, None], VG, near="Postdocs", note="August 2025 - Present"),
        M("Xiao Liang", "postdoc", [2023, 2024], VG, near="Postdocs", note="Feb 2023 - March 2024"),
        M("Naresh Boddu", "postdoc", [2023, 2024], VG, near="Postdocs", note="March 2023 - Oct 2024"),
        M("Chen-Da Liu Zhang", "postdoc", [2021, 2023], VG, near="Postdocs", note="July 2021 - June 2023"),
        M("Joao Ribeiro", "postdoc", [2021, 2023], VG, near="Postdocs", note="August 2021 - Feb 2023"),
        M("Pratik Soni", "postdoc", [2020, 2022], VG, near="Postdocs", note="Oct 2020 - June 2022"),
        M("Giulio Malavolta", "postdoc", [2019, 2020], VG, near="Postdocs", note="Feb 2019 - Aug 2020"),
        M("Nils Fleischhacker", "postdoc", [2017, 2018], VG, near="Postdocs", note="Feb 2017 - May 2018"),
        M("Hanjun Li", "staff", [2020, 2020], VG, near="Full time Research Assistants", note="Jan 2020 - July 2020; also in the CMU masters/undergrad list"),
        M("Anirudh Baddepudi", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU", note="listed with no dates (page text 'Anirudh Baddepudi Sai')"),
        M("Rebecca Stevens", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU", note="name boundary ambiguous in page text; undated"),
        M("Xiaoqi Duan", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU"),
        M("Florian Breuer", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU"),
        M("Mingjia Huo", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU"),
        M("Chenzhi Zhu", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU"),
        M("Kartik Chitturi", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU"),
        M("George Lu", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU"),
        M("Yanyi Liu", "member", None, VG, near="Masters/Undergrad Students/Interns at CMU"),
    ],
    pubs=[PUB(VG + "publications.html", mode="auto")],
    notes="PI homepage vipulgoyal.org (cs.cmu.edu/~goyal redirects there). Goyal is NTT Research senior scientist and CMU adjunct "
          "(associate professor 2017-2022, on leave 2020-2022), so some postdocs/interns 2023-2025 may have been at NTT Research rather than "
          "CMU; recorded as listed. Skipped: summer interns at NTT Research (Aditya Gulati, Saachi Mutreja, Kabir Tomer, Bhaskar Roberts, "
          "Jiahui Liu, Jesse Goodman, Mingyuan Wang, Erica Blum; Hao Chung is a CMU PhD of another PI), visiting scientists (external), and "
          "Microsoft Research India fellows/interns (previous institution). Wayback was in shared back-off, not needed. "
          "'Chen Xiwen' in the masters/undergrad list skipped (name boundary unclear).",
    blocked=[],
)

# ---------------------------------------------------------------- Albert Gu
GG = "https://goombalab.github.io/"
D["Albert Gu"] = dict(
    lab_site=GG,
    people_page=GG,
    people_pages=[GG],
    members=[
        M("Kevin Li", "phd", None, GG, near="ph.d. students"),
        M("Aakash Lahoti", "phd", None, GG, near="ph.d. students"),
        M("Sukjun Hwang", "phd", None, GG, near="ph.d. students"),
        M("Aviv Bick", "phd", None, GG, near="ph.d. students"),
        M("Isaac Liao", "phd", None, GG, near="ph.d. students"),
        M("Abi Kothapalli", "phd", None, GG, near="ph.d. students"),
        M("Ricardo Buitrago", "masters", None, GG, near="affiliated m.s. students"),
    ],
    pubs=[],
    notes="Goomba Lab people page (goombalab.github.io) lists 6 PhD students and 1 affiliated MS student, no alumni. Wayback captures of the site "
          "(2024-06, 2025-01, 2026-01) could not be read: archive.org was in shared back-off (wayback-backoff). No publications page on the site "
          "(only blog/repositories); PI has no separate publications page found.",
    blocked=[],
)

# ---------------------------------------------------------------- Abhinav Gupta
AGH = "http://www.cs.cmu.edu/~abhinavg/"
AG17 = WB + "20170101222750id_/http://www.cs.cmu.edu/~abhinavg/"
AG20 = WB + "20200111012934id_/http://www.cs.cmu.edu:80/~abhinavg/"
D["Abhinav Gupta"] = dict(
    lab_site=AGH,
    people_page=AGH,
    people_pages=[AGH, AG17, AG20],
    members=[
        M("Unnat Jain", "postdoc", [None, None], AGH, near="Postdocs and Students"),
        M("Aravind Rajeswaran", "member", None, AGH, near="Postdocs and Students", note="listed with no role under Postdocs and Students"),
        M("Sudeep Dasari", "phd", None, AGH, near="Postdocs and Students"),
        M("Shikhar Bahl", "phd", None, AGH, near="Postdocs and Students"),
        M("Yufei Ye", "phd", None, AGH, near="Postdocs and Students"),
        M("Raunaq Bhirangi", "phd", None, AGH, near="Postdocs and Students"),
        M("Homanga Bharadwaj", "phd", None, AGH, near="Postdocs and Students"),
        M("David Fouhey", "phd", [None, 2016], AGH, near="Former PhD Students"),
        M("Carl Doersch", "phd", [None, 2016], AGH, near="Former PhD Students"),
        M("Abhinav Shrivastava", "phd", [None, 2017], AGH, near="Former PhD Students"),
        M("Xinlei Chen", "phd", [None, 2018], AGH, near="Former PhD Students"),
        M("Jacob Walker", "phd", [None, 2018], AGH, near="Former PhD Students"),
        M("Ishan Misra", "phd", [None, 2018], AGH, near="Former PhD Students"),
        M("Xiaolong Wang", "phd", [None, 2019], AGH, near="Former PhD Students"),
        M("Lerrel Pinto", "phd", [None, 2019], AGH, near="Former PhD Students"),
        M("Gunnar Sigurdsson", "phd", [None, 2020], AGH, near="Former PhD Students"),
        M("Kenneth Marino", "phd", [None, 2020], AGH, near="Former PhD Students"),
        M("Adithya Murali", "phd", [None, 2020], AGH, near="Former PhD Students"),
        M("Senthil Purushwalkam", "phd", [None, 2021], AGH, near="Former PhD Students"),
        M("Victoria Dean", "phd", [None, 2023], AGH, near="Former PhD Students"),
        M("Samantha Powers", "phd", [None, 2023], AGH, near="Former PhD Students"),
        M("Dhiraj Gandhi", "masters", None, AGH, near="Former MS Students"),
        M("Tian Ye", "masters", None, AGH, near="Former MS Students"),
        M("Nilesh Kulkarni", "masters", None, AGH, near="Former MS Students"),
        M("Tao Chen", "masters", None, AGH, near="Former MS Students"),
        M("Wenxuan Zhou", "masters", None, AGH, near="Former MS Students"),
        M("Nadine Chang", "masters", None, AGH, near="Former MS Students"),
        M("Simone Parisi", "other", None, AGH, near="Former Research Fellows/Members", note="former research fellow/member, undated"),
        M("Tess Hellebrekers", "other", None, AGH, near="Former Research Fellows/Members", note="former research fellow/member, undated"),
        M("Olga Russakovsky", "postdoc", [None, None], AG17, near="Postdocs and Students", note="postdoc co-advised with Deva Ramanan in the 2017-01 capture"),
        M("Tanmay Batra", "masters", None, AG17, near="Postdocs and Students", note="Robotics MS in the 2017-01 capture"),
        M("Jacob Huh", "phd", None, AG20, near="Postdocs and Students", note="Robotics PhD in the 2020-01 capture"),
        M("Gaurav Pathak", "visitor", None, AG20, near="Visitors", note="visitor in the 2020-01 capture"),
        M("Pratyusha Sharma", "visitor", None, AG20, near="Visitors", note="visitor in the 2020-01 capture"),
    ],
    pubs=[PUB(AGH + "publications.html", mode="auto")],
    notes="Homepage cs.cmu.edu/~abhinavg is the live source (last updated ~2023: 'Back full-time at CMU starting May 2022'); no separate lab site. "
          "Used Wayback 2017-01 and 2020-01 captures for people who left before the current list. Skipped: Yin Li, Saurabh Gupta, Shubham Tulsiani, "
          "Pedro Morgado (undated former fellows), Rohit Girdhar, Aayush Bansal, Saurabh Singh, Aravindh Mahendran, Tomasz Malisiewicz "
          "(former MS/collaborators, undated and likely pre-2016); PhD students listed on 2017/2020 captures are all already covered by the Former PhD list. "
          "Publications page is a 2017-era list (53 entries, all matched to held papers). No 2023 capture read (back-off).",
    blocked=[],
)

# ---------------------------------------------------------------- Anupam Gupta
ANY = "https://cs.nyu.edu/~anupamg"
D["Anupam Gupta"] = dict(
    lab_site=ANY,
    people_page=ANY,
    people_pages=[ANY],
    members=[
        M("David Witmer", "phd", [None, 2017], ANY, near="Graduated Ph.D. Students"),
        M("Sahil Singla", "phd", [None, 2018], ANY, near="Graduated Ph.D. Students"),
        M("Guru Guruganesh", "phd", [None, 2018], ANY, near="Graduated Ph.D. Students"),
        M("Jason Li", "phd", [None, 2021], ANY, near="Graduated Ph.D. Students"),
        M("C.J. Argue", "phd", [None, 2022], ANY, near="Graduated Ph.D. Students"),
        M("Roie Levin", "phd", [None, 2022], ANY, near="Graduated Ph.D. Students"),
    ],
    pubs=[PUB("https://cs.nyu.edu/~anupamg/publicat.html", mode="auto")],
    notes="PI is now Silver Professor at NYU (adjunct at CMU); cs.cmu.edu/~anupamg just redirects to cs.nyu.edu/~anupamg. Only graduated PhDs with year >= 2016 "
          "recorded (Ankit Sharma 2014 and earlier excluded). Current NYU postdocs/students (Romain Cosson, Madhusudhan Reddy Pittu, Sherry Sarkar, Zhaozi Wang) "
          "are not placed at CMU by the page and were skipped; past postdocs (Melanie Schmidt, Ilan Reuven Cohen, Danny Segev) undated. "
          "CMU theory-group faculty listed as collaborators were ignored. Wayback only holds NYU captures (2024+), not useful.",
    blocked=[],
)

# ---------------------------------------------------------------- Venkatesan Guruswami
VB = "https://people.eecs.berkeley.edu/~venkatg"
D["Venkatesan Guruswami"] = dict(
    lab_site=VB,
    people_page=VB,
    people_pages=[VB],
    members=[
        M("Ameya Velingker", "phd", [None, 2016], VB, near="Graduated Ph.D."),
        M("Euiwoong Lee", "phd", [None, 2017], VB, near="Graduated Ph.D."),
        M("Vijay Bhattiprolu", "phd", [None, 2019], VB, near="Graduated Ph.D."),
        M("Nicolas Resch", "phd", [None, 2020], VB, near="Graduated Ph.D."),
        M("Andrii Riazanov", "phd", [None, 2022], VB, near="Graduated Ph.D.", note="PhD 2022; PI moved to Berkeley Jan 2022"),
        M("Sai Sandeep", "phd", [None, 2022], VB, near="Graduated Ph.D.", note="PhD 2022; also Berkeley postdoc Sep 2022-May 2023"),
        M("Jonathan Mosheiff", "postdoc", [2019, 2022], VB, near="Former postdocs", note="Oct 2019 - Mar 2022"),
        M("Joao Ribeiro", "postdoc", [2021, 2023], VB, near="Former postdocs", note="Aug 2021 - Jan 2023 (CMU until PI's move in Jan 2022)"),
        M("Ankit Singh Rawat", "postdoc", [2015, 2016], VB, near="Former postdocs", note="Sep 2015 - Aug 2016"),
        M("Mary Wootters", "postdoc", [2014, 2016], VB, near="Former postdocs", note="Sept 2014 - July 2016"),
        M("Ray Li", "undergraduate", [None, 2017], VB, near="Undergraduate/M.S:", note="honors thesis 2017"),
        M("Joshua Brakensiek", "undergraduate", [None, 2018], VB, near="Undergraduate/M.S:", note="2018 CRA Outstanding Undergraduate Researcher award"),
    ],
    pubs=[PUB(VB + "/pubs/venkat-papers.html", mode="auto")],
    notes="PI moved to UC Berkeley (Simons Institute) Jan 2022 after 13+ years at CMU; cs.cmu.edu/~venkatg redirects to the Berkeley page. Recorded only CMU-era people "
          "(PhDs 2016-2022, postdocs overlapping 2016-2021, undergrads with dated CMU work). Skipped: Berkeley-era current advisees and postdocs, PhDs Peter Manohar (2024) and "
          "Pranav Trivedi (2026) whose degree institution the page does not state, Hsin-Po Wang, Ray Li as postdoc (Berkeley), undated undergrad/MS list (Rohit Agarwal, Omar Alrabiah, "
          "Runzhou Tao, Santhoshini Velusamy, Zhen Zhou, Patrick Lin), pre-2016 PhDs.",
    blocked=[],
)

# ---------------------------------------------------------------- Bernhard Haeupler
BH = "https://people.inf.ethz.ch/haeuplb/"
D["Bernhard Haeupler"] = dict(
    lab_site=BH,
    people_page=BH,
    people_pages=[BH],
    members=[
        M("D. Ellis Hershkowitz", "phd", [None, 2022], BH, near="Ph.D. Students"),
        M("Jason Li", "phd", [None, 2021], BH, near="Ph.D. Students"),
        M("Amirbehshad Shahrasbi", "phd", [None, 2020], BH, near="Ph.D. Students"),
        M("David Wajc", "phd", [None, 2020], BH, near="Ph.D. Students"),
        M("Goran Zuzic", "phd", [None, 2020], BH, near="Ph.D. Students"),
        M("Nicolas Resch", "phd", [None, 2019], BH, near="Ph.D. Students"),
    ],
    pubs=[PUB(BH, mode="bibtex")],
    notes="cs.cmu.edu/~haeupler redirects to the ETH/INSAIT homepage (PI at CMU 2014-2022 full-time, adjunct to 2024). Page lists his PhD students with CMU PhD years; "
          "current ETH/INSAIT students (Richard Hladik, Antti Roeyskoe) excluded. Publications come from embedded BibTeX (mode=bibtex, 138 entries). "
          "Old CMU-era group pages were not read (Wayback in back-off).",
    blocked=[],
)

# ---------------------------------------------------------------- Jessica Hammer
JH = "https://hcii.cmu.edu/people/jessica-hammer"
CTP = "https://www.cmu.edu/ctp/people"
D["Jessica Hammer"] = dict(
    lab_site="http://replayable.net/",
    people_page=JH,
    people_pages=[JH],
    members=[
        M("Rotem Guttman", "phd", None, JH, near="Advisees"),
        M("Beatrice (Bea) Maggipinto", "phd", None, JH, near="Advisees"),
        M("Bria Massey", "phd", None, JH, near="Advisees"),
    ],
    pubs=[PUB("http://replayable.net/publications/", mode="auto")],
    notes="PI site replayable.net has no members page (research, publications, CTP, work-with-me, about-my-lab only). Members come from the HCII faculty profile 'Advisees'. "
          "She directs the Center for Transformational Play (cmu.edu/ctp/people): its PhD students (Bea Maggipinto, Noor Hammad, Rotem Guttman, Bria Massey) and alumni "
          "(Jaemarie Solyst, Erica Cruz, Morgan Evans) are center-wide 'in conjunction with the CTP', not stated as Hammer's own advisees, so only the HCII advisees were recorded "
          "(Noor Hammad is Erik Harpstead's advisee). Publications page lists only ~7 selected papers. Wayback captures of replayable.net (2017-2023) could not be read at first because of the shared back-off.",
    blocked=[],
)

# ---------------------------------------------------------------- Robert Harper
RH = "http://www.cs.cmu.edu/~rwh/"
RHS = "http://www.cs.cmu.edu/~rwh/students.html"
D["Robert Harper"] = dict(
    lab_site=RH,
    people_page=RHS,
    people_pages=[RH, RHS],
    members=[
        M("Harrison Grodin", "phd", None, RH, near="Students"),
        M("Runming Li", "phd", None, RH, near="Students"),
        M("Andrew Zhou", "member", None, RH, near="Students", note="listed under Students with a project on the parallel prefix sum (likely MS/undergraduate)"),
        M("Lukas Kebuladze", "member", None, RH, near="Students", note="listed under Students with a splay-tree project (likely MS/undergraduate)"),
        M("Yue Niu", "phd", [None, 2024], RHS, near="Former PhD Students", note="Ph.D. September 2024"),
        M("Jonathan Sterling", "phd", [None, 2021], RHS, near="Former PhD Students", note="Ph.D. October 2021"),
        M("Evan Cavallo", "phd", [None, 2021], RHS, near="Former PhD Students", note="M.Sc. December 2015, Ph.D. February 2021"),
        M("Carlo Angiuli", "phd", [None, 2019], RHS, near="Former PhD Students", note="Ph.D. September 2019"),
        M("Joseph Tassarotti", "phd", [None, 2019], RHS, near="Former PhD Students", note="Ph.D. January 2019, co-advised with Derek Dreyer"),
        M("Kuen-Bang Hou", "phd", [None, 2017], RHS, near="Former PhD Students", note="Favonia; Ph.D. February 2017"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~rwh/papers.html", mode="auto")],
    notes="PI homepage cs.cmu.edu/~rwh plus its students.html (current students on the homepage, former PhDs on students.html). Skipped: PhD students before 2016 "
          "(Licata 2011, Acar, Cheng, etc.), 'Member of PhD Thesis Committee' list (other advisors' students: Jaitin Arora, Henry DeYoung, Stefan Muller, Cyrus Omar...), "
          "collaborators (Balzer, Crary, Hoffmann; other faculty). Papers page has many undated older entries (55 of 77 without year).",
    blocked=[],
)

# ---------------------------------------------------------------- Erik Harpstead
EH = "https://hcii.cmu.edu/people/erik-harpstead"
D["Erik Harpstead"] = dict(
    lab_site="https://www.erikharpstead.net/",
    people_page=EH,
    people_pages=[EH],
    members=[
        M("Noor Hammad", "phd", None, EH, near="Advisees"),
    ],
    pubs=[],
    notes="erikharpstead.net lists projects, CV and links only (no people or publications list; project pages have no parseable paper lists; full list is on Google Scholar/ORCID). "
          "HCII profile 'Advisees' gives Noor Hammad. He is also affiliated faculty of the Center for Transformational Play (cmu.edu/ctp/people), whose student list is center-wide and not attributed to him. "
          "edugames.design is a course site (not read).",
    blocked=[],
)

# ---------------------------------------------------------------- Christina Harrington
CH = "https://www.hcii.cmu.edu/people/christina-harrington"
D["Christina Harrington"] = dict(
    lab_site="https://www.christinaharrington.me/",
    people_page=CH,
    people_pages=[CH],
    members=[
        M("Adinawa Adjagbodjou", "phd", None, CH, near="Advisees"),
        M("Sanika Moharana", "phd", None, CH, near="Advisees"),
    ],
    pubs=[PUB(WB + "20240415142656id_/https://www.christinaharrington.me/publications", mode="auto")],
    notes="Personal site christinaharrington.me is robots-disallowed live (a 2025-01 Wayback copy of the home page has no member list; Equity and Health Innovations Design Research Lab has no separate "
          "site found). Members from the HCII profile 'Advisees'. Her previous-institution (DePaul) lab team page was not used. Publications page is a 2024-04 Wayback copy; titles parse "
          "imperfectly (some entries show author lines), 23 in-window entries.",
    blocked=["https://www.christinaharrington.me/ (robots-disallowed)"],
)

# ---------------------------------------------------------------- Chris Harrison
FG = "https://www.figlab.com/team"
FG22 = WB + "20220503153944id_/https://www.figlab.com/team"
D["Chris Harrison"] = dict(
    lab_site="https://www.figlab.com/",
    people_page=FG,
    people_pages=[FG, FG22],
    members=[
        M("Nathan DeVrio", "phd", None, FG, near="Nathan DeVrio"),
        M("Daehwa Kim", "phd", None, FG, near="Daehwa Kim"),
        M("Vimal Mollyn", "phd", None, FG, near="Vimal Mollyn"),
        M("Taejun Kim", "visitor", None, FG, near="Taejun Kim"),
        M("Vivian Shen", "phd", None, FG22, near="Vivian Shen", note="second-year Robotics PhD student in the 2022-05 capture; PhD alumna on the live page"),
        M("Karan Ahuja", "phd", None, FG22, near="Karan Ahuja", note="HCII PhD student in the 2022-05 capture; alumnus now at Northwestern on the live page"),
        M("Nathan Riopelle", "phd", None, FG22, near="Nathan Riopelle", note="same person as live-page Nathan DeVrio (name change)"),
        M("Andy Kong", "undergraduate", None, FG22, near="Andy Kong", note="fourth-year undergraduate in the 2022-05 capture"),
        M("Yang Zhang", "phd", None, FG, near="Ph.D. Alumni", note="PhD alumnus, now faculty at UCLA; undated on page"),
        M("Gierad Laput", "phd", None, FG, near="Ph.D. Alumni", note="PhD alumnus, now at Apple; undated on page"),
        M("Craig Shultz", "postdoc", None, FG22, near="Craig Shultz", note="post-doctoral researcher in the 2022-05 capture; alumnus now at UIUC on the live page"),
        M("Sven Mayer", "postdoc", None, FG, near="Postdoc Alumni", note="postdoc alumnus, now faculty at TU Dortmund; undated on page"),
    ],
    pubs=[],
    notes="Future Interfaces Group site figlab.com (team page). Alumni are undated; PhD/postdoc alumni recorded because their 'now faculty/at Apple' status places their CMU time after "
          "~2016 (Robert Xiao, PhD alumnus listed with UBC, skipped as possibly pre-2016). The ~40 undated 'Undergrad, Masters, Mentees, and Other Alumni' names were NOT recorded "
          "(no dates; only the 2022-05 Wayback capture was readable: the 2018 capture is a JS shell and later captures hit archive.org back-off; the 2022 capture lists the same alumni without dates; 'Master Alumni' John Horstman, Zhiquan Yeo, Ketaki Rao, Anuraag Jain, Gregory Lew are among them). Research page lists papers as project cards, no parseable publication list; no publications page added. "
          "Chris Harrison's own homepage (chrisharrison.net) not used.",
    blocked=[],
)

# ---------------------------------------------------------------- Alex Hauptmann
AHS = WB + "20200126195700id_/http://lastchance.inf.cs.cmu.edu:80/alex/students.html"
D["Alex Hauptmann"] = dict(
    lab_site="https://www.cs.cmu.edu/~alex/",
    people_page=AHS,
    people_pages=[AHS],
    members=[
        M("Shoou-I Yu", "phd", None, AHS, near="Current Students", note="'CMU, since 2010' on a stale page (2020 capture); PhD thesis ~2016"),
        M("Arnold Overwijk", "phd", None, AHS, near="Current Students", note="'CMU, since 2009' on a stale page (2020 capture); likely graduated before 2016"),
    ],
    pubs=[],
    notes="Homepage www.cs.cmu.edu/~alex/ (LTI research professor) has no people list; it links a students page on lastchance.inf.cs.cmu.edu that is dead live (connect timeout), "
          "so the only readable copy is a 2020 Wayback capture which is a stale page (current students 'since 2009/2010', advisees/thesis-committee names all pre-2012). Recorded the two "
          "'Current Students' per the 2016+ capture rule; both may predate the window. Other captures (2016-2019) could not be read when archive.org began refusing connections. "
          "Publications: only Google Scholar (off limits) and the old lastchance pubs page (dead; Wayback copy is 2008), so none added. Informedia project site does not resolve.",
    blocked=[],
)
