"""atlas_cli: the `atlas <command>` dispatcher."""
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]


def test_dispatcher_lists_commands():
    out = subprocess.run([sys.executable, '-m', 'atlas_cli', 'help'], cwd=CODE, capture_output=True, text=True, check=True).stdout
    for c in ('build', 'release', 'copies', 'ledger', 'stage-gate', 'collect', 'test'):
        assert f'  {c} ' in out
