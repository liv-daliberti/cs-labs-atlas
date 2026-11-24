"""Worker A decisions (CMU few-students investigation, 2026-10-22): 13 CSD-listed PIs.

Blum, Brookes, Brumley, Datta, Goldstein, Kothari, Kumar, Jason Li, Lucia, Maxion, Mitsch, Paccagnella, Ravi.
"""
from dhelp import Q, SE, ST, WB

D = {}
RA = "http://reports-archive.adm.cs.cmu.edu/anon/"
FS = "https://api.figshare.com/v2/articles/"


def ra(year, num):
    return f"{RA}{year}/abstracts/{str(year)[2:]}-{num}.html"


def kilthub(aid, author, advisor_value):
    """KiltHub thesis JSON: span from the author's full_name to the Advisor(s) value (same record)."""
    return SE(FS + str(aid), f'"full_name": "{author}"', f'"name": "Advisor(s)", "value": "{advisor_value}"',
              raw=True, long=True)


def thesis(year, num, author, chair_marker, degree="Ph.D. Thesis"):
    """reports-archive abstract page: span from '<author> <degree>' to the chair marker."""
    return SE(ra(year, num), f"{author} {degree}", chair_marker, long=True)


# ---------------------------------------------------------------------------------------------- Avrim Blum
D["Avrim Blum"] = dict(
    students=[],
    lab_note=("CMU CSD faculty until 2017, then TTIC; his cs.cmu.edu/~avrim page (Wayback 2016-2018) and current TTIC "
              "page carry no student list; SCS thesis archive 2016-2026 shows one CMU thesis he chaired (Nika Haghtalab, "
              "already held)."),
    notes=("Searched: reports-archive CS/ML thesis abstracts 2016-2026 (only Haghtalab CMU-CS-18-114 co-chaired; later "
           "theses list him as a TTIC external member, not chair), KiltHub theses with his name (all pre-2016: Yi Wu 2010, "
           "Michael Dinitz 2010, Pranjal Awasthi 2013, Liu Yang 2013), Wayback captures of cs.cmu.edu/~avrim 2016 (no "
           "student section). Jamie Morgenstern (already held) finished in 2015. TTIC-era students are out of scope."),
)

# ---------------------------------------------------------------------------------------------- Stephen Brookes
D["Stephen Brookes"] = dict(
    students=[],
    lab_note=("Personal page only; its 'Current Students' list (Ruy Ley-Wild, Carsten Varming) and 'Former Students' "
              "(theses 1995-2003) predate the window. Only in-window advisee found is Ryan Kavanagh (already held)."),
    notes=("Searched: cs.cmu.edu/~brookes, reports-archive CS theses 2016-2026 (chair only for Kavanagh CMU-CS-21-141, "
           "co-chaired with Pfenning; committee member for Qinsi Wang 2016, Evan Cavallo 2021, Di Wang 2022, Yue Niu 2024), "
           "KiltHub (no thesis advised by him). Teaching-heavy role; no further advisees found."),
)

# ---------------------------------------------------------------------------------------------- David Brumley
BR16 = WB + "20160713201512id_/https://users.ece.cmu.edu/~dbrumley/index.html"
BRQ = ("I am fortunate to advise several great PhD students: Tiffany Bao Dominic Chen Samantha Gottlieb Dimitris "
       "Konomis Matthew Maurer Rijnard van Tonder")
