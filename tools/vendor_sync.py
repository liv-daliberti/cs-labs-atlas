"""Code the pipeline used to call in old working folders, copied into vendor/ (2026-10-30). Code only, never data.

Each vendored file is the original byte for byte, plus
  - one provenance header line (source path and sha256), and
  - the rewrites below, which repoint *code* locations (sys.path entries, the collector's scripts directory) to
    vendor/, and
  - every absolute *data* path routed through tools/atlas_paths.py (tools/route_paths.py), which gives the same directory
    under today's layout and follows the project move (a stage's STAGE / ROOT, which the original computed from its own
    location, becomes the slot that directory now has: archive_sweep(<stage>), WORLD_ATLAS, HOMOGENIZATION_STUDY).
vendor/PROVENANCE.tsv records, per file: the vendored path, the source path, the source sha256, the vendored sha256
and the rewrites applied.

usage: vendor_sync.py check     vendored files match PROVENANCE.tsv (no unrecorded edits), and report every source
                                 whose sha256 changed since it was vendored (drift: re-sync before switching over)
       vendor_sync.py sync      copy every source again and re-apply the rewrites (after drift, or to add a file)
       vendor_sync.py list      the sources and their status
Exit status 1 when check finds a mismatch (drift alone is reported and exits 0 unless --strict).
Once the download loops run on vendor/ and the originals are retired, vendor/ is the only copy: edit it directly and
drop the file's entry here (see vendor/README.md).
"""
import argparse, hashlib, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_paths  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
VENDOR = REPO / 'vendor'  # this checkout's vendor/ (atlas_paths.VENDOR, the one the scripts run, is <WORK>/vendor)
SW = '/n/fs/resemble/maxent-grpo/.research-sweeps'
HS = '/n/fs/resemble/homogenizing-science'
DATE = '2026-10-30'

# vendored directory -> (source directory, data root the stage's code computed from its own location, files)
ORIGINS = {
    'homogenizing_scripts': (f'{HS}/scripts', HS, [
        # the full-text collector (run through cmu_tools/collector_wrapper.py) and its imports
        'collect_princeton_fulltext_expanded.py', 'collect_princeton_fulltext.py', 'discover_princeton_fulltext.py',
        # imported by princeton_tools/cs_pi_works.py (publications) and its closure
        'publications.py', 'common.py', 'arxiv_identifiers.py', 'author_name_matching.py', 'bibliography_anchor.py',
        'dblp_identity_bridge.py', 'epfl_infoscience.py', 'epfl_infoscience_review.py', 'reviewed_arxiv_pi_identity.py',
        'reviewed_arxiv_relations.py', 'reviewed_hzau_owner_profile.py', 'reviewed_image_leadership.py',
        'reviewed_lab_arxiv.py', 'reviewed_lab_citations.py', 'reviewed_owner_bibliography.py',
        'reviewed_rail_bibliography.py', 'reviewed_wallraven_profile.py', 'source_decoding.py', 'sweep10_lib.py',
        'unipapers_lib.py']),
    'cmu_tools': (f'{SW}/claude-cmu-20261017/tools', f'{SW}/claude-cmu-20261017', [
        'collector_wrapper.py', 'arxiv_bulk.py', 'arxiv_oai.py', 'core_search.py', 's2_key_lookup.py',
        'europepmc_lookup.py']),
    'princeton_tools': (f'{SW}/claude-princeton-20261015/tools', f'{SW}/claude-princeton-20261015', [
        'import_all_when_free.py', 'import_when_free.py', 'cs_pi_works.py', 'cs_complete.py', 'cs_open_copies.py',
        'cs_structure_catalog.py', 'catalog_snapshot.py', 'cs_nsf_par.py', 'oar_index.py']),
    'homogenization_tools': (f'{SW}/claude-homogenization-20261019/tools', f'{SW}/claude-homogenization-20261019', [
        'fulltext_store.py', 'homog.py', 'study_copies.py']),
    'epfl_tools': (f'{SW}/claude-epfl-20261019/tools', f'{SW}/claude-epfl-20261019', ['epfl_infoscience_rest.py']),
    'mit_tools': (f'{SW}/claude-mit-20261020/tools', f'{SW}/claude-mit-20261020', ['mit_dspace_rest.py']),
    'site_builder': ('/n/fs/resemble/maxent-grpo/princeton-live-20261015/scripts', '/n/fs/resemble/maxent-grpo/princeton-live-20261015',
                     ['build-cs-hierarchy.py']),  # imported by tools/school_profiles.py and tools/export_release.py
    'princeton_listings': (f'{SW}/claude-princeton-listings-20261022/scripts', f'{SW}/claude-princeton-listings-20261022',
                           ['extract.py', 'match.py']),  # tools/listed_not_in_census.py, tools/princeton_census.py
}

