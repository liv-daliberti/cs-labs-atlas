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


class _Site:
    def __init__(self, pages):
        self.pages, self.asked = pages, []

    def get(self, url):
        self.asked.append(url)
        return self.pages.get(url)


def test_old_workshop_menus_use_relative_links(monkeypatch):
    menu = 'https://openaccess.thecvf.com/CVPR2019_workshops/menu.py'
    ws = 'https://openaccess.thecvf.com/CVPR2019_workshops/CVPR2019_CV-COPS.py'
    site = _Site({menu: '<a href="http://openaccess.thecvf.com">home</a><a href="CVPR2019_CV-COPS.py">CV-COPS</a>',
                  ws: '<dt class="ptitle"><br><a href="../content_CVPRW_2019/html/CV-COPS/Wang_X_CVPRW_2019_paper.html">Privacy-Preserving '
                      'Action Recognition Using Coded Aperture Videos</a></dt><dd>[<a href="../content_CVPRW_2019/papers/CV-COPS/'
                      'Wang_X_CVPRW_2019_paper.pdf">pdf</a>]</dd>'})
    monkeypatch.setattr(PE, 'CVF_MAIN', [])
    monkeypatch.setattr(PE, 'CVF_MENUS', ['CVPR2019_workshops/menu.py'])
    rows, counts = [], {}
    PE.cvf(site, rows, counts)
    assert counts == {'CVPR2019_workshops/menu.py': 1}
    assert rows[0][2] == 'https://openaccess.thecvf.com/content_CVPRW_2019/papers/CV-COPS/Wang_X_CVPRW_2019_paper.pdf'
