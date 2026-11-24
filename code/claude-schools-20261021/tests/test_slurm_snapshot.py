"""Every Slurm script of the atlas runs from a code snapshot (docs/CONTRIBUTING.md, tools/job_code_snapshot.sh; ROADMAP #16): a landing
rewrites the main checkout's files, and a job importing code from there can see half a commit. A script must source the snapshot helper
(fulltext-push/job_snapshot.sh sources it for the collectors) or hand over to hierarchy/rebuild.sh, which takes its own snapshot.
Exempt: archive/ (retired) and ai-writing/ (the ML studies run their own environment and import nothing from the atlas build)."""
import subprocess
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
OK = ('job_code_snapshot.sh', 'job_snapshot.sh', 'hierarchy/rebuild.sh')


def test_every_slurm_script_runs_from_a_snapshot():
    files = subprocess.run(['git', '-C', str(CODE), 'ls-files', '*.slurm'], capture_output=True, text=True).stdout.split()
    bad = [f for f in files if not f.startswith(('archive/', 'ai-writing/')) and not any(k in (CODE / f).read_text() for k in OK)]
    assert not bad, f'source tools/job_code_snapshot.sh (or fulltext-push/job_snapshot.sh) after paths.sh, or retire to archive/: {bad}'
