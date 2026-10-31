"""Researched facts for the 31 MIT gap labs (2026-10-22). Each fact names its stored source and the regex that finds
its verbatim quote; build_gap_evidence.py turns these into hierarchy/mit/gap-evidence.json.

Sources are live URLs or Wayback id_ capture URLs stored in hierarchy/mit/gap-captures.sqlite.
"""
from evlib import ev, student as S, idev, appt, dspace_student as DS  # noqa: F401  (kept: a project module; possibly a re-export or a side effect)

WB = "https://web.archive.org/web/"
KAIMING_WB = WB + "20260303190408id_/https://people.csail.mit.edu/kaiming/"
CLEAR = "https://clear.csail.mit.edu/people.html"
OASYS = "https://omarkhattab.com/"
FLAME = "https://flame.csail.mit.edu/"
PEL = "https://mit-pel.com/"
GORDON_JS = "http://mitchellg.github.io/data.js"
OA = "https://api.openalex.org/"


def oa_author(aid):
    return OA + "authors/" + aid


def oa_rx(aid, orcid, display, field="display_name"):
    """regex for the head of an OpenAlex author record: id, ORCID (or null), display name."""
    o = ('"orcid":"https://orcid\\.org/' + orcid.replace("-", "\\-") + '"') if orcid else '"orcid":null'
    return '"id":"https://openalex\\.org/' + aid + '",' + o + '.{0,400}?"' + field + '":"' + display + '"'


SPEC = {}


def add(pi, **kw):
    SPEC[pi] = kw


# ---------------------------------------------------------------- new faculty with group pages
def kaiming():
    st = [("Keya Hu", "phd", r"Research Group Grad students: Keya Hu"),
          ("Jake Austin", "phd", r"Grad students: Keya Hu , Jake Austin"),
          ("Xingjian Bai", "phd", r"Grad students: Keya Hu , Jake Austin , Xingjian Bai"),
          ("Mingyang Deng", "phd", r"Grad students: Keya Hu , Jake Austin , Xingjian Bai , Mingyang Deng"),
          ("Zongyi Li", "postdoc", r"Mingyang Deng Postdocs: Zongyi Li"),
          ("Tianhong Li", "postdoc", r"Postdocs: Zongyi Li , Tianhong Li")]
    return dict(
        status="pi",
        status_evidence=[ev(KAIMING_WB, r"Kaiming He 何恺明 Associate Professor, EECS, MIT", "Kaiming He")],
        students=[S(n, r, [2025, 2026], KAIMING_WB, rx, note="'Research Group' section of the PI's homepage (Wayback 2026-03-03; also in the 2025-12-13 capture); the live page of 2026-10 no longer shows the section") for n, r, rx in st],
        appointment_notes=[appt("https://people.csail.mit.edu/kaiming/", r"I am an Associate Professor with tenure in the Department of EECS at MIT", "Associate Professor"),
                           appt("https://people.csail.mit.edu/kaiming/", r"Before joining MIT in 2024, I was a research scientist at Facebook AI Research \(FAIR\)", "joining MIT")],
        notes="Joined MIT EECS in 2024. Students are not yet in DSpace theses (no dc.contributor.advisor match for 'Kaiming', 2016-2026). "
              "The pipeline's 11 'he' advising mentions are namesakes; the homepage 'Research Group' list (Wayback) names 4 grad students and 2 postdocs. "
              "Keya Hu is co-advised with Jacob Andreas (secondary report, not quoted).")


def bobu():
    rows = [("Tanmay Patel", "phd", None, r"Tanmay Patel PhD Student @ MIT"),
            ("Michal Lewkowicz", "phd", None, r"Michal Lewkowicz PhD Student @ MIT \(co-advised with Nick Roy\)"),
            ("Aryan Naveen", "phd", None, r"Aryan Naveen PhD Student @ MIT \(co-advised with Luca Carlone\)"),
            ("Yiran Tao", "phd", None, r"Yiran Tao PhD Student @ MIT"),
            ("Minyoung Hwang", "phd", None, r"Minyoung Hwang PhD Student @ MIT"),
            ("Nathan Dennler", "postdoc", None, r"Postdocs Nathan Dennler Postdoc"),
            ("Nick Walker", "postdoc", None, r"Nick Walker Postdoc"),
            ("Arthur Hu", "masters", None, r"Masters Students Arthur Hu MEng Student"),
            ("Arul Kolla", "masters", None, r"Arul Kolla MEng Student"),
            ("Shane Pornprinya", "masters", None, r"Shane Pornprinya Masters Student"),
            ("Amanda Cheng", "undergraduate", None, r"Undergraduate Students Amanda Cheng Undergraduate Student"),
            ("George Cao", "undergraduate", None, r"George Cao Undergraduate Student"),
            ("Jefferson Lin", "undergraduate", None, r"Jefferson Lin Undergraduate Student"),
            ("Jocelyn Zhao", "undergraduate", None, r"Jocelyn Zhao Undergraduate Student"),
            ("Jonas Sun", "undergraduate", None, r"Jonas Sun Undergraduate Student"),
            ("Kallie Wang", "undergraduate", None, r"Kallie Wang Undergraduate Student"),
            ("Kevin Chafloque", "undergraduate", None, r"Kevin Chafloque Undergraduate Student"),
            ("Jordan Abi Nader", "masters", [2024, 2026], r"Jordan Abi Nader , Masters \(2024-2026\)"),
            ("Audrey Lee", "masters", [2024, 2026], r"Audrey Lee , Masters \(2024-2026\)"),
            ("Helena Merker", "masters", [2024, 2026], r"Helena Merker , Masters \(2024-2026\)"),
            ("Megan Tian", "undergraduate", [2025, 2026], r"Megan Tian , Undergraduate \(2025-2026\)"),
            ("David Lee", "undergraduate", [2024, 2026], r"David Lee , Undergraduate \(2024-2026\)"),
            ("Min Khant Zaw", "undergraduate", [2024, 2025], r"Min Khant Zaw , Undergraduate \(2024-2025\)"),
            ("Ananya Kulshrestha", "undergraduate", [2024, 2025], r"Ananya Kulshrestha , Undergraduate \(2024-2025\)")]
    return dict(
        status="pi",
        status_evidence=[ev(CLEAR, r"Principal Investigator Andreea Bobu Assistant Professor Department of Aeronautics and Astronautics & CSAIL", "Andreea Bobu")],
        students=[S(n, r, y or [2026, 2026], CLEAR, rx, note=None if y else "current member on the CLEAR lab people page (observed 2026-10-22)") for n, r, y, rx in rows],
        notes="CLEAR lab (Collaborative Learning and Autonomy Research) people page. Collaborators, visiting students, MATS scholars and interns are left out. "
              "Her home department is AeroAstro (joined 2024); no DSpace thesis with dc.contributor.advisor 'Bobu' yet.")


def khattab():
    rows = [("Alex L. Zhang", "member", r"Its current members include: Alex L\. Zhang"),
            ("Diane Tchuindjo", "member", r"Its current members include: Alex L\. Zhang Diane Tchuindjo"),
            ("Jacob X. Li", "member", r"Its current members include: Alex L\. Zhang Diane Tchuindjo Jacob X\. Li"),
            ("Matthew Yang", "member", r"Its current members include: Alex L\. Zhang Diane Tchuindjo Jacob X\. Li Matthew Yang"),
            ("Rikiya Takehi", "member", r"Its current members include: Alex L\. Zhang Diane Tchuindjo Jacob X\. Li Matthew Yang Rikiya Takehi"),
            ("Souradip Chakraborty", "postdoc", r"Rikiya Takehi Souradip Chakraborty \(postdoc\)"),
            ("Maggie Lin", "masters", r"Its master’s and undergraduate research students include: Maggie Lin \(MEng\)"),
            ("Nathaniel Morgan", "undergraduate", r"Maggie Lin \(MEng\) Nathaniel Morgan \(UROP\)"),
            ("Ziyad Hassan", "masters", r"Ziyad Hassan \(MEng at MIT\)"),
            ("Noah Ziems", "other", r"Noah Ziems \(visiting PhD at MIT; PhD at Notre Dame\)")]
    return dict(
        status="pi",
        status_evidence=[ev(OASYS, r"Omar Khattab Assistant Professor MIT EECS & CSAIL Research Teaching Research Group Selected Work Email CV Scholar GitHub X / Twitter I.m an Assistant Professor at MIT EECS and a member of CSAIL, where I lead the MIT OASYS lab", "Omar Khattab")],
        students=[S(n, r, None if n in ("Ziyad Hassan", "Noah Ziems") else [2026, 2026], OASYS, rx,
                    note=("current OASYS lab member on the PI's homepage (observed 2026-10-22); degree level not stated" if r == "member" else
                          "former mentee listed on the PI's homepage" if n in ("Ziyad Hassan", "Noah Ziems") else None))
                  for n, r, rx in rows],
        notes="The homepage 'Research Group' section: 'I lead the MIT OASYS lab. Its current members include ...' (five members, degree level not stated, "
              "role 'member'), one postdoc, one MEng and one UROP student, plus former MIT mentees (Ziyad Hassan, MEng; Noah Ziems, visiting PhD). "
              "Former Stanford/ETH/Berkeley mentees are excluded (not at MIT). No DSpace thesis yet (joined MIT in 2025).")


