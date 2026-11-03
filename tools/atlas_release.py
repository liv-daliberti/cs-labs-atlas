"""One release command: `atlas release` (ROADMAP #37, 2026-11-01).

Runs the whole chain, in order, and stops at the first failure:

  preflight    FAST, in a few minutes, before any build (2026-11-03): main clean; the full test suite in a git-archive snapshot with the release's own
               environment (STAGES/TAG/RELEASE_ARGS set); validate and the evidence check on the current files; the regression check against the last
               release. Swings are listed for sign-off up front (--allow-swings or a signed --swings-file) and every failure is reported at once.
  rebuild      one stage at a time, each recorded in run.json (--resume starts at the failed stage): snapshot, build (a per-school Slurm array,
               newest school first; --serial-build runs it in this job), zero_paper, ids, copies, ledger, audits, evidence, tests   (hierarchy/rebuild.sh)
  regression   the build regression check against the pre-build snapshot             (STAGES=regression; BEFORE validate, which reads its file)
  validate     the packages and shared files against schemas/                         (STAGES=validate)
  reader       the reader export: host or link per confirmed copy, by licence         (STAGES=reader; tools/reader_export.py)
  release      tools/make_release.py: the immutable dated release, with CHANGES.md (the release notes, generated from the regression)
  notes        the release carries CHANGES.md and reader/ (checked)
  tree         the organized school/lab/paper tree from the release                   (STAGES=tree)
  export       tools/export_release.py: the GitHub export repository, written and committed locally
  export-push  EXTERNAL: tag release-<id> and push the export repository to origin
  hf-upload    EXTERNAL: tools/hf_upload_release.py, the private Hugging Face dataset
  handoff      the publication handoff (SITE-HANDOFF.md: what changed, where to read it, the reader steps), added to the release

The steps that publish outside this host (export-push, hf-upload) never run on their own: they need --yes-push / --yes-hf, or an answer "y" at
the terminal; in a job (no terminal) without the flag the run stops there with exit status 3 and says which flag to add. Everything before
them is local and rerunnable. Progress is kept in <scratch>/release-<tag>/run.json: `--resume` skips the steps that passed.

usage: atlas release [--local] [--tag TAG] [--schools "a b"] [--from STEP] [--only STEP[,STEP]] [--resume] [--dry-run] [--preflight-only]
                     [--target all|site] [--release-id ID] [--yes-push] [--yes-hf] [--allow-swings | --swings-file FILE] [--export-dir DIR]
                     [--serial-build] [--array-throttle N]
By default the chain runs as the Slurm job hierarchy/release.slurm and this command blocks until it ends (one sacct call per 120 s or more; exit 0 = the
job completed; `--wait` is accepted and means the same). `--local` runs it in this process instead: opt-in only, because the login host's memory budget is
shared. --dry-run and --local are the only modes that do not submit. One release at a time: a lock (atlas lease `atlas-release`, holder and host) is refused
while another release holds it and released on exit. --preflight-only runs the preflight and stops (nothing is built or frozen).
A signed swings file is JSON {"signed_by": "...", "signed_at": "YYYY-MM-DD", "swings": ["<id>", ...]} with the ids the preflight prints.
Use --target site to freeze and write a handoff without GitHub/Hugging Face exports.
Resume requires the same --tag, source commit and options. The exact frozen release
is saved in run.json; downstream steps never resolve the moving latest symlink.
Run it in a Slurm job (hierarchy/release.slurm) or a terminal multiplexer: the rebuild takes an hour or more. Exit 0 all steps passed,
1 a step failed, 3 stopped at an external step awaiting confirmation.
"""
import argparse, concurrent.futures, contextlib, datetime, json, os, re, shlex, signal, socket, subprocess, sys, threading, time
from pathlib import Path

import agent_lease  # noqa: E402
import atlas_paths as P  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
REBUILD = ['bash', str(CODE / 'hierarchy' / 'rebuild.sh')]  # route-ok: code that stays in hierarchy/, not a data file
EXTERNAL = {'export-push': 'yes_push', 'hf-upload': 'yes_hf'}
FLAG = {'yes_push': '--yes-push', 'yes_hf': '--yes-hf'}
ORDER = ['preflight', 'rebuild', 'regression', 'validate', 'reader', 'release', 'notes', 'tree', 'export', 'export-push', 'hf-upload', 'handoff']
SITE_ORDER = ORDER[:7] + ['handoff']
# the rebuild's stages, in order (hierarchy/rebuild.sh STAGES); `reader` is its own release step, regression and validate follow the rebuild
REBUILD_STAGES = ['snapshot', 'build', 'zero_paper', 'ids', 'copies', 'ledger', 'audits', 'evidence', 'tests']
LOCK_NAME = 'atlas-release'
LOCK_TTL = 4 * 3600          # renewed every LOCK_BEAT seconds by a heartbeat thread and after every step; a crashed holder expires
LOCK_BEAT = 300
LEASE_ROOT = None            # tests point this at a temporary directory
SAFE_RESUME_DIRS = ('tests/', 'docs/')   # a commit that only touches these may resume (with a recorded note)


