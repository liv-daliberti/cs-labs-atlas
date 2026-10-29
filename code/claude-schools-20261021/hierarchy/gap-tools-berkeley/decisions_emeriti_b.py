"""Berkeley gap decisions, worker emeriti_b (2026-10-21/22): Karp, Parlett, Rowe, Séquin, A. J. Smith, Stonebraker,
Sturmfels, Berlekamp, Ramamoorthy, Zadeh.

Evidence specs name stored captures (see dhelp.py); build.py resolves and re-verifies every quote.
MGP = Mathematics Genealogy Project (live site offline since 2026-10-20 for a PHP vulnerability, so Wayback id_
captures are used). math.berkeley.edu robots.txt sets Crawl-delay: 10, honoured for the past-PhD pages.
"""
import sys

sys.path.insert(0, "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-berkeley")
from dhelp import *  # noqa: E402,F401,F403

D = {}
TR = "https://www2.eecs.berkeley.edu/Pubs/TechRpts/"
MEMORIAM = "https://eecs.berkeley.edu/people/faculty/in-memoriam/"
L2015 = WB + "20151204175958id_/http://www.eecs.berkeley.edu:80/Faculty/Lists/faculty.shtml"
L2017 = WB + "20171101140017id_/https://www2.eecs.berkeley.edu/Faculty/Lists/faculty.html"
L2019 = WB + "20190715184029id_/https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html"
WIKI = "https://en.wikipedia.org/wiki/"
MGP_KARP = WB + "20250623064022id_/https://www.genealogy.ams.org/id.php?id=25275"
MGP_PARLETT = WB + "20240915233517id_/https://www.genealogy.math.ndsu.nodak.edu/id.php?id=32898"
MGP_SMITH = WB + "20241212190636id_/https://mathgenealogy.org/id.php?id=70094"
MGP_BERLEKAMP = WB + "20260203171820id_/https://www.mathgenealogy.org/id.php?id=16958"
MGP_STONEBRAKER = WB + "20260905090645id_/https://mathgenealogy.org/id.php?id=31091"
MGP_STURMFELS = WB + "20251114181518id_/https://www.mathgenealogy.org/id.php?id=28162"


def diss_newest(pi, entry):
    """Heading of the PI's EECS dissertations-by-faculty page through its newest entry."""
    return SE(diss_page_url(pi), "Ph.D. Dissertations - " + pi, entry)


# ============================================================================ Carlo H. Séquin (pi)
SQ = "https://people.eecs.berkeley.edu/~sequin/"
SQCUR = "http://people.eecs.berkeley.edu/%7Esequin/BIO/stu.cur.html"
SQMS = "http://people.eecs.berkeley.edu/%7Esequin/BIO/stu.ms.html"
SQPUB = "http://people.eecs.berkeley.edu/%7Esequin/BIO/rpub.html"
SQFAN = TR + "2021/EECS-2021-125.html"

