"""Small markdown/table helpers shared by the AI-dose reports."""
import numpy as np
import pandas as pd


def md_table(df, floatfmt='{:.3f}', pct=(), ci=()):
    """DataFrame -> markdown pipe table. `pct`: columns shown as percentages; `ci`: (est, lo, hi) column triples shown as 'est [lo, hi]'."""
    d = df.copy()
    cols = []
    for c in d.columns:
        cols.append(c)
    out_cols = {}
    skip = set()
    for est, lo, hi in ci:
        f = (lambda v: '' if pd.isna(v) else f'{100 * v:.2f}') if est in pct else (lambda v: '' if pd.isna(v) else floatfmt.format(v))
        out_cols[est] = [f'{f(a)} [{f(b)}, {f(c)}]' if not pd.isna(a) else '' for a, b, c in zip(d[est], d[lo], d[hi])]
        skip |= {lo, hi}
    rows = []
    heads = [c for c in cols if c not in skip]
    for i in range(len(d)):
        r = []
        for c in heads:
            if c in out_cols:
                r.append(out_cols[c][i])
                continue
            v = d[c].iloc[i]
            if isinstance(v, (float, np.floating)):
                r.append('' if np.isnan(v) else (f'{100 * v:.2f}' if c in pct else floatfmt.format(v)))
            else:
                r.append(str(v))
        rows.append(r)
    head = '| ' + ' | '.join(heads) + ' |\n|' + '|'.join('---' for _ in heads) + '|\n'
    return head + '\n'.join('| ' + ' | '.join(r) + ' |' for r in rows) + '\n'
