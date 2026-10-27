from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Hirokazu Shirado
HS = "https://www.hcii.cmu.edu/people/hirokazu-shirado"
D["Hirokazu Shirado"] = dict(
    lab_site="https://www.shirado.net/",
    people_page=HS,
    people_pages=[HS],
    members=[
        M("Yuxuan Li", "phd", None, HS, near="Advisees"),
        M("Faria Huq", "phd", None, HS, near="Advisees"),
        M("Tinn Kukamjad", "phd", None, HS, near="Advisees"),
    ],
    pubs=[PUB("https://www.shirado.net/publications/", mode="auto")],
    notes="shirado.net is a personal WordPress site (Home, Research, Publications, Bio, CV, Contact) with no people/members page; Wayback captures of the homepage from 2021 and 2023 also list no group members. The only member list is the HCII profile Advisees section (3 people, all already held). Shirado joined CMU Aug 2019 (Yale PhD 2019), so no earlier-institution students. Publications page parses 33 entries with 4 missing from lab papers (anchor mode).",
    blocked=[],
)

# ---------------------------------------------------------------- Daniel Siewiorek
DS = "https://www.cs.cmu.edu/~dps/"
D["Daniel Siewiorek"] = dict(
    lab_site=DS,
    people_page=DS,
    people_pages=[DS],
    members=[
        M("Scott Fisk", "phd", [2017, None], DS, near="Current Graduate Students"),
        M("Brian French", "phd", [2017, None], DS, near="Current Graduate Students"),
        M("Kevin Huang", "phd", [2017, None], DS, near="Current Graduate Students"),
        M("John Kelly", "phd", [2017, None], DS, near="Current Graduate Students"),
    ],
    pubs=[],
    notes="Personal page cs.cmu.edu/~dps is live but last updated 24 Feb 2017 and lists four current graduate students (Fisk, French, Huang, Kelly) with no publications list or alumni list; years recorded as joined-by-2017 because the list is dated. HCII profile (hcii.cmu.edu/people/daniel-siewiorek) has no advisees section, only related QoLT projects. Siewiorek is Emeritus now. Wayback CDX was refused (connection refused) so no older/newer captures of ~dps could be read; the csd.cs.cmu.edu faculty profile in the input row 404s. No publications page exists on the site.",
    blocked=[],
)

# ---------------------------------------------------------------- Max Simchowitz
RIMS = "https://www.ri.cmu.edu/ri-people/max-simchowitz/"
D["Max Simchowitz"] = dict(
    lab_site="https://msimchowitz.github.io/",
    people_page=RIMS,
    people_pages=[RIMS],
    members=[
        M("Giridharan Anantharaman", "phd", None, RIMS, near="current phd students"),
        M("Sarvesh Patil", "phd", None, RIMS, near="current phd students"),
        M("Sankalp Agrawal", "masters", None, RIMS, near="current masters students"),
        M("Partha Kaushik", "masters", None, RIMS, near="current masters students"),
        M("Andrew Magnuson", "masters", None, RIMS, near="current masters students"),
        M("Sreyas Venkataraman", "masters", None, RIMS, near="current masters students"),
        M("Edmond Wang", "masters", None, RIMS, near="current masters students"),
        M("Angchen Xie", "masters", None, RIMS, near="current masters students"),
        M("Yidi Zhang", "masters", None, RIMS, near="current masters students"),
    ],
    pubs=[],
    notes="Personal Jekyll site msimchowitz.github.io has a People page that only says 'Coming soon!'. The RI profile (ri.cmu.edu/ri-people/max-simchowitz) lists 2 current PhD and 7 current masters students (all already held); used that. Simchowitz joined CMU in 2023 (Berkeley PhD 2021, MIT postdoc) so only CMU-placed members count. The site's other people links (locomotion.csail.mit.edu = Tedrake, MIT) are not his lab. Publications page lists papers as title / author-line / venue paragraphs in a Jekyll layout; none of auto/li/block/text/css modes gave correct titles (junk like 'Outstanding Paper Award', 'NeurIPS , 2025'), so no pubs page was added. Wayback not used (no alumni exist; joined 2023).",
    blocked=[],
)

