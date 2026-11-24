"""Oxford ORA thesis records as a student source (the supervisor field of a DPhil record page).

list    pick the ORA theses of the local OpenAlex snapshot extension (ext-oxford, no API credit) in the computing-related fields -> a jsonl of DOIs
crawl   for each DOI: resolve https://doi.org/<doi> to its ORA object page (one request, redirect NOT followed, only an ora.ox.ac.uk/objects/ target
        is used), then fetch that page. At least DELAY seconds between requests of a host. Resumable: a stored page is never fetched twice.
parse   read the stored pages -> a json list: author, title, year, award, contributors (name, role, department, ORCID), url, sha256 of the stored bytes
evidence the parsed records -> thesis-evidence rows (R-STU-24): a record whose Supervisor contributor is exactly one Oxford PI (ORCID match, else family name + first initial unique among the PIs)
usage: ora_theses.py list|crawl|parse|evidence [--delay 3] [--limit N] [--fields ...]

Access: ora.ox.ac.uk/robots.txt is checked through school_web.robots_ok (the `*` group; no rule names an AI agent; no Crawl-delay; /objects/ pages are
allowed, the search and facet paths are not touched). doi.org serves no robots.txt (404). Generic User-Agent, no e-mail address.
Why not school_web.live: ORA record pages load Google's recaptcha script for the feedback form, which school_web's challenge pattern reads as a bot
challenge and would block the host. A record page is judged here by its own markers (an ORA record has `citation_title`); a page without them, or any
401/403/429/503, stops the crawl and nothing is worked around.
"""
import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
import time
import zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402

KEY = 'oxford'
FIELDS = ('Computer Science', 'Engineering', 'Mathematics', 'Decision Sciences')
UA = W.UA
COMP_DEPTS = {'Computer Science', 'Engineering Science', 'Statistics', 'Mathematical Institute', 'Mathematics', 'Internet Institute', 'Oxford Internet Institute',
              'Physics', 'Materials', 'Big Data Institute', 'Oxford e-Research Centre', 'Experimental Psychology', 'Statistical Science', 'Computing'}


def db():
    p = Path(P.HIERARCHY) / KEY / 'raw' / 'ora-theses.sqlite'
    c = sqlite3.connect(str(p), timeout=60)
    c.execute('create table if not exists rec (doi text primary key, url text, fetched_at text, status int, sha256 text, raw_zlib blob, note text)')
    c.execute('create table if not exists doi_hop (doi text primary key, fetched_at text, status int, location text)')
    return c


def snapshot_rows(fields):
    snap = Path(P.OA_SNAPSHOT) / 'current' / 'ext-oxford.sqlite'
    c = sqlite3.connect(f'file:{snap}?mode=ro', uri=True)
    for id_, doi, year, title, body in c.execute("select id, doi, year, title, body from works where type='dissertation' and year>=2015"):
        if not doi or '10.5287/ora-' not in doi:
            continue
        b = json.loads(body) if body[:1] == b'{' else json.loads(zlib.decompress(body))
        f = ((b.get('primary_topic') or {}).get('field') or {}).get('display_name')
        if f in fields:
            names = [a.get('raw_author_name') or (a.get('author') or {}).get('display_name') for a in (b.get('authorships') or [])]
            yield dict(openalex=id_, doi=doi.replace('https://doi.org/', ''), year=year, title=title, field=f, author_names=[n for n in names if n])


def cmd_list(a):
    rows = sorted(snapshot_rows(set(a.fields or FIELDS)), key=lambda r: (-(r['year'] or 0), r['doi']))
    Path(a.out).write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(len(rows), 'ORA theses ->', a.out)


