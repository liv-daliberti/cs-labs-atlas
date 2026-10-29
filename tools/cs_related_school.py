"""CS-related faculty for a protocol school (protocol stage 2; owner rule 2026-10-22/28: computing-related faculty in any
department, computing being the object or the method of their research; administrative advisers are not PIs).

candidates  (a) every person a department with coverage "affiliated" lists with a professor rank (census rank ladder),
                whose computing work is to be decided (Michigan ECE)
            (b) every DBLP person whose dump record names the school (tools/dblp_affiliated.py: affiliation note or a URL
                on a school domain) with >= MIN_DBLP records 2016-2026 and who is not in the census
            (c) once the OpenAlex sweep is complete: tools/cs_related_candidates.py's rule on the school's sweep
                (>= 8 school works, >= 5 DBLP-indexed and >= 20% so, ...), when that pass has been run
            -> hierarchy/<key>/cs-related-candidates.json
units       one Wayback capture per year 2016-2026 of every faculty listing URL the charter's [[affiliated_units]] name
            (`listings`), into captures/<key>.sqlite (live only where the host's charter `use` is live)
review      faculty evidence: a 2016-2026 unit capture whose text has the candidate's name followed (within 300
            characters, before the next person's name) by a professor title; the quote runs from the name through the
            title. For (a) the department listing itself is the evidence.
            computing evidence: the DBLP record that names the school, with its 2016-2026 record count (every DBLP record
            is a computing venue or a CS preprint); >= MIN_DBLP records is computing as object or method.
            decision  accepted                 faculty evidence (ladder professor title) and computing evidence
                      faculty_not_computing    faculty evidence, < MIN_DBLP DBLP records naming the school
                      not_faculty_listed       no searched unit lists them as faculty in 2016-2026 and the DBLP record
                                               names the school only as a past or student affiliation (or nothing else
                                               shows a faculty appointment); `units_searched` says where we looked
                      research_or_other_rank   listed, but with a research / adjunct / emeritus / clinical title only
                      namesake                 the DBLP person is not the listed faculty member (another affiliation
                                               conflicts; recorded with the evidence)
            -> hierarchy/<key>/cs-related-review.json {school, rule, reviewed, provisional, decisions: [...]}
            -> census/<key>-additions.json: accepted people of other units (census format; is_pi with pi_basis
               ladder_faculty from the unit listing; added = cs_related_review_<date>)
usage: cs_related_school.py candidates|units|review <key>
"""
import collections, datetime, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402
from pi_hierarchy import Name, toks  # noqa: E402

MIN_DBLP = 5
TODAY = datetime.date.today().isoformat()
PROF_T = re.compile(r'\b(?:(?:Assistant|Associate|Full|Collegiate|University|Distinguished|Arthur F\. Thurnau)\s+)?Professor\b(?:\s+of\s+[A-Z][\w&,\- ]{2,80})?', re.I)
NOT_LADDER = re.compile(r'emerit|adjunct|visiting|research\s+(?:assistant\s+|associate\s+)?professor|clinical|courtesy|professor\s+of\s+(?:the\s+)?practice|lecturer|postdoc', re.I)


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def clean_dblp(n):
    return re.sub(r'\s+\d{4}$', '', n)


