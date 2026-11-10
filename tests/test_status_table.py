"""tools/status_table.py (2026-11-10): the generated status table. Synthetic fixtures only (a fake release manifest, a fake package, a fake gate
result, a fake roster); nothing here reads the live project data."""
import argparse
import csv
import datetime
import gzip
import hashlib
import json
import subprocess

import pytest

import status_table as T


def put(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))
    return p


def put_gz(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, 'wt') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


ROSTER = ('site_id\tname\tcountry\tcohort_rank\trank_low\trank_high\tin_cohort\topenalex_id\n'
          'alpha-u\tAlpha University\tUS\t1\t1\t1\ttrue\tI1\n'
          'beta-u\tBeta University\tUK\t2\t2\t2\ttrue\tI2\n'
          'gamma-u\tGamma University\tFR\t3\t3\t3\ttrue\tI3\n'
          'delta-u\tDelta University\tDE\t51-75\t51\t75\ttrue\tI4\n'
          'eps-u\tEpsilon University\tDE\t201-300\t201\t300\ttrue\tI5\n'
          'out-u\tOutside University\tDE\t\t\t\tfalse\tI6\n')
CHARTER = 'key = "{k}"\nname = "{n}"\nstatus = "{s}"\n[ids]\nopenalex = ["{o}"]\n'


@pytest.fixture
def world(tmp_path):
    root = tmp_path / 'root'
    (root / 'schools').mkdir(parents=True)
    (root / 'schools' / 'alpha.toml').write_text(CHARTER.format(k='alpha', n='Alpha University', s='released', o='I1'))
    (root / 'schools' / 'beta.toml').write_text(CHARTER.format(k='beta', n='Beta University', s='onboarding', o='I2'))
    (root / 'schools' / 'TEMPLATE.toml').write_text(CHARTER.format(k='template', n='x', s='onboarding', o='I0'))
    roster = root / 'roster.tsv'
    roster.write_text(ROSTER)
    # a frozen release that counts alpha
    rel = root / 'releases' / '2026-11-07'
    put(rel / 'MANIFEST.json', dict(release='2026-11-07', created='2026-11-07T08:00:00Z',
                                    counts=dict(alpha=dict(builtAt='2026-11-07T06:00:00Z', pis=10, lab_papers=120, students=30, lab_student_pairs=40, pis_with_lab_papers=9))))
    put(rel / 'hierarchy' / 'alpha' / 'copies.json', dict(summary=dict(lab_papers=100, local=60, local_share=0.6, counted_at='2026-11-07T07:00:00Z'), papers={}))
    put(rel / 'hierarchy' / 'alpha' / 'students.json', {'P1': [{'person': 'a'}, {'person': 'b'}], 'P2': [{'person': 'a'}]})
    (root / 'releases' / 'latest').symlink_to(rel)
    # an isolated package for beta: 5 rows, 3 distinct works (a work listed under two PIs and a row without an id)
    pk = root / 'scratch' / 'beta-pkg' / 'beta'
    put_gz(pk / 'lab_papers.jsonl.gz', [dict(pi='P1', oa='W1', title='One'), dict(pi='P2', oa='W1', title='One'), dict(pi='P1', oa='W2', title='Two'),
                                        dict(pi='P1', doi='10.1/X', title='Three'), dict(pi='P1', doi='10.1/x', title='Three')])
    put(pk / 'pis.json', [dict(pi='P1'), dict(pi='P2'), dict(pi='P3')])
    put(pk / 'students.json', {'P1': [{'person': 's1'}, {'person': 's2'}], 'P2': [{'person': 's1'}]})
    put(pk / 'report.json', dict(builtAt='2026-11-09T12:00:00Z', counts=dict(students=2, lab_student_pairs=3)))
    return root


def args(**kw):
    return argparse.Namespace(**dict(dict(gates='off', registry=None), **kw))