def cmd_crawl(a):
    import requests
    c = db()
    wc = W.con(KEY)
    ok, delay = W.robots_ok(wc, 'https://ora.ox.ac.uk/objects/uuid:x')
    if not ok:
        raise SystemExit('ora.ox.ac.uk robots.txt does not allow /objects/ for this project: stop')
    delay = max(a.delay, delay)
    rows = [json.loads(x) for x in Path(a.todo).read_text().splitlines() if x.strip()]
    done = {r[0] for r in c.execute('select doi from rec where status=200')}
    n = 0
    last = 0.0
    for r in rows:
        doi = r['doi']
        if doi in done:
            continue
        hop = c.execute('select status, location from doi_hop where doi=?', (doi,)).fetchone()
        if hop is None:
            w = last + 1.0 - time.time()
            if w > 0:
                time.sleep(w)
            try:
                h = requests.get(f'https://doi.org/{doi}', headers={'User-Agent': UA}, timeout=60, allow_redirects=False)
                hop = (h.status_code, h.headers.get('Location'))
            except Exception as e:  # noqa: BLE001
                hop = (-1, repr(e)[:200])
            last = time.time()
            c.execute('insert or replace into doi_hop values (?,?,?,?)', (doi, time.strftime('%Y-%m-%dT%H:%M:%S'), hop[0], hop[1])); c.commit()
        loc = hop[1] or ''
        if hop[0] not in (301, 302, 303, 307, 308) or not re.match(r'https://ora\.ox\.ac\.uk/objects/uuid:[0-9a-f-]{36}$', loc):
            c.execute('insert or replace into rec values (?,?,?,?,?,?,?)', (doi, loc, time.strftime('%Y-%m-%dT%H:%M:%S'), 0, None, None, f'doi hop {hop[0]}'))
            c.commit()
            continue
        w = last + delay - time.time()
        if w > 0:
            time.sleep(w)
        try:
            g = requests.get(loc, headers={'User-Agent': UA}, timeout=60, allow_redirects=False)
            body, st = g.content, g.status_code
        except Exception as e:  # noqa: BLE001
            body, st = repr(e).encode(), -1
        last = time.time()
        note = ''
        if st == 200 and b'citation_title' not in body:
            st, note = 999, 'no record markers (not a record page)'
        c.execute('insert or replace into rec values (?,?,?,?,?,?,?)', (doi, loc, time.strftime('%Y-%m-%dT%H:%M:%S'), st, hashlib.sha256(body).hexdigest(), zlib.compress(body, 6), note))
        c.commit()
        n += 1
        if st != 200:
            print('stop: status', st, loc, note, flush=True)
            if st in (401, 403, 429, 503, 999, -1):
                return 3
        if n % 50 == 0:
            print(n, doi, flush=True)
        if a.limit and n >= a.limit:
            break
    print('fetched', n)
    return 0


def text_of(b):
    b = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', b, flags=re.S)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', b)).split())


