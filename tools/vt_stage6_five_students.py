"""Replay five VT student links from pinned first-party source captures."""

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "hierarchy/vt/reviewed/source-captures"
EVIDENCE = ROOT / "hierarchy/vt/reviewed/few-students-evidence.json"
SOURCES = {
    "weitong": ("vt-weitong-r6.html", "cc8d5800dc65c0dea1ba61339a6691f689426a4d1fc3ef2014c6b71cf4ba691a", "https://weitongli.com/"),
    "xrt": ("vt-xrt-people-r6.html", "f0b4dfab7de7e39c10b2c00239b95995c19d3ebee4d3370dd39dca833adffa07", "https://xrtlab.github.io/xrtlab-site/people/"),
    "kabilan": ("vt-kabilan-r6.html", "15d1339d2bf33a5e5c646af30c11d2be6401390fa21de4d27e0e1b4f970f0254", "https://kabilan.info/"),
    "minhyuk": ("vt-minhyuk-r6.html", "b48abfa3a87d683751fd58cddb35d4adb71853671b19762c1c4028290bcb4581", "https://people.cs.vt.edu/minhyukko/"),
    "hamza": ("vt-hamza-r6.html", "a4dfbbd06a812a9841dd910a1f352b9e2509ca7c7997ab0e4a3ac31b9275629a", "https://muhamza.com/"),
}


def source_text(key):
    filename, sha, _ = SOURCES[key]
    path = SRC_DIR / filename
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, filename
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def main():
    pages = {key: source_text(key) for key in SOURCES}
    findings = [
        ("Tijay Chung", "Weitong Li", 2025, "weitong", "I received my PhD from Virginia Tech in 2025, advised by Tijay Chung", "advising"),
        ("Ryan P. McMahan", "Tiffany D Do", 2026, "xrt", "Principal Investigators Ryan P McMahan Associate Professor Grad Students Tiffany D Do Ph.D. Candidate", "membership"),
        ("Kirshanthan Sundararajah", "Kabilan Mahathevan", 2026, "kabilan", "I am fortunate enough to be advised by Prof. Kirshanthan (“Krish”) Sundararajah", "advising"),
        ("Chris Brown", "Minhyuk Ko", 2026, "minhyuk", "At Virginia Tech, I work with Dr. Chris Brown", "membership"),
        ("Eric Pauley", "Muhammad Hamza", 2026, "hamza", "I’m a PhD candidate in Computer Science at Virginia Tech, where I work with Eric Pauley", "membership"),
    ]
    records = json.loads(EVIDENCE.read_text())
    added = []
    for pi, student, year, key, quote, relation in findings:
        assert quote in pages[key], (pi, student)
        rec = next((r for r in records if r["pi"] == pi), None)
        if rec is None:
            rec = {"pi": pi, "students": []}
            records.append(rec)
        existing = next((s for s in rec["students"] if s["name"] == student), None)
        if existing:
            existing["relationship"] = relation
            continue
        _, sha, url = SOURCES[key]
        rec["students"].append({
            "name": student, "role": "phd", "years": [year, year],
            "years_basis": "dated 2025 PhD or current page captured 2026-11-12; no other years inferred",
            "relationship": relation, "source": "reviewed_first_party_page",
            "reviewed": True, "auto": False, "url": url, "sha256": sha,
            "quote": quote,
            "note": "Named student relationship from a student or lab page; only the evidenced year is recorded.",
        })
        added.append((pi, student))
    EVIDENCE.write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"added": added}))


if __name__ == "__main__":
    main()