def ctx_for(root, **over):
    reg = over.pop('registry', dict(packages=dict(beta=dict(basis='native package', path='scratch/beta-pkg/beta', next_step='go')), paper_target=100))
    ov = dict(root=root, code=root, registry=reg, charters=T.load_charters(root / 'schools'), release=T.frozen_release(root / 'releases'),
              data=lambda key, name: root / 'hierarchy' / key / name, collectors=root / 'none.json', no_nice=True)
    ov.update(over)
    c = T.make_context(args(), ov)
    c.update(git={}, queue={})
    return c


def test_package_counts_distinct_works_not_rows(world):
    s = T.package_stats(world / 'scratch' / 'beta-pkg' / 'beta')
    assert s['rows'] == 5 and s['distinct'] == 3          # W1, W2 and one DOI (case-folded)
    assert s['relations'] == 4 and s['pis_with_papers'] == 2 and s['pis'] == 3
    assert s['students'] == 2 and s['lab_student_pairs'] == 3 and s['member_pairs'] == 3 and s['built_at'] == '2026-11-09T12:00:00Z'
    assert T.package_stats(world / 'missing') is None


def test_frozen_release_and_school(world):
    rel = T.frozen_release(world / 'releases')
    assert rel['id'] == '2026-11-07' and set(rel['counts']) == {'alpha'}
    f = T.frozen_school(rel, 'alpha')
    assert f['distinct'] == 100 and f['lab_papers'] == 120 and f['local'] == 60 and f['member_pairs'] == 3
    assert T.frozen_school(rel, 'beta') is None and T.frozen_release(world / 'nowhere') is None
    (world / 'releases' / 'latest').unlink()                  # no `latest`: the newest dated directory with a manifest
    assert T.frozen_release(world / 'releases')['id'] == '2026-11-07'


def test_registry_candidates_prefer_newest_built_and_stay_under_root(world):
    d, flags = T.resolve_package(dict(candidates=['scratch/not-built'], path='scratch/beta-pkg/beta'), world)
    assert d == world / 'scratch' / 'beta-pkg' / 'beta' and 'newer candidate not built yet' in flags[0]
    d, flags = T.resolve_package(dict(path='../outside'), world)
    assert d is None and 'leaves the project root' in flags[0]
    d, flags = T.resolve_package(dict(path='scratch/missing'), world)
    assert d is None and 'not found' in flags[0]


def test_universe_ranks_bands_and_inventory(world):
    reg = dict(inventory=dict(gam=dict(site_id='gamma-u')))
    rows = T.universe(T.load_roster(world / 'roster.tsv'), T.load_charters(world / 'schools'), reg, top=3)
    assert [(r['key'], r['rank']) for r in rows] == [('alpha', '1'), ('beta', '2'), ('gam', '3')]     # delta/epsilon are beyond top 3 and have no charter
    rows = T.universe(T.load_roster(world / 'roster.tsv'), {}, {}, top=3)                               # nothing registered: keys fall back to the site id
    assert rows[2]['key'] == 'gamma-u' and not rows[2]['registered']
    ch = T.load_charters(world / 'schools')
    ch['delta'] = dict(name='Delta University', status='onboarding', openalex='I4')
    rows = T.universe(T.load_roster(world / 'roster.tsv'), ch, {}, top=1)
    assert [(r['key'], r['rank']) for r in rows] == [('alpha', '1'), ('beta', '2'), ('delta', '51-75')]  # a charter school keeps its band
    assert T.universe(T.load_roster(world / 'roster.tsv'), ch, {}, top=1, only={'alpha'})[0]['key'] == 'alpha'


