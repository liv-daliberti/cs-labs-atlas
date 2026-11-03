"""The per-school build runs newest school first (owner 2026-11-03), so a school still settling in fails soonest."""
import re
import subprocess
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]


def test_rebuild_builds_newest_school_first():
    line = next(l for l in (CODE / 'hierarchy' / 'rebuild.sh').read_text().splitlines() if l.strip().startswith('BUILD_ORDER='))
    out = subprocess.run(['bash', '-c', 'SCHOOLS="princeton cmu michigan"; ' + line.strip() + '; echo $BUILD_ORDER'],
                         capture_output=True, text=True, check=True).stdout.split()
    assert out == ['michigan', 'cmu', 'princeton']
    assert re.search(r'for s in \$BUILD_ORDER; do .*pi_hierarchy\.py', (CODE / 'hierarchy' / 'rebuild.sh').read_text())


def test_parallel_rebuild_puts_newest_school_at_task_0():
    line = next(l for l in (CODE / 'hierarchy' / 'submit-parallel.sh').read_text().splitlines() if 'tac' in l and l.startswith('SCHOOLS='))
    out = subprocess.run(['bash', '-c', 'SCHOOLS="princeton cmu michigan"; ' + line.split('#')[0].strip() + '; echo $SCHOOLS'],
                         capture_output=True, text=True, check=True).stdout.split()
    assert out == ['michigan', 'cmu', 'princeton']
