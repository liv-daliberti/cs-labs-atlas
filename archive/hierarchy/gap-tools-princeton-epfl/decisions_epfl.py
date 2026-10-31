"""Researched decisions for the EPFL gap PIs (hierarchy/epfl/gap-input.json). Every evidence item is resolved against
hierarchy/epfl/gap-captures.sqlite by evlib (quote checked at build time). Build: build.py epfl
"""
from urllib.parse import urlencode

from evlib import q, rx, window, student, oa_verify, oa_author_quote, dedupe_students, infoscience_theses  # noqa: F401
from epfl_helpers import people_page_students

S = "epfl"
ROWS = []


def row(pi, status, status_evidence=(), students=(), dblp=(), orcid=(), openalex=(), identity_evidence=(),
        collection_person_id=None, appointment_notes=(), notes=None, openalex_candidates=()):
    idn = dict(dblp=list(dblp), orcid=list(orcid), openalex=list(openalex), evidence=list(identity_evidence))
    if openalex_candidates:  # not verified by the three-works rule (no own publication list / too few 2016+ works)
        idn["openalex_candidates"] = list(openalex_candidates)
    ROWS.append(dict(pi=pi, status=status, status_evidence=list(status_evidence), students=dedupe_students(list(students)),
                     identity=idn, collection_person_id=collection_person_id, appointment_notes=list(appointment_notes), notes=notes))


def ev(kind, item, note=None):
    d = dict(kind=kind, **item)
    if note:
        d["note"] = note
    return d


def opt(fn, *a, **k):
    """Optional evidence: [] when the capture is not stored (e.g. a Wayback fetch that was refused)."""
    try:
        r = fn(*a, **k)
        return r if isinstance(r, list) else [r]
    except (KeyError, ValueError):
        return []


def strip(e, note):
    o = {k: e[k] for k in ("url", "capture_url", "sha256", "quote") if k in e}
    o["note"] = note
    return o


def isurl(advisor):
    """The stored Infoscience discover URL that infosci.py builds for 'dc.contributor.advisor:"<advisor>"'."""
    return "https://infoscience.epfl.ch/server/api/discover/search/objects?" + urlencode(
        {"query": f'dc.contributor.advisor:"{advisor}"', "dsoType": "ITEM", "size": 100, "page": 0})


def isurl_raw(query):
    return "https://infoscience.epfl.ch/server/api/discover/search/objects?" + urlencode(
        {"query": query, "dsoType": "ITEM", "size": 100, "page": 0})


def pp(slug):
    return f"https://people.epfl.ch/{slug}?lang=en"


EDIC_LABS = "https://www.epfl.ch/education/phd/edic-computer-and-communication-sciences/edic-computer-and-communication-sciences/edic-affiliated-labs-research-expertise/"
IC2016 = "https://web.archive.org/web/20161218083132id_/http://ic.epfl.ch:80/professors"
APPT2025 = "https://actu.epfl.ch/news/appointment-of-epfl-professors-172"

# ---------------------------------------------------------------- Alexandra Henzinger
HOME_AH = "https://people.csail.mit.edu/ahenz/"
row("Alexandra Henzinger", "not_pi_in_window",
    status_evidence=[q(S, HOME_AH, "Alexandra Henzinger I am a postdoc at Stanford with Dan Boneh and an incoming Assistant Professor of "
                                   "Computer and Communication Sciences at EPFL, starting in Fall 2027.")],
    dblp=["https://dblp.org/pid/215/4426"],
    openalex=["A5028224055"],
    identity_evidence=[
        *[ev("dblp_person_page", e, "Wayback capture of the DBLP person page (dblp.org HTML is bot-walled).")
          for e in opt(rx, S, "https://web.archive.org/web/20251114022748id_/https://dblp.org/pid/215/4426.html", r"dblp: Alexandra Henzinger", name="Henzinger")],
        ev("own_homepage", q(S, HOME_AH, "Alexandra Henzinger I am a postdoc at Stanford with Dan Boneh"), "The PI's own homepage, used as the publication list below."),
        *oa_verify(S, "A5028224055", HOME_AH, "Henzinger", n=3),
        oa_author_quote(S, "A5028224055", "Alexandra Henzinger"),
    ],
    collection_person_id="epfl_person_527990fa14ff1d748400",
    appointment_notes=[q(S, HOME_AH, "Alexandra Henzinger I am a postdoc at Stanford with Dan Boneh and an incoming Assistant Professor of "
                                     "Computer and Communication Sciences at EPFL, starting in Fall 2027.")],
    notes="Incoming hire: her own homepage says she starts at EPFL in Fall 2027 and is recruiting PhD students to start then; "
          "people.epfl.ch/alexandra.henzinger returns 404 and Infoscience has no thesis she directs. No EPFL papers or students can "
          "exist yet; the EDIC affiliated-labs table already lists her ('TBC (IC)'). Revisit after Fall 2027.")

