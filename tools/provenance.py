"""Build provenance (2026-10-29, owner): what one school's package was built from, written by tools/pi_hierarchy.py into
report.json -> provenance, and required by tools/make_release.py.

  code              the git commit of the code repository, or dirty with the sha256 of `git diff HEAD` over the build's own
                    changed files (BUILD_CODE and every tracked JSON/CSV input); other tracked changes (collectors,
                    school-onboarding work of other agents) are listed apart as other_dirty_paths
  rules             the rule ids and dates of docs/RULES.md
  openalex_sweep    hierarchy/<school>/openalex-sweep.sqlite: first and last page fetch dates, pages, works, bytes, sha256
  dblp_dump         DBLP's monthly dump: file, date, md5 (the .md5 file DBLP publishes next to it)
  dblp_persons      hierarchy/dblp-dump-persons.json.gz: modified, bytes, sha256, the dump it was read from
  pi_works          hierarchy/<school>/pi-works.sqlite: modified, bytes, sha256, works, page-1 reads and the last read
  reviewed_inputs   every tracked JSON/CSV input (docs/REVIEWED-INPUTS.md): path -> sha256
  inputs            the untracked inputs of this school the build reads (census, collection, listings, researched
                    evidence, recoveries): path -> {bytes, modified, sha256}

usage (a check): provenance.py <school>     prints the block the builder would write
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)

REQUIRED = ('code', 'rules', 'openalex_sweep', 'dblp_dump', 'dblp_persons', 'pi_works', 'reviewed_inputs')
# the build's own code and inputs: the builder and what it imports, the audits, the evidence check, the copies counter, the
# regression check, the release and tree tools, the rebuild script, the rules, the tests and every tracked JSON/CSV input.
# Other tracked files (the collectors in fulltext-push/, the AI-writing study, the school-onboarding tools and configs that
# other agents edit while builds run) are recorded as other_dirty_paths, never refused.
BUILD_CODE = ['tools/pi_hierarchy.py', 'tools/pihier/', 'schemas/', 'tools/schema_check.py', 'tools/validate.py', 'tools/atlas_paths.py', 'tools/provenance.py', 'tools/pi_fulltext_affiliation.py',
              'tools/student_audit.py', 'tools/chain_audit.py', 'tools/link_diagnosis.py', 'tools/evidence_check.py',
              'tools/lab_paper_copies.py', 'tools/build_regression.py', 'tools/make_release.py', 'tools/organize_tree.py',
              'tools/zero_paper_ledger.py', 'hierarchy/rebuild.sh', 'paths.sh', 'docs/RULES.md', 'docs/evidence-whitelist.json', 'tests/']
NOT_BUILD = ('fulltext-push/', 'ai-writing/')


def onboarding_schools():
    """Schools with a charter (schools/<key>.toml) that are not released yet (not in atlas_paths.SCHOOL_IDS): their inputs
    are not this build's and stay out of the release until the school is admitted."""
    d = getattr(P, 'SCHOOL_CONFIGS', P.WORK / 'schools')
    return {f.stem for f in Path(d).glob('*.toml')} - set(P.SCHOOL_IDS) - {'TEMPLATE'} if Path(d).is_dir() else set()


def of_onboarding_school(f, keys=None):
    keys = onboarding_schools() if keys is None else keys
    parts = f.split('/')
    return any(x in keys or x.split('-')[0] in keys for x in parts)


def is_build_path(f):
    return (any(f == b or (b.endswith('/') and f.startswith(b)) for b in BUILD_CODE)
            or (f.endswith(('.json', '.csv')) and not f.startswith(('tests/', 'accuracy/')) and not of_onboarding_school(f)))


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def _git(*a):
    return subprocess.run(['git', '-C', str(P.WORK), *a], capture_output=True, text=True, check=True).stdout


def _mtime(p):
    return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _file(p):
    p = Path(p)
    return dict(path=str(p), bytes=p.stat().st_size, modified=_mtime(p), sha256=sha256(p)) if p.exists() else None


def code_state():
    """{commit, dirty, diff_sha256?, dirty_paths, other_dirty_paths}: dirty means a tracked build path differs from HEAD."""
    head = _git('rev-parse', 'HEAD').strip()
    changed = [l[3:] for l in _git('status', '--porcelain', '--untracked-files=no').split('\n') if l.strip()]
    mine = [f for f in changed if is_build_path(f) and not f.startswith(NOT_BUILD)]
    snap = os.environ.get('CS_ATLAS_SNAPSHOT_COMMIT')  # a Slurm job running from a code snapshot (tools/job_code_snapshot.sh)
    out = dict(commit=snap or head, dirty=bool(mine), dirty_paths=mine, other_dirty_paths=[f for f in changed if f not in mine])
    if snap:
        out['snapshot'] = True
        if snap != head:
            out['live_head'] = head
    if mine:
        out['diff_sha256'] = hashlib.sha256(_git('diff', 'HEAD', '--', *mine).encode()).hexdigest()
    return out