def git(*a, cwd=None):
    cwd = cwd or P.CODE   # the main checkout (a job runs its tools from a snapshot that has no .git)
    return subprocess.run(['git', '-C', str(cwd), *a], capture_output=True, text=True)


def newest_first(schools):
    """The build order: the newest school (last in charter order) first, so a school still settling in fails soonest (owner 2026-11-03)."""
    return list(reversed(list(schools)))


class Ctx:
    def __init__(self, a):
        self.a = a
        self.tag = a.tag or 'release-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path(P.SCRATCH) / self.tag
        self.release_id = a.release_id
        self.state = {}
        self.runner = subprocess.run
        self.commit = os.environ.get('CS_ATLAS_SNAPSHOT_COMMIT') or git('rev-parse', 'HEAD').stdout.strip()
        raw = getattr(a, 'raw_args', None)
        # the environment the release's own stages run in: tests that pass without it and fail with it are what the preflight must catch (2026-11-03 (b))
        self.env = dict(os.environ, TAG=self.tag, RELEASE_ARGS=os.environ.get('RELEASE_ARGS') or ' '.join(shlex.quote(x) for x in (raw or [])))
        if self.commit:
            self.env['CS_ATLAS_SNAPSHOT_COMMIT'] = self.commit   # every stage runs the code of one commit
        if a.schools:
            self.env['SCHOOLS'] = a.schools
        if a.allow_swings:
            self.env['ALLOW_SWINGS'] = '1'
        self.export_dir = Path(a.export_dir or P.EXPORT)
        self.state_f = self.dir / 'run.json'

    @property
    def schools(self):
        return self.a.schools.split() if self.a.schools else list(P.SCHOOL_IDS)

    def save(self):
        tmp = self.state_f.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.state, indent=1))
        tmp.replace(self.state_f)


def stages(stage_list):
    return lambda c: (REBUILD, dict(c.env, STAGES=stage_list))


def exact_release(c):
    if not c.release_id:
        raise ValueError('No frozen release recorded; run the release step or pass --release-id ID')
    return c.release_id


def swings_approved(c):
    return bool(c.a.allow_swings or c.state.get('_swings_approved'))


def cmd_for(step, c):
    """(argv, env) of a step, or a callable(c) -> (ok, message) for the steps done in-process."""
    if step == 'preflight':
        return preflight
    if step == 'rebuild':
        return rebuild_step
    if step == 'reader':   # recomputed at release time against the site's hosted set as it is now (read-only): the takedown list travels in the release
        site = Path(P.SITE) / 'atlas' / 'data'
        return ([sys.executable, str(CODE / 'tools' / 'reader_export.py'), '--site-local-papers', str(site / 'local-papers.json'),
                 '--site-reader-objects', str(site / 'reader-objects.json')], c.env)
    if step in ('validate', 'regression'):
        return stages(step)(c)
    if step == 'tree':
        return ([sys.executable, str(CODE / 'tools' / 'organize_tree.py'), '--release', exact_release(c)] +
                (c.a.schools.split() if c.a.schools else []), c.env)
    if step == 'release':
        return ([sys.executable, str(CODE / 'tools' / 'make_release.py')] + (['--allow-swings'] if swings_approved(c) else []), c.env)
    if step == 'notes':
        return check_notes
    if step == 'export':
        return ([sys.executable, str(CODE / 'tools' / 'export_release.py'), str(c.export_dir), '--release', exact_release(c)], c.env)
    if step == 'export-push':
        return push_export
    if step == 'hf-upload':
        return ([sys.executable, str(CODE / 'tools' / 'hf_upload_release.py'), exact_release(c)], c.env)
    if step == 'handoff':
        return handoff
    raise SystemExit(f'unknown step {step}')


# ---- swings: listed for sign-off up front, approved by --allow-swings or a signed file ----

def swing_id(flag):
    """The id the preflight prints and a swings file lists: kind|school|pi-or-count."""
    return '|'.join(str(flag[k]) for k in ('kind', 'school', 'pi', 'count') if flag.get(k) is not None)


def load_swings_file(path):
    """-> (approved ids, error). Signed = signed_by and signed_at present, and a list of ids."""
    try:
        d = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return set(), f'swings file {path}: {e}'
    if not isinstance(d, dict) or not str(d.get('signed_by') or '').strip() or not str(d.get('signed_at') or '').strip() or not isinstance(d.get('swings'), list):
        return set(), f'swings file {path} is not signed: it needs "signed_by", "signed_at" and a "swings" list of ids'
    return set(map(str, d['swings'])), None


def swings_verdict(flags, allow_all=False, swings_file=None):
    """-> (ok, ids, unapproved ids, error)."""
    ids = [swing_id(f) for f in flags]
    if not ids or allow_all:
        return True, ids, [], None
    if not swings_file:
        return False, ids, ids, None
    approved, err = load_swings_file(swings_file)
    if err:
        return False, ids, ids, err
    missing = [i for i in ids if i not in approved]
    return not missing, ids, missing, None


