"""Shared helpers of the CS-related scope review: the author index (author_index.py output), OpenAlex id resolution by
name, CS-venue work examples, and listing quotes read from a stored capture's text.
"""
import collections, gzip, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'tools'))
from pi_hierarchy import Name, toks  # noqa: E402

IDX_DIR = Path('/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/csrel')
_IDX, _BYLAST = {}, {}


def index(school):
    if school not in _IDX:
        A = json.load(gzip.open(IDX_DIR / f'{school}-authors.json.gz', 'rt'))
        by = collections.defaultdict(set)
        for aid, r in A.items():
            for raw in r['raw']:
                t = toks(raw)
                if len(t) >= 2:
                    by[t[-1]].add(aid); by[t[0]].add(aid)
        _IDX[school], _BYLAST[school] = A, by
    return _IDX[school]


def oa_matches(school, names):
    """OpenAlex authors of the school index whose raw names match any of names (pi_hierarchy.Name rules)."""
    A = index(school); nm = Name(list(names)); out = []
    cand = set()
    for n in names:
        t = toks(n)
        if t:
            cand |= _BYLAST[school].get(t[-1], set()) | _BYLAST[school].get(''.join(t[1:]), set())
    for aid in cand:
        r = A[aid]
        if any(nm.match(raw) for raw in r['raw']):
            out.append(dict(id=aid, n=r['n'], cs=r['cs'], last=r['last'], years=sorted(map(int, r['years'])), raw=list(r['raw'])[:3],
                            orcid=r['orcid'], venues=list(r['venues'])[:4]))
    return sorted(out, key=lambda x: -x['n'])


def cs_works(school, ids, k=None):
    A = index(school); out = []
    for i in ids:
        out += [dict(oa=w[0], year=w[1], venue=w[2], title=w[3]) for w in A.get(i, {}).get('cs_works', [])]
    out.sort(key=lambda w: (w['year'], w['oa']))
    return out[:k] if k else out


def cs_count(school, ids):
    A = index(school)
    return sum(A.get(i, {}).get('cs', 0) for i in ids), sum(A.get(i, {}).get('n', 0) for i in ids)


def orcids(school, ids):
    A = index(school)
    return sorted({o for i in ids for o in A.get(i, {}).get('orcid', [])})


def find_quote(text, name_forms, after_rx=r'(?:Professor|Lecturer|Chair|Dean|Scientist|Emerit\w*|Adjunct|Director|Senior|Assistant|Associate|Professeur\w*|MER|Visiting)[^|]{0,60}?', maxlen=120):
    """The first 'Name ... rank' span in text, for one of name_forms written as on the page; None if absent."""
    for nf in name_forms:
        for m in re.finditer(re.escape(nf), text):
            tail = text[m.end():m.end() + 160]
            r = re.match(r'\s*(?:[,\-–|]\s*)?(?:Ph\.?D\.?\s*)?(' + after_rx + r')(?=\s|$|,|\.)', tail)
            if r:
                q = text[m.start():m.end() + r.end()]
                return q[:maxlen].rstrip(' ,')
    return None
