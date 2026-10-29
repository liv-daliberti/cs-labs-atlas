"""Markdown tables for REPORT.md from results/<tag>/metrics.json and results/flagged_by_year_school.json.
usage: tables.py > results/tables.md"""
import json
import v2common as V

TAGS = ('holdout-llama70b', 'holdout-qwen72b', 'all')


def pct(x, d=1):
    return '' if x is None else f'{100 * x:.{d}f}%'


def f3(x):
    return '' if x is None else f'{x:.4f}'


def main():
    M = {t: json.load(open(V.RESULTS / t / 'metrics.json')) for t in TAGS if (V.RESULTS / t / 'metrics.json').exists()}
    print('## Detection: AUC and TPR at the 1%-FPR threshold, test-split sources\n')
    print('Rows: generator / task. AUC is against every passage of the 2,928 test-split 2016-2021 papers. '
          '`*` marks the generator the model never saw.\n')
    print('| generator / task | ' + ' | '.join(f'{t} AUC | {t} TPR' for t in M) + ' | n |')
    print('|---|' + '---|---|' * len(M) + '---|')
    for g in V.GENS + ('all',):
        for t in V.TASKS + ('all',):
            k = f'{g}/{t}'
            if g == 'all' and t == 'all':
                continue
            cells, n = [], ''
            for tag, m in M.items():
                r = m['test_by_gen_task'].get(k)
                star = '*' if m['holdout'] == g else ''
                cells.append(f'{f3(r["auc"])}{star} | {pct(r["tpr"])}{star}' if r else ' | ')
                n = r['n'] if r else n
            print(f'| {k} | ' + ' | '.join(cells) + f' | {n} |')
    print()
    for tag, m in M.items():
        if m.get('holdout_all_outputs'):
            print(f'Held-out generator {m["holdout"]}, all of its outputs (any split): ' + '; '.join(
                f'{k.split("/")[1]} AUC {f3(v["auc"])}, TPR {pct(v["tpr"])} (n={v["n"]})' for k, v in m['holdout_all_outputs'].items()
                if k.startswith(m['holdout'] + '/')) + '\n')
    print('## Thresholds and calibration\n')
    print('| model | train human | train AI (x repeat) | threshold | cal AUC | cal passages | minutes |')
    print('|---|---|---|---|---|---|---|')
    for tag, m in M.items():
        print(f'| {tag} | {m["train_human"]} | {m["train_ai"]} (x{m["ai_repeat"]}) | {m["threshold"]:.4g} | {f3(m["cal_auc"])} | {m["cal_real_passages"]} | {m["minutes"]} |')
    print('\n## Real-text check: flagged share of every passage of the test-split 2016-2021 papers\n')
    print('| model | passages | papers | flagged | 95% CI (paper bootstrap) | sampled test humans |')
    print('|---|---|---|---|---|---|')
    for tag, m in M.items():
        rc = m['real_check']
        print(f'| {tag} | {rc["passages"]} | {rc["papers"]} | {pct(rc["flagged"], 2)} | {pct(rc["flagged_ci95"][0], 2)} - {pct(rc["flagged_ci95"][1], 2)} | '
              f'{pct(m["sampled_test_humans"]["flagged"], 2)} (n={m["sampled_test_humans"]["n"]}) |')
    print()
    for dim in ('by_year', 'by_school', 'by_kind', 'by_words', 'by_midcap_quintile', 'by_nonascii_quintile', 'by_wordish_quintile'):
        keys = list(next(iter(M.values()))['real_check'][dim])
        print(f'| {dim[3:]} | ' + ' | '.join(M) + ' | passages |')
        print('|---|' + '---|' * len(M) + '---|')
        for k in keys:
            print(f'| {k} | ' + ' | '.join(pct(m['real_check'][dim][k]['flagged'], 2) for m in M.values()) +
                  f' | {next(iter(M.values()))["real_check"][dim][k]["n"]} |')
        print()
    print('| passage position | ' + ' | '.join(M) + ' |\n|---|' + '---|' * len(M))
    for k in ('first_passage', 'later_passages'):
        print(f'| {k} | ' + ' | '.join(pct(m['real_check'][k]['flagged'], 2) for m in M.values()) + ' |')
    print('\n## Paper-level null on the test-split 2016-2021 papers\n')
    print('| model | papers | mean ai_share | ai_any | ai_any expected if passages were independent | ai_share >= 0.25 | median passages |')
    print('|---|---|---|---|---|---|---|')
    for tag, m in M.items():
        n = m['real_check']['paper_null']
        print(f'| {tag} | {n["papers"]} | {pct(n["mean_ai_share"], 2)} | {pct(n["share_ai_any"])} | {pct(n["expected_ai_any_if_independent"])} | '
              f'{pct(n["share_ai_share_ge_025"], 2)} | {n["median_passages"]:.0f} |')
    fb = V.RESULTS / 'flagged_by_year_school.json'
    if fb.exists():
        F = json.load(open(fb))
        print('\n## Final model: flagged passage share by year (usable full texts)\n')
        print('| year | scope | papers | passages | flagged share | 95% CI | mean ai_share | ai_any | ai_share >= 0.25 |')
        print('|---|---|---|---|---|---|---|---|---|')
        for t in F['table']:
            if t['school'] == 'all':
                print(f'| {t["year"]} | {t["scope"]} | {t["papers"]} | {t["passages"]} | {pct(t["flagged_share"], 2)} | {pct(t["ci_lo"], 2)} - {pct(t["ci_hi"], 2)} | '
                      f'{pct(t["mean_ai_share"], 2)} | {pct(t["share_ai_any"])} | {pct(t["share_ai_share_ge_025"], 2)} |')
        schools = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')
        print('\n## Final model: flagged passage share by year and school (all papers)\n')
        print('| year | ' + ' | '.join(schools) + ' |\n|---|' + '---|' * len(schools))
        for y in range(2016, 2027):
            row = {t['school']: t for t in F['table'] if t['year'] == y and t['scope'] == 'all papers'}
            print(f'| {y} | ' + ' | '.join(f'{pct(row[s]["flagged_share"], 2)} ({row[s]["papers"]})' if s in row else '' for s in schools) + ' |')
        print('\n' + json.dumps(F['summary']))


if __name__ == '__main__':
    main()
