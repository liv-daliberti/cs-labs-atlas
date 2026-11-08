"""A reviewed correction cannot silently discard newly sourced lab membership."""
import collections
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

import atlas_paths as P
from pihier import students


def member(name='Jingyi Chen'):
    return dict(person='ext:example:jingyi-chen', name=name, roles=['phd'], relations=[dict(
        type='researched_advising', role='phd', years=[2026], sources=[dict(
            url='https://example.edu/collective', sha256='1' * 64, quote='Jingyi Chen; advisers A and B')])])


def digest(row):
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def apply(root, stu, corrections):
    P.data_w('student-corrections.json', root=root).write_text(json.dumps(corrections))
    ctx = SimpleNamespace(here=root, school='example', n=collections.Counter())
    students.corrections(ctx, stu)
    return ctx


def decision(row, **extra):
    return dict(school='example', pi='One PI', student=row['person'], action='drop',
                reason='Exact collective roster claim lacks this PI-specific source.',
                expected_member_sha256=digest(row), **extra)


def test_exact_correction_preserves_other_labs_and_replays(tmp_path):
    row = member()
    stu = {'One PI': {row['person']: copy.deepcopy(row)}, 'Other PI': {row['person']: copy.deepcopy(row)}}
    other = copy.deepcopy(stu['Other PI'])
    ctx = apply(tmp_path, stu, [decision(row)])
    assert not stu['One PI'] and stu['Other PI'] == other
    assert ctx.n['student_corrections_drop'] == 1
    assert apply(tmp_path, stu, [decision(row)]).n['student_corrections_drop'] == 0


@pytest.mark.parametrize('change', ['name', 'role', 'year', 'source_url', 'source_hash', 'source_quote', 'alias', 'new_relation'])
def test_new_or_changed_member_evidence_holds_before_any_mutation(tmp_path, change):
    row = member()
    current = copy.deepcopy(row)
    if change == 'name': current['name'] = 'Jingyi Chen New'
    elif change == 'role': current['roles'].append('postdoc')
    elif change == 'year': current['relations'][0]['years'].append(2025)
    elif change == 'source_url': current['relations'][0]['sources'][0]['url'] += '/new'
    elif change == 'source_hash': current['relations'][0]['sources'][0]['sha256'] = '2' * 64
    elif change == 'source_quote': current['relations'][0]['sources'][0]['quote'] += '; new source'
    elif change == 'alias': current['aliases'] = ['Jingyi Chen Alias']
    elif change == 'new_relation': current['relations'].append(dict(type='direct_lab_membership', years=[2026], sources=[]))
    stu = {'One PI': {row['person']: current}}
    before = copy.deepcopy(stu)
    with pytest.raises(ValueError, match='preimage changed'):
        apply(tmp_path, stu, [decision(row)])
    assert stu == before


def test_later_stale_guard_prevents_earlier_correction_mutation(tmp_path):
    row = member()
    other = member('Other Student')
    other['person'] = 'ext:example:other'
    stu = {'One PI': {row['person']: copy.deepcopy(row), other['person']: copy.deepcopy(other)}}
    bad = decision(other)
    bad['expected_member_sha256'] = '0' * 64
    before = copy.deepcopy(stu)
    with pytest.raises(ValueError, match='preimage changed'):
        apply(tmp_path, stu, [decision(row), bad])
    assert stu == before


def test_legacy_unconditional_correction_keeps_existing_contract(tmp_path):
    row = member()
    d = decision(row)
    d.pop('expected_member_sha256')
    stu = {'One PI': {row['person']: copy.deepcopy(row)}}
    assert apply(tmp_path, stu, [d]).n['student_corrections_drop'] == 1


def test_malformed_applicable_guard_holds(tmp_path):
    row = member()
    d = decision(row)
    d['expected_member_sha256'] = 'bad'
    stu = {'One PI': {row['person']: copy.deepcopy(row)}}
    with pytest.raises(ValueError, match='valid expected_member_sha256'):
        apply(tmp_path, stu, [d])
    assert stu['One PI'][row['person']] == row


def test_prior_in_batch_evidence_change_cannot_be_silently_dropped(tmp_path):
    row = member()
    stu = {'One PI': {row['person']: copy.deepcopy(row)}}
    new_source = dict(url='https://example.edu/independent', sha256='2' * 64, quote='Independent lab source')
    replace = dict(school='example', pi='One PI', student=row['person'], action='replace_sources',
                   reason='Separately reviewed new source.', years=[2026], sources=[new_source])
    with pytest.raises(ValueError, match='preimage changed'):
        apply(tmp_path, stu, [replace, decision(row)])
    assert row['person'] in stu['One PI']
    assert stu['One PI'][row['person']]['relations'][0]['sources'] == [new_source]