def test_gates_live_recorded_off_and_gates_left():
    live = {0: dict(gate='pass', open=0), 3: dict(gate='waived', open=2), 5: dict(gate='fail', open=7)}

    def live_fn(key, n):
        if n == 8:
            raise RuntimeError('boom')
        return live.get(n, dict(gate='pass', open=0))

    def rec_fn(key, n):
        return dict(gate='fail', open=4, at='2026-11-04') if n in (8, 9) else None
    cells, basis, flags = T.gates_for('x', 'live', live_fn, rec_fn)
    assert basis == 'live+recorded' and any('gate 8' in f for f in flags)
    assert T.gate_cell(cells[5]) == 'fail (7 open)' and T.gate_cell(cells[8]) == 'recorded 2026-11-04: fail (4 open)'
    assert T.gate_cell(cells[0]) == 'pass' and T.gate_cell(cells[3]) == 'waived (2 open)'
    assert T.gates_left(cells) == '3w,5,8'
    cells, basis, _ = T.gates_for('x', 'recorded', live_fn, rec_fn)
    assert basis == 'recorded' and T.gates_left(cells).startswith('0?,1?') and T.gate_cell(cells[0]) == ''   # unknown, never pass
    cells, basis, flags = T.gates_for('x', 'off', live_fn, rec_fn, has_charter=False)
    assert basis == 'no charter' and flags and not any(cells.values())


def test_recorded_gate_reads_the_stage_file(tmp_path):
    put(tmp_path / 'k' / 'reports' / 'stage-4-gate.json', dict(at='2026-11-04T10:00:00Z', result=dict(gate='fail', open=2)))
    assert T.recorded_gate('k', 4, tmp_path) == dict(gate='fail', open=2, at='2026-11-04')
    assert T.recorded_gate('k', 5, tmp_path) is None


def test_row_for_a_released_school_uses_frozen_counts_and_blank_is_not_zero(world):
    ctx = ctx_for(world)
    u = dict(key='alpha', rank='1', rank_low=1, university='Alpha University', country='US', registered=True)
    r = T.build_row(u, ctx)
    assert (r['state'], r['PIs'], r['papers'], r['known_member_lab_pairs'], r['known_student_lab_pairs']) == ('built', 10, 100, 3, 40)
    assert r['frozen_lab_paper_rows'] == 120 and r['frozen_distinct_papers'] == 100          # rows and works stay apart
    assert r['copies_local'] == 60 and r['copies_total'] == 100 and r['copies_share'] == 0.6
    assert r['admission_status'] == 'in frozen release 2026-11-07' and 'met in frozen release: 100 distinct >= 100' == r['target_status']
    assert r['data_as_of_utc'] == '2026-11-07T06:00:00Z' and 'MANIFEST.json' in r['source_files']
    assert r['package_distinct_works'] == '' and r['websites'] == '' and 'websites blank' in r['flags']
    ghost = T.build_row(dict(key='ghost', rank='9', rank_low=9, university='G', country='', registered=False), ctx)
    assert ghost['papers'] == '' and ghost['PIs'] == '' and ghost['data_as_of_utc'] == '' and ghost['state'] == 'staged'
    assert 'counts unknown' in ghost['flags'] and 'no charter' in ghost['flags'] and ghost['gates_left'] == '0,1,2,3,4,5,6,7,8,9,10'


def test_row_for_a_package_school_labels_basis_and_never_admits(world):
    ctx = ctx_for(world, registry=dict(paper_target=3, packages=dict(beta=dict(basis='native package', path='scratch/beta-pkg/beta', next_step='go',
                                                                              split=dict(source_backed_distinct=2, all_kept_distinct=3, as_of='2026-11-10', source='report.md')))))
    r = T.build_row(dict(key='beta', rank='2', rank_low=2, university='Beta University', country='UK', registered=True), ctx)
    assert (r['state'], r['papers'], r['package_pi_paper_relations'], r['package_pis_with_papers']) == ('staged', 3, 4, 2)
    assert r['counts_basis'].startswith('native package') and r['admission_status'] == 'not admitted' and r['next_step'] == 'go'
    assert (r['source_backed_distinct'], r['all_kept_distinct']) == (2, 3) and 'NOT admitted' in r['target_status']
    assert 'typed in the registry' in r['flags'] and 'not recomputed' in r['flags']          # the split is read, never recomputed, and said so
    assert r['data_as_of_utc'] == '2026-11-09T12:00:00Z' and r['package_path'] == 'scratch/beta-pkg/beta'
    assert r['copies_share'] == ''                                                              # no copies measured: blank


