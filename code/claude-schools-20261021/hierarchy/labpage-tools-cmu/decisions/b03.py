from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Alan Black
AB = "http://www.cs.cmu.edu/~awb/"
AB16 = WB + "20160110145307id_/http://www.cs.cmu.edu:80/~awb/"
AB20 = WB + "20200112043615id_/http://www.cs.cmu.edu:80/~awb/"
AB22 = WB + "20220118203104id_/http://www.cs.cmu.edu/~awb/"
D["Alan Black"] = dict(
    lab_site=AB,
    people_page=AB,
    people_pages=[AB, AB16, AB20, AB22],
    members=[
        M("Siddharth Dalmia", "phd", None, AB, near="Working Group",
          note="'Working Group' on the homepage = his doctoral students"),
        M("Xinjian Li", "phd", None, AB, near="Working Group"),
        M("Sai Krishna Rallabandi", "phd", None, AB22, near="Working Group"),
        M("Khyathi Raghavi Chandu", "phd", None, AB22, near="Working Group"),
        M("Shruti Palaskar", "phd", None, AB22, near="Working Group"),
        M("Shrimai Prabhumoye", "phd", None, AB22, near="Working Group",
          note="also Working Group in 2018 and 2020 captures"),
        M("Elijah Mayfield", "phd", None, AB22, near="Working Group"),
        M("Pallavi Baljekar", "phd", None, AB16, near="Working Group"),
        M("Wang Ling", "phd", None, AB16, near="Working Group"),
        M("Prasanna Muthukumar", "phd", None, AB16, near="Working Group"),
        M("Joao Miranda", "phd", None, AB16, near="Working Group"),
        M("Sunayana Sitaram", "phd", None, AB16, near="Working Group"),
        M("Zhou Yu", "phd", None, AB16, near="Working Group"),
    ],
    pubs=[PUB(AB, mode="auto")],
    notes=("No lab site; the homepage (retired 2022) lists 'Working Group' (current students) and 'Recent "
           "Graduates', and holds the publication list by year. Captures 2016/2020/2022 used (2018 adds nothing "
           "beyond 2020). Skipped: recent graduates never shown as current in a 2016+ capture (Philgoo Han, "
           "S P Kishore, John Kominek, Brian Langner, Arthur Toth, Gopala Krishna Anumanchipalli, Alok Parlikar, "
           "and Kevin Lenzo, who first appears under Recent Graduates on the post-2022 live page; held already). "
           "Alex Rudnicky / Lori Levin / Emma Strubell appear only as co-teaching faculty."),
    blocked=[],
)

