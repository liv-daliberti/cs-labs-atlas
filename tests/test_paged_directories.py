"""R3 (Georgia Tech friction 10): a paged directory is one listing; every page of the same half-year is fetched and merged."""
import sqlite3
import zlib

import listing_formats as F
import plan_fetch as PF
import wb

D7 = ('<ul class="pager"><li class="pager-current">1</li><li><a href="/people/faculty?title=&amp;page=1">2</a></li><li><a href="/people/faculty?title=&amp;page=2">3</a></li>'
      '<li><a href="/people/faculty?title=&amp;page=3">last</a></li></ul>')
D9 = '<nav class="pager"><a href="?page=1">2</a><a href="?page=4" title="Go to last page">last</a></nav><a href="/people/other?page=9">elsewhere</a>'


def card(name):
    return (f'<div class="row profile-card__content variant-directory"><div class="card-block"><h4 class="card-block__title"><a href="/people/{name}">{name}</a></h4>'
            f'<h6 class="card-block__subtitle">Professor</h6></div></div>')


def test_page_links_drupal7_escaped_query():
    assert F.page_links(D7, 'http://www.cse.gatech.edu/people/faculty') == {n: f'http://www.cse.gatech.edu/people/faculty?title=&page={n}' for n in (1, 2, 3)}


def test_page_links_drupal9_fills_the_elided_pages_and_ignores_other_paths():
    assert F.page_links(D9, 'https://scs.gatech.edu/people/faculty') == {n: f'https://scs.gatech.edu/people/faculty?page={n}' for n in (1, 2, 3, 4)}
    assert F.page_links('<p>no pager</p>', 'https://x.edu/a') == {}


def _fixture(monkeypatch, archived):
    """A captures db holding page 0; wb.cdx / wb.fetch_capture serve `archived` = {page n: timestamp} (a page missing from it is not archived)."""
    con = sqlite3.connect(':memory:')
    con.execute('create table captures(capture_url text primary key, page_url text, department text, wayback_timestamp text, final_url text, http_status integer, fetched_at text, '
                'sha256 text, nbytes integer, content_type text, raw_zlib blob, blocks_json text, text text, note text)')
    page0 = '<html><body>' + D9 + card('a1') + card('a2') + '</body></html>'
    cap0 = 'https://web.archive.org/web/20240414000000id_/https://scs.gatech.edu/people/faculty'
    con.execute('insert into captures values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (cap0, 'scs.gatech.edu/people/faculty', 'CS', '20240414000000', cap0, 200, '', 'x', 1, 'text/html', zlib.compress(page0.encode()), None, None, None))

    def cdx(params, con_, refresh=False):
        n = int(params['url'].rsplit('page=', 1)[1])
        return [dict(timestamp=archived[n], original='https://' + params['url'], statuscode='200', digest='d')] if n in archived else []

    def fetch(ts, original, page_url, dept, con_, refresh=False):
        cap = f'https://web.archive.org/web/{ts}id_/{original}'
        html = f'<html><body>{card("p" + original[-1])}</body></html>'
        con_.execute('insert or replace into captures values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (cap, page_url, dept, ts, cap, 200, '', 'h', 1, 'text/html', zlib.compress(html.encode()), None, None, None))
        return cap
    monkeypatch.setattr(wb, 'cdx', cdx)
    monkeypatch.setattr(wb, 'fetch_capture', fetch)
    return con, cap0, page0


def test_fetch_pages_gets_every_page_of_the_half_year(monkeypatch):
    con, cap0, page0 = _fixture(monkeypatch, {1: '20240420000000', 2: '20240301000000', 3: '20240601000000', 4: '20240415000000'})
    got, missing = PF.fetch_pages(con, {'dept': 'CS'}, cap0, page0, '20240101', '20240630', 'CS')
    assert missing == [] and sorted(got) == [1, 2, 3, 4]
    assert got[4][1].startswith('https://web.archive.org/web/20240415000000id_/https://scs.gatech.edu/people/faculty?page=4')


def test_a_page_not_archived_in_the_half_year_is_reported_missing(monkeypatch):
    con, cap0, page0 = _fixture(monkeypatch, {1: '20240420000000', 2: '20240301000000', 4: '20240415000000'})
    got, missing = PF.fetch_pages(con, {'dept': 'CS'}, cap0, page0, '20240101', '20240630', 'CS')
    assert missing == [3] and sorted(got) == [1, 2, 4]
