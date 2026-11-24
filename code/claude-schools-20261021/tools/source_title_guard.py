#!/usr/bin/env python3
"""R-PAP-41 source-title guard (2026-11-09, Claude on the owner's delegation).

A record's title must match the title the source gives for its DOI (arXiv or Crossref). A record whose title is another work's
(Roberts' 'HumBugDB' under arXiv 1705.05180, Gal's 'ME-JEPA' under 2305.17493) is HELD, not dropped: the verdict is `hold`
and a person reads the pair. The comparison is normalised and tolerant: case, punctuation, HTML entities and markup, accents,
'&' versus 'and', a subtitle (one title is the other's prefix up to a colon or dash), and a small wording change
('Iterate' / 'Iterative') all match. A genuine retitling between arXiv versions is held too; that is the cost of the guard,
and the reviewer clears it.

  source_title_guard.py PAPERS.jsonl[.gz] SOURCES.json [--out holds.json]
      PAPERS: lab-paper rows (pi, doi, title, ...); SOURCES: {doi-or-arxiv-id: {"title": ...} | [titles]} (the scratch
      bulk_arxiv.json / bulk_crossref.json shape). Prints the held rows; a DOI with no source title is not judged.
"""
import difflib
import gzip
import html
import json
import re
import sys
import unicodedata

ARXIV_DOI = re.compile(r'(?i)^10\.48550/arxiv\.(.+)$')
MIN_PREFIX_WORDS = 2
RATIO = 0.78
JACCARD = 0.6


def norm(t):
    """Normalised title: no markup or entities, accents, case or punctuation; '&' is 'and'."""
    t = html.unescape(re.sub(r'<[^>]+>', '', str(t or '')))
    t = unicodedata.normalize('NFKD', t).replace('&', ' and ')
    t = ''.join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


def stem(w):
    return re.sub(r'(?:ing|ive|ion|ed|es|s|e)$', '', w) if len(w) > 4 else w


def titles_match(a, b):
    """True when two titles are the same work's, tolerant to case, punctuation, markup, subtitle and small wording changes."""
    x, y = norm(a), norm(b)
    if not x or not y:
        return False
    if x == y:
        return True
    short, long_ = sorted((x, y), key=len)
    if len(short.split()) >= MIN_PREFIX_WORDS and long_.startswith(short + ' '):
        return True                       # the other carries a subtitle
    if difflib.SequenceMatcher(None, x, y).ratio() >= RATIO:
        return True
    sx, sy = {stem(w) for w in x.split()}, {stem(w) for w in y.split()}
    return len(sx & sy) / len(sx | sy) >= JACCARD


def source_titles(doi, sources):
    """Titles the sources hold for a DOI (arXiv id for 10.48550/arxiv.*), as a list."""
    d = str(doi or '').lower()
    m = ARXIV_DOI.match(d)
    for k in ([m.group(1), re.sub(r'v\d+$', '', m.group(1)), d] if m else [d]):
        v = sources.get(k)
        if v:
            return [t for t in ([v.get('title')] if isinstance(v, dict) else v) if t]
    return []


def title_conflict(r, sources):
    """None, or the source titles that disagree: the record's title matches none of them. A DOI with no source title is not judged."""
    ts = source_titles(r.get('doi'), sources)
    if not ts or any(titles_match(r.get('title'), t) for t in ts):
        return None
    return ts


def held_rows(rows, sources):
    out = []
    for r in rows:
        ts = title_conflict(r, sources)
        if ts:
            out.append(dict(pi=r.get('pi'), doi=r.get('doi'), year=r.get('year'), title=r.get('title'), source_titles=ts, verdict='hold'))
    return out


def _read(p):
    with (gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p)) as f:
        return [json.loads(x) for x in f] if str(p).split('.gz')[0].endswith('.jsonl') else json.load(f)


def main(argv):
    out = argv[argv.index('--out') + 1] if '--out' in argv else None
    args = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or argv[i - 1] != '--out')]
    sources = {}
    for p in args[1:]:
        sources.update({k.lower(): v for k, v in _read(p).items()})
    held = held_rows(_read(args[0]), sources)
    if out:
        with open(out, 'w') as f:
            json.dump(held, f, ensure_ascii=False, indent=1)
    for h in held:
        print(h['pi'], h['doi'], '|', h['title'][:60], '|', h['source_titles'][0][:60])
    print(f'{len(held)} held', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
