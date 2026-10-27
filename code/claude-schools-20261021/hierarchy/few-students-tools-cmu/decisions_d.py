"""Worker D decisions (CMU few-students investigation): S3D / RI / CBD PIs.

Brett Browning, Sarah Cen, Justin Chan, Phillip Compeau, Inseung Kang, Patrick Park, Jürgen Pfeffer,
Matthew Johnson-Roberson, Christian Cuba Samaniego, Anthony Stentz, George D Stetten, Christopher Timperley, Wei Wu.
"""
from dhelp import Q, SE, ST, WB

D = {}

# ---------------------------------------------------------------------------- Justin Chan
CHAN = "https://semanticsignals.com/cadre.html"   # people fragment the lab site (semanticsignals.com) loads via data-include
D["Justin Chan"] = dict(
    students=[
        ST("Mengning Li", "postdoc", None, Q(CHAN, "Mobile innovators Justin Chan Assistant Professor and Principal Investigator Mengning Li Postdoc")),
        ST("Siqi Zhang", "phd", None, Q(CHAN, "Siqi Zhang Ph.D. Student co-advised with Mayank Goel")),
        ST("Jiangyifei Zhu", "phd", None, Q(CHAN, "Jiangyifei Zhu Ph.D. Student co-advised with Swarun Kumar")),
        ST("Freddy Liu", "phd", None, Q(CHAN, "Freddy Liu Ph.D. Student co-advised with Swarun Kumar")),
        ST("Dongrak Choi", "other", None, Q(CHAN, "Dongrak Choi Visiting Ph.D. Student from Seoul National University"),
           note="Visiting PhD student (Seoul National University)."),
        ST("Leah Zhang", "undergraduate", None, Q(CHAN, "Leah Zhang Undergraduate")),
        ST("Ashee Bansaal", "undergraduate", None, Q(CHAN, "Ashee Bansaal Undergraduate")),
        ST("Anika Sharma", "undergraduate", None, Q(CHAN, "Anika Sharma Undergraduate")),
        ST("Alexandra Yin", "undergraduate", None, Q(CHAN, "Alexandra Yin Undergraduate Alumni network")),
        ST("Xiyuxing Zhang", "other", None, Q(CHAN, "Alumni network Xiyuxing Zhang Visiting Ph.D. from Tsinghua"),
           note="Lab alumnus: visiting PhD student from Tsinghua."),
        ST("Kuang Yuan", "member", None, Q(CHAN, "Kuang Yuan Affiliated Ph.D. Student advised by Swarun Kumar, → Meta"),
           note="Lab alumnus; affiliated PhD student whose advisor is Swarun Kumar."),
        ST("Saksham Bhutani", "masters", None, Q(CHAN, "Saksham Bhutani Masters → Columbia University PhD")),
        ST("Zhikai Qin", "other", None, Q(CHAN, "Zhikai Qin Visiting Undergraduate from Tsinghua"), note="Visiting undergraduate (Tsinghua)."),
        ST("Duc Vu", "undergraduate", None, Q(CHAN, "Duc Vu Undergraduate, CRA Outstanding Undergraduate Researcher Award (finalist), → Georgia Tech PhD")),
        ST("Tao Qiang", "undergraduate", None, Q(CHAN, "Tao Qiang Undergraduate, → CMU PhD")),
        ST("Caroline Zhao", "undergraduate", None, Q(CHAN, "Caroline Zhao Undergraduate, NSF REU"), note="NSF REU student."),
        ST("Akshay Anand", "undergraduate", None, Q(CHAN, "Akshay Anand Undergraduate, NSF REU, → Intern at Caltech"), note="NSF REU student."),
        ST("Clara Palacios", "undergraduate", None, Q(CHAN, "Clara Palacios Undergraduate, → Intern at MIT")),
    ],
    lab_note=("Semantic Signals Lab (semanticsignals.com), founded at CMU in 2024; its people section ('Mobile innovators' + "
              "'Alumni network') lists 1 postdoc, 4 PhD students (all co-advised), 1 visiting PhD student, 4 undergraduates "
              "and 9 alumni."),
    notes=("The lab homepage is a JS shell; the roster is the cadre.html fragment it loads, fetched directly. Seungjoo Lee "
           "(already held) is listed there too ('co-advised with Mayank Goel'). Alumni carry no years; the lab only exists "
           "since his 2024 CMU start, so all fall in the window. His CMU homepage (cs.cmu.edu/~justinc3) has no people list; "
           "no CMU thesis is chaired by him yet (reports-archive index)."),
)

