"""Same evaluation as v3 (eval3.Run: cal-only threshold at 0.3% FPR on non-abstained passages, paper-bootstrap FPR CI, Clopper-Pearson miss CIs,
abstain categories separate), applied to any scores.npz, v3's or a v4 candidate's.

usage: eval4.py table TAG [TAG ...]    markdown: FPR, held-out-family miss on the TEST split and on the unseen TRAIN-split outputs (selection set), per task
"""
import gzip, json, sys
import numpy as np
import v4common as K
import eval3 as E

ALPHA = 0.003
TASKS = ('polish', 'paraphrase', 'humanize', 'notes', 'continue', 'partial', 'claim')


def load(tag, score='z'):
    """tag: 'v3:all' / 'v3:lofo-qwen' (v3's outputs, read only) or a v4 tag. score 'zw' = AI-written-only score (tri variant)."""
    d = (K.V3RESULTS / tag[3:]) if tag.startswith('v3:') else (K.RESULTS / tag)
    z = np.load(d / 'scores.npz')
    m = json.loads(gzip.open(d / 'scores_meta.jsonl.gz', 'rt').read())
    r = E.Run.__new__(E.Run)
    r.tag = tag
    sfx = '' if score == 'z' else 'w'
    pick = lambda k: z[f'{k}_z{sfx}'].astype(np.float64)  # noqa: E731
    r.zc, r.zt, r.za, r.zat = pick('cal_real'), pick('test_real'), pick('ai'), pick('ai_train')
    r.mc, r.mt, r.ma, r.mat = m['cal_real'], m['test_real'], m['ai'], m['ai_train']
    return r


def cell(x):
    return f"{100 * x['miss_rate']:.2f}% ({100 * x['miss_ci'][0]:.2f}-{100 * x['miss_ci'][1]:.2f})" if x else 'n/a'


def held(tag):
    return tag.split('lofo-')[-1].split('-')[0] if 'lofo-' in tag else None


def table(tags, score='z'):
    out = ['| model | FPR (95% CI) | abstain | unseen-fam claim miss, TEST | unseen-fam claim miss, train-split (selection) | polish | paraphrase | humanize | notes | continue | partial |', '|' + '---|' * 11]
    for t in tags:
        ev = load(t, score).evaluate(ALPHA)
        f = held(t)
        if f is None:
            fam = {k: v for k, v in ev['family'].items() if k.endswith('/claim')}
            f = 'qwen'  # for 'all', show qwen only as a seen-family reference
        row = [t, E.fmt(ev['fpr']), f"{100 * ev['abstain_share_test']:.1f}%",
               cell(ev['family'].get(f'{f}/claim')), cell(ev['family_train_split'].get(f))]
        row += [cell(ev['family'].get(f'{f}/{k}')) for k in ('polish', 'paraphrase', 'humanize', 'notes', 'continue', 'partial')]
        out.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(out)


if __name__ == '__main__':
    if sys.argv[1] == 'table':
        sc = 'z'
        tags = sys.argv[2:]
        if tags and tags[0] in ('--zw',):
            sc, tags = 'zw', tags[1:]
        print(table(tags, sc))
