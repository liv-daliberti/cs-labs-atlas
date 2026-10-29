"""Candidate theses from the Codex DSpace snapshot (read-only): items whose dc.contributor.advisor matches REGEX.
usage: scan_repo.py LABEL=REGEX [...]"""
import gzip, json, re, sys
items = json.loads(gzip.decompress(open('/n/fs/resemble/maxent-grpo/.research-sweeps/mit-cs-deep-20261019/repository/repository-items.json.gz', 'rb').read()))
for arg in sys.argv[1:]:
    lab, rx = arg.split('=', 1); rx = re.compile(rx, re.I)
    hits = []
    for it in items:
        md = it.get('metadata') or {}
        adv = [v['value'] for v in md.get('dc.contributor.advisor') or []]
        if any(rx.search(a) for a in adv):
            hits.append((str((md.get('dc.date.issued') or [{}])[0].get('value')), [v['value'] for v in md.get('dc.contributor.author') or []][:2], adv, it['handle'], it['uuid'], ((md.get('dc.description') or [{}])[0].get('value') or '')[:60]))
    print('=====', lab, len(hits))
    for h in sorted(hits):
        print('  ', h)
