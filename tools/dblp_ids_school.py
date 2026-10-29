"""DBLP person ids for a protocol school's census PIs, from DBLP's dump (never dblp.org): protocol stage 5.

candidates  every dump person record (<www key="homepages/...">) one of whose names has a PI's (given, family) pair
            (pi_hierarchy.Name forms: middle names and initials ignored, nicknames, compound family names), DBLP's
            homonym number set aside ('Lu Wang 0001')
decision    school_affiliation  exactly one candidate whose affiliation note matches the charter's affiliation regex or
                                one of whose URLs is on a school web domain (a disambiguated record names the school)
            unique_name         the only candidate (no homonym record carries the name) and it is not a disambiguation
                                profile; accepted only when its record names no other institution as current
                                (otherwise ambiguous)
            none                several candidates and none (or several) names the school, or the only candidate is a
                                disambiguation profile: identity then rests on OpenAlex ids, ORCID or advisees
evidence    url (https://dblp.org/pid/..., the person page the dump record is), the dump file, sha256 of the record's XML
            text as it stands in the dump, and the quote (the affiliation note that names the school, or the record's
            name line for unique_name)
-> hierarchy/<key>/dblp-ids.json {pi: {pid, basis, url, dump, sha256, quote, orcid, candidates}}; census_build.py folds
   pid and ORCID into the census (dblp, orcid)
usage: dblp_ids_school.py <key>        (one streamed pass over the dump, ~2 min; nice)
"""
import collections, hashlib, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pi_hierarchy import Name, toks  # noqa: E402
from dblp_dump_persons import records, text, AUTH, NOTE, URL  # noqa: E402

NOTE_AFF = re.compile(r'<note[^>]*type="affiliation"[^>]*>(.*?)</note>', re.S)


def main(key):
    cfg = S.get(key); aff = S.aff_rx(key)
    doms = [d.lower() for d in (cfg.get('web') or {}).get('domains') or []]
    xh = [d.lower() for d in (cfg.get('web') or {}).get('excluded_hosts') or []]
    census = json.loads((P.CENSUS / f'{key}-faculty.json').read_text())['faculty']
    pis = [x for x in census if x.get('is_pi')]
    by_fam = collections.defaultdict(list)
    for x in pis:
        N = Name([x['name']] + list(x.get('aliases') or []))
        for f, l in N.forms:
            by_fam[l].append((x['name'], N))
    cands = collections.defaultdict(list)
    t0 = time.time()
    for typ, k, body in records():
        if typ != 'www' or not k.startswith('homepages/'):
            continue
        ns = [text(a) for _, a in AUTH.findall(body)]
        hit = set()
        for n in ns:
            b = re.sub(r'\s+\d{4}$', '', n); t = toks(b)
            if len(t) < 2:
                continue
            for fam in {t[-1], t[0]}:
                for pi, N in by_fam.get(fam, ()):
                    if N.match(b):
                        hit.add(pi)
        if not hit:
            continue
        affs = [text(v) for v in NOTE_AFF.findall(body)]
        urls = [text(u) for u in URL.findall(body)]
        hosts = [re.sub(r'^https?://', '', u).split('/')[0].split(':')[0].lower() for u in urls]
        school_note = next((a for a in affs if aff.search(a)), None)
        school_url = next((u for u, h in zip(urls, hosts) if any(h == d or h.endswith('.' + d) for d in doms) and not any(h == x or h.endswith('.' + x) for x in xh)), None)
        rec = dict(pid='https://dblp.org/pid/' + k.split('/', 1)[1], names=ns, affiliations=affs, school_note=school_note, school_url=school_url,
                   orcid=sorted({m.group(1) for u in urls for m in [re.search(r'orcid\.org/([0-9X-]{19})', u)] if m}),
                   disambiguation=any(t_ == 'disambiguation' for t_, _ in NOTE.findall(body)),
                   sha256=hashlib.sha256(body.encode()).hexdigest())
        for pi in hit:
            cands[pi].append(rec)
    out, n = {}, collections.Counter()
    for x in pis:
        cs = cands.get(x['name'], [])
        sch = [c for c in cs if (c['school_note'] or c['school_url']) and not c['disambiguation']]
        d = None
        if len(sch) == 1:
            c = sch[0]; d = dict(c, basis='school_affiliation', quote=c['school_note'] or f"<url>{c['school_url']}</url>")
        elif len(cs) == 1 and not cs[0]['disambiguation'] and not [a for a in cs[0]['affiliations'] if not aff.search(a)]:
            c = cs[0]; d = dict(c, basis='unique_name', quote=c['names'][0])
        if d:
            out[x['name']] = dict(pid=d['pid'], basis=d['basis'], url=d['pid'], dump=P.DBLP_DUMP_FILE, sha256=d['sha256'], quote=d['quote'],
                                  orcid=d['orcid'], names=d['names'], candidates=len(cs))
        else:
            out[x['name']] = dict(pid=None, basis='none', candidates=len(cs), why='no candidate' if not cs else
                                  (f'{len(sch)} candidates name the school' if sch else f'{len(cs)} candidates, none names the school'),
                                  candidate_pids=[c['pid'] for c in cs][:8])
        n[out[x['name']]['basis']] += 1
    (P.HIERARCHY / key / 'dblp-ids.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(pis=len(pis), secs=round(time.time() - t0), **n)))


if __name__ == '__main__':
    main(sys.argv[1])
