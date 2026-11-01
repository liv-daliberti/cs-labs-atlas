"""tools/relocate_data.py (dry run only): the plan for the flat -> split data layout on a fake tree in tmp_path."""
import os
import subprocess

import json
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
    assert D.readiness(fake)['direct_joins'] == {'tools/joins.py': 1}      # the comment line is not counted
    assert D.readiness(fake)['gitignore_plan'] == [('!hierarchy/mit/gap-evidence.json', '!hierarchy/mit/reviewed/gap-evidence.json')]
    assert pl['missing']                                                 # table entries with no file are listed, not moved


def test_dry_run_moves_nothing_and_has_no_apply(fake):
    before = sorted(str(p) for p in fake.rglob('*') if '.git' not in p.parts)
    D.plan(fake, ['mit', 'princeton'])
    assert sorted(str(p) for p in fake.rglob('*') if '.git' not in p.parts) == before
    


def test_gitignore_translation():
    t = D.gitignore_translate
    assert t('!hierarchy/*/gap-evidence.json') == '!hierarchy/*/reviewed/gap-evidence.json'
    assert t('!hierarchy/census-overrides.json') == '!hierarchy/reviewed/census-overrides.json'
    assert t('!hierarchy/stanford/tobagi-review.json') == '!hierarchy/stanford/reviewed/tobagi-review.json'
    assert t('!hierarchy/nicknames/*.csv') == '!hierarchy/reviewed/nicknames/*.csv'
    assert t('!census/*-additions.json') == '!hierarchy/*/reviewed/census-additions.json'
    assert t('!hierarchy/labpage-tools-cmu/worker_brief.txt') == '!hierarchy/labpage-tools-cmu/worker_brief.txt'
    assert t('!hierarchy/unknown-thing.json') is None


def ready(fake, monkeypatch):
    monkeypatch.setattr(D, 'readiness', lambda root: dict(direct_joins={}, gitignore_lines=[], gitignore_unmapped=[],
                                                          gitignore_plan=[('!hierarchy/*/gap-evidence.json', '!hierarchy/*/reviewed/gap-evidence.json')]))
    monkeypatch.setattr(D.R, 'busy_processes', lambda sources: [])


def git(root, *a):
    return subprocess.run(['git', '-C', str(root), '-c', 'user.name=t', '-c', 'user.email=t@e.org', *a], capture_output=True, text=True, check=True).stdout


def test_apply_moves_commits_flips_and_verifies(fake, monkeypatch, tmp_path):
    ready(fake, monkeypatch)
    (fake / 'tools' / 'atlas_paths.py').write_text("DATA_LAYOUT_DEFAULT = 'flat'\n")
    (fake / 'paths.sh').write_text('old\n')
    (fake / 'hierarchy' / 'CHAIN-AUDIT.md').unlink()
    (fake / 'hierarchy' / 'mit' / 'STAGE-3.md').unlink()
    (fake / '.gitignore').write_text('*\n!*/\n!.gitignore\n!*.py\n!paths.sh\n!hierarchy/*/gap-evidence.json\n')
    git(fake, 'add', '-A'); git(fake, 'commit', '-qm', 'base')
    (fake / 'hierarchy' / 'mit' / 'pis.json').write_text('[1]')            # untracked derived file
    shutil_rm = __import__('shutil').rmtree
    shutil_rm(fake / 'hierarchy' / 'princeton')                            # the conflict fixture is not part of this test
    pl = D.plan(fake, ['mit'])
    assert not pl['conflicts']
    rec = tmp_path / 'rec.jsonl'
    regen = []
    n = D.apply(pl, 'tester', rec, code_root=fake, regen=lambda r: regen.append(r) or (fake / 'paths.sh').write_text('split\n'))
    assert n == len(pl['moves']) and regen == [fake]
    assert (fake / 'hierarchy' / 'mit' / 'derived' / 'pis.json').read_text() == '[1]' and not (fake / 'hierarchy' / 'mit' / 'pis.json').exists()
    assert (fake / 'hierarchy' / 'mit' / 'reviewed' / 'gap-evidence.json').exists()                    # a tracked file, by git mv
    assert "DATA_LAYOUT_DEFAULT = 'split'" in (fake / 'tools' / 'atlas_paths.py').read_text()
    assert '!hierarchy/*/reviewed/gap-evidence.json' in (fake / '.gitignore').read_text()
    assert git(fake, 'log', '--format=%s', '-1').startswith('Data layout:') and git(fake, 'status', '--porcelain', '--untracked-files=no').strip() == ''
    kinds = [json.loads(x)['kind'] for x in rec.read_text().splitlines()]
    assert kinds[0] == 'start' and 'git-mv' in kinds and 'rename' in kinds and kinds[-1] == 'done'
    assert D.verify(rec, fake) == []
    (fake / 'hierarchy' / 'mit' / 'pis.json').write_text('stray')
    assert any('a flat path is left' in p for p in D.verify(rec, fake))


def test_apply_refuses_on_blockers(fake, monkeypatch, tmp_path):
    ready(fake, monkeypatch)
    pl = D.plan(fake, ['mit', 'princeton'])                                # princeton's destination exists: a conflict
    with pytest.raises(SystemExit, match='refused'):
        D.apply(pl, 'tester', tmp_path / 'r.jsonl', code_root=fake)
    assert (fake / 'hierarchy' / 'mit' / 'pis.json').exists() and not (tmp_path / 'r.jsonl').exists()
    pl2 = D.plan(fake, ['mit'])
    pl2['conflicts'] = []
    for key, val in (('busy', [(1, 'cwd', '/x')]), ('journals', ['/x-journal']), ('loop_locks', {'/s/.loop.lock': True}), ('jobs', ['9 job RUNNING'])):
        bad = dict(pl2, preflight=dict(pl2['preflight'], **{key: val}))
        assert D.preflight_blockers(bad), key
    assert D.preflight_blockers(dict(pl2, readiness=dict(pl2['readiness'], direct_joins={'tools/x.py': 2})))
    assert D.preflight_blockers(pl2) == []
