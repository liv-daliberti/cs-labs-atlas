"""tools/atlas_paths.py: one root, the two layouts (legacy today, project after the move), the overrides and paths.sh."""
import os
import subprocess
import sys
from pathlib import Path

import atlas_paths as P

CODE = Path(__file__).resolve().parents[1]
HS = Path('/n/fs/resemble/homogenizing-science')


def run(env, *args):
    e = {k: v for k, v in os.environ.items() if not k.startswith('CS_ATLAS_')}
    e.update(env)
    return subprocess.run([sys.executable, str(CODE / 'tools/atlas_paths.py'), *args], env=e, capture_output=True, text=True,
                          check=True).stdout


def test_one_root_project_layout():
    d = P._resolve({'CS_ATLAS_LAYOUT': 'project'})
    assert d['ROOT'] == HS
    for name, v in d.items():
        if name not in ('ENV_PY', 'ENV_LIB', 'COLLECTOR_PY'):  # the old envs stay where they are until retired
            assert v == HS or HS in v.parents, (name, v)
    assert d['CODE'] == HS / 'code' and d['HIERARCHY'] == HS / 'code/hierarchy' and d['WORK'] == d['CODE']
    assert d['STORES'] == HS / 'stores' and d['STANFORD_STORE'] == HS / 'stores/stanford'
    assert d['SWEEPS'] == HS / 'archive/sweeps' and d['WORLD_ATLAS'] == HS / 'world-atlas'
    assert d['PY'] == HS / 'env/atlas/bin/python' and d['EXPORT'] == HS / 'export'


def test_legacy_layout_is_today():
    d = P._resolve({'CS_ATLAS_LAYOUT': 'legacy'})
    assert d['ROOT'] == HS and d['PY'] == HS / 'env/atlas/bin/python'
    assert d['CODE'] == Path('/n/fs/resemble/cs-atlas/work') and d['HIERARCHY'] == d['CODE'] / 'hierarchy'
    assert d['RELEASES'] == Path('/n/fs/resemble/cs-atlas/releases')
    assert d['SWEEPS'] == Path('/n/fs/resemble/maxent-grpo/.research-sweeps')
    assert d['STORES'] == HS / 'data/fulltext' and d['WORLD_ATLAS'] == HS
    assert P.archive_sweep('claude-cmu-20261017') == P.SWEEPS / 'claude-cmu-20261017' == P.sweep('claude-cmu-20261017')
    assert P.store('stanford') == P.STORES / 'stanford' and P.vendor('cmu_tools') == P.VENDOR / 'cmu_tools'


def test_cutover_is_one_line():
    src = (CODE / 'tools/atlas_paths.py').read_text()
    import re
    assert len(re.findall(r"^LAYOUT_DEFAULT = '(legacy|project)'", src, re.M)) == 1


def test_overrides():
    assert run({'CS_ATLAS_LAYOUT': 'project', 'CS_ATLAS_ROOT': '/tmp/atlas-x'}, 'HIERARCHY').strip() == '/tmp/atlas-x/code/hierarchy'
    assert run({'CS_ATLAS_CODE': '/tmp/c'}, 'HIERARCHY').strip() == '/tmp/c/hierarchy'
    assert run({'CS_ATLAS_WORK': '/tmp/w'}, 'TOOLS').strip() == '/tmp/w/tools'  # the old name still works
    assert run({'CS_ATLAS_SWEEPS': '/tmp/sw'}, 'SWEEPS').strip() == '/tmp/sw'


def test_paths_sh_is_current():
    assert (CODE / 'paths.sh').read_text() == P.shell(), 'regenerate: python tools/atlas_paths.py --sh > paths.sh'


def _sh(env):
    base = {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
    base.update(env)
    return subprocess.run(['sh', '-c', f'. {CODE}/paths.sh; echo "$CS_ATLAS_HIERARCHY|$CS_ATLAS_SITE_DATA|$(cs_atlas_sweep s)|'
                           '$CS_ATLAS_WORK|$CS_ATLAS_PY"'], env=base, capture_output=True, text=True, check=True).stdout.strip()


def test_paths_sh_agrees_with_python():
    d = P._resolve({'CS_ATLAS_LAYOUT': P.LAYOUT_DEFAULT})
    assert _sh({}) == f'{d["HIERARCHY"]}|{d["SITE_ROOT"]}/atlas/data|{d["SWEEPS"]}/s|{d["CODE"]}|{d["PY"]}'
    assert _sh({'CS_ATLAS_CODE': '/tmp/c'}).startswith('/tmp/c/hierarchy|')
    assert _sh({'CS_ATLAS_WORK': '/tmp/w'}).split('|')[3] == '/tmp/w'


def test_project_paths_sh_agrees_with_python(tmp_path):
    (tmp_path / 'paths.sh').write_text(P.shell('project'))
    out = subprocess.run(['sh', '-c', f'. {tmp_path}/paths.sh; echo "$CS_ATLAS_HIERARCHY|$CS_ATLAS_STORES|$CS_ATLAS_PY"'],
                         env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'CS_ATLAS_ROOT': '/tmp/r'},
                         capture_output=True, text=True, check=True).stdout.strip()
    assert out == '/tmp/r/code/hierarchy|/tmp/r/stores|/tmp/r/env/atlas/bin/python'
