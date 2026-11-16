"""Student-recall gate (owner 2026-11-11): metrics, the seeded stratified draw, recall math, binding invalidation, capture validation, gate messages."""
import hashlib
import json
from pathlib import Path
import sqlite3
import zlib

import pytest

import atlas_paths as P
import stage_gate as G
import student_recall as R


def row(name, role='phd', years=(), src='https://lab.example/people'):
    return dict(person=name, name=name, roles=[role], relations=[dict(type='direct_lab_membership', years=list(years), role=role, sources=[dict(url=src)])])


@pytest.fixture
def tree(tmp_path, monkeypatch):
    d = tmp_path / 'u'
    d.mkdir()
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / (school or '_') / name)
    monkeypatch.setattr(P, 'data_w', lambda name, school=None, **k: tmp_path / (school or '_') / name)
    pis = [dict(pi=f'PI{i:02d}') for i in range(60)]
    st = {}
    for i, p in enumerate(pis):   # 20 zero, 20 with 1-2, 20 with 3+
        n = 0 if i < 20 else (1 + i % 2 if i < 40 else 3 + i % 3)
        st[p['pi']] = [row(f'Stu{i}x{j} Name{i}{j}', years=[2025]) for j in range(n)]

    def put(name, obj):
        (d / name).write_text(json.dumps(obj))
    put('pis.json', pis)
    put('students.json', st)
    return dict(root=tmp_path, dir=d, pis=pis, st=st, put=put)


def test_name_match_variants():
    assert R.name_match('Jakub (Kuba) Grudzien', 'Jakub Grudzien')
    assert R.name_match('J. Smith', 'John Smith') and not R.name_match('Mary Smith', 'John Smith')
    assert R.name_match('Zhou Xiaofang', 'Xiaofang Zhou') and R.name_match('周晓方', '周 晓方') and not R.name_match('周晓方', '周晓芳')


@pytest.mark.parametrize(('source', 'recorded', 'expected'), [
    ('冯明泉', 'Mingquan Feng 冯明泉', True),
    ('Mingquan Feng (冯明泉)', '冯 明泉', True),
    ('张赟', 'Yunhao Zhang 张昀浩', False),
    ('Yun Zhang 张赟', 'Yunhao Zhang 张昀浩', False),
    ('Yun Zhang 张赟', 'Yun Zhang 张昀浩', False),
    ('张赟', 'Yun Zhang', False),
    ('John Zhang 张三', 'Michael Zhang 张三', False),
    ('田中みずき', '田中さくら', False),
])
def test_recall_literal_han_names_precede_latin_variants(source, recorded, expected):
    assert R.name_match(source, recorded) is expected
    assert R.name_match(recorded, source) is expected


def test_recall_latin_alias_cannot_bypass_conflicting_han_name():
    recorded = dict(row('Yunhao Zhang 张昀浩'), aliases=['Yunhao Zhang'])
    assert not R.is_recorded('Yun Zhang 张赟', [recorded])
    assert not R.is_recorded('张赟', [recorded])
    assert R.is_recorded('张昀浩', [recorded])
    literal_alias = dict(row('Mingquan Feng'), aliases=['冯明泉'])
    assert R.is_recorded('冯明泉', [literal_alias])


def test_recall_counts_bilingual_match_without_crediting_different_han_person():
    entries = dict(listed=[
        dict(name='冯明泉', role='phd', section='current'),
        dict(name='张赟', role='postdoc', section='current'),
    ])
    counts = R.entry_counts(entries, [row('Mingquan Feng 冯明泉'), row('Yunhao Zhang 张昀浩')])
    assert counts['L'] == 2 and counts['K'] == 1
    assert counts['Lc'] == 1 and counts['Kc'] == 1


def test_metrics_counts_and_zero_reasons(tree):
    tree['put']('lab-coverage-reasons.json', {
        'PI00': {'students': {'code': 'sources_exhausted', 'why': 'No student of this PI in any allowed source checked.', 'sources_checked': ['a', 'b']}},
        'PI01': {'students': {'code': 'sources_exhausted', 'why': 'emeritus, no group since 2012', 'sources_checked': ['cv', 'page']}},
        'PI02': {'students': {'code': 'sources_exhausted', 'why': 'researched but one source', 'sources_checked': ['cv']}}})
    m = R.metrics('u')
    assert m['pis'] == 60 and m['pis_with_student'] == 40 and m['zero_recorded_pis'] == 20
    assert m['zero_recorded_unreasoned'] == 19    # only PI01 has a researched reason (>= 2 sources, not boilerplate)
    assert m['boilerplate_reason_pis'] == 1 and m['pis_with_current_phd'] == 40
    assert m['per_pi_median'] == pytest.approx(1.5) and m['source_mix']['member_list'] == 40