OWN = 'str(Path(__file__).resolve().parent)'


def sib(d):
    return f"Path(__file__).resolve().parents[1] / '{d}'"


# (vendored directory or '*', file or '*', old, new): every rule must match at least once in each file it names
# explicitly; '*' rules apply wherever they match. Only code locations change.
def rewrites(origin, root):
    data_root = f"Path('{root}')  # vendored: the data root (was Path(__file__).resolve().parents[1])"
    return [
        ('*', 'STAGE = Path(__file__).resolve().parents[1]', f'STAGE = {data_root}'),
        ('*', 'HERE = Path(__file__).resolve().parents[1]', f'HERE = {data_root}'),
        ('*', 'ROOT = Path(__file__).resolve().parents[1]', f'ROOT = {data_root}'),
        ('*', "R = Path(__file__).resolve().parents[1]; ", f"R = Path('{root}')  # vendored: the data root (was parents[1])\n"),
        ('*', "str(STAGE / 'tools')", OWN),
        ('*', "str(ROOT / 'scripts')", OWN),
        ('*', "str(ROOT/'scripts')", OWN),
        ('arxiv_bulk.py', f"sys.path.insert(0, '{SW}/claude-princeton-20261015/tools')",
         f"sys.path.insert(0, str({sib('princeton_tools')}))"),
        ('arxiv_oai.py', f"sys.path.insert(0, '{SW}/claude-princeton-20261015/tools')",
         f"sys.path.insert(0, str({sib('princeton_tools')}))"),
        ('s2_key_lookup.py', "sys.path.insert(0, str(PRIN / 'tools'))", f"sys.path.insert(0, str({sib('princeton_tools')}))"),
        ('study_copies.py', f"CMU_TOOLS = Path('{SW}/claude-cmu-20261017/tools')", f"CMU_TOOLS = {sib('cmu_tools')}"),
        ('study_copies.py', f"PRIN_TOOLS = Path('{SW}/claude-princeton-20261015/tools')", f"PRIN_TOOLS = {sib('princeton_tools')}"),
        ('build-cs-hierarchy.py', "H = R.parent / '.research-sweeps/claude-schools-20261021/hierarchy'",
         "H = Path('/n/fs/resemble/cs-atlas/work/hierarchy')  # vendored: was the old sweep link to the same directory"),
        ('collector_wrapper.py', f"SCRIPTS = Path('{HS}/scripts')", f"SCRIPTS = {sib('homogenizing_scripts')}"),
        ('cs_pi_works.py', f"sys.path.insert(0, '{HS}/scripts')", f"sys.path.insert(0, str({sib('homogenizing_scripts')}))"),
    ]


# a code location left pointing outside the repo: a string literal ending in an old tools/ or scripts/ directory
LEFTOVER = re.compile(r"""['"](?:/n/fs/resemble/maxent-grpo/\.research-sweeps/[^'"]+/(?:tools|scripts)|"""
                      r"""/n/fs/resemble/homogenizing-science/scripts)/?['"]""")


