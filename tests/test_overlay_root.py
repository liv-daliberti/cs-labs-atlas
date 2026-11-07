"""ROADMAP #44 workaround: the overlay code root resolves a school's reviewed files to the worktree's branch copies and leaves main alone."""
import subprocess

import pytest

import overlay_root as O


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
