"""Content-preservation checks of a rewrite against its source abstract (pure Python, tested on fixtures in tests/test_allai.py).

numbers   every numeric token (integers, decimals, 1,000-style groupings, percentages; the '%' is not part of the token) of the source
          must appear in the rewrite; a number in the rewrite that is not in the source is 'new'.  Number words are not matched.
terms     'named methods': tokens with an internal capital or a digit and at least two capitals-or-digits (BERT, ResNet-50, GPT-4, PyTorch, k-NN,
          LoRA), plus capitalised mid-sentence names are NOT included (too noisy). A term is kept when the rewrite contains it
          case-insensitively with hyphens and spaces ignored.
checks(src, rewrite) -> dict(n_num, num_lost, num_new, n_term, term_lost, len_ratio)
keep_rule(ok, why, checks) -> (bool, reason)
"""
import re

NUM = re.compile(r'(?<![A-Za-z0-9_.])\d+(?:[.,]\d+)*(?![A-Za-z0-9_])')
TERM = re.compile(r'\b[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*\b')


def norm_num(s):
    s = s.rstrip('.,')
    return s.replace(',', '')


LABEL = re.compile(r'\b[A-Za-z]+-?\d+[A-Za-z0-9-]*\b')   # ResNet-50, GPT-4, x86: names with a digit are checked as terms, not as numbers


def numbers(text):
    text = LABEL.sub(' ', text)
    return [norm_num(m.group(0)) for m in NUM.finditer(text)]


def is_term(tok):
    caps = sum(c.isupper() or c.isdigit() for c in tok)
    return len(tok) >= 2 and caps >= 2 and not tok.isdigit() and any(c.isalpha() for c in tok)


def terms(text):
    out = set()
    for m in TERM.finditer(text):
        t = m.group(0)
        if is_term(t):
            out.add(t)
    return out


def squash(s):
    return re.sub(r'[\s\-_]', '', s).lower()


def checks(src, rew):
    ns, nr = numbers(src), numbers(rew)
    sset, rset = set(ns), set(nr)
    lost = [n for n in sset if n not in rset]
    new = [n for n in rset if n not in sset]
    ts = terms(src)
    rsq = squash(rew)
    tlost = [t for t in ts if squash(t) not in rsq]
    return dict(n_num=len(sset), num_lost=len(lost), num_new=len(new), n_term=len(ts), term_lost=len(tlost),
                len_ratio=round(len(rew.split()) / max(1, len(src.split())), 3))


def keep_rule(ok, why, f, tol=0.25):
    if not ok:
        return False, why or 'not_ok'
    if f['n_num'] and f['num_lost'] / f['n_num'] >= tol:
        return False, 'numbers_lost'
    if f['num_new'] > max(1, tol * max(f['n_num'], 1)):
        return False, 'numbers_added'
    if f['n_term'] and f['term_lost'] / f['n_term'] >= tol:
        return False, 'terms_lost'
    return True, ''
