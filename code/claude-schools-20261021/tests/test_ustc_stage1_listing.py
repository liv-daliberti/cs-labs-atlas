from tools import listing_formats as F
import sqlite3
import zlib
import plan_fetch as PF
import types


def test_webplus_faculty_page_requires_every_pager_page():
    html = '''<li class="col_title"><h2>教授</h2></li>
    <a class="sub-link" href="/trjs/list.htm">特任教授</a>
    <div class="col_news_list listcon"><div id="wp_news_w6"><ul class="news_list list2">
      <li class="news n1"><div class="news_title"><a href="/profiles/chen.htm">陈恩红</a></div>
      <div class="news_tel">[email removed]</div></li>
      <li class="news n2"><div class="news_title"><a href="/profiles/an.htm">安 虹</a></div></li>
    </ul></div></div>
    <ul class="wp_paging"><li class="page_nav"><a href="/js_23235/list3.htm">尾页</a></li>
    <li><em class="curr_page">1</em>/<em class="all_pages">3</em></li></ul>'''
    fmt, rows = F.parse(html)
    assert fmt == 'ustc_cs_cards'
    assert [(r['name_listed'], r['titles'], r['profile']) for r in rows] == [
        ('陈恩红', ['教授'], '/profiles/chen.htm'),
        ('安 虹', ['教授'], '/profiles/an.htm'),
    ]
    assert F.is_paged(html)
    assert F.page_links(html, 'https://cs.ustc.edu.cn/js_23235/list.htm') == {
        1: 'https://cs.ustc.edu.cn/js_23235/list2.htm',
        2: 'https://cs.ustc.edu.cn/js_23235/list3.htm',
    }


def test_legacy_profile_sidebar_uses_rank_rosters_and_ignores_biography():
    html = '''<a class="gk">教授</a><table><tr><td>
      <a href="../../bdjs/201006/t20100614_22053.html">陈恩红</a>
    </td></tr></table>
    <a class="gk">副教授</a><table><tr><td>
      <a href="../../fjs/201006/t20100614_22054.html">董兰芳</a>
    </td></tr></table>
    <a class="gk">博士后</a><table><tr><td>
      <a href="../../bsh/201007/t20100701_23943.html">博士后名单</a>
    </td></tr></table>
    <div class="wp_articlecontent"><h1>陈国良</h1><p>个人简介</p></div>'''
    rows = F.parse(html, 'ustc_cs_legacy_sidebar')[1]
    assert [(r['name_listed'], r['titles']) for r in rows] == [
        ('陈恩红', ['教授']), ('董兰芳', ['副教授'])]


def test_rank_specific_small_roster_keeps_real_people_but_rejects_shell():
    con = sqlite3.connect(':memory:')
    con.execute('create table captures(capture_url text, raw_zlib blob)')
    def put(body):
        con.execute('delete from captures')
        con.execute('insert into captures values (?,?)', ('capture', zlib.compress(body.encode())))
    page = '<li class="col_title"><h2>特任研究员</h2></li><div class="col_news_list listcon"><ul>' + ''.join(
        f'<li class="news"><div class="news_title"><a href="/person/{n}.htm">研究员{n}</a></div></li>' for n in range(3)) + '</ul></div>'
    put(page)
    assert not PF.charter_usable(con, 'capture', {'format': 'ustc_cs_cards'})[0]
    assert PF.charter_usable(con, 'capture', {'format': 'ustc_cs_cards', 'min_entries': 1})[0]
    put('<li class="col_title"><h2>特任研究员</h2></li><div class="col_news_list listcon"></div>')
    assert not PF.charter_usable(con, 'capture', {'format': 'ustc_cs_cards', 'min_entries': 1})[0]


def test_paged_charter_reaches_the_page_fetch_even_if_first_page_is_partial(monkeypatch):
    con = sqlite3.connect(':memory:')
    con.execute('create table captures(capture_url text, page_url text, department text, wayback_timestamp text, final_url text, http_status integer, fetched_at text, sha256 text, nbytes integer, content_type text, raw_zlib blob, blocks_json text, text text, note text)')
    con.execute('create table plan(slot text, dept text, year integer, half text, page_url text, capture_url text, wayback_timestamp text, status text, reason text, tried text)')
    con.execute('create table plan_pages(slot text, year integer, half text, page integer, page_url text, capture_url text, wayback_timestamp text)')
    base = 'https://cs.ustc.edu.cn/js_23235/list.htm'
    cap = 'https://web.archive.org/web/20240414000000id_/' + base
    page = '<li class="col_title"><h2>教授</h2></li><div class="col_news_list listcon"><ul>' + ''.join(
        f'<li class="news"><div class="news_title"><a href="/p/{n}">教授{n}</a></div></li>' for n in range(5)) + '</ul></div><ul class="wp_paging"><em class="all_pages">2</em></ul>'
    con.execute('insert into captures values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (cap, 'cs.ustc.edu.cn/js_23235/list.htm', 'CS', '20240414000000', cap, 200, '', 'x', len(page), 'text/html', zlib.compress(page.encode()), None, None, None))
    monkeypatch.setitem(PF._CFG, 'ustc', types.SimpleNamespace(CHARTER=True))
    monkeypatch.setattr(PF, 'candidates', lambda s, c: [(0, s['urls'][0][0], dict(timestamp='20240414000000', original=base, statuscode='200', digest='x'))])
    monkeypatch.setattr(PF.wb, 'fetch_capture', lambda *a: cap)
    monkeypatch.setattr(PF, 'ensure_extracted', lambda *a: (200, []))
    monkeypatch.setattr(PF, 'usable', lambda *a: (False, 'no English title'))
    monkeypatch.setattr(PF, 'fetch_pages', lambda *a: ({1: (base.replace('list.htm', 'list2.htm'), cap, '20240414000000')}, []))
    PF.run_slot('ustc', dict(slot='professors', dept='CS', urls=[('cs.ustc.edu.cn/js_23235/list.htm', '20240101', '20241231')],
                             format='ustc_cs_cards', years=[2024]), con, {})
    assert con.execute("select status from plan where year=2024 and half='H1'").fetchone()[0] == 'ok'
    assert con.execute('select count(*) from plan_pages').fetchone()[0] == 1
