"""Downloads-ready: a school's download catalogue and loop may start before the stage 3-8 gates pass (R3c, owner 2026-11-17).

What the catalogue and the loop actually read (from the code, not the docs):
  fulltext-push/add_works.py      hierarchy/<school>/lab_papers.jsonl.gz (rows written by tools/pihier/build.py from the PIs of pis.json), the OpenAlex
                                  records (snapshot, pi-works.sqlite or the API), the school's stores/<school>/catalog.sqlite (must exist: atlas new-school)
  fulltext-push/lab_first_loop.py the same lab_papers file and the catalog; the work ids are the catalog's, so only papers already added are fetched
  fulltext-push/loop_starter.py   stores/<school>/.copy-quality-warm.json, the disk-guard marker, no live loop job, a free .loop.lock
  pi_hierarchy build              census (PIs, DBLP/ORCID/OpenAlex anchors), faculty-periods / census-overrides periods / listings (the appointment
                                  window), the sweep, collection, DBLP dumps. Each lab_papers row records its identity proof and its appointment
                                  (a reviewed periodId, or a captured same-year listing that names the PI: that calendar year only)
None of it reads the lab-page audit, the website register, the lab-page students or papers acceptance, the student recall, the chain audit or the
copies/ledger (stages 3's website part, 6, 7 and 8's outputs). The catalogue is the INPUT of stage 8, so stage 8 can not be its precondition.

The rule (school level, then per PI; `stage_gate.py <key> catalogue`). Process v4 (owner decision 1, 2026-11-17): the census is per person too, so gates 1 and 2
no longer hold the school; a PI is held when a gate-2 finding names them (tools/pi_states.py attributes it):
  school  gate 0 (charter, hosts, snapshot) passes (or is waived) and the bulk-pull sanity check (stage_gate.sweep_gate) passes; pis.json and lab_papers.jsonl.gz exist and are NOT older than the inputs the build reads for
          identity, appointment windows and papers (SETTLE_INPUTS). The stage-3 website/lab-page audit files and every student file are not in it.
  per PI  a settled appointment window (stage_gate.period_basis: a reviewed period, a contiguous run of listing years, or a reviewed unproven gap) AND
          an identity anchor (stage_gate.identity_basis: DBLP id, ORCID, reviewed OpenAlex id, credited source-owned publication evidence, or a reviewed no_identity). A PI without both is HELD:
          its papers are not added yet (fail closed per PI). A row without an appointment record is held with it (never a paper outside the window).
Later stages settle more PIs: rebuild, then re-run add_works --early; works already in the catalogue are skipped, so it only adds.
The decision is recorded in hierarchy/<key>/reports/downloads-ready.json (held PIs with reasons, row counts).

usage: downloads_ready.py <school> [--json] [--record]
"""
import collections
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import atlas_paths as P  # noqa: E402
import stage_gate as SG  # noqa: E402

GATES = ('0',)   # gates 1 and 2 are per person since process v4 (census findings that name a PI hold that PI only)
# Data names the build reads for identity, appointment windows and papers. Deliberately absent: lab-websites.json, person-websites.json, labpage-*
# (the stage-3 audit), students.json, student-*.json, labpage-acceptance.json, labpage-handcheck.json and the other stage 6-8 files.
SETTLE_INPUTS = ('census-faculty.json', 'census-additions.json', 'cs-related-review.json', 'census-overrides-school.json', 'faculty-periods.json',
                 'deep-gap-evidence.json', 'gap-evidence.json', 'dblp-ids.json', 'openalex-identity-review.json', 'openalex-sweep.sqlite',
                 'pi-works.sqlite', 'collection.json.gz', 'listings.json', 'dblp-dump-persons-school.json.gz', 'pi-publication-lists.json')
OUTPUTS = ('pis.json', 'lab_papers.jsonl.gz')


def _mtime(p):
    try:
        return Path(p).stat().st_mtime
    except OSError:
        return None


def school_blockers(key):
    """Why the school as a whole cannot start: gate 0, the sweep check, a built package, a build newer than the identity/period/paper inputs."""
    out = []
    for g in GATES:
        r = SG.evaluate(key, g)
        if r['gate'] == 'fail':
            out.append(f"gate {g} fails ({r['open']} open): {(r['items'] or ['?'])[0][:140]}")
    out += SG.sweep_gate(key)   # the OpenAlex sweep feeds every PI's papers: one school-wide technical check
    outs = {n: _mtime(P.data(n, key)) for n in OUTPUTS}
    missing = [n for n, t in outs.items() if t is None]
    if missing:
        out.append('not built: ' + ', '.join(missing) + ' (stage 3 build step: pi_hierarchy.py)')
        return out
    built = min(outs.values())
    newer = [n for n in SETTLE_INPUTS if (_mtime(P.data(n, key)) or 0) > built + 1]
    if newer:
        out.append('build is older than ' + ', '.join(newer) + ' (rebuild: pi_hierarchy.py ' + key + ')')
    return out


