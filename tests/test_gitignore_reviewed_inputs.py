"""A reviewed school-local input that is not whitelisted in .gitignore never reaches the branch (Georgia Tech friction 21: cs-related-hand.json was silently
left out of the first commit, and sync_school_files, which copies what .gitignore admits, skipped it too)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_hand_evidence_file_is_admitted_by_gitignore():
    for name in ('cs-related-hand.json', 'cs-related-review.json', 'census-additions.json'):
        r = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', f'hierarchy/gatech/reviewed/{name}'], capture_output=True)
        assert r.returncode == 1, f'{name} is ignored by .gitignore'


# files of reviewed/ that a step REGENERATES from raw captures (never hand decisions); everything else an onboarding school keeps in reviewed/ must be tracked
GENERATED = {'labpage-evidence.json', 'directory-evidence.json', 'profile-year-evidence.json'}


def onboarding_schools():
    import tomllib
    return [p.stem for p in sorted((ROOT / 'schools').glob('*.toml')) if p.stem != 'TEMPLATE' and tomllib.loads(p.read_text()).get('status') == 'onboarding']


def test_every_student_input_of_an_onboarding_school_is_admitted_by_gitignore():
    """The student build reads these from reviewed/ (tools/pihier/students.py RESEARCHED_FILES and the decisions): ignored means a release built from a
    git-archive snapshot silently loses the relations (UChicago thesis-evidence.json, 2026-11-04)."""
    from pihier.students import RESEARCHED_FILES
    names = (set(RESEARCHED_FILES) - GENERATED) | {'student-decisions.json', 'labpage-additions.json', 'labpage-acceptance.json', 'labpage-handcheck.json', 'lab-coverage-reasons.json'}
    for school in onboarding_schools():
        for name in sorted(names):
            r = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', f'hierarchy/{school}/reviewed/{name}'], capture_output=True)
            assert r.returncode == 1, f'hierarchy/{school}/reviewed/{name} is ignored by .gitignore'


def test_no_ignored_file_sits_in_an_onboarding_schools_reviewed_directory():
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--others', '--ignored', '--exclude-standard'], capture_output=True, text=True).stdout.split('\n')
    bad = [f for f in out for s in onboarding_schools() if f.startswith(f'hierarchy/{s}/reviewed/') and f.rsplit('/', 1)[-1] not in GENERATED]
    assert not bad, f'reviewed files that git ignores (add them to the .gitignore whitelist or move them): {bad}'
