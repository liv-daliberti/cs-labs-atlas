"""Listing histories of the units whose professors the census admitted from one current list (protocol stage 4; ETH 2026-11-25).

The census additions (accepted CS-related professors of other units) carry one dated source, so their window was one year. The owner rules: a dated
same-year listing proves a year, affiliation-based lower bounds do not, and D-0080 bridges only department-wide capture gaps. This reads each unit's
professor-list pages in the Wayback Machine for 2016-2025 (the pages cited by the additions' own sources, plus the unit host's professor/faculty
pages found in the CDX), keeps for each year the capture that names most of the unit's PIs, and records every PI named in it as a dated listing
year (url, sha256, verbatim quote). A year in which the unit has no 200 capture at all is a department-wide capture gap: a PI named before and after
it is bridged (D-0080), with the CDX coverage evidence stored once per unit-year.

  unit_history_school.py <key> fetch [--units A,B]     Wayback pages -> captures store; writes hierarchy/<key>/reviewed/unit-history.json
  unit_history_school.py <key> apply                   folds unit-history.json into census-additions.json (sources + years_listed; never removes one)
usage: nice unit_history_school.py ethz fetch
"""
import collections, json, re, sys, unicodedata
from urllib.parse import urlsplit

import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402

YEARS = range(2016, 2026)
LIST_PATH = re.compile(r'professor|faculty|people|personen|who-is-who|persons|team|mitarbeit', re.I)


def fold(s):
    """Accent-fold one character at a time, so the folded text keeps the length and positions of the original (quotes are cut from the original)."""
    out = []
    for ch in str(s or ''):
        d = ''.join(c for c in unicodedata.normalize('NFKD', ch) if not unicodedata.combining(c))
        out.append((d[:1] or ch).lower() if d else ch.lower())
    return ''.join(out)


def name_forms(name, aliases=()):
    """[(family, first given)] folded forms of a person's names."""
    out = []
    for n in [name, *aliases]:
        t = [w for w in re.sub(r"[^\w\s.-]", ' ', fold(n)).replace('.', ' ').split() if len(w) > 1]
        if len(t) >= 2:
            out.append((t[-1], t[0]))
    return out


def find_name(text, forms):
    """The verbatim stretch of `text` that names a person ('Surname, Given' or 'Given Surname'), or None. Accent-insensitive; the quote keeps the page's characters."""
    ft = fold(text)
    for fam, giv in forms:
        for pat in (rf'\b{re.escape(fam)}\b.{{0,3}},?\s{{0,3}}{re.escape(giv)}', rf'\b{re.escape(giv)}\w*\s+(?:\w+\s+){{0,2}}{re.escape(fam)}\b'):
            m = re.search(pat, ft)
            if m:
                return ' '.join(text[max(0, m.start() - 20):m.end() + 40].split())
    return None


def units_of(key):
    """{unit code: {'pis': {name: forms}, 'urls': set of the additions' own unit-listing urls}} from census-additions.json."""
    adds = json.loads(P.data('census-additions.json', key).read_text())
    out = collections.defaultdict(lambda: dict(pis={}, urls=set()))
    for x in adds:
        if not x.get('is_pi'):
            continue
        code = (x.get('departments') or ['ETH'])[-1]
        u = out[code]
        u['pis'][x['name']] = name_forms(x['name'], x.get('aliases') or [])
        for s in x.get('sources') or []:
            if str(s.get('kind', '')).startswith('unit_listing') and s.get('url'):
                u['urls'].add(re.sub(r'^https?://(?:web\.archive\.org/web/\d+(?:id_)?/)?', '', s['url']))
    for code, u in out.items():   # only the unit's own list pages: not Board notices, news items or other institutions' pages
        u['urls'] = {x for x in u['urls'] if re.match(r'^[\w.-]*ethz\.ch/', x) and re.search(r'who-is-who/\w+\.html|/people/|/professors|/faculty', x) and 'news' not in x and 'retired' not in x}
        if code not in ('ETH', 'INFK', 'ITET'):
            u['urls'].add(f'ethz.ch/en/the-eth-zurich/organisation/who-is-who/{code.lower()}.html')
    return {k: v for k, v in out.items() if k not in ('ETH', 'INFK', 'ITET')}   # INFK and ITET have their own listing rows (stage 1)


UNIT_HOSTS = {'EAPS': ['erdw.ethz.ch', 'eaps.ethz.ch']}   # other units: <code>.ethz.ch


