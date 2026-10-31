"""One immutable, dated release per successful build (2026-10-29).

  /n/fs/resemble/homogenizing-science/releases/<YYYY-MM-DD>[.N]/       (atlas_paths.RELEASES; .2, .3 ... for later builds that day)
    hierarchy/<school>/{pis.json, students.json, report.json, lab_papers.jsonl.gz, student_papers.jsonl.gz, copies.json,
                        link-diagnosis.json, unavailable.jsonl.gz, unavailable-summary.json}
                                                                    the built packages, their audit outputs and the
                                                                    unavailability ledger (docs/UNAVAILABLE.md) when present
    hierarchy/..., census/..., periods/...                          the reviewed inputs (every JSON/CSV input tracked in
                                                                    the code repository, at the paths it has there)
    hierarchy/{home-departments.json, zero-paper-labs.json, ...}    what the site builder and the export read
    hierarchy/{CHAIN-AUDIT.md, chain-audit.json, student-audit.json, BUILD-REGRESSION.md, BUILD-REGRESSION.json}
    docs/RULES.md                                                   the rules this build applied
    MANIFEST.json      sha256 and bytes per file, the code commit, rule ids, counts per school, build and audit times,
                       upstream versions (OpenAlex sweep dates, the DBLP dump, the site collections), tests, regression,
                       and per school the ledger's built_at, papers and counts by reason_code (`ledger`; null without one)
  Files and directories are made read-only; releases/latest points at the newest. An existing release is never
  overwritten: the next free .N is taken. Consumers (tools/organize_tree.py, tools/export_release.py, the site, the
  Hugging Face upload) read a release, never the working packages.

Refuses when: a school's package is missing, has no complete provenance block (report.json -> provenance, written by
tools/pi_hierarchy.py through tools/provenance.py; 2026-10-29), or was rewritten while copying, the tests fail, the code
has uncommitted changes to tracked build files (--allow-dirty records it instead; collectors' files are recorded only), or the regression check is older than the packages or
flagged swings (--allow-swings records them instead).

usage: make_release.py [--before counts.json] [--allow-dirty] [--allow-swings] [--dry-run]
       make_release.py add-note <release id> <SITE-HANDOFF.md|HF-UPLOAD.json> <file>   (add one note file, never a manifest file)
"""
import argparse, gzip, hashlib, json, os, re, shutil, sqlite3, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
import provenance  # noqa: E402  (report.json -> provenance, required)

