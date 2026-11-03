"""tools/departed_faculty.py: a review list from snapshot affiliations and recent works (ROADMAP #26); it writes no overrides."""
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
import departed_faculty as D  # noqa: E402

OA = 'https://openalex.org/'
OURS = {'I1'}


def inst(i, name, lineage=None):
    return {'id': OA + i, 'display_name': name, 'lineage': [OA + x for x in (lineage or [i])]}


def test_affiliations_find_the_last_year_here_and_the_move():
    author = {'affiliations': [{'institution': inst('I1', 'Here U'), 'years': [2021, 2022, 2023, 2024]},
                               {'institution': inst('I9', 'There U'), 'years': [2025, 2026]}]}
    last_here, since, latest, rows = D.affiliations(author, OURS)
    assert (last_here, since, latest) == (2024, 2025, 2026) and ('There U', [2025, 2026]) in rows


def test_a_child_institution_in_the_lineage_counts_as_here():
    author = {'affiliations': [{'institution': inst('I5', 'Dept of Here U', lineage=['I5', 'I1']), 'years': [2026]}]}
    assert D.affiliations(author, OURS)[0] == 2026


def test_recent_works_count_the_pis_own_authorship_only(monkeypatch):
    w1 = {'id': OA + 'W1', 'publication_date': '2025-06-01', 'authorships': [
        {'author': {'id': OA + 'A1'}, 'institutions': [inst('I9', 'There U')]}, {'author': {'id': OA + 'A2'}, 'institutions': [inst('I1', 'Here U')]}]}
    w2 = {'id': OA + 'W2', 'publication_date': '2024-06-01', 'authorships': [{'author': {'id': OA + 'A1'}, 'institutions': [inst('I1', 'Here U')]}]}
    monkeypatch.setattr(D.S, 'works_by_author', lambda aid, root=None: [w1, w2])
    here, elsewhere, ex = D.recent_works(['A1'], OURS)
    assert (here, elsewhere) == (0, 1) and ex[0]['institutions'] == ['There U']  # A2's Here U and the 2024 work do not count


def test_the_list_is_written_without_touching_any_period(tmp_path, monkeypatch):
    import json
    called = []
    monkeypatch.setattr(D, 'run', lambda s, i: ([{'school': 'x', 'pi': 'P', 'signals': ['a', 'b']}], {'x': 1}))
    monkeypatch.setattr(D.SC, 'keys', lambda: ['x'])
    monkeypatch.setattr(sys, 'argv', ['departed_faculty.py', '--out', str(tmp_path / 'o.json')])
    D.main()
    d = json.loads((tmp_path / 'o.json').read_text())
    assert d['candidates'][0]['pi'] == 'P' and 'No overrides' in d['note'] and not called