# ---------------------------------------------------------------- Amin Shokrollahi
DBLP_AS = "https://web.archive.org/web/20260130090934id_/https://dblp.org/pid/05/2386.html"
row("Amin Shokrollahi", "pi",
    status_evidence=[q(S, pp("amin.shokrollahi"), "Amin Shokrollahi amin.shokrollahi@epfl.ch http://algo.epfl.ch/index.php?p=group_members_amin vCard Professor Emeritus")],
    students=infoscience_theses(isurl_raw("dc.contributor.advisor:Shokrollahi"), ["Shokrollahi"]),
    dblp=["https://dblp.org/pid/05/2386"],
    identity_evidence=[ev("dblp_person_page", q(S, DBLP_AS, "Amin Shokrollahi ORCID ID inferred from metadata, verification pending 0000-0001-7938-7022 "
                                                            "visit author's page @ epfl.ch"),
                          "Wayback capture of the DBLP person page; DBLP lists the EPFL page as his homepage.")],
    collection_person_id="epfl_person_998bc24f3bea748202bc",
    notes="Papers are genuinely absent, not a matching failure: his 2016+ works carry Kandou Bus affiliations (e.g. OpenAlex W2966525599 "
          "'Kandou Bus, Lausanne, Switzerland', W3018249970, W4292862800, W4410492735), never EPFL. OpenAlex A5058641647 (ORCID "
          "0000-0001-7938-7022) is conflated with a namesake petroleum engineer at the University of Adelaide (CO2-storage papers "
          "2022-2025), so it is not listed as a verified id. Student added: Lyudmila Yartseva, PhD 2017, co-directed with Matthias "
          "Grossglauser (Infoscience).")

# ---------------------------------------------------------------- Bertrand Merminod
NEWS_BM = "https://actu.epfl.ch/news/prof-bertrand-merminod-2"
row("Bertrand Merminod", "pi",
    students=infoscience_theses(isurl("Merminod, Bertrand"), ["Merminod"]),
    openalex=[],
    collection_person_id="epfl_person_700da3285322e619298e",
    appointment_notes=[
        q(S, NEWS_BM, "Professor Bertrand Merminod, Full Professor of Topometry, left on retirement on 31 January 2023."),
        q(S, NEWS_BM, "Bertrand Merminod studied at EPFL before returning as an associate professor in 1995."),
    ],
    notes="outside_appointment is a missing faculty period, not a non-appointment: EPFL's retirement notice gives associate professor "
          "from 1995 and retirement on 2023-01-31 (now honorary professor), so his 2016-2018 EPFL-affiliated works (OpenAlex A5062099260) "
          "fall inside his appointment. Students from Infoscience: PhDs Dragos Constantin (2017, co-directed with Yosef Akhtman) and "
          "Kevin Barbieux (2018, with Jan Skaloud); master's theses 2017-2021.")

