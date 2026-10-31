"""Every path the CS Labs Atlas code uses, in one place (stdlib only; Python 3.6+).

Python   sys.path.insert(0, '<code>/tools'); import atlas_paths as P; P.HIERARCHY / 'princeton' / 'pis.json'
         (scripts in tools/ already have their own directory on sys.path; scripts elsewhere insert
         Path(__file__).resolve().parents[k] / 'tools' first)
shell    . <code>/paths.sh   then $CS_ATLAS_CODE, $CS_ATLAS_PY, ... (see `--sh`). Shell scripts source it relative to
         themselves (. "$(dirname "$0")/../paths.sh"); Slurm scripts are submitted from the code root and source
         "$SLURM_SUBMIT_DIR/paths.sh". paths.sh is generated: python tools/atlas_paths.py --sh > paths.sh
         (tests/test_atlas_paths.py checks it is current).
CLI      python tools/atlas_paths.py [NAME]      prints one path, or every name=value

One project root (2026-10-30). Everything lives under ROOT = /n/fs/resemble/homogenizing-science:

  code/ (this repository)   releases/   schools/   stores/<school>/   studies/   figures/   site/   export/
  env/ (atlas, hf-cache)    cache/      external/ (dblp-dump, research-library)
  archive/ (sweeps/, site-history/, migrations/, cs-atlas-archive/)    world-atlas/ (the 300-university atlas)

LAYOUT says where the directories are today:
  'legacy'   before the move: each slot has its old absolute location (_LEGACY below; the only place those appear)
  'project'  after tools/relocate_project.py has moved the directories: every slot is derived from ROOT
THE CUTOVER IS ONE LINE: set LAYOUT_DEFAULT = 'project' below, then regenerate paths.sh. CS_ATLAS_LAYOUT overrides it
per process (CS_ATLAS_LAYOUT=project to try the new layout).

Overrides: any name can be overridden by CS_ATLAS_<NAME> (CS_ATLAS_ROOT, CS_ATLAS_CODE, CS_ATLAS_SWEEPS, CS_ATLAS_PY, ...);
an override of a slot moves the slots derived from it. CS_ATLAS_WORK is the old name of CS_ATLAS_CODE and still works.

Interpreters (2026-10-30): PY is the one project interpreter (env/atlas, built from env/conda-linux-64.lock; no
LD_LIBRARY_PATH needed). COLLECTOR_PY is what the download loops run: the old Anaconda Python until the loops are
restarted on the new env (docs/ENVIRONMENT.md, switch-over), then PY. ENV_PY/ENV_LIB are the old py310 env, kept in
place for the ML studies (torch, transformers) until a [studies] env replaces it (conda envs cannot be moved).
"""
import os
import re
import sys
from pathlib import Path

SCHOOL_IDS_STATIC = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']  # fallback when schools/ is unreadable
ROOT_DEFAULT = '/n/fs/resemble/homogenizing-science'
LAYOUT_DEFAULT = 'project'  # cutover 2026-10-30 (archive/migrations/relocate-2026-10-30.jsonl); 'legacy' = the old paths

