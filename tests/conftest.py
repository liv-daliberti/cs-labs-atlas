"""Shared setup: the tools directory on sys.path, and the fixtures directory.

Run (from work/): LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib /n/fs/resemble/cs-atlas-env/py310/bin/python -m pytest tests -q
"""
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
FIXTURES = Path(__file__).resolve().parent / 'fixtures'


@pytest.fixture
def fixture_json():
    def load(name):
        return json.loads((FIXTURES / name).read_text())
    return load
