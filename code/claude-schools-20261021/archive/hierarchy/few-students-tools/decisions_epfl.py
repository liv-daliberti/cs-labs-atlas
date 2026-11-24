"""EPFL few-students decisions (2026-10-22): students/postdocs for the 21 PI labs in hierarchy/epfl/few-students-input.json.

Every row is resolved against hierarchy/epfl/few-students-captures.sqlite by fsev (exact-substring + all-name-tokens
checks). Sources: people.epfl.ch profiles ("PhD Students" / "Past EPFL PhD Students [as codirector]"), Infoscience
thesis records (advisor field), the labs' own member pages, and the PIs' mentoring/students pages.
Policy: students and postdocs a PI's own page/profile places at EPFL; theses from 2016 on; visiting PhD students and
visiting faculty from other institutions are left out unless the lab roster itself lists them as lab members;
administrative/technical staff are left out; students of a PI's previous institution are out (Sayed/UCLA,
Foster/Cornell, Arnon/Weizmann, Vishnoi/Yale).
"""
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fsev  # noqa: E402

S_ = "epfl"
PP = "https://people.epfl.ch/"
WB = "https://web.archive.org/web/"


def prof(slug, exclude=()):
    return fsev.epfl_people_students(PP + slug, exclude=exclude)


def S(name, role, years, src, end, start=None, after=None, note=None, max_span=2500, quote=None):
    if quote:
        return fsev.S(S_, name, role, years, src, quote=quote, note=note)
    return fsev.S(S_, name, role, years, src, start=start, end=end, after=after, note=note, max_span=max_span)


def infosci(surname):
    return "https://infoscience.epfl.ch/server/api/discover/search/objects?" + urlencode(
        {"query": f"dc.contributor.advisor:{surname}", "dsoType": "ITEM", "size": 100, "page": 0})


def setyears(rows, years_by_name, note):
    for r in rows:
        if r["name"] in years_by_name:
            r["years"] = list(years_by_name[r["name"]])
            r["note"] = (r.get("note", "") + "; " + note).strip("; ")
    return rows


D = {}

# ------------------------------------------------------------------ Alcherio Martinoli (DISAL)
D["Alcherio Martinoli"] = dict(
    students=prof("alcherio.martinoli"),
    lab_note="DISAL (Distributed Intelligent Systems and Algorithms Laboratory), ENAC; long-running lab. The profile lists "
             "6 current PhD students and 14 theses defended 2016-2024 (plus earlier ones outside the window).",
    notes="people.epfl.ch/alcherio.martinoli PhD sections (theses before 2016 dropped). The DISAL people page "
          "(www.epfl.ch/labs/disal/people/) loads its team/alumni lists dynamically, so it gave no names; postdocs not "
          "covered.")

# ------------------------------------------------------------------ Ali H. Sayed (ASL)
ASL = "https://asl.epfl.ch/members/"
D["Ali H. Sayed"] = dict(
    students=prof("ali.sayed") + [
        S("Aleksandar Armacki", "postdoc", [2026, 2026], ASL, "Aleksandar Armacki Post-doc", start="Post-docs & Research staff"),
        S("Flavio Pavan", "postdoc", [2021, 2023], ASL, "Flavio Pavan (2021-2023)", start="Former Post-Doctoral Scholars"),
        S("Roula Nassif", "postdoc", [2017, 2019], ASL, "Roula Nassif (2017-2019)", start="Former Post-Doctoral Scholars"),
        S("Augusto Santos", "postdoc", [2017, 2019], ASL, "Augusto Santos (2017-2019)", start="Former Post-Doctoral Scholars"),
        S("Konstantinos Ntemos", "postdoc", [2020, 2021], ASL, "Ntemos Konstantinos (2020-2021)", start="Former Post-Doctoral Scholars",
          note="written 'Ntemos Konstantinos' on the ASL page"),
        S("Stefan Vlaski", "postdoc", [2019, 2021], ASL, "Stefan Vlaski (2019-2021)", start="Former Post-Doctoral Scholars",
          note="postdoc at EPFL 2019-2021; his 2013-2019 PhD with Sayed was at UCLA and is not counted"),
    ],
    lab_note="ASL (Adaptive Systems Laboratory), STI; Sayed moved from UCLA in 2017 (Dean of Engineering 2017-2025). EPFL-era "
             "lab: 3 current PhD students, 7 EPFL theses 2022-2026, and postdocs from 2017 on.",
    notes="people.epfl.ch/ali.sayed PhD sections + asl.epfl.ch/members (postdocs). The ASL 'Former Ph.D. Students' list "
          "also names UCLA-era students (Cassano, Alghunaim, Yuan, Vlaski, Salami, Ying, Yu, ...); no source puts their PhDs "
          "at EPFL, so they are left out. Visitors (35, mostly faculty) left out.")

