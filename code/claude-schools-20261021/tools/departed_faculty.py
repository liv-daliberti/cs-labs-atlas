"""Departed-faculty review list (ROADMAP #26): PIs whose OpenAlex (bulk snapshot) or DBLP affiliation has moved elsewhere while our build still
has an OPEN period for them at the school. A review list only: it writes no overrides and changes no period. A confirmed departure goes into
census-overrides with dated quotes, as before.

Per PI with an open period (a period whose `end` is null) at school S, from the snapshot (tools/oa_snapshot.py):
  affiliations   the PI's OpenAlex author records (oaAuthorIds + reviewedOpenAlex; not the notOpenAlex / mixedOpenAlex ones): institutions with
                 the years OpenAlex lists them. `last_year_here` = the last year at one of S's charter institutions; `elsewhere_since` = the
                 first year after it with an affiliation at another institution; `latest_elsewhere` = the latest such year.
  works          the PI's works dated 2025-01-01 or later: how many carry S's lineage on the PI's own authorship and how many only another institution,
                 with up to 3 examples (id, date, institution names).
  dblp           the affiliation notes of the PI's DBLP person records (hierarchy/raw/dblp-dump-persons.json.gz), and whether any matches S's affiliation
                 regex.
Signals (each counts once): `snapshot_affiliation_moved` (last year here <= 2024 and an affiliation elsewhere in 2025 or later),
`recent_works_elsewhere` (>= 2 works since 2025 with another institution and none with S), `last_known_not_here` (OpenAlex last_known_institutions
exclude S), `dblp_affiliation_elsewhere` (DBLP notes exist and none matches S). Candidates have at least two signals, or the first one alone;
`--include` forces named PIs (e.g. Gupta, Platzer) into the list whatever their signals.
usage: departed_faculty.py [--schools a,b] [--include "Platzer,Gupta"] [--out FILE]
"""
import argparse, collections, gzip, json
from pathlib import Path

import atlas_paths as P  # noqa: E402
import oa_snapshot as S  # noqa: E402
import school_config as SC  # noqa: E402

RECENT = '2025-01-01'


def short(i):
    return (i or '').rsplit('/', 1)[-1]


def ours_ids(school):
    cfg = SC.get(school)
    return set(SC.sweep_ids(school)) - set(cfg['ids'].get('openalex_excluded') or [])


def affiliations(author, ours):
    """(last year here, first year elsewhere after it, latest year elsewhere, [(institution, years)])."""
    rows, here, away = [], set(), {}
    for a in author.get('affiliations') or []:
        inst = a.get('institution') or {}
        ids = {short(inst.get('id'))} | {short(x) for x in inst.get('lineage') or []}
        yrs = sorted(a.get('years') or [])
        rows.append((inst.get('display_name'), yrs))
        if ids & ours:
            here |= set(yrs)
        else:
            for y in yrs:
                away.setdefault(y, inst.get('display_name'))
    last_here = max(here) if here else None
    after = sorted(y for y in away if last_here is None or y > last_here)
    return last_here, (after[0] if after else None), (max(away) if away else None), rows


def recent_works(author_ids, ours):
    here = elsewhere = 0
    ex = []
    seen = set()
    for aid in author_ids:
        for w in S.works_by_author(aid):
            if w['id'] in seen or (w.get('publication_date') or '') < RECENT:
                continue
            seen.add(w['id'])
            for a in w.get('authorships') or []:
                if short((a.get('author') or {}).get('id')) != short(aid):
                    continue
                insts = a.get('institutions') or []
                ids = {short(i.get('id')) for i in insts} | {short(x) for i in insts for x in i.get('lineage') or []}
                if ids & ours:
                    here += 1
                elif insts:
                    elsewhere += 1
                    if len(ex) < 3:
                        ex.append(dict(work=w['id'], date=w.get('publication_date'), institutions=[i.get('display_name') for i in insts][:3]))
    return here, elsewhere, ex