# (name, path in the project layout, relative to which slot (None: absolute)) in dependency order
_SPEC = [
    ('ROOT', ROOT_DEFAULT, None),
    ('CODE', 'code', 'ROOT'),                       # this git repository: code, docs, reviewed inputs, built packages
    ('TOOLS', 'tools', 'CODE'),
    ('TESTS', 'tests', 'CODE'),
    ('VENDOR', 'vendor', 'CODE'),                   # code copied in from the old sweeps (tools/vendor_sync.py)
    ('SCHOOL_CONFIGS', 'schools', 'CODE'),          # the school charters schools/<key>.toml (tools/school_config.py)
    ('HIERARCHY', 'hierarchy', 'CODE'),             # built packages hierarchy/<school>/ and the reviewed inputs
    ('CENSUS', 'census', 'CODE'),
    ('PERIODS', 'periods', 'CODE'),
    ('LISTINGS', 'listings', 'CODE'),
    ('CAPTURES', 'captures', 'CODE'),
    ('FULLTEXT_PUSH', 'fulltext-push', 'CODE'),     # the full-text collectors
    ('AI_WRITING', 'ai-writing', 'CODE'),           # the AI-writing study's code (its data is git-ignored)
    ('RELEASES', 'releases', 'ROOT'),               # immutable dated releases (tools/make_release.py)
    ('SCHOOLS_TREE', 'schools', 'ROOT'),            # the organized school -> lab -> papers tree (tools/organize_tree.py)
    ('STORES', 'stores', 'ROOT'),                   # full-text stores <STORES>/<school>: catalog.sqlite + objects/
    ('STANFORD_STORE', 'stanford', 'STORES'),       # a real directory in the project layout
    ('STUDIES', 'studies', 'ROOT'),
    ('HOMOGENIZATION_STUDY', 'homogenization', 'STUDIES'),  # the homogenization study's corpus (was a sweep)
    ('FIGURES', 'figures', 'ROOT'),
    ('SITE', 'site', 'ROOT'),                       # the live site's source checkout
    ('EXPORT', 'export', 'ROOT'),                   # the public GitHub clone (main = release exports)
    ('ENV', 'env', 'ROOT'),
    ('PY', 'atlas/bin/python', 'ENV'),              # THE project interpreter (env/environment.yml)
    ('HF_HOME', 'hf-cache', 'ENV'),
    ('CACHE', 'cache', 'ROOT'),                     # API caches (never in git)
    ('LOCKS', '/tmp/cs-atlas-locks', None),         # node-local flock files that space requests across processes on one host
    ('EXTERNAL', 'external', 'ROOT'),
    ('DBLP_DUMP', 'dblp-dump', 'EXTERNAL'),         # DBLP's XML dump directory
    ('RESEARCH_LIBRARY', 'research-library', 'EXTERNAL'),
    ('ARCHIVE', 'archive', 'ROOT'),                 # read-only history; code should not need it (see vendor/README.md)
    ('SWEEPS', 'sweeps', 'ARCHIVE'),                # the old base sweeps (DBLP lists, captures, census sources)
    ('SITE_HISTORY', 'site-history', 'ARCHIVE'),
    ('SITE_ROOT', 'princeton-live-20261015', 'SITE_HISTORY'),  # the 300-university atlas site build (collections)
    ('MIGRATIONS', 'migrations', 'ARCHIVE'),        # tools/relocate_project.py records every move here
    ('WORLD_ATLAS', 'world-atlas', 'ROOT'),         # the 300-university atlas (its scripts/ hold the collector's origin)
    ('ENV_PY', '/n/fs/resemble/cs-atlas-env/py310/bin/python', None),  # old env, ML studies only; LD_LIBRARY_PATH=ENV_LIB
    ('ENV_LIB', '/n/fs/resemble/cs-atlas-env/py310/lib', None),
    ('COLLECTOR_PY', '/usr/local/anaconda3/2024.02/bin/python', None),  # the download loops' (-I); -> PY at the switch-over
]
# Where each slot is before the move (LAYOUT 'legacy'). A slot not listed derives as in the project layout.
_LEGACY = {
    'CODE': '/n/fs/resemble/cs-atlas/work',
    'RELEASES': '/n/fs/resemble/cs-atlas/releases',
    'SCHOOLS_TREE': '/n/fs/resemble/cs-atlas/schools',
    'STORES': '/n/fs/resemble/homogenizing-science/data/fulltext',
    'STANFORD_STORE': '/n/fs/resemble/cs-atlas-fulltext/stanford',
    'STUDIES': '/n/fs/resemble/cs-atlas/studies',
    'HOMOGENIZATION_STUDY': '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-homogenization-20261019',
    'FIGURES': '/n/fs/resemble/cs-atlas/figures',
    'SITE': '/n/fs/resemble/maxent-grpo/homogenizing-publish-20261029',
    'EXPORT': '/n/fs/resemble/cs-labs-atlas',
    'HF_HOME': '/n/fs/resemble/cs-atlas-env/hf-cache',
    'CACHE': '/n/fs/resemble/cs-atlas-cache',
    'DBLP_DUMP': '/n/fs/resemble/maxent-grpo/var/data/dblp-dump',
    'RESEARCH_LIBRARY': '/n/fs/resemble/maxent-grpo/research-library',
    'SWEEPS': '/n/fs/resemble/maxent-grpo/.research-sweeps',
    'SITE_HISTORY': '/n/fs/resemble/maxent-grpo',
    'WORLD_ATLAS': '/n/fs/resemble/homogenizing-science',
}
_ALIASES = {'WORK': 'CODE', 'GITHUB_EXPORT': 'EXPORT', 'HOMOGENIZING': 'WORLD_ATLAS'}  # old names, still served
DBLP_DUMP_FILE = 'dblp-2026-09-01.xml.gz'