# ------------------------------------------------------------------ Amin Shokrollahi (ALGO)
ALGO18 = WB + "20180118042120id_/http://algo.epfl.ch/en/group/members"
D["Amin Shokrollahi"] = dict(
    students=fsev.infoscience_theses(infosci("Shokrollahi"), ["Shokrollahi"]) + [
        S("Anna-Lena Horlemann", "member", [2016, 2018], ALGO18, "Dr. Anna-Lena Horlemann Researcher and lecturer",
          start="Prof. Amin Shokrollahi Head of ALGO and LMA",
          note="listed on the ALGO members page in the 2016-03 and 2018-01 Wayback captures (researcher and lecturer)"),
    ],
    lab_note="ALGO (Algorithmic Laboratory), IC; Shokrollahi is Professor Emeritus. The archived group page (2016) says he "
             "was on sabbatical and the group took no new students; in 2016-2018 it listed only him, one researcher, an "
             "engineer and an assistant. A genuinely closed-out lab in the window.",
    notes="Infoscience advisor search 'Shokrollahi' (10 theses; only Lyudmila Yartseva 2017, co-advised with Matthias "
          "Grossglauser, is from 2016 on; she is already held, under two name orders). Current profile has no PhD section. "
          "ALGO group pages via Wayback (2016, 2017, 2018). Nothing more exists for 2016+.")

# ------------------------------------------------------------------ Andreas Peter Burg (TCL)
TCL = "https://www.epfl.ch/labs/tcl/page-55969-en-html/"
D["Andreas Peter Burg"] = dict(
    students=prof("andreas.burg") + [
        S("Yifei Shen", "postdoc", [2026, 2026], TCL, "Yifei Shen Position Postdoctoral Researcher", start="Post-docs & Research staff"),
        S("Wenqing Song", "postdoc", [2026, 2026], TCL, "Wenqing Song Position Postdoctoral Researcher", start="Post-docs & Research staff"),
        S("Huiyu Feng", "other", [2026, 2026], TCL, "Huiyu Feng Position Guest PhD Student", start="PhD students Ludovic Damien Blanc",
          note="guest PhD student listed in the TCL PhD students section"),
        S("Baheyeldin Shalash", "other", [2026, 2026], TCL, "Baheyeldin Shalash Position Student/Auxiliary", start="PhD students Ludovic Damien Blanc"),
        S("Zongyao Li", "other", [2026, 2026], TCL, "Zongyao Li Position Trainee", start="Trainee"),
    ] + [S(n, "other", [2026, 2026], TCL, f"{n} Position Project Student", start="Other Alexios Balatsoukas Stimming",
           note="project student on the TCL people page")
         for n in ["Michel Cancalon", "Corinne Fogarty Draper", "Aadhit Manish Manke", "Paolo Rubino",
                   "Julius Theodor Thiemeyer", "Antonin Louis Ambroise Vollard"]],
    lab_note="TCL (Telecommunications Circuits Laboratory), STI; long-running lab: 13 current PhD students, 20 theses "
             "directed or co-directed 2016-2026, 2 postdocs, plus guest/project students.",
    notes="people.epfl.ch/andreas.burg PhD sections + TCL people page. Alumni on the TCL page without years are covered "
          "by the profile's dated thesis list.")