D["David Brumley"] = dict(
    students=[
        ST("Tiffany Bao", "phd", [None, 2018], Q(BR16, BRQ),
           note="KiltHub thesis 7207325 (ECE PhD, 2018-08), Advisor(s): David Brumley."),
        ST("Dominic Chen", "phd", None, Q(BR16, BRQ)),
        ST("Samantha Gottlieb", "phd", None, Q(BR16, BRQ)),
        ST("Dimitris Konomis", "phd", None, Q(BR16, BRQ)),
        ST("Matthew Maurer", "phd", [None, 2018], Q(BR16, BRQ),
           note="KiltHub thesis 7571519 (ECE PhD, 2018-10), Advisor(s): David Brumley."),
        ST("Rijnard van Tonder", "phd", None, Q(BR16, BRQ),
           note="Later finished his PhD in ISR (CMU-ISR) with Claire Le Goues; listed as Brumley's PhD student in 2016."),
        ST("Amit Chahal", "masters", [None, 2024], kilthub(25796629, "Amit Chahal", "David Brumley"),
           note="KiltHub MS thesis (Information Networking Institute), 2024-05."),
    ],
    lab_note=("ECE faculty with CSD courtesy (CEO of ForAllSecure); his users.ece.cmu.edu page (Wayback 2016) lists 6 "
              "current PhD students; the live page no longer resolves."),
    notes=("Sources: Wayback 2016-07 capture of users.ece.cmu.edu/~dbrumley (current PhD students), KiltHub theses with "
           "Advisor(s) David Brumley (Bao 2018, Maurer 2018, Chahal MS 2024; Avgerinos 2014, Cha 2015, Jang 2013, Schwartz "
           "2014 are pre-window). The 2019 capture lists former postdoc Maverick Woo and on-leave student Alex Rebert "
           "without dates; not added."),
)

# ---------------------------------------------------------------------------------------------- Anupam Datta
DA16 = WB + "20160430154910id_/http://www.andrew.cmu.edu/user/danupam/research.html"
DA16Q = ("PhD Students: Alejandro Carbonara (CSD), Amit Datta (ECE), Gihyuk Ko (ECE), Shayak Sen (CSD) , Postdocs: "
         "Yair Zick")
DA18 = WB + "20180322004137id_/http://www.andrew.cmu.edu/user/danupam/research.html"
DAQ = "PhD Students: Gihyuk Ko (ECE), Sophia Kovaleva (ECE), Caleb Lu (ECE), Shayak Sen (CSD)"
DAP = "Postdocs: Arthur Azevedo de Amorin , Piotr Mardziel"
D["Anupam Datta"] = dict(
    students=[
        ST("Alejandro Carbonara", "phd", [None, 2016], Q(DA16, DA16Q),
           note="Listed as a current CSD PhD student in the April 2016 capture; absent from the 2018 capture."),
        ST("Yair Zick", "postdoc", [None, 2016], Q(DA16, DA16Q),
           note="Current postdoc in the April 2016 capture; later listed among alumni (NUS faculty)."),
        ST("Gihyuk Ko", "phd", [2016, None], Q(DA18, DAQ), note="Also listed in the April 2016 capture."),
        ST("Sophia Kovaleva", "phd", None, Q(DA18, DAQ)),
        ST("Kaiji Lu", "phd", [None, 2022], kilthub(21843396, "Kaiji Lu", "Anupam Datta"),
           note="KiltHub ECE PhD thesis 2022-05, Advisor(s): Anupam Datta. Probably the 'Caleb Lu (ECE)' on the 2018 lab page."),
        ST("Zifan Wang", "phd", [None, 2023], kilthub(24026334, "Zifan Wang", "Anupam Datta, Matt Fredrikson"),
           note="KiltHub ECE PhD thesis 2023-08, co-advised with Matt Fredrikson."),
        ST("Amit Datta", "phd", [None, 2018], Q(DA18, "Amit Datta (ECE PhD 2018; Snap Inc.)"),
           note="Alumni list of the Accountable Systems Lab; KiltHub thesis 6716627 (2018-03), Advisor(s): Anupam Datta."),
        ST("Arthur Azevedo de Amorin", "postdoc", None, Q(DA18, DAP),
           note="Spelled 'Amorin' on the page (usually Arthur Azevedo de Amorim)."),
        ST("Piotr Mardziel", "postdoc", None, Q(DA18, DAP)),
    ],
    lab_note=("Accountable Systems Lab (ECE, CMU Silicon Valley; CSD courtesy); 2018 Wayback capture of his "
              "andrew.cmu.edu page lists 4 PhD students and 2 postdocs. CSD profile now 404; he left CMU for industry "
              "(TruEra) after ~2022."),
    notes=("Sources: Wayback 2016-04 and 2018-03 captures of andrew.cmu.edu/user/danupam/research.html ('Students & "
           "Postdocs'), KiltHub theses with Advisor(s) Anupam Datta (Shayak Sen 2018 already held; Amit Datta 2018; Kaiji Lu "
           "2022; Zifan Wang 2023; Divya Sharma 2015 and Arunesh Sinha 2014 pre-window). No capture after 2018 lists the "
           "group (2020-2022 captures of the homepage carry no student section)."),
)

