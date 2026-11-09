"""Oxford Computer Science student profile pages: the department's own record of a student's supervisors (R-STU-25).

A CS student profile (www.cs.ox.ac.uk/people/First.Last) reads, after the name: "Doctoral Student  Student, <College>  [Leaving date: <date>]  Themes: ...
Supervisors <name> <name> ...". The supervisor names are the department's own record; a supervisor counts only when his or her FULL name is that of a PI
of the school (R-STU-03: no initials, no surname-only matches).

crawl     fetch the students list (people/students.html), plus any extra profile URLs given in a file, and each profile (same-host redirects only, robots.txt
          honoured through school_web, at least 2 s between requests) into the school capture store
evidence  stored profiles -> reviewed rows {pi, students: [{name, role, years, url, sha256, quote, note}]} (roster-evidence.json shape)
usage: cs_student_pages.py crawl [--extra FILE] [--limit N] | evidence --pis pis.json --out FILE
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import school_web as W  # noqa: E402

KEY = 'oxford'
BASE = 'https://www.cs.ox.ac.uk'
LIST = BASE + '/people/students.html'
MONTHS = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'


def fold(s):
    s = unicodedata.normalize('NFKD', s.replace('\xa0', ' '))
    return ' '.join(re.sub(r'[^a-z ]', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower().replace('-', ' ')).split())


def resolve(url, hops=2):
    import requests
    c = W.con(KEY)
    host = urllib.parse.urlsplit(url).netloc
    for _ in range(hops + 1):
        ok, delay = W.robots_ok(c, url)
        if not ok:
            return None
        time.sleep(max(delay, 2.0))
        try:
            r = requests.get(url, headers={'User-Agent': W.UA}, timeout=40, allow_redirects=False)
        except Exception:  # noqa: BLE001
            return None
        if r.status_code in (301, 302, 303, 307, 308):
            t = urllib.parse.urljoin(url, r.headers.get('Location', ''))
            if urllib.parse.urlsplit(t).netloc != host or not t.startswith('https://'):
                return None
            url = t
            continue
        return url if r.status_code == 200 else None
    return None


def crawl(extra, limit):
    c = W.con(KEY)
    res = W.live(c, LIST)
    if not res or res[0] != 200:
        raise SystemExit('students list not readable')
    h = W.live_html(c, LIST)
    urls = [BASE + u for u in dict.fromkeys(re.findall(r'<li[^>]*class="personIndex"[^>]*>.*?href="(/people/[^"]+)"', h, re.S))]
    if extra:
        urls += [u for u in json.loads(Path(extra).read_text()) if u not in urls]
    n = 0
    for u in urls:
        done = c.execute('select 1 from live where url=? and status=200', (u.lower().rstrip('/'),)).fetchone()
        if done:
            continue
        fin = resolve(u)
        if not fin:
            continue
        W.live(c, fin)
        n += 1
        if n % 25 == 0:
            print(n, fin, flush=True)
        if limit and n >= limit:
            break
    print('fetched', n, 'of', len(urls))


def parse_page(flat, name):
    """(role, leaving year, supervisors string, quote) from the profile's flat text, or None."""
    i = flat.find(name)
    if i < 0:
        return None
    seg = flat[i:]
    m = re.search(r'\b(Doctoral Student|DPhil Student|Student on|Master\w* Student|MSc Student|Visiting Student)\b', seg[:400])
    sup = re.search(r'\bSupervisors?\s+(.*?)(?=\s+About Us\b|\s+Interests\b|\s+Biography\b|\s+Selected Publications\b|$)', seg)
    if not m or not sup:
        return None
    lv = re.search(rf'Leaving date:\s*\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}\s+(\d{{4}})', seg[:600])
    q0 = m.start()
    quote = seg[q0:sup.end()]
    return m.group(1), int(lv.group(1)) if lv else None, sup.group(1), quote


def evidence(pis_file, out):
    pis = json.loads(Path(pis_file).read_text())
    forms = {}
    for p in pis:
        for nm in [p['pi']] + list(p.get('names') or []):
            f = fold(nm)
            if len(f.split()) >= 2:
                forms.setdefault(f, set()).add(p['pi'])
    c = W.con(KEY)
    rows, cnt = {}, {}

    def bump(k):
        cnt[k] = cnt.get(k, 0) + 1
    for url, sha in c.execute("select url, sha256 from live where status=200 and url like 'https://www.cs.ox.ac.uk/people/%' and url not like '%/students.html'"):
        res = W.live(c, url)
        flat = W.flat(res[2])
        mm = re.search(r"\b([A-Z][^\s]*(?: [A-Z][^\s]*){1,3}) \1 \1\b", flat)
        name = None
        if mm:
            name = mm.group(1)
        if not name:
            bump('no_name')
            continue
        p = parse_page(flat, name)
        if not p:
            bump('no_role_or_supervisors')
            continue
        role, leave, sup, quote = p
        if quote not in flat:
            bump('quote_not_in_text')
            continue
        bump('students_with_supervisors')
        fs = fold(sup)
        hits = sorted({pi for f, v in forms.items() if re.search(rf'(?:^| ){re.escape(f)}(?: |$)', fs) for pi in v})
        year = leave or 2026
        if year < 2016:
            bump('before_window')
            continue
        for pi in hits:
            if fold(name) == fold(pi):
                continue
            rows.setdefault(pi, {})[fold(name)] = dict(
                name=name, role='masters' if role.startswith('Master') or role.startswith('MSc') else ('visiting' if role.startswith('Visiting') else 'phd'),
                years=[year, year], url=url, sha256=sha, quote=quote,
                note=f"Oxford CS student profile ('{role}'; supervisors line names {pi} by full name). Years: {'the leaving-date year' if leave else 'the capture year (current student)'}. R-STU-25")
            bump('rows')
    out_rows = [dict(pi=p, students=sorted(v.values(), key=lambda s: (s['years'][0], s['name'])),
                     notes='Oxford CS student profile pages naming the supervisor (tools/cs_student_pages.py, R-STU-25).') for p, v in sorted(rows.items())]
    Path(out).write_text(json.dumps(out_rows, indent=1, ensure_ascii=False))
    print(json.dumps(cnt), len(out_rows), 'PIs')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['crawl', 'evidence'])
    ap.add_argument('--extra')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--pis')
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.cmd == 'crawl':
        crawl(a.extra, a.limit)
    else:
        evidence(a.pis, a.out)
