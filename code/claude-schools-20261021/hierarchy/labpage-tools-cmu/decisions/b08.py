from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Jodi Forlizzi
JF_HCII = "https://hcii.cmu.edu/people/jodi-forlizzi"
D["Jodi L Forlizzi"] = dict(
    lab_site="https://jodiforlizzi.com",
    people_page=JF_HCII,
    people_pages=[JF_HCII],
    members=[
        M("Hyun Jin (Alicia) Lee", "phd", None, JF_HCII, near="Advisees"),
        M("Minjung Park", "phd", None, JF_HCII, near="Advisees"),
        M("Jini Kim", "phd", None, JF_HCII, near="Advisees"),
        M("Hao-Ping (Hank) Lee", "phd", None, JF_HCII, near="Advisees"),
        M("Neeta Khanuja", "phd", None, JF_HCII, near="Advisees"),
    ],
    pubs=[],
    notes=("jodiforlizzi.com (live + 2017/2020 captures) has no students/group section; the only per-PI member "
           "list is the 'Advisees' block of the HCII profile (role not stated there; HCII advisees are PhD "
           "students). jodiforlizzi.com/publications lists only her 1997/2007 theses + a Scholar link, so no "
           "pubs page added."),
    blocked=[],
)

# ---------------------------------------------------------------- Sarah Fox
TSL = "https://techsolidaritylab.com/"
SF_HCII = "https://hcii.cmu.edu/people/sarah-fox"
D["Sarah Fox"] = dict(
    lab_site=TSL,
    people_page=TSL,
    people_pages=[TSL, SF_HCII],
    members=[
        M("Shivani Kapania", "phd", None, TSL, q="Shivani Kapania | PhD Student, CMU HCII"),
        M("Cella Sum", "member", None, TSL, near="Alumni"),
        M("Jordan Taylor", "member", None, TSL, near="Alumni"),
        M("Franchesca Spektor", "member", None, TSL, near="Alumni"),
        M("Hunter Akridge", "member", None, TSL, near="Alumni"),
        M("Bobbie Fan", "member", None, TSL, near="Alumni"),
        M("Esther Kang", "member", None, TSL, near="Alumni"),
        M("Chinar Mehta", "member", None, TSL, near="Alumni"),
        M("Alex Ahmed", "member", None, TSL, near="Alumni"),
    ],
    pubs=[],
    notes=("Tech Solidarity Lab moved with Fox to UMich SI (~2025); it was her CMU HCII lab from ~2019, so the "
           "undated alumni are CMU-era. Pegah Moradi (Postdoctoral Fellow, UMSI) skipped as UMich. Live page "
           "only shows 'Recent Publications' as plain text (15 items), not added as pubs page."),
    blocked=[],
)