def _layout(env):
    lay = env.get('CS_ATLAS_LAYOUT') or LAYOUT_DEFAULT
    if lay not in ('legacy', 'project'):
        raise ValueError(f'CS_ATLAS_LAYOUT must be legacy or project, not {lay!r}')
    return lay


def _default(name, rel, base, out, lay):
    if lay == 'legacy' and name in _LEGACY:
        return Path(_LEGACY[name])
    return out[base] / rel if base else Path(rel)


def _resolve(env=None):
    env = os.environ if env is None else env
    lay = _layout(env)
    out = {}
    for name, rel, base in _SPEC:
        v = env.get('CS_ATLAS_' + name) or (env.get('CS_ATLAS_WORK') if name == 'CODE' else None)
        out[name] = Path(v) if v else _default(name, rel, base, out, lay)
    for old, new in _ALIASES.items():
        out[old] = out[new]
    return out


LAYOUT = _layout(os.environ)
_P = _resolve()
globals().update(_P)
ROOT = _P['ROOT']; CODE = WORK = _P['CODE']; TOOLS = _P['TOOLS']; TESTS = _P['TESTS']; VENDOR = _P['VENDOR']
SCHOOL_CONFIGS = _P['SCHOOL_CONFIGS']; HIERARCHY = _P['HIERARCHY']; CENSUS = _P['CENSUS']; PERIODS = _P['PERIODS']
LISTINGS = _P['LISTINGS']; CAPTURES = _P['CAPTURES']; FULLTEXT_PUSH = _P['FULLTEXT_PUSH']; AI_WRITING = _P['AI_WRITING']
RELEASES = _P['RELEASES']; SCHOOLS_TREE = _P['SCHOOLS_TREE']; STORES = _P['STORES']; STANFORD_STORE = _P['STANFORD_STORE']
STUDIES = _P['STUDIES']; HOMOGENIZATION_STUDY = _P['HOMOGENIZATION_STUDY']; FIGURES = _P['FIGURES']; SITE = _P['SITE']
EXPORT = GITHUB_EXPORT = _P['EXPORT']; ENV = _P['ENV']; PY = _P['PY']; HF_HOME = _P['HF_HOME']; CACHE = _P['CACHE']
EXTERNAL = _P['EXTERNAL']; DBLP_DUMP = _P['DBLP_DUMP']; RESEARCH_LIBRARY = _P['RESEARCH_LIBRARY']; ARCHIVE = _P['ARCHIVE']
SWEEPS = _P['SWEEPS']; SITE_HISTORY = _P['SITE_HISTORY']; SITE_ROOT = _P['SITE_ROOT']; MIGRATIONS = _P['MIGRATIONS']
WORLD_ATLAS = HOMOGENIZING = _P['WORLD_ATLAS']; ENV_PY = _P['ENV_PY']; ENV_LIB = _P['ENV_LIB']
COLLECTOR_PY = _P['COLLECTOR_PY']
SITE_DATA = SITE_ROOT / 'atlas/data'               # collection-<school>.json.gz, universities/
DBLP_DUMP_XML = DBLP_DUMP / DBLP_DUMP_FILE
HOMOGENIZING_SCRIPTS = WORLD_ATLAS / 'scripts'     # the collector's origin (vendored: vendor/homogenizing_scripts)


def _released_schools(d):
    """The released schools in charter order, read from schools/<key>.toml with two line patterns (stdlib only, so this
    module stays importable by any Python 3.6+): `status = "released"` and `order = N`. A school being onboarded
    (status = "onboarding") is not in SCHOOL_IDS: the build, the release and the tree never see it before stage 10."""
    out = []
    try:
        for f in sorted(Path(d).glob('*.toml')):
            if f.stem == 'TEMPLATE':
                continue
            t = f.read_text()
            st = re.search(r'^status\s*=\s*"([a-z]+)"', t, re.M); od = re.search(r'^order\s*=\s*(\d+)', t, re.M)
            if st and st.group(1) == 'released':
                out.append((int(od.group(1)) if od else 999, f.stem))
    except OSError:
        return []
    return [k for _, k in sorted(out)]


