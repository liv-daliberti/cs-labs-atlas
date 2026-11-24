"""PROTOCOL-FRICTION R1 (UChicago, 2026-11-02): school_web.py is a download entry point and runs under `python -I`, which leaves its own directory off sys.path."""
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / 'tools' / 'school_web.py'


def test_runs_under_python_dash_I():
    r = subprocess.run([sys.executable, '-I', str(TOOL)], capture_output=True, text=True, cwd='/')
    assert 'ModuleNotFoundError' not in r.stderr and 'No module named' not in r.stderr
    assert r.returncode != 0 and 'school_web.py <key> cdx' in r.stderr          # a usage message, not a traceback
    assert 'Traceback' not in r.stderr