# ---------------------------------------------------------------------------------------------- Seth Goldstein
D["Seth Goldstein"] = dict(
    students=[
        ST("Qingyang Li", "masters", [None, 2020], thesis(2020, 124, "Qingyang Li", "Seth Copen Goldstein (Chair)", "M.S. Thesis")),
        ST("Sarayu Namineni", "masters", [None, 2023], thesis(2023, 142, "Sarayu Namineni", "Seth Copen Goldstein (Chair)", "M.S. Thesis")),
    ],
    lab_note=("Personal page (cs.cmu.edu/~seth) has not been updated since the late 2000s; its student lists predate "
              "2016. In-window advisees found only through SCS master's theses he chaired."),
    notes=("Searched: cs.cmu.edu/~seth, reports-archive CS theses 2016-2026 (chair of 2 MS theses; committee member for "
           "Scott Mionis MS 2021), KiltHub (only Karagozler 2012 and Mionis, advised by Franchetti). Flávio Cruz (already "
           "held) is his last PhD graduate."),
)

# ---------------------------------------------------------------------------------------------- Pravesh Kothari
PK = "https://www.cs.cmu.edu/~praveshk/"  # now redirects to his Princeton page, which keeps the CMU-era advising list
D["Pravesh Kothari"] = dict(
    students=[
        ST("Jun-Ting Hsieh", "phd", [None, 2025], thesis(2025, 131, "Jun-Ting Hsieh", "Pravesh K. Kothari (Chair, CMU/Princeton)"),
           note="'Tim Hsieh' on his advising list."),
        ST("Jeff (Sichao) Xu", "phd", [None, 2025], thesis(2025, 137, "Jeff (Sichao) Xu", "(Chair, Carnegie Mellon University / Princeton University)")),
        ST("Peter Manohar", "phd", [None, 2024], thesis(2024, 142, "Peter Manohar", "Pravesh K. Kothari (Co-Chair"),
           note="Co-chaired with Venkatesan Guruswami."),
        ST("Xinyu Wu", "phd", None, Q(PK, "Xinyu Wu (winner of the MSR Ada Lovelace Fellowship , co-advised with Ryan O'Donnell)"),
           note="Former PhD student on his advising list; co-advised with CMU's Ryan O'Donnell."),
        ST("Shuchen Li", "masters", [None, 2023], thesis(2023, 146, "Shuchen Li", "Pravesh K. Kothari (Chair)", "M.S. Thesis"),
           note="Also listed among his undergraduate advisees."),
        ST("Prashanti Anderson", "undergraduate", [None, 2023],
           Q(PK, "Prashanti Anderson ( Alan J Perlis Award for student teaching, runner up to the Alan Newell award for best undergraduate SCS thesis for 2023)")),
        ST("Misha Ivkov", "undergraduate", None,
           Q(PK, "Misha Ivkov (winner of the Mark Stehlik SCS Alumni Undergraduate Impact Scholarship , now PhD student at Stanford CS )")),
        ST("Zachary Sussman", "undergraduate", None,
           Q(PK, "Zachary Sussman (winner of the Alan Newell Award for best undergraduate SCS Thesis)")),
    ],
    lab_note=("CMU CSD faculty c. 2019-2024, now at Princeton; cs.cmu.edu/~praveshk redirects to his Princeton page, whose "
              "'Advising' section keeps his CMU-era PhD students and SCS undergraduates. Current PhD students there are "
              "Princeton students (out)."),
    notes=("Sources: SCS thesis abstracts he chaired (Hsieh 2025, Xu 2025, Manohar 2024 co-chair, Shuchen Li MS 2023; Ainesh "
           "Bakshi already held), his advising list (Xinyu Wu co-advised with O'Donnell; undergraduates with SCS awards). "
           "Former postdocs Alperen Ergür (2019-20) and Mitali Bafna (2022-23) are listed without an institution and were "
           "not added; Max Hopkins (2024-25) is Princeton-era."),
)

