"""Researched decisions for the Princeton gap PIs (hierarchy/princeton/gap-input.json). Every evidence item is resolved
against hierarchy/princeton/gap-captures.sqlite by evlib (quote checked at build time). Build: build.py princeton
"""
from evlib import q, rx, window, student, oa_verify, oa_author_quote, dedupe_students, oai_students  # noqa: F401

S = "princeton"
ROWS = []


def row(pi, status, status_evidence=(), students=(), dblp=(), orcid=(), openalex=(), identity_evidence=(),
        collection_person_id=None, appointment_notes=(), notes=None, openalex_candidates=()):
    idn = dict(dblp=list(dblp), orcid=list(orcid), openalex=list(openalex), evidence=list(identity_evidence))
    if openalex_candidates:
        idn["openalex_candidates"] = list(openalex_candidates)
    ROWS.append(dict(pi=pi, status=status, status_evidence=list(status_evidence), students=dedupe_students(list(students)),
                     identity=idn, collection_person_id=collection_person_id, appointment_notes=list(appointment_notes), notes=notes))


def ev(kind, item, note=None):
    d = dict(kind=kind, **item)
    if note:
        d["note"] = note
    return d


# ---------------------------------------------------------------- Abhishek Bhattacharjee
NEWS_AB = "https://www.cs.princeton.edu/news/abhishek-bhattacharjee-expert-brain-computer-interfaces-joins-princeton"
HOME_AB = "https://web.archive.org/web/20260113015541id_/https://www.cs.yale.edu/homes/abhishek/"
DBLP_AB = "https://web.archive.org/web/20260208111412id_/https://dblp.org/pid/78/4478.html"
row("Abhishek Bhattacharjee", "pi",
    status_evidence=[q(S, "https://www.cs.princeton.edu/people/profile/abhattac",
                       "Abhishek Bhattacharjee is a Professor of Computer Science at Princeton University.")],
    dblp=["https://dblp.org/pid/78/4478"],
    openalex=["A5019487275", "A5122207823"],
    identity_evidence=[
        ev("dblp_person_page", q(S, DBLP_AB, "Abhishek Bhattacharjee ORCID ID conflict found in this bibliography 0000-0003-2742-2679 "
                                 "0000-0002-9664-1050 visit author's page @ yale.edu"),
           "Wayback capture of the DBLP person page (dblp.org HTML is bot-walled); it links the Yale homepage. pid 78/4478 is also the "
           "pid carried for this name in the local DBLP family caches."),
        ev("own_homepage", q(S, HOME_AB, "Abhishek Bhattacharjee Abhishek Bhattacharjee A. Bartlett Giamatti Professor of Computer Science Yale University"),
           "The PI's own homepage (Wayback 2026-01-13), used as the publication list below."),
        *oa_verify(S, "A5019487275", HOME_AB, "Bhattacharjee", n=3),
        oa_author_quote(S, "A5019487275", "Abhishek Bhattacharjee"),
        oa_author_quote(S, "A5122207823", "Abhishek Bhattacharjee"),
    ],
    collection_person_id="member_cs_7ac24090f8154b3e9900",
    appointment_notes=[q(S, NEWS_AB, "Abhishek Bhattacharjee, an expert in computer architecture, operating systems and neurotechnology, "
                                     "joined Princeton as a professor of computer science on July 1. Bhattacharjee was most recently the "
                                     "A. Bartlett Giamatti Professor of Computer Science at Yale University, where he taught from 2019 to 2026.")],
    notes="Joined Princeton 2026-07-01 from Yale (news 2026-09-16). His OpenAlex ids (A5019487275 to 2025; split id A5122207823 for "
          "2026, same ORCID 0000-0003-2742-2679, both already in reviewedOpenAlex) carry no Princeton-affiliated work dated after "
          "2026-07-01: his three 2026 works are Yale-affiliated. The 88 Princeton-affiliated name hits belong to the namesake "
          "A. Bhattacharjee = Amitava Bhattacharjee (A5077408069, PPPL plasma physics). Papers are genuinely absent so far, not a "
          "matching failure. ORCID 0000-0003-2742-2679 not listed as verified: his page does not link it and the ORCID record "
          "has no employment (DBLP also flags an ORCID conflict).")


