"""wayback-acm-vol.slurm takes turns with the rotator's downloads: a bounded run, then a PENDING successor; no successor when nothing is left."""
import subprocess
from pathlib import Path

JOB = Path(__file__).resolve().parents[1] / 'fulltext-push' / 'wayback-acm-vol.slurm'


def test_syntax():
    assert subprocess.run(['bash', '-n', str(JOB)]).returncode == 0


def test_bounded_turn_and_pending_successor():
    s = JOB.read_text()
    assert 'END=$(( $(date +%s) + ${RUN_S:-5400} ))' in s and 'timeout -s INT "$left"' in s
    assert '--begin="now+${GAP_S:-5400}"' in s and '#SBATCH --time=03:00:00' in s
    assert 'run_steps-wayback_acm_vol.lock' in s and "'\"stopped\"' && break" in s
    assert '"wayback_acm_vol_papers_to_ask": 0,' in s and "'{\"wayback-acm-vol\": \"done\"}'" in s
