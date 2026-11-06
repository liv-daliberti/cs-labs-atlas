"""Papers with a stored full-text copy that sections.sqlite lacks (Georgia Tech, newer UChicago copies, ...).

Matches copies exactly as embeddings/texts.py does (match_copies: catalog work id, <school>_oa_<W>, DOI, title; home school first),
then lists those paper_ids that are not in data/sections/sections.sqlite -> data/missing_copies.jsonl.gz {paper_id, school, path, kind, title}.
usage: missing3.py
"""
import gzip, json, sqlite3, sys
from collections import Counter
import v3common as C

EMB = C.AIW / 'embeddings'
sys.path.insert(0, str(EMB))
sys.path.insert(0, str(C.V.P.vendor('homogenization_tools')))
import texts as T  # noqa: E402  (embeddings/texts.py)
import ecommon as EC  # noqa: E402


def main():
    want = T.match_copies(EC.SCHOOLS)
    db = sqlite3.connect(f'file:{C.AIW}/data/sections/sections.sqlite?mode=ro', uri=True)
    have = {r[0] for r in db.execute('select paper_id from sections')}
    miss = {p: v for p, v in want.items() if p not in have}
    C.DATA.mkdir(parents=True, exist_ok=True)
    with gzip.open(C.DATA / 'missing_copies.jsonl.gz', 'wt') as f:
        for p, (s, path, kind, title) in sorted(miss.items()):
            f.write(json.dumps(dict(paper_id=p, school=s, path=str(path), kind=kind, title=title)) + '\n')
    print(json.dumps(dict(matched=len(want), in_sections=len(have), missing=len(miss), by_school=Counter(v[0] for v in miss.values()),
                          matched_by_school=Counter(v[0] for v in want.values()))))


if __name__ == '__main__':
    main()