def nigam():
    rows = [("Elam Day-Friedland", "phd", None, r"People Rachit Nigam Faculty Elam Day-Friedland PhD"),
            ("Carolyn Zech", "phd", None, r"Elam Day-Friedland PhD Carolyn Zech PhD"),
            ("Christine Guo", "phd", None, r"Carolyn Zech PhD Christine Guo PhD"),
            ("Liam Hanrahan", "undergraduate", None, r"Christine Guo PhD Liam Hanrahan Undergrad"),
            ("Armaan Gomes", "undergraduate", None, r"Liam Hanrahan Undergrad Armaan Gomes Undergrad"),
            ("Charles Reischer", "undergraduate", None, r"Armaan Gomes Undergrad Charles Reischer Undergrad"),
            ("Ayana Alemayehu", "masters", [2026, 2026], r"Alumni Ayana Alemayehu \(M\.Eng\. 2026\)")]
    return dict(
        status="pi",
        status_evidence=[ev(FLAME, r"People Rachit Nigam Faculty Elam Day-Friedland PhD", "Rachit Nigam")],
        students=[S(n, r, y or [2026, 2026], FLAME, rx) for n, r, y, rx in rows],
        appointment_notes=[appt("https://people.csail.mit.edu/rachit/", r"At MIT, I direct the Foundations of Languages and Machines \(FLAME\) lab", "FLAME")],
        notes="FLAME lab people list (live 2026-10-22). Started at MIT January 2026 (home-departments.json); no DSpace thesis yet.")


def jas_brooks():
    rows = [("MacKenzie Harnett", "postdoc"), ("Tai Le", "postdoc"), ("Peng Kuang", "postdoc"),
            ("Alejandro López-Rodríguez", "phd"), ("Riley Lawson", "phd"), ("Sol (Eunsol) Choi", "phd"), ("Young Lee", "phd"),
            ("Yuting Tang", "phd"), ("Gene S-H Kim", "phd"), ("Terry Kim", "masters")]
    lab = {"postdoc": "Postdoc", "phd": "PhD Student", "masters": "Master's Student"}
    import re
    return dict(
        status="pi",
        status_evidence=[ev(PEL, r"The Perceptual Engineering Lab is led by Assistant Professor Jas Brooks at MIT", "Jas Brooks")],
        students=[S(n, r, [2026, 2026], PEL, re.escape(n) + r" \(opens in a new tab\) " + re.escape(lab[r]),
                    note="Team list of the Perceptual Engineering Lab homepage (observed 2026-10-22)") for n, r in rows],
        appointment_notes=[appt("https://jasbrooks.com", r"Excited to join MIT EECS / CSAIL as an Assistant Professor in Fall 2026!", "MIT EECS"),
                           appt("https://jasbrooks.com", r"They received a Ph\.D\. \(2025\) and B\.S\. \(2016\) in Computer Science from the University of Chicago", "Ph.D.")],
        notes="Started Fall 2026; the lab homepage's Team list names 3 postdocs, 6 PhD students and 1 master's student (an external collaborator is excluded). "
              "Pre-2026 papers are UChicago work; the two MIT lab papers found are in the 2026 listing year.")


def gordon():
    rows = [("Hyemin (Helen) Bang", "phd", r'const students = \[ \{ name: "Hyemin \(Helen\) Bang", type: "phd"'),
            ("Andre Ye", "phd", r'name: "Andre Ye", type: "phd"'),
            ("Elinor Poole-Dayan", "phd", r'name: "Elinor Poole-Dayan", note: "Co.advised with Jacob Andreas and Michiel Bakker", type: "phd"'),
            ("Grace C. Kim", "phd", r'name: "Grace C\. Kim", type: "phd"'),
            ("Yi-Hao Peng", "postdoc", r'name: "Yi-Hao Peng", note: "Co.advised with Arvind Satyanarayan and Zana Bu.inca", type: "postdoc"')]
    pubs = [("W4415952342", "MoReBench", r'"title": "MoReBench: Evaluating Procedural and Pluralistic Moral Reasoning[^"]*", "authors": \[[^\]]*?"Mitchell L Gordon"'),
            ("W7155074569", "Navigating the Conceptual Multiverse", r'"title": "Navigating the Conceptual Multiverse", "authors": \[[^\]]*?"Mitchell L\. Gordon"'),
            ("W7155566055", "Alignment has a Fantasia Problem", r'"title": "Alignment has a Fantasia Problem", "authors": \[[^\]]*?"Mitchell Gordon"'),
            ("W4402581130", "DracoGPT", r'"title": "DracoGPT: Extracting Visualization Design Preferences from Large Language Models", "authors": \[[^\]]*?"Mitchell Gordon"')]
    return dict(
        status="pi",
        status_evidence=[ev("http://mgordon.me/", r"Mitchell L\. Gordon Assistant Professor of Computer Science, MIT EECS/CSAIL Research Scientist, OpenAI mlgordon@mit\.edu · 32-G718 CV · Google Scholar · Twitter PhD students Postdocs", "Mitchell Gordon")],
        students=[S(n, r, [2026, 2026], GORDON_JS, rx, note="students array of the PI's homepage data file (rendered under 'PhD students' / 'Postdocs'; observed 2026-10-22)") for n, r, rx in rows],
        identity=dict(
            dblp=["https://dblp.org/pid/144/5660"], orcid=["0000-0003-1008-2321"], openalex=["A5026198819"],
            evidence=[idev("openalex_author", oa_author("A5026198819"), oa_rx("A5026198819", "0000-0003-1008-2321", "Mitchell Gordon"), "Mitchell Gordon",
                           "OpenAlex author record; its ORCID is the PI's (the ORCID record names Mitchell Gordon and lists his website)")]
                     + [idev("own_publication_list_match", GORDON_JS, rx, "Gordon", f"OpenAlex {w} (author A5026198819) is '{t}' on the PI's own publication list") for w, t, rx in pubs]
                     + [idev("orcid_record", "https://orcid.org/0000-0003-1008-2321/public-record.json", r'"displayName":"Mitchell Gordon"', "Mitchell Gordon", "ORCID public record naming the PI"),
                        idev("dblp_person_page", WB + "20260215135006id_/https://dblp.org/pid/144/5660.html", r"dblp: Mitchell L\. Gordon", "Mitchell L. Gordon",
                             "DBLP person page (Wayback; dblp.org is bot-walled live). The pipeline's DBLP cache already has records for pid 144/5660.")]),
        appointment_notes=[appt(GORDON_JS, r'term: "Fall 2025", course: "6\.1040: Software Design", institution: "MIT EECS", role: "Instructor"', "MIT EECS")],
        notes="Started 2025-07. Papers were missing for lack of an identity anchor: OpenAlex A5026198819 (ORCID 0000-0003-1008-2321) holds his MIT works "
              "(MoReBench 2025, Navigating the Conceptual Multiverse 2026, Alignment has a Fantasia Problem 2026, A Scale for Value Alignment 2026). "
              "Byline variants: 'Mitchell L. Gordon', 'Gordon, Mitchell L', 'Mitchell Gordon'.")