# ---------------------------------------------------------------------------- Inseung Kang
KP = "https://metamobility.cmu.edu/people"
KANG_PHD = ["Maria Tagliaferri", "Changseob Song", "Nate Shoemaker-Trejo", "Ilseung Park"]
KANG_MS = ["Rajiv Joshi", "Itak Choi", "Jinwoo Hwang", "Oscar Luo", "Jingshu Peng", "Rafay Mahmood", "Nancy Sahagun",
           "Ryan Yongsuk Lee", "Chong Li", "Sanguk Ahn"]
KANG_MS_ECE = ["Marvin Lim", "Junseo Lee"]
KANG_UG = [("Joseph Kim", "Mechanical Engineering"), ("Eric Jin", "Electrical Engineering"),
           ("Emmet McEvilley", "Mechanical Engineering"), ("Cole Drake", "Electrical and Computer Engineering & Robotics"),
           ("Danny Fiskin", "Mechanical Engineering"), ("David Newsom", "Mechanical Engineering"),
           ("Ajay Kavuri", "Computer Science"), ("Joel Jacob", "Mechanical Engineering"),
           ("Yousef Bin Hammad", "Mechanical Engineering"), ("Atri Dey", "Electrical and Computer Engineering"),
           ("Ezra Kahn", "Mechanical Engineering"), ("Chloe Lin", "Mechanical Engineering")]
D["Inseung Kang"] = dict(
    students=(
        [ST(n, "phd", None, Q(KP, n + " Mechanical Engineering")) for n in KANG_PHD]
        + [ST("Jimin An", "phd", None, Q(KP, "Jimin An Mechanical Engineering Co-advised by Dr. Halilaj"))]
        + [ST(n, "masters", None, Q(KP, n + " Mechanical Engineering")) for n in KANG_MS]
        + [ST(n, "masters", None, Q(KP, n + " Electrical and Computer Engineering")) for n in KANG_MS_ECE]
        + [ST("Diya Dinesh", "masters", None, SE(KP, "Sahagun Mechanical Engineering", "Diya Dinesh Computer Science"))]
        + [ST(n, "undergraduate", None, Q(KP, f"{n} {d}")) for n, d in KANG_UG]
        + [ST("Kaustubh Kuvalekar", "masters", [None, 2024], Q(KP, "Lab Alumni Kaustubh Kuvalekar (MSME 2024)")),
           ST("Yi-Hung (Bernie) Chiu", "masters", [None, 2024], Q(KP, "Yi-Hung (Bernie) Chiu (MSME 2024)")),
           ST("Crystal Scott", "masters", [None, 2026], Q(KP, "Crystal Scott (MSME-R 202 6 )")),
           ST("Adrian Krieger", "masters", [None, 2026], Q(KP, "Adrian Krieger (MSME-R 2026)")),
           ST("Yunliang Zhao", "masters", [None, 2026], Q(KP, "Yunliang Zhao (MSME-R 2026)")),
           ST("Pragya Devashish", "other", [None, 2026], Q(KP, "Pragya Devashish (2026)"), note="Lab alumna; degree not stated.")]
    ),
    lab_note=("MetaMobility Lab (metamobility.cmu.edu), Mechanical Engineering with an RI courtesy appointment; lab founded "
              "~2023-24 (first alumni MSME 2024). People page lists 5 PhD, 13 master's and 12 undergraduate students plus 8 alumni."),
    notes=("Rajiv Joshi appears both as a current master's student and as alumnus 'MSME-R 2026'; one row. Vaidehi Wagh (already "
           "held) is the RI profile's only listed student and is in the lab alumni as 'MSR 2026'. RI profile: "
           "www.ri.cmu.edu/ri-people/inseung-kang/."),
)

