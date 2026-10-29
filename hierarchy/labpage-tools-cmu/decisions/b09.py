from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Geoffrey J Gordon
GG = "http://www.cs.cmu.edu/~ggordon/students.html"
D["Geoffrey J Gordon"] = dict(
    lab_site="http://www.cs.cmu.edu/~ggordon/",
    people_page=GG,
    people_pages=[GG],
    members=[
        M("Carlton Downey", "phd", None, GG, near="I am advising the students:", note="co-advised with Steve Fienberg"),
        M("Ahmed Hefny", "phd", None, GG, near="I am advising the students:"),
        M("Shiva Kaul", "phd", None, GG, near="I am advising the students:"),
        M("Zita Marinho", "phd", None, GG, near="I am advising the students:", note="co-advised with Sidd Srinivasa"),
        M("Renato Negrinho", "phd", None, GG, near="I am advising the students:"),
        M("Erik Zawadzki", "phd", None, GG, near="I am advising the students:", note="co-advised with Andre Platzer"),
        M("Han Zhao", "phd", None, GG, near="I am advising the students:"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~ggordon/", mode="auto")],
    notes="Group is the SELECT lab (no separate site). students.html is a static page whose 2017, 2020 and 2023 Wayback "
          "captures show the same 'currently advising' list (7 students, last updated ~2018); recorded as current. Former "
          "advisees (Boots, Chi, Dudik etc.) and committee-only students are undated or pre-2016 and were skipped; "
          "committee-only names are not members. Homepage lists papers inline (pubs added; matched 11, missing 5 in preview).",
    blocked=[],
)

# ---------------------------------------------------------------- Mayank Goel
MG = "https://mynkgoel.github.io/"
D["Mayank Goel"] = dict(
    lab_site="https://mynkgoel.github.io/",
    people_page=MG,
    people_pages=[MG],
    members=[
        M("Riku Arakawa", "phd", None, MG, near="Current Ph.D. Students"),
        M("Shreya Bali", "phd", None, MG, near="Current Ph.D. Students"),
        M("Seungjoo Lee", "phd", None, MG, near="Current Ph.D. Students"),
        M("Ayush Shrivastava", "phd", None, MG, near="Current Ph.D. Students"),
        M("Siqi Zhang", "phd", None, MG, near="Current Ph.D. Students"),
        M("Haozhe Zhou", "phd", None, MG, near="Current Ph.D. Students"),
        M("Rishiraj Adhikary", "phd", None, MG, near="Ph.D. Alumni", note="alumni, undated; PI at CMU since 2016"),
        M("Karan Ahuja", "phd", None, MG, near="Ph.D. Alumni", note="alumni, undated"),
        M("Abdelkareem Bedri", "phd", None, MG, near="Ph.D. Alumni", note="alumni, undated"),
        M("Prerna Chikersal", "phd", None, MG, near="Ph.D. Alumni", note="alumni, undated"),
        M("Rushil Khurana", "phd", None, MG, near="Ph.D. Alumni", note="alumni, undated"),
        M("Julian Ramos", "phd", None, MG, near="Ph.D. Alumni", note="alumni, undated"),
    ],
    pubs=[PUB("https://mynkgoel.github.io/publications", mode="auto")],
    notes="SMASH Lab; old mayankgoel.com redirects (http://www.mayank.prof) to mynkgoel.github.io. Page lists only PhD students "
          "(no masters/undergrads/postdocs). Alumni undated; Goel joined CMU in 2016 so all alumni are in window. Wayback "
          "captures of the site were read: 2020 is an empty page and 2024 has no student list; the 2019 frame-site capture hit wayback-backoff, so older members are not recorded.",
    blocked=[],
)

# ---------------------------------------------------------------- Cleotilde Gonzalez
CUR = "https://www.cmu.edu/dietrich/sds/ddmlab/people/index.html"
PAST = "https://www.cmu.edu/dietrich/sds/ddmlab/people/past-members.html"
D['Cleotilde Gonzalez'] = dict(
    lab_site='https://www.cmu.edu/dietrich/sds/ddmlab/',
    people_page=CUR,
    people_pages=[CUR, PAST],
    members=[
        M('Xiaohong Cai', 'postdoc', None, CUR, q='Xiaohong Cai, Ph.D. Post-Doctoral Fellow'),
        M('Grace Roessling', 'postdoc', None, CUR, q='Grace Roessling, Ph.D. Post-Doctoral Fellow'),
        M('Jeffrey Flagg', 'staff', None, CUR, q='Jeffrey Flagg, M.S. Lab Manager - Research Associate II'),
        M('Kibo Schaffer', 'staff', None, CUR, q='Kibo Schaffer Research Programmer'),
        M('Yuchen Li', 'staff', None, CUR, q='Yuchen Li, M.S. Research Assistant'),
        M('Maha Alosaimi', 'phd', None, CUR, q='Maha Alosaimi, M.S. PhD Student'),
        M('Bodhisattva Das', 'masters', None, CUR, q='Bodhisattva Das Student Research Assistant'),
        M('Vlad Miloserdov', 'undergraduate', None, CUR, q='Vlad Miloserdov Student Research Assistant'),
        M('Jet Jacobsen', 'visitor', None, CUR, q='Jet Jacobsen Visiting Research Associate'),
        M('Kent Grass-Valdivia', 'masters', None, CUR, q='Kent Grass-Valdivia Student Research Assistant'),
        M('Jinfeng Lou', 'postdoc', None, CUR, q='Jinfeng Lou, Ph.D. Research Associate'),
        M('Maria Ferreira', 'postdoc', [2023, 2025], PAST, q='Maria Ferreira, Ph.D. April 2023 to December 2025'),
        M('Tailia Malloy', 'postdoc', [2022, 2025], PAST, q='Tailia Malloy, Ph.D. December 2022 to July 2025'),
        M('Roderick Seow', 'postdoc', [2023, 2025], PAST, q='Roderick Seow, Ph.D. September 2023 to February 2025'),
        M('Ngoc Nguyen', 'postdoc', [2019, 2023], PAST, q='Ngoc Nguyen, Ph.D. October 2019 to March 2023'),
        M('Baptiste Prebot', 'postdoc', [2021, 2023], PAST, q='Baptiste Prebot, Ph.D. October 2021 to March 2023'),
        M('Nhat Phan', 'postdoc', [2021, 2022], PAST, q='Nhat Phan, Ph.D. March 2021 to August 2022'),
        M('Palvi Aggarwal', 'postdoc', [2018, 2021], PAST, q='Palvi Aggarwal, Ph.D. September 2018 to August 2021'),
        M('Kuldeep Singh', 'postdoc', [2019, 2021], PAST, q='Kuldeep Singh, Ph.D. April 2019 to August 2021'),
        M('Farnaz Tehranchi', 'postdoc', [2020, 2021], PAST, q='Farnaz Tehranchi, Ph.D. October 2020 to August 2021'),
        M('Hanshu Zhang', 'postdoc', [2019, 2020], PAST, q='Hanshu Zhang, Ph.D. September 2019 to July 2020'),
        M('Korosh Mahmoodi', 'postdoc', [2018, 2020], PAST, q='Korosh Mahmoodi, Ph.D. September 2018 to May 2020'),
        M('Pegah Fakhari', 'postdoc', [2018, 2018], PAST, q='Pegah Fakhari, Ph.D. February 2018 to December 2018'),
        M('Prashnanth Rajivan', 'postdoc', [2015, 2018], PAST, q='Prashnanth Rajivan, Ph.D. December 2015 to August 2018'),
        M('Efrat Aharonov', 'postdoc', [2016, 2018], PAST, q='Efrat Aharonov, Ph.D. August 2016 to August 2018'),
        M('Jeffrey Chrabaszcz', 'postdoc', [2016, 2017], PAST, q='Jeffrey Chrabaszcz, Ph.D. August 2016 to September 2017'),
        M('Michael Yu', 'postdoc', [2014, 2017], PAST, q='Michael Yu, Ph.D. May 2014 to May 2017'),
        M('Marko Morrison', 'phd', [2025, 2026], PAST, q='Marko Morrison May 2025 to August 2026'),
        M('Aarya Bhave', 'undergraduate', [2026, 2026], PAST, q='Aarya Bhave Summer 2026'),
        M('Raghav Sharma', 'member', [2026, 2026], PAST, q='Raghav Sharma Summer 2026'),
        M('Don Morrison', 'staff', [2017, 2026], PAST, q='Don Morrison January 2017 to May 2026'),
        M('Anu Aggarwal', 'staff', [2024, 2025], PAST, q='Anu Aggarwal, M.S. January 2024 to December 2025'),
        M('Selena Zheng', 'undergraduate', [2025, 2025], PAST, q='Selena Zheng June 2025 to August 2025'),
        M('Yinuo Du', 'phd', [2020, 2025], PAST, q='Yinuo Du September 2020 to August 2025'),
        M('Erin Bugbee', 'phd', [2020, 2025], PAST, q='Erin Bugbee September 2020 to May 2025'),
        M('Chase McDonald', 'phd', [2020, 2025], PAST, q='Chase McDonald September 2020 to May 2025'),
        M('Saketh Mudundi', 'masters', [2024, 2025], PAST, q='Saketh Mudundi October 2024 to May 2025'),
        M('Sophie Ding', 'undergraduate', [2024, 2025], PAST, q='Sophie Ding November 2024 to May 2025'),
        M('Duncan Wood', 'phd', [2023, 2024], PAST, q='Duncan Wood August 2023 to December 2024'),
        M('Arya Mane', 'undergraduate', [2024, 2024], PAST, q='Arya Mane January to December 2024'),
        M('Carlos Botelho', 'member', [2022, 2023], PAST, q='Carlos Botelho July 2022 to July 2023'),
        M('Tony Xi', 'masters', [2021, 2022], PAST, q='Tony Xi September 2021 to December 2022'),
        M('Erin McCormick', 'phd', [2015, 2022], PAST, q='Erin McCormick August 2015 to May 2022'),
        M('Wenjia (Jiajia) Hu', 'member', [2021, 2022], PAST, q='Wenjia (Jiajia) Hu September 2021 to May 2022'),
        M('Ed Matlack', 'visitor', [2021, 2022], PAST, q='Ed Matlack October 2021 to May 2022'),
        M('Miso Demko', 'undergraduate', [2021, 2021], PAST, q='Miso Demko August 2021 to December 2021'),
        M('Aditya Gulati', 'member', [2020, 2021], PAST, q='Aditya Gulati June 2020 to August 2021'),
        M('Disha Das', 'undergraduate', [2020, 2021], PAST, q='Disha Das September 2020 to January 2021'),
        M('Alison Butler', 'member', [2019, 2020], PAST, q='Alison Butler September 2019 to May 2020'),
        M('Peijie He', 'undergraduate', [2019, 2020], PAST, q='Peijie He September 2019 to May 2020'),
        M('Max Gamerman', 'undergraduate', [2019, 2020], PAST, q='Max Gamerman September 2019 to May 2020'),
        M('Andrew Ye', 'undergraduate', [2019, 2020], PAST, q='Andrew Ye September 2019 to May 2020'),
        M('Max Yeh', 'undergraduate', [2019, 2020], PAST, q='Max Yeh September 2019 to May 2020'),
        M('Orsi Kovacs', 'member', [2019, 2020], PAST, q='Orsi Kovacs September 2019 to May 2020'),
        M('David Hagmann', 'postdoc', [2014, 2018], PAST, q='David Hagmann, Ph.D. 2014 to 2018'),
        M('Cristobal De La Maza Guzman', 'postdoc', [2014, 2018], PAST, q='Cristobal De La Maza Guzman, Ph.D. 2014 to 2018'),
        M('Qiao Shen', 'undergraduate', [2018, 2018], PAST, q='Qiao Shen Fall 2018'),
        M('Sabina Sloman', 'phd', [2017, 2018], PAST, q='Sabina Sloman 2017 to 2018'),
        M('Nalyn Sriwattanakomen', 'member', [2016, 2018], PAST, q='Nalyn Sriwattanakomen 2016 to 2018'),
        M('Emily Ho', 'visitor', [2017, 2017], PAST, q='Emily Ho September to December 2017'),
        M('German Lenin Dugarte Pena', 'visitor', [2017, 2017], PAST, q='German Lenin Dugarte Pena September to December 2017'),
        M('Fei Lua', 'member', [2015, 2017], PAST, q='Fei Lua 2015 to 2017'),
        M('Melisa E. Chavez Guerrero', 'visitor', [2017, 2017], PAST, q='Melisa E. Chavez Guerrero February to May 2017'),
        M('Jörn von Grabe', 'postdoc', [2016, 2016], PAST, q='Jörn von Grabe, Ph.D. January 2016 to March 2016'),
        M('Sam Cheyette', 'member', [2015, 2016], PAST, q='Sam Cheyette Fall 2015 to Fall 2016'),
    ],
    pubs=[PUB("https://www.cmu.edu/dietrich/sds/ddmlab/publications/index.html", mode="auto")],
    notes="DDMLab (Social and Decision Sciences). Live People page (11 current members) plus Past Members page "
          "(Post-Docs and Students & Staff sections, dated entries). Recorded all past members whose dates end 2015 or later "
          "(overlap with 2016-2026); entries ending before 2016 skipped. Past-members page is long; the postdoc part is "
          "dated, the students part mostly dated. Wayback not needed.",
    blocked=[],
)

# ---------------------------------------------------------------- Rayid Ghani
GT = "https://datasciencepublicpolicy.org/team/"
D["Rayid Ghani"] = dict(
    lab_site="https://datasciencepublicpolicy.org/",
    people_page=GT,
    people_pages=[GT],
    members=[
        M("Kasun Amarasinghe", "postdoc", None, GT, q="Our Team Kasun Amarasinghe Post-doc Researcher"),
        M("Alice Lai", "staff", None, GT, q="Alice Lai Senior Data Scientist"),
        M("Liliana Millán Núñez", "staff", None, GT, q="Liliana Millán Núñez Senior Data Scientist"),
        M("Peter Casey", "staff", None, GT, q="Peter Casey Program Director", note="alumni list; undated, held by CMU data"),
        M("Anne Driscoll", "staff", None, GT, q="Anne Driscoll Data Analyst", note="alumni list; undated, held by CMU data"),
        M("Hemank Lamba", "postdoc", None, GT, q="Hemank Lamba Post-doc", note="alumni list; undated, held by CMU data"),
        M("Kit Rodolfa", "staff", None, GT, q="Kit Rodolfa Senior Research Scientist", note="alumni list; undated, held by CMU data"),
    ],
    pubs=[PUB("https://datasciencepublicpolicy.org/our-work/publications/", mode="auto"),
          PUB("https://www.rayidghani.com/selected-publications/", mode="auto")],
    notes="DSSG lab site datasciencepublicpolicy.org. Alumni list is undated and mostly University of Chicago-era DSSG "
          "staff (Ghani joined CMU ~2020), so only current members plus alumni already held from CMU evidence were recorded; "
          "about 36 other undated alumni skipped. Wayback 2021-03 and 2023-01 captures read: the 2021 capture is a stale Chicago-era roster (Ghani as Director, page last edited 2019; Crockett, Gee, Kumar, Ramachandran, Saleiro, Salomon, Sung, De Unanue and RAs Barbey/Herdeman/Hinkson/Stern) with no evidence they were at CMU, so not recorded; the 2023 capture matches the live page.",
    blocked=[],
)

# ---------------------------------------------------------------- Ioannis Gkioulekas
GK = "https://imaging.cs.cmu.edu/team/"
D["Ioannis Gkioulekas"] = dict(
    lab_site="https://imaging.cs.cmu.edu/igkioule/",
    people_page=GK,
    people_pages=[GK],
    members=[
        M("Sreekar Ranganathan", "phd", None, GK, q="Sreekar Ranganathan PhD Student", note="2026 ECCV paper with Gkioulekas on the PI page"),
        M("Neham Jain", "masters", None, GK, q="Neham Jain Alumni MS Student"),
        M("Bailey Miller", "phd", None, GK, q="Bailey Miller Alumni PhD Student"),
        M("Shirsendu Halder", "masters", None, GK, q="Shirsendu Halder Alumni MS Student"),
        M("Bharath Hegde", "masters", None, GK, q="Bharath Hegde MS Student"),
        M("Tanli Su", "phd", None, GK, q="Tanli Su PhD Student"),
    ],
    pubs=[PUB("https://imaging.cs.cmu.edu/igkioule/", mode="auto")],
    notes="Imaging@CMU team page (imaging.cs.cmu.edu/team) is shared by five faculty (Sankaranarayanan, Gkioulekas, O'Toole, "
          "Chamanzar, Narasimhan) and does not say whose student each person is, so only people attributable to Gkioulekas "
          "(already held for him or coauthors on his page) were recorded; ~35 other team/alumni names skipped as unattributable. "
          "PI homepage has no student list; its publication list is added.",
    blocked=[],
)

# ---------------------------------------------------------------- Garth Gibson
D["Garth Gibson"] = dict(
    lab_site="http://www.cs.cmu.edu/~garth/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB("http://www.cs.cmu.edu/~garth/pubs.html", mode="auto")],
    notes="PI homepage has no student list (he left CMU for the Vector Institute in Jan 2018). The PDL people page "
          "(pdl.cmu.edu/PEOPLE/) lists lab-wide people without advisors, so none are attributable to Gibson; pubs.html added.",
    blocked=[],
)

# ---------------------------------------------------------------- Phillip Gibbons
D["Phillip Gibbons"] = dict(
    lab_site="http://www.cs.cmu.edu/~gibbons/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Homepage (not updated since 2019) has no students section; publication list is a link to DBLP (off limits). "
          "CSD profile gives no lab site. Nothing usable.",
    blocked=[],
)

# ---------------------------------------------------------------- Seth Goldstein
D["Seth Goldstein"] = dict(
    lab_site="https://www.cs.cmu.edu/~seth/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Homepage has no student list. papers.html (368 undated entries incl. bibtex) did not parse to usable titles/years "
          "(1 in-window entry), so not added. Claytronics and CINR pages: cinr.org robots-disallowed.",
    blocked=["http://www.cinr.org/"],
)

# ---------------------------------------------------------------- Gabe Gomes
D["Gabe Gomes"] = dict(
    lab_site="https://groups.chem.cmu.edu/gomes/",
    people_page="https://groups.chem.cmu.edu/gomes/people/",
    people_pages=[],
    members=[],
    pubs=[],
    notes="Publications page parsed as quoted titles with 0 matches against the PI's 9 lab papers (UofT/FSU-era mix), not added. Gomes Group site (groups.chem.cmu.edu/gomes, also gpggrp.cheme.cmu.edu) people page lists only the PI. "
          "Search says he is on leave at X. No student roster found.",
    blocked=[],
)

# ---------------------------------------------------------------- Claire Le Goues
CL = "https://squareslab.github.io/team/"
D["Claire Le Goues"] = dict(
    lab_site="https://squareslab.github.io/",
    people_page=CL,
    people_pages=[CL],
    members=[
        M("Andrea Miller", "phd", None, CL, q="PhD Students Andrea Miller"),
        M("Cláudia Mamede", "phd", None, CL, q="PhD Students Andrea Miller Cláudia Mamede"),
        M("Harrison Green", "phd", None, CL, q="Andrea Miller Cláudia Mamede Harrison Green"),
        M("Kaia Newman", "phd", None, CL, q="Cláudia Mamede Harrison Green Kaia Newman"),
        M("Luke Dramko", "phd", None, CL, q="Harrison Green Kaia Newman Luke Dramko"),
        M("Trenton Tabor", "phd", None, CL, q="Luke Dramko Program Repair TT Trenton Tabor"),
        M("Paulo Canelas", "member", None, CL, q="Other Members Paulo Canelas"),
        M("He Ye", "postdoc", [None, 2025], CL, q="Postdoctoral Scholars He Ye Assistant Professor, University College London 2025"),
        M("Milda Zizyte", "postdoc", [None, 2021], CL, q="Milda Zizyte Lecturer in Computer Science, Brown University 2021"),
        M("Chris Timperley", "postdoc", [None, 2017], CL, q="Chris Timperley Systems Scientist, Carnegie Mellon University 2017"),
        M("Aidan Yang", "phd", [None, 2025], CL, q="Aidan Yang Applied Scientist, Amazon AWS 2025"),
        M("Daniel Ramos", "phd", [None, 2025], CL, q="Daniel Ramos Software Engineer, Uber (Programming Systems Group) 2025"),
        M("Kush Jain", "phd", [None, 2025], CL, q="Kush Jain Research Scientist, Mistral AI 2025"),
        M("Nikitha Rao", "phd", [None, 2025], CL, q="Nikitha Rao Research Scientist, Google (DeepMind) 2025"),
        M("Tobias Dürschmid", "phd", [None, 2025], CL, q="Tobias Dürschmid Assistant Teaching Professor, UCLA 2025"),
        M("Jeremy Lacomis", "phd", [None, 2023], CL, q="Jeremy Lacomis Mark Stehlik Postdoctoral Teaching Fellow 2023"),
        M("Afsoon Afzal", "phd", [None, 2021], CL, q="Afsoon Afzal Software Engineer, Nuro 2021"),
        M("Cody Kinneer", "phd", [None, 2021], CL, q="Cody Kinneer Trader, IMC Trading 2021"),
        M("Mauricio Soto", "phd", [None, 2021], CL, q="Mauricio Soto Research Scientist, ABB/Hitachi 2021"),
        M("Deby Katz", "phd", [None, 2020], CL, q="Deby Katz Research Engineer, Seegrid Corp 2020"),
        M("Zack Coker", "phd", [None, 2020], CL, q="Zack Coker Research Scientist, Sandia National Labs 2020"),
        M("Rijnard van Tonder", "phd", [None, 2019], CL, q="Rijnard van Tonder Research Scientist, Sourcegraph 2019"),
        M("Sophia Kolak", "masters", [None, 2024], CL, q="Masters Students Sophia Kolak 2024"),
        M("Leo Chen", "masters", [None, 2023], CL, q="Leo Chen 2023"),
        M("Qibin Chen", "masters", [None, 2022], CL, q="Qibin Chen Staff ML Engineer, Apple 2022"),
        M("Yiwei Lyu", "undergraduate", [None, 2023], CL, q="Undergraduate Researchers YL Yiwei Lyu 2023"),
        M("Zhen Yu Ding", "undergraduate", [None, 2022], CL, q="Zhen Yu Ding 2022"),
    ],
    pubs=[PUB("https://www.clairelegoues.com/publications/", mode="auto")],
    notes="squaresLab team page (live): current PhDs/other members and 26 alumni with departure years. Six visiting scholars "
          "(Cruz Carlon, Tian, Le Bui Tien Duy, Kochhar, Yuan, Le Dinh) are undated and were skipped. Faculty entry is the PI. "
          "REUSE undergraduates are mentioned but not named. squareslab.github.io/publications did not parse; PI site publications page added instead. Wayback not used (page is current and lists alumni).",
    blocked=[],
)

# ---------------------------------------------------------------- Hartmut Geyer
HG = "https://sites.google.com/andrew.cmu.edu/ri-lsg/people"
G17 = WB + "20170120220740id_/http://www.cs.cmu.edu:80/~hgeyer/Students_Main.html"
G20 = WB + "20200124224102id_/http://www.cs.cmu.edu:80/~hgeyer/Students_Main.html"
D["Hartmut Geyer"] = dict(
    lab_site="https://sites.google.com/andrew.cmu.edu/ri-lsg",
    people_page=HG,
    people_pages=[HG, G17, G20],
    members=[
        M("Atharva Ramdas", "phd", None, HG, near="Current Graduate Students"),
        M("Vyvaswath Kalva", "phd", None, HG, near="Current Graduate Students"),
        M("Fawaz Mallick", "phd", None, HG, near="Current Graduate Students"),
        M("Haosen Xing", "phd", [None, 2025], HG, q="Haosen Xing , PhD 2025, Mechanical Engineering"),
        M("Omar Refy", "phd", [None, 2024], HG, q="Omar Refy , PhD 2024, Physics (co-advised with Douglas Weber, CMU Mechanical Engineering)"),
        M("Michelle (Karabin) Harter", "phd", [None, 2024], HG,
          q="Michelle (Karabin) Harter , PhD 2024, University of Pittsburgh Bioengineering (primary advisor: Mark Redfern, University of Pittsburgh)",
          note="Pitt PhD with primary advisor Redfern; listed as alumna of the group, CMU affiliation unclear"),
        M("Ashwin Khadke", "phd", [None, 2024], HG, q="Ashwin Khadke , PhD 2024, Robotics Institute"),
        M("Nitish Thatte", "phd", [None, 2019], HG, q="Nitish Thatte , PhD 2019, Robotics Institute"),
        M("William Martin", "phd", [None, 2019], HG, q="William Martin , PhD 2019, Robotics Institute"),
        M("Wei Sin Ang", "phd", [None, 2017], HG, q="Wei Sin Ang , PhD 2017, NTU-CMU program (co-advisor I-Ming Chen, NTU Singapore)"),
        M("Bowei Tang", "phd", None, G17, near="Current Students"),
        M("Helei Duan", "masters", [None, 2017], G20, q="Helei Duan (MechE MSc May 2017)"),
        M("Junlin Wang", "masters", [None, 2017], G20, q="Junlin Wang(MechE, MSc May 2017)"),
        M("Seungmoon Song", "phd", [None, 2017], G20, q="Seungmoon Song (RI, PhD May 2017)"),
        M("Albert Wu", "phd", [None, 2017], G20, q="Albert Wu (RI, PhD Feb 2017)"),
        M("Alexander Schepelmann", "phd", [None, 2016], G20, q="Alexander Schepelmann (RI, PhD Feb 2016)"),
        M("Yin Zhong", "masters", [None, 2016], G20, q="Yin Zhong (RI, MSc May 2016)"),
        M("Bolun Dai", "masters", None, G20, near="Current Students"),
        M("Timothy Kyung", "masters", None, G20, near="Current Students"),
        M("Tianyu Li", "masters", None, G20, near="Current Students"),
        M("Preeti Sar", "phd", None, G20, near="Current Students"),
        M("Chendur Senthilnathan", "masters", None, G20, near="Current Students"),
        M("Lin Song", "masters", None, G20, near="Current Students"),
        M("Krishna Toshniwal", "masters", None, G20, near="Current Students"),
        M("Yigit Yakupoglu", "masters", None, G20, near="Current Students"),
    ],
    pubs=[PUB("https://sites.google.com/andrew.cmu.edu/ri-lsg/publications", mode="auto")],
    notes="Legged Systems Group Google Site (cs.cmu.edu/~hgeyer redirects there). People page lists 3 current grad students and "
          "7 PhD alumni with years; no masters/undergrad/postdoc entries. Held students not on the page (Song, Schepelmann, "
          "Wu, Zhong, Shi, Sripada, Balaji, Shah) came from papers; Old Students_Main.html Wayback captures (2017, 2020; 2023 identical to 2020) "
          "added the 2016-2020 cohort. Former students ending before 2016 skipped (12).",
    blocked=[],
)

# ---------------------------------------------------------------- Anatole Gershman
D["Anatole Gershman"] = dict(
    lab_site="http://www.cs.cmu.edu/~anatoleg/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="PI homepage (www.cs.cmu.edu/~anatoleg/) lists research interests, projects (TREE, Encore, Metal) and bio only: no "
          "students/members section and no publications page. LTI profile URL guessed 404. WebSearch found no group page.",
    blocked=[],
)