# ---------------------------------------------------------------- Bixio Rimoldi
row("Bixio Rimoldi", "not_pi_in_window",
    status_evidence=[
        q(S, pp("bixio.rimoldi"), "Bixio Rimoldi bixio.rimoldi@epfl.ch vCard Professor Emeritus , Honorary Professors IC"),
        *[strip(e, "Latest thesis he directed per Infoscience (dc.contributor.advisor 'Rimoldi, Bixio': 12 records, defended 2002-2015)")
          for e in infoscience_theses(isurl("Rimoldi, Bixio"), ["Rimoldi"], from_year=2015, to_year=2015)],
    ],
    dblp=["https://dblp.org/pid/11/2041"],
    openalex_candidates=["A5074152408"],
    identity_evidence=[
        *[ev("dblp_person_page", e, "Wayback capture of the DBLP person page (dblp.uni-trier.de mirror).")
          for e in opt(q, S, "https://web.archive.org/web/20251214084048id_/https://dblp.uni-trier.de/pid/11/2041.html", "ORCID Bixio Rimoldi export bibliography")],
        oa_author_quote(S, "A5074152408", "Bixio Rimoldi"),
    ],
    collection_person_id="epfl_person_fd8b62b2e2fbd9deb852",
    notes="No student in 2016-2026: every Infoscience thesis or student work with Rimoldi as advisor (12) was defended 2002-2015 "
          "(last: Adrian Tarniceriu, 2015); his EPFL profile lists only pre-EPFL past students (Quinn Li, Long Duan, Ruediger Urbanke) and "
          "no current ones; now Professor Emeritus. He was an active professor (LCM) in 2016-2019 but with no stated student, so the "
          "status is a judgment call (closest category: emeritus with no student since 2016). OpenAlex A5074152408 has a single 2016+ "
          "work (his textbook 'Principles of Digital Communication', 2016, EPFL-affiliated), so the 3-work verification rule cannot be "
          "met; listed from the author record and DBLP pid 11/2041.")

# ---------------------------------------------------------------- Christian Piguet
row("Christian Piguet", "not_pi_in_window",
    status_evidence=[
        *opt(q, S, IC2016, "External adjunct Professors Jean-Dominique Decotignie LAMS jean-dominique.decotignie@epfl.ch BC 140 Christian Piguet LAP"),
        dict(note="Infoscience jury field of Karim Kanoun's thesis (2015), the latest of the 3 Infoscience records with Piguet as advisor",
             **rx(S, isurl("Piguet, Christian"), r"Prof\. David Atienza Alonso, Prof\. Christian Piguet \(directeurs\)", views=("raw",))),    ],
    dblp=["https://dblp.org/pid/29/5753"],
    identity_evidence=[ev("dblp_person_page", e, "Wayback capture of the DBLP person page.")
                       for e in opt(rx, S, "https://web.archive.org/web/20250826035112id_/https://dblp.org/pid/29/5753.html", r"dblp: Christian Piguet", name="Piguet")],
    collection_person_id="epfl_person_a19f3e92ae81fb6d26f7",
    notes="External adjunct professor (CSEM) attached to LAP (Ienne's processor-architecture lab), not the head of a group; "
          "people.epfl.ch/christian.piguet is gone (404). Infoscience: the theses he co-directed were defended in 2011 and 2015 (Karim "
          "Kanoun, with David Atienza); none since. His 2016+ OpenAlex works (A5025444477) carry no EPFL affiliation.")

# ---------------------------------------------------------------- Christos Kozyrakis
WIKI_CK = "https://en.wikipedia.org/wiki/Christos_Kozyrakis"
row("Christos Kozyrakis", "not_pi_in_window",
    status_evidence=[
        rx(S, WIKI_CK, r"In 2015, he spent a year at École Polytechnique Fédérale de Lausanne as a professor of computer science and communication systems\..{0,120}?Kozyrakis's research", name="Kozyrakis"),
        *opt(q, S, "https://web.archive.org/web/20160108114526id_/http://ic.epfl.ch:80/professors", "Christos Kozyrakis IC-DO"),
        dict(note="His own homepage in March 2016 (Wayback): primary appointment still Stanford.",
             **q(S, "https://web.archive.org/web/20160307234716id_/http://csl.stanford.edu/~christos/",
                 "Christos Kozyrakis is an Associate Professor of Electrical Engineering and Computer Science at Stanford University")),
    ],
    collection_person_id="epfl_person_3cc9375302e1bc93dfde",
    appointment_notes=[rx(S, WIKI_CK, r"He joined Stanford University in 2002 after completing his doctorate\..{0,300}?Kozyrakis's research", name="Kozyrakis")],
    notes="A one-year visiting professorship (2015-2016) while on leave from Stanford: the 2016 IC faculty card lists him under IC-DO "
          "(the dean's office), not a lab of his own; Infoscience has no thesis with Kozyrakis as advisor; his EPFL directory entry "
          "(people.epfl.ch/229313) is gone. His 4-5 EPFL-affiliated 2016 papers are from that visit. The quote is from Wikipedia "
          "(secondary); neither his current nor his March 2016 homepage mentions the visit.")

