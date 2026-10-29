from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Emma Brunskill
EB = "http://www.cs.cmu.edu/~ebrun/"
EB16 = WB + "20160116004633id_/http://www.cs.cmu.edu/~ebrun/"
EB17 = WB + "20170124230252id_/http://www.cs.cmu.edu:80/~ebrun/"
D["Emma Brunskill"] = dict(
    lab_site=EB,
    people_page=EB,
    people_pages=[EB, EB16, EB17],
    members=[
        M("Philip Thomas", "postdoc", None, EB, q="Postdoc Philip Thomas"),
        M("Christoph Dann", "phd", None, EB, near="Ph.D."),
        M("Shayan Doroudi", "phd", None, EB, near="Ph.D."),
        M("Zhaohan Daniel Guo", "phd", None, EB, near="Ph.D."),
        M("Yao Liu", "phd", None, EB, q="Yao Liu Masters",
          note="listed last under Ph.D. on the frozen CMU page (written early 2017)"),
        M("Karan Goel", "masters", None, EB, near="Masters"),
        M("Rika Antonova", "masters", [None, 2016], EB, near="Masters",
          note="news: finished masters Aug 2016"),
        M("Joe Runde", "masters", [None, 2016], EB, near="Masters",
          note="news: finished masters Aug 2016"),
        M("Li Zhou", "masters", None, EB, near="Masters"),
        M("Qi Guo", "masters", [None, 2016], EB16, near="Masters",
          note="Jan 2016 capture; news on the live page: finished masters Aug 2016"),
    ],
    pubs=[],
    notes=("lab_url (csd profile) 404s; the live www.cs.cmu.edu/~ebrun/ page is her frozen CMU homepage "
           "(says she joins Stanford March 2017), group listed in a 'currently working with' section; "
           "also read Jan 2016 and Jan 2017 captures (later captures identical, CMU tenure ended 2017). "
           "Skipped: Yun-En Liu and Travis Mandel (University of Washington students co-advised with Zoran "
           "Popovic; Liu defended May 2015); (Dexter) Min Hyung Lee (listed in the Jan 2016 capture but news "
           "says he graduated Dec 2015). Stanford-era students not CMU. Publications page "
           "www.cs.cmu.edu/~ebrun/publications.html exists (12 in-window 2016 entries) but its unclosed <li> "
           "markup does not parse in any mode (only pre-2016 entries extract), so not added."),
    blocked=[],
)

# ---------------------------------------------------------------- Randal Bryant
RB = "http://www.cs.cmu.edu/~bryant/"
RBV = "http://www.cs.cmu.edu/~bryant/vitae-full.html"
D["Randal Bryant"] = dict(
    lab_site=RB,
    people_page=RB,
    people_pages=[RB, RBV],
    members=[
        M("Zach Battleman", "phd", None, RB, near="Current Graduate Students"),
        M("Joseph Reeves", "phd", [None, 2026], RBV, q="Ph.D. Advisees 2026 Joseph Reeves",
          note="jointly advised by Marijn Heule; PhD 2026 per full CV, now at AWS"),
    ],
    pubs=[],
    notes=("No separate lab site; PI homepage lists 'Current Graduate Students' and 'Former Graduate Students'; "
           "the full CV (vitae-full.html) dates advisees: only Joseph Reeves (2026) is in window; Jiri Simsa "
           "PhD 2013 and Adam Blank MS 2014 are before 2016; all other former students are 1988-2005. "
           "Wayback refused connections during this pass, so homepage captures could not be compared "
           "(2016-2026 captures exist). Publication list pubs.html exists and titles parse (each entry a "
           "p.noindent) but every pre-1990 entry is assigned year 2025 by the extractor in all modes (~28 "
           "1980s papers would enter the window as false in-window papers), so not added. Genuinely missing "
           "in-window titles seen: 'Binary Decision Diagrams: An Algorithmic Basis for Symbolic Model "
           "Checking' (2018), 'Translating Pseudo-Boolean Proofs into Boolean Clausal Proofs' (FMCAD 2024), "
           "'TBUDDY: A Proof-Generating BDD Package' (FMCAD 2022), 'Implementing Malloc: Students and "
           "Systems Programming' (SIGCSE 2018), 'Notes on BDD-Based Bucket Elimination' (2023)."),
    blocked=[],
)

