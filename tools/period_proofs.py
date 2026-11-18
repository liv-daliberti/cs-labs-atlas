"""Dated year proofs for faculty the listings name once (stage 4, local first; generic and charter-driven since 2026-11-18, replaces the
VT-only vt_year_proofs.py).

A census addition (an accepted CS-related person of another unit) or a courtesy-listed professor is admitted with ONE dated source, so their lab papers of
every other year fell outside the appointment (pihier.periods.pi_listings: a dated source whose quote names the family name proves that calendar year).
This adds, per person and year, a ladder-professor row found in the official documents already stored on disk. The charter lists them:

  [period_proofs]
  root = "scratch/vt-followthrough-1110"            # directory of the stored files, relative to the project root
  target_basis = ["courtesy_faculty"]               # census PIs (not additions) with this pi_basis.kind also get proofs
  documents = [
    {kind = "salary_layout", year = 2016, file = "bov-2016-17-faculty-salary", url = "https://..."},   # <root>/<file>.layout.txt + <file>.pdf (sha256 of the pdf)
    {kind = "catalog_directory", year = 2017, url = "https://.../faculty.html"},                      # the stored page in captures table `live`
  ]
  kinds: salary_layout   'Surname, Given   Rank   salary AY|CY' lines;  catalog_directory   '<p>SURNAME, Given M. (1990), Rank of Dept' paragraphs

A row counts only for a ladder rank (assistant / associate / full / named professor; not research, teaching, adjunct, emeritus, practice, lecturer) and when its given
name equals a spelled-out given name of the person (initial-only rows are never used). Where the proofs go:
  additions  hierarchy/<key>/reviewed/census-additions.json  `sources` + `years_listed` (never removes one)
  courtesy   census-overrides-school.json  <person>.year_proofs  (census_build.merge_year_proofs folds them into the census row)
`gaps` (after a census + build): the span years no listing proves are written as reviewed unproven (`unproven_years`, `why_unproven`, R-PAP-01) for every PI
whose window is not settled otherwise (stage_gate.period_basis), so the proven years settle and no paper of an unproven year is admitted.
usage: period_proofs.py proofs <key> [--apply] [--root DIR]      period_proofs.py gaps <key> [--apply] [--root DIR]     (--root: a worktree whose reviewed files are edited)
"""
import argparse, hashlib, json, re, sqlite3, sys, unicodedata, zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402

LADDER = re.compile(r'^(?:[A-Z][\w.\'\- ]*? )?(?:Assistant |Associate |Assoc\.? |Asst\.? )?Prof(?:essor|\.)?(?: of [A-Za-z ,&\-]+)?$', re.I)
NOT_LADDER = re.compile(r'research|teaching|adjunct|emerit|practice|lecturer|instructor|visiting|collegiate|clinical|extension|courtesy|postdoc', re.I)


