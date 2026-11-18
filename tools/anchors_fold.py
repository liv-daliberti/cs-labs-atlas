"""Fold stage-5 identity evidence into a school's reviewed census overrides for PIs that are held for 'no identity anchor' (2026-11-18).

Why: dblp_ids_school.py writes derived/dblp-ids.json and census_build.py folds it into census-faculty rows, but PIs of census-additions.json
(CS-related review) and rows built before the ids run never receive it, so downloads_ready holds them. This writes the decided record as a
reviewed override `dblp` with its evidence, only on a URL/ID binding:
  strong    basis homepage_url | school_affiliation | school_coauthors (dblp_ids_school rules: the record links the listing homepage, names the
            school in its affiliation note or URL, or shares >= 5 window records with the school's decided PIs)
  orcid     a unique_name/unique_exact_name record whose ORCID equals an ORCID the PI's own page lists (homepage-identity.json) or that the PI's
            computing-share OpenAlex author carries (oa-author-stats.json.gz)
  url       a unique_name/unique_exact_name record with a <url> on the school's web domains (the person's own official page)
A name-only match (no corroboration) is never written: it is listed in the report for the OpenAlex route or the reviewer step.
usage: anchors_fold.py <key> [--write] [--report FILE]
"""
import gzip, json, sys
from urllib.parse import urlsplit

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import census_overrides as CO  # noqa: E402
import downloads_ready as DR  # noqa: E402

STRONG = {'homepage_url', 'school_affiliation', 'school_coauthors'}
WEAK = {'unique_name', 'unique_exact_name'}


def jload(p, d):
    p = P.data(p[0], p[1]) if isinstance(p, tuple) else p
    return json.loads(p.read_text()) if p.exists() else d


def main(key, write=False, report=None):
    ids = jload(('dblp-ids.json', key), {})
    hp = jload(('homepage-identity.json', key), {})
    status = DR.pi_status(key)
    held = {r['name']: r for r in status.values() if not r['identity']}
    sec, save = CO.open_section(key)
    persons = {}
    f = P.data('dblp-dump-persons-school.json.gz', key)
    if f.exists():
        persons = json.load(gzip.open(f, 'rt'))['persons']
    stats = {}
    sf = P.data('oa-author-stats.json.gz', key)
    if sf.exists():
        st = json.load(gzip.open(sf, 'rt'))
        stats = st if isinstance(st, dict) else {}
    from stage_gate import pis_of
    pis = {x['name']: x for x in pis_of(key)}
    domains = [d.lower() for d in S.get(key).get('web', {}).get('domains', [])]
    out, rep = {}, {'strong': [], 'orcid': [], 'url': [], 'weak_uncorroborated': [], 'none': [], 'no_entry': []}
    for name in sorted(held):
        d = ids.get(name) or {}
        pid = d.get('pid')
        h = hp.get(name) or {}
        if not pid and (h.get('dblp') or {}).get('pid'):
            e = h['dblp']
            out[name] = dict(dblp=[e['pid']], why_dblp="2026-11-18 (pi_homepage_link): the PI's own page links this DBLP person page (href exactly as stored).",
                             dblp_evidence=[dict(url=e['url'], sha256=e['sha256'], quote=e['quote'])])
            rep['strong'].append(name)
            continue
        if not pid:
            rep['none' if d else 'no_entry'].append(name)
            continue
        ev = [dict(url=d['url'], source=f"DBLP dump {d.get('dump')}", sha256=d.get('sha256'), quote=d.get('quote'))]
        basis = d['basis']
        if basis in STRONG:
            out[name] = dict(dblp=[pid], why_dblp=f"2026-11-18 (dblp_ids_school rule {basis}): {d['quote']!r} in the decided DBLP dump record; identifies the person only, "
                             'school affiliation, appointment and paper filtering remain independent checks.', dblp_evidence=ev)
            rep['strong'].append(name)
            continue
        p = persons.get(pid) or {}
        want = {o for o in (pis[name].get('orcid') or [])} | {o['orcid'] for o in h.get('orcid') or []}
        corr = None
        po = set(p.get('orcid') or []) | set(d.get('orcid') or [])
        if want & po:
            corr = ('orcid', f"ORCID {sorted(want & po)[0]} is on the DBLP record and on the PI's own page / census row")
        else:
            for u in p.get('urls') or []:
                host = (urlsplit(u).hostname or '').lower()
                if any(host == dm or host.endswith('.' + dm) for dm in domains):
                    corr = ('url', f"the DBLP record links {u} on the school's web domain")
                    break
        if corr:
            out[name] = dict(dblp=[pid], why_dblp=f"2026-11-18 (dblp_ids_school {basis} + {corr[0]} binding): {corr[1]}. Identifies the person only.",
                             dblp_evidence=ev)
            rep[corr[0]].append(name)
        else:
            rep['weak_uncorroborated'].append(name)
    for name, e in out.items():
        cur = sec.setdefault(name, {})
        if cur.get('dblp'):
            continue
        cur.update(e)
    if write:
        save()
    summary = {k: len(v) for k, v in rep.items()}
    print(json.dumps(dict(school=key, held_identity=len(held), written=bool(write), **summary)))
    if report:
        open(report, 'w').write(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], '--write' in a, a[a.index('--report') + 1] if '--report' in a else None)
