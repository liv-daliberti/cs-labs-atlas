"""tools/relocate_data.py (dry run only): the plan for the flat -> split data layout on a fake tree in tmp_path."""
import os
import subprocess

import pytest

import relocate_data as D


@pytest.fixture
def fake(tmp_path, monkeypatch):
    root = tmp_path / 'code'
    H = root / 'hierarchy'
    for p in ['mit/tmp', 'princeton']:
        (H / p).mkdir(parents=True)
    (root / 'tools').mkdir()
    (H / 'mit' / 'pis.json').write_text('[]')                       # derived, untracked
    (H / 'mit' / 'gap-evidence.json').write_text('[]')              # reviewed, tracked
    (H / 'mit' / 'STAGE-3.md').write_text('x')
    (H / 'CHAIN-AUDIT.md').write_text('x')
    (H / 'princeton' / 'pis.json').write_text('[]')
    (H / 'princeton' / 'raw').mkdir()
    (H / 'princeton' / 'derived').mkdir()
    (H / 'princeton' / 'derived' / 'pis.json').write_text('[]')     # a destination that exists: a conflict
    (root / '.gitignore').write_text('!hierarchy/mit/gap-evidence.json\n')
    (root / 'tools' / 'joins.py').write_text("p = HIERARCHY / 'x'\n# HIERARCHY / 'comment'\n")
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.gitignore', 'hierarchy/mit/gap-evidence.json', 'tools/joins.py'], check=True)
    monkeypatch.setattr(D, 'jobs', lambda: [])
    monkeypatch.setattr(D.R, 'store_locks', lambda dirs: {})
    return root


def test_plan_lists_moves_conflicts_and_readiness(fake):
    pl = D.plan(fake, ['mit', 'princeton'])
    by_old = {os.path.relpath(m['old'], fake): m for m in pl['moves']}
    assert os.path.relpath(by_old['hierarchy/mit/pis.json']['new'], fake) == 'hierarchy/mit/derived/pis.json'
    assert by_old['hierarchy/mit/gap-evidence.json']['tracked'] and not by_old['hierarchy/mit/pis.json']['tracked']
    assert os.path.relpath(by_old['hierarchy/mit/tmp']['new'], fake) == 'hierarchy/mit/work/tmp'
    assert os.path.relpath(by_old['hierarchy/mit/STAGE-3.md']['new'], fake) == 'hierarchy/mit/reports/STAGE-3.md'
    assert os.path.relpath(by_old['hierarchy/CHAIN-AUDIT.md']['new'], fake) == 'hierarchy/derived/CHAIN-AUDIT.md'
    assert [os.path.relpath(c['old'], fake) for c in pl['conflicts']] == ['hierarchy/princeton/pis.json']   # destination exists
    assert pl['readiness']['direct_joins'] == {'tools/joins.py': 1}      # the comment line is not counted
    assert pl['readiness']['gitignore_lines'] == ['!hierarchy/mit/gap-evidence.json']
    assert pl['missing']                                                 # table entries with no file are listed, not moved


def test_dry_run_moves_nothing_and_has_no_apply(fake):
    before = sorted(str(p) for p in fake.rglob('*') if '.git' not in p.parts)
    D.plan(fake, ['mit', 'princeton'])
    assert sorted(str(p) for p in fake.rglob('*') if '.git' not in p.parts) == before
    assert not hasattr(D, 'apply') and '--apply' not in open(D.__file__).read().split('def main')[1]
