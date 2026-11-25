"""HKUST CSE 'Qualifying Exams, Proposal Defenses & Thesis Defenses' event pages as dated student-supervisor pairs (rule R-STU-29).

https://cse.hkust.edu.hk/pg/defenses/<season>/ (department's own pages; robots.txt allows them, no AI-agent rule) is a season index (Date / Candidate /
Title / Announcement type) linking one page per event. An event page reads `<PhD|MPhil> <Thesis Defence|Thesis Proposal Defence|Qualifying Examination>`,
`By <Mr./Miss/Dr. Given FAMILY>`, and `Committee Members: <Prof./Dr. Full Name> (Supervisor) / (Chairperson) / ...`. A candidate of a PhD event under a
named '(Supervisor)' is a PhD student of that supervisor in the year of the event.

seasons  fetch the season indexes (S/Summer/F of 2016-2026, stored in the school's capture store, 3 s apart) -> a todo json of event pages (PhD events only)
crawl    fetch the event pages of the todo json through school_web.live (robots honoured, >= 3 s per host, stored, resumable: a stored page is not fetched
         again); stops (exit 3) on a block, a challenge, a 401/403/429 or a burst of failures; nothing is worked around
evidence offline, from the stored captures only -> rows (thesis-evidence shape), a held list and counts

Admitted event: PhD qualifying / proposal / thesis event dated 2016-01-01 .. 2026 and not after the capture date (a future event is HELD); a spelled-out
candidate name (given name not an initial); a '(Supervisor)' line (also '(Co-supervisor)', '(Thesis Supervisor)') whose name matches EXACTLY ONE HKUST PI by
the build's full-name rule (pihier.names.Name; a name two PIs share is dropped). Chairperson and plain members are never supervisors. MPhil events are skipped.
One student under one PI = one row, years [first event year, last event year]. A PI with no period record (pis.json periods, reviewed/faculty-periods.json)
or an event year before the PI's period start is HELD, not a row (R-STU-26's period condition). Quotes are the verbatim candidate block and the verbatim
supervisor line of the page (two parts, each a substring of the page text).

usage: hkust_cse_defences.py seasons|crawl|evidence [--todo FILE] [--pis pis.json] [--periods faculty-periods.json] [--listing-window] [--out FILE] [--held FILE]
"""
import argparse
import html as H
import json
import re
import sys
import time
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import urljoin

import school_web as W  # noqa: E402
from pihier.names import Name  # noqa: E402

KEY = 'hkust'
RULE = 'R-STU-29'
BASE = 'https://cse.hkust.edu.hk/pg/defenses/'
WINDOW = (2016, 2026)
LISTING_NOW = 2026   # the year of the newest dated listing capture: a PI named in it has no end
DELAY = 3.0
KINDS = ('Thesis Defence', 'Thesis Proposal Defence', 'Qualifying Examination')
TITLE = re.compile(r'^(?:Dr|Prof|Professor|Mr|Miss|Ms|Mrs)\.?\s+', re.I)
SUP = re.compile(r'\((?:Thesis\s+)?(?:Co-?\s?)?[Ss]upervisor\)')
MONTHS = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'], 1)}


def season_slugs():
    out = []
    for y in range(WINDOW[0], WINDOW[1] + 1):
        yy = '%02d' % (y % 100)
        out += [f'S{yy}', f'Summer{yy}', f'F{yy}']
    return out


def text_lines(raw):
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', raw)
    t = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</tr>|</li>|</h\d>', '\n', t)
    t = H.unescape(re.sub(r'<!--.*?-->|<[^>]+>', ' ', t))
    return [re.sub(r'\s+', ' ', x).strip() for x in t.split('\n') if x.strip()]


def flat_text(raw):
    return ' '.join(text_lines(raw))