def test_role_class_and_currency():
    assert R.role_class(dict(roles=['phd_alumnus'])) == 'alumni' and R.role_class(dict(roles=['student_or_alumnus'])) == 'alumni'
    assert R.role_class(dict(roles=['doctoral_student'])) == 'phd' and R.role_class(dict(roles=['masters'])) == 'masters'
    assert R.is_current_phd(row('A B', years=[2025])) and not R.is_current_phd(row('A B', years=[2023])) and not R.is_current_phd(row('A B'))
    assert R.is_current_phd_undated(row('A B'))


def test_allocation_and_draw_are_seeded_stratified(tree):
    a = R.allocate({'0': 3, '1-2': 100, '3+': 100}, 30)
    assert a['0'] == 3 and sum(a.values()) == 30
    assert R.allocate({'0': 2, '1-2': 1, '3+': 0}, 30) == {'0': 2, '1-2': 1, '3+': 0}
    names = [p['pi'] for p in tree['pis']]
    p1, sizes = R.draw_sample(names, tree['st'], 7)
    p2, _ = R.draw_sample(names, tree['st'], 7)
    p3, _ = R.draw_sample(names, tree['st'], 8)
    assert p1 == p2 and p1 != p3 and sizes == {'0': 20, '1-2': 20, '3+': 20}
    assert {k: len(v) for k, v in p1.items()} == {'0': 10, '1-2': 10, '3+': 10}
    assert all(len(tree['st'][p]) == 0 for p in p1['0']) and all(1 <= len(tree['st'][p]) <= 2 for p in p1['1-2'])


def test_draw_binds_build_and_refuses_overwrite(tree):
    rec = R.draw('u', drawn_by='drawer')
    assert len(rec['sample']) == 30 and rec['binds'] == R.bindings('u') and rec['seed'] == R.default_seed(R.bindings('u'))
    with pytest.raises(SystemExit):
        R.draw('u')
    tree['put']('students.json', dict(tree['st'], PI59=[]))   # a rebuild
    ev = R.evaluate_record('u', json.loads((tree['dir'] / 'student-recall-check.json').read_text()))
    assert len(ev['findings']) == 1 and ev['findings'][0].startswith('bound: the build changed') and 'students.json' in ev['findings'][0]
    rec2 = R.draw('u', force=True, seed=5)
    assert rec2['seed'] == 5 and list(tree['dir'].glob('student-recall-check.*.json'))


