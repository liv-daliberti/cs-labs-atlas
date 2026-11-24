"""Review VT DBLP affiliation leads against hashed person and degree sources.

The records are provisional candidate decisions. A VT degree, student role, or
postdoctoral appointment is not counted as a professor-rank VT appointment.
"""

import collections
import hashlib
import json
import subprocess
import zlib
from pathlib import Path

import atlas_paths as P
import school_web as W


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "hierarchy/vt/reviewed/cs-related-review.json"
DB = P.CODE / "hierarchy/vt/raw/school-captures.sqlite"
RULES = {
    "Arturo S. Bretas": ("https://www.sandia.gov/people/staff/arturo-bretas/", "Ph.D., Virginia Tech, 2001", "not_faculty_listed"),
    "Bo Zhou": ("https://sites.google.com/site/bozhousite/", "postdoctoral associate at the Bradley Department of Electrical and Computer Engineering at Virginia Tech", "research_or_other_rank"),
    "Chao Fei": ("https://tpea.cpss.org.cn/uploads/soft/161229/1_1401078661.pdf", "Chao Fei received the B.S. degree in electrical engineering from Zhejiang University", "not_faculty_listed"),
    "Chao Peng": ("https://people.cs.vt.edu/~yongcao/", "Chao Peng graduated from my research lab as a Ph.D. student", "not_faculty_listed"),
    "Da Zhang": ("https://daz88.github.io/", "He was a Ph.D. student at the Department of Computer Science of Virginia Tech", "not_faculty_listed"),
    "David Yang Gao": ("https://ctc.shmtu.edu.cn/2021/0414/c8571a76809/page.htm", "1992年至2009年在弗吉尼亚理工大学任教", "not_faculty_listed"),
    "Haris Volos": ("https://buehrer.ece.vt.edu/Students.html", "Haris Volos Ph.D. Student (2010)", "not_faculty_listed"),
    "Jia Guo": ("https://jiaguo18.github.io/", "I obtained my Ph.D. in Mechanical Engineering from Virginia Tech", "not_faculty_listed"),
    "Jian Chen": ("https://steamfactory.osu.edu/people/chen.8028", "Virginia Tech, Computer Science, PhD", "not_faculty_listed"),
    "Junpeng Wang": ("https://usa.visa.com/about-visa/visa-research/junpeng-wang.html", "M.S. in Computer Science and Application from Virginia Polytechnic Institute and State University in 2015", "not_faculty_listed"),
    "Katarzyna Swirydowicz": ("https://personal.math.vt.edu/sturler/", "Katarzyna Swirydowicz (PhD Math VT, 2017, Computational Scientist", "not_faculty_listed"),
    "Lemuria D. Carter": ("https://vtechworks.lib.vt.edu/server/api/core/bitstreams/717beb2e-92be-4879-8b3f-976da35a3f35/content", "Lemuria Carter, a Ph.D. student in accounting", "not_faculty_listed"),
    "Leonardo Pavanatto": ("https://wordpress.cs.vt.edu/3digroup/author/lpavanat/", "I’m a Ph.D. Candidate in Computer Science and Applications at Virginia Tech", "not_faculty_listed"),
    "Lijing Wang": ("https://computational-epidemiology.org/about-us", "Lijing Wang; Graduate Student; now at New Jersey Institute of Technology", "not_faculty_listed"),
    "Mahboub Baccouch": ("https://www.unomaha.edu/college-of-arts-and-sciences/mathematics/about-us/directory/mahboub-baccouch.php", "Ph.D., Mathematics, Virginia Tech, May 2008", "not_faculty_listed"),
    "Minsu Kim": ("https://sites.google.com/vt.edu/minsukim/home", "I joined Wireless@VirginiaTech as a PhD student", "not_faculty_listed"),
    "Pedro Mendes": ("https://vtechworks.lib.vt.edu/items/93924e79-3417-4f5d-bad0-d466be8d30f4", "Pedro Mendes, associate professor at the Virginia Bioinformatics Institute at Virginia Tech, will become chair", "not_faculty_listed"),
    "Qi Zhang": ("https://people.cs.vt.edu/jicho/people.html", "Qi Zhang Fall 2021–present", "not_faculty_listed"),
    "Robert E. Crossler": ("https://news.wsu.edu/news/2026/02/09/crossler-named-carson-college-of-business-senior-associate-dean-for-academic-affairs/", "Crossler earned his doctorate in accounting and information systems from Virginia Tech", "not_faculty_listed"),
    "Ruizhe Zhang": ("https://widebandgap.ece.vt.edu/yhzhang.html", "Ruizhe Zhang on passing the PhD defense", "not_faculty_listed"),
    "Sen Wang": ("https://zephyr06.github.io/uploads/Resume_SenWang_academic.pdf", "Ph.D. Computer Engineering, Virginia Tech", "not_faculty_listed"),
    "Seung In Park": ("https://vtechworks.lib.vt.edu/server/api/core/bitstreams/5ae7baf5-c0ea-47d8-9f41-e0d98634c052/content", "Modeling Social Group Interactions for Realistic Crowd Behaviors Seung In Park Dissertation submitted", "not_faculty_listed"),
    "Syed Suhaib": ("https://ece.vt.edu/content/dam/ece_vt_edu/research/annual-report/pdf/2009_AR.pdf", "Suhaib, Syed Mohammed Formal Methods for Intellectual Property Composition Across Synchronization Domains", "not_faculty_listed"),
    "Tung Le": ("https://tunglethanh.github.io/", "I am a computer science Ph.D. graduate from Virginia Tech", "not_faculty_listed"),
    "Vasanth Reddy": ("https://sanghani.cs.vt.edu/news/2021/sanghani-center-students-spend-summer-months-gaining-real-world-experience-at-companies-labs-and-organizations-across-the-country.html", "Vasanth Reddy Baddam , a Ph.D. student in computer science", "not_faculty_listed"),
    "Yifei Song": ("https://wireless.vt.edu/Directory/Students.html", "Yifei Song PhD Student Advisor: Dr. Liu", "not_faculty_listed"),
    "Young-Woo Kwon": ("https://people.cs.vt.edu/~tilevich/", "Young-Woo Kwon Ph.D. 2014 Assistant Professor, Kyungpook National University", "not_faculty_listed"),
    "Xinyi Zhang": ("https://echolab.cs.vt.edu/members/", "Xinyi Zhang (Computer Science, Virginia Tech)", "not_faculty_listed"),
    "Hao Song": ("https://lingjialiu.ece.vt.edu/index/research-group.html", "Hao Song Ph.D. Student Defended in February 2021", "not_faculty_listed"),
    "Hong Zhang": ("https://synergy.cs.vt.edu/afosr-bri/people.php", "Hong Zhang Formerly PhD Student Now at ANL", "not_faculty_listed"),
    "Zhou Zhou": ("https://lingjialiu.ece.vt.edu/index/research-group.html", "Zhou (John) Zhou Ph.D. Student Defended in June 2021", "not_faculty_listed"),
    "Bo Gao": ("https://bgao-vt.github.io/", "I received the Ph.D. degree in computer engineering from the Bradley Department of Electrical and Computer Engineering at Virginia Tech, USA in 2014", "not_faculty_listed"),
}


