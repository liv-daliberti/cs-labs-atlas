"""Add every ETH person named by an official list as a candidate (source `official_list`) and decide the ones no earlier row covers.
Lists (reviewed/official-lists.json, built from stored sources): the SNSF professorship list 2000-2018 and the Eccellenza awardee list (snf.ch PDFs),
ETH Board professorial appointment / title-award releases (ETH News 2013-2016, ethrat.ch 2017-2026) and Board retirement / resignation entries.
Rule (owner 2026-11-24, D-0055, D-0070): an ETH professorship (Board appointment, SNSF professorship = non-TT assistant professorship) in 2016-2026 plus
computing as object or method of research (the OpenAlex/DBLP computing-share test) admits; outside the window, not a ladder title, or not computing is recorded
with the list as evidence. Idempotent: earlier official_list rows are rebuilt. Run after cs_related_manual_layer.py and before excluded_audit.py convert.
usage: cs_related_official_lists.py <key>"""
import collections
import json
import re
import sys

import atlas_paths as P
import cs_related_school as C

key = sys.argv[1]
BY, ON = 'claude-ethz-computing-1124', '2026-11-24'
toks = lambda n: ' '.join(C.toks(n))
lists = json.loads((P.data('cs-related-hand.json', key).parent / 'official-lists.json').read_text())
_L = json.loads((P.data('cs-related-hand.json', key).parent / 'cs-related-manual-layer.json').read_text())
PROMOTE = {toks(k): v for k, v in (_L.get('official_list_promote') or {}).items()}
DEMOTE = {toks(k): v for k, v in (_L.get('official_list_not_computing') or {}).items()}
rp, ap = P.data_w('cs-related-review.json', key), P.data_w('census-additions.json', key)
doc = json.loads(rp.read_text())
adds = json.loads(ap.read_text())
doc['decisions'] = [d for d in doc['decisions'] if d.get('source') != 'official_list']
adds = [a for a in adds if a.get('added') != 'official_list_' + ON.replace('-', '')]
census = C.census_rows(json.loads(P.data('census-faculty.json', key).read_text()))
have = [C.Name([x['name']] + list(x.get('aliases') or [])) for x in census]
have += [C.Name([d['name']] + list(d.get('aliases') or [])) for d in doc['decisions']]
SH = C.oa_stats(key)
CLEAN = re.compile(r'^(?:Prof(?:essor|\.)?|Dr\.?|PD Dr\.?)\s+')
UNIT = [('computer science', 'INFK'), ('information technology and electrical', 'ITET'), ('mechanical and process', 'MAVT'), ('civil, environmental', 'BAUG'),
        ('architecture', 'ARCH'), ('biosystems', 'BSSE'), ('biology', 'BIOL'), ('chemistry', 'CHAB'), ('mathematics', 'MATH'), ('physics', 'PHYS'),
        ('earth and planetary', 'ERDW'), ('health sciences', 'HEST'), ('environmental systems', 'USYS'), ('management, technology', 'MTEC'),
        ('humanities', 'GESS'), ('materials', 'MATL')]
COMP = re.compile(r'comput|data |machine|informatic|quantum|robot|information|algorithm|learning|cyber|software|simulation|statistic|intelligen|network|vision|signal|control|cryptograph|security', re.I)
NONLADDER = re.compile(r'adjunct|titular|of practice|private|lecturer|emerit', re.I)


def clean(n):
    n = re.sub(r'\.\s+(?:Prof\w*\.?|Dr\.?)\s+', '. ', n).split('. ')[-1] if '. ' in n and re.search(r'\.\s+(?:Prof|Dr)', n) else n
    return CLEAN.sub('', n).strip()


def unit_of(rank, name):
    t = (rank or '').lower()
    return next((c for k, c in UNIT if k in t), 'ETH')


groups = collections.OrderedDict()
for e in lists:
    nm = clean(e['name'])
    groups.setdefault(toks(nm), dict(name=nm, entries=[]))['entries'].append(e)