def dblp_notes(pis_dblp, persons):
    out = []
    for u in pis_dblp or []:
        for pid, rec in persons.items():
            if pid == u or pid.rstrip('/') == u.rstrip('/'):
                out += rec.get('affiliations') or []
    return out


def run(schools, include):
    persons = {}
    p = P.data('dblp-dump-persons.json.gz')
    if Path(p).exists():
        persons = json.load(gzip.open(p, 'rt')).get('persons', {})
    out, stats = [], collections.Counter()
    for school in schools:
        ours, rx = ours_ids(school), SC.aff_rx(school)
        for pi in json.load(open(P.data('pis.json', school))):
            open_p = [x for x in pi.get('periods') or [] if not x.get('end')]
            forced = any(k.lower() in pi['pi'].lower() for k in include)
            if not open_p and not forced:
                continue
            stats['open_period_pis'] += 1
            skip = set(pi.get('notOpenAlex') or []) | set(pi.get('mixedOpenAlex') or [])
            ids = [short(a) for a in (pi.get('oaAuthorIds') or []) + (pi.get('reviewedOpenAlex') or []) if a not in skip]
            sig, affs, last_here, since, latest, last_known = [], [], None, None, None, []
            for aid in ids:
                a = S.author(aid)
                if not a:
                    continue
                lh, el, la, rows = affiliations(a, ours)
                affs += [dict(author=aid, institution=n, years=y) for n, y in rows if y][:12]
                last_here = max([x for x in (last_here, lh) if x] or [None]) if (last_here or lh) else None
                if el and (since is None or el < since):
                    since = el
                latest = max([x for x in (latest, la) if x] or [None]) if (latest or la) else None
                lk = [short(i.get('id')) for i in a.get('last_known_institutions') or []]
                last_known += [i.get('display_name') for i in a.get('last_known_institutions') or []]
                if lk and not (set(lk) & ours) and not any(set(short(x) for x in i.get('lineage') or []) & ours for i in a.get('last_known_institutions') or []):
                    sig.append('last_known_not_here')
            if last_here is not None and last_here <= 2024 and latest and latest >= 2025:
                sig.append('snapshot_affiliation_moved')
            wh, we, ex = recent_works(ids, ours)
            if we >= 2 and wh == 0:
                sig.append('recent_works_elsewhere')
            notes = dblp_notes(pi.get('dblp'), persons)
            if notes and not any(rx.search(n) for n in notes):
                sig.append('dblp_affiliation_elsewhere')
            sig = sorted(set(sig))
            if ('snapshot_affiliation_moved' in sig or len(sig) >= 2) or forced:
                out.append(dict(school=school, pi=pi['pi'], open_period_start=(open_p[0].get('start') if open_p else None), signals=sig,
                                last_year_here=last_here, elsewhere_since=since, latest_elsewhere=latest, last_known=sorted(set(last_known))[:4],
                                works_since_2025=dict(here=wh, elsewhere_only=we, examples=ex), dblp_notes=notes[:4],
                                affiliations=affs[:10], oa_author_ids=ids, forced=forced and not sig))
                stats[school] += 1
    out.sort(key=lambda r: (-len(r['signals']), r['school'], r['pi']))
    return out, dict(stats)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--schools'); ap.add_argument('--include', default='Platzer,Gupta'); ap.add_argument('--out')
    a = ap.parse_args()
    schools = a.schools.split(',') if a.schools else SC.keys()
    out, stats = run(schools, [x for x in a.include.split(',') if x])
    path = Path(a.out) if a.out else P.HIERARCHY / 'derived' / 'departed-faculty-review.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(built_at=__import__('time').strftime('%Y-%m-%dT%H:%M:%SZ', __import__('time').gmtime()), snapshot=S.snapshot_date(),
                                    note='A review list. No overrides are written; a confirmed departure needs dated quotes in census-overrides.', stats=stats, candidates=out),
                               indent=1, ensure_ascii=False))
    print(json.dumps(dict(stats, candidates=len(out), out=str(path))))


if __name__ == '__main__':
    main()
