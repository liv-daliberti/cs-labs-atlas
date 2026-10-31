"""Per-PI decisions for the CMU gap investigation (33 PIs, 2026-10-21/22).

Each evidence spec names the stored capture by URL (live URL or Wayback id_ URL) and either an exact
quote (q=) or start/end markers (s=, e=); build.py extracts/validates the quote, fills sha256 and
capture_url, and re-verifies every quote against the stored bytes.
"""

D = {}
WB = "https://web.archive.org/web/"


def Q(url, q, **kw):
    d = {"url": url, "q": q}
    d.update(kw)
    return d


def SE(url, s, e, **kw):
    d = {"url": url, "s": s, "e": e}
    d.update(kw)
    return d


def ST(name, role, years, ev, must=None, note=None):
    d = {"name": name, "role": role, "years": years, "ev": ev}
    if must:
        d["must"] = must
    if note:
        d["note"] = note
    return d


def ID(kind, ev, note=""):
    return {"kind": kind, "ev": ev, "note": note}


CSD = "https://csd.cmu.edu/people/faculty/"
CSD16 = WB + "20160512112516id_/http://www.csd.cs.cmu.edu:80/directory/faculty"
CSD17 = WB + "20170502112003id_/http://www.csd.cs.cmu.edu:80/directory/faculty"
CSD19 = WB + "20190724065615id_/https://www.csd.cs.cmu.edu/directory/faculty"
CSD23 = WB + "20230306193914id_/https://csd.cmu.edu/people/faculty"


def csd_advisees(slug, pi, students, **kw):
    """Status evidence from the CSD profile header: '<PI> <title> ... Advisees <names>'."""
    return SE(CSD + slug, pi + " " + pi, students, **kw)


# ============================================================================ outside_appointment PIs
# (papers exist but fall in years without a captured listing; yearly listings are another agent's job)

AV = "https://www.andrew.cmu.edu/user/avigad/"
D["Jeremy Avigad"] = dict(
    status="pi",
    status_ev=[csd_advisees("jeremy-avigad", "Jeremy Avigad", "Advisees Joshua Clune Cayden Codel Chase Norman"),
               SE(AV + "students.html", "Jeremy Avigad's Home Page", "PhD students Xinrui (Henry) Li (Computer Science, current)")],
    students=[
        ST("Xinrui (Henry) Li", "phd", None, Q(AV + "students.html", "PhD students Xinrui (Henry) Li (Computer Science, current)"), must=["Xinrui (Henry) Li"]),
        ST("Sidharth Hariharan", "phd", None, Q(AV + "students.html", "Sidharth Hariharan (Mathematical Sciences, current)")),
        ST("Chase Norman", "phd", None, Q(AV + "students.html", "Chase Norman (Computer Science, current)")),
        ST("Cayden Codel", "phd", None, Q(AV + "students.html", "Cayden Codel (Computer Science, co-advised with Marijn Heule, current)")),
        ST("Hannah Fechtner", "phd", None, Q(AV + "students.html", "Hannah Fechtner (Logic, Computation, and Methodology, current)")),
        ST("Joshua Clune", "phd", None, Q(AV + "students.html", "Joshua Clune (Computer Science, current)")),
        ST("Wojciech Nawrocki", "phd", [None, 2026], Q(AV + "students.html", "Wojciech Nawrocki (PhD Logic, Computation, and Methodology, May 2026)")),
        ST("Mario Carneiro", "phd", [None, 2022], Q(AV + "students.html", "Mario Carneiro (PhD Pure and Applied Logic, August 2022)")),
        ST("Floris van Doorn", "phd", [None, 2018], Q(AV + "students.html", "Floris van Doorn (PhD Pure and Applied Logic, May 2018)")),
        ST("Robert Lewis", "phd", [None, 2018], Q(AV + "students.html", "Robert Lewis (PhD Pure and Applied Logic, May 2018)")),
    ],
    appt=[SE(AV, "Jeremy Avigad Welcome to my home page.", "at Carnegie Mellon University"),
          SE(AV + "students.html", "Jeremy Avigad's Home Page", "and again from 2011 to 2012.")],
    notes=("Home department is Philosophy (with Mathematical Sciences); the CSD profile lists him with department "
           "'Philosophy Mathematical Sciences', i.e. a courtesy CSD listing, which is why no CSD yearly listing was captured. "
           "At CMU throughout 2016-2026 (Director of Graduate Studies in Philosophy 2005-2009 and 2011-2012; current Dean's Chair). "
           "His CV (andrew.cmu.edu/user/avigad/CV.pdf, stored) puts the dates in a separate column from the titles, so no "
           "single quote carries a year range with his name."),
)

D["Theophilus Benson"] = dict(
    status="pi",
    status_ev=[csd_advisees("theophilus-benson", "Theophilus Benson", "Advisees Isabel Suizo Hamna Shafqat")],
    students=[
        ST("Isabel Suizo", "phd", None, csd_advisees("theophilus-benson", "Theophilus Benson", "Advisees Isabel Suizo")),
        ST("Hamna Shafqat", "phd", None, SE("https://csd.cmu.edu/people/doctoral-student/hamna-shafqat", "Hamna Shafqat Doctoral", "Thesis Advisor Theophilus Benson")),
    ],
    appt=[],
    notes=("CSD profile lists his department as Electrical and Computer Engineering (CSD courtesy listing), so CSD yearly "
           "listings do not carry him. No dated arrival statement captured (the guessed ECE bio URL 404'd). Not in the "
           "collection (no collection person id in the input)."),
)

D["Tim Dettmers"] = dict(
    status="pi",
    status_ev=[csd_advisees("tim-dettmers", "Tim Dettmers", "Advisees Eulrang Cho Trang Nguyen")],
    students=[
        ST("Eulrang Cho", "phd", None, csd_advisees("tim-dettmers", "Tim Dettmers", "Advisees Eulrang Cho")),
        ST("Trang Nguyen", "phd", None, csd_advisees("tim-dettmers", "Tim Dettmers", "Advisees Eulrang Cho Trang Nguyen")),
        ST("Vladimir Malinovskii", "member", None, Q("https://timdettmers.com/about/", "Group Eulrang Cho Trang Nguyen Vladimir Malinovskii Christine Park")),
        ST("Christine Park", "member", None, Q("https://timdettmers.com/about/", "Group Eulrang Cho Trang Nguyen Vladimir Malinovskii Christine Park")),
    ],
    appt=[SE("https://timdettmers.com/about/", "Tim Dettmers Making deep learning accessible.", "Research Scientist at the Allen Institute for Artificial Intelligence (Ai2).")],
    pi_must=["Dettmers"],
    notes=("Current CMU Assistant Professor (MLD + CSD) and Ai2 research scientist; first captured listing 2025. The "
           "about page gives no start year. 'Group' heading on his own page lists the four members."),
)

D["William Kuszmaul"] = dict(
    status="pi",
    status_ev=[csd_advisees("william-kuszmaul", "William Kuszmaul", "Advisees Jingxun Liang Andrew Krapivin")],
    students=[
        ST("Jingxun Liang", "phd", None, csd_advisees("william-kuszmaul", "William Kuszmaul", "Advisees Jingxun Liang")),
        ST("Andrew Krapivin", "phd", None, csd_advisees("william-kuszmaul", "William Kuszmaul", "Advisees Jingxun Liang Andrew Krapivin")),
    ],
    appt=[SE(CSD + "william-kuszmaul", "William Kuszmaul William Kuszmaul Assistant Professor", "Rabin Postdoc of Theoretical Computer Science at Harvard University.")],
    notes=("CSD profile biography: Rabin Postdoc at Harvard before CMU (prior affiliation, no explicit start year). "
           "PhD-era MIT/Harvard papers are correctly outside the CMU appointment."),
)

D["Jason Li"] = dict(
    status="pi",
    status_ev=[csd_advisees("jason-li", "Jason Li", "Advisees Henry Fleischmann George Li"),
               SE("https://www.cs.cmu.edu/~jmli/", "Jason Li Jason Li Assistant Professor, Carnegie Mellon University", "Current Students Henry Fleischmann George Li")],
    students=[
        ST("Henry Fleischmann", "phd", None, Q("https://www.cs.cmu.edu/~jmli/", "Current Students Henry Fleischmann George Li")),
        ST("George Li", "phd", None, Q("https://www.cs.cmu.edu/~jmli/", "Current Students Henry Fleischmann George Li"), must=["George Li"]),
    ],
    appt=[SE("https://www.cs.cmu.edu/~jmli/", "Jason Li Jason Li Assistant Professor, Carnegie Mellon University Teaching", "Spring 2024: 15-850 Advanced Algorithms")],
    pi_must=["Li"],
    notes=("Teaching list on his homepage starts Spring 2024 (earliest dated CMU faculty activity seen). He was earlier a "
           "CMU PhD student, so 2016-2021 CMU-affiliated papers are student-era and correctly not faculty-period papers."),
)

ML = "https://www.cs.cmu.edu/~minchenl/"
D["Minchen Li"] = dict(
    status="pi",
    status_ev=[csd_advisees("minchen-li", "Minchen Li", "Advisees Guying Lin Juntian Zheng Zhaofeng Luo")],
    students=[
        ST("Guying Lin", "phd", None, csd_advisees("minchen-li", "Minchen Li", "Advisees Guying Lin")),
        ST("Juntian Zheng", "phd", None, csd_advisees("minchen-li", "Minchen Li", "Advisees Guying Lin Juntian Zheng")),
        ST("Zhaofeng Luo", "phd", None, csd_advisees("minchen-li", "Minchen Li", "Advisees Guying Lin Juntian Zheng Zhaofeng Luo")),
    ],
    appt=[Q(ML, "Minchen Li is an Assistant Professor in the Computer Science Department at Carnegie Mellon University since 2023.")],
    notes="Arrival 2023 stated on his homepage; previously Assistant Adjunct Professor at UCLA Mathematics.",
)