# ---------------------------------------------------------------------------- Christopher Timperley
TCV = "https://chris.timperley.info/cv.pdf"
PHDA = "Ph.D. Student Advising"
MENT = "Ph.D. Student Mentoring"
REU = "Research Experience for Undergraduates (REU) Mentoring"
REU_NAMES = [("Mohamed Radalla", 2024), ("Levi Busching", 2024), ("Lauren Gayle", 2024), ("Varun Damarla", 2024),
             ("Eduardo Pareja", 2023), ("Ryan Wong", 2022), ("Mehal Kayshapp", 2021), ("Victoria Jordan", 2020),
             ("Sophia Kolak", 2019), ("Jam Marcos Hernandez", 2017)]
D["Christopher Timperley"] = dict(
    students=(
        [ST("Ben-Hau Chia", "phd", [2024, None], SE(TCV, PHDA, "Ben-Hau Chia Carnegie Mellon University")),
         ST("Trenton Tabor", "phd", [2023, None], SE(TCV, PHDA, "Trenton Tabor Carnegie Mellon University")),
         ST("Paulo Santos", "phd", [2020, None], SE(TCV, PHDA, "Paulo Santos Carnegie Mellon University & University of Lisbon"),
            note="CMU Portugal dual-degree PhD (CMU & University of Lisbon)."),
         ST("Yining Hong", "other", [2024, None], SE(TCV, MENT, "Yining Hong Software and Societal Systems Department, CMU"),
            note="CV 'Ph.D. Student Mentoring' (not advising)."),
         ST("Leticia Madureira", "other", [2023, None], SE(TCV, MENT, "Leticia Madureira Department of Chemistry, CMU"),
            note="CV 'Ph.D. Student Mentoring' (not advising)."),
         ST("Tobias Dürschmid", "other", [2021, None], SE(TCV, MENT, "Tobias Dürschmid Software and Societal Systems Department, CMU"),
            note="CV 'Ph.D. Student Mentoring' (not advising)."),
         ST("Afsoon Afzal", "other", [2017, 2021], SE(TCV, MENT, "Afsoon Afzal Software and Societal Systems Department, CMU"),
            note="CV 'Ph.D. Student Mentoring' (not advising)."),
         ST("Deborah Katz", "other", [2018, 2020], SE(TCV, MENT, "Deborah Katz Computer Science Department, CMU"),
            note="CV 'Ph.D. Student Mentoring' (not advising).")]
        + [ST(n, "undergraduate", [y, y], SE(TCV, REU, n),
              note=f"CMU REU mentee; the CV prints years and names in separate columns, year {y} assigned by column order.")
           for n, y in REU_NAMES]
    ),
    lab_note=("No separate lab page; Senior Systems Scientist (RI/NREC, S3D core faculty listing). His CV lists 4 CMU PhD "
              "advisees (incl. Andrea Miller), 5 mentored PhD students and 10 REU mentees 2017-2024."),
    notes=("Source: CV dated January 15, 2025 (chris.timperley.info/cv.pdf). Andrea Miller (= held 'Andrea Rose Miller') is "
           "in 'Ph.D. Student Advising' 2024-present. Three master's advisees 2020-2022 (Miguel Tavares, Ricardo Cordeiro, "
           "Catarina Gamboa) are University of Lisbon students and are left out. No CMU thesis chaired by him in the "
           "reports-archive index; he joined CMU as a postdoc in Oct 2016 (CV)."),
)