# ---------------------------------------------------------------------------------------------- Swarun Kumar
WT = "https://www.witechlab.com/people.html"
WTP = ("Ph.D. Students Yiwen Song Kuang Yuan Yawen Liu Veronica Muriga Co-advised by Prof. Akshitha Sriraman and Dr. "
       "Assane Gueye Jiangyifei Zhu Co-advised by Prof. Justin Chan Freddy Liu Co-advised by Prof. Justin Chan")
WTA = ("Ph.D. Alumni Diana Zhang JHU Applied Physics Lab Haojian Jin Asst. Prof., UCSD Akshay Gadre Asst. Prof., U of "
       "Washington Jingxian Wang Asst. Prof., NUS Vaibhav Singh Apple Akarsh Prabhakara Asst. Prof., UW-Madison Junbo "
       "Zhang Apple Atul Bansal Apple")
WT18 = WB + "20180604203030id_/http://www.witechlab.com:80/people.html"
WT20 = WB + "20200806152856id_/https://www.witechlab.com/people.html"
WT22 = WB + "20220525000604id_/https://www.witechlab.com/people.html"
WT18U = ("Undergraduate Students Junsu Jang Summer Interns Summer 2017 Interns: Zhijian Yang , Nan Zhou , Junsu Jang , "
         "and Atul Bansal Summer 2016 Interns: Zijian Chen Zhenyu Song Raghav Sonavane")
WT20I = "Summer 2019 Interns: Ke Li, Milind Srivastava and Yash Jain Summer 2018 Interns: Rajarshi Saha and Junbo Zhang"
WT22I = "Summer 2021 Interns: Riddhiman Lahiri Diksha Agarwal"
WT_INTERNS = [  # (name, summer, capture, quote)
    ("Zhijian Yang", 2017, WT18, WT18U), ("Nan Zhou", 2017, WT18, WT18U),
    ("Zijian Chen", 2016, WT18, WT18U), ("Zhenyu Song", 2016, WT18, WT18U), ("Raghav Sonavane", 2016, WT18, WT18U),
    ("Ke Li", 2019, WT20, WT20I), ("Milind Srivastava", 2019, WT20, WT20I), ("Yash Jain", 2019, WT20, WT20I),
    ("Rajarshi Saha", 2018, WT20, WT20I),
    ("Riddhiman Lahiri", 2021, WT22, WT22I), ("Diksha Agarwal", 2021, WT22, WT22I),
]
D["Swarun Kumar"] = dict(
    students=[
        ST("Yiwen Song", "phd", None, Q(WT, WTP)),
        ST("Kuang Yuan", "phd", None, Q(WT, WTP)),
        ST("Yawen Liu", "phd", None, Q(WT, WTP)),
        ST("Veronica Muriga", "phd", None, Q(WT, WTP), note="Co-advised with Akshitha Sriraman and Assane Gueye."),
        ST("Jiangyifei Zhu", "phd", None, Q(WT, WTP), note="Co-advised with Justin Chan."),
        ST("Freddy Liu", "phd", None, Q(WT, WTP), note="Co-advised with Justin Chan."),
        ST("Mohamed Ibrahim Ahmed", "postdoc", None, Q(WT, "Postdoctoral Alumni Mohamed Ibrahim Ahmed")),
        ST("Diana Zhang", "phd", [None, 2021], Q(WT, WTA), note="KiltHub thesis 19216740 (2021-06), Advisor(s): Swarun Kumar."),
        ST("Akshay Gadre", "phd", [None, 2022], Q(WT, WTA), note="KiltHub thesis 22045250 (2022-08), Advisor(s): Swarun Kumar."),
        ST("Jingxian Wang", "phd", [None, 2022], Q(WT, WTA), note="KiltHub thesis 22144685 (2022-08), Advisor(s): Swarun Kumar."),
        ST("Vaibhav Singh", "phd", [None, 2023], Q(WT, WTA), note="KiltHub thesis 24116229 (2023-08), Advisor(s): Swarun Kumar and Osman Yagan."),
        ST("Akarsh Prabhakara", "phd", [None, 2024], Q(WT, WTA), note="KiltHub thesis 28754774 (2024-12), Advisor(s): Anthony Rowe, Swarun Kumar."),
        ST("Junbo Zhang", "phd", [None, 2024], Q(WT, WTA), note="KiltHub thesis 26937616 (2024-08), Advisor(s): Swarun Kumar."),
        ST("Atul Bansal", "phd", [2017, None], Q(WT, WTA), note="Also a Summer 2017 intern (2018 capture)."),
        ST("Junsu Jang", "undergraduate", [2017, 2018], Q(WT18, WT18U),
           note="Undergraduate student in the 2018 capture; Summer 2017 intern."),
    ] + [ST(n, "other", [y, y], Q(src, q), note=f"Summer {y} intern hosted by the WiTech Lab.") for n, y, src, q in WT_INTERNS],
    lab_note=("WiTech Lab (Laboratory for Emerging Wireless Technologies), CMU ECE with CSD/HCII affiliation; lab People "
              "page lists 6 current PhD students, 1 postdoc alumnus and 8 PhD alumni; 2018-2022 captures add 1 "
              "undergraduate and dated summer interns 2016-2021."),
    notes=("Sources: witechlab.com/people.html live (linked from his swarunkumar.com page) and Wayback captures 2018-06, "
           "2020-08, 2022-05; KiltHub theses with Advisor(s) Swarun Kumar give graduation years. Haojian Jin is already "
           "held (also HCII thesis CMU-HCII-22-105, co-chaired by Kumar). 'Graduate Collaborators' advised by others "
           "(Rashad Eletreby, Revathy Narayanan) are not added. Junbo Zhang was a Summer 2018 intern before his PhD."),
)