new = []
cnt = collections.Counter()
names_by_dec = collections.defaultdict(list)
for gk, g in groups.items():
    nm, ents = g['name'], g['entries']
    if len(toks(nm).split()) < 2 or any(N.match(nm) for N in have):
        cnt['already_covered'] += 1
        continue
    ladder = [e for e in ents if e['list'] != 'board_appointment' or not NONLADDER.search(e.get('rank') or '')]
    ladder = [e for e in ladder if e['list'] != 'board_retirement' or re.search(r'Professor', e['quote'] or '') and not NONLADDER.search(e['quote'].split('currently')[-1][:80])]
    kinds = sorted({e['list'] for e in ents})
    rank = next((e.get('rank') for e in ents if e.get('rank')), '')
    sh = C.share_test(SH, [nm], [], None) if SH else None
    last_y = max([a['years'][1] for a in (sh or {}).get('authors', []) if a.get('years')] or [0])
    # window: a Board entry dated 2016+ (or an undated ethrat.ch one, which begins March 2017), an Eccellenza call of 2018+, a 2013-2015 Board appointee
    # (professors serve beyond 2016), or an SNSF professor with ETH-attributed works from 2016
    inw = any((e['list'] in ('board_appointment', 'board_retirement') and (not e['date'] or e['date'] >= '20130101')) or e['list'] == 'eccellenza' for e in ladder) \
        or (any(e['list'] == 'snsf_professorship' for e in ladder) and last_y >= 2016)
    best = sorted(ladder or ents, key=lambda e: (e['list'] == 'snsf_professorship', e['date'] or '9'))[0]
    title = ' '.join([rank] + [e['quote'] or '' for e in ents])
    d = dict(name=nm, aliases=[], source='official_list', cs_basis=dict(openalex=(sh or {}).get('ids'), openalex_share=sh), official_lists=kinds,
             list_evidence=[dict(list=e['list'], url=e['url'], sha256=e['sha256'], date=e['date'], quote=e['quote'], rank=e.get('rank')) for e in ents][:4],
             years_listed=[], units_searched=['official lists: ' + ', '.join(kinds)], reviewed_by=BY, reviewed_on=ON)
    if not ladder:
        d.update(decision='research_or_other_rank', reason='the official list gives only an adjunct, titular, practice or other non-ladder title')
    elif not inw:
        d.update(decision='out_of_window', reason='official list names an ETH professorship but none in 2016-2026 (SNSF list has no award year; no ETH-attributed work from 2016)')
    elif toks(nm) in DEMOTE:
        d.update(decision='faculty_not_computing', reason=DEMOTE[toks(nm)] + f' (manual review {ON}, {BY})')
    elif toks(nm) in PROMOTE or (sh and sh['result'] == 'computing'):
        unit = unit_of(rank + ' ' + (best['quote'] or ''), nm)
        obs = best['date'] or '20170301'
        if best['list'] == 'snsf_professorship':
            obs = '20191101'
        if toks(nm) in PROMOTE:
            why = f"ETH professorship per the {best['list'].replace('_', ' ')} list; {PROMOTE[toks(nm)]}"
        else:
            why = f"ETH professorship per the {best['list'].replace('_', ' ')} list; computing-share test passes: {sh['dblp_indexed']} of {sh['school_works']} school works DBLP-indexed (share {sh['share']:.2f})"
        d.update(decision='accepted', reason=why + f' (official list rule {ON}, {BY})',
                 faculty_evidence=[dict(unit=unit, url=best['url'], sha256=best['sha256'], observed=obs, quote=best['quote'], ladder=True, hand=True)])
        adds_row = dict(name=nm, aliases=[], collection_person_id=f'{key}_fac_' + re.sub(r'[^a-z0-9]+', '-', toks(nm)).strip('-'), dblp=[], rank='ladder',
                        title_as_listed=best['quote'], departments=[unit], years_listed=[int(obs[:4])],
                        sources=[dict(url=best['url'], sha256=best['sha256'], quote=best['quote'], kind=f'unit_listing:{unit}', observed=obs)], is_pi=True,
                        pi_basis=dict(kind='ladder_faculty', url=best['url'], sha256=best['sha256'], quote=best['quote'], observed=obs,
                                      role='ETH professorship on an official list (' + best['list'].replace('_', ' ') + ')',
                                      cs_related=dict(dblp=[], dblp_window=0, openalex=(sh or {}).get('ids'), share=(sh or {}).get('share'), manual_basis=why)),
                        lab_units=[], added='official_list_' + ON.replace('-', ''), reviewed_by=BY)
        adds.append(adds_row)
    elif COMP.search(title) and not (sh and sh['result'] == 'not_computing'):
        d.update(decision='excluded_unresolved', reason_code='official_list_unmeasured',
                 reason='ETH professorship in window per an official list; the title or field is computing-like but the OpenAlex sweep has too few ETH works to test it')
    else:
        d.update(decision='faculty_not_computing', reason='ETH professorship per an official list; computing-share test ' + (f"fails ({sh['dblp_indexed']} of {sh['school_works']} school works DBLP-indexed)" if sh and sh['school_works'] else 'finds no ETH-attributed computing works and the title is not computing'))
    d['manual_review'] = dict(kind='official_list', by=BY, on=ON)
    doc['decisions'].append(d)
    new.append(d)
    cnt[d['decision']] += 1
    names_by_dec[d['decision']].append(nm)
    for x in (C.Name([nm]),):
        have.append(x)
for d in doc['decisions']:   # an existing row an official list settles (e.g. an adjunct title the earlier name match missed)
    ov = (_L.get('official_list_overrides') or {}).get(d['name'])
    if ov and d['decision'] in ('excluded_unresolved', 'pending_source_coverage'):
        d.pop('converted_from', None); d.pop('reason_code', None)
        d.update(decision=ov['decision'], reason=ov['reason'] + f' (manual review {ON}, {BY})', manual_review=dict(kind='official_list_override', by=BY, on=ON))
c2 = collections.Counter(d['decision'] for d in doc['decisions'])
doc['counts'] = dict(c2)
rp.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
ap.write_text(json.dumps(adds, indent=1, ensure_ascii=False))
cp = P.data_w('cs-related-candidates.json', key)
cands = [c for c in json.loads(cp.read_text()) if c.get('source') != 'official_list']
cands += [dict(name=d['name'], aliases=[], source='official_list', lists=d['official_lists']) for d in new]
cp.write_text(json.dumps(cands, indent=1, ensure_ascii=False))
print(json.dumps(dict(groups=len(groups), new_candidates=len(new), **cnt)))
print('ACCEPTED', names_by_dec['accepted'])
print('UNRESOLVED', names_by_dec['excluded_unresolved'])
