"""Reviewed canonical names for a Han-name school's listing rows (stage 2, census_build `source_names`).

census_build never joins two listing rows of a literal Han name unless they share a profile URL, so a department that re-publishes its faculty
list (new CMS, a link-less year, a second list of the same people) fails with 'Distinct faculty profiles need reviewed unique names'. This tool
writes the reviewed file `hierarchy/<key>/reviewed/census-name-aliases.json` (`source_names`), one entry per identity with the exact saved rows
as evidence (url, sha256, format, name_listed, profile, quote), under the rule USTC used (2026-11-15):

  join    every row of one normalized Han name inside the school's listing when no saved capture lists that name twice and no covered year strictly
          between the first and last observation lacks it by two or more consecutive covered years.
  split   otherwise (two rows of the name in one capture, or a gap) the rows are split by source profile, each identity named `<name> [<profile tail>]`;
          a row without a profile is attached to the identity of the nearest listing year (ties: the earlier), and counted in `attached_rows`.
Listing-name continuity only: no DBLP, OpenAlex, ORCID or paper identity and no appointment interval is admitted. Never a pinyin or cross-script join.

  cjk_name_review.py <key> [--write]     report (and with --write, write the file)
"""
import collections, json, re, sys
import sqlite3
import zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import census_build as C  # noqa: E402
import listing_formats as LF  # noqa: E402
import school_config as S  # noqa: E402
from listing_rows import quote_of  # noqa: E402
from pihier.names import literal_cjk_name  # noqa: E402
from school_web import body  # noqa: E402

RULE = ('same normalized Han name in the one department listing; no capture lists the name twice; no two consecutive covered listing years between the '
        "first and last observation without it. Otherwise split by source profile ('<name> [<profile tail>]'), a link-less row attached to the nearest listing year.")
NOTE = 'Listing-name continuity only: not a DBLP, OpenAlex, ORCID or paper identity, and not an appointment interval.'


def norm(n):
    return re.sub(r'[\s　]+', '', n)


def tail(profile):
    pk = C.profile_key(profile) or profile or ''
    m = re.search(r'(\d{4,}|[\w-]+)(?:\.\w+)?$', pk)
    return m.group(1) if m else pk[-12:]


def pointer(r):
    return C.profile_key(r.get('profile')) or r.get('profile') or None


def clusters(name, rs, covered):
    capn = collections.Counter(r['capture_url'] for r in rs)
    dup = any(v > 1 for v in capn.values())
    gap = False
    for d in {r['dept'] for r in rs}:
        ys = {r['year'] for r in rs if r['dept'] == d}
        miss = sorted(y for y in covered[d] if min(ys) < y < max(ys) and y not in ys)
        gap = gap or any(b == a + 1 or (b in covered[d] and a in covered[d] and not [y for y in covered[d] if a < y < b]) for a, b in zip(miss, miss[1:]))
    if not dup and not gap:
        return [(name, rs, False)], 0
    profs = sorted({pointer(r) for r in rs if pointer(r)}, key=lambda p: min(r['observed'] for r in rs if pointer(r) == p))
    if len(profs) < 2:
        return [(name, rs, False)], 0   # one profile only: nothing to split on
    groups = {p: [r for r in rs if pointer(r) == p] for p in profs}
    attached = 0
    for r in rs:
        if pointer(r):
            continue
        best = min(profs, key=lambda p: (min(abs(r['year'] - q['year']) for q in groups[p]), p))
        groups[best].append(r)
        attached += 1
    return [(f'{name} [{tail(p)}]', g, True) for p, g in groups.items()], attached


