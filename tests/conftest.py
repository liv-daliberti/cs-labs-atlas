"""Shared setup: the fixtures directory, and the `nfs` marker.

Run (from the code root): bin/atlas test    (= <env>/bin/python -m pytest; pyproject.toml holds the pytest config)
Tests marked @pytest.mark.nfs need the project data on /n/fs (packages, stores, sweeps). They run locally and are
skipped in CI (CS_ATLAS_CI=1, or `atlas test --ci`, or -m 'not nfs'); a test that needs data it cannot find skips itself.
"""
import json
import os
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'   # on sys.path through pyproject.toml [tool.pytest.ini_options] pythonpath
FIXTURES = Path(__file__).resolve().parent / 'fixtures'


# Source-tree hygiene tests read the git index. A job's code snapshot (tools/job_code_snapshot.sh: a `git archive` of one
# commit, as the release's tests stage runs) has no .git, so there they skip; CI and `agent_worktree.sh land` run them on
# the full checkout before any commit reaches main.
NEEDS_GIT = {'test_script_map.py', 'test_imports_and_sys_path.py', 'test_pi_hierarchy_exports.py', 'test_job_code_snapshot.py', 'test_gitignore_reviewed_inputs.py'}
CODE = Path(__file__).resolve().parents[1]


def _school_data_present():
    """True when the school placement has data on disk (after the cutover): schools/<s>/reviewed for the first released school."""
    import atlas_paths
    return atlas_paths.school_dir('cmu', 'reviewed').exists()


def pytest_collection_modifyitems(config, items):
    if os.environ.get('CS_ATLAS_CI') == '1':
        skip = pytest.mark.skip(reason='needs the NFS project data (CS_ATLAS_CI=1)')
        for item in items:
            if 'nfs' in item.keywords:
                item.add_marker(skip)
    if os.environ.get('CS_ATLAS_DATA_LAYOUT') == 'school' and not _school_data_present():
        skip_live = pytest.mark.skip(reason='reads live reviewed data through data(): the school placement has none until the cutover creates schools/<s>/reviewed')
        for item in items:
            if 'live_school_data' in item.keywords:
                item.add_marker(skip_live)
    if not (CODE / '.git').exists():
        skip_git = pytest.mark.skip(reason='source-tree hygiene test: needs the git checkout, not a code snapshot')
        for item in items:
            if Path(str(item.fspath)).name in NEEDS_GIT:
                item.add_marker(skip_git)


@pytest.fixture
def fixture_json():
    def load(name):
        return json.loads((FIXTURES / name).read_text())
    return load


@pytest.fixture
def flat_data_root(monkeypatch):
    """Point atlas_paths.data (and so hfile, SchoolDir, data_w) at a flat fixture tree: use_root(tmp_path) before the code under test runs."""
    import atlas_paths
    orig = atlas_paths.data

    def use_root(root):
        monkeypatch.setattr(atlas_paths, 'data', lambda name, school=None, root_=None, layout=None, **kw: orig(name, school, root=kw.get('root', root_) or root, layout=layout or 'flat'))
    return use_root


@pytest.fixture(autouse=True)
def _split_only(request, monkeypatch):
    """Tests marked split_only (module `pytestmark = pytest.mark.split_only`) build a split-placement fixture tree by hand (hierarchy/<school>/...,
    a patched STORES or LISTINGS); they run in the split placement whatever CS_ATLAS_DATA_LAYOUT says. The school placement is covered by the
    `layout` fixture and tests/test_overlay_root_school.py, tests/test_school_part.py, tests/test_atlas_paths_school_layout.py."""
    if request.node.get_closest_marker('split_only'):
        monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'split')


@pytest.fixture(params=['flat', 'split', 'school'])
def layout(request, monkeypatch):
    """Run the test in both data layouts: the code under test finds its files through atlas_paths.data, which follows CS_ATLAS_DATA_LAYOUT."""
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', request.param)
    return request.param