def census_holds(key):
    """{census PI name: [gate-2 findings that name them]}: an unresolved decision, a display-name collision, a pending review of THIS person."""
    import pi_states as PS
    names = PS.Names(key)
    out = {}
    for item in SG.evaluate(key, '2')['unwaived_items']:
        who = names.of(item)
        if who:
            out.setdefault(who, []).append('census: ' + item.split(': ', 1)[1][:160])
    return out


def pi_status(key):
    """{census PI name or alias: dict(name, period, identity, reasons)}: the per-PI settled test. `reasons` empty = settled."""
    holds = census_holds(key)
    per, ov, have = SG.periods_have(key)
    owned_works = SG.read(P.data('pi-publication-lists.json', key), {}) or {}
    bad_iso = {n for n, _f, _v in SG.non_iso_periods(per)}
    out = {}
    for x in SG.pis_of(key):
        period = SG.period_basis(key, x, have, ov)
        ident = SG.identity_basis(x, ov.get(x['name']) or {}, owned_works.get(x['name']))
        reasons = list(holds.get(x['name'], []))
        if not period:
            reasons.append('appointment window not settled (no reviewed period, listing years not contiguous)')
        elif x['name'] in bad_iso:
            reasons.append('a reviewed period date is not ISO')
        if not ident:
            reasons.append('no identity anchor (DBLP id, ORCID, reviewed OpenAlex id, or reviewed no_identity)')
        rec = dict(name=x['name'], period=period, identity=ident, reasons=reasons)
        for n in [x['name']] + list(x.get('aliases') or []):
            out.setdefault(n, rec)
    return out


def _rows(key):
    for line in gzip.open(P.data('lab_papers.jsonl.gz', key), 'rt'):
        yield json.loads(line)


def row_hold(status, r):
    """The reason a lab_papers row is held back, or None."""
    s = status.get(r['pi'])
    if s is None:
        return 'PI is not a census PI of the school'
    if s['reasons']:
        return '; '.join(s['reasons'])
    if not r.get('appointment'):
        return 'row has no appointment record'
    return None


def readiness(key):
    """-> dict(ready, school_blockers, settled_pis, held {PI: reasons}, rows, rows_ready, rows_held). ready = no school blocker."""
    blockers = school_blockers(key)
    status = pi_status(key)
    held, rows, ok = {}, 0, 0
    if not Path(P.data('lab_papers.jsonl.gz', key)).exists():
        return dict(school=key, ready=False, school_blockers=blockers, settled_pis=0, held={}, rows=0, rows_ready=0, rows_held=0)
    for r in _rows(key):
        rows += 1
        why = row_hold(status, r)
        if why:
            held.setdefault(r['pi'], collections.Counter())[why] += 1
        else:
            ok += 1
    for name, s in status.items():
        if s['name'] == name and s['reasons']:
            held.setdefault(name, collections.Counter())[('; '.join(s['reasons']))] += 0   # a held PI with no row yet is listed too
    settled = len({s['name'] for s in status.values() if not s['reasons']})
    return dict(school=key, ready=not blockers, school_blockers=blockers, settled_pis=settled,
                held={p: sorted(c) for p, c in sorted(held.items())}, rows=rows, rows_ready=ok, rows_held=rows - ok)


def keep(key, status=None):
    """A predicate over lab_papers rows: True for a row whose PI is settled (add_works --early)."""
    status = status or pi_status(key)
    return lambda r: row_hold(status, r) is None


def record(key, res, **extra):
    d = P.school_part(key, 'reports')
    d.mkdir(parents=True, exist_ok=True)
    doc = dict(res, at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), rule='tools/downloads_ready.py docstring', **extra)
    (d / 'downloads-ready.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    return doc


def recorded(key):
    """The last record (dict) or None."""
    return SG.read(P.school_part(key, 'reports') / 'downloads-ready.json')


def start_blocker(key):
    """For loop_starter --early: why the school's loop may not start from a recorded readiness, or None. The record must say ready, be newer than
    the build, and have an add_works pass after it (catalogue_added)."""
    rec = recorded(key)
    if not rec:
        return 'no downloads-ready record'
    if not rec.get('ready'):
        return 'downloads-ready: not ready'
    if not rec.get('catalogue_added'):
        return 'downloads-ready: add_works --early has not run'
    built = min([t for t in (_mtime(P.data(n, key)) for n in OUTPUTS) if t] or [0])
    f = P.school_part(key, 'reports') / 'downloads-ready.json'
    if (_mtime(f) or 0) + 1 < built:
        return 'downloads-ready record is older than the build'
    return None


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('--json', action='store_true'); ap.add_argument('--record', action='store_true')
    a = ap.parse_args(argv)
    res = readiness(a.key)
    if a.record:
        record(a.key, res)
    if a.json:
        print(json.dumps(res, ensure_ascii=False))
    else:
        print(json.dumps({k: v for k, v in res.items() if k != 'held'}, ensure_ascii=False))
        for p, why in list(res['held'].items())[:15]:
            print(f'   held {p}: {why[0]}')
    return 0 if res['ready'] else 1


if __name__ == '__main__':
    sys.exit(main())