# ---------------------------------------------------------------------------------------------- Jason Li
D["Jason Li"] = dict(
    students=[],
    lab_note=("New lab: CMU CSD faculty since 2023 (CMU PhD 2021, CMU-CS-21-119); homepage (q3r.github.io) lists 2 "
              "current students, both already held."),
    notes=("Searched: homepage, CSD profile (Advisees: Henry Fleischmann, George Li), SCS theses 2016-2026 (committee "
           "member only: Owen Li MS 2025, Jun-Ting Hsieh PhD 2025). Genuinely small/new group."),
)

# ---------------------------------------------------------------------------------------------- Brandon Lucia
AB = "https://abstract.ece.cmu.edu/people.html"
ABP = ("PhD Students Souradip Ghosh co-advised w/ Nathan Beckmann Nathan Serafin co-advised w/ Nathan Beckmann Guy Wilks "
       "co-advised w/ Nathan Beckmann Sun A Cho co-advised w/ Nathan Beckmann Ania Krzyżańska co-advised w/ Ken Mai "
       "McKenzie van der Hagen")


def abg(name, tail):
    return Q(AB, name + " — first employment: " + tail)


def abr(name, yrs):
    return Q(AB, f"{name} ({yrs})")


LUCIA_RA = [  # (name, years text, [first, last])
    ("Jaehyun Lim", "2024–", [2024, None]), ("David Peng", "2024–", [2024, None]), ("Yufei Shi", "2023–", [2023, None]),
    ("Haochen Zhang", "2023–2024", [2023, 2024]), ("M Nguyen", "2022–2024", [2022, 2024]),
    ("Saral Tayal", "2022–2023", [2022, 2023]), ("Abhishek Anand", "2021–2023", [2021, 2023]),
    ("Alok Anand", "2021–2023", [2021, 2023]), ("Eli Wirth-Aptley", "2021–2023", [2021, 2023]),
    ("Anthony Martinez", "2021–2023", [2021, 2023]), ("Chad Taylor", "2020–2023", [2020, 2023]),
    ("Shize Che", "2020–2022", [2020, 2022]), ("Fayyaz Zaidi", "2020–2021", [2020, 2021]), ("Hailang Liou", "2019", [2019, 2019]),
    ("Myles Sherman", "2018–2019", [2018, 2019]), ("David Hanna", "2018–2019", [2018, 2019]),
    ("Amolak Nagi", "2018–2019", [2018, 2019]), ("Suyash Bhatt", "2018", [2018, 2018]), ("Hannah Tomio", "2017", [2017, 2017]),
    ("Akshay Kulkarni", "2017", [2017, 2017]), ("Akansha Patel", "2017", [2017, 2017]),
    ("Amanda Marano", "2017–2018", [2017, 2018]), ("Neil Ryan", "2017–2018", [2017, 2018]), ("Devon White", "2017", [2017, 2017]),
    ("Chris Meredith", "2017", [2017, 2017]), ("Zesheng Li", "2016", [2016, 2016]), ("Ridhi Surana", "2016", [2016, 2016]),
]
D["Brandon Lucia"] = dict(
    students=[
        ST("Souradip Ghosh", "phd", None, Q(AB, ABP), note="Co-advised with Nathan Beckmann."),
        ST("Nathan Serafin", "phd", [2018, None], Q(AB, ABP),
           note="Co-advised with Nathan Beckmann; also listed as a research assistant 2018-2019."),
        ST("Sun A Cho", "phd", None, Q(AB, ABP), note="Co-advised with Nathan Beckmann."),
        ST("Ania Krzyżańska", "phd", None, Q(AB, ABP), note="Co-advised with Ken Mai."),
        ST("McKenzie van der Hagen", "phd", None, Q(AB, ABP)),
        ST("Harsh Desai", "phd", [None, 2025], abg("Harsh Desai", "postdoc at Yale University"),
           note="Graduated PhD; KiltHub thesis 28750451 (2025-02), Advisor(s): Brandon Lucia."),
        ST("Brad Denby", "phd", [None, 2024], abg("Brad Denby", "Assistant Professor at Virginia Tech"),
           note="Graduated PhD; KiltHub thesis 25872256 (Bradley D. Denby, 2024-05)."),
        ST("Milijana Surbatovich", "phd", [None, 2023], abg("Milijana Surbatovich", "Assistant Professor at the University of Maryland"),
           note="Graduated PhD; KiltHub thesis 24123480 (2023-08), Advisor(s): Limin Jia, Brandon Lucia."),
        ST("Emily Ruppel", "phd", [None, 2022], abg("Emily Ruppel", "Research Scientist at Bosch"),
           note="Graduated PhD; KiltHub thesis 22123241 (2022-07)."),
        ST("Vignesh Balaji", "phd", [None, 2021], abg("Vignesh Balaji", "Research Scientist, Architecture Research Group at NVIDIA"),
           note="Graduated PhD; KiltHub thesis 19229661 (2021-06)."),
        ST("Kiwan Maeng", "phd", None, abg("Kiwan Maeng", "Assistant Professor at Pennsylvania State University"),
           note="Graduated PhD (listed under 'Graduated PhD Students')."),
        ST("Alexei Colin", "phd", [None, 2018], abg("Alexei Colin", "Researcher at ISI"),
           note="Graduated PhD; KiltHub thesis 6723470 (2018-05), Advisor(s): Brandon Lucia."),
    ] + [ST(n, "member", y, abr(n, t), note="Listed under 'Current and Former Masters and Undergraduate Research Assistants'.")
         for n, t, y in LUCIA_RA] + [
        ST("Dylan Joos", "other", [2019, 2019], Q(AB, "Dylan Joos (Junior at City Charter High School) — Summer 2019"),
           note="High-school intern hosted by the lab."),
        ST("Hemank Kohli", "other", [2018, 2018], Q(AB, "Hemank Kohli (CMU APEA program) — Summer 2018"),
           note="High-school intern (CMU APEA program) hosted by the lab."),
        ST("Beth Ann Kushner", "other", [2017, 2017], Q(AB, "Beth Ann Kushner (Junior at City Charter High School) — Spring 2017"),
           note="High-school intern hosted by the lab."),
        ST("Jessie Foley", "other", [2016, 2016], Q(AB, "Jessie Foley (Junior at City Charter High School) — Summer 2016"),
           note="High-school intern hosted by the lab."),
    ],
    lab_note=("abstract Research Group (CMU ECE; CSD courtesy); lab People page lists 6 current PhD students, 8 graduated "
              "PhDs, ~35 dated masters/undergraduate research assistants and 5 high-school interns."),
    notes=("Source: abstract.ece.cmu.edu/people.html; graduation years from KiltHub theses with Advisor(s) Brandon Lucia. Lucia "
           "joined CMU in 2014, so every graduated PhD on the page overlapped the window. RAs dated 2015 and earlier are "
           "excluded; masters vs undergraduate is not distinguished on the page, so those rows are 'member'. Guy Wilks and "
           "Graham Gobieski are already held."),
)