D["Jignesh Patel"] = dict(
    status="pi",
    status_ev=[SE(CSD + "jignesh-patel", "Jignesh Patel Jignesh Patel Dean and Vice President CMU Miami; Professor", "Advisees Drew Ripberger Sam Arch")],
    students=[
        ST("Drew Ripberger", "phd", None, SE(CSD + "jignesh-patel", "Jignesh Patel Jignesh Patel", "Advisees Drew Ripberger")),
        ST("Sam Arch", "phd", None, SE(CSD + "jignesh-patel", "Jignesh Patel Jignesh Patel", "Advisees Drew Ripberger Sam Arch")),
    ],
    appt=[Q(CSD + "jignesh-patel", "Jignesh Patel is a professor in the Computer Science Department at Carnegie Mellon University.")],
    notes=("Current title on the CSD profile is 'Dean and Vice President CMU Miami; Professor' (gap input still says "
           "Interim Department Head). No dated arrival statement captured. Not in the collection (no collection person id)."),
)

D["Richard Peng"] = dict(
    status="pi",
    status_ev=[csd_advisees("richard-peng", "Richard Peng", "Advisees Hoai-An Nguyen Alicia Stepin Junzhao Yang")],
    students=[
        ST("Hoai-An Nguyen", "phd", None, csd_advisees("richard-peng", "Richard Peng", "Advisees Hoai-An Nguyen")),
        ST("Alicia Stepin", "phd", None, csd_advisees("richard-peng", "Richard Peng", "Advisees Hoai-An Nguyen Alicia Stepin")),
        ST("Junzhao Yang", "phd", None, csd_advisees("richard-peng", "Richard Peng", "Advisees Hoai-An Nguyen Alicia Stepin Junzhao Yang")),
    ],
    appt=[SE(CSD + "richard-peng", "Richard Peng Richard Peng Associate Professor", "Prior to joining in 2023,")],
    notes=("Arrival 2023 ('Prior to joining in 2023') on the CSD profile. He was a CMU PhD student earlier (advised by "
           "Gary L. Miller), so pre-2023 CMU-affiliated papers are not faculty-period papers."),
)

D["Anthony Rowe"] = dict(
    status="pi",
    status_ev=[csd_advisees("anthony-rowe", "Anthony Rowe", "Advisees Sagar Kalasibail Seetharam")],
    students=[
        ST("Sagar Kalasibail Seetharam", "phd", None, csd_advisees("anthony-rowe", "Anthony Rowe", "Advisees Sagar Kalasibail Seetharam")),
    ],
    appt=[Q("https://www.ece.cmu.edu/directory/bios/rowe-anthony.html", "Bio Anthony Rowe is the Siewiorek and Walker Family Professor in the Electrical and Computer Engineering Department at Carnegie Mellon University.")],
    notes=("Home department is ECE (CSD courtesy listing, department shown as Electrical and Computer Engineering). "
           "ECE bio: CMU ECE PhD 2010, CMU teaching award 2013, CIT Early Career Fellowship 2015, Strecker Early Career chair "
           "2016 - continuously at CMU through the window."),
)

D["Riad Wahby"] = dict(
    status="pi",
    status_ev=[SE(CSD + "riad-wahby", "Riad Wahby Riad Wahby Assistant Professor, Affiliated Faculty", "Advisees Quang Dao Kunming Jiang")],
    students=[
        ST("Quang Dao", "phd", None, SE(CSD + "riad-wahby", "Riad Wahby Riad Wahby", "Advisees Quang Dao")),
        ST("Kunming Jiang", "phd", None, SE(CSD + "riad-wahby", "Riad Wahby Riad Wahby", "Advisees Quang Dao Kunming Jiang")),
    ],
    appt=[Q("https://www.ece.cmu.edu/directory/bios/wahby-riad.html", "Riad Wahby is an Assistant Professor in the Department of Electrical and Computer Engineering at Carnegie Mellon University.")],
    notes=("Home department ECE; CSD lists him as 'Affiliated Faculty', so CSD yearly listings miss him. No dated "
           "arrival statement captured."),
)

D["Dana Scott"] = dict(
    status="not_pi_in_window",
    status_ev=[Q(CSD + "dana-scott", "Dana Scott Dana Scott University Professor Emeritus"),
               Q(CSD16, "Scott Dana Professor Emeritus Traffic 21 Classroom 6501 Wean Hall"),
               SE("http://www.cs.cmu.edu/~scott/students.html", "Dana Scott's Ph.D. Students PhD. Students of Dana S. Scott:", "[01] E.G.K. Lopez-Escobar"),
               SE("http://www.cs.cmu.edu/~scott/students.html", "[41] Jesse Hughes, Carnegie Mellon, 2001 [Phil]", "Last revised: 2 December 2003", must=["dana.scott"])],
    students=[],
    appt=[Q(CSD16, "Scott Dana Professor Emeritus Traffic 21 Classroom 6501 Wean Hall")],
    notes=("Emeritus before the window (listed 'Professor Emeritus' in the May-2016 CSD directory; 'University Professor "
           "Emeritus' today). His own Ph.D.-students page ends with #41 Jesse Hughes (2001) and was last revised 2003; no "
           "advisee after 2001 found. The pipeline's 'own_group' basis was his 2005 homepage's 'Ph.D. Students' link, which "
           "is that historical list."),
)

AS = "https://users.ece.cmu.edu/~asrirama/"
D["Akshitha Sriraman"] = dict(
    status="pi",
    status_ev=[SE(AS, "Meet the Team Principal Investigator Akshitha Sriraman Assistant Professor", "Jaylen Wang PhD Candidate")],
    students=[
        ST("Jaylen Wang", "phd", None, SE(AS, "Meet the Team Principal Investigator Akshitha Sriraman", "Jaylen Wang PhD Candidate")),
        ST("Sara Mahdizadeh Shahri", "phd", None, Q(AS, "Sara Mahdizadeh Shahri PhD Candidate Dissertation Title: Introducing Equitable Web Systems")),
        ST("Veronica Muriga", "phd", None, Q(AS, "Veronica Muriga PhD Candidate Dissertation Title: Communication and Compute for All")),
        ST("Deepanjali Mishra", "phd", [2024, None], Q(AS, "Deepanjali Mishra PhD Candidate Dissertation Title: Salvaging Data Center Processors")),
        ST("Abnash Bassi", "phd", None, Q(AS, "Abnash Bassi PhD Student Dissertation Title: Enabling Efficient and Sustainable Data Centers")),
        ST("Mihailo Rancic", "phd", [2021, 2026], Q(AS, "Alumni Mihailo Rancic Dissertation Title: Enabling Hardware and Software Acceleration at Hyperscale")),
        ST("Melissa Pan", "masters", [None, 2024], Q(AS, "Apr 2024 My Master's student, Melissa Pan, has accepted a PhD offer from UC Berkeley!")),
        ST("Zibo Gong", "masters", [None, 2023], Q(AS, "Apr 2023 My Master's student, Zibo Gong, has accepted a PhD offer from UIUC!")),
        ST("Swamynathan Siva", "masters", [None, 2024], Q(AS, "Dec 2024 My Master's advisee, Swamynathan Siva, graduated and is now at NVIDIA.")),
    ],
    appt=[SE(AS, "Akshitha Sriraman Assistant Professor Carnegie Mellon University About Me", "at Carnegie Mellon University .")],
    notes=("Home department ECE (CSD affiliated). Lab page 'Meet the Team' lists the PhD students; news items name "
           "Master's advisees. Group started Sep 2021 (first PhD student); her ORCID record lists CMU ECE Assistant "
           "Professor from 2022. Not in the collection (no collection person id). Undergraduate 'interns' in her news "
           "(e.g. Shixin Song, Hilbert Chen) are not recorded because the page does not tie them to CMU."),
)

# Natasa Miskov-Zivanov: see below (decided after reading her CMU/Pitt pages)

# ============================================================================ identity-gap PIs

BL = "https://borderlab.org/people"
D["Richard Schuster Border"] = dict(
    status="pi",
    status_ev=[Q(BL, "People border.lab @ CMU news / publications / people / join Richard Border Principal Investigator")],
    students=[
        ST("Alireza Rasoulzadeh", "phd", None, Q(BL, "Alireza Rasoulzadeh PhD Student")),
        ST("McKenzie van der Hagen", "phd", None, Q(BL, "McKenzie van der Hagen PhD Student")),
        ST("Ajay Prabhakar", "masters", None, Q(BL, "Ajay Prabhakar MS Student")),
        ST("Ziyan Zhang", "masters", None, Q(BL, "Ziyan Zhang MS Student")),
        ST("Siyona Dhingra", "undergraduate", None, Q(BL, "Siyona Dhingra Undergraduate Researcher")),
    ],
    identity=dict(
        dblp=[], orcid=["0000-0002-6293-2968"], openalex=["A5069656894", "A5134514127"],
        evidence=[
            ID("orcid_record", Q("https://orcid.org/0000-0002-6293-2968/person.json",
                                 '"displayName":"Richard Border","biography":{"lastModifiedDate":{"value":1741277843187},"createdDate":{"value":1647965068516},"content":"Assistant Professor of Computational Biology at the Carnegie Mellon University School of Computer Science"'),
               "ORCID record names Richard Border with CMU (biography)."),
            ID("openalex_verified", Q("https://borderlab.org/publications", "Phenotype integration improves power and preserves specificity in biobank-based genetic studies of major depressive disorder. Nature Genetics. 10.1038/s41588-023-01559-9 Border"), "A5069656894 work W4388824145 on the lab publications page; 30 title matches in total."),
            ID("openalex_verified", Q("https://borderlab.org/publications", "Assortative mating biases marker-based heritability estimators. Nature Communications. 10.1038/s41467-022-28294-9 Ip, HF, Van Der Laan, CM, Krapohl, EML, …, Border"), "W4226091797."),
            ID("openalex_verified", Q("https://borderlab.org/publications", "No evidence that schizophrenia candidate genes are more associated with schizophrenia than noncandidate genes. Biological Psychiatry. 10.1016/j.biopsych.2017.06.033 Border"), "W2735838525."),
            ID("openalex_verified", Q("https://borderlab.org/publications", "Border, R , …, Schork, AJ, Kendler, K, Flint, J (2026). The predicament of heritable confounders"), "A5134514127 (3-work split, same ORCID) work W7123352947 on the lab page; its 2026 'The geometry of G × E' also matches."),
        ]),
    pi_must=["Border"],
    notes=("No DBLP person page found (dblp.org API is bot-walled from here). OpenAlex A5069656894 (54 works, ORCID "
           "0000-0002-6293-2968, last institution CMU) and the 3-work split A5134514127 carry the same ORCID; works "
           "verified against the lab publications page (see identity evidence)."),
)

