"""The routing helpers of 2026-11-26 (school_part, reviewed_path, reviewed_rel, rel_label) and the new DATA_FILES names, in the split and school placements."""
from pathlib import Path

import atlas_paths as P


def test_census_report_resolves_to_derived_report_in_both_placements():
    assert P.data('census-report.md', 'mit', root='/r', layout='split') == Path('/r/hierarchy/mit/derived/report.md')
    assert P.data('census-report.md', 'mit', root='/r', layout='school') == Path('/r/schools/mit/derived/report.md')


def test_school_part_follows_the_placement():
    sp = lambda part, lay: P.school_part('mit', part, root='/r', layout=lay)   # noqa: E731
    assert sp('raw', 'split') == Path('/r/hierarchy/mit/raw') and sp('raw', 'school') == Path('/r/schools/mit/raw')
    assert sp('tmp', 'split') == Path('/r/hierarchy/mit/tmp') and sp('tmp', 'school') == Path('/r/schools/mit/tmp')
    assert sp('listings-raw', 'split') == Path('/r/listings/mit/raw') and sp('listings-raw', 'school') == Path('/r/schools/mit/listings/raw')
    assert sp('reports', 'flat') == Path('/r/hierarchy/mit')
    for part in ('raw', 'derived', 'work', 'reports', 'tmp'):   # the same names as the cutover tool moves
        assert sp(part, 'school').relative_to('/r/schools/mit').as_posix() == part


def test_school_part_without_a_root_uses_the_slots(layout):
    if layout == 'flat':
        assert P.school_part('mit', 'derived') == P.HIERARCHY / 'mit'  # route-ok: the slot itself is the subject
    else:
        assert P.school_part('mit', 'derived') == (P.school_dir('mit', 'derived') if layout == 'school' else P.HIERARCHY / 'mit' / 'derived')  # route-ok: the slot itself is the subject


def test_a_data_file_lies_in_its_part_directory(layout):
    assert P.data('catalog-captures.sqlite', 'washu').parent == P.school_part('washu', 'listings-raw', layout=layout)


def test_reviewed_files_stay_in_the_code_tree():
    assert P.reviewed_path('a.json', 'mit', '/wt') == Path('/wt/hierarchy/mit/reviewed/a.json')
    assert P.reviewed_rel('mit', 'a.json') == 'hierarchy/mit/reviewed/a.json' and P.reviewed_rel('mit') == 'hierarchy/mit/reviewed'


def test_rel_label_is_relative_to_code_then_root():
    assert P.rel_label(P.CODE / 'hierarchy/mit/derived') == 'hierarchy/mit/derived'
    assert P.rel_label(P.ROOT / 'schools/mit/derived') == 'schools/mit/derived'
