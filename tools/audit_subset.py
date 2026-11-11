"""Lab-page audit records for a subset of a school's PIs, merged into the school's labpage-audit.jsonl.gz (stage 3, legacy released schools).

The full `labpage_audit.py audit <key>` is single-thread CPU-bound (CMU: more than 60 minutes for 467 PIs). The register only needs each PI's `lab_page` record, so this
assembles records for the named PIs alone (same assemble() call, ctx['pis'] filtered), replaces or appends those PIs' lines in the existing jsonl.gz and writes
nothing else (not labpage-additions.json, not the summary).
usage: audit_subset.py <key> <name> [<name> ...]     (run in the private overlay: CS_ATLAS_CODE=<overlay>)
"""
import gzip
import json
import os
import sys

import atlas_paths as P  # noqa: E402
import labpage_audit as L  # noqa: E402


def main(key, names):
    kit = L.Kit(key)
    ctx = L.load_ctx(key, kit)
    want = set(names)
    ctx['pis'] = [p for p in ctx['pis'] if p['pi'] in want]
    missing = want - {p['pi'] for p in ctx['pis']}
    if missing:
        print('not in pis.json:', sorted(missing))
    disc = L.read_discovery(key)
    recs, _stu, _pap, _ = L.assemble(kit, ctx, disc, L.recover_verdicts(key))
    new = {r['pi']: r for r in recs}
    out = P.data('labpage-audit.jsonl.gz', key)
    keep = []
    if out.exists():
        with gzip.open(out, 'rt', encoding='utf-8') as f:
            keep = [json.loads(line) for line in f]
    merged = [r for r in keep if r['pi'] not in new] + list(new.values())
    tmp = str(out) + '.tmp'
    with gzip.open(tmp, 'wt', encoding='utf-8') as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(tmp, out)
    print(json.dumps(dict(school=key, replaced_or_added=len(new), total=len(merged))))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