# ------------------------------------------------------------------ Andrés Cristi (GO)
CR = "https://sites.google.com/view/andres-cristi/mentoring"
D["Andrés Cristi"] = dict(
    students=prof("andres.cristi") + [
        S("Neel Patel", "postdoc", [2025, 2026], CR, "Neel Patel (2025 - 2026), postdoc, EPFL", start="Mentoring Doctoral Students and Postdocs",
          note="joint with Ola Svensson"),
        S("Vasilis Livanos", "postdoc", [2024, 2025], CR, "Vasilis Livanos (Oct 2024 - Apr 2025), visiting postdoctoral researcher, EPFL",
          start="Mentoring Doctoral Students and Postdocs", note="visiting postdoctoral researcher listed among his mentees"),
        S("João Rocha", "masters", [2025, 2025], CR, "João Rocha (2025), MSc in Computer Science", start="Master Students"),
        S("Tiago Oliveira Marques", "other", [2025, 2025], CR, "Tiago Oliveira Marques (Jun-Aug 2025), summer intern, EPFL", start="Interns and Visiting Students"),
        S("Ioannis Dorkofikis", "other", [2025, 2025], CR, "Ioannis Dorkofikis (Jun-Aug 2025), summer intern, EPFL", start="Interns and Visiting Students"),
        S("Alireza Danaei", "other", [2024, 2024], CR, "Alireza Danaei (Jul-Sep 2024), summer intern, EPFL", start="Interns and Visiting Students"),
        S("Yifan Zhou", "other", [2026, 2026], CR, "Yifan Zhou (Fall 2026)", start="Semester Projects", note="semester project"),
        S("Yilin Kong", "other", [2026, 2026], CR, "Yilin Kong (Spring 2026)", start="Semester Projects", note="semester project"),
        S("Simone Palazzotto", "other", [2026, 2026], CR, "Simone Palazzotto (Spring 2026)", start="Semester Projects", note="semester project"),
        S("Elias Mir", "other", [2025, 2025], CR, "Elias Mir (Fall 2025)", start="Semester Projects", note="semester project"),
    ],
    lab_note="Chair of Game Theory and Operations (GO), CDM; new lab (tenure-track since 2024). 3 PhD students (2024-), "
             "one postdoc, one MSc thesis, interns and semester projects; small because it is new.",
    notes="people.epfl.ch/andres.cristi + his site's Mentoring page. Left out: Eugenio Cruz Ossa (visiting student from PUC "
          "Chile) and Samuel Boite (intern at Universidad de Chile, not EPFL).")

# ------------------------------------------------------------------ Auke Ijspeert (BIOROB)
BR = "https://www.epfl.ch/labs/biorob/people/"
D["Auke Ijspeert"] = dict(
    students=prof("auke.ijspeert") + [
        S(n, "postdoc", [2026, 2026], BR, f"Dr. {n} Post-doc", start="BioRob Members Prof. Auke Ijspeert")
        for n in ["Guillaume Bellegarda", "Andrea Ferrario", "Qiyuan Fu", "Xiangxiao Liu", "Sichao Liu"]],
    lab_note="BioRob (Biorobotics Laboratory), STI; long-running lab: 10 current PhD students, 24 theses 2016-2026, 5+ "
             "current postdocs.",
    notes="people.epfl.ch/auke.ijspeert PhD sections + BioRob people page (current postdocs). The BioRob 'Past Members' "
          "list gives no years, so past postdocs are not added; collaborateurs scientifiques, technician, secretary and "
          "visitors left out.")

# ------------------------------------------------------------------ Clément Hongler (CSFT)
CS = "https://www.epfl.ch/labs/csft/members/"
CSH = "https://www.epfl.ch/labs/csft/"
hong = setyears(prof("clement.hongler"),
                {"Amire Bendjeddou": (2023, 2025), "Evgenii Golikov": (2021, 2025), "Berfin Simsek": (2019, 2023),
                 "Arthur Ulysse Jacot-Guillarmod": (2018, 2022), "Francesco Spadaro": (2017, 2021), "Sung Chul Park": (2016, 2019)},
                "start year from the CSFT members page (PhD Alumni)")
