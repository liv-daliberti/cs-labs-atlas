"""Student-RECALL (completeness) check: a stage-6 gate item for every school (owner directive 2026-11-11, "we need to do better here").

Stage 6 used to pass with many students missing: the lab-page students acceptance measures PRECISION of the rows that exist (docs/LAB-PAGES.md),
and the chain audit's students check only asks that a PI has >= 1 student. This tool measures whether the students are all there.

  (A) metrics      computed from derived data on every run, no network: rows, people, PIs with students / current PhD students, students per PI,
                   member-list source mix, role mix, withheld roles, boilerplate reasons                       -> student_recall.py report <key>
  (B) hand record  hierarchy/<key>/reviewed/student-recall-check.json: a SEEDED, STRATIFIED sample of PIs drawn after the last rebuild and bound to
                   the sha256 of students.json and pis.json (a rebuild or rule change invalidates it, like the stage-9 draw). For each sampled PI the
                   checker opens the PI's member-list page, stores the capture (student-recall-captures.sqlite), lists the names ACTUALLY on it
                   and gives a verdict: readable | unverifiable (+ reason class). The TOOL compares those names with students.json and computes
                   recall; the checker never writes "recorded". A fresh reviewer (not the drawer, not the filler) signs off.
  (C) gate items   stage_gate.g6 appends gate_items(key): record exists and is bound to the build; strict recall on readable PIs >= R1; unverifiable
                   share of the sample <= U (a school cannot pass by having unreadable pages); PIs with no recorded student and no researched
                   reason <= Z of all PIs; estimated whole-school current-PhD recall (unverifiable PIs count as recall 0) >= R2.

Strict rule kept (owner): a listed name counts only when it is DATED (a year in the window) or sits in a CURRENT-members section of the page; undated
names elsewhere stay excluded and are reported as `undated_excluded`. Nothing here relabels: unverifiable stays unverifiable.

usage: student_recall.py report <key> [--json]            metrics (A) and the gate items as they stand today
       student_recall.py draw <key> [--seed N] [--drawn-by NAME] [--force]    write the sample skeleton (B)
       student_recall.py capture <key> <pi> <url> [--file PATH]   store the member-list page of a sampled PI (polite single fetch: robots incl. the
                                                       Claude agent groups, >= 3 s, stops at a challenge; or --file with a page you already hold)
       student_recall.py text <key> <url>                  print a stored capture as readable text lines (for the checker)
       student_recall.py check <key>                       recompute recall from the filled record, validate bindings and captures; exit 1 on a finding
"""
import collections
import datetime
import hashlib
import html
import json
import random
import re
import sqlite3
import statistics
import sys
import time
import unicodedata
import zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402

# ---- THE THRESHOLDS: every number the gate uses lives here, and nowhere else (owner adjusts them) --------------------------------------------
THRESHOLDS = dict(
    R1=0.90,   # strict recall on the READABLE sampled PIs (names listed on the page and placeable, found in students.json), stratum-weighted
    U=0.30,    # (owner wants 0.20 after the first round of discovery fixes) max share of the sample that may be unverifiable (no member-list page, robots, challenge, login, unreachable ...)
    R2=0.60,   # (owner wants 0.70 after the first round) estimated whole-school CURRENT PhD recall; unverifiable PIs count as recall 0. BOUNDED: R2 <= (1-U) x R1 = 0.63 at these values
    Z=0.05,    # max share of ALL PIs with no recorded student and no researched (non-boilerplate, >= 2 sources) reason
    X=0.20,    # max share of listed names the checker may exclude with a reason (guard against excluding the misses)
)
# Coherence: with unverifiable PIs at recall 0, R2 can never exceed (1-U) x R1, so R2 must stay below that ceiling (0.63 at U .30, R1 .90).
SAMPLE_SIZE = 30                     # PIs per school
STRATA = (('0', 0, 0), ('1-2', 1, 2), ('3+', 3, None))   # by number of recorded student rows: name, lo, hi
CURRENT_FROM_YEAR = 2025             # a PhD row/name is CURRENT with a year >= this (the window ends 2026; the data were collected 2026-10/11)
WINDOW = (2016, 2026)                # a dated name must have a year in the window to be placeable
BOOTSTRAP_REPS, BOOTSTRAP_SEED = 1000, 20261111
MIN_SOURCES_FOR_REASON = 2           # a researched reason names at least this many sources checked (the onboarding trap's rule)
SCHEMA = 1

UNVERIFIABLE_REASONS = {
    'no_member_list_page': 'the PI has no lab or homepage page that lists members (a real search was done)',
    'robots_disallowed': 'robots.txt (or a Claude-agent group) disallows the page',
    'bot_challenge': 'the page serves a bot challenge',
    'login_required': 'the member list is behind a login',
    'js_not_renderable': 'the list is built by JavaScript that no allowed render shows',
    'page_unreachable': 'the page does not load (dead host, 4xx/5xx)',
    'list_not_current': 'the page lists members but states no date and no current section',
}
EXCLUDE_REASONS = ('not_a_person', 'co_advised_elsewhere', 'rotation_or_highschool', 'outside_school', 'is_the_pi')
SECTIONS = ('current', 'alumni', 'other')

BOILERPLATE = 'No student of this PI in any allowed source checked'   # tools/onboarding_traps.BOILERPLATE (kept literal: no import cycle with stage_gate)


