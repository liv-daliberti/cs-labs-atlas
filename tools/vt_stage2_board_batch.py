"""Review additional VT OpenAlex leads using hash-checked public Board rosters.

The public PDFs are used only for name and appointment rank; pay is never saved
in the review ledger. Each local text extract was checked against pdftotext of
the identified official PDF before these hashes were recorded.
"""

import collections
import hashlib
import json
import re
from pathlib import Path

import atlas_paths as P
import cs_related_school as C
from pi_hierarchy import Name
from vt_stage2_registrar_batch import NON_LADDER, PROFESSOR, strict_person


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "hierarchy/vt/reviewed/cs-related-review.json"
SOURCES = {
    2021: ("bov-2021-22-faculty-salary.layout.txt",
           "https://bov.vt.edu/assets/Attachment%20UU_Resolution%20to%20Approve%202021-22%20Faculty%20Salary%20Program.pdf",
           "91c15c7b4717dc4c2bcf77d7ad2c1da4c28f60988b9181a5847959fd175c019e",
           "7f04199c78411fadf1b049d4f1f3b8d9b3f9c5b22ceef1b67626d38601a09904"),
    2022: ("bov-2022-23-faculty-salary.layout.txt",
           "https://bov.vt.edu/assets/Attachment%20PP_Resolution%20to%20Ratify%202022-23%20Faculty%20Salary%20Program%20as%20amended%20effective%20July%2010%2C%202022%2C%20contingent%20upon%20approval%20of%20state%20budget.pdf",
           "9276ceb6ae9f40d11080d7ec06ed93f1fa69805e923f5f0718632176ba43de32",
           "9d52c4fda7d3b66422a67faeecf22575fd4105a45a5095e169344adc80e36fa6"),
    2023: ("bov-2023-24-faculty-salary.layout.txt",
           "https://www.bov.vt.edu/assets/Minutes-June%205-6%2C%202023-138.pdf",
           "9d1b86a4c16e0cefb8d72456793df938e3d115611959e9c9272f39ec7ceaa8aa",
           "c3ae46d7afa68a8c6030772a63705dd50b0393fdc32b3461a34dec2486182ead"),
}
PAY_START = re.compile(r"\s{2,}(?=\d[\d,]*\s+(?:AY|CY|RE\d))")
NON_LADDER = re.compile(NON_LADDER.pattern.replace("specialist", "administrative|specialist"), re.I)


def rows():
    out = []
    for year, (file, url, pdf_sha, text_sha) in SOURCES.items():
        raw = (P.SCRATCH / "vt-followthrough-1110" / file).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == text_sha
        for line in raw.decode("utf-8", "replace").splitlines():
            match = re.match(r"^\s+([^,\n]{2,45}),\s+(.{2,45}?)\s{2,}(.*)$", line)
            if not match:
                continue
            name = match.group(1) + ", " + match.group(2)
            role = PAY_START.split(match.group(3), maxsplit=1)[0].strip()
            if len(role) > 75 or not role:
                continue
            # Keep the source line only up to the pay column. No compensation data
            # enters the review ledger or a debug print.
            prefix = line[:line.find(match.group(3))] + match.group(3)[:match.group(3).find(role) + len(role)]
            out.append(dict(year=year, name=name, role=role, quote=prefix.rstrip(),
                            url=url, sha256=pdf_sha, extract_sha256=text_sha))
    return out


def main():
    doc = json.loads(REVIEW.read_text())
    decisions = {d["name"]: d for d in doc["decisions"]}
    before = len(decisions)
    candidates = json.loads((P.data("cs-related-candidates.json", "vt")).read_text())
    roster, stats = rows(), C.oa_stats("vt")
    counts = collections.Counter()
    for c in candidates:
        name = c["name"]
        if name in decisions or c["source"] != "openalex_rule":
            continue
        matches = [r for r in roster if Name([name] + (c.get("aliases") or [])).match(r["name"])
                   and strict_person(name, r["name"])]
        if not matches:
            continue
        ids = c.get("openalex") or []
        assert len(ids) == 1, name
        share = C.share_test(stats, [name] + (c.get("aliases") or []), [], min(r["year"] for r in matches), ids)
        assert ids[0] in share["ids"] and not share["namesake_orcids"], name
        evidence = [dict(unit="VT Board of Visitors", url=r["url"], sha256=r["sha256"],
                         extract_sha256=r["extract_sha256"], observed=str(r["year"]),
                         quote=r["quote"], ladder=bool(PROFESSOR.search(r["role"])) and not bool(NON_LADDER.search(r["role"])))
                    for r in matches]
        ladder = [e for e in evidence if e["ladder"]]
        if not ladder:
            decision, reason = "research_or_other_rank", "public university roster shows only research, collegiate, professional, or other non-ladder rank"
        elif share["result"] == "computing":
            decision, reason = "accepted", f"professor-rank roster and {share['dblp_indexed']}/{share['school_works']} VT works DBLP-indexed (share {share['share']:.3f})"
        elif share["result"] == "not_computing":
            decision, reason = "faculty_not_computing", f"professor-rank roster but computing share {share['dblp_indexed']}/{share['school_works']} ({share['share']:.3f}) below 0.20"
        else:
            decision, reason = "too_few_school_works", "professor-rank roster; too few attributable VT works to settle computing scope"
        decisions[name] = dict(name=name, aliases=c.get("aliases") or [], source=c["source"], decision=decision,
                               reason=reason, cs_basis=dict(openalex_share=share, candidate_openalex=ids),
                               faculty_evidence=evidence[:3] + evidence[-1:] if len(evidence) > 3 else evidence,
                               years_listed=sorted({r["year"] for r in matches}),
                               units_searched=["VT Board of Visitors public faculty salary rosters, 2021–2023"],
                               provisional="Full unit period, identity, and lab ownership review remain open; no school package admitted.")
        counts[decision] += 1
    doc["decisions"] = list(decisions.values())
    doc["counts"] = dict(collections.Counter(d["decision"] for d in doc["decisions"]))
    REVIEW.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(dict(before=before, added=sum(counts.values()), after=len(decisions), by_decision=dict(counts))))


if __name__ == "__main__":
    main()
