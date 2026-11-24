"""Verify EPFL IC's legacy faculty captures and publish real Stage 1 year coverage.

The released EPFL listing sweep predates protocol department keys. Its plan and
captured bytes are retained in listings/epfl/raw/captures.sqlite. This adapter
checks those source receipts, parses every IC card, and adds only the IC
department-year key to the existing coverage file. Missing or corrupt evidence
raises before any output is written.
"""
import gzip
import hashlib
import json
import re
import sqlite3
import sys
import tempfile
import os
import zlib
from pathlib import Path

import atlas_paths as P
import listing_formats as F
import school_config as S

SLOT = "IC professors and senior scientists"


def coverage_from_captures(con, sources, years):
    """Return (coverage, receipts) only when every year has a verified faculty list."""
    plans = con.execute(
        "select year,half,page_url,capture_url,wayback_timestamp,status,reason "
        "from plan where slot=? order by year,half", (SLOT,)
    ).fetchall()
    seen = set()
    coverage, receipts = {}, []
    for year, half, page_url, cap, stamp, status, reason in plans:
        if year not in years or half not in ("H1", "H2"):
            continue
        if (year, half) in seen:
            raise ValueError(f"duplicate IC plan row {year} {half}")
        seen.add((year, half))
        key = f"{SLOT} {half}"
        if status != "ok":
            coverage.setdefault(str(year), {})[key] = status or "missing"
            receipts.append(dict(year=year, half=half, status=status, reason=reason))
            continue
        if not cap or not stamp or not page_url:
            raise ValueError(f"IC {year} {half}: incomplete plan receipt")
        m = re.fullmatch(r"https://web\.archive\.org/web/(\d{14})id_/.+", cap)
        if not m or m.group(1) != stamp or stamp[:4] != str(year):
            raise ValueError(f"IC {year} {half}: capture date mismatch")
        month = int(stamp[4:6])
        if not (1 <= month <= 6 if half == "H1" else 7 <= month <= 12):
            raise ValueError(f"IC {year} {half}: capture is outside its half-year")
        if not any(page_url == url and lo <= stamp[:8] <= hi for url, lo, hi in sources):
            raise ValueError(f"IC {year} {half}: {page_url} is outside the charter URL eras")
        row = con.execute(
            "select http_status,sha256,raw_zlib,final_url from captures where capture_url=?", (cap,)
        ).fetchone()
        if not row or row[0] != 200 or not row[1] or row[2] is None:
            raise ValueError(f"IC {year} {half}: missing HTTP-200 captured bytes")
        raw = zlib.decompress(row[2])
        if hashlib.sha256(raw).hexdigest() != row[1]:
            raise ValueError(f"IC {year} {half}: captured-byte hash mismatch")
        if row[3] != cap:
            raise ValueError(f"IC {year} {half}: capture redirected away from its exact URL")
        body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        html = body.decode("utf-8", "replace")
        fmt, people = F.parse(html)
        if fmt not in ("epfl_ic_legacy", "epfl_ic_contact"):
            raise ValueError(f"IC {year} {half}: no reviewed faculty-list parser")
        markers = html.count('class="g-span-1_4"') if fmt == "epfl_ic_legacy" else html.count('class="contact-list-row"')
        if len(people) != markers or len(people) < 5 or any(not p["name_listed"] for p in people):
            raise ValueError(f"IC {year} {half}: {len(people)} parsed people versus {markers} source cards")
        coverage.setdefault(str(year), {})[key] = "ok"
        receipts.append(dict(year=year, half=half, status="ok", page_url=page_url,
                             capture_url=cap, sha256=row[1], format=fmt, people=len(people)))
    missing = [year for year in years if "ok" not in coverage.get(str(year), {}).values()]
    if missing:
        raise ValueError(f"IC has no verified faculty listing in years {missing}")
    return coverage, receipts


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main():
    key = "epfl"
    cfg = S.get(key)
    dept = next((d for d in cfg.get("departments") or [] if d["code"] == "IC"), None)
    if not dept or dept.get("coverage") != "full":
        raise ValueError("EPFL requires a full-coverage IC department in the charter")
    slots = [s for s in S.listing_slots(key) if s["slot"] == SLOT and s["dept"] == "IC"]
    if len(slots) != 1:
        raise ValueError("EPFL charter must define exactly one IC faculty listing slot")
    lo, hi = cfg["window"]
    p = P.data("listings-captures.sqlite", key)
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as con:
        coverage, receipts = coverage_from_captures(con, slots[0]["urls"], range(lo, hi + 1))
    out = P.data_w("coverage.json", key)
    old = json.loads(out.read_text()) if out.exists() else {}
    old["IC"] = coverage
    atomic_json(out, old)
    if len(sys.argv) > 1:
        atomic_json(sys.argv[1], dict(school=key, department="IC", years=list(range(lo, hi + 1)), receipts=receipts))
    print(json.dumps(dict(school=key, department="IC", years=len(coverage), verified_captures=sum(r["status"] == "ok" for r in receipts))))


if __name__ == "__main__":
    main()
