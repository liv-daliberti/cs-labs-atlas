"""Markdown helpers shared by the three report writers."""
import numpy as np


def f(x, d=4, signed=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return 'n/a'
    s = f'{x:+.{d}f}' if signed else f'{x:.{d}f}'
    return s.replace('-', '−') if False else s


def ci(est, lo, hi, d=4, signed=True):
    return f'{f(est, d, signed)} [{f(lo, d, signed)}, {f(hi, d, signed)}]'


def md_table(rows, header):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join(['---'] * len(header)) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def pick(df, **kw):
    m = np.ones(len(df), bool)
    for k, v in kw.items():
        m &= (df[k] == v).to_numpy() if not isinstance(v, (list, tuple, set)) else df[k].isin(list(v)).to_numpy()
    return df[m]


def row_of(df, **kw):
    d = pick(df, **kw)
    return None if len(d) == 0 else d.iloc[0]


def now():
    import time
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
