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


READER = '''
import hashlib, json, sys, tempfile
sys.path.insert(0, {tests!r}); sys.path.insert(0, {tools!r})
from pathlib import Path
from _pytest.monkeypatch import MonkeyPatch
import test_reader_export as T
import reader_export as R
tmp = Path(tempfile.mkdtemp())
mp = MonkeyPatch()
papers = T.make_store(tmp, mp)
A = R.ArxivLicenses()
A.add_body(dict(id='https://openalex.org/W1', locations=[dict(id='pmh:oai:arXiv.org:1111.1111', landing_page_url='https://arxiv.org/abs/1111.1111', license='cc-by'),
                                                      dict(id='pmh:oai:arXiv.org:2222.2222', landing_page_url='https://arxiv.org/abs/2222.2222', license=None)]))
recs, stats, chk, reqs = R.school_rows('mit', papers, A, frozenset([T.SHA(1), T.SHA(3), T.SHA(5)]))
hosted = R.hosted_not_permitted({{T.SHA(i): dict(bytes=1, path='p') for i in (1, 3, 5, 99)}}, {{'mit': chk}})
out = tmp / 'out'
R.write_outputs({{'mit': recs}}, {{'mit': stats}}, hosted, out, '2026-11-01T00:00:00Z', None, requests={{'mit': reqs}})
print(json.dumps({{f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir())}}))
'''

NOTES = '''
import sys
sys.path.insert(0, {tests!r}); sys.path.insert(0, {tools!r})
import release_notes as RN
import test_release_notes as T
print(RN.render(T.REG, '2026-11-01.1', '2026-10-29.4', [dict(id='R-A-01', decided='x'), dict(id='R-B-02', decided='y')], [dict(id='R-A-01', decided='x')]))
'''

RESOLVE = '''
import json, sys
sys.path.insert(0, {tools!r})
import lab_paper_copies as L
rows = [dict(work=None, oa='https://openalex.org/W%d' % i, doi='10.1/x%d' % (i % 5), title='Paper %d about graphs' % (i % 7), year=2020, editions=[dict(work=None, oa='https://openalex.org/W%d' % (i + 50), doi='10.1/y%d' % i)]) for i in range(40)]
status = {{'mit_oa_W%d' % i: ('downloaded' if i % 3 == 0 else 'queued') for i in range(40)}}
by_doi = {{'10.1/x%d' % (i % 5): 'mit_oa_W%d' % i for i in range(40)}}
local_titles = {{'paper3aboutgraphs'}}
out, n = L.resolve('mit', rows, status, by_doi, local_titles)
print(json.dumps([out, dict(n)], sort_keys=True))
'''


def run_script(src, seed, **kw):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    code = src.format(tests=str(TESTS), tools=str(TESTS.parent / 'tools'), **kw)
    return subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True, env=env).stdout


def test_reader_export_is_independent_of_the_hash_seed():
    """Same inputs -> the same bytes in every reader file (ROADMAP #22)."""
    outs = {run_script(READER, s) for s in range(6)}
    assert len(outs) == 1, 'reader export output depends on PYTHONHASHSEED'
    assert 'SUMMARY.json' in json.loads(next(iter(outs)))


def test_release_notes_are_independent_of_the_hash_seed():
    assert len({run_script(NOTES, s) for s in range(4)}) == 1


def test_coverage_counter_resolution_is_independent_of_the_hash_seed():
    assert len({run_script(RESOLVE, s) for s in range(6)}) == 1


def test_gzip_text_writes_identical_bytes_whenever_it_runs(tmp_path):
    import time
    import atlas_paths as P
    outs = []
    for i in range(2):
        f = tmp_path / f'a{i}.jsonl.gz'
        with P.gzip_text(f) as g:
            g.write('{"a": 1}\n')
        time.sleep(1.1)   # the default gzip header carries the clock in seconds
        outs.append(f.read_bytes())
    assert outs[0] == outs[1]
