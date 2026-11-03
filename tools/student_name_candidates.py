"""Queue the same-lab one-letter surname typos (R-STU-13) for review: collects every school's report.json
`studentSurnameTypoCandidates` into hierarchy/reviewed/student-name-candidates.json (student-identity-review.json shape,
`verdict` empty, plus the `signals` found). Rows already judged in the identity review are skipped by the build; rows
already in the queue keep any hand-written fields.
  student_name_candidates.py [--root <dir holding <school>/report.json>] [--out <file>]"""
import argparse, json
from pathlib import Path

import atlas_paths as P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', help='package root (PI_HIERARCHY_OUT of a trial build); default the live packages')
    ap.add_argument('--review', help='identity review file whose judged pairs leave the queue; default the registered reviewed path')
    ap.add_argument('--out', help='queue file; default the registered reviewed path')
    a = ap.parse_args()
    out = Path(a.out) if a.out else P.data('student-name-candidates.json')
    old = json.loads(out.read_text()) if out.exists() else []
    rv = Path(a.review) if a.review else P.data('student-identity-review.json')
    judged = {(x['school'], x['pi'], x['a'][0], x['b'][0]) for x in (json.loads(rv.read_text()) if rv.exists() else []) if x.get('verdict')}
    key = lambda x: (x['school'], x['pi'], x['a'][0], x['b'][0])
    rows = {key(x): x for x in old if key(x) not in judged}
    for school in P.SCHOOL_IDS:
        rp = (Path(a.root) / school / 'report.json') if a.root else P.data('report.json', school)
        if rp.exists():
            for x in json.loads(rp.read_text()).get('studentSurnameTypoCandidates') or []:
                if key(x) not in judged:
                    rows.setdefault(key(x), x)
    out.write_text(json.dumps(sorted(rows.values(), key=key), indent=1, ensure_ascii=False) + '\n')
    print(f'{len(rows)} candidates -> {out}')


if __name__ == '__main__':
    main()
