from lab_coverage import derived_reason


def test_current_only_listing_does_not_make_an_established_professor_a_new_hire():
    pi = dict(periods=[dict(start='2002', end=None, asof='2026-11-06')])
    census = dict(title_as_listed='Haley Family Professor of Computer Science', years_listed=[2026],
                  ranks_by_year={'2026': ['ladder']}, sources=[dict(url='https://seas.harvard.edu/computer-science/people')])
    assert derived_reason('students', pi, census, {}) is None
    assert derived_reason('papers', pi, census, {}) is None


def test_archived_listing_history_retains_the_legacy_coverage_reason():
    census = dict(title_as_listed='Assistant Professor of Computer Science', years_listed=[2025, 2026],
                  sources=[dict(url='https://web.archive.org/web/20250401000000id_/https://school.example/faculty')])
    assert derived_reason('students', {}, census, {})[0] == 'new_hire_2025_or_later'
