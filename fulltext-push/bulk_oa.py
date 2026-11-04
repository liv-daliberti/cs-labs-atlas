"""Shared helpers of the bulk open-access channels (2026-11-04, owner): the targets table the bulk-source jobs match against, and the
local matching rule (DOI first, then arXiv id, then normalized title plus first author).

targets    FT_RAW/bulk-oa/targets.jsonl.gz: one row per missing lab paper of every school (the runner's own plan,
           lab_channels.plan_for): school, key, work_id, doi, arxiv (from the DOI), nt (normalized title), fam (family names of the first
           8 byline authors, first author first), year. Built by `bulk_oa.py targets <school> ...` (a Slurm job; catalogs read-only).
match_key  the title key: normalized title of >= 20 characters + the first author's family name.
usage: bulk_oa.py targets <school> [<school> ...]      write/refresh the targets rows of these schools (other schools' rows are kept)
       bulk_oa.py survey                               print the per-school counts of the table
"""
import gzip
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402

DIR = F.P.FT_RAW / 'bulk-oa'
TARGETS = DIR / 'targets.jsonl.gz'


def fam(name):
    name = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    if ',' in name:
        name = name.split(',', 1)[0]
    else:
        toks = [t for t in re.sub(r'[^a-z \-]', ' ', name).split() if t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
        name = toks[-1] if toks else ''
    return re.sub(r'[^a-z]', '', name)


def match_key(title, first_family):
    t = F.nt(title)
    return f'{t}|{first_family}' if len(t) >= 20 and first_family else None


def target_row(school, r, work_id):
    d = F.ndoi(r.get('doi'))
    fams = [x for x in (fam(b) for b in (r.get('byline') or [])[:8]) if x]
    return dict(school=school, key=r['work'] or r['oa'], work_id=work_id, doi=d or None, arxiv=F.arxiv_of(r, None), nt=F.nt(r.get('title')),
                fam=fams, year=r.get('year'))


def read_targets(schools=None):
    rows = []
    if TARGETS.exists():
        with gzip.open(TARGETS, 'rt') as f:
            for line in f:
                r = json.loads(line)
                if not schools or r['school'] in schools:
                    rows.append(r)
    return rows


def build(schools):
    import lab_channels as L
    keep = [r for r in read_targets() if r['school'] not in schools]
    new = []
    for s in schools:
        miss, _known, _n = L.plan_for(s)
        new += [target_row(s, r, w) for r, w in miss]
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = TARGETS.with_suffix('.tmp')
    with gzip.open(tmp, 'wt') as f:
        for r in keep + new:
            f.write(json.dumps(r) + '\n')
    tmp.replace(TARGETS)
    return Counter(r['school'] for r in keep + new)


def index(rows):
    """-> (by_doi, by_arxiv, by_title): {key: [target rows]} for the matching order DOI, arXiv id, title + first author."""
    by_doi, by_ax, by_t = {}, {}, {}
    for r in rows:
        if r.get('doi'):
            by_doi.setdefault(r['doi'], []).append(r)
        if r.get('arxiv'):
            by_ax.setdefault(r['arxiv'], []).append(r)
        k = match_key_of(r)
        if k:
            by_t.setdefault(k, []).append(r)
    return by_doi, by_ax, by_t


def match_key_of(r):
    return match_key(r.get('nt') and r['nt'], (r.get('fam') or [''])[0]) if len(r.get('nt') or '') >= 20 else None


def match_record(ix, doi=None, arxiv=None, title=None, first_family=None, year=None):
    """-> (how, [target rows]) of the first rule that hits: 'doi', 'arxiv', 'title_author' (same normalized title and first author's
    family name, year within 2 when both are known), else (None, [])."""
    by_doi, by_ax, by_t = ix
    d = F.ndoi(doi)
    if d and d in by_doi:
        return 'doi', by_doi[d]
    if arxiv and re.sub(r'v\d+$', '', arxiv) in by_ax:
        return 'arxiv', by_ax[re.sub(r'v\d+$', '', arxiv)]
    t = F.nt(title)
    k = match_key(title, first_family) if len(t) >= 20 else None
    if k and k in by_t:
        hit = [r for r in by_t[k] if not (year and r.get('year') and abs(int(year) - int(r['year'])) > 2)]
        if hit:
            return 'title_author', hit
    return None, []


if __name__ == '__main__':
    if sys.argv[1] == 'targets':
        print(json.dumps(build(sys.argv[2:])))
    elif sys.argv[1] == 'survey':
        print(json.dumps(Counter(r['school'] for r in read_targets())))