def bucinca():
    pubs = [("W3159250634", r"To trust or to think: cognitive forcing functions can reduce overreliance on AI in AI-assisted decision-making Zana Buçinca"),
            ("W4409747746", r"Contrastive Explanations That Anticipate Human Misconceptions Can Improve Human Decision-Making Skills Zana Buçinca"),
            ("W7162035190", r"Offline Reinforcement Learning for Adaptive Support in AI-Assisted Decision-Making Zana Buçinca")]
    return dict(
        status="pi",
        status_evidence=[ev(GORDON_JS, r'name: "Yi-Hao Peng", note: "Co.advised with Arvind Satyanarayan and Zana Bu.inca", type: "postdoc"', "Zana Bucinca")],
        students=[S("Yi-Hao Peng", "postdoc", [2026, 2026], GORDON_JS, r'name: "Yi-Hao Peng", note: "Co.advised with Arvind Satyanarayan and Zana Bu.inca", type: "postdoc"',
                    note="co-advised postdoc, stated on Mitchell Gordon's homepage data file (co-advised with Arvind Satyanarayan and Zana Buçinca); "
                         "her own homepage lists no group")],
        identity=dict(
            dblp=[], orcid=["0000-0002-2644-6065"], openalex=["A5073269010"],
            evidence=[idev("openalex_author", oa_author("A5073269010"), oa_rx("A5073269010", "0000-0002-2644-6065", "Bucinca, Zana", "full_name"), "Zana Bucinca",
                           "OpenAlex author record (ORCID attached); its 2026 works list MIT ('Sloan and EECS, Massachusetts Institute of Technology')")]
                     + [idev("own_publication_list_match", "https://zbucinca.github.io/publications/", rx, "Zana Bucinca", f"OpenAlex {w} (author A5073269010) is on the PI's own publication list")
                        for w, rx in pubs]),
        appointment_notes=[appt("https://zbucinca.github.io/", r"I’m an Assistant Professor at MIT, with a shared appointment in the Sloan School of Management and the Department of Electrical Engineering and Computer Science", "MIT"),
                           appt("https://zbucinca.github.io/", r"I am unlikely to accept new PhD students for Fall 2027", "PhD students")],
        collection_person_id="mit_person_45aea7350ce2fd40",
        notes="Started Fall 2026 (Sloan IWER + EECS). Only one stated mentee: postdoc Yi-Hao Peng, co-advised with Mitchell Gordon's group and Arvind Satyanarayan; "
              "her own page names no students, so the student side is thin. OpenAlex A5073269010 (ORCID 0000-0002-2644-6065) is verified against her own list "
              "and has two 2026 MIT works. The collection also holds a second record 'Zana Buçinca' (mit_person_fde94e860ef3e3c6, HCI community member) that "
              "should be merged with mit_person_45aea7350ce2fd40.")


add("Kaiming He", **kaiming())
add("Andreea Bobu", **bobu())
add("Omar Khattab", **khattab())
add("Rachit Nigam", **nigam())
add("Jas Brooks", **jas_brooks())
add("Mitchell Gordon", **gordon())
add("Zana Bucinca", **bucinca())


# ---------------------------------------------------------------- not PIs in 2016-2026 (emeritus / departed / staff / deceased)
EECS2016 = WB + "20160104094659id_/http://www.eecs.mit.edu/people/faculty-advisors"


def rodney_brooks():
    return dict(
        status="not_pi_in_window",
        status_evidence=[ev("https://people.csail.mit.edu/brooks/", r"NOTE: Rodney Brooks is an emeritus professor at MIT\. That means that he is no longer on the regular faculty\. He no longer has a research group there, and he no longer has any students\.", "Rodney Brooks"),
                         ev("https://people.csail.mit.edu/brooks/phd%20students.html", r"Following are the people for whom Rodney Brooks served as thesis supervisor\.", "Rodney Brooks"),
                         ev(EECS2016, r"Rodney Brooks Panasonic Professor of Robotics, Emeritus", "Rodney Brooks")],
        appointment_notes=[appt("https://people.csail.mit.edu/brooks/", r"Rodney Brooks is the Panasonic Professor of Robotics \(emeritus\) at MIT", "Rodney Brooks")],
        notes="Emeritus before the window: the EECS faculty list of 2016-01 already says 'Panasonic Professor of Robotics, Emeritus'. His own 'Graduated PhDs' list "
              "ends with #27 in 2007, and his homepage states he no longer has a research group or students at MIT. DSpace has no 2016-2026 thesis with him as "
              "supervisor. Identity (only if ever needed): DBLP b/RodneyABrooks; OpenAlex A5113436962 holds his 2017-2026 essays and IEEE Spectrum columns.")


def saltzer():
    return dict(
        status="not_pi_in_window",
        status_evidence=[ev("https://web.mit.edu/saltzer/www/bio.html", r"In September, 1995, Professor Saltzer retired from the full-time faculty, continuing to teach part-time\. In 2005 he retired further and moved to Idaho", "Saltzer"),
                         ev("https://web.mit.edu/saltzer/www/theses.html", r"Theses supervised by Jerome H\. Saltzer as of June 2000", "Jerome H. Saltzer"),
                         ev("https://web.mit.edu/saltzer/www/home.html", r"Jerome H\. Saltzer Professor of Computer Science, Emeritus", "Jerome H. Saltzer")],
        notes="Retired from the full-time faculty in 1995 and fully in 2005; his own list of theses supervised stops in 2000; no DSpace thesis 2016-2026 "
              "names him as supervisor. His 2020-2021 papers are historical notes (MIT License, Kerberos origins).")


def corbato():
    return dict(
        status="not_pi_in_window",
        status_evidence=[ev("https://news.mit.edu/2019/mit-professor-emeritus-fernando-corby-corbato-computing-pioneer-dies-0715",
                            r"Fernando “Corby” Corbató, an MIT professor emeritus whose work in the 1960s on time-sharing systems broke important ground in democratizing the use of computers, died on Friday, July 12, at his home in Newburyport, Massachusetts\. He was 93\.", "Corbató")],
        notes="Professor emeritus long before 2016; died 12 July 2019 (MIT News). No DSpace thesis 2016-2026 names him. DBLP c/FernandoJCorbato exists, but OpenAlex's only "
              "2016+ MIT-affiliated work under his name (W7171420358, 2024, 'Adaptive Query Routing for High-Speed Distributed Data Systems') is posthumous and "
              "misattributed; it must not become a lab paper.")


def brewer():
    return dict(
        status="not_pi_in_window",
        status_evidence=[ev("https://www.w3.org/People/Brewer/", r"Between September 1997 and January 2023, Judy Brewer directed the Web Accessibility Initiative \(WAI\) at the World Wide Web Consortium \(W3C\)", "Judy Brewer"),
                         ev("https://www.w3.org/People/Brewer/", r"She was a Principal Research Scientist at MIT's Computer Science and Artificial Intelligence Laboratory \(CSAIL\) \. Judy", "Judy")],
        identity=dict(dblp=["https://dblp.org/pid/61/5798"], orcid=[], openalex=["A5055751908"], evidence=[]),
        notes="Research staff (W3C/WAI director hosted at CSAIL until January 2023), not a faculty PI: no thesis supervision in DSpace 2016-2026 (advisor search "
              "'Brewer' returned none) and no group with students. Identity is listed for completeness only (unverified beyond name + W3C/MIT affiliation "
              "on her 2018 and 2021 works).")


def jaffe():
    return dict(
        status="not_pi_in_window",
        status_evidence=[ev("https://www.w3.org/People/Jeff/", r"Dr\. Jeff Jaffe was Chief Executive Officer of the World Wide Web Consortium from March 2010 till November 2022\.", "Jaffe")],
        notes="Research staff: CEO of W3C (hosted at MIT) March 2010 - November 2022; W3C left MIT hosting in 2023. No DSpace thesis 2016-2026 names him "
              "(the only 'Jaffe' advisor hit is Robert Jaffe, Physics), no OpenAlex MIT works 2016+, no group with students.")


def leighton():
    return dict(
        status="not_pi_in_window",
        status_evidence=[ev("https://www.csail.mit.edu/person/tom-leighton", r"Tom Leighton is a Professor of Applied Mathematics and a member of the Computer Science and Artificial Intelligence Laboratory \(CSAIL\) at MIT \(currently on leave\)\. In 1998, he co-founded Akamai Technologies, where he is currently the CEO", "Tom Leighton"),
                         ev("https://en.wikipedia.org/wiki/F._Thomson_Leighton", r'Frank Thomson "Tom" Leighton \(born 1956\) is an American mathematician and computer scientist who is the CEO of Akamai Technologies', "Tom Leighton")],
        appointment_notes=[appt("https://www.csail.mit.edu/person/tom-leighton", r"During his time as CEO, Akamai’s revenue has more than doubled, growing from less than \$1\.4 billion in 2012", "CEO")],
        notes="On leave from MIT as Akamai CEO (CEO since 2013; the CSAIL page dates his CEO tenure from 2012 revenue). No DSpace thesis 2016-2026 names him as "
              "supervisor; OpenAlex has no 2016+ MIT-affiliated works under any of his byline forms ('Tom Leighton', 'F. Thomson Leighton'). "
              "The collection has a second record 'Thomson Leighton' (mit_person_a82e12fc33b868d6).")


def willsky():
    return dict(
        status="not_pi_in_window",
        status_evidence=[ev("https://willsky.lids.mit.edu/bio_short.htm", r"Alan S\. Willsky is the Edwin Sibley Webster Professor in the Dept\. of Electrical Engineering and Computer Science \(retired\) at MIT which he joined in 1973, and leads the Stochastic Systems Group\. through June 2014\.", "Alan S. Willsky"),
                         ev("https://willsky.lids.mit.edu/", r"ALAN S\. WILLSKY Edwin Sibley Webster Professor of Electrical Engineering \(Retired\)", "WILLSKY")],
        appointment_notes=[appt("https://willsky.lids.mit.edu/ssg/alumni.shtml", r"Johnson, Matthew PhD & SM 6/14 & 6/10", "Johnson, Matthew"),
                           appt("https://willsky.lids.mit.edu/ssg/alumni.shtml", r"Liu, Ying PhD & SM 6/14 & 6/10", "Liu, Ying")],
        identity=dict(dblp=["https://dblp.org/pid/48/6690"], orcid=[], openalex=["A5107833743"], evidence=[]),
        notes="Retired in June 2014 (led the Stochastic Systems Group 'through June 2014'). His group's alumni list ends with two PhDs of 6/14; DSpace has no thesis "
              "2016-2026 naming him. His 2016-2020 papers are with Systems & Technology Research (Woburn), not MIT; the only MIT-affiliated 2016 item is a journal "
              "rejoinder. OpenAlex A5107833743 is his author record (listed for completeness).")


