"""Reviewed id reconciliation (tools/id_reconcile.py, docs/IDS.md): a native rebuild that carries no ids keeps every issued id
once the reviewed redirects, anchor bindings and student re-keys are applied to an isolated registry copy."""
import copy
import gzip
import json
import sqlite3

import pytest

import atlas_ids as A
import id_reconcile as R
from test_atlas_ids import paper, pi, stu, write

SCHOOL = 'hkust'
URL_Z = 'https://cse.example.edu/faculty/'
URL_S = 'https://cse.example.edu/~ma/students.html'
ORCID = '0000-0001-2345-6789'
DBLP = 'https://dblp.org/pid/1/Chan'


def package(pis, students, papers=()):
    return {SCHOOL: dict(pis=pis, students=students, papers=list(papers), links=[], sweep=[])}


def issue(root, reg, fx, day):
    write(root, fx)
    db = A.open_registry(reg, seed=False)
    try:
        A.run([SCHOOL], root, db, use_sweep=False, today=day)
    finally:
        db.close()
    return {p['pi']: p for p in json.loads((root / SCHOOL / 'pis.json').read_text())}


def tim_student(person):
    return stu(person, 'Tim Cheng', [URL_S])


@pytest.fixture()
def world(tmp_path):
    """The history behind the 2026-11-25 HKUST case, in miniature."""
    reg = tmp_path / 'registry.sqlite'
    listing = [dict(url=URL_Z)]
    # day 0: the alias spelling alone; day 1: one merged record that has gained an ORCID and a DBLP person
    issue(tmp_path / 'd0', reg, package([pi('Alias Chan', personIds=['c_alias'])], {}), '2026-11-08')
    issue(tmp_path / 'd1', reg, package([pi('Alias Chan', personIds=['c_alias', 'c_canon'], orcid=[ORCID], dblp=[DBLP]),
                                         pi('Tim Main', personIds=['c_tim_main', 'c_tim_alias']), pi('Zed Zhang', listings=listing)],
                                        {'Pia Ma': [tim_student('ext:hkust:tim-cheng')]}), '2026-11-18')
    # day 2: the census lists both spellings again, so the alias keeps the earlier id and the canonical record is split off
    day2 = issue(tmp_path / 'd2', reg, package([pi('Alias Chan', personIds=['c_alias']), pi('Canon Chan', personIds=['c_canon'], orcid=[ORCID], dblp=[DBLP]),
                                                pi('Tim Main', personIds=['c_tim_main', 'c_tim_alias']), pi('Zed Zhang', listings=listing),
                                                pi('Pia Ma', personIds=['c_pia'])],
                                               {'Pia Ma': [tim_student('ext:hkust:tim-cheng')]}, [paper('Zed Zhang', 'https://openalex.org/W9', doi='10.1/z')]), '2026-11-19')
    assert day2['Canon Chan']['atlasId'] != day2['Alias Chan']['atlasId']
    # the id-less rebuild of day 3: one canonical PI, Zed with a reviewed OpenAlex id, the student keyed by the merged alias's collection id
    d3 = package([pi('Canon Chan', personIds=['c_canon'], orcid=[ORCID], dblp=[DBLP], mergedCensusRows=['Alias Chan']),
                  pi('Tim Main', personIds=['c_tim_main']), pi('Pia Ma', personIds=['c_pia']),
                  pi('Zed Zhang', listings=listing, oa=['https://openalex.org/A55'])],
                 {'Pia Ma': [tim_student('c_tim_alias')]}, [paper('Zed Zhang', 'https://openalex.org/W9', doi='10.1/z'), paper('Zed Zhang', 'https://openalex.org/W10', doi='10.1/y')])
    write(tmp_path / 'hier', d3)
    (tmp_path / 'hier' / SCHOOL / 'census-name-aliases.json').write_text(json.dumps(dict(school=SCHOOL, native_pi_merges=[
        dict(canonical='Canon Chan', aliases=['Alias Chan'], evidence=[dict(url='https://x.example/', quote='same person')])])))
    # the package the promotion replaces: the day-2 ids for the PIs that survive
    before = tmp_path / 'before'; before.mkdir()
    pis2 = json.loads((tmp_path / 'd2' / SCHOOL / 'pis.json').read_text())
    (before / 'pis.json').write_text(json.dumps([p for p in pis2 if p['pi'] != 'Alias Chan']))
    (before / 'students.json').write_text((tmp_path / 'd2' / SCHOOL / 'students.json').read_text())
    with gzip.open(before / 'lab_papers.jsonl.gz', 'wt') as f:
        f.write(open_gz(tmp_path / 'd2' / SCHOOL / 'lab_papers.jsonl.gz'))
    return tmp_path, reg, day2