# DataSpace OAI sets (dim): doctoral dissertations, senior theses, master's theses
ORFE_PHD, ORFE_SR, ORFE_MS = "col_88435_dsp012r36tx551", "col_88435_dsp011r66j119j", "col_88435_dsp01qv33s0915"
EE_PHD, ECE_SR, ECE_MS = "col_88435_dsp01rf55z771t", "col_88435_dsp0100000007x", "col_88435_dsp01hq37vr909"
ARCH_PHD, ARCH_SR = "col_88435_dsp01f4752g74r", "col_88435_dsp01x346d4232"
FAC_LIVE = "https://www.cs.princeton.edu/people/faculty"
FAC_2019 = "https://web.archive.org/web/20190317002522id_/https://www.cs.princeton.edu/people/faculty"

# ---------------------------------------------------------------- Arash Adel
SOA_AA = "https://web.archive.org/web/20231216155920id_/https://soa.princeton.edu/content/arash-adel"
row("Arash Adel", "pi",
    status_evidence=[q(S, SOA_AA, "Arash Adel Assistant Professor, Architecture Director, ADR Laboratory"),
                     q(S, SOA_AA, "Dr. Arash Adel is an Assistant Professor at the School of Architecture at Princeton University. "
                                  "He is the founder and director of ADR Laboratory .")],
    collection_person_id="member_cs_structure_231585c792dcabe0c9c1",
    notes="Directs ADR Laboratory at the School of Architecture since 2023, but no source states an advisee. The lab site his SoA "
          "profile links (adeldesignresearch.org) is now a parked domain; its only Wayback captures (2021-2022) are the "
          "Michigan-era front page with no people page. soa.princeton.edu is Cloudflare-blocked live and its captured PhD and "
          "researcher rosters carry no adviser field. DataSpace OAI (Architecture dissertations and Architecture School senior "
          "theses, harvested 2026-10-22) has no record advised by Adel. Princeton-affiliated co-authors on his 2024-2026 papers "
          "(Salma Mozaffari, Daniel Ruan, Zhengyi Chen, Roman Ibrahimov, Jutang Gao) are likely lab members, and Jutang Gao is "
          "on the SoA PhD roster (2026-01), but no page states the relation. A web search finds only job postings for the "
          "renamed Adel Research Group (ARG) and no roster of its members. Students are still missing.")

# ---------------------------------------------------------------- Ewin Tang
PROF_ET = "https://www.cs.princeton.edu/people/profile/xo3179"
DBLP_ET = "https://web.archive.org/web/20260214023534id_/https://dblp.org/pid/223/2983.html"
row("Ewin Tang", "not_pi_in_window",
    status_evidence=[q(S, PROF_ET, "Ewin Tang works on quantum computing and theoretical computer science, with a focus on designing "
                                   "algorithms for learning and preparing quantum systems. She joined the Princeton faculty in "
                                   "September 2026, affiliated with the Princeton Quantum Initiative."),
                     q(S, "https://ewintang.com/", "Ewin Tang Ewin Tang 🗒️ about me I am an assistant professor doing theory at "
                                                  "Princeton, affiliated with the computer science department and the Princeton "
                                                  "Quantum Initiative .")],
    dblp=["https://dblp.org/pid/223/2983"],
    openalex=["A5020583189"],
    identity_evidence=[
        ev("dblp_person_page", q(S, DBLP_ET, "Ewin Tang ORCID 0000-0002-7451-9687 visit author's page @ ewintang.com"),
           "Wayback capture of the DBLP person page; it links her homepage."),
        *oa_verify(S, "A5020583189", "https://ewintang.com/", "Tang", n=3),
        oa_author_quote(S, "A5020583189", "Ewin Tang"),
    ],
    collection_person_id="member_cs_structure_47b52baa0d58bc3e7b37",
    appointment_notes=[q(S, PROF_ET, "Ewin Tang works on quantum computing and theoretical computer science, with a focus on designing "
                                     "algorithms for learning and preparing quantum systems. She joined the Princeton faculty in "
                                     "September 2026, affiliated with the Princeton Quantum Initiative. Prior to this, she was a Miller "
                                     "postdoctoral fellow at UC Berkeley.")],
    notes="Judgment call: a new assistant professor (started September 2026) with no advisee yet. The full CS graduate roster "
          "(253 students, fetched 2026-10-22) names no student advised by her, and her homepage lists no group. This is the "
          "'incoming hire' case: she becomes a pi once an advisee is stated. Identity: OpenAlex A5020583189 is verified against "
          "her homepage. Its Princeton-affiliated work 'Unitary complexity in polynomial space' (2026-10-02) falls after the "
          "September 2026 start, so the appointment note resolves the year-only '2026' boundary that blocked it. ORCID "
          "0000-0002-7451-9687 (on DBLP and the OpenAlex record) is not listed: her page does not link it and the ORCID record "
          "has no employment.")

