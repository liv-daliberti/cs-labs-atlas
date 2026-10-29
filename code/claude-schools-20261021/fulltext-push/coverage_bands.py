"""Local-copy share of a school's lab papers by year band, with the coverage counter's rule (ftp_common.is_local: the
paper's own catalog work, or any catalog work with the same DOI or normalized title, is downloaded / fulltext_xml), and
the report_remaining.py states of the papers without a copy. Read-only, rowid-chunked.
usage: coverage_bands.py <school> ...   -> one JSON line per school (also appended to logs/coverage-bands.jsonl)"""
import json, sqlite3, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

BANDS = (('2016-2022', 2016, 2022), ('2023-2026', 2023, 2026))


def band(y):
    for name, lo, hi in BANDS:
        if y and lo <= int(y) <= hi:
            return name
    return 'other'


def main():
    for school in sys.argv[1:]:
        papers = F.lab_papers(school)
        cs = F.catalog_state(school, with_urls=False)
        db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
        cands, atts = defaultdict(set), defaultdict(set)
        for w, u in F.chunks(db, 'candidates', 'work_id, url', n=20000):
            cands[w].add(u)
        for w, u in F.chunks(db, 'attempts', 'work_id, url', n=20000):
            atts[w].add(u)
        db.close()
        tot, loc, state = Counter(), Counter(), defaultdict(Counter)
        for r in papers.values():
            b = band(r.get('year'))
            tot[b] += 1; tot['all'] += 1
            if F.is_local(school, r, cs):
                loc[b] += 1; loc['all'] += 1; continue
            w = F.match_work(school, r, cs)
            s = ('not_in_catalog' if not w else 'untried_candidates_left' if cands[w] - atts[w] else 'all_links_failed' if cands[w]
                 else 'no_open_link_found')
            state[b][s] += 1; state['all'][s] += 1
        out = dict(at=F.now(), school=school, bands={b: dict(lab_papers=tot[b], local=loc[b], share=round(loc[b] / tot[b], 3) if tot[b] else None,
                                                             missing=dict(state[b])) for b in [x[0] for x in BANDS] + ['all'] if tot[b]})
        with open(F.HERE / 'logs' / 'coverage-bands.jsonl', 'a') as f:
            f.write(json.dumps(out) + '\n')
        print(json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