def open_gz(p):
    with gzip.open(p, 'rt') as f:
        return f.read()


def state(db, i):
    return dict(row=list(db.execute('select * from ids where id=?', (i,)).fetchone()),
                anchors=sorted(a for (a,) in db.execute('select anchor from anchors where id=?', (i,))))


def review_for(tmp_path, reg, day2):
    db = sqlite3.connect(reg)
    keep, alias = day2['Canon Chan'], day2['Alias Chan']
    stu_id = json.loads((tmp_path / 'd2' / SCHOOL / 'students.json').read_text())['Pia Ma'][0]['atlasId']
    sample = json.loads((tmp_path / 'hier' / SCHOOL / 'students.json').read_text())['Pia Ma'][0]
    hashed = R.member_sha(sample)
    zed = day2['Zed Zhang']
    r = dict(version=1, school=SCHOOL, reviewed_by='test', reviewed_on='2026-11-25',
             pi_redirects=[dict(canonical='Canon Chan', alias_name='Alias Chan', survivor=dict(id=keep['atlasId'], lab=keep['labId']),
                                alias=dict(id=alias['atlasId'], lab=alias['labId']),
                                registry_before=dict(survivor=state(db, keep['atlasId']), alias=state(db, alias['atlasId']),
                                                     survivor_lab=state(db, keep['labId']), alias_lab=state(db, alias['labId'])))],
             anchor_bindings=[dict(id=zed['atlasId'], anchor='p|openalex:A55', subject=dict(school=SCHOOL, pi='Zed Zhang'),
                                   registry_before=state(db, zed['atlasId']))],
             student_rekeys=[dict(pi='Pia Ma', from_person='c_tim_alias', to_person='ext:hkust:tim-cheng', name='Tim Cheng', issued_id=stu_id,
                                  expected_member_sha256=hashed, registry_before=state(db, stu_id))])
    db.close()
    return r, stu_id


def run_all(tmp_path, reg, review):
    work = tmp_path / 'work.sqlite'
    work.write_bytes(reg.read_bytes())
    db = A.open_registry(work, seed=False)
    applied = R.apply(db, review, tmp_path / 'hier', today='2026-11-25')
    res = A.run([SCHOOL], tmp_path / 'hier', db, use_sweep=False, today='2026-11-25')
    db.commit(); db.close()
    return work, applied, res


def test_without_the_review_the_rebuild_splits_and_mints(world):
    tmp_path, reg, day2 = world
    work = tmp_path / 'plain.sqlite'; work.write_bytes(reg.read_bytes())
    db = A.open_registry(work, seed=False)
    res = A.run([SCHOOL], tmp_path / 'hier', db, use_sweep=False, today='2026-11-25')
    pis = {p['pi']: p for p in json.loads((tmp_path / 'hier' / SCHOOL / 'pis.json').read_text())}
    assert pis['Canon Chan']['atlasId'] == day2['Alias Chan']['atlasId'] != day2['Canon Chan']['atlasId']   # the earlier-issued id wins, no redirect
    assert pis['Zed Zhang']['atlasId'] != day2['Zed Zhang']['atlasId']                                        # a second id for the same person
    assert res['report']['stats']['split_minted'] >= 1


def test_review_keeps_every_issued_id_and_replays(world):
    tmp_path, reg, day2 = world
    review, stu_id = review_for(tmp_path, reg, day2)
    work, applied, res = run_all(tmp_path, reg, review)
    pis = {p['pi']: p for p in json.loads((tmp_path / 'hier' / SCHOOL / 'pis.json').read_text())}
    for n in ('Canon Chan', 'Tim Main', 'Pia Ma', 'Zed Zhang'):
        assert pis[n]['atlasId'] == day2[n]['atlasId'] and pis[n]['labId'] == day2[n]['labId'], n
    st = json.loads((tmp_path / 'hier' / SCHOOL / 'students.json').read_text())['Pia Ma'][0]
    assert st['atlasId'] == stu_id and st['rekeyedFrom'] == ['c_tim_alias'] and st['person'] == 'ext:hkust:tim-cheng'
    stats = res['report']['stats']
    assert stats.get('minted', 0) == 1 and stats.get('split_minted', 0) == 0 and stats.get('redirects_new', 0) == 0   # only the new work
    db = sqlite3.connect(work)
    assert A.resolve(db, day2['Alias Chan']['atlasId']) == day2['Canon Chan']['atlasId']
    assert A.resolve(db, day2['Alias Chan']['labId']) == day2['Canon Chan']['labId']
    assert db.execute("select count(*) from anchors where id=?", (day2['Alias Chan']['atlasId'],)).fetchone()[0] == 0
    assert applied['anchor_bindings'] == [('p|openalex:A55', day2['Zed Zhang']['atlasId'])]
    # a replay changes nothing
    before = {t: sorted(db.execute(f'select * from {t}')) for t in ('ids', 'anchors')}
    A.run([SCHOOL], tmp_path / 'hier', A.open_registry(work, seed=False), use_sweep=False, today='2026-11-26')
    db2 = sqlite3.connect(work)
    assert before == {t: sorted(db2.execute(f'select * from {t}')) for t in ('ids', 'anchors')}