# ---------------------------------------------------------------- Jianqing Fan
FAN = "https://web.archive.org/web/20260314090851id_/https://fan.princeton.edu/students"
fan_page = []
for nm, y in [("Yuheng Zheng", 2025), ("Jikai Hou", 2025), ("Yihong Gu", 2025), ("Cheng Gao", 2024), ("Yuling Yan", 2023),
              ("Mengxin Yu", 2023), ("Bingyan Wang", 2023), ("Pierre Bayle", 2023), ("Igor Silin", 2022), ("Francesca Tang", 2022),
              ("Yongyi Guo", 2022), ("Daniel Gitelman", 2022), ("Zhuoran Yang", 2022), ("Lirong Xue", 2021), ("Yifeng Zhou", 2021),
              ("Wenyan Gong", 2020), ("Cong Ma", 2020), ("Kaizheng Wang", 2020), ("Thomas Patrick Pumir", 2020),
              ("Yiqiao (Joe) Zhong", 2019), ("Carson Eisenach", 2019), ("Koushiki Bose", 2018), ("Junwei Lu", 2018),
              ("Ziwei Zhu", 2018), ("Yuyan Wang", 2016), ("Weichen Wang", 2016)]:
    fan_page.append(student(S, FAN, nm.replace("(Joe) ", ""), "phd", [y, y], needle=nm, before=0, after=170,
                            note="Listed under 'Ph.D. Theses Supervised' on the PI's own Students page (Wayback 2026-03-14)."))
for nm in ["Jinhang Chai", "Jiawei Ge", "Shangge Tang", "Xiaonan Zhu", "Yihan He", "Li Ximing", "Qishuo Yin"]:
    fan_page.append(student(S, FAN, nm, "phd", [2026, 2026], heading=r"Current Students & Postdoctoral Fellows", before=0, after=20,
                            note="Current Ph.D. student on the PI's own Students page (Wayback 2026-03-14)."))
fan_page.append(student(S, FAN, "Hyukjun Kwon", "postdoc", [2026, 2026], heading=r"Current Students & Postdoctoral Fellows", before=0, after=20,
                        note="Current postdoctoral fellow on the PI's own Students page (Wayback 2026-03-14)."))
for nm, a, b in [("Soham Jana", 2022, 2024), ("Sohom Bhattacharya", 2022, 2023), ("Debarghya Mukherjee", 2022, 2023),
                 ("Zhipeng Lou", 2020, 2023), ("Alexander Giessing", 2018, 2021), ("Yang Zhou", 2019, 2021), ("Yi Chen", 2018, 2019),
                 ("Bai Jiang", 2017, 2019), ("Krishna Balasubramanian", 2017, 2018), ("Haolei Weng", 2017, 2018),
                 ("Qiang Sun", 2015, 2017), ("Wenxin Zhou", 2015, 2017), ("Donggyu Kim", 2016, 2017), ("Yuan Ke", 2015, 2017),
                 ("Xiaolin Yang", 2015, 2017), ("Dong Wang", 2016, 2017), ("Heather Battey", 2014, 2016)]:
    fan_page.append(student(S, FAN, nm, "postdoc", [a, b], needle=f"{nm} ({a % 100:02d}-{b % 100:02d})", before=0, after=60,
                            note="Listed under 'Postdoctoral Fellows Supervised' on the PI's own Students page (Wayback 2026-03-14)."))