ORC = "https://orcid.org/"


def orcid_cmu_affil(oid, name, **kw):
    """ORCID affiliations JSON: from the first CMU affiliation to the self-asserted sourceName (the holder's name)."""
    return SE(ORC + oid + "/affiliationGroups.json", '"value":"Carnegie Mellon University"', '"sourceName":"' + name + '"', raw=True, **kw)


# ---------------------------------------------------------------------------- Maggie Henderson
HL = "https://hendersonneurolab.github.io/people/"
HCV = "https://www.cmu.edu/dietrich/psychology/pdf/cv-maggie-henderson-2024.pdf"
D["Maggie Henderson"] = dict(
    status="pi",
    status_ev=[SE(HL, "People Principal Investigator Maggie Henderson I am an Assistant Professor", "Ph.D Students Tamar Japaridze")],
    students=[
        ST("Tamar Japaridze", "phd", None, Q(HL, "Ph.D Students Tamar Japaridze Ph.D program in Cognitive Neuroscience")),
        ST("Yuhan Shi", "phd", None, Q(HL, "Yuhan Shi Ph.D program in Cognitive Neuroscience (co-supervised with Susanne Ferber )")),
        ST("Junru Zhao", "phd", None, Q(HL, "Junru Zhao Ph.D program in Cognitive Neuroscience")),
        ST("Achin Parashar", "masters", None, Q(HL, "M.S. Students Achin Parashar M.S. in Neural Technologies (MiNT)")),
        ST("Stephanie Lu", "undergraduate", None, Q(HL, "Undergraduate Students Stephanie Lu Cognitive Science (concentration in AI) and Human-Computer Interaction")),
        ST("Ahana Dey", "undergraduate", None, Q(HL, "Ahana Dey Computational Neuroscience, minor in Artificial Intelligence")),
        ST("Iishaan Inabathini", "undergraduate", None, Q(HL, "Iishaan Inabathini Cognitive Science (concentration in NeuroAI)")),
        ST("Ziyu Li", "masters", [2025, 2026], Q(HL, "Ziyu Li M.S. Student in Computational Biology Program, 2025-2026.")),
        ST("Gaurika Sawhney", "undergraduate", [2022, 2025], Q(HL, "Gaurika Sawhney Undergraduate research 2022-2025")),
        ST("Evren Konuk", "undergraduate", [2024, 2025], Q(HL, "Evren Konuk Undergraduate research 2024-2025")),
        ST("Omisa Jinsi", "undergraduate", [2021, 2022], Q(HL, "Omisa Jinsi Undergraduate research 2021-2022")),
        ST("William Friebel", "other", [2025, 2026], Q(HL, "Ph.D Rotation Students William Friebel Ph.D Program in Neural Computation"),
           note="Ph.D. rotation student (2026); earlier a 2025 uPNC summer undergraduate in the lab."),
    ],
    identity=dict(dblp=["https://dblp.org/pid/348/9728"], orcid=[], openalex=["A5070257872"], evidence=[
        ID("openalex_verified", Q(HCV, "Henderson, M.M., Lin, R., Prince, J.S., Tarr, M.J., & Wehbe, L. (2023). Selectivity for food in human ventral visual cortex"), "W4321003712 on her CV; 21 title matches in total."),
        ID("openalex_verified", Q(HCV, "Henderson, M.M.*, & Tarr, M.J. (2023). Early experience with low-pass filtered images facilitates visual category learning in a neural network model"), "W4313639619."),
        ID("openalex_verified", Q(HCV, "Henderson, M.M., Serences, J.T., & Rungratsameetaweemana, N. (2023). Dynamic categorization rules alter representations in human visual cortex"), "W4409358137."),
    ]),
    appt=[SE(HCV, "Maggie Henderson, Ph.D mmhender@cmu.edu EMPLOYMENT 2024 – present 2021 – 2024 Assistant Professor", "Carnegie Mellon University, Pittsburgh, PA Postdoctoral Research Associate")],
    notes=("Assistant Professor (Psychology + Neuroscience Institute, MLD affiliated) since 2024; CMU NI postdoc 2021-2024 "
           "(CV). Her lab site lists 3 PhD students, an MS student, undergraduates and alumni since 2021. Papers before 2024 "
           "are postdoc-era CMU papers. OpenAlex id A5070257872 was already in the pipeline (not re-verified here)."),
)

# ---------------------------------------------------------------------------- Natasa Miskov-Zivanov
NMZ15 = WB + "20150930044621id_/https://www.csd.cs.cmu.edu/people/adjunct-faculty/natasa-miskov-zivanov"
D["Natasa Miskov-Zivanov"] = dict(
    status="not_pi_in_window",
    status_ev=[Q("https://nmzlab.pitt.edu/people", "Faculty Natasa Miskov Zivanov PhD Associate Professor nmzivanov@pitt.edu", must=["Miskov Zivanov"]),
               Q(WB + "20220816063317id_/https://2013.igem.org/Team:Carnegie_Mellon/Advisors", "Natasa Miskov-Zivanov Adjunct Faculty Electrical and Computer Engineering Research Associate School of Medicine, University of Pittsburgh"),
               Q(NMZ15, "Department(s): Computer Science Department Natasa Miskov-Zivanov Senior Researcher")],
    students=[],
    appt=[Q(NMZ15, "Department(s): Computer Science Department Natasa Miskov-Zivanov Senior Researcher")],
    notes=("Not a CMU faculty PI in 2016-2026: her lab (Miskov-Zivanov Lab, nmzlab.pitt.edu) is at the University of "
           "Pittsburgh, where she is Associate Professor; her ORCID lists only University of Pittsburgh employment. At CMU she "
           "was ECE adjunct faculty (2013) and a CSD 'Senior Researcher' under the adjunct-faculty path (2015 capture). The two "
           "pipeline students (Stefan Andjelkovic, Emilee Holtzapple) are joint CMU-Pitt CPCB PhD students whose CPCB listing "
           "names her as advisor (e.g. 2022 capture: 'Stefan Andjelkovic 5th year Advisor: Natasa Miskov-Zivanov'); they belong "
           "to her Pitt lab, not a CMU lab. Owner may prefer to keep CPCB co-advising as a CMU relation; if so flip to 'pi'."),
)

# ---------------------------------------------------------------------------- Farzaneh Derakhshan
DOT = "http://reports-archive.adm.cs.cmu.edu/anon/2026/abstracts/26-130.html"
D["Farzaneh Derakhshan"] = dict(
    status="pi",
    status_ev=[Q(DOT, "Thesis Committee: Limin Jia (Co-chair) Farzaneh Derakhshan (Co-chair) Jan Hoffmann Frank Pfenning Brigitte Pientka (McGill University)"),
               Q(CSD + "farzaneh-derakhshan-IIT", "Farzaneh Derakhshan Farzaneh Derakhshan Assistant Professor Website Department Illinois Institute of Technology")],
    students=[ST("Myra Dotzel", "phd", [None, 2026], Q(DOT, "Myra Dotzel Ph.D. Thesis August 2026 CMU-CS-26-130.pdf"),
                 note="CMU-CS PhD thesis 2026; co-chaired by Limin Jia and Farzaneh Derakhshan.")],
    appt=[SE("https://www.iit.edu/directory/people/farzaneh-derakhshan", "Farzaneh Derakhshan Assistant Professor of Computer Science", "Ph.D. Pure and Applied Logic, Carnegie Mellon University")],
    notes=("Her faculty post is at Illinois Institute of Technology (IIT directory: 'Assistant Professor of Computer Science'; "
           "CMU PhD in Pure and Applied Logic). CSD lists her as faculty with department 'Illinois Institute of Technology', "
           "and she co-chairs a CMU PhD thesis without the external-institution tag CMU gives outside members - i.e. a CMU "
           "courtesy/adjunct advising role. Her only CMU group member is Myra Dotzel (co-advised with Limin Jia). 2016-2021 "
           "CMU-affiliated papers are from her own CMU PhD, not a faculty period. Marked 'pi' because a stated CMU advisee "
           "exists; the owner may prefer 'not_pi_in_window' (courtesy, primary lab elsewhere)."),
)

# ============================================================================ identity-gap PIs (continued)

