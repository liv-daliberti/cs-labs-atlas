"""tools/scratch.py: what clean removes, on a fake tree (nothing outside tmp_path)."""
import os
import time
import json

import pytest

import scratch as S


def age(p, days):
    t = time.time() - days * 86400
    os.utime(p, (t, t))


def test_candidates_by_age_keep_and_snapshots(tmp_path):
    sc, logs, eq = tmp_path / 'scratch', tmp_path / 'logs', tmp_path / 'wt' / '.equiv'
    for d in (sc / 'old-trial', sc / 'new-trial', sc / 'old-kept', logs / 'pkg-before-a', logs / 'pkg-before-b', logs / 'pkg-before-c', logs / 'other.log', eq / 'r1', eq / 'keep-r2'):
        d.mkdir(parents=True)
    (sc / 'old-kept' / 'KEEP').write_text('')
    for p, days in ((sc / 'old-trial', 30), (sc / 'old-kept', 30), (logs / 'pkg-before-a', 30), (logs / 'pkg-before-b', 20), (logs / 'pkg-before-c', 20),
                    (logs / 'other.log', 99), (eq / 'r1', 30), (eq / 'keep-r2', 30)):
        age(p, days)
    got = {(p.name, why) for p, why in S.candidates(14, 2, scratch=sc, logs=logs, equivs=[eq])}
    assert got == {('old-trial', 'scratch'), ('pkg-before-a', 'rebuild snapshot'), ('r1', 'equivalence report')}   # newest 2 snapshots kept; KEEP and keep- kept
    assert S.candidates(60, 2, scratch=sc, logs=logs, equivs=[eq]) == []


def test_clean_applies_only_with_flag(tmp_path, monkeypatch):
    sc = tmp_path / 'scratch'; (sc / 'x').mkdir(parents=True); (sc / 'x' / 'f').write_text('1'); age(sc / 'x', 40)
    monkeypatch.setattr(S.P, 'SCRATCH', sc); monkeypatch.setattr(S.P, 'HIERARCHY', tmp_path / 'h'); monkeypatch.setattr(S, 'worktree_equiv', lambda: [])
    S.main(['clean'])
    assert (sc / 'x').exists()
    S.main(['clean', '--apply'])
    assert not (sc / 'x').exists()


def test_history_aliases_and_broken_links_are_preserved(tmp_path):
    sc = tmp_path / 'scratch'
    sc.mkdir()
    history = tmp_path / 'archive' / 'research'
    history.mkdir(parents=True)
    (history / 'source.txt').write_text('original evidence')
    age(history, 40)
    (sc / 'research').symlink_to(history, target_is_directory=True)
    (sc / 'pkg-before-research').symlink_to(history, target_is_directory=True)
    (sc / 'missing').symlink_to(tmp_path / 'missing-target')
    assert S.candidates(14, 0, scratch=sc, logs=tmp_path / 'logs', equivs=[]) == []
    assert (sc / 'research' / 'source.txt').read_text() == 'original evidence'


def test_retained_standalone_evidence_survives_clean(tmp_path, monkeypatch):
    sc = tmp_path / 'scratch'
    sc.mkdir()
    for name in ['cited-evidence.json', 'obsolete.txt']:
        (sc / name).write_text('data')
        age(sc / name, 40)
    policy = sc / S.RETENTION_FILE
    policy.write_text(json.dumps({'keep': ['cited-evidence.json']}))
    age(policy, 40)
    monkeypatch.setattr(S.P, 'SCRATCH', sc)
    monkeypatch.setattr(S.P, 'HIERARCHY', tmp_path / 'h')
    monkeypatch.setattr(S, 'worktree_equiv', lambda: [])
    S.main(['clean', '--apply'])
    assert (sc / 'cited-evidence.json').read_text() == 'data'
    assert policy.exists()
    assert not (sc / 'obsolete.txt').exists()


def test_invalid_retention_policy_refuses_cleanup(tmp_path, monkeypatch):
    sc = tmp_path / 'scratch'
    sc.mkdir()
    (sc / 'old-source.txt').write_text('original')
    age(sc / 'old-source.txt', 40)
    (sc / S.RETENTION_FILE).write_text(json.dumps({'keep': ['../outside']}))
    monkeypatch.setattr(S.P, 'SCRATCH', sc)
    monkeypatch.setattr(S.P, 'HIERARCHY', tmp_path / 'h')
    monkeypatch.setattr(S, 'worktree_equiv', lambda: [])
    with pytest.raises(ValueError, match='invalid scratch retention policy'):
        S.main(['clean', '--apply'])
    assert (sc / 'old-source.txt').read_text() == 'original'
