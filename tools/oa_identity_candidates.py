"""Proposed OpenAlex author ids for the PIs that stage 5's DBLP / ORCID pass left without an identity (protocol stage 5; Georgia Tech: 91 of 454).

For each such PI, the authors of hierarchy/<key>/oa-author-stats.json.gz (every OpenAlex author id with 3+ school papers) whose raw names match the PI: same family name, the
first given name spelled out equal (or an initial / nickname-compatible only when the PI's own given name is an initial), middle initials not in conflict. A PI with exactly one
matching author of at least MIN_WORKS school works, who also publishes in the PI's listed years, is `accepted` automatically (`auto: true` in the review file, with the works,
years, raw names, ORCID and top venues as `why`: the evidence a hand review would cite). A PI with several matches, a namesake-looking one (another ORCID than the PI's, works ending
before the first listing) or none goes to `ambiguous` / `unmatched` for the hand review.
-> hierarchy/<key>/openalex-identity-proposals.json {auto, ambiguous, unmatched}; with --write the auto entries are merged into
   hierarchy/<key>/openalex-identity-review.json (hand decisions already in it are never replaced), which tools/oa_identity_school.py reads.
A second pass covers the authors below MIN_WORKS (oa-author-stats keeps only 3+ school works): for a PI the first pass leaves unmatched or ambiguous, the sweep is scanned once for
school-affiliated authorships whose raw name matches the PI by the strict full-name rule and whose author record carries an ORCID; such an author is proposed even with 1-2 works
(UMD Zia Khan 2026-11-25: OpenAlex A5089152025, 2 school works, was missed and the PI was recorded no_identity). `--holds` also re-examines the PIs a hand review recorded
`no_identity` / `no_papers`, to find ids those holds missed.
usage: oa_identity_candidates.py <key> [--write] [--holds]
"""
import collections, gzip, json, re, sys, unicodedata

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pi_hierarchy import NOT_PAPERS  # noqa: E402

MIN_WORKS = 3
DOMINANT_MIN, DOMINANCE = 20, 5   # several name matches: the first is taken when it has >= 20 school works and >= 5x the next one's
SUFFIX = {'jr', 'sr', 'ii', 'iii', 'iv'}


def toks(n):
    n = unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower()
    n = re.sub(r'\([^)]*\)', ' ', n)
    return [t for t in re.sub(r'[^a-z\- ]', ' ', n).replace('-', ' ').split() if t not in SUFFIX]


def name_match(pi, raw, strict=False):
    """Same family name and a compatible given name: spelled-out first names must be equal (a prefix of 3+ letters is a nickname: 'Beki'/'Rebecca' is NOT assumed), initials match initials."""
    a, b = toks(pi), toks(raw)
    if len(a) < 2 or len(b) < 2 or a[-1] != b[-1]:
        return False
    fa, fb = a[0], b[0]
    if strict and len(fb) == 1 and len(fa) > 1:   # strict: a spelled-out PI name needs a spelled-out raw name
        return False
    if len(fa) == 1 or len(fb) == 1:
        if fa[0] != fb[0]:
            return False
    elif fa != fb:
        return False
    ma, mb = [t for t in a[1:-1]], [t for t in b[1:-1]]
    if ma and mb and ma[0][0] != mb[0][0]:   # conflicting middle initials
        return False
    return True


def propose(pis, authors, min_works=MIN_WORKS, need_orcid=False, strict_name=False, name_only='bind'):
    """-> (auto {name: entry}, ambiguous {name: [candidate summaries]}, unmatched [names]). pis: [{name, aliases, orcid, years_listed}].
    name_only = 'propose' ([identity] in the charter, KAIST D-0064): a unique name match is never `auto`; it needs an identifier (the author id carries the PI's ORCID) and otherwise
    goes to `ambiguous` with held_name_only = True, to be decided by hand against homepage/email/coauthor evidence."""
    auto, amb, un = {}, {}, []
    for x in pis:
        names = [x['name']] + list(x.get('aliases') or [])
        orc = {o.replace('https://orcid.org/', '') for o in x.get('orcid') or []}
        fy = min(x.get('years_listed') or [2016])
        cands = []
        for aid, a in authors.items():
            if a['n'] < min_works or (need_orcid and not a.get('orcids')):
                continue
            raws = a.get('raw') or {}
            if not any(name_match(nm, r, strict=strict_name) for nm in names for r in raws):
                continue
            ao = set(a.get('orcids') or {})
            namesake = bool(orc and ao and not (orc & ao)) or (a.get('years') and max(a['years']) < fy)
            cands.append(dict(id=aid, n=a['n'], years=[min(a['years']), max(a['years'])] if a.get('years') else [], raw=sorted(raws, key=raws.get, reverse=True)[:3],
                              orcids=sorted(ao), venues=list((a.get('venues') or {}))[:4], namesake=bool(namesake)))
        # a candidate must also be named by its most frequent raw name (not only by an initial form such as 'J.-Y. Kim' for a 'Jennifer Kim')
        for c in cands:
            c['top_match'] = any(name_match(nm, c['raw'][0], strict=True) for nm in names)
        good = sorted((c for c in cands if not c['namesake'] and c['top_match']), key=lambda c: -c['n'])
        if len(good) > 1 and good[0]['n'] >= DOMINANT_MIN and good[0]['n'] >= DOMINANCE * good[1]['n']:
            good = good[:1]   # one author carries the name; the others are small namesakes
        if not cands:
            un.append(x['name'])
        elif len(good) == 1 and name_only == 'propose' and not (orc & set(good[0]['orcids'])):
            amb[x['name']] = [dict(good[0], held_name_only=True)]
        elif len(good) == 1:
            c = good[0]
            auto[x['name']] = dict(openalex=[c['id']], auto=True, why=f"unique name match under family name and first given name among the school's OpenAlex authors: {c['n']} school works {c['years'][0]}-{c['years'][1]}, "
                                   f"raw names {c['raw']}, ORCID {c['orcids'] or 'none'}, venues {c['venues']}; {len(cands) - 1} other name match(es) set aside (other ORCID, ended before the first listing, an initial-only name, or under a fifth of the works)")
        else:
            amb[x['name']] = cands
    return auto, amb, un


