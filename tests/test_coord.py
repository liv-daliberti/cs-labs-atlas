"""tools/coord.py: log/ask/answer/decide, concurrent appends, the legacy cutover and sync, the old-questions import."""
import multiprocessing as mp

import coord as C

S = 'claude-test-1'


def _noter(args):
    root, i = args
    C.note(f'event {i} ' + 'x' * 3000, session=f's{i}', task=f'T{i}', root=root)


def test_note_stamps_session_task_school(tmp_path):
    line = C.note('hello\nworld', session=S, task='T1', school='mit', root=tmp_path)
    assert line.startswith('- 20') and f' UTC {S} (T1) [mit]: hello world' in line
    assert (tmp_path / 'LOG.md').read_text() == line + '\n'


def test_concurrent_notes_never_interleave(tmp_path):
    with mp.get_context('fork').Pool(8) as pool:
        pool.map(_noter, [(tmp_path, i) for i in range(64)])
    lines = (tmp_path / 'LOG.md').read_text().splitlines()
    assert len(lines) == 64 and all(x.startswith('- 20') and x.endswith('x' * 3000) for x in lines)
    assert len({x.split(' UTC ')[1].split(' ')[0] for x in lines}) == 64


def _asker(args):
    root, i = args
    return C.ask(f'q{i}', 'mit', session=f's{i}', root=root)


def test_concurrent_asks_get_distinct_ids(tmp_path):
    with mp.get_context('fork').Pool(8) as pool:
        ids = pool.map(_asker, [(tmp_path, i) for i in range(24)])
    assert len(set(ids)) == 24 and len(C.read_questions(tmp_path)) == 24


def test_ask_list_answer_decide(tmp_path):
    a = C.ask('May we fetch X?\nsecond line', 'hkust', rec='yes', task='T9', session=S, root=tmp_path)
    b = C.ask('Other?', 'mit', session=S, root=tmp_path)
    assert (a, b) == ('Q-0001', 'Q-0002')
    assert C.answer('Q-0001', 'Yes, robots first.', session='owner', root=tmp_path)
    assert not C.answer('Q-0099', 'x', session='owner', root=tmp_path)
    qs = {q['id']: q for q in C.read_questions(tmp_path)}
    assert qs['Q-0001']['status'] == 'answered' and 'Yes, robots first.' in qs['Q-0001']['text'] and qs['Q-0001']['question'] == 'May we fetch X?\nsecond line'
    assert qs['Q-0002']['status'] == 'open' and '- recommendation: (none given)' in qs['Q-0002']['text']
    d = C.decide('Per-school promotion is allowed.', ref='Q-0001', session=S, root=tmp_path)
    assert d == 'D-0001' and 'ref Q-0001: Per-school promotion' in (tmp_path / 'DECISIONS.md').read_text()
    log = (tmp_path / 'LOG.md').read_text()
    assert 'asked the owner Q-0001' in log and 'owner answered Q-0001' in log and 'decision D-0001' in log


def test_cli_list_filters(tmp_path, capsys):
    C.ask('one', 'mit', session=S, root=tmp_path)
    C.ask('two', 'cmu', session=S, root=tmp_path)
    C.answer('Q-0002', 'ok', session=S, root=tmp_path)
    assert C.main(['ask', '--list', '--open', '--root', str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert 'Q-0001' in out and 'Q-0002' not in out
    C.main(['ask', '--list', '--school', 'cmu', '--root', str(tmp_path)])
    assert 'Q-0002 [cmu] answered' in capsys.readouterr().out


def test_cutover_and_sync_legacy(tmp_path):
    old = tmp_path / 'old.md'
    old.write_text('- before 1\n- before 2\n')
    root = tmp_path / 'coord'
    t, off = C.cutover(session=S, root=root, old=old)
    assert old.read_text().splitlines()[-1].startswith(f'- {t} UTC {S} (V4b): FROZEN') and off == old.stat().st_size
    assert (root / 'LOG.md').read_text().startswith(f'- {t} UTC {S} (V4b): LOG START')
    assert C.sync_legacy(root) == 0
    with open(old, 'a') as f:
        f.write('- 2026-11-17T23:00:00Z UTC stray (T1): late line\n- half written')
    assert C.sync_legacy(root) == 1                       # the unterminated line waits
    with open(old, 'a') as f:
        f.write(' done\n')
    assert C.sync_legacy(root) == 1 and C.sync_legacy(root) == 0
    log = (root / 'LOG.md').read_text().splitlines()
    assert log[-2].endswith('legacy: 2026-11-17T23:00:00Z UTC stray (T1): late line') and log[-1].endswith('legacy: half written done')
    assert 'before 1' not in ''.join(log)
    try:
        C.cutover(session=S, root=root, old=old)
        raise AssertionError('second cutover must refuse')
    except SystemExit:
        pass


def test_import_open_questions(tmp_path):
    old = tmp_path / 'q.md'
    old.write_text('- [hkust] Open one?\n- [ANSWERED by owner] done one mit\n- Toronto: still pending\n\n'
                   '## 10:00Z ZJU: heading\n- body line RESOLVED by owner. Still open: part two\n1. numbered\n\n'
                   '- 2026-11-12 coordinator: RESOLVED by owner: yes\n')
    sd = tmp_path / 'schools'; sd.mkdir()
    for k in ('hkust', 'toronto', 'zju', 'mit'):
        (sd / f'{k}.toml').write_text('')
    root = tmp_path / 'coord'
    n, total = C.import_questions(session=S, root=root, old=old, schools_dir=sd)
    assert (n, total) == (3, 5)
    qs = C.read_questions(root)
    assert [q['school'] for q in qs] == ['hkust', 'toronto', 'zju'] and all(q['status'] == 'open' for q in qs)
    assert 'Open one?' in qs[0]['question'] and 'OVERNIGHT-QUESTIONS.md lines 1-1' in qs[0]['text']
    assert 'numbered' in qs[2]['question']
    try:
        C.import_questions(session=S, root=root, old=old, schools_dir=sd)
        raise AssertionError('second import must refuse')
    except SystemExit:
        pass
