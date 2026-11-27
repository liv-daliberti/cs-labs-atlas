"""ROADMAP #44 workaround: the overlay code root resolves a school's reviewed files to the worktree's branch copies and leaves main alone."""
import subprocess
import sqlite3

import pytest

import overlay_root as O


@pytest.fixture(autouse=True)
def _split_placement(monkeypatch):
    """These fixtures are split-placement trees (hierarchy/<school>/...); the school placement is tested in test_overlay_root_school.py."""
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'split')


def tree(tmp_path):
    main, wt = tmp_path / 'main', tmp_path / 'wt'
    for root in (main, wt):
        (root / 'tools').mkdir(parents=True)
        (root / 'tools' / 'x.py').write_text(root.name)
    (main / 'hierarchy' / 'newu' / 'reviewed').mkdir(parents=True)
    (main / 'hierarchy' / 'newu' / 'derived').mkdir()
    (main / 'hierarchy' / 'newu' / 'raw').mkdir()
    (main / 'hierarchy' / 'newu' / 'tmp').mkdir()
    (main / 'hierarchy' / 'mit').mkdir()
    (main / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').write_text('main-a')
    (main / 'hierarchy' / 'newu' / 'reviewed' / 'b.json').write_text('main-b')
    (main / 'census').mkdir()
    (main / 'listings').mkdir()
    (main / 'hierarchy' / 'newu' / 'work').mkdir()
    (main / 'hierarchy' / 'newu' / 'work' / 'dblp-recover.sqlite').write_text('main-work')
    (main / 'hierarchy' / 'reviewed').mkdir()
    (main / 'hierarchy' / 'reviewed' / 'census-overrides.json').write_text('main-co')
    (main / 'hierarchy' / 'reviewed' / 'home-departments.json').write_text('main-hd')
    subprocess.run(['git', 'init', '-q', str(wt)], check=True)
    (wt / 'hierarchy' / 'newu' / 'reviewed').mkdir(parents=True)
    (wt / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').write_text('branch-a')
    (wt / 'hierarchy' / 'reviewed').mkdir(parents=True)
    (wt / 'hierarchy' / 'reviewed' / 'census-overrides.json').write_text('branch-co')
    subprocess.run(['git', '-C', str(wt), 'add', 'hierarchy/newu/reviewed/a.json', 'hierarchy/reviewed/census-overrides.json'], check=True)
    return main, wt


def test_overlay_reads_branch_reviewed_files_and_main_for_the_rest(tmp_path):
    main, wt = tree(tmp_path)
    out, n = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main)
    assert n == 2   # a.json and the shared census-overrides.json
    rv = out / 'hierarchy' / 'newu' / 'reviewed'
    assert (rv / 'a.json').read_text() == 'branch-a' and (rv / 'b.json').read_text() == 'main-b'   # branch wins, main fills in
    assert (out / 'tools' / 'x.py').read_text() == 'wt'                                            # code is the worktree's
    assert (out / 'hierarchy' / 'newu' / 'derived').resolve() == (main / 'hierarchy' / 'newu' / 'derived').resolve()
    assert (out / 'hierarchy' / 'mit').resolve() == (main / 'hierarchy' / 'mit').resolve() and (out / 'census').is_symlink()


def test_a_write_through_the_overlay_lands_in_the_worktree_not_main(tmp_path):
    main, wt = tree(tmp_path)
    out, _ = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main)
    (out / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').write_text('edited')
    assert (wt / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').read_text() == 'edited'
    assert (main / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').read_text() == 'main-a'


def test_refuses_an_output_inside_main_outside_the_school_tmp(tmp_path):
    main, wt = tree(tmp_path)
    with pytest.raises(SystemExit):
        O.build('newu', main / 'census' / 'ov', worktree=wt, main=main)


def test_shared_reviewed_files_are_overlaid_per_file(tmp_path):
    main, wt = tree(tmp_path)
    out, _ = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main)
    sh = out / 'hierarchy' / 'reviewed'
    assert not sh.is_symlink() and (sh / 'census-overrides.json').read_text() == 'branch-co' and (sh / 'home-departments.json').read_text() == 'main-hd'
    (sh / 'census-overrides.json').write_text('edited')
    assert (main / 'hierarchy' / 'reviewed' / 'census-overrides.json').read_text() == 'main-co'


def test_work_is_overlay_local_and_seeded_on_first_write(tmp_path, monkeypatch):
    import atlas_paths as P
    main, wt = tree(tmp_path)
    out, _ = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main)
    work = out / 'hierarchy' / 'newu' / 'work'
    assert work.is_dir() and not work.is_symlink() and list(work.iterdir()) == []
    monkeypatch.setattr(P, 'CODE', out); monkeypatch.setattr(P, 'HIERARCHY', out / 'hierarchy')
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'split')
    p = P.data_w('dblp-recover.sqlite', 'newu')
    assert p == work / 'dblp-recover.sqlite' and p.read_text() == 'main-work'          # seeded from main, local
    p.write_text('overlay-edit')
    assert (main / 'hierarchy' / 'newu' / 'work' / 'dblp-recover.sqlite').read_text() == 'main-work'   # main untouched
    assert P.data_w('dblp-recover.sqlite', 'newu').read_text() == 'overlay-edit'        # a second call does not reseed


