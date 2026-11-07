"""A protocol school's faculty-listing captures -> one row per (person, listing capture): protocol stages 1-2.

Reads the plan the listings pipeline wrote (listings/<key>/captures.sqlite, table plan, status ok: one Wayback id_
capture per slot and half-year, listings/scripts/plan_fetch.py driven by the charter's [[departments.listings]]), parses
each capture with tools/listing_formats.py, and writes listings/<key>/rows.json.
Reviewed live-listing-sources.json supplements the plan from saved school_web live pages, using their actual
fetch dates and URLs. A complete group must match its reviewed expected entry count; no archive URL is invented.

row      name (given-first, as the page spells it), name_listed ('Last, First M.'), dept (the slot's department code),
         slot, kind (the slot's kind), year, observed (capture timestamp), titles (as listed), dept_title (the title lines
         that name the department, by the charter's [[departments]].title_match), rank (classified from dept_title, else
         from every title: emeritus | courtesy | adjunct | visiting | lecturer | research | teaching | ladder | other),
         homepage, profile (the department's own profile page, when the listing links one instead of a homepage), capture_url, sha256 (of the capture body as stored), quote (the person's name through their last
         title, a substring of the capture's whitespace-collapsed text; never the contact lines)
coverage listings/<key>/coverage.json: department x year -> slots with an ok capture, and the plan's reason for each
         half-year without one (nocapture | unusable | out_of_scope)
usage: listing_rows.py <key>
"""
import collections, hashlib, json, re, sqlite3, sys, urllib.parse, zlib
from datetime import datetime

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import listing_formats as LF  # noqa: E402
from school_web import body as wb_body, extract as html_extract  # noqa: E402  (stored capture bytes, gunzipped)

RANKS = [('emeritus', r'emerit'), ('courtesy', r'courtesy|\baffiliate\s+faculty'), ('adjunct', r'\badjunct\b|\badjoint\b'), ('visiting', r'\bvisiting\b'),
         ('lecturer', r'\blecturer\b|\binstructor\b'), ('research', r'\bresearch\s+(?:scientist|investigator|professor|fellow|faculty)|\bresearch\s+assistant\s+professor'),
         ('teaching', r'\bteaching\s+professor|\binstructional\s+professor|\bclinical\s+(?:assistant\s+|associate\s+)?professor|professor\s+of\s+(?:the\s+)?practice'),
         ('ladder', r'\bprofessor\b')]
NOT_NAME = re.compile(r'\s*\((?:video|website|web|on leave|he/him|she/her|they/them)\)', re.I)  # page furniture after a name ('Mars, Jason (Video)')
SUFFIX = re.compile(r',?\s*\b(Jr|Sr|II|III|IV)\.?$')


def given_first(n):
    """'Ackerman, Mark S.' -> 'Mark S. Ackerman'; 'Smith, John, Jr.' -> 'John Smith Jr.'"""
    n = ' '.join(NOT_NAME.sub(' ', n).split()).strip(' ,')
    suf = SUFFIX.search(n)
    core = n[:suf.start()].strip(' ,') if suf else n
    if ',' in core:
        last, first = core.split(',', 1)
        core = f'{first.strip()} {last.strip()}'
    return core + (f' {suf.group(1)}.' if suf else '')


def rank_of(titles, extra=None):
    """The rank a title list reads as. `extra` = the charter's [census].rank_words ({rank = regex}): title words of one school that
    join the shared RANKS patterns for that rank (UChicago PROTOCOL-FRICTION 17, R3), so a new school never edits the shared table."""
    t = ' | '.join(titles)
    if re.search(r'\b(?:incoming|future)\s+(?:\w+\s+){0,5}professor\b', t, re.I):
        return 'other'  # an announced future appointment is not a dated faculty appointment
    for r, rx in RANKS:
        if extra and extra.get(r):
            rx = f'(?:{rx})|(?:{extra[r]})'
        if re.search(rx, t, re.I):
            return r
    return 'other'


def listing_rank(titles, dept_titles, kind=None, extra=None):
    """Classify the written titles, retaining a listing's explicit courtesy-appointment context."""
    rank = rank_of(dept_titles, extra) if dept_titles else 'other'
    if rank == 'other':
        rank = rank_of(titles, extra)
    return 'courtesy' if kind == 'courtesy' and rank == 'ladder' else rank


def quote_of(flat, e):
    i = flat.find(e['name_listed'])
    if i < 0:
        return None
    end = i + len(e['name_listed'])
    for t in e['titles']:
        j = flat.find(t, end)
        if j >= 0 and j - end < 400:
            end = j + len(t)
    return flat[i:end]