# ---------------------------------------------------------------------------------------------- Roy Maxion
D["Roy Maxion"] = dict(
    students=[],
    lab_note=("Personal page (cs.cmu.edu/~maxion) lists courses and projects but no students; only in-window advisee "
              "found is Shing-hon Lau (already held; KiltHub MLD PhD thesis 2018, Advisor(s): Roy Maxion)."),
    notes=("Searched: personal page, CSD profile (404), SCS theses 2016-2026 (only a 'Subject Matter Expert' role on Archan "
           "Das MS 2025, advised by Stehlik/Kosbie), KiltHub (only Lau 2018)."),
)

# ---------------------------------------------------------------------------------------------- Stefan Mitsch
CV = "http://www.cs.cmu.edu/~smitsch/pdf/CV_SM_20220520.pdf"
MITSCH = [  # (name, quote, years)
    ("Emily Song", "Proof terms to proof tactics 5/2022present Emily Song", [2022, None]),
    ("Claire (Qianfan) Liu", "Quantitative ModelPlex semantics for reinforcement learning 5/2022present Claire (Qianfan) Liu", [2022, None]),
    ("Marian Qin", "Safety proofs as control boundaries for learning recovery control 5/2022present Marian Qin", [2022, None]),
    ("Ziqi Liu", "Performance optimization of verified virtual substitution 5/2022present Ziqi Liu", [2022, None]),
    ("Myra Dotzel", "Minimizing Sequents to Find Modeling Errors 1/2022present Myra Dotzel, Ben Gafford", [2022, None]),
    ("Ben Gafford", "Minimizing Sequents to Find Modeling Errors 1/2022present Myra Dotzel, Ben Gafford", [2022, None]),
    ("Megan Strauss", "Formal verification of the responsibility-sensitive safety model for 09/2021- Megan Strauss", [2021, None]),
    ("James Gallicchio", "Implicit definitions in KeYmaera X 02/2021present James Gallicchio", [2021, None]),
    ("David Bayani", "Abstraction and CEGAR for verification and explanations of neural networks 01/20191/2022 David Bayani", [2019, 2022]),
    ("Zhongyi Cao", "Hybrid program falsification 09/202112/2021 Zhongyi Cao", [2021, 2021]),
    ("Naveen Pai", "Modeling and verification of ground robots with learned controllers 01/202005/2020 Naveen Pai", [2020, 2020]),
    ("Rachel Cleaveland", "(CMU SCS Alumni Award for Undergraduate Excellence 2021, CRA Outstanding Researcher Award Honorable Mention 2021) 09/201805/2021 Rachel Cleaveland", [2018, 2021]),
    ("Yiyang Guo", "01/2018 – 08/2018 Yiyang Guo (now CS Masters CMU)", [2018, 2018]),
    ("Vaidehi Srinivas", "Simulation of cyber-physical systems models and train braking controllers 08/2017 – 04/2018 Vaidehi Srinivas", [2017, 2018]),
]
D["Stefan Mitsch"] = dict(
    students=[ST(n, "member", y, Q(CV, q),
                 note="CV section 'Undergraduate and Masters Research Mentoring' (CMU, Logical Systems Lab).")
              for n, q, y in MITSCH],
    lab_note=("Senior Systems Scientist in André Platzer's Logical Systems Lab (CSD) since 2016; no separate lab page. "
              "His 2022 CV lists 13 dated CMU undergraduate/masters research mentees; Aditi Kabra (already held) is the "
              "PhD he co-chaired (CMU-CS-26-118)."),
    notes=("Sources: CV_SM_20220520.pdf (linked from cs.cmu.edu/~smitsch). The CV's 'PhD theses committee service and "
           "mentoring' entries (Yong Kiam Tan, Rose Bohrer, Nathan Fulton, Sarah Loos) are Platzer's students on whose "
           "committees he sat - not added; masters-thesis mentees Samuel Teuber and Marvin Brieger are not placed at CMU "
           "by the CV - not added. Mentee roles are 'member' because the CV does not separate undergraduates from masters."),
)

