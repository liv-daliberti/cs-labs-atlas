from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Keenan Crane
G26 = WB + "20260421214949id_/http://geometry.cs.cmu.edu/"
G23 = WB + "20230128004214id_/http://geometry.cs.cmu.edu/"
G20 = WB + "20200129122631id_/http://geometry.cs.cmu.edu:80/"
D["Keenan Crane"] = dict(
    lab_site="http://geometry.cs.cmu.edu/",
    people_page=G26,
    people_pages=[G26, G23, G20],
    members=[
        M("Jiří Minarčík", "postdoc", None, G26, q="Jiří Minarčík — Postdoc"),
        M("Nicole Feng", "phd", None, G26, q="Nicole Feng — PhD (Computer Science)"),
        M("Olga Guțan", "phd", None, G26, q="Olga Guțan — PhD (Computer Science)"),
        M("Hossein Baktash", "phd", None, G26, q="Hossein Baktash — PhD (Electrical & Computer Engineering)"),
        M("Zoë Marschner", "phd", [2023, None], G26, q="Zoë Marschner — PhD (Computer Science, starting Fall 2023)"),
        M("Hyojae Park", "undergraduate", None, G26, q="Hyojae Park — BS (Computer Science)"),
        M("Mark Gillespie", "phd", None, G26, q="Mark Gillespie — PhD (Computer Science)",
          note="current in 2020 and 2023 captures"),
        M("Rohan Sawhney", "phd", None, G26, q="Rohan Sawhney — PhD (Computer Science)",
          note="current in 2020 and 2023 captures"),
        M("Denise Yang", "masters", None, G26, q="Denise Yang — MS (Electrical & Computer Engineering)",
          note="past member first listed after the 2023 capture"),
        M("Simon Schwarz", "visitor", None, G26, q="Simon Schwarz — PhD (Mathematics, visitor from @UGöttingen)",
          note="visiting PhD student, first listed after the 2023 capture"),
        M("Sam Estep", "phd", None, G23, q="Sam Estep — PhD (Computer Science)", note="current in 2023 capture"),
        M("Ethan Lu", "undergraduate", None, G20, q="Ethan Lu — BS (Mathematics)", note="current in 2020 capture"),
        M("Daniel Li", "undergraduate", None, G20, q="Daniel Li — BS (Material Science)", note="current in 2020 capture"),
        M("Hesper Yin", "undergraduate", None, G23, q="Hesper Yin — BS (Computer Science)",
          note="absent in 2020 capture, past member by 2023"),
        M("Maxwell Slater", "undergraduate", None, G23, q="Maxwell Slater — BS (Computer Science / Math)",
          note="absent in 2020 capture, past member by 2023"),
        M("Josua Sassen", "visitor", None, G23, q="Josua Sassen — PhD (Mathematics, University of Bonn)",
          note="visiting PhD student from Bonn; absent in 2020 capture, past member by 2023"),
        M("Nick Sharp", "phd", None, G20, q="Nick Sharp — PhD (Computer Science)", note="current in 2020 capture"),
        M("Chris Yu", "phd", None, G20, q="Chris Yu — PhD (Computer Science)", note="current in 2020 capture"),
        M("Katherine Ye", "phd", None, G20, q="Katherine Ye — PhD (Computer Science)",
          note="current in 2020 capture; listed as Kai Ye on the 2023/2026 pages"),
        M("Ray Ye", "undergraduate", None, G20, q="Ray Ye — BS (Physics)", note="current in 2020 capture"),
        M("Josh Kalapos", "undergraduate", None, G20, q="Josh Kalapos — BS (Computer Science)",
          note="current in 2020 capture"),
        M("Alex Havrilla", "undergraduate", None, G23, q="Alex Havrilla — BS (Computer Science & Mathematics)",
          note="absent in 2020 capture, past member by 2023"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~kmcrane/", mode="css:div.paperBlock", title_css="span.paperTitle")],
    notes=("Geometry Collective (geometry.cs.cmu.edu) now 404s live; used Wayback captures 2026/2023/2020. "
           "Publications are on Crane's homepage."),
    blocked=[],
)

# ---------------------------------------------------------------- Karl Crary
KC = "http://www.cs.cmu.edu/~crary"
KC17 = WB + "20170210053307id_/http://www.cs.cmu.edu/~crary/"
KC20 = WB + "20200111220410id_/http://www.cs.cmu.edu:80/~crary/"
D["Karl Crary"] = dict(
    lab_site="http://www.cs.cmu.edu/~crary/",
    people_page=KC,
    people_pages=[KC, KC17, KC20],
    members=[
        M("Maria Khutoretsky", "phd", None, KC17, q="Current Students Maria Khutoretsky",
          note="current student in 2017 capture only"),
        M("Michael Sullivan", "phd", None, KC17, q="Current Students Maria Khutoretsky Michael Sullivan",
          note="current in 2017 capture; former student by 2020"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~crary/papers/", mode="auto")],
    notes=("Homepage only (no lab site). Live page lists only undated Former Students; of those only Michael "
           "Sullivan is seen as current in a 2016+ capture (2017). Skipped as pre-2016 alumni: Derek Dreyer, "
           "Chris Martens (PhD 2015), Tom Murphy, Leaf Petersen, Susmit Sarkar, Joe Vanderwaart (6). "
           "Held students Joshua Grosso and Matias Scharager do not appear on the page."),
    blocked=[],
)

# ---------------------------------------------------------------- Lorrie Cranor
LC = "https://lorrie.cranor.org/"
LC17 = WB + "20170101215231id_/http://lorrie.cranor.org/"
LC23 = WB + "20230103111319id_/https://lorrie.cranor.org/"
CU = "http://cups.cs.cmu.edu/"
CUA = "http://cups.cs.cmu.edu/alumni.html"
CU17 = WB + "20170131044332id_/https://cups.cs.cmu.edu/"
CU20 = WB + "20200118033508id_/http://cups.cs.cmu.edu:80/"
CU23 = WB + "20230108183108id_/https://cups.cs.cmu.edu/"
_cur = "Current members:"
_alum = "CUPS Alumni and Former Lab Members"
_ali = "not in the 2017 capture's alumni list, so a member who left after Jan 2017"
D["Lorrie Cranor"] = dict(
    lab_site="http://cups.cs.cmu.edu/",
    people_page=LC,
    people_pages=[LC, LC17, LC23, CU, CUA, CU17, CU20, CU23],
    members=[
        # Cranor's own PhD students (homepage)
        M("Wendy Bickersteth", "phd", None, LC, near="Current PhD Students"),
        M("John Driscoll", "phd", None, LC, near="Current PhD Students"),
        M("Lily Klucinec", "phd", None, LC, near="Current PhD Students"),
        M("Alexandra Li", "phd", None, LC, near="Current PhD Students"),
        M("Megan Li", "phd", None, LC, near="Current PhD Students"),
        M("Yanzi Lin", "phd", None, LC, near="Current PhD Students"),
        M("Alexandra Nisenoff", "phd", None, LC, near="Current PhD Students"),
        M("Ginger Smith", "phd", None, LC, near="Current PhD Students"),
        M("Elijah Bouma-Sims", "phd", [None, 2026], LC, q="Elijah Bouma-Sims ( Societal Computing ) PhD 2026"),
        M("Jessica Colnago", "phd", [None, 2021], LC, q="Jessica Colnago ( Societal Computing PhD 2021"),
        M("Kyle Crichton", "phd", [None, 2023], LC, q="Kyle Crichton ( EPP PhD 2023"),
        M("Pardis Emami-Naeini", "phd", [None, 2020], LC, q="Pardis Emami-Naeini ( Societal Computing PhD 2020"),
        M("Andy Gallardo", "phd", [None, 2025], LC, q="Andy Gallardo ( Societal Computing PhD 2025",
          note="Andrea Gallardo on the CUPS pages"),
        M("Hana Habib", "phd", [None, 2021], LC, q="Hana Habib ( Societal Computing PhD 2021)"),
        M("Saranga Komanduri", "phd", [None, 2016], LC, q="Saranga Komanduri ( Societal Computing PhD 2016)"),
        M("Abby Marsh", "phd", [None, 2018], LC, q="Abby Marsh ( Societal Computing PhD 2018)"),
        M("Manya Sleeper", "phd", [None, 2016], LC, q="Manya Sleeper ( Societal Computing PhD 2016)"),
        M("Josh Tan", "phd", [None, 2020], LC, q="Josh Tan ( Societal Computing PhD 2020"),
        M("Blase Ur", "phd", [None, 2016], LC, q="Blase Ur ( Societal Computing PhD 2016)"),
        M("Sarah Pearman", "phd", None, LC23, near="Current PhD Students",
          note="also on the live CUPS current-members list"),
        # CUPS lab members (lab directed by Cranor; role not stated on the page)
        M("Hazim Almuhimedi", "member", None, CU17, near=_cur),
        M("Sekhar Bhagvatula", "member", None, CU17, near=_cur),
        M("Alain Forget", "member", None, CU17, near=_cur),
        M("David Gordon", "member", None, CU17, near=_cur),
        M("Jim Graves", "member", None, CU17, near=_cur),
        M("Hanan Hibshi", "member", None, CU17, near=_cur, note="also current in 2020 and 2023 captures"),
        M("Candice Hoke", "member", None, CU17, near=_cur),
        M("Mandy Holbrook", "member", None, CU17, near=_cur),
        M("Darya Kurilova", "member", None, CU17, near=_cur, note="Darya Melicher in the 2020 capture"),
        M("Shing-hon Lau", "member", None, CU17, near=_cur),
        M("Bin Liu", "member", None, CU17, near=_cur),
        M("Billy Melicher", "member", None, CU17, near=_cur, note="also current in 2020 capture"),
        M("Alessandro Oltramari", "member", None, CU17, near=_cur),
        M("Emmanuel Owusu", "member", None, CU17, near=_cur),
        M("Ashwini Rao", "member", None, CU17, near=_cur),
        M("Florian Schaub", "member", None, CU17, near=_cur),
        M("Sean Segreti", "member", None, CU17, near=_cur),
        M("Stephen Siena", "member", None, CU17, near=_cur),
        M("Yuan Tian", "member", None, CU17, near=_cur),
        M("Tiffany Todd", "member", None, CU17, near=_cur, note="also current in 2020 capture"),
        M("Timothy Vidas", "member", None, CU17, near=_cur),
        M("Maggie Oates", "member", None, CU20, near=_cur),
        M("Kentrell Owens", "member", None, CU20, near=_cur),
        M("Mahmood Sharif", "member", None, CU20, near=_cur),
        M("Michelle Ling", "member", None, CU23, near=_cur),
        M("Ellie Young", "member", None, CU23, near=_cur),
        M("Omer Akgul", "member", None, CUA, near=_alum, note=_ali),
        M("Eman Alashwali", "member", None, CUA, near=_alum, note=_ali),
        M("Casey Canfield", "member", None, CUA, near=_alum, note=_ali),
        M("Miguel Flores", "member", None, CUA, near=_alum, note=_ali),
        M("McKenna McCall", "member", None, CUA, near=_alum, note=_ali),
        M("Andrea Miller", "member", None, CUA, near=_alum, note=_ali),
        M("Kyerra Norton", "member", None, CUA, near=_alum, note=_ali),
        M("Ama Sefah", "member", None, CUA, near=_alum, note=_ali),
        M("Chelse Swoopes", "member", None, CUA, near=_alum, note=_ali),
    ],
    pubs=[PUB("http://cups.cs.cmu.edu/", mode="auto",
              note="CUPS 'Projects and Selected Publications' list on the lab homepage (includes other members' papers)")],
    notes=("Cranor homepage Students section (live, 2017, 2023) gives her PhD advisees with years; CUPS lab "
           "(cups.cs.cmu.edu, directed by Cranor) lists current members (live, 2017, 2020, 2023 captures) and an "
           "undated alumni page. Faculty on CUPS lists skipped (Acquisti, Agarwal, Bauer, Christin, Downs, Hong, "
           "Sadeh, Savvides). Pedro Leon (EPP PhD 2014) and Rich Shay (COS PhD 2015) appear as current on the "
           "2017 CUPS capture but graduated before 2016 per Cranor's homepage: skipped. Pre-2016 graduated PhDs "
           "skipped (Balebako, Bravo Lillo, Egelman, Kelley, Kumaraguru, McDonald, Reeder, Sheng, Tsai, Vaniea) "
           "and the 45 names already in the 2017 capture's alumni list. Resume PDF (cranor-cv.pdf) not added."),
    blocked=[],
)

# ---------------------------------------------------------------- Laura Dabbish
CX = "http://coexlab.com/"
CX16 = WB + "20160106192856id_/http://coexlab.com:80/"
CX19 = WB + "20190119082509id_/http://coexlab.com:80/"
CX22 = WB + "20220124144522id_/http://coexlab.com/"
_ug = "Undergraduate Students"
D["Laura Dabbish"] = dict(
    lab_site="http://coexlab.com/",
    people_page=CX,
    people_pages=[CX, CX16, CX19, CX22],
    members=[
        M("Tianying Chen", "phd", None, CX, q="Tianying Chen PhD Student"),
        M("Isadora Krsek", "phd", None, CX, q="Isadora Krsek PhD Student",
          note="Research Assistant in the 2022 capture"),
        M("Kimi Wenzel", "phd", None, CX, q="Kimi Wenzel PhD Student",
          note="undergraduate RA from Summer 2020 per 2022 capture"),
        M("Hana Frluckaj", "staff", None, CX, q="Hana Frluckaj Research Associate"),
        M("Hong Shen", "staff", None, CX, q="Hong Shen Systems Scientist, HCII", note="listed under Lab Affiliates"),
        M("Daniel Klug", "staff", None, CX, q="Daniel Klug Systems Scientist, ISR", note="listed under Lab Affiliates"),
        M("Eddie Wang", "member", None, CX, q="Current Research Assistants Graduate Students Eddie Wang",
          note="graduate-student research assistant"),
        M("Rozay Chen", "undergraduate", None, CX, near=_ug),
        M("Sherry Chen", "undergraduate", None, CX, near=_ug),
        M("Leo Liu", "undergraduate", None, CX, near=_ug),
        M("Menghan Liu", "undergraduate", None, CX, near=_ug),
        M("Ria Manathkar", "undergraduate", None, CX, near=_ug),
        M("Chelsea Tang", "undergraduate", None, CX, near=_ug),
        M("Yuqi Qiu", "undergraduate", None, CX, near=_ug),
        M("Mansi Agarwal", "undergraduate", None, CX, q="Mansi Agarwal, Designer & Research Programmer",
          note="undergraduate alumna not in the 2022 capture's alumni list"),
        M("Bianca Caproni", "undergraduate", None, CX, q="Bianca Caproni, Summer Research Assistant",
          note="undergraduate alumna not in the 2022 capture's alumni list"),
        M("Jennifer Chou", "undergraduate", None, CX, q="Jennifer Chou, Summer Research Assistant",
          note="undergraduate alumna not in the 2022 capture's alumni list"),
        M("Emily Ding", "undergraduate", None, CX, q="Emily Ding, Designer & User Researcher",
          note="undergraduate alumna not in the 2022 capture's alumni list"),
        M("Anna Lieb", "undergraduate", None, CX, q="Anna Lieb, Summer Research Assistant",
          note="undergraduate alumna not in the 2022 capture's alumni list"),
        M("Anissa Patel", "undergraduate", None, CX, q="Anissa Patel, Summer Research Assistant",
          note="undergraduate alumna not in the 2022 capture's alumni list"),
        M("Ije Okafor", "masters", [2021, 2021], CX22, q="Ije Okafor, Spring 2021",
          note="MHCI Student per live alumni list"),
        M("Onyekachi Nwabueze", "masters", [2021, 2021], CX22, q="Onyekachi Nwabueze, Spring 2021",
          note="MHCI Student per live alumni list"),
        # 2016 capture (Jan 2016)
        M("Jason Tsay", "phd", None, CX16, q="Jason Tsay PhD Student"),
        M("Ruogu Kang", "phd", None, CX16, q="Ruogu Kang PhD Student",
          note="listed both as current PhD student and as former PhD student in the Jan 2016 capture"),
        M("Sauvik Das", "phd", None, CX16, q="Sauvik Das PhD Student"),
        M("Joseph Seering", "phd", None, CX16, q="Joseph Seering PhD Student"),
        M("Maria Tomprou", "staff", None, CX16, q="Maria Tomprou Project Scientist",
          note="Adjunct Faculty, Tepper on later pages"),
        M("Min Kyung Lee", "staff", None, CX16, q="Min Kyung Lee Research Scientist",
          note="listed as Postdoc in later alumni lists"),
        M("Bingrui Tang", "member", None, CX16, near="Current Research Assistants"),
        M("Evan Metsky", "member", None, CX16, near="Current Research Assistants",
          note="masters/undergraduate per 2019 'Recent Masters and Undergraduate Alumni'"),
        M("Prerna Chikersal", "masters", None, CX19, q="Prerna Chikersal, Masters Student",
          note="current research assistant in Jan 2016 capture"),
        M("Nathaniel Fruchter", "member", None, CX16, near="Current Research Assistants",
          note="masters/undergraduate per 2019 'Recent Masters and Undergraduate Alumni'"),
        M("Taryn Bipat", "member", None, CX16, near="Current Research Assistants",
          note="masters/undergraduate per 2019 'Recent Masters and Undergraduate Alumni'"),
        M("Tiffany Chen", "undergraduate", None, CX16, near="Current Research Assistants",
          note="undergraduate RA per 2019 alumni list"),
        # 2019 capture
        M("Fannie Liu", "phd", None, CX19, q="Fannie Liu PhD Student"),
        M("Joanna Lo", "member", None, CX19, near="Recent Masters and Undergraduate Alumni"),
        M("Thomas Rasmussen", "member", None, CX19, near="Recent Masters and Undergraduate Alumni"),
        M("Mikahla Vicino", "member", None, CX19, near="Recent Masters and Undergraduate Alumni"),
        # 2022 capture
        M("Cori Faklaris", "phd", None, CX22, q="Cori Faklaris PhD Student"),
        M("David Widder", "phd", None, CX22, q="David Widder PhD Student"),
        M("Junchao Lin", "staff", None, CX22, q="Junchao Lin Research Associate",
          note="David Junchao Lin on the live alumni list"),
        M("Allie Blaising", "staff", None, CX22, q="Allie Blaising Research Associate"),
        M("Magali Ngouabou", "undergraduate", [2020, None], CX22, q="Magali Ngouabou, Summer 2020 - Present"),
        M("Yumi Sato", "undergraduate", [2020, None], CX22, q="Yumi Sato, Summer 2020 - Present"),
        M("Serena Wang", "undergraduate", [2020, None], CX22, q="Serena Wang, Summer 2020 - Present"),
        M("Kristy Zhang", "undergraduate", [2020, None], CX22, q="Kristy Zhang, Summer 2020 - Present"),
        M("Erin Zhu", "undergraduate", [2020, 2020], CX22, q="Erin Zhu, Summer-Fall 2020"),
        M("Irene Yu", "member", None, CX22, q="Irene Yu, Research Assistant",
          note="graduate-section research assistant; not in the 2019 alumni list"),
        M("Dong Yun Lee", "undergraduate", None, CX22, q="Dong Yun Lee, Psychology",
          note="undergraduate alumna not in the 2019 alumni list"),
        M("Amrutha Palaniyappan", "undergraduate", None, CX22, q="Amrutha Palaniyappan, Economics & HCI",
          note="undergraduate alumna not in the 2019 alumni list"),
        M("Irene Chen", "undergraduate", None, CX22, q="Irene Chen, Summer Research Assistant",
          note="undergraduate alumna not in the 2019 alumni list"),
    ],
    pubs=[],
    notes=("CoEx Lab (coexlab.com) Team section, live plus Jan 2016/2019/2022 captures. No publications page "
           "(lab and lauradabbish.com point to Google Scholar only). Faculty skipped: Geoff Kaufman (lab "
           "affiliate). Alumni already listed as former in the Jan 2016 capture and never current later are "
           "skipped as pre-2016 (Mary Nguyen, Jennifer Marlow, Tatiana Vlahovic, Mirae Kim, Zheng Yao and 11 "
           "undergraduates: Bakyal, Chakrasali, Crawford, Gopalakrishnan, He, Kusbit, A. Liu, Mullins, Sutton, "
           "Wier, L. Yang)."),
    blocked=[],
)

# ---------------------------------------------------------------- Roger Dannenberg
CMP = "https://www.cs.cmu.edu/~music/cmp/index.html"
CMT = "https://www.cs.cmu.edu/~music/cmp/theses.html"
MU = "https://www.cs.cmu.edu/~music"
MU17 = WB + "20170309124046id_/http://www.cs.cmu.edu:80/~music/"
MU23 = WB + "20230326213035id_/https://www.cs.cmu.edu/~music/"
_ms = "Masters Theses"
D["Roger Dannenberg"] = dict(
    lab_site="https://www.cs.cmu.edu/~music/cmp/index.html",
    people_page=CMP,
    people_pages=[CMP, CMT, MU, WB + "20160219071833id_/http://www.cs.cmu.edu:80/~music/", MU17,
                  WB + "20200106222524id_/http://www.cs.cmu.edu:80/~music/", MU23],
    members=[
        M("Shuqi Dai", "phd", None, CMP, q="Shuqi Dai PhD Candidate, Computer Science Department"),
        M("Anders Øland", "phd", [None, 2024], CMT, q="Ph.D. Theses Anders Øland (2024)",
          note="graduate student on the 2016-2023 Computer Music Group captures"),
        M("Gus Xia", "phd", None, MU17, q="Gus Xia Graduate Student, Machine Learning Department"),
        M("Huiran Yu", "masters", [None, 2022], CMT, near=_ms,
          note="MSCS thesis 2022; listed as Graduate Student, Computer Science Department on the 2023 capture"),
        M("Ari Liloia", "masters", [None, 2025], CMT, near=_ms),
        M("Hanzhi Yin", "masters", [None, 2023], CMT, near=_ms),
        M("Yuxuan Wu", "masters", [None, 2023], CMT, near=_ms),
        M("Ruibin Yuan", "masters", [None, 2023], CMT, near=_ms),
        M("Zheng Jiang", "masters", [None, 2019], CMT, near=_ms),
        M("Anirudh Mani", "masters", [None, 2019], CMT, near=_ms),
        M("Andrew Russell", "masters", [None, 2018], CMT, near=_ms),
        M("Che-Yuan Liang", "masters", [None, 2018], CMT, near=_ms),
        M("Hao Huang", "masters", [None, 2017], CMT, near=_ms),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~rbd/bib.html", mode="auto")],
    notes=("Computer Music Project (cs.cmu.edu/~music/cmp) People + Theses pages; Computer Music Group page "
           "(~music) live and 2016/2017/2020/2023 captures. Skipped: faculty Tom Cortina, Chris Donahue; external "
           "collaborator Jorge Sastre (UPV); Ning Hu (PhD 2013, stale 'Graduate Student' entry); pre-2016 theses "
           "(Brandt, Thom, Grubb, Rubine; MS Liu 2014, Cheng, Tang, Jin 2013, Liang 2012); the undated "
           "alumni/associates picture board (Brandt, Burdell, Lee, Kim, Cohen, Mazzoni, Neuendorffer, Srihari, "
           "Stanchak, Thom, Murray, Rho, Simsekli, Tzanetakis, Williams, Xu, Y. Liu: 17) which is unchanged since "
           "the Feb 2016 capture, so no evidence of 2016+ presence."),
    blocked=[],
)

# ---------------------------------------------------------------- Sauvik Das
SP = "https://cmu-spuds.github.io/people/"
SP25 = WB + "20250122034341id_/https://cmu-spuds.github.io/cmu-spuds-web/people/"
D["Sauvik Das"] = dict(
    lab_site="https://cmu-spuds.github.io/",
    people_page=SP,
    people_pages=[SP, SP25, "http://sauvik.me/students"],
    members=[
        M("Hao-Ping (Hank) Lee", "phd", [2021, None], SP, q="Hao-Ping (Hank) Lee AI Privacy CMU Ph.D. 2021-present"),
        M("Isadora Krsek", "phd", [2022, None], SP,
          q="Isadora Krsek NLP for privacy, S&P for IPV Professionals CMU Ph.D. 2022-present"),
        M("Kyzyl Monteiro", "phd", [2023, None], SP,
          q="Kyzyl Monteiro Intelligent agents for security CMU Ph.D. 2023-present"),
        M("William Agnew", "postdoc", [2023, None], SP, q="William Agnew Community-centered AI CMU Postdoc 2023-present"),
        M("Yuxuan Li", "phd", [2024, None], SP, q="Yuxuan Li Social agent simulation & policy CMU Ph.D. 2024-present"),
        M("Bill Watson", "phd", [2026, None], SP, q="Bill Watson CMU Ph.D. 2026-present"),
        M("Yasmeen Galle", "member", [2025, None], SP,
          q="Yasmeen Galle S&P for IPV Professionals Research Assistant Summer 2025-present", note="Research Assistant"),
        M("Daniel Amon-Kotey", "member", [2025, None], SP,
          q="Daniel Amon-Kotey NLP for Privacy Research Assistant Summer 2025-present", note="Research Assistant"),
        M("Iris Yin", "member", [2026, None], SP,
          q="Iris Yin Cybersecurity Behavior Interventions Research Assistant Spring 2026-present", note="Research Assistant"),
        M("Anirudh Janapati", "member", [2026, None], SP,
          q="Anirudh Janapati Interventions to Protect Against AI-powered NCII Research Assistant Fall 2026-present",
          note="Research Assistant"),
        M("Eddie Liu", "member", [2026, None], SP,
          q="Eddie Liu Interventions to Protect Against AI-powered NCII Research Assistant Fall 2026-present",
          note="Research Assistant"),
        M("Jeffrey Wang", "member", [2026, None], SP,
          q="Jeffrey Wang NLP for Privacy Research Assistant Fall 2026-present", note="Research Assistant"),
        M("Sadhil Mehta", "member", [2026, None], SP,
          q="Sadhil Mehta Interventions to Protect Against AI-powered NCII Research Assistant Fall 2026-present",
          note="Research Assistant"),
    ],
    pubs=[PUB("http://sauvik.me/papers.json", mode="json",
              note="data file behind sauvik.me/publications (React page)")],
    notes=("SPUD Lab (cs.cmu.edu/~spudlab -> cmu-spuds.github.io) people page, live and Jan 2025 capture; "
           "sauvik.me/students holds the same list in React props. Das joined CMU in 2022 from Georgia Tech: "
           "Jacob Logas, Youngwook Do and Yuxi Wu are labelled 'GT Ph.D.' and skipped (no CMU placement). "
           "SPUD /publications page parses poorly (auto picks author/venue anchors); used papers.json instead."),
    blocked=[],
)

# ---------------------------------------------------------------- Tim Dettmers
TD = "https://timdettmers.com/about/"
D["Tim Dettmers"] = dict(
    lab_site="https://timdettmers.com/about/",
    people_page=TD,
    people_pages=[TD, WB + "20260109065940id_/https://timdettmers.com/about/"],
    members=[
        M("Eulrang Cho", "member", None, TD, near="Group"),
        M("Trang Nguyen", "member", None, TD, near="Group"),
        M("Vladimir Malinovskii", "member", None, TD, near="Group"),
        M("Christine Park", "member", None, TD, near="Group"),
    ],
    pubs=[],
    notes=("No lab website; the 'Group' section of his personal site (live and Jan 2026 capture, identical) lists "
           "four names without roles. Earlier captures predate his CMU appointment (UW PhD). Publications: the "
           "site points to Google Scholar only, so no page added."),
    blocked=[],
)

# ---------------------------------------------------------------- Anind Dey
HD17 = WB + "20170101215343id_/http://www.hcii.cmu.edu/people/anind-dey"
D["Anind Dey"] = dict(
    lab_site="http://anind.cmubi.org/",
    people_page=HD17,
    people_pages=[HD17, WB + "20180128163609id_/http://anind.cmubi.org:80/site/Students/Students",
                  WB + "20100111042036id_/http://anind.cmubi.org:80/site/Students/Students",
                  "http://www.cs.cmu.edu/~anind/past_students.html"],
    members=[
        M("Julian Ramos Rojas", "phd", None, HD17, near="Advisees"),
        M("Adrian de Freitas", "phd", None, HD17, near="Advisees"),
        M("Brandon Taylor", "phd", None, HD17, near="Advisees"),
        M("Nikola Banovic", "phd", None, HD17, near="Advisees"),
    ],
    pubs=[],
    notes=("Dey left CMU for UW in 2018. His cs.cmu.edu/~anind homepage and its publications list stop in 2010 "
           "(no in-window papers, not added); past_students.html covers 2005-2008 only. His group site "
           "anind.cmubi.org (DNS dead) has a Students page whose 2018 capture is byte-identical in content to the "
           "2010 capture (Davidoff, M. Lee, I. Li, Lim, Rosenthal, Ziebart, postdocs Hong, Kim, Wac, Yang), i.e. "
           "stale, so not recorded. Members taken from the 'Advisees' list on his HCII profile (Jan 2017 capture); "
           "advisees are labelled only as advisees (PhD students per HCII)."),
    blocked=[],
)

# ---------------------------------------------------------------- Mona Diab
MD = "https://lti.cmu.edu/people/faculty/diab-mona.html"
D["Mona Diab"] = dict(
    lab_site=None,
    people_page=MD,
    people_pages=[MD, WB + "20250214234751id_/https://lti.cmu.edu/people/faculty/diab-mona.html"],
    members=[
        M("Karina Halevy", "member", None, MD, near="Advisees"),
        M("Andy Liu", "member", None, MD, near="Advisees"),
        M("Nishant Subramani", "member", None, MD, near="Advisees"),
        M("Jiarui Liu", "member", None, MD, near="Advisees"),
        M("Neemesh Yadav", "member", None, MD, near="Advisees"),
    ],
    pubs=[],
    notes=("Diab directs the R3LIT Lab at CMU (since 2023) but no lab website was found (LTI profile has no link; "
           "web search found none). Members from the 'Advisees' list on her LTI profile (live; the Feb 2025 capture "
           "has no advisees section). Skipped Rana Salama (GWU) and Amal AlQahtani (GWU), students from her "
           "previous institution. No publications page (Google Scholar only)."),
    blocked=[],
)

# ---------------------------------------------------------------- John M Dolan
DP = "https://drive-lab-cmu.github.io/people/"
RI = "https://www.ri.cmu.edu/robotics-groups/driverless-intelligent-vehicles-lab/"
D["John M Dolan"] = dict(
    lab_site="https://drive-lab-cmu.github.io/",
    people_page=DP,
    people_pages=[DP, RI],
    members=[
        M('Juan Rodolfo Alvarez-Padilla', 'phd', None, DP, q='Juan Rodolfo Alvarez-Padilla MIT AeroAstro PhD 2026 ECE PhD 2022-2025', note='co-advised with Zachary Manchester; ECE PhD 2022-2025'),
        M('Mohammed Alsakabi', 'phd', [2023, None], DP, q='Mohammed Alsakabi ECE PhD 2023', note='co-advised with Ozan Tonguz'),
        M('Maitham F. AL-Sunni', 'phd', [2024, None], DP, q='Maitham F. AL-Sunni ECE PhD 2024'),
        M('Henry Z. Liao', 'masters', [2025, None], DP, q='Henry Z. Liao RI MS 2025'),
        M('Myra Cropper', 'masters', [2025, None], DP, q='Myra Cropper ECE MS 2025', note='co-advised with Ozan Tonguz'),
        M('Sebin Jung', 'staff', [2024, 2026], DP, q='Sebin Jung Research Assistant 2026 MechE MS 2024-2026', note='research assistant 2026, MechE MS 2024-2026; co-advised with Changliu Liu'),
        M('Qin Lin', 'postdoc', [2019, 2022], DP, q='Qin Lin (2019-2022)'),
        M('Simin Liu', 'phd', [2020, 2025], DP, q='Simin Liu (RI PhD 2020-2025)'),
        M('Adam Villaflor', 'phd', [2018, 2024], DP, q='Adam Villaflor (RI PhD 2018-2024)'),
        M('Yiwei Lyu', 'phd', [2019, 2025], DP, q='Yiwei Lyu (ECE PhD 2019-2025)'),
        M('Chen Fu', 'phd', [2018, 2022], DP, q='Chen Fu (ECE PhD 2018-2022)'),
        M('Zhiqian Qiao', 'phd', [2016, 2021], DP, q='Zhiqian Qiao (ECE PhD 2016-2021)'),
        M('Chris Tomaszewski', 'phd', [2014, 2020], DP, q='Chris Tomaszewski (RI PhD 2014-2020)'),
        M('Chiyu Dong', 'phd', [2014, 2019], DP, q='Chiyu Dong (ECE PhD 2014-2019)'),
        M('Wenda Xu', 'phd', [2013, 2019], DP, q='Wenda Xu (ECE PhD 2013-2019)'),
        M('Tianyu Gu', 'phd', [2012, 2017], DP, q='Tianyu Gu (ECE PhD 2012-2017)'),
        M('Corey Ippolito', 'phd', [2011, 2016], DP, q='Corey Ippolito (ECE PhD 2011-2016)'),
        M('Junqing Wei', 'phd', [2008, 2017], DP, q='Junqing Wei (ECE PhD 2008-2017)'),
        M('Yogita Choudhary', 'masters', [2023, 2025], DP, q='Yogita Choudhary (RI MS 2023-2025)'),
        M('Wenli Xiao', 'masters', [2023, 2025], DP, q='Wenli Xiao (RI MS 2023-2025)'),
        M('Kai S. Yun', 'masters', [2023, 2025], DP, q='Kai S. Yun (MechE MS 2023-2025)'),
        M('Dvij Kalaria', 'masters', [2022, 2024], DP, q='Dvij Kalaria (RI MS 2022-2024)'),
        M('Haoru Xue', 'masters', [2022, 2024], DP, q='Haoru Xue (RI MS 2022-2024)'),
        M('Antonio Artuñedo', 'visitor', [2026, 2026], DP, q='Antonio Artuñedo (2026) Tenured Scientist', note='visiting scholar'),
        M('Yuning Wang', 'visitor', [2024, 2024], DP, q='Yuning Wang (2024) PhD', note='visiting scholar'),
        M('Naa Korkoi Addo', 'visitor', [2025, 2025], DP, q='Naa Korkoi Addo (2025) PhD', note='visiting scholar'),
        M('Fan Zhang', 'visitor', [2024, 2024], DP, q='Fan Zhang (2024) PhD', note='visiting scholar'),
        M('Saba Tsirekidze', 'undergraduate', [2026, 2026], DP, q='Saba Tsirekidze (RISS 2026)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('William Muckelroy III', 'undergraduate', [2025, 2025], DP, q='William Muckelroy III (RISS 2025)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Tianhao Wu', 'undergraduate', [2025, 2025], DP, q='Tianhao Wu (2025)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Paul Schulte', 'undergraduate', [2024, 2024], DP, q='Paul Schulte (RISS 2024)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Teodor Tchalakov', 'undergraduate', [2024, 2024], DP, q='Teodor Tchalakov (RISS 2024)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Chase Dunaway', 'undergraduate', [2024, 2024], DP, q='Chase Dunaway (RISS 2024)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Caleb Chang', 'undergraduate', [2022, 2022], DP, q='Caleb Chang (RISS 2022)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Andres Reyes', 'undergraduate', [2026, 2026], DP, q='Andres Reyes (RISS 2026)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Timeea-Andreea Radu', 'undergraduate', [2025, 2025], DP, q='Timeea-Andreea Radu (RISS 2025)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Devodita Chakravarty', 'undergraduate', [2025, 2025], DP, q='Devodita Chakravarty (2025)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Kevin Chen', 'undergraduate', [2024, 2025], DP, q='Kevin Chen (RISS 2024-2025)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Hojune Kim', 'undergraduate', [2024, 2024], DP, q='Hojune Kim (RISS 2024)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Nathan Ludlow', 'undergraduate', [2023, 2023], DP, q='Nathan Ludlow (RISS 2023)', note='Robotics Institute Summer Scholars / undergraduate visitor'),
        M('Ann-Sophie Allgaier', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Sohaib Bantan', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Parag Batavia', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Kritan Bhandari', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Ishaan Bhimwal', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Xintong Du', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Gerardo Lara Fabian', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Kanami Fukuoka', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Malgorzata Gwiazda', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Evelyn Lorena Moncayo Gómez', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Syed Ali-Naqi Hasnain', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Hongyi Hu', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Iulia Iordanescu', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Piotr Kacprzak', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Emilia Kaczmarczyk', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Bartłomiej Kamiński', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Madhav Khanal', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Padmaksh Khandelwal', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Daniel Kim', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Taekyung Lee', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Cheryl Li', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Ryan Lu', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Moe Myint Myat Maung', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Adam Mazur', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Karol Musielinski', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Jedrzej Jakub Ogrodowski', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Michal Paradowski', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Quinn Pfeifer', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Juan Robles', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Szymon Rusiecki', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Mohammad Saatialsoruji', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Jumpei Saito', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Gaurav Sharma', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Grant Stec', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Ryosei Tamura', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('William Valentine', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Mikolaj Wozniak', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Kaoru Yoshida', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Michal Zmyslowski', 'staff', None, RI, near='current staff', note="listed under 'current staff' on the RI lab page (undated roster)"),
        M('Bowen Li', 'member', None, RI, near='current student', note="listed under 'current student' on the RI lab page (undated roster)"),
        M('Radhika Mohanan', 'masters', None, RI, near='current student', note="listed under 'current student' on the RI lab page (undated roster)"),
        M('Yanjun Pan', 'masters', None, RI, near='current student', note="listed under 'current student' on the RI lab page (undated roster)"),
        M('Jesica Rosaline', 'member', None, RI, near='current student', note="listed under 'current student' on the RI lab page (undated roster)"),
        M('Xuning Ying', 'member', None, RI, near='current student', note="listed under 'current student' on the RI lab page (undated roster)"),
        M('Zherui Zhang', 'masters', None, RI, near='current student', note="listed under 'current student' on the RI lab page (undated roster)"),
        M('Jing Zhao', 'masters', None, RI, near='current student', note="listed under 'current student' on the RI lab page (undated roster)"),
    ],
    pubs=[PUB("https://drive-lab-cmu.github.io/publications/", mode="auto")],
    notes=("DRIVE Lab site drive-lab-cmu.github.io (found via the 'Visit External Site' link on the RI lab page "
           "ri.cmu.edu/robotics-groups/driverless-intelligent-vehicles-lab/; the input had no lab_url). Live people page "
           "gives current members, post-docs, PhD, MS, visiting scholars and RISS undergraduates with years; recorded all "
           "whose stated dates overlap 2016-2026. The RI lab page adds 'current staff' (about 40 summer/visiting project "
           "staff, undated) and 'current student' lists, recorded as listed (live page counts as current); duplicates of the "
           "DRIVE page were recorded once. Skipped: Rachel Burcin (RISS programme director, not a lab member); alumni whose "
           "dates ended before 2016 (post-docs Navarro-Serment, Althoff, Liang, Sahin, Salido, Trebi-Ollennu; PhDs Baker, "
           "Stancliff, Low, Rachlin, Tangamchit, Navarro-Serment, Soto); 'MS' alumni with no dates (about 25, e.g. Tom Bu, "
           "Pranay Agrawal, Haiyue Li, Aman Khurana, Adam Werries, Aaron Huang) and RI 'past members' (Solomon Fenton, Jack Henry "
           "Good, Guanqi He, Ronit Hire, Rolanda Hutson, Muhan Lin) because none was seen current in a 2016+ capture; "
           "co-advisors (Zachary Manchester, Ozan Tonguz, Changliu Liu) are faculty. Publications: DRIVE publications page "
           "(bold-title mode, 8 missing from the PI's lab papers). No Wayback captures were read (archive.org was in back-off)."),
    blocked=[],
)

# ---------------------------------------------------------------- Chris Donahue
GC = "https://gclef-cmu.org/team/"
D["Chris Donahue"] = dict(
    lab_site="https://gclef-cmu.org/",
    people_page=GC,
    people_pages=[GC],
    members=[
        M("Wayne Chi", "phd", None, GC, q="Wayne Chi Ph.D. Student"),
        M("Irmak Bukey", "phd", None, GC, q="Irmak Bukey Ph.D. Student"),
        M("Yewon Kim", "phd", None, GC, q="Yewon Kim Ph.D. Student"),
        M("Nathan Pruyne", "phd", None, GC, q="Nathan Pruyne Ph.D. Student"),
        M("Alexander Wang", "phd", None, GC, q="Alexander Wang Ph.D. Student"),
        M("Satvik Dixit", "phd", None, GC, q="Satvik Dixit Ph.D. Student"),
        M("Lynn Ye", "masters", None, GC, q="Lynn Ye MS Student"),
        M("Louis Bradshaw", "visitor", None, GC, near="Alumni", note="alumni, visiting researcher"),
        M("Yichen (William) Huang", "visitor", None, GC, near="Alumni", note="alumni, visiting researcher"),
        M("Xun (Rick) Zhou", "masters", None, GC, near="Alumni", note="alumni, MS student"),
        M("Shih-Lun Wu", "masters", None, GC, near="Alumni", note="alumni, MS student"),
    ],
    pubs=[PUB("https://chrisdonahue.com/publication/", mode="auto")],
    notes=("Lab is the Generative Creativity Lab (G-CLef) at gclef-cmu.org, linked from the PI homepage chrisdonahue.com; "
           "its team page (live) lists faculty, current students and alumni. Donahue joined CMU in 2023, so the undated "
           "alumni (two visiting researchers, two MS students) all fall in the window and are recorded. Skipped the PI. "
           "The PI homepage has no student list (news items mention Wayne Chi, co-advised with Ameet Talwalkar). Other "
           "discovered pages: Annie Hsieh (CMU School of Music, collaborator) and Michael Feffer (acmilab.org, SSL error) are "
           "collaborators, not group members. Publications: chrisdonahue.com/publication/ (17 missing from the PI's lab "
           "papers; the team site's research pages are per-project and were not added). Wayback was in back-off and not needed."),
    blocked=["https://acmilab.org/ (SSL certificate error)"],
)

# ---------------------------------------------------------------- Anupam Datta
FA = "http://fairlyaccountable.org/"
FA18 = WB + "20180809192932id_/http://fairlyaccountable.org/"
AN = WB + "20260713024244id_/https://www.andrew.cmu.edu/user/danupam/research.html"
D["Anupam Datta"] = dict(
    lab_site="http://fairlyaccountable.org/",
    people_page=FA,
    people_pages=[FA, FA18, AN],
    members=[
        M("Matt Fredrikson", "other", None, FA, q="Matt Fredrikson (prof.)", note="faculty co-PI, listed for completeness only; not a student"),
        M("Piotr Mardziel", "staff", None, FA, q="Piotr Mardziel (systems scientist)", note="postdoc on the 2018 capture, systems scientist live"),
        M("Arthur Azevedo de Amorim", "postdoc", None, FA, q="Arthur Azevedo de Amorim (postdoc)", note="spelled 'Amorin' on the Datta homepage"),
        M("Shayak Sen", "phd", None, FA18, q="Shayak Sen (PhD student)", note="PhD student on the 2018 capture, postdoc on live page"),
        M("Gihyuk Ko", "phd", None, FA, q="Gihyuk Ko (PhD student)"),
        M("Sophia Kovaleva", "phd", None, FA, q="Sophia Kovaleva (PhD student)"),
        M("Klas Leino", "phd", None, FA, q="Klas Leino (PhD student)"),
        M("Samuel Yeom", "phd", None, FA, q="Samuel Yeom (PhD student)"),
        M("Caleb Kaiji Lu", "phd", None, FA, q="Caleb Kaiji Lu (PhD student)"),
        M("Emily Black", "phd", None, FA, q="Emily Black (PhD student)"),
        M("Han Zhang", "phd", None, FA, q="Han Zhang (PhD student)"),
        M("Amit Datta", "phd", [None, 2018], AN, q="Amit Datta (ECE PhD 2018; Snap Inc.)", note="alumni entry"),
    ],
    pubs=[],
    notes=("Lab = Accountable Systems Lab (fairlyaccountable.org, linked from the PI homepage andrew.cmu.edu/user/danupam; "
           "the PI's CSD profile 404s). People list read live and on the Aug 2018 capture (the 2021 capture is identical to live); "
           "Datta homepage 'Students & Postdocs' read via Wayback (Mar 2026 capture of an old page): PhD students Ko, Kovaleva, Caleb Lu, "
           "Shayak Sen, postdocs Azevedo de Amorin, Mardziel, alumni list. Fredrikson recorded as role other (faculty), not a student. "
           "Skipped alumni with pre-2016 dates (Garg, Jia, Franklin, Tschantz, Kaynar, Blocki, Sinha, Chowdhury, Divya Sharma 2015) and undated "
           "Yair Zick (faculty at NUS; undated, never seen as current in a 2016+ capture). Pubs: Datta publications.html parses to bold "
           "headings with no years (nothing usable); fairlyaccountable.org lists only 4 papers inline, not added."),
    blocked=[],
)