# ---------------------------------------------------------------- Damir Filipovic
row("Damir Filipovic", "pi",
    students=people_page_students(pp("damir.filipovic")) + infoscience_theses(isurl("Filipovic, Damir"), ["Filipovic", "Filipović"]),
    collection_person_id="epfl_person_b8f2775087ef991d847b",
    notes="Students from his EPFL profile (3 current PhD students; past theses 2016-2026, incl. one co-directed) and Infoscience "
          "(dc.contributor.advisor 'Filipovic, Damir').")

# ---------------------------------------------------------------- Giuseppe Carleo
row("Giuseppe Carleo", "pi",
    students=people_page_students(pp("giuseppe.carleo")) + infoscience_theses(isurl("Carleo, Giuseppe"), ["Carleo"]),
    collection_person_id="epfl_person_c66de03fa4e03acb9024",
    notes="Students from his EPFL profile (12 current PhD students, 5 past theses) and Infoscience (6 theses 2024-2026, EDPY/CQSL). "
          "Doctoral students are in the physics programme (EDPY), which is why no CS advising record matched.")

# ---------------------------------------------------------------- Jean-Dominique Decotignie
row("Jean-Dominique Decotignie", "pi",
    students=infoscience_theses(isurl("Decotignie, Jean-Dominique"), ["Decotignie"]),
    dblp=["https://dblp.org/pid/62/2980"],
    identity_evidence=[oa_author_quote(S, "A5110890572", "Jean-Dominique Decotignie")],
    collection_person_id="epfl_person_d949c92bc66811861908",
    appointment_notes=[q(S, pp("jean-dominique.decotignie"), "Jean-Dominique Decotignie jean-dominique.decotignie@epfl.ch vCard Invited guest , Honorary Professors IC")],
    notes="Papers are genuinely absent with an EPFL affiliation: OpenAlex A5110890572 (his only author id; 10 works 2016-2019) lists "
          "CSEM (Swiss Center for Electronics and Microtechnology, Neuchatel) on every 2016+ work and EPFL only for 1991-1998, so the "
          "EPFL sweep has no name hit. Not listed as a verified OpenAlex id: no personal publication list exists to check works "
          "against (his EPFL profile has none). Student: Daniel Camilo Rojas Quiros, PhD 2018 (Infoscience).")

# ---------------------------------------------------------------- Laura Grigori
row("Laura Grigori", "pi",
    students=people_page_students(pp("laura.grigori")),
    collection_person_id="epfl_person_7826e3d949d82bec1ec1",
    notes="7 current doctoral students on her EPFL profile (chair HPNALGS since 2023; doctoral programme EDMA). No EPFL thesis "
          "completed yet, so Infoscience has none.")

# ---------------------------------------------------------------- Lénaïc Chizat
HOME_LC = "https://lchizat.github.io/"
PUBS_LC = "https://www.epfl.ch/labs/dola/dola-chair-of-dynamics-of-learning-algorithms/publications/"
LC_HEAD = r"PhD students and Post-docs"
LC_WORKS = ("https://api.openalex.org/works?filter=author.id%3AA5010177550%2Cfrom_publication_date%3A2016-01-01&per-page=200"
            "&select=id%2Ctitle%2Cpublication_year%2Cpublication_date%2Cdoi%2Cauthorships&sort=publication_year%3Adesc")