# ---------------------------------------------------------------------------------------------- Riccardo Paccagnella
RP = "https://www.cs.cmu.edu/~rpaccagn/"
D["Riccardo Paccagnella"] = dict(
    students=[ST("Inwhan Chun", "phd", [2023, None], Q(RP, "PhD Students : Inwhan Chun (2023-present), Otso Barron (2025-present)"))],
    lab_note="New lab: CMU faculty since 2023 (S3D/CyLab, ECE courtesy); homepage lists 2 PhD students (2023-, 2025-).",
    notes="Otso Barron is already held; Inwhan Chun is new (homepage 'Students' section).",
)

# ---------------------------------------------------------------------------------------------- R. Ravi
RV = "https://www.contrib.andrew.cmu.edu/~ravi/"
RVC = "Current Ph. D. Students: Daniel Hathcock , Aidin Niaparast , Siyue Liu , Weizhong Zhang . Current postdoc: Mik Zlatin ."
RAVI_PAST = [  # (name as on page, page tail, year)
    ("Arda Antikacioglu", "Ph. D. 2017; First position: WorldQuant LLC", 2017),
    ("Jennifer Iglesias", "Ph. D. 2017; First position: Waymo", 2017),
    ("Jeremy Karp", "Ph. D. 2017; First position: Lyft", 2017),
    ("Stelios Despotakis", "Ph. D. 2018; First position: City University of Hong Kong", 2018),
    ("Yang Jiao", "Ph. D. 2018; First position: Boeing Corp", 2018),
    ("Arash Haddadan", "Ph. D. 2020; First position: Post-doctoral researcher at UVA Biocomplexity Institute", 2020),
    ("Da Qi Chen", "Ph. D. 2021; First position: Post-doctoral researcher at UVA Biocomplexity Institute", 2021),
    ("Oleksandr Rudenko", "Ph. D. 2022; First position: Jane Street Capital", 2022),
    ("Su Jia", "Ph. D. 2022; First position: Research Assistant Professor at Cornell University", 2022),
    ("Daniel de Roux", "Ph. D. 2024; First position: Google", 2024),
]
D["R. Ravi"] = dict(
    students=[ST(n, "phd", [None, y], Q(RV, f"{n} ({t})"), note="Listed under 'Past Ph.D. students' on his homepage.")
              for n, t, y in RAVI_PAST] + [
        ST("Daniel Hathcock", "phd", None, Q(RV, RVC)),
        ST("Aidin Niaparast", "phd", None, Q(RV, RVC)),
        ST("Siyue Liu", "phd", None, Q(RV, RVC)),
        ST("Weizhong Zhang", "phd", None, Q(RV, RVC)),
        ST("Mik Zlatin", "postdoc", None, Q(RV, RVC)),
        ST("Thomas Bosman", "other", [2018, 2018], Q(RV, "Thomas Bosman (visiting doctoral student from Vrie University, 2018)"),
           note="Visiting doctoral student hosted at CMU (listed under 'Past Visitors')."),
    ],
    lab_note=("Tepper School of Business faculty (CSD courtesy); homepage 'Advising' lists 4 current PhD students, 1 "
              "postdoc and a dated list of past PhD students (11 graduated 2017-2024)."),
    notes=("Source: contrib.andrew.cmu.edu/~ravi (updated April 2025). Most students are Tepper ACO/OR or Math PhDs; "
           "KiltHub confirms Daniel De Roux Uribe 2024, Da Qi Chen 2022 (Math), Su Jia 2022 with Advisor(s) R. Ravi. "
           "D Ellis Hershkowitz (spelled 'Hershkowtiz' on the page) and Subhodeep Mitra are already held."),
)