def make_store(tree, pages):
    path = tree['dir'] / 'cap.sqlite'
    c = sqlite3.connect(path)
    c.execute('create table if not exists live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    c.execute('delete from live')
    for url, body in pages.items():
        c.execute('insert into live values (?,?,?,?,?,?,?)', (url, '2026-11-11T00:00:00', 200, hashlib.sha256(body).hexdigest(), 'text/html', zlib.compress(body), None))
    c.commit()
    return c


def fill(rec, conn_pages, per_pi_listed, unverifiable=()):
    """Readable for every PI that has a listing; unverifiable (reason) for the rest."""
    for r in rec['sample']:
        if r['pi'] in per_pi_listed:
            url = f'https://lab.example/{r["pi"]}'
            body = ('<html><body><h2>Current members</h2>' + ' '.join(f'<li>{e["name"]}</li>' for e in per_pi_listed[r['pi']]) + '</body></html>').encode()
            conn_pages[url] = body
            r.update(verdict='readable', page=dict(url=url, sha256=hashlib.sha256(body).hexdigest(), quote='Current members'), listed=per_pi_listed[r['pi']])
        else:
            r.update(verdict='unverifiable', unverifiable_reason='no_member_list_page')
    rec.update(filled_by='checker', signoff=dict(reviewer='fresh', date='2026-11-11'))
    return rec


def test_recall_math_strict_and_unverifiable(tree):
    rec = R.draw('u', drawn_by='drawer')
    st = tree['st']
    listed = {}
    for r in rec['sample']:
        rows = st[r['pi']]
        names = [{'name': x['name'], 'role': 'phd', 'section': 'current'} for x in rows]
        if r['stratum'] == '0':
            names = [{'name': f'Missed {r["pi"]} A', 'role': 'phd', 'section': 'current'}]   # a zero-recorded lab with a listed student: recall 0
        else:
            names.append({'name': f'Undated {r["pi"]} X', 'role': 'phd', 'section': 'other'})   # undated outside a current section: excluded, not a miss
        listed[r['pi']] = names
    pages = {}
    rec = fill(rec, pages, listed)
    ev = R.evaluate_record('u', rec, conn=make_store(tree, pages))
    assert ev['findings'] == [], ev['findings']
    n = ev['numbers']
    assert n['undated_excluded'] == 20 and n['unverifiable'] == 0
    # strata weights 20/10 each: zero stratum contributes L (10 names x 20/10) and K = 0; the others are complete
    L = sum(len(st[p]) for p in [r['pi'] for r in rec['sample'] if r['stratum'] != '0'])
    zero_L = 10
    assert n['r1_strict_recall'] == pytest.approx(round(L * 2 / (L * 2 + zero_L * 2), 3), abs=1e-3)
    # unverifiable PIs count as 0 recall on an imputed count: drop two '3+' PIs' pages
    unv = [r['pi'] for r in rec['sample'] if r['stratum'] == '3+'][:5]
    listed2 = {k: v for k, v in listed.items() if k not in unv}
    rec2 = fill(R.draw('u', force=True, seed=int(rec['seed'])), {}, listed2)
    pages2 = {}
    rec2 = fill(rec2, pages2, listed2)
    ev2 = R.evaluate_record('u', rec2, conn=make_store(tree, pages2))
    assert ev2['numbers']['unverifiable'] == 5 and ev2['numbers']['unverifiable_share'] == pytest.approx(5 / 30, abs=1e-3)
    assert ev2['numbers']['r2_est_current_phd_recall'] < ev['numbers']['r2_est_current_phd_recall']


def test_check_catches_fabricated_names_bad_sha_and_signoff(tree):
    rec = R.draw('u', drawn_by='drawer')
    pi = rec['sample'][-1]['pi']
    listed = {pi: [{'name': 'Real One', 'role': 'phd', 'section': 'current'}]}
    pages = {}
    rec = fill(rec, pages, listed)
    conn = make_store(tree, pages)
    rec['sample'][-1]['listed'].append({'name': 'Invented Person', 'role': 'phd', 'section': 'current'})
    f = R.evaluate_record('u', rec, conn=conn)['findings']
    assert any('not on any captured page of the PI' in x for x in f)
    rec['sample'][-1]['page']['sha256'] = '0' * 64
    assert any('does not match the stored capture' in x for x in R.evaluate_record('u', rec, conn=conn)['findings'])
    rec['signoff'] = dict(reviewer='drawer', date='2026-11-11')
    assert any('fresh reviewer is needed' in x for x in R.evaluate_record('u', rec, conn=conn)['findings'])
    rec['sample'][0]['unverifiable_reason'] = 'because'
    assert any('needs a reason class' in x for x in R.evaluate_record('u', rec, conn=conn)['findings'])
    rec['sample'] = rec['sample'][1:]   # an edited sample
    assert any('seeded draw' in x for x in R.evaluate_record('u', rec, conn=conn)['findings'])


def test_exclusions_are_capped_and_relabelling_is_visible(tree, monkeypatch):
    rec = R.draw('u', drawn_by='drawer')
    listed = {r['pi']: [{'name': f'Gone {r["pi"]}', 'role': 'phd', 'section': 'current', 'exclude': 'not_a_person'}] for r in rec['sample']}
    pages = {}
    rec = fill(rec, pages, listed)
    (tree['dir'] / 'student-recall-check.json').write_text(json.dumps(rec))
    monkeypatch.setattr(R, 'captures_path', lambda key: tree['root'] / 'u' / 'cap.sqlite')
    make_store(tree, pages)
    msgs = R.gate_items('u')
    assert any(m.startswith('recall record: ') and 'excluded by the checker' in m for m in msgs)


def test_R_STU_31_captured_same_line_external_school_proof_keeps_x_cap(tree, monkeypatch):
    rec = R.draw('u', drawn_by='drawer')
    pages = {}
    for r in rec['sample']:
        url = f'https://lab.example/{r["pi"]}'
        name = f'Visitor {r["pi"]}'
        line = f'{name} UBC PhD student'
        body = f'<html><h2>Current members</h2><p>{line}</p></html>'.encode()
        sha = hashlib.sha256(body).hexdigest()
        pages[url] = body
        r.update(verdict='readable', page=dict(url=url, sha256=sha, quote='Current members'),
                 listed=[dict(name=name, role='phd', section='current', exclude='outside_school',
                              outside_school_evidence=dict(url=url, sha256=sha, quote=line, school='UBC'))])
    rec.update(filled_by='checker', signoff=dict(reviewer='independent', date='2026-11-14'))
    conn = make_store(tree, pages)
    monkeypatch.setattr(R, 'captures_path', lambda key: tree['dir'] / 'cap.sqlite')
    (tree['dir'] / 'student-recall-check.json').write_text(json.dumps(rec))
    ev = R.evaluate_record('u', rec, conn=conn)
    assert not ev['findings']
    assert ev['numbers']['excluded_share'] == 1.0
    assert ev['numbers']['proven_external_school'] == 30
    assert ev['numbers']['x_counted_share'] == 0.0
    assert not any('excluded without same-line' in x for x in R.gate_items('u'))

    rec['sample'][0]['listed'][0]['outside_school_evidence']['quote'] = 'Current members'
    ev = R.evaluate_record('u', rec, conn=conn)
    assert any('outside-school proof needs' in x for x in ev['findings'])
    assert ev['numbers']['x_counted_exclusions'] == 1
    rec['sample'][0]['listed'][0].pop('outside_school_evidence')
    assert R.evaluate_record('u', rec, conn=conn)['numbers']['x_counted_exclusions'] == 1


def test_gate_messages_name_item_and_action(tree, monkeypatch):
    m = R.gate_items('u')
    assert any(x.startswith('recall Z:') and 'researched reason' in x for x in m)           # 20 zero-student PIs of 60
    assert any(x.startswith('recall record:') and 'student_recall.py draw u' in x for x in m)
    th = dict(Z=0.5)
    assert not any(x.startswith('recall Z') for x in R.gate_items('u', th))
    rec = R.draw('u', drawn_by='d')
    listed = {r['pi']: [{'name': f'Missing {r["pi"]} {i}', 'role': 'phd', 'section': 'current'} for i in range(3)] for r in rec['sample'][:10]}
    pages = {}
    rec = fill(rec, pages, listed)
    (tree['dir'] / 'student-recall-check.json').write_text(json.dumps(rec))
    make_store(tree, pages)
    monkeypatch.setattr(R, 'captures_path', lambda key: tree['root'] / 'u' / 'cap.sqlite')
    m = R.gate_items('u')
    assert any(x.startswith('recall R1:') and 'add the missing members' in x for x in m)
    assert any(x.startswith('recall U:') and 'unverifiable stays unverifiable' in x for x in m)
    assert any(x.startswith('recall R2:') for x in m)
    assert R.would_fail('u')['U'] == 'fail' and R.would_fail('u')['record'] == 'ok'


def test_stage6_gate_carries_the_recall_items(tree, monkeypatch):
    cfg = {'status': 'onboarding', 'window': [2016, 2026]}
    monkeypatch.setattr(G.S, 'get', lambda key: cfg)
    monkeypatch.setattr(G, 'traps_for', lambda key, stage: [])
    monkeypatch.setattr(G, 'acceptance_gate', lambda key, part: [])
    monkeypatch.setattr(G, 'audit_open', lambda key, checks: ([], {c: True for c in checks}))
    r = G.evaluate('u', 6)
    assert r['gate'] == 'fail' and any(x.startswith('recall record:') for x in r['items']) and 'recall_r1' in r
    monkeypatch.setattr(R, 'gate_items', lambda key, th=None: [])
    assert G.evaluate('u', 6)['gate'] == 'pass'


def test_capture_from_file_then_check_sha(tree, tmp_path):
    f = tmp_path / 'page.html'
    f.write_bytes(b'<html>Current members: Ada Lovelace</html>')
    c = sqlite3.connect(':memory:')
    c.execute('create table live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    out = R.capture('u', 'PI00', 'https://lab.example/p', file=f, store=c)
    assert out['sha256'] == hashlib.sha256(f.read_bytes()).hexdigest()
    sp = R.stored_page(c, 'https://lab.example/p')
    assert sp['sha256'] == out['sha256'] and 'ada lovelace' in R.page_text(sp['raw'])


def test_capture_live_stops_at_refusal_and_challenge(tree, monkeypatch):
    import school_web as W
    c = sqlite3.connect(':memory:')
    c.execute('create table live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    monkeypatch.setattr(W, 'live', lambda conn, url: None)
    with pytest.raises(SystemExit, match='robots'):
        R.capture('u', 'PI00', 'https://x.example/a', store=c, sleep=lambda s: None)
    monkeypatch.setattr(W, 'live', lambda conn, url: (999, 'x', []))
    with pytest.raises(SystemExit, match='challenge'):
        R.capture('u', 'PI00', 'https://x.example/a', store=c, sleep=lambda s: None)


def test_ratchet_levels_are_coherent_and_fixed_bars_stay():
    assert R.FIXED_BARS == dict(R1=0.90, Z=0.05, X=0.20)
    assert [(l['U'], l['R2']) for l in R.RATCHET_LEVELS] == [(0.60, 0.35), (0.50, 0.40), (0.40, 0.50), (0.30, 0.60)]
    for i, lv in enumerate(R.RATCHET_LEVELS):
        assert lv['R2'] <= (1 - lv['U']) * R.FIXED_BARS['R1'] + 1e-9, f'level {i}: R2 above the (1-U) x R1 ceiling'
        b = R.bars(i)
        assert (b['R1'], b['Z'], b['X'], b['U'], b['R2']) == (0.90, 0.05, 0.20, lv['U'], lv['R2'])
    us = [l['U'] for l in R.RATCHET_LEVELS]
    r2 = [l['R2'] for l in R.RATCHET_LEVELS]
    assert us == sorted(us, reverse=True) and r2 == sorted(r2)   # each level is tighter
    assert R.RATCHET_LEVEL == 0 and R.THRESHOLDS == R.bars(0)


def test_ratchet_text_names_level_bars_and_next(monkeypatch):
    t = R.ratchet_text()
    assert 'level 0 of 3' in t and 'U <= 60%' in t and 'R2 >= 0.35' in t and 'next level 1: U <= 50%, R2 >= 0.40' in t
    monkeypatch.setattr(R, 'RATCHET_LEVEL', 3)
    assert 'long-term target' in R.ratchet_text() and 'next level' not in R.ratchet_text()


def test_level_change_changes_bars_not_the_record(tree, monkeypatch):
    # the same recorded numbers pass at one level and fail at another: a level change only moves the bars
    rec = R.draw('u', drawn_by='d')
    listed = {r['pi']: [{'name': f'Gone {r["pi"]} {i}', 'role': 'phd', 'section': 'current'} for i in range(3)] for r in rec['sample'][:18]}
    pages = {}
    rec = fill(rec, pages, listed)   # 18 readable (all names missing: R1 0), 12 unverifiable (U .40)
    (tree['dir'] / 'student-recall-check.json').write_text(json.dumps(rec))
    make_store(tree, pages)
    monkeypatch.setattr(R, 'captures_path', lambda key: tree['root'] / 'u' / 'cap.sqlite')
    for lvl, u_fails in ((0, False), (1, False), (2, False), (3, True)):
        monkeypatch.setattr(R, 'RATCHET_LEVEL', lvl)
        msgs = R.gate_items('u')
        assert any(x.startswith('recall U:') for x in msgs) == u_fails, lvl
        assert any(x.startswith('recall R2:') and f'ratchet level {lvl} of 3' in x for x in msgs)
    assert not any(x.startswith('recall record:') and 'build changed' in x for x in R.gate_items('u'))



def test_capture_refuses_charter_use_none(tree, monkeypatch):
    import school_config as S
    monkeypatch.setattr(S, 'get', lambda key: {'hosts': [{'host': 'www.blocked.example', 'use': 'none'}]})
    c = sqlite3.connect(':memory:')
    c.execute('create table live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    with pytest.raises(SystemExit, match='use=none'):
        R.capture('u', 'PI00', 'https://blocked.example/p', store=c, sleep=lambda s: None)


def test_page_text_lines_keeps_block_breaks():
    assert R.page_text_lines(b'<ul><li>A One</li><li>B Two</li></ul><script>x</script>') == 'A One\nB Two'


def test_page_text_reads_attribute_names_of_a_data_file():
    assert 'ada lovelace' in R.page_text(b'<people><person name="Ada Lovelace" role="phd"/></people>')
    assert 'ada lovelace' not in R.page_text(b'<html><body><a title="Ada Lovelace">x</a></body></html>')


def test_capture_never_refetches_a_host_after_challenge_or_robots_refusal(tree, monkeypatch):
    import school_web as W
    calls = []
    c = sqlite3.connect(':memory:')
    c.execute('create table live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    monkeypatch.setattr(W, 'live', lambda conn, url: calls.append(url) or (999, 'x', []))
    with pytest.raises(SystemExit, match='challenge'):
        R.capture('u', 'PI00', 'https://chal.example/a', store=c, sleep=lambda s: None)
    with pytest.raises(SystemExit, match='blocked since an earlier'):   # a different URL on the same host, same run or a later process (the store persists)
        R.capture('u', 'PI00', 'https://chal.example/b', store=c, sleep=lambda s: None)
    monkeypatch.setattr(W, 'live', lambda conn, url: calls.append(url))   # robots refusal returns None
    with pytest.raises(SystemExit, match='robots'):
        R.capture('u', 'PI00', 'https://nor.example/a', store=c, sleep=lambda s: None)
    with pytest.raises(SystemExit, match='blocked since an earlier'):
        R.capture('u', 'PI00', 'https://nor.example/b', store=c, sleep=lambda s: None)
    assert calls == ['https://chal.example/a', 'https://nor.example/a']


def test_gitignore_whitelists_the_recall_record_for_every_school(tmp_path):
    import subprocess
    root = Path(__file__).resolve().parents[1]
    ignore = (root / '.gitignore').read_text()
    assert '!hierarchy/*/reviewed/student-recall-check.json' in ignore.splitlines()
    # Release tests run from a git archive, which has no .git directory. Check
    # the repository's rules in an isolated git worktree instead.
    (tmp_path / '.gitignore').write_text(ignore)
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    for key in ('mit', 'stanford', 'anyschool'):
        r = subprocess.run(['git', 'check-ignore', '-q', f'hierarchy/{key}/reviewed/student-recall-check.json'], cwd=tmp_path)
        assert r.returncode == 1, f'{key}: the recall record is git-ignored'


def test_page_text_reads_utf16_pages():
    raw = '<html><body>Ada Lovelace</body></html>'.encode('utf-16')
    assert 'ada lovelace' in R.page_text(raw) and 'Ada Lovelace' in R.page_text_lines(raw)


def test_R_STU_32_captured_pdf_supervision_text_is_checked_against_original_bytes():
    fitz = pytest.importorskip('fitz')
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), 'Doctoral Supervision')
    page.insert_text((72, 90), 'Ada Lovelace (2025-)')
    raw = doc.tobytes()
    doc.close()
    assert raw.startswith(b'%PDF-')
    assert 'Doctoral Supervision' in R.page_text_lines(raw)
    assert 'ada lovelace' in R.page_text(raw)
    conn = sqlite3.connect(':memory:')
    conn.execute('create table live (url text, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    conn.execute('insert into live values (?,?,?,?,?,?,?)',
                 ('https://lab.example/cv.pdf', '2026-11-14', 200, hashlib.sha256(raw).hexdigest(),
                  'application/pdf', zlib.compress(raw), ''))
    assert R.stored_page(conn, 'https://lab.example/cv.pdf')['sha256'] == hashlib.sha256(raw).hexdigest()


def test_page_text_joins_adjacent_inline_spans_in_a_name():
    raw = b'<html><body><span>J</span><span>onas Ballweg</span></body></html>'
    assert 'jonas ballweg' in R.page_text(raw)


def test_page_text_preserves_names_split_by_inline_links_and_formatting():
    raw = (b'<html><body><p><b>J<a href="photo.png">ulie McIntosh</a></b></p>'
           b'<p><font><b>Theo Chalvatzi</b></font><font><b>s</b></font></p>'
           b'<pre><font>V</font><font>ivek Dhande:</font></pre></body></html>')
    text = R.page_text(raw)
    assert all(name in text for name in ['julie mcintosh', 'theo chalvatzis', 'vivek dhande'])


def test_page_text_inline_reading_keeps_blocks_apart_and_ignores_hidden_sources():
    raw = (b'<html><body><p>J</p><p>ulie McIntosh</p>'
           b'<a title="Ada Lovelace">visible</a><!-- Grace Hopper -->'
           b'<script><b>Katherine Johnson</b></script></body></html>')
    text = R.page_text(raw)
    assert all(name not in text for name in
               ['julie mcintosh', 'ada lovelace', 'grace hopper', 'katherine johnson'])


def test_R_STU_28_names_on_any_captured_page_of_the_pi_same_host_only(tree):
    """R-STU-28: a listed name may be on any captured page of the PI on the primary page's host; a name on no page, a page of another host,
    a bad sha and an unstored page are findings; a single `page` dict still works; small-caps spacing is folded."""
    rec = R.draw('u', drawn_by='drawer')
    pi = rec['sample'][-1]['pi']
    listed = {pi: [{'name': 'Real One', 'role': 'phd', 'section': 'current'}]}
    pages = {}
    rec = fill(rec, pages, listed)
    r = next(x for x in rec['sample'] if x['pi'] == pi)
    assert isinstance(r['page'], dict)   # the old single-page shape
    alum = b'<html><body><h2>Alumni</h2><li>Old Student 2019</li><li>Jonathan S HEWCHUK</li></body></html>'
    other = b'<html><body>Old Student</body></html>'
    pages['https://lab.example/alumni'] = alum
    pages['https://elsewhere.example/alumni'] = other
    conn = make_store(tree, pages)
    assert R.evaluate_record('u', rec, conn=conn)['findings'] == []   # unchanged with one page
    r['listed'] = r['listed'] + [{'name': 'Old Student', 'role': 'phd', 'section': 'alumni', 'years': [2019]},
                                {'name': 'Jonathan Shewchuk', 'role': 'phd', 'section': 'alumni', 'years': [2019]}]
    f = R.evaluate_record('u', rec, conn=conn)['findings']
    assert any('not on any captured page of the PI' in x for x in f)
    sha = hashlib.sha256(alum).hexdigest()
    r['extra_pages'] = [dict(url='https://lab.example/alumni', sha256=sha)]
    assert R.evaluate_record('u', rec, conn=conn)['findings'] == []
    r['page'] = [r['page'], dict(url='https://lab.example/alumni', sha256=sha)]   # the list form is the same
    del r['extra_pages']
    assert R.evaluate_record('u', rec, conn=conn)['findings'] == []
    r['extra_pages'] = [dict(url='https://lab.example/alumni', sha256=sha)]   # tokens do not combine across pages
    r['listed'] = r['listed'] + [{'name': 'Real Student', 'role': 'phd', 'section': 'current'}]
    assert any('not on any captured page' in x for x in R.evaluate_record('u', rec, conn=conn)['findings'])
    r['listed'] = r['listed'][:-1]
    r['extra_pages'] = [dict(url='https://elsewhere.example/alumni', sha256=hashlib.sha256(other).hexdigest())]
    r['listed'] = [x for x in r['listed'] if x['name'] != 'Jonathan Shewchuk']
    f = R.evaluate_record('u', rec, conn=conn)['findings']
    assert any('not on the host' in x for x in f)
    r['extra_pages'] = [dict(url='https://lab.example/alumni', sha256='0' * 64)]
    assert any('does not match the stored capture' in x for x in R.evaluate_record('u', rec, conn=conn)['findings'])
    r['extra_pages'] = [dict(url='https://lab.example/nope', sha256=sha)]
    assert any('not in the capture store' in x for x in R.evaluate_record('u', rec, conn=conn)['findings'])


def test_R_STU_28_wayback_capture_belongs_to_the_archived_host():
    assert R._host('https://web.archive.org/web/20261105id_/http://www.lab.example/people.html') == 'lab.example'
    assert R._host('https://www.lab.example/x') == 'lab.example'


@pytest.mark.parametrize('html', [
    b'<html><body><h2>Current students</h2><!-- <p>Ryo Hidden, PhD Student</p> --><p>Ada Visible, PhD Student</p></body></html>',
    b'<html><body><p>Ada Visible</p><!-- <p>Ryo Hidden</p>',
])
def test_recall_source_text_excludes_hidden_html_comments(html):
    for text in (R.page_text(html), R.page_text_lines(html).casefold()):
        assert 'ada visible' in text
        assert 'ryo hidden' not in text