LC_WORKS_SHA = "4148e49db381679f696b8c2d561ecb21d9e6160272132e981bf7203c9aee29c1"
row("Lénaïc Chizat", "pi",
    students=people_page_students(pp("lenaic.chizat")) + infoscience_theses(isurl("Chizat, Lénaïc"), ["Chizat"]) + [
        student(S, HOME_LC, "Javier Maass", "phd", [2025, 2026], needle="Javier Maass (2025-…) (Continuing at EPFL under the supervision of Nicolas Boumal)",
                heading=LC_HEAD, before=0, after=0),
        student(S, HOME_LC, "Louis-Pierre Chaintron", "postdoc", [2025, 2026], needle="Louis-Pierre Chaintron (2025-2026)", heading=LC_HEAD, before=0, after=0),
        student(S, HOME_LC, "Orr Paradise", "postdoc", [2025, 2026], needle="Orr Paradise (2025-2026)", heading=LC_HEAD, before=0, after=0),
        student(S, HOME_LC, "Pierre Marion", "postdoc", [2024, 2025], needle="Pierre Marion (2024-2025)", heading=LC_HEAD, before=0, after=0),
        student(S, HOME_LC, "Alex Delalande", "postdoc", [2024, 2025], needle="Alex Delalande (2024-2025)", heading=LC_HEAD, before=0, after=0),
        student(S, HOME_LC, "Tomas Vaškevičius", "postdoc", [2022, 2024], needle="Tomas Vaškevičius (2022-2024)", heading=LC_HEAD, before=0, after=0),
    ],
    dblp=["https://dblp.org/pid/192/1488"],
    openalex=["A5010177550"],
    identity_evidence=[
        *[ev("dblp_person_page", e, "Wayback capture of the DBLP person page (dblp.uni-trier.de mirror).")
          for e in opt(rx, S, "https://web.archive.org/web/20250818010813id_/https://dblp.uni-trier.de/pid/192/1488.html", r"dblp: L[ée]na[ïi]c Chizat", name="Chizat")],
        ev("own_lab_publications", q(S, PUBS_LC, "Infinite-width limit of deep linear neural networks L. Chizat"),
           "DOLA (his chair) publication list, used for the OpenAlex check below."),
        *[dict(kind="own_publication_list_title", note=f"OpenAlex {w} ({y}) '{tt}' is in the works of A5010177550 (stored response "
                                                        f"{LC_WORKS} sha256 {LC_WORKS_SHA}) and is listed on the DOLA publication list",
               **q(S, PUBS_LC, quote, name="Chizat"))
          for w, y, tt, quote in [
              ("W4396678331", 2024, "Infinite-width limit of deep linear neural networks", "Infinite-width limit of deep linear neural networks L. Chizat"),
              ("W4392286628", 2024, "Displacement smoothness of entropic optimal transport", "Displacement smoothness of entropic optimal transport G. Carlier ; L. Chizat"),
              ("W4307652671", 2023, "On the symmetries in the dynamics of wide two-layer neural networks",
               "On the symmetries in the dynamics of wide two-layer neural networks K. Hajjar ; L. Chizat")]],
        oa_author_quote(S, "A5010177550", "Lénaïc Chizat"),
    ],
    collection_person_id="epfl_person_5bf6d5a24f34eb28b0ad",
    appointment_notes=[q(S, HOME_LC, "Lénaïc Chizat I am an Associate Professor at NUS in the Department of Mathematics")],
    notes="Identity anchored: OpenAlex A5010177550 (ORCID 0000-0002-6553-1211 on the author record) verified against the DOLA "
          "publication list; DBLP 192/1488 from the local DBLP family cache. Students: Guillaume Wang (PhD 2026, EPFL profile + "
          "Infoscience) and the 'PhD students and Post-docs' list on his homepage for his EPFL years (2021-2026); Karl Hajjar "
          "(2020-2023, a Paris-Saclay PhD from before EPFL) is left out. Roles other than Wang and Maass are postdocs (the heading "
          "covers both). Surprise: his homepage (generated 2026-07-06) now says he is an Associate Professor at NUS, while the EPFL "
          "directory still lists him as tenure-track professor of DOLA; the EPFL period likely ends in 2026.")

