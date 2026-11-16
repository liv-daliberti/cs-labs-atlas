"""lab_first_loop.take_full_first_flag: an opt-in per-school one-shot, consumed on use."""
import ftp_common as F
import lab_first_loop as L


def test_flag_is_one_shot_and_per_school(tmp_path, monkeypatch):
    monkeypatch.setattr(F.P, 'FT_RAW', tmp_path)
    assert L.take_full_first_flag('cmu') is False
    (tmp_path / 'cmu-full-first.flag').write_text('')
    assert L.take_full_first_flag('mit') is False
    assert (tmp_path / 'cmu-full-first.flag').exists()
    assert L.take_full_first_flag('cmu') is True
    assert not (tmp_path / 'cmu-full-first.flag').exists()
    assert L.take_full_first_flag('cmu') is False
