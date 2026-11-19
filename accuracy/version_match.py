"""Version match for lab coverage (2026-11-19, coordinator answer to the Harvard/JHU g9 coverage review).

A DBLP record often names the venue version of a work that the build holds as its arXiv preprint or its publisher version under a
different DOI and a slightly different title (Harvard: Doshi-Velez ICLR 2025 vs the arXiv "Federated ADMM from Bayesian Duality").
The DOI/normalized-title match of evidence.py cannot see that. `same_work` accepts a build row of the SAME PI as the same work when all hold:
  * the row's year lies in [dblp year - 3, dblp year + 1] (a preprint comes before its venue version; a late publisher date is allowed one year);
  * at least 75% of the DBLP authors' family names appear in the row's byline (or in one of its editions' bylines);
  * the titles share content words (>= 3 letters, not a stopword): 'strong' when at least 3 agree and they are at least 90% of the shorter
    title (the same title with a subtitle, a suffix such as "(Experience Report)" or a shortened form), 'candidate' when at least 2 agree and
    they are at least 40% of the shorter title. A candidate can be a DIFFERENT paper of the same authors (Koehn/Knowles have several on neural
    translation), so only 'strong' counts as in the build; the sheet lists candidates for the judge, who must cite stored evidence to accept one.
It never matches on the PI alone and never across PIs."""
import re
import unicodedata

STOP = {'the', 'and', 'for', 'with', 'from', 'into', 'via', 'using', 'towards', 'toward', 'their', 'that', 'this', 'are', 'its', 'not',
        'how', 'what', 'can', 'on', 'of', 'in', 'to', 'an', 'a', 'by', 'at', 'is', 'as', 'or', 'we', 'new', 'study', 'analysis',
        'approach', 'method', 'methods', 'based', 'learning'}


def _fold(t):
    t = unicodedata.normalize('NFKD', str(t or '')).lower()
    return ''.join(c for c in t if not unicodedata.combining(c))


def words(title):
    return {w for w in re.findall(r'[a-z0-9]+', _fold(title)) if len(w) >= 3 and w not in STOP}


def family(name):
    n = re.sub(r'\s+\d{4}$', '', _fold(name)).strip()      # DBLP homonym number
    if ',' in n:
        n = n.split(',')[0]
    toks = [t for t in re.split(r'[\s.]+', n.replace('-', ' ')) if t]
    return toks[-1] if toks else ''


def _bylines(row):
    out = [row.get('byline') or []] + [e.get('byline') or [] for e in row.get('editions') or []]
    return [{family(a) for a in b} - {''} for b in out]


def same_work(dblp, row):
    """'strong', 'candidate' or None. dblp: {'title','year','authors'}; row: a lab_papers row of the same PI."""
    try:
        ry = int(str(row.get('date') or '')[:4])
        dy = int(dblp['year'])
    except (TypeError, ValueError):
        return None
    if not dy - 3 <= ry <= dy + 1:
        return None
    a, b = words(dblp.get('title')), words(row.get('title'))
    common = a & b
    if len(common) < 2 or len(common) < 0.4 * min(len(a), len(b)):
        return None
    fam = {family(x) for x in dblp.get('authors') or []} - {''}
    if not fam or not any(len(fam & s) >= 0.75 * len(fam) for s in _bylines(row)):
        return None
    return 'strong' if len(common) >= 3 and len(common) >= 0.9 * min(len(a), len(b)) else 'candidate'
