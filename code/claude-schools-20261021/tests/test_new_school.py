"""ROADMAP #19: `atlas new-school` makes the charter, folders and an EMPTY store with the catalog schema; it refuses an existing school."""
import sqlite3

import pytest

import new_school as N

CODE = N.CODE


def run(tmp_path, key='testu', extra=()):
    sd = tmp_path / 'schools'
    if not sd.exists():
        sd.mkdir()
        (sd / 'TEMPLATE.toml').write_text((CODE / 'schools' / 'TEMPLATE.toml').read_text())
        (sd / 'other.toml').write_text('key = "other"\norder = 7\n')
    return N.main([key, '--name', 'University of Testland', '--schools-dir', str(sd), '--hierarchy-dir', str(tmp_path / 'h'), '--stores-dir', str(tmp_path / 's'), *extra]), sd


def test_makes_charter_folders_and_an_empty_store(tmp_path):
    rc, sd = run(tmp_path)
    assert rc == 0
    t = (sd / 'testu.toml').read_text()
    assert 'key = "testu"' in t and 'name = "University of Testland"' in t and 'short = "Testland"' in t and 'order = 8' in t and 'status = "onboarding"' in t
    assert f'started = "{__import__("datetime").date.today().isoformat()}"' in t   # the local day, not UTC
    assert all((tmp_path / 'h' / 'testu' / d).is_dir() for d in N.SUBDIRS)
    store = tmp_path / 's' / 'testu'
    assert all((store / d).is_dir() for d in N.STORE_DIRS) and (store / 'summary.json').exists()
    db = sqlite3.connect(store / 'catalog.sqlite')
    tables = {r[0] for r in db.execute("select name from sqlite_master where type in ('table','view')")}
    assert {'works', 'candidates', 'attempts', 'assets', 'access_review', 'receipts', 'nodes', 'edges', 'work_alias', 'work_canonical'} <= tables
    assert db.execute('select count(*) from works').fetchone()[0] == 0 and db.execute('select count(*) from candidates').fetchone()[0] == 0   # never a copy
    assert db.execute("select value from receipts where key='created'").fetchone()
    assert (tmp_path / 'h' / 'testu' / 'reports' / 'new-school.json').exists()


def test_refuses_an_existing_school_and_dry_run_makes_nothing(tmp_path):
    rc, sd = run(tmp_path, extra=('--dry-run',))
    assert rc == 0 and not (sd / 'testu.toml').exists() and not (tmp_path / 's').exists()
    run(tmp_path)
    with pytest.raises(SystemExit) as e:
        run(tmp_path)
    assert 'already exists' in str(e.value)


def test_key_must_be_lowercase_letters_and_digits(tmp_path):
    with pytest.raises(SystemExit):
        run(tmp_path, key='Bad-Key')


def test_charter_template_carries_every_config_the_later_stages_read():
    import tomllib
    t = tomllib.loads((CODE / 'schools' / 'TEMPLATE.toml').read_text())
    # the sections later stages needed and the protocol had to add by hand: ledger repository (stage 8), collector (stage 8), affiliation cases,
    # DBLP strings, thesis, students sources, lab-page hints, rank words, home units (stages 2-9)
    assert {'name', 'pattern'} <= set(t['repository']) and 'channels' in t['collector']
    assert {'regex', 'loose', 'own_units', 'must_match', 'must_not_match'} <= set(t['affiliation'])
    assert 'affiliation_strings' in t['dblp'] and {'rank_words', 'home_units', 'center_units'} <= set(t['census'])
    assert {'adviser_directories', 'rosters', 'directories'} <= set(t['students']) and 'skip_pages' in t['labpages'] and 'kind' in t['thesis']


def test_new_school_prints_the_before_you_start_checklist(tmp_path, capsys):
    run(tmp_path)
    out = capsys.readouterr().out
    assert 'Before you start' in out and 'agent_worktree.sh new testu' in out and '--traps' in out
