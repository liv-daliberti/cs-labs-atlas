"""Check a protocol school's stage gates (docs/ADDING-A-SCHOOL.md) from the files the stages wrote, before the school is
wired into pi_hierarchy.py / chain_audit.py. Prints one JSON line per stage and the items that fail.

  1 sources   every department of the charter has an ok listing capture in every window year (listings/<key>/coverage.json);
              a missing year must carry a plan reason
  2 census    every CS-related candidate has a decision other than pending_openalex (hierarchy/<key>/cs-related-review.json),
              and every candidate is in the review
  3 pis       every census PI (and addition) has a PI basis with url + sha256 + quote, and an accepted home department
              (hierarchy/<key>/home-departments.json)
  4 periods   every PI has a reviewed period (periods/<key>-faculty-periods.json, census-overrides periods) or listing years
              that run without a gap from their first to their last listed year (a year with papers outside them is
              checked again at stage 7)
  5 identity  every PI has an anchor: a DBLP id, an ORCID or a reviewed OpenAlex id (census, additions, census-overrides)
usage: stage_gate.py <key> [stage ...]
"""
import collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def pis_of(key):
    cen = read(P.CENSUS / f'{key}-faculty.json', {}).get('faculty', [])
    add = read(P.CENSUS / f'{key}-additions.json', [])
    return [x for x in cen + add if x.get('is_pi')]


def g1(key):
    cov = read(P.LISTINGS / key / 'coverage.json', {}); lo, hi = S.get(key).get('window')
    bad = []
    for d in S.get(key).get('departments') or []:
        for y in range(lo, hi + 1):
            v = (cov.get(d['code']) or {}).get(str(y)) or {}
            if not any(s == 'ok' for s in v.values()):
                bad.append(f"{d['code']} {y}: " + ('; '.join(sorted(set(v.values()))) or 'never planned'))
    return bad, dict(departments=len(S.get(key).get('departments') or []))


def g2(key):
    cands = read(P.HIERARCHY / key / 'cs-related-candidates.json', [])
    rev = read(P.HIERARCHY / key / 'cs-related-review.json', {}) or {}
    dec = {d['name']: d for d in rev.get('decisions', [])}
    bad = [f"{c['name']}: no decision" for c in cands if c['name'] not in dec and not any(a in dec for a in c.get('aliases') or [])]
    bad += [f"{d['name']}: {d['decision']} ({d['reason'][:100]})" for d in dec.values() if d['decision'] == 'pending_openalex']
    return bad, dict(candidates=len(cands), **collections.Counter(d['decision'] for d in dec.values()))


def g3(key):
    homes = {r['name']: r for r in read(P.HIERARCHY / key / 'home-departments.json', [])}
    bad = []
    for x in pis_of(key):
        b = x.get('pi_basis') or {}
        if not (b.get('url') and b.get('sha256') and b.get('quote')):
            bad.append(f"{x['name']}: PI basis without url/sha256/quote")
        h = homes.get(x['name'])
        if not h or h.get('status') != 'accepted' or not h.get('home_department'):
            bad.append(f"{x['name']}: no accepted home department")
    return bad, dict(pis=len(pis_of(key)), homes=len(homes))


def g4(key):
    per = read(P.PERIODS / f'{key}-faculty-periods.json', [])
    ov = (read(P.HIERARCHY / 'census-overrides.json', {}) or {}).get(key, {})
    have = {p['name'] for p in per} | {k for k, v in ov.items() if isinstance(v, dict) and v.get('periods')}
    bad, n = [], collections.Counter()
    for x in pis_of(key):
        if x['name'] in have:
            n['period'] += 1; continue
        ys = sorted(set(x.get('years_listed') or []))
        if ys and ys == list(range(ys[0], ys[-1] + 1)):
            n['contiguous_listings'] += 1; continue
        bad.append(f"{x['name']}: no period, listing years {ys}")
    return bad, dict(n)


def g5(key):
    ov = (read(P.HIERARCHY / 'census-overrides.json', {}) or {}).get(key, {})
    bad, n = [], collections.Counter()
    for x in pis_of(key):
        o = ov.get(x['name']) or {}
        a = [k for k, v in (('dblp', x.get('dblp') or o.get('dblp')), ('orcid', x.get('orcid') or o.get('orcid')),
                            ('openalex', x.get('openalex') or o.get('openalex'))) if v]
        if a:
            n['+'.join(a)] += 1
        else:
            bad.append(f"{x['name']}: no DBLP id, ORCID or reviewed OpenAlex id")
    return bad, dict(n)


GATES = {'1': g1, '2': g2, '3': g3, '4': g4, '5': g5}

if __name__ == '__main__':
    key, stages = sys.argv[1], sys.argv[2:] or list(GATES)
    ok = True
    for st in stages:
        bad, counts = GATES[st](key)
        ok &= not bad
        print(json.dumps(dict(stage=int(st), gate='pass' if not bad else 'fail', open=len(bad), **counts)))
        for b in bad[:int(__import__('os').environ.get('SHOW', 15))]:
            print('   ', b)
    sys.exit(0 if ok else 1)
