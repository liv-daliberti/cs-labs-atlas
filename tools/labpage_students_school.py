"""Students from a protocol school's lab member pages (protocol stage 6, source 3), into the builder's lab-page evidence
format (hierarchy/<key>/labpage-evidence.json, read by pi_hierarchy.py like Berkeley's and EPFL's).

pages    each PI's homepage pages (tools/periods_school.py fetched them) and, one level down, the links on them whose
         text or path says people / students / group / members / team (at most 3 per PI, same site or the PI's lab
         site). Fetching follows the charter: hosts whose `host_use` is live are fetched live (robots honoured,
         challenges detected and the host then blocked); every other host, and every challenged one, is read only from
         existing Wayback id_ captures (the nearest 2026 capture and the nearest one to the PI's first listed year).
         No source the charter marks `none` (Deep Blue, news.umich.edu, record.umich.edu) is ever used.
names    hierarchy/labpage-tools-epfl-berkeley/lpdom.member_candidates (sectioned name lines under role headings).
         Kept: a role of phd or postdoc (lpdom.role_of over the heading path and the line), a plausible person name
         that is not the PI. Alumni headings (former, graduated, alumni) give role phd_alumnus / postdoc_alumnus.
years    a year or range on the line (lpdom.years_in), else the page's capture year (current members; years_basis
         capture_date)
quote    the page's own whitespace-collapsed text from the section heading through the student's name (verbatim, at
         most 600 characters; a candidate without such a stretch is dropped)
filters  plausible person names only (lpdom.plausible_person: no paper titles or topics), 2-4 tokens; alumni only from
         an alumni section and only with a stated year (a graduate without a year cannot be placed); nothing whose years
         end before 2016
status   automatic and unreviewed (auto: true); stage 9's accuracy sample measures it
-> hierarchy/<key>/labpage-evidence.json, hierarchy/<key>/labpage-students-report.json
defenses (protocol stage 6, source 2) department dissertation-defense announcements, read only from Wayback captures of
         the department hosts' /event/ pages whose URL says defense or dissertation (CDX filter). An announcement
         names the candidate ('<Student>PhD Candidate', 'PhD Defense: <Student>') and, on the EECS sites, a
         'Faculty Host <PI>' (the defense chair). The student's quote is the announcement head through the candidate's
         name; host_quote is the 'Faculty Host' line (same page, same sha256). Only hosts that are census PIs count.
         -> hierarchy/<key>/defense-evidence.json, merged into labpage-evidence.json by extract (role phd_alumnus,
         years = the defense year)
usage: labpage_students_school.py links|defenses|extract <key>
"""
import collections, json, re, sys, urllib.parse, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402
import periods_school as PS  # noqa: E402
from pi_hierarchy import Name, toks  # noqa: E402

sys.path.insert(0, str(P.HIERARCHY / 'labpage-tools-epfl-berkeley'))
import lpdom  # noqa: E402

PEOPLE = re.compile(r'\b(people|students|group|members|team|lab)\b', re.I)
SKIP = re.compile(r'mailto:|\.pdf$|calendar|publication|paper|teaching|course|news|blog|cv|resume|twitter|linkedin|github\.com|scholar\.google', re.I)
ALUM = lpdom.ALUMNI_RX


def stored_pages(c, url):
    """(page url as cited, sha256, html, observed year) of every stored copy of a URL (live, then Wayback captures)."""
    out = []
    r = c.execute('select status, sha256, raw_zlib, fetched_at from live where url=?', (url,)).fetchone()
    if r and r[0] == 200 and r[2]:
        out.append((url, r[1], zlib.decompress(r[2]).decode('utf-8', 'replace'), int(r[3][:4])))
    for cap, sha, raw, ts in c.execute('select capture_url, sha256, raw_zlib, wayback_timestamp from captures where page_url=? and http_status=200', (url,)):
        if raw:
            out.append((cap, sha, zlib.decompress(raw).decode('utf-8', 'replace'), int(str(ts)[:4])))
    return out


def fetch(key, c, url, first):
    host = urllib.parse.urlsplit(url).netloc.lower()
    if S.host_use(key, host) == 'live' and host not in W._blocked:
        res = W.live(c, url)
        if res and res[0] == 200:
            return
    rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:6')
    if not rows:
        return
    picks = {min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - 202607))['timestamp'],
             min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - (first * 100 + 7)))['timestamp']}
    for r in rows:
        if r['timestamp'] in picks:
            W.capture(c, r['timestamp'], r['original'], url, 'labpage')


