"""Shared setup: the tools directory on sys.path, the fixtures directory, and the `nfs` marker.

Run (from the code root): bin/atlas test    (= <env>/bin/python -m pytest; pyproject.toml holds the pytest config)
Tests marked @pytest.mark.nfs need the project data on /n/fs (packages, stores, sweeps). They run locally and are
skipped in CI (CS_ATLAS_CI=1, or `atlas test --ci`, or -m 'not nfs'); a test that needs data it cannot find skips itself.
"""
import json
import os
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def pytest_collection_modifyitems(config, items):
    if os.environ.get('CS_ATLAS_CI') == '1':
        skip = pytest.mark.skip(reason='needs the NFS project data (CS_ATLAS_CI=1)')
        for item in items:
            if 'nfs' in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def fixture_json():
    def load(name):
        return json.loads((FIXTURES / name).read_text())
    return load
