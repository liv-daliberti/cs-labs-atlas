"""The open proceedings index reads the supplement raw/proceedings_extra.json.gz beside the frozen sweep index (2026-11-25), and the
supplement's listing parser takes CVF ptitle entries with their PDF links."""
import gzip
import json

import ftp_common as F
import proceedings_extra as PE


def test_supplement_rows_join_the_frozen_index(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'PROCEEDINGS_EXTRA', tmp_path / 'absent.json.gz')
    base, _ = F.proceedings_index()
    extra = tmp_path / 'proceedings_extra.json.gz'
    row = ['A Workshop Paper Title That Is Long Enough', 2024, 'https://openaccess.thecvf.com/content/x_paper.pdf',
           'https://openaccess.thecvf.com/content/x_paper.html', 'CVPR2024 workshops']
    extra.write_bytes(gzip.compress(json.dumps([row]).encode()))
    monkeypatch.setattr(F, 'PROCEEDINGS_EXTRA', extra)
    rows, _ = F.proceedings_index()
    assert len(rows) == len(base) + 1 and rows[-1] == row


def test_missing_supplement_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'PROCEEDINGS_EXTRA', tmp_path / 'absent.json.gz')
    rows, built = F.proceedings_index()
    assert rows and built is not None


class _Fx:
    def __init__(self, page):
        self.page = page

    def get(self, url):
        return self.page


def test_cvf_listing_takes_title_and_pdf():
    page = ('<dl><dt class="ptitle"><br><a href="/content/ACCV2024/html/Liu_Depth_Attention_ACCV_2024_paper.html">Depth Attention for '
            'Robust RGB Tracking</a></dt><dd>[<a href="/content/ACCV2024/papers/Liu_Depth_Attention_ACCV_2024_paper.pdf">pdf</a>]</dd>'
            '<dt class="ptitle"><br><a href="/x.html">Short</a></dt><dd>[<a href="/x.pdf">pdf</a>]</dd></dl>')
    rows = []
    assert PE.cvf_listing(_Fx(page), 'ACCV2024', 'ACCV2024', 2024, rows) == 1
    assert rows[0] == ['Depth Attention for Robust RGB Tracking', 2024,
                       'https://openaccess.thecvf.com/content/ACCV2024/papers/Liu_Depth_Attention_ACCV_2024_paper.pdf',
                       'https://openaccess.thecvf.com/content/ACCV2024/html/Liu_Depth_Attention_ACCV_2024_paper.html', 'ACCV2024']
