"""Resolve VT OpenAlex leads from captured, named university person pages."""

import collections
import hashlib
import json
import zlib
from pathlib import Path

import atlas_paths as P
import school_web as W


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "hierarchy/vt/reviewed/cs-related-review.json"
CAPTURES = P.SCRATCH / "vt-followthrough-1110/openalex-person-source-captures.json"

# Each anchor must occur verbatim in the saved page capture. Student and
# research-rank findings remain provisional pending a full period review.
RULES = {
    "Surendrabikram Thapa": ("research_or_other_rank", "Surendrabikram Thapa, Research Associate"),
    "Chengzhang Li": ("not_faculty_listed", "Chengzhang Li, Ph.D. in ECE@VT"),
    "Xuchao Zhang": ("not_faculty_listed", "Xuchao Zhang, a Ph.D. student in computer science"),
    "Mohammad J. Abdel-Rahman": ("research_or_other_rank", "Research Faculty Member in the ECE Department at Virginia Tech"),
    "Vuk Marojevic": ("research_or_other_rank", "Research Assistant Professor, Bradley Dept. ECE, Virginia Tech"),
    "Yanshen Sun": ("not_faculty_listed", "Yanshen Sun was a Ph.D. student in the Department of Computer Science"),
    "Yaxing Yao": ("accepted", "Yaxing Yao is a new assistant professor in Computer Science"),
    "Ahmed Abdelhadi": ("research_or_other_rank", "Ahmed Abdelhadi and Joseph Ernst, research assistant professors at the Hume Center"),
    "William Diehl": ("accepted", "Joined ECE August 2018 as Assistant Professor"),
    "Samarth Swarup": ("research_or_other_rank", "Samarth Swarup, a research assistant professor in the Biocomplexity Institute"),
    "Amir I. Zaghloul": ("research_or_other_rank", "Amir I. Zaghloul Research Professor"),
    "Mohamed Handosa": ("not_faculty_listed", "Mohamed Handosa, PhD Computer Science. (2018)"),
    "İ. Esra Büyüktahtakın": ("accepted", "Esra Büyüktahtakın Toy is a Full Professor of Operations Research"),
    "Adedeji Afolabi": ("research_or_other_rank", "Adedeji Afolabi is a research associate in the Myers-Lawson School of Construction"),
    "Ihudiya Finda Ogbonnaya-Ogburu": ("accepted", "I publish under my pen name, Ihudiya Finda Ogbonnaya-Ogburu"),
    "Vishnu Vardhan Chetlur": ("not_faculty_listed", "Vishnu Vardhan Chetlur completed his Ph.D. in Summer 2020"),
    "Ayat Mohammed": ("research_or_other_rank", "Ayat Mohammed Computational Scientist"),
    "Jaeho Kim": ("research_or_other_rank", "NECSST postdoc Jaeho Kim was appointed professor at Gyeongsang National University"),
    "Tanmoy Sarkar Pias": ("not_faculty_listed", "Tanmoy Sarkar Pias, advised by Danfeng (Daphne) Yao, earned a Ph.D. in computer science"),
}


def main():
    doc = json.loads(REVIEW.read_text())
    decisions = {d["name"]: d for d in doc["decisions"]}
    candidates = {c["name"]: c for c in json.loads((P.CODE / "hierarchy/vt/derived/cs-related-candidates.json").read_text())}
    captures = {r["name"]: r for r in json.loads(CAPTURES.read_text())}
    db = W.con("vt")
    added = collections.Counter()
    for name, (decision, anchor) in RULES.items():
        if name in decisions:
            continue
        c, r = candidates[name], captures[name]
        assert c["source"] == "openalex_rule" and r["status"] == 200
        row = db.execute("select status,sha256,raw_zlib,content_type from live where url=?", (r["url"],)).fetchone()
        assert row and row[0] == 200 and row[1] == r["sha256"] and row[2], name
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], name
        body = W.flat(W.extract.blocks(raw, row[3], r["url"]))
        assert anchor in body, name
        if name == "Ihudiya Finda Ogbonnaya-Ogburu":
            assert "I am an Assistant Professor at Virginia Tech's Department of Computer Science" in body
        if decision == "accepted":
            assert c["oa_dblp_works"] >= 5 and c["oa_cs_share"] >= .2
        decisions[name] = {
            "name": name, "aliases": c.get("aliases") or [], "source": c["source"],
            "decision": decision,
            "reason": "Named university source gives a dated role; full period and identity review remains open",
            "cs_basis": {"candidate_openalex": c.get("openalex", []), "oa_works": c.get("oa_works"),
                         "oa_dblp_works": c.get("oa_dblp_works"), "oa_cs_share": c.get("oa_cs_share")},
            "faculty_evidence": [{"url": r["url"], "sha256": r["sha256"], "quote": anchor,
                                  "observed": "captured 2026-11-10", "ladder": decision == "accepted"}],
            "provisional": "Full unit period, author identity, and lab ownership review remain open; no school package admitted.",
        }
        added[decision] += 1
    doc["decisions"] = list(decisions.values())
    doc["counts"] = dict(collections.Counter(d["decision"] for d in doc["decisions"]))
    REVIEW.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"added": sum(added.values()), "after": len(decisions), "by_decision": dict(added)}))


if __name__ == "__main__":
    main()