# ---------------------------------------------------------------------------- Wei Wu
WWP16 = WB + "20160426192812id_/http://www.cs.cmu.edu:80/~weiwu2/people.html"
CBDVI = "https://www.cmu.edu/cbd/people/visiting-interns.html"
D["Wei Wu"] = dict(
    students=[
        ST("Siwei Xie", "masters", [2016, 2016], Q(WWP16, "Siwei Xie: Master's student, Computational Biology Department, CMU")),
        ST("Xupeng Tong", "masters", [2016, 2016], Q(WWP16, "Xupeng Tong: Master's student, Computational Biology Department, CMU")),
        ST("Micol Marchetti-Bowick", "other", [2016, 2016],
           Q(WWP16, "Students who are working with me Micol Marchetti-Bowick: PhD Student (advisor: Eric Xing), Machine Learning Department, CMU"),
           note="Listed under 'Students who are working with me'; advisor Eric Xing."),
        ST("Pengtao Xie", "other", [2016, 2016], Q(WWP16, "Pengtao Xie: PhD Student (advisor: Eric Xing), Machine Learning Department"),
           note="Listed under 'Students who are working with me'; advisor Eric Xing."),
        ST("Charlotte Barretto", "other", None, Q(CBDVI, "Current Visiting Interns Charlotte Barretto Wei Wu Lab"),
           note="CBD current visiting intern, Wei Wu Lab."),
        ST("Ke Chen", "other", [2025, 2025], Q(CBDVI, "Ke Chen Wei Wu Lab January 1- December 31, 2025"),
           note="CBD past visiting intern, Wei Wu Lab."),
    ],
    lab_note=("Wei Wu research group (cs.cmu.edu/~weiwu2); its People page lists 'Current Students' (1 PhD, 2 master's) and "
              "'Students who are working with me' (2 MLD PhD students) unchanged from the April 2016 capture to today."),
    notes=("Dated with the 2016-04-26 Wayback capture of people.html (the live page is identical and stale). Seojin Bang "
           "(held) is the PhD student. CBD visiting-interns page adds 2 interns. KiltHub searches on 'Wei Wu' are swamped by "
           "authors of that name; no CBD/CPCB page in reach names him as advisor of anyone else. CBD theses are not in the "
           "reports-archive index."),
)

# ---------------------------------------------------------------------------- Christian Cuba Samaniego
CBDRS = "https://www.cmu.edu/cbd/people/research-staff.html"
D["Christian Cuba Samaniego"] = dict(
    students=[
        ST("Sushmita Halder", "member", None,
           Q(CBDRS, "Sushmita Halder Research Associate Ray and Stephanie Lane Computational Biology Department Gates-Hillman Complex Room 7603 Cuba Samaniego Lab"),
           note="Research associate (staff) in the Cuba Samaniego Lab."),
        ST("Kriva Shah", "other", [2026, 2026], Q(CBDVI, "Kriva Shah Christian Cuba Samaniego Lab June-September 2026"),
           note="CBD visiting intern."),
    ],
    lab_note=("New lab: joined CMU Computational Biology in 2025 (own site: 'In 2025, I joined the Computational Biology "
              "Department'); no lab people page. CBD pages list 2 PhD students (held), 1 research associate, 1 visiting intern."),
    notes=("Personal site christiansami.wixsite.com/cecubasamaniego has no people page. CPCB PhD students page names him as "
           "advisor of Frank Britto Bisso and Terry Ma (both held). No KiltHub theses under his name."),
)

# ---------------------------------------------------------------------------- Matthew Johnson-Roberson
DROPP = "https://droplab.ri.cmu.edu/people-1"
D["Matthew Johnson-Roberson"] = dict(
    students=[
        ST("Weiming (William) Zhi", "postdoc", None, Q(DROPP, "Post Docs Featured Weiming (William) Zhi")),
        ST("Diana Frias Franco", "member", None,
           Q("https://www.ri.cmu.edu/ri-people/diana-frias-franco/",
             "Diana Frias Franco PhD Student Office: 4123 Newell-Simon Hall Advisor: Aaron M. Johnson Lab: Deep Robot Optical Perception (DROP) Lab"),
           note="RI PhD student in the DROP Lab (RI group page lists her as its current student); advisor Aaron M. Johnson."),
    ],
    lab_note=("DROP (Deep Robot Optical Perception) Lab, moved from Michigan when he became RI Director in 2022; CMU people "
              "page lists 1 postdoc and 1 graduate student (Tianyi Zhang, held), and the RI group page 1 current student."),
    notes=("The DROP lab alumni (Jie Li, Katherine Skinner, Wonhui Kim, Ming-Yuan Yu, Gideon Billings, Corina Barbalata, "
           "Eduardo Iscar Rüland) are University of Michigan students and are left out. RI events: he chairs Tianyi Zhang's "
           "2024 proposal and 2025 defense (KiltHub 30533489, held); other RI theses list him only as a member. An RI news "
           "post names graduate student Kaining Huang as a co-author on his team, which is not an advising relation. No RI "
           "faculty profile is live for him (ri-faculty and ri-people slugs 404)."),
)