add("Rodney Brooks", **rodney_brooks())
add("Jerome Saltzer", **saltzer())
add("F. J. Corbato", **corbato())
add("Judy Brewer", **brewer())
add("Jeffrey Jaffe", **jaffe())
add("Tom Leighton", **leighton())
add("Alan Willsky", **willsky())


# ---------------------------------------------------------------- DSpace@MIT thesis supervision (discover search captures)
import re as _re
import capstore as _cap
import evlib as _ev


def dspace_src(fragment):
    con = _cap.connect()
    rows = [u for (u,) in con.execute("SELECT url FROM captures WHERE url LIKE 'https://dspace.mit.edu/server/api/discover/%' AND status=200 ORDER BY id")]
    con.close()
    hit = [u for u in rows if fragment in u]
    if len(hit) != 1:
        raise KeyError(f"{len(hit)} DSpace captures match {fragment!r}")
    return hit[0]


def _role(degrees):
    d = " ".join(degrees)
    if _re.search(r"Ph\.\s?D|Sc\.\s?D", d):
        return "phd"
    if _re.search(r"S\.M\.|M\.\s?Eng|S\.M |Master", d):
        return "masters"
    if _re.search(r"S\.B\.|B\.S\.", d):
        return "undergraduate"
    return "other"


def _display(prefix):
    if "," in prefix:
        last, first = [x.strip() for x in prefix.split(",", 1)]
        return f"{first} {last}"
    return prefix


def dspace_rows(src, adv_rx, skip=(), quote_rx=None):
    """One student row per thesis in a DSpace discover capture whose dc.contributor.advisor matches adv_rx."""
    out = []
    for it in _ev.dspace_items(src):
        if not any(_re.search(adv_rx, a) for a in it["advisors"]) or not it["authors"]:
            continue
        a = it["authors"][0]
        prefix = _re.split(r"\(|\.\s|\. |\.$|,\s?(?:Ph|S\.M|M\.)", a)[0].strip().rstrip(",. ")
        if prefix in skip:
            continue
        role = _role(it["degree"])
        yr = int(it["date"][:4]) if it["date"][:4].isdigit() else None
        co = [x for x in it["advisors"] if not _re.search(adv_rx, x)]
        note = f"DSpace@MIT thesis {it['handle']} ({', '.join(d for d in it['degree'][:1])}, {it['date']}): '{it['title']}'"
        if co or _re.search(r" and ", " ".join(it["advisors"])):
            note += "; supervisors as listed: " + "; ".join(it["advisors"])
        out.append(_ev.dspace_student(src, prefix, quote_rx or adv_rx, role, yr, _display(prefix), note=note))
    return out


def adelson():
    q1 = dspace_src("Grimson+OR+Liskov")
    pubs = [("W2196697617", r"Visually indicated sounds</a > A Owens, P Isola, J McDermott, A Torralba, EH Adelson"),
            ("W2607241646", r"Shape-independent hardness estimation using deep learning and a gelsight tactile sensor</a > W Yuan, C Zhu, A Owens, MA Srinivasan, EH Adelson"),
            ("W2793598667", r"Gelslim: A high-resolution, compact, robust, and calibrated tactile-sensing finger</a > E Donlon, S Dong, M Liu, J Li, E Adelson"),
            ("W4389666848", r"GelSight Svelte: A Human Finger-shaped Single-camera Tactile Robot Finger with Large Sensing Coverage and Proprioceptive Sensing</a > J Zhao, EH Adelson"),
            ("W2614829919", r"Visual wetness perception based on image color statistics</a > M Sawayama, EH Adelson")]
    persci = WB + "20260616082728id_/https://persci.mit.edu/publications"
    return dict(
        status="pi",
        status_evidence=[_ev.ev(q1, r'"dc\.contributor\.advisor" : \[ \{ "value" : "Adelson, Edward H\."', "Adelson")],
        students=dspace_rows(q1, r"Adelson"),
        identity=dict(
            dblp=["https://dblp.org/pid/73/143"], orcid=[], openalex=["A5021989698"],
            variants=["Edward H. Adelson", "Edward Adelson", "Adelson, Edward H.", "E. H. Adelson", "EH Adelson"],
            evidence=[idev("openalex_author", oa_author("A5021989698"), oa_rx("A5021989698", None, "Edward H. Adelson"), "Edward H. Adelson",
                           "OpenAlex author record; last known institution MIT CSAIL; 56 MIT-affiliated 2016-2026 works in the school sweep, all under this id")]
                     + [idev("own_publication_list_match", persci, rx, "Adelson", f"OpenAlex {w} (author A5021989698) is on the Perceptual Science Group's 'Edward Adelson Publications' list (Wayback 2026-06)")
                        for w, rx in pubs]
                     + [idev("dblp_person_page", WB + "20260217155857id_/https://dblp.org/pid/73/143.html", r"dblp: Edward H\. Adelson", "Edward H. Adelson",
                             "DBLP person page (Wayback). The pipeline's DBLP cache already holds 33 records for pid 73/143.")]),
        appointment_notes=[],
        notes="Root cause of both gaps: the census name 'Ted Adelson' never matches his byline or thesis-supervisor form 'Edward H. Adelson' "
              "(the pipeline's nickname table has no ted->edward), so the 56 MIT-affiliated OpenAlex works (one author id) and all DSpace theses were missed. "
              "Add the variants above as aliases; with them the OpenAlex id and DBLP pid 73/143 anchor the papers. Students: 11 DSpace theses 2018-2025 "
              "with 'Edward H. Adelson' as supervisor (GelSight / tactile-sensing group). The persci.mit.edu people page is shared with Ruth Rosenholtz, so it is "
              "not used for advising.")


def arvind():
    q5 = dspace_src("Arvind+NOT+Satyanarayan")
    pubs_url = "https://csg.csail.mit.edu/Users/arvind/Pubs_public.htm"
    pubs = [("W2572583791 (BlueCache, 2016)", r"Shuotao Xu, Sungjin Lee, Sang-Woo Jun, Ming Liu, Jamey Hicks, Arvind, “BlueCache: A Scalable Distributed Flash-based Key-value Store"),
            ("W2884496840 (GraFBoost, 2018)", r"Sang-Woo Jun, Andy Wright, Sizhuo Zhang, Shuotao Xu, and Arvind, “GraFBoost: Using accelerated flash storage for external graph analytics"),
            ("W2803529289 (Constructing a Weak Memory Model, 2018)", r"Sizhuo Zhang, Muralidaran Vijayaraghavan, Andrew Wright, Mehdi Alipour , and Arvind, “Constructing a Weak Memory Model"),
            ("W2906372616 (MI6, 2018/2019)", r"Thomas Bourgeat , I\. Lebedev , A\. Wright, S\. Zhang, Arvind, and S\. Devadas , ``MI6: Secure Enclaves in a Speculative Out-of-Order Processor"),
            ("W3033189783 (The Essence of Bluespec, 2020)", r"Thomas Bourgeat , Clement Pit-Claudel, Adam Chipala , and Arvind, “The Essence of Bluespec")]
    return dict(
        status="pi",
        status_evidence=[_ev.ev(q5, r'"dc\.contributor\.advisor" : \[ \{ "value" : "Arvind\."', "Arvind"),
                         _ev.ev("https://csg.csail.mit.edu/pubs/people.html", r"People Faculty Arvind , Architecture/Synthesis, arvind@csail\.mit\.edu , Professor", "Arvind")],
        students=dspace_rows(q5, r"^Arvind\.?$|Arvind and |and Arvind\.?$", quote_rx=r'"value" : "(?:Arvind\.?|Arvind and [^"]*|[^"]* and Arvind\.?)"'),
        identity=dict(
            dblp=["https://dblp.org/pid/a/Arvind"], orcid=[], openalex=["A5060692552"],
            variants=["Arvind", "Arvind Mithal", "Arvind Arvind"],
            evidence=[idev("dblp_person_page", WB + "20260306113353id_/https://dblp.org/pid/a/Arvind.html",
                           r"Arvind Mithal '20 '10 '00 '90 '80 '70 Dagstuhl Trier by year by type > Home > Persons Person information affiliation: Massachusetts Institute of Technology \(MIT\), Cambridge, MA, USA",
                           "Arvind Mithal", "DBLP person page 'Arvind 0001' (pid a/Arvind; Wayback 2026-03-06) with the MIT affiliation"),
                      idev("openalex_author", oa_author("A5060692552"), oa_rx("A5060692552", None, "Arvind Arvind"), "Arvind",
                           "OpenAlex author record (display name 'Arvind Arvind'; byline 'Arvind'); 28 of its 2016-2026 works in the MIT sweep list MIT")]
                     + [idev("own_publication_list_match", pubs_url, rx, "Arvind", f"OpenAlex {w}, author A5060692552, is on Arvind's own publication list") for w, rx in pubs]),
        appointment_notes=[appt("https://news.mit.edu/2024/computer-science-professor-arvind-dies-0618",
                                r"Arvind Mithal, the Charles W\. and Jennifer C\. Johnson Professor in Computer Science and Engineering at MIT, head of the faculty of computer science in the Department of Electrical Engineering and Computer Science \(EECS\), and a pillar of the MIT community, died on June 17\.", "Arvind Mithal")],
        collection_person_id="mit_source_profile_a17b819b8c8ce3b96983",
        notes="Died 17 June 2024; led the Computation Structures Group with students throughout 2016-2024. Root causes: (1) no collection person and no DBLP pid "
              "in the census (DBLP is a/Arvind, 'Arvind 0001'); (2) the pipeline's advising matcher skips one-token supervisor names, and DSpace lists him "
              "as 'Arvind.' / 'Arvind', so all 20 theses were dropped; (3) OpenAlex shows him as 'Arvind Arvind' (A5060692552). The collection has two source "
              "records named 'Arvind' (mit_source_profile_a17b819b8c8ce3b96983, CSAIL/CSG; mit_source_profile_85cafc5f60346d601d96, EECS roster); the CSAIL one is "
              "proposed. A second OpenAlex record A5114637305 'Arvind Mithal' (ORCID 0000-0002-9737-2366, one 2024 MIT/MIT-IBM work on money-laundering subgraphs "
              "with his MEng student Muhua Xu) is very likely him but has too few works to verify by the 3-work rule; its ORCID record lists no affiliation.")


