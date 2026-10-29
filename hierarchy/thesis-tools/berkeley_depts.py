"""Source spec for the Berkeley advisee hunt outside EECS (2026-10-27): read by harvest_berkeley_depts.py (what to store)
and records.berkeley_depts() (how each stored page becomes thesis records).

DEPT: department lists that name the adviser of every thesis (parsed automatically):
  math    Mathematics 'Past PhD Students' (Title | 'Student; Advisor[; Advisor]' | Year | 'PhD Thesis'), pages 0-15 = 2026..2016;
  ischool School of Information 'Completed Ph.D. Dissertations' ('<Student>. <Title>. Ph.D. dissertation. Advisor(s): ...
          University of California, Berkeley. <Year>.'), page 0 live (2025-2018) and page 1 from the Wayback Machine (the
          live site answers 403 to query-string pages; 2018-2016).

LAB_SOURCES: the PIs' own pages (lab / group rosters, alumni lists, CVs), curated by reading each stored page. Each source:
  pi        the PI as in hierarchy/berkeley/pis.json
  kind      lab-roster | pi-homepage | pi-cv | lab-theses (the record's source tag)
  captures  stored URLs (a live URL, or a Wayback id_ URL); the first is the default capture of 'entries'
  wayback   optional list of page URLs: one Wayback id_ capture per year 2016-2026 (the year's last distinct capture in the
            CDX listing) is added to the captures (used by 'roster')
  entries   explicit rows: (student as named, role, y0, y1[, anchor[, capture]]): one record per row from that capture.
            anchor = the exact (whitespace-collapsed) page text naming the student (default: the name); years come from
            the page (graduation year, 'PhD expected', 'Started', '2022-'), else the capture year.
  roster    {'section': [start_regex, end_regex], 'role': ..., 'names': [...]}: for every capture of the source, each
            name inside the section counts for that capture's year (current-student lists seen across Wayback years).
  parse     {'rx': regex with groups 'name' and 'y', 'role': ...}: numbered thesis lists on the default capture
  from      first year a roster capture may count (the PI's Berkeley start, for PIs who moved their lab to Berkeley)
  qmax      a longer quote limit for list pages that name the PI only in their heading
  note      what the page is and what was left out.
A quote is the shortest stretch of the stored text that runs from a PI family-name occurrence to the student's anchor
(or from the anchor to the next PI family-name occurrence), at most QMAX characters.
"""

QMAX = 5000

MATH_PAGES = ["https://math.berkeley.edu/people/past-department-members/past-phd-students"] + \
    [f"https://math.berkeley.edu/people/past-department-members/past-phd-students?page={i}" for i in range(1, 16)]
ISCHOOL_PAGES = ["https://www.ischool.berkeley.edu/programs/phd/dissertations",
                 "https://web.archive.org/web/20260308004416id_/https://www.ischool.berkeley.edu/programs/phd/dissertations?page=1"]


def dept_urls():
    return MATH_PAGES + ISCHOOL_PAGES


def cdx_query(url):
    """The Wayback CDX URL tcap.wayback_cdx(school, url, frm=2016, to=2026) stores."""
    from urllib.parse import urlencode
    q = {"url": url, "output": "json", "filter": "statuscode:200", "fl": "timestamp,original,digest", "collapse": "digest",
         "from": "2016", "to": "2026"}
    return "https://web.archive.org/cdx/search/cdx?" + urlencode(q)


def yearly(rows):
    """CDX rows [timestamp, original, digest] -> one Wayback id_ URL per year (the year's last capture)."""
    last = {}
    for ts, orig, _ in rows:
        if 2016 <= int(ts[:4]) <= 2026:
            last[ts[:4]] = (ts, orig)
    return [f"https://web.archive.org/web/{ts}id_/{orig}" for ts, orig in (last[y] for y in sorted(last))]


def stored_yearly(read_url):
    """yearly() from the stored CDX answer; read_url(url) -> bytes or None (read-only access to the capture store)."""
    import json

    def f(url):
        b = read_url(cdx_query(url))
        try:
            rows = json.loads(b or b"[]")
        except ValueError:
            return []
        return yearly(rows[1:] if rows else [])
    return f


def all_captures(src, read_url):
    caps = list(src.get("captures") or [])
    for w in src.get("wayback") or []:
        caps += [u for u in stored_yearly(read_url)(w) if u not in caps]
    return caps


