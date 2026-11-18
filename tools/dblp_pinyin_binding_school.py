"""DBLP person ids for Han-name census people by UNIQUE pinyin full-name match + school affiliation note (owner D-0010, 2026-11-18, Q-0352).

Identity, medium confidence, covered by the 50-row identity audit: a census person (Han roster name, no DBLP id yet) is bound to a DBLP person record when
  (a) the record's name (homonym number set aside) equals the pinyin of the Han name in either order (family syllable(s) + given syllables, joined),
  (b) the record's `<note type="affiliation">` matches the school's affiliation regex (or a record URL is on a school web domain),
  (c) exactly ONE such record exists for that name, and exactly ONE census person's Han name has that pinyin key (no homophone pair on either side).
Nothing else: not a name-only join across schools, and a record without the school in its note never counts. Existing pids are never overwritten.

  dblp_pinyin_binding_school.py <key> [<key> ...]    one streamed pass over the dump; merges into hierarchy/<key>/dblp-ids.json
     {person: {pid, basis: 'pinyin_unique_affiliation', confidence: 'medium', url, dump, sha256, quote, orcid, names, candidates, n_window, roster_evidence}}
"""
import collections, hashlib, json, re, sys, unicodedata

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from dblp_dump_persons import records, text, AUTH, URL, YEAR  # noqa: E402

HAN = re.compile(r'^[㐀-鿿]{2,5}$')
NOTE_AFF = re.compile(r'<note[^>]*type="affiliation"[^>]*>(.*?)</note>', re.S)


def fold(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z]', '', ''.join(c for c in s if not unicodedata.combining(c)).lower())


def keys_of(han):
    """The joined pinyin strings a Latin rendering of the Han name can take (family 1 or 2 syllables, either order; polyphonic first character tried in every reading)."""
    from pypinyin import lazy_pinyin, pinyin
    han = ''.join(han.split())
    if not HAN.match(han):
        return set()
    rest = [x for x in lazy_pinyin(han[1:])]
    firsts = {r for rr in pinyin(han[0], heteronym=True) for r in rr}
    out = set()
    for f in firsts:
        syl = [f] + rest
        for k in (1, 2):
            if len(syl) > k:
                fam, giv = ''.join(syl[:k]), ''.join(syl[k:])
                out |= {fold(fam + giv), fold(giv + fam)}
    if len(han) >= 4:   # compound family name read with the first two characters
        syl = lazy_pinyin(han)
        out |= {fold(''.join(syl[:2]) + ''.join(syl[2:])), fold(''.join(syl[2:]) + ''.join(syl[:2]))}
    return out


def bind(people, recs):
    """people: [{name, evidence}] without a pid; recs: [{pid, names, school_note, sha256, ...}] school-affiliated DBLP persons. -> [(person, rec, key)]"""
    by_key = collections.defaultdict(set)
    for p in people:
        for k in keys_of(p['name']):
            by_key[k].add(p['name'])
    rec_keys = collections.defaultdict(dict)
    for r in recs:
        for nm in r['names']:
            k = fold(re.sub(r'\s+\d{4}$', '', nm))
            rec_keys[k][r['pid']] = r
    out = []
    for p in people:
        hits = {}
        for k in keys_of(p['name']):
            if len(by_key[k]) == 1:
                hits.update(rec_keys.get(k, {}))
            elif k in rec_keys:
                hits = {}   # a roster homophone pair: nobody is bound by this key
                break
        if len(hits) == 1:
            r = next(iter(hits.values()))
            out.append((p['name'], r))
    return out


def main(keys):
    cfgs = {k: (S.get(k), S.aff_rx(k)) for k in keys}
    people = {}
    for k in keys:
        cen = json.loads(P.data('census-faculty.json', k).read_text())['faculty']
        ids = json.loads(P.data('dblp-ids.json', k).read_text()) if P.data('dblp-ids.json', k).exists() else {}
        rows = json.loads(P.data('rows.json', k).read_text())
        ev = {}
        for r in rows:
            ev.setdefault(r['name'], dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote']))
        people[k] = [dict(name=x['name'], evidence=ev.get(x['name'])) for x in cen if HAN.match(''.join(x['name'].split())) and not (ids.get(x['name']) or {}).get('pid')]
    recs = {k: [] for k in keys}
    for typ, key, body in records():
        if typ != 'www' or not key.startswith('homepages/'):
            continue
        affs = [text(v) for v in NOTE_AFF.findall(body)]
        for k in keys:
            cfg, aff = cfgs[k]
            note = next((a for a in affs if aff.search(a)), None)
            doms = [d.lower() for d in (cfg.get('web') or {}).get('domains') or []]
            urls = [text(u) for u in URL.findall(body)]
            hosts = [re.sub(r'^https?://', '', u).split('/')[0].split(':')[0].lower() for u in urls]
            sch_url = next((u for u, h in zip(urls, hosts) if any(h == d or h.endswith('.' + d) for d in doms)), None)
            if note or sch_url:
                recs[k].append(dict(pid='https://dblp.org/pid/' + key.split('/', 1)[1], names=[text(a) for _, a in AUTH.findall(body)], school_note=note or f'<url>{sch_url}</url>',
                                    orcid=sorted({m.group(1) for u in urls for m in [re.search(r'orcid\.org/([0-9X-]{19})', u)] if m}), sha256=hashlib.sha256(body.encode()).hexdigest()))
    for k in keys:
        bound = bind(people[k], recs[k])
        lo, hi = cfgs[k][0].get('window') or [2016, 2026]
        owner = {nm: r['pid'] for _, r in bound for nm in r['names']}
        k_cnt = collections.Counter()
        for typ, key, body in records():
            if typ in ('www', 'data'):
                continue
            hit = {owner[a] for _, a in AUTH.findall(body) for a in [text(a)] if a in owner}
            y = YEAR.search(body)
            if hit and y and lo <= int(y.group(1)) <= hi:
                for p in hit:
                    k_cnt[p] += 1
        path = P.data_w('dblp-ids.json', k)
        cur = json.loads(path.read_text()) if path.exists() else {}
        ev = {p['name']: p['evidence'] for p in people[k]}
        n = 0
        for person, r in bound:
            if (cur.get(person) or {}).get('pid'):
                continue
            cur[person] = dict(pid=r['pid'], basis='pinyin_unique_affiliation', confidence='medium', url=r['pid'], dump=P.DBLP_DUMP_FILE, sha256=r['sha256'],
                               quote=r['school_note'], orcid=r['orcid'], names=r['names'], candidates=1, n_window=k_cnt[r['pid']], roster_evidence=ev.get(person))
            n += 1
        path.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
        print(json.dumps(dict(key=k, unbound_han_people=len(people[k]), school_dblp_records=len(recs[k]), bound=len(bound), written=n)))


if __name__ == '__main__':
    main(sys.argv[1:])
