"""Resolve five VT affiliation leads with saved, identity-matched student sources.

The candidate's DBLP bibliography is checked against the source's named work or
research area. A degree alone is not used to infer a faculty appointment.
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
CANDIDATES = P.data("cs-related-candidates.json", "vt")
RULES = {
    "Lee Lisle": ("https://hci.icat.vt.edu/news/the-american-soldier-in-world-war-ii.html",
                  ["Lee Lisle (CS, PhD student)"], "Immersive", "VT CS doctoral student; later VT lab alumni"),
    "Hao Zhang": ("https://wordpress.cs.vt.edu/csblog/2015/12/",
                 ["Dr. Daphne Yao’s doctoral student Hao Zhang", "Hao Zhang will join the database security team at Oracle"],
                 "network", "VT CS doctoral student who left for Oracle in January 2016"),
    "Madhava Krishnan Ramanathan": (
        "https://ece.vt.edu/content/dam/ece_vt_edu/research/annual-report/2024/VT_ECE_24127_2024AnnReport_Web.pdf",
        ["Ph.D.’s Awarded", "Madhava Krishnan Ramanathan", "Exploring the Boundaries of Operating System"],
        "Exploring the Boundaries", "VT 2022–23 PhD recipient, listed with dissertation title"),
    "Manish Kumar Singh": ("https://sites.google.com/view/manish-k-singh/home",
                            ["Manish Kumar Singh", "I obtained my PhD in June 2021", "Vassilis Kekatos"],
                            "Voltage", "self-described VT ECE PhD 2021; subsequent external faculty role"),
    "Mi Zhou": ("https://directory.business.vcu.edu/profile.php?urn=mizhou",
                 ["Mi(Jamie) Zhou", "doctoral degree in Accounting from Virginia Tech", "Big Data Analytics"],
                 "Social", "VCU faculty profile identifies VT accounting doctorate, not a VT faculty appointment"),
    "Joungmin Choi": ("https://research.cs.vt.edu/zhanglab/people.html",
                       ["Joung Min Choi Ph.D. Student", "Dr. Liqing Zhang Professor"],
                       "Cell-specific network-based", "VT Zhang Lab roster places this name among the PI's doctoral students"),
    "Peng Xu": ("https://par.nsf.gov/servlets/purl/10205112",
                ["Peng Xu is a Ph.D. candidate in the Grado Department of Industrial and Systems Engineering",
                 "at Virginia Tech"],
                "An evaluation of the optimality of frequent verification",
                "author biography in the exact candidate paper identifies a VT ISE doctoral student"),
}


def text_of(raw, content_type, url):
    if url.endswith(".pdf") or (content_type or "").lower().startswith("application/pdf"):
        cp = subprocess.run(["pdftotext", "-layout", "-", "-"], input=raw,
                            capture_output=True, check=True)
        return " ".join(cp.stdout.decode("utf-8", "replace").split())
    return W.flat(W.extract.blocks(raw, content_type, url))


def main():
    doc = json.loads(REVIEW.read_text())
    decisions = {d["name"]: d for d in doc["decisions"]}
    candidates = {c["name"]: c for c in json.loads(CANDIDATES.read_text())}
    db = W.con("vt")
    added = []
    for name, (url, anchors, title_anchor, reason) in RULES.items():
        if name in decisions:
            continue
        c = candidates[name]
        assert c["source"] == "dblp_affiliation", name
        row = db.execute("select status,sha256,raw_zlib,content_type,fetched_at from live where url=?", (url,)).fetchone()
        assert row and row[0] == 200 and row[2], name
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], name
        body = text_of(raw, row[3], url)
        assert all(anchor in body for anchor in anchors), name
        # Require a title or research area already present in the candidate's
        # source bibliography before applying the role quote to this identity.
        pubs = json.loads((P.SCRATCH / "vt-followthrough-1110/dblp-candidate-pubs.json").read_text())
        assert any(title_anchor.lower() in p["title"].lower() for p in pubs[name]), name
        decisions[name] = {
            "name": name, "aliases": c.get("aliases") or [], "source": c["source"],
            "decision": "not_faculty_listed",
            "reason": reason + "; no professor appointment appears in the reviewed VT faculty rosters",
            "cs_basis": {"dblp": [c["dblp"]], "dblp_window": c.get("dblp_window"),
                         "affiliation_notes": c.get("affiliations") or []},
            "faculty_evidence": [],
            "status_evidence": [{"url": url, "sha256": row[1], "quote": anchor,
                                 "observed": row[4][:10]} for anchor in anchors],
            "years_listed": [], "units_searched": ["VT faculty rosters 2016–2026"],
            "provisional": "A later VT faculty appointment would require a separate dated professor-rank source.",
        }
        added.append(name)
    doc["decisions"] = list(decisions.values())
    doc["counts"] = dict(collections.Counter(d["decision"] for d in doc["decisions"]))
    REVIEW.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"added": added, "remaining": len(candidates) - len(decisions)}))


if __name__ == "__main__":
    main()