def main(key, write):
    rows = json.load(open(P.data('rows.json', key)))
    covered = collections.defaultdict(set)
    for r in rows:
        covered[r['dept']].add(r['year'])
    by = collections.defaultdict(list)
    for r in rows:
        if literal_cjk_name(r['name']):
            by[norm(r['name'])].append(r)
    todo = {n: rs for n, rs in by.items() if len(rs) > 1 and (len({pointer(r) for r in rs}) > 1 or any(not pointer(r) for r in rs))}
    db = P.data('listings-captures.sqlite', key)
    entries, split_names, attached_total, skipped = [], 0, 0, []
    c = sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True)
    cache = {}
    cfg = S.get(key)
    eras = [(sl['slot'], sl.get('from') or '0', sl.get('to') or '9', sl.get('format')) for d in S.listing_units(cfg) for sl in d.get('listings') or []]

    def html_of(url):
        if url not in cache:
            row = c.execute('select http_status,sha256,raw_zlib from captures where capture_url=?', (url,)).fetchone()
            cache[url] = (row, body(row[2]).decode('utf-8', 'replace') if row and row[2] else '')
        return cache[url]

    for name, rs in sorted(todo.items()):
        groups, attached = clusters(name, rs, covered)
        attached_total += attached
        split_names += any(g[2] for g in groups)
        for canon, grs, is_split in groups:
            ev = []
            for r in sorted(grs, key=lambda r: (r['observed'], r['name_listed'])):
                row, html = html_of(r['capture_url'])
                if not row or row[0] != 200:
                    skipped.append((name, r['capture_url']))
                    continue
                m = re.search(r'/web/(\d{14})id_/', r['capture_url'])
                named = [f for sl, a, b, f in eras if sl == r['slot'] and f and m and a <= m.group(1)[:8] <= b]
                fmt, es = LF.parse(html, named[0] if named else None)
                if not es and named:
                    fmt, es = LF.parse(html)
                import hashlib
                if hashlib.sha256(zlib.decompress(row[2])).hexdigest() != r['sha256']:
                    skipped.append((name, r['capture_url']))
                    continue
                flat = ' '.join((c.execute('select text from captures where capture_url=?', (r['capture_url'],)).fetchone()[0] or '').split())
                ok = [e for e in es if e['name_listed'] == r['name_listed'] and C.profile_key(e.get('profile')) == C.profile_key(r.get('profile'))
                      and (e.get('profile') or None) == (r.get('profile') or None) and quote_of(flat, e, html) == r['quote']]
                if len(ok) != 1:
                    skipped.append((name, r['capture_url'], 'no unique parse match'))
                    continue
                ev.append(dict(url=r['capture_url'], sha256=r['sha256'], format=fmt, name_listed=r['name_listed'], profile=r.get('profile'), quote=r['quote']))
            if ev:
                profs = collections.OrderedDict()
                for r in sorted(grs, key=lambda r: r['observed']):
                    if pointer(r):
                        d = profs.setdefault(pointer(r), dict(profile=r.get('profile'), first_observed=r['observed'], last_observed=r['observed']))
                        d['last_observed'] = r['observed']
                entries.append(dict(canonical_name=canon, scope='Only the exact saved listing observations enumerated below; literal source names and quotes remain.',
                                    identity_basis=dict(rule=RULE, profiles=list(profs.values()), split=is_split, note=NOTE), evidence=ev))
    doc = dict(school=key, scope=f'Source-row canonical faculty names for the {key.upper()} census only (Han-name listing continuity; tools/cjk_name_review.py). '
                                 'No DBLP/OpenAlex identity, paper or appointment interval is admitted.',
               reviewed_by='claude-newschools-1118', reviewed_on='2026-11-18', rows=[], profile_names=[])
    doc['source_names'] = entries
    print(json.dumps(dict(school=key, names_total=len(by), names_reviewed=len(todo), identities=len(entries), split_names=split_names,
                          attached_rows=attached_total, skipped=len(skipped), evidence_rows=sum(len(e['evidence']) for e in entries)), ensure_ascii=False))
    for s in skipped[:10]:
        print('skipped', s)
    if write:
        out = P.data('census-name-aliases.json', key)
        if out.exists():
            old = json.loads(out.read_text())
            if old.get('rows') or old.get('profile_names'):
                raise SystemExit('existing reviewed aliases/profile names: merge by hand')
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1], '--write' in sys.argv)
