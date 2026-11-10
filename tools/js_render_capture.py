"""Capture JavaScript-rendered faculty-directory pages (url list in, captures out). Owner decision 2026-11-10 (Tsinghua EE/SIST, HKUST, ZJU, NTU shells).

Hard rules, all enforced here:
  1  robots.txt of the exact origin is checked BEFORE navigation (school_web.robots_ok: AI-agent disallows by name and unreadable robots both mean "not allowed");
     a host that is `blocked` in the school's capture store is not used again.
  2  honest user agent (school_web.UA), no spoofing or stealth; a rendered page that carries a bot-challenge marker (school_web.CHALLENGE) or a login wall is NOT
     stored as a page: the receipt says `challenge` / `login` and the host is blocked. Nothing is solved or worked around.
  3  polite: URLs are visited one at a time, at least `gap` seconds apart (and the robots crawl delay), a bounded wait for the render (`wait` seconds: the DOM
     must stop changing, or `wait_css` must be present), and a per-run page `cap`.
  4  the RENDERED DOM (after JavaScript) and the raw pre-render HTML are both stored in the school's capture store (table js_render) with their sha256, the fetch time,
     the HTTP status of the raw fetch, the requested sub-resource URLs the page itself made (window.performance resource entries: the XHR/JSON endpoints, for a later
     robots-checked plain fetch), and the tool/browser/driver versions, so quotes stay verifiable.
  5  only the URLs given are visited; nothing is crawled.
  6  no Wayback.
usage (compute node, e.g. Slurm -p all, 4G; the login node's sandbox cannot start a browser):
  JSRENDER_GECKODRIVER=<geckodriver> <venv>/bin/python tools/js_render_capture.py <school> <url> [<url> ...] [--wait-css SEL] [--cap N] [--gap S] [--wait S]
The Selenium venv is scratch/jsrender-venv (selenium 4.x, geckodriver recorded in docs/JS-RENDER.md); the tests need neither a browser nor Selenium.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import zlib


import school_web as W  # noqa: E402

TOOL = 'js_render_capture/1'
LOGIN_WALL = re.compile(r'<input[^>]+type=["\']password["\']|统一身份认证|请先登录|please (?:log ?in|sign in)', re.I)
SCHEMA = ('create table if not exists js_render (url text, fetched_at text, status text, raw_http int, raw_sha256 text, raw_zlib blob, '
          'dom_sha256 text, dom_zlib blob, resources text, tool text, browser text, driver text, wait_css text, note text, '
          'primary key (url, fetched_at))')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def default_raw_fetch(url):
    import requests
    r = requests.get(url, headers={'User-Agent': W.UA}, timeout=60, allow_redirects=False)
    return r.status_code, r.content


def firefox_driver():
    """Headless Firefox with the honest user agent; geckodriver from $JSRENDER_GECKODRIVER, else Selenium Manager."""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    o = Options()
    o.add_argument('-headless')
    o.set_preference('general.useragent.override', W.UA)
    o.set_preference('network.http.sendRefererHeader', 0)
    drv = os.environ.get('JSRENDER_GECKODRIVER')
    return webdriver.Firefox(options=o, service=Service(drv) if drv else Service())


def versions(driver):
    caps = getattr(driver, 'capabilities', {}) or {}
    return (f"{caps.get('browserName', '?')} {caps.get('browserVersion', '?')}",
            f"geckodriver {(caps.get('moz:geckodriverVersion') or '?')}")


def settle(driver, wait, wait_css=None, poll=1.0, sleep=time.sleep):
    """Bounded wait: document complete, then `wait_css` present, or the DOM length unchanged over two polls."""
    t0, last, stable = time.monotonic(), -1, 0
    while time.monotonic() - t0 < wait:
        if driver.execute_script('return document.readyState') == 'complete':
            if wait_css:
                if driver.execute_script('return document.querySelector(arguments[0]) !== null', wait_css):
                    return True
            else:
                n = len(driver.page_source)
                stable = stable + 1 if n == last else 0
                last = n
                if stable >= 2:
                    return True
        sleep(poll)
    return False


def ensure(c):
    c.execute(SCHEMA)
    c.commit()


def render(key, urls, *, wait=20.0, gap=3.0, cap=20, wait_css=None, http_origin=False, driver_factory=firefox_driver, raw_fetch=default_raw_fetch, con=None, sleep=time.sleep):
    """Render each URL once; returns one receipt per URL: {url, status, ...}. status: ok | robots_disallowed | host_blocked | challenge | login | not_settled | capped | error."""
    c = con or W.con(key)
    ensure(c)
    receipts, driver, last_visit = [], None, 0.0
    try:
        for i, url in enumerate(urls):
            host = urllib.parse.urlsplit(url).netloc
            if i >= cap:
                receipts.append(dict(url=url, status='capped'))
                continue
            if host in W._blocked:
                receipts.append(dict(url=url, status='host_blocked'))
                continue
            ok, delay = W.robots_ok(c, url, same_origin=True) if http_origin else W.robots_ok(c, url)
            if not ok:
                receipts.append(dict(url=url, status='robots_disallowed'))
                continue
            wait_s = max(gap, float(delay or 0)) - (time.monotonic() - last_visit)
            if last_visit and wait_s > 0:
                sleep(wait_s)
            if driver is None:
                driver = driver_factory()
            note, raw_http, raw = None, None, b''
            try:
                raw_http, raw = raw_fetch(url)
                driver.get(url)
                last_visit = time.monotonic()
                settled = settle(driver, wait, wait_css, sleep=sleep)
                dom = driver.page_source.encode('utf-8')
                try:
                    res = driver.execute_script('return performance.getEntriesByType("resource").map(function(e){return e.name})') or []
                except Exception:  # noqa: BLE001
                    res = []
            except Exception as e:  # noqa: BLE001
                receipts.append(dict(url=url, status='error', note=repr(e)[:200]))
                continue
            text = dom.decode('utf-8', 'replace')
            status = 'ok' if settled else 'not_settled'
            if W.CHALLENGE.search(text):
                status = 'challenge'
                W.block(c, host, f'challenge in rendered page {url}')
            elif LOGIN_WALL.search(text):
                status = 'login'
                W.block(c, host, f'login wall in rendered page {url}')
            browser, drv = versions(driver)
            now = time.strftime('%Y-%m-%dT%H:%M:%S')
            if status in ('ok', 'not_settled'):
                c.execute('insert or replace into js_render values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (url, now, status, raw_http, sha(raw), zlib.compress(raw, 6), sha(dom), zlib.compress(dom, 6), json.dumps(res), TOOL, browser, drv, wait_css, note))
            else:  # a challenge or login page is recorded as a receipt only, never kept as a page
                c.execute('insert or replace into js_render values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (url, now, status, raw_http, None, None, sha(dom), None, '[]', TOOL, browser, drv, wait_css, 'not stored: ' + status))
            c.commit()
            receipts.append(dict(url=url, status=status, raw_http=raw_http, raw_sha256=sha(raw), dom_sha256=sha(dom), dom_bytes=len(dom), resources=len(res)))
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:  # noqa: BLE001
                pass
    return receipts


def stored(c, url):
    """(rendered DOM str, raw HTML str, row) of the newest ok capture of url, hashes verified; None when absent."""
    r = c.execute("select dom_zlib, raw_zlib, dom_sha256, raw_sha256, fetched_at, resources, browser, driver from js_render "
                  "where url=? and status in ('ok','not_settled') order by fetched_at desc limit 1", (url,)).fetchone()
    if not r:
        return None
    dom, raw = zlib.decompress(r[0]), zlib.decompress(r[1])
    assert sha(dom) == r[2] and sha(raw) == r[3], 'stored capture bytes do not match their sha256'
    return dom.decode('utf-8', 'replace'), raw.decode('utf-8', 'replace'), dict(fetched_at=r[4], resources=json.loads(r[5] or '[]'), browser=r[6], driver=r[7])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('school'); ap.add_argument('urls', nargs='+')
    ap.add_argument('--wait', type=float, default=20.0); ap.add_argument('--gap', type=float, default=3.0)
    ap.add_argument('--cap', type=int, default=20); ap.add_argument('--wait-css')
    ap.add_argument('--http-origin', action='store_true', help='read robots.txt at each URL\'s own origin (http://host/robots.txt) for an owner-approved http-only host; HTTPS is never inferred')
    a = ap.parse_args(argv)
    out = render(a.school, a.urls, wait=a.wait, gap=max(a.gap, 3.0), cap=a.cap, wait_css=a.wait_css, http_origin=a.http_origin)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if all(r['status'] in ('ok', 'not_settled') for r in out) else 3


if __name__ == '__main__':
    sys.exit(main())
