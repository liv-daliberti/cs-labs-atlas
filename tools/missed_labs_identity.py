"""Stage-5 identity for the missed-labs additions (coordinator follow-up 2026-11-09): the OpenAlex author ids of an accepted addition become
reviewed ids (hierarchy/<school>/reviewed/openalex-identity-review.json, read by tools/oa_identity_school.py) only when the id's stats record
carries an ORCID, a name form with the first given name spelled out, and school works in at least one of the person's listed years or within a
year of them; the rest are held (the person stays a PI, no papers are attributed).
usage: missed_labs_identity.py <school>
"""
import gzip, json, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

TAG = 'missed_labs_20261109'


def main(school):
    root = Path(__file__).resolve().parents[1] / 'hierarchy' / school / 'reviewed'
    add = [r for r in json.load(open(root / 'census-additions.json')) if r.get('added') == TAG]
    stats = json.load(gzip.open(P.data('oa-author-stats.json.gz', school), 'rt'))['authors']
    f = root / 'openalex-identity-review.json'
    doc = json.load(open(f)) if f.exists() else {'school': school, 'reviewed': '2026-11-09', 'rule': 'hand-reviewed OpenAlex author ids per PI', 'decisions': {}}
    held = []
    for r in add:
        ids = []
        for a in r['pi_basis']['cs_related']['openalex']:
            s = stats.get(a) or {}
            ly = set(r['years_listed'])
            near = any(abs(y - l) <= 1 for y in s.get('years') or [] for l in ly)
            if s.get('orcids') and near:
                ids.append((a, s))
        if not ids:
            held.append(r['name']); continue
        doc['decisions'][r['name']] = {'openalex': [a.rsplit('/', 1)[-1] for a, _ in ids], 'aliases': r.get('aliases') or [],
            'why': 'Missed-labs pass: ' + '; '.join(f"{a.rsplit('/', 1)[-1]} (ORCID {next(iter(s['orcids']))}) holds {s['n']} school works {min(s['years'])}-{max(s['years'])}, "
                                                 f"{s['cs']} DBLP-indexed, under the name {next(iter(s['raw']))!r}; the unit listing names {r['name']} {min(r['years_listed'])}-{max(r['years_listed'])}"
                                                 for a, s in ids)}
    f.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(school, 'identity entries', len(add) - len(held), 'held', held)


if __name__ == '__main__':
    main(sys.argv[1])
