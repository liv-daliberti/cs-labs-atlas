import listing_formats as F


def test_bme_cards_strip_credentials_and_require_pager_pages():
    html = '''
    <div class="zn-faculty-profile "><div class="zn-name">
      <a href="/people/faculty/soumyadipta-acharya/">Soumyadipta Acharya, MD, MSE, PhD</a>
      </div><div class="zn-position">Assistant Professor</div></div>
    <div class="zn-faculty-profile "><div class="zn-name">
      <a href="/people/faculty/alexis-battle/">Alexis Battle, PhD</a>
      </div><div class="zn-position">Associate Professor</div></div>
    <div class="pagination"><a href="?pg=2">2</a><a href="?pg=3">3</a></div>
    '''
    fmt, rows = F.parse(html)
    assert fmt == "jhu_bme_faculty"
    assert [(r["name_listed"], r["titles"]) for r in rows] == [
        ("Soumyadipta Acharya", ["Assistant Professor"]),
        ("Alexis Battle", ["Associate Professor"]),
    ]
    base = "https://www.bme.jhu.edu/people/faculty/"
    assert F.is_paged(html)
    assert F.page_links(html, base) == {1: base + "?pg=2", 2: base + "?pg=3"}


def test_bme_pager_gap_does_not_hide_unlinked_intermediate_page():
    html = '<div class="pagination"><a href="?pg=2">2</a><a href="?pg=4">4</a></div>'
    base = "https://www.bme.jhu.edu/people/faculty/"
    assert F.page_links(html, base) == {
        1: base + "?pg=2",
        2: base + "?pg=3",
        3: base + "?pg=4",
    }