for nm, y in [("Byron Vickors", 2017), ("Tiangge Huang", 2019), ("Henry Guanghong Fu", 2020)]:
    fan_page.append(student(S, FAN, nm, "masters", [y, y], before=0, after=200,
                            note="Listed under 'Master Theses Supervised' on the PI's own Students page (Wayback 2026-03-14)."))
for nm in ["Harrison Witt", "Kadem Kram", "Stephen Jiang"]:
    fan_page.append(student(S, FAN, nm, "undergraduate", [2025, 2025], heading=r"Senior Theses Supervised 2025", before=0, after=40,
                            note="Listed under 'Senior Theses Supervised 2025' on the PI's own Students page (Wayback 2026-03-14)."))
row("Jianqing Fan", "pi",
    students=oai_students(["Fan, Jianqing", "Fan, Jian Qing"], {ORFE_PHD: "phd", ORFE_SR: "undergraduate", ORFE_MS: "masters"}) + fan_page,
    collection_person_id="member_cs_structure_41b45a4fd8f9f783e0c1",
    notes="Students were absent because ORFE theses never reached the collection's advising records. Sources: Princeton DataSpace "
          "OAI-PMH (ORFE doctoral dissertations and ORFE senior theses, contributor.advisor = 'Fan, Jianqing'), plus the PI's own "
          "Students page (fan.princeton.edu is Cloudflare-blocked live, so the Wayback 2026-03-14 capture is used). That page adds "
          "current Ph.D. students, postdocs with their years, master's theses, and Ph.D. theses missing from DataSpace. Collection "
          "persons for this name: member_cs_structure_41b45a4fd8f9f783e0c1 (CS roster, chosen), member_2516ea7e4f8ab6cdc9ce and "
          "member_acaba9092f96c5400f48 (roster observations).")

# ---------------------------------------------------------------- Perry Cook
CV_PC = "https://www.cs.princeton.edu/~prc/PRCVOct2021.pdf"
EMER16 = "https://web.archive.org/web/20160531112403id_/http://www.cs.princeton.edu/people/faculty?type=emeritus"
pc_students = q(S, CV_PC, "GRADUATE STUDENTS COMPLETED (Advisor, CoAdvisor or Committee Reader) Max Jaffe, “ Augmented Drumming With "
                          "Sensory Percussion,” MFA Thesis, CalArts, 2021.")
pc_students.update(name_exempt=True, kind="cv_students_section",
                   note="The PI's own CV (Oct 2021): every student it lists after 2016 is at CalArts or Victoria University of "
                        "Wellington. The last Princeton entries are Rebecca Fiebrink (PhD CS, Jan 2011) and Matt Hoffman (2010).")
row("Perry Cook", "not_pi_in_window",
    status_evidence=[window(S, CV_PC, "Professor (Emeritus as of Oct. 9/10), Princeton University Computer Science, jointly in Music",
                            name="Perry Cook", heading=r"Perry R\. Cook", before=0, after=0, max_span=2500),
                     q(S, EMER16, "Perry Cook Professor Emeritus Ph.D., Stanford University, 1991"),
                     pc_students],
    collection_person_id="member_cs_structure_04dc4bbe3e4edea4b447",
    notes="Emeritus since October 2010 and on CalArts faculty since January 2020. His CV's completed-students list has no "
          "Princeton student after 2011, and DataSpace and the CS rosters show no advisee 2016-2026. This is the case of an "
          "emeritus with no student since 2016. The 7 Princeton-affiliated lab papers (2016-2019) are emeritus-era works.")