add("Ted Adelson", **adelson())
add("Arvind", **arvind())


# ---------------------------------------------------------------- papers-only gaps (students already found by the pipeline)
Q7 = None


def q7():
    return dspace_src("Terman+OR+Sipser")


def zero_q(fragment, name, name_rx):
    """Quote of a zero-result DSpace supervisor search: its query string through 'totalElements : 0'."""
    src = dspace_src(fragment)
    return _ev.ev(src, r'"query" : "[^"]*' + name_rx + r'[^"]*".{0,3000}?"totalElements" : 0', name)


def huang():
    hp = "https://czhuang.github.io/"
    pubs = [("W4300936792 / W2919624000 (Music Transformer, 2018/2019)", r"Music Transformer Cheng-Zhi Anna Huang , Ashish Vaswani"),
            ("W2962212541 (The Bach Doodle, 2019)", r"The Bach Doodle: Approachable Music Composition with Machine Learning at Scale Cheng-Zhi Anna Huang"),
            ("W2753868141 (Counterpoint by Convolution, 2017)", r"Coconet: Counterpoint by Convolution Cheng-Zhi Anna Huang"),
            ("W4287643030 (AI Song Contest, 2020)", r"AI Song Contest: Human-AI Co-Creation in Songwriting Cheng-Zhi Anna Huang"),
            ("W4220793291 (Expressive Communication, 2022)", r"Expressive Communication: A Common Framework for Evaluating Developments in Generative Models and Steering Interfaces Ryan Louie, Jesse Engel, Cheng-Zhi Anna Huang")]
    return dict(
        status="pi",
        status_evidence=[_ev.ev(q7(), r'"dc\.contributor\.advisor" : \[ \{ "value" : "Huang, Cheng-Zhi Anna"', "Cheng-Zhi Anna Huang")],
        students=dspace_rows(q7(), r"Huang, Cheng-Zhi Anna"),
        identity=dict(
            dblp=["https://dblp.org/pid/59/9006"], orcid=[], openalex=["A5007555810"],
            variants=["Cheng-Zhi Anna Huang", "Huang, Cheng-Zhi Anna", "Anna Huang"],
            evidence=[idev("openalex_author", oa_author("A5007555810"), oa_rx("A5007555810", "0009-0009-4194-0393", "Cheng-Zhi Anna Huang"), "Cheng-Zhi Anna Huang",
                           "OpenAlex author record holding her MIT 2026 works (Stemphonic, H2H Music Improv, Encypher, JazzSAMBA). CAUTION: the record is merged with "
                           "namesakes 'Chengzhi Huang' (Xidian, Xiamen, Chongqing) and carries an ORCID that is not hers; only MIT-affiliated works should be taken")]
                     + [idev("own_publication_list_match", hp, rx, "Cheng-Zhi Anna Huang", f"OpenAlex {w}, author A5007555810, is on her own homepage publication list") for w, rx in pubs]
                     + [idev("dblp_person_page", WB + "20260223183028id_/https://dblp.org/pid/59/9006.html", r"dblp: Cheng-Zhi Anna Huang", "Cheng-Zhi Anna Huang",
                             "DBLP person page (Wayback 2026-02-23); not in the pipeline's DBLP cache"),
                        idev("orcid_record", "https://orcid.org/0000-0002-8440-2378/public-record.json", r'"displayName":"Cheng-Zhi Anna Huang"', "Cheng-Zhi Anna Huang",
                             "ORCID 0000-0002-8440-2378 names her (and is the ORCID on OpenAlex A5127872917 and A5021136099), but the record lists no affiliation, "
                             "so it is not verified by the MIT rule and is not added to identity.orcid")]),
        appointment_notes=[appt(hp, r"In Fall 2024, I started a faculty position at Massachusetts Institute of Technology \(MIT\), with a shared position between Electrical Engineering and Computer Science \(EECS\) and Music and Theater Arts \(MTA\)", "MIT")],
        notes="Papers were missing for lack of an anchor (no DBLP pid in the census). OpenAlex A5007555810 is verified by 5 titles on her homepage; it carries her MIT "
              "2026 works. Two small OpenAlex records with her real ORCID (A5127872917: 'A Design Space for Live Music Agents', 'Agents in Concert', both MIT 2026; "
              "A5021136099: TISMIR editorial 2022, ReaLJam 2025, H2H and JazzSAMBA datasets 2026) are her too but cannot meet the 3-work rule on their own; "
              "adding ORCID 0000-0002-8440-2378 would pick them up once accepted. DBLP: 59/9006. Student side was already satisfied (MEng thesis Heidi Lei, 2026).")


def sussman():
    hp = "http://groups.csail.mit.edu/mac/users/gjs/"
    pubs = [("W3201851568 (SICP JavaScript Edition, 2022)", r"Structure and Interpretation of Computer Programs: JAVASCRIPT Edition , Harold Abelson and Gerald Jay Sussman"),
            ("W7213255759 (Software Design for Flexibility, 2021)", r"Chris Hanson and Gerald Jay Sussman; Software Design for Flexibility , MIT Press, 2021"),
            ("W2179987222 (Pluto chaos, 2018 reprint)", r".Numerical evidence that the motion of Pluto is chaotic,. Gerald Jay Sussman and Jack Wisdom"),
            ("W4240818533 / W4230600607 (Amorphous Computing, 2017/2018)", r".Amorphous Computing,. Harold Abelson, Don Allen, Daniel Coore, Chris Hanson, George Homsy, Thomas F\. Knight, Jr\., Radhika Nagpal, Erik Rauch, Gerald Jay Sussman")]
    return dict(
        status="pi",
        status_evidence=[_ev.ev(hp, r"2017: Bonnie Kit Ying Lam Energy Scalable Systems for 2D and 3D Low-Power Ultrasound Beamforming 2020: Leilani Hendrina Gilpin Anomaly Detection Through Explanations 2021: Michael A\. Specter", "Leilani Hendrina Gilpin"),
                         _ev.ev(q7(), r'"dc\.contributor\.advisor" : \[ \{ "value" : "Gerald Jay Sussman and Lalana Kagal\."', "Gerald Jay Sussman")],
        students=dspace_rows(q7(), r"Gerald"),
        identity=dict(
            dblp=[], orcid=[], openalex=["A5004435962"], variants=["Gerald Jay Sussman", "Gerald J. Sussman", "Sussman, Gerald Jay"],
            evidence=[idev("openalex_author", oa_author("A5004435962"), oa_rx("A5004435962", None, "Gerald Jay Sussman"), "Gerald Jay Sussman", "OpenAlex author record")]
                     + [idev("own_publication_list_match", hp, rx, "Gerald Jay Sussman", f"OpenAlex {w}, author A5004435962, matches a title on his homepage 'Selected Publications'") for w, rx in pubs]),
        notes="identity_unproven: his only MIT-affiliated sweep hits are two 'Amorphous Computing' encyclopedia entries (2017, 2018), which are not on DBLP "
              "s/GeraldJSussman. OpenAlex A5004435962 is verified by 4 titles on his homepage and anchors them. Caveat: these are reprints of 1990s/2000 work; his "
              "real 2016-2026 output (Software Design for Flexibility 2021, SICP JS 2022, SonicPACT 2020) carries no affiliation in OpenAlex, so it cannot place "
              "him at MIT; the lab may still end up with only reprints. Students: homepage PhD list (2017 Lam, 2020 Gilpin, 2021 Specter) and DSpace theses.")


