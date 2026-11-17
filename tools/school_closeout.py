"""One reusable school closeout: repairs -> sealed inputs -> native job -> reviews.

atlas closeout stages SCHOOL [--json]
atlas closeout plan SCHOOL
atlas closeout research SCHOOL [--previous FILE] [--out FILE] [--json]
atlas closeout seal SCHOOL --run-dir DIR --repairs FILE
atlas closeout submit SCHOOL --run-dir DIR
atlas closeout status|certify|draw SCHOOL --run-dir DIR

Uses the existing builder, audits, gates and recall rules. Never accepts a
review, changes a threshold, publishes, or repairs scientific inputs itself.
Run against the school's reviewed data overlay using the CS_ATLAS_* slots.
"""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import atlas_paths as P

CODE = Path(__file__).resolve().parents[1]
GATES = (1, 2, 3, 4, 5, 7, 8)
STAGES = {
    0: ('Charter and access', (), 'Confirm charter, host policy and snapshot coverage.'),
    1: ('Faculty sources', (0,), 'Finish the missing department/year source captures.'),
    2: ('Faculty census', (1,), 'Resolve candidate identities and census decisions as one batch.'),
    3: ('PI labs and websites', (2,), 'Complete PI basis, home departments and website evidence.'),
    4: ('Appointment periods', (3,), 'Resolve dated appointment evidence and explicit gap decisions.'),
    5: ('Publication identities', (4,), 'Resolve identity anchors and zero-yield publication cases.'),
    6: ('Students and recall', (5,), 'Finish complete roster repairs, then the fixed independent recall review.'),
    7: ('Papers and links', (5,), 'Resolve exact paper attribution and all unexplained student-paper links.'),
    8: ('Copies and availability', (7,), 'Count current copies and finish the availability ledger.'),
    9: ('Accuracy review', (6, 7, 8), 'Judge the final fixed accuracy sample on this same candidate.'),
    10: ('Research release', tuple(range(10)), 'Freeze and integrate the reviewed research; prepare and verify publication.'),
}
OUTPUTS = {
    'build': ('pis.json', 'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'report.json', 'home-departments-school.json'),
    'copies': ('copies.json',),
    'ledger': ('copies.json', 'unavailable.jsonl.gz', 'unavailable-summary.json'),
    'diagnose': ('link-diagnosis.json',),
    'students': ('student-audit-school.json',),
}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    path = Path(path)
    temporary = path.with_name(path.name + f'.{os.getpid()}.part')
    temporary.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def fingerprint(path, content=True):
    path = Path(path)
    if not path.exists():
        return None
    stat = path.stat()
    if not path.is_file():
        return dict(kind='directory', modified_ns=stat.st_mtime_ns)
    if not content:
        return dict(bytes=stat.st_size, modified_ns=stat.st_mtime_ns)
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for part in iter(lambda: handle.read(2**20), b''):
            digest.update(part)
    return dict(bytes=stat.st_size, sha256=digest.hexdigest())


@contextlib.contextmanager
def locked(directory):
    with (Path(directory) / '.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another closeout operation owns this run') from None
        yield


def code_commit():
    return os.environ.get('CS_ATLAS_SNAPSHOT_COMMIT') or subprocess.check_output(
        ['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip()


def stage_board(school, evaluate=None):
    """All current gates, explicit prerequisites, and one next eligible stage.

    This evaluates the selected data root; it never substitutes recorded main
    receipts for an isolated candidate, nor treats a planned action as a pass.
    """
    import stage_gate as G
    evaluate = evaluate or G.evaluate
    results = {}
    for stage in STAGES:
        try:
            results[stage] = evaluate(school, str(stage))
        except (OSError, ValueError, KeyError) as exc:
            results[stage] = dict(gate='unmeasured', items=[str(exc)])
    complete = {stage for stage, result in results.items() if result.get('gate') in ('pass', 'waived')}
    rows = []
    for stage, (label, requires, action) in STAGES.items():
        result = results[stage]
        waiting = [n for n in requires if n not in complete]
        items = result.get('unwaived_items', result.get('items', []))
        status = ('complete' if result.get('gate') == 'pass' else 'waived') if stage in complete else (
            'waiting' if waiting else 'unmeasured' if result.get('gate') == 'unmeasured' else 'needs review' if stage in (6, 9) else 'needs work')
        rows.append(dict(stage=stage, name=label, status=status, gate=result.get('gate'),
                         blocked_by=waiting, findings=items, action=action,
                         check=f'bin/atlas stage-gate {school} {stage} --json'))
    eligible = [r for r in rows if r['stage'] not in complete and not r['blocked_by']]
    return dict(school=school, data_root=str(P.CODE), hierarchy=str(P.HIERARCHY), code_commit=code_commit(),
                stages=rows, next_stage=eligible[0]['stage'] if eligible else None,
                native_ready=all(n in complete for n in GATES),
                research_ready=all(n in complete for n in range(10)),
                publication_note='Stage 10 is the formal research release. A separately verified interim website snapshot is a distinct milestone.')


def render_stages(board):
    lines = [f"{board['school']} — current stage advancement", f"Data: {board['data_root']}", '',
             '| Stage | Work | State | Waiting for | Findings |', '|---:|---|---|---|---:|']
    for row in board['stages']:
        lines.append(f"| {row['stage']} | {row['name']} | {row['status']} | "
                     + ', '.join(map(str, row['blocked_by'])) + f" | {len(row['findings'])} |")
    if board['next_stage'] is not None:
        row = board['stages'][board['next_stage']]
        lines += ['', f"Next: stage {row['stage']} — {row['action']}", row['check']]
        lines += ['- ' + finding for finding in row['findings'][:8]]
    else:
        lines += ['', 'All research stages pass on this data root.']
    lines += ['', board['publication_note']]
    return '\n'.join(lines)


def input_specs(school):
    """Known paths only; hash reviewed content, guard large raw stores by stat.

    Include absent optional inputs so adding evidence also invalidates the seal.
    Shared reviewed inputs must be private copies in a school overlay when other
    schools are changing them. Catalog downloads may continue independently.
    """
    from stale_stages import native_upstream_paths
    paths = {str(path): dict(content=True) for path in native_upstream_paths(school)}
    for name, kind, flat, _split in P.DATA_FILES:
        if kind not in ('raw', 'reviewed') or name == 'student-recall-check.json':
            continue
        if '{school}' not in flat and kind != 'reviewed':
            continue
        path = Path(P.data(name, school if '{school}' in flat else None))
        content = kind == 'reviewed' or path.suffix in ('.json', '.jsonl', '.csv', '.toml')
        paths[str(path)] = dict(content=content)
        if path.suffix == '.sqlite':
            for suffix in ('-journal', '-wal'):
                paths[str(path) + suffix] = dict(content=False)
    paths[str(P.SCHOOL_CONFIGS / (school + '.toml'))] = dict(content=True)
    return paths


def changed_inputs(seal):
    return [name for name, item in seal['inputs'].items()
            if fingerprint(name, item['content']) != item['fingerprint']]


def phases(school):
    return [
        ('build', [sys.executable, str(CODE / 'tools/pi_hierarchy.py'), school]),
        ('copies', [sys.executable, str(CODE / 'tools/lab_paper_copies.py'), school]),
        ('ledger', [str(P.COLLECTOR_PY), '-I', '-u', str(CODE / 'fulltext-push/unavailable_ledger.py'), school, '--offline']),
        ('diagnose', [sys.executable, str(CODE / 'tools/link_diagnosis.py'), school]),
        ('students', [sys.executable, str(CODE / 'tools/student_audit.py'), school]),
    ]


def repair_cases(path, school):
    board = read(path)
    if board.get('school') != school or not isinstance(board.get('cases'), list):
        raise ValueError('Repair board needs the school key and a cases list')
    ids = [row.get('id') for row in board['cases']]
    if not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Repair case IDs must be nonempty and unique')
    if 'research' in board:
        import research_plan
        research_plan.validate_board(board)
    unresolved = [r['id'] for r in board['cases'] if r.get('status') != 'resolved']
    if unresolved:
        raise ValueError('Finish the repair batch before building: ' + ', '.join(unresolved))
    receipts = {}
    for case in board['cases']:
        receipt = case.get('receipt') or {}
        path = receipt.get('path', '')
        if path not in receipts:
            receipts[path] = fingerprint(path)
        actual = receipts[path]
        if not actual or not actual.get('sha256') or actual['sha256'] != receipt.get('sha256'):
            raise ValueError('Repair receipt missing or changed: ' + case['id'])
    return board


def seal_run(school, directory, repairs):
    import school_config as S
    from pihier import preflight
    if S.get(school).get('status') != 'onboarding':
        raise ValueError('Closeout writes only onboarding schools')
    preflight.check(school)
    board = repair_cases(repairs, school)
    dirty = subprocess.check_output(['git', '-C', str(CODE), 'diff', '--name-only', 'HEAD'], text=True).strip()
    if dirty:
        raise ValueError('Commit the reviewed checkout before sealing: ' + dirty.replace('\n', ', '))
    if Path(directory).exists():
        raise ValueError('Run directory already exists; inspect/resume it or use a new run')
    specs = input_specs(school)
    specs[str(Path(repairs).resolve())] = dict(content=True)
    for case in board['cases']:
        specs[case['receipt']['path']] = dict(content=True)
    inputs = {name: dict(spec, fingerprint=fingerprint(name, spec['content'])) for name, spec in specs.items()}
    seal = dict(schema=1, school=school, code_commit=code_commit(), created=now(), data_root=str(P.CODE),
                hierarchy=str(P.HIERARCHY), school_configs=str(P.SCHOOL_CONFIGS), inputs=inputs, repairs=board,
                charter=fingerprint(P.SCHOOL_CONFIGS / (school + '.toml')))
    Path(directory).mkdir(parents=True)
    write(Path(directory) / 'inputs.json', seal)
    write(Path(directory) / 'state.json', dict(status='sealed', phases=[], artifacts={}, submissions=[]))
    return seal


def validate_seal(school, directory):
    seal = read(Path(directory) / 'inputs.json')
    if seal['school'] != school or seal['code_commit'] != code_commit():
        raise ValueError('School/code differ from the sealed run; use the pinned checkout')
    if seal['data_root'] != str(P.CODE) or seal['hierarchy'] != str(P.HIERARCHY):
        raise ValueError('Data roots differ from the sealed run; restore its CS_ATLAS_* environment')
    # Slurm extracts charters to node-local snapshot paths. Compare their bytes,
    # not their location; node-local paths disappear when the job exits.
    if fingerprint(P.SCHOOL_CONFIGS / (school + '.toml')) != seal['charter']:
        raise ValueError('Running charter differs from the sealed charter')
    changed = changed_inputs(seal)
    if changed:
        raise ValueError('Inputs changed; finish one new repair batch, then seal a new run: ' + ', '.join(changed))
    return seal


def capture_outputs(school, phase):
    out = {}
    for name in OUTPUTS[phase]:
        path = Path(P.data(name, school))
        value = fingerprint(path)
        if not value or not value.get('sha256'):
            raise ValueError(f'{phase} did not produce {path}')
        out[name] = dict(value, path=str(path))
    return out


def resume_index(state):
    """Restart at the producer of a changed output, preserving earlier work."""
    names = list(OUTPUTS)
    done = state['phases']
    start = len(done)
    # Some later phases update an earlier product (ledger attaches copies data).
    owners = {name: i for i, phase in enumerate(names) for name in OUTPUTS[phase]}
    for name, entry in state['artifacts'].items():
        if fingerprint(entry['path']) != {k: v for k, v in entry.items() if k != 'path'}:
            start = min(start, owners[name])
    return min(start, len(names))


def worker(school, directory, run=subprocess.run, evaluate=None):
    import stage_gate
    evaluate = evaluate or stage_gate.evaluate
    directory = Path(directory)
    seal = validate_seal(school, directory)
    state = read(directory / 'state.json')
    start = resume_index(state)
    state['phases'] = state['phases'][:start]
    state.update(status='running', job=os.environ.get('SLURM_JOB_ID'), gates={}, ready_for_reviews=False)
    write(directory / 'state.json', state)
    for name, argv in phases(school)[start:]:
        validate_seal(school, directory)
        with (directory / (name + '.log')).open('a') as log:
            result = run(argv, stdout=log, stderr=subprocess.STDOUT, cwd=str(P.CODE))
        if result.returncode:
            state.update(status='phase_failed', failed_phase=name, exit_code=result.returncode)
            write(directory / 'state.json', state)
            return state
        validate_seal(school, directory)
        state['artifacts'].update(capture_outputs(school, name))
        if name == 'build':
            code = read(P.data('report.json', school)).get('provenance', {}).get('code', {})
            if code.get('commit') != seal['code_commit'] or not code.get('snapshot') or code.get('dirty'):
                state.update(status='phase_failed', failed_phase='build', exit_code='provenance_mismatch')
                write(directory / 'state.json', state)
                raise ValueError('Builder provenance differs from the clean sealed code snapshot')
        state['phases'].append(name)
        write(directory / 'state.json', state)
    # Collect ALL gate findings on this one build instead of discovering a new
    # gate only after each expensive rebuild. Human review gates stay separate.
    state['gates'] = {}
    for stage in GATES:
        try:
            state['gates'][str(stage)] = evaluate(school, str(stage))
        except (OSError, ValueError, KeyError) as exc:
            state['gates'][str(stage)] = dict(stage=stage, gate='fail', items=['Gate evaluation failed: ' + str(exc)])
    validate_seal(school, directory)
    state.update(status='awaiting_completion' if all(g['gate'] == 'pass' for g in state['gates'].values()) else 'gate_failed',
                 completed=now())
    write(directory / 'state.json', state)
    return state


def certify(school, directory, run=subprocess.run):
    validate_seal(school, directory)
    directory = Path(directory)
    state = read(directory / 'state.json')
    if state['status'] not in ('awaiting_completion', 'review_ready') or resume_index(state) != len(OUTPUTS):
        raise ValueError('Native outputs/gates are incomplete or changed; inspect state.json')
    job = state.get('job')
    if not job or not str(job).isdigit():
        raise ValueError('No exact producer Slurm job recorded')
    result = run(['sacct', '-n', '-P', '-j', str(job), '--format=JobIDRaw,State,ExitCode'], capture_output=True, text=True, check=True)
    rows = [line.split('|') for line in result.stdout.splitlines()]
    exact = [row for row in rows if len(row) >= 3 and row[0] == str(job)]
    if len(exact) != 1 or exact[0][1:3] != ['COMPLETED', '0:0']:
        raise ValueError('Exact producer job has not completed successfully; no review draw permitted')
    state.update(status='review_ready', ready_for_reviews=True, slurm=exact[0][:3])
    write(directory / 'state.json', state)
    return state


def submission_available(state, run=subprocess.run):
    """One scheduler lookup prevents duplicate jobs and permits timeout recovery."""
    if state['status'] in ('awaiting_completion', 'review_ready', 'gate_failed'):
        raise ValueError('Native run is complete; certify it or finish a new repair batch')
    if state.get('submissions'):
        job = str(next(iter(state['submissions'][-1].values())))
        result = run(['sacct', '-n', '-P', '-j', job, '--format=JobIDRaw,State,ExitCode'],
                     capture_output=True, text=True, check=True)
        exact = [r for line in result.stdout.splitlines() if (r := line.split('|'))[0] == job]
        failures = {'FAILED', 'CANCELLED', 'TIMEOUT', 'OUT_OF_MEMORY', 'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL', 'DEADLINE'}
        if len(exact) != 1 or len(exact[0]) < 3 or exact[0][1].split()[0] not in failures:
            raise ValueError('Prior job is live, successful, or unknown; no duplicate submission')


def draw_once(school, directory, drawn_by):
    import student_recall as R
    directory = Path(directory)
    validate_seal(school, directory)
    state = read(directory / 'state.json')
    if not state.get('ready_for_reviews') or resume_index(state) != len(OUTPUTS):
        raise ValueError('Certify the completed native job before drawing the review')
    original = directory / 'draw-original.json'
    if original.exists():
        if fingerprint(original) != state.get('draw_fingerprint'):
            raise ValueError('Original review draw changed; restore the preserved draw before resuming')
        return read(original)  # resume the same draw; never rotate its sample
    worksheet = Path(P.data_w('student-recall-check.json', school))
    if worksheet.exists():
        prior = worksheet.read_bytes()
        if read(worksheet).get('binds') == R.bindings(school):
            raise ValueError('A review already exists on this build; resume it rather than drawing again')
        (directory / 'prior-recall.json').write_bytes(prior)
        if worksheet.is_symlink():
            worksheet.unlink()
            worksheet.write_bytes(prior)
    record = R.draw(school, drawn_by=drawn_by)
    write(original, record)
    state['draw_fingerprint'] = fingerprint(original)
    write(directory / 'state.json', state)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stages', 'plan', 'research', 'seal', 'submit', 'worker', 'status', 'certify', 'draw'])
    parser.add_argument('school')
    parser.add_argument('--run-dir', type=Path)
    parser.add_argument('--repairs', type=Path)
    parser.add_argument('--drawn-by', default=os.environ.get('ATLAS_SESSION', ''))
    parser.add_argument('--json', action='store_true', help='Machine-readable stage advancement')
    parser.add_argument('--previous', type=Path, help='Prior research board with explicit whole-source review receipts')
    parser.add_argument('--out', type=Path, help='Write the research board to this file; existing files are preserved')
    args = parser.parse_args(argv)
    try:
        if args.command == 'research':
            import research_plan
            if args.out and (args.out.exists() or args.out.is_symlink()):
                raise ValueError('Research output already exists; preserve it and choose a new path: ' + str(args.out))
            board = research_plan.collect(args.school, read(args.previous) if args.previous else None)
            if args.out:
                # A previous board may be the only durable copy of human review work.
                with args.out.open('x') as handle:
                    json.dump(board, handle, indent=2, ensure_ascii=False)
                    handle.write('\n')
            print(json.dumps(board, indent=2, ensure_ascii=False) if args.json else research_plan.render(board))
            return 0
        if args.command == 'stages':
            board = stage_board(args.school)
            print(json.dumps(board, indent=2) if args.json else render_stages(board))
            return 0
        if args.command == 'plan':
            print(json.dumps(dict(school=args.school, data_root=str(P.CODE), code_commit=code_commit(),
                                  phases=[dict(name=n, argv=a) for n, a in phases(args.school)], gates=GATES,
                                  reviews='After certification: one fixed recall draw; fresh independent review; then existing accuracy workflow.'), indent=2))
            return 0
        if not args.run_dir or (args.command == 'seal' and not args.repairs):
            parser.error('--run-dir is required; seal also requires --repairs')
        if args.command == 'seal':
            result = seal_run(args.school, args.run_dir, args.repairs)
        else:
            with locked(args.run_dir):
                if args.command == 'status':
                    seal = read(args.run_dir / 'inputs.json')
                    result = dict(read(args.run_dir / 'state.json'), changed_inputs=changed_inputs(seal))
                elif args.command == 'submit':
                    import atlas_pipeline as AP
                    seal = validate_seal(args.school, args.run_dir)
                    state = read(args.run_dir / 'state.json')
                    submission_available(state)
                    stages = [('closeout', 'once', 'PY $TOOLS/school_closeout.py worker {school} --run-dir "$ATLAS_CLOSEOUT_RUN"', 'project', 4, '24G', '00:59:00')]
                    jobs = AP.submit('school-closeout', [args.school], stages=stages, commit=seal['code_commit'],
                                     repo=CODE, guard_preempt=True, overrides={'ATLAS_CLOSEOUT_RUN': str(args.run_dir.resolve())})
                    state['submissions'].append(jobs)
                    state['status'] = 'submitted'
                    write(args.run_dir / 'state.json', state)
                    result = jobs
                elif args.command == 'worker':
                    if not os.environ.get('SLURM_JOB_ID'):
                        raise ValueError('Worker must run in the submitted Slurm job')
                    result = worker(args.school, args.run_dir)
                elif args.command == 'certify':
                    result = certify(args.school, args.run_dir)
                else:
                    result = draw_once(args.school, args.run_dir, args.drawn_by)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1 if result.get('status') in ('phase_failed', 'gate_failed') else 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print('Closeout stopped: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