D["Clément Hongler"] = dict(
    students=hong + [
        S("Barbora Hudcová", "postdoc", [2024, 2026], CS, "Barbora Hudcová", start="Members Group Leader Clément Hongler Post-Docs",
          note="Post-Doc since May 2024 per CSFT news"),
        S("Ehsan Pajouheshgar", "postdoc", [2025, 2026], CS, "Ehsan Pajouheshgar", start="Members Group Leader Clément Hongler Post-Docs",
          note="Post-Doc since August 2025 per CSFT news"),
        S("Vassilis Papadopoulos", "postdoc", [2022, 2026], CS, "Vassilis Papadopoulos", start="Members Group Leader Clément Hongler Post-Docs",
          note="Post-Doc since December 2022 per CSFT news"),
        S("François Ged", "postdoc", [2020, 2024], CS, "François Ged (2020-2024)", start="Post-Doc Alumni"),
        S("Maxime Savoy", "postdoc", [2021, 2022], CS, "Maxime Savoy (2021-2022)", start="Post-Doc Alumni"),
        S("Franck Gabriel", "postdoc", [2018, 2022], CS, "Franck Gabriel (2018-2022)", start="Post-Doc Alumni", after="Post-Doc Alumni"),
        S("Nicolas Orantin", "postdoc", [2015, 2018], CS, "Nicolas Orantin (2015-2018)", start="Post-Doc Alumni"),
        S("Laurence Field", "postdoc", [2015, 2017], CS, "Laurence Field (2015-2017)", start="Post-Doc Alumni"),
        S("Marco Tuccio", "other", [2024, 2026], CSH, "Marco Tuccio joins the Chair as a scientific assistant, starting September 2024",
          start="Marco Tuccio", note="scientific assistant (CSFT news)"),
    ] + [S(n, "masters", [y, y], CS, f"{n} ({y})", start="Master Alumni At CSFT", after="Master Alumni At CSFT",
           note="master's thesis at CSFT")
         for n, y in [("Thomas Boys", 2016), ("Manuel Stathis", 2019), ("Nicolas Peretti", 2019), ("Nicolas Rime", 2019),
                      ("Martin Leblanc", 2020), ("Alejandro Bonell de Pascual", 2021), ("Nathanaël Genestrier", 2021),
                      ("Oguz Kaan Yüksel", 2022), ("Benjamin Dupuis", 2023), ("Wu Zhengqing", 2023), ("Marcel Bourg", 2023),
                      ("Francesco Bollero", 2023), ("Paul Bagourd", 2024), ("Wissam Pheng", 2024), ("Arthur Renard", 2024),
                      ("Noé Hollande", 2024), ("Alain Follonier", 2025), ("Spinakis Konstantinos", 2025)]],
    lab_note="Chair of Statistical Field Theory (CSFT), SB MATH; lab since 2014. 1 current PhD student, 6 theses 2019-2025, "
             "3 current and 5 past postdocs, ~18 master's theses since 2016.",
    notes="people.epfl.ch/clement.hongler PhD sections + CSFT members page (dated PhD/postdoc/master alumni) + CSFT news. "
          "'Exchanges' (students sent elsewhere) and past visitors left out.")

# ------------------------------------------------------------------ Devis Tuia (ECEO)
EC = "https://www.epfl.ch/labs/eceo/eceo/team/"
D["Devis Tuia"] = dict(
    students=prof("devis.tuia") + [
        S(n, "postdoc", [2026, 2026], EC, f"{n} Scientist", start="Post-docs & Research staff",
          note="listed as Scientist under 'Post-docs & Research staff'")
        for n in ["Théo Gnassounou", "Benjamin Kellenberger", "Etienne Pauthenet", "Gencer Sümbül", "Chiara Vanalli"]] + [
        S("Nicole Lai-Lopez", "phd", [2026, 2026], EC, "Nicole Lai-Lopez Doctoral Assistant", start="PhD students Gianfranco Basile"),
        S("Lionel Safar", "phd", [2026, 2026], EC, "Lionel Safar Doctoral Assistant", start="PhD students Gianfranco Basile"),
        S("Filip Dorm", "other", [2026, 2026], EC, "Filip Dorm Invited guest", start="Other Filip Dorm"),
    ],
    lab_note="ECEO (Environmental Computational Science and Earth Observation Laboratory), ENAC, Sion; Tuia joined EPFL in "
             "2020. 11 PhD students, 6 theses 2025-2026 (+1 co-directed 2019), 5 postdoc-level scientists.",
    notes="people.epfl.ch/devis.tuia PhD sections + ECEO team page. Matthew Parkan (2019) is a co-directed thesis from before "
          "Tuia joined EPFL (co-director credit as shown on his EPFL profile).")