def terman():
    return dict(
        status="pi",
        status_evidence=[_ev.ev(q7(), r'"dc\.contributor\.advisor" : \[ \{ "value" : "Christopher J\. Terman\."', "Christopher J. Terman")],
        students=dspace_rows(q7(), r"Terman"),
        identity=dict(dblp=[], orcid=[], openalex=["A5039186317"], variants=["Christopher J. Terman", "Chris Terman"],
                      evidence=[idev("openalex_author", oa_author("A5039186317"), oa_rx("A5039186317", None, "Christopher J\\. Terman"), "Christopher J. Terman",
                                     "OpenAlex author record (MIT CSAIL); it has no works dated 2016 or later")]),
        needs_after_research=["papers"],
        notes="Papers remain missing because none exist: Terman is a Senior Lecturer (emeritus by 2026) whose MIT role is teaching (6.004); OpenAlex has no "
              "2016+ works under any 'Terman' author record at MIT and the DBLP records (159/3667, plus split records 04/6988 'Chris Terman', 133/4488 "
              "'Chris J. Terman', 317/8554 'C. J. Terman') have nothing in the window. Students: 3 MEng theses 2016-2017 in DSpace.")


def sipser():
    return dict(
        status="pi",
        status_evidence=[_ev.ev(q7(), r'"dc\.contributor\.advisor" : \[ \{ "value" : "Michael Sipser\."', "Michael Sipser")],
        students=dspace_rows(q7(), r"Sipser"),
        identity=dict(dblp=["https://dblp.org/pid/s/MichaelSipser"], orcid=[], openalex=["A5112131750"],
                      evidence=[idev("dblp_person_page", WB + "20251020144855id_/https://dblp.org/pid/s/MichaelSipser.html", r"dblp: Michael Sipser", "Michael Sipser",
                                     "DBLP person page (Wayback 2025-10-20); its newest record is from 2013"),
                                idev("openalex_author", oa_author("A5112131750"), oa_rx("A5112131750", None, "Michael Sipser"), "Michael Sipser",
                                     "OpenAlex author record; its 2016+ items are Dean of Science annual reports (2016-2020) and a 2021 textbook edition")]),
        needs_after_research=["papers"],
        notes="Papers remain missing because there are none: Sipser was Dean of Science 2014-2020 and has no research publications dated 2016-2026 in DBLP "
              "(newest 2013) or OpenAlex (only Dean's reports and a textbook edition). Student: Zachary Remscrim, PhD 2016 (DSpace).")


def berners_lee():
    work = OA + "works/W2492893878"
    dblp = WB + "20260906003223id_/https://dblp.org/pid/b/TimBernersLee.html"
    dpubs = [("W2492893878 (2016)", r"Tim Berners-Lee : A Demonstration of the Solid Platform for Social Web Applications"),
             ("W2614951978 (2017)", r"Andrei Vlad Sambra , Tim Berners-Lee : Linked Data Notifications: A Resource-Centric Communication Proto"),
             ("W4415256665 (2025)", r"Tim Berners-Lee , Nigel Shadbolt : Libertas: Privacy-Preserving Collaborative Compu")]
    return dict(
        status="pi",
        status_evidence=[_ev.ev(q7(), r'"dc\.contributor\.advisor" : \[ \{ "value" : "Tim Berners-Lee\."', "Tim Berners-Lee")],
        students=dspace_rows(q7(), r"Berners"),
        identity=dict(
            dblp=["https://dblp.org/pid/b/TimBernersLee"], orcid=["0000-0003-1279-3709"], openalex=["A5025908133"],
            variants=["Tim Berners-Lee", "Tim Berners‐Lee", "Berners-Lee, Tim", "Timothy J Berners-Lee"],
            evidence=[idev("orcid_record", "https://orcid.org/0000-0003-1279-3709/public-record.json", r'"title":"Timothy J Berners-Lee \(0000-0003-1279-3709\) - ORCID', "Berners-Lee",
                           "ORCID record naming the PI; its employment list (affiliationGroups.json, sha256 d81fd935…) has a 'Massachusetts Institute of Technology' "
                           "entry asserted by MIT itself (sourceName MIT)"),
                      idev("openalex_work_authorship", work, r'"author":\{"id":"https://openalex\.org/A5025908133","display_name":"Tim Berners\\u2010Lee","orcid":"https://orcid\.org/0000-0003-1279-3709".{0,400}?"display_name":"Massachusetts Institute of Technology".{0,400}?"raw_author_name":"Tim Berners-Lee"', "Berners-Lee",
                           "OpenAlex W2492893878 (2016): authorship by A5025908133 with ORCID 0000-0003-1279-3709 at MIT")]
                     + [idev("dblp_person_page_match", dblp, rx, "Tim Berners-Lee", f"OpenAlex {w}, author A5025908133, is on DBLP's Tim Berners-Lee page (b/TimBernersLee, Wayback)") for w, rx in dpubs]),
        notes="no_identity_anchor: no DBLP pid in the census. OpenAlex A5025908133 carries his ORCID 0000-0003-1279-3709 (ORCID record: 'Timothy J Berners-Lee', "
              "MIT-asserted employment) and 8 MIT-affiliated works 2016-2023 (Solid demo, LDOW/DeSemWeb proceedings, LDN, dokieli, 'Linked Data - The Story So Far'). "
              "Several are workshop proceedings front matter; the research papers are the Solid demo (2016), LDN and dokieli (2017). DBLP: b/TimBernersLee. "
              "Student: Nicola Greco, S.M. 2017 (DSpace).")


def goemans():
    dblp = WB + "20260208064845id_/https://dblp.org/pid/g/MichelXGoemans.html"
    dpubs = [("W2107465809 (2017)", r"Satoru Fujishige , Michel X\. Goemans , Tobias Harks , Britta Peis , Rico Zenklusen : Matroids Are Immune to Braess' Paradox"),
             ("W2620262408 (2017)", r"Michel X\. Goemans , Swati Gupta , Patrick Jaillet : Discrete Newton's Algorithm for Parametric Submodular Function Minimization"),
             ("W2296493992 (2020)", r"Michel X\. Goemans , Thomas Rothvoss : Polynomiality for Bin Packing with a Constant Number of Item Types"),
             ("W4316652302 (2023)", r"Cole Franks , Tasuku Soma , Michel X\. Goemans : Shrunk subspaces via operator Sinkhorn iteration")]
    return dict(
        status="pi",
        status_evidence=[_ev.ev("https://math.mit.edu/~goemans/students.html", r"Michel Goemans - Students Michel Goemans Home Bio Publications Teaching Students People Current Ph\.D\. students: John Urschel", "Michel Goemans")],
        students=dspace_rows(q7(), r"Goemans"),
        identity=dict(
            dblp=["https://dblp.org/pid/g/MichelXGoemans"], orcid=[], openalex=["A5112864313"], variants=["Michel X. Goemans", "Michel Goemans", "Goemans, Michel X."],
            evidence=[idev("dblp_person_page", dblp, r"dblp: Michel X\. Goemans", "Michel X. Goemans",
                           "DBLP person page (Wayback 2026-02-08; affiliation 'MIT, Cambridge, USA'). The pipeline's DBLP cache already holds records for this pid."),
                      idev("openalex_author", oa_author("A5112864313"), oa_rx("A5112864313", None, "Michel X\\. Goemans"), "Michel X. Goemans",
                           "OpenAlex author record (last known institution MIT); all 12 MIT-affiliated 2016-2026 sweep hits are under this id")]
                     + [idev("dblp_person_page_match", dblp, rx, "Michel X. Goemans", f"OpenAlex {w}, author A5112864313, is on his DBLP page "
                             "(his own publication list at math.mit.edu/~goemans/publ.html stops before 2016)") for w, rx in dpubs]),
        collection_person_id="mit_person_7d7814c499ca9087",
        notes="no_person: the census row carries the CSAIL spelling 'Michael Goemans' and no DBLP pid, and was not bound to the collection person "
              "mit_person_7d7814c499ca9087 ('Michel Goemans', alias 'Michael Goemans'). DBLP g/MichelXGoemans and OpenAlex A5112864313 anchor 12 MIT works "
              "2017-2026. Home department is Mathematics (department head). Students: 4 PhD theses 2017-2021 in DSpace (Gupta co-supervised with Jaillet).")


