"""Channel arxiv_loose (2026-10-30): arXiv versions of missing lab papers posted under a different title (a preprint
title that changed before publication), from the local arXiv OAI-PMH index (claude-cmu-20261017/raw/arxiv_oai: cs,
stat, eess, q-bio, quant-ph, math since 2015), never arxiv.org. Applies to papers with a title of >= 20 normalized
characters and no arXiv link known yet.

Candidates: arXiv records sharing the paper's rarest significant title words (each word on <= 4,000 records). A record
is the paper's preprint only when ALL of these hold:
  - title similarity (difflib ratio of the normalized titles) >= 0.90 with word Jaccard >= 0.70, or >= 0.85 with
    Jaccard >= 0.80; the same numbers and roman numerals; no item-type word (artifact, demo, abstract, part, ...) in
    the catalog title that the arXiv title lacks; every significant word of the catalog title in the arXiv title, which
    may add words (a system name, a qualifier) but not drop or swap any (strict_ok)
  - the same author set: every family name of the paper's byline (at most the first 8) is among the record's author
    families, or (bylines over 8 names) at least 6 of the first 8 and every lab PI are; a byline of one or two names
    needs both the names and an identical first author
  - the record's first version from 3 years before to 1 year after the paper's year
  - no second record passes with a similar score (a tie is ambiguous and dropped)
A match -> the bulk copy on GCS (storage.googleapis.com/arxiv-dataset, ftp_common.bulk_rows); the collector's identity
check (the catalog title in the file, or the arXiv id against an arXiv DOI) still applies, and a title that changed
completely fails it, so a match is written only after the hand-checked sample (docs/CHANNELS.md) passed.
"""
import difflib
import gzip
import json
import re
import unicodedata
from collections import Counter, defaultdict

NAME = 'arxiv_loose'
MIN_SIM, MIN_JACCARD, MAX_POSTING = 0.85, 0.70, 4000
# a hand-checked sample of 40 matches at similarity >= 0.80 / Jaccard >= 0.55 (2026-10-30) had 10 that were not the
# paper: research artifacts and demo abstracts matched to the paper, a series part (II vs VII), related papers of one
# group. Hence: similarity >= 0.90 with Jaccard >= 0.70, or similarity >= 0.85 with Jaccard >= 0.80; equal numbers and
# roman numerals; no item-type word in the catalog title that the arXiv title lacks.
TYPE_WORDS = {'artifact', 'artefact', 'experiments', 'experiment', 'demo', 'demonstration', 'abstract', 'poster', 'workshop', 'proceedings',
              'solution', 'tutorial', 'extended', 'supplementary', 'supplement', 'appendix', 'erratum', 'errata', 'correction', 'corrigendum',
              'part', 'keynote', 'panel', 'dataset', 'code', 'software', 'thesis', 'dissertation', 'report', 'summary', 'overview',
              'rejoinder', 'discussion', 'comment', 'comments', 'reply', 'response', 'invited', 'chapter', 'preface', 'editorial'}
NEGATION = {'non', 'not', 'no', 'un', 'without', 'anti'}
# a second hand-checked sample (35 at the rule above) still had rejoinders matched to their paper, 'non-symmetric'
# matched to 'symmetric', and word substitutions (binary / network systems, stochastic / robust, context / time).
ROMAN = re.compile(r'^(?:i{1,3}|iv|v|vi{1,3}|ix|x|xi{1,3})$')


def _numbers(t):
    toks = re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower())
    return sorted(x for x in toks if x.isdigit() or ROMAN.match(x))


def strict_ok(title, arxiv_title, sim, jac):
    if not ((sim >= 0.90 and jac >= 0.70) or (sim >= 0.85 and jac >= 0.80)):
        return False
    if _numbers(title) != _numbers(arxiv_title):
        return False
    ct = set(re.findall(r'[a-z]+', (title or '').lower()))
    at = set(re.findall(r'[a-z]+', (arxiv_title or '').lower()))
    if (ct - at) & TYPE_WORDS or (ct ^ at) & NEGATION:
        return False
    import ftp_common  # noqa: F401  (puts the CMU stage's tools, arxiv_oai among them, on sys.path)
    import arxiv_oai as ao
    stem = lambda w: re.sub(r'(?:ically|ally|ations?|ness|ing|ed|al|es|s)$', '', w) if len(w) > 4 else w
    cw = {stem(w) for w in ao.words(title)} - {''}
    aw = {stem(w) for w in ao.words(arxiv_title)} - {''}
    # a third sample (30) still had catalog titles with words of their own: 'Two More Attacks' vs 'Two Attacks', a
    # 'Replication of', an 'O28:' abstract, 'Deep compression and EIE' (a talk) vs 'EIE', 'Semi-Supervised' added: the
    # catalog title's significant words must all be in the arXiv title (the arXiv title may add a name or a qualifier)
    return not (cw - aw)
