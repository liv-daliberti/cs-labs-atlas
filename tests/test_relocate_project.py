"""tools/relocate_project.py: the cutover plan, its refusals, the reference rewrite and the compat links, on a fake tree
in tmp_path (nothing outside it is touched)."""
import fcntl
import json
import os
import subprocess

import pytest

import relocate_project as R


def tree(tmp_path):
    """A miniature of the real situation: the old world-atlas root becomes the project root, its data/fulltext stores
    move out to stores/, a sweep pool keeps most of its content, cs-atlas is dissolved."""
    root = tmp_path / 'hs'
    for d in ['app', 'scripts', 'data/raw', 'data/fulltext/princeton/objects', 'data/fulltext/cmu', 'env/atlas']:
        (root / d).mkdir(parents=True)
    (root / 'README.md').write_text('world atlas\n')
    (root / 'data/fulltext/princeton/catalog.sqlite').write_text('x')
    sw = tmp_path / 'mg/.research-sweeps'
    for d in ['claude-cmu/tools', 'claude-homog/corpus']:
        (sw / d).mkdir(parents=True)
    (tmp_path / 'mg/other-project').mkdir()
    ca = tmp_path / 'ca'
    for d in ['work/tools', 'releases', 'studies']:
        (ca / d).mkdir(parents=True)
    os.symlink(str(ca / 'work'), str(sw / 'claude-schools'))
    os.symlink(str(ca / 'work/ai'), str(ca / 'studies/ai'))
    (ca / 'README.md').write_text('old map\n')
    legacy = {'CODE': str(ca / 'work'), 'RELEASES': str(ca / 'releases'), 'STORES': str(root / 'data/fulltext'),
              'SWEEPS': str(sw), 'HOMOGENIZATION_STUDY': str(sw / 'claude-homog'), 'WORLD_ATLAS': str(root),
              'STUDIES': str(ca / 'studies')}
    project = {'CODE': root / 'code', 'RELEASES': root / 'releases', 'STORES': root / 'stores',
               'SWEEPS': root / 'archive/sweeps', 'HOMOGENIZATION_STUDY': root / 'studies/homogenization',
               'WORLD_ATLAS': root / 'world-atlas', 'STUDIES': root / 'studies', 'ROOT': root}
    rows = [f'{root}/{i}\tworld-atlas/{i}\trename\tworld atlas' for i in ('app', 'scripts', 'data', 'README.md')]
    rows += [f'{root}/env\tenv\tkeep\tfinal', f'{root}/data/fulltext\tstores\tsplit\tone by one',
             f'{root}/data/fulltext/princeton\tstores/princeton\trename\tstore', f'{root}/data/fulltext/cmu\tstores/cmu\trename\t',
             f'{tmp_path}/mg\tarchive/site-history\tpool\tstays', f'{sw}/claude-schools\tcode\tstale-link\tlink',
             f'{ca}\t.\tsplit\tdissolved', f'{ca}/studies\tstudies\tsplit\treal dir', f'{ca}/studies/ai\tcode/ai\tstale-link\t',
             f'{ca}/stores\tstores\talias\t']
    ex = tmp_path / 'extra.tsv'
    ex.write_text('# comment\n' + '\n'.join(rows) + '\n')
    return root, legacy, project, R.load_extras(ex, root)


def plan_of(tmp_path):
    root, legacy, project, extras = tree(tmp_path)
    return root, R.build_plan(legacy, project, extras, root)


def renames(plan):
    return [(e['old'], e['new']) for e in plan['entries'] if e['kind'] == 'rename']


def test_order_children_out_first_and_root_split(tmp_path):
    root, plan = plan_of(tmp_path)
    assert plan['conflicts'] == []
    olds = [o for o, _ in renames(plan)]
    # the stores leave data/fulltext before data/ goes to world-atlas; the study leaves the sweeps before they move
    assert olds.index(f'{root}/data/fulltext/princeton') < olds.index(f'{root}/data')
    assert olds.index(str(tmp_path / 'mg/.research-sweeps/claude-homog')) < olds.index(str(tmp_path / 'mg/.research-sweeps'))
    kinds = {e['old']: e['kind'] for e in plan['entries'] if e['old']}
    assert kinds[str(root)] == 'split'                       # the old root moves into its own subtree: split
    assert kinds[f'{root}/data/fulltext'] == 'split' and kinds[f'{root}/env'] == 'keep'
    mk = [e['new'] for e in plan['entries'] if e['kind'] == 'mkdir']
    assert str(root / 'world-atlas') in mk and str(root / 'stores') in mk and str(root / 'archive') in mk
    assert all(not R.inside(n, o) for o, n in renames(plan))  # nothing into its own subtree