# ---------------------------------------------------------------- Fernando De la Torre
HSL = "https://www.cmu.edu/cs/humansensing/pages/people.html"
FT_RI = "https://www.ri.cmu.edu/ri-faculty/fernando-de-la-torre-frade/"
D["Fernando De La Torre Frade"] = dict(
    lab_site="http://www.humansensing.cs.cmu.edu",
    people_page=HSL,
    people_pages=[HSL, FT_RI],
    members=[
        M("Stanislav Panev", "staff", None, HSL, q="Stanislav Panev Project Scientist"),
        M("Francisco Vicente", "staff", None, HSL, q="Francisco Vicente Project Scientist"),
        M("Kennard Chan", "postdoc", None, HSL, q="Kennard Chan Postdoc"),
        M("Yehonathan Litman", "phd", None, HSL, q="Yehonathan Litman Ph.D."),
        M("Jianjin Xu", "phd", None, HSL, q="Jianjin Xu Ph.D."),
        M("Yinong (Oliver) Wang", "phd", None, HSL, q="Yinong (Oliver) Wang Ph.D."),
        M("Jose Gomes", "phd", None, HSL, q="Jose Gomes Ph.D."),
        M("Aviral Chharia", "phd", None, HSL, q="Aviral Chharia Ph.D."),
        M("Diogo Araújo", "phd", None, HSL, q="Diogo Araújo Ph.D."),
        M("Duarte Leao", "phd", None, HSL, q="Duarte Leao Ph.D.",
          note="tecnico.ulisboa.pt address; likely CMU-Portugal dual-degree PhD"),
        M("Álvaro Fernández", "masters", None, HSL, q="Álvaro Fernández M.S.R."),
        M("Runkai Zheng", "masters", None, HSL, q="Runkai Zheng M.S.R."),
        M("Saswat", "masters", None, HSL, q="Saswat M.S.R.",
          note="first name only; RI profile lists Saswat Subhajyoti Mallick as current masters student"),
        M("Saswat Subhajyoti Mallick", "masters", None, FT_RI, near="current masters students"),
        M("Xiao Fang", "masters", None, HSL, q="Xiao Fang M.S.R."),
        M("Ding-jiun Huang", "masters", None, HSL, q="Ding-jiun Huang M.S.C.V."),
        M("Srinath", "masters", None, HSL, q="Srinath M.S.C.V.", note="first name only on page"),
        M("Xia Chu", "masters", None, HSL, q="Xia Chu M.S.R."),
        M("Soham Dasgupta", "masters", None, HSL, q="Soham Dasgupta M.S.C.V."),
        M("Wen Wu", "masters", None, HSL, q="Wen Wu M.S.R.", note="RI profile spells Wenglei Wu"),
        M("Riu Cherdchusakulchai", "masters", None, HSL, q="Riu Cherdchusakulchai M.S.C.V."),
        M("Manan Shah", "masters", None, HSL, q="Manan Shah M.S.C.V."),
        M("Kashish Gandhi", "masters", None, HSL, q="Kashish Gandhi M.S.C.V."),
        M("Abhinav Mahajan", "masters", None, HSL, q="Abhinav Mahajan M.S.C.V."),
        M("Arun Reddy", "masters", None, HSL, q="Arun Reddy M.S.C.V."),
        M("Shreyans Sethi", "masters", None, HSL, q="Shreyans Sethi M.S.C.V."),
        M("Liujie Zheng", "masters", None, HSL, q="Liujie Zheng M.S.C.V."),
        M("Zizheng Zhou", "masters", None, HSL, q="Zizheng Zhou M.S.C.V."),
        M("Alejandro Amat", "masters", None, HSL, q="Alejandro Amat M.S.C.S."),
        M("Felipe San Martín", "masters", None, HSL, q="Felipe San Martín M.S.R."),
        M("Soham Kumar", "masters", None, HSL, q="Soham Kumar M.C.D.S."),
        M("Ruihao Xi", "masters", None, HSL, q="Ruihao Xi M.S.M.L."),
        M("Nick Cheng", "masters", None, HSL, q="Nick Cheng M.S.R."),
        M("Zachary Xiao", "masters", None, HSL, q="Zachary Xiao M.S.E.C.E."),
        M("Viren Velacheri", "masters", None, HSL, q="Viren Velacheri M.S.M.L."),
        M("Otto Zeng", "masters", None, HSL, q="Otto Zeng M.E.T."),
        M("Tedd Jung", "masters", None, HSL, q="Tedd Jung M.S.E.C.E."),
        M("Vishwesh Vhavle", "masters", None, HSL, q="Vishwesh Vhavle M.S.R."),
        M("Yuqin Jiao", "masters", None, HSL, q="Yuqin Jiao M.S.C.V."),
        M("Shreenidhi Sathyanarayanan", "masters", None, HSL, q="Shreenidhi Sathyanarayanan M.C.D.S."),
        M("Nhat-Tan Bui", "visitor", None, HSL, q="Nhat-Tan Bui Visiting scholar"),
        M("Lucia Aparicio", "visitor", None, HSL, q="Lucia Aparicio Visiting scholar"),
        M("Arnav Pandey", "visitor", None, HSL, q="Arnav Pandey Visiting scholar"),
        M("Amruta Dharmapurikar", "undergraduate", None, HSL, q="Amruta Dharmapurikar Undergraduate"),
        M("Meenakshi Nair", "undergraduate", None, HSL, q="Meenakshi Nair Undergraduate"),
    ],
    pubs=[],
    notes=("Human Sensing Lab (humansensing.cs.cmu.edu -> cmu.edu/cs/humansensing). Affiliated faculty/"
           "collaborators (Cohn, Cheng Zhang, Tulsiani, Jun-Yan Zhu, Holt, Bajcsy) skipped."),
    blocked=[],
)