# ---------------------------------------------------------------- Robert Vanderbei
CV_RV = "https://vanderbei.princeton.edu/tex/misc/Vanderbei_CV.html"
rv_cv = [student(S, CV_RV, nm, "phd", [y, y], needle=f"{nm} Ph.D. {y}", heading=r"Graduate Students Advised / Co-Advised", before=0, after=0,
                 note="Listed under 'Graduate Students Advised / Co-Advised' in the PI's own CV.")
         for nm, y in [("Ethan Fang", 2016), ("Haotian Pang", 2017), ("Hari Subedi", 2018), ("Elahe Naghib", 2019), ("He Sun", 2019),
                       ("Joane Joseph", 2020)]]
row("Robert Vanderbei", "pi",
    students=rv_cv + oai_students(["Vanderbei, Robert"], {ORFE_PHD: "phd", EE_PHD: "phd", ORFE_SR: "undergraduate"}),
    collection_person_id="member_0c2c0732224787f0618a",
    appointment_notes=[q(S, CV_RV, "Robert J. Vanderbei Professor Emeritus, Operations Research & Financial Engineering, Princeton University")],
    notes="Sources: his own CV ('Graduate Students Advised / Co-Advised': six PhDs 2016-2020) and DataSpace OAI (ORFE and EE "
          "dissertations; ORFE senior theses 2016-2023 with contributor.advisor 'Vanderbei, Robert'). The CV lists 'Professor "
          "Emeritus 2024 –', which is consistent with the reviewed 1991-2024 period. DataSpace's 'Fang, Xingyuan' (2016) is "
          "the CV's 'Ethan Fang', and 'Naghib, Elahesadat' is 'Elahe Naghib'.")

# ---------------------------------------------------------------- Ruby Lee
PALMS16 = "https://web.archive.org/web/20160304235153id_/http://palms.ee.princeton.edu/node/2"
PALMS24 = "https://web.archive.org/web/20240415094118id_/http://palms.ee.princeton.edu/node/2"
row("Ruby Lee", "pi",
    students=oai_students(["Lee, Ruby"], {EE_PHD: "phd", ECE_SR: "undergraduate", ECE_MS: "masters"}) + [
        student(S, PALMS16, "Fangfei Liu", "phd", [2016, 2016], heading=r"PhD Students", before=0, after=0,
                note="PALMS (the PI's lab) People page, 'Lab Director Prof. Ruby B. Lee PhD Students ...' (Wayback 2016-03-04)."),
        student(S, PALMS24, "Guangyuan Hu", "phd", [2018, 2024], heading=r"PhD Students", before=0, after=0,
                note="PALMS People page (Wayback 2024-04-15); also on the 2018 capture."),
    ],
    collection_person_id="member_cs_structure_3aa51f9f5f421e45dbe3",
    notes="Sources: DataSpace OAI (Electrical Engineering dissertations and ECE senior theses, contributor.advisor 'Lee, Ruby') "
          "and the PALMS lab People page (palms.ee.princeton.edu does not answer live; Wayback captures 2016, 2018 and 2024 are "
          "stored). The PhD students in the window are Fangfei Liu 2016, Tianwei Zhang 2017, Wei-Han Lee 2019, Zecheng He 2021 "
          "and Guangyuan Hu 2024.")

# ---------------------------------------------------------------- Samory Kpotufe
row("Samory Kpotufe", "pi",
    students=oai_students(["Kpotufe, Samory"], {ORFE_PHD: "phd", ORFE_SR: "undergraduate"}),
    collection_person_id="member_cs_structure_2f7dc25305076a816eef",
    appointment_notes=[window(S, "https://web.archive.org/web/20240614205934id_/https://www.columbia.edu/~skk2175/index.html",
                              "I then spent 4 years at ORFE, Princeton University as an Assistant Professor.", name="Samory Kpotufe",
                              heading=r"Samory Kpotufe", before=0, after=0, max_span=3000)],
    notes="Sources: DataSpace OAI ORFE senior theses, with contributor.advisor 'Kpotufe, Samory': 11 theses 2016-2018. His own "
          "homepages (Princeton 2018 and Columbia 2024 captures) list no students. No ORFE dissertation names him as adviser. "
          "Guillaume Martinet, his Princeton co-author on 'Marginal singularity...' (2021), is a likely PhD advisee but no stored "
          "source states it. The appointment note (Columbia homepage: '4 years at ORFE, Princeton University as an Assistant "
          "Professor') agrees with the reviewed 2014-2019 period.")

