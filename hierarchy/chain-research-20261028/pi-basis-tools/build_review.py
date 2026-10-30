"""Assemble pi-basis-review.json from captures.sqlite (this directory). Every quote is re-checked as an exact substring
of the stored text of the capture with that sha256. Written after each person so partial work survives."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[3] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, re, sqlite3, sys
from cap import DB

HERE = str(P.HIERARCHY / 'chain-research-20261028')
OUT = HERE + "/pi-basis-review.json"
INP = json.load(open(HERE + "/pi-basis-input.json"))
C = sqlite3.connect(DB)
WB = re.compile(r"^https://web\.archive\.org/web/(\d{14})id_/(.*)$")


def cap(url):
    r = C.execute("select url, final_url, fetched_at, status, sha256, text from captures where url=? and status=200 "
                  "order by id desc limit 1", (url,)).fetchone()
    if not r:
        raise KeyError(url)
    return dict(zip(["url", "final_url", "fetched_at", "status", "sha256", "text"], r))


def ev(url, pat, observed=None, flags=0):
    c = cap(url)
    m = re.search(pat, c["text"], flags)
    if not m:
        raise ValueError(f"pattern not found in {url}: {pat}")
    q = m.group(0)
    assert q in c["text"]
    m2 = WB.match(url)
    out = {"url": m2.group(2) if m2 else url}
    if m2:
        out["capture_url"] = url
        obs = observed or f"{m2.group(1)[:4]}-{m2.group(1)[4:6]}-{m2.group(1)[6:8]}"
    else:
        obs = observed or c["fetched_at"][:10]
    out.update({"sha256": c["sha256"], "quote": q, "observed": obs, "fetched_at": c["fetched_at"]})
    return out


def adv(name, role, years, e, note=None):
    a = {"name": name, "role": role, "years": years, "url": e["url"], "sha256": e["sha256"], "quote": e["quote"]}
    if "capture_url" in e:
        a["capture_url"] = e["capture_url"]
    if note:
        a["note"] = note
    return a


# ---------------- MIT: DSpace@MIT advisor queries ----------------
HITS = json.load(open(HERE + "/pi-basis-tools/mit_dspace_hits.json"))


def person_name(author):
    a = re.split(r",\s*(?:Ph\.? ?D\.?|S\.M\.|M\. ?Eng\.?)", author)[0]
    a = re.sub(r"\s*\([^)]*\)\s*", " ", a).strip().rstrip(".")
    a = re.sub(r",\s*\d{4}-\s*$", "", a).strip()
    if "," in a:
        last, first = [x.strip() for x in a.split(",", 1)]
        a = f"{first} {last}"
    return re.sub(r"\s+", " ", a)


def mit_advisees(pi, limit=8):
    h = HITS[pi]
    c = cap(h["url"])
    out = []
    for r in h["records"]:
        if not r["doctoral"] or not r["quote"]:
            continue
        q = r["quote"]
        k = q.find('"dc.contributor.advisor"')
        q = q[k:] if k >= 0 else q
        if q not in c["text"]:
            continue
        yr = int(r["issued"][0][:4])
        out.append({"name": person_name(r["author"]), "role": "phd", "years": [yr, yr], "url": h["url"],
                    "sha256": c["sha256"], "quote": q,
                    "note": f"DSpace@MIT {r['uri'][0] if r['uri'] else ''}; degree '{r['degree'][:60]}'; title '{(r['title'] or [''])[0][:90]}'"})
    out.sort(key=lambda a: a["years"][0])
    return out[:limit], sum(1 for r in h["records"] if r["doctoral"]), h["total"], c


def mit_entry(item):
    pi = item["pi"]
    advs, ndoc, total, c = mit_advisees(pi)
    yrs = sorted({int(r["issued"][0][:4]) for r in HITS[pi]["records"] if r["doctoral"]})
    e = {"url": advs[0]["url"], "sha256": advs[0]["sha256"], "quote": advs[0]["quote"], "observed": c["fetched_at"][:10],
         "fetched_at": c["fetched_at"]} if advs else None
    return advs, ndoc, total, yrs, e


MIT_SEARCHED = ["DSpace@MIT REST discover (server/api/discover/search/objects) query dc.contributor.advisor:(<last> AND <first>), "
                "dateIssued 2016-2026, all departments; doctoral = degree/description naming Ph.D./Sc.D./Doctor of Philosophy"]

R = []


def write():
    json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False)


def add(**kw):
    kw.setdefault("advisees", [])
    R.append(kw)
    write()
    print(kw["school"], kw["pi"], kw["verdict"], len(kw["evidence"]), len(kw["advisees"]), flush=True)


ROLE = {x["pi"]: x["title"] for x in INP}

for item in INP:
    pi, s = item["pi"], item["school"]
    if s != "mit":
        continue
    if pi == "Priya Donti":
        g = "https://priyadonti.com/group/"
        evs = [ev("https://priyadonti.com/", r"My group’s research focuses on [^.]*\."),
               ev(g, r"Current Members Alvaro Carbonero \(Ph\.D\. student\).{0,200}?Lara Booth \(Ph\.D\. student\)"),
               ev(g, r"Arsam Aryandoust \(postdoc, 2023-25\)")]
        advs = [adv(n, "phd", [], ev(g, re.escape(n) + r" \(Ph\.D\. student\)"), "current member on group page (fetched 2026-10-28); start year not stated")
                for n in ["Alvaro Carbonero", "Ana Rivera", "Anvita Bhagavathula", "Hoang Nguyen", "James Chen", "Khai Nguyen", "Lara Booth"]]
        advs += [adv("Arsam Aryandoust", "postdoc", [2023, 2025], ev(g, r"Arsam Aryandoust \(postdoc, 2023-25\)")),
                 adv("Enrico Marchesini", "postdoc", [2023, 2025], ev(g, r"Enrico Marchesini \(postdoc, 2023-25\)"))]
        hits = HITS[pi]
        add(school=s, pi=pi, verdict="pi", role_found="Assistant Professor, MIT EECS and LIDS (since 2023)",
            reason="Heads a research group whose own page lists seven current Ph.D. students and two postdocs (2023-25). "
                   "No MIT doctoral thesis names her yet (DSpace has one 2024 S.M. thesis she co-supervised), which is expected for a 2023 start.",
            evidence=evs, advisees=advs,
            searched=MIT_SEARCHED + [f"DSpace query returned {hits['total']} item(s), 0 doctoral", "priyadonti.com home and /group/"])
        continue
    advs, ndoc, total, yrs, e = mit_entry(item)
    extra = ""
    if pi == "George Verghese":
        extra = " The only doctoral thesis in the window is a 2016 co-supervision (with Thomas Heldt); his other 2016-2019 theses are M.Eng."
    if pi == "Alexandre Megretski":
        extra = " Only one doctoral thesis (2019) names him in the window, so the basis is thin but explicit."
    if pi == "YuFeng (Kevin) Chen":
        extra = " Only one doctoral thesis so far (2025); the other DSpace hits are S.B./M.Eng. theses."
    add(school=s, pi=pi, verdict="pi", role_found=ROLE[pi],
        reason=f"DSpace@MIT names {pi.split()[-1] if pi != 'YuFeng (Kevin) Chen' else 'Chen'} as thesis supervisor (dc.contributor.advisor) on {ndoc} doctoral thesis(es) issued "
               f"{yrs[0]}-{yrs[-1]} (of {total} theses 2016-2026 matching the name query); up to eight are listed as advisees.{extra}",
        evidence=[e], advisees=advs, searched=MIT_SEARCHED)

# ---------------- CMU ----------------
RA = "http://reports-archive.adm.cs.cmu.edu/anon/"
add(school="cmu", pi="Yuanzhi Li", verdict="pi", role_found="Assistant Professor, Machine Learning Department (since 2019-09)",
    reason="The MLD Ph.D. student directory (2022 capture) names him as advisor of two Ph.D. students. His homepage dates the "
           "CMU appointment from 2019.9; no completed KiltHub thesis names him yet.",
    evidence=[ev("https://web.archive.org/web/20210606113345id_/https://www.andrew.cmu.edu/user/yuanzhil/", r"I'm an Assistant Professor in the Machine Learning Department at CMU \(2019\.9-present\)\."),
              ev("https://web.archive.org/web/20220528094210id_/https://www.ml.cmu.edu/people/phd-students.html", r"Tian Ye Tsinghua University B\.E\. in Computer Science Advisor: Yuanzhi Li")],
    advisees=[adv("Tian Ye", "phd", [2022, 2022], ev("https://web.archive.org/web/20220528094210id_/https://www.ml.cmu.edu/people/phd-students.html", r"Tian Ye Tsinghua University B\.E\. in Computer Science Advisor: Yuanzhi Li")),
              adv("Zixin Wen", "phd (co-advised with Yuejie Chi)", [2022, 2022], ev("https://web.archive.org/web/20220528094210id_/https://www.ml.cmu.edu/people/phd-students.html", r"Zixin Wen University of International Business and Economics in China B\.A\. in Financial Mathematics Advisors: Yuanzhi Li & Yuejie Chi"))],
    searched=["KiltHub figshare API search 'Yuanzhi Li' / 'Yuanzhi' (CMU group 18614 and institution 13): 0 theses",
              "homepage www.andrew.cmu.edu/user/yuanzhil (live 404; Wayback 2021, 2024)", "MLD Ph.D. student directory (Wayback 2022-05-28)"])

add(school="cmu", pi="Alex Smola", verdict="pi", role_found="Professor, MLD (CMU 2013-2017 per his homepage; moved to Amazon July 2016)",
    reason="SCS technical-report thesis pages list him as Thesis Committee Co-Chair for Ph.D. theses completed in 2016 and 2017. "
           "His own homepage says he was CMU professor 2013-2017 and moved to AWS in July 2016, so the PI period should end 2016/2017.",
    evidence=[ev(RA + "ml2017/abstracts/17-102.html", r"Sashank J\. Reddi July 2017 Ph\.D\. Thesis"),
              ev(RA + "ml2017/abstracts/17-102.html", r"Thesis Committee: Alexander J\. Smola \(Co-Chair\)"),
              ev("https://alex.smola.org/", r"From 2013-2017 I was professor at Carnegie Mellon University \. I co-founded Marianas Labs in early 2015\. In July 2016 I moved to Amazon Web Services")],
    advisees=[adv("Alex Beutel", "phd (co-chair with Christos Faloutsos)", [2016, 2016], ev(RA + "2016/abstracts/16-105.html", r"Alex Beutel May 2016 Ph\.D\. Thesis.*?Thesis Committee: Christos Faloutsos \(Co-Chair\) Alexander J\. Smola \(Co-Chair\)", flags=re.S)),
              adv("Sashank J. Reddi", "phd (co-chair with Barnabas Poczos)", [2017, 2017], ev(RA + "ml2017/abstracts/17-102.html", r"Thesis Committee: Alexander J\. Smola \(Co-Chair\)"), "CMU-ML-17-102, July 2017")],
    searched=["SCS report archive thesis pages (cs/ml/isr 2016-2020) via the existing thesis harvest, re-fetched", "KiltHub figshare search", "alex.smola.org"])

add(school="cmu", pi="Daniel Neill", verdict="pi", role_found="Associate Professor of Information Systems, Heinz College; Director, Event and Pattern Detection Laboratory (left CMU 2018-07-01 for NYU)",
    reason="His CMU homepage says he directs the Event and Pattern Detection Laboratory and is leaving CMU on July 1, 2018; his CV lists "
           "him as primary research advisor of CMU Ph.D. students (Heinz, MLP joint program, MLD). No KiltHub/SCS thesis names him as chair, so the basis is lab headship plus CV-stated advising, 2016-2018.",
    evidence=[ev("http://www.cs.cmu.edu/~neill/", r"At CMU, I direct the Event and Pattern Detection Laboratory"),
              ev("http://www.cs.cmu.edu/~neill/", r"As of July 1st, 2018, I will be leaving CMU to join New York University"),
              ev("http://www.cs.cmu.edu/~neill/papers/cv.pdf", r"Primary research advisor for Seth Flaxman, William Herlands, and Dylan Fitzpatrick, Ph\.D\. stu-\s*dents, Joint Ph\.D\. Program in Machine Learning and Policy")],
    advisees=[adv(n, "phd", [], ev("http://www.cs.cmu.edu/~neill/papers/cv.pdf", r"Primary research advisor for Seth Flaxman, William Herlands, and Dylan Fitzpatrick, Ph\.D\. stu-\s*dents"), "CV (c. 2018) lists as primary research advisor; years not stated")
              for n in ["William Herlands", "Dylan Fitzpatrick"]]
             + [adv(n, "phd", [], ev("http://www.cs.cmu.edu/~neill/papers/cv.pdf", r"nav Maurya, Mallory Nobles, and Zhe Zhang, Ph\.D\. students, H\. John Heinz III College"), "CV (c. 2018) lists as primary research advisor; years not stated")
                for n in ["Mallory Nobles", "Zhe Zhang"]],
    searched=["KiltHub figshare search 'Daniel Neill' (only a 2014 thesis)", "SCS report archive (committee member only, ISR 2017)",
              "www.cs.cmu.edu/~neill/ and papers/cv.pdf", "cs.nyu.edu/~neill/", "Wayback CDX epdlab.heinz.cmu.edu/people (only a 2016-02 capture)"])

add(school="cmu", pi="Stephen Fienberg", verdict="pi", role_found="University Professor of Statistics and Machine Learning",
    reason="The SCS thesis page names him Thesis Committee Co-Chair of an MLD Ph.D. thesis completed August 2017, so he was advising "
           "in 2016 (he also sat on the committee of Yu-Xiang Wang's Dec 2017 MLD thesis). His period should be bounded to 2016 "
           "(he died in December 2016; that date is not captured here).",
    evidence=[ev(RA + "ml2017/abstracts/17-103.html", r"Kirstin Early August 2017 Ph\.D\. Thesis"),
              ev(RA + "ml2017/abstracts/17-103.html", r"Thesis Committee: Jennifer Mankoff \(Co-Chair\) Stephen Fienberg \(Co-Chair\)")],
    advisees=[adv("Kirstin Early", "phd (co-chair with Jennifer Mankoff)", [2017, 2017], ev(RA + "ml2017/abstracts/17-103.html", r"Thesis Committee: Jennifer Mankoff \(Co-Chair\) Stephen Fienberg \(Co-Chair\)"), "CMU-ML-17-103, August 2017")],
    searched=["SCS report archive thesis pages via existing harvest, re-fetched", "KiltHub figshare search 'Fienberg' (2017 theses 6716123 and 6720836)"])

add(school="cmu", pi="Ryan Tibshirani", verdict="pi", role_found="Associate Professor, Statistics and Machine Learning (CMU 2011-2022; later Berkeley)",
    reason="SCS thesis pages name him Thesis Committee Chair of MLD Ph.D. theses in 2017 and 2019, and the 2022 MLD Ph.D. directory lists him as advisor "
           "of current students. The 'Adjunct Faculty' title in the listing is from after his 2022 move to Berkeley; he is also a Berkeley PI in this data (same person, separate period).",
    evidence=[ev(RA + "ml2019/abstracts/19-104.html", r"Veeranjaneyulu Sadhanala May 2019 Ph\.D\. Thesis"),
              ev(RA + "ml2019/abstracts/19-104.html", r"Thesis Committee: Ryan Tibshirani \(Chair\)")],
    advisees=[adv("Yu-Xiang Wang", "phd", [2017, 2017], ev(RA + "ml2017/abstracts/17-105.html", r"Thesis Committee: Ryan J\. Tibshirani \(Chair\)"), "CMU-ML-17-105, December 2017"),
              adv("Veeranjaneyulu Sadhanala", "phd", [2019, 2019], ev(RA + "ml2019/abstracts/19-104.html", r"Thesis Committee: Ryan Tibshirani \(Chair\)"), "CMU-ML-19-104, May 2019"),
              adv("Addison Hu", "phd", [2022, 2022], ev("https://web.archive.org/web/20220528094210id_/https://www.ml.cmu.edu/people/phd-students.html", r"Addison Hu Yale University BS in Statistics Advisor: Ryan Tibshirani")),
              adv("Pratik Patil", "phd", [2022, 2022], ev("https://web.archive.org/web/20220528094210id_/https://www.ml.cmu.edu/people/phd-students.html", r"Pratik Patil University of Toronto MASc in Electrical & Computer Engineering MS in Statistics Advisor: Ryan Tibshirani"))],
    searched=["SCS report archive thesis pages, re-fetched", "MLD Ph.D. student directory (Wayback 2022-05-28)"])

# ---------------- Berkeley ----------------
D23 = "https://www2.eecs.berkeley.edu/Pubs/Dissertations/Years/2023.html"
D22 = "https://www2.eecs.berkeley.edu/Pubs/Dissertations/Years/2022.html"
CC = "https://web.archive.org/web/20160802145023id_/http://cocosci.berkeley.edu:80/people.php"
add(school="berkeley", pi="Thomas Griffiths", verdict="pi", role_found="Professor of Psychology and Cognitive Science (EECS 'below the line' affiliate); Director, Computational Cognitive Science Lab (Berkeley until 2018)",
    reason="The Berkeley Computational Cognitive Science Lab people page (2016 capture) lists him as Lab Director with graduate students and postdocs, and "
           "Berkeley EECS dissertations of 2022 and 2023 name him as co-advisor. He moved to Princeton in 2018, so the Berkeley period is 2016-2018 (plus co-advising that finished later); "
           "he is the same person as Princeton PI 'Tom Griffiths'.",
    evidence=[ev(CC, r"Faculty Tom Griffiths, Lab Director"),
              ev(D23, r"Infrastructure Support for Datacenter Applications Michael Chang \[advisor: Thomas Griffiths and Sergey Levine\]"),
              ev("https://www.cs.princeton.edu/news/tom-griffiths-recognized-outstanding-mentoring-graduate-students", r"When he came to Princeton in 2018, he was the first faculty member to be jointly appointed in the departments of Psychology and Computer Science\.")],
    advisees=[adv("Michael Chang", "phd (co-advised with Sergey Levine)", [2023, 2023], ev(D23, r"Michael Chang \[advisor: Thomas Griffiths and Sergey Levine\]")),
              adv("Erin Grant", "phd (co-advised with Michael Jordan)", [2022, 2022], ev(D22, r"Erin Grant \[advisor: Michael Jordan and Thomas Griffiths\]"))]
             + [adv(n, "graduate student (lab roster)", [2016, 2016], ev(CC, re.escape(n) + r" \( webpage \)"), "listed under 'Graduate Students' on the lab people page whose Faculty entry is 'Tom Griffiths, Lab Director' (2016-08-02 capture)")
                for n in ["Joshua Abbott", "Jessica Hamrick", "Falk Lieder", "Stephan Meylan", "Michael Pacer", "Joshua Peterson"]],
    searched=["EECS dissertations by year 2016-2023 ('[advisor: ...]')", "Wayback cocosci.berkeley.edu home and people.php (2016-2018)",
              "Princeton CS news page (move date)"])

# ---------------- Stanford ----------------
OSG = lambda ts: f"https://web.archive.org/web/{ts}id_/https://profiles.stanford.edu/brad-osgood"
add(school="stanford", pi="Brad Osgood", verdict="pi", role_found="Professor of Electrical Engineering (and, by courtesy, Education); Senior Associate Dean for Student Affairs, School of Engineering (2021-22 captures)",
    reason="Stanford Profiles Wayback captures from 2024-06 to 2024-11 list him as 'Doctoral Dissertation Advisor (AC)' of Chien-yi Chang and 2025-05 to 2025-06 captures of Travis Skare, which meets the literal rule. "
           "CAUTION: both are long-running EE Ph.D. students (admitted 2017 and 2009) whose research advisors are elsewhere (Chang is also Fei-Fei Li's 'Doctoral Dissertation Advisor (AC)' advisee), the entries are short-lived, and no SDR dissertation names him as degree supervisor (three 2026-27 SDR theses list him only as committee member); this looks like EE advisor-of-record, so the owner may prefer not_pi.",
    evidence=[ev(OSG("20240625150759"), r"Doctoral Dissertation Advisor \(AC\) Chien-yi Chang"),
              ev(OSG("20241103115738"), r"Doctoral Dissertation Advisor \(AC\) Chien-yi Chang"),
              ev(OSG("20250503090516"), r"Doctoral Dissertation Advisor \(AC\) Travis Skare"),
              ev("https://web.archive.org/web/20240913045535id_/https://profiles.stanford.edu/chien-yi-chang", r"Chien-Yi Chang Ph\.D\. Student in Electrical Engineering, admitted Autumn 2017"),
              ev("https://web.archive.org/web/20250505011958id_/https://profiles.stanford.edu/travis-skare", r"Travis Skare Ph\.D\. Student in Electrical Engineering, admitted Spring 2009"),
              ev("https://profiles.stanford.edu/brad-osgood", r"Doctoral Dissertation Reader \(AC\) Ibrahim Gulluk Master's Program Advisor Marissa Kuo , Pengyu Mo Doctoral \(Program\) Peijing Li , Marina Qian, Tom Stone , Sarah Zou")],
    advisees=[adv("Chien-yi Chang", "phd (Doctoral Dissertation Advisor (AC), EE)", [2024, 2024], ev(OSG("20240625150759"), r"Doctoral Dissertation Advisor \(AC\) Chien-yi Chang"), "listed in 2024-06-25, 2024-08-05 and 2024-11-03 captures; absent 2024-05-03 and 2025-02-06"),
              adv("Travis Skare", "phd (Doctoral Dissertation Advisor (AC), EE)", [2025, 2025], ev(OSG("20250503090516"), r"Doctoral Dissertation Advisor \(AC\) Travis Skare"), "listed in 2025-05-03 and 2025-06-20 captures; absent 2025-09-08")],
    searched=["profiles.stanford.edu/brad-osgood live + every Wayback capture 2024-2025 and first/last capture of every other year 2015-2026",
              "DataCite SDR (prefix 10.25740) queries 'Osgood', 'Skare', 'Chang, Chien'", "existing SDR MODS captures (Osgood = degree committee member only)",
              "advisee profiles chien-yi-chang, travis-skare (Wayback)"])

GR = "https://profiles.stanford.edu/christopher-gregg"
add(school="stanford", pi="Chris Gregg", verdict="not_pi", role_found="Associate Professor (Teaching) of Computer Science (teaching-track; formerly Lecturer)",
    reason="Teaching-track faculty. No Stanford Profiles capture 2019-2026 (all 18 Wayback captures plus live) lists a Doctoral Dissertation Advisor/Co-Advisor (AC) or Postdoctoral Faculty Sponsor entry; "
           "only Master's Program Advisor, Orals Chair, one Doctoral Dissertation Reader (AC) and one Doctoral (Program) student, none of which count. No lab is stated.",
    evidence=[ev(GR, r"Christopher Gregg Associate Professor \(Teaching\) of Computer Science"),
              ev(GR, r"Prior to becoming a lecturer at Stanford, Chris was a lecturer in the computer science department at Tufts University"),
              ev(GR, r"Doctoral Dissertation Reader \(AC\) Daniela Ganelin Orals Chair Zach Hulcher"),
              ev(GR, r"Doctoral \(Program\) Diana Popescu")],
    searched=["profiles.stanford.edu/christopher-gregg live + all 18 Wayback captures 2019-08..2026-03", "DataCite SDR query 'Gregg' (no dissertation he supervised)"])

DA = "https://profiles.stanford.edu/emma-dauterman"
add(school="stanford", pi="Emma Dauterman", verdict="not_pi", role_found="Assistant Professor of Computer Science (started fall 2025)",
    reason="Ladder faculty who started in fall 2025; neither her live profile nor its six Wayback captures (2024-09..2026-04) list a Doctoral Dissertation Advisor/Co-Advisor (AC) or Postdoctoral Faculty Sponsor, "
           "only 'Doctoral (Program)' students (excluded by the 2026-10-28 rule) and Master's Program Advisor. No lab page or student list was found. Likely to qualify later; re-check.",
    evidence=[ev(DA, r"Emma Dauterman Assistant Professor of Computer Science"),
              ev(DA, r"Doctoral \(Program\) Ryan Cottone, Ihyun Nam"),
              ev("https://web.archive.org/web/20241109130033id_/https://people.eecs.berkeley.edu/~edauterman/", r"I will be starting as an assistant professor at Stanford in fall 2025\.")],
    searched=["profiles.stanford.edu/emma-dauterman live + 6 Wayback captures", "cs.stanford.edu/people/emma-dauterman", "people.eecs.berkeley.edu/~edauterman (Wayback 2024-11; live 404)",
              "emmadauterman.com / edauterman.github.io (do not resolve / 404)", "DataCite SDR query 'Dauterman' (none)", "OpenAlex A5009677502 works 2025-2026 (no Stanford student co-authors)"])

# order like the input
order = {(x["school"], x["pi"]): i for i, x in enumerate(INP)}
R.sort(key=lambda r: order[(r["school"], r["pi"])])
write()
print(len(R))