# ---- data access ------------------------------------------------------------------------------------------------------------------------------
def _read(p, default=None):
    p = Path(p)
    try:
        return json.loads(p.read_text()) if p.exists() else default
    except ValueError:
        return default


def sha_file(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _pis(key):
    d = _read(P.data('pis.json', key), [])
    return d if isinstance(d, list) else d.get('pis', [])


def _students(key):
    return _read(P.data('students.json', key), {}) or {}


def _audit(key):
    import gzip
    p = Path(P.data('labpage-audit.jsonl.gz', key))
    if not p.exists():
        return {}
    out = {}
    with gzip.open(p, 'rt') as f:
        for line in f:
            r = json.loads(line)
            out[r['pi']] = r
    return out


def _reasons(key):
    return _read(P.data('lab-coverage-reasons.json', key), {}) or {}


def bindings(key):
    return {'students.json': sha_file(P.data('students.json', key)), 'pis.json': sha_file(P.data('pis.json', key))}


# ---- classification ---------------------------------------------------------------------------------------------------------------------------
def role_class(row):
    """alumni | postdoc | phd | masters | undergrad | visiting | student_unspecified | member_other, from the row's roles and relation roles."""
    x = ' '.join(list(row.get('roles') or []) + [str(rel.get('role') or '') for rel in row.get('relations') or []]).lower()
    if 'alumn' in x:
        return 'alumni'
    if 'postdoc' in x:
        return 'postdoc'
    if re.search(r'phd|doctoral|doctor|dissertation|graduate_student', x):
        return 'phd'
    if re.search(r'master|meng|mphil|\bsm\b', x):
        return 'masters'
    if 'undergrad' in x:
        return 'undergrad'
    if 'visit' in x:
        return 'visiting'
    if 'student' in x or 'graduate' in x:
        return 'student_unspecified'
    return 'member_other'


THESIS_URL = re.compile(r'dspace|purl\.stanford|searchworks|proquest|thesis|dissertation|etd|escholarship|techrpts|kilthub|repository|handle\.net', re.I)
PROFILE_URL = re.compile(r'profiles?\.|/profile|/people/|/person/|/faculty/|bair_people|listing', re.I)


def source_class(row):
    """The row's best member evidence: member_list (a lab/PI page) > profile > thesis."""
    classes = set()
    for rel in row.get('relations') or []:
        t = rel.get('type') or ''
        for s in (rel.get('sources') or [{}])[:3]:
            u = (s.get('url') or '') + ' ' + (s.get('kind') or '')
            if t in ('academic_advising', 'thesis_adviser') or THESIS_URL.search(u):
                classes.add('thesis')
            elif t == 'pi_basis_advising':
                classes.add('profile')
            elif PROFILE_URL.search(u) and t != 'direct_lab_membership':
                classes.add('profile')
            else:
                classes.add('member_list')
    return classes


def max_year(row):
    ys = [y for rel in row.get('relations') or [] for y in rel.get('years') or [] if isinstance(y, int)]
    return max(ys) if ys else None


def withheld(row):
    return any(rel.get('role_withheld') for rel in row.get('relations') or []) or role_class(row) == 'member_other' and not row.get('roles')


def is_current_phd(row):
    return role_class(row) == 'phd' and (max_year(row) or 0) >= CURRENT_FROM_YEAR


def is_current_phd_undated(row):
    return role_class(row) == 'phd' and max_year(row) is None and 'member_list' in source_class(row)


def stratum_of(n):
    for name, lo, hi in STRATA:
        if n >= lo and (hi is None or n <= hi):
            return name


# ---- names ------------------------------------------------------------------------------------------------------------------------------------
def _fold(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


def name_tokens(s):
    t = re.sub(r'[^a-z ]', ' ', _fold(re.sub(r'\([^)]*\)', ' ', s or ''))).split()
    return t


def name_match(a, b):
    """The same person under spelling variants: equal token sets; or equal last token and compatible first (equal, or one an initial/prefix of the
    other); a name with no Latin letters (CJK) matches only by its whitespace-free form."""
    ta, tb = name_tokens(a), name_tokens(b)
    if len(ta) < 2 or len(tb) < 2:
        ra, rb = re.sub(r'\s+', '', a or ''), re.sub(r'\s+', '', b or '')
        return bool(ra) and ra == rb and not (ta and tb)
    if set(ta) == set(tb):
        return True
    return ta[-1] == tb[-1] and (ta[0] == tb[0] or ta[0].startswith(tb[0]) and len(tb[0]) <= 2 or tb[0].startswith(ta[0]) and len(ta[0]) <= 2)


def recorded_names(rows):
    out = []
    for r in rows:
        out.append(r.get('name') or '')
        out += list(r.get('aliases') or [])
    return [n for n in out if n]


def is_recorded(name, rows):
    return any(name_match(name, n) for n in recorded_names(rows))


# ---- (A) metrics ------------------------------------------------------------------------------------------------------------------------------
def _quart(xs):
    if len(xs) < 2:
        return [xs[0]] * 3 if xs else [None] * 3
    return [round(q, 1) for q in statistics.quantiles(xs, n=4, method='inclusive')]


def researched_reason(reasons, pi):
    """A non-boilerplate students reason that names >= MIN_SOURCES_FOR_REASON sources (the onboarding trap's standard)."""
    s = (reasons.get(pi) or {}).get('students') or {}
    why = str(s.get('why') or '')
    return bool(s and why and not why.startswith(BOILERPLATE) and len(s.get('sources_checked') or []) >= MIN_SOURCES_FOR_REASON)


def metrics(key):
    """Every school-level number of (A), from derived data only. None-safe for schools without an audit."""
    pis, st, audit, reasons = _pis(key), _students(key), _audit(key), _reasons(key)
    names = [p['pi'] for p in pis]
    n = len(names)
    per = [len(st.get(p, [])) for p in names]
    rows = [r for p in names for r in st.get(p, [])]
    role_mix = collections.Counter(role_class(r) for r in rows)
    cur = {p: sum(1 for r in st.get(p, []) if is_current_phd(r)) for p in names}
    cur_u = {p: sum(1 for r in st.get(p, []) if is_current_phd_undated(r)) for p in names}
    src = collections.Counter()
    for p in names:
        rs = st.get(p, [])
        classes = set().union(*[source_class(r) for r in rs]) if rs else set()
        audited = (audit.get(p) or {}).get('students', {}).get('page_status') == 'audited'
        src['member_list' if audited or 'member_list' in classes else 'profile_only' if 'profile' in classes else 'thesis_only' if classes else 'none'] += 1
    boiler = sum(1 for p in names if str(((reasons.get(p) or {}).get('students') or {}).get('why') or '').startswith(BOILERPLATE))
    zero = [p for p in names if not st.get(p)]
    zero_unreasoned = [p for p in zero if not researched_reason(reasons, p)]
    m = dict(
        school=key, pis=n, rows=len(rows), distinct_people=len({r.get('person') or r.get('name') for r in rows}),
        pis_with_student=n - len(zero), pis_with_current_phd=sum(1 for p in names if cur[p]),
        pis_with_current_phd_incl_undated=sum(1 for p in names if cur[p] or cur_u[p]),
        current_phd_rows=sum(cur.values()), current_phd_undated_listed_rows=sum(cur_u.values()),
        per_pi_median=statistics.median(per) if per else None, per_pi_mean=round(sum(per) / n, 1) if n else None, per_pi_quartiles=_quart(per),
        per_pi_zero=len(zero), per_pi_1_2=sum(1 for x in per if 1 <= x <= 2), per_pi_3plus=sum(1 for x in per if x >= 3),
        source_mix=dict(src), source_share={k: round(v / n, 3) for k, v in src.items()} if n else {},
        role_mix=dict(role_mix), withheld_row_share=round(sum(1 for r in rows if withheld(r)) / len(rows), 3) if rows else None,
        boilerplate_reason_pis=boiler, boilerplate_share=round(boiler / n, 3) if n else None,
        zero_recorded_pis=len(zero), zero_recorded_unreasoned=len(zero_unreasoned),
        zero_recorded_unreasoned_share=round(len(zero_unreasoned) / n, 3) if n else None,
        audit_present=bool(audit),
    )
    m['audit_proxy'] = audit_proxy(names, st, audit)
    return m


def audit_proxy(names, st, audit):
    """INDICATIVE only (not the gate): the lab-page audit lists the names on each PI's captured people page; recall of the current PhD names among
    them against students.json, counting only names DATED >= CURRENT_FROM_YEAR (strict rule). Covers only the PIs whose page was read (page_status audited); the others are the unverifiable part."""
    if not audit:
        return None
    L = K = L2 = K2 = n_aud = undated = 0
    for p in names:
        a = (audit.get(p) or {}).get('students') or {}
        if a.get('page_status') != 'audited':
            continue
        n_aud += 1
        for e in a.get('listed_current') or []:
            if role_class({'roles': [e.get('role') or '']}) != 'phd':
                continue
            ys = [y for y in e.get('years') or [] if isinstance(y, int)]
            if not ys:
                undated += 1   # the strict rule: an undated name is not counted in `recall`; `recall_incl_undated` counts it (a looser, noisier reading)
                L2 += 1
                K2 += is_recorded(e.get('name') or '', st.get(p, []))
                continue
            if max(ys) < CURRENT_FROM_YEAR:
                continue
            L += 1
            hit = is_recorded(e.get('name') or '', st.get(p, []))
            K += hit
            L2 += 1
            K2 += hit
    return dict(audited_pis=n_aud, audited_share=round(n_aud / len(names), 3) if names else None, listed_current_phd_dated=L, recorded=K, undated_phd_names_not_counted=undated, recall_incl_undated=round(K2 / L2, 3) if L2 else None,
                recall=round(K / L, 3) if L else None, recall_times_audited_share=round(K / L * n_aud / len(names), 3) if L and names else None)


# ---- (B) the draw -----------------------------------------------------------------------------------------------------------------------------
def default_seed(binds):
    return int(hashlib.sha256(json.dumps(binds, sort_keys=True).encode()).hexdigest()[:8], 16)


def allocate(sizes, total=SAMPLE_SIZE):
    """Equal split over the strata, a small stratum taken whole and its unused share given to the larger ones (largest first)."""
    alloc = {k: 0 for k in sizes}
    left = min(total, sum(sizes.values()))
    open_ = [k for k in sizes if sizes[k]]
    while left > 0 and open_:
        share = max(1, left // len(open_))
        for k in list(open_):
            take = min(share, sizes[k] - alloc[k], left)
            alloc[k] += take
            left -= take
            if alloc[k] >= sizes[k]:
                open_.remove(k)
            if left <= 0:
                break
    return alloc


def draw_sample(pis, st, seed, total=SAMPLE_SIZE):
    """-> (picks {stratum: [pi names]}, sizes {stratum: N}). Pure and deterministic: check() redraws it from the record's seed."""
    strata = {name: [] for name, _, _ in STRATA}
    for p in sorted(pis):
        strata[stratum_of(len(st.get(p, [])))].append(p)
    sizes = {k: len(v) for k, v in strata.items()}
    rnd = random.Random(seed)
    alloc = allocate(sizes, total)
    return {k: sorted(rnd.sample(v, alloc[k])) for k, v in strata.items()}, sizes


def candidate_urls(key, pi, pis_by, st, audit):
    """Where the PI's member list may be: the audit's lab-page URLs, the pages its student rows came from (non-thesis), the PI's lab URL."""
    out, seen = [], set()

    def add(u, why):
        if u and u not in seen and u.startswith('http'):
            seen.add(u)
            out.append(dict(url=u, source=why))
    a = audit.get(pi) or {}
    for k, u in ((a.get('lab_page') or {}).get('urls') or {}).items():
        add(u, f'audit lab_page.{k}')
    for u in (a.get('students') or {}).get('pages') or []:
        add(u, 'audit students.pages')
    for r in st.get(pi, []):
        for rel in r.get('relations') or []:
            if (rel.get('type') or '') in ('academic_advising', 'thesis_adviser'):
                continue
            for s in (rel.get('sources') or [])[:1]:
                if not THESIS_URL.search(s.get('url') or ''):
                    add(s.get('url'), 'student row source')
    add(((pis_by.get(pi) or {}).get('lab') or {}).get('url'), 'pis.json lab.url')
    return out[:8]


def draw(key, seed=None, drawn_by=None, force=False, now=None):
    pis, st, audit = _pis(key), _students(key), _audit(key)
    binds = bindings(key)
    if not all(binds.values()):
        raise SystemExit(f'{key}: students.json / pis.json missing; nothing to draw from')
    seed = default_seed(binds) if seed is None else int(seed)
    picks, sizes = draw_sample([p['pi'] for p in pis], st, seed)
    by = {p['pi']: p for p in pis}
    out_p = Path(P.data_w('student-recall-check.json', key))
    prev = _read(out_p)
    if prev and not force and prev.get('binds') == binds:
        raise SystemExit(f'{out_p} is already a draw on this build (seed {prev.get("seed")}); --force archives it and redraws (use --seed for a new sample)')
    if prev and force:
        out_p.rename(out_p.with_name(f'student-recall-check.{(prev.get("drawn_at") or "old")[:19].replace(":", "")}.json'))
    when = (now or datetime.datetime.now(datetime.timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
    rec = dict(schema=SCHEMA, school=key, drawn_at=when, drawn_by=drawn_by or '', seed=seed, binds=binds, current_from_year=CURRENT_FROM_YEAR,
               sizes=sizes, picked={k: len(v) for k, v in picks.items()},
               how='tools/student_recall.py draw: seeded stratified sample by recorded student rows (0 / 1-2 / 3+); the checker fills `verdict`, `page` and `listed`',
               sample=[dict(pi=p, stratum=k, candidate_urls=candidate_urls(key, p, by, st, audit), verdict=None, unverifiable_reason=None,
                            page=None, listed=[], notes='') for k, v in picks.items() for p in v],
               filled_by='', signoff=dict(reviewer='', date='', note='a fresh reviewer: not the drawer and not the filler'))
    out_p.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + '\n')
    return rec


# ---- captures ---------------------------------------------------------------------------------------------------------------------------------
def captures_path(key):
    return Path(P.data_w('student-recall-captures.sqlite', key))


def _store(path):
    c = sqlite3.connect(str(path), timeout=60)
    c.execute('create table if not exists live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    c.execute('create table if not exists robots (host text primary key, fetched_at text, status int, body text)')
    c.execute('create table if not exists blocked (host text primary key, at text, why text)')
    c.commit()
    return c


def capture(key, pi, url, file=None, store=None, sleep=time.sleep):
    """Store the member-list page of a sampled PI. With `file` the bytes are a page you already hold; otherwise one polite live fetch through
    school_web.live (robots incl. the Claude agent groups, a challenge blocks the host) at least 3 s after any earlier fetch of the same host.
    Returns dict(url, sha256, status, fetched_at) for the record's `page`."""
    c = store or _store(captures_path(key))
    if file:
        body = Path(file).read_bytes()
        sha = hashlib.sha256(body).hexdigest()
        now = time.strftime('%Y-%m-%dT%H:%M:%S')
        c.execute('insert or replace into live values (?,?,?,?,?,?,?)', (url, now, 200, sha, 'text/html', zlib.compress(body, 6), None))
        c.commit()
        return dict(url=url, sha256=sha, status=200, fetched_at=now, via='file')
    import school_web as W
    import school_config as S
    host = re.sub(r'^https?://([^/]+).*', r'\1', url)
    bare = host.lower().removeprefix('www.')
    try:
        charter_hosts = S.get(key).get('hosts') or []
    except KeyError:
        charter_hosts = []
    for h in charter_hosts:
        if h.get('use') == 'none' and h['host'].lower().removeprefix('www.') == bare:
            raise SystemExit(f'{host}: charter use=none; never fetched: record the PI as unverifiable (robots_disallowed)')
    c.execute('create table if not exists blocked (host text primary key, at text, why text)')
    row = c.execute('select why from blocked where host=?', (host,)).fetchone()
    if row:   # a challenge, an access refusal or a robots refusal earlier (any process): the host is never fetched again; the PI is unverifiable
        raise SystemExit(f'{host}: blocked since an earlier refusal or challenge ({row[0]}); never fetched again: record the PI as unverifiable')
    last = c.execute("select max(fetched_at) from live where url like ?", (f'%//{host}/%',)).fetchone()[0]
    if last:   # the stored time of a fetch of this host: keep the 3 s gap across invocations
        age = time.time() - time.mktime(time.strptime(last, '%Y-%m-%dT%H:%M:%S'))
        if age < 3:
            sleep(3 - age)
    res = W.live(c, url)
    if res is None:
        c.execute('insert or ignore into blocked values (?,?,?)', (host, time.strftime('%Y-%m-%dT%H:%M:%S'), f'robots disallows or unreadable at {url}'))
        c.commit()
        raise SystemExit(f'{url}: robots disallows it, robots is unreadable, or the host is blocked after a challenge: record the PI as unverifiable (robots_disallowed / bot_challenge)')
    status, sha, _ = res
    if status in (401, 403, 429, 999):
        c.execute('insert or ignore into blocked values (?,?,?)', (host, time.strftime('%Y-%m-%dT%H:%M:%S'), f'HTTP {status} at {url}'))
        c.commit()
    if status != 200:
        raise SystemExit(f'{url}: status {status} ({"bot challenge: stop, never retry" if status == 999 else "not a readable page"}): record the PI as unverifiable')
    return dict(url=url, sha256=sha, status=status, fetched_at=c.execute('select fetched_at from live where url=?', (url,)).fetchone()[0], via='live')


def page_text(raw):
    """The visible text of a stored page, whitespace-collapsed, accent-folded and lower-cased (a name or quote must be a substring of it)."""
    try:
        s = raw.decode('utf-8')
    except UnicodeDecodeError:
        s = raw.decode('gb18030', 'replace')
    s = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', s)
    if not re.search(r'(?i)<html|<body', s[:5000]):   # a data file (XML: names in attributes): the attribute values are its text
        s = re.sub(r'(?s)<[^>]+>', lambda m: ' ' + ' '.join(re.findall(r'="([^"]*)"', m.group(0))) + ' ', s)
    s = html.unescape(re.sub(r'(?s)<[^>]+>', ' ', s))
    return norm_text(s)


def page_text_lines(raw):
    """The visible text of a stored page with line breaks kept at block ends (for a checker to read), links dropped."""
    try:
        s = raw.decode('utf-8')
    except UnicodeDecodeError:
        s = raw.decode('gb18030', 'replace')
    s = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', s)
    s = re.sub(r'(?i)</(p|div|li|tr|h\d|section|ul|table)>|<br\s*/?>', '\n', s)
    s = html.unescape(re.sub(r'(?s)<[^>]+>', ' ', s)).replace('\xa0', ' ')
    return '\n'.join(' '.join(x.split()) for x in s.split('\n') if x.strip())


def norm_text(s):
    return ' '.join(unicodedata.normalize('NFKC', s or '').replace('\xa0', ' ').casefold().split())


def stored_page(conn, url):
    r = conn.execute('select status, sha256, raw_zlib from live where url=?', (url,)).fetchone()
    if not r or not r[2]:
        return None
    try:
        raw = zlib.decompress(r[2])
    except zlib.error:
        raw = bytes(r[2])
    return dict(status=r[0], sha256=hashlib.sha256(raw).hexdigest(), raw=raw)


# ---- (B) the check: recall from the entries ---------------------------------------------------------------------------------------------------
def classify_entry(e):
    """-> (kind, current_phd): kind is excluded | eligible | undated_excluded.
    eligible = dated with a year in the window, or in a current-members section. Undated names elsewhere stay excluded (the strict rule)."""
    if e.get('exclude'):
        return 'excluded', False
    sec = e.get('section') or 'other'
    ys = [y for y in e.get('years') or [] if isinstance(y, int)]
    dated = bool(ys) and WINDOW[0] <= max(ys) <= WINDOW[1] + 1
    if sec != 'current' and not dated:
        return 'undated_excluded', False
    cur = sec != 'alumni' and (sec == 'current' or max(ys) >= CURRENT_FROM_YEAR)
    return 'eligible', cur and role_class({'roles': [e.get('role') or '']}) == 'phd'


def entry_counts(rec_entry, rows):
    """Per sampled PI: L eligible names, K of them recorded; Lc/Kc the current-PhD part; and the exclusions."""
    c = collections.Counter()
    for e in rec_entry.get('listed') or []:
        kind, curphd = classify_entry(e)
        c['listed'] += 1
        if kind != 'eligible':
            c[kind] += 1
            continue
        hit = is_recorded(e.get('name') or '', rows)
        c['L'] += 1
        c['K'] += hit
        if curphd:
            c['Lc'] += 1
            c['Kc'] += hit
    return c


def _weights(sample_rows, sizes):
    """Per stratum h: N_h / n_h (all sampled) and N_h / n_h_readable."""
    n = collections.Counter(r['stratum'] for r in sample_rows)
    nr = collections.Counter(r['stratum'] for r in sample_rows if r.get('verdict') == 'readable')
    return {h: sizes[h] / n[h] for h in n if n[h]}, {h: sizes[h] / nr[h] for h in nr if nr[h]}


def estimate(sample_rows, per_pi, sizes):
    """Stratified ratio estimates. R1: strict recall over the readable PIs' eligible names, readable PIs weighted N_h/n_h_readable.
    R2: current-PhD recall of the whole school: every sampled PI weighted N_h/n_h; an UNVERIFIABLE PI adds its stratum's mean current-PhD name count
    to the denominator and nothing to the numerator (conservative: unreadable counts as everything missing)."""
    w_all, w_read = _weights(sample_rows, sizes)
    readable = [r for r in sample_rows if r.get('verdict') == 'readable']
    num1 = sum(w_read[r['stratum']] * per_pi[r['pi']]['K'] for r in readable)
    den1 = sum(w_read[r['stratum']] * per_pi[r['pi']]['L'] for r in readable)
    allmean = (sum(per_pi[r['pi']]['Lc'] for r in readable) / len(readable)) if readable else 0
    num2 = den2 = 0.0
    for r in sample_rows:
        w = w_all[r['stratum']]
        if r.get('verdict') == 'readable':
            num2 += w * per_pi[r['pi']]['Kc']
            den2 += w * per_pi[r['pi']]['Lc']
        else:
            in_h = [per_pi[x['pi']]['Lc'] for x in readable if x['stratum'] == r['stratum']]
            den2 += w * (sum(in_h) / len(in_h) if in_h else allmean)
    return (num1 / den1 if den1 else None), (num2 / den2 if den2 else None)


def bootstrap_lo(sample_rows, per_pi, sizes, which=1):
    """5th percentile of R2 over cluster resamples of the sampled PIs within their strata (informational; the gate reads the point estimate)."""
    rnd = random.Random(BOOTSTRAP_SEED)
    by = collections.defaultdict(list)
    for r in sample_rows:
        by[r['stratum']].append(r)
    vals = []
    for _ in range(BOOTSTRAP_REPS):
        rs = []
        for h, g in by.items():
            for i, r in enumerate(rnd.choices(g, k=len(g))):
                rs.append(dict(r, pi=f'{r["pi"]}#{h}{i}'))   # each draw is its own cluster
                per_pi[rs[-1]['pi']] = per_pi[r['pi']]
        v = estimate(rs, per_pi, sizes)[which]
        if v is not None:
            vals.append(v)
    return sorted(vals)[int(0.05 * len(vals))] if vals else None


def evaluate_record(key, rec, st=None, binds_now=None, conn=None, pis=None):
    """-> dict(findings [str], numbers {...}). No finding means the record is complete, bound, signed and verifiable."""
    st = _students(key) if st is None else st
    binds_now = bindings(key) if binds_now is None else binds_now
    fnd, num = [], {}
    if rec.get('schema') != SCHEMA:
        fnd.append(f'record: schema {rec.get("schema")} is not {SCHEMA}')
    if rec.get('binds') != binds_now:
        stale = [k for k in binds_now if (rec.get('binds') or {}).get(k) != binds_now[k]]
        return dict(findings=[f'bound: the build changed since the draw ({", ".join(stale)} differ); a rebuild or rule change invalidates the sample: '
                              f'run student_recall.py draw {key} --force and re-check a NEW sample'], numbers=num)
    pis = [p['pi'] for p in (_pis(key) if pis is None else pis)]
    picks, sizes = draw_sample(pis, st, rec['seed'])
    want = sorted(p for v in picks.values() for p in v)
    have = sorted(r['pi'] for r in rec.get('sample') or [])
    if want != have:
        fnd.append('sample: the PIs are not the seeded draw of this build (the sample was edited); draw again')
    sample = rec.get('sample') or []
    if len(sample) < min(SAMPLE_SIZE, len(pis)):
        fnd.append(f'sample: {len(sample)} PIs drawn, {min(SAMPLE_SIZE, len(pis))} needed')
    per_pi, excl, listed = {}, 0, 0
    conn = conn if conn is not None else (_store(captures_path(key)) if Path(captures_path(key)).exists() else None)
    for r in sample:
        v = r.get('verdict')
        if v not in ('readable', 'unverifiable'):
            fnd.append(f'{r["pi"]}: no verdict (readable | unverifiable) filled in')
            per_pi[r['pi']] = collections.Counter()
            continue
        if v == 'unverifiable':
            if r.get('unverifiable_reason') not in UNVERIFIABLE_REASONS:
                fnd.append(f'{r["pi"]}: unverifiable needs a reason class from {sorted(UNVERIFIABLE_REASONS)}')
            per_pi[r['pi']] = collections.Counter()
            continue
        pg = r.get('page') or {}
        if not (pg.get('url') and re.fullmatch(r'[0-9a-f]{64}', pg.get('sha256') or '') and (pg.get('quote') or '').strip()):
            fnd.append(f'{r["pi"]}: readable needs page.url, page.sha256 (64 hex) and a verbatim page.quote')
        elif conn is None:
            fnd.append(f'{r["pi"]}: the capture store student-recall-captures.sqlite is missing (student_recall.py capture {key} "{r["pi"]}" <url>)')
        else:
            sp = stored_page(conn, pg['url'])
            if not sp:
                fnd.append(f'{r["pi"]}: {pg["url"]} is not in the capture store')
            elif sp['sha256'] != pg['sha256']:
                fnd.append(f'{r["pi"]}: page.sha256 does not match the stored capture of {pg["url"]}')
            else:
                text = page_text(sp['raw'])
                if norm_text(pg['quote']) not in text:
                    fnd.append(f'{r["pi"]}: the quote is not on the captured page')
                lost = [e.get('name') for e in r.get('listed') or [] if norm_text(e.get('name') or '').split() and
                        not all(t in text for t in norm_text(re.sub(r'\([^)]*\)', ' ', e.get('name') or '')).split())]
                if lost:
                    fnd.append(f'{r["pi"]}: {len(lost)} listed name(s) are not on the captured page (e.g. {lost[0]!r})')
        for e in r.get('listed') or []:
            if e.get('section') not in SECTIONS:
                fnd.append(f'{r["pi"]}: {e.get("name")!r}: section must be one of {SECTIONS}')
            if e.get('exclude') and e['exclude'] not in EXCLUDE_REASONS:
                fnd.append(f'{r["pi"]}: {e.get("name")!r}: exclude reason must be one of {EXCLUDE_REASONS}')
        c = entry_counts(r, st.get(r['pi'], []))
        per_pi[r['pi']] = c
        excl += c['excluded']
        listed += c['listed']
    readable = [r for r in sample if r.get('verdict') == 'readable']
    unv = [r for r in sample if r.get('verdict') == 'unverifiable']
    pp = {k: dict(L=v['L'], K=v['K'], Lc=v['Lc'], Kc=v['Kc']) for k, v in per_pi.items()}
    r1, r2 = estimate(sample, pp, sizes) if readable else (None, None)
    num.update(sample=len(sample), readable=len(readable), unverifiable=len(unv), unverifiable_share=round(len(unv) / len(sample), 3) if sample else None,
               unverifiable_reasons=dict(collections.Counter(r.get('unverifiable_reason') for r in unv)),
               names_listed=listed, names_excluded=excl, excluded_share=round(excl / listed, 3) if listed else 0.0,
               undated_excluded=sum(c['undated_excluded'] for c in per_pi.values()), eligible_names=sum(c['L'] for c in per_pi.values()),
               recorded_names=sum(c['K'] for c in per_pi.values()), r1_strict_recall=round(r1, 3) if r1 is not None else None,
               r2_est_current_phd_recall=round(r2, 3) if r2 is not None else None,
               r2_bootstrap_p5=round(bootstrap_lo(sample, dict(pp), sizes) or 0, 3) if readable else None, sizes=sizes)
    sg = rec.get('signoff') or {}
    others = {rec.get('drawn_by'), rec.get('filled_by')} - {'', None}
    if not (sg.get('reviewer') and sg.get('date')):
        fnd.append('signoff: a fresh reviewer must sign off (signoff.reviewer, signoff.date)')
    elif sg['reviewer'] in others:
        fnd.append(f'signoff: the reviewer {sg["reviewer"]!r} drew or filled the record; a fresh reviewer is needed')
    if not rec.get('filled_by'):
        fnd.append('filled_by: name the checker who read the pages')
    worst = sorted(((v['L'] - v['K'], p) for p, v in pp.items() if v['L'] > v['K']), reverse=True)[:3]
    num['largest_gaps'] = [f'{p} ({n} missing)' for n, p in worst]
    return dict(findings=fnd, numbers=num)


# ---- (C) gate items ---------------------------------------------------------------------------------------------------------------------------
def gate_items(key, th=None):
    """The stage-6 recall findings: [] when every item passes. Each message names the item, the number, the bar and what to do."""
    th = dict(THRESHOLDS, **(th or {}))
    items = []
    m = metrics(key)
    if m['zero_recorded_unreasoned_share'] is not None and m['zero_recorded_unreasoned_share'] > th['Z']:
        items.append(f'recall Z: {m["zero_recorded_unreasoned"]} of {m["pis"]} PIs ({m["zero_recorded_unreasoned_share"]:.1%}) have no recorded student and no researched reason '
                     f'(> {th["Z"]:.0%}); collect their students (rosters, CVs, group pages) or record a researched non-boilerplate reason with >= {MIN_SOURCES_FOR_REASON} sources')
    rp = Path(P.data('student-recall-check.json', key))
    rec = _read(rp)
    if not rec:
        items.append(f'recall record: reviewed/student-recall-check.json missing (student_recall.py draw {key}; read {SAMPLE_SIZE} sampled member-list pages; student_recall.py check {key})')
        return items
    ev = evaluate_record(key, rec)
    items += [f'recall record: {f}' for f in ev['findings']]
    n = ev['numbers']
    if ev['findings'] and any(f.startswith('bound:') for f in ev['findings']):
        return items
    if n.get('r1_strict_recall') is not None and n['r1_strict_recall'] < th['R1']:
        items.append(f'recall R1: strict recall on readable PIs {n["r1_strict_recall"]:.2f} < {th["R1"]:.2f} ({n["recorded_names"]} of {n["eligible_names"]} listed names recorded; '
                     f'largest gaps {"; ".join(n["largest_gaps"]) or "none"}); add the missing members (member-list rounds), rebuild, draw a new sample')
    if n.get('unverifiable_share') is not None and n['unverifiable_share'] > th['U']:
        items.append(f'recall U: {n["unverifiable"]} of {n["sample"]} sampled PIs are unverifiable ({n["unverifiable_share"]:.0%} > {th["U"]:.0%}; {n["unverifiable_reasons"]}); '
                     'find readable member lists for these labs (Wayback is allowed for lab pages only where the project rules say so) - unverifiable stays unverifiable')
    if n.get('r2_est_current_phd_recall') is None and n.get('readable') == 0 and n.get('sample'):
        items.append('recall R2: no readable PI in the sample, so whole-school current-PhD recall cannot be estimated')
    elif n.get('r2_est_current_phd_recall') is not None and n['r2_est_current_phd_recall'] < th['R2']:
        items.append(f'recall R2: estimated whole-school current-PhD recall {n["r2_est_current_phd_recall"]:.2f} < {th["R2"]:.2f} '
                     f'(5th pct of a cluster bootstrap {n["r2_bootstrap_p5"]}; unverifiable PIs count as 0, so R2 is bounded by (1-U) x R1 = {(1 - th["U"]) * th["R1"]:.2f}; the owner wants U tightened toward 0.20 and R2 toward 0.70 after the first round of discovery fixes); raise recall on the strata with the gaps, or make more pages readable')
    if n.get('excluded_share', 0) > th['X']:
        items.append(f'recall record: {n["names_excluded"]} of {n["names_listed"]} listed names were excluded by the checker ({n["excluded_share"]:.0%} > {th["X"]:.0%}); excluding is not a way to raise recall')
    return items


def gate_counts(key):
    """The numbers the stage-6 gate line carries (stage_gate.g6 merges them into its counts)."""
    m = metrics(key)
    rec = _read(P.data('student-recall-check.json', key))
    n = evaluate_record(key, rec)['numbers'] if rec else {}
    return dict(recall_pis_with_current_phd=m['pis_with_current_phd'], recall_zero_recorded_unreasoned=m['zero_recorded_unreasoned'],
                recall_r1=n.get('r1_strict_recall'), recall_u=n.get('unverifiable_share'), recall_r2=n.get('r2_est_current_phd_recall'))


# ---- report / CLI -----------------------------------------------------------------------------------------------------------------------------
def would_fail(key, th=None):
    """{item: 'fail' | 'ok' | 'unmeasured'} as the gate stands today: items needing the hand record are 'unmeasured' while it is missing."""
    th = dict(THRESHOLDS, **(th or {}))
    m = metrics(key)
    res = {'Z': 'fail' if (m['zero_recorded_unreasoned_share'] or 0) > th['Z'] else 'ok'}
    rec = _read(P.data('student-recall-check.json', key))
    if not rec:
        res.update({'record': 'fail (missing)', 'R1': 'unmeasured', 'U': 'unmeasured', 'R2': 'unmeasured'})
        return res
    msgs = gate_items(key, th)
    res['record'] = 'fail' if any(x.startswith('recall record') for x in msgs) else 'ok'
    for k in ('R1', 'U', 'R2'):
        res[k] = 'fail' if any(x.startswith(f'recall {k}') for x in msgs) else 'ok'
    return res


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('report', 'draw', 'capture', 'check', 'text'))
    ap.add_argument('key')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--seed'); ap.add_argument('--drawn-by', default=''); ap.add_argument('--force', action='store_true')
    ap.add_argument('--file'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'report':
        m = metrics(a.key)
        m['would_fail'] = would_fail(a.key)
        print(json.dumps(m, indent=1, ensure_ascii=False) if a.json else '\n'.join(f'{k}: {v}' for k, v in m.items()))
        return 0
    if a.cmd == 'draw':
        rec = draw(a.key, seed=a.seed, drawn_by=a.drawn_by, force=a.force)
        print(f'{a.key}: drew {len(rec["sample"])} PIs (seed {rec["seed"]}, strata {rec["sizes"]} -> {rec["picked"]}); fill the entries, then check')
        return 0
    if a.cmd == 'capture':
        if len(a.args) != 2:
            ap.error('capture <key> <pi> <url>')
        print(json.dumps(capture(a.key, a.args[0], a.args[1], file=a.file)))
        return 0
    if a.cmd == 'text':
        sp = stored_page(_store(captures_path(a.key)), a.args[0])
        if not sp:
            print('NOT STORED')
            return 1
        print(page_text_lines(sp['raw']))
        import urllib.parse
        print('--- LINKS')
        for h, t in re.findall(r'(?is)<a\s[^>]*href=["\']([^"\'#][^"\']*)["\'][^>]*>(.*?)</a>', sp['raw'].decode('utf-8', 'replace'))[:150]:
            print(' '.join(re.sub(r'<[^>]+>', ' ', t).split())[:50], '->', urllib.parse.urljoin(a.args[0], h))
        return 0
    rec = _read(P.data('student-recall-check.json', a.key))
    if not rec:
        print('no record: run draw first')
        return 1
    ev = evaluate_record(a.key, rec)
    for f in ev['findings']:
        print(f)
    print(json.dumps(ev['numbers'], ensure_ascii=False))
    return 1 if ev['findings'] else 0


if __name__ == '__main__':
    sys.exit(main())
