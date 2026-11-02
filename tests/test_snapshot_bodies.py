"""ftp_common.oa_bodies reads the OpenAlex snapshot first and leaves the rest to the older stores (ROADMAP #24)."""
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
for d in (CODE / 'fulltext-push', CODE / 'tools'):
    if str(d) not in sys.path:
        sys.path.append(str(d))
import ftp_common as F  # noqa: E402
import oa_snapshot as OS  # noqa: E402


def test_snapshot_bodies_prefer_the_snapshot_and_skip_missing(monkeypatch):
    held = {'https://openalex.org/W1': {'id': 'https://openalex.org/W1', 'locations': [{'pdf_url': 'https://x/y.pdf'}], 'snapshot_date': '2026-10-14'}}
    monkeypatch.setattr(OS, 'conn', lambda *a, **k: None)
    monkeypatch.setattr(OS, 'work', lambda k, root=None: held.get(k))
    got = F.snapshot_bodies(['https://openalex.org/W1', 'https://openalex.org/W2'])
    assert list(got) == ['https://openalex.org/W1'] and got['https://openalex.org/W1']['snapshot_date'] == '2026-10-14'


def test_no_snapshot_means_the_old_path(monkeypatch):
    def none(*a, **k):
        raise FileNotFoundError('no snapshot')
    monkeypatch.setattr(OS, 'conn', none)
    assert F.snapshot_bodies(['https://openalex.org/W1']) == {}


def test_oa_bodies_merges_snapshot_over_the_stores(monkeypatch, tmp_path):
    monkeypatch.setattr(F, 'snapshot_bodies', lambda ids: {i: {'id': i, 'src': 'snapshot'} for i in ids if i.endswith('W1')})
    monkeypatch.setattr(F, 'oa_store', lambda school: tmp_path / 'absent.sqlite')
    got = F.oa_bodies('epfl', ['https://openalex.org/W1', 'https://openalex.org/W2'])
    assert got['https://openalex.org/W1']['src'] == 'snapshot' and 'https://openalex.org/W2' not in got
