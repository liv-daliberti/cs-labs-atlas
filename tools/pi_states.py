"""Per-PI admission state (process v4, owner decision 1, 2026-11-17): stages 3-7 are judged per PI, not per school.

A PI's state at the census and at stages 3 (basis, home, website), 4 (window), 5 (identity, papers), 6 (students, links) and 7 (papers/links audit) is
  done                  every bar of the stage is met for this PI
  excluded_with_reason  a recorded, reviewed reason replaces the evidence (a reviewed no_identity / no_papers / researched student reason, a gate
                        exception that names the item, or the build excluded the PI by review)
  open                  a bar fails: `reasons` says which. Fail closed: an open PI's papers stay out of the catalogue, and nothing else waits for it.
The evidence bar per PI is the existing gate logic (stage_gate.GATES, pi_coverage's per-PI ledger, chain_audit's per-PI items): this module only
ATTRIBUTES each finding to the person it names. A finding that names no person (a lab-page acceptance, a sample statistic such as recall R1/U/R2,
a register mismatch) is a SCHOOL item: it never holds a PI, it is reported, and it stays a condition of the school-level release.
A share bar (pi_coverage ratchet, recall Z) is a `ratchet` school item; its per-PI gaps are open with `ratchet` set: the owner's ratchet tolerates
them for release (the bar is unchanged) but they are listed per person and never hold anyone's downloads.

  downloadable PI = census clean (no gate-2 finding names the person) + window settled (stage_gate.period_basis) + identity anchor (identity_basis)
                    and not excluded from the build. tools/downloads_ready.py reads this.
  release_ready   = no open PI (ratchet gaps excepted) and no open school item of stages 2-7 (kept school-wide; stage_gate.g10 reads release_findings).

usage: pi_states.py <school> [--write] [--json]     (--write: hierarchy/<school>/reports/pi-states.json)
"""
import collections
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import atlas_paths as P  # noqa: E402
import stage_gate as SG  # noqa: E402

STAGES = ('3', '4', '5', '6', '7')
ALL = ('census',) + STAGES
CHAIN_STAGE = {'students': '6', 'one_person': '6', 'papers': '7', 'links': '7'}
CHAIN_SUMMARY = re.compile(r'^(students|one_person|papers|links): \d+ unexplained of \d+$')
RATCHET_ITEM = re.compile(r'^(PI coverage |recall Z:)')
RATCHET_REASON = 'PI coverage'


def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Names:
    """Census name and alias -> the canonical PI name; `of(item)` is the PI an item 'Name: ...' names (longest name first)."""
    def __init__(self, key):
        import chain_audit
        self._norm = chain_audit.norm
        self.pis = SG.pis_of(key)
        self.canon = {}
        for x in self.pis:
            for n in [x['name']] + list(x.get('aliases') or []):
                self.canon.setdefault(n, x['name'])
        self.sorted = sorted(self.canon, key=len, reverse=True)
        self.by_norm = {self._norm(n): c for n, c in self.canon.items()}

    def of(self, item):
        for n in self.sorted:
            if item.startswith(n + ': '):
                return self.canon[n]
        return None

    def of_norm(self, name):
        return self.by_norm.get(self._norm(name or ''))


def _build_excluded(key):
    rep = SG.read(P.data('report.json', key), {})
    return {e.get('pi'): (e.get('reason') or e.get('why') or 'no reason recorded')
            for e in (rep.get('excluded') if isinstance(rep, dict) else None) or [] if isinstance(e, dict) and e.get('pi')}


def _ledger(key):
    import pi_coverage as PC
    try:
        return {r['pi']: r for r in PC.ledger(key)}
    except (OSError, ValueError, KeyError):
        return {}


def _ratchet_only(rec, s):
    return rec[s]['state'] == 'open' and rec[s]['reasons'] and all(r.startswith(RATCHET_REASON) for r in rec[s]['reasons'])


def _hard_open(rec):
    return any(rec[s]['state'] == 'open' and not _ratchet_only(rec, s) for s in ALL)


