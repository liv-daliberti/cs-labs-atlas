"""All Princeton DataSpace thesis records 2016-2025 (senior, master's, PhD) from hierarchy/princeton/thesis-captures.sqlite
as adviser rows and author rows, each with its quote (exact substring of the capture's collapsed text).
-> <out>/princeton-thesis-index.json {advisers: [...], authors: [...]}
usage: princeton_thesis_index.py <out_dir>
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/thesis-tools'))
import records  # noqa: E402

adv, au = [], []
for r in records.load('princeton'):
    base = dict(student=r['student'], author_raw=r['author_raw'], year=r['year'], role=r['role'], dept=r['dept'], title=r['title'][:150],
                url=r['url'], sha256=r['sha256'], id=r['id'])
    q0 = None
    for a in r['advisers']:
        try:
            q = r['q'](a)
        except ValueError:
            q = None
        q0 = q0 or q
        adv.append(dict(base, adviser=a, quote=q))
    au.append(dict(base, advisers=r['advisers'], quote=q0))
json.dump(dict(advisers=adv, authors=au), open(Path(sys.argv[1]) / 'princeton-thesis-index.json', 'w'), ensure_ascii=False)
print(len(adv), len(au))