add("Cheng Zhi (Anna) Huang", **huang())
add("Gerald Sussman", **sussman())
add("Christopher Terman", **terman())
add("Michael Sipser", **sipser())
add("Tim Berners-Lee", **berners_lee())
add("Michael Goemans", **goemans())


# ---------------------------------------------------------------- faculty / staff with no students in 2016-2026
def agarwal():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev(EECS2016, r"Anant Agarwal Professor of Electrical Engineering and Computer Science Director, Open Learning Enterprise at MIT", "Anant Agarwal"),
                         _ev.ev(WB + "20260311163629id_/https://www.eecs.mit.edu/role/faculty/", r"Anant Agarwal CEO, edX; Professor Post-Tenure \[CS and EE\]", "Anant Agarwal"),
                         _ev.ev("https://people.csail.mit.edu/agarwal/", r"Anant Agarwal is the CEO and Chairman of Grady", "Anant Agarwal"),
                         zero_q("Anant+AND+Agarwal", "Anant Agarwal", r"Anant AND Agarwal")],
        appointment_notes=[appt("https://people.csail.mit.edu/agarwal/", r"He was the Founder and CEO of edX , an online learning platform founded by Harvard and MIT\. After the acquisition of edX by 2U for \$800 million, he served as 2U's Chief Platform Officer\.", "edX")],
        notes="No group with students in 2016-2026: founder/CEO of edX (from 2012), then 2U Chief Platform Officer and now CEO of Grady; EECS lists him as "
              "'Professor Post-Tenure'. DSpace has no thesis 2016-2026 supervised by him (advisor search '(Anant AND Agarwal)' = 0; 'Agarwal' returns only "
              "Anuradha, Nikhil and Aditya Agarwal). The pipeline's one 'Agarwal' advising mention is Aditya Agarwal (namesake). His one MIT lab paper (TinyML "
              "education, 2022) is a multi-institution course paper. Judged not a PI in the window (full-time executive, no supervision found).")


def grimson():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev(EECS2016, r"W\. Eric L\. Grimson Bernard M\. Gordon Professor of Medical Engineering Department Head \(2005 - Feb\. 28, 2011\) MIT Chancellor", "Grimson"),
                         _ev.ev("https://www.eecs.mit.edu/people/w-eric-l-grimson/", r"Chancellor for Academic Advancement; Interim Vice President for Open Learning; Bernard M\. Gordon Professor in Medical Engineering; Professor of Computer Science and Engineering, \[CS and AI\+D\] egrimson@mit\.edu", "egrimson")],
        notes="Senior administrator throughout the window (MIT Chancellor, then Chancellor for Academic Advancement from 2015, now also Interim VP for Open Learning). "
              "DSpace has no thesis 2016-2026 with 'Grimson' as supervisor (combined advisor search, sha256 b25a3053…: only Adelson theses and one Robert Jaffe "
              "thesis). His one 2016 lab paper is a multi-author 3D Slicer community paper. Judged not a PI in the window (no supervision found).")


def liskov():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev("https://www.csail.mit.edu/research/programming-methodology-group", r"Last updated Jul 19 '17 Research Areas Programming Languages & Software Engineering Impact Areas Big Data Related Links Website Members Barbara Liskov MIT CSAIL", "Barbara Liskov"),
                         _ev.ev(WB + "20241012004455id_/https://pmg.csail.mit.edu/", r"Current Members Barbara Liskov Dorothy Curtis Liuba Shrira Recent PhD Alumni Winnie Cheng James Cowling Dan Ports David Schultz Ben Vandiver", "Barbara Liskov"),
                         _ev.ev(WB + "20260311163629id_/https://www.eecs.mit.edu/role/faculty/", r"Barbara Liskov Institute Professor \(post tenure\)", "Barbara Liskov")],
        notes="No students in 2016-2026: the CSAIL group page lists her as the only member, the PMG site (last updated 2012) lists only staff and alumni, and "
              "DSpace has no thesis 2016-2026 with 'Liskov' as supervisor (two separate advisor searches). Her 2016-2022 papers are collaborations with Harvard "
              "(Kohler group), Brown (Herlihy) and Liuba Shrira. Now 'Institute Professor (post tenure)'. Judged not a PI in the window.")


def lampson():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev(EECS2016, r"Butler Lampson Adjunct Professor of Computer Science and Engineering blampson@microsoft\.com", "Butler Lampson"),
                         _ev.ev("https://www.eecs.mit.edu/people/butler-lampson/", r"Butler Lampson People Faculty Faculty AI\+D Faculty CS Faculty EE Faculty Emeritus Lecturers Leadership Staff Instructors Adjunct Professor of CS and Engineering, \(Emeritus\) \[CS\] blampson@microsoft\.com", "Butler Lampson")],
        notes="Adjunct professor whose employer is Microsoft Research (Technical Fellow); emeritus adjunct by 2026. DSpace has no thesis 2016-2026 with 'Lampson' as "
              "supervisor (two advisor searches). His one MIT lab paper (Science 2020, 'There's plenty of room at the Top') is a faculty collaboration. "
              "Judged not a PI in the window.")


def seneff():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev("https://people.csail.mit.edu/seneff/", r"Stephanie Seneff is a Senior Research Scientist at the MIT Computer Science and Artificial Intelligence Laboratory", "Stephanie Seneff"),
                         _ev.ev("https://www.csail.mit.edu/research/toxic-environmental-chemicals-and-human-diseases", r"Last updated Jan 31 '18 Impact Areas Health Care Members Stephanie Seneff Publications", "Stephanie Seneff")],
        notes="Research staff (Senior Research Scientist) who supervised nobody in 2016-2026: her CSAIL project page lists her as its only member, and DSpace has no "
              "thesis 2016-2026 with 'Seneff' as supervisor (two advisor searches); her homepage's 'supervised numerous Master's and PhD theses' refers to her "
              "earlier spoken-language work. Her 2016-2026 papers are on nutrition/toxicology with outside co-authors.")


def moses():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev("https://news.mit.edu/2022/joel-moses-institute-professor-emeritus-dies-0531", r"Institute Professor Emeritus Joel Moses PhD ’67, an innovative computer scientist and dedicated teacher who held multiple leadership positions at MIT, died on May 29 after a long battle with Alzheimer’s and Parkinson’s diseases", "Joel Moses"),
                         _ev.ev(WB + "20220416110120id_/https://www.eecs.mit.edu/role/emeritus/", r"Joel Moses Institute Professor \(Emeritus\), \[AI&D\]", "Joel Moses"),
                         zero_q("Anant+AND+Agarwal", "Joel Moses", r"Joel AND Moses")],
        notes="No students in 2016-2026: DSpace advisor search '(Joel AND Moses)' returned no thesis 2016-2026 (the pipeline's 'Moses' advising mentions are "
              "William S. Moses, a student of Leiserson). His 2016-2017 papers are with his former student David Broniatowski (already GWU faculty). Listed as an "
              "active Institute Professor in January 2016, emeritus by 2022, died 29 May 2022 after a long illness. Judged not a PI in the window.")


def meyer():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev("https://people.csail.mit.edu/meyer/resume.html", r"Albert R\. Meyer Curriculum Vitae \(October, 2020\) Title: Emeritus Professor of Computer Science \(retired 2018\)", "Albert R. Meyer"),
                         zero_q("Anant+AND+Agarwal", "Albert Meyer", r"Albert AND Meyer"),
                         _ev.ev(WB + "20180405185941id_/https://www.csail.mit.edu/people?person%5B0%5D=role%3A299", r"Albert R\. Meyer Professor Programming languages, theory, complexity, online education", "Albert R. Meyer")],
        notes="Retired 2018 (emeritus from 2019). In 2016-2018 his role was teaching (6.042, Undergraduate Officer; CV research interest 'Active and Distance "
              "Learning'); DSpace has no thesis 2016-2026 with him as supervisor and he has no 2016+ research papers (OpenAlex A5104063086 has only a 2018 "
              "repost of an old CMU report; DBLP m/ARMeyer nothing after 2014). Judged not a PI in the window.")