SCHOOL_IDS = _released_schools(SCHOOL_CONFIGS) or list(SCHOOL_IDS_STATIC)


def archive_sweep(name):
    """An old base sweep (read-only history): archive_sweep('claude-cmu-20261017') -> <SWEEPS>/claude-cmu-20261017.
    New code should not need one: vendor the code (tools/vendor_sync.py) or move the data into a project slot."""
    return SWEEPS / name


sweep = archive_sweep  # the old name


def site_history(name):
    """An old site build or transfer (princeton-live-*, catalogue-publish-*, ...): <SITE_HISTORY>/<name>."""
    return SITE_HISTORY / name


def vendor(name):
    """A vendored code directory: vendor('cmu_tools') -> <CODE>/vendor/cmu_tools (see vendor/README.md)."""
    return VENDOR / name


def store(school):
    """A school's full-text store as the collectors address it (<STORES>/<school>; before the move Stanford's is a link
    to STANFORD_STORE)."""
    return STORES / school


def shell(layout=None):
    """paths.sh: every name as an exported CS_ATLAS_<NAME> whose default is written relative to the slot it derives from,
    so that overriding a slot before sourcing (CS_ATLAS_ROOT, CS_ATLAS_CODE, ...) moves the slots under it."""
    lay = layout or LAYOUT_DEFAULT
    L = ['# Generated by tools/atlas_paths.py --sh; do not edit. Regenerate: python tools/atlas_paths.py --sh > paths.sh',
         '# Every name may be set beforehand to override it (CS_ATLAS_ROOT moves the project root; CS_ATLAS_WORK is the',
         '# old name of CS_ATLAS_CODE).',
         f'export CS_ATLAS_LAYOUT="${{CS_ATLAS_LAYOUT:-{lay}}}"',
         'export CS_ATLAS_CODE="${CS_ATLAS_CODE:-${CS_ATLAS_WORK:-}}"; [ -n "$CS_ATLAS_CODE" ] || unset CS_ATLAS_CODE']
    for name, rel, base in _SPEC:
        if lay == 'legacy' and name in _LEGACY:
            val = _LEGACY[name]
        else:
            val = f'$CS_ATLAS_{base}/{rel}' if base else rel
        L.append(f'export CS_ATLAS_{name}="${{CS_ATLAS_{name}:-{val}}}"')
    L += [f'export CS_ATLAS_{old}="$CS_ATLAS_{new}"' for old, new in _ALIASES.items()]
    L += ['export CS_ATLAS_SITE_DATA="$CS_ATLAS_SITE_ROOT/atlas/data"',
          f'export CS_ATLAS_DBLP_DUMP_XML="$CS_ATLAS_DBLP_DUMP/{DBLP_DUMP_FILE}"',
          'export CS_ATLAS_HOMOGENIZING_SCRIPTS="$CS_ATLAS_WORLD_ATLAS/scripts"',
          f'export CS_ATLAS_SCHOOLS="{" ".join(SCHOOL_IDS)}"',
          'cs_atlas_sweep() { printf "%s/%s\\n" "$CS_ATLAS_SWEEPS" "$1"; }',
          'cs_atlas_vendor() { printf "%s/%s\\n" "$CS_ATLAS_VENDOR" "$1"; }']
    return '\n'.join(L) + '\n'


def as_dict():
    d = {k: str(v) for k, v in _P.items()}
    d.update(LAYOUT=LAYOUT, SITE_DATA=str(SITE_DATA), DBLP_DUMP_XML=str(DBLP_DUMP_XML),
             HOMOGENIZING_SCRIPTS=str(HOMOGENIZING_SCRIPTS))
    return d


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--sh']:
        sys.stdout.write(shell(a[1] if len(a) > 1 else None))
    elif a:
        print(as_dict()[a[0]])
    else:
        for k, v in as_dict().items():
            print(f'{k}={v}')
