"""The known onboarding traps as checks (docs/LESSONS-CHECKLIST.md): each was hit by Michigan, UChicago or Georgia Tech and cost hours, and each
is cheap to detect before the stage that needs it. `stage_gate.py` adds `STAGE_TRAPS[n]` to the gate of stage n, and
`stage_gate.py <key> --traps` prints every check at once. A check returns a list of findings (empty = clear); none writes anything.

  charter      the charter names what later stages read: affiliation regex with cases, a [repository] name + pattern (the unavailability
               ledger's REPO tables crashed on a school with no entry), DBLP affiliation strings (L-01, L-27)
  collectors   every collector script resubmits itself: `--signal=B:USR1@N` and loop_job.sh (Georgia Tech friction 45; a collector without
               them ends at its limit and stays down)
  captures     the lab-page capture store the ledger and the labpages channel read exists (labpage-captures.sqlite or the audit's
               labpage-audit-captures.sqlite; UChicago friction 73, Georgia Tech 44)
  shared       an onboarding school has no section in a shared tracked file (census-overrides.json, the lab-page audit summary, the
               student audit): the release freeze refuses dirty tracked inputs (UChicago friction 30, 31, 42)
  ignored      no file in hierarchy/<key>/reviewed is git-ignored: a git-archive release silently loses it (UChicago friction 36, Georgia Tech 21)
  additions    the lab-page additions hold at least the rows the acceptance accepted: an audit run after wiring once overwrote them with 0
               rows (R13; UChicago friction 53, 69; Georgia Tech 36, 38, 41)
  reasons      `sources_exhausted` lab reasons rest on real search: 2+ sources each, boilerplate on at most a quarter of the PIs
  stale        a recorded stage-<n>-gate.json is not older than the reviewed inputs of its own stage (UChicago friction 72, Georgia Tech 22)
"""
import json
import re
import subprocess
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402

CODE = Path(__file__).resolve().parents[1]   # the running checkout or snapshot, never the data root


def _read(p, default=None):
    p = Path(p)
    try:
        return json.loads(p.read_text()) if p.exists() else default
    except ValueError:
        return default


def _onboarding(key):
    return S.get(key).get('status') == 'onboarding'


def charter_traps(key):
    cfg = S.get(key)
    if not _onboarding(key):
        return []   # a released charter predates [repository]; the tables in the ledger still serve it
    out = []
    rx = S.field(cfg, 'affiliation.regex', '')
    if not rx:
        out.append('charter: [affiliation].regex is empty (the sweep, page-1 reader, periods and accuracy sample all read it)')
    for f in ('must_match', 'must_not_match'):
        if rx and not S.field(cfg, f'affiliation.{f}', []):
            out.append(f'charter: [affiliation].{f} has no cases (test the regex against DBLP notes and campus/medical names too)')
    if not S.field(cfg, 'affiliation.loose', ''):
        out.append('charter: [affiliation].loose is empty (page-1 text reader)')
    if not S.field(cfg, 'dblp.affiliation_strings', []):
        out.append('charter: [dblp].affiliation_strings is empty (tools/dblp_affiliated.py finds nobody)')
    repo = S.field(cfg, 'repository', {}) or {}
    if not repo.get('name'):
        out.append('charter: [repository].name is empty (the unavailability ledger names the school repository; fulltext-push/unavailable_ledger.py)')
    pat = repo.get('pattern', '')
    if not pat:
        out.append('charter: [repository].pattern is empty (regex over repository hosts; without it the ledger cannot tell repository records)')
    else:
        try:
            re.compile(pat)
        except re.error as e:
            out.append(f'charter: [repository].pattern does not compile: {e}')
    if not S.field(cfg, 'thesis.kind', ''):
        out.append('charter: [thesis].kind is empty (stage 6 source 1: write none and the reason if the repository is closed)')
    return out