def test_copies_counter_in_the_registry_wins_and_a_base_mismatch_is_flagged(world):
    put(world / 'scratch' / 'counter' / 'copies.json', dict(summary=dict(lab_papers=9, local=3, local_share=0.333, counted_at='2026-11-10T01:00:00Z')))
    reg = dict(packages=dict(beta=dict(basis='b', path='scratch/beta-pkg/beta', copies_counter='scratch/counter/copies.json')))
    r = T.build_row(dict(key='beta', rank='2', rank_low=2, university='B', country='', registered=True), ctx_for(world, registry=reg))
    assert (r['copies_local'], r['copies_total']) == (3, 9) and 'scratch/counter/copies.json' in r['copies_source']
    assert 'copies base (9) differs' in r['flags']


def test_websites_come_from_the_register(world):
    ctx = ctx_for(world)
    put(world / 'hierarchy' / 'alpha' / 'lab-websites.json', dict(labs=[dict(coverage='website'), dict(coverage='reason'), dict(coverage='website')]))
    assert T.build_row(dict(key='alpha', rank='1', rank_low=1, university='A', country='', registered=True), ctx)['websites'] == 2


def test_carried_figures_are_used_only_without_a_live_source_and_flagged(world):
    reg = dict(carried=dict(ghost=dict(PIs=85, websites=16, as_of='2026-11-09T16:05:53Z', source='old.csv (carried)'), alpha=dict(websites=7, as_of='x', source='old.csv')))
    ctx = ctx_for(world, registry=reg)
    g = T.build_row(dict(key='ghost', rank='9', rank_low=9, university='G', country='', registered=True), ctx)
    assert (g['PIs'], g['websites'], g['papers'], g['data_as_of_utc']) == (85, 16, '', '2026-11-09T16:05:53Z') and 'carried' in g['flags']
    a = T.build_row(dict(key='alpha', rank='1', rank_low=1, university='A', country='', registered=True), ctx)
    assert a['PIs'] == 10 and a['websites'] == 7                      # the frozen PIs win; only the missing websites are carried
    put(world / 'hierarchy' / 'alpha' / 'lab-websites.json', dict(labs=[dict(coverage='website')]))
    assert T.build_row(dict(key='alpha', rank='1', rank_low=1, university='A', country='', registered=True), ctx)['websites'] == 1   # a live register wins