def test_without_an_overlay_work_files_resolve_as_before(tmp_path, monkeypatch):
    import atlas_paths as P
    monkeypatch.setattr(P, 'CODE', tmp_path); monkeypatch.setattr(P, 'HIERARCHY', tmp_path / 'hierarchy')
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'split')
    assert P.overlay_main() is None
    p = P.data_w('dblp-recover.sqlite', 'newu')
    assert p == tmp_path / 'hierarchy' / 'newu' / 'work' / 'dblp-recover.sqlite' and not p.exists() and p.parent.is_dir()


def test_read_only_build_recovery_inputs_are_copied_without_sharing_mutable_work(tmp_path):
    main, wt = tree(tmp_path)
    original = main / 'hierarchy' / 'newu' / 'work'
    for name in O.WORK_READ_INPUTS:
        (original / name).write_bytes(b'recovered source bytes')
    out, _ = O.build('newu', tmp_path / 'overlay', worktree=wt, main=main)
    work = out / 'hierarchy' / 'newu' / 'work'
    assert not (work / 'dblp-recover.sqlite').exists()
    for name in O.WORK_READ_INPUTS:
        assert (work / name).read_bytes() == (original / name).read_bytes()
        assert not (work / name).is_symlink()
        (work / name).write_bytes(b'isolated changed input')
        assert (original / name).read_bytes() == b'recovered source bytes'


def test_private_copies_survive_a_rebuild_and_main_stays_unchanged(tmp_path):
    main, wt = tree(tmp_path)
    (main / 'listings' / 'newu' / 'derived').mkdir(parents=True)
    (main / 'hierarchy' / 'newu' / 'derived' / 'pis.json').write_text('main-pis')
    (main / 'hierarchy' / 'newu' / 'raw' / 'school-captures.sqlite').write_text('main-cap')
    out = main / 'hierarchy' / 'newu' / 'tmp' / 'ov'
    O.build('newu', out, worktree=wt, main=main, private=True)
    for rel in ('hierarchy/newu/derived', 'hierarchy/newu/raw', 'listings/newu'):
        assert (out / rel).is_dir() and not (out / rel).is_symlink()
    (out / 'hierarchy' / 'newu' / 'derived' / 'pis.json').write_text('trial')
    (out / 'listings' / 'newu' / 'raw' / 'captures.sqlite').write_text('27 captures')
    (out / 'hierarchy' / 'newu' / 'raw' / 'school-captures.sqlite').write_text('grown')
    O.build('newu', out, worktree=wt, main=main)   # a plain rebuild must not delete or relink them
    assert (out / 'listings' / 'newu' / 'raw' / 'captures.sqlite').read_text() == '27 captures'
    assert (out / 'hierarchy' / 'newu' / 'derived' / 'pis.json').read_text() == 'trial'
    assert (out / 'hierarchy' / 'newu' / 'raw' / 'school-captures.sqlite').read_text() == 'grown'
    assert (main / 'hierarchy' / 'newu' / 'derived' / 'pis.json').read_text() == 'main-pis'
    assert O.verify(out) == []


def test_private_listing_sources_include_committed_wal_and_remain_isolated(tmp_path, monkeypatch):
    main, wt = tree(tmp_path)
    raw = main / 'listings' / 'newu' / 'raw'
    raw.mkdir(parents=True)
    source = raw / 'captures.sqlite'
    conn = sqlite3.connect(source)
    try:
        conn.execute('pragma journal_mode=wal')
        conn.execute('pragma wal_autocheckpoint=0')
        conn.execute('create table captures (body text)')
        conn.execute('insert into captures values (?)', ('original archived roster',))
        conn.commit()
        assert source.with_name('captures.sqlite-wal').stat().st_size > 0
        before = source.read_bytes()
        out = tmp_path / 'overlay'
        O.build('newu', out, worktree=wt, main=main, private=True)
        copied = out / 'listings' / 'newu' / 'raw' / 'captures.sqlite'
        assert not copied.is_symlink()
        assert not list(copied.parent.glob('*.sqlite-wal'))
        with sqlite3.connect(copied) as private:
            assert private.execute('select body from captures').fetchall() == [('original archived roster',)]
            private.execute('insert into captures values (?)', ('private new capture',))
        assert conn.execute('select count(*) from captures').fetchone()[0] == 1
        assert source.read_bytes() == before

        def no_recopy(*args, **kwargs):
            pytest.fail('Rebuilding a private overlay recopied its source archive store')

        monkeypatch.setattr(O, 'copy_listing_source', no_recopy)
        O.build('newu', out, worktree=wt, main=main, private=True)
        with sqlite3.connect(copied) as private:
            assert private.execute('select count(*) from captures').fetchone()[0] == 2
    finally:
        conn.close()


def test_verify_reports_a_change_to_main_derived_files(tmp_path):
    main, wt = tree(tmp_path)
    (main / 'hierarchy' / 'newu' / 'derived' / 'pis.json').write_text('before')
    out = main / 'hierarchy' / 'newu' / 'tmp' / 'ov'
    O.build('newu', out, worktree=wt, main=main, private=True)
    assert O.main(['newu', '--out', str(out), '--verify']) == 0
    (main / 'hierarchy' / 'newu' / 'derived' / 'pis.json').write_text('overwritten')
    assert O.verify(out) == ['hierarchy/newu/derived/pis.json']
    assert O.main(['newu', '--out', str(out), '--verify']) == 1