_IDX = {}


def _fam(name):
    name = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    if ',' in name:
        name = name.split(',', 1)[0]
    else:
        toks = [t for t in re.sub(r'[^a-z \-]', ' ', name).split() if t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
        name = toks[-1] if toks else ''
    return re.sub(r'[^a-z]', '', name)


def _nt(t):
    import arxiv_oai as ao
    return ao.nt(t)


def index():
    if 'recs' not in _IDX:
        import arxiv_oai as ao
        recs, post = [], defaultdict(list)
        for f in sorted(ao.RAW.glob('*.jsonl.gz')):
            for line in gzip.decompress(f.read_bytes()).decode().splitlines():
                if not line:
                    continue
                r = json.loads(line)
                ws = set(ao.words(r['title']))
                if len(ws) < 3:
                    continue
                i = len(recs)
                recs.append((r['id'], r['title'], tuple(ao.fam(x) for x in r['families']), int((r['created'] or '0')[:4] or 0), frozenset(ws)))
                for w in ws:
                    post[w].append(i)
        _IDX.update(recs=recs, post=post, ao=ao)
    return _IDX


def APPLIES(school, paper):
    import lab_channels as L
    return len(_nt(paper.r.get('title'))) >= 20 and not L.has_arxiv(paper.known)


def same_authors(byline, pis, fams):
    fams = set(fams) - {''}
    by = [_fam(x) for x in byline if _fam(x)]
    if not by:
        return False
    first8 = by[:8]
    if len(by) <= 2:
        return all(f in fams for f in by)
    if len(by) <= 8:
        return all(f in fams for f in first8)
    return sum(f in fams for f in first8) >= 6 and all(_fam(p) in fams for p in pis if _fam(p))


def match(r):
    """-> (best, detail): best = (arXiv id, title, similarity) of the one record that passes, else None."""
    ix = index()
    ao = ix['ao']
    ws = set(ao.words(r.get('title')))
    rare = sorted((w for w in ws if ix['post'].get(w)), key=lambda w: len(ix['post'][w]))[:3]
    cand = Counter()
    for w in rare:
        if len(ix['post'][w]) <= MAX_POSTING:
            for i in ix['post'][w]:
                cand[i] += 1
    a = _nt(r.get('title'))
    y0 = r.get('year')
    passed, best_seen = [], (None, 0.0)
    for i, _ in cand.most_common(200):
        aid, title, fams, y, rws = ix['recs'][i]
        sim = difflib.SequenceMatcher(None, a, _nt(title)).ratio()
        if sim > best_seen[1]:
            best_seen = ((aid, title), sim)
        jac = len(ws & rws) / max(1, len(ws | rws))
        if sim < MIN_SIM or jac < MIN_JACCARD or not strict_ok(r.get('title'), title, sim, jac):
            continue
        if y0 and y and not -1 <= y0 - y <= 3:
            continue
        if not same_authors(r.get('byline') or [], r.get('pis') or [], fams):
            continue
        by = [_fam(x) for x in r.get('byline') or [] if _fam(x)]
        if len(by) <= 2 and (not fams or fams[0] != by[0]):
            continue
        passed.append((aid, title, round(sim, 3), round(jac, 3)))
    passed.sort(key=lambda x: -x[2])
    if not passed or (len(passed) > 1 and passed[1][2] >= passed[0][2] - 0.02 and passed[1][0] != passed[0][0]):
        return None, dict(best_title=best_seen[0][1] if best_seen[0] else None, best_arxiv=best_seen[0][0] if best_seen[0] else None,
                          similarity=round(best_seen[1], 3), ambiguous=len(passed) > 1)
    aid, title, sim, jac = passed[0]
    return (re.sub(r'v\d+$', '', aid), title, sim), dict(arxiv=aid, arxiv_title=title, similarity=sim, jaccard=jac)


def discover(school, papers, ctx):
    import ftp_common as F
    want, det = {}, {}
    for p in papers:
        best, d = match(p.r)
        det[p.work_id] = d
        if best:
            want[p.work_id] = best[0]
    rows, ctx.n['arxiv_loose_not_in_bulk'] = F.bulk_rows(want, 'arxiv_loose_author_set_title_similarity') if want else ([], 0)
    by_w = defaultdict(list)
    for x in rows:
        x['detail'] = json.dumps(dict(arxiv=x['detail'], **{k: v for k, v in det[x['work_id']].items() if k != 'arxiv'}))
        by_w[x['work_id']].append(x)
    ctx.n['arxiv_loose_matches'] = len(want)
    for p in papers:
        yield ctx.result(p, 'found' if by_w.get(p.work_id) else 'none', by_w.get(p.work_id, []), query=f"arXiv OAI index, loose title + author set: {p.r.get('title')}"[:300],
                         detail=det[p.work_id] if not by_w.get(p.work_id) else None)
