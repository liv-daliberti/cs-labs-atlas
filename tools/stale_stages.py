"""Rebuild only what changed (ROADMAP #33): which rebuild stages are stale, from the inputs and outputs the stages declare.

Each stage names its INPUTS (DATA_FILES names of kind raw and reviewed, other stages' outputs, a store's catalog, and the git files of its
code) and its OUTPUTS (DATA_FILES names). A stage is STALE for a school when an output is missing, or the newest input is newer than the
oldest output, or a code file of the stage was committed after the oldest output. Stages fresh for every school are skipped.

  stale_stages.py [school ...] [--json]      per stage: stale schools and why
  stale_stages.py --stages [school ...]      the STAGES value for hierarchy/rebuild.sh (also: STAGES=auto hierarchy/rebuild.sh)

The always-run tail (audits, evidence, tests, regression, validate, release, tree, housekeeping) is never skipped: they are checks, not
products. snapshot comes first when anything is stale, because the regression compares against it. Limits (v1): modification times, not
content hashes; the per-school stages run for the union of stale schools; a code file is one named script, not its imports.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
ALWAYS = ['audits', 'evidence', 'tests', 'regression', 'validate', 'release', 'tree', 'housekeeping']
BUILD_OUT = ['pis.json', 'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'report.json']
# stage -> (scope, input DATA_FILES names | 'RAW_REVIEWED' | 'catalog', code files, output names)
STAGES = {
    'build':  ('school', ['RAW_REVIEWED'], ['tools/pi_hierarchy.py', 'tools/pihier'], BUILD_OUT),
    'ids':    ('once', [('build', BUILD_OUT)], ['tools/atlas_ids.py'], ['ids/registry.sqlite']),
    'copies': ('school', ['catalog', ('build', ['lab_papers.jsonl.gz'])], ['tools/lab_paper_copies.py'], ['copies.json']),
    'ledger': ('school', ['catalog', ('copies', ['copies.json'])], ['fulltext-push/unavailable_ledger.py'], ['unavailable.jsonl.gz', 'unavailable-summary.json']),
    'reader': ('once', [('copies', ['copies.json']), ('ledger', ['unavailable-summary.json'])], ['tools/reader_export.py', 'tools/reader_links.py'], ['reader-SUMMARY.json', 'reader-upload.tsv']),
}
ORDER = ['build', 'ids', 'copies', 'ledger', 'reader']


def mtime(p):
    try:
        return Path(p).stat().st_mtime
    except OSError:
        return None


def code_time(files):
    """Commit time of the newest commit that touched these files (0 when git cannot say)."""
    r = subprocess.run(['git', '-C', str(CODE), 'log', '-1', '--format=%ct', '--', *files], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def raw_reviewed_names():
    return [n for n, k, f, s in P.DATA_FILES if k in ('raw', 'reviewed') and '{school}' in f]


def input_paths(spec, school):
    out = []
    for item in spec:
        if item == 'RAW_REVIEWED':
            out += [P.data(n, school) for n in raw_reviewed_names()]
        elif item == 'catalog':
            out.append(P.store(school) / 'catalog.sqlite')
        elif isinstance(item, tuple):
            out += [data_path(n, school) for n in item[1]]
    return out


def data_path(name, school):
    """P.data for a DATA_FILES name, per school when its pattern has {school}; 'ids/registry.sqlite' is a file inside the 'ids' entry."""
    head, _, rest = name.partition('/')
    flat = {n: f for n, k, f, s in P.DATA_FILES}[head]
    p = P.data(head, school) if '{school}' in flat else P.data(head)
    return p / rest if rest else p


def output_paths(stage, school):
    return [data_path(n, school) for n in STAGES[stage][3]]


def check(stage, school, ctime=None):
    """-> (stale?, reason) for one stage and school."""
    scope, ins, code, _outs = STAGES[stage]
    outs = output_paths(stage, school)
    ot = [mtime(p) for p in outs]
    if any(t is None for t in ot):
        return True, 'an output is missing: ' + next(str(p.name) for p, t in zip(outs, ot) if t is None)
    oldest = min(ot)
    ts = [t for t in (mtime(p) for p in input_paths(ins, school)) if t is not None]
    if ts and max(ts) > oldest:
        return True, 'an input is newer than the oldest output'
    c = code_time(code) if ctime is None else ctime
    if c > oldest:
        return True, 'its code was committed after the oldest output'
    return False, 'fresh'


def plan(schools):
    res = {}
    for st in ORDER:
        scope = STAGES[st][0]
        if scope == 'once':
            stale, why = check(st, schools[0])
            res[st] = dict(stale=bool(stale), schools=list(schools) if stale else [], why={'*': why} if stale else {})
            continue
        bad = {s: check(st, s)[1] for s in schools if check(st, s)[0]}
        res[st] = dict(stale=bool(bad), schools=sorted(bad), why=bad)
    return res


def stage_list(res):
    """The STAGES value: a stale stage drags every later stage that reads its outputs; snapshot leads when anything runs."""
    chain, dirty = [], False
    for st in ORDER:
        dirty = dirty or res[st]['stale']
        if dirty:
            chain.append(st)
    return (['snapshot'] if chain else []) + chain + ([] if not chain else ALWAYS)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--stages', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    schools = a.schools or list(P.SCHOOL_IDS)
    res = plan(schools)
    if a.stages:
        print(' '.join(stage_list(res)))
    elif a.json:
        print(json.dumps(res, indent=1))
    else:
        for st in ORDER:
            r = res[st]
            print(f"{st:8} {'STALE ' + ','.join(r['schools']) if r['stale'] else 'fresh'}")
            for s, w in r['why'].items():
                print(f'           {s}: {w}')
        print('STAGES=' + ' '.join(stage_list(res)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