# ---------------------------------------------------------------- Victoria Dean
PROF_VD = "https://www.cs.princeton.edu/people/profile/vd2713"
row("Victoria Dean", "pi",
    status_evidence=[q(S, "https://www.cs.princeton.edu/people/grad", "Anha Khan Graduate Student Envelope ak3987@cs.princeton.edu Advisers Victoria Dean")],
    openalex=["A5001500916"],
    identity_evidence=[
        ev("own_homepage", q(S, "https://vdean.github.io/", "Victoria Dean she/they vdean@princeton.edu Hello! I'm a teaching professor in "
                                                           "the Department of Computer Science at Princeton University .")),
        *oa_verify(S, "A5001500916", "https://vdean.github.io/", "Dean", n=3),
        oa_author_quote(S, "A5001500916", "Victoria Dean"),
    ],
    collection_person_id="member_cs_structure_4673040efe1f3cff5b68",
    appointment_notes=[q(S, PROF_VD, "Victoria Dean joined the Princeton faculty in 2025."),
                       window(S, "https://vdean.github.io/", "As of Summer 2025, I have joined Princeton's Computer Science Department",
                              name="Victoria Dean", heading=r"Victoria Dean she/they", before=0, after=0, max_span=3000)],
    notes="Teaching faculty (Lecturer) since summer 2025, previously at Olin College. OpenAlex A5001500916 (ORCID "
          "0000-0002-9337-0689) is verified against her homepage. Its four Princeton-affiliated 2026 works need a 2025 start "
          "period or a 2026 listing to count; the appointment notes give 'joined ... in 2025' and 'Summer 2025'. Split id "
          "A5133835725 (2 Princeton works in 2026, no ORCID) is not verified: too few works. The ORCID is not listed: her page "
          "does not link it and the ORCID record is empty. DBLP 270/0473 comes only from the local family cache (no Wayback "
          "capture), so it is not listed. Collection person member_cs_structure_4673040efe1f3cff5b68 is chosen; "
          "princeton_source_princeton-inst-sweep-author-A5001500916 also exists.")

# ---------------------------------------------------------------- Robert Sedgewick
DBLP_RS = "https://web.archive.org/web/20251027161409id_/https://dblp.org/pid/s/RobertSedgewick.html"
row("Robert Sedgewick", "pi",
    status_evidence=[q(S, "https://www.cs.princeton.edu/people/profile/rs", "Robert Sedgewick William O. Baker *39 Professor in Computer Science, Emeritus")],
    dblp=["https://dblp.org/pid/s/RobertSedgewick"],
    openalex=["A5077370067"],
    identity_evidence=[
        ev("dblp_person_page", q(S, DBLP_RS, "Robert Sedgewick visit author's page @ princeton.edu"), "Wayback capture of the DBLP person page."),
        *oa_verify(S, "A5077370067", "https://www.cs.princeton.edu/~rs/", "Sedgewick", n=2, manual=[
            ("W7128740302", "Bit-Array-Based Alternatives to HyperLogLog (with J. Lumbroso and S. Janson). Theoretical Computer Science 1054, 2025. "
                            "Conference version presented at AofA’24"),
            ("W2891743437", "Introduction to Programming in Java: An Interdisciplinary Approach, Second Edition (with K. Wayne). "
                            "Addison-Wesley, Reading, MA, 2016, 713 pp.")]),
        oa_author_quote(S, "A5077370067", "Robert Sedgewick"),
    ],
    collection_person_id="leader_c84856fd8cc73d41",
    notes="No collection person was attached. The collection has leader_c84856fd8cc73d41 (PI / faculty, chosen), "
          "member_cs_structure_73df19d7428605f481aa, and princeton_source_princeton-inst-sweep-author-A5077370067. OpenAlex "
          "A5077370067 is verified with four 2016+ works on his own site sedgewick.io (the ~rs homepage redirects there). Two of "
          "its works are Princeton-affiliated in the window: 'Introduction for S.I. AofA14' (2016) and 'Bit-array-based "
          "alternatives to HyperLogLog' (2025); both years have a department listing.")