def ward():
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev(EECS2016, r"Stephen Ward Professor of Computer Science and Engineering", "Stephen Ward"),
                         _ev.ev(WB + "20220416110120id_/https://www.eecs.mit.edu/role/emeritus/", r"Stephen Ward Professor of CS and Engineering \(Emeritus\)", "Stephen Ward"),
                         zero_q("Ward+AND", "Steve Ward", r"Ward AND \(Stephen OR Steve\)")],
        identity=dict(dblp=["https://dblp.org/pid/08/3963"], orcid=[], openalex=[], variants=["Stephen A. Ward", "Stephen Ward"],
                      evidence=[idev("dblp_person_page", WB + "20240416134054id_/https://dblp.org/pid/08/3963.html", r"dblp: Stephen A\. Ward", "Stephen A. Ward",
                                     "DBLP person page (Wayback 2024-04-16): newest record 2014")]),
        notes="No students and no papers in 2016-2026: DSpace advisor search '(Ward AND (Stephen OR Steve))' returned no thesis 2016-2026 (the 'Ward' advising "
              "mentions are James, Bryan, Paul and Collin Ward); DBLP 08/3963 'Stephen A. Ward' ends in 2014; OpenAlex has no MIT works under his name; his "
              "people.csail page is a bare directory listing. Active professor in the 2016 listing, emeritus by 2022. Note the byline form 'Stephen A. Ward' "
              "would not match the census name 'Steve Ward' (nickname table maps steve->steven). Judged not a PI in the window.")


def long_():
    dblp = WB + "20240430064519id_/https://dblp.org/pid/22/4747.html"
    return dict(
        status="not_pi_in_window",
        status_evidence=[_ev.ev("http://groups.csail.mit.edu/medg/people/wjl/", r"Bill Long Bill Long email: wjl@mit\.edu Phone: 617-253-3508 Fax: 617-258-8682 Mail: William J\. Long MIT CSAIL 32 Vassar St\. Room 256 Cambridge, MA 02139 I am a Principal Research Scientist in the Clinical Decision Making Group", "Bill Long"),
                         _ev.ev(WB + "20180405185941id_/https://www.csail.mit.edu/people?person%5B0%5D=role%3A299", r"Bill Long Research Affiliate Machine learning, healthcare, artificial intelligence", "Bill Long"),
                         zero_q("Long+AND", "Bill Long", r"Long AND \(William OR Bill\)")],
        identity=dict(dblp=["https://dblp.org/pid/22/4747"], orcid=[], openalex=[], variants=["William J. Long", "William Long"],
                      evidence=[idev("dblp_person_page_match", dblp, r"Yang Dai , Sharukh Lokhandwala , William J\. Long , Roger G\. Mark , Li-Wei H\. Lehman : Phenotyping hypotensive patients in critical care using hospital discharge summaries\. BHI 2017", "William J. Long",
                                     "DBLP 'William J. Long' (22/4747) lists the two 2017 MIT (IMES) papers found by name in the sweep (W2607448700, W2606201306); "
                                     "OpenAlex gives these authorships no author id, so only the DBLP pid can anchor them")]),
        notes="Research staff who supervised nobody: listed as Research Affiliate (2018) and Principal Research Scientist (2021) in the Clinical Decision-Making "
              "Group; DSpace advisor search '(Long AND (William OR Bill))' found no thesis 2016-2026; his group page dates from 2003. He did co-author two 2017 "
              "MIT papers (BHI 2017, with Li-wei Lehman's group), anchored by DBLP 22/4747 if ever needed.")


add("Anant Agarwal", **agarwal())
add("W. Eric L Grimson", **grimson())
add("Barbara Liskov", **liskov())
add("Butler Lampson", **lampson())
add("Stephanie Seneff", **seneff())
add("Joel Moses", **moses())
add("Albert R. Meyer", **meyer())
add("Steve Ward", **ward())
add("Bill Long", **long_())


# ---------------------------------------------------------------- per-row status basis, remaining needs and suggested pipeline actions
EXTRA = {
    "Kaiming He": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["accept researched students (homepage 'Research Group', Wayback)"]),
    "Andreea Bobu": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["accept researched students (CLEAR lab people page)"]),
    "Omar Khattab": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["accept researched students (homepage 'Research Group')"]),
    "Rachit Nigam": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["accept researched students (FLAME lab page)"]),
    "Jas Brooks": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["accept researched students (Perceptual Engineering Lab team list)"]),
    "Mitchell Gordon": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["accept researched students", "add OpenAlex A5026198819, ORCID 0000-0003-1008-2321, DBLP 144/5660"]),
    "Zana Bucinca": dict(status_basis="students_found (one co-advised postdoc)", needs_after_research=[], pipeline_actions=["accept researched postdoc", "add OpenAlex A5073269010, ORCID 0000-0002-2644-6065", "merge duplicate collection person mit_person_fde94e860ef3e3c6"]),
    "Ted Adelson": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["ADD CENSUS ALIASES 'Edward H. Adelson', 'Edward Adelson' (gap-evidence identity.variants are not read by pi_hierarchy.py; without them no sweep hit or thesis matches 'Ted Adelson')", "add OpenAlex A5021989698 and DBLP 73/143", "accept researched students (DSpace)"]),
    "Arvind": dict(status_basis="students_found (deceased 2024-06-17)", needs_after_research=[], pipeline_actions=["bind collection person mit_source_profile_a17b819b8c8ce3b96983", "add DBLP a/Arvind and OpenAlex A5060692552", "accept researched students (DSpace; the advising matcher drops one-token supervisor names such as 'Arvind.')"]),
    "Cheng Zhi (Anna) Huang": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["add OpenAlex A5007555810 (MIT-affiliated works only; merged profile)", "consider ORCID 0000-0002-8440-2378 (names her; no affiliation on record)"]),
    "Gerald Sussman": dict(status_basis="students_found", needs_after_research=["papers (possibly: only encyclopedia reprints carry MIT affiliation)"], pipeline_actions=["add OpenAlex A5004435962"]),
    "Christopher Terman": dict(status_basis="students_found", needs_after_research=["papers (none exist 2016-2026)"], pipeline_actions=[]),
    "Michael Sipser": dict(status_basis="students_found", needs_after_research=["papers (none exist 2016-2026)"], pipeline_actions=["optional: DBLP s/MichaelSipser"]),
    "Tim Berners-Lee": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["add OpenAlex A5025908133, ORCID 0000-0003-1279-3709, DBLP b/TimBernersLee"]),
    "Michael Goemans": dict(status_basis="students_found", needs_after_research=[], pipeline_actions=["bind collection person mit_person_7d7814c499ca9087", "add DBLP g/MichelXGoemans and OpenAlex A5112864313"]),
    "Rodney Brooks": dict(status_basis="emeritus_before_2016", needs_after_research=[], pipeline_actions=["exclude"]),
    "Jerome Saltzer": dict(status_basis="emeritus_before_2016", needs_after_research=[], pipeline_actions=["exclude"]),
    "Alan Willsky": dict(status_basis="emeritus_before_2016 (retired June 2014)", needs_after_research=[], pipeline_actions=["exclude"]),
    "F. J. Corbato": dict(status_basis="deceased_2019_emeritus_long_before", needs_after_research=[], pipeline_actions=["exclude", "never accept OpenAlex W7171420358 (posthumous misattribution)"]),
    "Tom Leighton": dict(status_basis="on_leave_before_2016 (Akamai CEO)", needs_after_research=[], pipeline_actions=["exclude"]),
    "Judy Brewer": dict(status_basis="research_staff_no_supervision (left 2023)", needs_after_research=[], pipeline_actions=["exclude"]),
    "Jeffrey Jaffe": dict(status_basis="research_staff_no_supervision (left 2022)", needs_after_research=[], pipeline_actions=["exclude"]),
    "Stephanie Seneff": dict(status_basis="research_staff_no_supervision", needs_after_research=[], pipeline_actions=["exclude"]),
    "Bill Long": dict(status_basis="research_staff_no_supervision", needs_after_research=[], pipeline_actions=["exclude"]),
    "Anant Agarwal": dict(status_basis="no_supervision_found_in_window (judgement: full-time edX/2U/Grady executive)", needs_after_research=[], pipeline_actions=["exclude (owner may prefer to keep and mark as no-group)"]),
    "W. Eric L Grimson": dict(status_basis="no_supervision_found_in_window (judgement: senior administrator)", needs_after_research=[], pipeline_actions=["exclude (owner may prefer to keep and mark as no-group)"]),
    "Barbara Liskov": dict(status_basis="no_supervision_found_in_window (judgement)", needs_after_research=[], pipeline_actions=["exclude (owner may prefer to keep and mark as no-group)"]),
    "Butler Lampson": dict(status_basis="no_supervision_found_in_window (adjunct; Microsoft)", needs_after_research=[], pipeline_actions=["exclude"]),
    "Joel Moses": dict(status_basis="no_supervision_found_in_window (judgement; emeritus by 2022, died 2022)", needs_after_research=[], pipeline_actions=["exclude"]),
    "Albert R. Meyer": dict(status_basis="no_supervision_found_in_window (judgement; retired 2018)", needs_after_research=[], pipeline_actions=["exclude"]),
    "Steve Ward": dict(status_basis="no_supervision_found_in_window (judgement; emeritus by 2022)", needs_after_research=[], pipeline_actions=["exclude"]),
}
