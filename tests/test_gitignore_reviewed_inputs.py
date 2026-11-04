"""A reviewed school-local input that is not whitelisted in .gitignore never reaches the branch (Georgia Tech friction 21: cs-related-hand.json was silently
left out of the first commit, and sync_school_files, which copies what .gitignore admits, skipped it too)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_hand_evidence_file_is_admitted_by_gitignore():
    for name in ('cs-related-hand.json', 'cs-related-review.json', 'census-additions.json'):
        r = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', f'hierarchy/gatech/reviewed/{name}'], capture_output=True)
        assert r.returncode == 1, f'{name} is ignored by .gitignore'
