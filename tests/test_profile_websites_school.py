import json
import sqlite3
import zlib

import profile_websites_school as PW

CARD = '''<dl class="detail"><dt>학위 </dt><dd>PhD</dd><dt>웹사이트 </dt><dd><a href="https://www.wiederrecht.com/">https://www.wiederrecht.com/</a></dd>
<dt>이메일</dt><dd><a href="javascript:emailSend('w^*kaist.ac.kr');">x</a></dd></dl>'''


def test_card_website_reads_the_website_field_only():
    assert PW.card_website(CARD) == 'https://www.wiederrecht.com/'
    assert PW.card_website('<dl><dt>웹사이트</dt><dd><a href="https://cs.kaist.ac.kr/people/view?idx=3">p</a></dd></dl>') is None
    assert PW.card_website('<dl><dt>이메일</dt><dd><a href="mailto:a@b.c">a</a></dd></dl>') is None


def test_only_same_host_redirects_are_followed():
    c = sqlite3.connect(':memory:')
    c.execute('create table live (url text primary key, status int, raw_zlib blob)')
    def put(u, loc):
        c.execute('insert into live values (?,?,?)', (u, 301, zlib.compress(json.dumps({'location': loc}).encode())))
    put('http://se.kaist.ac.kr', 'https://se.kaist.ac.kr/')
    put('https://www.deal.kaist.ac.kr/', 'https://www.ai2lab.kaist.ac.kr/')
    put('http://a.example.org/x', '/y')
    assert PW.same_host_redirect(c, 'http://se.kaist.ac.kr') == 'https://se.kaist.ac.kr/'
    assert PW.same_host_redirect(c, 'https://www.deal.kaist.ac.kr/') is None
    assert PW.same_host_redirect(c, 'http://a.example.org/x') == 'http://a.example.org/y'
    assert PW.same_host_redirect(c, 'https://missing.example.org/') is None