def people_links(html, base):
    out = []
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
        href, text = m.group(1), re.sub(r'<[^>]+>', ' ', m.group(2))
        u = urllib.parse.urljoin(base, href)
        orig = re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', u)
        if SKIP.search(orig) or not orig.startswith('http'):
            continue
        if PEOPLE.search(' '.join(text.split())[:60]) or PEOPLE.search(urllib.parse.urlsplit(orig).path):
            out.append(orig)
    return list(dict.fromkeys(out))


def targets_pages(key):
    """{pi: [urls]}: the homepages plus their stored people links (computed from stored pages only)."""
    c = W.con(key); out = {}
    for t in PS.targets(key):
        urls = list(t['urls'])
        for u in t['urls']:
            for cited, sha, h, y in stored_pages(c, u):
                urls += people_links(h, re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cited) if 'web.archive.org' in cited else cited)
        out[t['name']] = (t, list(dict.fromkeys(urls))[:3 + len(t['urls'])])
    return out


def links(key):
    c = W.con(key); n = collections.Counter()
    for pi, (t, urls) in targets_pages(key).items():
        for u in urls[len(t['urls']):]:
            if not stored_pages(c, u):
                fetch(key, c, u, t['first']); n['fetched'] += 1
        print(json.dumps(dict(pi=pi, pages=len(urls))), flush=True)
    print(json.dumps(dict(n)))


DEFENSE_HOSTS = ['cse.engin.umich.edu/event/', 'ece.engin.umich.edu/event/']  # TODO(debt): move to the charter ([students].defense_event_prefixes)