LAB_SOURCES = [
    # ---------------------------------------------------------------- IEOR
    {"pi": "Javad Lavaei", "kind": "lab-roster", "title": "Lavaei group page: PhD Students / Alumni (PhD year)",
     "captures": ["https://lavaei.ieor.berkeley.edu/Group.html"], "wayback": ["lavaei.ieor.berkeley.edu/Group.html"],
     "entries": [("Salar Fattahi", "phd", 2020, 2020), ("SangWoo Park", "phd", 2022, 2022), ("Igor Molybog", "phd", 2022, 2022),
                 ("Donghao Ying", "phd", 2025, 2025), ("Baturalp Yalcin", "phd", 2025, 2025), ("Haixiang Zhang", "phd", 2024, 2024),
                 ("Yuhao Ding", "phd", 2023, 2023), ("Han Feng", "phd", 2022, 2022), ("Julie Mulvaney-Kemp", "phd", 2022, 2022),
                 ("Morteza Ashraphijuo", "masters", 2016, 2016, "Morteza Ashraphijuo (MS 2016, UC Berkeley)")],
     "roster": {"section": [r"PhD Students", r"Alumni|Postdoc"], "role": "phd",
                "names": ["Eli Brock", "Jihun Kim", "Ying Chen", "Charles Philip Gulian", "Aoxi Li", "Junyu Guo", "Yuchen Fang",
                          "Salar Fattahi", "SangWoo Park", "Igor Molybog", "Donghao Ying", "Baturalp Yalcin", "Haixiang Zhang",
                          "Yuhao Ding", "Han Feng", "Julie Mulvaney-Kemp"]},
     "note": "postdocs and the Columbia PhDs (2015) left out"},
    {"pi": "Xin Guo", "kind": "pi-homepage", "title": "Xin Guo, People: current / past PhD students (IEOR, UC Berkeley, year)",
     "captures": ["https://xinguo.ieor.berkeley.edu/people"],
     "entries": [("Wangdong Jia", "phd", 2022, 2026), ("Matteo Santamaria", "phd", 2022, 2026), ("Grace He", "phd", 2023, 2026),
                 ("Ziheng Cheng", "phd", 2024, 2026), ("Zijiu Lyu", "phd", 2024, 2026), ("Jackson Gao", "phd", 2024, 2026),
                 ("Xinyu Li", "phd", 2025, 2025), ("Haotian Gu", "phd", 2023, 2023), ("Mahan Tajrobehkar", "phd", 2023, 2023),
                 ("Anran Hu", "phd", 2022, 2022), ("Yusuke Kikuchi", "phd", 2022, 2022), ("Haoyang Cao", "phd", 2020, 2020),
                 ("Renyuan Xu", "phd", 2019, 2019), ("Nan Yang", "phd", 2019, 2019), ("Joon Seok Lee", "phd", 2017, 2017)],
     "note": "Tsinghua-Berkeley Shenzhen Institute students (no UC Berkeley degree) and pre-2016 graduates left out"},
    {"pi": "Paul Grigas", "kind": "pi-homepage", "title": "Grigas research group: current / past PhD students",
     "captures": ["https://grigas.ieor.berkeley.edu/group/"], "wayback": ["grigas.ieor.berkeley.edu/group/"],
     "entries": [("Heyuan Liu", "phd", 2022, 2022), ("Meng Qi", "phd", 2022, 2022), ("Alfonso Lobos", "phd", 2021, 2021)],
     "roster": {"section": [r"Current Students", r"Past Students"], "role": "phd",
                "names": ["Jessica Zhao", "Jeffrey Cheng", "Ricky Huang", "Wyame Benslimane", "Qiran Dong", "Meng Li", "Hyungki Im",
                          "Mo Liu", "Heyuan Liu", "Meng Qi", "Alfonso Lobos"]}},
    {"pi": "Zuo-Jun Max Shen", "kind": "pi-homepage", "title": "co-advisees named on IEOR colleagues' pages (Grigas, Udwani, Aswani)",
     "captures": ["https://grigas.ieor.berkeley.edu/group/", "https://rudwani.ieor.berkeley.edu/students-teaching/",
                  "https://aswani.ieor.berkeley.edu/"],
     "entries": [("Meng Qi", "phd", 2022, 2022, "Meng Qi (main advisor was Max Shen), Ph.D. 2022"),
                 ("Shuo Sun", "phd", 2026, 2026, "Shuo Sun (PhD, 2026) – Co-advised with Max Shen",
                  "https://rudwani.ieor.berkeley.edu/students-teaching/")]},
    {"pi": "Zuo-Jun Max Shen", "kind": "pi-homepage", "title": "Grigas group page across Wayback years: 'Mo Liu (main advisor was Max Shen)'",
     "captures": ["https://grigas.ieor.berkeley.edu/group/"], "wayback": ["grigas.ieor.berkeley.edu/group/"],
     "roster": {"section": [r"Current Students", r"Past Students"], "role": "phd", "names": ["Mo Liu"]}},
    {"pi": "Zuo-Jun Max Shen", "kind": "pi-homepage", "title": "Aswani homepage (Wayback 2017, 2020): 'Jointly advised with Max Shen'",
     "captures": ["https://web.archive.org/web/20200815145143id_/https://aswani.ieor.berkeley.edu/", "https://web.archive.org/web/20171102222931id_/http://ieor.berkeley.edu:80/~aaswani/"],
     "entries": [("Auyon Siddiq", "phd", 2018, 2018, "Auyon Siddiq — PhD 2018 (Assistant Professor at the University of California, at Los Angeles), Jointly advised with Max Shen"),
                 ("Auyon Siddiq", "phd", 2017, 2017, "Auyon Siddiq — PhD expected 2018 (Jointly advised with Max Shen", "https://web.archive.org/web/20171102222931id_/http://ieor.berkeley.edu:80/~aaswani/"),
                 ("Ilgin Dogan", "phd", 2020, 2020, "Ilgin Dogan — PhD expected 2023, Jointly advised with Max Shen")]},
    {"pi": "Rajan Udwani", "kind": "pi-homepage", "title": "Udwani, Students & Teaching: current advisees / alumni",
     "captures": ["https://rudwani.ieor.berkeley.edu/students-teaching/"],
     "entries": [("Suho Kang", "phd", 2024, 2026), ("Shruti Penumatsa", "phd", 2023, 2026), ("Shuo Sun", "phd", 2026, 2026),
                 ("Ziyang Liu", "phd", 2026, 2026), ("Engin Deniz Tekalp", "masters", 2022, 2022),
                 ("Selena Li", "undergraduate", 2023, 2023)]},
    {"pi": "Anil Aswani", "kind": "pi-homepage", "title": "Aswani homepage, Students (live; Wayback 2017 'PhD expected', 2019 'Students Advised' with years, 2020)",
     "captures": ["https://aswani.ieor.berkeley.edu/", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/", "https://web.archive.org/web/20200815145143id_/https://aswani.ieor.berkeley.edu/", "https://web.archive.org/web/20171102222931id_/http://ieor.berkeley.edu:80/~aaswani/"],
     "entries": [("Edward Dowling", "phd", 2026, 2026), ("Jae Won Jeong", "phd", 2026, 2026), ("Chenran Weng", "phd", 2026, 2026),
                 ("Sukanya Kudva", "phd", 2026, 2026), ("Joo Seung Lee", "phd", 2026, 2026), ("Muyan Jiang", "phd", 2026, 2026),
                 ("Ilgin Dogan", "phd", 2019, 2019, "2019-Now Ilgin Dogan", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Yoon Lee", "phd", 2019, 2019, "2019-Now Yoon Lee", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Caleb Bugg", "phd", 2017, 2019, "2017-Now Caleb Bugg", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Matt Olfat", "phd", 2016, 2019, "2016-Now Matt Olfat", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Pedro Hespanhol", "phd", 2016, 2019, "2015-Now Pedro Hespanhol", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Auyon Siddiq", "phd", 2016, 2018, "2014-2018 Auyon Siddiq", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Mo Zhou", "phd", 2016, 2018, "2014-2018 Mo Zhou", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Yonatan Mintz", "phd", 2016, 2018, "2014-2018 Yonatan Mintz", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Abigail Chaver", "masters", 2018, 2018, "2018 Abigail Chaver, UC Berkeley", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Qi Xu", "masters", 2016, 2016, "2016 Qi (Charlene) Xu, UC Berkeley", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Hing Mak", "masters", 2016, 2016, "2016 Hing (Katie) Mak, UC Berkeley", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Aurelien Ouattara", "masters", 2016, 2016, "2015-2016 Aurelien Ouattara, UC Berkeley", "https://web.archive.org/web/20191001125948id_/https://aswani.ieor.berkeley.edu/"),
                 ("Caleb Bugg", "phd", 2020, 2020, "Caleb Bugg — PhD expected 2023", "https://web.archive.org/web/20200815145143id_/https://aswani.ieor.berkeley.edu/"),
                 ("Ilgin Dogan", "phd", 2020, 2020, "Ilgin Dogan — PhD expected 2023", "https://web.archive.org/web/20200815145143id_/https://aswani.ieor.berkeley.edu/"),
                 ("Yoon Lee", "phd", 2020, 2020, "Yoon Lee — PhD expected 2023", "https://web.archive.org/web/20200815145143id_/https://aswani.ieor.berkeley.edu/"),
                 ("Matt Olfat", "phd", 2020, 2020, "Matt Olfat — PhD expected 2020", "https://web.archive.org/web/20200815145143id_/https://aswani.ieor.berkeley.edu/"),
                 ("Pedro Hespanhol", "phd", 2020, 2020, "Pedro Hespanhol — PhD expected 2020", "https://web.archive.org/web/20200815145143id_/https://aswani.ieor.berkeley.edu/")],
     "note": "'Now' in the Oct-2019 capture = 2019; the TUM visiting master's student left out"},
    {"pi": "Shmuel Oren", "kind": "pi-homepage", "title": "Oren, Doctoral Students and Thesis (year)",
     "captures": ["https://oren.ieor.berkeley.edu/students.htm", "https://aswani.ieor.berkeley.edu/"],
     "entries": [("Clay Campaign", "phd", 2016, 2016), ("Jiaying Shi", "phd", 2018, 2018), ("Zhu Yang", "phd", 2018, 2018),
                 ("Georgios Patsakis", "phd", 2020, 2020), ("Tomas Valencia Zuluaga", "phd", 2024, 2024),
                 ("Edward Dowling", "phd", 2026, 2026, "Edward Dowling PhD expected 2029 Co-advised by Shmuel Oren",
                  "https://aswani.ieor.berkeley.edu/")]},
    {"pi": "Dorit S. Hochbaum", "kind": "pi-homepage", "title": "Hochbaum, List of Present Graduate Students (Wayback years)",
     "captures": ["https://hochbaum.ieor.berkeley.edu/html/present_phds.html"],
     "wayback": ["hochbaum.ieor.berkeley.edu/html/present_phds.html", "www.ieor.berkeley.edu/~hochbaum/html/present_phds.html"],
     "roster": {"section": [r"Present", r"Back to Hochbaum|$"], "role": "phd",
                "names": ["Jonathan Bodine", "Catalina Pezo", "Tor Nitayanont", "Torpong Nitayanont", "Quico Spaen", "Xu Rao", "Cheng Lu",
                          "Yan Yang", "Ryan Goldberg"]}},
    {"pi": "Philip Kaminsky", "kind": "pi-homepage", "title": "Kaminsky homepage, STUDENTS (PhD / PhD expected year)",
     "captures": ["http://kaminsky.ieor.berkeley.edu/"],
     "entries": [("Arman Jabbari", "phd", 2019, 2019), ("Tugce Gurek", "phd", 2018, 2018), ("Heejung Kim", "phd", 2018, 2018),
                 ("Shiman Ding", "phd", 2017, 2017), ("Yang Wang", "phd", 2017, 2017), ("Dan Bu", "phd", 2016, 2016),
                 ("Stewart Liu", "phd", 2017, 2017)],
     "note": "the list was last edited c. 2017 ('PhD expected 2018/2019'): years are the stated (expected) PhD years"},
    {"pi": "Alper Atamtürk", "kind": "lab-roster", "title": "BCOL (Berkeley Computational Optimization Lab): Current Students",
     "captures": ["http://bcol.ieor.berkeley.edu/", "https://grigas.ieor.berkeley.edu/group/"], "wayback": ["bcol.ieor.berkeley.edu/"],
     "entries": [("Meng Li", "phd", 2026, 2026, "Meng Li (co-advised with Alper Atamturk)", "https://grigas.ieor.berkeley.edu/group/")],
     "roster": {"section": [r"Current Students", r"Former Students"], "role": "phd",
                "names": ["Isabel Agostino", "Anna Deza", "Hyungki Im", "Jisun Lee", "Meng Li", "Mark Velednitsky", "Andres Gomez",
                          "Qi Zhang", "Jacob Bergquist", "Birce Tezel", "Carlos Deck", "Timmy Siauw", "Chen Chen", "Avinash Bhardwaj"]}},
    # ---------------------------------------------------------------- CEE
    {"pi": "Marta C. González", "kind": "lab-roster", "title": "HuMNet Lab People (PhD students; alumni with degree and year)",
     "captures": ["http://humnetlab.berkeley.edu/index.php/people/"], "wayback": ["humnetlab.berkeley.edu/index.php/people/"],
     "entries": [("Jiaman Wu", "phd", 2025, 2025), ("Alben Bagabaldo", "phd", 2024, 2024), ("Sarah Lindbergh", "phd", 2023, 2023),
                 ("Pelagie Elimbi Moudio", "phd", 2023, 2023), ("Weixin Li", "masters", 2022, 2022), ("Chun Ho Chow", "masters", 2022, 2022),
                 ("Andrew Nelson", "masters", 2020, 2020), ("Ziyun Yuan", "masters", 2020, 2020), ("Alev Bilginsoy", "masters", 2020, 2020),
                 ("María Sol Tadeo", "masters", 2018, 2018), ("Pierre Melikov", "masters", 2019, 2019)],
     "roster": {"section": [r"People Marta", r"Collaborators"], "role": "phd",
                "names": ["Albert Cao", "Abdullah Alhadlaq", "Aparimit Kasliwal", "Eileen Chen", "Giuseppe Perona", "Minho Kim",
                          "Ayse Tugba Ozturk", "Jiaman Wu", "Alben Bagabaldo", "Sarah Lindbergh", "Pelagie Elimbi Moudio"]},
     "from": 2017, "note": "MIT students (before her 2017 move) left out"},
    {"pi": "Scott Moura", "kind": "pi-cv", "title": "Moura CV (last updated 10/25/2021), Student Researcher Mentoring",
     "captures": ["https://ecal.studentorg.berkeley.edu/files/MouraScott-CV.pdf"],
     "entries": [(n, "phd", 2021, 2021, a) for n, a in [
         ("Bertrand Travacca", "Bertrand TRAVACCA"), ("Soomin Woo", "Soomin Woo"), ("Mathilde Badoual", "Mathilde BADOUAL"),
         ("Teng Zeng", "Teng ZENG"), ("Dylan Kato", "Dylan KATO"), ("Aaron Kandel", "Aaron Kandel"),
         ("Patrick Keyantuo", "Patrick Keyantuo"), ("Ioanna Kavvada", "Ioanna Kavvada"), ("Hassan Obeid", "Hassan OBEID"),
         ("Guillaume Goujard", "Guillaume GOUJARD"), ("Preet Gill", "Preet GILL"), ("Chitra Dangwal", "Chitra DANGWAL"),
         ("Callie Clark", "Callie CLARK")]] +
        [("Deep Dayaramani", "masters", 2021, 2021), ("German Perez Lopez", "masters", 2021, 2021),
         ("Akshat Jain", "undergraduate", 2021, 2021), ("Kai Jin", "undergraduate", 2021, 2021)],
     "note": "current mentees in the Oct-2021 CV; the undated former PhD list is left to the Wayback roster below"},
    {"pi": "Scott Moura", "kind": "lab-roster", "title": "eCAL lab people page across Wayback years",
     "captures": [], "wayback": ["ecal.berkeley.edu/people.html", "ecal.berkeley.edu/team.html"],
     "roster": {"section": [r"Ph\.? ?D\.? Students?|Graduate Students", r"Post-?[Dd]oc|Visiting|M\.S\.|Alumni|Former"], "role": "phd",
                "names": ["Hector Perez", "Eric Burger", "Caroline Le Floch", "Eric Munsing", "Hongcai Zhang", "Zach Gima", "Laurel Dunn",
                          "Dong Zhang", "Sangjae Bae", "Saehong Park", "Yiqi Zhao", "Bertrand Travacca", "Soomin Woo", "Mathilde Badoual",
                          "Teng Zeng", "Dylan Kato", "Aaron Kandel", "Patrick Keyantuo", "Ioanna Kavvada", "Hassan Obeid"]}},
    # ---------------------------------------------------------------- ME
    {"pi": "Koushil Sreenath", "kind": "lab-roster", "title": "Hybrid Robotics people: PhD students (start year) and PhD alumni (MechE, UC Berkeley, year)",
     "captures": ["https://hybrid-robotics.berkeley.edu/people/"],
     "entries": [("Chuye Hong", "phd", 2025, 2026), ("Haoyi Niu", "phd", 2025, 2026), ("Huixuan Cheng", "phd", 2025, 2026),
                 ("Yiyang Shao", "phd", 2025, 2026), ("Qiayuan Liao", "phd", 2023, 2026), ("Mintae Kim", "phd", 2023, 2026),
                 ("Akshay Thirugnanam", "phd", 2026, 2026), ("Shuxiao Chen", "phd", 2025, 2025), ("Bike Zhang", "phd", 2025, 2025),
                 ("Jason Choi", "phd", 2025, 2025), ("Zhongyu Li", "phd", 2025, 2025), ("Fernando Castaneda", "phd", 2023, 2023),
                 ("Ayush Agrawal", "phd", 2022, 2022), ("Prasanth Kotaru", "phd", 2022, 2022), ("Jun Zeng", "phd", 2022, 2022),
                 ("Johnathon Li", "phd", 2019, 2019, "Johnathon Li Ph.D. Candidate, ME, 2019-"),
                 ("Matthew Wen", "phd", 2018, 2018, "Matthew Wen MS/Ph.D. Candidate, ME, 2018-")],
     "note": "Carnegie Mellon students (before 2017) left out; Berkeley MEng/undergraduate researchers sit beyond the quote limit"},
    {"pi": "Roberto Horowitz", "kind": "lab-roster", "title": "ARC Lab people: PhD students / students who completed their Ph.D. under my supervision",
     "captures": ["https://sites.google.com/berkeley.edu/prof-roberto-horowitz/people"],
     "entries": [("Joohwan Seo", "phd", 2021, 2026), ("Arvind Kruthiventy", "phd", 2024, 2026), ("Soomi Lee", "phd", 2024, 2026),
                 ("Junfeng Long", "phd", 2025, 2026), ("Nikhil Potu Surya Prakash", "phd", 2024, 2024), ("Ruolin Li", "phd", 2023, 2023),
                 ("Zhi Chen", "phd", 2021, 2021), ("Prateek Shah", "phd", 2020, 2020), ("Cheng-Ju Wu", "phd", 2019, 2019),
                 ("Negar Mehr", "phd", 2019, 2019), ("Matthew A. Wright", "phd", 2019, 2019), ("Omid Bagherieh", "phd", 2017, 2017)]},
    {"pi": "Hannah Stuart", "kind": "lab-roster", "title": "Embodied Dexterity Group people page across Wayback years: Doctoral Students",
     "captures": ["https://edg.berkeley.edu/people", "https://best.berkeley.edu/best-people/"],
     "wayback": ["edg.berkeley.edu/people", "edg.berkeley.edu/people/"],
     "entries": [("Deaho Moon", "phd", 2026, 2026, "Deaho Moon (co-advised by Prof. Hannah Stuart)", "https://best.berkeley.edu/best-people/")],
     "roster": {"section": [r"Doctoral Students|Graduate Students|PhD Students", r"Alumni|Undergraduate|Masters"], "role": "phd",
                "names": ["Jadesola Aderibigbe", "Ben Davis", "Gia Jeong", "Deaho Moon", "Isabel Morales", "Nimran Shergill",
                          "Drew McPherson", "Andrew McPherson", "Erin Chang", "Wilson Torres", "Jungpyo Lee", "Sebastian Lee",
                          "Michael Abbott", "Sareum Kim", "Monica Li", "Cyndia Cao", "Laura Treers"]},
     "from": 2018, "note": "the alumni list page (edg.berkeley.edu/people/alumni/) does not name the PI, so years come from the people page"},
    {"pi": "Mark Mueller", "kind": "lab-roster", "title": "HiPeRLab members across Wayback years: Graduate students",
     "captures": ["https://hiperlab.berkeley.edu/members/"], "wayback": ["hiperlab.berkeley.edu/members/"],
     "roster": {"section": [r"Graduate students", r"Post-?doc|Past members|Undergrad"], "role": "phd",
                "names": ["Carlo Bosio", "Eric Foss", "Thanos Kyriakopoulos", "Gaofeng Su", "Andrew Tai", "Ting-Hao Wang", "Teaya Yang",
                          "Ruiqi Zhang", "Daisy Zhang", "Haoyun (Jerry) Tang", "Haoyun Tang", "Jiaming (Clark) Zha", "Jiaming Zha",
                          "Karan Jain", "Xiangyu Wu", "Nathan Bucki", "Conrad Holda"]}},
    {"pi": "Negar Mehr", "kind": "lab-roster", "title": "ICON Lab people: Graduate Students (Mechanical Engineering, UC Berkeley)",
     "captures": ["https://iconlab.negarmehr.com/people/"], "wayback": ["iconlab.negarmehr.com/people/"], "from": 2024, "qmax": 8000,
     "roster": {"section": [r"Graduate Students", r"Visiting|Alumni|Robots"], "role": "phd",
                "names": ["Kanghyun Ryu", "Kartik Nagpal", "John Viljoen", "Aayushi Shrivastava", "Ethan Dong", "Seoyeon Choi",
                          "Ryan Park", "Marfred Barrera", "Junwoo Chang", "Zhenlong Fang", "Maulik Bhatt"]},
     "note": "roster years start at her 2024 Berkeley appointment (the lab moved from UIUC)"},
    {"pi": "Lining Yao", "kind": "lab-roster", "title": "Morphing Matter Lab people (Started <date>)",
     "captures": ["https://morphingmatter.org/people"],
     "entries": [("Atulit Dasaratha", "phd", 2024, 2026), ("Semina Yi", "phd", 2024, 2026), ("Tianyu Yu", "phd", 2024, 2026),
                 ("Mako Miyatake", "phd", 2024, 2026), ("Stella Shen", "phd", 2024, 2026),
                 ("Jeremy Chen", "masters", 2024, 2026), ("Christy Huang", "undergraduate", 2024, 2026),
                 ("Sean Barbieri", "undergraduate", 2024, 2026), ("Yunosuke Nakamura", "undergraduate", 2026, 2026)],
     "note": "years start at her 2024 Berkeley appointment; 'Ming' (one name only) left out"},
    {"pi": "Alice Agogino", "kind": "lab-theses", "title": "BEST Lab: Ph.D. Theses chaired by Alice M. Agogino (numbered, academic year, term)",
     "captures": ["http://best.berkeley.edu/best-director-alice-m-agogino/ph-d-theses-chaired-by-alice-m-agogino/"], "qmax": 9000,
     "parse": {"rx": r"\d+\.? (?:20)?\d\d/(?:20)?\d\d (?P<name>[A-Z][^“”\"]{2,60}?) (?:\(Co-Advised[^)]*\) )?“[^”]*”\s?,? (?:\([^)]*\),? )?(?:Spring|Summer|Fall|Winter) (?P<y>20\d\d)",
               "role": "phd", "label": "Ph.D. thesis chaired"}},
    {"pi": "Alice Agogino", "kind": "lab-theses", "title": "BEST Lab: Ph.D. Theses chaired (entries without a term)",
     "captures": ["http://best.berkeley.edu/best-director-alice-m-agogino/ph-d-theses-chaired-by-alice-m-agogino/"], "qmax": 9000,
     "entries": [("Elena Cristina Durán López", "phd", 2022, 2022, "2021/22 Elena Cristina Durán López")]},
    {"pi": "Alice Agogino", "kind": "lab-roster", "title": "BEST People: Recent M.S./Ph.D. Graduate Students",
     "captures": ["https://best.berkeley.edu/best-people/"],
     "entries": [("Deaho Moon", "phd", 2026, 2026), ("Ankita Joshi", "masters", 2026, 2026), ("Danielle Poreh", "other", 2026, 2026)]},
    {"pi": "Shawn C. Shadden", "kind": "lab-roster", "title": "Shadden Lab people across Wayback years: PhD Students",
     "captures": [], "wayback": ["shaddenlab.berkeley.edu/people.html", "shaddenlab.berkeley.edu/people"],
     "roster": {"section": [r"PhD Students", r"Masters Students|Undergraduate|Alumni"], "role": "phd",
                "names": ["Siavash Ameli", "Sarah Frank", "Mehran Mirramezani", "Jeffrey Pyne", "Kirk Hansen", "Adam Updegrove",
                          "Jiacheng Wu", "Miguel Rodriguez", "Fanwei Kong", "Amirhossein Arzani"]},
     "note": "the live page is a stale copy; only Wayback captures 2016-2026 date the roster"},
    # ---------------------------------------------------------------- Statistics, Philosophy, Physics, Linguistics, ChemE
    {"pi": "Ryan Tibshirani", "kind": "pi-homepage", "title": "Tibshirani, Group (current; alumni Statistics Ph.D., UC Berkeley, year)",
     "captures": ["https://www.stat.berkeley.edu/~ryantibs/group.html"],
     "entries": [("Erez Buchweitz", "phd", 2026, 2026), ("João Romano", "phd", 2026, 2026), ("Xueda Shen", "phd", 2026, 2026),
                 ("Tiffany Ding", "phd", 2026, 2026), ("Jeremy Goldwasser", "phd", 2026, 2026), ("Hyunsuk Kim", "phd", 2026, 2026),
                 ("Seunghoon Paik", "phd", 2026, 2026)],
     "note": "Carnegie Mellon students (before 2022) and postdocs left out"},
    {"pi": "Wesley Holliday", "kind": "pi-homepage", "title": "Holliday, Students: dissertation committees as Chair or Co-Chair; MA thesis committees as Chair",
     "captures": ["https://sites.google.com/site/wesholliday/students"],
     "entries": [("Ahmee Christensen", "phd", 2025, 2025), ("Guillaume Massas", "phd", 2024, 2024), ("Reid Dale", "phd", 2022, 2022),
                 ("Yifeng Ding", "phd", 2021, 2021), ("Kentaro Yamamoto", "phd", 2020, 2020), ("Alex Kocurek", "phd", 2018, 2018),
                 ("Raha Ahmadian", "phd", 2026, 2026), ("Emma Boniface", "phd", 2026, 2026), ("Lucy Horowitz", "phd", 2026, 2026),
                 ("Adam Lesnikowski", "phd", 2026, 2026), ("Isabella Carlsson", "masters", 2021, 2021), ("Pen Long", "masters", 2020, 2020)],
     "note": "committees as additional member and undergraduate research collaborations left out"},
    {"pi": "Michael DeWeese", "kind": "lab-roster", "title": "DeWeese Lab people across Wayback years: Graduate Students",
     "captures": ["https://deweeselab.com/people"], "wayback": ["deweeselab.com/people", "deweese-lab.github.io/people"],
     "roster": {"section": [r"Graduate Students", r"Alumni|Undergrad"], "role": "phd",
                "names": ["Sam D'Ambrosia", "Joey Turnbull", "Hana Mir", "Eduardo Sandoval", "Dhruva Karkada", "Chad Harper", "Steven Lee",
                          "Jamie Simon", "Adrianne Zhong", "Adam Frim", "Juliana Chase", "Andrew Ligeralde", "Neha Wadia", "Pratik Sachdeva"]}},
    {"pi": "Terry Regier", "kind": "lab-roster", "title": "Language and Cognition Lab people across Wayback years: Students",
     "captures": ["https://terry-regier.github.io/lclab/people.html"],
     "wayback": ["terry-regier.github.io/lclab/people.html", "lclab.berkeley.edu/people.html", "lclab.berkeley.edu/"],
     "roster": {"section": [r"Students", r"Alumni"], "role": "phd",
                "names": ["Elise Kim", "Iñigo Parra", "Joshua Abbott", "Geoff Bacon", "Alexandra Carstensen", "Emily Cibelli",
                          "Noah Hermalin", "Elise Stickles", "Yang Xu", "Noga Zaslavsky"]},
     "entries": [("David Yang", "undergraduate", 2025, 2025, "David Yang B.A. 2025")]},
    {"pi": "Ali Mesbah", "kind": "lab-roster", "title": "Mesbah Lab people across Wayback years: Graduate Researchers",
     "captures": ["https://www.mesbahlab.com/people"], "wayback": ["mesbahlab.com/people"],
     "roster": {"section": [r"Graduate Researchers", r"Undergraduate|Alumni|Visiting"], "role": "phd",
                "names": ["Shoubhanik Nath", "Joshua Hang Sai Ip", "Melanie Huynh", "Thomas Banker", "Alan Stoev", "Harry Papargyriou",
                          "Shauryaraj Jilkar", "Jerry Fung", "Dogan Gidon", "Marc Martin-Casas", "Georgios Makrygiorgos", "Kimberly Buehler",
                          "Angelo Bonzanini", "Ketong Shao", "Andrew Chen", "Joel Paulson"]}},
    # ---------------------------------------------------------------- I School, Education
    {"pi": "Joshua Blumenstock", "kind": "pi-cv", "title": "Blumenstock CV (Sept 2025), Advising: Doctoral Committee Chair",
     "captures": ["http://www.jblumenstock.com/files/jblumenstock_cv.pdf"],
     "entries": [("Robert On", "phd", 2018, 2018), ("Muhammad Raza Khan", "phd", 2019, 2019), ("Niall Keleher", "phd", 2019, 2019),
                 ("Gabriel Cadamuro", "phd", 2020, 2020), ("Guanghua Chi", "phd", 2021, 2021), ("Emily Aiken", "phd", 2024, 2024),
                 ("Suraj Nair", "phd", 2018, 2025), ("Simón Ramirez Amaya", "phd", 2018, 2025), ("Satej Soman", "phd", 2020, 2025),
                 ("Zoe Kahn", "phd", 2020, 2025), ("Susana Constenla-Villoslada", "phd", 2022, 2025),
                 ("Samuel Merritt Smith", "phd", 2024, 2025)]},
    {"pi": "Michelle Hoda Wilkerson", "kind": "pi-cv", "title": "Wilkerson CV (July 2022): DOCTORAL STUDENTS; MASTERS STUDENTS (MACSME, by year)",
     "captures": ["https://bse.berkeley.edu/sites/default/files/general/cvjul2022-michellehodawilkerson.pdf"],
     "entries": [(n, "phd", 2022, 2022) for n in ["Tyler Graff", "Brendan Henrique", "Andrew Phuong", "Jacob Barton", "Erin Foley",
                                                  "Lisette Lopez", "Collette Roberto", "Nicole Bulalacao", "Vasiliki Laina"]] +
        [(n, "masters", 2019, 2019) for n in ["Sheila Afnan", "Luis Hernández", "Sean Li", "Alex Paauwe", "Jane Sadetsky", "Yixiao Zhang"]] +
        [(n, "masters", 2018, 2018) for n in ["Jim Han", "Alyssa Kehlenbach", "Annie Lu", "Nathan Usselman"]] +
        [(n, "masters", 2017, 2017) for n in ["Sydney Aardhal", "Eugenia Clark", "Tarah Kirnan", "Sierra Flynn", "Sierra Reyburn"]] +
        [("Katrina Halle", "masters", 2016, 2016)],
     "note": "doctoral rows carry 2016-2021 start years in a separate column that pdftotext does not keep aligned, so the CV date "
             "(2022) is used; Becca Shareff ('Graduated 2020', alignment unclear) left out"},
    {"pi": "Dor Abrahamson", "kind": "lab-roster", "title": "EDRL Graduate Students across Wayback years",
     "captures": ["https://edrl.berkeley.edu/graduate-students/"], "wayback": ["edrl.berkeley.edu/graduate-students/"],
     "roster": {"section": [r"Graduate Students (?!Research)(?=[A-Z])", r"Upcoming Events|View All Events|Making Math Meaningful"],
                "role": "phd",
                "names": ["Ellie Chew", ("Emma Teresa Booth", "Emma Teresa (Ter) Booth"), "Jessica Benally", "Julien Putz", "Ratih Ayu Apsari",
                          "Zoe Silverman", "Sofia Tancredi", "Brittney Cooper", "Amelia Farid", "Leah Rosenbaum", "Alyse Schneider",
                          "Darryl Diptee", "Jacqueline Anton", "John Kim"]},
     "note": "the EDRL dissertation list carries no years, so years come from the graduate-student page captures"},
    {"pi": "Maggi Kelly", "kind": "lab-roster", "title": "Kelly Research & Outreach Lab people across Wayback years (graduate students; "
     "Former Kellylab Graduate Students with graduation term)",
     "captures": ["https://web.archive.org/web/20171229064530id_/http://kellylab.berkeley.edu:80/people/", "https://web.archive.org/web/20260226000212id_/http://kellylab.berkeley.edu/people"],
     "wayback": ["kellylab.berkeley.edu/people/", "kellylab.berkeley.edu/people"],
     "entries": [("Anu Kramer", "phd", 2016, 2016, "Anu Kramer, ESPM-UCB. Co-Advisor (with Scott Stephens). Graduated May 2016"),
                 ("Annie Taylor", "phd", 2024, 2024, "Annie Taylor , ESPM-UCB. 2024.", "https://web.archive.org/web/20260226000212id_/http://kellylab.berkeley.edu/people"),
                 ("Chippie Kislik", "phd", 2022, 2022, "Chippie Kislik , ESPM-UCB. 2022.", "https://web.archive.org/web/20260226000212id_/http://kellylab.berkeley.edu/people"),
                 ("Christine Wilkinson", "phd", 2021, 2021, "Christine Wilkinson , PhD. ESPM-UCB. 2021.", "https://web.archive.org/web/20260226000212id_/http://kellylab.berkeley.edu/people"),
                 ("Kelly Easterday", "phd", 2018, 2018, "Kelly Easterday , PhD. ESPM-UCB. 2018.", "https://web.archive.org/web/20260226000212id_/http://kellylab.berkeley.edu/people"),
                 ("Jenny Palomino", "phd", 2018, 2018, "Jenny Palomino , PhD. ESPM-UCB. Co-Advisor (with M Potts). 2018.", "https://web.archive.org/web/20260226000212id_/http://kellylab.berkeley.edu/people")],
     "roster": {"section": [r"People Kelly Research", r"Former Kellylab"], "role": "phd",
                "names": ["Chippie Kislik", "Kelly Easterday", "Jenny Palomino", "Christine Wilkinson", "Annie Taylor"]},
     "note": "the 2016-2018 captures list the current graduate students with bios; staff of the IGIS program are not on this page"},
    {"pi": "Michelle Hoda Wilkerson", "kind": "dept-roster", "title": "Berkeley School of Education graduate students: 'advised by Prof. Michelle Wilkerson'",
     "captures": ["https://bse.berkeley.edu/people/graduate-students"],
     "entries": [("Brendan Henrique", "phd", 2026, 2026, "Brendan Henrique Brendan is a fifth-year doctoral student at the Berkeley School of "
                  "Education in the Learning Sciences and Human Development (LSHD) cluster and is advised by Prof. Michelle Wilkerson")]},
    {"pi": "Dor Abrahamson", "kind": "dept-roster", "title": "Berkeley School of Education graduate students: 'Working with Prof. Dor Abrahamson'",
     "captures": ["https://bse.berkeley.edu/people/graduate-students"],
     "entries": [("Julien Putz", "phd", 2026, 2026, "Julien Putz is a PhD candidate in the Graduate Group in Science and Mathematics "
                  "Education (SESAME) at UC Berkeley, with a designated emphasis in Cognitive Science. Working with Prof. Dor Abrahamson")]},
]