PACKAGE = ['pis.json', 'students.json', 'report.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'copies.json']
SCHOOL_EXTRA = ['link-diagnosis.json',  # audit output per school (the reviewed per-school inputs come from git)
                'unavailable.jsonl.gz', 'unavailable-summary.json']  # the unavailability ledger (docs/UNAVAILABLE.md; 2026-10-30)
TOP = ['home-departments.json', 'zero-paper-labs.json', 'school-profiles.json', 'SCHOOL-PROFILES.md', 'missing-papers-audit.json',
       'CHAIN-AUDIT.md', 'chain-audit.json', 'student-audit.json', 'BUILD-REGRESSION.md', 'BUILD-REGRESSION.json',
       'EVIDENCE-CHECK.md', 'EVIDENCE-CHECK.json',
       # the atlas ids (tools/atlas_ids.py, docs/IDS.md): the registry travels with every release so an id is never reissued
       'ids/registry.sqlite', 'ids/crossref.tsv.gz', 'ids/redirects.tsv', 'ids/persons-cross-school.json', 'ids/IDS-REPORT.json']
NOTES = {'SITE-HANDOFF.md', 'HF-UPLOAD.json'}
COUNT_KEYS = ['pis', 'lab_papers', 'students', 'lab_student_pairs', 'student_paper_links', 'pis_with_lab_papers', 'pis_with_students',
              'pis_complete_chain', 'labs_with_student_papers', 'lab_papers_by_period', 'lab_papers_by_listing']


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def git(*a):
    return subprocess.run(['git', '-C', str(P.WORK), *a], capture_output=True, text=True, check=True).stdout


def tracked_inputs():
    """The reviewed inputs: every tracked JSON/CSV file outside tests/ (the .gitignore whitelist names them)."""
    return provenance.tracked_inputs()  # the accuracy sample (accuracy/) is a measurement, not an input


def code_state():
    """(HEAD, uncommitted tracked build paths, uncommitted tracked paths outside the build). The collectors (fulltext-push/)
    and the AI-writing study (ai-writing/) are not build inputs (tools/provenance.py NOT_BUILD); other agents edit them
    while builds run, so their changes are recorded, not refused."""
    st = provenance.code_state()
    return st['commit'], st['dirty_paths'], st['other_dirty_paths']


def run_tests():
    env = dict(os.environ)  # the interpreter running the release (env/atlas needs no LD_LIBRARY_PATH; py310 does)
    if Path(sys.executable).resolve() == Path(P.ENV_PY).resolve():
        env['LD_LIBRARY_PATH'] = f"{P.ENV_LIB}:{os.environ.get('LD_LIBRARY_PATH', '')}".rstrip(':')
    r = subprocess.run([sys.executable, '-m', 'pytest', str(P.TESTS), '-q', '-p', 'no:cacheprovider'], cwd=P.WORK, env=env,
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.strip().split('\n') if l.strip()]
    return r.returncode == 0, (lines[-1] if lines else r.stderr.strip()[-300:])


def upstream():
    out = dict(openalex_sweeps={}, dblp_dump=None, site_collections={})
    for s in P.SCHOOL_IDS:
        db = P.HIERARCHY / s / 'openalex-sweep.sqlite'
        if db.exists():
            c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=60)
            lo, hi, pages, works = c.execute('select min(fetched_at), max(fetched_at), count(*), sum(n) from pages').fetchone()
            out['openalex_sweeps'][s] = dict(first_fetched=lo, last_fetched=hi, pages=pages, works=works)
            c.close()
        coll = P.HIERARCHY / s / 'collection.json.gz'
        coll = coll if coll.exists() else P.SITE_DATA / f'collection-{s}.json.gz'
        if coll.exists():
            st = coll.stat()
            out['site_collections'][s] = dict(path=str(coll), bytes=st.st_size, mtime=datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat())
    md5 = P.DBLP_DUMP / (P.DBLP_DUMP_FILE + '.md5')
    m = re.search(r'(\d{4}-\d{2}-\d{2})', P.DBLP_DUMP_FILE)
    out['dblp_dump'] = dict(file=str(P.DBLP_DUMP_XML), date=m.group(1) if m else None,
                            md5=md5.read_text().split()[0] if md5.exists() else None,
                            persons_extract=str(P.HIERARCHY / 'dblp-dump-persons.json.gz'))
    return out


def rule_ids():
    rp = P.WORK / 'docs/RULES.md'
    return re.findall(r'^### (R-[A-Z]+-\d+[a-z]?) \(([^)]*)\)', rp.read_text(), re.M) if rp.exists() else []


def ledger_counts(d):
    """The unavailability ledger of one school directory (docs/UNAVAILABLE.md): {built_at, papers, by_reason} from
    unavailable-summary.json, by_reason recounted from unavailable.jsonl.gz when the summary lacks it; None without a ledger."""
    d = Path(d); sm = d / 'unavailable-summary.json'; lg = d / 'unavailable.jsonl.gz'
    if not sm.exists() and not lg.exists():
        return None
    summ = json.loads(sm.read_text()) if sm.exists() else {}
    by = summ.get('by_reason')
    if by is None and lg.exists():
        by = {}
        with gzip.open(lg, 'rt') as f:
            for l in f:
                if l.strip():
                    c = json.loads(l).get('reason_code'); by[c] = by.get(c, 0) + 1
    by = dict(sorted((by or {}).items()))
    return dict(built_at=summ.get('built_at'), papers=summ.get('papers', sum(by.values())), by_reason=by,
                final=summ.get('final'), not_final=summ.get('not_final'))


def next_id(day):
    i, rid = 1, day
    while (P.RELEASES / rid).exists() or any(P.RELEASES.glob(f'.tmp-{rid}-*')):
        i += 1; rid = f'{day}.{i}'
    return rid


def lock(d):
    for root, dirs, files in os.walk(d, topdown=False):
        for f in files:
            p = os.path.join(root, f); os.chmod(p, os.stat(p).st_mode & ~0o222)
        os.chmod(root, os.stat(root).st_mode & ~0o222)


def point_latest(rid):
    tmp = P.RELEASES / f'.latest-{os.getpid()}'
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    os.symlink(rid, tmp)
    os.replace(tmp, P.RELEASES / 'latest')