# ---------------------------------------------------------------- Katerina Fragkiadaki
KF = "https://www.cs.cmu.edu/~katef/"
D["Katerina Fragkiadaki"] = dict(
    lab_site=KF,
    people_page=KF,
    people_pages=[KF],
    members=[
        M("Brian Yang", "phd", None, KF, near="PhD Students"),
        M("Mihir Prabhudesai", "phd", None, KF, near="PhD Students"),
        M("Ayush Jain", "phd", None, KF, near="PhD Students"),
        M("Kashu Yamazaki", "phd", None, KF, near="PhD Students"),
        M("Matthew Bronars", "phd", None, KF, near="PhD Students"),
        M("Yuxuan Kuang", "phd", None, KF, near="PhD Students"),
        M("Yash Jangir", "masters", None, KF, near="MS Students"),
        M("He Zhu", "masters", None, KF, near="MS Students"),
        M("Ziyin Xiong", "masters", None, KF, near="MS Students"),
        M("Lucy Lin", "masters", None, KF, near="MS Students"),
        M("Naman Kumar", "masters", None, KF, near="MS Students"),
        M("Robert Ren", "masters", None, KF, near="MS Students"),
        M("Nikos Gkanatsios", "phd", None, KF, q="Nikos Gkanatsios (PhD student"),
        M("Wen-hsuan Chu", "phd", None, KF, q="Wen-hsuan Chu (PhD student"),
        M("Gabriel Sarch", "phd", None, KF, q="Gabriel Sarch (PhD student"),
        M("Alexander Swerlow", "masters", None, KF, q="Alexander Swerlow (MS student",
          note="spelled Swerlow on page; Alexander Swerdlow"),
        M("Tsung-Wei Ke", "postdoc", None, KF, q="Tsung-Wei Ke (PostDoc"),
        M("Lei Ke", "postdoc", None, KF, q="Lei Ke (PostDoc"),
        M("Xian Zhou", "phd", None, KF, q="Xian Zhou (PhD student"),
        M("Fish Tung", "phd", None, KF, q="Fish Tung (PhD student", note="Hsiao-Yu Fish Tung"),
        M("Adam Harley", "phd", None, KF, q="Adam Harley (PhD student"),
        M("Theo Gevret", "phd", None, KF, q="Theo Gevret (PhD student", note="Theophile Gervet (spelled Gevret)"),
        M("Pushkal Katara", "masters", None, KF, q="Pushkal Katara (MS student"),
        M("Ricson Chen", "undergraduate", None, KF, q="Ricson Chen (undergrad",
          note="Ricson Cheng (CRA award 2019 per news list)"),
        M("Zhaoyuan Fang", "masters", None, KF, q="Zhaoyuan Fang (MS student"),
        M("Mayank Singh", "masters", None, KF, q="Mayank Singh (MS student"),
        M("Yunchu Zhang", "masters", None, KF, q="Yunchu Zhang (MS student"),
        M("Ziyan Wang", "masters", None, KF, q="Ziyan Wang (MSR student"),
        M("Shamit Lal", "masters", None, KF, q="Shamit Lal (MS student"),
        M("Yiming Zuo", "masters", None, KF, q="Yiming Zuo (MSR student"),
        M("Max Sieb", "masters", None, KF, q="Max Sieb (MSR student"),
        M("Arpit Agarwal", "masters", None, KF, q="Arpit Agarwal (MSR student"),
        M("Henry Huang", "masters", None, KF, q="Henry Huang (MS student"),
        M("Chris Ying", "masters", None, KF, q="Chris Ying (MS student"),
        M("Darshan Patil", "undergraduate", None, KF, q="Darshan Patil (undergraduate"),
        M("Nilay Pande", "masters", None, KF, q="Nilay Pande (MS"),
    ],
    pubs=[],
    notes=("Homepage 'Research Group' paragraph (PhD / MS / Former Students / Collaborators). She joined CMU in "
           "2016, so every former student is in window. Skipped 'Ishitta Mediratta (undergraduate collaborator, "
           "Meta)' as an external collaborator. Homepage shows only 'Selected Publications', added below."),
    blocked=[],
)

