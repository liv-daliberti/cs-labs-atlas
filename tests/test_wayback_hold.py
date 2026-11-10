"""WAYBACK_HOLD=1: the download loops' collector does not request web.archive.org (2026-11-10 429 cooldown, drawn by loop collectors)."""
from types import SimpleNamespace

import collector_quality as D


def test_held_hosts_only_when_env_is_one():
    on = {'WAYBACK_HOLD': '1'}
    assert D.wayback_held('https://web.archive.org/web/2020/http://x.org/a.pdf', on)
    assert D.wayback_held('http://archive.org/download/x/y.pdf', on)
    assert not D.wayback_held('https://example.org/a.pdf', on)
    assert not D.wayback_held('https://web.archive.org/web/2020/http://x.org/a.pdf', {})
    assert not D.wayback_held('https://web.archive.org/x', {'WAYBACK_HOLD': '0'})


def test_install_raises_source_paused_without_asking(monkeypatch):
    calls = []

    class Client:
        def get(self, url, *a, **k):
            calls.append(url)
            return b'', url, 'application/pdf'
    wrapper = SimpleNamespace(c=SimpleNamespace(PublicClient=Client, base=SimpleNamespace(validate_pdf=lambda d, p: 1)))
    D.install(wrapper, SimpleNamespace(xml_quality=lambda d: dict(ok=True), file_quality=lambda p, k: dict(ok=True)))
    monkeypatch.setenv('WAYBACK_HOLD', '1')
    try:
        Client().get('https://web.archive.org/web/1/http://a/b.pdf')
        raise AssertionError('asked')
    except RuntimeError as e:
        assert str(e).startswith('source_paused:')
    assert calls == []
    assert Client().get('https://example.org/a.pdf')[1] == 'https://example.org/a.pdf'
    monkeypatch.setenv('WAYBACK_HOLD', '0')
    assert Client().get('https://web.archive.org/web/1/http://a/b.pdf') and len(calls) == 2


def test_loop_scripts_default_the_hold_on():
    from pathlib import Path
    for f in ('school-collector.slurm', 'michigan-collector.slurm', 'downloads.slurm'):
        assert 'WAYBACK_HOLD="${WAYBACK_HOLD:-1}"' in (Path(__file__).resolve().parents[1] / 'fulltext-push' / f).read_text()