D["Luis von Ahn"] = dict(
    status="not_pi_in_window",
    status_ev=[Q(CSD17, "Von Ahn Luis Consulting Professor (412) 268-2813 biglou@cs.cmu.edu"),
               Q(CSD19, "Von Ahn, Luis Consulting Professor (412) 567-6602 biglou@cs.cmu.edu"),
               SE("http://reports-archive.adm.cs.cmu.edu/anon/2015/abstracts/15-106.html", "Thesis Committee: Luis von Ahn (Co-Chair)", "Manuel Blum (Co-Chair)"),
               SE("http://www.cs.cmu.edu/~biglou/", "Luis von Ahn Luis von Ahn I build systems", "I'm currently working on Duolingo")],
    students=[],
    identity=dict(dblp=["https://dblp.org/pid/78/391"], orcid=[], openalex=["A5104092531"], evidence=[
        ID("openalex_author", Q("https://api.openalex.org/authors?per-page=25&search=Luis+von+Ahn", '"display_name": "Luis von Ahn"', raw=True, must=["von Ahn"]),
           "Only OpenAlex author for the name (73 works); it has 0 works dated 2016 or later (works filter from_publication_date:2016-01-01 returned count 0), so no 2016+ work can be checked or attributed."),
    ]),
    appt=[Q(CSD16, "Von Ahn Luis Associate Professor 7113 Gates & Hillman Centers (412) 268-2813 biglou@cs.cmu.edu"),
          Q(CSD17, "Von Ahn Luis Consulting Professor (412) 268-2813 biglou@cs.cmu.edu")],
    pi_must=["Ahn"],
    notes=("Associate Professor in the May-2016 CSD directory, 'Consulting Professor' from 2017 on (Duolingo CEO). The last "
           "thesis he (co-)chaired is Brendan Meeder's CMU-CS-15-106 (2015, outside the window); no advisee found 2016-2026. "
           "OpenAlex lists no works by him after 2015, so the paper gap is genuine (there are no in-window CMU papers). "
           "DBLP pid 78/391 is from the input; dblp.org is bot-walled here so it was not re-read."),
)

D["Angel Jordan"] = dict(
    status="not_pi_in_window",
    status_ev=[Q(WB + "20160410101111id_/http://ri.cmu.edu/ri_people.html?fcode=1&menu_id=251&distype=detail&dis_type=detail&list_type=current&selected_letter=AZ", "Angel Jordan University Professor Emeritus, RI/ECE/ISR"),
               Q(WB + "20170701214954id_/http://ri.cmu.edu/ri-faculty/angel-jordan/", "Angel Jordan Angel Jordan University Professor Emeritus, RI/ECE/ISR"),
               Q(CSD19, "Sandholm, Tuomas Angel Jordan Professor of Computer Science 9205 Gates & Hillman Centers"),
               Q(CSD23, "Sandholm, Tuomas Angel Jordan University Professor of Computer Science 9205 Gates and Hillman Centers"),
               SE("http://www.cs.cmu.edu/~amem/", "Tuomas Sandholm - Angel Jordan University Professor of Computer Science", "Founder and Director")],
    students=[],
    identity=dict(dblp=["https://dblp.org/pid/11/4304"], orcid=[], openalex=["A5074235644"], evidence=[
        ID("openalex_author", Q("https://api.openalex.org/authors?per-page=25&search=Angel+Jordan", '"display_name": "Angel G. Jordan"', raw=True),
           "OpenAlex author 'Angel G. Jordan' (90 works) has 0 works dated 2016 or later."),
    ]),
    appt=[],
    notes=("PIPELINE ERROR: Angel Jordan (b. 1930, former provost) was University Professor Emeritus before the window "
           "(RI 2016 listing). His 2019 and 2023 'listings' and the 'Electronic Marketplaces Lab' lab basis are Tuomas "
           "Sandholm's endowed chair title ('Angel Jordan (University) Professor of Computer Science', GHC 9205) parsed as a "
           "person. No students, no 2016+ works. This row should be removed (or reassigned: the evidence belongs to Sandholm)."),
)

D["Steven Xia"] = dict(
    status="not_pi_in_window",
    status_ev=[SE("https://steven.cs.illinois.edu/", "Chunqiu Steven Xia PhD Student University of Illinois Urbana-Champaign", "I am a final year Computer Science PhD student at UIUC advised by Lingming Zhang ."),
               SE("https://conf.researchr.org/profile/ase-2026/chunqiuxia", "Name: Chunqiu Steven Xia", "Affiliation: University of Illinois at Urbana-Champaign")],
    students=[ST("André Catarino", "phd", None, SE("https://se-phd.s3d.cmu.edu/People/students/student-bios/andre-catarino.html", "André Catarino André Catarino Software Engineering PhD Student", "Advisor(s): Claire Le Goues and Steven Xia and Rui Maranhao"),
                 note="Listed as a co-advisor (with Claire Le Goues and Rui Maranhao) of an S3D Software Engineering PhD student; Xia has not started at CMU.")],
    identity=dict(dblp=[], orcid=[], openalex=["A5075857263"], evidence=[
        ID("openalex_verified", Q("https://steven.cs.illinois.edu/", "Xia and Lingming Zhang | Sep, 2024. [ preprint ] Fuzz4All: Universal Fuzzing with Large Language Models"), "W4394769544 on his homepage publication list; 14 title matches in total."),
        ID("openalex_verified", Q("https://steven.cs.illinois.edu/", "Xia , Haoran Peng , Chenyuan Yang , Lingming Zhang | July, 2023. [ preprint ] Automated Program Repair in the Era of Large Pre-trained Language Models"), "W4384345708."),
        ID("openalex_verified", Q("https://steven.cs.illinois.edu/", "Xia , Yuxiang Wei , Lingming Zhang | May, 2023. [ preprint ] Less Training, More Repairing Please: Revisiting Automated Program Repair via Zero-shot Learning"), "W4308643319."),
    ]),
    appt=[],
    notes=("Incoming hire who has not started: his own homepage (fetched 2026-10-21) still reads 'final year Computer Science "
           "PhD student at UIUC advised by Lingming Zhang', his ASE 2026 profile gives UIUC, and the S3D faculty index does not "
           "list him. The only CMU trace is the co-advisor line on Andre Catarino's SE-PhD bio. Byline name is 'Chunqiu Steven "
           "Xia' (the input name 'Steven Xia' misses OpenAlex/DBLP). OpenAlex A5075857263 verified against his homepage "
           "publication list (14 title matches, e.g. Agentless FSE 2025, Fuzz4All ICSE 2024); all its works are UIUC. ORCID "
           "0000-0001-8660-9324 is on that OpenAlex record and the ORCID record names him, but neither his page nor the ORCID "
           "record ties it to CMU, so it is not listed as verified."),
)

SS = "https://www.sh-reya.com/"
D["Shreya Shankar"] = dict(
    status="not_pi_in_window",
    status_ev=[SE("https://www.sh-reya.com/SS_CV.pdf", "Shreya Shankar shreyashankar@berkeley.edu", "Visiting Assistant Professor, Carnegie Mellon University")],
    students=[],
    identity=dict(dblp=["https://dblp.org/pid/215/5341"], orcid=["0000-0002-0919-9672"], openalex=["A5023956968"], evidence=[
        ID("orcid_on_cmu_profile", Q(CSD + "shreya-shankar", "Shreya Shankar Shreya Shankar Assistant Professor Website ORCID 0000-0002-0919-9672"),
           "CMU CSD profile names her ORCID."),
        ID("openalex_verified", Q("https://www.sh-reya.com/SS_CV.pdf", "Shankar, Shreya, Chambers, T., Shah, T., Parameswaran, A. G. & Wu, E. DocETL: Agentic Query Rewriting and Evaluation for Complex Document Processing"), "W4413948895 on her CV; 25 title matches in total."),
        ID("openalex_verified", Q("https://www.sh-reya.com/SS_CV.pdf", "Shankar, Shreya, Zamfirescu-Pereira, J., Hartmann, B., Parameswaran, A. & Arawjo, I. Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences"), "W4403334020."),
        ID("openalex_verified", Q("https://www.sh-reya.com/SS_CV.pdf", "Shankar, Shreya & Parameswaran, A. Towards Observability for Production Machine Learning Pipelines"), "W4317641499."),
    ]),
    appt=[SE("https://www.sh-reya.com/SS_CV.pdf", "Shreya Shankar shreyashankar@berkeley.edu", "Visiting Assistant Professor, Carnegie Mellon University")],
    notes=("Incoming hire: her homepage says 'In 2027, I will join Carnegie Mellon University as an Assistant Professor'; "
           "her CV dates column gives 'Jul. 2027–' (tenure-track) and 'Jul. 2026–27' (Visiting Assistant Professor, CMU CSD). "
           "All her mentees are UC Berkeley/high-school students; no CMU advisee found. OpenAlex A5023956968 (ORCID "
           "0000-0002-0919-9672) holds her Berkeley-era works, none affiliated with CMU, hence no_openalex_name_hits under CMU. "
           "DBLP pid 215/5341 is from the input."),
)

TC = "https://www.thcostello.com/"
TCV = "https://thcostello.com/assets/docs/thomas-costello-cv.pdf"
D["Tom Costello"] = dict(
    status="pi",
    status_ev=[Q(TC, "The lab is Thomas Costello (director) and Ph.D. students Kenneth Diao, Duncan Wood, and Ali Levontin, all in Social and Decision Sciences.")],
    students=[ST(n, "phd", None, Q(TC, "The lab is Thomas Costello (director) and Ph.D. students Kenneth Diao, Duncan Wood, and Ali Levontin, all in Social and Decision Sciences."))
              for n in ("Kenneth Diao", "Duncan Wood", "Ali Levontin")],
    identity=dict(dblp=[], orcid=["0000-0002-5188-3881"], openalex=["A5055631608"], evidence=[
        ID("orcid_on_own_page", SE(TC, 'alt="Thomas Costello as a child, playing baseball"', 'href="https://orcid.org/0000-0002-5188-3881"', raw=True),
           "His homepage links ORCID 0000-0002-5188-3881."),
        ID("openalex_verified", Q(TCV, "Costello, T.H., Pennycook, G., Rand, D. (2024). Durably reducing conspiracy beliefs through dialogues with AI"),
           "OpenAlex A5055631608 work W4402474910 is on his CV; 43 of its 2016+ titles match the CV."),
        ID("openalex_verified", Q(TCV, "Costello, T.H., Tasimi, A (2023). The conspiratorial mind: A meta-analytic review of motivational and personological correlates"),
           "W4382011162 on his CV."),
        ID("openalex_verified", Q(TCV, "Costello, T.H., Bowes, S.M., Stevens, S.T., Waldman, I.W., Tasimi, A., & Lilienfeld, S.O. (2022). Clarifying the structure and nature of left-wing authoritarianism"),
           "W3165171550 on his CV."),
    ]),
    appt=[SE(TCV, "THOMAS H. COSTELLO Curriculum Vitae", "2025 – Present Carnegie Mellon University Assistant Professor, Department of Social and Decision Sciences", must=["COSTELLO"])],
    pi_must=["Costello"],
    notes=("Assistant Professor in Social and Decision Sciences (Dietrich) since 2025, HCII affiliated. Byline 'Thomas H. "
           "Costello' / 'Costello, T.H.' (input name 'Tom Costello' misses OpenAlex). Most of his 119 works since 2016 are "
           "Emory/MIT/American-University era; CMU-affiliated works start 2025-2026."),
)

