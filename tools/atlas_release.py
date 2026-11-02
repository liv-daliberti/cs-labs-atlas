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
  handoff      the publication handoff (SITE-HANDOFF.md: what changed, where to read it, the reader steps), added to the release

The steps that publish outside this host (export-push, hf-upload) never run on their own: they need --yes-push / --yes-hf, or an answer "y" at
the terminal; in a job (no terminal) without the flag the run stops there with exit status 3 and says which flag to add. Everything before
them is local and rerunnable. Progress is kept in <scratch>/release-<tag>/run.json: `--resume` skips the steps that passed.

usage: atlas release [--tag TAG] [--schools "a b"] [--from STEP] [--only STEP[,STEP]] [--resume] [--dry-run]
                     [--target all|site] [--release-id ID] [--yes-push] [--yes-hf] [--allow-swings] [--export-dir DIR]
Use --target site to freeze and write a handoff without GitHub/Hugging Face exports.
Resume requires the same --tag, source commit and options. The exact frozen release
is saved in run.json; downstream steps never resolve the moving latest symlink.
Run it in a Slurm job (hierarchy/release.slurm) or a terminal multiplexer: the rebuild takes an hour or more. Exit 0 all steps passed,
1 a step failed, 3 stopped at an external step awaiting confirmation.
"""
import argparse, datetime, json, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
REBUILD = ['bash', str(CODE / 'hierarchy' / 'rebuild.sh')]  # route-ok: code that stays in hierarchy/, not a data file
EXTERNAL = {'export-push': 'yes_push', 'hf-upload': 'yes_hf'}
FLAG = {'yes_push': '--yes-push', 'yes_hf': '--yes-hf'}
ORDER = ['preflight', 'rebuild', 'validate', 'regression', 'reader', 'release', 'notes', 'tree', 'export', 'export-push', 'hf-upload', 'handoff']
SITE_ORDER = ORDER[:7] + ['handoff']


class Ctx:
    def __init__(self, a):
        self.a = a
        self.tag = a.tag or 'release-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path(P.SCRATCH) / self.tag
        self.release_id = a.release_id
        self.state = {}
        self.env = dict(os.environ, TAG=self.tag)
        if a.schools:
            self.env['SCHOOLS'] = a.schools
        if a.allow_swings:
            self.env['ALLOW_SWINGS'] = '1'
        self.export_dir = Path(a.export_dir or P.EXPORT)


def stages(stage_list):
    return lambda c: (REBUILD, dict(c.env, STAGES=stage_list))


def exact_release(c):
    if not c.release_id:
        raise ValueError('No frozen release recorded; run the release step or pass --release-id ID')
    return c.release_id


def cmd_for(step, c):
    """(argv, env) of a step, or a callable(c) -> (ok, message) for the steps done in-process."""
    if step == 'preflight':
        return preflight
    if step == 'rebuild':
        return stages('snapshot build ids copies ledger audits evidence tests')(c)
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
        return ([sys.executable, str(CODE / 'tools' / 'make_release.py')] + (['--allow-swings'] if c.a.allow_swings else []), c.env)
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
    return r.returncode == 0, f'exit {r.returncode}; log {log}' + (': ' + ' | '.join(tail) if r.returncode else '')


def main(argv=None, runner=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag'); ap.add_argument('--schools'); ap.add_argument('--export-dir')
    ap.add_argument('--target', choices=['all', 'site'], default='all')
    ap.add_argument('--release-id', help='Exact existing frozen release for downstream-only work')
    ap.add_argument('--from', dest='from_step', choices=ORDER); ap.add_argument('--only')
    ap.add_argument('--resume', action='store_true'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--yes-push', action='store_true'); ap.add_argument('--yes-hf', action='store_true'); ap.add_argument('--allow-swings', action='store_true')
    a = ap.parse_args(argv)
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
    c = Ctx(a)
    steps = order[order.index(a.from_step):] if a.from_step else list(order)
    if a.only:
        steps = [s for s in steps if s in a.only.split(',')]
    state_f = c.dir / 'run.json'
    state = json.loads(state_f.read_text()) if a.resume and state_f.exists() else {}
    context = dict(target=a.target, schools=a.schools, allow_swings=a.allow_swings,
                   export_dir=str(c.export_dir), commit=os.environ.get('CS_ATLAS_SNAPSHOT_COMMIT') or git('rev-parse', 'HEAD').stdout.strip())
    if a.resume:
        if not state or state.get('_context') != context:
            ap.error('Cannot resume missing/legacy state or changed source/options; inspect run.json and start a new tag')
        saved_id = state.get('_release_id')
        if a.release_id and saved_id and a.release_id != saved_id:
            ap.error('--release-id differs from this run')
        c.release_id = saved_id or a.release_id
        if state.get('preflight', {}).get('ok') and not a.dry_run:
            ok, message = preflight(c)
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
        try:
            ok, msg = run_step(s, c, runner)
        except (ValueError, OSError) as error:
            ok, msg = False, str(error)
        state['_release_id'] = c.release_id
        state[s] = dict(ok=ok, message=msg, seconds=round(time.time() - t0), at=datetime.datetime.now().isoformat(timespec='seconds'))
        temporary = state_f.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, indent=1))
        temporary.replace(state_f)
        print(f"{s:12} {'ok' if ok else 'FAILED'}  {msg}", flush=True)
        if not ok:
            return 1
    print('atlas release: all steps passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
