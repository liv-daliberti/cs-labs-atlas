"""Tsinghua adviser statements in stored department pages (rule R-STU-30): department news / speeches, the Beijing outstanding-doctoral-thesis list and
a PI's own official profile page. OFFLINE: reads captures already stored by the crawl (sqlite table `live`: url, sha256, raw_zlib), fetches nothing.

A statement is a dated student-adviser pair when ONE sentence names a student (2-4 Han characters, a common-surname start), a student level (博士 phd,
硕士 masters) and the adviser by 导师 / 指导教师 / 论文指导教师 / 师从. Patterns (everything else is not a row):
  A  <level><name>（导师为|论文指导教师 <PI>        博士生方骏祺（导师为汪东升教授
  C  <level><name>，导师是|为 <PI>                  ...2026级博士生钟羿，导师是艾清遥副教授
  B  <name>，[<=70 chars, no 。；——, one level word] ，导师|指导教师|导师为 <PI>   关超宇，计算机系2019级硕士研究生，导师朱文武教授
  E  <name>的博士学位论文...指导教师为<PI>   (also 博士学位 as the level of B: 毛佳昕…获得博士学位，导师为马少平教授)
Thesis list (the university's 2025 Beijing outstanding doctoral theses PDF): a line `<year> <subject> <student> <adviser> <title> [提名]`; the year is the AWARD
year; a 提名 (nomination) line counts like any other (the list names the thesis author and the adviser either way).
Profile page: `<year>年指导博士生|硕士生 <name> 获 ...` on a PI's own official page.

Conditions (R-STU-30): quote verbatim in the page text, capture sha256 stored; the adviser is the exact full Han name of ONE PI (a name two PIs share is
dropped; a PI name with a bracket tag `杨帆 [EE]` matches only a page of that department's site); the page's site belongs to the PI's department; a postdoc,
a faculty member, a team clause (postdoc / undergraduates / developers listed with the student), a competition team and an unspecified 'graduate' are never rows; the year is the article / list year, not after the capture year (held); the PI
needs a period record covering the year (pis.json `periods` or a faculty-periods file; none, or a year before its start or after its end: HELD).

usage: tsinghua_adviser_statements.py evidence --captures DB [DB ...] --pis pis.json [--periods faculty-periods.json] [--pdf-url URL] [--out FILE] [--held FILE]
"""
import argparse
import hashlib
import html as H
import json
import re
import subprocess
import sys
import tempfile
import zlib
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

RULE = 'R-STU-30'
WINDOW = (2016, 2026)
SURNAMES = set('王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤'
                '关祖易班鲁都洪屈宫晏庄柳符季翟甘华喻管单牛游温蓝乔祁封阎项裘'.replace(' ', ''))
SITE_DEPTS = {'www.cs.tsinghua.edu.cn': {'CS', 'AIR'}, 'air.tsinghua.edu.cn': {'AIR', 'CS'}, 'www.ee.tsinghua.edu.cn': {'EE'}, 'web.ee.tsinghua.edu.cn': {'EE'},
              'www.thss.tsinghua.edu.cn': {'SW'}, 'www.au.tsinghua.edu.cn': {'AU'}, 'iiis.tsinghua.edu.cn': {'IIIS'}, 'www.me.tsinghua.edu.cn': {'ME', 'SVM'}}
SUBJECT_DEPTS = {'计算机科学与技术': {'CS', 'AIR', 'IIIS'}, '软件工程': {'SW'}, '控制科学与工程': {'AU'}, '信息与通信工程': {'EE'}, '电子科学与技术': {'EE'},
                 '机械工程': {'SVM', 'ME'}, '电子科学与技术 ': {'EE'}}
NAME = r'([一-鿿]{2,4})'
LEVEL = r'(?:直博生|博士生|博士研究生|博士毕业生|硕士生|硕士研究生|硕转博研究生|博士(?:[一二三四五六]年级)?研究生|博士学位)'
TEACHER = r'(?:教授|副教授|研究员|老师|助理教授|副研究员|讲席教授|长聘教授|长聘副教授|助理研究员)'
ADV = r'(?:导师|指导教师|论文指导教师|师从)(?:为|是|：|:)?\s*(?:[一-鿿]{0,8}?(?:系|院|所|中心))?([一-鿿]{2,4}?)' + TEACHER
PATS = [
    ('A', re.compile(r'(' + LEVEL + r')' + NAME + r'[（(](?:导师为|论文指导教师|导师：|导师)' + r'(?:[一-鿿]{0,8}?(?:系|院|所))?([一-鿿]{2,4}?)' + TEACHER)),
    ('C', re.compile(r'(' + LEVEL + r')' + NAME + r'[，,]\s*' + ADV)),
    ('E', re.compile(r'([一-鿿]{2,8})的(博士)学位论文[^。]{0,90}?(?:指导教师|导师)(?:为|是)(?:[一-鿿]{0,8}?(?:系|院|所|中心))?([一-鿿]{2,4}?)' + TEACHER)),
    ('B', re.compile(r'(?:(?<=[。；、：\s）)])|^)' + NAME + r'\s*[，,](?:[^。；，,—]{0,60}[，,])?[^。；—]{0,50}?(' + LEVEL + r')[^。；—]{0,24}?[，,]\s*' + ADV)),
]
PROFILE = re.compile(r'((?:19|20)\d\d)年指导(博士生|硕士生|博士研究生|硕士研究生)' + NAME + r'(?=获|荣获|入选|的|完成)')
PDF_LINE = re.compile(r'^\s*((?:20)\d\d)\s+(\S+)\s+([一-鿿]{2,4})\s+([一-鿿]{2,4})\s+(\S.*?)(?:\s+(提名))?\s*$')
TEAM = re.compile(r'博士后|本科生|研发人员|团队|参赛|成员|课题组全体')
DATE = re.compile(r'((?:19|20)\d\d)[.\-](\d\d)[.\-](\d\d)')