# ---------------------------------------------------------------- Guy Blelloch
GB = "http://www.cs.cmu.edu/~guyb/"
GBCSD = "https://csd.cmu.edu/people/faculty/guy-blelloch"
D["Guy Blelloch"] = dict(
    lab_site=GB,
    people_page=GB,
    people_pages=[GB, GBCSD],
    members=[
        M("Magdalen Dobson", "phd", None, GB, q="Recent(ish) PhD Students Magdalen Dobson Current student",
          note="= Magdalen Dobson Manohar"),
        M("Hao Wei", "phd", [None, 2023], GB, near="Recent(ish) PhD Students",
          note="thesis 'General Techniques for Efficient Concurrent Data Structures' 2023 = Yuanhao Wei"),
        M("Daniel Anderson", "phd", [None, 2023], GB, near="Recent(ish) PhD Students"),
        M("Ziv Scully", "phd", [None, 2022], GB, near="Recent(ish) PhD Students"),
        M("Laxman Dhulipala", "phd", [None, 2020], GB, near="Recent(ish) PhD Students"),
        M("Naama Ben-David", "phd", [None, 2020], GB, near="Recent(ish) PhD Students"),
        M("Yihan Sun", "phd", [None, 2019], GB, near="Recent(ish) PhD Students"),
        M("Yan Gu", "phd", [None, 2018], GB, near="Recent(ish) PhD Students"),
        M("Andrew Brady", "phd", None, GBCSD, q="Advisees Andrew Brady",
          note="CSD directory advisee list"),
        M("André Cesar Costa", "phd", None, GBCSD, q="Advisees Andrew Brady André Cesar Costa"),
        M("Zak Kent", "phd", None, GBCSD, q="Advisees Andrew Brady André Cesar Costa Zak Kent"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~guyb/pubs.html", mode="auto")],
    notes=("No separate lab site; homepage has a 'Recent(ish) PhD Students' list (first appears in 2024; the "
           "2017/2021/2023 captures have no student list). Current advisees taken from the CSD directory profile. "
           "Skipped PhDs before 2016 (Shun 2015, Kyrola 2014, Simhadri 2013, Tangwongsan 2011, and earlier)."),
    blocked=[],
)

# ---------------------------------------------------------------- Avrim Blum
AV = "http://www.cs.cmu.edu/~avrim/"
AV16 = WB + "20160113065636id_/http://www.cs.cmu.edu/~avrim/"
AV17 = WB + "20170102001605id_/http://www.cs.cmu.edu/~avrim/"
D["Avrim Blum"] = dict(
    lab_site=AV,
    people_page=AV17,
    people_pages=[AV, AV16, AV17],
    members=[
        M("Nika Haghtalab", "phd", None, AV17, q="My advisees: Nika Haghtalab (co-advised with Ariel Procaccia)"),
        M("Vaishnavh Nagarajan", "phd", None, AV17,
          q="My advisees: Nika Haghtalab (co-advised with Ariel Procaccia), Vaishnavh Nagarajan (co-advised with Nina Balcan)"),
        M("Chen Dan", "phd", None, AV17,
          q="Vaishnavh Nagarajan (co-advised with Nina Balcan), Chen Dan (co-advised with Pradeep Ravikumar)",
          note="appears as current advisee in the Jan-2017 capture only"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~avrim/Papers/pubs.html", mode="auto")],
    notes=("Blum left CMU for TTI-Chicago on 2017-08-01 (old CMU homepage says so), so the CMU window is 2016-2017. "
           "Homepage captures Jan-2016 and Jan-2017 list current advisees; live page lists only undated 'Past PhD "
           "advisees' (20 names). Skipped past advisees who graduated before 2016 (Jamie Morgenstern, Ankit Sharma, "
           "Liu Yang, Pranjal Awasthi, Or Sheffet, ... - none shown as current in 2016+ captures); Nika Haghtalab is "
           "kept via the current list. No lab site of his own at CMU (ALADDIN / Theory group are shared)."),
    blocked=[],
)

# ---------------------------------------------------------------- Manuel Blum
MB = "http://www.cs.cmu.edu/~mblum/news/students.html"
MB16 = WB + "20160303191026id_/http://www.cs.cmu.edu/~mblum/news/students.html"
MB17 = WB + "20170329221130id_/http://www.cs.cmu.edu:80/~mblum/news/students.html"
D["Manuel Blum"] = dict(
    lab_site="http://www.cs.cmu.edu/~mblum/",
    people_page=MB,
    people_pages=[MB, MB16, MB17],
    members=[
        M("Brendan Meeder", "phd", None, MB16, near="Current PhD Students"),
        M("Mehdi Samadi", "phd", None, MB16, near="Current PhD Students"),
        M("Jeremiah Blocki", "phd", None, MB16, near="Current PhD Students",
          note="listed as current in the Mar-2016 capture, but his CMU PhD was 2014 and the Mar-2017 capture moves "
               "him to 'PhD students over the years' with Purdue University: the 2016 listing is likely stale"),
    ],
    pubs=[],
    notes=("No lab site; homepage has a Students page ('Current PhD Students' empty on the live page, filled in the "
           "Mar-2016 capture) and an undergraduate-research page naming only Brendan Juba and Matt Humphrey "
           "(undated, from the 2000s consciousness talk; skipped). The rest of 'PhD students over the years' are "
           "pre-2016 (Ryan Williams, Luis von Ahn, ...). Research page lists papers only up to 2006, so no "
           "publications page added. Sahil Singla (held) is not named on any of his pages."),
    blocked=[],
)

# ---------------------------------------------------------------- Nicholas Boffi
NB = "https://nmboffi.github.io/"
D["Nicholas Boffi"] = dict(
    lab_site=NB,
    people_page=NB,
    people_pages=[NB],
    members=[
        M("Jerry Huang", "phd", None, NB, near="PhD Students"),
        M("Stephen Huan", "phd", None, NB, near="PhD Students", note="co-advised with Andrej Risteski"),
        M("Fadi Atieh", "phd", None, NB, near="PhD Students", note="co-advised with Max Simchowitz"),
        M("Justin Lin", "masters", None, NB, near="Masters Students"),
        M("Kartik Nair", "masters", None, NB, near="Masters Students"),
        M("Sheel Shah", "masters", None, NB, near="Masters Students"),
        M("Anna Wei", "other", None, NB, near="Affiliates",
          note="group 'Affiliate' (MLD PhD advised by Ameet Talwalkar and Andrej Risteski)"),
        M("Rishal Aggarwal", "other", None, NB, near="Affiliates",
          note="group 'Affiliate' (CBD PhD advised by David Ryan Koes)"),
        M("Sanjit Dandapanthula", "phd", None, NB, near="Former Students",
          note="former student; PhD in Statistics/MLD co-advised with Aaditya Ramdas"),
        M("Tejas Guha", "masters", None, NB, near="Former Students", note="co-advised with Ameet Talwalkar"),
        M("Ishin Shah", "undergraduate", None, NB, near="Former Students", note="co-advised with Max Simchowitz"),
    ],
    pubs=[PUB(NB, mode="css:article.paper-card", title_css="h3.title")],
    notes=("Homepage doubles as the group page (PhD / Masters / Affiliates / Former Students; publications on the same "
           "page). Joined CMU 2024; the only Wayback capture (Feb 2025) has no student list. Skipped Abbas Mammadov "
           "(PhD student at Oxford co-advised with Yee Whye Teh; not placed at CMU)."),
    blocked=[],
)

# ---------------------------------------------------------------- Richard Schuster Border
RB = "https://borderlab.org/people/"
D["Richard Schuster Border"] = dict(
    lab_site="https://borderlab.org/",
    people_page=RB,
    people_pages=[RB],
    members=[
        M("Alireza Rasoulzadeh", "phd", None, RB, q="Alireza Rasoulzadeh PhD Student"),
        M("McKenzie van der Hagen", "phd", None, RB, q="McKenzie van der Hagen PhD Student"),
        M("Ajay Prabhakar", "masters", None, RB, q="Ajay Prabhakar MS Student"),
        M("Ziyan Zhang", "masters", None, RB, q="Ziyan Zhang MS Student"),
        M("Siyona Dhingra", "undergraduate", None, RB, q="Siyona Dhingra Undergraduate Researcher"),
    ],
    pubs=[PUB("https://borderlab.org/publications/", mode="auto")],
    notes=("border.lab @ CMU (new lab). People page lists PI, the lab dog (skipped) and 5 members; no Wayback "
           "captures of the people page exist, so no alumni source."),
    blocked=[],
)

# ---------------------------------------------------------------- Marcel Bruchez
BZ = "https://labs.bio.cmu.edu/bruchez-lab/people/"
BZ16 = WB + "20160124074624id_/http://bruchez-lab.mbic.cmu.edu:80/gradstudents.php"
D["Marcel Bruchez"] = dict(
    lab_site="https://labs.bio.cmu.edu/bruchez-lab/",
    people_page=BZ,
    people_pages=[BZ, BZ16],
    members=[
        M("Lydia Perkins", "phd", None, BZ, q="Lydia Perkins Ph.D. Student, Biological Sciences"),
        M("Daniel Ackerman", "phd", None, BZ, q="Daniel Ackerman Ph.D. Student, Biological Sciences"),
        M("Iris Yank", "phd", None, BZ, q="Iris Yank Ph.D. Student, Biological Sciences"),
        M("Alex Carpenter", "phd", None, BZ, q="Alex Carpenter Ph.D. Student, Chemistry",
          note="'Alexandra Carpenter' on the Jan-2016 capture"),
        M("Dmytrio Kolodieznyi", "phd", None, BZ, q="Dmytrio Kolodieznyi Ph.D. Student, Chemistry",
          note="spelling as on the page; = Dmytro Kolodieznyi"),
        M("Huaxia Shi", "phd", None, BZ, q="Huaxia Shi Ph.D. Student, Chemistry"),
        M("Pingping Liang", "phd", None, BZ, q="Pingping Liang Ph.D. Student, Chemistry"),
        M("Brigitte Schmidt", "staff", None, BZ, q="Brigitte Schmidt, Ph.D. Senior Chemist"),
        M("Cheryl Telmer", "staff", None, BZ, q="Cheryl Telmer, Ph.D. Senior Molecular Biologist"),
        M("Christopher Szent-Gyorgyi", "staff", None, BZ, q="Christopher Szent-Gyorgyi, Ph.D. Senior Molecular Biologist"),
        M("Greg Fisher", "staff", None, BZ, q="Greg Fisher, Ph.D. Senior Cell Biologist"),
        M("Dorsin Chang", "staff", None, BZ, q="Dorsin Chang Molecular Biologist"),
        M("Xiaohong Tan", "postdoc", None, BZ, q="Xiaohong Tan, Ph.D. Postdoctoral Scholar, Chemistry"),
        M("Taylor Canady", "phd", [None, 2017], BZ, q="Taylor Canady, PhD 2017"),
        M("Matharishwan Naganbabu", "phd", [None, 2017], BZ, q="Matharishwan Naganbabu, PhD 2017"),
        M("Bruce Feldman", "masters", [None, 2017], BZ, q="Bruce Feldman , MS 2017"),
        M("Chris Pratt", "phd", [None, 2016], BZ, q="Chris Pratt, PhD 2016"),
        M("Jianjun He", "phd", [None, 2016], BZ, q="Jianjun He , PhD 2016"),
        M("Yi Wang", "phd", None, BZ16, near="Department of Biological Sciences",
          note="alumni list says PhD 2015, but still listed as a current graduate student in the Jan-2016 capture"),
    ],
    pubs=[],
    notes=("Lab site moved chem.cmu.edu/groups/bruchez (frozen ~2013, still online, lists pre-2016 people as "
           "current) -> bruchez-lab.mbic.cmu.edu -> labs.bio.cmu.edu/bruchez-lab (used; found via the cmu.edu/cmecs "
           "people page). Bruchez died Aug 2022 (CMU obituary). Skipped alumni before 2016 (Jonathan deWerd MS 2015, "
           "Saurabh 2014, Grover 2013, Maji 2012, Yan 2012, Mittal 2010) and the frozen chem.cmu.edu roster "
           "(Richa Verma postdoc, undergrads Lauren Beck/Kelsey Diffley/Victor Mann/Melissa Sidran, MBIC scientists "
           "Byron Ballou/Lauren Ernst/Susan Andreko) - none shown in a 2016+ source. Publications page "
           "(labs.bio.cmu.edu/bruchez-lab/publications/) not added: entries put the author list in <strong>, so every "
           "mode extracts author lists as titles; only 1 in-window paper is not a lab paper (Shiwarski et al. 2017, "
           "'PI3K class II alpha regulates delta-opioid receptor export...')."),
    blocked=[],
)

# ---------------------------------------------------------------- David Brumley
DB0 = "http://users.ece.cmu.edu/~dbrumley/index.html"
DB16 = WB + "20160530042115id_/https://users.ece.cmu.edu/~dbrumley/"
DB17 = WB + "20170201231559id_/https://users.ece.cmu.edu/~dbrumley/"
DB18 = WB + "20180301040311id_/http://users.ece.cmu.edu:80/~dbrumley/"
DBCSD = "https://csd.cmu.edu/people/faculty/david-brumley"
D["David Brumley"] = dict(
    lab_site="http://users.ece.cmu.edu/~dbrumley/",
    people_page=DB16,
    people_pages=[DB0, DB16, DB17, DB18, DBCSD],
    members=[
        M("Tiffany Bao", "phd", None, DB16, near="I am fortunate to advise several great PhD students",
          note="still current in the 2018 capture"),
        M("Jonathan Burket", "phd", None, DB16, near="I am fortunate to advise several great PhD students",
          note="former student (now at Apogee Research) by the Feb-2017 capture"),
        M("Sang Kil Cha", "phd", None, DB16, near="I am fortunate to advise several great PhD students",
          note="listed as current in May 2016, but the same page's later versions say 'PhD ECE 2015, now at KAIST'"),
        M("Peter Chapman", "phd", None, DB16, near="I am fortunate to advise several great PhD students",
          note="former student (now at Duolingo) by the Feb-2017 capture"),
        M("Dominic Chen", "phd", None, DB16, near="I am fortunate to advise several great PhD students"),
        M("Samantha Gottlieb", "phd", None, DB16, near="I am fortunate to advise several great PhD students"),
        M("Dimitris Konomis", "phd", None, DB16, near="I am fortunate to advise several great PhD students"),
        M("Matthew Maurer", "phd", None, DB16, near="I am fortunate to advise several great PhD students",
          note="still current in the 2018 capture"),
        M("Rijnard van Tonder", "phd", None, DB16, near="I am fortunate to advise several great PhD students"),
        M("Seunghyun Lee", "phd", None, DBCSD, q="Advisees Seunghyun Lee", note="CSD directory advisee"),
    ],
    pubs=[],
    notes=("No lab site; ECE homepage has a Students section (live: one undated list of advised PhD students and "
           "former postdocs). Current students taken from the May-2016 capture (Feb-2017 and Mar-2018 captures are "
           "subsets). Skipped: former students already 'former' in 2016 (Thanassis Avgerinos, Alex Rebert, Edward J. "
           "Schwartz PhD 2014, Jiyong Jang PhD 2014) and former postdocs (Maverick Woo, JongHyup Lee, Manuel Egele), "
           "none current in a 2016+ capture. The 'Papers' link goes to Google Scholar (off limits); the papers list "
           "embedded in 2016-2018 captures stops at 2014, so no publications page added. Plaid Parliament of Pwning "
           "(CTF team he advises) is not a research group."),
    blocked=[],
)

# ---------------------------------------------------------------- Travis Breaux
BX = "http://www.cs.cmu.edu/~breaux/research.html"
BXH = "http://www.cs.cmu.edu/~breaux/"
BX16 = WB + "20160224161858id_/http://www.cs.cmu.edu:80/~breaux/research.html"
BX20 = WB + "20200216165222id_/http://www.cs.cmu.edu:80/~breaux/research.html"
BX22 = WB + "20221128072846id_/http://www.cs.cmu.edu/~breaux/research.html"
RE17 = WB + "20170226112408id_/http://gaius.isri.cmu.edu/"
D["Travis Breaux"] = dict(
    lab_site="http://www.cs.cmu.edu/~breaux/",
    people_page=BX,
    people_pages=[BX, BX16, BX20, BX22, RE17, BXH],
    members=[
        M("Anmol Singhal", "phd", None, BX, q="Anmol Singhal , Ph.D. Student in Software Engineering"),
        M("Sarah Santos", "phd", None, BX, q="Sarah Santos , Ph.D. Student in Software Engineering"),
        M("Yuchen Shen", "phd", [None, 2024], BX, q="Dr. Yuchen Shen received the Ph.D. in Software Engineering in 2024",
          note="current student in the Nov-2022 capture"),
        M("Jaspreet Bhatia", "phd", [None, 2019], BX, q="Dr. Jaspreet Bhatia received the Ph.D. in Software Engineering in 2019"),
        M("Hanan Hibshi", "phd", [None, 2019], BX, q="Dr. Hanan Hibshi received the Ph.D. in Societal Computing in 2019"),
        M("Daniel Smullen", "phd", None, BX16,
          q="Daniel Smullen , Ph.D. Student in Software Engineering and co-advised with Dr. David Garlan"),
        M("Morgan Evans", "phd", None, BX20, q="Morgan Evans , Ph.D. Student in Software Engineering",
          note="only current student in the Feb-2020 capture; not listed later"),
        M("Sudarshan Wadkar", "member", None, RE17, near="Associates:",
          note="'Associate' of the Requirements Engineering Lab (Feb-2017 capture), CMU homepage cs.cmu.edu/~swadkar"),
        M("Tianjian Huang", "masters", None, BXH, q="CMU INI student Tianjian Huang",
          note="co-author per the homepage news item of 30 May 2023"),
        M("Vaishnavi Kualagi", "masters", None, BXH, q="MSE-SS student Vaishnavi Kualagi",
          note="co-author per the homepage news item of 30 May 2023"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~breaux/publications.html", mode="auto")],
    notes=("lab_url in the input was the ISRI faculty index. Homepage research.html has Current Students / Alumni "
           "(used live + 2016/2020/2022 captures); the Requirements Engineering Lab site (gaius.isri.cmu.edu, now "
           "refusing connections) lists faculty Collaborators (skipped) and Associates in 2017/2021 captures; "
           "associates Mitra Bokaei Hosseini and Rocky Slavin (UTSA) and Maria Riaz (NCSU) are external and skipped. "
           "Skipped Dave Gordon (EPP PhD 2014) and 'Sharfuddin' (surname only, homepage news 2025)."),
    blocked=[],
)

# ---------------------------------------------------------------- Stephen Brookes
D["Stephen Brookes"] = dict(
    lab_site="http://www.cs.cmu.edu/~brookes/",
    people_page="http://www.cs.cmu.edu/~brookes/",
    people_pages=["http://www.cs.cmu.edu/~brookes/",
                  WB + "20080908064944id_/http://www.cs.cmu.edu/~brookes/",
                  WB + "20231020223522id_/http://www.cs.cmu.edu/~brookes/"],
    members=[],
    pubs=[],
    notes=("Only source is the homepage, which is byte-identical (same sha256) to the Sep-2008 Wayback capture and "
           "unchanged in every capture since. Its 'Current Students' (Ruy Ley-Wild, Carsten Varming, jointly with "
           "John Reynolds) are 2008-era students who finished long before 2016 (Ley-Wild's 2010 thesis is listed on "
           "Blelloch's page), so they are not recorded despite the 'current' label; Former Students are 1995-2003. "
           "Ryan Kavanagh (held) is not named. Papers list ends in 2007, so no publications page added. CSD profile "
           "lists him as Professor Emeritus with no advisees."),
    blocked=[],
)

# ---------------------------------------------------------------- Fraser Brown
FBC = "https://csd.cmu.edu/people/faculty/fraser-brown"
D["Fraser Brown"] = dict(
    lab_site="https://mlfbrown.com/",
    people_page=FBC,
    people_pages=[FBC, "https://mlfbrown.com/",
                  WB + "20230226173522id_/https://mlfbrown.com/",
                  WB + "20240119222539id_/https://mlfbrown.com/"],
    members=[
        M("Kunming Jiang", "phd", None, FBC, q="Advisees Kunming Jiang", note="CSD directory advisee list"),
        M("Edward Chen", "phd", None, FBC, q="Advisees Kunming Jiang Edward Chen"),
        M("Michael McLoughlin", "phd", None, FBC, q="Advisees Kunming Jiang Edward Chen Michael McLoughlin"),
        M("Seunghyun Lee", "phd", None, FBC, q="Advisees Kunming Jiang Edward Chen Michael McLoughlin Seunghyun Lee"),
    ],
    pubs=[PUB("https://mlfbrown.com/", mode="auto")],
    notes=("No lab site; mlfbrown.com is a one-page homepage with a publication list and no people section (live, "
           "and the 2023/2024 captures - the Feb-2023 capture is still his Stanford-student page). Members taken "
           "from the CSD directory 'Advisees' list; S3D profile lists none. One auto-extracted pub entry is the bio "
           "sentence, the rest are real titles."),
    blocked=[],
)

# ---------------------------------------------------------------- Brett Browning
D["Brett Browning"] = dict(
    lab_site=None,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes=("No usable site: lab_url cs.cmu.edu/~brettb returns 404 live; the RI faculty/people slugs "
           "(ri-faculty/brett-browning, ri-people/brett-browning) 404 and the RI search API has no profile for him; "
           "Wayback CDX was refused (connection refused) so no captures could be read. Only already-held student "
           "Hatem Alismail is known from other sources."),
    blocked=[],
)
