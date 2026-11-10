"""Review VT computing candidates against saved registrar and unit role sources.

The registrar pages are university-wide, dated faculty directories.  This batch
only decides people with a positive role match; absence is not a negative result.
The OpenAlex candidate must also have an anchored VT computing-share result.
"""

import collections
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

import atlas_paths as P
import cs_related_school as C
from pi_hierarchy import Name, toks


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "hierarchy/vt/reviewed/cs-related-review.json"
ROSTERS = P.SCRATCH / "vt-followthrough-1110/faculty-directory-sources"
EXPLICIT_GIVEN = {("tim", "timothy"), ("jeff", "jeffrey"), ("doug", "douglas")}
NON_LADDER = re.compile(r"\b(research|collegiate|professional|clinical|adjunct|emeritus|specialist|lecturer|instructor|postdoctoral)\b", re.I)
PROFESSOR = re.compile(r"\b(?:professor|prof\.?|asst\.?|assoc\.?|assistant|associate)\b", re.I)


def strict_person(candidate, roster_name):
    """Require a real given-name agreement, not just Name's initial alias."""
    a, b = toks(candidate), toks(roster_name)
    if len(a) < 2 or len(b) < 2 or a[-1] != b[-1]:
        return False
    firsts = (a[0], b[0])
    if a[0] == b[0] or firsts in EXPLICIT_GIVEN or firsts[::-1] in EXPLICIT_GIVEN:
        return True
    return False


def registrar_rows():
    receipts = {r["year"]: r for r in json.loads((ROSTERS / "capture-receipt.json").read_text())}
    rows = []
    for year, receipt in sorted(receipts.items()):
        raw = (ROSTERS / f"{year}-faculty.html").read_bytes()
        assert receipt["status"] == 200 and hashlib.sha256(raw).hexdigest() == receipt["sha256"]
        for p in BeautifulSoup(raw, "html.parser").select("p"):
            line = p.get_text(" ", strip=True)
            match = re.match(r"^([^()]{4,90})\s*\((?:19|20)\d{2}\)", line)
            if not match:
                continue
            printed = match.group(1).strip(" ,")
            if "," not in printed:
                continue
            role = line[match.end():].lstrip(" ,.;")
            role = re.split(r"\b(?:B\.?S\.?|M\.?S\.?|Ph\.?D\.?)\b", role, maxsplit=1)[0][:180].strip(" ,.;")
            rows.append(dict(year=year, printed=printed, role=role, line=line,
                             url=receipt["url"], sha256=receipt["sha256"]))
    return rows


def main():
    doc = json.loads(REVIEW.read_text())
    decisions = {d["name"]: d for d in doc["decisions"]}
    before = len(decisions)
    candidates = json.loads((P.CODE / "hierarchy/vt/derived/cs-related-candidates.json").read_text())
    pages, hand, stats, registrar = C.unit_pages("vt"), C.hand_evidence("vt"), C.oa_stats("vt"), registrar_rows()
    counts = collections.Counter()
    for candidate in candidates:
        name = candidate["name"]
        if name in decisions or candidate["source"] not in ("openalex_rule", "official_profile_ladder"):
            continue
        aliases = candidate.get("aliases") or []
        historical = [r for r in registrar if Name([name] + aliases).match(r["printed"])
                      and strict_person(name, r["printed"])] if candidate["source"] == "openalex_rule" else []
        current = C.faculty_evidence(pages, [name] + aliases, "") if candidate["source"] == "openalex_rule" else []
        profiles = hand.get(" ".join(toks(name)), []) if candidate["source"] == "official_profile_ladder" else []
        if not historical and not current and not profiles:
            continue
        evidence = [dict(unit="university registrar", url=r["url"], sha256=r["sha256"],
                         observed=str(r["year"]), quote=r["line"][:220],
                         ladder=bool(PROFESSOR.search(r["role"])) and not bool(NON_LADDER.search(r["role"])))
                    for r in historical]
        evidence += current + profiles
        ladder = [e for e in evidence if e["ladder"]]
        if candidate["source"] == "openalex_rule":
            ids = candidate.get("openalex") or []
            assert len(ids) == 1, name
            share = C.share_test(stats, [name] + aliases, [], min(int(e["observed"][:4]) for e in evidence), ids)
            assert ids[0] in share["ids"] and not share["namesake_orcids"], name
        else:
            share = C.share_test(stats, [name] + aliases, [], min(int(e["observed"][:4]) for e in evidence), [])
        if not ladder:
            decision, reason = "research_or_other_rank", "dated university source names only a non-ladder or professional role"
        elif share["result"] == "computing":
            decision, reason = "accepted", f"professor-rank university source and {share['dblp_indexed']}/{share['school_works']} VT works DBLP-indexed (share {share['share']:.3f})"
        elif share["result"] == "not_computing":
            decision, reason = "faculty_not_computing", f"professor-rank university source but computing share {share['dblp_indexed']}/{share['school_works']} ({share['share']:.3f}) below 0.20"
        else:
            decision, reason = "too_few_school_works", "professor-rank university source; OpenAlex sweep has too few attributable VT works to settle computing scope"
        decisions[name] = dict(name=name, aliases=aliases, source=candidate["source"], decision=decision,
                               reason=reason, cs_basis=dict(openalex_share=share, candidate_openalex=candidate.get("openalex") or []),
                               faculty_evidence=evidence[:3] + evidence[-1:] if len(evidence) > 3 else evidence,
                               years_listed=sorted({int(e["observed"][:4]) for e in evidence}),
                               units_searched=["official VT registrar faculty directories 2016–2021", "saved current affiliated-unit listings and profiles"],
                               provisional="Full affiliated-unit historical review and lab ownership remain open; no school package admitted.")
        counts[decision] += 1
    assert len(decisions) == before + sum(counts.values())
    doc["decisions"] = list(decisions.values())
    doc["reviewed"] = "2026-11-10"
    doc["provisional"] = "Registrar and current unit role decisions appended; full affiliated-unit historical review pending."
    doc["counts"] = dict(collections.Counter(d["decision"] for d in doc["decisions"]))
    REVIEW.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(dict(before=before, added=sum(counts.values()), after=len(decisions), by_decision=dict(counts))))


if __name__ == "__main__":
    main()
