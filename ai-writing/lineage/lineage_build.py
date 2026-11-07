"""Step 1: link tables of the lineage study from a hierarchy snapshot -> RUN/{student_papers,pi_papers,students}.parquet, coverage.csv, build.json.

usage: lineage_build.py            (paths by environment, see lineage_common.py)
"""
import json
import time

import lineage_common as L


def main():
    sp, pp, stu = L.build_links()
    L.RUN.mkdir(parents=True, exist_ok=True)
    sp.to_parquet(L.RUN / 'student_papers.parquet')
    pp.to_parquet(L.RUN / 'pi_papers.parquet')
    stu.to_parquet(L.RUN / 'students.parquet')
    rows = []
    for st in ('verified', 'candidate', 'all'):
        d = sp if st == 'all' else sp[sp['status'] == st]
        d = d[d['year'].between(2017, 2025)]
        for s, g in list(d.groupby('school')) + [('ALL', d)]:
            rows.append(dict(status=st, school=s, pairs=g[['lab', 'student']].drop_duplicates().shape[0], students=g['student'].nunique(),
                             labs=g['lab'].nunique(), papers=g['paper_id'].nunique(), links=len(g),
                             phd_students=g[g['student'].isin(set(stu[stu['role'] == 'phd']['student']))]['student'].nunique()))
    import pandas as pd
    pd.DataFrame(rows).to_csv(L.RUN / 'coverage.csv', index=False)
    snap = (L.HIER / 'SNAPSHOT_TIME')
    json.dump(dict(built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), hier=str(L.HIER),
                   snapshot_time=snap.read_text().strip() if snap.exists() else 'live (no SNAPSHOT_TIME)',
                   student_paper_links=len(sp), pi_papers=len(pp), students=len(stu)), open(L.RUN / 'build.json', 'w'), indent=1)
    L.log(done='build', links=len(sp), pi_papers=len(pp), students=len(stu))


if __name__ == '__main__':
    main()
