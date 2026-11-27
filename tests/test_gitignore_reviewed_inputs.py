"""A reviewed school-local input that is not whitelisted in .gitignore never reaches the branch (Georgia Tech friction 21: cs-related-hand.json was silently
left out of the first commit, and sync_school_files, which copies what .gitignore admits, skipped it too)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_hand_evidence_file_is_admitted_by_gitignore():
    for name in ('cs-related-hand.json', 'cs-related-review.json', 'census-additions.json'):
        r = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', f'hierarchy/gatech/reviewed/{name}'], capture_output=True)
        assert r.returncode == 1, f'{name} is ignored by .gitignore'


# files of reviewed/ that a step REGENERATES from raw captures (never hand decisions); the rest the builds read must be tracked
GENERATED = {'labpage-evidence.json', 'directory-evidence.json', 'profile-year-evidence.json', 'defense-evidence.json'}
# registered as reviewed inputs but not read by any build or release step (agent briefs and step inputs kept as data, 2026-11-04 audit)
NOT_READ = {'cs-related-home-departments.json', 'few-students-input.json', 'gap-input.json', 'labpage-input.json', 'departures-20261031.json',
            'listings-input.json'}   # the step input the 2026-11-26 school-layout move brought in from hierarchy/reviewed/listings-input-<school>.json (SHARED_DATA below)
# the shared directory: listings-input-<school>.json are step inputs too; reader/link-verdicts.jsonl is the downloads agent's growing landing-page
# verdict file (1 MB, written by tools/link_check.py), left as data until the owner decides (ROADMAP #46)
SHARED_DATA = ('listings-input-', 'reader/link-verdicts.jsonl')


def schools():
    """Every school with a charter, released or onboarding."""
    return [p.stem for p in sorted((ROOT / 'schools').glob('*.toml')) if p.stem != 'TEMPLATE']


def onboarding_schools():
    import tomllib
    return [s for s in schools() if tomllib.loads((ROOT / 'schools' / f'{s}.toml').read_text()).get('status') == 'onboarding']


def admitted(rel):
    return subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', rel], capture_output=True).returncode == 1


def test_every_reviewed_input_the_builds_read_is_admitted_by_gitignore_for_all_schools():
    """The student build reads these from reviewed/ (tools/pihier/students.py RESEARCHED_FILES and the decisions), the identity build the PI publication
    lists: ignored means a release built from a git-archive snapshot silently loses the relations (UChicago thesis-evidence.json, 2026-11-04; the
    released schools' thesis-evidence, thesis-held-years-evidence and pi-publication-lists were ignored until the all-school audit)."""
    from pihier.students import RESEARCHED_FILES
    names = (set(RESEARCHED_FILES) - GENERATED) | {'student-decisions.json', 'labpage-additions.json', 'labpage-acceptance.json', 'labpage-handcheck.json',
                                                   'lab-coverage-reasons.json', 'pi-publication-lists.json', 'cs-related-review.json', 'census-additions.json',
                                                   'faculty-periods.json', 'missing-pi-review.json', 'gap-evidence.json', 'relation-evidence.json',
                                                   'openalex-identity-review.json', 'gap-year-evidence.json', 'census-overrides-school.json'}
    assert len(schools()) >= 9
    for school in schools():
        for name in sorted(names):
            assert admitted(f'hierarchy/{school}/reviewed/{name}'), f'hierarchy/{school}/reviewed/{name} is ignored by .gitignore'  # route-ok: recorded wording or a path-rewrite fixture, not a data path


def test_the_shared_reviewed_inputs_are_admitted_by_gitignore():
    for name in ('census-overrides.json', 'home-departments.json', 'chain-reasons.json', 'student-corrections.json', 'student-identity-review.json',
                 'student-name-candidates.json', 'zero-paper-review.json', 'cs-venues.json', 'labpage-departure-review.json', 'nicknames/names.csv'):
        assert admitted(f'hierarchy/reviewed/{name}'), f'hierarchy/reviewed/{name} is ignored by .gitignore'


def test_no_unexplained_ignored_file_sits_in_a_reviewed_directory():
    """On a checkout with the data (the main one): a file git ignores in hierarchy/<school>/reviewed/ or hierarchy/reviewed/ is either regenerated, not
    read, or a recorded decision above. Anything else is a reviewed input the builds read that never reaches git."""
    paths = [f'hierarchy/{s}/reviewed' for s in schools()] + ['hierarchy/reviewed']  # route-ok: recorded wording or a path-rewrite fixture, not a data path
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--others', '--ignored', '--exclude-standard', '--', *paths], capture_output=True, text=True).stdout.split('\n')
    def explained(f):
        shared = 'hierarchy' + '/reviewed/'   # the .gitignore path, not a data path (tests/test_tests_use_atlas_paths.py)
        if f.startswith(shared):
            return f.startswith(tuple(shared + x for x in SHARED_DATA))
        return f.rsplit('/', 1)[-1] in GENERATED | NOT_READ
    bad = [f for f in out if f and not explained(f)]
    assert not bad, f'reviewed files that git ignores (add them to the .gitignore whitelist or to the lists in this test with the reason): {sorted(bad)}'
