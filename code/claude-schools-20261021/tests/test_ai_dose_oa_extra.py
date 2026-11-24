"""oa_extra.project keeps the fields of the AI-dose controls and tolerates null ids (a failed pass on 2026-11-04 died on one)."""
import zlib

import oa_extra


def test_project_handles_nulls_and_keeps_references():
    w = dict(id='https://openalex.org/W5', publication_year=2024, type='article', open_access=dict(oa_status='green', is_oa=True),
             primary_location=dict(source=dict(type='journal', display_name='J')), cited_by_count=3,
             authorships=[dict(author=dict(id='https://openalex.org/A1')), dict(author=dict(id=None)), dict(author=None)],
             referenced_works=['https://openalex.org/W10', 'https://openalex.org/W11', None, 'bad'])
    r = oa_extra.project(w, '2026-10-14')
    assert r[0] == 'W5' and r[3] == 'green' and r[4] == 1 and r[5] == 'journal' and r[7] == 3
    assert r[8] == '["A1", "", ""]' and r[9] == 2 and zlib.decompress(r[10]).decode() == '10,11'
    assert oa_extra.project(dict(id='https://openalex.org/W6'), 'd')[9] == 0