def live_listing_rows(key, cfg, rw, tm, title_filters, kind_of):
    """Import reviewed saved live pages; dates and hashes come from the raw store, never the wall clock.

    sources: [{dept, slot, format?, complete, expected_entries, pages: [{url, sha256, fetched_at?}]}].
    A group explicitly reviews all pages of one listing. Incomplete groups supply sourced person rows, but
    never an ok coverage entry. This reads cached bytes only and does not fetch or create archive plan rows.
    """
    manifest = P.data('live-listing-sources.json', key)
    rows, n, coverage = [], collections.Counter(), []
    if not manifest.exists():
        return rows, n, coverage
    sources = json.loads(manifest.read_text())['sources']
    slots = {(d['code'], s['slot']) for d in cfg.get('departments') or [] for s in d.get('listings') or []}
    db = P.data('school-captures.sqlite', key)
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as c:
        for source in sources:
            dept, slot = source['dept'], source['slot']
            if (dept, slot) not in slots:
                raise ValueError(f'live listing names an unknown department/slot: {dept}/{slot}')
            if not source.get('pages'):
                raise ValueError(f'live listing has no reviewed pages: {slot}')
            complete = source.get('complete') is True
            expected = source.get('expected_entries')
            if complete and (type(expected) is not int or expected < 1):
                raise ValueError(f'complete live listing needs a positive expected_entries: {slot}')
            def normalized(url):
                parsed = urllib.parse.urlsplit(url)
                query = urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)))
                return parsed._replace(query=query, fragment='').geturl()
            reviewed_urls = {normalized(p['url']) for p in source['pages']}
            group_rows, buckets = [], set()
            for page in source['pages']:
                url = page['url']
                cached = c.execute('select fetched_at,status,sha256,raw_zlib,content_type from live where url=?', (url,)).fetchone()
                if not cached or cached[1] != 200 or not cached[3]:
                    raise ValueError(f'live listing lacks a saved HTTP 200 body: {url}')
                fetched, _, sha, raw, ct = cached
                data = zlib.decompress(raw)
                if page['sha256'] != sha or hashlib.sha256(data).hexdigest() != sha:
                    raise ValueError(f'live listing hash mismatch: {url}')
                if page.get('fetched_at', fetched) != fetched:
                    raise ValueError(f'live listing fetch date mismatch: {url}')
                observed = datetime.fromisoformat(fetched.replace('Z', '+00:00'))
                year, half = observed.year, ('H1' if observed.month <= 6 else 'H2')
                buckets.add((year, half))
                html = data.decode('utf-8', 'replace')
                missing = {normalized(u) for u in LF.page_links(html, url).values()} - reviewed_urls
                if complete and missing:
                    raise ValueError(f'complete live listing has unreviewed linked pages: {slot}: {sorted(missing)}')
                fmt, entries = LF.parse(html, source.get('format'))
                flat = ' '.join(' '.join(t for _, t in html_extract.blocks(data, ct, url)).split())
                n[f'live_captures_{fmt}'] += 1
                for entry in entries:
                    if slot in title_filters and not any(title_filters[slot].search(t) for t in entry['titles']):
                        n['entries_outside_title_filter'] += 1
                        continue
                    quote = quote_of(flat, entry)
                    if not quote:
                        n['entries_without_quote'] += 1
                        continue
                    titles = entry['titles']
                    dt = [t for t in titles if tm[dept].search(t)]
                    links = {f: urllib.parse.urljoin(url, entry[f]) for f in ('homepage', 'profile') if entry.get(f)}
                    group_rows.append(dict(name=given_first(entry['name_listed']), name_listed=entry['name_listed'], dept=dept,
                                           slot=slot, kind=kind_of[slot], year=year, half=half, observed=observed.strftime('%Y%m%d%H%M%S'),
                                           titles=titles, dept_title=dt, rank=listing_rank(titles, dt, kind_of[slot], rw), division=entry.get('division'),
                                           homepage=links.pop('homepage', None), **links, capture_url=url, sha256=sha, quote=quote,
                                           source_kind='live', fetched_at=fetched))
            if len(buckets) != 1:
                raise ValueError(f'live listing pages must belong to one observed half-year: {slot}')
            if expected is not None and len(group_rows) != expected:
                raise ValueError(f'live listing entry count mismatch for {slot}: reviewed {expected}, parsed {len(group_rows)}')
            year, half = next(iter(buckets))
            coverage.append((dept, year, f'{slot} live {half}', 'ok' if complete else 'partial: reviewed live listing is incomplete'))
            rows.extend(group_rows)
            n['live_rows'] += len(group_rows)
    return rows, n, coverage