# ------------------------------------------------------------------ Jean-Dominique Decotignie
D["Jean-Dominique Decotignie"] = dict(
    students=fsev.infoscience_theses(infosci("Decotignie"), ["Decotignie"]),
    lab_note="Honorary professor (invited guest, emeritus) in IC. In the window only Daniel Camilo Rojas Quirós's 2018 "
             "thesis exists; earlier theses are 1995-2010. Effectively no active lab in 2016-2026.",
    notes="Infoscience advisor search 'Decotignie' (10 theses; one from 2016 on, already held, under two name orders). The "
          "current profile has no PhD section. Note: lams.epfl.ch (the 'LAMS' department in the input) is the Laboratory "
          "for Systemic Modeling run by Alain Wegmann in the 2017 capture, so 'LAMS' may not be Decotignie's own lab.")

# ------------------------------------------------------------------ Marco Mattavelli
D["Marco Mattavelli"] = dict(
    students=prof("marco.mattavelli"),
    lab_note="Former SCI-STI-MM multimedia group; Mattavelli is now an invited guest (retired). 5 theses 2017-2024 in the "
             "window; no current students.",
    notes="people.epfl.ch/marco.mattavelli past-PhD list; Infoscience advisor search 'Mattavelli' gives the same 2016+ "
          "theses (Michalska 2017, Hernandez Lopez 2019, Bloch 2023, Besirli 2023 co-directed with Dehollain, Öztürk 2024).")

# ------------------------------------------------------------------ Mario Paolone (DESL)
D["Mario Paolone"] = dict(
    students=prof("mario.paolone"),
    lab_note="DESL (Distributed Electrical Systems Laboratory), STI; large long-running lab: 10 current PhD students and "
             "31 theses directed or co-directed 2016-2026.",
    notes="people.epfl.ch/mario.paolone PhD sections. The DESL site (www.epfl.ch/labs/desl/) has no people page; postdocs "
          "not covered.")

# ------------------------------------------------------------------ Maryam Kamgarpour (SYCAMORE)
SY = "https://www.epfl.ch/labs/sycamore/biography/"
SYH = "https://www.epfl.ch/labs/sycamore/"
D["Maryam Kamgarpour"] = dict(
    students=prof("maryam.kamgarpour") + [
        S(n, "phd", [2026, 2026], SY, f"{n} Doctoral Assistant", start="PhD Students Daniele De Cecco",
          note="started September 2026 (Sycamore news)")
        for n in ["Emad Emamjomeh", "Alipasha Montaseri", "Romina Nobahari"]] + [
        S("Aymeric Capitaine", "postdoc", [2026, 2026], SYH,
          quote="Welcome to Dr Capitaine Aymeric who started as Post Doc @ Sycamore in September 2026",
          end=None, note="written 'Capitaine Aymeric' in the news item"),
    ],
    lab_note="SYCAMORE (Systems Control and Multiagent Optimization Research), STI; Kamgarpour joined EPFL in 2022 "
             "(previously ETH Zurich, UBC). 12 PhD students (3 started Sept 2026), 2 theses 2026, 1 co-directed 2023, 1 new postdoc.",
    notes="people.epfl.ch/maryam.kamgarpour + Sycamore current-staff page + Sycamore news.")

# ------------------------------------------------------------------ Maryna Viazovska (TN)
TN = "https://www.epfl.ch/labs/tn/number-theory-tn/people/"
D["Maryna Viazovska"] = dict(
    students=prof("maryna.viazovska") + [
        S(n, "member", [2026, 2026], TN, f"{n} Position Scientist", start="People Laetitia Al-Sulaymaniyin",
          note="listed as Scientist on the Chair of Number Theory people page (postdoc-level)")
        for n in ["Doyon Kim", "Seewoo Lee", "Ilaria Viglino"]],
    lab_note="Chair of Number Theory (TN), SB MATH. 3 current PhD students, 3 theses 2022-2024, 3 scientists.",
    notes="people.epfl.ch/maryna.viazovska + TN people page.")

