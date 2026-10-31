"""The build gives the same output whatever Python's str hash seed (2026-10-31): two runs of the stages on the fixture
school of test_build_rules.py, in subprocesses with different PYTHONHASHSEED values, must write identical data. Before
the fix, set iteration over PI names decided the order of the labs and, through shared source dicts, the re-captured
evidence of a student in several labs (R-STU-08)."""
import json
import os
import subprocess
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
RUN = '''
import json, sys
sys.path.insert(0, {tests!r}); sys.path.insert(0, {tools!r})
from pathlib import Path
import test_build_rules as T
ctx = T.run_stages(Path({root!r}))
for r in ctx.rows:
    r.pop('_bylines', None)
print(json.dumps(dict(pis=ctx.pis, students={{k: list(v.values()) for k, v in ctx.stu.items()}}, rows=ctx.rows, links=ctx.sp,
                      counts=ctx.n), default=str))
'''


def run(root, seed):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    code = RUN.format(tests=str(TESTS), tools=str(TESTS.parent / 'tools'), root=str(root))
    return subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True, env=env).stdout


def test_R_STU_08_build_is_independent_of_the_hash_seed(tmp_path):
    import test_build_rules as T
    T.write_school(tmp_path)
    T.write_shared_advising(tmp_path)          # one context naming three advisers, with re-captured evidence per lab
    outs = {run(tmp_path, s) for s in range(8)}
    assert len(outs) == 1, 'the build output depends on PYTHONHASHSEED'
    assert json.loads(next(iter(outs)))['students']