def main(key):
    cfg = S.get(key)
    rw = (cfg.get('census') or {}).get('rank_words') or {}
    tm = {d['code']: re.compile(d.get('title_match') or r'.', re.I) for d in cfg.get('departments') or []}
    eras = [(s['slot'], s.get('from') or '0', s.get('to') or '9', s.get('format')) for d in cfg.get('departments') or [] for s in d.get('listings') or []]
    title_filters = {s['slot']: re.compile(s['title_filter'], re.I) for d in cfg.get('departments') or [] for s in d.get('listings') or [] if s.get('title_filter')}
    kind_of = {s['slot']: s['kind'] for s in S.listing_slots(key)}
    db = P.data('listings-captures.sqlite', key)
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True) if db.exists() else None
    has_pages = bool(c and c.execute("select 1 from sqlite_master where name='plan_pages'").fetchone())
    rows, n = [], collections.Counter()
    cov = collections.defaultdict(lambda: collections.defaultdict(dict))
    has_plan = bool(c and c.execute("select 1 from sqlite_master where name='plan'").fetchone())
    plan = c.execute('select slot, dept, year, half, capture_url, status, reason from plan order by slot, year, half') if has_plan else []
    for slot, dept, year, half, cap, status, reason in plan:
        cov[dept][year][f'{slot} {half}'] = status if status == 'ok' else f'{status}: {reason}'
        if status != 'ok':
            continue
        # a paged directory (R3, Georgia Tech friction 10) is one listing: the plan row's capture is page 0, plan_pages holds the other pages' captures
        pages = [r[0] for r in c.execute('select capture_url from plan_pages where slot=? and year=? and half=? order by page', (slot, year, half))] if has_pages else []
        for cap in [cap] + pages:
            raw, sha, txt, ts = c.execute('select raw_zlib, sha256, text, wayback_timestamp from captures where capture_url=?', (cap,)).fetchone()
            h = wb_body(raw).decode('utf-8', 'replace')  # gunzipped when Wayback served it gzip-encoded
            flat = ' '.join((txt or '').split())
            m = re.search(r'/web/(\d{14})id_/', cap); obs = m.group(1) if m else ts
            # one slot can have several URL eras with different page formats: the era that holds the capture date names the format; a named
            # format that finds nobody falls back to detection (era boundaries overlap; UChicago friction #13: the last era's format won for the whole slot)
            named = [f for sl, a, b, f in eras if sl == slot and f and a <= obs[:8] <= b]
            fmt, es = LF.parse(h, named[0] if named else None)
            if not es and named:
                fmt, es = LF.parse(h)
            n[f'captures_{fmt}'] += 1
            if LF.is_paged(h) and es and not pages:
                # a paged directory: this capture holds one page of several (UChicago CS 2017: 5 of ~45 people); the next pages may not be archived
                n['captures_paged'] += 1; print(json.dumps(dict(paged_listing=cap, entries=len(es))), flush=True)
            if not es:
                n['captures_without_entries'] += 1; print(json.dumps(dict(no_entries=cap, fmt=fmt)), flush=True)
            for e in es:
                # A school-wide listing can supply one department's rows without
                # making every other discipline ladder faculty in that department.
                # Filter here, after capture usability and all-page completeness.
                if slot in title_filters and not any(title_filters[slot].search(t) for t in e['titles']):
                    n['entries_outside_title_filter'] += 1
                    continue
                q = quote_of(flat, e)
                if not q:
                    n['entries_without_quote'] += 1; continue
                dt = [t for t in e['titles'] if tm.get(dept, re.compile('.')).search(t)]
                rows.append(dict(name=given_first(e['name_listed']), name_listed=e['name_listed'], dept=dept, slot=slot, kind=kind_of.get(slot), year=int(obs[:4]),
                                 half=half, observed=obs, titles=e['titles'], dept_title=dt, rank=listing_rank(e['titles'], dt, kind_of.get(slot), rw), division=e.get('division'),
                                 homepage=e.get('homepage'), **({'profile': e['profile']} if e.get('profile') else {}), capture_url=cap, sha256=sha, quote=q))
                n['rows'] += 1
    if c:
        c.close()
    live, live_counts, live_coverage = live_listing_rows(key, cfg, rw, tm, title_filters, kind_of)
    rows.extend(live)
    n.update(live_counts)
    n['rows'] += len(live)
    for dept, year, slot, status in live_coverage:
        cov[dept][year][slot] = status
    out = P.data('rows.json', key)
    out.parent.mkdir(parents=True, exist_ok=True)  # listings/<key>/derived does not exist for a new school (UChicago friction #12)
    out.write_text(json.dumps(rows, indent=0, ensure_ascii=False))
    P.data_w('coverage.json', key).write_text(json.dumps({d: {str(y): v for y, v in sorted(ys.items())} for d, ys in cov.items()}, indent=1))
    people = collections.defaultdict(set)
    for r in rows:
        people[r['dept']].add(r['name'])
    print(json.dumps(dict(n, people={d: len(v) for d, v in people.items()}, out=str(out))))


if __name__ == '__main__':
    main(sys.argv[1])