def compute(key):
    names = Names(key)
    pis = {x['name']: {s: dict(state='done', reasons=[]) for s in ALL} for x in names.pis}
    school_items = {s: [] for s in ('2',) + STAGES}
    waived_school = {}
    waived_chain, waived_cov = set(), set()   # (check) / (stage, dim): a gate exception that waives the school-level summary waives the per-PI items it summarises

    def put(pi, stage, state, why):
        rec = pis[pi]['census' if stage == '2' else stage]
        if state == 'open':
            rec['state'] = 'open'
        elif rec['state'] == 'done':
            rec['state'] = 'excluded_with_reason'
        if why not in rec['reasons']:
            rec['reasons'].append(why)

    for st in ('2',) + STAGES:
        try:
            ev = SG.evaluate(key, st)
        except Exception as exc:   # a gate that cannot run is a school item, never a silent pass
            school_items[st].append(f'gate {st} could not be evaluated: {type(exc).__name__}: {exc}')
            continue
        waived = set(ev.get('waived_items') or [])
        for item in ev['items']:
            if st in STAGES and CHAIN_SUMMARY.match(item):
                if item in waived:
                    waived_chain.add(item.split(':')[0])
                continue    # replaced below by the per-PI chain-audit items
            if item.startswith(RATCHET_REASON + ' ') and item in waived:
                waived_cov.add((st, item.split(':')[0].split(' ')[2]))
            who = names.of(item)
            if who and item in waived:
                put(who, st, 'excluded_with_reason', f'waived by gate exception: {item}')
            elif who:
                put(who, st, 'open', item.split(': ', 1)[1])
            elif item in waived:
                waived_school.setdefault(st, []).append(item)
            else:
                school_items[st].append(item)

    # per-PI chain-audit findings (stages 6 and 7), read in-process like stage_gate.audit_open
    try:
        import chain_audit
        res = chain_audit.audit(key)['checks']
        for check, st in CHAIN_STAGE.items():
            for r in (res.get(check) or {}).get('unexplained', []):
                who = names.of_norm(r.get('pi') or r.get('name'))
                if who:
                    detail = '; '.join(f'{k}={v}' for k, v in r.items() if k not in ('pi', 'diagnosis_works') and v not in (None, ''))
                    put(who, st, 'excluded_with_reason' if check in waived_chain else 'open',
                        ('waived by gate exception: ' if check in waived_chain else '') + f'chain audit {check}: {detail[:200]}')
                else:
                    school_items[st].append(f'chain audit {check}: {str(r.get("key") or r)[:160]}')
    except Exception as exc:
        for st in ('6', '7'):
            school_items[st].append(f'chain audit could not be read: {type(exc).__name__}: {exc}')

    # per-PI coverage ledger: a gap is open at the ratchet; a recorded reason is an exclusion with that reason
    for pi, r in _ledger(key).items():
        pi = names.canon.get(pi, pi)
        if pi not in pis:
            continue
        for dim, st in (('lab', '5'), ('students', '6'), ('links', '6')):
            state = r.get(dim + '_state')
            if state == 'gap' and (st, dim) in waived_cov:
                put(pi, st, 'excluded_with_reason', f'waived by gate exception: {RATCHET_REASON} {dim} gap ({r.get(dim + "_cause")})')
            elif state == 'gap':
                put(pi, st, 'open', f"{RATCHET_REASON} {dim}: neither evidence nor a researched reason ({r.get(dim + '_cause')})")
            elif state == 'reason':
                put(pi, st, 'excluded_with_reason', f"{dim}: recorded reason ({str(r.get(dim + '_reason') or '')[:120]})")

    ov = SG.CO.section(key)
    for pi in pis:
        o = ov.get(pi) or {}
        if o.get('no_identity') and o.get('why_no_identity'):
            put(pi, '5', 'excluded_with_reason', 'reviewed no_identity: ' + str(o['why_no_identity'])[:160])
        elif o.get('no_papers') and o.get('why_no_papers'):
            put(pi, '5', 'excluded_with_reason', 'reviewed no_papers: ' + str(o['why_no_papers'])[:160])
    excluded = _build_excluded(key)
    for pi, why in excluded.items():
        if pi in pis:
            pis[pi] = {s: dict(state='excluded_with_reason', reasons=[f'excluded from the build by review: {why}']) for s in ALL}

    import downloads_ready as DR
    settled = DR.pi_status(key)
    for pi, rec in pis.items():
        s = settled.get(pi)
        rec['window'] = s['period'] if s else None
        rec['identity'] = s['identity'] if s else None
        rec['downloadable'] = bool(s) and not s['reasons'] and pi not in excluded and rec['census']['state'] != 'open'
        rec['state'] = ('open' if any(rec[x]['state'] == 'open' for x in ALL) else
                        'excluded_with_reason' if all(rec[x]['state'] == 'excluded_with_reason' for x in ALL) else 'done')

    ratchet_items = {st: [i for i in v if RATCHET_ITEM.match(i)] for st, v in school_items.items()}
    hard_school = {st: [i for i in v if not RATCHET_ITEM.match(i)] for st, v in school_items.items()}
    counts = {}
    for st in ALL:
        c = collections.Counter(rec[st]['state'] for rec in pis.values())
        counts[st] = {s: c.get(s, 0) for s in ('done', 'excluded_with_reason', 'open')}
        counts[st]['open_ratchet_only'] = sum(1 for rec in pis.values() if _ratchet_only(rec, st))
    hard_open = sorted(pi for pi, rec in pis.items() if _hard_open(rec))
    return dict(school=key, at=_now(), pis_total=len(pis), downloadable=sum(1 for r in pis.values() if r['downloadable']), counts=counts,
                open_pis=hard_open, school_items=hard_school, ratchet_items=ratchet_items, waived_school_items=waived_school,
                release_ready=not hard_open and not any(hard_school.values()) and not any(ratchet_items.values()), pis=pis)