def test_stale_link_travels_and_leftovers(tmp_path):
    root, plan = plan_of(tmp_path)
    link = [e for e in plan['entries'] if e['kind'] == 'stale-link' and e['old'].endswith('claude-schools')][0]
    assert link['travels_to'] == str(root / 'archive/sweeps/claude-schools')
    left = plan['leftovers']
    assert left[str(tmp_path / 'ca')] == ['README.md', 'stores'] or 'README.md' in left[str(tmp_path / 'ca')]
    assert left[f'{root}/data/fulltext'] == []


def test_with_parent_when_the_layout_is_kept(tmp_path):
    root, legacy, project, extras = tree(tmp_path)
    legacy['TOOLS'] = legacy['CODE'] + '/tools'
    project['TOOLS'] = project['CODE'] / 'tools'
    plan = R.build_plan(legacy, project, extras, root)
    e = [e for e in plan['entries'] if e['old'] == legacy['TOOLS']][0]
    assert e['kind'] == 'with-parent'
    assert legacy['TOOLS'] not in [o for o, _ in renames(plan)]


def test_conflicts_dest_exists_missing_and_cross_device(tmp_path, monkeypatch):
    root, legacy, project, extras = tree(tmp_path)
    (root / 'releases').mkdir()
    legacy['FIGURES'] = str(tmp_path / 'ca/figures-missing')
    project['FIGURES'] = root / 'figures'
    plan = R.build_plan(legacy, project, extras, root)
    text = '\n'.join(plan['conflicts'])
    assert 'destination exists' in text and 'source missing' in text
    monkeypatch.setattr(R, '_dev', lambda p: 1 if str(p).startswith(str(tmp_path / 'ca')) else 2)
    plan = R.build_plan(legacy, project, extras, root)
    assert any('cross-device' in c for c in plan['conflicts'])


def test_same_destination_twice(tmp_path):
    root, legacy, project, extras = tree(tmp_path)
    extras.append(R.entry(str(tmp_path / 'mg/other-project'), str(root / 'stores/princeton'), 'rename', '', 'x'))
    plan = R.build_plan(legacy, project, extras, root)
    assert any('same destination' in c for c in plan['conflicts'])


def test_lock_held_and_free(tmp_path):
    store = tmp_path / 'stores/princeton'
    store.mkdir(parents=True)
    lock = store / '.loop.lock'
    lock.write_text('')
    assert R.store_locks([str(tmp_path / 'stores')]) == {str(lock): False}
    holder = subprocess.Popen(['python3', '-c', 'import fcntl,sys,time; f=open(sys.argv[1],"a"); '
                               'fcntl.flock(f, fcntl.LOCK_EX); print("x", flush=True); time.sleep(30)', str(lock)],
                              stdout=subprocess.PIPE)
    try:
        holder.stdout.readline()
        assert R.lock_held(str(lock)) is True
        assert R.store_locks([str(tmp_path / 'stores')]) == {str(lock): True}
    finally:
        holder.kill()
        holder.wait()
    assert R.lock_held(str(lock)) is False
    with open(lock) as f:  # the probe left no lock behind
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_busy_processes_scans_cwd_and_fds_of_own_uid(tmp_path):
    proc = tmp_path / 'proc'
    src = tmp_path / 'src'
    (src / 'a').mkdir(parents=True)
    for pid, cwd, fd in (('100', src / 'a', None), ('101', tmp_path, src / 'a/f.txt'), ('102', tmp_path, tmp_path)):
        (proc / pid / 'fd').mkdir(parents=True)
        os.symlink(str(cwd), str(proc / pid / 'cwd'))
        if fd:
            os.symlink(str(fd), str(proc / pid / 'fd' / '3'))
    hits = R.busy_processes([str(src)], proc=str(proc), uid=os.getuid(), self_pid=1)
    assert sorted((p, w) for p, w, _ in hits) == [(100, 'cwd'), (101, 'fd')]
    assert R.busy_processes([str(src)], proc=str(proc), uid=os.getuid() + 1, self_pid=1) == []


