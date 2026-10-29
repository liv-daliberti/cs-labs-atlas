"""tools/atlas_paths.py: the defaults, the overrides and the generated paths.sh."""
import os
import subprocess
import sys
from pathlib import Path

import atlas_paths as P

WORK = Path(__file__).resolve().parents[1]


def run(env, *args):
    e = {k: v for k, v in os.environ.items() if not k.startswith('CS_ATLAS_')}
    e.update(env)
    return subprocess.run([sys.executable, str(WORK / 'tools/atlas_paths.py'), *args], env=e, capture_output=True, text=True, check=True).stdout


def test_defaults():
    d = P._resolve({})
    assert d['ROOT'] == Path('/n/fs/resemble/cs-atlas')
    assert d['WORK'] == d['ROOT'] / 'work' and d['HIERARCHY'] == d['WORK'] / 'hierarchy'
    assert d['RELEASES'] == d['ROOT'] / 'releases' and d['SCHOOLS_TREE'] == d['ROOT'] / 'schools'
    assert d['SWEEPS'] == Path('/n/fs/resemble/maxent-grpo/.research-sweeps')
    assert P.sweep('claude-cmu-20261017') == P.SWEEPS / 'claude-cmu-20261017'
    assert P.store('stanford') == P.STORES / 'stanford'


def test_work_is_this_checkout_by_default():
    if not os.environ.get('CS_ATLAS_ROOT') and not os.environ.get('CS_ATLAS_WORK'):
        assert P.WORK.resolve() == WORK.resolve()


def test_root_override_moves_derived_paths():
    assert run({'CS_ATLAS_ROOT': '/tmp/atlas-x'}, 'HIERARCHY').strip() == '/tmp/atlas-x/work/hierarchy'
    assert run({'CS_ATLAS_ROOT': '/tmp/atlas-x'}, 'SWEEPS').strip() == '/n/fs/resemble/maxent-grpo/.research-sweeps'
    assert run({'CS_ATLAS_SWEEPS': '/tmp/sw'}, 'SWEEPS').strip() == '/tmp/sw'


def test_paths_sh_is_current():
    assert (WORK / 'paths.sh').read_text() == P.shell(), 'regenerate: python tools/atlas_paths.py --sh > paths.sh'


def test_paths_sh_agrees_with_python():
    out = subprocess.run(['sh', '-c', f'. {WORK}/paths.sh; echo "$CS_ATLAS_HIERARCHY|$CS_ATLAS_SITE_DATA|$(cs_atlas_sweep s)"'],
                         env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'CS_ATLAS_ROOT': '/tmp/atlas-y'},
                         capture_output=True, text=True, check=True).stdout.strip()
    assert out == f'/tmp/atlas-y/work/hierarchy|{P._resolve({})["SITE_ROOT"]}/atlas/data|{P._resolve({})["SWEEPS"]}/s'
