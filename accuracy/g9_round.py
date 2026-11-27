"""Gate 9, round pi2: the ONE redraw of every included school after the data freeze (owner 2026-11-19: 50 per measure per school, a NEW seed,
independent reviewers). One tool for the whole chain; nothing here judges anything.

  plan     [--schools a b | default: every school with an included PI] [--seed N] [--work DIR]
           the schools, their included PIs and nominal reviewer batches. Reads packages only; writes nothing but --json.
  draw     --seed N [--schools ...] --yes      draws accuracy/round-pi2/sample-<school>.json (never overwrites a draw). The seed must be new: it is refused
           when an earlier round (sample.ROUNDS) or any draw file in accuracy/ used it. One process, a few seconds per school.
  batches  [--schools ...] [--work DIR]        from the DRAWN files: <= 25 rows per reviewer batch, per school and measure (lab_precision, student_precision,
           lab_coverage; student_coverage is judged in candidate order in waves, see SCOV_WAVE), the sheet command, the output path and the reviewer prompt of
           each batch -> DIR/batches.json
  sheets   [--schools ...] [--work DIR]        writes DIR/sheets/<batch>.txt (accuracy/evidence.py, read-only)
  convert  [--schools ...] [--work DIR]        reviewer outputs DIR/out/<batch>.jsonl -> accuracy/round-pi2/verdicts-<school>.jsonl (+ screened-<school>.jsonl);
                                               refuses a missing or duplicated item; never overwrites
Then, per school: ACCURACY_ROUND=pi2 python accuracy/summarize.py --school <key> writes accuracy/summary-<key>.json (what `atlas stage-gate <key> 9` reads).

Reviewers (docs in the plan): every batch goes to a FRESH subagent that did not draw the sample and sees no other batch's verdicts; the brief is
scratch/g9-1119/BRIEF.md (criteria from accuracy/ACCURACY.md; stored evidence only, no network; `doubtful` when the evidence cannot decide); each
verdict cites the stored evidence (affiliation string, DOI, year, period). A batch is at most 25 rows.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

ACC = Path(__file__).resolve().parent
import sample as S0  # noqa: E402,F401  (the script's directory is sys.path[0]; sample.py puts tools/ on the path for atlas_paths)
import atlas_paths as P  # noqa: E402

ROUND = 'pi2'          # 'pi2', 'pi2b', 'pi2c' or 'pi2d' (D-0026: redraws of superseded schools go to accuracy/round-pi2b/); set from --round
MAX_BATCH = 25
SCOV_WAVE = 3          # student coverage: judge candidates in order; first wave = 3 batches of 25 candidates, then one more batch per wave until 50 confirmed or the 200 candidates are used
MEASURES = (('lab_precision', 'lab'), ('student_precision', 'student'), ('lab_coverage', 'coverage'))
BRIEF = '/n/fs/resemble/homogenizing-science/scratch/g9-1119/BRIEF.md'
FAIL = {'namesake', 'not_at_school', 'outside_appointment', 'not_a_paper', 'wrong_student', 'other', 'missing_from_build', 'student_not_linked'}


def main_acc():
    """The measurements live in the main checkout (untracked there); a worktree or a job snapshot only carries the code."""
    return Path(P.CODE) / 'accuracy'


def used_seeds():
    S = S0
    seeds = {c['seed'] for c in S.ROUNDS.values() if c.get('seed')} | {S.SEED}
    for f in list(main_acc().glob('round-*/sample-*.json')) + list(main_acc().glob('sample*.json')):
        try:
            d = json.loads(f.read_text())
            if isinstance(d, dict) and d.get('seed'):
                seeds.add(d['seed'])
        except (OSError, ValueError):
            pass
    return seeds


def included_schools(only=None):
    import pi_release as PR
    out = {}
    for f in sorted(Path(P.SCHOOL_CONFIGS).glob('*.toml')):
        s = f.stem
        if s == 'TEMPLATE' or (only and s not in only):
            continue
        try:
            pl = PR.plan(s)
        except Exception as e:   # a school without a package has nothing to draw
            out[s] = dict(error=repr(e)[:120], included=0)
            continue
        out[s] = dict(included=len(pl['included']), held=len(pl['held']), sha=pl['included_sha'][:12])
    return {s: v for s, v in out.items() if v['included']}


def chunks(n, size=MAX_BATCH):
    return [(i, min(size, n - i)) for i in range(0, n, size)]


def cmd_plan(a):
    sch = included_schools(a.schools)
    tot = 0
    rows = []
    for s, v in sch.items():
        nominal = dict(lab_precision=65, student_precision=65, lab_coverage=50)   # 50 uniform + up to 15 stratum rows (pi1 draws: 60-65)
        nb = {m: len(chunks(n)) for m, n in nominal.items()}
        nb['student_coverage'] = SCOV_WAVE            # first wave; more only while fewer than 50 confirmed
        rows.append(dict(school=s, **v, nominal_batches=nb, nominal_total=sum(nb.values())))
        tot += sum(nb.values())
    seed_ok = (a.seed not in used_seeds()) if a.seed else None
    print(f'{ROUND}: {len(sch)} schools with an included PI, about {tot} reviewer batches of <= {MAX_BATCH} rows (judging uniform + stratum rows, as in pi1)')
    for r in rows:
        print(f"  {r['school']:10s} included {r['included']:4d} held {r['held']:4d} sha {r['sha']} batches {r['nominal_total']}")
    if a.seed:
        print(f'seed {a.seed}: {"NEW" if seed_ok else "ALREADY USED, pick another"}')
    if a.json:
        Path(a.json).write_text(json.dumps(dict(round=ROUND, schools=rows, total_batches=tot, seed=a.seed, seed_new=seed_ok), indent=1) + '\n')
    return 0 if seed_ok in (None, True) else 1


def cmd_draw(a):
    if a.seed in used_seeds():
        sys.exit(f'seed {a.seed} was used by an earlier round or draw: the owner rule is a NEW seed')
    if not a.yes:
        sys.exit('refusing to draw without --yes (the freeze must be declared first; a draw is never overwritten)')
    sch = list(included_schools(a.schools))
    env = dict(os.environ, ACCURACY_REDRAW_SEED=str(a.seed), PYTHONHASHSEED='0', ACCURACY_DRAW_ROOT=str(main_acc()))
    r = subprocess.run([sys.executable, '-u', str(ACC / 'sample.py'), '--round', ROUND, '--school', *sch], env=env)
    return r.returncode


def drawn(schools=None):
    d = main_acc() / S0.ROUNDS[ROUND]['dir']
    out = {}
    for f in sorted(d.glob('sample-*.json')):
        s = f.stem[len('sample-'):]
        if schools and s not in schools:
            continue
        out[s] = json.loads(f.read_text())
    return out


def cmd_batches(a):
    work = Path(a.work)
    batches = []
    for s, doc in drawn(a.schools).items():
        S = doc['schools'][s]
        for m, kind in MEASURES:
            for k, (start, n) in enumerate(chunks(len(S[m])), 1):
                refs = [str(it['i']) if 'i' in it else it['key'] for it in S[m][start:start + n]]
                batches.append(dict(id=f'{s}-{kind}-{k:02d}', school=s, measure=m, kind=kind, start=start, n=n, refs=refs))
        cands = S['student_coverage_order']
        for k, (start, n) in enumerate(chunks(len(cands)), 1):
            batches.append(dict(id=f'{s}-scov-{k:02d}', school=s, measure='student_coverage', kind='scov', start=start, n=n,
                                refs=[c['key'] for c in cands[start:start + n]], wave=1 + max(0, k - SCOV_WAVE),
                                note='judge in order; stop after the first confirmed PhD students needed to reach 50 in total over the batches; launch batches beyond the first wave only while fewer than 50 are confirmed'))
    for b in batches:
        b['sheet'] = str(work / 'sheets' / f"{b['id']}.txt")
        b['out'] = str(work / 'out' / f"{b['id']}.jsonl")
        b['sheet_cmd'] = f"ACCURACY_ROUND={ROUND} python accuracy/evidence.py {b['school']} {b['kind']} {b['n']} {b['start']}"
        b['prompt'] = (f"You are a FRESH, independent reviewer of gate 9 (round {ROUND}). Read {BRIEF} first, then judge every item of your sheet {b['sheet']} "
                       f"(school {b['school']}, {b['measure']}, {b['n']} items) from the STORED evidence only and write one JSONL line per item to {b['out']}. "
                       f"You did not draw this sample and must not look at any other reviewer's output or at accuracy/round-*/verdicts*. Cite concrete evidence in each reason.")
    work.mkdir(parents=True, exist_ok=True)
    (work / 'batches.json').write_text(json.dumps(dict(round=ROUND, max_batch=MAX_BATCH, batches=batches), indent=1) + '\n')
    per = {}
    for b in batches:
        per.setdefault(b['school'], []).append(b)
    print(f'{len(batches)} batches (<= {MAX_BATCH} rows) for {len(per)} schools -> {work / "batches.json"}')
    return 0


def cmd_sheets(a):
    work = Path(a.work)
    plan = json.loads((work / 'batches.json').read_text())
    (work / 'sheets').mkdir(exist_ok=True)
    env = dict(os.environ, ACCURACY_ROUND=ROUND)
    for b in plan['batches']:
        if a.schools and b['school'] not in a.schools:
            continue
        dest = Path(b['sheet'])
        if dest.exists():
            continue
        r = subprocess.run([sys.executable, str(ACC / 'evidence.py'), b['school'], b['kind'], str(b['n']), str(b['start'])], env=env, capture_output=True, text=True)
        if r.returncode:
            print('SHEET-FAIL', b['id'], r.stderr[-300:])
            continue
        dest.write_text(r.stdout)
    return 0


def _rows(f):
    return [json.loads(l) for l in open(f) if l.strip()] if Path(f).exists() else []


def cmd_convert(a):
    work = Path(a.work)
    plan = json.loads((work / 'batches.json').read_text())
    now = datetime.datetime.now().isoformat(timespec='seconds')
    rd = main_acc() / S0.ROUNDS[ROUND]['dir']
    for s, doc in drawn(a.schools).items():
        S = doc['schools'][s]
        mine = [b for b in plan['batches'] if b['school'] == s]
        items = {m: {(str(it['i']) if 'i' in it else it['key']): it for it in S[m]} for m, _ in MEASURES}
        cand = {c['key']: c for c in S['student_coverage_order']}
        out, screened = [], []
        for b in mine:
            got = _rows(b['out'])
            if b['kind'] != 'scov':
                refs = [str(r['ref']) for r in got]
                if sorted(refs) != sorted(b['refs']):
                    sys.exit(f"{b['id']}: reviewer output covers {len(set(refs))} of {len(b['refs'])} items (missing {sorted(set(b['refs']) - set(refs))[:3]}, duplicates {len(refs) - len(set(refs))})")
            for r in got:
                ref = str(r['ref'])
                v, extra = r['verdict'], {}
                if v == 'doubtful':
                    extra['doubtful'] = True
                    v = 'unclear'
                ft = r.get('failure_type') if v == 'incorrect' else None
                if v == 'incorrect' and ft not in FAIL:
                    sys.exit(f"{b['id']} {ref}: failure_type {ft!r} not in {sorted(FAIL)}")
                if r.get('policy'):
                    extra['policy'] = r['policy']
                for k in ('true_lab_paper', 'in_build', 'has_coauthored_paper', 'linked'):
                    if k in r:
                        extra[k] = r[k]
                if b['kind'] == 'scov':
                    if r.get('screened'):
                        screened.append(dict(r, batch=b['id']))
                        continue
                    it = cand[ref]
                    stratum = 'thesis_advisee_phd_ge_2018'
                else:
                    it = items[b['measure']][ref]
                    stratum = it.get('stratum')
                out.append(dict(school=s, sample=b['measure'], stratum=stratum, item=it['key'], row=it.get('i'), verdict=v, failure_type=ft,
                                reason=('DOUBTFUL: ' if extra.get('doubtful') else '') + r['reason'], evidence=P.rel_label(P.school_part(s, 'derived')),
                                reviewer=f"independent-g9-{ROUND}-{b['id']}", judged_at=now, **extra))
        # student coverage: the first 50 confirmed in candidate order count; later ones are surplus
        order = {c['key']: i for i, c in enumerate(S['student_coverage_order'])}
        sc = sorted((d for d in out if d['sample'] == 'student_coverage'), key=lambda d: order[d['item']])
        drop = {id(d) for d in sc[50:]}
        out = [d for d in out if id(d) not in drop]
        have = {d['sample'] for d in out}
        for m, _ in MEASURES:
            if m not in have and S[m]:
                sys.exit(f'{s}: no verdicts for {m}')
        with open(rd / f'verdicts-{s}.jsonl', 'x') as fh:
            for d in out:
                fh.write(json.dumps(d, ensure_ascii=False) + '\n')
        if screened:
            with open(rd / f'screened-{s}.jsonl', 'x') as fh:
                for r in screened:
                    fh.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(s, len(out), 'verdicts', len(screened), 'screened')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['plan', 'draw', 'batches', 'sheets', 'convert'])
    ap.add_argument('--schools', nargs='*')
    ap.add_argument('--seed', type=int)
    ap.add_argument('--work', default=str(Path(P.CODE).parent / 'scratch' / 'g9-pi2'))
    ap.add_argument('--json')
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--round', choices=['pi2', 'pi2b', 'pi2c', 'pi2d'], default='pi2')
    a = ap.parse_args(argv)
    global ROUND
    ROUND = a.round
    if a.cmd == 'draw' and not a.seed:
        ap.error('draw needs --seed')
    return globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
