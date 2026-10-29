"""ORCID record via the orcid.org web-app JSON (pub.orcid.org's robots.txt disallows all; orcid.org's allows these).

usage: orcid.py 0000-0000-0000-0000 [...]
Prints displayName, biography, employments (with organisation and years). Stored in the capture DB.
"""
import json
import sys

sys.path.insert(0, "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-berkeley")
import capstore  # noqa: E402

H = {"Accept": "application/json"}
for oid in sys.argv[1:]:
    r = capstore.fetch(f"https://orcid.org/{oid}/person.json", headers=H)
    print("##", oid, "person", r.get("status"), r.get("sha256"), r.get("error"))
    try:
        j = json.loads(r["content"])
        print("  displayName:", j.get("displayName"))
        bio = (j.get("biography") or {}).get("content")
        print("  bio:", (bio or "")[:300])
        on = j.get("publicGroupedOtherNames") or {}
        print("  other names:", list(on.keys())[:8])
    except Exception as e:
        print("  parse error", e)
    r = capstore.fetch(f"https://orcid.org/{oid}/affiliationGroups.json", headers=H)
    print("  affiliations", r.get("status"), r.get("sha256"))
    try:
        j = json.loads(r["content"])
        for kind, groups in (j.get("affiliationGroups") or {}).items():
            for g in groups:
                for a in g.get("affiliations", []):
                    sd = a.get("startDate") or {}
                    ed = a.get("endDate") or {}
                    print(f"  {kind}: {(a.get('affiliationName') or {}).get('value')} | "
                          f"{(a.get('departmentName') or {}).get('value')} | {(a.get('roleTitle') or {}).get('value')} | "
                          f"{sd.get('year')}-{ed.get('year')}")
    except Exception as e:
        print("  parse error", e)
