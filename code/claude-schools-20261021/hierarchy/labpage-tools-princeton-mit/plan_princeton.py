"""Reviewed lab-page plan for Princeton (see lpauto.py for the keys). Pages were chosen by reading the discovery
dossier (dossier_princeton.json), autom/peek listings and the pages themselves; notes say what was used and why."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lpev import M, MS, P as Pub, Pubs  # noqa: E402,F401

SCH = "princeton"
P = {}
from lpauto import R, RS  # noqa: E402

# ---------------------------------------------------------------- Aarti Gupta
P["Aarti Gupta"] = dict(
    site="https://www.cs.princeton.edu/~aartig/",
    people=["https://www.cs.princeton.edu/~aartig/", "https://www.cs.princeton.edu/~aartig/group.html"],
    wb=["https://www.cs.princeton.edu/~aartig/", "https://www.cs.princeton.edu/~aartig/group.html"],
    alumni_ok=True,
    pubs=[],
    notes=("Group section of the homepage (graduate students, graduated students with dates, post-doctoral fellows) "
           "and the older group.html (current graduate students, post-doctoral fellows, visitor students). She joined "
           "Princeton in 2015 from NEC Labs (industry), so every listed student is a Princeton student. No publications "
           "page (the homepage links DBLP; projs.html is a project list)."),
)

# ---------------------------------------------------------------- Adam Finkelstein
P["Adam Finkelstein"] = dict(
    site="https://www.cs.princeton.edu/~af/",
    notes=("Homepage (~af/) has no students, group or publications page; it links the PIXL graphics group "
           "(pixl.cs.princeton.edu, not reachable as a member list). No lab members page found."),
)

# ---------------------------------------------------------------- Adji Bousso Dieng
P["Adji Bousso Dieng"] = dict(
    site="https://vertaix.princeton.edu/",
    people=["https://vertaix.princeton.edu/people"],
    wb=["https://vertaix.princeton.edu/people"],
    drop=["Annie T. Randall Innovator"],
    alumni_ok=True,
    pubs=[Pubs("https://vertaix.princeton.edu/publications")],
    notes="Vertaix people page (one card per member with role). First faculty job (2021), so all members are Princeton.",
)

# ---------------------------------------------------------------- Aleksandra Korolova
P["Aleksandra Korolova"] = dict(
    site="https://www.korolova.com/",
    rows=R(SCH, "https://korolova.com/", [
        ("Maya", "member", [2026, 2026], "Excited to welcome Maya and Katie to my research group and to co-advise them with Jonathan Mayer"),
        ("Katie", "member", [2026, 2026], "Excited to welcome Maya and Katie to my research group and to co-advise them with Jonathan Mayer"),
    ], note="news item (Sep 2026), first names only"),
    pubs=[Pubs("https://korolova.com/publications")],
    notes=("No members page: korolova.com has news items and a publications page. The Sep 2026 news item welcomes "
           "'Maya and Katie' to the group (co-advised with Jonathan Mayer); first names only."),
)

# ---------------------------------------------------------------- Alex Lombardi
P["Alex Lombardi"] = dict(
    site="https://sites.google.com/view/alex-lombardi/home",
    notes="Academic home page (Google Sites) has no students/group section and no separate publications page.",
)

# ---------------------------------------------------------------- Amit Levy
P["Amit Levy"] = dict(
    site="https://amitlevy.com/",
    people=["https://amitlevy.com/"],
    wb=["https://amitlevy.com/"],
    alumni_ok=True,
    pubs=[Pubs("https://amitlevy.com/publications/")],
    notes=("Homepage lists PhD students and alumni (with degree years). He joined Princeton in 2018 after a Stanford "
           "PhD/postdoc; the alumni listed graduated 2022-2024 at Princeton."),
)

# ---------------------------------------------------------------- Andrés Monroy-Hernández
P["Andrés Monroy-Hernández"] = dict(
    site="https://hci.princeton.edu/",
    people=["https://hci.princeton.edu/people/"],
    wb=["https://hci.princeton.edu/people/"],
    alumni_ok=True,
    pubs=[Pubs("https://hci.princeton.edu/publications-1/")],
    notes=("The lab is the Princeton HCI Group; its people page (postdocs and researchers, graduate students, alumni) "
           "is shared with Parastoo Abtahi, Manoel Horta Ribeiro and Janet Vertesi and does not state advisors, so rows "
           "here are HCI-group members, not necessarily his advisees. Faculty and Collaborators sections left out. "
           "His homepage andresmh.com has no advisee list."),
)

# ---------------------------------------------------------------- Andrew Appel
P["Andrew Appel"] = dict(
    site="https://www.cs.princeton.edu/~appel/",
    people=["https://www.cs.princeton.edu/~appel/students.html"],
    wb=["https://www.cs.princeton.edu/~appel/students.html"],
    roles={"Yichen Tao": "phd", "Dennis Corraliza": "phd", "Tim Welch": "phd"},
    pubs=[Pubs("https://www.cs.princeton.edu/~appel/papers/")],
    notes=("students.html: former students with PhD years (pre-2016 graduates dropped) and current students. VST "
           "project page (vst.cs.princeton.edu) lists collaborators, not used."),
)

# ---------------------------------------------------------------- Arvind Narayanan
P["Arvind Narayanan"] = dict(
    site="https://www.cs.princeton.edu/~arvindn/",
    people=["https://www.cs.princeton.edu/~arvindn/advising", "https://sage.cs.princeton.edu/"],
    wb=["https://www.cs.princeton.edu/~arvindn/advising", "https://sage.cs.princeton.edu/"],
    drop=["Life After Benchmark Saturation"],
    alumni_ok=True,
    pubs=[Pubs("https://www.cs.princeton.edu/~arvindn/publications")],
    notes=("Advising page (dated advisees) and the SAgE group page (team, alumni; Collaborators section left out). "
           "At Princeton since 2012; SAgE alumni are recent group members."),
)

# ---------------------------------------------------------------- Bartolomeo Stellato
P["Bartolomeo Stellato"] = dict(
    site="https://stella.to/",
    people=["https://stella.to/group/"],
    wb=["https://stella.to/group/", "https://stellato.io/group/"],
    alumni_ok=True,
    pubs=[Pubs("https://stella.to/publications")],
    notes="stella.to/group (postdocs, graduate students, postgraduate researchers, undergraduates, alumni). First faculty job (Princeton 2020).",
)

# ---------------------------------------------------------------- Benjamin Eysenbach
P["Benjamin Eysenbach"] = dict(
    site="https://princeton-rl.github.io/",
    people=["https://princeton-rl.github.io/"],
    wb=["https://princeton-rl.github.io/"],
    alumni_ok=True,
    pubs=[],
    notes="Princeton RL lab page lists members. First faculty job (Princeton 2023). No publications page found.",
)

# ---------------------------------------------------------------- Bernard Chazelle
P["Bernard Chazelle"] = dict(
    site="https://www.cs.princeton.edu/~chazelle/",
    pubs=[Pubs("https://www.cs.princeton.edu/~chazelle/pubs.html")],
    notes="Homepage has no students or group list. Publications page pubs.html.",
)

# ---------------------------------------------------------------- Brian Kernighan
P["Brian Kernighan"] = dict(
    site="https://www.cs.princeton.edu/~bwk/",
    pubs=[Pubs("https://www.cs.princeton.edu/~bwk/bwkbib.html")],
    notes="Homepage has no students or group list. Bibliography page bwkbib.html.",
)

# ---------------------------------------------------------------- Chi Jin
P["Chi Jin"] = dict(
    site="https://sites.google.com/view/cjin/home",
    people=["https://sites.google.com/view/cjin/group"],
    wb=["https://sites.google.com/view/cjin/group"],
    alumni_ok=True,
    pubs=[Pubs("https://sites.google.com/view/cjin/publications")],
    notes="Google Sites group page. First faculty job (Princeton 2019).",
)

# ---------------------------------------------------------------- Ellen Zhong
P["Ellen Zhong"] = dict(
    site="https://ezlab.princeton.edu/",
    people=["https://ezlab.princeton.edu/team/"],
    wb=["https://ezlab.princeton.edu/team/"],
    alumni_ok=True,
    pubs=[Pubs("https://ezlab.princeton.edu/publications/")],
    notes="EZ Lab team page. First faculty job (Princeton 2022).",
)

# ---------------------------------------------------------------- Felix Heide
P["Felix Heide"] = dict(
    site="https://light.princeton.edu/",
    people=["https://light.princeton.edu/team/"],
    wb=["https://light.princeton.edu/team/"],
    alumni_ok=True,
    pubs=[Pubs("https://light.princeton.edu/publications/")],
    notes="Princeton Computational Imaging Lab team page. First faculty job (Princeton 2018).",
)

# ---------------------------------------------------------------- Elad Hazan
P["Elad Hazan"] = dict(
    site="https://www.ehazan.com/",
    people=["https://www.ehazan.com/students/", "https://www.minregret.com/people/"],
    wb=["https://www.ehazan.com/students/", "https://www.minregret.com/people/"],
    pubs=[],
    notes=("Students page on ehazan.com and the MinRegret lab people page. At Princeton since 2015 after the Technion; "
           "undated alumni are kept only when a 2016+ capture lists them as current."),
)

# ---------------------------------------------------------------- Elad Hazan (correction)
P["Elad Hazan"].update(
    drop=["Oren Anava", "Jennifer Sun D.E Shaw"],
    rows=R(SCH, "https://www.minregret.com/people/", [
        ("Jennifer Sun", "phd", None, "Former Xinyi Chen Research Scientist at Google DeepMind Edgar Minasyan Research Scientist at Nvidia Nataly Brukhim Postdoc at Institute for Advanced Study Udaya Ghai Senior Applied Scientist at AWS Wenhan Xia Research Engineer at Google Research Jennifer Sun"),
    ], note="MinRegret 'Former' list (his PhD alumni); role from the ehazan.com students page"),
    auto=["https://www.ehazan.com/students/", "https://www.minregret.com/people/"],
)
P["Elad Hazan"]["notes"] += (" The ehazan.com list also names his Technion students (Tomer Koren, Dan Garber, Kfir Levy, Oren "
                             "Anava), left out.")

# ---------------------------------------------------------------- Ben Raphael
P["Ben Raphael"] = dict(
    site="https://raphael-group.github.io/",
    people=["https://raphael-group.github.io/people/"],
    wb=["https://raphael-group.github.io/people/"],
    pubs=[Pubs("https://raphael-group.github.io/publications/")],
    notes=("Raphael Lab people page: current members with start dates and former members with dates. He moved from "
           "Brown in 2016; former members dated before 2016 (Brown) are dropped, undated former members count only when "
           "a 2016+ capture lists them as current."),
)

# ---------------------------------------------------------------- Brenden Lake
P["Brenden Lake"] = dict(
    site="https://lake-lab.github.io/",
    people=["https://lake-lab.github.io/people/"],
    wb=["https://lake-lab.github.io/people/"], wb_from=2025,
    pubs=[Pubs("https://lake-lab.github.io/publications/")],
    notes=("Lake Lab people page. He moved from NYU in 2025: the 'Lab alumni' are NYU members and are left out; "
           "Wayback captures before 2025 (NYU era) are not used."),
)

# ---------------------------------------------------------------- Christine Allen-Blanchette
P["Christine Allen-Blanchette"] = dict(
    site="https://cablanc.github.io/",
    notes=("Homepage has no group/members list. ML4PEARL (ml4pearl.github.io), the lab she co-founded as a postdoc with "
           "a University of Chicago fellow, lists two research assistants without affiliation; not used."),
)

# ---------------------------------------------------------------- Dan Trueman
P["Dan Trueman"] = dict(
    site="https://music.princeton.edu/people/dan-trueman",
    notes="Music faculty profile (Wayback; live music.princeton.edu serves a bot challenge). No lab or members page.",
)

# ---------------------------------------------------------------- Danqi Chen
P["Danqi Chen"] = dict(
    site="https://www.cs.princeton.edu/~danqic/",
    people=["https://www.cs.princeton.edu/~danqic/lab.html"],
    wb=["https://www.cs.princeton.edu/~danqic/lab.html"],
    drop=["Peter Henderson"],
    alumni_ok=True,
    pubs=[Pubs("https://www.cs.princeton.edu/~danqic/papers.html")],
    notes=("lab.html (current members, alumni with degree years). First faculty job (Princeton 2019). The Princeton NLP "
           "group page (princeton-nlp.github.io/people) is shared with other NLP faculty and was not attributed."),
)

# ---------------------------------------------------------------- David August
P["David August"] = dict(
    site="https://liberty.princeton.edu/",
    pubs=[Pubs("https://liberty.princeton.edu/Publications/")],
    notes=("liberty.princeton.edu (and its People/ page) is his personal page with selected publications; no member "
           "list. Publications page used."),
)

# ---------------------------------------------------------------- David Walker
P["David Walker"] = dict(
    site="https://www.cs.princeton.edu/~dpw/",
    people=["https://www.cs.princeton.edu/~dpw/coauthors.htm"],
    pubs=[Pubs("https://www.cs.princeton.edu/~dpw/papers.html")],
    notes=("'Students & Co-authors' page: current PhD students/postdocs, former students (undated, mostly before "
           "2016, left out unless dated), undergraduate advisees with terms."),
)

# ---------------------------------------------------------------- simple homepage / group-page labs
def lab(site, people=(), wb=None, pubs=(), notes="", **kw):
    d = dict(site=site, people=list(people), wb=list(people) if wb is None else list(wb), pubs=list(pubs), notes=notes)
    d.update(kw)
    return d


P["David Wentzlaff"] = lab("https://parallel.princeton.edu/", ["https://parallel.princeton.edu/people.html"],
                           pubs=[Pubs("https://parallel.princeton.edu/pubs.html")], alumni_ok=True,
                           notes="Princeton Parallel Group people page. First faculty job (Princeton 2012).")
P["Jia Deng"] = lab("https://pvl.cs.princeton.edu/", ["https://pvl.cs.princeton.edu/people.html"], alumni_ok=True,
                    notes="Princeton Vision & Learning Lab people page. He joined Princeton in 2018 from Michigan; alumni are the lab's Princeton alumni per the page.")
P["Jason Lee"] = lab("https://jasondlee88.github.io/", ["https://jasondlee88.github.io/group.html"],
                     pubs=[Pubs("https://jasondlee88.github.io/publications.html")],
                     notes="Group page. At Princeton 2019-2025 after USC (2016-2019), now at Berkeley: undated alumni count only when a 2019+ capture lists them as current.",
                     wb_from=2019)
P["Jennifer Rexford"] = lab("https://www.cs.princeton.edu/~jrex/", ["https://www.cs.princeton.edu/~jrex/"],
                            pubs=[Pubs("https://www.cs.princeton.edu/~jrex/publications.html")],
                            notes="Homepage lists current and former students/postdocs. At Princeton since 2005.")
P["Jialin Ding"] = lab("https://jialinding.github.io/", ["https://jialinding.github.io/"], alumni_ok=True,
                       notes="Homepage (students section). First faculty job (Princeton 2025).")
P["Kai Li"] = lab("https://www.cs.princeton.edu/~li/", ["https://www.cs.princeton.edu/~li/"],
                  notes="Homepage lists current and former students (former mostly before 2016, kept only when dated or seen current on a 2016+ capture).")
P["Karthik Narasimhan"] = lab("https://karthiknarasimhan.com/", ["https://karthiknarasimhan.com/lab/"], alumni_ok=True,
                              notes="Lab page. First faculty job (Princeton 2018).")
P["Lydia Liu"] = lab("https://www.lydiatliu.com/", ["https://www.lydiatliu.com/group/"], alumni_ok=True,
                     notes="Group page. First faculty job (Princeton 2024).")
P["Mae Milano"] = lab("https://www.languagesforsyste.ms/", ["https://www.languagesforsyste.ms/"], alumni_ok=True,
                      drop=["Andrew Appel’s"], pubs=[Pubs("https://www.languagesforsyste.ms/publication/")],
                      notes="Homepage group section. First faculty job (Princeton 2024).")
P["Margaret Martonosi"] = lab("https://mrmgroup.cs.princeton.edu/", ["https://mrmgroup.cs.princeton.edu/"],
                              wb=["https://mrmgroup.cs.princeton.edu/"], alumni_ok=True,
                              notes="MRM group page (members, alumni). At Princeton since 1994.")
P["Mark Braverman"] = lab("https://mbraverm.princeton.edu/", ["https://mbraverm.princeton.edu/team/members/",
                                                             "https://mbraverm.princeton.edu/team/undergraduate-projects/"],
                          pubs=[Pubs("https://mbraverm.princeton.edu/research/all-papers/")],
                          notes="Team members and undergraduate projects pages. At Princeton since 2011 (Toronto before).")
P["Matthew Weinberg"] = lab("https://www.cs.princeton.edu/~smattw/", ["https://www.cs.princeton.edu/~smattw/Students.html"],
                            alumni_ok=True, notes="Students page. First faculty job (Princeton 2016).")
P["Mona Singh"] = lab("https://www.cs.princeton.edu/~mona/", ["https://www.cs.princeton.edu/~mona/group.html"],
                      pubs=[Pubs("https://www.cs.princeton.edu/~mona/publications.html")],
                      notes="Group page. At Princeton since 1999.")
P["Olga Russakovsky"] = lab("https://visualai.princeton.edu/", ["https://visualai.princeton.edu/people.html"], alumni_ok=True,
                            notes="Visual AI Lab people page (first faculty job, Princeton 2017). The page is shared with Ruth Fong's group members.")
P["Olga Troyanskaya"] = lab("https://function.princeton.edu/", ["https://function.princeton.edu/people/"],
                            pubs=[Pubs("https://function.princeton.edu/publications/")],
                            notes="Troyanskaya Lab people page. At Princeton since 2003.")
P["Parastoo Abtahi"] = lab("https://parastooabtahi.com/", ["https://parastooabtahi.com/team"], alumni_ok=True,
                           notes="Team page. First faculty job (Princeton 2023).")
P["Ravi Netravali"] = lab("https://sysml.cs.princeton.edu/", ["https://sysml.cs.princeton.edu/people.html"],
                          pubs=[Pubs("https://sysml.cs.princeton.edu/publications.html")],
                          notes="Princeton SysML group people page. He was at UCLA 2019-2021 before Princeton (2021): undated alumni count only when a 2021+ capture lists them as current.",
                          wb_from=2021)
P["Ryan Adams"] = lab("https://lips.cs.princeton.edu/", ["https://lips.cs.princeton.edu/people/"],
                      pubs=[Pubs("https://lips.cs.princeton.edu/pubs/")], wb_from=2016,
                      notes="LIPS people page. He moved from Harvard (2011-2016) in 2016/17: undated alumni count only when a 2016+ capture lists them as current.")
P["Sanjeev Arora"] = lab("https://aroraresearch-princeton.github.io/", ["https://aroraresearch-princeton.github.io/pages/team.html"],
                         pubs=[Pubs("https://aroraresearch-princeton.github.io/pages/publications.html")], alumni_ok=True,
                         notes="Arora research group team page (Princeton group).")
P["Sebastian Seung"] = lab("https://seunglab.org/", ["https://seunglab.org/"], wb_from=2016,
                           notes="Seung Lab homepage people section. He moved from MIT in 2014; undated alumni count only when a 2016+ capture lists them as current.")
P["Tom Griffiths"] = lab("https://cocosci.princeton.edu/", ["https://cocosci.princeton.edu/people.php"],
                         pubs=[Pubs("https://cocosci.princeton.edu/publications.php")], wb_from=2018,
                         notes="Computational Cognitive Science Lab people page. He moved from Berkeley in 2018; Berkeley-era alumni are left out unless a 2018+ capture lists them as current.")
P["Tri Dao"] = lab("https://dao-lab.ai/", ["https://dao-lab.ai/"], alumni_ok=True,
                   pubs=[Pubs("https://dao-lab.ai/publications/")], notes="Dao AI Lab page. First faculty job (Princeton 2024).")
P["Wyatt Lloyd"] = lab("https://www.cs.princeton.edu/~wlloyd/", ["https://www.cs.princeton.edu/~wlloyd/"],
                       pubs=[Pubs("https://www.cs.princeton.edu/~wlloyd/publications.html")],
                       notes="Homepage students section. He was at USC 2015-2017 before Princeton: undated alumni count only when a 2017+ capture lists them as current.",
                       wb_from=2017)
P["Yuri Pritykin"] = lab("https://pritykinlab.github.io/", ["https://pritykinlab.github.io/people/"], alumni_ok=True,
                         notes="Pritykin Lab people page. First faculty job (Princeton 2021).")
P["Yuxin Chen"] = lab("https://yuxinchen2020.github.io/", ["https://yuxinchen2020.github.io/Group.html"],
                      wb=["https://yuxinchen2020.github.io/Group.html", "http://www.princeton.edu/~yc5/"], wb_from=2017,
                      pubs=[Pubs("https://yuxinchen2020.github.io/Publications_year.html")],
                      notes="Group page. He was at Princeton 2017-2022 and is now at UPenn: current members are Penn people; only alumni dated to the Princeton years or seen current on a 2017-2022 capture count.")
P["Pravesh Kothari"] = lab("https://www.cs.princeton.edu/~kothari/", ["https://www.cs.princeton.edu/~kothari/"],
                           pubs=[Pubs("https://www.cs.princeton.edu/~kothari/papers.html")], wb_from=2023,
                           notes="Homepage students section. He moved from CMU in 2023; CMU students are left out unless the page places them at Princeton.")
P["Ruth Fong"] = lab("https://www.ruthfong.com/", ["https://www.ruthfong.com/"], alumni_ok=True,
                     notes="Homepage mentees section (teaching faculty at Princeton since 2021).")
P["Zachary Kincaid"] = lab("https://www.cs.princeton.edu/~zkincaid/", ["https://www.cs.princeton.edu/~zkincaid/"], alumni_ok=True,
                           pubs=[Pubs("https://www.cs.princeton.edu/~zkincaid/publications.html")],
                           notes="Homepage students section. First faculty job (Princeton 2016).")
P["Zeev Dvir"] = lab("https://www.cs.princeton.edu/~zdvir/", ["https://www.cs.princeton.edu/~zdvir/"],
                     pubs=[Pubs("https://www.cs.princeton.edu/~zdvir/publications.html")],
                     notes="Homepage; students listed there when present.")
P["Szymon Rusinkiewicz"] = lab("https://www.cs.princeton.edu/~smr/", ["https://www.cs.princeton.edu/~smr/"],
                               notes="Homepage (students/advisees section). PIXL group people page (pixl.engineering.princeton.edu) is shared by the graphics faculty.")
P["Thomas Funkhouser"] = lab("https://www.cs.princeton.edu/~funk/", ["https://www.cs.princeton.edu/~funk/"],
                             pubs=[Pubs("https://www.cs.princeton.edu/~funk/publications.html")],
                             notes="Homepage (students section).")
P["Zhuang Liu"] = lab("https://liuzhuang13.github.io/", ["https://liuzhuang13.github.io/"], alumni_ok=True,
                      notes="Homepage (students section). First faculty job (Princeton 2025).")
P["Victoria Dean"] = lab("https://vdean.github.io/", ["https://vdean.github.io/"], alumni_ok=True,
                         notes="Homepage. First faculty job (Princeton 2025).")
P["Warren Powell"] = lab("https://castle.princeton.edu/", ["https://castle.princeton.edu/people/"],
                         notes="CASTLE Labs people page (emeritus since 2020).")
P["Robert Sedgewick"] = lab("https://www.cs.princeton.edu/~rs/", ["https://www.cs.princeton.edu/~rs/"],
                            notes="Homepage; no group page.")
P["Robert Schapire"] = lab("http://www.schapire.net/", [], pubs=[Pubs("http://www.schapire.net/publist.html")],
                           notes="Homepage (Microsoft Research; Princeton affiliation) has no students list; publication list used.")
P["Larry Peterson"] = lab("https://www.cs.princeton.edu/~llp/", [], notes="Homepage has no students or group list.")
P["Jonathan Mayer"] = lab("https://jonathanmayer.org/", [], pubs=[Pubs("https://jonathanmayer.org/publications/")],
                          notes="Homepage has no members list; publications page used.")
P["Michael Freedman"] = lab("https://www.cs.princeton.edu/~mfreed/", [],
                            pubs=[Pubs("http://www.cs.princeton.edu/~mfreed/publications/")],
                            notes="Homepage has no students list (SNS group site sns.cs.princeton.edu times out).")
P["Robert Vanderbei"] = lab("https://vanderbei.princeton.edu/", [], pubs=[Pubs("https://vanderbei.princeton.edu/Publications.html")],
                            notes="Homepage has no group page; the CV lists students but is a CV, not a lab page.")
P["Paul Seymour"] = lab("https://web.math.princeton.edu/~pds/", [], pubs=[Pubs("https://web.math.princeton.edu/~pds/online.html")],
                        notes="Math homepage; no students list.")
P["Edward Felten"] = lab("https://www.cs.princeton.edu/~felten/", [], pubs=[Pubs("https://www.cs.princeton.edu/~felten/papers.html")],
                         notes="Homepage has no students list.")
P["Janet Vertesi"] = lab("https://janet.vertesi.com/", [], notes="Homepage has no lab members list.")
P["Gillat Kol"] = lab(None, [], notes="Only the CS profile (links Google Scholar); ~gkol returns 404. No lab site found.")
P["Ran Raz"] = lab(None, [], notes="Only the CS profile (links Google Scholar); ~ranr returns 404. No lab site found.")
P["Robert Tarjan"] = lab("https://www.cs.princeton.edu/~ret/", [], notes="Minimal homepage (~ret); no students list.")
P["Andrea LaPaugh"] = lab(None, [], notes="No homepage found (~aslapaugh returns 404).")
P["Yoram Singer"] = lab(None, [], notes="No Princeton homepage found (~ys returns 404).")

# ---------------------------------------------------------------- corrections after review
for _pi in ("David Wentzlaff", "Jia Deng", "Sanjeev Arora", "Aarti Gupta"):
    P[_pi]["alumni_ok"] = False   # long-tenured or moved from elsewhere: undated alumni need a 2016+ capture
P["David Wentzlaff"]["notes"] = ("Princeton Parallel Group people page (graduate students; alumni with their next job, "
                                 "undated). At Princeton since 2010: undated alumni count only when a 2016+ capture "
                                 "lists them as current.")
P["Jia Deng"]["notes"] = ("Princeton Vision & Learning Lab people page (students). He moved from Michigan in 2018: "
                          "undated former members count only when a 2018+ capture lists them as current.")
P["Jia Deng"]["wb_from"] = 2018
P["Margaret Martonosi"] = lab(
    "https://mrm.scholar.princeton.edu/",
    ["https://web.archive.org/web/20261012095901id_/https://mrm.scholar.princeton.edu/",
     "https://web.archive.org/web/20260922164118id_/https://mrm.scholar.princeton.edu/graduated-advisees"],
    wb=["https://mrm.scholar.princeton.edu/graduated-advisees", "https://mrm.scholar.princeton.edu/"],
    pubs=[Pubs("https://mrmgroup.cs.princeton.edu/")],
    notes=("mrm.scholar.princeton.edu (current group) and its graduated-advisees page, both via Wayback id_ captures "
           "(the live site serves a bot challenge). mrmgroup.cs.princeton.edu is the group's publications list. At "
           "Princeton since 1994: undated advisees count only when a 2016+ capture lists them as current."))
P["Jennifer Rexford"]["drop"] = ["Daily Princetonian"]
P["Jialin Ding"]["drop"] = ["Industry Experience"]
P["Olga Troyanskaya"]["drop"] = ["Simons Foundation", "Xi Chen", "Chris Park", "Natalie Sauerwald", "Rachel Sealfon",
                                 "Aaron Wong", "Aviya Litman", "Claudia Skok-Gibbs"]
P["Olga Troyanskaya"]["notes"] += (" Members whose affiliation is the Simons Foundation (Flatiron Institute) are left out "
                                   "(not at Princeton); the Collaborators section is left out.")
P["Kai Li"]["drop"] = ["Barbara Varga"]
P["Kai Li"]["notes"] += " Barbara Varga is his administrative assistant (left out)."
P["Mona Singh"]["drop"] = ["James Fife Minh Hoang"]
P["Mona Singh"]["rows"] = R(SCH, "https://www.cs.princeton.edu/~mona/group.html", [
    ("James Fife", "member", None, "Current members Isabel Armour-Garb Ariel Bruner James Fife"),
    ("Minh Hoang", "postdoc", None, "Minh Hoang, Postdoctoral Fellow"),
])
P["Mona Singh"]["auto"] = ["https://www.cs.princeton.edu/~mona/group.html"]
P["Pravesh Kothari"] = lab(
    "https://www.cs.princeton.edu/~kothari/", ["https://www.cs.princeton.edu/~kothari/"], wb=[],
    rows=R(SCH, "https://www.cs.princeton.edu/~kothari/", [
        ("Max Hopkins", "postdoc", [2024, 2025], "Max Hopkins (Fall 24-25) now postdoc at School of Math, IAS"),
        ("Stefan Tudose", "phd", None, "Current PhD Students Stefan Tudose (Math)"),
        ("Arpon Basu", "phd", None, "Current PhD Students Stefan Tudose (Math) Arpon Basu (Computer Science)"),
        ("Michael Li", "phd", None, "Current PhD Students Stefan Tudose (Math) Arpon Basu (Computer Science) Michael Li (Applied Math)"),
        ("Andrew Lin", "phd", None, "Current PhD Students Stefan Tudose (Math) Arpon Basu (Computer Science) Michael Li (Applied Math) Andrew Lin (Applied Math)"),
        ("Yukai Tang", "phd", None, "Yukai Tang (Operations Research, co-advised with Amirali Ahmadi)"),
    ], note="Advising section of the homepage"),
    pubs=[Pubs("https://www.cs.princeton.edu/~kothari/papers.html")],
    notes=("Homepage 'Advising' section. He moved from CMU in 2023: the former postdocs Alperen Ergür (2019-20) and Mitali "
           "Bafna (2022-23), the former PhD students (Ainesh Bakshi, Tim Hsieh, Peter Manohar, Xinyu Wu, Jeff Xu) and the "
           "undergraduates (SCS theses) are CMU advisees and are left out; Max Hopkins (Fall 2024-25) and the current PhD "
           "students are Princeton."))
P["Ravi Netravali"] = lab(
    "https://www.cs.princeton.edu/~ravian/", ["https://www.cs.princeton.edu/~ravian/"], wb_from=2021,
    drop=["Pradeep Dogga", "Ayush Goel", "Lei Zhang", "Arthi Padmanabhan", "Pengzhan Zhao", "Shaghayegh Mardani",
          "Lana Ramjit", "Nikhil Kansal", "Mihir Mathur", "Qualcomm Innovation Fellowship", "SIGCOMM CCR Editorial"],
    pubs=[Pubs("https://www.cs.princeton.edu/~ravian/publications.html")],
    notes=("Homepage 'Current Students and Postdocs' and 'Graduated Students'. He was at UCLA 2019-2021: graduated "
           "students not otherwise placed at Princeton (Pradeep Dogga, Ayush Goel, Lei Zhang, Arthi Padmanabhan, Pengzhan "
           "Zhao, Shaghayegh Mardani, Lana Ramjit, Nikhil Kansal, Mihir Mathur) are left out as likely UCLA advisees. The "
           "SAIL@Princeton people page (sysml.cs.princeton.edu) is a cross-lab collective with an unattributed student "
           "list and was not used."))
P["Olga Russakovsky"]["drop"] = ["Zero-Shot Semantic Segmentation", "Sofia Egan", "Alvin Kim Lyuh", "Kathy Lin", "Ellie Zhou",
                                 "Lindsey Ehrlich", "Kelly Lao", "Noa Souccar"]
P["Olga Russakovsky"]["notes"] += " High-school summer interns are left out."
P["Sebastian Seung"]["drop"] = ["Nat. Communications", "Nat. Methods"]
P["Tri Dao"]["drop"] = ["Ion Stoica", "Joey Gonzalez"]
P["Tri Dao"]["notes"] += " Ion Stoica and Joey Gonzalez appear only as co-advisors (left out)."
P["Yuxin Chen"].update(people=[], auto=[], wb=["https://yuxinchen2020.github.io/Group.html", "http://www.princeton.edu/~yc5/"],
                       wb_from=2017, wb_to=2022)
P["Yuxin Chen"]["notes"] = ("He was at Princeton 2017-2022 and is now at UPenn: the live Group page lists Penn members, so "
                            "only Wayback captures from 2017-2022 (Princeton era) of his group page / Princeton homepage "
                            "are used.")
P["Szymon Rusinkiewicz"]["span"] = {"https://www.cs.princeton.edu/~smr/": ("Students Current graduate advisees", "Collaborators"),
                                    "*": ("Students", "Collaborators")}
P["Thomas Funkhouser"]["span"] = {"https://www.cs.princeton.edu/~funk/": ("Recent Graduate Students and Postdocs", None),
                                  "*": ("Graduate Students", None)}
P["Mae Milano"]["span"] = {"https://www.languagesforsyste.ms/": ("PhD/MS Students", "Close Student Collaborators")}
P["Mae Milano"]["notes"] += " 'Close Student Collaborators' (students of other PIs) left out."
P["Zhuang Liu"]["span"] = {"https://liuzhuang13.github.io/": ("Research Group • Gabe Sarch", None)}
P["Zachary Kincaid"]["span"] = {"https://www.cs.princeton.edu/~zkincaid/": ("students ¶ current", "teaching ¶"),
                                "*": ("students", "teaching")}
P["Jialin Ding"]["span"] = {"https://jialinding.github.io/": ("Graduate Students Karan Tandon", "Conference Publications")}
P["Victoria Dean"].update(people=[], wb=[], notes="Homepage has no students list (first faculty year at Princeton, 2025).")
P["Robert Sedgewick"].update(people=[], wb=[], notes="Homepage (books, courses, media) has no students or group list.")
_RF = "https://www.ruthfong.com/"
P["Ruth Fong"] = lab(_RF, [_RF], wb=[], rows=R(SCH, _RF, [
    ("Anha Khan", "undergraduate", [None, 2026], "Alumni Anha Khan '26 and Jennifer Yan '27, UCAs (summer 2026)"),
    ("Jennifer Yan", "undergraduate", [None, 2027], "Alumni Anha Khan '26 and Jennifer Yan '27, UCAs (summer 2026)"),
    ("Alex Tao", "undergraduate", [None, 2025], "Alex Tao '25, UCA (summer 2025)"),
    ("Indu Panigrahi", "masters", [None, 2025], "Indu Panigrahi '23 *25, master's thesis (co-advised with Parastoo Abtahi)"),
    ("Rawand Aziz", "undergraduate", [None, 2025], "Rawand Aziz '25, senior thesis"),
    ("Matthew Barrett", "undergraduate", [None, 2025], "Matthew Barrett '25, senior thesis"),
    ("Emilio Chan", "undergraduate", [None, 2025], "Emilio Chan '25, senior thesis"),
    ("Ben Wachspress", "undergraduate", [None, 2025], "Ben Wachspress '25, senior thesis"),
    ("Adam Kelch", "undergraduate", [2023, 2023], "Adam Kelch '24, IW (spring 2023)"),
    ("Sai Rachumalla", "undergraduate", [2023, 2023], "Sai Rachumalla '24, IW (spring 2023)"),
    ("Creston Brooks", "undergraduate", [None, 2023], "Creston Brooks '23, senior thesis"),
    ("Alexis Sursock", "undergraduate", [None, 2023], "Alexis Sursock '23, senior thesis"),
    ("Devon Ulrich", "undergraduate", [None, 2023], "Devon Ulrich '23, senior thesis"),
    ("Rohan Jinturkar", "undergraduate", [None, 2023], "Rohan Jinturkar '23, senior thesis (co-advised with Olga Russakovsky)"),
    ("Icey Siyi", "undergraduate", [2022, 2022], "Icey Siyi '24 and Fatima Zohra Boumhaout '24, research (summer 2022)"),
    ("Fatima Zohra Boumhaout", "undergraduate", [2022, 2022], "Icey Siyi '24 and Fatima Zohra Boumhaout '24, research (summer 2022)"),
    ("Frelicia Tucker", "undergraduate", [None, 2022], "Frelicia Tucker '22, senior thesis"),
    ("Vedant Dhopte", "undergraduate", [None, 2022], "Vedant Dhopte '22, senior thesis"),
], note="homepage 'Alumni' (advised undergraduate research/IW/theses with class years)"),
    notes=("Homepage 'Alumni' list of advised undergraduate research, IW and theses (class years); the rest of the "
           "homepage is publications. She also appears on the Visual AI Lab page (Olga Russakovsky's lab)."))

# ---------------------------------------------------------------- labs that need Wayback / data files
from lpauto import js_members, sqs_members  # noqa: E402

P["Abhishek Bhattacharjee"] = lab(
    None, [], wb=[],
    rows=R(SCH, "https://www.cs.princeton.edu/people/research", [
        ("Harsh Desai", "postdoc", None, "Harsh Desai Postdoctoral Research Associate Advisers Abhishek Bhattacharjee"),
    ], note="Princeton CS 'Researchers' page (adviser field)"),
    notes=("Joined Princeton CS 2026-07-01 from Yale; no Princeton lab page yet (~abhattac 404). The CS Researchers page "
           "lists postdoc Harsh Desai with adviser Bhattacharjee. His Yale group page lists Yale students (left out)."))
_AAA = "https://web.archive.org/web/20260822094150id_/https://aaa.princeton.edu/research-group"
P["Amir Ali Ahmadi"] = lab(
    "https://aaa.princeton.edu/", [], wb=[],
    rows=R(SCH, _AAA, [
        ("Cole Becker", "undergraduate", None, "Cole Becker (undergraduate student, now PhD student at MIT)"),
        ("Abraar Chaudhry", "phd", None, "Abraar Chaudhry , PhD Thesis , jointly advised with Eliza Rebrova"),
        ("Cemil Dibek", "phd", None, "Cemil Dibek , PhD Thesis , jointly advised with Maria Chudnovsky"),
        ("Bachir El Khadir", "phd", None, "Bachir El Khadir , PhD Thesis ( Goldstine Fellow at IBM Research"),
        ("Georgina Hall", "phd", None, "Georgina Hall , PhD Thesis (now Assistant Professor at INSEAD"),
        ("Yixuan (Ethan) Hua", "phd", None, "Yixuan (Ethan) Hua , jointly advised with Bartolomeo Stellato"),
        ("Vanshika Jain", "member", None, "Vanshika Jain (now PhD student at Princeton, Math)"),
        ("Yanjun Liu", "phd", None, "Yanjun Liu , jointly advised with Bartolomeo Stellato"),
        ("Yukai Tang", "phd", None, "Yukai Tang , jointly advised with Pravesh Kothari"),
        ("Shen Shen", "postdoc", None, "Shen Shen , Postdoctoral Associate (now Lecturer at MIT)"),
        ("Jeffrey Zhang", "phd", None, "Jeffrey Zhang , PhD Thesis , PhD defense"),
    ], note="'Research Group' page: past and present group members (Wayback id_ 2026-08-22; live site serves a bot challenge)"),
    pubs=[Pubs("https://web.archive.org/web/20260922164137id_/https://aaa.princeton.edu/publications")],
    notes=("Research Group page (past and present members, alphabetical, undated) via Wayback (aaa.princeton.edu serves a "
           "bot challenge). He has been at Princeton since 2014; members without dates are recorded as listed. The "
           "undergrad-theses page lists senior theses by year (not used: thesis-only advisees)."))
P["Anirudha Majumdar"] = lab("https://irom-lab.princeton.edu/", [], wb=["https://irom-lab.princeton.edu/people/"],
                             notes="IRoM Lab pages are rendered by JavaScript from YAML data; see rows/notes below.")
P["Jaime Fernández Fisac"] = lab(
    "https://saferobotics.princeton.edu/", [], wb=[],
    rows=sqs_members(SCH, "https://saferobotics.princeton.edu/people", drop=("Marjan Sharifi",)),
    pubs=[Pubs("https://saferobotics.princeton.edu/publications")],
    notes=("Safe Robotics Lab people page (Squarespace; the member list is embedded as item titles/descriptions in the "
           "page's data). Roles from the descriptions. Marjan Sharifi (artist/scholar collaborator) left out."))
P["Peter Henderson"] = lab(
    "https://polarislab.org/", [], wb=[],
    rows=js_members(SCH, "https://polarislab.org/static/js/main.1d02cfb6.js"),
    notes=("POLARIS Lab site is a React app; its people list (categories and members with titles) is in the site's "
           "JavaScript bundle main.1d02cfb6.js, read as data. First faculty job (Princeton 2024)."))
P["Kyle Jamieson"] = lab("https://paws.princeton.edu/",
                         ["https://web.archive.org/web/20260203231823id_/https://paws.princeton.edu/people"],
                         wb=["https://paws.princeton.edu/people"],
                         notes="PAWS group people page via Wayback (paws.princeton.edu serves a bot challenge). At Princeton since 2015.")
P["Maria Apostolaki"] = lab("https://netsyn.princeton.edu/",
                            ["https://web.archive.org/web/20250815084019id_/https://netsyn.princeton.edu/people"],
                            wb=["https://netsyn.princeton.edu/people"], alumni_ok=True,
                            pubs=[Pubs("https://web.archive.org/web/20250913194559id_/https://netsyn.princeton.edu/publications")],
                            notes="NetΣyn Lab people page via Wayback (live site serves a bot challenge). First faculty job (Princeton 2022).")
P["Yasaman Ghasempour"] = lab("https://ghasempour.princeton.edu/",
                              ["https://web.archive.org/web/20250805231628id_/https://ghasempour.princeton.edu/members"],
                              wb=["https://ghasempour.princeton.edu/members"], alumni_ok=True,
                              notes="SWAN Lab members page via Wayback (live site serves a bot challenge). First faculty job (Princeton 2020).")
P["Radhika Nagpal"] = lab("https://ssr.princeton.edu/",
                          ["https://web.archive.org/web/20260211000428id_/https://ssr.princeton.edu/people",
                           "https://web.archive.org/web/20251009170305id_/https://ssr.princeton.edu/people/alumni"],
                          wb=["https://ssr.princeton.edu/people"], wb_from=2022,
                          notes=("Self-organizing Swarms & Robotics Lab people and alumni pages via Wayback (live site serves a "
                                 "bot challenge). She moved from Harvard in 2022: alumni from the Harvard years are left out "
                                 "unless a Princeton capture lists them as current."))
P["Mark Zhandry"] = lab("https://www.cs.princeton.edu/~mzhandry/",
                        ["https://web.archive.org/web/20230304232521id_/https://www.cs.princeton.edu/~mzhandry/",
                         "https://web.archive.org/web/20220429010736id_/https://www.cs.princeton.edu/~mzhandry/",
                         "https://web.archive.org/web/20210129095425id_/https://www.cs.princeton.edu/~mzhandry/"],
                        wb=[], alumni_ok=True,
                        notes="Princeton homepage via Wayback captures 2021-2023 (he left for NTT Research/Stanford). First faculty job (Princeton 2016).")
P["Pramod Viswanath"] = lab("https://ece.princeton.edu/people/pramod-viswanath",
                            ["https://web.archive.org/web/20261003125229id_/https://ece.princeton.edu/people/pramod-viswanath"],
                            wb=["https://ece.princeton.edu/people/pramod-viswanath"], wb_from=2021,
                            notes="ECE profile 'Advisees' list via Wayback (ece.princeton.edu serves a bot challenge). Moved from UIUC in 2021.")
P["Prateek Mittal"] = lab("https://www.princeton.edu/~pmittal/",
                          ["https://web.archive.org/web/20260216231920id_/https://ece.princeton.edu/people/prateek-mittal",
                           "https://web.archive.org/web/20260929212654id_/https://www.princeton.edu/~pmittal/"],
                          wb=["https://www.princeton.edu/~pmittal/", "https://ece.princeton.edu/people/prateek-mittal"],
                          notes="Homepage and ECE profile 'Advisees' list via Wayback (both hosts serve bot challenges live). At Princeton since 2013.")
P["Jianqing Fan"] = lab("https://fan.princeton.edu/", [], wb=["https://fan.princeton.edu/", "https://fan.princeton.edu/people"],
                        notes="fan.princeton.edu serves a bot challenge; Wayback captures used.")
P["Han Liu"] = lab("http://www.princeton.edu/~hanliu/", [], wb=["http://www.princeton.edu/~hanliu/"], wb_to=2018,
                   notes="At Princeton ORFE until 2018 (now Northwestern); Princeton homepage via Wayback.")
P["Mung Chiang"] = lab("http://edge.princeton.edu/", [], wb=["http://edge.princeton.edu/", "http://edge.princeton.edu/people.html"],
                       wb_to=2017, notes="EDGE Lab (left Princeton in 2017 for Purdue); site via Wayback (live host unreachable).")
P["Ruby Lee"] = lab("http://palms.ee.princeton.edu/", [], wb=["http://palms.ee.princeton.edu/", "http://palms.ee.princeton.edu/people"],
                    notes="PALMS lab site (live host times out); Wayback captures used.")
P["Samory Kpotufe"] = lab("http://www.princeton.edu/~samory/", [], wb=["http://www.princeton.edu/~samory/"], wb_to=2019,
                          notes="At Princeton ORFE until ~2019 (now Columbia); Princeton homepage via Wayback.")
P["Jianxiong Xiao"] = lab("http://vision.princeton.edu/", [], wb=["http://vision.princeton.edu/people.html", "http://vision.princeton.edu/"],
                          wb_to=2017, notes="Princeton Vision Group (he left Princeton in 2016); site via Wayback.")
P["Nick Feamster"] = lab("https://www.cs.princeton.edu/~feamster/", [], wb=["https://www.cs.princeton.edu/~feamster/", "https://noise-lab.net/people/"],
                         wb_from=2016, wb_to=2019, notes="At Princeton 2015-2019 (now UChicago); Princeton-era pages via Wayback.")
P["Barbara Engelhardt"] = lab("https://www.cs.princeton.edu/~bee/", [], wb=["https://www.cs.princeton.edu/~bee/", "http://beehive.cs.princeton.edu/people.html"],
                              wb_to=2022, notes="BEEHIVE group at Princeton (she moved to Gladstone/Stanford in 2022); Princeton-era pages via Wayback.")
P["Mengdi Wang"] = lab("https://mwang.princeton.edu/", [], wb=["https://mwang.princeton.edu/people"],
                       notes="Group site is a Next.js app (mwang-delta.vercel.app); see rows/notes.")
P["Huacheng Yu"] = lab("https://www.cs.princeton.edu/~hy2/", [], notes="Homepage has no students list.")
P["Arash Adel"] = lab("https://adrlab.princeton.edu/", [], wb=["https://adrlab.princeton.edu/people", "https://adrlab.princeton.edu/"],
                      notes="ADR Laboratory (School of Architecture); live site not usable, Wayback captures used.")

# ---------------------------------------------------------------- publication-page specs (checked with pubx.py)
def _spec(pi, url, spec, note=None):
    for p in P[pi]["pubs"]:
        if p.get("pubs_page") == url:
            p["spec"] = spec
            if note:
                p["note"] = note
            return
    P[pi]["pubs"].append(Pubs(url, spec, note=note))


_spec("Aleksandra Korolova", "https://korolova.com/publications", {"item": "div.w-dyn-item", "title": "a.publication-title-link"})
_spec("Amit Levy", "https://amitlevy.com/publications/", {"item": "li", "title_rx": "^\\s*(.+?)\\.\\s+(?:[Ww]ith|[Bb]y)\\b"})
_spec("Bartolomeo Stellato", "https://stella.to/publications", {"item": "div.mb-3", "title": "a.font-semibold"})
_spec("Ellen Zhong", "https://ezlab.princeton.edu/publications/", {"item": "div.col-sm-10", "title": "div.title", "venue": "div.periodical em"})
_spec("Felix Heide", "https://light.princeton.edu/publications/", {"item": "div.individual_publication", "title": "div.publication_upper p"})
_spec("Ben Raphael", "https://raphael-group.github.io/publications/", {"item": "li", "title": "strong"})
_spec("Brenden Lake", "https://lake-lab.github.io/publications/", {"item": "p", "title_rx": "\\((?:19|20)\\d\\d[a-z]?\\)\\.\\s*(.+?)\\.(?:\\s|$)"},
      note="selected publications only")
_spec("Mona Singh", "https://www.cs.princeton.edu/~mona/publications.html", {"split": "hr", "title": "div.ptitle"})
_spec("Tom Griffiths", "https://cocosci.princeton.edu/publications.php", {"item": "tr", "title_rx": "\\((?:19|20)\\d\\d[a-z]?\\)\\.\\s*(.+?)\\.(?:\\s|$)"})
_spec("Mark Braverman", "https://mbraverm.princeton.edu/research/all-papers/", {"item": "li", "title_br": True})
_spec("Jason Lee", "https://jasondlee88.github.io/publications.html", {"item": "li", "title": "a"})
_spec("Zeev Dvir", "https://www.cs.princeton.edu/~zdvir/publications.html", {"item": "li.compact-publication-entry", "title": "h2"})
_spec("Michael Freedman", "http://www.cs.princeton.edu/~mfreed/publications/", {"item": "li", "title": "font[color=red]"})
_spec("Robert Vanderbei", "https://vanderbei.princeton.edu/Publications.html", {"split": "br", "title": "a"})
_spec("Jaime Fernández Fisac", "https://saferobotics.princeton.edu/publications", {"item": "div.sqs-html-content", "title": "strong", "venue": "em"})
_spec("Bartolomeo Stellato", "https://stella.to/publications", {"item": "div.mb-3", "title": "a.font-semibold", "year": "div.pl-5 div.inline-block"})
P["Amit Levy"]["span"] = {"*": ("PhD Students", None)}
P["Andrés Monroy-Hernández"]["wb_from"] = 2021
P["Andrés Monroy-Hernández"]["span"] = {"*": ("Postdocs", "Collaborators")}
P["Arvind Narayanan"]["span"] = {"https://sage.cs.princeton.edu/": ("Team", "Collaborators")}
P["Jaime Fernández Fisac"]["rows"] = sqs_members(
    SCH, "https://saferobotics.princeton.edu/people", drop=("Marjan Sharifi", "Samuel Bateman"),
    roles={"Javier Borquez": "postdoc", "Anoop Sonar": "undergraduate", "Jovana Kondic": "undergraduate",
           "Justin Wang": "phd"})
P["Jaime Fernández Fisac"]["notes"] += (" Samuel Bateman (advised by Dhruv Shah, PRISM Lab) left out; Javier Borquez is a "
                                        "postdoc (PhD USC 2025); Anoop Sonar and Jovana Kondic were Princeton "
                                        "undergraduates.")
P["Maria Apostolaki"]["drop"] = ["NetΣyn's Cheerleader"]
P["Mark Zhandry"].update(people=[], wb=[], notes=("Princeton homepage captures (2021-2023, Wayback) describe his move to "
                                                   "NTT Research and list no students; no members list found."))
_PV = "https://web.archive.org/web/20261003125229id_/https://ece.princeton.edu/people/pramod-viswanath"
P["Pramod Viswanath"].update(people=[], rows=RS(SCH, _PV, "phd", "Advisee(s):", ["Zerui Cheng", "Niusha Moshrefi", "Viraj Nadkarni", "Atharv Patlan", "Esin Türeci", "Peiyang Xu", "Jianzhu Yao"],
                                                note="ECE profile 'Advisee(s)' (graduate advisees)"))
_PM = "https://web.archive.org/web/20260216231920id_/https://ece.princeton.edu/people/prateek-mittal"
P["Prateek Mittal"].update(people=["https://web.archive.org/web/20260929212654id_/https://www.princeton.edu/~pmittal/"],
                           rows=RS(SCH, _PM, "phd", "Advisee(s):", ["Grace H. Cimaszewski", "David Huang", "Cyrill Krähenbühl", "Seungju Lee", "Atharv Patlan", "Tianhao Wang", "Tong Wu", "Tinghao Xie", "Peiyang Xu"],
                                   note="ECE profile 'Advisee(s)' (graduate advisees)"))
P["Radhika Nagpal"]["min_last_year"] = 2022
P["Radhika Nagpal"]["notes"] += " Alumni whose stated dates end before 2022 (Harvard years) are left out."
_CA = "https://castle.princeton.edu/people/"
P["Warren Powell"].update(people=[], wb=[], rows=R(SCH, _CA, [
    ("Brian Cheung", "phd", None, "Current Graduate Students Brian Cheung (ORFE)"),
    ("Ahmet Duzgun", "phd", None, "Current Graduate Students Brian Cheung (ORFE) Ahmet Duzgun (ORFE)"),
    ("Xiaohe Luo", "phd", None, "Current Graduate Students Brian Cheung (ORFE) Ahmet Duzgun (ORFE) Xiaohe Luo (ORFE)"),
    ("Donghun Lee", "phd", [None, 2020], "Donghun Lee, 2020, “Learning to Learn Optimally"),
    ("Yingfei Wang", "phd", [None, 2017], "Yingfei Wang, 2017, “Optimal Learning in High Dimensions.”"),
    ("Daniel Jiang", "phd", [None, 2016], "Daniel Jiang, 2016, “Risk Neutral and Risk Averse Approximate Dynamic Programming methods,”"),
], note="CASTLE Labs people page"),
    notes=("CASTLE Labs people page: current graduate students and past graduate students with thesis years (2016+ "
           "kept); the post-doc list is undated (left out). He retired in 2020."))


def _drop(pi, *names_, note=None):
    P[pi]["drop"] = list(P[pi].get("drop", [])) + list(names_)
    if note:
        P[pi]["notes"] += " " + note


_drop("Barbara Engelhardt", "Genotype-Tissue Expression (GTEx)")
_drop("Jianqing Fan", "Pao-Lu Hsu Prize", "Academia Sinica")
P["Jianqing Fan"]["notes"] += " The captures of fan.princeton.edu show no members list."
_drop("Jianxiong Xiao", "Alain L. Kornhauser", "Sanjeev R. Kulkarni", "Christiane D. Fellbaum", "LSUN Challenge",
      note="Faculty collaborators listed on the group page are left out.")
_drop("Ruby Lee", "OpenSPARC Researh", "PALMScloud Cloud Server Benchmarks", "PALMS Post-Doc Announcement")
P["Ruby Lee"]["notes"] += " The captures show project pages but no members list."
_drop("Nick Feamster", "Detecting DNS Root Manipulation", "Spam Filtering", "Sean Donovan", "Abhinav Narain", "Maria Konte",
      "Yogesh Mundada", "Bilal Anwer", "Guillherme Martins", "Andrew Kim", "Joseph Lee", "Mi Seon Park", "Sathya Gunasekaran",
      note=("The noise-lab.net people page (2016-2019 captures) still lists his Georgia Tech students; only members placed "
            "at Princeton are kept (Roya Ensafi, Danny Huang, Kevin Borgolte, Hooman Mohajeri, Paul Schmitt, Hyojoon Kim)."))
P["Mengdi Wang"]["notes"] = ("The group site (mwang.princeton.edu -> mwang-delta.vercel.app) is a Next.js app whose people "
                             "list is fetched client-side from an API not present in the page or its JavaScript chunk; no "
                             "Wayback capture of the people page exists. No members list retrievable.")
P["Anirudha Majumdar"]["notes"] = ("IRoM Lab people page is rendered by JavaScript from YAML data; the Wayback captures "
                                   "(2020, 2024, 2026) of the people page are used.")
_drop("Aarti Gupta", "Sharad Malik")
_drop("Andrés Monroy-Hernández", "JP Morgan Chase", "Fannie Liu", "Dan Calacci", "Maryam Hedayati")
P["Brenden Lake"]["wb"] = []
P["Brenden Lake"]["notes"] += " Wayback captures (2025-2026) still list NYU members and are not used."
_drop("Ellen Zhong", "Fred Poitevin", "Gordon Wetzstein", "Adam Lerer", "Karsten Kreis", "Abhay Kotecha Thermo Fisher",
      "Martin Obr Thermo Fisher", "Pilar Cossio", "Nina Miolane UCSB", "Tim Dockhorn", "Sagar Khavnekar", "Jake Johnston",
      note="Collaborators listed on older captures are left out.")
_drop("Jia Deng", "Yu-Wei Chao", "Weifeng Chen", "Noriyuki Kojima", "Lanlan Liu", "Jonathan Stroud", "Dawei Yang",
      note="Michigan-era students still shown on 2018-2019 captures are left out.")
_drop("Olga Troyanskaya", "Samuel Sledzieski", "Adam Lamson", "Zijun Zhang")
P["Pramod Viswanath"]["wb"] = []
_drop("Prateek Mittal", "Declaring ECE", "Princeton-Intel REU", "Lori Bailey", "Padmini Nindra", "Ryann Myers",
      note="ECE staff and page furniture on the profile captures are left out.")
_drop("Tom Griffiths", "Mayank Agrawal", "Dilip Arumugam", "Rafael Batista", "David Bourgin", "Michael Chang", "Erin Grant",
      "Jessica Hamrick", "Robert Hawkins", "Mark Ho", "Rachel Jansen", "Thomas Langlois", "Maya Malaviya", "Raja Marjieh",
      "Stephan Meylan", "Aida Nematzadeh", "Kerem Oktar", "Alexandra Paxton", "Joshua Peterson", "Daniel Reichman",
      "Ilia Sucholutsky", "Jordan Suchow", "Bill Thompson", "Bas van Opheusden", "Jianqiao Zhu",
      note="The 'Alumni and Long-Distance Affiliates' list mixes Berkeley and Princeton years without dates and is left out.")
_drop("Wyatt Lloyd", "Ethan Katz-Bassett", "Yousif Aldolaijan (USC)")
_drop("Yuxin Chen", "Emmanuel Candès", "Andrea Goldsmith")
_drop("Zeev Dvir", "Fellowship")
_drop("Mark Braverman", "Omri Weinstein", "Anastasios Zouzias", "Gil Cohen", "Ran Gelles", "Rotem Oshman", "Klim Efremenko",
      "Ankur Moitra", "Jing Chen", "Eden Chlamtac", "Per Austrin", "Cristobal Rojas", "Yang P. Liu",
      note=("The members page lists all past graduate students and postdocs without dates; those known to predate 2016 "
            "or to be collaborators are left out."))
P["Radhika Nagpal"]["people"] = ["https://web.archive.org/web/20260211000428id_/https://ssr.princeton.edu/people"]
P["Radhika Nagpal"]["notes"] += " The alumni page is her Harvard-era list (undated or ending before 2022) and is not used."
P["Margaret Martonosi"]["alumni_pages"] = ["https://web.archive.org/web/20260922164118id_/https://mrm.scholar.princeton.edu/graduated-advisees"]