# ---------------------------------------------------------------- Jonathan Francis
JFR_RI = "https://www.ri.cmu.edu/ri-people/jonathan-francis/"
D["Jonathan Francis"] = dict(
    lab_site="https://jonfranc.com/",
    people_page=JFR_RI,
    people_pages=[JFR_RI],
    members=[
        M("Ingrid Navarro", "phd", None, JFR_RI, near="current phd students"),
        M("Kalie Ching", "masters", None, JFR_RI, near="current masters students"),
        M("Revanth Senthilkumaran", "masters", None, JFR_RI, near="current masters students"),
    ],
    pubs=[PUB("https://jonfranc.com/publications.html", mode="css:td", title_css="papertitle")],
    notes=("Francis is Bosch (BCAI) research scientist and RI courtesy faculty; jonfranc.com (home, RLL@BCAI, bio) "
           "has no member list. Members from the RI people page 'Students/Affiliates'. LTI seed URL is his own "
           "2022 PhD alumni entry."),
    blocked=[],
)

# ---------------------------------------------------------------- Robert Frederking
D["Robert E Frederking"] = dict(
    lab_site="https://www.cs.cmu.edu/~ref/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes=("No lab/group site. Homepage cs.cmu.edu/~ref/ is personal (no students section); LTI faculty profile "
           "lists no advisees. ~ref/papers.html is a pre-1995 list (nothing in 2016-2026), not added. His held "
           "students likely come from his role as LTI graduate-programs chair / SCS associate dean."),
    blocked=[],
)

# ---------------------------------------------------------------- Matt Fredrikson
MF = "https://www.mattfredrikson.com/"
MF_MEMBERS = [
    M("Kai Hu", "member", None, MF, near="Current"),
    M("Saranya Vijaykumar", "member", None, MF, near="Current", note="Saranya Vijayakumar"),
    M("Weichen Yu", "member", None, MF, near="Current"),
    M("Emily Black", "member", None, MF, near="Former"),
    M("Klas Leino", "member", None, MF, near="Former"),
    M("Zifan Wang", "member", None, MF, near="Former"),
    M("Ryan Wagner", "member", None, MF, near="Former"),
    M("Andy Zou", "member", None, MF, near="Former"),
    M("Samuel Yeom", "member", None, MF, near="Former"),
    M("Han Zhang", "member", None, MF, near="Former"),
    M("Arthur Azevedo de Amorim", "postdoc", None, MF, q="Arthur Azevedo de Amorim · postdoc"),
    M("Abhishek Bichhawat", "postdoc", None, MF, q="Abhishek Bichhawat · postdoc"),
]
MF_PUBS = [PUB(MF, mode="css:div[id^=year-] li", title_css="h3")]
MF_NOTES = ("mattfredrikson.com (cs.cmu.edu/~mfredrik redirects) section 'Students & postdocs' (Current / Former; "
            "students' roles not stated, they are PhD advisees). Joined CMU 2015, so all in window. Same person "
            "as the other Fredrikson input row.")