# ---------------------------------------------------------------------------- George D Stetten
VIA = "https://web.pitt.edu/vialab/1327-2/"
HORV = ("https://www.ri.cmu.edu/event/the-optical-coherence-tomography-microsurgical-augmented-reality-system-oct-mars-"
        "a-novel-device-for-microsurgeries-3/")
D["George D Stetten"] = dict(
    students=[
        ST("Samantha Horvath", "phd", [None, 2016],
           SE(HORV, "Samantha Horvath Carnegie Mellon University Friday, September 9", "Committee: George Stetten, Co-chair", long=True),
           note="RI PhD thesis defense 2016-09-09, co-chaired by George Stetten and John Galeotti (KiltHub 6723734 lists both as advisors)."),
        ST("Zhixuan Yu", "masters", [None, 2016], Q(VIA, "Zhixuan Yu MS, BME, CMU, December 2016"),
           note="VIA Lab past member; CMU BME master's, December 2016."),
        ST("Han-Yu Lee", "masters", [2018, 2018],
           SE(WB + "2017id_/http://www.vialab.org/main/Home/People.html", "Present Members", "Han-Yu Lee Masters Candidate, Mechanical Engineering, CMU"),
           note="VIA Lab present member in the 2018-01-17 Wayback capture (CMU MechE master's candidate)."),
        ST("Tejas Mathai", "member", [None, 2019],
           Q(VIA, "Tejas Mathai, M.S. MS, BME CMU Internships Stanford and Siemens at Princeton PhD, Robotics Institute, CMU"),
           note=("VIA Lab past member; RI PhD defended 2019-05-28 as Tejas Sudharshan Mathai, committee chaired by John "
                 "Galeotti with Stetten a member.")),
    ],
    lab_note=("Visualization and Image Analysis (VIA) Lab, based in Pitt Bioengineering (Stetten is Professor at Pitt and "
              "Adjunct Research Professor at RI). Its people page lists mostly Pitt students; 3 people with a dated CMU "
              "connection in 2016-2026 besides held Samantha Horvath."),
    notes=("Only VIA members with a CMU program and an in-window date are kept. Left out: Pitt-only students (most of the "
           "list); Randy Lee and Jihang Wang (CMU BME MS predates their 2016/2017 Pitt PhDs); Ada Zhang (RI PhD, undated); "
           "John Galeotti (now RI faculty). "
           "RI profile's 'past phd students' (John Galeotti, Samantha J. Horvath, Damion Shelton): only Horvath is in the "
           "window. No reports-archive thesis chaired by him."),
)

# ---------------------------------------------------------------------------- Jürgen Pfeffer
D["Jürgen Pfeffer"] = dict(
    students=[
        ST("Momin Malik", "phd", [None, 2018], must=["Momin M. Malik"], ev=
           SE("http://reports-archive.adm.cs.cmu.edu/anon/isr2018/abstracts/18-105.html", "Momin M. Malik August 2018 Ph.D. Thesis",
              "Pfeffer (Co-Chair)", long=True),
           note="CMU-ISR-18-105, Societal Computing PhD 2018, co-chaired with Anind K. Dey (held as 'Momin Malik')."),
        ST("Hemank Lamba", "phd", [None, 2019],
           SE("http://reports-archive.adm.cs.cmu.edu/anon/isr2019/abstracts/19-106.html", "Hemank Lamba December 2019 Ph.D. Thesis",
              "Jürgen Pfeffer (Co-Chair)", long=True),
           note="CMU-ISR-19-106, Societal Computing PhD 2019, co-chaired with Christos Faloutsos."),
    ],
    lab_note=("Adjunct in S3D; his own group is at TU Munich (pfeffer.at now 404). CMU advisees are the two Societal "
              "Computing PhDs he co-chaired (both already held)."),
    notes=("Rows add thesis sources and end years for the two held students; no new names. reports-archive ISR theses "
           "2016-2022 show no other Pfeffer chair; KiltHub '\"Jürgen Pfeffer\"' finds only these two theses; current SC "
           "PhD bios name no Pfeffer advisee. TU Munich students are out of scope."),
)

