"""A protocol school's faculty-listing captures -> one row per (person, listing capture): protocol stages 1-2.

Reads the plan the listings pipeline wrote (listings/<key>/captures.sqlite, table plan, status ok: one Wayback id_
capture per slot and half-year, listings/scripts/plan_fetch.py driven by the charter's [[departments.listings]]), parses
each capture with tools/listing_formats.py, and writes listings/<key>/rows.json.

row      name (given-first, as the page spells it), name_listed ('Last, First M.'), dept (the slot's department code),
         slot, kind (the slot's kind), year, observed (capture timestamp), titles (as listed), dept_title (the title lines
         that name the department, by the charter's [[departments]].title_match), rank (classified from dept_title, else
         from every title: emeritus | courtesy | adjunct | visiting | lecturer | research | teaching | ladder | other),
         homepage, capture_url, sha256 (of the capture body as stored), quote (the person's name through their last
         title, a substring of the capture's whitespace-collapsed text; never the contact lines)
coverage listings/<key>/coverage.json: department x year -> slots with an ok capture, and the plan's reason for each
         half-year without one (nocapture | unusable | out_of_scope)
usage: listing_rows.py <key>
"""
import collections, json, re, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import listing_formats as LF  # noqa: E402
from school_web import body as wb_body  # noqa: E402  (stored capture bytes, gunzipped)

RANKS = [('emeritus', r'emerit'), ('courtesy', r'courtesy|\baffiliate\s+faculty'), ('adjunct', r'\badjunct\b'), ('visiting', r'\bvisiting\b'),
         ('lecturer', r'\blecturer\b|\binstructor\b'), ('research', r'\bresearch\s+(?:scientist|investigator|professor|fellow|faculty)|\bresearch\s+assistant\s+professor'),
         ('teaching', r'\bteaching\s+professor|\bclinical\s+(?:assistant\s+|associate\s+)?professor|professor\s+of\s+(?:the\s+)?practice'),
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


def rank_of(titles):
    t = ' | '.join(titles)
    for r, rx in RANKS:
        if re.search(rx, t, re.I):
            return r
    return 'other'


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


def main(key):
    cfg = S.get(key)
    tm = {d['code']: re.compile(d.get('title_match') or r'.', re.I) for d in cfg.get('departments') or []}
    fmt_of = {s['slot']: s.get('format') for d in cfg.get('departments') or [] for s in d.get('listings') or []}
    kind_of = {s['slot']: s['kind'] for s in S.listing_slots(key)}
    db = P.data('listings-captures.sqlite', key)
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    rows, n = [], collections.Counter()
    cov = collections.defaultdict(lambda: collections.defaultdict(dict))
    for slot, dept, year, half, cap, status, reason in c.execute('select slot, dept, year, half, capture_url, status, reason from plan order by slot, year, half'):
        cov[dept][year][f'{slot} {half}'] = status if status == 'ok' else f'{status}: {reason}'
        if status != 'ok':
            continue
        raw, sha, txt, ts = c.execute('select raw_zlib, sha256, text, wayback_timestamp from captures where capture_url=?', (cap,)).fetchone()
        h = wb_body(raw).decode('utf-8', 'replace')  # gunzipped when Wayback served it gzip-encoded
        flat = ' '.join((txt or '').split())
        fmt, es = LF.parse(h, fmt_of.get(slot))
        n[f'captures_{fmt}'] += 1
        if not es:
            n['captures_without_entries'] += 1; print(json.dumps(dict(no_entries=cap, fmt=fmt)), flush=True)
        m = re.search(r'/web/(\d{14})id_/', cap); obs = m.group(1) if m else ts
        for e in es:
            q = quote_of(flat, e)
            if not q:
                n['entries_without_quote'] += 1; continue
            dt = [t for t in e['titles'] if tm.get(dept, re.compile('.')).search(t)]
            rows.append(dict(name=given_first(e['name_listed']), name_listed=e['name_listed'], dept=dept, slot=slot, kind=kind_of.get(slot), year=int(obs[:4]),
                             half=half, observed=obs, titles=e['titles'], dept_title=dt, rank=(rank_of(dt) if dt and rank_of(dt) != 'other' else rank_of(e['titles'])), division=e.get('division'),
                             homepage=e.get('homepage'), capture_url=cap, sha256=sha, quote=q))
            n['rows'] += 1
    out = P.data('rows.json', key)
    out.write_text(json.dumps(rows, indent=0, ensure_ascii=False))
    P.data_w('coverage.json', key).write_text(json.dumps({d: {str(y): v for y, v in sorted(ys.items())} for d, ys in cov.items()}, indent=1))
    people = collections.defaultdict(set)
    for r in rows:
        people[r['dept']].add(r['name'])
    print(json.dumps(dict(n, people={d: len(v) for d, v in people.items()}, out=str(out))))


if __name__ == '__main__':
    main(sys.argv[1])