def low_volume_authors(key, pis):
    """{author id: stats-shaped entry} of the school-affiliated authors that carry an ORCID and have fewer than MIN_WORKS school works, whose raw name matches one of `pis`
    (strict full-name rule). One pass over the sweep (as oa_identity_school.evidence does)."""
    from cs_related_candidates import works, school_test
    at_school = school_test(key)
    names = [[x['name']] + list(x.get('aliases') or []) for x in pis]
    fams = {toks(n)[-1] for ns in names for n in ns if len(toks(n)) > 1}
    out = {}
    for w in works(key):
        if w.get('type') in NOT_PAPERS:
            continue
        for a in w.get('authorships') or []:
            au = a.get('author') or {}
            raw = a.get('raw_author_name') or au.get('display_name') or ''
            if not au.get('id') or not au.get('orcid') or not (set(toks(raw)) & fams) or not at_school(a):
                continue
            if not any(name_match(n, raw, strict=True) for ns in names for n in ns):
                continue
            e = out.setdefault(au['id'], dict(n=0, years=set(), raw=collections.Counter(), orcids=collections.Counter(), venues=collections.Counter()))
            e['n'] += 1; e['years'].add(w.get('publication_year')); e['raw'][raw] += 1; e['orcids'][au['orcid'].rsplit('/', 1)[-1]] += 1
            v = ((w.get('primary_location') or {}).get('source') or {}).get('display_name')
            if v:
                e['venues'][v] += 1
    return {k: dict(n=e['n'], years=sorted(y for y in e['years'] if y), raw=dict(e['raw']), orcids=dict(e['orcids']), venues=dict(e['venues'])) for k, e in out.items() if e['n'] < MIN_WORKS}


def main(key, write=False, holds=False):
    stats = json.load(gzip.open(P.data('oa-author-stats.json.gz', key), 'rt'))['authors']
    import stage_gate as SG
    open_names = {re.split(r': (?:no DBLP id|anchors yield 0 papers)', b)[0] for b in SG.g5(key)[0]}
    if holds:   # PIs a hand review recorded no_identity / no_papers: look again
        import census_overrides as CO
        open_names |= {n for n, o in CO.section(key).items() if o.get('no_identity') or o.get('no_papers')}
    cen = {x['name']: x for x in json.loads(P.data('census-faculty.json', key).read_text())['faculty']}
    add = {x['name']: x for x in json.loads(P.data('census-additions.json', key).read_text())} if P.data('census-additions.json', key).exists() else {}
    pis = [cen.get(n) or add.get(n) for n in sorted(open_names)]
    idc = (S.get(key).get('identity') or {})
    pis = [x for x in pis if x]
    auto, amb, un = propose(pis, stats, name_only=idc.get('name_only', 'bind'))
    rest = [x for x in pis if x['name'] not in auto]   # second pass: authors below MIN_WORKS with an ORCID, full name matching
    if rest:
        low = low_volume_authors(key, rest)
        a2, m2, _ = propose(rest, low, min_works=1, need_orcid=True, strict_name=True, name_only=idc.get('name_only', 'bind'))
        for n, e in a2.items():
            e['why'] = 'LOW-VOLUME PASS (1-2 school works): ' + e['why']
        auto.update(a2); amb = {n: v for n, v in {**amb, **m2}.items() if n not in a2}; un = [n for n in un if n not in a2]
    P.data_w('openalex-identity-proposals.json', key).write_text(json.dumps(dict(auto=auto, ambiguous=amb, unmatched=un), indent=1, ensure_ascii=False))
    if write:
        rf = P.data_w('openalex-identity-review.json', key)
        cur = json.loads(rf.read_text()) if rf.exists() else {'decisions': {}}
        for n, e in auto.items():
            cur['decisions'].setdefault(n, e)
        rf.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    print(json.dumps(dict(open=len(open_names), auto=len(auto), ambiguous=len(amb), unmatched=len(un))))


if __name__ == '__main__':
    main(sys.argv[1], '--write' in sys.argv, '--holds' in sys.argv)