def parse_index(raw, url):
    """-> [dict(url, date 'YYYY-MM-DD', candidate, title, kind, degree)] of a season index page (rows with a link to an event page)."""
    out = []
    for tr in re.findall(r'<tr.*?</tr>', raw, re.S):
        a = re.search(r'href="([^"]+\.html)"', tr)
        cells = [re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', x))).strip() for x in re.findall(r'<td.*?</td>', tr, re.S)]
        if not a or len(cells) < 4:
            continue
        m = re.match(r'(\d{1,2}) (\w+) (\d{4})$', cells[0])
        k = re.match(r'(PhD|MPhil)\s+(.*)$', cells[3])
        if not (m and k and m.group(2) in MONTHS):
            continue
        out.append(dict(url=urljoin(url, a.group(1)), date='%s-%02d-%02d' % (m.group(3), MONTHS[m.group(2)], int(m.group(1))),
                        candidate=cells[1], title=cells[2], degree=k.group(1), kind=k.group(2)))
    return out


def parse_event(raw):
    """-> dict(kind, degree, candidate, supervisors[(name, line)], cand_quote) of one event page; None fields when absent."""
    lines = text_lines(raw)
    flat = ' '.join(lines)
    km = re.search(r'\b(PhD|MPhil)\s+(Thesis\s+Proposal\s+Defence|Thesis\s+Defence|Qualifying\s+Examination)', flat)
    cand, cq = None, None
    for i, ln in enumerate(lines):
        if re.fullmatch(r'[Bb]y:?', ln) and i + 1 < len(lines):
            cand, cq = lines[i + 1], f'{ln} {lines[i + 1]}'
            break
        m = re.match(r'[Bb]y:?\s+((?:Mr|Miss|Ms|Mrs|Dr)\.?\s+\S.*)$', ln)
        if m:
            cand, cq = m.group(1), ln
            break
    sups = []
    for ln in lines:
        if SUP.search(ln):
            for part in re.split(r'(?<=\))\s+(?=(?:Prof|Dr|Professor)\b)', ln):
                if SUP.search(part):
                    nm = re.sub(r'^Committee Members?:?\s*', '', SUP.split(part)[0]).strip(' ,;:')
                    sups.append((TITLE.sub('', nm).strip(), part.strip()))
    return dict(kind=re.sub(r'\s+', ' ', km.group(2)) if km else None, degree=km.group(1) if km else None, candidate=TITLE.sub('', cand).strip() if cand else None,
                cand_quote=cq, supervisors=sups, flat=flat)


def fold(s):
    return re.sub(r'[^a-z ]', '', unicodedata.normalize('NFKD', s).lower()).strip()


def spelled(name):
    toks = [t for t in re.split(r'[\s]+', name) if t]
    return len(toks) >= 2 and not all(len(t.rstrip('.')) <= 1 for t in toks[:-1]) and not re.fullmatch(r'[A-Z]\.?', toks[0])


def yr(v):
    m = re.match(r'(\d{4})', str(v or ''))
    return int(m.group(1)) if m else None


def listing_window(p):
    """-> [first, last-or-None] year range of a PI's dated department listings (pis.json `listings`), or None without any (2026-11-25).
    A PI with no period record is listed in the CSE faculty pages of its years: the first listing year is the earliest year the PI is dated at HKUST
    (2016 is the first capture, so a PI listed in 2016 started in or before it), and the PI is still here when the newest listing year (2026) names it;
    otherwise the last listing year closes the window (listing drop closes the period, owner 2026-11-02). Nothing is guessed beyond the listed years."""
    ys = sorted({int(l['year']) for l in p.get('listings') or [] if l.get('year')})
    if not ys:
        return None
    return [ys[0], None if ys[-1] >= LISTING_NOW else ys[-1]]


def period_index(pis, periods_file, by_listing=False):
    """-> {pi: [start_year or None, end_year or None] | None}: the period record of each PI (pis.json periods, else reviewed/faculty-periods.json by name,
    else, only with by_listing, the dated-listing window of listing_window)."""
    rev = {}
    for r in (json.load(open(periods_file)) if periods_file else []):
        rev.setdefault(r.get('name'), r)
    out = {}
    for p in pis:
        rec = None
        for q in p.get('periods') or []:
            rec = [yr(q.get('start')), yr(q.get('end'))]
            break
        if rec is None:
            r = rev.get(p['pi'])
            if r and r.get('facultyStart'):
                rec = [yr(r['facultyStart']), yr(r.get('facultyEnd'))]
        if rec is None and by_listing:
            rec = listing_window(p)
        out[p['pi']] = rec
    return out


def build(events, pis, periods_file=None, today=None, by_listing=False):
    """events: [dict(url, sha256, date, raw, fetched_at)] -> (rows, held, counts, unmatched). Offline: nothing is fetched."""
    idx = {p['pi']: Name(list(dict.fromkeys([p['pi']] + list(p.get('names') or [])))) for p in pis}
    per = period_index(pis, periods_file, by_listing)
    today = today or time.strftime('%Y-%m-%d')
    cnt = dict(events=0, not_phd_event=0, outside_window=0, future_held=0, no_candidate=0, name_not_spelled=0, no_supervisor=0, supervisor_no_pi=0,
               ambiguous=0, pairs=0, quote_missing=0)
    unmatched, got = {}, {}
    for ev in sorted(events, key=lambda e: (e['date'], e['url'])):
        cnt['events'] += 1
        pe = parse_event(ev['raw'])
        if pe['degree'] != 'PhD' or pe['kind'] is None or not any(pe['kind'].startswith(k) for k in KINDS):
            cnt['not_phd_event'] += 1
            continue
        y = int(ev['date'][:4])
        if not WINDOW[0] <= y <= WINDOW[1]:
            cnt['outside_window'] += 1
            continue
        if ev['date'] > today:
            cnt['future_held'] += 1
            continue
        if not pe['candidate']:
            cnt['no_candidate'] += 1
            continue
        if not spelled(pe['candidate']):
            cnt['name_not_spelled'] += 1
            continue
        if not pe['supervisors']:
            cnt['no_supervisor'] += 1
            continue
        for sname, sline in pe['supervisors']:
            ps = [p for p, nm in idx.items() if nm.match(sname)]
            if len(ps) > 1:
                cnt['ambiguous'] += 1
                unmatched.setdefault(sname, dict(n=0, why='ambiguous', pis=ps))['n'] += 1
                continue
            if not ps:
                cnt['supervisor_no_pi'] += 1
                unmatched.setdefault(sname, dict(n=0, why='no_pi'))['n'] += 1
                continue
            if pe['cand_quote'] not in pe['flat'] or sline not in pe['flat']:
                cnt['quote_missing'] += 1
                continue
            g = got.setdefault((ps[0], fold(pe['candidate'])), dict(name=pe['candidate'], pi=ps[0], events=[]))
            g['events'].append(dict(url=ev['url'], sha256=ev['sha256'], date=ev['date'], kind=f"{pe['degree']} {pe['kind']}", quote=f"{pe['cand_quote']} [...] {sline}",
                                    sup=sname, n_sup=len(pe['supervisors']), fetched_at=ev.get('fetched_at')))
            cnt['pairs'] += 1
    rows_by, held_by = {}, {}
    for (pi, _), g in got.items():
        evs = sorted(g['events'], key=lambda e: e['date'])
        rec = per.get(pi)
        why = None
        if by_listing and rec:
            # 2026-11-25: an event inside the PI's window dates the relation; events outside it are not evidence and are left out of the row (a student
            # defending after the PI's last listing year keeps the in-window qualifying / proposal events, years clipped to them)
            inside = [e for e in evs if (not rec[0] or int(e['date'][:4]) >= rec[0]) and (not rec[1] or int(e['date'][:4]) <= rec[1])]
            if inside:
                evs = inside
        years = [int(evs[0]['date'][:4]), int(evs[-1]['date'][:4])]
        prim = next((e for e in reversed(evs) if 'Thesis Defence' in e['kind']), evs[-1])
        s = dict(name=g['name'], role='phd', years=years, url=prim['url'], sha256=prim['sha256'], quote=prim['quote'],
                 note=f"HKUST CSE event pages ({', '.join(sorted({e['kind'] for e in evs}))}; {', '.join(e['date'] for e in evs)}): '(Supervisor)' {evs[0]['sup']}"
                      + (' (committee names more than one supervisor)' if any(e['n_sup'] > 1 for e in evs) else '') + f'. {RULE}',
                 other_sources=[dict(url=e['url'], sha256=e['sha256'], date=e['date'], kind=e['kind'], quote=e['quote']) for e in evs if e is not prim])
        if rec is None:
            why = 'no_period_record'
        elif rec[0] and years[0] < rec[0]:
            why = f'event_year_before_period_start_{rec[0]}'
        elif rec[1] and years[1] > rec[1]:
            why = f'event_year_after_period_end_{rec[1]}'
        (held_by if why else rows_by).setdefault(pi, []).append(dict(s, held_why=why) if why else s)
    mk = lambda d, n: [dict(pi=p, students=sorted(v, key=lambda x: (x['years'][0], x['name'])), notes=n) for p, v in sorted(d.items())]
    note = 'HKUST CSE qualifying/proposal/thesis event pages with a named (Supervisor) (tools/hkust_cse_defences.py, %s).' % RULE
    return mk(rows_by, note), mk(held_by, note + ' HELD: period condition.'), cnt, unmatched


# --- network steps (school_web: robots, per-host delay, challenge detection, the capture store) -------------------------------------------------------

def load_stored(c, url):
    r = c.execute('select status, sha256, raw_zlib, fetched_at from live where url=?', (url,)).fetchone()
    if r and r[0] == 200 and r[2]:
        return dict(sha256=r[1], raw=zlib.decompress(r[2]).decode('utf-8', 'replace'), fetched_at=r[3])
    return None


def cmd_seasons(a):
    c = W.con(KEY)
    seen = {}
    for slug in season_slugs():
        for url in [BASE + slug + '/']:
            r = W.live(c, url, min_delay=DELAY)
            if r is None:
                print('stop: blocked or robots', url)
                return 3
            if r[0] != 200:
                if r[0] in (401, 403, 429, 999):
                    print('stop: status', r[0], url)
                    return 3
                continue
            for e in parse_index(W.live_html(c, url), url):
                if e['degree'] == 'PhD' and e['kind'] in KINDS:
                    seen[e['url']] = dict(e, season=slug)
    todo = sorted(seen.values(), key=lambda e: (e['date'], e['url']))
    Path(a.out).write_text(json.dumps(todo, ensure_ascii=False, indent=1))
    print(len(todo), 'PhD event pages in the todo ->', a.out)
    return 0


def cmd_crawl(a):
    c = W.con(KEY)
    todo = json.load(open(a.todo))
    n = fails = 0
    t0 = time.time()
    for e in todo:
        if a.max_minutes and (time.time() - t0) / 60 > a.max_minutes:
            print('time budget reached; re-submit to continue')
            return 0
        if c.execute('select 1 from live where url=? and status=200', (e['url'],)).fetchone():
            continue
        r = W.live(c, e['url'], min_delay=DELAY)
        if r is None:
            print('stop: blocked or robots', e['url'])
            return 3
        n += 1
        if r[0] != 200:
            fails += 1
            print('status', r[0], e['url'], flush=True)
            if r[0] in (401, 403, 429, 999) or fails >= 10:
                print('stop: status', r[0], 'failures', fails)
                return 3
        if n % 100 == 0:
            print(n, 'fetched', e['date'], flush=True)
        if a.limit and n >= a.limit:
            break
    print('fetched', n, 'failures', fails)
    return 0


def cmd_evidence(a):
    c = W.con(KEY)
    todo = json.load(open(a.todo))
    events = []
    for e in todo:
        st = load_stored(c, e['url'])
        if st:
            events.append(dict(url=e['url'], date=e['date'], **st))
    rows, held, cnt, unmatched = build(events, json.load(open(a.pis)), a.periods, by_listing=a.listing_window)
    cnt['todo'], cnt['stored'] = len(todo), len(events)
    cnt['rows_pis'], cnt['rows_students'] = len(rows), sum(len(r['students']) for r in rows)
    cnt['held_pis'], cnt['held_students'] = len(held), sum(len(r['students']) for r in held)
    Path(a.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n')
    if a.held:
        Path(a.held).write_text(json.dumps(held, ensure_ascii=False, indent=1) + '\n')
    if a.unmatched:
        Path(a.unmatched).write_text(json.dumps(unmatched, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    print(json.dumps(cnt))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['seasons', 'crawl', 'evidence'])
    ap.add_argument('--todo')
    ap.add_argument('--pis')
    ap.add_argument('--periods')
    ap.add_argument('--out')
    ap.add_argument('--held')
    ap.add_argument('--listing-window', action='store_true', help='a PI without a period record gets its dated-listing window (listing_window), not a hold; events outside a window are left out of a row that has events inside it')
    ap.add_argument('--unmatched')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--max-minutes', type=float, default=0)
    a = ap.parse_args()
    sys.exit({'seasons': cmd_seasons, 'crawl': cmd_crawl, 'evidence': cmd_evidence}[a.cmd](a))


if __name__ == '__main__':
    main()