# (name, role, years, section heading on 'Current and Recent Students Supervised by Carlo H. Séquin', name as shown)
SEQUIN_ROWS = [
    ('Michelle Chow', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Michelle Chow'),
    ('Arjun Damerla', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Arjun Damerla'),
    ('Miro Yoshiki Garrett', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Miro Yoshiki Garrett'),
    ('Robert Severo Meli', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Robert Severo Meli'),
    ('Tamara Tam Nguyen', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Tamara Tam Nguyen'),
    ('Katy Qin', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Katy Qin'),
    ('Ronak Lal Sinha', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Ronak Lal Sinha'),
    ('Benjamin Atticus Smothers', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Benjamin Atticus Smothers'),
    ('Ashvin Verma', 'undergraduate', [2024, 2024], 'Undergraduate Students: Fall 2024', 'Ashvin Verma'),
    ('Rajoshi Basu', 'undergraduate', [2023, 2024], 'Undergraduate Students: 2023-2024', 'Basu, Rajoshi'),
    ('Charles Cai', 'undergraduate', [2023, 2024], 'Undergraduate Students: 2023-2024', 'Cai, Charles'),
    ('Russell Castro', 'undergraduate', [2023, 2024], 'Undergraduate Students: 2023-2024', 'Castro, Russell'),
    ('Samantha Huang', 'undergraduate', [2023, 2024], 'Undergraduate Students: 2023-2024', 'Huang, Samantha'),
    ('Brian Kim', 'undergraduate', [2020, 2024], 'Undergraduate Students: 2023-2024', 'Kim, Brian'),
    ('Dan Lyu', 'undergraduate', [2023, 2024], 'Undergraduate Students: 2023-2024', 'Lyu, Dan'),
    ('Monica Tang', 'undergraduate', [2019, 2024], 'Undergraduate Students: 2023-2024', 'Tang, Monica'),
    ('Marissa Tsoi', 'undergraduate', [2023, 2024], 'Undergraduate Students: 2023-2024', 'Tsoi, Marissa'),
    ('Ian Zhang', 'undergraduate', [2023, 2024], 'Undergraduate Students: 2023-2024', 'Zhang, Ian'),
    ('Ryan Alameddine', 'undergraduate', [2021, 2022], 'Undergraduate Students: Spring 2022:', 'Ryan Alameddine'),
    ('Samantha Averitt', 'undergraduate', [2022, 2022], 'Undergraduate Students: Spring 2022:', 'Samantha Averitt'),
    ('Andrew Fan', 'undergraduate', [2021, 2022], 'Undergraduate Students: Spring 2022:', 'Andrew Fan'),
    ('Qingsong Ji', 'undergraduate', [2022, 2022], 'Undergraduate Students: Spring 2022:', 'Qingsong Ji'),
    ('Vedang Joshi', 'undergraduate', [2022, 2022], 'Undergraduate Students: Spring 2022:', 'Vedang Joshi'),
    ('Uri Kreindler', 'undergraduate', [2022, 2022], 'Undergraduate Students: Spring 2022:', 'Uri Kreindler'),
    ('Ruchi Maheshwari', 'undergraduate', [2021, 2022], 'Undergraduate Students: Spring 2022:', 'Ruchi Maheshwari'),
    ('Samuel Speas', 'undergraduate', [2022, 2022], 'Undergraduate Students: Spring 2022:', 'Samuel Speas'),
    ('Benedict Taguinod', 'undergraduate', [2022, 2022], 'Undergraduate Students: Spring 2022:', 'Benedict Taguinod'),
    ('Justin Wang', 'undergraduate', [2022, 2022], 'Undergraduate Students: Spring 2022:', 'Justin Wang'),
    ('Amruth Uppaluri', 'undergraduate', [2021, 2021], 'Undergraduate Students: Fall 2021:', 'Uppaluri, Amruth'),
    ('Ruohan Yan', 'undergraduate', [2021, 2021], 'Undergraduate Students: Fall 2021:', 'Yan, Ruohan'),
    ('Xinyu Zhang', 'undergraduate', [2019, 2021], 'Undergraduate Students: Fall 2021:', 'Zhang, Xinyu'),
    ('Randy Fan', 'masters', [2019, 2021], 'Graduate Students: Spring 2021:', 'Randy Fan'),
    ('Brandon Lee', 'undergraduate', [2020, 2021], 'Undergraduate Students: Spring 2021:', 'Brandon Lee'),
    ('Vishnu Pamula', 'undergraduate', [2019, 2021], 'Undergraduate Students: Spring 2021:', 'Vishnu Pamula'),
    ('Rohan Sood', 'undergraduate', [2020, 2021], 'Undergraduate Students: Spring 2021:', 'Rohan Sood'),
    ('Hridhay Suresh', 'undergraduate', [2020, 2021], 'Undergraduate Students: Spring 2021:', 'Hridhay Suresh'),
    ('Fei Cong', 'undergraduate', [2020, 2020], 'Undergraduate Students: Fall 2020:', 'Fei Cong'),
    ('Adrian Fan', 'undergraduate', [2020, 2020], 'Undergraduate Students: Fall 2020:', 'Adrian Fan'),
    ('Sam Maher', 'undergraduate', [2020, 2020], 'Undergraduate Students: Fall 2020:', 'Sam Maher'),
    ('Tianqi Yang', 'undergraduate', [2020, 2020], 'Undergraduate Students: Fall 2020:', 'Tianqi Yang'),
    ('Zixin Yin', 'undergraduate', [2020, 2020], 'Undergraduate Students: Fall 2020:', 'Zixin Yin'),
    ('Jonathan Liu', 'undergraduate', [2018, 2020], 'Undergraduate Students: 2019/20:', 'Jonathan Liu'),
    ('Ronan Alam', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Ronan Alam'),
    ('Shide Dehghani', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Shide Dehghani'),
    ('Jay Garg', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Jay Garg'),
    ('Peter Generao', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Peter Generao'),
    ('Zuyong Li', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Zuyong Li'),
    ('Nishant Nayak', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Nishant Nayak'),
    ('Patricia Ouyang', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Patricia Ouyang'),
    ('Yin Tang', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Yin Tang'),
    ('Debbie Yuen', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Debbie Yuen'),
    ('Toby Chen', 'undergraduate', [2017, 2020], 'Undergraduate Students: 2019/20:', 'Toby Chen'),
    ('Jennifer Hoang', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Jennifer Hoang'),
    ('Kevin Tezel', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Kevin Tezel'),
    ('Anjali Thakrar', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Anjali Thakrar'),
    ('Claire Tsau', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Claire Tsau'),
    ('Steven Yang', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Steven Yang'),
    ('Darren Yang', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Darren Yang'),
    ('Zachary Yin', 'undergraduate', [2019, 2020], 'Undergraduate Students: 2019/20:', 'Zachary Yin'),
    ('Henry Sun', 'undergraduate', [2018, 2019], 'Undergraduate Students: Spring 2019:', 'Henry Sun'),
    ('Ricardo Herrera', 'undergraduate', [2018, 2019], 'Undergraduate Students: Spring 2019:', 'Ricardo Herrera'),
    ('Nilay Khatore', 'undergraduate', [2019, 2019], 'Undergraduate Students: Spring 2019:', 'Nilay Khatore'),
    ('Hamza Qadeer', 'undergraduate', [2019, 2019], 'Undergraduate Students: Spring 2019:', 'Hamza Qadeer'),
    ('Jimmy Xu', 'undergraduate', [2019, 2019], 'Undergraduate Students: Spring 2019:', 'Jimmy Xu'),
    ('Mengti Sun', 'undergraduate', [2018, 2019], 'Undergraduate Students: Spring 2019:', 'Mengti Sun'),
    ('Kenny Chen', 'undergraduate', [2018, 2019], 'Undergraduate Students: Spring 2019:', 'Kenny Chen'),
    ('William Brandon', 'undergraduate', [2017, 2019], 'Undergraduate Students: Spring 2019:', 'William Brandon'),
    ('Brian Aronowitz', 'undergraduate', [2018, 2019], 'Undergraduate Students: Spring 2019:', 'Brian Aronowitz'),
    ('Marc WuDunn', 'undergraduate', [2018, 2018], 'Undergraduate Students: Fall 2018:', 'Marc WuDunn'),
    ('Gauthier Dieppedalle', 'masters', [2016, 2018], 'Graduate Students: 2017/18:', 'Gauthier Dieppedalle'),
    ('Lewis Pan', 'undergraduate', [2016, 2018], 'Undergraduate Students: 2017/18:', 'Lewis Pan'),
    ('Arman Babakhani', 'undergraduate', [2016, 2018], 'Undergraduate Students: 2017/18:', 'Arman Babakhani'),
    ('Xingjian Han', 'undergraduate', [2017, 2018], 'Undergraduate Students: 2017/18:', 'Xingjian Han'),
    ('Nagaganesh Jaladanki', 'undergraduate', [2017, 2018], 'Undergraduate Students: 2017/18:', 'Nagaganesh Jaladanki'),
    ('Sarah Sun', 'undergraduate', [2017, 2018], 'Undergraduate Students: 2017/18:', 'Sarah Sun'),
    ('Beren Oguz', 'undergraduate', [2015, 2017], 'Undergraduate Students: 2016/17:', 'Beren Oguz'),
    ('Yifat Amir', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Yifat Amir'),
    ('Ruta Jawale', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Ruta Jawale'),
    ('Rohan Taori', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Rohan Taori'),
    ('Nicholas Ward', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Nicholas Ward'),
    ('Zirui Zhou', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Zirui Zhou'),
    ('Kendra Duran', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Kendra Duran'),
    ('Vi Le', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Vi Le'),
    ('Joshua Lin', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Joshua Lin'),
    ('Kevin Mu', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'Kevin Mu'),
    ('Alex Romano', 'undergraduate', [2015, 2017], 'Undergraduate Students: 2016/17:', 'Alex Romano'),
    ('David Vakshlyak', 'undergraduate', [2016, 2017], 'Undergraduate Students: 2016/17:', 'David Vakshlyak'),
    ('Nancy Wang', 'undergraduate', [2015, 2016], 'Undergraduate Students: 2015/16:', 'Nancy Wang'),
    ('Pratham Alag', 'undergraduate', [2015, 2016], 'Undergraduate Students: 2015/16:', 'Pratham Alag'),
    ('Yunfan Song', 'undergraduate', [2015, 2016], 'Undergraduate Students: 2015/16:', 'Yunfan Song'),
    ('Korbi Thalhammer', 'undergraduate', [2015, 2016], 'Undergraduate Students: 2015/16:', 'Korbi Thalhammer'),
    ('Alex Wang', 'undergraduate', [2015, 2016], 'Undergraduate Students: 2015/16:', 'Alex Wang'),
    ('Joanna Yang', 'undergraduate', [2015, 2016], 'Undergraduate Students: 2015/16:', 'Joanna Yang'),
    ('Hong Jeon', 'undergraduate', [2015, 2016], 'Undergraduate Students: 2015/16:', 'Hong Jeon'),
]
_MS_OVERRIDE = {
    "Randy Fan": ST("Randy Fan", "masters", [2019, 2021],
                    SE(SQFAN, "Advisors: Carlo H. Séquin", "Author= {Fan, Randy}"), must=["Fan"],
                    note=("M.S. report UCB/EECS-2021-125 (May 2021), 'Advisors: Carlo H. Séquin' (co-editor R. Ng); also "
                          "listed as Séquin's undergraduate researcher 2019-2020 and graduate student Fall 2020/Spring 2021.")),
    "Gauthier Dieppedalle": ST("Gauthier Dieppedalle", "masters", [2016, 2018],
                               SE(SQMS, "M.S. Theses Completed under Direction of Carlo H. Séquin", "May 15, 2018."),
                               note="M.S. thesis May 15, 2018 under Séquin; undergraduate researcher 2016/17, graduate student 2017/18."),
}
_sq_students = []
for _name, _role, _years, _head, _disp in SEQUIN_ROWS:
    if _name in _MS_OVERRIDE:
        _sq_students.append(_MS_OVERRIDE[_name])
        continue
    _sq_students.append(ST(_name, _role, _years, SE(SQCUR, _head, _disp), must=[_disp.split(",")[0].split()[-1]],
                           note=("Listed under '" + _head.rstrip(":") + "' on Séquin's 'Current and Recent Students "
                                 "Supervised by Carlo H. Séquin' page; years from the terms listed.")))
_sq_students.append(ST("Andy Yu Wang", "masters", [None, 2016],
                       SE(SQMS, "M.S. Theses Completed under Direction of Carlo H. Séquin", "May 12, 2016."),
                       note="M.S. thesis 'Robust Geometry Kernel and UI for Handling Non-orientable 2-Mainfolds', May 12, 2016."))

D["Carlo H. Séquin"] = dict(
    status="pi",
    status_ev=[
        SE(SQCUR, "Current and Recent Students Supervised by Carlo H. Séquin", "Undergraduate Students: Fall 2024 Michelle Chow"),
        SE(SQMS, "M.S. Theses Completed under Direction of Carlo H. Séquin", "May 15, 2018."),
        SE(SQFAN, "Advisors: Carlo H. Séquin", "Author= {Fan, Randy}"),
    ],
    students=_sq_students,
    identity=dict(
        orcid=["0000-0002-0060-2162"], openalex=["A5040375281"],
        evidence=[
            ID("openalex_author_record", SE(oa_author_url("A5040375281"), '{"id":"https://openalex.org/A5040375281"',
                                            '"Carlo H. Sequin"', raw=True, must=["Sequin"]),
               ("OpenAlex author record (282 works; ORCID 0000-0002-0060-2162; UC Berkeley affiliation years incl. "
                "2016-2020). Its display_name is JSON-escaped ('Carlo H. S\\u00e9quin'), so the quote runs on to the "
                "unaccented raw author name 'Carlo H. Sequin'.")),
            ID("openalex_verified_by_publication_list", Q(SQPUB, 'Séquin, "Parametric Co-Design of Modular Free-Form 2-Manifolds'),
               "Own 'Recent Publications' page; = OpenAlex W2532349502 (2016) of A5040375281. 11 of the id's 17 works dated 2016+ match this page."),
            ID("openalex_verified_by_publication_list", Q(SQPUB, 'Séquin, "From Klein Bottles to Modular Super-Bottles'),
               "= OpenAlex W2526589786 (2016) of A5040375281."),
            ID("openalex_verified_by_publication_list", Q(SQPUB, 'Séquin, "From Seifert Surfaces to Star Cinders'),
               "= OpenAlex W2968151089 (2019) of A5040375281."),
            ID("openalex_verified_by_publication_list", Q(SQPUB, 'Séquin, "Two complementary ways of linking math and art'),
               "= OpenAlex W3037196114 (2020) of A5040375281."),
            ID("orcid_record", SE("https://orcid.org/0000-0002-0060-2162/person.json", '"title":"Carlo Sequin (0000-0002-0060-2162)',
                                  '"publicGroupedResearcherUrls":{"http://www.cs.berkeley.edu/~sequin/"', raw=True, must=["Sequin"]),
               ("ORCID record names Carlo Sequin (other name 'Carlo H. Sequin') and links his Berkeley homepage; its "
                "affiliationGroups.json (sha256 fcbc07d0...) lists EMPLOYMENT 'University of California Berkeley | EECS, "
                "Computer Science | Prof | 1977-2014'.")),
        ]),
    appt=[Q(SQ, "Carlo H. Séquin Professor of Computer Science, CS Division, EECS Dept., U.C. Berkeley")],
    pi_must=["Séquin"],
    notes=("Emeritus (listed 'Professor Emeritus, Professor in the Graduate School' from the 2016 listings) but runs an "
           "active undergraduate/MS research group: his own page lists students supervised every term from 2015/16 "
           "through Fall 2024 (URAP / CS299 / JIPCAD and NOME CAD projects) -- 95 people recorded here "
           "(92 undergraduates, 3 M.S.: Andy Yu Wang 2016, Gauthier Dieppedalle 2018, Randy Fan 2021). The EECS "
           "dissertations page stops at 2013 (last PhD James Andrews), which is why the pipeline found no advising "
           "records. Several 2017-2024 EECS tech reports are co-authored with these students (Y. Amir, R. Jawale, "
           "H. Jeon, A. Romano, R. Taori 2017; B. Aronowitz 2019; M. Tang 2020, 2024). OpenAlex also has single-work "
           "junk author records that fold a whole byline into one name (e.g. A5003224430 'Yifat Amir and Carlo H. "
           "Séquin', A5078546973 'Peter Alexander Generao and Carlo H. Séquin'); not anchored."),
)

# ============================================================================ Bernd Sturmfels (pi)
BS = "https://math.berkeley.edu/~bernd/"
BSSTU = BS + "students.html"
BSART = BS + "articles.html"
PASTPHD = "https://math.berkeley.edu/people/past-department-members/past-phd-students"
PASTPHD1 = PASTPHD + "?page=1"
_bs_mgp = [("Yulia Alexandr", "Alexandr, Yulia University of California, Berkeley 2023", 2023),
           ("Madeline Brandt", "Brandt, Madeline University of California, Berkeley 2020", 2020),
           ("Yassine El Maazouz", "El Maazouz, Yassine University of California, Berkeley 2022", 2022),
           ("Joe Kileel", "Kileel, Joe University of California, Berkeley 2017", 2017),
           ("Bo Lin", "Lin, Bo University of California, Berkeley 2017", 2017),
           ("Yelena Mandelshtam", "Mandelshtam, Yelena University of California, Berkeley 2024", 2024),
           ("Elina Robeva", "Robeva, Elina University of California, Berkeley 2016", 2016),
           ("Anna Seigal", "Seigal, Anna University of California, Berkeley 2019", 2019),
           ("Emmanuel Tsukerman", "Tsukerman, Emmanuel University of California, Berkeley 2017", 2017),
           ("Madeleine Weinstein", "Weinstein, Madeleine University of California, Berkeley 2021", 2021),
           ("Leon Zhang", "Zhang, Leon University of California, Berkeley 2021", 2021)]
_bs_students = diss_students("Bernd Sturmfels")  # Lynn Chua (EECS, 2020)
for _n, _q, _y in _bs_mgp:
    _bs_students.append(ST(_n, "phd", [None, _y], Q(MGP_STURMFELS, _q),
                           note="Listed under 'Students:' on Sturmfels' Mathematics Genealogy Project page (school, PhD year)."))
_bs_students += [
    ST("Svala Sverrisdóttir", "phd", [None, 2026],
       Q(PASTPHD, "Nonlinear Algebra in Quantum Chemistry Svala Sverrisdóttir ; Bernd Sturmfels 2026 PhD Thesis (Author field refers to student + advisor)"),
       must=["Sverrisdóttir"], note="Berkeley Mathematics past-PhD listing (author field = student + advisor)."),
    ST("Lizzie Pratt", "phd", [None, 2026],
       Q(PASTPHD, "Positive and Projective Geometry Lizzie Pratt ; Bernd Sturmfels 2026 PhD Thesis (Author field refers to student + advisor)"),
       note="Berkeley Mathematics past-PhD listing (author field = student + advisor)."),
    ST("Hannah Friedman", "phd", [None, 2026],
       Q(PASTPHD1, "Metric Algebraic Geometry of Grassmannians Hannah Friedman ; Bernd Sturmfels ; Serkan Hosten 2026 PhD Thesis (Author field refers to student + advisor)"),
       note="Berkeley Mathematics past-PhD listing, co-advised with Serkan Hosten."),
    ST("Smita Rajan", "phd", None, SE(BSSTU, "PhD Students Supervised: Current:", "Smita Rajan (joint with H. Larson)"),
       note="Current PhD student on Sturmfels' own students page; on the Berkeley Mathematics graduate-student directory (math.berkeley.edu/people/graduate-students, [email removed])."),
    ST("Madeleine Goertz", "phd", None, SE(BSSTU, "PhD Students Supervised: Current:", "Madeleine Goertz"),
       note="Current PhD student (joint with S. Hosten) on Sturmfels' own students page; on the Berkeley Mathematics graduate-student directory ([email removed])."),
]

D["Bernd Sturmfels"] = dict(
    status="pi",
    status_ev=[
        diss_status("Bernd Sturmfels"),
        Q(PASTPHD, "Positive and Projective Geometry Lizzie Pratt ; Bernd Sturmfels 2026 PhD Thesis (Author field refers to student + advisor)"),
        SE(MGP_STURMFELS, "According to our current on-line database, Bernd Sturmfels", "students and 199 descendants."),
    ],
    students=_bs_students,
    identity=dict(
        orcid=[], openalex=["A5027670183"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5027670183", "Bernd Sturmfels"),
               "OpenAlex author record (552 works; last institutions MPI MiS Leipzig and UC Berkeley)."),
            ID("openalex_verified_by_publication_list", SE(BSART, "Articles | Bernd Sturmfels", "The Logarithmic A-Discriminant"),
               "Own Articles page, entry 337 = OpenAlex W7222919436 (2026) of A5027670183. 99 of the id's 149 works dated 2016+ match titles on this page."),
            ID("openalex_verified_by_publication_list", SE(BSART, "Articles | Bernd Sturmfels", "Positive Geometries from Cubic Surfaces"),
               "Entry 336 = OpenAlex W7161012334 (2026)."),
            ID("openalex_verified_by_publication_list", SE(BSART, "Articles | Bernd Sturmfels", "Landau Analysis in the Grassmannian"),
               "Entry 335 = OpenAlex W7141481859 (2026)."),
            ID("openalex_verified_by_publication_list", SE(BSART, "Articles | Bernd Sturmfels", "Multigraded Hurwitz Forms"),
               "Entry 334 = OpenAlex W7131387278 (2026)."),
        ]),
    appt=[SE(BS, "Bernd Sturmfels Director at the Max Planck Institute", "University of California at Berkeley")],
    notes=("Emeritus since ~2023/24 (EECS listings: 'Professor' through 2023, 'Professor Emeritus' from 2024); also Director "
           "at MPI MiS Leipzig since 2017. His Berkeley students are mostly Mathematics PhDs, invisible to the EECS-only "
           "advising sources: 1 EECS dissertation (Lynn Chua 2020, joint with A. Chiesa), 11 Berkeley PhDs 2016-2024 on "
           "MGP, 3 Berkeley 2026 PhDs on the Math department's past-PhD listing, and 2 current Berkeley Math PhD students "
           "(his page + the Math grad directory). His MGP list also has Leipzig/TU Berlin students (Görlach, Marigliano, "
           "Kohn, Timme, Meroni, Fevola, Pavlov, Rose, Wiesmann, ...) -- not Berkeley, excluded; his postdoc page has no "
           "years/locations, so no postdocs recorded. ORCID 0000-0002-6642-1479 is on the OpenAlex record but its ORCID "
           "record lists no institution and his pages do not link it, so it is not anchored."),
)

# ============================================================================ Richard M. Karp (not_pi_in_window)
D["Richard M. Karp"] = dict(
    status="not_pi_in_window",
    status_ev=[
        diss_newest("Richard M. Karp", "Luqman Hodgkinson [2013]"),
        Q(MGP_KARP, "According to our current on-line database, Richard Karp has 44 students and 549 descendants."),
        Q(L2017, "Richard M. Karp Professor 621 Soda Hall"),
        Q(L2019, "Richard M. Karp Professor Emeritus"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[SE("https://www2.eecs.berkeley.edu/Faculty/Homepages/karp.html", "Richard M. Karp Professor Emeritus", "Contact Information")],
    notes=("No stated advisee in 2016-2026. His newest dissertation is 2013 (Luqman Hodgkinson) on both the EECS "
           "dissertations page and MGP (44 students, newest 2013; nothing later). Active 'Professor' in the Dec 2015 "
           "and Nov 2017 EECS lists, 'Professor Emeritus' from the Jul 2019 list, i.e. retired c. 2018 without a "
           "post-2013 student. His 2016+ papers (Random Knockout Tournaments 2016/17, MPC matching/MIS 2018/19, IEOR "
           "union bounds 2025) are collaborations, none naming an advisee; he was founding director of the Simons "
           "Institute 2012-2017 (institute fellows are not his lab). EECS biography: 'He has supervised thirty-six "
           "Ph.D. dissertations.' Identity not anchored: OpenAlex candidate A5068875104 'Richard M. Karp' (380 works, "
           "7 dated 2016+) -- too few 2016+ works on any own list to verify. Status is the closest listed reason "
           "(retired during the window, no student since 2013)."),
)

# ============================================================================ Beresford N. Parlett (not_pi_in_window)
D["Beresford N. Parlett"] = dict(
    status="not_pi_in_window",
    status_ev=[
        SE("https://www2.eecs.berkeley.edu/Faculty/Homepages/parlett.html", "Parlett retired in 1994", "Beresford Parlett passed away on February 7, 2026."),
        Q(MGP_PARLETT, "According to our current on-line database, Beresford Parlett has 26 students and 82 descendants."),
        Q(MEMORIAM, "Beresford N. Parlett 1932 - 2026"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Retired in 1994 (EECS profile), died 7 Feb 2026. MGP lists 26 students; the newest Berkeley PhD is 1997 "
           "(Inderjit Dhillon) and the only later one is Jason Slemons (University of Washington, 2008), so no Berkeley "
           "advisee in 2016-2026. No EECS dissertations-by-faculty page (404)."),
)

# ============================================================================ Lawrence A. Rowe (not_pi_in_window)
D["Lawrence A. Rowe"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q("https://www2.eecs.berkeley.edu/Faculty/Homepages/rowe.html", "Professor Lawrence A. Rowe retired from the University in June 2003 after twenty-seven years"),
        diss_newest("Lawrence A. Rowe", "Amar S. Chaudhary [2001]"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes="Retired June 2003 (EECS profile); newest EECS dissertation 2001 (Amar S. Chaudhary). No advisee since.",
)

# ============================================================================ Alan J. Smith (not_pi_in_window)
D["Alan J. Smith"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(L2015, "Alan J. Smith Professor Emeritus 192 Soda Hall"),
        diss_newest("Alan J. Smith", "Windsor Wee Sun Hsu [2002]"),
        Q(MGP_SMITH, "According to our current on-line database, Alan Smith has 11 students and 62 descendants."),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Already 'Professor Emeritus' in the Dec 2015 EECS faculty list; newest dissertation 2002 (Windsor Hsu) on "
           "the EECS page and on MGP (11 students, 1979-2002); his homepage publication list was 'Last Updated April, "
           "2009' (last entry 2009). NAMESAKE WARNING: the sweep's dominant 'Alan Smith' at Berkeley, OpenAlex "
           "A5105837080 (81 Berkeley-affiliated hits, ORCID 0000-0003-2095-631X), is Alan R. Smith, the fern "
           "taxonomist at the UC Berkeley University Herbarium (Valley Life Sciences Bldg.) -- it must not be attached "
           "to this lab. That explains student_cause 'adviser_name_unmatched_or_namesake'. Identity not anchored."),
)

# ============================================================================ Michael Stonebraker (not_pi_in_window)
D["Michael Stonebraker"] = dict(
    status="not_pi_in_window",
    status_ev=[
        SE("https://www2.eecs.berkeley.edu/Faculty/Homepages/stonebraker.html", "Michael Stonebraker is a pioneer", "for twenty-nine years."),
        Q(WIKI + "Michael_Stonebraker", "Stonebraker's career can be broadly divided into two phases: his time at University of California, Berkeley when he focused on relational database management systems such as Ingres and Postgres , and, starting in 2001, at Massachusetts Institute of Technology (MIT)"),
        diss_newest("Michael Stonebraker", "Paul M. Aoki [1999]"),
        Q(MGP_STONEBRAKER, "According to our current on-line database, Michael Stonebraker has 31 students and 199 descendants."),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Left Berkeley for MIT c. 2000-2001 (taught at Berkeley 29 years from 1971; MIT from 2001; EECS profile: "
           "'presently an Adjunct Professor of Computer Science at M.I.T.'). Newest Berkeley PhD 1999 (Paul Aoki); his "
           "only later MGP student is Leilani Battle (MIT, 2017) -- an MIT advisee, not Berkeley. Emeritus title only."),
)

# ============================================================================ Elwyn R. Berlekamp (not_pi_in_window)
D["Elwyn R. Berlekamp"] = dict(
    status="not_pi_in_window",
    status_ev=[
        SE("https://www2.eecs.berkeley.edu/Faculty/Homepages/berlekamp.html", "Elwyn Ralph Berlekamp was born", "retired in 2002."),
        Q(MEMORIAM, "Elwyn Berlekamp 1940 - 2019"),
        Q(MGP_BERLEKAMP, "According to our current on-line database, Elwyn Berlekamp has 15 students and 47 descendants."),
        diss_newest("Elwyn R. Berlekamp", "David S. Wolfe [1991]"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Retired 2002 (EECS profile), died 9 Apr 2019. Newest PhD on MGP is Aaron Siegel (Berkeley Math, 2005); "
           "EECS dissertations end 1991. No advisee in 2016-2026."),
)

# ============================================================================ Chittoor V. Ramamoorthy (not_pi_in_window)
D["Chittoor V. Ramamoorthy"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(MEMORIAM, "Chittoor Vijayaraghavalu “Ram” Ramamoorthy 1926 - 2016"),
        Q(WIKI + "C._V._Ramamoorthy", "Chittoor V. Ramamoorthy Born May 5, 1926 Rangoon , Burma Died March 9, 2016"),
        diss_newest("Chittoor V. Ramamoorthy", "Keith B. Vanderveen [1998]"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[Q("https://www2.eecs.berkeley.edu/Faculty/Homepages/ramamoorthy.html", "Chittoor V. Ramamoorthy Former Professor Emeritus")],
    pi_must=["Ramamoorthy"],
    notes=("Retired from UC Berkeley in 1994 (Wikipedia: 'In 1994, he retired from UC Berkeley and became professor "
           "emeritus after having mentored 73 Ph.D. students'); died 9 March 2016. Newest EECS dissertation 1998."),
)

# ============================================================================ Lotfi A. Zadeh (not_pi_in_window)
D["Lotfi A. Zadeh"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q("https://www2.eecs.berkeley.edu/Faculty/Homepages/zadeh.html", "Lotfi Zadeh passed away on September 6, 2017."),
        Q(MEMORIAM, "Lotfi Zadeh 1921 - 2017"),
        diss_newest("Lotfi A. Zadeh", "Keith B. Vanderveen [1998]"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[Q("https://www2.eecs.berkeley.edu/Faculty/Homepages/zadeh.html", "Lotfi Zadeh was a Professor in the Graduate School of the Computer Science Division of Berkeley EECS.")],
    notes=("Professor in the Graduate School (emeritus) who died 6 Sep 2017; newest EECS dissertation 1998. His 2014-2016 "
           "EECS 'publications' are patents. No advisee in 2016-2017."),
)
