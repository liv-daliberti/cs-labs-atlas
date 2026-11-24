"""DBLP person ids for Han-name census people by UNIQUE pinyin full-name match + school affiliation note (owner D-0010, 2026-11-18, Q-0352).

Identity, medium confidence, covered by the 50-row identity audit: a census person (Han roster name, no DBLP id yet) is bound to a DBLP person record when
  (a) the record's name (homonym number set aside) equals the pinyin of the Han name in either order (family syllable(s) + given syllables, joined),
  (b) the record's `<note type="affiliation">` matches the school's affiliation regex (or a record URL is on a school web domain),
  (c) exactly ONE such record exists for that name, and exactly ONE census person's Han name has that pinyin key (no homophone pair on either side).
Census additions (reviewed rows of hierarchy/<key>/reviewed/census-additions.json) are census people here too (2026-11-23).
Nothing else: not a name-only join across schools, and a record without the school in its note never counts. Existing pids are never overwritten.

  dblp_pinyin_binding_school.py --openalex <key> ...   OpenAlex extension (Q-0354): the DBLP note is replaced by an OpenAlex-rule author id with >= 70% computing share; writes hierarchy/<key>/reviewed/openalex-identity-review.json
  dblp_pinyin_binding_school.py <key> [<key> ...]    one streamed pass over the dump; merges into hierarchy/<key>/dblp-ids.json
     {person: {pid, basis: 'pinyin_unique_affiliation', confidence: 'medium', url, dump, sha256, quote, orcid, names, candidates, n_window, roster_evidence}}
"""
import collections, hashlib, json, re, sys, unicodedata

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from dblp_dump_persons import records, text, AUTH, URL, YEAR  # noqa: E402

MIN_WINDOW = 5
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


def name_keys(nm):
    """The joined keys of a DBLP name: itself, and (owner D-0013) with one token dropped when it has 3+ tokens (an added English middle or given name:
    'Shengbo Eben Li', 'Sean Xin Xu'); the homonym number is set aside."""
    toks = re.sub(r'\s+\d{4}$', '', nm).split()
    out = {fold(''.join(toks))}
    if len(toks) >= 3:
        out |= {fold(''.join(toks[:i] + toks[i + 1:])) for i in range(len(toks))}
    return {k for k in out if k}


def bind(people, recs):
    """people: [{name, evidence}] without a pid; recs: [{pid, names, school_note, sha256, ...}] school-affiliated DBLP persons. -> [(person, rec, key)]"""
    by_key = collections.defaultdict(set)
    for p in people:
        for k in keys_of(p['name']):
            by_key[k].add(p['name'])
    rec_keys = collections.defaultdict(dict)
    for r in recs:
        for nm in r['names']:
            for k in name_keys(nm):
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


def oa_bind(people, cands, min_share=0.7):
    """OpenAlex extension (Q-0354): school-lineage OpenAlex-rule candidates (computing share >= min_share) whose name pinyin-matches exactly one census Han person
    (and that name key is carried by no other candidate of any source). -> [(person, candidate)]"""
    by_key = collections.defaultdict(set)
    for p in people:
        for k in keys_of(p['name']):
            by_key[k].add(p['name'])
    cand_keys = collections.defaultdict(list)
    for c in cands:
        for nm in [c['name']] + list(c.get('aliases') or []):
            k = fold(re.sub(r'\s+\d{4}$', '', nm))
            if not any(x is c for x in cand_keys[k]):   # one candidate under several alias spellings of one key is one candidate
                cand_keys[k].append(c)
    out = []
    for p in people:
        hits = {}
        for k in keys_of(p['name']):
            if len(by_key[k]) != 1:
                continue
            cs = cand_keys.get(k, [])
            if len(cs) == 1 and cs[0]['source'] == 'openalex_rule' and (cs[0].get('oa_cs_share') or 0) >= min_share and len(cs[0].get('openalex') or []) == 1:
                hits[cs[0]['openalex'][0]] = cs[0]
        if len(hits) == 1:
            out.append((p['name'], next(iter(hits.values()))))
    return out