# ---------------------------------------------------------------------------- Marcel Bruchez
BP = "https://labs.bio.cmu.edu/bruchez-lab/people/"
BPUB = "https://labs.bio.cmu.edu/bruchez-lab/publications/"
FS = "https://api.figshare.com/v2/articles/"
D["Marcel Bruchez"] = dict(
    status="pi",
    status_ev=[Q(BP, "People Marcel Bruchez Director, Professor of Chemistry and Biological Sciences"),
               Q(FS + "6715046", '"name": "Advisor(s)", "value": "Marcel Bruchez"', raw=True)],
    students=[
        ST("Lydia Perkins", "phd", [None, 2018], Q(BP, "Graduate Students Biologists Lydia Perkins Ph.D. Student, Biological Sciences"),
           note="KiltHub thesis 2018 (figshare 6715046), Advisor(s): Marcel Bruchez."),
        ST("Daniel Ackerman", "phd", None, Q(BP, "Daniel Ackerman Ph.D. Student, Biological Sciences")),
        ST("Iris Yank", "phd", None, Q(BP, "Iris Yank Ph.D. Student, Biological Sciences")),
        ST("Alex Carpenter", "phd", None, Q(BP, "Chemists Alex Carpenter Ph.D. Student, Chemistry")),
        ST("Dmytro Kolodieznyi", "phd", [None, 2020], Q(BP, "Dmytrio Kolodieznyi Ph.D. Student, Chemistry"), must=["Kolodieznyi"],
           note="Spelled 'Dmytrio' on the lab page; KiltHub thesis 2020 (figshare 13148828) by Dmytro Kolodieznyi, Advisor(s): Bruce Armitage, Marcel Bruchez."),
        ST("Huaxia Shi", "phd", None, Q(BP, "Huaxia Shi Ph.D. Student, Chemistry")),
        ST("Pingping Liang", "phd", None, Q(BP, "Pingping Liang Ph.D. Student, Chemistry")),
        ST("Xiaohong Tan", "postdoc", None, Q(BP, "Xiaohong Tan, Ph.D. Postdoctoral Scholar, Chemistry")),
        ST("Taylor Canady", "phd", [None, 2017], Q(BP, "Alumni Taylor Canady, PhD 2017"),
           note="KiltHub thesis dated 2019 (figshare 10052024), Advisor(s): Bruce Armitage, Marcel Bruchez."),
        ST("Matharishwan Naganbabu", "phd", [None, 2017], Q(BP, "Matharishwan Naganbabu, PhD 2017")),
        ST("Bruce Feldman", "masters", [None, 2017], Q(BP, "Bruce Feldman , MS 2017")),
        ST("Chris Pratt", "phd", [None, 2016], Q(BP, "Chris Pratt, PhD 2016")),
        ST("Jianjun He", "phd", [None, 2016], Q(BP, "Jianjun He , PhD 2016")),
    ],
    identity=dict(dblp=[], orcid=["0000-0002-7370-4848"], openalex=["A5028325980"], evidence=[
        ID("orcid_record", orcid_cmu_affil("0000-0002-7370-4848", "Marcel Bruchez"),
           "ORCID record (self-asserted) employment: Carnegie Mellon University, Chemistry and Biological Sciences, Professor, 2011-. His lab publications page also links this ORCID."),
        ID("openalex_verified", Q(BPUB, "Bruchez, MP . A genetically targetable near-infrared photosensitizer"), "W2263056748 (2016) on the lab publications page."),
        ID("openalex_verified", Q(BPUB, "Bruchez, MP . Affibody-targeted fluorogen activating protein for in vivo tumor imaging"), "W2576331818 (2017)."),
        ID("openalex_verified", Q(BPUB, "Bruchez, MP, McManus, CJ . Structural analyses of NEAT1 lncRNAs suggest long-range RNA interactions that may contribute to paraspeckle architecture"), "W2791055994 (2018); 17 title matches in total."),
    ]),
    appt=[],
    notes=("Joint Biological Sciences/Chemistry professor (CBD affiliated). Byline 'Marcel P. Bruchez' / 'Bruchez, MP'. "
           "OpenAlex A5028325980 (167 works, ORCID 0000-0002-7370-4848) verified against labs.bio.cmu.edu/bruchez-lab/publications. "
           "Students come from the current lab site (labs.bio.cmu.edu/bruchez-lab/people; the old chem.cmu.edu/groups/bruchez "
           "pages list pre-2015 members only) plus KiltHub theses 2018-2020."),
)

# ---------------------------------------------------------------------------- Phillip Compeau
CCV = WB + "20250116030510id_/https://compeau.cbd.cmu.edu:443/wp-content/uploads/2024/05/Compeau_CV.pdf"
CPD = "https://www.cmu.edu/cbd/people/postdoctoral-fellows.html"
D["Phillip Compeau"] = dict(
    status="pi",
    status_ev=[Q(CPD, "Roshni Bhatt Advisor: Phillip Compeau")],
    students=[ST("Roshni Bhatt", "postdoc", None, Q(CPD, "Postdoctoral Fellows Ghada Abdelhady Advisor: Andreas Pfenning Roshni Bhatt Advisor: Phillip Compeau"))],
    identity=dict(dblp=[], orcid=["0000-0002-2772-4119"], openalex=["A5028841180"], evidence=[
        ID("orcid_record", orcid_cmu_affil("0000-0002-2772-4119", "Phillip Compeau"),
           "ORCID record (self-asserted) employment: Carnegie Mellon University, Computational Biology, Assistant Teaching Professor 2015-2020 (then Associate 2020-2025, Teaching Professor 2025-)."),
        ID("openalex_verified", Q(CCV, "Life After MOOCs: Online Science Education Needs a New Revolution.” P. Compeau"), "W2587528537 (2017) on his CV."),
        ID("openalex_verified", Q(CCV, "Establishing a computational biology flipped classroom.” P. Compeau"), "W2944970492 (2019) on his CV."),
    ]),
    appt=[orcid_cmu_affil("0000-0002-2772-4119", "Phillip Compeau")],
    pi_must=["Compeau"],
    notes=("Teaching-track (Teaching Professor; Assistant Dean for Innovation in Computing Education). OpenAlex A5028841180 "
           "('Phillip E. C. Compeau', ORCID 0000-0002-2772-4119) has only 2 works dated 2016+, and both are on his CV - the "
           "'at least 3' check cannot be met because only 2 exist; ORCID ties the id to CMU. His publication record since "
           "2016 is mostly textbooks/education, so very few lab papers are expected. Only research advisee found: postdoc "
           "Roshni Bhatt (CBD postdoctoral-fellows page). His CV 'Student Advising' entries are program/academic advising, "
           "not research supervision, and are not recorded."),
)

# ---------------------------------------------------------------------------- Scott Fahlman
D["Scott Fahlman"] = dict(
    status="pi",
    status_ev=[Q("https://lti.cmu.edu/people/students/na-clara.html", "Clara Na Contact csna(through)andrew.cmu.edu Ph.D. in Language and Information Technology Academic Advisor: Scott Fahlman"),
               SE("https://www.cs.cmu.edu/~sef/", "Scott E. Fahlman's Homepage", "advising, and departmental activities.")],
    students=[
        ST("Clara Na", "phd", None, Q("https://lti.cmu.edu/people/students/na-clara.html", "Clara Na Contact csna(through)andrew.cmu.edu Ph.D. in Language and Information Technology Academic Advisor: Scott Fahlman")),
        ST("Dean Alderucci", "phd", [2019, 2019], Q(WB + "20191114071652id_/https://lti.cs.cmu.edu/directory/students/current/a",
                                                    "Dean Alderucci Program: Ph.D. in Language and Information Technology Email: dalderuc@andrew.cmu.edu Office: Gates & Hillman Centers Academic Advisor: Scott Fahlman")),
        ST("Dheeru Dua", "masters", [2016, 2016], Q(WB + "20160710060228id_/http://www.lti.cs.cmu.edu:80/directory/students/current/d",
                                                   "Dheeru Dua Program: Master of Science in Intelligent Information Systems Email: ddua@andrew.cmu.edu Academic Advisor: Scott Fahlman")),
    ],
    identity=dict(dblp=["https://dblp.org/pid/16/3174"], orcid=[], openalex=[], evidence=[
        ID("openalex_candidate", Q("https://api.openalex.org/authors?per-page=25&search=Scott+E.+Fahlman", '"display_name": "Scott E. Fahlman"', raw=True),
           "Candidate OpenAlex A5113677164 (82 works, last institution CMU) - NOT verified: he has no reachable own publication list (CV link on his homepage returns HTTP 500, no Wayback copy). Its 9 works dated 2016+ are mostly old papers re-dated (e.g. 'The Cascade-Correlation learning architecture' as 2018); genuinely new: 'Score: A Rule Engine for the Scone Knowledge Base System' (2023)."),
    ]),
    appt=[SE("https://www.cs.cmu.edu/~sef/", "Scott E. Fahlman's Homepage Scott E. Fahlman Professor Emeritus", "I am also emeritus faculty in the Computer Science Department (CSD).")],
    pi_must=["Fahlman"],
    notes=("Emeritus (CSD 'Emeritus Faculty' from 2017; LTI 'Research Professor Emeritus') but self-described as 'formally "
           "retired, but still active in research, advising'; LTI lists him as academic advisor of PhD students in 2019 and "
           "today (Clara Na - who is also listed under Emma Strubell). Paper gap: byline 'Scott E. Fahlman'; few genuine "
           "2016+ papers exist, and the OpenAlex candidate cannot be verified against an own list."),
)

