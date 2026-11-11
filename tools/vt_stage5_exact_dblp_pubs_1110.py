"""Collect sample publication titles for unique exact VT PI DBLP person leads."""

import collections
import json
from datetime import datetime, timezone
from pathlib import Path

from dblp_dump_persons import AUTH, TITLE, YEAR, records, text

import atlas_paths as P


def main():
    audit = json.loads((Path(P.CODE) / 'hierarchy/vt/reviewed/stage5-exact-dblp-audit.json').read_text())
    unique = {name: rows[0] for name, rows in audit['people'].items()
              if len(rows) == 1 and not rows[0]['disambiguation']}
    by_alias = collections.defaultdict(set)
    for name, person in unique.items():
        for alias in person['names']:
            by_alias[alias].add(name)
    works = collections.defaultdict(list)
    for typ, key, body in records():
        if typ in ('www', 'data'):
            continue
        year = YEAR.search(body)
        if not year or not 2016 <= int(year.group(1)) <= 2026:
            continue
        hit = {name for _, raw in AUTH.findall(body) for name in by_alias.get(text(raw), ())}
        if not hit:
            continue
        title = TITLE.search(body)
        rec = dict(title=text(title.group(1)) if title else '', year=int(year.group(1)),
                   key=key, type=typ)
        for name in hit:
            works[name].append(rec)
    out = dict(school='vt', reviewed_at=datetime.now(timezone.utc).isoformat(),
               source='dblp-2026-09-01.xml.gz', rule='exact unique person-name string in local DBLP publication record; identity review still required',
               people={name: dict(pid=person['pid'], count=len(works[name]),
                                  titles=sorted(works[name], key=lambda x: (-x['year'], x['title'])))
                       for name, person in sorted(unique.items())})
    path = Path(P.CODE) / 'hierarchy/vt/reviewed/stage5-exact-dblp-pubs.json'
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'people': len(unique), 'with_works': sum(bool(v) for v in works.values()),
                      'works': sum(map(len, works.values())), 'path': str(path)}))


if __name__ == '__main__':
    main()
