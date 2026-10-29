"""Summarize verdicts.jsonl into summary.json (precision and coverage with Wilson 95% intervals).

Precision = correct / (correct + incorrect); 'unclear' items stay out of every denominator and are counted.
Lab-paper coverage = in_build share of the coverage items judged true lab papers.
Student coverage = linked share of the sampled thesis advisees who have a co-authored paper with the PI.
'meeting_abstract' marks conference/meeting abstracts judged not_a_paper; the alternative figures count them correct.
usage: summarize.py
"""
import collections, json, math, sys
from pathlib import Path

ACC = Path(__file__).parent
sys.path.insert(0, str(ACC))
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']


def wilson(k, n, z=1.959964):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return dict(k=k, n=n, p=round(p, 4), lo=round(max(0.0, c - h), 4), hi=round(min(1.0, c + h), 4))


def prec(rows, abstracts_ok=False):
    ok = sum(r['verdict'] == 'correct' or (abstracts_ok and r.get('policy') == 'meeting_abstract') for r in rows if r['verdict'] != 'unclear')
    n = sum(r['verdict'] != 'unclear' for r in rows)
    out = wilson(ok, n) or {}
    out['unclear'] = sum(r['verdict'] == 'unclear' for r in rows)
    return out


def main():
    V = [json.loads(l) for l in open(ACC / 'verdicts.jsonl')]
    S = json.load(open(ACC / 'sample.json'))
    out = dict(date=S['date'], seed=S['seed'], files=S['files'], n_verdicts=len(V), schools={}, pooled={})
    groups = {s: [v for v in V if v['school'] == s] for s in SCHOOLS}
    groups['pooled'] = V
    for g, rows in groups.items():
        lab = [r for r in rows if r['sample'] == 'lab_precision']
        stu = [r for r in rows if r['sample'] == 'student_precision']
        cov = [r for r in rows if r['sample'] == 'lab_coverage']
        sc = [r for r in rows if r['sample'] == 'student_coverage']
        true_lab = [r for r in cov if r.get('true_lab_paper') is True]
        d = dict(
            lab_precision_uniform=prec([r for r in lab if r['stratum'] == 'uniform']),
            lab_precision_uniform_if_abstracts_count=prec([r for r in lab if r['stratum'] == 'uniform'], True),
            lab_precision_strata={st: prec([r for r in lab if r['stratum'] == st]) for st in ('advisee_unaffiliated', 'listing', 'identity_not_reviewed')},
            lab_precision_all40=prec(lab),
            student_precision_uniform=prec([r for r in stu if r['stratum'] == 'uniform']),
            student_precision_strata={st: prec([r for r in stu if r['stratum'] == st]) for st in sorted({r['stratum'] for r in stu} - {'uniform'})},
            student_precision_all40=prec(stu),
            lab_coverage=wilson(sum(bool(r.get('in_build')) for r in true_lab), len(true_lab)),
            lab_coverage_items=dict(drawn=len(cov), true_lab_papers=len(true_lab),
                                    not_lab_papers_absent=sum(r.get('true_lab_paper') is False and not r.get('in_build') for r in cov),
                                    not_lab_papers_in_build=sum(r.get('true_lab_paper') is False and bool(r.get('in_build')) for r in cov),
                                    unclear=sum(r['verdict'] == 'unclear' for r in cov)),
            student_coverage=wilson(sum(bool(r.get('linked')) for r in sc if r.get('has_coauthored_paper')), sum(bool(r.get('has_coauthored_paper')) for r in sc)),
            student_coverage_items=dict(drawn=len(sc), no_coauthored_paper=sum(not r.get('has_coauthored_paper') for r in sc),
                                        duplicate_record=sum(bool(r.get('duplicate_record')) for r in sc)),
            failures=dict(collections.Counter(r['failure_type'] for r in rows if r['verdict'] == 'incorrect')),
            secondary_flags=dict(date_wrong=sum(bool(r.get('date_wrong')) for r in rows), metadata_wrong=sum(bool(r.get('metadata_wrong')) for r in rows)),
        )
        if g != 'pooled':
            d['population'] = dict(lab_papers=S['schools'][g]['n_lab_papers'], student_papers=S['schools'][g]['n_student_papers'],
                                   coverage_pool=S['schools'][g]['n_coverage_pool'], student_candidates=S['schools'][g]['n_student_candidates'])
            out['schools'][g] = d
        else:
            out['pooled'] = d
    # size-weighted point estimate of uniform lab precision over the six schools
    w = {s: S['schools'][s]['n_lab_papers'] for s in SCHOOLS}
    out['pooled']['lab_precision_uniform_size_weighted'] = round(sum(w[s] * out['schools'][s]['lab_precision_uniform']['p'] for s in SCHOOLS) / sum(w.values()), 4)
    w2 = {s: S['schools'][s]['n_student_papers'] for s in SCHOOLS}
    out['pooled']['student_precision_uniform_size_weighted'] = round(sum(w2[s] * out['schools'][s]['student_precision_uniform']['p'] for s in SCHOOLS) / sum(w2.values()), 4)
    out['incorrect'] = [dict(school=r['school'], sample=r['sample'], stratum=r['stratum'], item=r['item'], failure_type=r['failure_type'],
                             reason=r['reason'], policy=r.get('policy'), evidence=r['evidence']) for r in V if r['verdict'] == 'incorrect']
    out['unclear'] = [dict(school=r['school'], sample=r['sample'], item=r['item'], reason=r['reason']) for r in V if r['verdict'] == 'unclear']
    out['screened'] = [json.loads(l) for l in open(ACC / 'screened.jsonl')] if (ACC / 'screened.jsonl').exists() else []
    from sample import sha, H, FILES
    later = {sc: {f: h for f in FILES for h in [sha(H / sc / f)] if h != S['files'][sc][f]} for sc in SCHOOLS}
    out['notes'] = dict(measured_build='the sha256 in files (the 13:40 build, hashed when the sample was drawn)',
                        rebuilt_after_draw={sc: v for sc, v in later.items() if v},
                        rebuilt_after_draw_note='package files whose hash differs from the measured build when summarize.py ran; '
                                                'for the 14:06-14:16 rebuild of princeton/cmu/epfl the row counts and every sampled '
                                                'row key were checked and are unchanged')
    (ACC / 'summary.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for g in SCHOOLS + ['pooled']:
        d = out['schools'].get(g) or out['pooled']
        f = lambda x: f"{x['p']:.3f} [{x['lo']:.3f},{x['hi']:.3f}] n={x['n']}" if x else '-'
        print(g, '| lab', f(d['lab_precision_uniform']), '| stu', f(d['student_precision_uniform']), '| cov', f(d['lab_coverage']), '| scov', f(d['student_coverage']))
    print('weighted', out['pooled']['lab_precision_uniform_size_weighted'], out['pooled']['student_precision_uniform_size_weighted'])


if __name__ == '__main__':
    main()