def candidates(key):
    census = read(P.CENSUS / f'{key}-faculty.json')['faculty']
    cov = {d['code']: d.get('coverage') for d in S.get(key).get('departments') or []}
    out = []
    for x in census:  # (a) ladder in an affiliated department, never ladder in a full-coverage one
        dep_rank = {(s_['kind'].split(':')[-1], s_.get('rank')) for s_ in x['sources']}
        if any(cov.get(d) == 'affiliated' and r == 'ladder' for d, r in dep_rank) and not any(cov.get(d) == 'full' and r == 'ladder' for d, r in dep_rank):
            out.append(dict(name=x['name'], aliases=x.get('aliases') or [], source='affiliated_department', departments=x['departments']))
    names = [Name([x['name']] + list(x.get('aliases') or [])) for x in census]
    for p in read(P.HIERARCHY / key / 'dblp-affiliated.json', {}).get('persons', []):
        if p.get('n_window', 0) < MIN_DBLP or p.get('disambiguation'):
            continue
        nm = clean_dblp(p['names'][0])
        if any(N.match(nm) for N in names):
            continue
        out.append(dict(name=nm, aliases=[clean_dblp(n) for n in p['names'][1:]], source='dblp_affiliation', dblp=p['pid'], dblp_window=p['n_window'],
                        affiliations=[a['text'] for a in p['affiliations']], matched_by=p['matched_by']))
    (P.HIERARCHY / key / 'cs-related-candidates.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(candidates=len(out), **collections.Counter(c['source'] for c in out))))


def units(key):
    cfg = S.get(key); c = W.con(key)
    use = {h['host']: h.get('use') for h in cfg.get('hosts') or []}
    n = collections.Counter()
    for u in cfg.get('affiliated_units') or []:
        for url in u.get('listings') or []:
            host = re.sub(r'^https?://', '', url).split('/')[0]
            if use.get(host) == 'live':
                res = W.live(c, url if url.startswith('http') else 'https://' + url)
                n['live'] += 1
            rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:4')
            for r in rows:
                cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], url, u['code'])
                n[f'wayback_{st}'] += 1
                print(json.dumps(dict(unit=u['code'], ts=r['timestamp'], status=st, blocks=len(b))), flush=True)
    print(json.dumps(dict(n)))


def unit_pages(key):
    """(unit code, url, sha256, observed, flat text) of every stored 2016-2026 unit capture and live page."""
    cfg = S.get(key); c = W.con(key)
    codes = {}
    for u in cfg.get('affiliated_units') or []:
        for url in u.get('listings') or []:
            codes[re.sub(r'^https?://(www\.)?', '', url).rstrip('/').lower()] = u['code']
    out = []
    for cap, page, dept, ts, st, sha, txt in c.execute('select capture_url, page_url, department, wayback_timestamp, http_status, sha256, text from captures'):
        k = re.sub(r'^https?://(www\.)?', '', page or '').rstrip('/').lower()
        if st == 200 and txt and (k in codes or dept in codes.values()):
            y = int(str(ts)[:4])
            if 2016 <= y <= 2026:
                out.append((codes.get(k, dept), cap, sha, str(ts), ' '.join(txt.split())))
    for url, at, st, sha, raw in c.execute('select url, fetched_at, status, sha256, raw_zlib from live'):
        k = re.sub(r'^https?://(www\.)?', '', url).rstrip('/').lower()
        if st == 200 and k in codes:
            import zlib
            b = W.extract.blocks(zlib.decompress(raw), 'text/html', url)
            out.append((codes[k], url, sha, at[:10].replace('-', ''), W.flat(b)))
    return out


def faculty_evidence(pages, names):
    """Every (unit, url, sha, observed, quote, ladder) where a page names the person followed by a professor title."""
    N = Name(names)
    forms = set()
    for n in names:
        t = n.split()
        if len(t) >= 2:
            forms |= {n, f'{t[-1]}, {" ".join(t[:-1])}', f'{t[0]} {t[-1]}', f'{t[-1]}, {t[0]}'}
    ev = []
    for unit, url, sha, obs, flat in pages:
        for f in forms:
            for m in re.finditer(re.escape(f), flat):
                win = flat[m.start():m.start() + 300]
                pt = PROF_T.search(win, len(f))
                if not pt:
                    continue
                q = win[:pt.end()]
                ev.append(dict(unit=unit, url=url, sha256=sha, observed=obs, quote=q, ladder=not NOT_LADDER.search(q[len(f):])))
                break
    return ev