def collector_traps(root=None):
    """Every collector script restarts itself near its time limit."""
    d = Path(root or CODE) / 'fulltext-push'
    out = []
    for f in sorted(list(d.glob('*collector*.slurm')) + list(d.glob('downloads.slurm'))):
        t = f.read_text()
        if '--signal=B:USR1' not in t:
            out.append(f'collector: {f.name} has no `#SBATCH --signal=B:USR1@900`; it ends at its limit and stays down')
        if 'loop_job.sh' not in t:
            out.append(f'collector: {f.name} does not source fulltext-push/loop_job.sh (run_restartable resubmits it)')
    return out


def captures_traps(key):
    if any(Path(P.data(n, key)).exists() for n in ('labpage-captures.sqlite', 'labpage-audit-captures.sqlite')):
        return []
    return [f'captures: neither raw/labpage-captures.sqlite nor raw/labpage-audit-captures.sqlite exists for {key} '
            '(run `tools/labpage_audit.py discover` first; the ledger and the labpages channel read it)']


SHARED_FILES = ('census-overrides.json', 'labpage-audit-summary.json', 'student-audit.json')


def shared_traps(key, files=None):
    """An onboarding school never writes into a shared tracked file; its sections live in school-local files."""
    if not _onboarding(key):
        return []
    out = []
    for name in SHARED_FILES:
        p = Path(files[name]) if files and name in files else Path(P.data(name))
        d = _read(p)
        if not isinstance(d, dict):
            continue
        hit = key in d or key in (d.get('schools') or {}) or key in (d.get('by_school') or {})
        if hit:
            out.append(f'shared: {p.name} holds a section for the onboarding school {key} (restore it from git; use the school-local file: '
                       'census-overrides-school.json, labpage-audit-summary-school.json, student-audit-school.json)')
    return out


# reviewed/ files a step regenerates from raw captures, or that no build reads: ignored on purpose (tests/test_gitignore_reviewed_inputs.py)
IGNORED_ON_PURPOSE = {'labpage-evidence.json', 'directory-evidence.json', 'profile-year-evidence.json', 'defense-evidence.json',
                      'cs-related-home-departments.json', 'few-students-input.json', 'gap-input.json', 'labpage-input.json', 'departures-20261031.json'}


def ignored_traps(key, repo=None, reviewed=None):
    """Files in hierarchy/<key>/reviewed that git ignores (the repo is the running checkout)."""
    repo = Path(repo or CODE)
    rd = Path(reviewed) if reviewed else P.school_part(key, 'reviewed')
    if not rd.is_dir():
        return []
    names = sorted(f.name for f in rd.iterdir() if f.is_file() and f.name not in IGNORED_ON_PURPOSE)
    if not names:
        return []
    rels = [P.reviewed_rel(key, n) for n in names]
    r = subprocess.run(['git', '-C', str(repo), 'check-ignore', '--stdin'], input='\n'.join(rels), capture_output=True, text=True)
    if r.returncode not in (0, 1):
        return []   # not a git checkout (a snapshot): nothing to check
    return [f'ignored: {rel} is git-ignored; whitelist it in .gitignore (`git check-ignore -v {rel}`), or a git-archive release loses it'
            for rel in r.stdout.split('\n') if rel]


def additions_traps(key, additions=None, acceptance=None):
    acc = _read(acceptance or P.data('labpage-acceptance.json', key))
    if not acc:
        return []
    add = _read(additions or P.data('labpage-additions.json', key)) or {}
    out = []
    for part in ('students', 'papers'):
        a = acc.get(part) or {}
        n = (a.get('counts') or {}).get('proposed')
        if a.get('accepted') and n and len(add.get(part) or []) < n:
            out.append(f"additions: labpage-additions.json holds {len(add.get(part) or [])} {part}, the acceptance accepted {n} "
                       "(an audit run after wiring overwrote them? restore the accepted file from git, then restamp; R13)")
    return out


BOILERPLATE = 'No student of this PI in any allowed source checked'   # tools/lab_coverage_reasons.py writes this for every lab left open
WEAK_SHARE = 0.25