# ------------------------------------------------------------------ Nate Foster (LASER)
AS = PP + "aditya.senthilnathan"
D["Nate Foster"] = dict(
    students=[
        S("Aditya Senthilnathan", "phd", [2026, 2026], AS, "External Student , Networked Systems Abstractions Lab",
          start="Administrative data Aditya Senthilnathan",
          note="EPFL profile: student in the EDIC doctoral program and external student in LASER"),
    ],
    lab_note="LASER (Networked Systems Abstractions Lab), IC; brand new at EPFL: Foster's group moved from Cornell in "
             "January 2026. His EPFL profile has no PhD section yet.",
    notes="natefoster.org/students lists the current group (postdoc Guy Amir; PhD students Aditya Senthilnathan, Mark "
          "Barbone, Mark Moeller; master's student Annabel Baniak; undergraduate Tudor Braicu) but does not say who is at "
          "EPFL; people.epfl.ch has a profile only for Senthilnathan (Moeller, Amir, Baniak, Braicu and Hojjat return 404), "
          "so the others are not added. laser.epfl.ch and its people page refuse connections and Wayback holds only the "
          "home page (2026-05). Cornell-era alumni are out.")

# ------------------------------------------------------------------ Nicolas Boumal (OPTIM)
OP = "https://www.epfl.ch/labs/optim/optim-chair-of-continuous-optimization/members/"
D["Nicolas Boumal"] = dict(
    students=prof("nicolas.boumal") + [
        S("Antoine Gonon", "other", [2026, 2026], OP, "Antoine Gonon Invited guest", start="Members Nicolas Boumal",
          note="invited guest on the OPTIM members page"),
    ],
    lab_note="OPTIM (Chair of Continuous Optimization), SB MATH; lab since 2020 (Boumal came from Princeton). 2 current "
             "PhD students, 2 theses in 2025.",
    notes="people.epfl.ch/nicolas.boumal + OPTIM members page. Past postdocs are not listed on either page.")

# ------------------------------------------------------------------ Nisheeth Vishnoi
D["Nisheeth Vishnoi"] = dict(
    students=fsev.infoscience_theses(infosci("Vishnoi"), ["Vishnoi"]),
    lab_note="THL3 (Theory of Computation Lab 3), IC, 2014-2017; Vishnoi left for Yale in 2017. One EPFL thesis "
             "(Damian Straszak, 2018).",
    notes="Infoscience advisor search 'Vishnoi' (1 thesis, already held). people.epfl.ch/243446 is 404; the 2017 Wayback "
          "capture of his profile has no PhD section; theory.epfl.ch/vishnoi now redirects to Yale. Yale students are out.")

# ------------------------------------------------------------------ Philippe Schwaller (LIAC)
LT = "https://schwallergroup.github.io/team.html"
MT = "Master’s Theses Master’s theses listing"
MS = "Master Semester Projects (EPFL)"
sch = prof("philippe.schwaller")
sch += [S(n, "postdoc", [y, 2026], LT, f"Dr. {n} Since {m} {y}", start="Postdoctoral Researchers Dr. Matthew Hart")
        for n, m, y in [("Matthew Hart", "September", 2025), ("Maarten R. Dobbelaere", "August", 2026),
                        ("Tom Frömbgen", "September", 2026), ("Gianin Thomann", "September", 2026), ("Oliver Loveday", "October", 2026)]]
sch += [S("Ka Lok Chan", "postdoc", [2025, 2026], LT, "Dr. Ka Lok (Jacky) Chan Since September 2025",
          start="Postdoctoral Researchers Dr. Matthew Hart", note="based in Singapore (CARES SM3 project)"),
        S("Oriol Villa Lavela", "phd", [2026, 2026], LT, "Oriol Villa Lavela Since October 2026", start="PhD Students Junwu Chen")]
sch += [S(n, "postdoc", list(y), LT, f"Dr. {n} , {span}", start="Alumni Postdoctoral Researchers")
        for n, span, y in [("Stéphane d’Ascoli", "March–October 2023", (2023, 2023)),
                           ("Geemi Wellawatte", "August 2023–August 2024", (2023, 2024)),
                           ("Zlatko Jončev", "September 2023–August 2025", (2023, 2025)),
                           ("Marta Brucka", "April–September 2024", (2024, 2024)),
                           ("Edvin Fako", "February 2025–January 2026", (2025, 2026)),
                           ("Julian Götz", "February 2025–March 2026", (2025, 2026)),
                           ("Sergey Pozdnyakov", "February–December 2025", (2025, 2025)),
                           ("Jan Rittig", "June 2025–May 2026", (2025, 2026))]]
