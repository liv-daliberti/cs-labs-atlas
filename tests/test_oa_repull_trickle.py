"""tools/oa_repull_trickle.py (ROADMAP #51): chunk plan, release deferral, credit-cap arithmetic, redaction on every error path, merge guard."""
import datetime as dt
import json
import sqlite3
import subprocess

import pytest

import oa_api  # noqa: E402
import oa_refresh_works as R  # noqa: E402
import oa_repull_trickle as T  # noqa: E402

KEY = 'k3y-SECRET-0123456789'


def test_plan_covers_81_chunks_newest_year_first_and_rotates():
    c = T.plan_chunks()
    assert len(c) == 81 and len(set(c)) == 81
    assert [y for _, y in c] == sorted((y for _, y in c), reverse=True) and c[0][1] == 2024 and c[-1][1] == 2016
    firsts = [c[i * 9][0] for i in range(9)]
    assert len(set(firsts)) == 9                                   # no school always goes first (or last)


def test_pending_skips_done_and_survives_torn_line(tmp_path):
    p = tmp_path / 'progress.jsonl'
    p.write_text(json.dumps(dict(event='chunk_done', school='mit', year=2024)) + '\n{"event": "chunk_do')
    ev = T.read_progress(p)
    assert T.done_chunks(ev) == {('mit', 2024)}
    assert ('mit', 2024) not in T.pending_chunks(T.plan_chunks(), ev) and len(T.pending_chunks(T.plan_chunks(), ev)) == 80


def led(tmp_path, rows):
    p = tmp_path / 'l.jsonl'
    p.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    return p


def test_cap_arithmetic(tmp_path):
    p = led(tmp_path, [
        dict(at='2026-11-06T01:00:00+00:00', kind='repull:mit:inst', status=200, credits='1', remaining='9000'),
        dict(at='2026-11-06T01:00:01+00:00', kind='repull:mit:pi', status=200, credits='1', remaining='8900'),
        dict(at='2026-11-06T01:00:02+00:00', kind='refresh2026:singleton', status=200, credits='0', remaining='8890'),
        dict(at='2026-11-06T02:00:00+00:00', kind='other:x', status=200, credits='7', remaining='8000'),
        dict(at='2026-11-05T23:59:59+00:00', kind='repull:mit:inst', status=200, credits='500', remaining='100')])
    assert T.credits_today(p, '2026-11-06') == 2                    # only today's, only repull*, other agents' credits are not ours
    assert T.shared_remaining_today(p, '2026-11-06') == 8000        # yesterday's low 'remaining' is stale
    assert T.shared_remaining_today(p, '2026-11-07') is None
    assert T.day_allowance(2000, 2, 8000, 3000) == 1998
    assert T.day_allowance(2000, 1990, 9000, 3000) == 10           # the daily cap binds
    assert T.day_allowance(2000, 100, 3050, 3000) == 50            # the shared floor binds
    assert T.day_allowance(2000, 100, 2999, 3000) == 0 and T.day_allowance(2000, 2000, None, 3000) == 0
    assert T.day_allowance(2000, 0, None, 3000) == 2000


def test_estimates_and_days():
    assert T.estimate_credits(0, 0) == 1 and T.estimate_credits(400, 50) == 1 + 2 + 2 + 1
    assert 120 <= T.estimate_credits(25016, 280) <= 160                    # measured: Stanford 2024 cost 134
    assert T.days_to_finish([1000] * 5, 2000) == 3 and T.days_to_finish([], 2000) == 0


def test_next_utc_day_begin_is_utc_midnight_plus_ten():
    s = T.next_utc_day_begin(dt.datetime(2026, 11, 6, 23, 50, tzinfo=dt.timezone.utc))
    local = dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S').astimezone()      # sbatch reads --begin as local time
    assert local.astimezone(dt.timezone.utc) == dt.datetime(2026, 11, 7, 0, 10, tzinfo=dt.timezone.utc)


def fake_run(out='', rc=0):
    return lambda cmd: subprocess.CompletedProcess(cmd, rc, out, '')


def test_release_guard_defers_on_any_release_and_on_unknowns(monkeypatch):
    kw = dict(clock=lambda: 1e9, sleep=lambda s: None)
    T._last_squeue[0] = 0.0
    assert T.release_jobs(fake_run(''), **kw) == []
    T.guard_no_release(fake_run(''), **kw)
    with pytest.raises(T.Deferred) as e:
        T.guard_no_release(fake_run('32110109\n'), **kw)
    assert e.value.jobs == ['32110109']
    with pytest.raises(T.Deferred):                                 # squeue failing = unknown = no write
        T.guard_no_release(fake_run('', rc=1), **kw)

    def boom(cmd):
        raise OSError('no squeue')
    with pytest.raises(T.Deferred):
        T.guard_no_release(boom, **kw)


def test_squeue_calls_are_60s_apart():
    t = [100.0]
    slept = []
    T._last_squeue[0] = 0.0
    T.release_jobs(fake_run(''), clock=lambda: t[0], sleep=slept.append)
    t[0] += 10
    T.release_jobs(fake_run(''), clock=lambda: t[0], sleep=slept.append)
    assert slept == [50.0]


def test_submit_refuses_preempts_and_tries_the_next_place():
    calls = []

    def run(cmd, cwd):
        calls.append(cmd)
        if '--test-only' in cmd:
            bad = '--partition=cs' in cmd
            return subprocess.CompletedProcess(cmd, 0, '', 'Preempts: 123' if bad else 'would start')
        return subprocess.CompletedProcess(cmd, 0, 'Submitted batch job 77\n', '')
    assert T.submit(T.sbatch_argv('x.slurm', begin='2026-11-07T00:10:00'), '.', run) == '77'
    real = [c for c in calls if '--test-only' not in c]
    assert len(real) == 1 and '--partition=mltheory' in real[0]            # the preempting plan was never submitted


