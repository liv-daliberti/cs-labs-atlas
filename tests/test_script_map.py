"""docs/SCRIPT-MAP.md against the tree (ROADMAP item 5): every retired script is in archive/ at its old path, every script
in archive/ is in the map, the folded tools exist, and no one-school or one-off script is left where the build, the
collectors or the stage tools live (except the lab-page agent's hierarchy/labpage-tools-*, deferred)."""
import re
import subprocess
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
MAP = (CODE / 'docs' / 'SCRIPT-MAP.md').read_text()
BUILD = {'hierarchy/rebuild.sh', 'hierarchy/rebuild-all.slurm', 'hierarchy/organize-tree.slurm', 'hierarchy/build-equivalence.slurm', 'hierarchy/layout-equivalence.slurm', 'hierarchy/build-school.slurm', 'hierarchy/merge-equivalence.slurm', 'hierarchy/submit-parallel.sh', 'hierarchy/release.slurm', 'hierarchy/pipeline-stage.slurm',
         'hierarchy/labpage-audit.slurm'}
SCHOOLS = 'princeton|cmu|epfl|mit|berkeley|stanford|michigan'


def tracked():
    return set(subprocess.run(['git', '-C', str(CODE), 'ls-files'], capture_output=True, text=True, check=True).stdout.split())


def test_retired_scripts_are_in_archive():
    files = tracked()
    retired = re.findall(r'\| retired: `(archive/[^`]+)` \|', MAP)
    assert len(retired) >= 250
    missing = [f for f in retired if f not in files]
    assert not missing, missing
    assert not [f for f in retired if f[len('archive/'):] in files]               # and gone from the old place


def test_every_archived_script_is_in_the_map():
    retired = set(re.findall(r'\| retired: `(archive/[^`]+)` \|', MAP))
    folded_originals = {'archive/hierarchy/michigan/run_sweep.sh', 'archive/hierarchy/michigan/sweep_daily.sh',
                        'archive/hierarchy/run_stanford_sweep.sh'}
    code = {f for f in tracked() if f.startswith('archive/') and f.endswith(('.py', '.sh', '.slurm'))}
    assert not code - retired - folded_originals


def test_folded_and_kept_targets_exist():
    files = tracked()
    for f in ('tools/mpcap.py', 'tools/sweep_school.py', 'listings/scripts/config_cmu.py'):
        assert f in files and f in MAP or f.split('/')[-1] in MAP


def test_no_one_school_scripts_left_in_live_places():
    left = [f for f in tracked() if f.endswith(('.py', '.sh', '.slurm')) and (
        (f.startswith('hierarchy/') and f not in BUILD and not f.startswith('hierarchy/labpage-tools-'))
        or f.startswith('census/') or re.match(rf'tools/({SCHOOLS})_', f))]
    assert not left, left


def test_live_code_does_not_import_from_archive():
    out = subprocess.run(['git', '-C', str(CODE), 'grep', '-n', '-E', r'sys\.path.*archive|archive_dir|/archive/(hierarchy|tools|census)',
                          '--', 'tools', 'atlas_cli', 'fulltext-push', 'listings', 'hierarchy/*.sh', 'hierarchy/*.slurm'],
                         capture_output=True, text=True).stdout
    assert not [l for l in out.splitlines() if not l.split(':', 2)[2].lstrip().startswith('#')], out