def test_reference_rewrite_longest_prefix_keep_and_unmapped(tmp_path):
    root, plan = plan_of(tmp_path)
    rmap = R.rewrite_map(plan['entries'], plan['root'])
    ca, sw = tmp_path / 'ca', tmp_path / 'mg/.research-sweeps'
    text = (f'a {sw}/claude-homog/corpus/x.sqlite, b {sw}/claude-cmu/raw. c {ca}/stores/princeton/objects '
            f'd {root}/env/atlas/bin/python e {ca}/work-infra/x')
    # the fake tree lives under tmp_path, not /n/fs/resemble: rewrite with a REF that matches it
    pat = R.REF
    R.REF = __import__('re').compile(__import__('re').escape(str(tmp_path)) + r'(?:/[A-Za-z0-9._+@=,\-]+)+')
    try:
        new, done, un = R.rewrite_text(text, rmap)
    finally:
        R.REF = pat
    assert f'{root}/studies/homogenization/corpus/x.sqlite,' in new        # longest prefix wins over the sweeps
    assert f'{root}/archive/sweeps/claude-cmu/raw.' in new                  # trailing punctuation kept
    assert f'{root}/stores/princeton/objects' in new                        # alias through the old links
    assert f'{root}/env/atlas/bin/python' in new and len(done) == 3          # keep: unchanged, not unmapped
    assert un == [f'{ca}/work-infra/x']                                     # the boundary is a path component


def test_scan_refs_and_grouping(tmp_path):
    f = tmp_path / 'a.sh'
    f.write_text('x=/n/fs/resemble/old/thing/y\nz=/n/fs/resemble/unknown/dir/q\n')
    (tmp_path / 'bin').write_bytes(b'\0/n/fs/resemble/old/thing')
    per_file, un = R.scan_refs([('a.sh', f), ('bin', tmp_path / 'bin')], [('/n/fs/resemble/old/thing', '/new/thing')])
    assert per_file == {'a.sh': [('/n/fs/resemble/old/thing/y', '/new/thing/y')]}
    assert R.group_unmapped(un) == {'/n/fs/resemble/unknown/dir': (1, ['a.sh'])}
    assert '/n/fs/resemble/old/thing' in f.read_text()                    # a dry run writes nothing
    R.scan_refs([('a.sh', f)], [('/n/fs/resemble/old/thing', '/new/thing')], apply=True)
    assert 'x=/new/thing/y' in f.read_text()


def test_apply_moves_records_and_compat_links_roundtrip(tmp_path):
    root, plan = plan_of(tmp_path)
    rec = tmp_path / 'rec.jsonl'
    R.apply_plan(plan, str(rec), compat=True)
    assert (root / 'stores/princeton/catalog.sqlite').read_text() == 'x'
    assert (root / 'world-atlas/data/raw').is_dir() and (root / 'code/tools').is_dir()
    assert (root / 'studies/homogenization/corpus').is_dir()
    ops = [json.loads(x) for x in rec.read_text().splitlines()]
    assert sum(o['op'] == 'rename' for o in ops) == len(renames(plan))
    # the compat link for a store lands inside the moved data/ (through the data/ link) and resolves to stores/
    assert (root / 'data/fulltext/princeton/catalog.sqlite').read_text() == 'x'
    assert os.path.islink(str(tmp_path / 'ca/work'))
    n = R.remove_compat([str(rec)])
    assert n == sum(o['op'] == 'compat-link' for o in ops) and n > 0
    assert not os.path.lexists(str(tmp_path / 'ca/work')) and not os.path.lexists(str(root / 'data'))
    assert (root / 'code/tools').is_dir()


def test_apply_refuses_cross_device(tmp_path, monkeypatch):
    root, plan = plan_of(tmp_path)
    monkeypatch.setattr(R, '_dev', lambda p: 1 if 'world-atlas' in str(p) else 2)
    with pytest.raises(SystemExit):
        R.apply_plan(plan, str(tmp_path / 'rec.jsonl'))
    assert not (root / 'world-atlas').exists() and not (tmp_path / 'rec.jsonl').exists()  # refused before any change