# ---- the fast preflight ----

def last_release_hierarchy():
    latest = Path(P.RELEASES) / 'latest'
    try:
        d = latest.resolve() / 'hierarchy'
    except OSError:
        return None
    return d if d.is_dir() else None


def run_logged(c, argv, env, log):
    with open(log, 'w') as f:
        return c.runner(argv, env=env, stdout=f, stderr=subprocess.STDOUT, cwd=str(CODE)).returncode


def log_tail(log, n=4):
    try:
        return ' | '.join(Path(log).read_text().splitlines()[-n:])
    except OSError:
        return '(no log)'


def preflight_regression(c, d):
    """The build regression check of the current files against the last release: -> (rc, flags, note)."""
    base = last_release_hierarchy()
    if base is None:
        return 0, [], 'no previous release to compare with'
    py = sys.executable
    tool = str(CODE / 'tools' / 'build_regression.py')
    counts = d / 'preflight-last-release-counts.json'
    if run_logged(c, [py, tool, 'snapshot', '--from', str(base), '--out', str(counts)], c.env, d / 'preflight-regression-snapshot.log'):
        return 1, [], 'snapshot of the last release failed: ' + log_tail(d / 'preflight-regression-snapshot.log')
    rc = run_logged(c, [py, tool, 'check', '--before', str(counts), '--md', str(d / 'preflight-BUILD-REGRESSION.md'), '--json', str(d / 'preflight-BUILD-REGRESSION.json')],
                    c.env, d / 'preflight-regression.log')
    if rc not in (0, 2):
        return 1, [], 'regression check failed: ' + log_tail(d / 'preflight-regression.log')
    try:
        flags = json.loads((d / 'preflight-BUILD-REGRESSION.json').read_text()).get('flags', [])
    except (OSError, ValueError):
        flags = []
    return rc, flags, f'against {base.parent.name}'


