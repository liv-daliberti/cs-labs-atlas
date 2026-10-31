"""tools/sweep_school.py (ROADMAP item 5): the one-school sweep runners as one charter-driven tool. Offline: no command is
run, no key is read from the real config."""
import pytest

import sweep_school as SW


def test_env_file_reads_keys_without_printing(tmp_path, capsys):
    f = tmp_path / 'openalex.env'
    f.write_text('# comment\nexport OPENALEX_API_KEY="abc123"\nOPENALEX_MAILTO=x\n')
    assert SW.env_file(f) == {'OPENALEX_API_KEY': 'abc123', 'OPENALEX_MAILTO': 'x'}
    assert SW.env_file(tmp_path / 'missing.env') == {}
    assert 'abc123' not in capsys.readouterr().out


def test_complete_reads_the_year_line(tmp_path):
    log = tmp_path / 'sweep.log'
    log.write_text('{"school": "x", "year": 2025, "works": 10, "count": 10}\n')
    assert not SW.complete(log, 2026) and SW.complete(log, 2025) and not SW.complete(tmp_path / 'none.log', 2026)


def test_print_shows_both_steps_for_a_charter_school(capsys):
    assert SW.main(['michigan', '--print']) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].endswith('oa_sweep.py michigan') and ' -I ' in out[0] and out[1].endswith('sweep_check.py michigan')


def test_unknown_school_is_refused():
    with pytest.raises(SystemExit):
        SW.main(['atlantis', '--print'])
