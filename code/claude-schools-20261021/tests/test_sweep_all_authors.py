"""Byline size is discovery metadata; it must not exclude an otherwise eligible PI paper."""
import copy

import pytest

import sweep_from_snapshot as M
from test_build_rules import au, run_stages, work, write_school


def large_work():
    return work('W101', 'A Large Collaborative Computing Paper', 2020,
                [au('Ada Lovelace', 'A1')] + [au(f'Collaborator Number{i}', f'A{i+100}', school=False) for i in range(100)])


def test_snapshot_sweep_retains_a_101_author_work_and_all_original_authorships(monkeypatch):
    source = large_work(); before = copy.deepcopy(source)
    monkeypatch.setattr(M.O, 'works_by_lineage', lambda inst, year, root=None: iter([source]))
    rows = M.works_of_year(['I1', 'I2'], 2020)
    assert rows == [source] and len(rows[0]['authorships']) == 101
    assert source == before  # deduplication across institution IDs must not edit the byline


@pytest.mark.usefixtures('layout')
def test_large_work_with_the_pis_own_identity_affiliation_and_period_is_a_native_lab_paper(tmp_path):
    source = large_work(); before = copy.deepcopy(source)
    write_school(tmp_path, sweep=[source])
    ctx = run_stages(tmp_path, upto='papers')
    row = next(r for r in ctx.rows if r['oa'] == source['id'])
    assert row['pi'] == 'Ada Lovelace' and row['identity'] == 'reviewed_openalex_author_id'
    assert row['authorship']['school_via'] == ['Princeton University', 'text: Princeton University']
    assert row['appointment']['periodId'] == 'reviewed:ada-lovelace:1'
    assert len(row['byline']) == 101 and row['byline'] == [a['raw_author_name'] for a in source['authorships']]
    assert source == before