# ---------------------------------------------------------------------------- Phillip Compeau
D["Phillip Compeau"] = dict(
    students=[],
    lab_note=("Teaching-track faculty (Teaching Professor, CBD); no research group page. Only research advisee found is "
              "postdoc Roshni Bhatt (held)."),
    notes=("compeau.cbd.cmu.edu is down (connection refused); its Wayback URL list has teaching/online-education pages and "
           "no people page. His CV (2024, Wayback) has 'Faculty Mentorship' (Joshua Kangas, Dan DeBlasio: faculty, not "
           "students) and program-level 'Student Advising' (concentration/minor/MS advisor), not research advising. CBD "
           "postdoc, Lane-fellow, CPCB student, research-staff and intern pages name no other advisee; KiltHub has no thesis "
           "advised by him."),
)

# ---------------------------------------------------------------------------- Patrick Park
D["Patrick Park"] = dict(
    students=[],
    lab_note=("No lab page (patpark.org is a personal site); S3D assistant professor since 2022. Only advisee found: SC "
              "PhD student Changyang Wu (held)."),
    notes=("Checked patpark.org (home, research, CV PDF Nov 2025: no advising section), the S3D and SC profile pages, all "
           "56 Societal Computing PhD bios ('Advisor(s): Patrick Park' only on Changyang Wu), and the ISR thesis index. "
           "Co-authors on his papers (e.g. Meryl Ye, Henry Xu) carry no stated advising relation."),
)

# ---------------------------------------------------------------------------- Sarah Cen
D["Sarah Cen"] = dict(
    students=[],
    lab_note="New faculty (ECE + EPP, S3D affiliated), first listed 2026; no lab page found. One SC PhD advisee (held).",
    notes=("ECE bio and SC affiliated-faculty page carry no student list; sarahcen.com refuses connections; EPP directory "
           "has no advisor fields; KiltHub has nothing. Steven Luo (held) is the only advisee found."),
)

# ---------------------------------------------------------------------------- Anthony Stentz
D["Anthony Stentz"] = dict(
    students=[],
    lab_note=("RI Research Professor (NREC); left for industry (Uber ATG) around 2015-16. RI profile lists 22 past PhD and 9 "
              "past master's students, all but the two held ones graduated before 2016."),
    notes=("RI people page (ri-people/anthony-tony-stentz) 'past phd students' and 'past masters students' carry no years; "
           "the in-window ones are Felix Duvallet and Jacqueline Libby (held; Libby's KiltHub thesis 11371482, 2019, "
           "Advisor(s): Anthony Stentz). KiltHub '\"Stentz\"' finds no other 2016+ thesis. The Wayback capture of his "
           "RI page (2018-01-02 capture) carries no student list at all."),
)

# ---------------------------------------------------------------------------- Brett Browning
D["Brett Browning"] = dict(
    students=[],
    lab_note="RI faculty who left CMU for industry around 2016; only 2016 advisee is Hatem Alismail (held).",
    notes=("cs.cmu.edu/~brettb and his RI profile are gone; KiltHub '\"Brett Browning\"' gives only Alismail's 2016 RI "
           "dissertation (Advisor(s): Brett Browning, Simon Lucey). His homepage in the 2016-12-06 Wayback capture lists "
           "'postdocs and students that I am advising or have advised' (Peter Hansen, CMU-Q postdoc; Alismail; Samreen "
           "Anjum 2010/11; Brenna Argall, Kristina Rohlin, Jeremy Searock, Dinesh Govindaraju, Jennifer Lin): undated or "
           "pre-2016 (the page is stale: Argall 'currently a postdoc at EPFL'), so none is added."),
)
