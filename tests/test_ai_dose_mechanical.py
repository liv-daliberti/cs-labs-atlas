"""Mechanical-shift measurement on synthetic vectors: a pure style direction moves novelty by a known sign and the pairing is respected."""
import numpy as np

import dose_mechanical as M


def test_unit_and_nov():
    rng = np.random.default_rng(0)
    P = M.unit(rng.normal(size=(200, 12)), np.zeros(12))
    Q = P[:5]
    nn, mx = M.nov(Q, P[5:])
    assert nn.shape == (5,) and (mx <= nn + 1e-6).all()          # the nearest is at least as close as the mean of the 5 nearest
    n2, m2 = M.nov(P[:5], P)                                     # a paper that is in the pool has nov_max = 0
    assert np.allclose(m2, 0, atol=1e-5)


def test_deltas_follow_a_style_direction_toward_the_crowd():
    rng = np.random.default_rng(1)
    d = 16
    crowd = rng.normal(size=d)
    pool_raw = crowd + 0.6 * rng.normal(size=(400, d))
    years = np.repeat(np.arange(2016, 2020), 100)
    Zu = M.unit(pool_raw, np.zeros(d))
    papers = rng.normal(size=(60, d))                            # papers far from the crowd
    meta = [dict(year=2020, school='x', key=f'k{i}') for i in range(60)]
    Zh = M.unit(papers, np.zeros(d))
    Za = M.unit(papers + 1.5 * crowd, np.zeros(d))               # the "AI wording" pulls toward the crowd: less novel
    dl = M.deltas(Zh, Za, meta, Zu, years, [['x']] * 400, 'all', 3)
    assert np.isfinite(dl).all() and dl[:, 0].mean() < -0.05
    rows = M.summarize(dl, [m['key'] for m in meta], dict(kind='t'))
    assert rows[0]['delta'] < 0 and rows[0]['lo'] < rows[0]['delta'] < rows[0]['hi']
