"""Audit exact-name VT PI person records in the local primary DBLP dump."""

import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from dblp_dump_persons import AUTH, NOTE, URL, base, records, text

import atlas_paths as P
import stage_gate


def main():
    names = {item.split(': ')[0] for item in stage_gate.evaluate('vt', '5')['items']}
    targets = collections.defaultdict(set)
    for name in names:
        targets[base(name)].add(name)
    found = collections.defaultdict(list)
    for typ, key, body in records():
        if typ != 'www' or not key.startswith('homepages/'):
            continue
        aliases = [text(a) for _, a in AUTH.findall(body)]
        hit = {name for alias in aliases for name in targets.get(base(alias), ())}
        if not hit:
            continue
        notes = NOTE.findall(body)
        entry = dict(pid='https://dblp.org/pid/' + key.split('/', 1)[1],
                     person_record_sha256=hashlib.sha256(body.encode()).hexdigest(),
                     names=aliases,
                     affiliations=[text(v) for t, v in notes if t == 'affiliation'],
                     urls=[text(v) for v in URL.findall(body)],
                     disambiguation=any(t == 'disambiguation' for t, _ in notes))
        for name in hit:
            found[name].append(entry)
    out = dict(school='vt', reviewed_at=datetime.now(timezone.utc).isoformat(),
               source='dblp-2026-09-01.xml.gz', match_rule='exact full name after DBLP homonym suffix removal',
               people={name: found[name] for name in sorted(names)})
    path = Path(P.CODE) / 'hierarchy/vt/reviewed/stage5-exact-dblp-audit.json'
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'targets': len(names), 'matched': sum(bool(x) for x in found.values()),
                      'unique': sum(len(x) == 1 for x in found.values()), 'path': str(path)}))


if __name__ == '__main__':
    main()
