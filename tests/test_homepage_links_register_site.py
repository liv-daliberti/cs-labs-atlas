"""homepage_links_school also reads each PI's register-chosen website from the stage-3 capture stores (family name and one-distinct-pid rules kept)."""
import re
import sqlite3
import zlib
import homepage_links_school as HL  # noqa: E402


def make_db(path, rows):
    con = sqlite3.connect(path)
    con.execute('create table captures (id integer primary key, url text, final_url text, status int, sha256 text, content blob)')
    for u, fu, st, sha, html in rows:
        con.execute('insert into captures (url, final_url, status, sha256, content) values (?,?,?,?,?)', (u, fu, st, sha, zlib.compress(html.encode())))
    con.commit(); con.close()


def test_register_pages_read_by_url_or_final_url_and_skip_pages_without_a_capture(tmp_path):
    db = tmp_path / 'a.sqlite'
    make_db(db, [('http://a.edu/~ann/', 'https://a.edu/~ann/', 200, 'a' * 64, '<a href="https://dblp.org/pid/12/345">Ann Lee</a>'),
                 ('http://b.edu/', None, 404, 'b' * 64, 'gone')])
    labs = [dict(pi='Ann Lee', url='https://a.edu/~ann/', coverage='website'), dict(pi='Bo', url='http://b.edu/', coverage='website'),
            dict(pi='Cy', url=None, coverage='reason'), dict(pi='Di', url='http://x.edu/', coverage='reason')]
    got = HL.register_pages(labs, [tmp_path / 'missing.sqlite', db])
    assert list(got) == ['Ann Lee']   # by final_url; a 404, a reason row and a missing capture give nothing
    u, sha, html = got['Ann Lee'][0]
    assert sha == 'a' * 64 and HL.DBLP.search(html).group(2) == '12/345'
    assert 'lee' in html.lower() and re.search(r'orcid', html) is None
