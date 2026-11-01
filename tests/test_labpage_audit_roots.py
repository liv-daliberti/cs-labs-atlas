"""The labpages channel reads page roots from labpage-evidence.json and from labpage-audit.jsonl.gz (2026-11-01)."""
import gzip
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
if str(CODE / 'fulltext-push') not in sys.path:
    sys.path.append(str(CODE / 'fulltext-push'))
import ftp_common as F  # noqa: E402
import labpage_channel as L  # noqa: E402


def setup(tmp_path, monkeypatch, school='michigan'):
    h = tmp_path / 'hierarchy' / school
    h.mkdir(parents=True)
    monkeypatch.setattr(F, 'SCHOOLS', tmp_path)
    (h / 'labpage-evidence.json').write_text(json.dumps([dict(pi='A One', lab_site='https://a.example.edu/lab/', people_page=None, pubs_pages=[])]))
    rows = [dict(pi='B Two', lab_page=dict(status='found', urls=dict(lab_site='https://b.example.edu/~two/', people_page='https://b.example.edu/~two/people', pubs_page=None))),
            dict(pi='A One', lab_page=dict(status='found', urls=dict(pubs_page='https://a.example.edu/lab/papers'))),
            dict(pi='C Three', lab_page=dict(status='found', urls=dict(lab_site='https://deepblue.lib.umich.edu/x', people_page=None))),
            dict(pi='D Four', lab_page=dict(status='none_found', urls=dict(lab_site=None)))]
    with gzip.open(h / 'labpage-audit.jsonl.gz', 'wt') as f:
        f.write('\n'.join(json.dumps(r) for r in rows) + '\n')
    return h


def test_roots_come_from_both_sources(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    urls, roots = L.pi_pages('michigan')
    assert set(urls) == {'A One', 'B Two'}  # Deep Blue and the page-less PI contribute nothing
    assert roots['B Two'] and roots['A One']
    assert any('papers' in u for u in urls['A One'])  # the audit's pubs page joins the evidence file's lab site
    assert any(u.rstrip('/').endswith('/lab') for u in urls['A One'])


def test_a_school_without_an_audit_file_is_unchanged(tmp_path, monkeypatch):
    h = setup(tmp_path, monkeypatch)
    (h / 'labpage-audit.jsonl.gz').unlink()
    assert L.audit_pages('michigan') == []
    assert set(L.pi_pages('michigan')[0]) == {'A One'}