def make(a):
    head, dirty, other_dirty = code_state()
    if dirty and not a.allow_dirty:
        raise SystemExit(f'uncommitted changes to tracked files (commit first, or --allow-dirty): {dirty[:10]}')
    ok, tests = run_tests()
    if not ok:
        raise SystemExit(f'tests failed: {tests}')
    built, prov = {}, {}
    for s in P.SCHOOL_IDS:
        for f in PACKAGE:
            if not (P.HIERARCHY / s / f).exists():
                raise SystemExit(f'missing package file hierarchy/{s}/{f}')
        rep_ = json.loads((P.HIERARCHY / s / 'report.json').read_text())
        built[s] = rep_.get('builtAt')
        miss = provenance.missing(rep_.get('provenance'))  # (2026-10-29, owner) provenance is required
        if miss:
            raise SystemExit(f'hierarchy/{s}/report.json: provenance missing or incomplete ({", ".join(miss)}); rebuild with tools/pi_hierarchy.py')
        prov[s] = rep_['provenance']
        pis_ = json.loads((P.HIERARCHY / s / 'pis.json').read_text())  # every package carries the atlas ids (2026-10-29)
        if not all(str(p.get('atlasId', '')).startswith('atl:p:') and str(p.get('labId', '')).startswith('atl:l:') for p in pis_):
            raise SystemExit(f'hierarchy/{s}/pis.json: atlas ids missing; run tools/atlas_ids.py (rebuild stage ids)')
    newest = max(datetime.fromisoformat(b.rstrip('Z')).replace(tzinfo=timezone.utc).timestamp() for b in built.values())
    reg_p = P.HIERARCHY / 'BUILD-REGRESSION.json'
    reg = json.loads(reg_p.read_text()) if reg_p.exists() else None
    if not reg or reg_p.stat().st_mtime < newest:
        if not a.allow_swings:
            raise SystemExit('hierarchy/BUILD-REGRESSION.json is missing or older than the packages: run tools/build_regression.py check')
    elif reg['flags'] and not a.allow_swings:
        raise SystemExit(f"{len(reg['flags'])} regression flags (hierarchy/BUILD-REGRESSION.md); --allow-swings releases anyway")
    ev_p = P.HIERARCHY / 'EVIDENCE-CHECK.json'  # the build-time evidence check (tools/evidence_check.py) must have passed
    ev = json.loads(ev_p.read_text()) if ev_p.exists() else None
    if not ev or ev_p.stat().st_mtime < newest or ev.get('mode') != 'strict' or not ev.get('ok'):
        raise SystemExit('hierarchy/EVIDENCE-CHECK.json is missing, older than the packages, not strict, or failed: run tools/evidence_check.py')
    files = [f'hierarchy/{s}/{f}' for s in P.SCHOOL_IDS for f in PACKAGE + SCHOOL_EXTRA if (P.HIERARCHY / s / f).exists()]
    files += [f'hierarchy/{f}' for f in TOP if (P.HIERARCHY / f).exists()]
    files += [f for f in tracked_inputs() if (P.WORK / f).exists()]
    files += ['docs/RULES.md']
    files = sorted(dict.fromkeys(files))
    day = datetime.now().strftime('%Y-%m-%d')
    P.RELEASES.mkdir(parents=True, exist_ok=True)
    rid = a.id or next_id(day)
    if (P.RELEASES / rid).exists():
        raise SystemExit(f'release {rid} exists; releases are never overwritten')
    if a.dry_run:
        print(json.dumps(dict(release=rid, files=len(files), code=head, dirty=dirty, tests=tests), indent=1)); return
    tmp = P.RELEASES / f'.tmp-{rid}-{os.getpid()}'
    entries = {}
    for f in files:
        src, dst = P.WORK / f, tmp / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        entries[f] = dict(bytes=dst.stat().st_size, sha256=sha256(dst))
    for s in P.SCHOOL_IDS:  # the package must not have been rebuilt while it was copied
        now = json.loads((P.HIERARCHY / s / 'report.json').read_text()).get('builtAt')
        if now != built[s] or sha256(P.HIERARCHY / s / 'lab_papers.jsonl.gz') != entries[f'hierarchy/{s}/lab_papers.jsonl.gz']['sha256']:
            shutil.rmtree(tmp)
            raise SystemExit(f'{s}: package rewritten while copying; rerun')
    counts = {}
    for s in P.SCHOOL_IDS:
        rep = json.loads((tmp / 'hierarchy' / s / 'report.json').read_text())
        c = rep.get('counts') or {}
        counts[s] = dict(builtAt=rep.get('builtAt'), **{k: c.get(k) for k in COUNT_KEYS})
    chain = json.loads((tmp / 'hierarchy/chain-audit.json').read_text()) if (tmp / 'hierarchy/chain-audit.json').exists() else {}
    man = dict(release=rid, created=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               code=dict(repository=str(P.WORK), commit=head, uncommitted_tracked_changes=dirty, uncommitted_outside_build=other_dirty,
                         built_from={s: dict(commit=v['code'].get('commit'), dirty=v['code'].get('dirty'), diff_sha256=v['code'].get('diff_sha256'))
                                     for s, v in prov.items()}),
               provenance={s: {k: v[k] for k in ('openalex_sweep', 'dblp_dump', 'dblp_persons', 'pi_works')} for s, v in prov.items()},
               evidence_check=(json.loads((P.HIERARCHY / 'EVIDENCE-CHECK.json').read_text()).get('ok') if (P.HIERARCHY / 'EVIDENCE-CHECK.json').exists() else None),
               rules=[dict(id=i, decided=d) for i, d in rule_ids()], rules_doc='docs/RULES.md',
               build=dict(packages_built=built, chain_audit_at=chain.get('at'),
                          chain_audit_open={x['school']: {c: x['checks'][c]['n_unexplained'] for c in x['checks']} for x in chain.get('schools', [])},
                          tests=tests,
                          regression=dict(at=(reg or {}).get('after', {}).get('at'), flags=len((reg or {}).get('flags') or []),
                                          before=(reg or {}).get('before'), allowed=bool(a.allow_swings),
                                          identical_to_before={s: r.get('identical') for s, r in ((reg or {}).get('schools') or {}).items()})),
               counts=counts, upstream=upstream(),
               ledger={s: ledger_counts(tmp / 'hierarchy' / s) for s in P.SCHOOL_IDS},  # docs/UNAVAILABLE.md (2026-10-30)
               ids=({k: v for k, v in json.loads((tmp / 'hierarchy/ids/IDS-REPORT.json').read_text()).items() if k != 'conflicts'}
                    if (tmp / 'hierarchy/ids/IDS-REPORT.json').exists() else None),  # tools/atlas_ids.py, docs/IDS.md
               layout='paths mirror the working root (hierarchy/, census/, periods/, docs/); hierarchy/<school>/ holds the packages',
               files=entries)
    (tmp / 'MANIFEST.json').write_text(json.dumps(man, indent=1, ensure_ascii=False) + '\n')
    lock(tmp)
    os.chmod(tmp, os.stat(tmp).st_mode | 0o200)  # the rename needs the directory itself, briefly
    os.rename(tmp, P.RELEASES / rid)
    os.chmod(P.RELEASES / rid, os.stat(P.RELEASES / rid).st_mode & ~0o222)
    point_latest(rid)
    print(json.dumps(dict(release=rid, dir=str(P.RELEASES / rid), files=len(entries), bytes=sum(e['bytes'] for e in entries.values()),
                          code=head, tests=tests, regression_flags=man['build']['regression']['flags'])))


def add_note(rid, name, src):
    d = P.RELEASES / rid
    if name not in NOTES:
        raise SystemExit(f'only {sorted(NOTES)} can be added to a release')
    if not (d / 'MANIFEST.json').exists():
        raise SystemExit(f'no release {rid}')
    if name in json.loads((d / 'MANIFEST.json').read_text())['files']:
        raise SystemExit(f'{name} is a manifest file')
    mode = os.stat(d).st_mode
    os.chmod(d, mode | 0o200)
    try:
        tmp = d / f'.{name}.part'
        shutil.copyfile(src, tmp)
        os.chmod(tmp, 0o444)
        os.replace(tmp, d / name)
    finally:
        os.chmod(d, mode)
    print(f'added {name} to {d}')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['add-note']:
        if len(argv) != 4:
            raise SystemExit(__doc__)
        return add_note(*argv[1:])
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', help='the snapshot the regression compared against (recorded only)')
    ap.add_argument('--allow-dirty', action='store_true')
    ap.add_argument('--allow-swings', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--id', help=argparse.SUPPRESS)  # tests only
    make(ap.parse_args(argv))


if __name__ == '__main__':
    main()
