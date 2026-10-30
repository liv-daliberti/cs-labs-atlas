"""Home departments of a protocol school's PIs, from the titles on their dated department listings: protocol stage 3.

rule      the PI's latest 2016-2026 listing row decides:
            a professor title in the listing's own department (the charter's [[departments]].title_match; not courtesy,
            affiliate, adjunct, visiting, emeritus) -> that department (charter name); a person listed with such a title
            by two departments takes the one with more such years, the other goes to `also`
            a courtesy / affiliate appointment -> the unit of the row's first professor title that is not the
            department's (census pi_basis.home_unit: 'School of Information', 'Linguistics')
            otherwise (emeritus or adjunct only in the latest row) -> the department of their last professor title
          the other units the row names go to `also`; the quote is the listing row (url + sha256 + quote)
status    accepted when one unit results; hold when none does (written, never a placeholder home)
-> hierarchy/<key>/home-departments.json, and the school's rows of the shared hierarchy/home-departments.json (re-read
   immediately before writing; only rows of this school are replaced)
usage: home_departments_school.py <key> [--write-shared]
"""
import collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402

NOT_HOME = re.compile(r'courtesy|affiliate|adjunct|visiting|emerit|lecturer|research (?:scientist|investigator)', re.I)
PROF = re.compile(r'\bprofessor\b', re.I)
UNIT = re.compile(r'professor(?:\s*\([^)]*\))?(?: of [^,]+)?,\s*(.+)$', re.I)


SCHOOL_LEVEL = re.compile(r'^(?:Medical School|School of|College of|Rackham)', re.I)


def unit_of(title):
    """'Professor, School of Information' -> 'School of Information'; 'Assistant Professor of Computational Medicine and
    Bioinformatics, Medical School' -> 'Computational Medicine and Bioinformatics' (the department, not the school)."""
    m = UNIT.search(title)
    if not m:
        return None
    u = m.group(1).strip()
    of = re.search(r'professor of (.+?),', title, re.I)
    return of.group(1).strip() if of and SCHOOL_LEVEL.match(u) else u


def main(key, write_shared=False):
    cfg = S.get(key)
    deps = {d['code']: d for d in cfg.get('departments') or []}
    tm = {c: re.compile(d.get('title_match') or '.', re.I) for c, d in deps.items()}
    census = json.loads((P.CENSUS / f'{key}-faculty.json').read_text())['faculty']
    adds = json.loads((P.CENSUS / f'{key}-additions.json').read_text()) if (P.CENSUS / f'{key}-additions.json').exists() else []
    units = {u['code']: u['name'] for u in cfg.get('affiliated_units') or []}
    canon = [(re.compile(rx, re.I), name) for name, rx in (S.field(cfg, 'census.home_units') or {}).items()]

    def norm(u):
        u = re.sub(r'\s*\((?:effective|as of)[^)]*\)', '', u or '').strip()
        u = re.sub(r'^Department of\s+', '', u)
        return next((name for rx, name in canon if rx.search(u)), u)
    rows = json.loads((P.LISTINGS / key / 'rows.json').read_text())
    by_name = collections.defaultdict(list)
    for r in rows:
        by_name[r['name']].append(r)
    out, n = [], collections.Counter()
    for x in census:
        if not x.get('is_pi'):
            continue
        rs = sorted([r for nm in [x['name']] + list(x.get('aliases') or []) for r in by_name.get(nm, [])], key=lambda r: r['observed'])
        own = collections.Counter()
        for r in rs:
            if any(PROF.search(t) and tm[r['dept']].search(t) and not NOT_HOME.search(t) for t in r['titles']):
                own[r['dept']] += 1
        b = x.get('pi_basis') or {}
        home, ev, note = None, None, None
        if b.get('kind') == 'courtesy_faculty' and b.get('home_unit'):
            home = b['home_unit']; ev = dict(url=b['url'], sha256=b['sha256'], quote=b['quote']); note = 'courtesy appointment: the home unit of the same listing row'
        elif own:
            code = own.most_common(1)[0][0]
            r = [r for r in rs if r['dept'] == code][-1]
            home = deps[code]['name']; ev = dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'])
            note = f'professor title in the {code} listing (latest row)' + (f'; also listed by {", ".join(c for c in own if c != code)}' if len(own) > 1 else '')
        else:
            prof = [(r, t) for r in rs for t in r['titles'] if PROF.search(t) and not re.search('courtesy|affiliate', t, re.I)]
            if prof:
                r, t = prof[-1]
                u = unit_of(t)
                home = deps[r['dept']]['name'] if (not u or tm[r['dept']].search(u)) else u
                ev = dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote']); note = 'the last professor title listed (emeritus or adjunct later)'
        also = []
        if rs:
            for t in rs[-1]['titles']:
                u = unit_of(t)
                if u and u != home and not any(tm[c].search(u) for c in tm if deps[c]['name'] == home):
                    also.append(u)
        also += [deps[c]['name'] for c in own if deps[c]['name'] != home]
        home = norm(home) if home else home
        also = [a_ for a_ in dict.fromkeys(norm(a_) for a_ in also) if a_ != home]
        row = dict(school=key, name=x['name'], home_department=home, also=list(dict.fromkeys(also)), no_academic_department=False,
                   status='accepted' if home else 'hold', evidence=ev, note=note or 'no professor title on any listing row')
        out.append(row); n[row['status']] += 1; n['home:' + str(home)] += 1
    for x in adds:  # accepted CS-related faculty of other units: the unit whose faculty listing proves the appointment
        if not x.get('is_pi'):
            continue
        b = x.get('pi_basis') or {}
        code = (x.get('departments') or [None])[-1]
        home = norm(units.get(code, code))
        row = dict(school=key, name=x['name'], home_department=home, also=[], no_academic_department=False, status='accepted' if home else 'hold',
                   evidence=dict(url=b.get('url'), sha256=b.get('sha256'), quote=b.get('quote')), note=f'the {code} faculty listing (cs-related-review.json)')
        out.append(row); n[row['status']] += 1; n['home:' + str(home)] += 1
    (P.HIERARCHY / key / 'home-departments.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if write_shared:
        f = P.HIERARCHY / 'home-departments.json'
        txt = f.read_text(); shared = json.loads(txt)
        ind = len(re.match(r'\[\n( *)', txt).group(1)) if re.match(r'\[\n( *)', txt) else 2  # keep the file's own layout
        shared = [r for r in shared if r.get('school') != key] + out
        f.write_text(json.dumps(shared, indent=ind, ensure_ascii='\\u' in txt) + ('\n' if txt.endswith('\n') else ''))
    print(json.dumps(dict(n.most_common(20))))


if __name__ == '__main__':
    main(sys.argv[1], '--write-shared' in sys.argv)
