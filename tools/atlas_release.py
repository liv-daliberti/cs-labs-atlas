"""One release command: `atlas release` (ROADMAP #37, 2026-11-01).

Runs the whole chain, in order, and stops at the first failure:

  preflight    main checkout clean, hooks and tests are the later steps' business; here: the code is committed, no stage is half done
  rebuild      snapshot, build, ids, copies, ledger, audits, evidence, tests        (hierarchy/rebuild.sh, STAGES=...)
  validate     the packages and shared files against schemas/                         (STAGES=validate)
  regression   the build regression check against the pre-build snapshot             (STAGES=regression)
  reader       the reader export: host or link per confirmed copy, by licence         (STAGES=reader; tools/reader_export.py)
  release      tools/make_release.py: the immutable dated release, with CHANGES.md (the release notes, generated from the regression)
  notes        the release carries CHANGES.md and reader/ (checked)
  tree         the organized school/lab/paper tree from the release                   (STAGES=tree)
  export       tools/export_release.py: the GitHub export repository, written and committed locally
  export-push  EXTERNAL: tag release-<id> and push the export repository to origin
  hf-upload    EXTERNAL: tools/hf_upload_release.py, the private Hugging Face dataset
  handoff      the Codex handoff note (SITE-HANDOFF.md: what changed, where to read it, the reader steps), added to the release

The steps that publish outside this host (export-push, hf-upload) never run on their own: they need --yes-push / --yes-hf, or an answer "y" at
the terminal; in a job (no terminal) without the flag the run stops there with exit status 3 and says which flag to add. Everything before
them is local and rerunnable. Progress is kept in <scratch>/release-<tag>/run.json: `--resume` skips the steps that passed.

usage: atlas release [--tag TAG] [--schools "a b"] [--from STEP] [--only STEP[,STEP]] [--resume] [--dry-run]
                     [--yes-push] [--yes-hf] [--allow-swings] [--export-dir DIR]
Run it in a Slurm job (hierarchy/release.slurm) or a terminal multiplexer: the rebuild takes an hour or more. Exit 0 all steps passed,
1 a step failed, 3 stopped at an external step awaiting confirmation.
"""
import argparse, datetime, json, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
REBUILD = ['bash', str(CODE / 'hierarchy' / 'rebuild.sh')]
EXTERNAL = {'export-push': 'yes_push', 'hf-upload': 'yes_hf'}
FLAG = {'yes_push': '--yes-push', 'yes_hf': '--yes-hf'}
ORDER = ['preflight', 'rebuild', 'validate', 'regression', 'reader', 'release', 'notes', 'tree', 'export', 'export-push', 'hf-upload', 'handoff']


class Ctx:
    def __init__(self, a):
        self.a = a
        self.tag = a.tag or 'release-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path(P.SCRATCH) / self.tag
        self.release_id = None
        self.env = dict(os.environ, TAG=self.tag)
        if a.schools:
            self.env['SCHOOLS'] = a.schools
        if a.allow_swings:
            self.env['ALLOW_SWINGS'] = '1'
        self.export_dir = Path(a.export_dir or P.EXPORT)


def stages(stage_list):
    return lambda c: (REBUILD, dict(c.env, STAGES=stage_list))


def latest_release():
    p = (Path(P.RELEASES) / 'latest').resolve()
    return p.name if p.exists() else None


def cmd_for(step, c):
    """(argv, env) of a step, or a callable(c) -> (ok, message) for the steps done in-process."""
    if step == 'preflight':
        return preflight
    if step == 'rebuild':
        return stages('snapshot build ids copies ledger audits evidence tests')(c)
    if step in ('validate', 'regression', 'reader', 'tree'):
        return stages(step)(c)
    if step == 'release':
        return ([sys.executable, str(CODE / 'tools' / 'make_release.py')] + (['--allow-swings'] if c.a.allow_swings else []), c.env)
    if step == 'notes':
        return check_notes
    if step == 'export':
        return ([sys.executable, str(CODE / 'tools' / 'export_release.py'), str(c.export_dir), '--release', c.release_id or 'latest'], c.env)
    if step == 'export-push':
        return push_export
    if step == 'hf-upload':
        return ([sys.executable, str(CODE / 'tools' / 'hf_upload_release.py'), c.release_id or 'latest'], c.env)
    if step == 'handoff':
        return handoff
    raise SystemExit(f'unknown step {step}')


def git(*a, cwd=None):
    cwd = cwd or P.CODE   # the main checkout (a job runs its tools from a snapshot that has no .git)
    return subprocess.run(['git', '-C', str(cwd), *a], capture_output=True, text=True)


