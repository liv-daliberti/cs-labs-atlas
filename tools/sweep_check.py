"""Sanity check of a school's bulk pulls (protocol stages 0/2/7 inputs; owner standard 2026-10-30, after Michigan's 2022).

openalex  hierarchy/<school>/openalex-sweep.sqlite (tools/oa_sweep.py), read-only:
            years        per publication year: stored works, distinct work ids, papers (types outside
                         pi_hierarchy.NOT_PAPERS), the API's meta count, and whether every page was stored
                         (sum of n == meta count; a paged sweep has no single count and is not tested)
            duplicates   rate of repeated work ids (rows / distinct - 1) and of DOIs carried by 2+ distinct works
            outliers     a year above RATIO x the median of the other years (or below 1/RATIO; the current year is
                         exempt on the low side, being partial), or with a robust z-score |x - median| / (1.4826 MAD)
                         above ZMAX (MAD floored at MAD_FLOOR x median), over the raw counts
            institutions the share of works with an authorship whose institution (lineage) is one of the charter's
                         sweep ids (lineage + related) must be >= INST_MIN, and every charter lineage id must occur
dblp      the school's PIs' records in hierarchy/dblp-dump-persons.json.gz (tools/dblp_dump_persons.py) and
          hierarchy/<school>/dblp-affiliated.json (tools/dblp_affiliated.py) when present: the dump file is the one
          atlas_paths names; per-year record counts with the same outlier test; duplicate record keys and DOIs per
          person; the affiliated persons' notes match the charter's regex
exceptions a test that trips fails the check unless the charter's [sweep_check].exceptions holds a reviewed exception
          {test, year?, reason, verify?} for it. verify = "papers_normal" means the exception holds only while the
          paper-only count of that year passes the outlier test (the excess is non-papers, which every reader drops).
-> hierarchy/<school>/sweep-check.json; exit 1 when the check fails.
usage: sweep_check.py <school> [<school> ...]
"""
import collections, gzip, json, sqlite3, statistics, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402

NOT_PAPERS = {'dataset', 'paratext', 'peer-review', 'erratum', 'supplementary-materials', 'other', 'grant', 'standard', 'retraction',
              'reference-entry', 'libguides'}  # = pi_hierarchy.NOT_PAPERS (asserted in tests; not imported, to keep this light)
RATIO, ZMAX, DUP_MAX, DOI_DUP_MAX, INST_MIN = 3.0, 8.0, 0.001, 0.02, 0.98
MAD_FLOOR = 0.05  # the MAD is at least 5% of the median: Princeton's 2016 (5.5k against 7.0k, MAD 128) is a trend, not an outlier
OA = 'https://openalex.org/'


def outliers(counts, current_year=None):
    """{year: why} for years whose count is off: RATIO x the median of the other years, or a robust z above ZMAX."""
    out = {}
    ys = sorted(counts)
    for y in ys:
        others = [counts[o] for o in ys if o != y]
        if len(others) < 3:
            continue
        med = statistics.median(others)
        mad = max(statistics.median([abs(v - med) for v in others]), MAD_FLOOR * med, 1.0)  # a steady series has a tiny MAD
        z = (counts[y] - med) / (1.4826 * mad)
        if med and counts[y] > RATIO * med:
            out[y] = f'{counts[y]} > {RATIO:g} x median {med:g} of the other years'
        elif med and counts[y] < med / RATIO and y != current_year:
            out[y] = f'{counts[y]} < median {med:g} / {RATIO:g}'
        elif abs(z) > ZMAX and not (z < 0 and y == current_year):
            out[y] = f'robust z {z:.1f} (median {med:g}, MAD {mad:g})'
    return out