SIMPLIFY = re.compile(r"Path\(str\((_?A?P\.[A-Z_]+(?: / '[^'\\]*')?)\)\)")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def vendor(origin, name):
    src_dir, root, _ = ORIGINS[origin]
    src = Path(src_dir) / name
    raw = src.read_bytes()
    text = raw.decode('utf-8')
    applied = []
    for target, old, new in rewrites(origin, root):
        if target not in ('*', name):
            continue
        n = text.count(old)
        if target == name and n == 0:
            raise SystemExit(f'{origin}/{name}: rewrite not found: {old}')
        if n:
            text = text.replace(old, new)
            applied.append(f'{n}x {old}')
    left = [m.group(0) for m in LEFTOVER.finditer(text)]
    if not left:
        # every remaining absolute data path -> an expression on atlas_paths (same value under today's layout), so the
        # vendored code follows the project move like the rest of the repository
        text, n, unresolved = route_paths.py_fix(f'vendor/{origin}/{name}', text)
        if unresolved:
            raise SystemExit(f'{origin}/{name}: paths left unrouted: {unresolved}')
        text = SIMPLIFY.sub(r'\1', text)
        if n:
            applied.append(f'{n} data paths via atlas_paths')
    if left:
        raise SystemExit(f'{origin}/{name}: code location still outside the repo: {left}')
    header = f'# Vendored {DATE} from {src} (sha256 {sha(raw)}); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.\n'
    if text.startswith('#!'):
        first, rest = text.split('\n', 1)
        text = first + '\n' + header + rest
    else:
        text = header + text
    return src, sha(raw), text.encode('utf-8'), applied


def sync():
    rows = ['vendored\tsource\tsource_sha256\tvendored_sha256\trewrites']
    for origin, (_, _, files) in ORIGINS.items():
        (VENDOR / origin).mkdir(parents=True, exist_ok=True)
        for name in files:
            src, ssha, out, applied = vendor(origin, name)
            dest = VENDOR / origin / name
            dest.write_bytes(out)
            rows.append('\t'.join([f'{origin}/{name}', str(src), ssha, sha(out), '; '.join(applied) or '-']))
    (VENDOR / 'PROVENANCE.tsv').write_text('\n'.join(rows) + '\n')
    print(f'vendor_sync: {len(rows) - 1} files -> {VENDOR}')


def provenance():
    lines = (VENDOR / 'PROVENANCE.tsv').read_text().splitlines()[1:]
    return [dict(zip(['vendored', 'source', 'source_sha256', 'vendored_sha256', 'rewrites'], l.split('\t'))) for l in lines]


def check(strict=False, sources=True):
    bad, drift, missing = [], [], []
    rows = provenance()
    listed = {r['vendored'] for r in rows}
    expected = {f'{o}/{n}' for o, (_, _, fs) in ORIGINS.items() for n in fs}
    if listed != expected:
        bad.append(f'PROVENANCE.tsv and ORIGINS disagree: {sorted(listed ^ expected)}')
    for r in rows:
        f = VENDOR / r['vendored']
        if not f.exists() or sha(f.read_bytes()) != r['vendored_sha256']:
            bad.append(f"{r['vendored']}: differs from PROVENANCE.tsv (edited after vendoring?)")
        if sources:
            s = Path(r['source'])
            if not s.exists():
                missing.append(r['source'])
            elif sha(s.read_bytes()) != r['source_sha256']:
                drift.append(r['source'])
    for b in bad:
        print('MISMATCH', b)
    for d in drift:
        print('DRIFT   ', d, '(the original changed since it was vendored: review, then vendor_sync.py sync)')
    for m in missing:
        print('GONE    ', m, '(original retired or moved)')
    print(f'vendor_sync check: {len(rows)} files, {len(bad)} mismatches, {len(drift)} drifted sources, {len(missing)} gone')
    return 1 if bad or (strict and drift) else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['check', 'sync', 'list'])
    ap.add_argument('--strict', action='store_true', help='check: drift is an error too')
    ap.add_argument('--no-sources', action='store_true', help='check: skip the originals (CI has no NFS)')
    a = ap.parse_args()
    if a.cmd == 'sync':
        sync()
        return check()
    if a.cmd == 'list':
        for r in provenance():
            print(r['vendored'], '<-', r['source'])
        return 0
    return check(a.strict, not a.no_sources)


if __name__ == '__main__':
    sys.exit(main())
