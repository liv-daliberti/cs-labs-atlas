"""ROADMAP #21: no NEW sys.path edits. The edits that remain are in tests/sys_path_allowlist.json with the reason: entry points that run
under `python -I` (which ignores PYTHONPATH and leaves the script directory off sys.path), the helpers they import, vendored code (never
edited) and a few cross-directory imports. An allowlisted file that loses its edit must leave the list, so the list only shrinks.
The packaging list (pyproject py-modules) must name every module of tools/."""
import json
import re
import subprocess
import tomllib
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
EDIT = re.compile(r'sys\.path\.(insert|append)')
EXEMPT = ('archive/', 'ai-writing/', 'studies/')


def tracked_with_edits():
    files = subprocess.run(['git', '-C', str(CODE), 'ls-files', '*.py'], capture_output=True, text=True).stdout.split()
    return {f for f in files if not f.startswith(EXEMPT) and (CODE / f).exists() and EDIT.search((CODE / f).read_text(errors='replace'))}


def test_no_new_sys_path_edits_outside_the_allowlist():
    allow = json.loads((CODE / 'tests' / 'sys_path_allowlist.json').read_text())
    have = tracked_with_edits()
    assert not have - set(allow), f'new sys.path edits (use PYTHONPATH / pyproject pythonpath, or record the reason in tests/sys_path_allowlist.json): {sorted(have - set(allow))}'
    assert not set(allow) - have, f'allowlisted files without an edit now (remove them from the list): {sorted(set(allow) - have)}'
    assert all(allow.values())


def test_pyproject_py_modules_match_tools():
    cfg = tomllib.loads((CODE / 'pyproject.toml').read_text())
    listed = set(cfg['tool']['setuptools']['py-modules'])
    assert listed == {p.stem for p in (CODE / 'tools').glob('*.py')}
    assert cfg['tool']['setuptools']['package-dir']['pihier'] == 'tools/pihier'
    assert 'tools' in cfg['tool']['pytest']['ini_options']['pythonpath']