def preflight(c):
    br = git('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
    if br != 'main':
        return False, f'run it from the main checkout on main (this is {br})'
    dirty = [l for l in git('status', '--porcelain', '--untracked-files=no').stdout.splitlines() if l.strip()]
    if dirty:
        return False, f'uncommitted tracked changes (commit or land them first): {dirty[:5]}'
    return True, f'main at {git("rev-parse", "--short", "HEAD").stdout.strip()}, clean'


def check_notes(c):
    rid = c.release_id = latest_release()
    if not rid:
        return False, 'no release'
    d = Path(P.RELEASES) / rid
    need = ['CHANGES.md', 'MANIFEST.json', 'reader/SUMMARY.json', 'reader/README.md']
    miss = [n for n in need if not (d / n).exists()]
    return (not miss), (f'release {rid}: ' + ('CHANGES.md and reader/ present' if not miss else f'missing {miss}'))


def push_export(c):
    d = c.export_dir
    rid = c.release_id or latest_release()
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


def render_handoff(rid, d):
    man = json.loads((d / 'MANIFEST.json').read_text())
    rd = json.loads((d / 'reader' / 'SUMMARY.json').read_text()) if (d / 'reader' / 'SUMMARY.json').exists() else {}
    L = [f'# Handoff for Codex: release {rid}', '',
         f"Created {man.get('created')} from code {str((man.get('code') or {}).get('commit'))[:10]}. Read-only, immutable: `{d}`.", '',
         '## What changed', '', 'CHANGES.md in the release is generated from the build regression: counts per school, the PIs that moved most, rules added, commits. Start there.', '']
    L += ['## Counts per school', '', '| school | PIs | lab papers | students | student-paper links |', '|---|---|---|---|---|']
    for s, c in (man.get('counts') or {}).items():
        L.append(f"| {s} | {c.get('pis')} | {c.get('lab_papers')} | {c.get('students')} | {c.get('student_paper_links')} |")
    if rd:
        t = rd.get('totals') or {}
        L += ['', '## Readable papers (reader/)', '',
              f"{t.get('readable')} of {t.get('lab_papers')} lab papers are readable: {t.get('host')} hosted (licence allows redistribution), {t.get('link')} linked to the source; "
              f"{t.get('not_readable')} not readable. `reader/README.md` says exactly how the site marks a paper readable (a works entry in local-papers.json; link entries have "
              f"`link: true` and no `path`), `reader/hosted-files.tsv` lists the files to upload and `reader/currently-hosted-not-permitted.tsv` the {rd.get('currently_hosted_not_permitted')} files to unpublish.",
              f"Candidate links wait for a landing-page check where unconfirmed: `reader/link-check-requests.tsv` ({rd.get('link_check_request_urls')} URLs).", '']
    L += ['## Where', '', f"- Release: `{d}` (MANIFEST.json lists every file with its sha256).",
          f"- GitHub export: tag `release-{rid}` on the export repository's main.", '- Hugging Face: the private dataset, releases/<id>/ (HF-UPLOAD.json in the release records the verified upload).', '']
    return '\n'.join(L)


def handoff(c):
    rid = c.release_id or latest_release()
    d = Path(P.RELEASES) / rid
    f = c.dir / 'SITE-HANDOFF.md'
    f.write_text(render_handoff(rid, d))
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
    spec = cmd_for(step, c)
    if callable(spec):
        ok, msg = spec(c)
        return ok, msg
    argv, env = spec
    log = c.dir / f'{step}.log'
    with open(log, 'w') as f:
        r = runner(argv, env=env, stdout=f, stderr=subprocess.STDOUT, cwd=str(CODE))
    tail = log.read_text().splitlines()[-3:]
    return r.returncode == 0, f'exit {r.returncode}; log {log}' + (': ' + ' | '.join(tail) if r.returncode else '')


def main(argv=None, runner=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag'); ap.add_argument('--schools'); ap.add_argument('--export-dir')
    ap.add_argument('--from', dest='from_step', choices=ORDER); ap.add_argument('--only')
    ap.add_argument('--resume', action='store_true'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--yes-push', action='store_true'); ap.add_argument('--yes-hf', action='store_true'); ap.add_argument('--allow-swings', action='store_true')
    a = ap.parse_args(argv)
    c = Ctx(a)
    steps = ORDER[ORDER.index(a.from_step):] if a.from_step else list(ORDER)
    if a.only:
        steps = [s for s in ORDER if s in a.only.split(',')]
    state_f = c.dir / 'run.json'
    state = json.loads(state_f.read_text()) if a.resume and state_f.exists() else {}
    if a.dry_run:
        for s in steps:
            spec = cmd_for(s, c)
            print(f"{s:12} " + ('EXTERNAL ' + FLAG[EXTERNAL[s]] if s in EXTERNAL else '') + (' '.join(spec[0]) + f" STAGES={spec[1].get('STAGES', '')}" if not callable(spec) else '(in-process)'))
        return 0
    c.dir.mkdir(parents=True, exist_ok=True)
    print(f'atlas release {c.tag}: {", ".join(steps)}', flush=True)
    for s in steps:
        if state.get(s, {}).get('ok'):
            print(f'{s:12} passed earlier (resume)')
            continue
        if s in EXTERNAL and not confirmed(s, c):
            print(f'{s:12} STOPPED: this step publishes outside this host; rerun with {FLAG[EXTERNAL[s]]} (and --resume) to run it')
            state_f.write_text(json.dumps(state, indent=1))
            return 3
        t0 = time.time()
        ok, msg = run_step(s, c, runner)
        state[s] = dict(ok=ok, message=msg, seconds=round(time.time() - t0), at=datetime.datetime.now().isoformat(timespec='seconds'))
        state_f.write_text(json.dumps(state, indent=1))
        print(f"{s:12} {'ok' if ok else 'FAILED'}  {msg}", flush=True)
        if not ok:
            return 1
    print('atlas release: all steps passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