# ---------------------------------------------------------------------------- Gabe Gomes
GT = "https://gpggrp.cheme.cmu.edu/team"
GCV = "https://engineering.cmu.edu/_files/documents/directory/gomes-cv.pdf"
CPCB25 = WB + "20250904150741id_/https://www.cmu.edu/compbio/people/cpcb-students.html"
D["Gabe Gomes"] = dict(
    status="pi",
    status_ev=[Q(GT, "Team - The Gomes Group @ CMU | Gomes Group - Carnegie Mellon University Skip to main content team Postdoctoral Researchers Liliana Gallegos"),
               Q(CPCB25, "Laura McDonnell 2nd year Advisor: Gabe Gomes")],
    students=[
        ST("Mitch Baumer", "phd", None, Q(GT, "PhD Students Mitch Baumer Mitch is a PhD candidate in Chemistry, co-advised with Prof. Stefan Bernhard .")),
        ST("Robert MacKnight", "phd", None, Q(GT, "Robert MacKnight Currently on leave at Google X as a PhD Resident")),
        ST("Rushik Radadiya", "phd", None, Q(GT, "Rushik Radadiya Rushik is a PhD student in Chemistry, co-advised with Prof. Krzysztof Matyjaszewski .")),
        ST("Laura McDonnell", "phd", [2025, 2025], Q(CPCB25, "Laura McDonnell 2nd year Advisor: Gabe Gomes")),
        ST("Liliana Gallegos", "postdoc", None, Q(GT, "Postdoctoral Researchers Liliana Gallegos")),
        ST("Ivan Novitskiy", "postdoc", None, Q(GT, "Ivan Novitskiy Ivan specializes in high-throuput experimentation")),
        ST("Yusef Ahmed", "phd", None, Q(GT, "Alumni Yusef Ahmed, PhD Postdoctoral Researcher, UC Davis")),
        ST("Daniil Boiko", "phd", None, Q(GT, "Daniil Boiko, PhD Co-founder & CEO, onepot AI")),
    ],
    identity=dict(dblp=[], orcid=["0000-0002-8235-5969"], openalex=["A5048633127"], evidence=[
        ID("orcid_record", Q(ORC + "0000-0002-8235-5969/person.json", '"displayName":"Gabe Gomes","biography":{"lastModifiedDate":{"value":1647609868223},"createdDate":{"value":1631204089800},"content":"In January 2022, Gabe Gomes joined Carnegie Mellon University in the Departments of Chemistry and Chemical Engineering.', raw=True),
           "ORCID biography names him with CMU (joined January 2022)."),
        ID("openalex_verified", Q(GCV, "Gomes, T. Zepel, M. S. Sigman, A. AspuruGuzik, J. Hein “Data-science driven autonomous process optimization"), "W3098893481 on his CV; 25 title matches in total."),
        ID("openalex_verified", Q(GCV, "Gomes, R. D. Bin, A. Aspuru-Guzik, D. Balcells “Machine Learning Dihydrogen Activation in the Chemical Space Surrounding Vaska’s Complex"), "W3015692433 on his CV."),
        ID("openalex_verified", Q(GCV, "Gomes & I. V. Alabugin “Drawing Catalytic Power from Charge Separation: Stereoelectronic and Zwitterionic Assistance in the Au(I)-Catalyzed Bergman Cyclization"), "W2586949393 on his CV."),
    ]),
    appt=[Q(ORC + "0000-0002-8235-5969/person.json", "In January 2022, Gabe Gomes joined Carnegie Mellon University in the Departments of Chemistry and Chemical Engineering.", raw=True)],
    notes=("Home: Chemistry + Chemical Engineering (MLD affiliated). Byline variants 'Gabe Gomes', 'Gabriel dos Passos Gomes', "
           "'G. P. Gomes'. OpenAlex A5048633127 (ORCID 0000-0002-8235-5969) verified against his CV. A second small OpenAlex "
           "profile A5023957810 ('Gabe Gomes', CMU, 8 works 2022-2026, e.g. 'Iron Mind', 'Provenance grounds trust in "
           "autonomous science') is very likely a split of the same person but none of its titles are on the (older) CV, so it "
           "is not listed as verified."),
)

# ---------------------------------------------------------------------------- Veronica Hinman
H19 = WB + "20191024040413id_/https://labs.bio.cmu.edu/hinman/people/"
HP = "https://labs.bio.cmu.edu/hinman/people/"
HCBD = "https://www.cmu.edu/cbd/people/hinman.html"
D["Veronica Hinman"] = dict(
    status="pi",
    status_ev=[SE(H19, "People Veronica Hinman Professor Department of Biological Sciences Carnegie Mellon University", "Pittsburgh. 15213"),
               Q(FS + "14417294", '"name": "Advisor(s)", "value": "Veronica Hinman"', raw=True)],
    students=[
        ST("Minyan (Mia) Zheng", "phd", [None, 2019], Q(H19, "Minyan (Mia) Zheng Ph.D. candidate GRNs for Regeneration"), must=["Zheng"],
           note="KiltHub thesis 2019 (figshare 9584741), Advisor(s): Veronica Hinman. The current alumni list spells her 'Minyan (Mia) Zhang. 2019.'"),
        ST("Andrew Wolff", "phd", [None, 2021], Q(H19, "Andrew Wolff (and Pumpkin) Ph.D. candidate"),
           note="KiltHub thesis 2021 (figshare 14417294), Advisor(s): Veronica Hinman."),
        ST("Annie Meyer", "phd", [2019, 2019], Q(H19, "Annie Meyer (and Monty) Ph.D. candidate")),
        ST("Gregory Cary", "postdoc", [2019, 2019], Q(H19, "Dr. Gregory Cary Postdoctoral Associate")),
        ST("William Hatleberg", "postdoc", [2019, 2019], Q(H19, "Dr. William Hatleberg Postdoctoral Researcher")),
        ST("Katherine Buckley", "postdoc", [None, 2019], Q(HP, "Lab Alumni Postdocs: Katherine Buckley. 2019. Assistant Professor, Auburn University"),
           note="Listed as 'Senior Research Scientist' on the 2019 people page."),
        ST("Rene Francolini", "masters", [None, 2016], Q(HP, "Rene Francolini. Masters in Computational Biology. 2016.")),
        ST("Siyao Wang", "undergraduate", [None, 2019], Q(HP, "Undergrads: Siyao Wang (2019). Honors Research.")),
        ST("Njairé Mckoy", "undergraduate", [None, 2017], Q(HP, "Njairé Mckoy (2017)")),
        ST("Katherine Huang", "undergraduate", [None, 2017], Q(HP, "Katherine Huang (2017). Honors Research.")),
        ST("Carolyn Ku", "undergraduate", [2019, 2019], Q(H19, "Carolyn Ku Undergraduate Researcher")),
        ST("Grace Wolczanski", "undergraduate", [2019, 2019], Q(H19, "Grace Wolczanski Undergraduate Researcher")),
        ST("Madison Dodds", "undergraduate", [2019, 2019], Q(H19, "Madison Dodds Undergraduate Researcher")),
        ST("Stephanie Blackwood", "undergraduate", [2019, 2019], Q(H19, "Stephanie Blackwood Undergraduate Researcher")),
        ST("Noah Lee", "undergraduate", [2019, 2019], Q(H19, "Noah Lee Undergraduate Researcher")),
    ],
    identity=dict(dblp=[], orcid=["0000-0003-3414-1357"], openalex=["A5049293538"], evidence=[
        ID("orcid_record", orcid_cmu_affil("0000-0003-3414-1357", "Veronica Hinman"),
           "ORCID record (self-asserted) employment: Carnegie Mellon University, Biology, Associate Professor, 2006-2024."),
        ID("openalex_verified", Q(HCBD, "Hinman VF. Echinoderm development and evolution in the post-genomic era"), "W2586555895 (2017) in the CBD profile's highlighted publications."),
        ID("openalex_verified", Q(HCBD, "Hinman VF, Burke RD. Embryonic neurogenesis in echinoderms"), "W2792974449 (2018)."),
        ID("openalex_verified", Q(HCBD, "Hinman VF. Analysis of sea star larval regeneration reveals conserved processes of whole-body regeneration across the metazoa"), "W2938696193 (2019); 13 title matches in total."),
    ]),
    appt=[orcid_cmu_affil("0000-0003-3414-1357", "Veronica Hinman"),
          SE(ORC + "0000-0003-3414-1357/affiliationGroups.json", '"value":"University of Florida"', '"sourceName":"Veronica Hinman"', raw=True)],
    notes=("DEPARTURE: her ORCID record ends the CMU employment in 2024 and adds 'University of Florida, Whitney Lab, Director, "
           "2025-'; OpenAlex's 2026 works carry University of Florida. CMU pages (CBD profile, lab site) still show her as "
           "Biological Sciences department head. Window coverage 2016-2024. Byline 'Veronica F. Hinman' / 'Hinman VF'. The live "
           "lab people page renders current members via a plugin (empty in HTML), so members come from the Oct-2019 Wayback "
           "capture plus the alumni list."),
)