def test_verify_passes_and_flags_a_changed_id(world):
    tmp_path, reg, day2 = world
    review, _ = review_for(tmp_path, reg, day2)
    work, _, _ = run_all(tmp_path, reg, review)
    (tmp_path / 'hier' / 'ids').mkdir(exist_ok=True)
    out = R.verify(tmp_path / 'before', tmp_path / 'hier', reg, work, review)
    assert out['pass'], out['violations']
    assert out['pi_ids_equal'] == out['pis']['before'] == 4 and out['works']['new_rows'] == 1 and out['new_non_work_ids'] == []
    pis = json.loads((tmp_path / 'hier' / SCHOOL / 'pis.json').read_text())
    pis[0]['atlasId'] = 'atl:p:000000000000'
    (tmp_path / 'hier' / SCHOOL / 'pis.json').write_text(json.dumps(pis))
    bad = R.verify(tmp_path / 'before', tmp_path / 'hier', reg, work, review)
    assert not bad['pass'] and any(v[0] == 'pi id differs' for v in bad['violations'])


@pytest.mark.parametrize('mutate', ['anchor', 'row', 'name_only', 'rekey_hash', 'merge_entry'])
def test_changed_preimage_or_name_only_refuses(world, mutate):
    tmp_path, reg, day2 = world
    review, _ = review_for(tmp_path, reg, day2)
    work = tmp_path / 'work.sqlite'; work.write_bytes(reg.read_bytes())
    db = A.open_registry(work, seed=False)
    if mutate == 'anchor':
        db.execute("insert into anchors (anchor,id,kind,first_seen) values ('p|dblp:9/new',?,'person','2026-11-20')", (day2['Alias Chan']['atlasId'],))
    elif mutate == 'row':
        db.execute("update ids set issued='2026-11-01' where id=?", (day2['Zed Zhang']['atlasId'],))
    elif mutate == 'name_only':   # the record would have to cite the url the issued name anchor carries
        pis = json.loads((tmp_path / 'hier' / SCHOOL / 'pis.json').read_text())
        for p in pis:
            if p['pi'] == 'Zed Zhang':
                p['listings'] = [dict(url='https://elsewhere.example/')]
        (tmp_path / 'hier' / SCHOOL / 'pis.json').write_text(json.dumps(pis))
    elif mutate == 'rekey_hash':
        review['student_rekeys'][0]['expected_member_sha256'] = '0' * 64
    elif mutate == 'merge_entry':
        (tmp_path / 'hier' / SCHOOL / 'census-name-aliases.json').write_text(json.dumps(dict(native_pi_merges=[])))
    db.commit()
    snapshot = {t: sorted(db.execute(f'select * from {t}')) for t in ('ids', 'anchors')}
    with pytest.raises(R.ReconcileRefused):
        R.apply(db, copy.deepcopy(review), tmp_path / 'hier', today='2026-11-25')
    assert snapshot == {t: sorted(db.execute(f'select * from {t}')) for t in ('ids', 'anchors')}    # nothing was written


def test_cli_refuses_the_live_registry(world, monkeypatch, capsys):
    tmp_path, reg, day2 = world
    review, _ = review_for(tmp_path, reg, day2)
    (tmp_path / 'review.json').write_text(json.dumps(review))
    monkeypatch.setattr(R, 'live_registry', lambda p: True)
    assert R.main(['apply', '--registry', str(reg), '--dir', str(tmp_path / 'hier'), '--review', str(tmp_path / 'review.json')]) == 2
    assert 'live registry' in capsys.readouterr().err


def test_swap_is_compare_and_swap(tmp_path):
    src = tmp_path / 'new'; dst = tmp_path / 'live'; src.write_text('new'); dst.write_text('old')
    plan = tmp_path / 'plan.json'
    R.plan([(src, dst)], plan)
    assert R.swap(plan)['dry_run'] and dst.read_text() == 'old'
    dst.write_text('changed by someone else')
    with pytest.raises(R.ReconcileRefused):
        R.swap(plan, apply_=True)
    assert dst.read_text() == 'changed by someone else'
    dst.write_text('old')
    src.write_text('tampered')
    with pytest.raises(R.ReconcileRefused):
        R.swap(plan, apply_=True)
    src.write_text('new')
    assert not R.swap(plan, apply_=True)['dry_run'] and dst.read_text() == 'new'
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith('.')] == []