# ---------------------------------------------------------------- Mahsa Shoaran
row("Mahsa Shoaran", "pi",
    students=people_page_students(pp("mahsa.shoaran")) + infoscience_theses(isurl("Shoaran, Mahsa"), ["Shoaran"]),
    collection_person_id="epfl_person_73dc0ca2eea07a67cbf6",
    appointment_notes=[q(S, APPT2025, "Shoaran, currently Tenure Track Assistant Professor at EPFL, as Associate Professor of Electrical and "
                                       "Electronic Engineering at the School of Engineering (STI)")],
    notes="20 current doctoral students on her EPFL profile plus 2 Infoscience theses (Cong Ding 2024, Yasemin Engur 2026); doctoral "
          "programme EDEE (STI), hence no CS advising record.")

# ---------------------------------------------------------------- Martin Rajman
row("Martin Rajman", "not_pi_in_window",
    status_evidence=[
        q(S, pp("martin.rajman"), "Martin Rajman martin.rajman@epfl.ch vCard Senior Scientist , SIN - Teaching"),
        rx(S, pp("martin.rajman"), r"Martin Rajman is a senior researcher.*?Past EPFL PhD Students Marita Ailomaa \(2009\).*?Martin Vesel. \(2012\)", name="Rajman", views=("html",)),
    ],
    dblp=["https://dblp.org/pid/88/6532"],
    collection_person_id="epfl_person_97278d23828fd0d090a3",
    appointment_notes=[q(S, pp("martin.rajman"), "Alongside his research management activities, Martin Rajman is a senior researcher specializing in "
                                                  "artificial intelligence, computational linguistics, and data-driven probabilistic machine learning.")],
    notes="Research staff (Senior Scientist; executive roles in the Swiss National AI Institute and the EPFL AI Center) who supervised no "
          "one in 2016-2026: the 11 theses he directed (EPFL profile and Infoscience agree) were defended 2002-2012, and no student "
          "work names him as advisor since. 'SCI IC MR Group' is a staff-scientist budget unit, not a lab with members. The "
          "outside_appointment papers (2017-2026, OpenAlex A5025577122) are his, but the lab has no students to pair with them.")

# ---------------------------------------------------------------- Mats Julius Stensrud
row("Mats Julius Stensrud", "pi",
    students=people_page_students(pp("mats.stensrud")) + infoscience_theses(isurl("Stensrud, Mats Julius"), ["Stensrud"]),
    collection_person_id="epfl_person_7632bda828ac1c7ca85b",
    notes="5 current doctoral students and 2 past theses (Matias Janvin 2023, Amit Sawant 2025) on his EPFL profile, matching "
          "Infoscience; doctoral programme EDMA (SB).")

# ---------------------------------------------------------------- Miranda Wei
HOME_MW = "https://mirandawei.com/"
PUBS_MW = "https://mirandawei.com/publications/"
row("Miranda Wei", "not_pi_in_window",
    status_evidence=[
        rx(S, HOME_MW, r"Miranda Wei Postdoctoral researcher at Princeton University.*?I’m hiring for PhD positions to start at EPFL in fall 2027!", name="Wei"),
        q(S, pp("miranda.wei"), "Miranda Wei miranda.wei@epfl.ch vCard Onboarding Professor"),
    ],
    dblp=["https://dblp.org/pid/217/4562"],
    openalex=["A5040630331"],
    identity_evidence=[
        *[ev("dblp_person_page", e, "Wayback capture of the DBLP person page.")
          for e in opt(rx, S, "https://web.archive.org/web/20260216193756id_/https://dblp.org/pid/217/4562.html", r"dblp: Miranda Wei", name="Wei")],
        *oa_verify(S, "A5040630331", PUBS_MW, "Wei", n=3),
        oa_author_quote(S, "A5040630331", "Miranda Wei"),
    ],
    collection_person_id="epfl_person_66b54aa6dc1c3c322cc8",
    appointment_notes=[q(S, APPT2025, "Wei, currently Postdoctoral Researcher at Princeton University, USA, as Tenure Track Assistant Professor "
                                       "of Computer Science and Communication Systems in the School of Computer and Communication Sciences (IC)")],
    notes="Appointed 2025 (ETH Board), started fall 2026: the EPFL directory lists her as 'Onboarding Professor' (unit UPWEI) and her "
          "homepage says her first PhD students start in fall 2027. No EPFL students or EPFL-affiliated papers can exist yet; her "
          "OpenAlex works (A5040630331) are UW/Princeton. Judgment: an onboarding hire with no group yet; revisit in 2027.")