def reasons_traps(key, reasons=None, n_pis=None):
    """The owner rejects `sources_exhausted` without real search effort (Georgia Tech: 312 of 447 labs passed stage 6 on the tool's boilerplate reason).
    A reason with fewer than 2 sources checked, or boilerplate reasons on more than a quarter of the PIs, is a finding: run the researched pass first."""
    rs = _read(reasons or P.data('lab-coverage-reasons.json', key))
    if not isinstance(rs, dict):
        return []
    if n_pis is None:
        import stage_gate as G
        n_pis = len(G.pis_of(key))
    out, boiler = [], 0
    for pi, e in rs.items():
        s = (e or {}).get('students') if isinstance(e, dict) else None
        if not s or s.get('code') != 'sources_exhausted':
            continue
        if len(s.get('sources_checked') or []) < 2:
            out.append(f'reasons: {pi}: sources_exhausted names fewer than 2 sources checked')
        boiler += str(s.get('why') or '').startswith(BOILERPLATE)
    if n_pis and boiler / n_pis > WEAK_SHARE:
        out.append(f'reasons: {boiler} of {n_pis} PIs rest on the tool-written boilerplate `sources_exhausted` reason (> {WEAK_SHARE:.0%}); '
                   'do the researched few-students pass (CVs, group pages, rosters) or have the owner waive stage 6 in gate-exceptions.json')
    return out


# the reviewed or built inputs of each stage (data names; an unknown name is skipped)
STAGE_INPUTS = {2: ['cs-related-review.json', 'census-additions.json', 'cs-related-hand.json'], 3: ['home-departments-school.json'],
                4: ['faculty-periods.json', 'census-overrides-school.json'], 5: ['openalex-identity-review.json', 'census-overrides-school.json'],
                6: ['labpage-acceptance.json', 'labpage-additions.json', 'student-decisions.json'],
                7: ['labpage-acceptance.json', 'labpage-additions.json', 'lab-coverage-reasons.json'], 8: ['copies.json']}


def stale_traps(key, reports=None, inputs=None):
    rep = Path(reports) if reports else P.school_part(key, 'reports')
    out = []
    for n, names in STAGE_INPUTS.items():
        g = rep / f'stage-{n}-gate.json'
        if not g.exists():
            continue
        paths = []
        for name in names:
            try:
                p = Path(inputs[name]) if inputs and name in inputs else Path(P.data(name, key))
            except (KeyError, ValueError):
                continue
            if p.exists():
                paths.append(p)
        newest = max(paths, key=lambda p: p.stat().st_mtime, default=None)
        if newest is not None and newest.stat().st_mtime > g.stat().st_mtime + 1:
            out.append(f'stale: {g.name} is older than {newest.name}; the recorded gate no longer describes the data '
                       f'(`atlas stage-gate {key} {n} --record` re-evaluates and records it)')
    return out


# which checks run with which stage gate (stage -> check names); `--traps` runs all
STAGE_TRAPS = {0: ('charter',), 3: ('shared', 'ignored'), 4: ('ignored',), 5: ('ignored',), 6: ('shared', 'ignored', 'additions', 'reasons'),
               7: ('shared', 'ignored', 'additions'), 8: ('collectors', 'captures'), 9: ('stale', 'additions'), 10: ('shared', 'ignored', 'additions', 'stale')}
CHECKS = dict(charter=charter_traps, collectors=lambda key: collector_traps(), captures=captures_traps, shared=shared_traps, ignored=ignored_traps,
              additions=additions_traps, stale=stale_traps, reasons=reasons_traps)


# the first stage whose work a check can demand (`stage-gate <key> <n> --traps` runs the checks of stages <= n only; with no stage, all).
# captures: the lab-page capture store is created by stage 3's labpage-discover step, so a stage-0 school cannot have it yet.
CHECK_FROM = dict(charter=0, collectors=0, shared=3, ignored=3, captures=3, stale=2, additions=6, reasons=6)


def checks_upto(stage=None):
    """Names of the checks that apply at `stage` (every one when None)."""
    return [n for n in CHECKS if stage is None or CHECK_FROM[n] <= int(stage)]


def run(key, names):
    out = []
    for n in names:
        out += CHECKS[n](key)
    return out


def for_stage(key, stage):
    return run(key, STAGE_TRAPS.get(int(stage), ()))
