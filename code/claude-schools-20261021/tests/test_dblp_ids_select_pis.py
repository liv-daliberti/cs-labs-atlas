"""dblp_ids_school.select_pis tolerates census sources without a `kind` (legacy released schools; Berkeley chain crashed with KeyError 'kind', 2026-11-10)."""
import dblp_ids_school as D


def test_source_without_kind_is_ignored_and_does_not_crash():
    people = [{'name': 'A', 'is_pi': True, 'sources': [{'url': 'u'}]},
              {'name': 'B', 'sources': [{'url': 'u', 'rank': 'ladder'}]},
              {'name': 'C', 'sources': [{'kind': 'dept_listing:PHYS', 'rank': 'ladder'}]},
              {'name': 'D', 'sources': [{'kind': 'dept_listing:PHYS', 'rank': 'research'}]}]
    assert [x['name'] for x in D.select_pis(people, {'PHYS': 'affiliated'})] == ['A', 'C']
