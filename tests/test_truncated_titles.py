"""R9 (Georgia Tech stage 2/4): years whose only rows are unranked cards with a cut-off title need dated profile evidence."""
import periods_school as PS


def test_truncated_years_are_unranked_rows_with_an_ellipsis():
    rows = [dict(name='A', year=2023, rank='ladder', titles=['Professor']),
            dict(name='A', year=2024, rank='other', titles=['Executive Director, Institute for Data…']),
            dict(name='A', year=2025, rank='other', titles=['Executive Director, Institute for Data…']),
            dict(name='B', year=2024, rank='other', titles=['Staff']),                       # unranked but not cut off: not a truncation
            dict(name='C', year=2024, rank='other', titles=['Chair…']), dict(name='C', year=2024, rank='ladder', titles=['Professor'])]  # a ladder row the same year proves it
    assert PS.truncated_years(rows) == {'A': [2024, 2025]}
