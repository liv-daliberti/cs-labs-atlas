"""School-local author records must reach venue dates, coauthor counts and page filters."""
import copy
import gzip
import json

import pytest

import test_build_rules as T
from pihier import identity

pytestmark = pytest.mark.usefixtures('layout')
PID = 'https://dblp.org/pid/example/AdaLovelace'
COLUMN = 'AI and Economics'
PAPER = 'A Long Research Article on Verification'


@pytest.mark.parametrize('shared_exists', [False, True])
@pytest.mark.parametrize('page_scope', ['shared', 'school'])
def test_own_author_metadata_reaches_paper_filters_without_mutating_shared_cache(tmp_path, monkeypatch, shared_exists, page_scope):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    col = T.work('W101', COLUMN, 2020, [T.au('Ada Lovelace', 'A1')], doi='10.1109/mis.2020.12345')
    col['primary_location']['source']['display_name'] = 'IEEE Intelligent Systems'
    paper = T.work('W102', PAPER, 2021, [T.au('Ada Lovelace', 'A1'), T.au('Alan Turing', 'A9')], typ='preprint', doi='10.9/research')
    T.write_school(tmp_path, sweep=[col, paper])
    overrides = copy.deepcopy(T.OVERRIDES)
    overrides[T.SCHOOL]['Ada Lovelace']['dblp'] = [PID]
    T.put(tmp_path, 'census-overrides.json', None).write_text(json.dumps(overrides))
    shared = dict(persons={}, by_name={})
    if shared_exists:
        T.put(tmp_path, 'dblp-dump-persons.json.gz', None).write_bytes(gzip.compress(json.dumps(shared).encode()))
    pubs = [dict(key='journals/expert/Lovelace20', title=COLUMN, year=2020, dois=[col['doi']], authors=['Ada Lovelace']),
            dict(key='conf/cav/Lovelace19', title=PAPER, year=2019, dois=[paper['doi']], authors=['Ada Lovelace', 'Alan Turing'])]
    own = dict(persons={PID: dict(names=['Ada Lovelace'], pubs=pubs)}, by_name={})
    local = T.put(tmp_path, 'dblp-dump-persons-school.json.gz')
    local.write_bytes(gzip.compress(json.dumps(own).encode()))
    T.put(tmp_path, 'dblp-dump-pages.json.gz' if page_scope == 'shared' else 'dblp-dump-pages-school.json.gz',
          None if page_scope == 'shared' else T.SCHOOL).write_bytes(gzip.compress(json.dumps(
        dict(pages={'journals/expert/Lovelace20': '34-35', 'conf/cav/Lovelace19': '1-15'})).encode()))

    ctx = T.run_stages(tmp_path, upto='papers')
    rows = T.rows_of(ctx, 'Ada Lovelace')
    assert COLUMN not in rows, 'school-specific short columns must retain the page-count exclusion'
    assert rows[PAPER]['year'] == 2019, 'the school-specific venue year must reach paper dating'
    assert ctx.n['dblp_page_counts_titles'] == 2
    assert ctx.n['not_paper:column'] == 1
    assert identity.DUMP_PERSONS == (shared if shared_exists else None)

    # A subsequent build without the school extraction must not inherit its records.
    local.unlink()
    next_ctx = T.run_stages(tmp_path, upto='papers')
    assert COLUMN in T.rows_of(next_ctx, 'Ada Lovelace')
    assert next_ctx.n.get('dblp_page_counts_titles', 0) == 0


def test_school_page_metadata_is_in_build_provenance(tmp_path, monkeypatch):
    import hashlib
    from types import SimpleNamespace
    import atlas_paths as P
    import provenance

    path = T.put(tmp_path, 'dblp-dump-pages-school.json.gz')
    path.write_bytes(gzip.compress(json.dumps(dict(pages={'conf/x/A': '1-9'})).encode()))
    monkeypatch.setattr(provenance, 'P', SimpleNamespace(
        data=lambda name, school=None: P.data(name, school, root=tmp_path), SITE_DATA=tmp_path / 'site'))
    assert provenance.school_inputs(T.SCHOOL)[str(path)]['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