# ---------------------------------------------------------------- Robert Schapire
DBLP_SCH = "https://web.archive.org/web/20260807011239id_/https://dblp.org/pid/s/RobertESchapire.html"
row("Robert Schapire", "pi",
    status_evidence=[q(S, FAC_LIVE, "Robert Schapire Lecturer with Rank of Professor")],
    dblp=["https://dblp.org/pid/s/RobertESchapire"],
    openalex=["A5084108666"],
    identity_evidence=[
        ev("dblp_person_page", q(S, DBLP_SCH, "Robert E. Schapire ORCID 0000-0001-8616-1611 visit author's page @ princeton.edu"),
           "Wayback capture of the DBLP person page."),
        *oa_verify(S, "A5084108666", "http://www.schapire.net/publist.html", "Schapire", n=3),
        oa_author_quote(S, "A5084108666", "Robert E. Schapire"),
    ],
    collection_person_id="leader_9e07fd53a82c003a",
    appointment_notes=[q(S, FAC_LIVE, "Robert Schapire Lecturer with Rank of Professor Research Areas Machine Learning"),
                       q(S, FAC_2019, "Robert Schapire Lecturer Ph.D., Massachusetts Institute of Technology, 1991")],
    notes="Identity: OpenAlex A5084108666 is verified against his own publication list (schapire.net/publist.html). His papers "
          "are genuinely absent, not unmatched: every 2017-2026 work of A5084108666 is affiliated with Microsoft Research. The "
          "only Princeton-affiliated 2016+ work is 'Improved Regret Bounds for Oracle-Based Adversarial Contextual Bandits' "
          "(2016-06), which falls outside his captured listings (2018-2021). He is still listed in 2026 as 'Lecturer with Rank of "
          "Professor', so 2022-2026 listings are missing from the input. ORCID 0000-0001-8616-1611 appears on DBLP and OpenAlex "
          "but is not listed: his pages do not link it and the ORCID record is empty. Collection: leader_9e07fd53a82c003a "
          "(chosen) and member_cs_structure_2c377b5c3d6b1a7ec6ef.")

# ---------------------------------------------------------------- Larry Peterson
DBLP_LP = "https://web.archive.org/web/20251202193117id_/https://dblp.org/pid/p/LLPeterson.html"
row("Larry Peterson", "pi",
    status_evidence=[q(S, "https://www.cs.princeton.edu/~llp/", "Larry Peterson is the Robert E. Kahn Professor Emeritus of Computer Science "
                                                               "and a Senior Research Scholar at Princeton University.")],
    dblp=["https://dblp.org/pid/p/LLPeterson"],
    openalex_candidates=["A5002436680"],
    identity_evidence=[
        ev("dblp_person_page", q(S, DBLP_LP, "Larry L. Peterson visit author's page @ princeton.edu"), "Wayback capture of the DBLP person page."),
        *oa_verify(S, "A5002436680", DBLP_LP, "Peterson", n=3, kind="dblp_person_page_title"),
        oa_author_quote(S, "A5002436680", "Larry Peterson"),
    ],
    collection_person_id="leader_687f14a80aeae67c",
    notes="He has in-window advisees already in the collection: Soner Sevinc (PhD 2016), Jude Nelson (PhD 2018) and Mike "
          "Wawrzoniak (MA 2018). OpenAlex A5002436680 cannot be verified against his own list: his homepage says only 'A "
          "bibliography of his papers can be found here' and links Google Scholar, whose list does not render for bots (no "
          "older homepage capture had a list either). It is therefore an openalex_candidate, matched on the DBLP person page "
          "instead (A P4-based 5G User Plane Function 2021, Using deep programmability... 2020, SDM 2019, Democratizing the "
          "Network Edge 2019, ...). Its Princeton-affiliated works in the window are the 2020 '5G Mobile Networks: A Systems "
          "Approach' book and chapters plus the 2020 CCR article. Accepting the candidate attaches them via the 2020 listing.")