def flat(raw_html):
    t = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', raw_html)
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<!--.*?-->|<[^>]+>', ' ', t))).strip()


def article_year(text):
    body = text[text.find('正文'):] if '正文' in text else text
    m = DATE.search(body)
    return int(m.group(1)) if m else None


def role_of(level):
    if '硕' in level and '博' not in level:
        return 'masters'
    return 'phd' if '博' in level or level == '直博生' else None


def plausible_name(n):
    return 2 <= len(n) <= 4 and n[0] in SURNAMES and not re.search(r'[的了在是和与及等]', n)


def han_index(pis):
    """Han full name -> [pi keys]: the PI's own name and listed Han names, bracket tag removed; a tagged key keeps its tag for site matching."""
    idx = {}
    for p in pis:
        for n in [p['pi']] + list(p.get('names') or []):
            h = re.sub(r'\s*\[.*?\]\s*', '', n).replace(' ', '')
            if re.fullmatch(r'[一-鿿·]{2,4}', h):
                idx.setdefault(h, set()).add(p['pi'])
    return idx


def period_start_end(pi, pis_by, periods):
    """-> (start_year, end_year or None) from pis.json periods or a faculty-periods file; the earliest start, the latest end (open = None)."""
    spans = []
    for p in (pis_by.get(pi) or {}).get('periods') or []:
        if p.get('start'):
            spans.append((int(str(p['start'])[:4]), int(str(p['end'])[:4]) if p.get('end') else None))
    for r in periods or []:
        if r.get('name') == pi and r.get('facultyStart'):
            spans.append((int(str(r['facultyStart'])[:4]), int(str(r['facultyEnd'])[:4]) if r.get('facultyEnd') else None))
    if not spans:
        return None
    return min(s for s, _ in spans), (None if any(e is None for _, e in spans) else max(e for _, e in spans))


def pdf_text(raw):
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(raw)
    try:
        return subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True, text=True, check=False).stdout
    finally:
        Path(f.name).unlink(missing_ok=True)


def statements(text):
    """-> [(pattern, level, student, adviser_han, quote)] of the page text."""
    out = []
    for pat, rx in PATS:
        for m in rx.finditer(text):
            g = m.groups()
            level, student, adv = (g[1], g[0], g[2]) if pat in ('B', 'E') else (g[0], g[1], g[2])
            if TEAM.search(text[max(0, m.start() - 60):m.end()]) and pat != 'E':   # a team clause (postdoc, undergraduates, developers listed together) is not a per-student statement
                continue
            if pat == 'E':   # the name is the last 3 (else 2) Han characters before 的博士学位论文 ('...2024届博士毕业生罗正雄的博士学位论文')
                tail = student
                student = tail[-3:] if plausible_name(tail[-3:]) else tail[-2:]
                quote = m.group(0)[len(tail) - len(student):]
            else:
                quote = m.group(0)
            out.append((pat, level, student, adv, quote))
    return out