def check_openalex(db, sweep_ids, lineage_ids, current_year):
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    paged = bool(c.execute("select count(*) from sqlite_master where name='windows'").fetchone()[0])
    years = collections.defaultdict(lambda: collections.Counter())
    meta = {y: (n, cnt) for y, n, cnt in c.execute('select year, sum(n), max(count) from pages group by year')}
    ids, dois = collections.Counter(), collections.defaultdict(set)
    inst_hit, inst_seen, total = 0, collections.Counter(), 0
    for y, b in c.execute('select year, body from pages'):
        try:
            b = zlib.decompress(b)
        except zlib.error:
            pass
        for w in json.loads(b):
            total += 1; ids[w['id']] += 1
            yy = years[w.get('publication_year') or y]
            yy['stored'] += 1; yy['papers'] += w.get('type') not in NOT_PAPERS
            if w.get('doi'):
                dois[w['doi'].lower()].add(w['id'])
            hit = False
            for a in w.get('authorships') or []:
                for x in a.get('institutions') or []:
                    lin = {i.replace(OA, '') for i in (x.get('lineage') or [x.get('id') or ''])}
                    if lin & sweep_ids:
                        hit = True; inst_seen.update(lin & sweep_ids)
            inst_hit += hit
    distinct = len(ids)
    res = dict(db=str(db), works=total, distinct=distinct, paged=paged,
               years={str(y): dict(stored=v['stored'], papers=v['papers'], meta_count=(meta.get(y) or (None, None))[1],
                                   complete=None if paged else ((meta.get(y) or (None, None))[0] == (meta.get(y) or (None, None))[1]))
                      for y, v in sorted(years.items())},
               dup_id_rate=round(total / distinct - 1, 6) if distinct else 0.0,
               dup_doi_rate=round(sum(1 for v in dois.values() if len(v) > 1) / len(dois), 6) if dois else 0.0,
               inst_share=round(inst_hit / total, 6) if total else 0.0, inst_seen=dict(inst_seen))
    raw = {int(y): v['stored'] for y, v in res['years'].items()}
    pap = {int(y): v['papers'] for y, v in res['years'].items()}
    trips = []
    for y, why in outliers(raw, current_year).items():
        trips.append(dict(test='year_outlier', year=y, why=why, papers_outlier=y in outliers(pap, current_year)))
    for y, v in res['years'].items():
        if v['complete'] is False:
            trips.append(dict(test='year_incomplete', year=int(y), why=f"stored {meta[int(y)][0]} of meta count {v['meta_count']}"))
    if res['dup_id_rate'] > DUP_MAX:
        trips.append(dict(test='duplicate_ids', why=f"{res['dup_id_rate']:.4f} > {DUP_MAX}"))
    if res['dup_doi_rate'] > DOI_DUP_MAX:
        trips.append(dict(test='duplicate_dois', why=f"{res['dup_doi_rate']:.4f} > {DOI_DUP_MAX}"))
    if res['inst_share'] < INST_MIN:
        trips.append(dict(test='institutions', why=f"{res['inst_share']:.4f} of works carry a charter id (< {INST_MIN})"))
    for i in lineage_ids:
        if not inst_seen.get(i):
            trips.append(dict(test='institutions', why=f'charter lineage id {i} occurs on no work'))
    res['trips'] = trips
    return res