# ---------------------------------------------------------------- Carlos Busso
CB = "https://lab-msp.com/MSP/MSPpeople.html"
CB_ALUM_NOTE = "lab moved from UT Dallas to CMU LTI in 2024; this alumnus is listed with 'after CMU'"
D["Carlos Busso"] = dict(
    lab_site="https://lab-msp.com/",
    people_page=CB,
    people_pages=[CB],
    members=[
        M("Pravin Mote", "phd", None, CB, near="Members",
          note="current member; publications on the lab list go back to UTD-era work"),
        M("Karen Rosero", "phd", None, CB, near="Members"),
        M("Xavier Yin", "phd", None, CB, near="Members"),
        M("Jaeyeon Kim", "phd", None, CB, near="Members", note="co-advised with Shinji Watanabe"),
        M("Haeri Kim", "phd", None, CB, near="Members", note="co-advised with Shinji Watanabe"),
        M("Vanessa Wei", "masters", None, CB, near="Members"),
        M("Elaine Zhang", "masters", None, CB, near="Members"),
        M("Kuan Yi (Gary) Lee", "masters", None, CB, near="Members"),
        M("Ella Wileman", "masters", None, CB, near="Members"),
        M("Prajwal Kadri", "masters", None, CB, near="Members"),
        M("Niveditha Kovilakath", "masters", None, CB, near="Members"),
        M("Szu-Ju Chen", "masters", None, CB, q="Szu-Ju Chen M.S. Student"),
        M("Zeyang Zhang", "masters", [2025, 2026], CB, q="Zeyang Zhang (2025-2026) MS. Thesis",
          note="MS 2025-2026; now Research Assistant in the lab (current Members list)"),
        M("Chan-Jan (Jeff) Hsu", "visitor", [2025, 2026], CB,
          near="Visiting Scholars and Post-Doctoral Researcher",
          note="visiting from National Taiwan University; also listed as Ph.D. Student under Members"),
        M("Patarapornkan Anantarangsi", "masters", [2025, 2026], CB, near="Master Students", note=CB_ALUM_NOTE),
        M("Esther Sun", "masters", [2025, 2026], CB, near="Master Students", note=CB_ALUM_NOTE),
        M("Hsuan-Hao Lin", "masters", [2025, 2026], CB, near="Master Students", note=CB_ALUM_NOTE),
        M("Anish Saha", "undergraduate", [2026, 2026], CB, near="Undergraduate Students",
          note="BS student at CMU"),
    ],
    pubs=[PUB("https://lab-msp.com/MSP/MSPpapers.html", mode="auto")],
    notes=("Lab site lab-msp.com (MSP Lab; moved with Busso from UT Dallas, where he was faculty 2009-2024, to CMU "
           "LTI). Current 'Members' list taken in full. Alumni lists (PhD, MS, undergrad, visitors) are almost all "
           "UT Dallas ('First position after UTD'): skipped as previous-institution students (about 40 in-window "
           "UTD alumni, e.g. Luz Martinez-Lucas 2022-2026, Abinay Reddy Naini 2022-2025, Lucas Goncalves, "
           "Seong-Gyun Leem, Ali N. Salman, Wei-Cheng Lin, Christian Flores 2024-2025). Kept only alumni marked "
           "'after CMU' or BS at CMU. Visitor Jing-Tong (Roger) Tzeng (2024) skipped: 2024 is the UTD/CMU "
           "transition year and the page does not place him at CMU. Publications page MSPpublications.html "
           "loads MSPpapers.html by JavaScript fetch; the data file parses cleanly (auto, class-title) and is the "
           "full lab list including UTD-era papers. Wayback refused connections during this pass."),
    blocked=[],
)

# ---------------------------------------------------------------- Joseph Anthony Calandrino
D["Joseph Anthony Calandrino"] = dict(
    lab_site="https://plaintextresponse.com/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB("https://plaintextresponse.com/", mode="auto")],
    notes=("No lab site. PI homepage (plaintextresponse.com) has bio, service and 'Selected Publications' only; no "
           "students/group section. S3D profile (s3d.cmu.edu/people/core-faculty/calandrino-joseph.html) lists only "
           "contact info and the homepage. He joined CMU recently (previously DOJ and FTC), so earlier homepage "
           "captures would predate CMU; Wayback refused connections during this pass anyway. Selected Publications "
           "added (auto: 4 in-window missing, correct years; entries dated only as ConPro '21/'22/'26 have no "
           "parsed year)."),
    blocked=[],
)