def evidence(captures, pis, periods=None, pdf_url=None, today=None):
    """captures: [dict(url, sha256, raw(bytes))]. -> (rows [{pi, students, notes}], held [dict], counts)."""
    import datetime as dt
    today = today or dt.date.today()
    idx = han_index(pis)
    pis_by = {p['pi']: p for p in pis}
    rows, held, counts = {}, [], dict(pages=0, statements=0, rows=0, held=0)

    def consider(pi_han, student, role, year, quote, url, sha, kind, depts_ok, note):
        counts['statements'] += 1
        why = None
        keys = idx.get(pi_han) or set()
        if len(keys) != 1:
            why = 'adviser_not_one_pi' if keys else 'adviser_no_pi'
        elif not plausible_name(student):
            why = 'student_name_not_plausible'
        elif role is None:
            why = 'role_not_phd_or_masters'
        else:
            pi = next(iter(keys))
            dp = set(pis_by[pi].get('departments') or [])
            tag = re.search(r'\[(.*?)\]', pi)
            if depts_ok is not None and not (dp & depts_ok):
                why = 'page_site_not_pi_department'
            elif tag and depts_ok is not None and tag.group(1) not in depts_ok:
                why = 'tag_department_mismatch'
            elif not (WINDOW[0] <= (year or 0) <= min(WINDOW[1], today.year)):
                why = 'year_outside_window_or_future'
            else:
                per = period_start_end(pi, pis_by, periods)
                if per is None:
                    why = 'no_period_record'
                elif year < per[0] or (per[1] is not None and year > per[1]):
                    why = f'year_{year}_outside_period_{per[0]}_{per[1]}'
        rec = dict(pi=next(iter(keys)) if len(keys) == 1 else pi_han, student=student, role=role, years=[year, year], url=url, sha256=sha, quote=quote,
                   source_class=kind, note=f'{note} {RULE}')
        if why:
            held.append(dict(rec, held_reason=why))
            counts['held'] += 1
            return
        key = (rec['pi'], student)
        d = rows.setdefault(rec['pi'], {})
        if key in {(rec['pi'], s['name']) for s in d.values()}:
            for s in d.values():
                if s['name'] == student:
                    s.setdefault('other_sources', []).append(url)
            return
        d[student] = dict(name=student, role=role, years=[year, year], url=url, sha256=sha, quote=quote, source_class=kind, note=rec['note'])
        counts['rows'] += 1

    for c in captures:
        url, raw = c['url'], c['raw']
        if hashlib.sha256(raw).hexdigest() != c['sha256']:
            continue
        counts['pages'] += 1
        if url.lower().endswith('.pdf'):
            if pdf_url and url != pdf_url:
                continue
            for line in pdf_text(raw).splitlines():
                m = PDF_LINE.match(line)
                if not m:
                    continue
                year, subj, student, adv, title, nom = m.groups()
                quote = re.sub(r'\s+', ' ', line).strip()
                consider(adv, student, 'phd', int(year), quote, url, c['sha256'], 'beijing_outstanding_phd_thesis_list' + ('_nomination' if nom else ''),
                         SUBJECT_DEPTS.get(subj.strip()), f'Beijing outstanding doctoral thesis list, award year {year}' + (' (提名)' if nom else '') + f', subject {subj}.')
            continue
        host = urlsplit(url).hostname or ''
        depts = SITE_DEPTS.get(host)
        text = flat(raw.decode('utf-8', 'replace'))
        year = article_year(text)
        for pat, level, student, adv, quote in statements(text):
            if level.endswith('导师'):
                continue
            consider(adv, student, role_of(level), year, quote, url, c['sha256'], 'dept_page_stated_adviser', depts, f'Stated adviser in a department page dated {year} (pattern {pat}).')
        head = text[:200].replace(' ', '')   # the page's owner: exactly one PI whose Han name is in the page heading
        owners = {next(iter(k)) for h, k in idx.items() if h in head and len(k) == 1}
        for m in PROFILE.finditer(text):
            if '/info/' in url and host in SITE_DEPTS and len(owners) == 1:
                consider(re.sub(r'\s*\[.*?\]\s*', '', next(iter(owners))), m.group(3), role_of(m.group(2)), int(m.group(1)), m.group(0), url, c['sha256'],
                         'official_pi_profile_page', depts, 'Own official profile page of the adviser.')
    out = [dict(pi=pi, students=sorted(d.values(), key=lambda s: s['name']), notes=f'Tsinghua adviser statements ({RULE}).') for pi, d in sorted(rows.items())]
    return out, held, counts


def load_captures(dbs, urls=None):
    out, seen = [], set()
    for d in dbs:
        con = sqlite3.connect(f'file:{d}?mode=ro', uri=True)
        for url, sha, blob in con.execute('select url, sha256, raw_zlib from live where status=200 and raw_zlib is not null'):
            if url in seen:
                continue
            seen.add(url)
            out.append(dict(url=url, sha256=sha, raw=zlib.decompress(blob)))
        con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['evidence'])
    ap.add_argument('--captures', nargs='+', required=True)
    ap.add_argument('--pis', required=True)
    ap.add_argument('--periods')
    ap.add_argument('--pdf-url')
    ap.add_argument('--out')
    ap.add_argument('--held')
    a = ap.parse_args()
    rows, held, counts = evidence(load_captures(a.captures), json.load(open(a.pis)), json.load(open(a.periods)) if a.periods else None, a.pdf_url)
    print(json.dumps(counts))
    if a.out:
        Path(a.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n')
    if a.held:
        Path(a.held).write_text(json.dumps(held, ensure_ascii=False, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
