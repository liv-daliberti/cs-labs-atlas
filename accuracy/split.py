"""How a round's judgments split between judging agents (helper). Reads the round's draws, counts the judgments per school
(lab precision, student precision, lab coverage, student coverage as far as the candidates go) and groups the schools into
`--agents N` balanced groups. The evidence sheets of a school come from evidence.py with ACCURACY_ROUND=<id>; verdicts are
appended with record.py the same way (one verdicts-<school>.jsonl per school, so agents on different schools never write the
same file).

usage: split.py <round id> [--agents N]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sample import ACC_DIR, ROUNDS  # noqa: E402


def counts(rnd):
    cfg = ROUNDS[rnd]
    out = {}
    for s in cfg['schools']:
        f = ACC_DIR / cfg['dir'] / f'sample-{s}.json'
        if not f.exists():
            continue
        m = json.load(open(f))['schools'][s]
        cand = len(m['student_coverage_order'])
        out[s] = dict(lab=len(m['lab_precision']), student=len(m['student_precision']), lab_cov=len(m['lab_coverage']),
                      student_cov=min(cand, 50), student_cov_candidates=cand, student_cov_pool=m['n_student_candidates'])
    return out


def group(c, k):
    """Greedy balanced grouping of the schools into k groups by judgment count (largest first)."""
    g = [[0, []] for _ in range(k)]
    for s, v in sorted(c.items(), key=lambda kv: -(kv[1]['lab'] + kv[1]['student'] + kv[1]['lab_cov'] + kv[1]['student_cov'])):
        t = min(g, key=lambda x: x[0])
        t[0] += v['lab'] + v['student'] + v['lab_cov'] + v['student_cov']; t[1].append(s)
    return g


if __name__ == '__main__':
    rnd = sys.argv[1]
    k = int(sys.argv[sys.argv.index('--agents') + 1]) if '--agents' in sys.argv else 3
    c = counts(rnd)
    for s, v in c.items():
        print(f"{s:10s} lab {v['lab']} student {v['student']} lab_cov {v['lab_cov']} student_cov <= {v['student_cov']} "
              f"(candidates {v['student_cov_candidates']}, pool {v['student_cov_pool']}) = {v['lab'] + v['student'] + v['lab_cov'] + v['student_cov']}")
    print('total <=', sum(v['lab'] + v['student'] + v['lab_cov'] + v['student_cov'] for v in c.values()))
    for i, (n, ss) in enumerate(group(c, k), 1):
        print(f'agent {i}: {n} judgments, schools {ss}')