sch += [S(n, "masters", list(y), LT, f"{n} {sep} {inst}", start=MT, after=MT,
          note=f"master's thesis supervised by Schwaller at EPFL ({inst})")
        for n, sep, inst, y in [("Michael Zhang", "-", "EPFL", (2026, 2027)), ("Tim Arni", "—", "Mila", (2025, 2026)),
                                ("Miquel Angel Perez Puigdomenech", "—", "EPFL", (2025, 2026)), ("Luca Rota", "—", "ETH Zurich", (2025, 2026)),
                                ("Milena Charlotte Wiegand", "—", "Technical University of Munich", (2025, 2026)),
                                ("Cesar Antonio Doñez Miranda", "—", "Empa", (2024, 2025)), ("Yunjie Xu", "—", "ETH Zurich", (2024, 2025)),
                                ("Lucien Michel Gérard Brey", "—", "MIT", (2023, 2024)), ("Amin Abdelrafour Debabeche", "—", "MIT", (2023, 2024)),
                                ("Cheng-Hua Huang", "—", "EPFL", (2022, 2023)), ("Artur Andrzej Stefaniuk", "—", "EPFL", (2022, 2023))]]
for yr, names in [((2025, 2026), ["Sathvik Bhagavan", "Malo Gfeller", "Zeineb Mellouli", "Cédric Nathanaël Rossboth", "Octavian Susanu",
                                  "Matéo Tatzber", "Anthony David Verhoeven", "Nicholas Jeffrey Weiss", "Zongmin Zhang"]),
                  ((2024, 2025), ["Arne Beckmann", "Ziad El Malki", "Aleksei Kudrinskii", "Guillaume Romain Galaad Malherbe",
                                  "Marko Simic", "Ines Bouchama"]),
                  ((2023, 2024), ["Jenestin Anton Anthonipillai", "Tugdual Marc-Emmanuel Pierre Marie Kerjan", "Colleen Rachèle Lonfat"]),
                  ((2022, 2023), ["Malte Franke"])]:
    sch += [S(n, "masters", list(yr), LT, n, start=MS, after=MS, note="master semester project (EPFL)") for n in names]
sch += [S(n, "other", [2026, 2026], LT, f"Note {n} Since {m} 2026", start="Interns Note Duc Dat Dang", note="intern")
        for n, m in [("Duc Dat Dang", "February"), ("Artiom Hrynov", "July"), ("Louis Vasseur", "July"),
                     ("Marc Al Hachem", "September"), ("Aurélie Bechinger", "September"), ("Gabrielė Strodomskytė", "September")]]
D["Philippe Schwaller"] = dict(
    students=sch,
    lab_note="LIAC (Laboratory of Artificial Chemical Intelligence), SB ISIC; founded February 2022. Large young lab: ~23 "
             "PhD students (several external/industrial or co-supervised), 4 PhD graduates 2025-2026, 6 current and 8 past "
             "postdocs, ~11 master's theses and ~19 master semester projects, interns.",
    notes="people.epfl.ch/philippe.schwaller PhD sections + schwallergroup.github.io/team.html. Left out: visiting PhD "
          "students/postdocs and 'Visiting Project Students' from other universities, research engineer, admin. "
          "Profile names differ slightly from the team page (e.g. 'Saumya Saumya' = Saumya Thakur, 'Paulo Filipe Valverde "
          "Das Neves' = Paulo Neves); profile forms kept.")

# ------------------------------------------------------------------ Rotem Arnon
D["Rotem Arnon"] = dict(
    students=prof("rotem.arnon"),
    lab_note="SCI-IC-RA, IC; Arnon (Weizmann) has been at EPFL on leave since February 2026; her group is split between "
             "Weizmann and EPFL. One PhD student is on her EPFL profile.",
    notes="people.epfl.ch/rotem.arnon (Itammar Steinberg, already held). Her site (sites.google.com/view/rotem-arnon) lists "
          "group members Thomas Hahn (postdoc), Noam Avidan and Ilya Merkulov (PhD) and Weizmann MSc alumni, but says the "
          "group is 'distributed between the two institutions' without saying who is at EPFL; none of them has a "
          "people.epfl.ch profile (404), so they are not added. Infoscience has no theses with her as advisor.")