def release_findings(key, res=None):
    """Gate-10 findings: every open PI (ratchet gaps excepted) and every open school item of stages 2-7 (the release stays school-wide)."""
    res = res or compute(key)
    bad = [f'PI {pi} is open: ' + '; '.join(f"stage {s} {res['pis'][pi][s]['reasons'][0][:100]}" for s in ALL if res['pis'][pi][s]['state'] == 'open')
           for pi in res['open_pis']]
    for st, items in {**{k: v for k, v in res['school_items'].items()}}.items():
        bad += [f'stage {st} school item: {i[:160]}' for i in items]
    for st, items in res['ratchet_items'].items():
        bad += [f'stage {st} ratchet bar: {i[:160]}' for i in items]
    return bad


def path(key):
    return Path(P.HIERARCHY) / key / 'reports' / 'pi-states.json'


def write(key, res):
    p = path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')
    return p


def recorded(key):
    return SG.read(path(key))


def summary_line(res):
    c = res['counts']
    return (f"{res['school']}: {res['pis_total']} PIs, {res['downloadable']} downloadable, {len(res['open_pis'])} open"
            + ''.join(f" | {s} {c[s]['done']}/{c[s]['excluded_with_reason']}/{c[s]['open']}" for s in ALL)
            + f" | school items {sum(len(v) for v in res['school_items'].values())}, release_ready {res['release_ready']}")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    res = compute(a.key)
    if a.write:
        write(a.key, res)
    if a.json:
        print(json.dumps({k: v for k, v in res.items() if k != 'pis'}, ensure_ascii=False))
    else:
        print(summary_line(res))
        for pi in res['open_pis'][:12]:
            rec = res['pis'][pi]
            print('  open', pi, '|', '; '.join(f"{s}: {rec[s]['reasons'][0][:80]}" for s in ALL if rec[s]['state'] == 'open')[:240])
    return 0


if __name__ == '__main__':
    sys.exit(main())