def contributors(h):
    out = []
    for m in re.finditer(r'<span>\+ </span>\s*([^<]+?)\s*</a>(.*?)(?=<div style="padding-bottom:10px">|<script)', h, re.S):
        name, rest = m.group(1), m.group(2)
        d = dict(re.findall(r'<dt>([^<]+):</dt>\s*<dd>(.*?)</dd>', rest, re.S))
        d = {k: html.unescape(re.sub(r'<[^>]+>', '', v)).strip() for k, v in d.items()}
        out.append(dict(name=html.unescape(name), role=d.get('Role'), department=d.get('Department'), division=d.get('Division'), institution=d.get('Institution'),
                        orcid=(re.search(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', rest) or [None])[0]))
    return out


def cmd_parse(a):
    c = db()
    out = []
    for doi, url, sha, raw in c.execute('select doi, url, sha256, raw_zlib from rec where status=200'):
        h = zlib.decompress(raw).decode('utf-8', 'replace')
        t = text_of(h)
        # the contributors block sits between the Authors and Bibliographic Details headings
        i, j = h.find('>Authors<'), h.find('id="BibliographicDetails"')
        blocks = contributors(h[i:j] if 0 <= i < j else h)
        meta = lambda n: html.unescape((re.search(rf'<meta name="{n}" content="([^"]*)"', h) or [None, ''])[1])  # noqa: E731
        award = (re.search(r'Type of award:\s*(\S+)', t) or [None, ''])[1]
        holder = (re.search(r'Copyright holder:\s*(.+?)\s+Copyright date', t) or [None, ''])[1]
        out.append(dict(doi=doi, url=url, sha256=sha, author=meta('citation_author'), copyright_holder=holder, title=meta('citation_title'), year=meta('citation_date')[:4],
                        award=award, contributors=blocks, text_has_all=all(b['name'] in t for b in blocks)))
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(len(out), 'records ->', a.out)


def fold(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', s)
    return re.sub(r'[^a-z ]', '', ''.join(c for c in s if not unicodedata.combining(c)).lower().replace('-', ' ')).strip()


def pi_index(pis):
    """{family: [(first-initial, pi name, orcids)]} from pis.json: R-STU-03, an initials-only supervisor names a PI only when no other PI shares family name and initial."""
    idx = {}
    for p in pis:
        for nm in [p['pi']] + list(p.get('names') or []):
            t = fold(nm).split()
            if len(t) >= 2:
                idx.setdefault(t[-1], set()).add((t[0][0], p['pi']))
    orc = {o.replace('https://orcid.org/', ''): p['pi'] for p in pis for o in (p.get('orcid') or [])}
    return idx, orc


def supervisor_pi(contrib, idx, orc):
    if contrib.get('orcid') and contrib['orcid'] in orc:
        return orc[contrib['orcid']], 'orcid'
    m = re.match(r'\s*([^,]+),\s*(.+)$', contrib['name'])
    if not m:
        return None, 'unparsed'
    fam, giv = fold(m.group(1)).split(), fold(m.group(2)).split()
    if not fam or not giv:
        return None, 'unparsed'
    cands = {pi for ini, pi in idx.get(fam[-1], ()) if ini == giv[0][0]}
    if len(cands) == 1:
        return next(iter(cands)), 'family_initial'
    return None, 'ambiguous' if cands else 'no_pi'


def cmd_evidence(a):
    pis = json.loads(Path(a.pis).read_text())
    idx, orc = pi_index(pis)
    todo = {json.loads(x)['doi']: json.loads(x) for x in Path(a.todo).read_text().splitlines() if x.strip()}
    recs = json.loads(Path(a.parsed).read_text())
    out, cnt = {}, {}
    def bump(k):
        cnt[k] = cnt.get(k, 0) + 1
    for r in recs:
        bump('records')
        if r['award'] not in ('DPhil', 'MSc', 'MPhil', 'MEng'):
            bump('award_' + (r['award'] or 'none')); continue
        year = int(r['year']) if r['year'].isdigit() else None
        if not year or year < 2016:
            bump('before_window'); continue
        sups = [c for c in r['contributors'] if c['role'] == 'Supervisor']
        hit = [(c, *supervisor_pi(c, idx, orc)) for c in sups]
        names = (todo.get(r['doi']) or {}).get('author_names') or []
        afam = fold(r['author'].split(',')[0])
        ini = fold(r['author'].split(',')[1])[:1] if ',' in r['author'] else ''
        full = None
        holder = (r.get('copyright_holder') or '').strip()
        # 1. OpenAlex's own byline of the thesis, 'Family, Given' with the given name spelled out (more than an initial)
        for n_ in names:
            if ',' in n_:
                f_, g_ = n_.split(',', 1)
                if fold(f_) == afam and len(fold(g_).replace(' ', '')) > 1 and fold(g_)[:1] == ini:
                    full = f"{g_.strip()} {f_.strip()}"
                    break
        # 2. the record's copyright holder in natural order (family tokens all present, same first initial, more than an initial)
        if not full and holder and ',' not in holder and set(afam.split()) <= set(fold(holder).split()) and len(fold(holder).split()) >= 2 \
                and fold(holder)[:1] == ini:
            full = holder
        full_name = full
        if not full_name:
            bump('author_name_not_full'); continue
        auth_dept = next((c_.get('department') for c_ in r['contributors'] if c_['role'] == 'Author'), None)
        for c, pi, how in hit:
            if not pi:
                bump('supervisor_' + how); continue
            # namesake guard (R-STU-03 spirit): an initials match needs the supervisor's department (else the author's) to be a computing-related unit
            if how != 'orcid' and (c.get('department') or auth_dept) and (c.get('department') or auth_dept) not in COMP_DEPTS:
                bump('supervisor_dept_outside_computing'); continue
            t = text_of(zlib.decompress(db().execute('select raw_zlib from rec where doi=?', (r['doi'],)).fetchone()[0]).decode('utf-8', 'replace'))
            q = f"{c['name']} Institution: {c['institution']}" if c.get('institution') else f"{c['name']} Role: Supervisor"
            i = t.find(q)
            j = t.find('Role: Supervisor', i)
            quote = t[i:j + len('Role: Supervisor')] if i >= 0 and 0 <= j - i < 400 else ''
            if not quote:
                bump('quote_not_found'); continue
            out.setdefault(pi, {})[(full_name, year)] = dict(
                name=full_name, role='phd' if r['award'] == 'DPhil' else 'masters', years=[year, year], url=r['url'], sha256=r['sha256'], quote=quote,
                note=f"ORA {r['award']} thesis '{r['title']}' ({year}), doi {r['doi']}; contributor '{c['name']}' (role Supervisor; {c.get('department') or '?'}) = {pi} ({how}); author '{r['author']}' = {full_name}. R-STU-24")
            bump('rows')
    rows = [dict(pi=p, students=sorted(v.values(), key=lambda s: (s['years'][0], s['name'])), notes='ORA thesis records with an explicit Supervisor contributor (tools/ora_theses.py, R-STU-24).')
            for p, v in sorted(out.items())]
    Path(a.out).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    # the evidence pages go into the school's capture store (live table) so a hash check finds the bytes the quote came from
    wc, used = W.con(KEY), {s_['url'] for r_ in rows for s_ in r_['students']}
    d = db()
    for url, sha, raw, at in d.execute('select url, sha256, raw_zlib, fetched_at from rec where status=200'):
        if url in used:
            wc.execute('insert or replace into live values (?,?,?,?,?,?,?)', (url, at, 200, sha, 'text/html', raw, None))
    wc.commit()
    print(json.dumps(cnt), len(rows), 'PIs', len(used), 'pages stored in the capture store')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['list', 'crawl', 'parse', 'evidence'])
    ap.add_argument('--pis')
    ap.add_argument('--parsed')
    ap.add_argument('--out')
    ap.add_argument('--todo')
    ap.add_argument('--delay', type=float, default=3.0)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--fields', nargs='*')
    a = ap.parse_args()
    if a.cmd == 'list':
        cmd_list(a)
    elif a.cmd == 'crawl':
        sys.exit(cmd_crawl(a))
    elif a.cmd == 'evidence':
        cmd_evidence(a)
    else:
        cmd_parse(a)

