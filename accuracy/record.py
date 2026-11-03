"""Append hand verdicts to verdicts.jsonl (helper). stdin: one item per line, tab-separated:
    <ref> <verdict correct|incorrect|unclear> <failure_type or -> <reason> [<evidence>] [<extra fields as JSON>]
Coverage items carry extra fields: true_lab_paper (bool) and in_build (bool); verdict is correct when the build agrees
with the truth (a true lab paper present, or a non-lab paper absent), and only true lab papers enter the coverage
denominator. Student-coverage items carry has_coauthored_paper and linked.
<ref> is the row index (lab/student samples) or the item key (coverage samples).
(ACCURACY_ROUND=r2 writes the round's own verdicts-<school>.jsonl; the 2026-10-29 files are not touched)
usage: record.py <school> <lab_precision|student_precision|lab_coverage|student_coverage>
"""
import datetime, json, os, sys
from pathlib import Path

ACC = Path(__file__).parent
FAIL = {'namesake', 'not_at_school', 'outside_appointment', 'not_a_paper', 'wrong_student', 'other', 'missing_from_build',
        'student_not_linked'}


RELEASED = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')


def round_dir():
    """The directory of the active round (env ACCURACY_ROUND=r2), or None for the 2026-10-29 files."""
    r = os.environ.get('ACCURACY_ROUND')
    if not r:
        return None
    from sample import ROUNDS
    return ACC / ROUNDS[r]['dir']


def files(school):
    """(draw file, verdict file): in a round (ACCURACY_ROUND=r2) every school has its own pair in the round's directory; for the
    2026-10-29 measurement the released schools share sample.json and verdicts.jsonl and any other school has its own."""
    rd = round_dir()
    if rd:
        return rd / f'sample-{school}.json', rd / f'verdicts-{school}.jsonl'
    return (ACC / 'sample.json', ACC / 'verdicts.jsonl') if school in RELEASED else (ACC / f'sample-{school}.json', ACC / f'verdicts-{school}.jsonl')


def main(school, sample):
    sf, vf = files(school)
    S = json.load(open(sf))['schools'][school]
    if sample == 'student_coverage':
        items = {c['key']: dict(c, stratum='thesis_advisee_phd_ge_2018') for c in S['student_coverage_order']}
    else:
        items = {(str(it['i']) if 'i' in it else it['key']): it for it in S[sample]}
    done = set()
    if vf.exists():
        for line in open(vf):
            d = json.loads(line); done.add((d['school'], d['sample'], d['item']))
    out = []
    for line in sys.stdin:
        if not line.strip():
            continue
        f = line.rstrip('\n').split('\t')
        ref, verdict, ft, reason = f[0].strip(), f[1].strip(), f[2].strip(), f[3].strip()
        ev = f[4].strip() if len(f) > 4 else ''
        extra = json.loads(f[5]) if len(f) > 5 and f[5].strip() else {}
        it = items[ref]
        assert verdict in ('correct', 'incorrect', 'unclear'), verdict
        assert verdict != 'incorrect' or ft in FAIL, ft
        key = it['key']
        if (school, sample, key) in done:
            print('skip duplicate', key, file=sys.stderr); continue
        done.add((school, sample, key))
        if not ev and 'openalex.org/W' in key:
            ev = key.split('|')[-1]
        out.append(dict(school=school, sample=sample, stratum=it.get('stratum'), item=key, row=it.get('i'), verdict=verdict,
                        failure_type=ft if verdict == 'incorrect' else None, reason=reason, evidence=ev or f'hierarchy/{school}',  # route-ok: a label, not a path
                        judged_at=datetime.datetime.now().isoformat(timespec='seconds'), **extra))
    with open(vf, 'a') as fh:
        for d in out:
            fh.write(json.dumps(d, ensure_ascii=False) + '\n')
    print(f'recorded {len(out)}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
