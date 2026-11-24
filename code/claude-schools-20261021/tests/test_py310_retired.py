"""ROADMAP #23: only the ML studies in ai-writing/ may still name the py310 env; everything else runs on env/atlas."""
import subprocess
from pathlib import Path

import atlas_paths as P

CODE = Path(__file__).resolve().parents[1]
MOVED = ['fulltext-push/ledger.slurm', 'fulltext-push/recover-1030.slurm', 'fulltext-push/channels-1030.slurm', 'fulltext-push/identity-alt.slurm',
         'fulltext-push/school-channels.slurm', 'ai-writing/fulltext.slurm', 'ai-writing/citations/fetch_new.slurm', 'ai-writing/citations/fetchers.slurm']
STUDY_ONLY_IMPORTS = ('torch', 'transformers', 'vllm', 'sklearn', 'pandas', 'scipy', 'matplotlib', 'PIL', 'joblib')


def test_collector_py_is_the_project_env():
    assert str(P.COLLECTOR_PY) == str(P.PY)
    assert 'anaconda' not in (CODE / 'paths.sh').read_text()


def test_only_ai_writing_names_py310():
    out = subprocess.run(['git', 'grep', '-lE', 'CS_ATLAS_ENV_(PY|LIB)|P\\.ENV_(PY|LIB)', '--', '.'], cwd=CODE, capture_output=True, text=True).stdout.split()
    allowed = ('ai-writing/', 'archive/', 'paths.sh', 'tests/test_py310_retired.py', 'tools/atlas_paths.py', 'tools/route_paths.py', 'docs/')
    assert [f for f in out if not f.startswith(allowed)] == []


def test_moved_scripts_use_the_project_env_and_need_no_study_packages():
    for f in MOVED:
        text = (CODE / f).read_text()
        assert 'ENV_PY' not in text and 'ENV_LIB' not in text, f
    for f in ('ai-writing/fulltext.py', 'ai-writing/citations/fetch.py', 'ai-writing/citations/s2fetch.py'):
        src = (CODE / f).read_text()
        assert not any(f'import {m}' in src or f'from {m}' in src for m in STUDY_ONLY_IMPORTS), f