def rule_ids():
    rp = P.WORK / 'docs/RULES.md'
    return [dict(id=i, decided=d) for i, d in re.findall(r'^### (R-[A-Z]+-\d+[a-z]?) \(([^)]*)\)', rp.read_text(), re.M)] if rp.exists() else []


def tracked_inputs():
    """The reviewed inputs: every tracked JSON/CSV file outside tests/, accuracy/ and schemas/ (the schemas are build code,
    BUILD_CODE; the .gitignore whitelist names the inputs)."""
    keys = onboarding_schools()
    return [f for f in _git('ls-files', '*.json', '*.csv').split('\n') if f and not f.startswith(('tests/', 'accuracy/', 'schemas/'))
            and not of_onboarding_school(f, keys)]


def openalex_sweep(school):
    db = P.data('openalex-sweep.sqlite', school)
    if not db.exists():
        return None
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=60)
    lo, hi, pages, works = c.execute('select min(fetched_at), max(fetched_at), count(*), sum(n) from pages').fetchone()
    c.close()
    return dict(_file(db), first_fetched=lo, last_fetched=hi, pages=pages, works=works)


def dblp_dump():
    md5 = P.DBLP_DUMP / (P.DBLP_DUMP_FILE + '.md5')
    m = re.search(r'(\d{4}-\d{2}-\d{2})', P.DBLP_DUMP_FILE)
    return dict(file=str(P.DBLP_DUMP_XML), date=m.group(1) if m else None, md5=md5.read_text().split()[0] if md5.exists() else None)


def pi_works(school):
    f = P.data('pi-works.sqlite', school)
    if not f.exists():
        return dict(path=str(f), present=False)
    out = _file(f)
    c = sqlite3.connect(f'file:{f}?mode=ro', uri=True, timeout=60)
    out.update(works=c.execute('select count(*) from works').fetchone()[0],
               page1_reads=c.execute('select count(*) from pages').fetchone()[0],
               page1_last_read=c.execute('select max(fetched_at) from pages').fetchone()[0])
    c.close()
    return out


def school_inputs(school):
    D = lambda name: P.data(name, school)  # noqa: E731  (atlas_paths.DATA_FILES)
    cands = [D('census-faculty-hierarchy.json'), D('census-faculty.json'), D('collection.json.gz'),
             P.SITE_DATA / f'collection-{school}.json.gz', D('listings.json'), D('thesis-evidence.json'),
             D('labpage-evidence.json'), D('thesis-held-years-evidence.json'), D('dblp-recovered.jsonl.gz'),
             D('labpage-recovered.jsonl.gz'), D('pi-publication-lists.json'), D('labpage-pubs.jsonl.gz'), D('dblp_pubs.json.gz')]
    out = {}
    for p in cands:
        if p.exists():
            f = _file(p); out[str(p)] = dict(bytes=f['bytes'], modified=f['modified'], sha256=f['sha256'])
    return out


def block(school):
    dp = P.data('dblp-dump-persons.json.gz')
    persons = _file(dp)
    if persons:
        persons['dump'] = P.DBLP_DUMP_FILE
    return dict(at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), code=code_state(), rules=rule_ids(),
                openalex_sweep=openalex_sweep(school), dblp_dump=dblp_dump(), dblp_persons=persons, pi_works=pi_works(school),
                reviewed_inputs={f: sha256(P.WORK / f) for f in tracked_inputs() if (P.WORK / f).exists()},
                inputs=school_inputs(school))


def missing(prov):
    """The required provenance fields a report lacks (empty when complete)."""
    if not isinstance(prov, dict):
        return list(REQUIRED)
    out = [k for k in REQUIRED if not prov.get(k)]
    code = prov.get('code') or {}
    if code and not code.get('commit'):
        out.append('code.commit')
    if code.get('dirty') and not code.get('diff_sha256'):
        out.append('code.diff_sha256')
    sw = prov.get('openalex_sweep') or {}
    if sw and not (sw.get('sha256') and sw.get('last_fetched')):
        out.append('openalex_sweep.sha256/last_fetched')
    dd = prov.get('dblp_dump') or {}
    if dd and not (dd.get('date') and dd.get('md5')):
        out.append('dblp_dump.date/md5')
    for k in ('dblp_persons', 'pi_works'):
        v = prov.get(k) or {}
        if v and v.get('present', True) and not (v.get('sha256') and v.get('modified')):
            out.append(k + '.sha256/modified')
    return out


if __name__ == '__main__':
    print(json.dumps(block(sys.argv[1]), indent=1))