# ---------------------------------------------------------------------------- Jeff Ichnowski
RIJ = "https://www.ri.cmu.edu/ri-faculty/jeffrey-ichnowski/"
JI = "https://ichnow.ski/"
D["Jeff Ichnowski"] = dict(
    status="pi",
    status_ev=[SE(RIJ, "Jeffrey Ichnowski Jeffrey Ichnowski Assistant Professor Home Department: RI", "current phd students Hongyi Chen Bardienus Duisterhof Adam Hung Yuemin Mao")],
    students=[
        ST("Hongyi Chen", "phd", None, Q(RIJ, "Jeffrey Ichnowski's Google Scholar Profile current phd students Hongyi Chen")),
        ST("Bardienus Duisterhof", "phd", None, Q(RIJ, "current phd students Hongyi Chen Bardienus Duisterhof")),
        ST("Adam Hung", "phd", None, Q(RIJ, "current phd students Hongyi Chen Bardienus Duisterhof Adam Hung")),
        ST("Yuemin Mao", "phd", None, Q(RIJ, "current phd students Hongyi Chen Bardienus Duisterhof Adam Hung Yuemin Mao")),
        ST("Kalie Ching", "masters", None, Q(RIJ, "current masters students Kalie Ching")),
        ST("Arthur Jakobsson", "masters", None, Q(RIJ, "current masters students Kalie Ching Arthur Jakobsson")),
        ST("Romina Mir", "member", None, Q(RIJ, "current affiliates Romina Mir")),
        ST("Richard Xu", "member", None, Q(RIJ, "current affiliates Romina Mir Richard Xu")),
        ST("Uksang Yoo", "phd", None, Q(RIJ, "past phd students Uksang Yoo")),
        ST("Dingkun Guo", "masters", None, Q(RIJ, "past masters students Dingkun Guo")),
        ST("Jeffrey Ke", "masters", None, Q(RIJ, "past masters students Dingkun Guo Jeffrey Ke")),
        ST("Yunchao Yao", "masters", None, Q(RIJ, "past masters students Dingkun Guo Jeffrey Ke Yunchao Yao")),
    ],
    identity=dict(dblp=[], orcid=[], openalex=["A5005587345"], evidence=[
        ID("openalex_verified", Q(JI, "FogROS2: An Adaptive Platform for Cloud and Fog Robotics Using ROS 2 Jeffrey Ichnowski"), "W4383108367 (2023) on his homepage publication list; 43 title matches in total."),
        ID("openalex_verified", Q(JI, "GOMP: Grasp-Optimized Motion Planning for Bin Picking Jeffrey Ichnowski"), "W3090993660 (2020)."),
        ID("openalex_verified", Q(JI, "Deep Imitation Learning of Sequential Fabric Smoothing From an Algorithmic Supervisor Daniel Seita , Aditya Ganapathi, Ryan Hoque, Minho Hwang , Edward Cen, Ajay Kumar Tanwani, Ashwin Balakrishna , Brijen Thananjeyan , Jeffrey Ichnowski"), "W3132971170 (2020)."),
    ]),
    appt=[SE(JI, "Jeffrey Ichnowski, Ph.D. Assistant Professor Robotics Institute Carnegie Mellon University", "AUTOLAB at the University of California at Berkeley.")],
    pi_must=["Ichnowski"],
    notes=("Byline 'Jeffrey Ichnowski' (input name 'Jeff Ichnowski'). No DBLP pid captured (dblp.org bot-walled here). "
           "OpenAlex A5005587345 (ORCID 0000-0003-4874-9478 on the OpenAlex record) verified against his homepage list; the "
           "ORCID record names him but carries no affiliation and his pages do not link it, so the ORCID is not listed as "
           "verified. No dated arrival statement found (homepage: assistant professor at RI after a Berkeley postdoc); his "
           "first PhD-thesis chairing at RI is in 2026.")
)

# ---------------------------------------------------------------------------- C. Joel McManus
MP = "https://labs.bio.cmu.edu/mcmanus/people/"
D["C. Joel McManus"] = dict(
    status="pi",
    status_ev=[Q(MP, "Melisa Tosiano Melisa is a PhD candidate in the McManus lab."),
               SE("https://www.cmu.edu/cbd/people/mcmanus.html", "C. Joel McManus C. Joel McManus Associate Professor", "Department of Biological Sciences")],
    students=[
        ST("Melisa Tosiano", "phd", None, Q(MP, "Melisa Tosiano Melisa is a PhD candidate in the McManus lab."), note="Spelled 'Melissa Tosiano' on the CBD profile."),
        ST("Christina Akirtava", "phd", [None, 2023], Q(MP, "Ph.D Students Christina Akirtava , Ph.D. Biological Sciences, 2023.")),
        ST("Yizhu Lin", "phd", [None, 2018], Q(MP, "Yizhu Lin , Ph.D. Biological Sciences, 2018.")),
        ST("Pieter Spealman", "phd", [None, 2017], Q(MP, "Pieter Spealman , Ph.D. Biological Sciences, 2017.")),
        ST("Salini Konikkat", "postdoc", [2016, 2018], Q(MP, "Lab alumni Post-Docs Salini Konikkat , Ph.D. Biological Sciences, 2016 (postdoc 2016-2018).")),
        ST("Kara Delbridge", "member", None, Q(MP, "Kara Delbridge Kara graduated from the University of Tennessee with a major in biology and a minor in math."),
           note="Entry on the McManus lab People page ('Now that she is in the McManus lab ...'); post-baccalaureate researcher."),
        ST("Lucy Johnson", "member", None, Q(MP, "Lucy Johnson Lucy is a postbac in the McManus lab.")),
        ST("Zeqing Jiang", "undergraduate", None, Q(MP, "Zeqing Jiang Zeqing is an undergraduate in the McManus Lab")),
        ST("Yuning Zheng", "masters", [None, 2025], Q(MP, "Masters Students Yuning Zheng , M.S. Computational Biology, 2025.")),
        ST("Rohan Munoth", "masters", [None, 2025], Q(MP, "Rohan Munoth , M.S. Quantitative Biology and Bioinformatics, 2025.")),
        ST("Simon Chow", "masters", [None, 2023], Q(MP, "Simon Chow , M.S. Computational Biology, 2023.")),
        ST("Sanat Mishra", "masters", [None, 2023], Q(MP, "Sanat Mishra , M.S. Quantitative Biology and Bioinformatics, 2023.")),
        ST("Evan Corden", "masters", [None, 2023], Q(MP, "Evan Corden , M.S. Computational Biologym 2023.")),
        ST("Saina Mahera", "masters", [None, 2020], Q(MP, "Saina Mahera , M.S. Computational Biology, 2020.")),
        ST("Ayushi Sood", "masters", [None, 2020], Q(MP, "Ayushi Sood , M.S. Computational Biology, 2020.")),
        ST("Brendan Wee", "masters", [None, 2019], Q(MP, "Brendan Wee , M.S. Computational Biology, 2019.")),
        ST("Tianqi Tang", "masters", [None, 2018], Q(MP, "Tianqi Tang , M.S. Computational Biology, 2018.")),
        ST("Myles Mao", "masters", [None, 2017], Q(MP, "Myles Mao , M.S. Computational Biology, 2017.")),
        ST("Chaohao Gu", "masters", [None, 2017], Q(MP, "Chaohao Gu , M.S. Computational Biology, 2017.")),
        ST("Emma Kulbida", "undergraduate", [None, 2025], Q(MP, "Undergraduates Emma Kulbida , B.S. Biological Sciences, 2025.")),
        ST("Cassia Williams-Rogers", "undergraduate", [None, 2023], Q(MP, "Cassia Williams-Rogers , B.S. Biological Sciences, 2023.")),
        ST("Kiran Mirpuri", "undergraduate", [None, 2021], Q(MP, "Kiran Mirpuri , B.S. Biological Sciences, 2021.")),
        ST("Valerie Collins", "undergraduate", [None, 2020], Q(MP, "Valerie Collins, B.S. Biological Sciences, 2020.")),
        ST("Lauren Nazzaro", "undergraduate", [None, 2019], Q(MP, "Lauren Nazzaro , B.S. Biological Sciences, 2019.")),
        ST("Hunter Kready", "undergraduate", [None, 2019], Q(MP, "Hunter Kready , B.S. Biological Sciences, 2019.")),
        ST("Alexander Muralles", "undergraduate", [None, 2019], Q(MP, "Alexander Muralles , B.S. Biological Sciences, 2019.")),
    ],
    identity=dict(dblp=["https://dblp.org/pid/178/2932"], orcid=[], openalex=["A5088627617"], evidence=[]),
    appt=[orcid_cmu_affil("0000-0002-6605-2642", "Charles McManus")],
    notes=("Biological Sciences associate professor (CBD core). Students were missed because the advisees are listed on his "
           "lab site (labs.bio.cmu.edu/mcmanus/people) and CBD profile, not in SCS thesis records. ORCID 0000-0002-6605-2642 "
           "is held as 'Charles McManus' (self-asserted CMU Biological Sciences Associate Professor, 2011-), a byline-name "
           "mismatch worth noting; identity anchors were already sufficient (26 lab papers)."),
)

# ---------------------------------------------------------------------------- Matt Ruffalo
D["Matt Ruffalo"] = dict(
    status="not_pi_in_window",
    status_ev=[SE("https://www.cmu.edu/cbd/people/ruffalo.html", "Matt Ruffalo Matt Ruffalo Systems Scientist", "Lab Members Sean Donahue Research Programmer"),
               Q(WB + "20170427003649id_/http://www.cbd.cmu.edu:80/directory/fellows/postdoctoral-researchers/", "Matt Ruffalo Advisor: Ziv Bar-Joseph")],
    students=[ST("Sean Donahue", "other", None, Q("https://www.cmu.edu/cbd/people/ruffalo.html", "Lab Members Sean Donahue Research Programmer"),
                 note="Staff research programmer listed as his only lab member - not a student.")],
    appt=[Q(WB + "20170427003649id_/http://www.cbd.cmu.edu:80/directory/fellows/postdoctoral-researchers/", "Matt Ruffalo Advisor: Ziv Bar-Joseph")],
    notes=("Research staff: CBD postdoc under Ziv Bar-Joseph (2017-2019 postdoc listings), Systems Scientist from 2020. His "
           "CBD profile lists one lab member, a staff Research Programmer; no student or postdoc advisee was found on CBD "
           "postdoc/Lane-fellow/CPCB pages, KiltHub, or the SCS reports archive. He has lab papers (14) but supervised no "
           "student, so 'research staff who supervised nobody' (a staff member only)."),
)

