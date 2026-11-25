"""Apply a school's manual computing-judgement layer (reviewed/cs-related-manual-layer.json) to its cs-related-review.json and
census-additions.json. Idempotent; run after `cs_related_school.py review <key>` and before `excluded_audit.py convert <key>`.
usage: cs_related_manual_layer.py <key>"""
import json
import re
import sys
from types import SimpleNamespace

import atlas_paths as P
import cs_related_school as C

key = sys.argv[1]
_L = json.loads((P.data('cs-related-hand.json', key).parent / 'cs-related-manual-layer.json').read_text())
M = SimpleNamespace(FLIP_NOT_COMPUTING=_L['flip_not_computing'], PROMOTE=_L['promote_computing'], INFK_FULL=_L['infk_full_coverage'])
BY, ON = _L['by'], _L['on']
rp, ap = P.data_w('cs-related-review.json', key), P.data_w('census-additions.json', key)
doc = json.loads(rp.read_text())
adds = json.loads(ap.read_text())
toks = lambda n: ' '.join(C.toks(n))
rows = {}
for d in doc['decisions']:
    rows.setdefault(toks(d['name']), []).append(d)
log = []


def find(name):
    r = rows.get(toks(name))
    if not r:
        raise SystemExit(f'manual layer: no decision row for {name}')
    return r[0]


def addition(d, why):
    fac = [e for e in d['faculty_evidence'] if e.get('ladder')]
    seen, srcs = set(), []
    for e in sorted(fac, key=C.faculty_observed):
        k = (e['url'], e['quote'])
        if k in seen:
            continue
        seen.add(k)
        srcs.append(dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], kind=f"unit_listing:{e['unit']}", observed=C.faculty_observed(e)))
    first = sorted(fac, key=C.faculty_observed)[0]
    cb = d.get('cs_basis') or {}
    return dict(name=d['name'], aliases=d.get('aliases') or [], collection_person_id=f'{key}_fac_' + re.sub(r'[^a-z0-9]+', '-', toks(d['name'])).strip('-'),
                dblp=(cb.get('dblp') or [])[:1], rank='ladder', title_as_listed=first['quote'], departments=sorted({e['unit'] for e in fac}),
                years_listed=sorted({int(C.faculty_observed(e)[:4]) for e in fac}), sources=srcs, is_pi=True,
                pi_basis=dict(kind='ladder_faculty', url=first['url'], sha256=first['sha256'], quote=first['quote'], observed=C.faculty_observed(first),
                              role='professor title on the unit faculty listing',
                              cs_related=dict(dblp=cb.get('dblp') or [], dblp_window=cb.get('dblp_window', 0), openalex=(cb.get('openalex_share') or {}).get('ids'),
                                              share=(cb.get('openalex_share') or {}).get('share'), manual_basis=why)),
                lab_units=[], added=f'cs_related_review_{ON.replace("-", "")}', reviewed_by=BY)


def set_dec(d, dec, why, kind):
    d.pop('converted_from', None)
    d['decision'] = dec
    d['reason'] = f'{why} (manual review {ON}, {BY}; owner rule 2026-11-24: computing as the object or method of research)'
    d['manual_review'] = dict(kind=kind, by=BY, on=ON, basis=why)
    d.pop('reason_code', None)


for name, why in M.FLIP_NOT_COMPUTING.items():
    d = find(name)
    set_dec(d, 'faculty_not_computing', why, 'applied_test_flip')
    adds = [a for a in adds if toks(a['name']) != toks(d['name'])]
    log.append(('flip', d['name']))
for name, why in {**M.PROMOTE, **M.INFK_FULL}.items():
    d = find(name)
    kind = 'applied_test_promote' if name in M.PROMOTE else 'infk_full_coverage'
    if name == 'Mennatallah El-Assady':
        off = find('Menna El-Assady')
        d['faculty_evidence'] = off['faculty_evidence']
        d['years_listed'] = off['years_listed']
        d['units_searched'] = off.get('units_searched')
        off.update(decision='census_alias', census_name='Mennatallah El-Assady', reason='the same ETH professor as the DBLP person Mennatallah El-Assady (name form on the who-is-who list)')
        off['cs_basis'] = dict(dblp=(d.get('cs_basis') or {}).get('dblp'))
        off.pop('manual_review', None)
    set_dec(d, 'accepted', why, kind)
    adds = [a for a in adds if toks(a['name']) != toks(d['name'])] + [addition(d, why)]
    log.append(('promote', d['name']))
cnt = {}
for d in doc['decisions']:
    cnt[d['decision']] = cnt.get(d['decision'], 0) + 1
doc['counts'] = cnt
doc['manual_layer'] = dict(by=BY, on=ON, flips=len(M.FLIP_NOT_COMPUTING), promotions=len(M.PROMOTE), infk_full=len(M.INFK_FULL))
rp.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
ap.write_text(json.dumps(adds, indent=1, ensure_ascii=False))
print(json.dumps(cnt), len(adds), log[:3])