def write_oa(key, people):
    cp = P.data('cs-related-candidates.json', key)
    cands = json.loads(cp.read_text())
    found = oa_bind(people, cands)
    path = P.data_w('openalex-identity-review.json', key)
    doc = json.loads(path.read_text()) if path.exists() else {'decisions': {}}
    n = 0
    for person, c in found:
        if person in doc['decisions']:
            continue
        doc['decisions'][person] = dict(openalex=c['openalex'], aliases=[c['name']], basis='pinyin_unique_openalex', confidence='medium',
                                        why=f"owner D-0010 + Q-0354 (2026-11-18): unique pinyin full-name match of {c['name']} to the census person, OpenAlex author id with {c['oa_works']} school works, {round(100 * c['oa_cs_share'])}% DBLP-indexed; medium confidence, identity audit")
        n += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    return len(found), n


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
        # reviewed census additions (affiliated units, lab hunts) are census people too (2026-11-23): their official profile is the roster evidence,
        # and they join the same uniqueness test (a homophone among census rows and additions blocks every one of them)
        add_f = P.data('census-additions.json', k)
        names_ = {x['name'] for x in cen}
        for x in (json.loads(add_f.read_text()) if add_f.exists() else []):
            if x['name'] in names_ or not HAN.match(''.join(x['name'].split())) or (ids.get(x['name']) or {}).get('pid') or x.get('dblp'):
                continue
            src = next((s_ for s_ in x.get('sources') or [] if s_.get('url')), None)
            people[k].append(dict(name=x['name'], evidence=dict(url=src['url'], sha256=src.get('sha256'), quote=src.get('quote')) if src else None))
            names_.add(x['name'])
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
        lo, hi = cfgs[k][0].get('window') or [2016, 2026]
        pkeys = {kk for p in people[k] for kk in keys_of(p['name'])}
        rel = [r for r in recs[k] if any(name_keys(nm) & pkeys for nm in r['names'])]
        owner = {nm: r['pid'] for r in rel for nm in r['names']}
        k_cnt = collections.Counter()
        for typ, key, body in records():
            if typ in ('www', 'data'):
                continue
            hit = {owner[a] for _, a in AUTH.findall(body) for a in [text(a)] if a in owner}
            y = YEAR.search(body)
            if hit and y and lo <= int(y.group(1)) <= hi:
                for p in hit:
                    k_cnt[p] += 1
        # a thin record (< MIN_WINDOW records in the window) is neither a candidate nor a competitor: 'Liwei Wang 0015' (2 records) does not block 'Liwei Wang 0011' (12)
        bound = bind(people[k], [r for r in rel if k_cnt[r['pid']] >= MIN_WINDOW])
        path = P.data_w('dblp-ids.json', k)
        cur = json.loads(path.read_text()) if path.exists() else {}
        ev = {p['name']: p['evidence'] for p in people[k]}
        n = 0
        for person, r in bound:
            if (cur.get(person) or {}).get('pid') or k_cnt[r['pid']] < MIN_WINDOW:
                continue   # a thin record (< MIN_WINDOW records in the window) is too weak for a name-derived join (PKU audit: Feng Liu 0049, Feng Chen 0021)
            cur[person] = dict(pid=r['pid'], basis='pinyin_unique_affiliation', confidence='medium', url=r['pid'], dump=P.DBLP_DUMP_FILE, sha256=r['sha256'],
                               quote=r['school_note'], orcid=r['orcid'], names=r['names'], candidates=1, n_window=k_cnt[r['pid']], roster_evidence=ev.get(person))
            n += 1
        path.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
        print(json.dumps(dict(key=k, unbound_han_people=len(people[k]), school_dblp_records=len(recs[k]), bound=len(bound), written=n)))


def oa_main(keys):
    for k in keys:
        cen = json.loads(P.data('census-faculty.json', k).read_text())['faculty']
        people = [dict(name=x['name']) for x in cen if HAN.match(''.join(x['name'].split()))]
        add_f = P.data('census-additions.json', k)   # reviewed census additions join the same uniqueness test (2026-11-23)
        seen = {x['name'] for x in cen}
        people += [dict(name=x['name']) for x in (json.loads(add_f.read_text()) if add_f.exists() else [])
                   if x['name'] not in seen and HAN.match(''.join(x['name'].split()))]
        print(json.dumps(dict(key=k, openalex_bound=write_oa(k, people))))


if __name__ == '__main__':
    if sys.argv[1] == '--openalex':
        oa_main(sys.argv[2:])
    else:
        main(sys.argv[1:])
