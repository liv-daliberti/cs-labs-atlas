"""Independent QA of hierarchy/berkeley/gap-evidence.json against the main capture DB (not the worker DBs).

Checks: schema; one row per input PI; every cited sha256 exists in gap-captures.sqlite as a status-200 row whose
url/capture_url match the citation and whose bytes re-hash to that sha256; every quote is an exact substring of
the stored page's whitespace-collapsed text; quotes name the person (PI surname/alias for status, appointment and
identity items; a token of the student's name for student rows); roles and years are well-formed.
usage: qa.py
"""
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
import zlib

sys.path.insert(0, "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-berkeley")
import capstore  # noqa: E402

H = "/n/fs/resemble/cs-atlas/work/hierarchy/berkeley"
rows = json.load(open(H + "/gap-evidence.json"))
gap = json.load(open(H + "/gap-input.json"))
con = sqlite3.connect(f"file:{capstore.DB_MAIN}?mode=ro", uri=True)
ROLES = {"phd", "postdoc", "masters", "undergraduate", "member", "other"}
ALIASES = {"Carlo H. Séquin": ["Séquin", "Sequin", "SEQUIN"], "Venkatesan Guruswami": ["Guruswami", "Venkat"],
           "Sophia Shao": ["Shao"], "Doug Tygar": ["Tygar"], "Jason Lee": ["Lee"]}
bad = []
texts = {}


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def stored(sha):
    if sha not in texts:
        r = con.execute("SELECT url, capture_url, status, content FROM captures WHERE sha256=? AND content IS NOT NULL",
                        (sha,)).fetchall()
        if not r:
            texts[sha] = None
        else:
            c = zlib.decompress(r[0][3])
            if hashlib.sha256(c).hexdigest() != sha:
                bad.append(f"sha mismatch for stored bytes {sha}")
            texts[sha] = ({(x[0], x[1], x[2]) for x in r}, capstore.page_text(c), capstore.raw_text(c))
    return texts[sha]


def check_item(pi, kind, it, name_tokens):
    for k in ("url", "sha256", "quote"):
        if not it.get(k):
            bad.append(f"{pi}/{kind}: missing {k}")
            return
    s = stored(it["sha256"])
    if s is None:
        bad.append(f"{pi}/{kind}: sha {it['sha256'][:12]} not in main DB")
        return
    meta, pt, rt = s
    if not any(u == it["url"] and (cu or None) == (it.get("capture_url") or None) and st == 200 for u, cu, st in meta):
        bad.append(f"{pi}/{kind}: url/capture_url/status do not match a stored row: {it['url']} {it.get('capture_url')}")
    q = it["quote"]
    if q not in pt and q not in rt:
        bad.append(f"{pi}/{kind}: quote not in stored text: {q[:80]}")
    fq = fold(q.replace("\\u00e9", "e"))
    if not any(fold(t) in fq for t in name_tokens):
        bad.append(f"{pi}/{kind}: quote lacks name {name_tokens}: {q[:120]}")


names = [g["pi"] for g in gap]
if [r["pi"] for r in rows] != names:
    bad.append("row order / PI set differs from gap-input")
n = 0
for r in rows:
    pi = r["pi"]
    keys = {"pi", "status", "status_evidence", "students", "identity", "collection_person_id", "appointment_notes", "notes"}
    if set(r) != keys:
        bad.append(f"{pi}: keys {sorted(set(r) ^ keys)}")
    if r["status"] not in ("pi", "not_pi_in_window"):
        bad.append(f"{pi}: status {r['status']}")
    if r["collection_person_id"] is not None:
        bad.append(f"{pi}: collection_person_id not null")
    if r["status"] == "pi" and not r["students"]:
        bad.append(f"{pi}: pi without students")
    ptoks = ALIASES.get(pi, [re.sub(r"[,.]", "", pi).split()[-1]])
    for it in r["status_evidence"]:
        n += 1
        check_item(pi, "status", it, ptoks)
    for it in r["appointment_notes"]:
        n += 1
        check_item(pi, "appointment", it, ptoks)
    for it in r["identity"]["evidence"]:
        n += 1
        if not it.get("kind"):
            bad.append(f"{pi}: identity evidence without kind")
        check_item(pi, "identity:" + it.get("kind", "?"), it, ptoks)
    for a in r["identity"]["openalex"]:
        if not re.fullmatch(r"A\d+", a):
            bad.append(f"{pi}: bad openalex id {a}")
    for o in r["identity"]["orcid"]:
        if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", o):
            bad.append(f"{pi}: bad orcid {o}")
    seen = set()
    for s in r["students"]:
        n += 1
        if s["role"] not in ROLES:
            bad.append(f"{pi}: role {s['role']} for {s['name']}")
        y = s.get("years")
        if y is not None and not (isinstance(y, list) and len(y) == 2 and all(v is None or isinstance(v, int) for v in y)):
            bad.append(f"{pi}: years {y} for {s['name']}")
        if y and all(v is not None for v in y) and (y[0] > y[1] or y[1] < 2016 or y[0] > 2026):
            bad.append(f"{pi}: years out of window {y} for {s['name']}")
        if s["name"] in seen:
            bad.append(f"{pi}: duplicate student {s['name']}")
        seen.add(s["name"])
        toks = [t for t in re.split(r"[\s,()]+", s["name"]) if len(t) > 1 and not t.endswith(".")]
        check_item(pi, f"student {s['name']}", s, toks[-1:] if toks else [s["name"]])
print(f"checked {n} evidence items across {len(rows)} rows")
print("ISSUES:" if bad else "no issues")
for b in bad:
    print("  -", b)
