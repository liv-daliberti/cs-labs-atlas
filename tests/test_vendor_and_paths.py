"""vendor/ matches its provenance (tools/vendor_sync.py), and tools/route_paths.py rewrites hardcoded paths faithfully."""
import subprocess
import warnings
from pathlib import Path

import pytest

import atlas_paths as P
import route_paths as R
import vendor_sync as V

CODE = Path(__file__).resolve().parents[1]


def test_vendored_files_match_provenance():
    rows = V.provenance()
    assert {r['vendored'] for r in rows} == {f'{o}/{n}' for o, (_, _, fs) in V.ORIGINS.items() for n in fs}
    for r in rows:
        assert V.sha((CODE / 'vendor' / r['vendored']).read_bytes()) == r['vendored_sha256'], r['vendored']
        assert len(r['source_sha256']) == 64


def test_vendored_code_compiles():
    for f in sorted((CODE / 'vendor').glob('*/*.py')):
        compile(f.read_text(), str(f), 'exec')
        assert not V.LEFTOVER.search(f.read_text()), f


@pytest.mark.nfs
def test_vendored_sources_have_not_drifted():
    rows = V.provenance()
    drift = [r['source'] for r in rows if Path(r['source']).exists() and V.sha(Path(r['source']).read_bytes()) != r['source_sha256']]
    if drift:  # an original changed after vendoring: review it, then tools/vendor_sync.py sync
        warnings.warn(f'vendored sources changed since vendoring: {drift}')


def test_route_python_literal():
    src = "import os\nk = 1\nX = '/n/fs/resemble/cs-atlas/work/hierarchy/mit'\nY = f'/n/fs/resemble/maxent-grpo/.research-sweeps/a/{k}.json'\n"
    out, n, unresolved = R.py_fix('tools/x.py', src)
    assert n == 2 and not unresolved
    assert "X = str(P.HIERARCHY / 'mit')" in out and "Y = f'{P.SWEEPS}/a/{k}.json'" in out
    assert "parents[1] / 'tools'" in out and 'import atlas_paths as P' in out
    ns = {'__file__': str(CODE / 'tools/x.py')}
    exec(compile(out, 'x', 'exec'), ns)  # noqa: S102 (the rewritten module must give the same value today)
    assert ns['X'] == str(P.HIERARCHY / 'mit')
    assert R.legacy_value('HIERARCHY', 'mit') == '/n/fs/resemble/cs-atlas/work/hierarchy/mit'


def test_route_python_keeps_docstrings_and_concatenation():
    src = '"""Reads /n/fs/resemble/cs-atlas/work/hierarchy."""\nA = ("/n/fs/resemble/cs-atlas/work/" "x")\nB = "{}".format(1)\n'
    out, n, _ = R.py_fix('hierarchy/t/y.py', src)
    assert out.startswith('"""Reads /n/fs/resemble/cs-atlas/work/hierarchy."""') and n == 1
    assert 'A = (f"{P.CODE}/" "x")' in out and "parents[2]" in out
    compile(out, 'y', 'exec')


def test_route_python_uses_existing_handle():
    src = "import ftp_common as F\nPY = '/usr/local/anaconda3/2024.02/bin/python'\n"
    out, n, _ = R.py_fix('fulltext-push/z.py', src)
    assert out == "import ftp_common as F\nPY = str(F.P.COLLECTOR_PY)\n"


def test_route_shell():
    src = ('#!/bin/bash\n#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/x-%j.out\n'
           '. /n/fs/resemble/cs-atlas/work/paths.sh\n/usr/local/anaconda3/2024.02/bin/python -I /n/fs/resemble/cs-atlas/work/tools/a.py\n')
    out, n, unresolved = R.sh_fix('hierarchy/run.slurm', src)
    assert '#SBATCH --output=fulltext-push/logs/x-%j.out' in out
    assert '${SLURM_SUBMIT_DIR:?}}/paths.sh' in out and '${CS_ATLAS_PY} -I ${CS_ATLAS_TOOLS}/a.py' in out and not unresolved
    out2, _, _ = R.sh_fix('hierarchy/tools-x/run.sh', '#!/bin/bash\ncat /n/fs/resemble/cs-atlas/releases/latest/x\n')
    assert '/../.." && pwd)/paths.sh' in out2 and 'cat ${CS_ATLAS_RELEASES}/latest/x' in out2
    assert subprocess.run(['bash', '-n'], input=out2, text=True).returncode == 0


def test_route_check_flags_code_not_comments(tmp_path, monkeypatch):
    f = tmp_path / 'tools' / 'q.py'
    f.parent.mkdir()
    f.write_text("# see /n/fs/resemble/cs-atlas/work\nX = '/n/fs/resemble/cs-labs-atlas'\n")
    code, notes = R.py_findings(f.read_text())
    assert [p for _, p in code] == ['/n/fs/resemble/cs-labs-atlas'] and len(notes) == 1