def test_submit_pushes_begin_when_every_place_preempts_and_gives_up():
    calls = []

    def run(cmd, cwd):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, '', 'Preempts: 1')
    with pytest.raises(RuntimeError, match='Preempts'):
        T.submit(T.sbatch_argv('x.slurm'), '.', run, retries=2)
    assert all('--test-only' in c for c in calls) and len(calls) == 6      # nothing was ever submitted


def test_sbatch_argv_dependencies_and_exclude():
    a = T.sbatch_argv('x.slurm', after=[1, 2], singleton=True, export={'A': 'b'})
    assert '--dependency=afterany:1:2,singleton' in a and '--exclude=node302' in a and '--export=ALL,A=b' in a


def test_redaction_on_error_paths(tmp_path, monkeypatch, capsys):
    import requests

    cl = oa_api.Client(cap=5, key=KEY, ledger=tmp_path / 'l.jsonl')
    monkeypatch.setattr(oa_api.time, 'sleep', lambda *_: None)

    class Resp:
        status_code = 429
        headers = {}
        text = f'Plan upgrade required for api_key={KEY}'

    monkeypatch.setattr(cl.s, 'get', lambda *a, **k: Resp())
    with pytest.raises(oa_api.OAError) as e:
        cl.get('works', {'filter': 'x'})
    assert KEY not in str(e.value)

    def boom(*a, **k):
        raise requests.ConnectionError(f'url /works?api_key={KEY}&mailto=o@w.er')
    monkeypatch.setattr(cl.s, 'get', boom)
    with pytest.raises(oa_api.OAError) as e:
        cl.get('works', {'filter': 'x'})
    assert KEY not in str(e.value) and KEY not in repr(e.value.__context__) and e.value.__cause__ is None
    # the trickle's own logging redacts whatever reaches it (a stalled chunk's reason, a progress record)
    st = T.State(tmp_path / 'state')
    monkeypatch.setenv('OPENALEX_API_KEY', KEY)
    st.log('stalled', reason=f'boom api_key={KEY} and {KEY}')
    assert KEY not in st.progress.read_text() and 'api_key=***' in st.progress.read_text()
    assert KEY not in oa_api.redact(f'RuntimeError: ...?api_key={KEY}', KEY)


def test_run_day_stall_message_is_redacted(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('OPENALEX_API_KEY', KEY)
    monkeypatch.setattr(T, 'guard_no_release', lambda *a, **k: None)
    monkeypatch.setattr(T, 'pending_chunks', lambda *a: [('mit', 2024)])
    monkeypatch.setattr(T, 'run_chunk', lambda *a, **k: (_ for _ in ()).throw(RuntimeError(f'x api_key={KEY}')))
    monkeypatch.setattr(oa_api, 'install_excepthook', lambda *a, **k: None)
    monkeypatch.setattr(oa_api.Client, '__init__', lambda self, **k: None)
    args = type('A', (), dict(cap=2000, floor=3000, max_chunks=0))()
    st = T.State(tmp_path / 's')
    assert T.run_day(args, st, ledger=tmp_path / 'none.jsonl', resubmit=False) == 1
    out = capsys.readouterr()
    assert KEY not in out.err and KEY not in out.out and KEY not in st.progress.read_text()


def test_merge_guard_blocks_before_any_write(tmp_path, monkeypatch):
    sweep = tmp_path / 'sweep.sqlite'
    sc = sqlite3.connect(sweep)
    sc.execute('create table pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob, primary key (year, page))')
    w = dict(id='https://openalex.org/W1', doi=None, title='t', publication_year=2020, type='article', ids={}, primary_location=None, authorships=[])
    sc.execute('insert into pages values (2020,0,"*",null,1,1,"x",?)', (R.pack([w]),)); sc.commit(); sc.close()
    pw = tmp_path / 'pw.sqlite'
    pc = sqlite3.connect(pw); pc.execute('create table works (id text primary key, body blob)'); pc.commit(); pc.close()
    stage = tmp_path / 'stage'; stage.mkdir()
    monkeypatch.setattr(R, 'stage_dir', lambda tag=R.TAG: stage)
    monkeypatch.setattr(R.P, 'data_w', lambda name, school=None, **k: sweep if name.startswith('openalex') else pw)
    monkeypatch.setattr(R, 'pi_author_ids', lambda school: [])
    monkeypatch.setattr(R, 'sweep_source', lambda sc: None)
    st = R.stage_db('x', 'T')
    st.execute('insert into pages values ("inst","2020",0,null,1,1,"x",?)', (R.pack([dict(w, title='new')]),))
    st.execute('insert into counts values ("all:2020",1,"x")'); st.execute('insert into done values ("inst","2020",1)'); st.commit(); st.close()

    def deny():
        raise T.Deferred(['32110109'])
    with pytest.raises(T.Deferred):
        R.merge('x', [2020], 'T', apply=True, guard=deny)
    assert not (stage / 'backup-x.sqlite').exists()
    c = sqlite3.connect(sweep)
    assert R.unpack(c.execute('select body from pages').fetchone()[0])[0]['title'] == 't'      # the store is unchanged
    R.merge('x', [2020], 'T', apply=True, guard=lambda: None)
    assert R.unpack(sqlite3.connect(sweep).execute('select body from pages').fetchone()[0])[0]['title'] == 'new'