# ---------------------------------------------------------------- Jamie Callan
JC = "http://www.cs.cmu.edu/~callan/Group.html"
JCD = "http://www.cs.cmu.edu/~callan/Dissertations.html"
D["Jamie Callan"] = dict(
    lab_site="http://www.cs.cmu.edu/~callan/",
    people_page=JC,
    people_pages=[JC, JCD],
    members=[
        M("Amy Grone", "staff", None, JC, q="Amy Grone Administrative Coordinator",
          note="group administrative coordinator; handles ClueWeb licenses"),
        M("Luís Borges", "phd", None, JC, q="Luís Borges Graduate Research Assistant",
          note="Graduate Research Assistant based in Lisbon (CMU Portugal)"),
        M("Luyu Gao", "phd", None, JC, q="Luyu Gao Machine Learning Engineer",
          note="listed in the current group as ML Engineer at OpenAI; former PhD student"),
        M("Hany Jasmine", "masters", None, JC, q="Hany Jasmine MIIS Student"),
        M("Francis Tom", "masters", None, JC, q="Francis Tom MIIS Student"),
        M("Kyle Yingkai Gao", "masters", [None, 2016], JC, q="Kyle Yingkai Gao MS 2016"),
        M("Jing Chen", "masters", [None, 2016], JC, q="Jing Chen MS 2016"),
        M("Dhivya Piraviperumal", "masters", [None, 2016], JC, q="Dhivya Piraviperumal MS 2016"),
        M("Keyang Xu", "masters", [None, 2017], JC, q="Keyang Xu MS 2017"),
        M("Xin Qian", "masters", [None, 2018], JC, q="Xin Qian MS 2018"),
        M("Chenyan Xiong", "phd", [None, 2018], JC, q="Chenyan Xiong Ph.D. 2018"),
        M("Arnav Kumar", "masters", [None, 2018], JC, q="Arnav Kumar MS 2018"),
        M("Yubin Kim", "phd", [None, 2018], JC, q="Yubin Kim Ph.D. 2018"),
        M("Hafeezul Rahman", "masters", [None, 2019], JC, q="Hafeezul Rahman MS 2019"),
        M("Ramith Padaki", "masters", [None, 2019], JC, q="Ramith Padaki MS 2019"),
        M("Xue Xia", "masters", [None, 2019], JC, q="Xue Xia MS 2019"),
        M("Shuo Wang", "masters", [None, 2020], JC, q="Shuo Wang MS 2020"),
        M("Zhuyun Dai", "phd", [None, 2020], JC, q="Zhuyun Dai PhD 2020"),
        M("Vaibhav Kumar", "masters", [None, 2020], JC, q="Vaibhav Kumar MS 2020"),
        M("Minjie Li", "masters", [None, 2020], JC, q="Minjie Li MS 2020"),
        M("HongChien Yu", "masters", [None, 2021], JC, q="HongChien Yu MS 2021"),
        M("Nour Jedidi", "masters", [None, 2022], JC, q="Nour Jedidi MS 2022"),
        M("Vaishakh Keshava", "masters", [None, 2022], JC, q="Vaishakh Keshava MS 2022"),
        M("Aditya Srikanth Veerubhotla", "masters", [None, 2022], JC, q="Aditya Srikanth Veerubhotla MS 2022"),
        M("Gustavo Gonçalves", "masters", [None, 2023], JC, q="Gustavo Gonçalves MLT 2023",
          note="MLT 2023 per page"),
        M("Guanzhong Liu", "masters", [None, 2023], JC, q="Guanzhong Liu MIIS 2023"),
        M("Siddharth Gandhi", "masters", [None, 2024], JC, q="Siddharth Gandhi MS 2024"),
        M("Zhen Fan", "masters", [None, 2024], JC, q="Zhen Fan MLT 2024"),
        M("Jingjie Ethan Ning", "masters", [None, 2026], JC, q="Jingjie Ethan Ning MCDS 2026"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~callan/Papers/", mode="auto")],
    notes=("Group page 'People and places' (Group.html) on the PI homepage: current people plus 'Former Students' "
           "with degree years; PhD dissertations page confirms Xiong 2018, Kim 2018, Dai 2020. Skipped former "
           "students with degrees 2005-2015 (21, incl. Reyyan Yeniterzi and Bhavana Dalvi Mishra PhD 2015). "
           "Former Staff Cameron VandenBerg is undated (skipped; Wayback needed to place him in 2016+). "
           "Wayback refused connections during this pass, so no captures of Group.html were compared. "
           "Papers page added (auto: 14 in-window missing, 66 matched)."),
    blocked=[],
)

# ---------------------------------------------------------------- Jaime Carbonell
JG = "http://www.cs.cmu.edu/~jgc/phd_students.html"
JG18 = WB + "20180503130300id_/http://www.cs.cmu.edu/~jgc/phd_students.html"
D["Jaime Carbonell"] = dict(
    lab_site="http://www.cs.cmu.edu/~jgc/",
    people_page=JG,
    people_pages=[JG, JG18],
    members=[
        M("Daegun Won", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS"),
        M("Peter Stojano", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS",
          note="spelled 'Peter Stojano' on the page (Petar Stojanov)"),
        M("Jesse Dunietz", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS"),
        M("Adams Wei Yu", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS"),
        M("Shane Moon", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS", note="Seungwhan (Shane) Moon"),
        M("Keerthiram Murugesan", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS"),
        M("Dishan Gupta", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS",
          note="listed under 'Current PhD and MLT students' (degree not stated)"),
        M("Jeffrey Flanigan", "phd", None, JG, near="CURRENT PHD AND MLT STUDENTS",
          note="co-advised with Lori Levin"),
        M("Ashique KhudaBukhsh", "phd", [None, 2017], JG, q="Ashique KhudaBukhsh 2017",
          note="PhD 2017; listed as current 'Ashiqur Khudbukhsh' in the May 2018 capture"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~jgc/publications.html", mode="auto")],
    notes=("PI passed away February 2020; homepage frozen. 'Graduate Students' page lists current PhD/MLT students "
           "(list unchanged 2017-2022; it was not updated for students who joined after ~2015, e.g. later "
           "low-resource NLP students) and graduated students with years: only Ashique KhudaBukhsh (2017) is "
           "in window; Meghana Kshirsagar 2015 and ~45 others 1985-2013 skipped; Selen Uguroglu undated. "
           "Wayback capture May 2018 compared (same people). Sep 2019 CV PDF has no student list. "
           "Wayback was intermittently refusing connections (2017 and Oct 2019 captures could not be fetched). "
           "Publications page added (auto: 2 in-window missing, 7 matched; list mostly pre-2016)."),
    blocked=[],
)

# ---------------------------------------------------------------- Oana Carja
OC = "https://www.cmu.edu/cbd/people/carja.html"
OC26 = WB + "20260116003307id_/https://www.cmu.edu/cbd/people/carja.html"
D["Oana Carja"] = dict(
    lab_site=None,
    people_page=OC,
    people_pages=[OC, OC26],
    members=[
        M("Zitong (Sam) Chen", "phd", None, OC, near="Lab Members"),
        M("Anush Devadhasan", "phd", None, OC, near="Lab Members"),
        M("Lanting Li", "phd", None, OC, near="Lab Members", note="co-advised by Russell Schwartz"),
        M("Steph Masotti", "phd", None, OC, near="Lab Members", note="co-advised by Nate Lord"),
        M("Seh Na Mellick", "phd", None, OC, near="Lab Members", note="co-advised by Drew Bridges"),
        M("Thomas Rachman", "phd", None, OC, near="Lab Members", note="co-advised by Russell Schwartz"),
        M("Zihang Wen", "phd", None, OC, near="Lab Members"),
        M("Dennis Aldea", "phd", None, OC26, near="Lab Members",
          note="listed in the Jan 2026 capture, no longer on the live profile"),
    ],
    pubs=[],
    notes=("No separate lab website found (CBD profile links only Google Scholar; a web search found no lab site). "
           "The CBD faculty profile has a 'Lab Members' section, used as the people page. Wayback has only 2026 "
           "captures of this profile URL (Jan/Apr 2026); the Jan 2026 capture adds Dennis Aldea. A CDX prefix "
           "search for older profile URLs timed out. No publications page (Google Scholar only)."),
    blocked=[],
)

# ---------------------------------------------------------------- Kathleen M Carley
KS = "https://www.cmu.edu/casos-center/people/students.html"
KF = "https://www.cmu.edu/casos-center/people/staff.html"
KT = "https://www.cmu.edu/casos-center/publications/thesis.html"
KC16 = WB + "20160224073522id_/http://www.casos.cs.cmu.edu/people/student.php"
KC19 = WB + "20190111055035id_/http://www.casos.cs.cmu.edu/people/student.php"
KC22 = WB + "20220125132730id_/http://www.casos.cs.cmu.edu/people/student.php"
CARLEY_MEMBERS = [
    M("Daniele Bellutta", "phd", None, KS, near="CASOS Graduate Students"),
    M("John Benson", "phd", None, KS, near="CASOS Graduate Students"),
    M("Peter Carragher", "phd", None, KS, near="CASOS Graduate Students"),
    M("Bianca Kang", "phd", None, KS, near="CASOS Graduate Students"),
    M("Ian Kloo", "phd", None, KS, near="CASOS Graduate Students"),
    M("Rebecca Marigliano", "phd", None, KS, near="CASOS Graduate Students"),
    M("Lynnette Ng", "phd", None, KS, near="CASOS Graduate Students"),
    M("Luke Osterritter", "phd", None, KS, near="CASOS Graduate Students",
      note="also Software Engineering Institute"),
    M("Samantha Phillips", "phd", None, KS, near="CASOS Graduate Students"),
    M("Jacob Shaha", "phd", None, KS, near="CASOS Graduate Students"),
    M("Jeongkeun (Jake) Shin", "phd", None, KS, near="CASOS Graduate Students", note="ECE and S3D"),
    M("Evan Williams", "phd", None, KS, near="CASOS Graduate Students"),
    M("Richelle Brown-Robinson", "staff", None, KF, near="CASOS Staff", note="Administration"),
    M("Michael Kowalchuck", "staff", None, KF, q="Michael Kowalchuck Senior Research Programmer"),
    M("Jeffrey Reminga", "staff", None, KF, q="Jeffrey Reminga Senior Research Programmer"),
    M("Dawn Robertson", "staff", None, KF, q="Dawn Robertson Research Associate"),
    M("Hicks, Matthew", "phd", [None, 2025], KT, q="Hicks, Matthew. (2025)"),
    M("King, Catherine", "phd", [None, 2025], KT, q="King, Catherine. (2025)"),
    M("Lepird, Christine", "phd", [None, 2025], KT, q="Lepird, Christine (Sowa). (2025)",
      note="Christine Sowa Lepird"),
    M("Jacobs, Charity", "phd", [None, 2025], KT, q="Jacobs, Charity. (2025)"),
    M("Uyheng, Joshua", "phd", [None, 2024], KT, q="Uyheng, Joshua. (2024)"),
    M("Blane, Janice", "phd", [None, 2023], KT, q="Blane, Janice. (2023)"),
    M("Magelinski, Thomas", "phd", [None, 2023], KT, q="Magelinski, Thomas. (2023)"),
    M("Dobson, Geoffrey", "phd", [None, 2022], KT, q="Dobson, Geoffrey. (2022)"),
    M("Villa-Cox, Ramon", "phd", [None, 2022], KT, q="Villa-Cox, Ramon. (2022)"),
    M("Tyagi, Aman", "phd", [None, 2021], KT, q="Tyagi, Aman. (2021)", note="EPP PhD, CASOS"),
    M("Beskow, David", "phd", [None, 2020], KT, q="Beskow, David. (2020)"),
    M("Huang, Binxuan", "phd", [None, 2020], KT, q="Huang, Binxuan. (2020)"),
    M("Cruickshank, Iain", "phd", [None, 2020], KT, q="Cruickshank, Iain. (2020)"),
    M("Kumar, Sumeet", "phd", [None, 2020], KT, q="Kumar, Sumeet. (2020)"),
    M("Benigni, Matthew", "phd", [None, 2017], KT, q="Benigni, Matthew. (2017)"),
    M("Frankenstein, William", "phd", [None, 2016], KT, q="Frankenstein, William. (2016)", note="EPP PhD, CASOS"),
    M("Joseph, Kenneth", "phd", [None, 2016], KT, q="Joseph, Kenneth. (2016)"),
    M("Wei, Wei", "phd", [None, 2016], KT, q="Wei, Wei. (2016)"),
    M("Hirshman, Brian", "phd", None, KC16, q="Hirshman, Brian ISR, CASOS IGERT",
      note="listed 2016 and 2019 (ABS; on leave, ABD)"),
    M("Landwehr, Peter", "phd", None, KC16, q="Landwehr, Peter ISR, CASOS IGERT"),
    M("Morgan, Geoffrey", "phd", None, KC16, q="Morgan, Geoffrey ISR, CASOS IGERT", note="listed 2016-2022"),
    M("Lin, Jun Jie Larry", "member", None, KC16, q="Lin, Jun Jie Larry Singapore Management University",
      note="listed among CASOS students with Singapore Management University affiliation (andrew.cmu.edu email)"),
    M("Bartulovic, Mihovil", "phd", None, KC19, q="Bartulovic, Mihovil ECE, CASOS",
      note="ECE PhD student in CASOS; now listed as CASOS related faculty"),
    M("Hou, Jialin", "member", None, KC19, q="Hou, Jialin University of Pittsburgh",
      note="University of Pittsburgh student listed among CASOS students (2019, 2022)"),
    M("Moffitt, James", "phd", None, KC22, q="Moffitt, James ISR, CASOS"),
    M("Murdock, Isabel", "phd", None, KC22, q="Murdock, Isabel ISR, CASOS"),
    M("Straughter, Jeremy", "phd", None, KC22, q="Straughter, Jeremy ISR, CASOS"),
]
D["Kathleen M Carley"] = dict(
    lab_site="https://www.cmu.edu/casos-center/",
    people_page=KS,
    people_pages=[KS, KF, KT, KC16, KC19, KC22],
    members=CARLEY_MEMBERS,
    pubs=[PUB("https://www.cmu.edu/casos-center/publications/index.html", mode="auto")],
    notes=("lab_url (casos.cs.cmu.edu/bios/carley) 404s; Carley directs the CASOS Center, now at "
           "www.cmu.edu/casos-center/ with Students, Staff and Faculty pages and a 'CASOS Graduate Student Thesis' "
           "list (dated PhD theses; used for alumni 2016-2025, ~30 theses 2004-2015 skipped). Faculty page lists "
           "other CASOS/related faculty (L. Richard Carley, Krackhardt, Yagan, Iain Cruickshank, etc.) - not "
           "recorded. Old CASOS site (casos.cs.cmu.edu/people/student.php) read in Wayback captures Feb 2016, Jan 2019, "
           "Jan 2022 for students not on the live page. Publications page (2016-2026 CASOS list) added, auto mode."),
    blocked=[],
)

# ---------------------------------------------------------------- Patrick Carrington
PA = "https://www.axle-lab.com/people"
PCV = "https://www.patrickcarrington.com/cv"
UG = "Undergraduate researchers"
D["Patrick Carrington"] = dict(
    lab_site="https://www.axle-lab.com/",
    people_page=PA,
    people_pages=[PA, PCV],
    members=[
        M("Eric Davidson", "staff", None, PA, q="Eric Davidson Administrative Coordinator"),
        M("Atieh Taheri", "postdoc", [2024, None], PCV, near="Postdoctoral fellows",
          note="Presidential Postdoctoral Fellow, with Jeffrey Bigham"),
        M("Ezra Awumey", "phd", [2024, None], PCV, near="Doctoral advisees"),
        M("JiWoong Jang", "phd", [2022, None], PCV, near="Doctoral advisees",
          note="co-advised with Andrew Begel; undergraduate researcher in the lab 2021-2022"),
        M("Sanika Moharana", "phd", [2022, None], PCV, near="Doctoral advisees",
          note="co-advised with Christina Harrington"),
        M("Yunzhi Li", "phd", [2021, None], PCV, near="Doctoral advisees"),
        M("Frank Elavsky", "phd", [2021, 2026], PCV, near="Doctoral advisees", note="co-advised with Dominik Moritz"),
        M("Franklin Mingzhe Li", "phd", [2020, 2026], PCV, near="Doctoral advisees"),
        M("Chloe Zhu", "masters", [2025, None], PCV, near="Master's students", note="MHCI"),
        M("Riya Mody", "masters", [2024, 2025], PCV, near="Master's students", note="MHCI"),
        M("Ashley Wang", "masters", [2020, 2023], PCV, near="Master's students",
          note="CS master's thesis 2022-2023; undergraduate researcher 2020-2022"),
        M("Peter Cederberg", "masters", [2020, 2022], PCV, near="Master's students", note="Interaction Design"),
        M("Isabel Ngan", "masters", [2021, 2021], PCV, near="Master's students", note="MHCI"),
        M("Simran Jobanputra", "masters", [2019, 2020], PCV, near="Master's students", note="MHCI"),
        M("Owais Yousuf", "visitor", [2026, None], PCV, near="Visiting researchers",
          note="post-baccalaureate visitor from George Mason University"),
        M("Brandon Woodard", "visitor", [2022, 2023], PCV, near="Visiting researchers",
          note="visiting Ph.D. student from Brown University"),
        M("Kaitlyn Ng", "undergraduate", [2024, 2026], PCV, near=UG),
        M("Misty Fan", "undergraduate", [2025, 2025], PCV, near=UG),
        M("Tatyana Cruz", "undergraduate", [2025, 2025], PCV, near=UG, note="CMU ECE"),
        M("Ashley Fong", "undergraduate", [2024, 2024], PCV, near=UG, note="Summer REU from UC Berkeley"),
        M("Areen Khalaila", "undergraduate", [2024, 2024], PCV, near=UG, note="Summer REU from Brandeis"),
        M("Rachel Sadeh", "undergraduate", [2022, 2023], PCV, near=UG,
          note="Summer REU, continuing as research assistant"),
        M("Yuqi Gong", "undergraduate", [2021, 2022], PCV, near=UG),
        M("Jamie Dorst", "undergraduate", [2021, 2021], PCV, near=UG),
        M("Juan Garza", "undergraduate", [2021, 2021], PCV, near=UG, note="Summer REU"),
        M("Mei-Lian Vader", "undergraduate", [2021, 2021], PCV, near=UG, note="Summer REU"),
        M("Yellina Yim", "undergraduate", [2020, 2021], PCV, near=UG),
        M("Nali Huynh", "undergraduate", [2020, 2021], PCV, near=UG),
        M("Andrew Chuang", "undergraduate", [2020, 2020], PCV, near=UG),
        M("Xingyu Liu", "undergraduate", [2019, 2020], PCV, near=UG),
        M("Christina Low", "undergraduate", [2019, 2020], PCV, near=UG, note="Summer REU"),
        M("Emma McCamey", "undergraduate", [2019, 2020], PCV, near=UG, note="Summer REU"),
        M("Cameron Cassidy", "undergraduate", [2019, 2019], PCV, near=UG, note="Summer REU"),
        M("Toni Kaplan", "undergraduate", [2019, 2019], PCV, near=UG),
        M("Elena Deng", "undergraduate", [2019, 2019], PCV, near=UG),
        M("Stephanie Wang", "undergraduate", [2018, 2018], PCV, near=UG,
          note="CMU Statistics and ML, Summer REU (PI was a CMU postdoc then)"),
        M("Adrian Jenkins", "undergraduate", [2018, 2018], PCV, near=UG,
          note="Summer REU from Hampton University (PI was a CMU postdoc then)"),
        M("Lucas Rosenblatt", "undergraduate", [2017, 2018], PCV, near=UG,
          note="Summer REU (PI was a CMU postdoc 2017-2019)"),
    ],
    pubs=[PUB("https://www.axle-lab.com/publications", mode="auto")],
    notes=("AXLE Lab site (axle-lab.com, linked from the PI homepage patrickcarrington.com) has People "
           "(current + doctoral alumni + undated 'former researchers and mentees'); the PI's CV page "
           "(patrickcarrington.com/cv, 'Supervision and Advising') dates every mentee, so dated entries are "
           "taken from the CV. PI: postdoc at CMU HCII 2017-2019, faculty since 2019. Skipped UMBC-era "
           "mentees (Denzel Ketter 2017, Catherine Hornback, Jian-Ming Chang, Kevin Chang 2015-2016) and "
           "doctoral committee members (other institutions/advisors). Publications page added (auto)."),
    blocked=[],
)

# ---------------------------------------------------------------- Paulo Carvalho
OK = "https://www.theoaklab.org/"


def _oak(names, role, years, near, note=None):
    return [M(n, role, years, OK, near=near, note=note) for n in names]


D["Paulo Carvalho"] = dict(
    lab_site=OK,
    people_page=OK,
    people_pages=[OK],
    members=(
        [M("Michael Asher", "staff", None, OK, near="Research Scientists & Postdocs", note="Project Scientist"),
         M("Meng Cao", "postdoc", None, OK, near="Research Scientists & Postdocs")]
        + _oak(["Yumou (James) Wei", "Gillian Gold", "Phenyo Moletsane", "Jess Turner"], "phd", None, "PhD Students")
        + _oak(["Abigail Lo", "Janessa Guo", "Katherine Geng", "Palomi Nihalani", "Neha Yadavilli", "Gwyneth Farley"],
               "undergraduate", None, "Undergraduate Research Assistants")
        + [M("Julia J. Conti", "phd", [None, 2026], OK, near="Alumni PhD", note="now postdoc at CMU"),
           M("Napol Rachatasumrit", "phd", [None, 2025], OK, near="Alumni PhD")]
        + _oak(["Jordan Gutterman", "Michael Sutton", "Canwen Wang", "Tingyue Cue", "Ryan Nuqui",
                "Pragati Maheshwary", "Mandy Pan"], "masters", [2024, 2026], "Master's (2024–2026)",
               note="master's alumni group dated 2024-2026")
        + [M("Arun Lekshmi Narayanan", "visitor", None, OK, near="Visiting Researchers & Staff",
             note="visiting PhD student from Pitt"),
           M("Sally Pak", "staff", None, OK, near="Visiting Researchers & Staff", note="Lab Coordinator"),
           M("Iris Liu", "staff", None, OK, near="Visiting Researchers & Staff", note="Project Coordinator")]
        + _oak(["Annie Chen", "Sophia Mou", "Rebecca Sucgang", "Nikhil Konkimalla", "Maddy Ng", "James Ryman",
                "Khushi Juneja"], "undergraduate", [2026, 2026], "Undergrad Research Assistants (2026)")
        + _oak(["Helen Peng", "Aditi Agni", "Dora Chen", "Ekin Ozince", "Hannah Hayes", "Vivianne Lee",
                "Jarret Huang", "Sage Rohrbach", "Xinfei Cen"], "undergraduate", [2025, 2025],
               "Undergrad Research Assistants (2025)")
        + _oak(["Isha Patel", "Jiwoo You", "Annie Wang", "Emily Jiang"], "undergraduate", [2024, 2024],
               "Undergrad Research Assistants (2024)")
        + _oak(["Charlotte Ku", "Mariam Syed"], "undergraduate", [2026, 2026], "Summer REUs & Interns (2026)",
               note="summer REU/intern")
        + _oak(["Calvin Macatantan", "Maylynn Rodriguez", "Jacob Tjaden", "Joyce Gill", "Lin Shi"], "undergraduate",
               [2025, 2025], "Summer REUs & Interns (2025)", note="summer REU/intern")
        + _oak(["Julia Fang", "Kristina Jenkins"], "undergraduate", [2024, 2024], "Summer REUs & Interns (2024)",
               note="summer REU/intern")
    ),
    pubs=[PUB(OK, mode="css:li.pub", title_css="span.pub-title")],
    notes=("OAK Lab single-page site (theoaklab.org, linked from the HCII profile) with People (current PI, "
           "scientists/postdocs, PhD, undergrads) and Alumni (PhD with years, Master's 2024-2026, visitors/staff, "
           "undergrads and REUs by year). Lab is CMU-only (PI at CMU HCII throughout the window), so the undated "
           "visitor/coordinators are kept. Publications are on the same page: css li.pub + span.pub-title "
           "excludes the press/news list that auto mode picked up."),
    blocked=[],
)

# ---------------------------------------------------------------- Sarah Cen
D["Sarah Cen"] = dict(
    lab_site=None,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes=("No lab or personal website found. Input had no lab_url. Searched: S3D profile URL "
           "(s3d.cmu.edu/people/core-faculty/cen-sarah.html, 404), ECE bio (404), EPP directory bio "
           "(epp.engineering.cmu.edu/directory/bios/cen-sarah.html: bio, research interests, media mentions; no "
           "website link, no students, no publication list), two web searches (only MIT Rising Stars and Stanford "
           "RegLab/HAI postdoc profiles), and sarahcen.com (no such host). Recently joined CMU (ECE/EPP, S3D "
           "affiliation) after a Stanford postdoc."),
    blocked=[],
)

# ---------------------------------------------------------------- Justine Cassell
CA16 = WB + "20161101190055id_/http://articulab.hcii.cs.cmu.edu/members/"
CA18 = WB + "20180308210032id_/http://articulab.hcii.cs.cmu.edu/members/"
CA19 = WB + "20191018191114id_/http://articulab.hcii.cs.cmu.edu/members/"
D["Justine Cassell"] = dict(
    lab_site="http://articulab.hcii.cs.cmu.edu/",
    people_page=CA18,
    people_pages=[CA16, CA18, CA19, "https://www.justinecassell.com/articulab/members/",
                  "https://www.justinecassell.com/articulab/members/previous-members"],
    members=[
        M('Yoichi Matsuyama', 'postdoc', None, CA16, q='Yoichi Matsuyama is a Post Doctoral Fellow in the Human-Computer Interaction'),  # Postdocs
        M('Zhen Bai', 'postdoc', None, CA16, q='Zhen Bai is a post-doctoral fellow at the ArticuLab. She leads the Sensing'),  # Postdocs
        M('Tanmay Sinha', 'phd', None, CA16, q='Tanmay Sinha Tanmay is a doctoral student in Language Technologies Institute in'),  # Ph.D Students
        M('Samantha Finkelstein', 'phd', None, CA16, q='Samantha Finkelstein Samantha is a doctoral student in human-computer interaction who is'),  # Ph.D Students
        M('Ran Zhao', 'phd', None, CA16, q='Ran Zhao is a doctoral Student in the Language Technologies Institute at'),  # Ph.D Students
        M('Michael Madaio', 'phd', None, CA16, q='Michael Madaio Michael is currently a PhD student in the Human-Computer Interaction'),  # Ph.D Students
        M('Fadi Botros', 'masters', None, CA16, q='Fadi Botros is currently pursuing a Master’s in Intelligent Information Systems'),  # Master Students
        M('Jiajia Li', 'visitor', None, CA16, q='Jiajia Li Jiajia is a Visiting Research Scholar in Articulab and a second-year'),  # Visiting Scholar
        M('David Slebodnick', 'staff', None, CA16, q='David Slebodnick David graduated the Art Institute of Pittsburgh in 2009 with a'),  # Staff
        M('Luo Yi Tan', 'masters', None, CA16, q='Luo Yi Tan Luo Yi is currently pursuing a Masters in Entertainment Technology'),  # Graduate Research Assistants
        M('Anna Tan', 'undergraduate', None, CA16, q='Anna Tan Anna is a senior student majoring in Computer Science and Cognitive'),  # Undergraduate Research Assistants
        M('Jarret Lin', 'undergraduate', None, CA16, q='Jarret Lin Jarret is a senior at Carnegie Mellon University, double majoring in'),  # Undergraduate Research Assistants
        M('Zoey Feng', 'undergraduate', None, CA16, q='Zoey Feng Zoey is a sophomore at CMU majoring in Business and Administration.'),  # Undergraduate Research Assistants
        M('Grace Cha', 'undergraduate', None, CA16, q='Grace Cha is a sophomore majoring in Design and minoring in HCI. She will be'),  # Undergraduate Research Assistants
        M('Angela Liang', 'undergraduate', None, CA16, q='Angela Liang is a junior at Carnegie Mellon University majoring in Cognitive'),  # Undergraduate Research Assistants
        M('Gaurav Lahiry', 'undergraduate', None, CA16, q='Gaurav Lahiry Gaurav is a Junior majoring in Computer Science and minoring in HCI.'),  # Undergraduate Research Assistants
        M('Michelle Deng', 'undergraduate', None, CA16, q='Michelle Deng Michelle is a senior at Carnegie Mellon, majoring in Cognitive'),  # Undergraduate Research Assistants
        M('Changning Shou', 'undergraduate', None, CA16, q='Changning Shou Changning is a sophomore at CMU majoring in Computer Science. She is'),  # Undergraduate Research Assistants
        M('Jacqueline Myra Yeung', 'undergraduate', None, CA16, q='Jacqueline Myra Yeung and currently a fifth year architecture and human computer'),  # Undergraduate Research Assistants
        M('Lu Sun', 'undergraduate', None, CA16, q='Lu Sun Lu is a junior student majoring in Communications. She has great'),  # Undergraduate Research Assistants
        M('Daya Lee', 'undergraduate', None, CA16, q='Daya Lee Daya is an undergraduate student studying HCI and Psychology at'),  # Undergraduate Research Assistants
        M('Clare Lai', 'undergraduate', None, CA16, q='Clare Lai Clare is a rising sophomore in the CS class of 2019 hailing from'),  # Undergraduate Research Assistants
        M('Brooke Ley', 'undergraduate', None, CA16, q='Brooke Ley is an undergraduate majoring in Computer Science with plans to'),  # Undergraduate Research Assistants
        M('Hyunji Do', 'undergraduate', None, CA16, q='Hyunji Do Hyunji is an undergraduate studying Cognitive Science, with a'),  # Undergraduate Research Assistants
        M('Akanksha Kartik', 'undergraduate', None, CA16, q='Akanksha Kartik Akanksha is an undergraduate freshman student at Carnegie Mellon'),  # Undergraduate Research Assistants
        M('Alex Bainbridge', 'undergraduate', None, CA16, q='Alex Bainbridge is a Freshman Information Systems Major at Carnegie Mellon. He is an'),  # Undergraduate Research Assistants
        M('Malcolm Guya', 'undergraduate', None, CA16, q='Malcolm Guya Malcolm is a senior at Carnegie Mellon University studying'),  # Undergraduate Research Assistants
        M('Robert Huerbin', 'undergraduate', None, CA16, q='Robert Huerbin Robbie is a junior at the University of Pittsburgh majoring in'),  # Undergraduate Research Assistants
        M('Timo Baumann', 'staff', None, CA18, q='Timo Baumann is a Systems Scientist at the Language Technologies Institute at', note='Systems Scientist (LTI), Yahoo InMind project'),  # Researchers
        M('Florian Pecune', 'postdoc', None, CA18, q='Florian Pecune is a post-doctoral fellow at the Articulab, working on SARA and'),  # Researchers
        M('Gabriel Bayomi Tinoco Kalejaiye', 'masters', None, CA18, q='Gabriel Bayomi Tinoco Kalejaiye Gabriel is a Brazilian engineer and is currently os his master’s'),  # Master Students
        M('Alankar Jain', 'masters', None, CA18, q='Alankar Jain Alankar is currently pursuing his Master’s in Language Technologies'),  # Master Students
        M('Bhargavi Paranjape', 'masters', None, CA18, q='Bhargavi Paranjape Bhargavi is a Master’s of Language Technologies student at CMU and'),  # Master Students
        M('Vasu Sharma', 'masters', None, CA18, q='Vasu Sharma Vasu is presently pursuing Masters in Language Technologies at the'),  # Master Students
        M('Lauren Simmons', 'staff', None, CA18, q='Lauren Simmons is the lab manager of the ArticuLab. Passionate about education, she', note='listed as lab manager "Lauren Smith" with the same bio in the Nov 2016 capture'),  # Lab Manager
        M('John Choi', 'staff', None, CA18, q='John Choi A recent graduate of the BCSA Computer Science and Arts student and'),  # Staff
        M('Apoorva Nitsure', 'masters', None, CA18, q='Apoorva Nitsure is a graduate student studying Information Systems with a Business'),  # Graduate Research Assistants
        M('Matt Oresky', 'masters', None, CA18, q='Matt Oresky Matt is a Masters student in Computer Science at Carnegie Mellon', note='graduate research assistant'),  # Graduate Research Assistants
        M('Deepika Mittal', 'masters', None, CA18, q='Deepika Mittal Deepika is a Masters student in Human Computer Interaction at'),  # Graduate Research Assistants
        M('Nadine Fares', 'masters', None, CA18, q='Nadine Fares Nadine is currently pursuing her Master of Information Systems'),  # Graduate Research Assistants
        M('Katarzyna Olszewska', 'masters', None, CA18, q='Katarzyna Olszewska Kate is a graduate student pursuing Master'),  # Graduate Research Assistants
        M('Kavya Elchuri', 'masters', None, CA18, q='Kavya Elchuri Kavya is pursuing a Master’s in Information System Management at'),  # Graduate Research Assistants
        M('Vaibhav Nachankar', 'masters', None, CA18, q='Vaibhav Nachankar Vaibhav is a Graduate student currently pursuing Master’s in'),  # Graduate Research Assistants
        M('Miao Ren', 'masters', None, CA18, q='Miao Ren is a Master’s of Entertainment Technology at CMU and is working on'),  # Graduate Research Assistants
        M('Yubin Ge', 'masters', None, CA18, q='Yubin Ge is a second-year master student at University of Pittsburgh majoring'),  # Graduate Research Assistants
        M('Sophia Weisman', 'undergraduate', None, CA18, q='Sophia Weisman Sophia is a current senior at Carnegie Mellon University, majoring'),  # Undergraduate Research Assistants
        M('Shuangni Huang', 'undergraduate', None, CA18, q='Shuangni Huang is a junior at Carnegie Mellon University, majoring in BHA (with'),  # Undergraduate Research Assistants
        M('Sarah Kerman', 'undergraduate', None, CA18, q='Sarah Kerman Sarah is a senior majoring in Linguistics at the University of'),  # Undergraduate Research Assistants
        M('Maxine Kwan', 'undergraduate', None, CA18, q='Maxine Kwan Maxine is a sophomore at Carnegie Mellon University majoring in'),  # Undergraduate Research Assistants
        M('Morgan Puterbaugh', 'undergraduate', None, CA18, q='Morgan Puterbaugh Morgan is a junior at the University of Pittsburgh studying'),  # Undergraduate Research Assistants
        M('Atlas Yu', 'undergraduate', None, CA18, q='Atlas Yu is a senior majoring in computer engineering, minoring in studio'),  # Undergraduate Research Assistants
        M('Priscilla Tai', 'undergraduate', None, CA18, q='Priscilla Tai is a senior studying Computer Science with minors in Human-Computer'),  # Undergraduate Research Assistants
        M('Jiayi (Cindy) Su', 'undergraduate', None, CA18, q='Jiayi (Cindy) Su is a freshman currently majoring in Information Systems at Carnegie'),  # Undergraduate Research Assistants
        M('Neeti Ganjur', 'undergraduate', None, CA18, q='Neeti Ganjur is a sophomore at Carnegie Mellon University, double majoring in'),  # Undergraduate Research Assistants
        M('Qile Chen', 'undergraduate', None, CA18, q='Qile Chen Qile is a junior at the University of Pittsburgh majoring'),  # Undergraduate Research Assistants
        M('Fengyi Zhang', 'undergraduate', None, CA18, q='Fengyi Zhang is a sophomore majoring in Cognitive Science at CMU. She is'),  # Undergraduate Research Assistants
        M('Andy Shen', 'undergraduate', None, CA18, q='Andy Shen is a junior at Carnegie Mellon University majoring in Electrical and'),  # Undergraduate Research Assistants
        M('Michelina Astle', 'undergraduate', None, CA18, q='Michelina Astle Michelina is a senior at Chatham University with a major in'),  # Undergraduate Research Assistants
        M('Shruti Murali', 'undergraduate', None, CA19, q='Shruti Murali Shruti is a sophomore at Carnegie Mellon University pursuing a B.S.'),  # Undergraduate Research Assistants
    ],
    pubs=[PUB("https://www.justinecassell.com/articulab/publications/", mode="auto"),
          PUB("http://www.justinecassell.com/jc_papers.htm", mode="auto")],
    notes=("ArticuLab: CMU-era site articulab.hcii.cs.cmu.edu now redirects to justinecassell.com/articulab/, whose "
           "live People page lists only Inria Paris members (PI moved to Inria/ALMAnaCH ~2019-2020): all current "
           "members skipped as non-CMU. Live 'Previous Members' page lists ~190 undated names mixing CMU (2010-2019) "
           "and Inria eras, so CMU membership in the window was taken from Wayback captures of the CMU members page "
           "(Nov 2016, Mar 2018, Oct 2019); every person current in one of those is recorded once (first capture "
           "seen). Undated previous members not seen in these captures were skipped (~120, incl. pre-2016 CMU "
           "students like David Gerritsen, Paul Tepper, Zhou Yu, and Inria-era staff/interns). Lauren Smith (2016) "
           "and Lauren Simmons (2018) share the same lab-manager bio: recorded once. Two publication pages added "
           "(ArticuLab list and PI's papers page, both auto)."),
    blocked=[],
)