# ---------------------------------------------------------------------------- William L Scherlis
MAAS = "http://reports-archive.adm.cs.cmu.edu/anon/isr2016/abstracts/16-105.html"
S3 = "https://www.s3d.cmu.edu/people/core-faculty/scherlis-william.html"
D["William L Scherlis"] = dict(
    status="pi",
    status_ev=[Q(MAAS, "Thesis Committee: Jonathan Aldrich (Co-Chair) William L. Scherlis (Co-Chair)")],
    students=[ST("Michael Maass", "phd", [None, 2016], Q(MAAS, "CMU-ISR-16-105 A Theory and Tools for Applying Sandboxes Effectively Michael Maass March 2016 Ph.D. Thesis (SE)"),
                 note="Thesis Committee: Jonathan Aldrich (Co-Chair) William L. Scherlis (Co-Chair) - same page.")],
    identity=dict(dblp=["https://dblp.org/pid/s/WilliamLScherlis"], orcid=[], openalex=[], evidence=[
        ID("openalex_candidate", Q("https://api.openalex.org/authors?per-page=25&search=William+L.+Scherlis", '"display_name": "William L. Scherlis"', raw=True),
           "Candidate OpenAlex A5018254610 (103 works, last institution CMU) - NOT verified: no own publication list found (S3D bio has none). Its 6 works dated 2016+: 'Advancing Cybersecurity: A Framework of Cyber Research Priorities' (2026, CMU; also a KiltHub record), 'Seven Core Research Areas for a Rapidly Evolving Cyber Landscape' (2026, SEI), 'Formal Methods at Scale' (2022, DARPA), 'Design Dimensions for Software Certification' (2019), and two re-dated older items."),
    ]),
    appt=[SE(S3, "Bio William L. Scherlis is a professor of computer science at Carnegie Mellon", "he served as director of DARPA’s Information Innovation Office (I2O)")],
    pi_must=["Scherlis"],
    notes=("Status 'pi' rests on one in-window advisee: Michael Maass, CMU-ISR-16-105 (March 2016), co-chaired with Jonathan "
           "Aldrich; his other SE-PhD advisees graduated before 2016. On leave Sept 2019-Sept 2022 as DARPA I2O director / "
           "special assistant (S3D bio), which explains few CMU papers. Byline variants 'William L. Scherlis', 'William Scherlis', "
           "'W.L. Scherlis'. Only 3 OpenAlex name hits 2016+, 1 CMU-affiliated."),
)

# ---------------------------------------------------------------------------- Adrien Treuille
D["Adrien Treuille"] = dict(
    status="not_pi_in_window",
    status_ev=[Q(WB + "20160410060750id_/http://ri.cmu.edu/ri_people.html?fcode=5&menu_id=255&distype=detail&dis_type=detail&list_type=current&selected_letter=AZ",
                 "Adrien Treuille Principal Project Scientist, RI Email: Phone: (206) 409-8246"),
               SE("http://www.cs.cmu.edu/~treuille/", "Adrien Treuille Adrien Treuille treuille [at] cs.cmu.edu", "I am an Assistant Professor of computer science and robotics at Carnegie Mellon University")],
    students=[],
    appt=[Q(WB + "20160410060750id_/http://ri.cmu.edu/ri_people.html?fcode=5&menu_id=255&distype=detail&dis_type=detail&list_type=current&selected_letter=AZ",
            "Adrien Treuille Principal Project Scientist, RI Email: Phone: (206) 409-8246")],
    notes=("Former assistant professor (CSD/RI; 2015 CSD profile still 'Assistant Professor'); by April 2016 listed only as "
           "RI 'Principal Project Scientist' with a Seattle (206) phone - he had left for industry (later Streamlit co-founder). "
           "His homepage (last updated c. 2011) lists graduate students Jee Lee, Alex Limpaecher and Matt Stanton; Stanton's "
           "thesis is CMU-CS-14-136 (2014, reports-archive cs2014 listing). No advisee in 2016-2026 found. The 2 in-window lab "
           "papers are collaborations from the project-scientist tail."),
)

# ---------------------------------------------------------------------------- Randi Williams
HRW = "https://hcii.cmu.edu/people/randi-williams"
RWCV = "https://randiwilliams.com/files/RWilliams_CV.pdf"
D["Randi Williams"] = dict(
    status="pi",
    status_ev=[SE(HRW, "Randi Williams Randi Williams Assistant Research Professor Faculty", "Advisees Leah Teffera")],
    students=[ST("Leah Teffera", "phd", [2026, 2026], SE("https://hcii.cmu.edu/people/leah-teffera", "Leah Teffera PhD Students Email", "Advisors Randi Williams"),
                 note="Leah Teffera's own HCII PhD-student profile; quote is its 'Advisors' field. Also listed as Williams's advisee on her HCII profile.")],
    identity=dict(dblp=["https://dblp.org/pid/201/9170"], orcid=["0000-0002-7740-5749"], openalex=["A5055884793"], evidence=[
        ID("orcid_record", orcid_cmu_affil("0000-0002-7740-5749", "Randi Williams"),
           "ORCID record (self-asserted) employment: Carnegie Mellon University, Human Computer Interaction Institute, Assistant Research Professor."),
        ID("openalex_verified", Q(RWCV, "Williams, Hae Won Park, Lauren Oh, and Cynthia Breazeal. 2019. PopBots: Designing an Artificial Intelligence Curriculum for Early Childhood Education"), "W2964603799 on her CV; 21 title matches in total."),
        ID("openalex_verified", Q(RWCV, "Williams, Cynthia Breazeal. 2020. Zhorai: Designing A Conversational Agent for Children to Explore Machine Learning Concepts"), "W3037097818 on her CV."),
        ID("openalex_verified", Q(RWCV, "Williams, Hae Won Park, and Cynthia Breazeal. 2018. How smart are the smart toys"), "W2808494254 on her CV."),
    ]),
    appt=[SE(RWCV, "Randi C. Williams randiw@andrew.cmu.edu", "Assistant Research Professor ​ ​ ​ ​ July 2026", long=True)],
    notes=("Started at CMU HCII in July 2026 (CV); PhD and all prior work at MIT Media Lab / Day of AI. OpenAlex "
           "A5055884793 is hers (verified) but none of its works lists CMU yet, so the paper gap (no_school_affiliation) is "
           "genuine for now; byline variants 'Randi Williams', 'Randi C. Williams', 'Williams, Randi'."),
)

# ---------------------------------------------------------------------------- Yun William Yu
YG = "https://yunwilliamyu.net/content/pages/research-group.html"
YCV = "https://yunwilliamyu.net/content/static/curriculum-vitae.pdf"
D["Yun William Yu"] = dict(
    status="pi",
    status_ev=[SE(YG, "Current group members Yun William Yu - Associate Professor - Computational Biology", "Molly Borowiak - PhD Student - Computational Biology")],
    students=[
        ST("Molly Borowiak", "phd", None, Q(YG, "Molly Borowiak - PhD Student - Computational Biology")),
        ST("Aidan Zhang", "phd", None, Q(YG, "Aidan Zhang - PhD Student - Computational Biology")),
        ST("Spencer Gibson", "masters", None, Q(YG, "Spencer Gibson - M.S. Student - Biomedical Engineering")),
        ST("Navid Bin Hasan", "phd", None, Q("https://www.cmu.edu/cbd/people/yu.html", "Lab Members Molly Borowiak Ph.D. Student Navid Bin Hasan Ph.D. Student Aidan Zhang Ph.D. Student"), must=["Navid Bin Hasan"]),
        ST("Mahmudur Rahman Hera", "postdoc", None, Q("https://www.cmu.edu/cbd/people/current-lane-fellows.html", "Mahmudur Rahman Hera Advisor: Yun William Yu")),
        ST("Grace Oualline", "undergraduate", None, Q(YG, "Grace Oualline CMU Double Major in Biology and Computational Biology")),
        ST("Xiaolei (Brian) Zhang", "masters", None, Q(YG, "Xiaolei (Brian) Zhang CMU M.S. in Quantitative Biology and Bioinformatics"), must=["Zhang"]),
    ],
    identity=dict(dblp=[], orcid=["0000-0002-8275-9576"], openalex=["A5015501574"], evidence=[
        ID("orcid_on_own_page", SE(YG, "<strong>Yun William Yu</strong> - Associate Professor", 'href="https://orcid.org/0000-0002-8275-9576"', raw=True),
           "His research-group page links ORCID 0000-0002-8275-9576; the ORCID record also lists CMU Computational Biology, Assistant Professor, 2023-."),
        ID("openalex_verified", Q(YCV, "Yu YW, Berger B (2016). Fast genotyping of known SNPs through approximate k-mer matching"), "W2515342656 on his CV; 29 title matches in total."),
        ID("openalex_verified", Q(YCV, "Yu YW (2023). Fast and robust metagenomic sequence comparison through sparse chaining with skani"), "W4386923678 on his CV."),
        ID("openalex_verified", Q(YCV, "Yu YW, Ippolito D, Jarvie M, Pilat D, Struck B, Krastev S, Sharma A (2020). The need for privacy with public digital contact tracing during the COVID-19 pandemic"), "W3028695384 on his CV."),
    ]),
    appt=[orcid_cmu_affil("0000-0002-8275-9576", "Yun William Yu"),
          SE(YG, "Yun William Yu - Associate Professor - Computational Biology William is", "Prior to moving to CMU, he was an assistant professor in the math department at the University of Toronto")],
    pi_must=["Yu"],
    notes=("Joined CMU Computational Biology in 2023 from the University of Toronto (ORCID: CMU Assistant Professor 2023-). "
           "Byline 'Yun William Yu' / 'Yu YW' / 'Y. William Yu'. No DBLP pid captured. Toronto-era students in his alumni list "
           "are not recorded; only CMU members are."),
)