def test_queue_state_counts_live_stale_open_and_blocked():
    now = datetime.datetime.now(datetime.timezone.utc)

    def hb(minutes):
        return (now - datetime.timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M:%SZ')
    tasks = [dict(id='T1', school='a', status='claimed', session='s1', heartbeat=hb(1), ttl=1800),
             dict(id='T2', school='a', status='claimed', session='s2', heartbeat=hb(120), ttl=1800),
             dict(id='T3', school='a', status='open'), dict(id='T4', school='a', status='blocked'), dict(id='T5', school='', status='open'),
             dict(id='T6', school='a', status='done')]
    q = T.queue_state(tasks)['a']
    assert q['live'] == [('T1', 's1')] and q['stale'] == ['T2'] and q['open'] == ['T3'] and q['blocked'] == ['T4']


def test_ids_state_hashes_the_registry_and_counts_holds(tmp_path):
    (tmp_path / 'registry.sqlite').write_bytes(b'abc')
    put(tmp_path / 'IDS-REPORT.json', dict(at='2026-11-07T07:03:15Z'))
    s = T.ids_state(tmp_path)
    assert s['registry_sha256'] == hashlib.sha256(b'abc').hexdigest() and s['coadvising_holds'] is None and 'predates' in s['holds_note']
    put(tmp_path / 'IDS-REPORT.json', dict(at='x', coadvising_holds_skipped=[1, 2, 3]))
    assert T.ids_state(tmp_path)['coadvising_holds'] == 3 and T.ids_state(tmp_path / 'none')['registry_sha256'] is None


def test_git_state_lists_unlanded_branches_by_token(tmp_path):
    def g(*a):
        subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=t', '-c', 'user.email=t@t', *a], check=True, capture_output=True)
    g('init', '-q', '-b', 'main')
    (tmp_path / 'hierarchy' / 'alpha').mkdir(parents=True)
    (tmp_path / 'hierarchy' / 'alpha' / 'x.py').write_text('1')
    g('add', '-A')
    g('commit', '-q', '-m', 'alpha work on main')
    g('checkout', '-q', '-b', 'agent/alpha-deepdive')
    (tmp_path / 'y.txt').write_text('2')
    g('add', '-A')
    g('commit', '-q', '-m', 'unlanded')
    g('branch', 'agent/landed')                      # a branch at main is an ancestor of main: not listed
    g('checkout', '-q', 'main')
    st = T.git_state(tmp_path, ['alpha', 'beta'], {})
    assert 'alpha work on main' in st['alpha']['last_main'] and st['beta']['last_main'] == ''
    assert [b[0] for b in st['alpha']['branches']] == ['agent/alpha-deepdive'] and st['alpha']['branches'][0][3] == 1 and st['beta']['branches'] == []
    st = T.git_state(tmp_path, ['beta'], {'beta': dict(branches=['agent/alpha-deepdive'])})        # the registry can name a branch explicitly
    assert [b[0] for b in st['beta']['branches']] == ['agent/alpha-deepdive']


def test_main_is_read_only_and_writes_only_the_three_files(world, tmp_path):
    out = tmp_path / 'out'
    legacy = tmp_path / 'legacy' / 'parallel-progress-current.csv'

    def snapshot():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in world.rglob('*') if p.is_file()}
    before = snapshot()
    ov = dict(root=world, code=world, registry=dict(packages=dict(beta=dict(basis='b', path='scratch/beta-pkg/beta'))), no_nice=True,
              charters=T.load_charters(world / 'schools'), release=T.frozen_release(world / 'releases'), roster=T.load_roster(world / 'roster.tsv'),
              data=lambda key, name: world / 'hierarchy' / key / name, collectors=world / 'none.json', git={}, queue={}, ids=dict(registry_sha256=None, coadvising_holds=None),
              live_fn=lambda key, n: dict(gate='pass' if n < 9 else 'fail', open=0 if n < 9 else 1))
    assert T.main(['--gates', 'live', '--out-dir', str(out), '--top', '2'], ov) == 0
    assert snapshot() == before                                  # nothing under the data tree changed
    assert sorted(p.name for p in out.iterdir()) == ['STATUS-TABLE.csv', 'STATUS-TABLE.json', 'STATUS-TABLE.md']
    assert not legacy.exists()                                   # the legacy file is opt-in
    rows = list(csv.DictReader(open(out / 'STATUS-TABLE.csv')))
    assert [r['school'] for r in rows] == ['alpha', 'beta'] and rows[1]['gates_left'] == '9,10' and rows[0]['gates_left'] == '9,10'
    assert set(T.COLUMNS) == set(rows[0]) and 'flags' in rows[0] and 'data_as_of_utc' in rows[0] and 'source_files' in rows[0]
    js = json.loads((out / 'STATUS-TABLE.json').read_text())
    assert js['meta']['gates_mode'] == 'live' and js['meta']['frozen_release'] == '2026-11-07' and len(js['rows']) == 2
    assert '| 1 | alpha |' in (out / 'STATUS-TABLE.md').read_text()
    assert T.main(['--gates', 'live', '--out-dir', str(out), '--top', '2', '--write-legacy', '--legacy-path', str(legacy)], ov) == 0
    assert [r['school'] for r in csv.DictReader(open(legacy))] == ['alpha', 'beta'] and snapshot() == before


def test_atlas_cli_registers_status():
    import atlas_cli
    assert atlas_cli.COMMANDS['status'][1] == 'tools/status_table.py' and (atlas_cli.CODE / 'tools' / 'status_table.py').exists()