def review(key):
    cands = read(P.HIERARCHY / key / 'cs-related-candidates.json', [])
    dblp = read(P.HIERARCHY / key / 'dblp-affiliated.json', {}).get('persons', [])
    census = {x['name']: x for x in read(P.CENSUS / f'{key}-faculty.json')['faculty']}
    pages = unit_pages(key)
    searched = sorted({p[0] for p in pages})
    dec, adds, n = [], [], collections.Counter()
    for c in cands:
        names = [c['name']] + list(c.get('aliases') or [])
        N = Name(names)
        recs = [p for p in dblp if any(N.match(clean_dblp(x)) for x in p['names'])] if c['source'] != 'dblp_affiliation' else \
            [p for p in dblp if p['pid'] == c.get('dblp')]
        win = max([p.get('n_window', 0) for p in recs] or [0])
        comp = dict(dblp=[p['pid'] for p in recs], dblp_window=win, affiliation_notes=[a['text'] for p in recs for a in p['affiliations']][:4],
                    evidence=[dict(url=p['pid'], source=f'DBLP dump {P.DBLP_DUMP_FILE}', quote=next((a['text'] for a in p['affiliations']), None)) for p in recs][:2])
        if c['source'] == 'affiliated_department':
            x = census[c['name']]
            src = next(s for s in x['sources'] if s.get('rank') == 'ladder')
            fac = [dict(unit=src['kind'].split(':')[-1], url=src['url'], sha256=src['sha256'], observed=src['observed'], quote=src['quote'], ladder=True)]
        else:
            fac = faculty_evidence(pages, names)
        lad = [e for e in fac if e['ladder']]
        if lad and win >= MIN_DBLP:
            d = 'accepted'; why = f'faculty ({lad[0]["unit"]} listing, professor rank) with {win} DBLP records 2016-2026 naming the school'
        elif lad:
            d = 'faculty_not_computing'; why = f'faculty ({lad[0]["unit"]}), {win} DBLP records 2016-2026 (< {MIN_DBLP})'
        elif fac:
            d = 'research_or_other_rank'; why = 'listed by a searched unit only with a research, adjunct, clinical or emeritus title'
        else:
            d = 'not_faculty_listed'; why = f'no 2016-2026 faculty listing of the searched units ({", ".join(searched)}) names them with a professor title'
        n[d] += 1
        row = dict(name=c['name'], aliases=c.get('aliases') or [], source=c['source'], decision=d, reason=why, cs_basis=comp,
                   faculty_evidence=sorted(fac, key=lambda e: e['observed'])[:3] + (sorted(fac, key=lambda e: e['observed'])[-1:] if len(fac) > 3 else []),
                   years_listed=sorted({int(e['observed'][:4]) for e in fac}), units_searched=searched,
                   provisional='computing share pending the OpenAlex sweep (DBLP-indexed share of school works >= 20%)')
        dec.append(row)
        if d == 'accepted' and c['source'] != 'affiliated_department':
            first, last = lad[0], sorted(lad, key=lambda e: e['observed'])[-1]
            adds.append(dict(name=c['name'], aliases=row['aliases'], collection_person_id=f'{key}_fac_' + re.sub(r'[^a-z0-9]+', '-', ' '.join(toks(c['name']))).strip('-'),
                             dblp=comp['dblp'][:1], rank='ladder', title_as_listed=last['quote'], departments=[last['unit']],
                             years_listed=row['years_listed'], sources=[dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], kind=f"unit_listing:{e['unit']}",
                                                                          observed=e['observed']) for e in sorted(lad, key=lambda e: e['observed'])],
                             is_pi=True, pi_basis=dict(kind='ladder_faculty', url=first['url'], sha256=first['sha256'], quote=first['quote'], observed=first['observed'],
                                                       role='professor title on the unit faculty listing', cs_related=dict(dblp=comp['dblp'], dblp_window=win)),
                             lab_units=[], added=f'cs_related_review_{TODAY.replace("-", "")}'))
    doc = dict(school=key, reviewed=TODAY, rule=__doc__.split('\nusage')[0], min_dblp=MIN_DBLP, units_searched=searched, counts=dict(n), decisions=dec)
    (P.HIERARCHY / key / 'cs-related-review.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    (P.CENSUS / f'{key}-additions.json').write_text(json.dumps(adds, indent=1, ensure_ascii=False))
    print(json.dumps(dict(decisions=len(dec), additions=len(adds), **n)))


if __name__ == '__main__':
    {'candidates': candidates, 'units': units, 'review': review}[sys.argv[1]](sys.argv[2])