# ------------------------------------------------------------------ Samy Bengio
D["Samy Bengio"] = dict(
    students=prof("samy.bengio"),
    lab_note="Adjunct professor in IC (he leads ML research at Apple). One current PhD student; his co-directed EPFL "
             "theses (2006-2008, from his IDIAP years) are outside the window.",
    notes="people.epfl.ch/samy.bengio; Infoscience advisor search 'Bengio' (7 theses, all 2006-2008); his homepage lists "
          "only IDIAP-era students. Nothing more for 2016+.")

# ------------------------------------------------------------------ Thomas Vidick (QCC)
QG = "https://www.epfl.ch/labs/qcc/members/"
QV = "https://www.epfl.ch/labs/qcc/members/visiting-students/"
QH = "Prof. Thomas Vidick Group Thomas Vidick Position Full Professor"
D["Thomas Vidick"] = dict(
    students=prof("thomas.vidick") + [
        S(n, "postdoc", [2026, 2026], QG, f"{n} Position Postdoctoral Researcher", start=QH)
        for n in ["Jonathan Conrad", "Yupan Liu", "Hamoon Mousavi"]] + [
        S("Valentine Chloé Blanpain", "phd", [2025, 2026], QG, "Valentine Chloé Blanpain Position Doctoral Assistant", start=QH,
          note="also a master's project in QCC 3-8.25 (visiting-students page)"),
        S("Mark Nicholas Deaconu", "phd", [2026, 2026], QG, "Mark Nicholas Deaconu Position Doctoral Assistant", start=QH),
        S("Baocheng Sun", "phd", [2026, 2026], QG, "Baocheng Sun Position Doctoral Assistant", start=QH),
        S("Boyang Chen", "other", [2026, 2026], QG, "Boyang Chen Position Doctoral Assistant", start=QH,
          note="visiting PhD student from Tsinghua University (10.26-10.27) listed as Doctoral Assistant"),
        S("Mehdi Jelassi", "masters", [2026, 2026], QV, "Mehdi Jelassi – EPFL (8-12.26)", start="Valorisation Master",
          note="also on the group page as Scientific Assistant (Mehdi Aziz Jelassi)"),
        S("Tal Barak", "masters", [2025, 2025], QV, "Tal Barak – The Hebrew University of Jerusalem (3-8.25)", start="Valorisation Master"),
        S("Tú Dúc Pham", "masters", [2026, 2026], QV, "Tú Dúc Pham – Ecole Normale Supérieure (5-8.26)", start="Master projects"),
        S("Qingxin Yang", "masters", [2025, 2025], QV, "Qingxin Yang – Aalto University (3-8.25)", start="Master projects"),
        S("Rehan Ahmed", "other", [2026, 2026], QV, "Rehan Ahmed – EPFL (7-8.26)", start="Summer@EPFL/SIL", note="summer intern"),
        S("Ghazal Hosseini", "other", [2025, 2025], QV, "Ghazal Hosseini – Sharif University of Technology (7-9.25)",
          start="Summer@EPFL/SIL", note="summer intern"),
    ],
    lab_note="QCC (Quantum Complexity and Cryptography Laboratory), IC; new lab: Vidick moved from Caltech/Weizmann in "
             "2024. 6 doctoral assistants, 3 postdocs, master's projects and interns; no theses yet.",
    notes="people.epfl.ch/thomas.vidick + www.epfl.ch/labs/qcc/members/ (+ visiting-students; former-members page is "
          "empty). qcc.epfl.ch refuses connections. Left out: visiting PhD students from other universities (Vollrath, "
          "Silberstein, Xu, Li, Yanguez). Surprise: Aviv Taller, already held as his EPFL PhD student, is listed on the "
          "visiting page as a visiting PhD student from the Weizmann Institute (2.25 / 7.25).")

# ------------------------------------------------------------------ Yihui Quek
D["Yihui Quek"] = dict(
    students=prof("yihui.quek"),
    lab_note="Prof. Quek Group 1/2 (UPQUEK1 in IC, UPQUEK2 in SB physics); brand-new tenure-track lab (2025). One PhD "
             "student on the profile.",
    notes="people.epfl.ch/yihui.quek (Helen Olivia Propson, already held). No lab page is linked from the profile; "
          "www.yihuiquek.com does not resolve; Infoscience has no theses with her as advisor. Nothing more found: new lab.")
