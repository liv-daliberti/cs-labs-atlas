import sqlite3
import zlib

import listing_formats as F
import plan_fetch as PF


def test_show_more_and_drupal_pager_classes_are_partial():
    assert F.is_paged('<a href="?search=&amp;page=1">Show More</a>')
    assert F.is_paged('<ul class="pager js-pager__items"><a href="?page=1">Next</a></ul>')


def test_sequential_pager_follows_second_link_and_fails_if_it_is_missing(monkeypatch):
    con = sqlite3.connect(':memory:')
    con.execute('create table captures(capture_url text primary key, page_url text, raw_zlib blob)')
    base = 'https://example.edu/faculty'
    cap = 'https://web.archive.org/web/20200401000000id_/' + base
    page0 = '<a href="?page=1">Show More</a>'
    con.execute('insert into captures values(?,?,?)', (cap, base, zlib.compress(page0.encode())))
    available = {1, 2}

    def cdx(params, db):
        n = int(params['url'].rsplit('page=', 1)[1])
        return [dict(timestamp='20200402000000', original='https://' + params['url'], statuscode='200')] if n in available else []

    def fetch(ts, original, page_url, dept, db):
        n = int(original.rsplit('page=', 1)[1])
        body = '<p>Faculty</p>' + ('<a href="?page=2">Show More</a>' if n == 1 else '')
        pc = f'https://web.archive.org/web/{ts}id_/{original}'
        db.execute('insert or replace into captures values(?,?,?)', (pc, page_url, zlib.compress(body.encode())))
        return pc

    monkeypatch.setattr(PF.wb, 'cdx', cdx)
    monkeypatch.setattr(PF.wb, 'fetch_capture', fetch)
    monkeypatch.setattr(PF, 'ensure_extracted', lambda *a: (200, []))
    monkeypatch.setattr(F, 'parse', lambda *a: ('test', [dict(name_listed='Faculty')]))
    got, missing = PF.fetch_pages(con, {}, cap, page0, '20200101', '20200630', 'CS')
    assert sorted(got) == [1, 2] and missing == []
    available.remove(2)
    got, missing = PF.fetch_pages(con, {}, cap, page0, '20200101', '20200630', 'CS')
    assert sorted(got) == [1] and missing == [2]