# ---------------------------------------------------------------- Reid Simmons
RS = "https://www.cs.cmu.edu/~reids/students.html"
RV = "https://www.cs.cmu.edu/~reids/visitors.html"
RF = "https://www.cs.cmu.edu/~reids/staff.html"
RR = "https://www.ri.cmu.edu/robotics-groups/reliable-autonomous-systems-lab/"
D["Reid Simmons"] = dict(
    lab_site="https://www.cs.cmu.edu/~reids/",
    people_page=RS,
    people_pages=[RS, RV, RF, RR],
    members=[
        M("Roykrong Sukkerd", "phd", None, RS, near="Current PhD Students", note="co-advised with David Garlan"),
        M("Mike Lee", "phd", None, RS, near="Current PhD Students", note="co-advised with Henny Admoni"),
        M("Pallavi Koppol", "phd", None, RS, near="Current PhD Students", note="co-advised with Henny Admoni"),
        M("Roshni Kaushik", "phd", None, RS, near="Current PhD Students"),
        M("Michelle Zhao", "phd", None, RS, near="Current PhD Students", note="co-advised with Henny Admoni"),
        M("Arnav Mahajan", "masters", None, RS, near="Masters Students"),
        M("Daphne Chen", "masters", None, RS, near="Masters Students"),
        M("Breelyn Kane Styler", "phd", [None, 2018], RS, near="Past PhD Students", note="thesis May 2018"),
        M("Juan Pablo Mendoza", "phd", [None, 2017], RS, near="Past PhD Students", note="thesis April 2017; co-advised with Manuela Veloso"),
        M("Heather Knight", "phd", [None, 2016], RS, near="Past PhD Students", note="thesis August 2016"),
        M("Robert Fisher", "phd", [None, 2016], RS, near="Past PhD Students", note="thesis May 2016; Machine Learning"),
        M("Brad Saund", "masters", [None, 2017], RS, near="Past Masters Students"),
        M("Shiyuan Chen", "masters", [None, 2017], RS, near="Past Masters Students"),
        M("Allison Funkhouser", "masters", [None, 2016], RS, near="Past Masters Students"),
        M("Moshik Mash", "postdoc", None, RV, near="Current Postdocs", note="with Stephanie Rosenthal"),
        M("Tesca Fitzgerald", "postdoc", [2019, None], RV, near="Current Postdocs", note="starting Fall 2019; with Henny Admoni and Aaron Steinfeld"),
        M("Greg Armstrong", "staff", None, RF, near="Current Staff", note="robot maintainer and manager of the Robot Education Lab"),
        M("Patrick Callaghan", "phd", None, RR, near="current student"),
        M("Gavin Zhu", "phd", None, RR, near="current student"),
        M("Michaela Tecson", "member", None, RR, near="past members"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~reids/bibliography.html", mode="auto")],
    notes="Live personal site cs.cmu.edu/~reids has Students (last modified 4 Mar 2022), Visitors (postdocs) and Staff pages, plus the RI lab page (Reliable Autonomous Systems Lab) listing current student/past members. Recorded 2016+ entries only: past PhD with 2016-2018 dates, past masters 2016-2017, current students/postdocs/staff. Skipped undated alumni: Eleanor Avrunin (listed only as 'was investigating'; already held), David Hershberger and Visitors list entries without dates (about 10 undated past postdocs/visitors e.g. Tom Kollar, Dani Goldberg) plus about 25 pre-2016 entries. Bibliography page parses with anchor mode (193 entries, 35 in window, 5 missing). Wayback captures of students.html were not read (Wayback in shared back-off at the time).",
    blocked=[],
)

# ---------------------------------------------------------------- Aarti Singh
AS = "http://www.cs.cmu.edu/~aarti/group.html"
D["Aarti Singh"] = dict(
    lab_site="http://www.cs.cmu.edu/~aarti/",
    people_page=AS,
    people_pages=[AS],
    members=[
        M("Yuda Song", "phd", None, AS, near="PhD students:", note="co-advised with Drew Bagnell"),
        M("Jennifer Hsia", "phd", None, AS, near="PhD students:", note="co-advised with Zack Lipton"),
        M("Zixin Wen", "phd", None, AS, near="PhD students:", note="co-advised with Yuejie Chi"),
        M("Kanad Pardeshi", "phd", None, AS, near="PhD students:", note="co-advised with Bryan Wilder"),
        M("Nuoya Xiong", "phd", None, AS, near="PhD students:"),
        M("Grace Liu", "phd", None, AS, near="PhD students:"),
        M("Samsara Foubert", "phd", None, AS, near="PhD students:", note="co-advised with Hoda Heidari"),
        M("Jianyu Xu", "postdoc", None, AS, near="Postdoc:"),
        M("Smriti Jha", "masters", None, AS, near="Masters students:"),
    ],
    pubs=[],
    notes="Live group page cs.cmu.edu/~aarti/group.html lists current PhD students, postdoc, masters and an ALUMNI section (PhD, postdocs, research associates, about 22 MS and 6 undergrad entries) whose entries give only current employer/next step and no CMU dates, so all undated alumni are skipped by rule (about 45 names, many already held). Wayback captures of group.html exist for 2017, 2020, 2023 but archive.org was in shared back-off when fetched, so none could be read. The pubs page (pubs.html) is a flat HTML list of 'title (ArXiv) <br> authors <br> venue' entries without per-entry tags: anchor mode gives 4 junk entries, block/li give 0-2, text mode returns URLs, so no pubs page was added.",
    blocked=[],
)

# ---------------------------------------------------------------- Rita Singh
D["Rita Singh"] = dict(
    lab_site="https://cmu-mlsp.github.io/",
    people_page="https://cmu-mlsp.github.io/team/",
    people_pages=[],
    members=[],
    pubs=[PUB("https://cmu-mlsp.github.io/publications", mode="auto")],
    notes="No personal lab site found: LTI profile (lti.cmu.edu/people/faculty/singh-rita.html) lists no students or links; www.cs.cmu.edu/~rsingh/ is a JavaScript redirect stub ('This page will appear in a few seconds'); mlsp.cs.cmu.edu/people/rsingh/ now 404s; WebSearch found no group page. Her only group site is the shared MLSP group (cmu-mlsp.github.io, PIs Bhiksha Raj, Rita Singh, Richard Stern): its Team page lists 7 PhD, 5 MS and 1 undergraduate students under shared headings with no advisor attribution, plus about 20 undated Recent Alumni (Ankit Shah, Hira Dhamyal, Mahmoud Alismail already held). Because members are not grouped by PI, none were recorded to avoid attributing Raj/Stern students to Rita Singh; the team page is the thing to resolve if shared-group members should count (current names: Ahmed Shah, Joseph Konan, Xiang Li, Soham Deshmukh, Hao Chen, Massa Baali, Yizhou Zhao, Hazim Bukhari, Dareen Alharti, Shuo Han, Sunghwan Baek, Satvik Dixit, Thomas Cantalapiedra). Publications page is the shared MLSP list (786 entries, 212 missing), added per brief; affiliation is judged by the other tool.",
    blocked=[],
)

# ---------------------------------------------------------------- Dimitrios Skarlatos
SK = "https://www.cs.cmu.edu/~caos/people.html"
D["Dimitrios Skarlatos"] = dict(
    lab_site="https://www.cs.cmu.edu/~caos/",
    people_page=SK,
    people_pages=[SK],
    members=[
        M("Siddharth Jayashankar", "phd", None, SK, near="PhD Students", note="co-advised with Wenting Zheng"),
        M("Patrick Coppock", "phd", None, SK, near="PhD Students", note="co-advised with Todd Mowry"),
        M("Eliot Solomon", "phd", None, SK, near="PhD Students", note="co-advised with Todd Mowry"),
        M("Vasilis Kypriotis", "phd", None, SK, near="PhD Students"),
        M("Alexandros Moiras", "phd", None, SK, near="PhD Students"),
        M("Kaiyang Zhao", "phd", [2021, 2026], SK, near="Alumni", note="PhD 2021-2026 -> NVIDIA Research"),
        M("Ziqi Wang", "phd", [2021, 2022], SK, near="Alumni", note="PhD 2017-2022, primary advisor Todd Mowry; co-advised by Skarlatos 2021-2022"),
        M("Nevena Stojkovic", "undergraduate", [None, 2026], SK, near="Undergraduates", note="BSc 2026; former visiting student from MIT"),
        M("Josh Kim", "undergraduate", [None, 2025], SK, near="Undergraduates", note="BSc 2025"),
        M("Alexander Blasberg", "undergraduate", [None, 2026], SK, near="Undergraduates", note="BSc 2026"),
        M("David Rudo", "undergraduate", [None, 2024], SK, near="Undergraduates", note="BSc 2024"),
        M("Xenia Xu", "undergraduate", [None, 2024], SK, near="Undergraduates", note="BSc 2024"),
        M("Tom Tang", "undergraduate", [None, 2024], SK, near="Undergraduates", note="BSc 2024"),
        M("Tony Yu", "undergraduate", [None, 2024], SK, near="Undergraduates", note="BSc 2024"),
        M("Fanyue (Chloe) Xia", "undergraduate", [None, 2023], SK, near="Undergraduates", note="BSc 2023"),
        M("Nikita Basu", "undergraduate", [None, 2023], SK, near="Undergraduates", note="BSc 2023; co-advised with Todd Mowry"),
        M("Adrian Abedon", "undergraduate", [None, 2023], SK, near="Undergraduates", note="BSc 2023; co-advised with Todd Mowry"),
        M("Kevin Xue", "masters", [None, 2024], SK, near="MSc", note="MSc 2024"),
        M("Sophia Zhang", "masters", [None, 2022], SK, near="MSc", note="MSc 2022"),
        M("Tae Hoon Kim", "masters", [None, 2024], SK, near="MSc", note="MSc 2024"),
        M("Brian Zhang", "masters", [None, 2024], SK, near="MSc", note="MSc 2024"),
        M("Rene Ravanan", "masters", [None, 2024], SK, near="MSc", note="MSc 2024"),
        M("Balamurugan Marimuthu", "masters", [None, 2022], SK, near="MSc", note="MSc 2022"),
        M("Pei Li", "masters", [None, 2022], SK, near="MSc", note="MSc 2022"),
        M("Anuvind Bhat", "masters", [None, 2022], SK, near="MSc", note="MSc 2022; co-advised with Todd Mowry"),
        M("Andrew Jacob", "masters", [None, 2022], SK, near="MSc", note="MSc 2022"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~caos/assets/bibtex/caos-publications.bib", mode="bibtex")],
    notes="Group site cs.cmu.edu/~caos (CAOS) has a People page with Faculty, PhD Students, Alumni (PhD), Undergraduates and MSc sections, all dated by graduation year or years; all recorded (members of the CAOS group; MSc and BSc graduation years 2022-2026). Skarlatos joined CMU in 2021 (UIUC PhD), so Ziqi Wang is counted only for his 2021-2022 co-advised period (primary advisor Todd Mowry). Publications: the site's own 'Download all BibTeX' file parses 35 entries, 18 missing from lab papers; the personal page cs.cmu.edu/~dskarlat only duplicates that list with award links. No Wayback needed (alumni are dated on the live page). Co-advisors named: Wenting Zheng, Todd Mowry.",
    blocked=[],
)

# ---------------------------------------------------------------- Stephen F Smith
RIS = "https://www.ri.cmu.edu/ri-faculty/stephen-smith/"
ICL = "https://www.ri.cmu.edu/robotics-groups/intelligent-coordination-and-logistics-laboratory/"
OZ = "http://www.ozone.ri.cmu.edu/"
D["Stephen F Smith"] = dict(
    lab_site="http://www.ozone.ri.cmu.edu/",
    people_page=RIS,
    people_pages=[RIS, ICL, OZ],
    members=[
        M("Hsu-kuang Chiu", "phd", None, RIS, near="current phd students"),
        M("Esme Rubinstein", "phd", None, RIS, near="current phd students"),
        M("Jingtian Yan", "phd", None, RIS, near="current phd students"),
        M("Laura Barbulescu", "staff", None, ICL, near="current staff"),
        M("David Neiman", "staff", None, ICL, near="current staff"),
        M("Zack Rubinstein", "staff", None, ICL, near="current staff"),
        M("Joseph Qu Zhou", "staff", None, ICL, near="current staff"),
        M("Rayna Hata", "phd", None, ICL, near="current student"),
        M("Isaac Isukapati", "postdoc", None, OZ, near="Postdoctoral Fellow"),
        M("Joris Kinable", "postdoc", None, OZ, near="Postdoctoral Fellow"),
        M("Gregory Barlow", "staff", None, OZ, near="Project Scientist"),
        M("Pranav Shah", "staff", None, OZ, near="Research Associate"),
    ],
    pubs=[],
    notes="Lab site is ICLL at ozone.ri.cmu.edu / icll.ri.cmu.edu (WordPress, content from 2012-era posts: People page lists Rubinstein, Barbulescu, Barlow, Isukapati, Kinable, Hsu-Chieh Hu (ECE PhD), Arvind, Hawkes, Mogali; its Publications page only links to the RI publication list). The ozone.ri home page 'Our Team' (live) lists Isukapati, Kinable, Barlow and Pranav Shah as current so they are recorded with undated roles; they may be stale. The RI profile (Students/Affiliates) lists current PhD (Chiu, E. Rubinstein, Yan), current affiliates (Barbulescu, Hata, Neiman, Z. Rubinstein, Zhou), plus undated past PhD (Barlow, Chen, Cicirello, Gallagher, Goldstein, Mogali, Neiman) and undated past masters (Aravindh, Arvind, Cao, Hawkes, Hua, Misra, Mitra, Parimi) which are skipped by rule (15 names, several held already). Personal page cs.cmu.edu/~sfs is a 2005-era stub. Rayna Hata is listed 'current student' on the RI lab page but 'current affiliate' on the profile. The RI profile 'Publications' is a JS-fed list of 306 entries (anchor parse is only nav links), so no pubs page added. Wayback captures of the RI profile were not read (archive.org in back-off).",
    blocked=[],
)

# ---------------------------------------------------------------- Virginia Smith
VS = "https://www.cs.cmu.edu/~smithv/"
D["Virginia Smith"] = dict(
    lab_site=VS,
    people_page=VS,
    people_pages=[VS],
    members=[
        M("Steven Kolawole", "phd", None, VS, near="PhD Students & Postdocs"),
        M("Kevin Kuo", "phd", None, VS, near="PhD Students & Postdocs"),
        M("Aashiq Muhamed", "phd", None, VS, near="PhD Students & Postdocs", note="with Mona Diab"),
        M("Qi Pang", "phd", None, VS, near="PhD Students & Postdocs", note="with Wenting Zheng"),
        M("Amrith Setlur", "phd", None, VS, near="PhD Students & Postdocs"),
        M("Chhavi Yadav", "phd", None, VS, near="PhD Students & Postdocs"),
        M("Don Dennis", "phd", [None, 2025], VS, near="Alumni", note="PhD 2025; Meta"),
        M("Yiwei Fu", "masters", [None, 2025], VS, near="Alumni", note="MS 2025"),
        M("Neel Guha", "masters", [None, 2020], VS, near="Alumni", note="MS 2020"),
        M("Shengyuan Hu", "phd", [None, 2025], VS, near="Alumni", note="PhD 2025"),
        M("Michael Kuchnik", "phd", [None, 2023], VS, near="Alumni", note="PhD 2023; with George Amvrosiadis"),
        M("Oscar Li", "phd", [None, 2025], VS, near="Alumni", note="PhD 2025"),
        M("Tian Li", "phd", [None, 2023], VS, near="Alumni", note="PhD 2023"),
        M("Ken Liu", "masters", [None, 2023], VS, near="Alumni", note="MS 2023"),
        M("Arian Raje", "masters", [None, 2024], VS, near="Alumni", note="MS 2024"),
        M("Qiqi Xu", "masters", [None, 2021], VS, near="Alumni", note="MS 2021"),
    ],
    pubs=[],
    notes="Personal page cs.cmu.edu/~smithv lists current PhD students & postdocs and a dated Alumni section (PhD/MS years); all alumni with 2016+ years recorded. Pratiksha Thaker (postdoc, with Steven Wu) is listed without dates so skipped (undated). Smith joined CMU in 2017 (Berkeley PhD 2015, postdoc Stanford), so no earlier-institution students. Wayback has yearly captures of the page (2019-2026) but archive.org was in shared back-off when 2020/2023 captures were requested, so earlier current-student lists were not read; alumni dates already cover the gap. The homepage embeds an unstructured publication list (title / authors / venue / abstract lines); auto/li/block modes pick up awards and abstract sentences as titles, so no pubs page was added.",
    blocked=[],
)

# ---------------------------------------------------------------- Akshitha Sriraman
SR = "https://users.ece.cmu.edu/~asrirama/"
D["Akshitha Sriraman"] = dict(
    lab_site=SR,
    people_page=SR,
    people_pages=[SR],
    members=[
        M("Jaylen Wang", "phd", None, SR, s="Meet the Team", e="Jaylen Wang PhD Candidate"),
        M("Sara Mahdizadeh Shahri", "phd", None, SR, near="Researchers"),
        M("Veronica Muriga", "phd", None, SR, near="Researchers"),
        M("Deepanjali Mishra", "phd", None, SR, near="Researchers"),
        M("Abnash Bassi", "phd", [2025, None], SR, near="Researchers"),
        M("Mihailo Rancic", "phd", [None, 2026], SR, s="Alumni", e="Mihailo Rancic", note="PhD thesis defended Apr 2026; first employment Google"),
        M("Swamynathan Siva", "masters", [None, 2024], SR, q="My Master's advisee, Swamynathan Siva, graduated and is now at NVIDIA", note="Dec 2024 news item"),
        M("Melissa Pan", "masters", [None, 2024], SR, q="My Master's student, Melissa Pan, has accepted a PhD offer from UC Berkeley", note="Apr 2024 news item"),
        M("Zibo Gong", "masters", [None, 2023], SR, q="My Master's student, Zibo Gong, has accepted a PhD offer from UIUC", note="Apr 2023 news item"),
        M("Hilbert Chen", "undergraduate", [None, 2023], SR, q="My undergraduate intern, Hilbert Chen, has accepted a PhD offer from CMU", note="Apr 2023 news item; undergraduate intern/advisee"),
        M("Sriram Devata", "undergraduate", [None, 2024], SR, q="My undergraduate intern, Sriram Devata, has accepted a PhD offer from UIUC", note="Apr 2024 news item; undergraduate intern"),
        M("Shixin Song", "undergraduate", [None, 2022], SR, q="My undergraduate intern, Shixin Song, has accepted a PhD offer from MIT", note="Apr 2022 news item; undergraduate intern"),
    ],
    pubs=[],
    notes="Site users.ece.cmu.edu/~asrirama is a single-page Hugo Academic site: 'Meet the Team' lists 5 current PhD students (Wang, Mahdizadeh Shahri, Muriga, Mishra, Bassi) and one alumnus (Rancic, PhD Apr 2026); Master's advisees and undergraduate interns appear only in dated Recent News items (recorded with the news quote). Undergraduate 'interns' may have been external to CMU; kept because the PI calls them her advisees. Non-CMU co-authors (Tanvir, Nathan from Michigan work) excluded. Sriraman joined CMU in 2021 (Michigan PhD 2021) so Michigan students are excluded. Publications: Conference/Journal lists are embedded in the homepage with news and award links; auto/block/anchor modes return mostly awards, talks and news (1 correct match, noise elsewhere), so no pubs page added. Wayback not used (team list is current and news items date earlier members).",
    blocked=[],
)

# ---------------------------------------------------------------- John C Stamper
HJ = "https://www.hcii.cmu.edu/people/john-stamper"
D["John C Stamper"] = dict(
    lab_site="https://dev.stamper.org/",
    people_page=HJ,
    people_pages=[HJ],
    members=[
        M("Christine Kwon", "phd", None, HJ, near="Advisees"),
        M("Marshall An", "phd", None, HJ, near="Advisees"),
        M("Yumou (James) Wei", "phd", None, HJ, near="Advisees"),
        M("Ruiwei Xiao", "phd", None, HJ, near="Advisees"),
        M("Hyeongdon (Doni) Moon", "phd", None, HJ, near="Advisees"),
    ],
    pubs=[PUB("https://dev.stamper.org/local/staticpage/view.php?page=pubs", mode="auto")],
    notes="dev.stamper.org (Moodle static pages: About, Research, Publications, Contact; banner 'Website currently being updated') has no people/students page. The only member list is the HCII profile Advisees section (5 PhD advisees; all already held). Stamper is Director of the METALS master's program; METALS students are not his advisees and were not recorded. Publications page parses cleanly (168 entries, class-title, 27 missing from lab papers). Wayback captures of the old stamper.org were not read (archive.org in back-off); an older version may list lab members.",
    blocked=[],
)

# ---------------------------------------------------------------- Siddhartha Srinivasa
D["Siddhartha Srinivasa"] = dict(
    lab_site="https://personalrobotics.cs.washington.edu/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="PENDING",
    blocked=[],
)