def check_dblp(key, pis_dblp):
    out = dict(dump_expected=P.DBLP_DUMP_FILE)
    f = P.HIERARCHY / 'dblp-dump-persons.json.gz'
    trips = []
    if f.exists() and pis_dblp:
        d = json.load(gzip.open(f, 'rt'))
        out['dump'] = d.get('dump')
        if d.get('dump') != P.DBLP_DUMP_FILE:
            trips.append(dict(test='dblp_dump', why=f"dump-persons file is from {d.get('dump')}, not {P.DBLP_DUMP_FILE}"))
        per = d['persons']; years = collections.Counter(); dk = dd = n = 0; missing = 0
        for pid in pis_dblp:
            p = per.get(pid)
            if not p:
                missing += 1; continue
            keys = collections.Counter(x['key'] for x in p.get('pubs') or [])
            dk += sum(v - 1 for v in keys.values())
            doi = collections.Counter(q.lower() for x in p.get('pubs') or [] for q in x.get('dois') or [])
            dd += sum(v - 1 for v in doi.values())
            for x in p.get('pubs') or []:
                n += 1
                if 2016 <= (x.get('year') or 0) <= 2026:
                    years[x['year']] += 1
        out.update(pis_with_dblp=len(pis_dblp), missing_in_dump=missing, records=n, years={str(y): v for y, v in sorted(years.items())},
                   dup_key_rate=round(dk / n, 6) if n else 0.0, dup_doi_rate=round(dd / n, 6) if n else 0.0)
        for y, why in outliers(dict(years), S.get(key).get('window', [2016, 2026])[1]).items():
            trips.append(dict(test='dblp_year_outlier', year=y, why=why))
        if out['dup_key_rate'] > DUP_MAX:
            trips.append(dict(test='dblp_duplicate_keys', why=f"{out['dup_key_rate']:.4f}"))
        if missing:
            trips.append(dict(test='dblp_missing_persons', why=f'{missing} PI DBLP ids are not in dblp-dump-persons.json.gz'))
    fa = P.HIERARCHY / key / 'dblp-affiliated.json'
    if fa.exists():
        a = json.loads(fa.read_text()); rx = S.aff_rx(key)
        notes = [x['text'] for p in a.get('persons', []) for x in p.get('affiliations') or [] if 'affiliation_note' in (p.get('matched_by') or [])]
        bad = [t for t in notes if not rx.search(t)]
        out['affiliated'] = dict(dump=a.get('dump'), persons=len(a.get('persons', [])), notes=len(notes), notes_not_matching_regex=len(bad))
        if a.get('dump') and a['dump'] != P.DBLP_DUMP_FILE:
            trips.append(dict(test='dblp_dump', why=f"dblp-affiliated.json is from {a['dump']}"))
    out['trips'] = trips
    return out


def apply_exceptions(trips, exc):
    """(failed, excused): a trip is excused by a reviewed exception {test, year?, reason, verify?} of the charter."""
    failed, excused = [], []
    for t in trips:
        e = next((e for e in exc if e.get('test') == t['test'] and e.get('year') in (None, t.get('year')) and e.get('reason')), None)
        if e and e.get('verify') == 'papers_normal' and t.get('papers_outlier', True):
            e = None  # the stated cause does not explain it: the papers alone are off too
        (excused if e else failed).append(dict(t, **({'exception': e['reason']} if e else {})))
    return failed, excused


def run(key, write=True):
    cfg = S.get(key)
    exc = list(S.field(cfg, 'sweep_check.exceptions') or [])
    cur = (cfg.get('window') or [2016, 2026])[1]
    res = dict(school=key, thresholds=dict(ratio=RATIO, zmax=ZMAX, dup_id=DUP_MAX, dup_doi=DOI_DUP_MAX, inst_min=INST_MIN))
    db = P.HIERARCHY / key / 'openalex-sweep.sqlite'
    res['openalex'] = check_openalex(db, set(S.sweep_ids(key)), S.inst_ids(key), cur) if db.exists() else dict(missing=str(db), trips=[dict(test='no_sweep', why='no sweep')])
    pis_dblp = set()
    for f in (P.HIERARCHY / key / 'pis.json',):
        if f.exists():
            pis_dblp |= {d for p in json.loads(f.read_text()) for d in p.get('dblp') or []}
    res['dblp'] = check_dblp(key, pis_dblp)
    failed, excused = apply_exceptions(res['openalex']['trips'] + res['dblp']['trips'], exc)
    res.update(failed=failed, excused=excused, status='pass' if not failed else 'fail')
    if write:
        (P.HIERARCHY / key / 'sweep-check.json').write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


if __name__ == '__main__':
    ok = True
    for k in sys.argv[1:]:
        r = run(k)
        ok &= r['status'] == 'pass'
        print(json.dumps(dict(school=k, status=r['status'], failed=r['failed'], excused=[(x['test'], x.get('year')) for x in r['excused']],
                              works=r['openalex'].get('works'), dup_id_rate=r['openalex'].get('dup_id_rate'), dup_doi_rate=r['openalex'].get('dup_doi_rate'),
                              inst_share=r['openalex'].get('inst_share'), dblp_records=r['dblp'].get('records'))), flush=True)
    sys.exit(0 if ok else 1)