# ---------------------------------------------------------------- Nate Foster
STU_NF = "https://natefoster.org/students/"
row("Nate Foster", "pi",
    students=[
        dict(student(S, STU_NF, "Aditya Senthilnathan", "phd", [2026, 2026], needle="PhD Students Aditya Senthilnathan", before=0, after=0),
             note="Also in the EPFL directory as an EDIC doctoral student in LASER (people.epfl.ch/aditya.senthilnathan)."),
        dict(student(S, STU_NF, "Mark Barbone", "phd", [2026, 2026], needle="PhD Students Aditya Senthilnathan Mark Barbone", before=0, after=0),
             note="Also in the EPFL directory as an EDIC doctoral student in LASER (people.epfl.ch/mark.barbone)."),
    ],
    dblp=["https://dblp.org/pid/15/3253"],
    collection_person_id="epfl_person_2b33d3ca87b690a16dab",
    appointment_notes=[
        q(S, APPT2025, "Professor Nate (John Nathan) Foster, currently full Professor at Cornell University in Ithaca, USA, as Full Professor of "
                       "Computer Science and Communication Systems in the School of Computer and Communication Sciences (IC)"),
        rx(S, "https://natefoster.org", r"Nate Foster Professor of Computer & Communication Sciences EPFL.*?\[09/2025\] My research group will move to EPFL in January 2026\.", name="Foster"),
    ],
    notes="Group moved from Cornell in January 2026. Students from his own group page ('PhD Students' heading) restricted to those the "
          "EPFL directory confirms as EDIC doctoral students in LASER; Mark Moeller (still Cornell) and the other listed members "
          "are left out.")

# ---------------------------------------------------------------- Olaf Blanke
row("Olaf Blanke", "pi",
    students=people_page_students(pp("olaf.blanke")) + infoscience_theses(isurl("Blanke, Olaf"), ["Blanke"]),
    collection_person_id="epfl_person_b108bb750caab61a0a5e",
    notes="6 current doctoral students plus theses defended 2016-2026 (directed and co-directed) from his EPFL profile and Infoscience; "
          "doctoral programme EDNE (SV), hence no CS advising record.")

# ---------------------------------------------------------------- Olga Fink
row("Olga Fink", "pi",
    students=people_page_students(pp("olga.fink")) + infoscience_theses(isurl("Fink, Olga"), ["Fink"]),
    collection_person_id="epfl_person_6bf0177d91ffc8515ada",
    notes="10 current doctoral students and 3 theses (2025-2026) on her EPFL profile and in Infoscience; programmes EDRS/EDCE (ENAC).")

# ---------------------------------------------------------------- Olivier Verscheure
row("Olivier Verscheure", "not_pi_in_window",
    status_evidence=[q(S, pp("olivier.verscheure"), "Olivier Verscheure olivier.verscheure@epfl.ch https://ch.linkedin.com/in/overscheure vCard "
                                                     "Executive Director , SDSC - Administration")],
    dblp=["https://dblp.org/pid/83/3119"],
    identity_evidence=[ev("dblp_person_page", e, "Wayback capture of the DBLP person page.")
                       for e in opt(rx, S, "https://web.archive.org/web/20260129040303id_/https://dblp.org/pid/83/3119.html", r"dblp: Olivier Verscheure", name="Verscheure")],
    collection_person_id="epfl_person_608c3dbc6397d483c542",
    notes="Executive Director of the Swiss Data Science Center (administration) whose professorship is adjunct and teaching-only "
          "(Adjunct Professor in the SSC, SIN and SEL teaching units); his profile lists no doctoral students and Infoscience has no "
          "thesis with him as advisor. SDSC is a centre, not a lab of his.")