def preflight(c):
    """Everything that failed only after a 35-60 minute rebuild, checked first and in parallel (about the time of the slowest check, the test suite)."""
    t0 = time.time()
    br = git('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
    problems, notes = [], []
    if br != 'main':
        problems.append(f'clean: run it from the main checkout on main (this is {br})')
    dirty = [ln for ln in git('status', '--porcelain', '--untracked-files=no').stdout.splitlines() if ln.strip()]
    if dirty:
        problems.append(f'clean: uncommitted tracked changes (commit or land them first): {dirty[:5]}')
    c.dir.mkdir(parents=True, exist_ok=True)
    d = c.dir
    py, tools = sys.executable, CODE / 'tools'
    ev_out = d / 'preflight-evidence'
    ev_out.mkdir(exist_ok=True)
    jobs = {
        'tests': lambda: run_logged(c, *stages('tests')(c), d / 'preflight-tests.log'),   # the rebuild's own tests stage: git-archive snapshot, STAGES/TAG/RELEASE_ARGS exported
        'validate': lambda: run_logged(c, [py, str(tools / 'validate.py'), *c.schools, '--shared', '--json', str(d / 'preflight-VALIDATION.json')], c.env, d / 'preflight-validate.log'),
        'evidence': lambda: run_logged(c, [py, str(tools / 'evidence_check.py'), '--out', str(ev_out)], c.env, d / 'preflight-evidence.log'),
        'regression': lambda: preflight_regression(c, d),
    }
    results, took = {}, {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futs = {pool.submit(lambda f=f: (f(), round(time.time() - t0))): k for k, f in jobs.items()}
        for fut in concurrent.futures.as_completed(futs):
            k = futs[fut]
            try:
                results[k], took[k] = fut.result()
            except Exception as e:   # a crashed check is a failed check, reported with the others
                results[k], took[k] = (1, [], f'crashed: {e}') if k == 'regression' else 1, round(time.time() - t0)
    for k in ('tests', 'validate', 'evidence'):
        if results[k]:
            problems.append(f'{k}: failed ({took[k]} s): ' + log_tail(d / f'preflight-{k}.log'))
        else:
            notes.append(f'{k} ok ({took[k]} s)')
    rc, flags, note = results['regression']
    if rc == 1:
        problems.append('regression: ' + note)
    else:
        ok, ids, missing, err = swings_verdict(flags, c.a.allow_swings, getattr(c.a, 'swings_file', None))
        if ids:
            print(f'preflight: {len(ids)} regression swing(s) {note}, for sign-off (details: {d / "preflight-BUILD-REGRESSION.md"}):', flush=True)
            for i in ids:
                print(f'  swing {i}' + ('' if ok or i in missing else '  (approved)'), flush=True)
        if ok:
            notes.append(f'regression ok {note}' + (f'; {len(ids)} swing(s) approved' if ids else ', no swings'))
        else:
            problems.append((err or f'{len(missing)} swing(s) not signed off: rerun with --allow-swings or --swings-file listing them') + f' (ids above; {d / "preflight-BUILD-REGRESSION.md"})')
    if not getattr(c.a, 'serial_build', False):   # sbatch --test-only of the build array now, not after the snapshot stage
        ok, msg = submit_build_array(c, test_only=True)
        (notes if ok else problems).append(('build array ' if ok else 'build array: ') + msg)
    seconds = round(time.time() - t0)
    (d / 'preflight.json').write_text(json.dumps(dict(ok=not problems, seconds=seconds, problems=problems, notes=notes, swings=[swing_id(f) for f in flags]), indent=1))
    if problems:
        return False, f'{len(problems)} problem(s) in {seconds} s: ' + ' || '.join(problems)
    return True, f'main at {git("rev-parse", "--short", "HEAD").stdout.strip()}, clean; {seconds} s: ' + '; '.join(notes)


def check_clean(c):
    """The quick re-check a resume makes: still on main, nothing tracked is dirty."""
    br = git('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
    if br != 'main':
        return False, f'run it from the main checkout on main (this is {br})'
    dirty = [ln for ln in git('status', '--porcelain', '--untracked-files=no').stdout.splitlines() if ln.strip()]
    if dirty:
        return False, f'uncommitted tracked changes (commit or land them first): {dirty[:5]}'
    return True, f'main at {git("rev-parse", "--short", "HEAD").stdout.strip()}, clean'


# ---- the rebuild, one recorded stage at a time ----

def sbatch(args, env):
    return subprocess.run(['sbatch', *args], capture_output=True, text=True, env=env, cwd=str(P.CODE))


def wait_jobs(jobs):
    import slurm_wait
    return slurm_wait.wait(jobs)


def submit_build_array(c, test_only=False):
    """The build stage as a per-school Slurm array (hierarchy/build-school.slurm, MODE=build), newest school first. -> (ok, message) or, submitted, (True, job id)."""
    schools = newest_first(c.schools)
    n = len(schools)
    arr = f'0-{n - 1}' + (f'%{c.a.array_throttle}' if getattr(c.a, 'array_throttle', None) else '')
    env = dict(c.env, MODE='build', SCHOOL_LIST=' '.join(schools), NEW_CODE=str(P.CODE), CS_ATLAS_SNAPSHOT_COMMIT=c.commit)   # NEW_CODE has the .git the array tasks archive from
    script = str(CODE / 'hierarchy' / 'build-school.slurm')  # route-ok: code that stays in hierarchy/
    out = f'{P.CODE}/hierarchy/logs/build-school-%A_%a.out'
    base = ['--parsable', '--export=ALL', f'--array={arr}', '--output', out, script]
    probe = sbatch(['--test-only', *base], env)
    text = (probe.stderr or '') + (probe.stdout or '')
    if probe.returncode:
        return False, 'sbatch --test-only of the build array failed: ' + text.strip()[:200]
    if 'Preempts:' in text:
        return (True, 'sbatch --test-only reports Preempts (the build stage waits for a clean --test-only)') if test_only else (False, 'sbatch --test-only reports Preempts: not submitted')
    if test_only:
        return True, f'sbatch --test-only passes ({n} schools, newest first: {" ".join(schools)})'
    r = sbatch(base, env)
    if r.returncode:
        return False, 'sbatch of the build array failed: ' + (r.stderr or '').strip()[:200]
    return True, r.stdout.strip().split(';')[0]


def build_parallel(c):
    ok, job = submit_build_array(c)
    if not ok:
        return False, job
    print(f'build: array job {job} ({len(c.schools)} schools, newest first); waiting with one sacct call per 120 s or more', flush=True)
    import slurm_wait
    v, st = wait_jobs([job])
    table = slurm_wait.table(st)
    (c.dir / 'rebuild-build.log').write_text(f'array job {job}\n{table}\n{v}\n')
    return v == 'ok', f'array job {job}: {v}; school logs hierarchy/logs/build-school-{job}_<n>.out\n{table}'


def rebuild_step(c):
    """Run the rebuild stages not yet recorded done; every stage is recorded in run.json at once, so --resume starts at the failed one."""
    done = c.state.setdefault('rebuild_stages', {})
    ran = 0
    for st in REBUILD_STAGES:
        if done.get(st, {}).get('ok'):
            print(f'  {st:12} passed earlier (resume)', flush=True)
            continue
        t0 = time.time()
        if st == 'build' and not getattr(c.a, 'serial_build', False):
            ok, msg = build_parallel(c)
        else:
            argv, env = stages(st)(c)
            log = c.dir / f'rebuild-{st}.log'
            ok = run_logged(c, argv, env, log) == 0
            msg = f'log {log}' + ('' if ok else ': ' + log_tail(log))
        done[st] = dict(ok=ok, message=msg[:400], seconds=round(time.time() - t0), at=datetime.datetime.now().isoformat(timespec='seconds'), commit=c.commit[:10])
        c.save()
        print(f'  {st:12} {"ok" if ok else "FAILED"}  {round(time.time() - t0)} s', flush=True)
        if not ok:
            return False, f'stage {st} failed ({msg}); `--resume` restarts at it'
        ran += 1
    return True, f'{ran} stage(s) run, {len(REBUILD_STAGES) - ran} already done'


def check_notes(c):
    rid = exact_release(c)
    d = Path(P.RELEASES) / rid
    need = ['CHANGES.md', 'MANIFEST.json', 'reader/SUMMARY.json', 'reader/README.md', 'reader/unpublish.tsv', 'reader/upload.tsv', 'reader/currently-hosted-not-permitted.tsv']
    miss = [n for n in need if not (d / n).exists()]
    return (not miss), (f'release {rid}: ' + ('CHANGES.md and reader/ present' if not miss else f'missing {miss}'))


def push_export(c):
    d = c.export_dir
    rid = exact_release(c)
    tag = f'release-{rid}'
    st = git('status', '--porcelain', cwd=d).stdout.strip()
    if st:
        r = git('add', '-A', cwd=d)
        r = git('commit', '-q', '-m', f'Export release {rid}', cwd=d)
        if r.returncode:
            return False, 'commit failed: ' + r.stderr.strip()[:200]
    r = git('tag', '-f', tag, cwd=d)
    r = git('push', 'origin', 'main', tag, cwd=d)
    return r.returncode == 0, (r.stderr.strip() or r.stdout.strip())[-300:] or f'pushed main and {tag}'


def render_handoff(rid, d, publication=None):
    """Assistant-independent handoff; only completed external steps are reported as published."""
    publication = publication or {}
    man = json.loads((d / 'MANIFEST.json').read_text())
    rd = json.loads((d / 'reader' / 'SUMMARY.json').read_text()) if (d / 'reader' / 'SUMMARY.json').exists() else {}
    if not rd or not rd.get('site_sync'):
        raise ValueError('no reader export with a site sync (reader/SUMMARY.json site_sync): the Take down section cannot be produced')
    t, ss = rd.get('totals') or {}, rd['site_sync']
    by = ', '.join(f'{k}: {v}' for k, v in (ss.get('unpublish_by_reason') or {}).items())
    L = [f'# Publication handoff: release {rid}', '',
         f"Created {man.get('created')} from code {str((man.get('code') or {}).get('commit'))[:10]}. Read-only, immutable: `{d}`.", '',
         '## What changed', '', 'CHANGES.md in the release is generated from the build regression: counts per school, the PIs that moved most, rules added, commits. Start there.', '']
    L += ['## Counts per school', '', '| school | PIs | lab papers | students | student-paper links |', '|---|---|---|---|---|']
    for s, c in (man.get('counts') or {}).items():
        L.append(f"| {s} | {c.get('pis')} | {c.get('lab_papers')} | {c.get('students')} | {c.get('student_paper_links')} |")
    L += ['', '## Host', '',
          f"{t.get('host')} papers have a stored copy whose licence allows redistribution; the site HOSTS them. `reader/hosted-files.tsv` lists the files (sha256, bytes, school, store path); "
          f"`reader/upload.tsv` the {ss.get('upload')} not on the site yet. `reader/<school>.jsonl.gz` rows with `decision: host` carry the path. `reader/README.md` says exactly how the site "
          "marks a paper readable (a works entry in local-papers.json).", '',
          '## Link', '',
          f"{t.get('link')} papers are readable through a source link: a confirmed copy whose licence does not allow hosting, or a candidate URL confirmed to be the paper (`link_basis`). "
          "Rows with `decision: link` carry `source_url`; write them as works entries with `link: true` and no `path` (see reader/README.md). Candidate links wait for a landing-page check "
          f"where unconfirmed: `reader/link-check-requests.tsv` ({rd.get('link_check_request_urls')} URLs). Readable papers overall: {t.get('readable')} of {t.get('lab_papers')}, host and link "
          f"together; {t.get('not_readable')} stay not readable.", '',
          '## Take down (required)', '',
          f"The site serves ONLY from releases. **Remove {ss.get('unpublish')} files from public hosting, from `data/local-papers.json` (`files` and the `works` entries that point at them) and "
          "from `reader-objects.json`**, without touching our stores. The list, computed at release time against the site's hosted set as it was then "
          f"({ss.get('site_files')} files; {ss.get('keep')} stay): `reader/unpublish.tsv` (sha256, bytes, path, reason, licence, schools). Reasons: {by}. `not_in_stores` files are untraceable to any "
          "store and have no licence we can show; `license` files may not be redistributed; `no_confirmed_copy` files have no confirmed copy; `outside_release` are outside this release's hosted set. "
          "`reader/currently-hosted-not-permitted.tsv` is the licence subset. After the take-down and the upload, `files` in local-papers.json and reader-objects.json equal "
          "`reader/hosted-files.tsv` exactly.", '',
          '## Where', '', f"- Release: `{d}` (MANIFEST.json lists every file with its sha256).",
          f"- GitHub export: {'completed in this run; tag release-' + rid if publication.get('export-push', {}).get('ok') else 'not performed in this run'}.",
          f"- Hugging Face upload: {'completed in this run; see HF-UPLOAD.json' if publication.get('hf-upload', {}).get('ok') else 'not performed in this run'}.",
          '- Website: separate preparation, upload and deployment; this handoff does not certify publication.', '',
          '## Prepare the site', '',
          'Follow `site/docs/PUBLISHING.md`. From the site checkout:', '',
          f'```sh\npython3 scripts/release.py plan --release {rid}\npython3 scripts/release.py prepare --release {rid}\n```',
          '', 'The same commands apply to a human, CI, ChatGPT, Claude, or another assistant. Keep credentials out of this handoff.', '']
    return '\n'.join(L)


def handoff(c):
    rid = exact_release(c)
    d = Path(P.RELEASES) / rid
    f = c.dir / 'SITE-HANDOFF.md'
    try:
        f.write_text(render_handoff(rid, d, c.state))
    except ValueError as e:
        return False, str(e)
    r = subprocess.run([sys.executable, str(CODE / 'tools' / 'make_release.py'), 'add-note', rid, 'SITE-HANDOFF.md', str(f)], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()[-300:]


def confirmed(step, c):
    flag = EXTERNAL[step]
    if getattr(c.a, flag):
        return True
    if sys.stdin.isatty():
        return input(f'{step} publishes outside this host. Run it? [y/N] ').strip().lower() == 'y'
    return False


def run_step(step, c, runner=subprocess.run):
    c.runner = runner
    spec = cmd_for(step, c)
    if callable(spec):
        ok, msg = spec(c)
        return ok, msg
    argv, env = spec
    log = c.dir / f'{step}.log'
    with open(log, 'w') as f:
        r = runner(argv, env=env, stdout=f, stderr=subprocess.STDOUT, cwd=str(CODE))
    if step == 'release' and r.returncode == 0:
        receipts = []
        for line in log.read_text().splitlines():
            try:
                item = json.loads(line)
                if isinstance(item, dict) and 'release' in item and 'dir' in item:
                    receipts.append(item)
            except ValueError:
                pass
        if len(receipts) != 1 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:\.\d+)?', receipts[0]['release']):
            return False, 'Freeze succeeded without one exact release receipt; inspect release.log before resuming'
        c.release_id = receipts[0]['release']
    tail = log.read_text().splitlines()[-3:]
    if step == 'regression' and r.returncode == 2:   # rebuild.sh exits 2 for swings only (1 = a failure)
        if c.a.allow_swings:
            return True, f'swings allowed (--allow-swings); log {log}: ' + ' | '.join(tail)
        if getattr(c.a, 'swings_file', None):
            try:
                flags = json.loads(Path(P.data('BUILD-REGRESSION.json')).read_text()).get('flags', [])
            except (OSError, ValueError) as e:
                return False, f'cannot read BUILD-REGRESSION.json to check the swings file: {e}'
            ok, ids, missing, err = swings_verdict(flags, False, c.a.swings_file)
            if ok:
                c.state['_swings_approved'] = True
                return True, f'{len(ids)} swing(s) approved by the signed swings file {c.a.swings_file}; log {log}'
            return False, (err or f'{len(missing)} swing(s) not in the signed swings file: ' + ', '.join(missing[:10])) + f'; log {log}'
    return r.returncode == 0, f'exit {r.returncode}; log {log}' + (': ' + ' | '.join(tail) if r.returncode else '')


@contextlib.contextmanager
def release_lock(c, root=None, beat=None):
    """One release at a time (2026-11-03 (i)): an atlas lease with the holder and host, refused while another live release holds it, released on exit
    (also on SIGTERM, i.e. scancel). A heartbeat renews it, so a crashed holder's lease expires instead of blocking for ever."""
    root = root or LEASE_ROOT
    session = f'release:{socket.gethostname()}:{os.getpid()}'
    note = f'{c.tag} job {os.environ.get("SLURM_JOB_ID", "-")}'
    ok, cur = agent_lease.acquire(LOCK_NAME, session=session, ttl=LOCK_TTL, note=note, root=root)
    if not ok:
        raise ReleaseLocked(lock_message(cur))
    stop = threading.Event()

    def pulse():
        while not stop.wait(beat or LOCK_BEAT):
            agent_lease.renew(LOCK_NAME, session=session, root=root)
    t = threading.Thread(target=pulse, daemon=True)
    t.start()
    old = None
    try:
        old = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
    except ValueError:   # not the main thread
        pass
    try:
        yield session
    finally:
        stop.set()
        if old is not None:
            signal.signal(signal.SIGTERM, old)
        agent_lease.release(LOCK_NAME, session=session, root=root)


class ReleaseLocked(Exception):
    pass


def lock_message(cur):
    return (f"another release is running: {cur.get('note')} on {cur.get('host')} (pid {cur.get('pid')}, since {cur.get('started_at')}, "
            f"session {cur.get('session')}); only one at a time. If it is certainly gone: atlas lease release {LOCK_NAME} --force")


def lock_holder(root=None):
    cur = agent_lease.read(LOCK_NAME, root or LEASE_ROOT)
    return cur if agent_lease.live(cur) else None


def submit_and_wait(args, run=subprocess.run, wait=None):
    """The default: the chain runs as the Slurm job hierarchy/release.slurm (code pinned to main's HEAD now, `sbatch --test-only` first and
    refused on `Preempts:`), and this command blocks until it ends with one sacct call per 120 s or more (tools/slurm_wait.py). -> exit status."""
    import slurm_wait
    wait = wait or slurm_wait.wait
    holder = lock_holder()
    if holder:
        print('atlas release: not submitted: ' + lock_message(holder), file=sys.stderr)
        return 1
    head = run(['git', '-C', str(P.CODE), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    env = dict(os.environ, CS_ATLAS_SNAPSHOT_COMMIT=head, RELEASE_ARGS=' '.join(shlex.quote(x) for x in args))
    script = str(CODE / 'hierarchy' / 'release.slurm')  # route-ok: code that stays in hierarchy/
    probe = run(['sbatch', '--parsable', '--test-only', '--export=ALL', script], capture_output=True, text=True, env=env, cwd=str(P.CODE))
    if probe.returncode or 'Preempts:' in (probe.stderr or '') + (probe.stdout or ''):
        print('atlas release: not submitted: ' + ((probe.stderr or probe.stdout or '').strip()[:300] or 'sbatch --test-only failed'), file=sys.stderr)
        return 1
    r = run(['sbatch', '--parsable', '--export=ALL', script], capture_output=True, text=True, env=env, cwd=str(P.CODE))
    if r.returncode:
        print('atlas release: sbatch failed: ' + (r.stderr or '').strip()[:300], file=sys.stderr)
        return 1
    job = r.stdout.strip().split(';')[0]
    print(f'atlas release: job {job} (code commit {head[:7]}); log {P.data("logs")}/release-{job}.out; run dir {P.SCRATCH}/release-{job}; '
          f'waiting with one sacct call per {slurm_wait.MIN_INTERVAL} s', flush=True)
    v, st = wait([job], run=run)
    print(slurm_wait.table(st))
    print(f'atlas release: {v}')
    return 0 if v == 'ok' else 1


def classify_commit_change(old, new):
    """-> (safe, files). A resume across commits is safe only when every changed file is under tests/ or docs/."""
    r = git('diff', '--name-only', old, new)
    if r.returncode:
        return False, [f'cannot diff {old[:10]}..{new[:10]}: ' + (r.stderr or '').strip()[:100]]
    files = [f for f in r.stdout.splitlines() if f]
    return bool(files) and all(f.startswith(SAFE_RESUME_DIRS) for f in files) or not files, files


def main(argv=None, runner=subprocess.run):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag'); ap.add_argument('--schools'); ap.add_argument('--export-dir')
    ap.add_argument('--target', choices=['all', 'site'], default='all')
    ap.add_argument('--release-id', help='Exact existing frozen release for downstream-only work')
    ap.add_argument('--from', dest='from_step', choices=ORDER); ap.add_argument('--only')
    ap.add_argument('--resume', action='store_true'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--yes-push', action='store_true'); ap.add_argument('--yes-hf', action='store_true')
    ap.add_argument('--allow-swings', action='store_true'); ap.add_argument('--swings-file', help='a signed JSON file listing the approved swing ids')
    ap.add_argument('--wait', action='store_true', help='accepted for compatibility: submitting and waiting is the default')
    ap.add_argument('--local', action='store_true', help='run in this process (opt-in: the login host has a shared memory budget); default is a Slurm job')
    ap.add_argument('--preflight-only', action='store_true', help='run the fast preflight and stop: nothing is built or frozen')
    ap.add_argument('--serial-build', action='store_true', help='build the schools one after another in this job instead of a per-school Slurm array')
    ap.add_argument('--array-throttle', type=int, help='at most N school tasks at once')
    a = ap.parse_args(argv)
    if a.allow_swings and a.swings_file:
        ap.error('--allow-swings and --swings-file are alternatives')
    if a.swings_file and not Path(a.swings_file).is_file():
        ap.error(f'--swings-file {a.swings_file}: no such file')
    if a.preflight_only and (a.only or a.from_step or a.resume):
        ap.error('--preflight-only takes no --only/--from/--resume')
    if not a.dry_run and not a.local:
        return submit_and_wait([x for x in argv if x not in ('--wait', '--local')])
    a.raw_args = [x for x in argv if x not in ('--wait', '--local')]
    if a.tag and (not re.fullmatch(r'[A-Za-z0-9_.-]+', a.tag) or a.tag in ('.', '..')):
        ap.error('--tag must be a simple run name, not a path')
    if a.resume and not a.tag:
        ap.error('--resume requires the original --tag')
    if a.release_id and not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:\.\d+)?', a.release_id):
        ap.error('--release-id must be an exact dated ID, not latest')
    order = SITE_ORDER if a.target == 'site' else ORDER
    if a.from_step and a.from_step not in order:
        ap.error('--from step is not part of this target')
    if a.only is not None and set(a.only.split(',')) - set(order):
        ap.error('--only contains an unknown step or a step outside this target')
    if a.preflight_only:
        a.only = 'preflight'
    c = Ctx(a)
    steps = order[order.index(a.from_step):] if a.from_step else list(order)
    if a.only:
        steps = [s for s in steps if s in a.only.split(',')]
    state_f = c.state_f
    state = json.loads(state_f.read_text()) if a.resume and state_f.exists() else {}
    context = dict(target=a.target, schools=a.schools, allow_swings=a.allow_swings, export_dir=str(c.export_dir), commit=c.commit)
    if a.resume:
        saved = state.get('_context') or {}
        if not state or {k: v for k, v in saved.items() if k != 'commit'} != {k: v for k, v in context.items() if k != 'commit'}:
            ap.error('Cannot resume missing/legacy state or changed options; inspect run.json and start a new tag')
        if saved.get('commit') != context['commit']:
            safe, files = classify_commit_change(saved.get('commit') or '', context['commit'])
            if not safe:
                ap.error(f"Cannot resume: the source commit changed {str(saved.get('commit'))[:10]} -> {context['commit'][:10]} and it touches more than tests/ and docs/: {files[:8]}; start a new tag")
            note = (f"resuming across commits {str(saved.get('commit'))[:10]} -> {context['commit'][:10]}: only tests/ and docs/ changed ({len(files)} files); "
                    'stage results are kept' + ('; tests re-run (tests/ changed)' if any(f.startswith('tests/') for f in files) else ''))
            print('NOTE: ' + note, flush=True)
            state.setdefault('_notes', []).append(note)
            state.get('preflight', {}).update(ok=False)   # the preflight checks the new commit again
            if any(f.startswith('tests/') for f in files):
                state.get('rebuild_stages', {}).pop('tests', None)
                state.get('rebuild', {}).update(ok=False)
        saved_id = state.get('_release_id')
        if a.release_id and saved_id and a.release_id != saved_id:
            ap.error('--release-id differs from this run')
        c.release_id = saved_id or a.release_id
        if state.get('preflight', {}).get('ok') and not a.dry_run:
            ok, message = check_clean(c)
            if not ok:
                ap.error('Resume preflight failed: ' + message)
    elif state_f.exists() and not a.dry_run:
        ap.error('Run tag already exists; use --resume or a new --tag')
    if 'release' in steps and c.release_id:
        if not state.get('release', {}).get('ok'):
            ap.error('An existing --release-id cannot be combined with a new freeze')
    if not a.dry_run and 'release' not in steps and not c.release_id and set(steps) & {'notes', 'tree', 'export', 'export-push', 'hf-upload', 'handoff'}:
        ap.error('Downstream steps require --release-id or a resumed frozen release')
    state['_context'] = context
    c.state = state
    if a.dry_run:
        for s in steps:
            if s in ('tree', 'export', 'hf-upload') and not c.release_id:
                print(f'{s:12} ' + ('EXTERNAL ' + FLAG[EXTERNAL[s]] + ' ' if s in EXTERNAL else '') + '(uses the exact release produced by this run)')
                continue
            if s == 'rebuild':
                print(f"{s:12} (in-process, one recorded stage each) " + ' '.join(f"{st}{'[array, newest first]' if st == 'build' and not a.serial_build else ''}" for st in REBUILD_STAGES))
                continue
            spec = cmd_for(s, c)
            print(f"{s:12} " + ('EXTERNAL ' + FLAG[EXTERNAL[s]] if s in EXTERNAL else '') + (' '.join(spec[0]) + f" STAGES={spec[1].get('STAGES', '')}" if not callable(spec) else '(in-process)'))
        return 0
    c.dir.mkdir(parents=True, exist_ok=True)
    try:
        with release_lock(c):
            return run_chain(c, steps, runner, state)
    except ReleaseLocked as e:
        print('atlas release: ' + str(e), file=sys.stderr)
        return 1


def run_chain(c, steps, runner, state):
    state_f = c.state_f
    print(f'atlas release {c.tag}: {", ".join(steps)}' + ('  (local: opt-in, on this host)' if not os.environ.get('SLURM_JOB_ID') else ''), flush=True)
    for s in steps:
        if state.get(s, {}).get('ok'):
            print(f'{s:12} passed earlier (resume)')
            continue
        if s in EXTERNAL and not confirmed(s, c):
            print(f'{s:12} STOPPED: this step publishes outside this host; rerun with {FLAG[EXTERNAL[s]]} (and --resume) to run it')
            c.save()
            return 3
        t0 = time.time()
        try:
            ok, msg = run_step(s, c, runner)
        except (ValueError, OSError) as error:
            ok, msg = False, str(error)
        state['_release_id'] = c.release_id
        state[s] = dict(ok=ok, message=msg, seconds=round(time.time() - t0), at=datetime.datetime.now().isoformat(timespec='seconds'))
        c.save()
        print(f"{s:12} {'ok' if ok else 'FAILED'}  {msg}", flush=True)
        if not ok:
            return 1
    print('atlas release: all steps passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
