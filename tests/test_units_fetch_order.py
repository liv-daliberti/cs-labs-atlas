import cs_related_school as C


def test_priority_years_first_for_every_unit_and_nothing_dropped():
    plan = [(u, 'x', {'timestamp': f'{y}0101000000'}) for u in ('A', 'B') for y in ('2016', '2020', '2025', '2026')]
    out = C.unit_fetch_order(plan)
    assert sorted(map(repr, out)) == sorted(map(repr, plan))
    head = [(u, r['timestamp'][:4]) for u, _, r in out[:4]]
    assert head == [('A', '2020'), ('A', '2026'), ('B', '2020'), ('B', '2026')]
    assert [r['timestamp'][:4] for _, _, r in out[4:]] == ['2016', '2025', '2016', '2025']
