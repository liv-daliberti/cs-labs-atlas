"""tools/scratch.py: what clean removes, on a fake tree (nothing outside tmp_path)."""
import os
import time

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
