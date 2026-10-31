"""Princeton PhD (and master's) advising 2016-2025 from the DataSpace OAI dissertation records already harvested into
hierarchy/princeton/thesis-captures.sqlite (hierarchy/thesis-tools/records.py), every department: one row per
(adviser as written, thesis) with the quote that names the student and the adviser (exact substring of the capture's
collapsed text). -> <out>/princeton-phd-advising.json
usage: princeton_phd_advisers.py <out_dir>
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/thesis-tools'))
import records  # noqa: E402

out = []
for r in records.load('princeton'):
    if r['role'] not in ('phd', 'masters'):
        continue
    for a in r['advisers']:
        try:
            q = r['q'](a)
        except ValueError:
            q = None
        out.append(dict(adviser=a, student=r['student'], year=r['year'], role=r['role'], dept=r['dept'], title=r['title'],
                        url=r['url'], sha256=r['sha256'], id=r['id'], handle=r.get('handle'), quote=q))
json.dump(out, open(Path(sys.argv[1]) / 'princeton-phd-advising.json', 'w'), ensure_ascii=False, indent=0)
print(len(out), len({x['adviser'] for x in out}))