def candidates(c, unit_urls, code=None):
    """{year: [(timestamp, original)]} of 200 captures of the unit's list pages (their own urls and the professor/faculty pages of their hosts)."""
    by_year = collections.defaultdict(list)
    hosts = {urlsplit('https://' + u).hostname for u in unit_urls} | set(UNIT_HOSTS.get(code, [f'{code.lower()}.ethz.ch'] if code else []))
    for u in sorted(unit_urls):
        for r in W.cdx_rows(c, u, frm='2016', to='2025', collapse='timestamp:6'):
            by_year[int(r['timestamp'][:4])].append((r['timestamp'], r['original'], u))
    for h in sorted(hosts):
        if not h or h == 'ethz.ch':
            continue
        for r in W.cdx_rows(c, h + '/', exact=False, frm='2016', to='2025', collapse='urlkey'):
            if LIST_PATH.search(urlsplit(r['original']).path) and re.search(r'professor|faculty|people|personen', r['original'], re.I):
                by_year[int(r['timestamp'][:4])].append((r['timestamp'], r['original'], h))
    return by_year


def fetch(key, only=None):
    c = W.con(key)
    out_path = P.data('cs-related-hand.json', key).parent / 'unit-history.json'
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    for code, u in sorted(units_of(key).items()):
        if only and code not in only:
            continue
        pis = u['pis']
        cand = candidates(c, u['urls'], code)
        rec = dict(urls=sorted(u['urls']), pis=sorted(pis), cdx_captures_by_year={str(y): len(v) for y, v in sorted(cand.items())}, years={}, listed={})
        for y in YEARS:
            best = None
            for ts, orig, via in sorted(cand.get(y, []), key=lambda t: abs(int(t[0][4:6]) - 7))[:4]:   # nearest July first, at most four fetches a year
                try:
                    cap, st, sha, blocks = W.capture(c, ts, orig, via, f'unit:{code}')
                except RuntimeError as e:   # the shared Wayback clock is cooling down after a 429
                    if 'cooling down' in str(e):
                        print(json.dumps(dict(unit=code, year=y, pending='wayback cooling down')), flush=True)
                        continue
                    raise
                if st != 200:
                    continue
                text = W.flat(blocks)
                hits = {n: q for n, f in pis.items() if (q := find_name(text, f))}
                if best is None or len(hits) > len(best[3]):
                    best = (cap, sha, ts, hits)
            if best and best[3]:
                cap, sha, ts, hits = best
                rec['years'][str(y)] = dict(url=cap, sha256=sha, timestamp=ts, pis_named=len(hits))
                for n, q in hits.items():
                    rec['listed'].setdefault(n, {})[str(y)] = dict(url=cap, sha256=sha, quote=q, observed=ts[:8], kind=f'unit_listing:{code}')
        out[code] = rec
        out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
        print(json.dumps(dict(unit=code, pis=len(pis), years_with_a_list=sorted(rec['years']), pis_with_history=len(rec['listed']))), flush=True)


def bridged(rec, name):
    """D-0080 per unit: {year: evidence} for the years with no 200 capture of the unit's pages at all, between two years the PI is named."""
    ys = sorted(int(y) for y in rec['listed'].get(name, {}))
    out = {}
    if len(ys) < 2:
        return out
    for y in range(ys[0] + 1, ys[-1]):
        if y not in ys and not rec['cdx_captures_by_year'].get(str(y)):
            out[y] = dict(url='; '.join(rec['urls'])[:300], sha256='0' * 64, kind='interpolated_department_gap', observed=f'{y}0701',
                          quote=f'no archived 200 capture of the unit listing pages for {y} (CDX: 0 captures); named in {ys[0]} and {ys[-1]}')
    return out


def apply(key):
    hist = json.loads((P.data('cs-related-hand.json', key).parent / 'unit-history.json').read_text())
    fa = P.data('census-additions.json', key)
    adds = json.loads(fa.read_text())
    n = collections.Counter()
    for x in adds:
        if not x.get('is_pi'):
            continue
        rec = hist.get((x.get('departments') or ['ETH'])[-1])
        if not rec:
            continue
        have = {int(str(s.get('observed'))[:4]) for s in x.get('sources') or [] if s.get('observed')}
        new = {int(y): e for y, e in (rec['listed'].get(x['name']) or {}).items()}
        for y, e in bridged(rec, x['name']).items():
            new.setdefault(y, e)
        for y, e in sorted(new.items()):
            if y not in have:
                x.setdefault('sources', []).append(e); n['years'] += 1
        x['years_listed'] = sorted(set(x.get('years_listed') or []) | set(new))
        n['pis'] += bool(new)
    fa.write_text(json.dumps(adds, indent=1, ensure_ascii=False))
    print(json.dumps(dict(n)))


if __name__ == '__main__':
    k, cmd = sys.argv[1], sys.argv[2]
    if cmd == 'fetch':
        fetch(k, set(sys.argv[sys.argv.index('--units') + 1].split(',')) if '--units' in sys.argv else None)
    else:
        apply(k)