def source(db, url):
    row = db.execute("select status,sha256,raw_zlib,content_type,fetched_at from live where url=?", (url,)).fetchone()
    assert row and row[0] == 200 and row[2], url
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1], url
    if raw[:4] == b"%PDF":
        proc = subprocess.run(["pdftotext", "-raw", "-", "-"], input=raw, capture_output=True, check=True)
        body = " ".join(proc.stdout.decode("utf8", "replace").split())
    else:
        body = W.flat(W.extract.blocks(raw, row[3], url))
    return row[1], body, row[4][:10]


def main():
    doc = json.loads(REVIEW.read_text())
    decisions = {d["name"]: d for d in doc["decisions"]}
    candidates = {c["name"]: c for c in json.loads((P.CODE / "hierarchy/vt/derived/cs-related-candidates.json").read_text())}
    db = W.con("vt")
    added = collections.Counter()
    for name, (url, quote, decision) in RULES.items():
        if name in decisions:
            continue
        c = candidates[name]
        assert c["source"] == "dblp_affiliation" and c["dblp_window"] >= 5, name
        sha, body, at = source(db, url)
        assert quote in body, (name, quote)
        if name == "David Yang Gao":
            assert "高扬（David Yang Gao）" in body and "2010年起在澳大利亚联邦大学任教" in body
        if name == "Pedro Mendes":
            assert "2007-02-02" in body and "University of Manchester" in body
        if name == "Xinyi Zhang":
            assert body.index("Ph.D. students") < body.index(quote) < body.index("Master Students")
        if name == "Chao Fei":
            assert "where he is currently pursuing the Ph.D. degree with the Center for Power Electronics Systems" in body
        if name == "Sen Wang":
            assert "Graduate Research/Teaching Assistant. Virginia Tech" in body
        if name == "Syed Suhaib":
            assert any(t["title"] == "Formal Methods for Intellectual Property Composition Across Synchronization Domains." for t in json.loads((P.SCRATCH / "vt-followthrough-1110/dblp-candidate-theses.json").read_text())[name])
        decisions[name] = {
            "name": name, "aliases": c.get("aliases") or [], "source": c["source"], "decision": decision,
            "reason": "Hash-checked named source documents a VT student, degree, research, postdoctoral, or departed faculty role; it does not establish a professor-rank VT appointment during the 2016–2026 review period.",
            "cs_basis": {"dblp": [c["dblp"]], "dblp_window": c["dblp_window"],
                         "affiliation_notes": c.get("affiliations", []), "dump": "dblp-2026-09-01.xml.gz"},
            "faculty_evidence": [], "status_evidence": [{"url": url, "sha256": sha, "observed": at, "quote": quote}],
            "years_listed": [], "units_searched": ["VT dated CS census and official person/degree sources"],
            "provisional": "Full affiliate-unit period and identity review remains open; no school package admitted.",
        }
        added[decision] += 1
    doc["decisions"] = list(decisions.values())
    doc["counts"] = dict(collections.Counter(d["decision"] for d in doc["decisions"]))
    REVIEW.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"added": sum(added.values()), "after": len(decisions), "by_decision": dict(added)}))


if __name__ == "__main__":
    main()