D["Matt Fredrikson"] = dict(
    lab_site=MF,
    people_page=MF,
    people_pages=[MF],
    members=MF_MEMBERS,
    pubs=MF_PUBS,
    notes=MF_NOTES,
    blocked=[],
)
D["Matthew Fredrikson"] = dict(
    lab_site=MF,
    people_page=MF,
    people_pages=[MF],
    members=MF_MEMBERS,
    pubs=MF_PUBS,
    notes=MF_NOTES,
    blocked=[],
)

# ---------------------------------------------------------------- Daniel Fried
LARC = "https://dpfried.github.io/group/"
D["Daniel Fried"] = dict(
    lab_site=LARC,
    people_page=LARC,
    people_pages=[LARC],
    members=[
        M("Andre He", "phd", None, LARC, near="PhD Advisees"),
        M("JY Koh", "phd", None, LARC, near="PhD Advisees", note="Jing Yu Koh"),
        M("Andy Liu", "phd", None, LARC, near="PhD Advisees"),
        M("Saujas Vaduguru", "phd", None, LARC, near="PhD Advisees"),
        M("Zora Wang", "phd", None, LARC, near="PhD Advisees", note="Zora Zhiruo Wang"),
        M("Yiqing Xie", "phd", None, LARC, q="Collaborators YX Yiqing Xie advised by Carolyn Rose",
          note="CMU LTI PhD listed under Collaborators (primary advisor Rose)"),
        M("Atharva Naik", "phd", None, LARC, q="Atharva Naik advised by Carolyn Rose",
          note="listed under Collaborators; LTI profile lists him as Fried advisee"),
        M("Alex Wilf", "phd", None, LARC, q="Alex Wilf advised by Louis-Philippe Morency",
          note="listed under Collaborators; LTI profile lists him as Fried advisee"),
        M("Alex Xie", "masters", None, LARC, q="Alumni AX Alex Xie MLT"),
    ],
    pubs=[PUB(LARC, mode="css:ul.publication-list li", title_css="a")],
    notes=("LARC group page (dpfried.github.io/group/). Fried joined CMU Aug 2022. Collaborators listed on the "
           "page are CMU PhD students with other primary advisors; kept with notes."),
    blocked=[],
)

# ---------------------------------------------------------------- John Galeotti
JG_RI = "https://www.ri.cmu.edu/ri-faculty/john-galeotti/"
BIG = "https://www.ri.cmu.edu/robotics-groups/biomedical-image-guidance/"
D["John Michael Galeotti"] = dict(
    lab_site=BIG,
    people_page=BIG,
    people_pages=[BIG, JG_RI],
    members=[
        M("Gautam Rajendrakumar Gare", "phd", None, JG_RI, near="current phd students"),
        M("James Emilian Uvan Joseph Antony", "member", None, BIG, near="current student"),
        M("Viekash Vinoth Kumar", "masters", None, JG_RI, near="past masters students"),
    ],
    pubs=[],
    notes=("BIG Lab has no own site (RI group page; 'Visit External Site' is ResearchGate, not fetched); "
           "cs.cmu.edu/~galeotti only links to the RI page."),
    blocked=[],
)

# ---------------------------------------------------------------- Gregory Ganger
GG_CSD = "https://csd.cmu.edu/people/faculty/gregory-ganger"
PDL = "http://www.pdl.cmu.edu/People/"
D["Gregory Ganger"] = dict(
    lab_site="http://www.pdl.cmu.edu/",
    people_page=GG_CSD,
    people_pages=[GG_CSD, PDL + "index.shtml"],
    members=[
        M("Sanjith Athlur", "phd", None, PDL + "sanjith.shtml", s="Sanjith Athlur", e="Greg Ganger"),
        M("Sherman Lim", "phd", None, PDL + "sherman.shtml", s="Sherman Lim", e="Greg Ganger"),
        M("Theo Gregersen", "phd", None, PDL + "theo.shtml", s="Theo Gregersen", e="Greg Ganger"),
        M("Timothy Kim", "masters", None, PDL + "timothyk.shtml", s="Timothy Kim", e="Greg Ganger"),
        M("Ziyue Qiu", "phd", None, PDL + "ziyue.shtml", s="Ziyue Qiu", e="Greg Ganger"),
    ],
    pubs=[],
    notes=("Ganger's group is part of the Parallel Data Lab (shared center, people index not grouped by PI); "
           "fetched all 80 current PDL person pages and kept those whose 'Advisor' names Greg Ganger. "
           "users.ece.cmu.edu/~ganger has no student list. CSD profile Advisees = same five."),
    blocked=[],
)