def defenses(key):
    c = W.con(key); out, n = [], collections.Counter()
    pfx = S.field(S.get(key), 'students.defense_event_prefixes') or DEFENSE_HOSTS
    for host in pfx:
        p = {'url': host, 'matchType': 'prefix', 'from': '2016', 'to': '2026', 'output': 'json', 'fl': 'timestamp,original,statuscode',
             'filter': 'original:.*(defense|dissertation).*', 'collapse': 'urlkey', 'limit': '20000'}
        for r in W.wb.cdx(p, c) or []:
            if r.get('statuscode') != '200' or 'google.com' in r['original']:
                continue
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], r['original'], 'defense')
            n[f'capture_{st}'] += 1
            if st != 200:
                continue
            t = W.flat(b)
            k = next((i_ for i_, x in enumerate(b) if x[0].startswith('h') and x[1].strip() == 'Dissertation Defense'), None)
            if k is None or k + 2 >= len(b):
                n['not_a_defense'] += 1; continue
            title, spk = b[k + 1][1], b[k + 2][1]
            name = None
            if 'PhD Candidate' in spk:
                name = spk[:spk.find('PhD Candidate')]
            elif re.search(r'Defense:\s*', title) and len(title.split(':', 1)[1].split()) <= 4:
                name = title.split(':', 1)[1]
            elif re.search(r'\s(?:Final|PhD|Ph\.D\.)?\s*Defense$', title):
                name = re.sub(r'\s*(?:Final|PhD|Ph\.D\.)?\s*Defense$', '', title)
            name = ' '.join((name or '').split())
            hk = next((i_ for i_, x in enumerate(b) if x[0].startswith('h') and x[1].strip() == 'Faculty Host'), None)
            host = None
            if hk is not None and hk + 1 < len(b):
                hm = re.match(r'(.+?)(?=Professor|Associate|Assistant|Research|Lecturer|University|$)', b[hk + 1][1])
                host = ' '.join(hm.group(1).split()) if hm else None
            w = re.search(r'WHEN:\s*(?:\w+,\s*)?\w+\s+\d{1,2},\s*((?:19|20)\d\d)', t)
            if not (name and 2 <= len(name.split()) <= 4 and host and w):
                n['no_candidate_or_host'] += 1; continue
            qi = t.find('Dissertation Defense ' + title); qj = t.find(name, qi)
            if qi < 0 or qj < 0 or qj - qi > 600:
                n['no_quote'] += 1; continue
            hq = t.find('Faculty Host ' + host)
            out.append(dict(student=name, host=host, year=int(w.group(1)), url=r['original'], capture_url=cap, sha256=sha,
                            quote=t[qi:qj + len(name)], host_quote=t[hq:hq + len('Faculty Host ' + host)] if hq >= 0 else 'Faculty Host ' + host))
            n['defenses'] += 1
    (P.HIERARCHY / key / 'defense-evidence.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(n)))


def extract(key):
    c = W.con(key); ev, rep = [], collections.Counter()
    fac = []  # the school's listed faculty: a co-adviser named in a students list is not a student
    for x in json.loads((P.CENSUS / f'{key}-faculty.json').read_text())['faculty'] + \
            (json.loads((P.CENSUS / f'{key}-additions.json').read_text()) if (P.CENSUS / f'{key}-additions.json').exists() else []):
        fac.append(Name([x['name']] + list(x.get('aliases') or [])))
    for pi, (t, urls) in targets_pages(key).items():
        N = Name([pi]); studs, seen = [], set()
        for u in urls:
            for cited, sha, h, year in stored_pages(c, u):
                try:
                    cands, _ = lpdom.member_candidates(h.encode('utf-8', 'replace'), u)
                except Exception:  # noqa: BLE001 (a page lpdom cannot linearise has no candidates)
                    continue
                flat = ' '.join(lpdom.collapse(x) for x in [re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)\b.*?</\1>', ' ', h, flags=re.S | re.I))])
                flat = ' '.join(__import__('html').unescape(flat).split())
                for path, name, rest, nxt, idx in cands:
                    role = lpdom.role_of(*(list(reversed(path)) + [rest]))
                    if role in ('phd', 'postdoc') and path and re.search(r'ph\.?\s?d|doctoral', path[-1], re.I) and re.search(r'post-?doc', path[-1], re.I):
                        role_out = 'member'  # 'Current PhD Students and Postdocs': the heading does not say which
                    else:
                        role_out = role
                    if role not in ('phd', 'postdoc') or not lpdom.looks_like_name(name) or not lpdom.plausible_person(name) \
                            or N.match(name) or len(toks(name)) < 2 or len(toks(name)) > 4 or any(F.match(name) for F in fac):
                        rep['dropped_not_a_student_name'] += 1; continue
                    alum = any(ALUM.search(x) for x in path)  # the section says it, not the person's line ('now Ph.D. student @ ...')
                    ys = lpdom.years_in(rest)
                    if alum and not ys:  # a graduate without a stated year cannot be placed in the window
                        rep['dropped_alumnus_without_year'] += 1; continue
                    years = [y for y in (ys or []) if y] or [year]
                    if max(years) < 2016:
                        rep['dropped_before_window'] += 1; continue
                    head = path[-1] if path else ''
                    j = flat.find(name)
                    i = flat.rfind(head, 0, j) if head and j >= 0 else -1
                    if j < 0 or i < 0 or j - i > 600:  # the quote must run from the section heading to the name
                        rep['dropped_no_heading_quote'] += 1; continue
                    q = flat[i:j + len(name)]
                    k = (' '.join(toks(name)), role)
                    if k in seen:
                        continue
                    seen.add(k)
                    studs.append(dict(name=name, role=role_out + ('_alumnus' if alum and role_out != 'member' else ''), years=[min(years), max(years)],
                                      years_basis='stated' if ys else 'capture_date', alumni=alum, section=' › '.join(path)[:200],
                                      url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cited), capture_url=cited if 'web.archive.org' in cited else None,
                                      sha256=sha, quote=q, auto=True))
        if studs:
            ev.append(dict(pi=pi, lab_site=t['urls'][0] if t['urls'] else None, people_page=studs[0]['url'], students=studs))
            rep['labs_with_students'] += 1; rep['students'] += len(studs)
        else:
            rep['labs_without'] += 1
    dfs = json.loads((P.HIERARCHY / key / 'defense-evidence.json').read_text()) if (P.HIERARCHY / key / 'defense-evidence.json').exists() else []
    by_pi = {e['pi']: e for e in ev}
    pis = {t['name']: Name([t['name']]) for t in PS.targets(key)}
    for d in dfs:
        hit = [pi for pi, N_ in pis.items() if N_.match(d['host'])]
        if len(hit) != 1 or not (2016 <= d['year'] <= 2026):
            rep['defense_host_not_one_pi'] += 1; continue
        e = by_pi.setdefault(hit[0], dict(pi=hit[0], lab_site=None, people_page=None, students=[]))
        if e not in ev:
            ev.append(e)
        e['students'].append(dict(name=d['student'], role='phd_alumnus', years=[d['year'], d['year']], years_basis='defense_date', alumni=True,
                                  section='dissertation defense announcement', url=d['url'], capture_url=d['capture_url'], sha256=d['sha256'],
                                  quote=d['quote'], host_quote=d['host_quote'], auto=True))
        rep['defense_students'] += 1
    (P.HIERARCHY / key / 'labpage-evidence.json').write_text(json.dumps(ev, indent=1, ensure_ascii=False))
    (P.HIERARCHY / key / 'labpage-students-report.json').write_text(json.dumps(dict(rep), indent=1))
    print(json.dumps(dict(rep)))


if __name__ == '__main__':
    {'links': links, 'defenses': defenses, 'extract': extract}[sys.argv[1]](sys.argv[2])