# ---------------------------------------------------------------- Rotem Arnon
HOME_RA = "https://sites.google.com/view/rotem-arnon"
PUBS_RA = "https://sites.google.com/view/rotem-arnon/research/papers"
ORCID_RA = "https://orcid.org/0000-0002-5808-6279/public-record.json"
row("Rotem Arnon", "pi",
    students=[student(S, pp("rotem.arnon"), "Itammar Steinberg", "phd", [2026, 2026], needle="PhD Students Itammar Steinberg", before=0, after=0)],
    orcid=["0000-0002-5808-6279"],
    openalex=["A5027892650"],
    identity_evidence=[
        ev("orcid_record", q(S, ORCID_RA, '"displayName":"Rotem Arnon"'), "ORCID public record names her; other name 'Rotem Arnon-Friedman'."),
        ev("orcid_record", rx(S, ORCID_RA, r'"content":"Rotem Arnon-Friedman"', views=("raw",)), "ORCID other name (her publishing name until 2025)."),
        dict(kind="orcid_employment", name_exempt=True,
             note="The same ORCID record's affiliations list an EPFL employment (2026, source 'ORCID Integration at EPFL').",
             **rx(S, "https://orcid.org/0000-0002-5808-6279/affiliationGroups.json",
                  r'"affiliationName":\{"errors":\[\],"value":"EPFL - École Polytechnique Fédérale de Lausanne"', views=("raw",))),
        ev("own_homepage", q(S, PUBS_RA, "Rotem Arnon - Papers"), "Her own papers page, used for the OpenAlex check below."),
        *oa_verify(S, "A5027892650", PUBS_RA, "Arnon", n=3),
        oa_author_quote(S, "A5027892650", "Rotem Arnon"),
    ],
    collection_person_id="epfl_person_a56e1fc6efdb5baffd5d",
    appointment_notes=[rx(S, HOME_RA, r"Rotem Arnon Quantum information theory News.*?My group members are now distributed between the two institutions\.", name="Arnon")],
    notes="Identity anchored: OpenAlex A5027892650 (display name 'Rotem Arnon-Friedman') verified against her own papers page, and "
          "ORCID 0000-0002-5808-6279 whose record names her with an EPFL employment. She published as Rotem Arnon-Friedman until "
          "2025; no DBLP pid found in the local caches under either name. At EPFL since February 2026 on leave from Weizmann.")

# ---------------------------------------------------------------- Samy Bengio
row("Samy Bengio", "pi",
    students=people_page_students(pp("samy.bengio")),
    dblp=["https://dblp.org/pid/b/SamyBengio"],
    openalex_candidates=["A5017529415"],
    identity_evidence=[oa_author_quote(S, "A5017529415", "Samy Bengio")],
    collection_person_id="epfl_person_652d9da5c474633618cb",
    notes="Papers are genuinely absent with an EPFL affiliation: he is an adjunct professor (listed 2025-2026) whose 2016+ works carry "
          "Google/Apple affiliations; the four EPFL-sweep works naming him (2018-2023) are EPFL only through co-authors. His EPFL "
          "theses as co-director (Chiappa ... Pozdnoukhov, 2006-2008) are from the IDIAP era. Current EDIC student: Kirill Brilliantov.")

# ---------------------------------------------------------------- Sarah Kenderdine
NOM_SK = "https://actu.epfl.ch/news/nominations-of-epfl-professors-31"
row("Sarah Irene Brutton Kenderdine", "pi",
    students=people_page_students(pp("sarah.kenderdine")) + infoscience_theses(isurl("Kenderdine, Sarah"), ["Kenderdine"]),
    collection_person_id="epfl_person_f6c00cfc4f71061b4653",
    appointment_notes=[q(S, NOM_SK, "Sarah Kenderdine, was named as Full Professor of Digital Museology in the College of Humanities.")],
    notes="outside_appointment is a missing faculty period: EPFL's 2016 nominations news names her Full Professor of Digital Museology "
          "(eM+ founded 2017), and she is still Full Professor (EMPLUS) in 2026, so her 2018-2025 EPFL-affiliated works (OpenAlex "
          "A5028298939) are in her appointment. Students: EPFL profile (3 current, 3 past theses 2024-2025) and Infoscience master's "
          "theses.")