# ---------------------------------------------------------------- David Garlan
ABLE = "http://www.cs.cmu.edu/~able/members.json"
D["David Garlan"] = dict(
    lab_site="http://www.cs.cmu.edu/~able/",
    people_page=ABLE,
    people_pages=[ABLE, "http://www.cs.cmu.edu/~garlan/academics.htm"],
    members=[
        M("Bradley Schmerl", "staff", None, ABLE, s='{"name" : "Bradley Schmerl"', e="Principal Systems Scientist",
          note="Principal Systems Scientist (research staff), co-runs ABLE"),
        M("Pedro Bravo Mendes", "phd", None, ABLE, s='{"name" : "Pedro Bravo Mendes"', e="PhD Student"),
        M("Tobias Dürschmid", "phd", [None, 2025], ABLE, s='{"name" : "Tobias Dürschmid"', e="Graduated 2025"),
        M("Ryan Wagner", "phd", [None, 2025], ABLE, s='{"name" : "Ryan Wagner"', e="Graduated 2025"),
        M("Maria da Loura Casimiro", "phd", [None, 2024], ABLE, s='{"name" : "Maria da Loura Casimiro"',
          e="Graduated 2024"),
        M("Changjian Zhang", "phd", [None, 2024], ABLE, s='{"name" : "Changjian Zhang"', e="Graduated 2924",
          note="page typo 'Graduated 2924'; thesis s3d2024"),
        M("T.J. Glazier", "phd", [None, 2023], ABLE, s='{"name" : "T.J. Glazier"', e="Graduated 2023"),
        M("Paulo Casanova", "phd", [None, 2023], ABLE, s='{"name" : "Paulo Casanova"', e="Graduated 2023"),
        M("Vishal Dwivedi", "phd", [None, 2022], ABLE, s='{"name" : "Vishal Dwivedi"', e="Graduated 2022"),
        M("Roykrong Sukkerd", "phd", [None, 2022], ABLE, s='{"name" : "Roykrong Sukkerd"', e="Graduated 2022"),
        M("Cody Kineer", "phd", [None, 2021], ABLE, s='{"name" : "Cody Kineer"', e="Graduated 2021",
          note="Cody Kinneer"),
        M("Ashutosh Pandey", "phd", [None, 2020], ABLE, s='{"name" : "Ashutosh Pandey"', e="Graduated 2020"),
        M("Ivan Ruchkin", "phd", [None, 2018], ABLE, s='{"name" : "Ivan Ruchkin"', e="Graduated 2018"),
        M("Gabe Moreno", "phd", [None, 2017], ABLE, s='{"name" : "Gabe Moreno", "desc"', e="Graduated 2017"),
    ],
    pubs=[PUB("https://acme.able.cs.cmu.edu/pubs/api/publications/", mode="json",
              note="ABLE group publication database API (the data behind ~able/publications.html)")],
    notes=("ABLE group members are loaded by JS from ~able/members.json. Faculty Eunsuk Kang and Shihong Huang "
           "and affiliated researchers at other institutions skipped. Graduates before 2016 skipped (Barnes 2013, "
           "Cheng 2008, Poladian, Fairbanks, Sousa, Spitznagel, Monroe, Ockerbloom, Allen, Kruger)."),
    blocked=[],
)
