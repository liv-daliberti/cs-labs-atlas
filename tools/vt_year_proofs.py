"""Dated year proofs for VT census additions from stored official documents (stage 4, local first; 2026-11-18).

An addition's `sources` are its dated listings (pihier.periods.pi_listings: a source whose year is in 2016-2026, whose quote names the
family name and is a faculty row proves that calendar year). The accepted CS-related people of other units were admitted with ONE
dated source each (2026, or a single catalog year), so their lab papers of every other year fell outside the appointment. This adds,
per person and year, a ladder-professor row found in the stored official documents already on disk:
  bov        Board of Visitors faculty salary reports 2016-17, 2018-19, 2021-22, 2022-23, 2023-24 ('Surname, Given   Rank   salary AY|CY'),
             year = the first year of the academic year
  registrar  undergraduate catalog faculty directories 2017-18 .. 2019-20 (hierarchy/vt/raw/school-captures.sqlite, table live;
             'SURNAME, Given M. (1990), Professor of ...'), year = the first year of the catalog
A row counts only for a ladder rank (assistant / associate / full / named professor; not research, teaching, adjunct, emeritus,
practice, lecturer) and when the given name matches a spelled-out given name of the person (initial-only rows are not used).
usage: vt_year_proofs.py [--apply] [--file census-additions.json]   rewrites hierarchy/vt/reviewed/census-additions.json (adds sources; never removes one)
"""
import argparse, hashlib, json, re, sqlite3, unicodedata, zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402

SCR = Path(P.data('census-faculty.json', 'vt').parents[4]) / 'scratch' / 'vt-followthrough-1110'
BOV = {2016: 'bov-2016-17-faculty-salary', 2018: 'bov-2018-19-faculty-salary', 2021: 'bov-2021-22-faculty-salary',
       2022: 'bov-2022-23-faculty-salary', 2023: 'bov-2023-24-faculty-salary'}
REG = {2017: '1718', 2018: '1819', 2019: '1920'}
LADDER = re.compile(r'^(?:[A-Z][\w.\'\- ]*? )?(?:Assistant |Associate |Assoc\.? |Asst\.? )?Prof(?:essor|\.)?(?: of [A-Za-z ,&\-]+)?$', re.I)
NOT_LADDER = re.compile(r'research|teaching|adjunct|emerit|practice|lecturer|instructor|visiting|collegiate|clinical|extension|courtesy|postdoc', re.I)


def fold(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


def given_set(person):
    out = set()
    for n in [person['name']] + list(person.get('aliases') or []):
        n = re.sub(r'\s+\d{4}$', '', n)
        if ',' in n:
            n = ' '.join(reversed([x.strip() for x in n.split(',', 1)]))
        for t in fold(n).replace('.', ' ').split()[:-1]:
            if len(t) > 1:
                out.add(t)
    return out


def surnames(person):
    out = set()
    for n in [person['name']] + list(person.get('aliases') or []):
        n = re.sub(r'\s+\d{4}$', '', n)
        n = n.split(',')[0] if ',' in n else n.split()[-1]
        out.add(fold(n).replace('.', '').strip())
    return out


def ladder(rank):
    rank = rank.strip()
    return bool(LADDER.match(rank)) and not NOT_LADDER.search(rank)


def bov_rows():
    for year, stem in BOV.items():
        txt = (SCR / f'{stem}.layout.txt').read_text(errors='ignore')
        sha = hashlib.sha256((SCR / f'{stem}.pdf').read_bytes()).hexdigest()
        url = f'https://bov.vt.edu/assets/{stem}.pdf (stored: scratch/vt-followthrough-1110/{stem}.pdf)'
        for line in txt.splitlines():
            parts = [x.strip() for x in re.split(r'\s{2,}', line.strip()) if x.strip()]
            if len(parts) >= 4 and parts[-1] in ('AY', 'CY') and re.fullmatch(r'[\d,]{5,}', parts[-2]) and ',' in parts[0]:
                s_, g_ = parts[0].split(',', 1)
                yield year, s_, g_, parts[1], ' '.join(line.split()), url, sha


def registrar_rows():
    c = sqlite3.connect(f"file:{P.data('school-captures.sqlite', 'vt')}?mode=ro", uri=True, timeout=30)
    for year, ed in REG.items():
        url = f'https://www.undergradcatalog.registrar.vt.edu/{ed}/faculty.html'
        r = c.execute('select text, raw_zlib, sha256 from live where url=?', (url,)).fetchone()
        if not r:
            continue
        txt = r[0] or zlib.decompress(r[1]).decode('utf8', 'ignore')
        for m in re.finditer(r'<p>([A-Z][A-Z\'\- ]{1,40}), ([^(<]{1,60}) \((\d{4})\), ([^.<]{1,80})', txt):
            rank = m.group(4)
            yield year, m.group(1).title(), m.group(2), rank, ' '.join(re.sub('<[^>]+>', '', m.group(0)).split()), url, r[2]


def proofs(person, rows):
    sur, giv = surnames(person), given_set(person)
    out = {}
    for year, s, g, rank, quote, url, sha in rows:
        gt = fold(g).replace('.', ' ').split()
        if fold(s).strip() in sur and gt and gt[0] in giv and ladder(rank):
            out.setdefault(year, dict(url=url, sha256=sha, quote=quote[:300], kind='stored_official_document', observed=str(year)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); ap.add_argument('--file'); a = ap.parse_args(argv)
    f = Path(a.file) if a.file else P.data('census-additions.json', 'vt')
    adds = json.loads(f.read_text())
    rows = list(bov_rows()) + list(registrar_rows())
    n = 0
    for p in adds:
        have = {int(str(s.get('observed'))[:4]) for s in p['sources'] if s.get('observed')}
        new = {y: s for y, s in proofs(p, rows).items() if y not in have}
        for y in sorted(new):
            p['sources'].append(new[y]); n += 1
        p['years_listed'] = sorted(set(p.get('years_listed') or []) | set(new))
    print(json.dumps(dict(additions=len(adds), proofs_added=n, with_new=sum(1 for p in adds if len(p['sources']) > 1))))
    if a.apply:
        f.write_text(json.dumps(adds, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