# ---------------------------------------------------------------- Andrea LaPaugh
row("Andrea LaPaugh", "pi",
    status_evidence=[q(S, "https://www.cs.princeton.edu/people/profile/aslp", "Andrea LaPaugh Professor Emeritus")],
    identity_evidence=[oa_author_quote(S, "A5007709732", "Andrea S. LaPaugh"),
                       ev("own_publication_list", q(S, "https://www.cs.princeton.edu/~aslp/pubs.html", "LaPaugh Publications Andrea S. LaPaugh Selected Publications"),
                          "Her own 'Selected Publications' page: the newest item is 2010.")],
    collection_person_id="leader_8c3cad40ef5450e8",
    notes="She is a pi through Muneeb Ali (PhD 2017) and senior theses 2016-2018, already in the collection. Her papers are "
          "genuinely absent: OpenAlex A5007709732 (Andrea S. LaPaugh, 42 works) has nothing after 2013 ('Enabling "
          "Author-Centric Ranking of Web Content'), and raw-name searches for LaPaugh from 2016 find only an unrelated Bailey "
          "LaPaugh. A5007709732 cannot be verified by the three-works rule because it has no 2016+ works, so it is not listed. "
          "No DBLP pid for her is in the local caches.")

# ---------------------------------------------------------------- Yoram Singer
DBLP_YS = "https://web.archive.org/web/20260803042138id_/https://dblp.org/pid/s/YoramSinger.html"
YS_PROF = "https://web.archive.org/web/20201216235113id_/https://www.cs.princeton.edu/people/profile/ysinger"
YS_BIO = "https://web.archive.org/web/20200621085009id_/https://www.cs.princeton.edu/~ysinger/bio.html"
row("Yoram Singer", "pi",
    status_evidence=[q(S, YS_BIO, "Yoram Singer is a professor of Computer Science at Princeton University.")],
    dblp=["https://dblp.org/pid/s/YoramSinger"],
    openalex_candidates=["A5113437318"],
    identity_evidence=[
        ev("dblp_person_page", q(S, DBLP_YS, "Yoram Singer visit author's page @ huji.ac.il"), "Wayback capture of the DBLP person page."),
        ev("own_homepage", q(S, "https://web.archive.org/web/20200319151141id_/https://www.cs.princeton.edu/~ysinger/",
                             "Prof. Yoram Singer Prof. Yoram Singer Department of Computer Science Princeton University"),
           "His Princeton homepage (Wayback 2020-03-19) delegates 'Publications' to an arXiv advanced search, a DuckDuckGo JMLR "
           "query and his ACM author page. The first two are robots-disallowed and ACM is bot-walled."),
        *oa_verify(S, "A5113437318", DBLP_YS, "Singer", n=3, kind="dblp_person_page_title"),
        oa_author_quote(S, "A5113437318", "Yoram Singer"),
    ],
    collection_person_id="leader_ef3ea7a2e10e819d",
    appointment_notes=[q(S, YS_PROF, "Yoram Singer Printer Friendly Title/Position Lecturer with the rank of Professor")],
    notes="He has in-window advisees already in the collection: Fanghong Dong (MA 2019), Seyed Sobhan Mir Yoosefi, and senior "
          "theses Di Qi 2018 and Changyan Wang 2019. OpenAlex A5113437318 (no ORCID) holds his six Princeton-affiliated "
          "2017-2020 works (Shampoo-line second-order optimization, Memory-Efficient Adaptive Optimization, Identity Crisis, "
          "...). It is an openalex_candidate because his own publication list is unreachable; it was matched against the DBLP "
          "person page. By late 2020 the profile reads 'Lecturer with the rank of Professor'. Collection: leader_ef3ea7a2e10e819d "
          "(chosen) and member_cs_structure_a03458b89b010aee264a.")
