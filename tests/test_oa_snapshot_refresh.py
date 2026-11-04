"""The snapshot refresh planner, compare and promote on fixture stores (no network, no Slurm)."""
import sqlite3

import pytest

import atlas_paths as P  # noqa: E402
import oa_snapshot as S  # noqa: E402
import oa_snapshot_refresh as R  # noqa: E402


def store(root, date, works, ext=None):
    d = root / date
    d.mkdir(parents=True)
    for name, rows in [('openalex.sqlite', works)] + ([(f'ext-{ext[0]}.sqlite', ext[1])] if ext else []):
        db = sqlite3.connect(d / name)
        db.executescript(S.SCHEMA)
        db.executemany('INSERT INTO work_inst VALUES (?,?)', rows)
        db.commit(); db.close()
    if ext:
        (d / f'ext-{ext[0]}.manifest.json').write_text('{}')


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / 'snap'
    store(r, '2026-10-14', [('W1', 'I1'), ('W2', 'I1'), ('W3', 'I2')], ext=('newu', [('W9', 'I9')]))
    (r / 'current').symlink_to('2026-10-14')
    monkeypatch.setattr(P, 'OA_SNAPSHOT', r)
    return r


def man(date):
    return lambda entity: (date, [])


def test_plan_states(root):
    assert R.plan(root=root, manifest=man('2026-10-14'), charters=['a', 'newu'])['status'] == 'up-to-date'
    assert R.plan(root=root, manifest=man('2027-01-13'), charters=['a', 'newu'])['status'] == 'refresh'
    assert R.plan(root=root, manifest=man('2027-01-13'), charters=['a'])['status'] == 'blocked'   # extension school without a charter
    (root / '2027-01-13').mkdir(); (root / '2027-01-13' / 'openalex.sqlite').write_text('')
    assert R.plan(root=root, manifest=man('2027-01-13'), charters=['a', 'newu'])['status'] == 'exists'  # never in place


def test_dry_run_submits_nothing(root):
    calls = []
    pl, shown = R.submit(None, False, True, run=lambda *a, **k: calls.append(a), root=root, manifest=man('2027-01-13'), charters=['a', 'newu'])
    assert not calls and pl['status'] == 'refresh' and [n for n, _ in shown] == ['filter', 'merge', 'compare']


def test_compare_then_promote_only_when_clean(root):
    ids = {'a': ['I1'], 'newu': ['I9']}
    store(root, '2027-01-13', [('W1', 'I1'), ('W2', 'I1'), ('W4', 'I1'), ('W3', 'I2'), ('W9', 'I9')])
    rep = R.compare('2027-01-13', root=root, sweep_ids=lambda k: ids[k], schools=['a', 'newu'])
    assert rep['ok'] and {r['school']: (r['old'], r['new']) for r in rep['schools']} == {'a': (2, 3), 'newu': (1, 1)}
    assert (root / '2027-01-13' / 'refresh-compare.json').exists() and (root / 'current').readlink().name == '2026-10-14'  # compare does not promote
    R.promote('2027-01-13', root=root)
    assert (root / 'current').readlink().name == '2027-01-13'


def test_a_school_that_loses_works_blocks_promotion(root):
    store(root, '2027-01-13', [('W1', 'I1')])
    rep = R.compare('2027-01-13', root=root, sweep_ids=lambda k: ['I1'], schools=['a'])
    assert not rep['ok']
    with pytest.raises(SystemExit):
        R.promote('2027-01-13', root=root)
    assert (root / 'current').readlink().name == '2026-10-14'
    R.promote('2027-01-13', root=root, force=True)


def test_promote_needs_compare(root):
    store(root, '2027-01-13', [('W1', 'I1')])
    with pytest.raises(SystemExit):
        R.promote('2027-01-13', root=root)


def test_submit_chain_pins_dependencies(root):
    got = []
    def fake(argv, **k):
        got.append(argv)
        return type('R', (), dict(returncode=0, stdout=f'{100 + len(got)}\n', stderr=''))()
    pl, _ = R.submit(None, True, False, run=fake, root=root, manifest=man('2027-01-13'), charters=['a', 'newu'])
    assert [a for a in got[1] if a.startswith('--dependency')] == ['--dependency=afterok:101'] and len(got) == 4 and pl['jobs']['promote'] == '104'