def fold(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


def _names(person):
    for n in [person['name']] + list(person.get('aliases') or []):
        n = re.sub(r'\s+\d{4}$', '', n)   # DBLP homonym number
        yield ' '.join(reversed([x.strip() for x in n.split(',', 1)])) if ',' in n else n


def given_set(person):
    return {t for n in _names(person) for t in fold(n).replace('.', ' ').split()[:-1] if len(t) > 1}


def surnames(person):
    return {fold(n.split()[-1]).replace('.', '').strip() for n in _names(person) if n.split()}


def ladder(rank):
    rank = rank.strip()
    return bool(LADDER.match(rank)) and not NOT_LADDER.search(rank)


def salary_rows(doc, root):
    txt = (root / f"{doc['file']}.layout.txt").read_text(errors='ignore')
    sha = hashlib.sha256((root / f"{doc['file']}.pdf").read_bytes()).hexdigest()
    for line in txt.splitlines():
        parts = [x.strip() for x in re.split(r'\s{2,}', line.strip()) if x.strip()]
        if len(parts) >= 4 and parts[-1] in ('AY', 'CY') and re.fullmatch(r'[\d,]{5,}', parts[-2]) and ',' in parts[0]:
            s_, g_ = parts[0].split(',', 1)
            yield doc['year'], s_.strip(), g_.strip(), parts[1], ' '.join(line.split()), doc['url'], sha


def directory_rows(doc, school):
    c = sqlite3.connect(f"file:{P.data('school-captures.sqlite', school)}?mode=ro", uri=True, timeout=30)
    r = c.execute('select text, raw_zlib, sha256 from live where url=?', (doc['url'],)).fetchone()
    if not r:
        return
    txt = r[0] or zlib.decompress(r[1]).decode('utf8', 'ignore')
    for m in re.finditer(r'<p>([A-Z][A-Z\'\- ]{1,40}), ([^(<]{1,60}) \((\d{4})\), ([^.<]{1,80})', txt):
        yield doc['year'], m.group(1).title(), m.group(2), m.group(4), ' '.join(re.sub('<[^>]+>', '', m.group(0)).split()), doc['url'], r[2]


def document_rows(school, cfg, project_root):
    pp = S.field(cfg, 'period_proofs') or {}
    out = []
    for doc in pp.get('documents') or []:
        if doc['kind'] == 'salary_layout':
            out += list(salary_rows(doc, project_root / pp['root']))
        elif doc['kind'] == 'catalog_directory':
            out += list(directory_rows(doc, school))
        else:
            raise ValueError(f"unknown period_proofs document kind {doc['kind']!r}")
    return out


def proofs(person, rows):
    sur, giv = surnames(person), given_set(person)
    out = {}
    for year, s, g, rank, quote, url, sha in rows:
        gt = fold(g).replace('.', ' ').split()
        if fold(s).strip() in sur and gt and gt[0] in giv and ladder(rank):
            out.setdefault(year, dict(url=url, sha256=sha, quote=quote[:300], kind='stored_official_document', observed=str(year)))
    return out


def add_to(person, rows):
    """Fold the person's new year proofs into person['sources'] / ['years_listed']; the proofs added."""
    have = {int(str(s.get('observed'))[:4]) for s in person.get('sources') or [] if s.get('observed')}
    new = {y: s for y, s in proofs(person, rows).items() if y not in have}
    for y in sorted(new):
        person.setdefault('sources', []).append(new[y])
    person['years_listed'] = sorted(set(person.get('years_listed') or []) | set(new))
    return new


def merge_year_proofs(census, key, root=None):
    """census_build: fold the reviewed year_proofs of census-overrides-school.json into the census rows (is_pi ones)."""
    import census_overrides as CO
    sec = CO.section(key, resolve=(lambda n, s=None: P.data(n, s, root=root)) if root else None)
    for r in census:
        for s in (sec.get(r['name']) or {}).get('year_proofs') or []:
            y = int(str(s['observed'])[:4])
            if not any(str(x.get('observed'))[:4] == str(y) for x in r['sources']):
                r['sources'].append(s)
            r['years_listed'] = sorted(set(r.get('years_listed') or []) | {y})


def run_proofs(key, apply, root):
    cfg = S.get(key)
    rows = document_rows(key, cfg, Path(P.data('census-faculty.json', key)).parents[4])
    fa = P.data('census-additions.json', key, root=root)
    adds = json.loads(fa.read_text()) if fa.exists() else []
    n_add = sum(len(add_to(p, rows)) for p in adds)
    fo = P.data('census-overrides-school.json', key, root=root)
    ov = json.loads(fo.read_text()) if fo.exists() else {}
    basis = set(S.field(cfg, 'period_proofs.target_basis', []) or [])
    census = json.loads(P.data('census-faculty.json', key).read_text())['faculty']
    n_c = 0
    for r in census:
        if r.get('is_pi') and (r.get('pi_basis') or {}).get('kind') in basis:
            new = proofs(r, rows)
            have = {str(s.get('observed'))[:4] for s in r['sources']}
            new = [v for y, v in sorted(new.items()) if str(y) not in have]
            if new:
                e = ov.setdefault(r['name'], {})
                e['year_proofs'] = new
                n_c += len(new)
    print(json.dumps(dict(school=key, additions=len(adds), addition_proofs=n_add, courtesy_proofs=n_c)))
    if apply:
        fa.write_text(json.dumps(adds, indent=1, ensure_ascii=False))
        fo.write_text(json.dumps(ov, indent=1, ensure_ascii=False))


def run_gaps(key, apply, root):
    import stage_gate as G
    per, ov, have = G.periods_have(key)
    fo = P.data('census-overrides-school.json', key, root=root)
    cur = json.loads(fo.read_text()) if fo.exists() else {}
    n = 0
    for x in G.pis_of(key):
        if G.period_basis(key, x, have, ov):
            continue
        gaps = [y for y in G.span_gaps(x) if y not in G.proven_years(key, x['name'])]
        ys = sorted(set(x.get('years_listed') or []))
        e = cur.setdefault(x['name'], {})
        e['unproven_years'] = gaps
        e['why_unproven'] = (f"stage 4 (local first): ladder-professor rows proven for {ys} from the stored official documents named in the charter [period_proofs] and the "
                             f"listings; no stored dated document names this person for {gaps}, so those years prove nothing (R-PAP-01) and no paper of those years is admitted.")
        n += 1
    print(json.dumps(dict(school=key, unproven_sets_written=n)))
    if apply:
        fo.write_text(json.dumps(cur, indent=1, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['proofs', 'gaps']); ap.add_argument('school')
    ap.add_argument('--apply', action='store_true'); ap.add_argument('--root')
    a = ap.parse_args(argv)
    (run_proofs if a.mode == 'proofs' else run_gaps)(a.school, a.apply, a.root)


if __name__ == '__main__':
    sys.exit(main())
