"""Summarize verdicts.jsonl into summary.json (precision and coverage with Wilson 95% intervals).

Precision = correct / (correct + incorrect); 'unclear' items stay out of every denominator and are counted.
Lab-paper coverage = in_build share of the coverage items judged true lab papers.
Student coverage = linked share of the sampled thesis advisees who have a co-authored paper with the PI.
'meeting_abstract' marks conference/meeting abstracts judged not_a_paper; the alternative figures count them correct.
usage: summarize.py [--school <key>] | --round <id>   (ACCURACY_ROUND=<id> routes --school to the round's files)
"""
import collections, json, math, os, sys
from pathlib import Path

ACC = Path(__file__).parent
sys.path.insert(0, str(ACC))
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']


def round_dir_():
    from record import round_dir
    return round_dir()


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


def one_school(school):
    """The four measures of a school outside the six released ones (draw sample-<school>.json, verdicts-<school>.jsonl) into
    summary-<school>.json; nothing is pooled and the released figures are not touched."""
    from record import files, round_dir
    from sample import FILES, P, sha
    sf, vf = files(school)
    S = json.load(open(sf))
    V = [json.loads(l) for l in open(vf)]
    lab = [r for r in V if r['sample'] == 'lab_precision']
    stu = [r for r in V if r['sample'] == 'student_precision']
    cov = [r for r in V if r['sample'] == 'lab_coverage']
    sc = [r for r in V if r['sample'] == 'student_coverage']
    true_lab = [r for r in cov if r.get('true_lab_paper') is True]
    d = dict(school=school, date=S['date'], seed=S['seed'], n_verdicts=len(V), files=S['files'][school],
             files_now={f: sha(P.SchoolDir(school) / f) for f in FILES},
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
                                     not_lab_papers_in_build=sum(r.get('true_lab_paper') is False and bool(r.get('in_build')) for r in cov)),
             student_coverage=wilson(sum(bool(r.get('linked')) for r in sc if r.get('has_coauthored_paper')), sum(bool(r.get('has_coauthored_paper')) for r in sc)),
             student_coverage_items=dict(drawn=len(sc), no_coauthored_paper=sum(not r.get('has_coauthored_paper') for r in sc)),
             failures=dict(collections.Counter(r['failure_type'] for r in V if r['verdict'] == 'incorrect')),
             incorrect=[dict(sample=r['sample'], stratum=r['stratum'], item=r['item'], failure_type=r['failure_type'], reason=r['reason'],
                             policy=r.get('policy')) for r in V if r['verdict'] == 'incorrect'],
             unclear=[dict(sample=r['sample'], item=r['item'], reason=r['reason']) for r in V if r['verdict'] == 'unclear'],
             screened=[json.loads(l) for l in open((round_dir() or ACC) / f'screened-{school}.jsonl')] if ((round_dir() or ACC) / f'screened-{school}.jsonl').exists() else [])
    d['population'] = {k: S['schools'][school][k] for k in ('n_lab_papers', 'n_student_papers', 'n_coverage_pool', 'n_student_candidates')}
    rd = round_dir()
    if rd:  # a round: the sizes drawn against the sizes judged (student coverage is judged as far as the candidates go)
        d['round'] = dict(id=os.environ['ACCURACY_ROUND'], sizes=S.get('sizes'), judged={k: sum(r['sample'] == k for r in V) for k in
                          ('lab_precision', 'student_precision', 'lab_coverage', 'student_coverage')})
    ((rd or ACC) / f'summary-{school}.json').write_text(json.dumps(d, indent=1, ensure_ascii=False))
    f = lambda x: f"{x['p']:.3f} [{x['lo']:.3f},{x['hi']:.3f}] k={x['k']} n={x['n']}" if x else '-'
    print(school, '| lab', f(d['lab_precision_uniform']), '| stu', f(d['student_precision_uniform']), '| cov', f(d['lab_coverage']), '| scov', f(d['student_coverage']))


def pooled_round(rnd):
    """Pool a round's per-school verdicts (ACCURACY_ROUND=<rnd>) into the round's summary.json: every school weighted equally
    (50 uniform rows each) and the Wilson interval on the pooled counts."""
    from record import round_dir
    from sample import ROUNDS
    rd = round_dir()
    schools = [s for s in ROUNDS[rnd]['schools'] if (rd / f'verdicts-{s}.jsonl').exists()]
    V = [json.loads(l) for s in schools for l in open(rd / f'verdicts-{s}.jsonl')]
    lab = [r for r in V if r['sample'] == 'lab_precision']
    stu = [r for r in V if r['sample'] == 'student_precision']
    cov = [r for r in V if r['sample'] == 'lab_coverage' and r.get('true_lab_paper') is True]
    sc = [r for r in V if r['sample'] == 'student_coverage' and r.get('has_coauthored_paper')]
    d = dict(round=rnd, seed=ROUNDS[rnd]['seed'], schools=schools, n_verdicts=len(V),
             lab_precision_uniform=prec([r for r in lab if r['stratum'] == 'uniform']),
             lab_precision_uniform_if_abstracts_count=prec([r for r in lab if r['stratum'] == 'uniform'], True),
             student_precision_uniform=prec([r for r in stu if r['stratum'] == 'uniform']),
             lab_coverage=wilson(sum(bool(r.get('in_build')) for r in cov), len(cov)),
             student_coverage=wilson(sum(bool(r.get('linked')) for r in sc), len(sc)),
             per_school={s: json.loads((rd / f'summary-{s}.json').read_text()) for s in schools if (rd / f'summary-{s}.json').exists()},
             failures=dict(collections.Counter(r['failure_type'] for r in V if r['verdict'] == 'incorrect')))
    (rd / 'summary.json').write_text(json.dumps(d, indent=1, ensure_ascii=False))
    print(json.dumps({k: d[k] for k in ('lab_precision_uniform', 'student_precision_uniform', 'lab_coverage', 'student_coverage')}))


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
    from sample import sha, P, FILES
    later = {sc: {f: h for f in FILES for h in [sha(P.SchoolDir(sc) / f)] if h != S['files'][sc][f]} for sc in SCHOOLS}
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
    if len(sys.argv) == 3 and sys.argv[1] == '--school':
        one_school(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == '--round':  # ACCURACY_ROUND=<id> summarize.py --round <id>: every school, then the pool
        os.environ['ACCURACY_ROUND'] = sys.argv[2]
        from sample import ROUNDS
        for sc_ in ROUNDS[sys.argv[2]]['schools']:
            if (round_dir_() / f'verdicts-{sc_}.jsonl').exists():
                one_school(sc_)
        pooled_round(sys.argv[2])
    else:
        main()
