"""Build the Berkeley CS-related review outputs (owner decision 2026-10-22) from accepted.py / others.py.

usage: build.py STAGE_DIR      writes additions.json, overrides.json (berkeley periods), home-departments.json, review.json
       into STAGE_DIR; every quote is re-checked against hierarchy/berkeley/cs-related-captures.sqlite. apply.py merges them.
"""
import json, os, re, sys
from ev import *
from accepted import A, EEH, EE_LIST
from others import O

ADDED = 'cs_related_scope_20261022'
STORE = 'hierarchy/berkeley/cs-related-captures.sqlite'
DISPLAY = {1: 'Michael Mahoney', 9: 'Zuo-Jun Max Shen', 6: 'Alberto Sangiovanni-Vincentelli', 16: 'Ali Niknejad', 43: 'Thomas Courtade',
           61: 'Michel Maharbiz', 67: 'Alper Atamtürk', 72: 'Marta C. González', 74: 'Bruno Olshausen', 99: 'Gopala Anumanchipalli',
           107: 'Robert Brayton', 112: 'Alice Agogino', 124: 'Paul Grigas', 141: 'Bernhard Boser', 156: 'Robert Full', 174: 'Ryan Tibshirani',
           211: 'Michael DeWeese', 215: 'Michael Lindsey', 66: 'Duncan Callaway', 13: 'Zachary Pardos', 168: 'Michelle Hoda Wilkerson',
           53: 'Hannah Stuart', 57: 'Mark Mueller', 42: 'Roberto Horowitz', 129: 'Antonio Montalbán', 55: 'Wesley Holliday',
           128: 'Deirdre Mulligan', 0: 'Masayoshi Tomizuka'}


def flip(n):
    if ',' in n:
        a, b = [x.strip() for x in n.split(',', 1)]
        return f'{b} {a}'
    return n


def ee_list_quote(name):
    for r in eecs_rows([name]):
        if r['url'] == EE_LIST:
            return dict(url=r['url'], sha256=r['sha256'], quote=r['quote'])
    raise Missing(f'{name} not on the live EE list')


def auto_diss(names):
    rows = adv_rows(names)
    if not rows:
        raise Missing(f'no EECS dissertation for {names}')
    sole = [r for r in rows if len(r['advisers']) == 1]
    r = max(sole or rows, key=lambda r: r['year'])
    q = r['quote']
    m = re.search(r'(\S+ \S+ \[advisor: [^\]]+\])$', q)  # the student's (last two) name words and the adviser field
    return E(r['url'], m.group(1) if m else q), r['year']


def resolve_pi(x, names):
    k = x['pi'][0]
    if k == 'diss':
        e = DISS(x['pi'][1]); return dict(kind='advises_phd', **e)
    if k == 'diss_auto':
        e, _ = auto_diss(names); return dict(kind='advises_phd', **e)
    if k == 'math':
        e = MATH(x['pi'][1]); return dict(kind='advises_phd', **e)
    if k == 'page':
        e = E(x['pi'][1], x['pi'][2]); return dict(kind='advises_phd', **e)
    if k == 'lab':
        e = E(x['pi'][1], x['pi'][2]); return dict(kind='lab_head', **e)
    raise ValueError(k)


def main(stage):
    os.makedirs(stage, exist_ok=True)
    adds, periods, homes, review, problems = [], {}, [], [], []
    dup_of = {d: i for i, x in A.items() for d in x.get('dups', [])}
    for i, x in sorted(A.items()):
        c = CANDS[i]
        try:
            name = DISPLAY.get(i) or flip(c['name'])
            ids = [c['author']] + [CANDS[d]['author'] for d in x.get('dups', [])]
            names_all = []
            for j in [i] + x.get('dups', []):
                names_all += [flip(n) for n in CANDS[j]['names']] + [flip(CANDS[j]['name'])]
            aliases = [a for a in dict.fromkeys(list(x.get('aliases', [])) + names_all) if a != name and not re.search(r'[A-Z]{3,}', a)]
            srcs = [L(u, q, k) for u, q, k in x.get('listings', [])]
            eecs_names = x.get('eecs') or []
            erows = EECS(eecs_names) if eecs_names else []
            srcs += erows
            years = sorted({int(s['observed'][:4]) for s in srcs if 2016 <= int(s['observed'][:4]) <= 2026})
            pi = resolve_pi(x, eecs_names or written_forms(c))
            extra = []
            for spec in x.get('pi_extra', []):
                extra.append(MATH(spec[1]) if spec[0] == 'MATH' else E(*spec))
            he = x.get('home_evidence', ('src0',))
            if he is None or he[0] == 'src0':
                h = srcs[0]; hev = dict(url=h['url'], sha256=h['sha256'], quote=h['quote'])
            elif he[0] == 'last_eecs':
                h = erows[-1]; hev = dict(url=h['url'], sha256=h['sha256'], quote=h['quote'])
            elif he[0] == 'ee_list':
                hev = ee_list_quote(he[1])
            else:
                hev = E(he[1], he[2])
            orcid = OA_orcid(c['author'])
            note = (f"OpenAlex {', '.join(a.split('/')[-1] for a in ids)}: {c['works']} works listing Berkeley 2016-2026, {c['dblp_works']} DBLP-indexed "
                    f"({c['cs_share']:.0%}), last author on {c['last_author_share']:.0%}; top venues {'; '.join(c['top_venues'][:3])}.")
            row = dict(name=name, aliases=aliases, openalex=ids, orcid=orcid, rank=x['rank'], title_as_listed=x['title'],
                       departments=[x['home']], years_listed=years, sources=srcs, is_pi=True,
                       pi_basis=dict(kind=pi['kind'], url=pi['url'], sha256=pi['sha256'], quote=pi['quote']),
                       lab_units=[], added=ADDED, identity_note=note + (' ' + x['note'] if x.get('note') else ''))
            if extra:
                row['pi_basis_more'] = extra
            if x.get('lab'):
                row['lab_name'] = x['lab']
            row['capture_store'] = STORE
            adds.append(row)
            per = x.get('period')
            if per:
                if per.get('from_first_eecs'):
                    ev = [erows[0]]
                elif per.get('from_eecs_span'):
                    w = [r for r in erows if 2016 <= int(r['observed'][:4]) <= 2026]
                    ev = [w[0], w[-1]]
                else:
                    ev = [E(u, q) for u, q in per['evidence']]
                pid = 'override_period_berkeley_' + re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
                periods[name] = {'periods': [dict(id=pid, start=per['start'], end=per['end'], asof=None,
                                                   evidence=[dict(url=e['url'], sha256=e['sha256'], quote=e['quote']) for e in ev])],
                                 'why': 'CS-related scope review 2026-10-22 (hierarchy/berkeley/cs-related-review.json): appointment period from dated evidence'}
            homes.append(dict(school='berkeley', name=name, home_department=x['home'], also=x.get('also', []), status='accepted',
                              evidence=hev, note=(x.get('note') or '')[:400]))
            for j in [i] + x.get('dups', []):
                review.append(dict(index=j, author=CANDS[j]['author'], name=flip(CANDS[j]['name']), decision='accepted',
                                   reason=(f'{x["title"]}, {x["home"]}; PI: ' + ('stated PhD advising' if pi['kind'] == 'advises_phd' else 'heads ' + (x.get('lab') or 'own lab'))
                                           + (f'; one census row with candidate {i}' if j != i else '')
                                           + (f"; period {per['start']} to {per['end'] or 'present'}" if per else '')),
                                   census_name=name, home_department=x['home'],
                                   evidence=[dict(url=s['url'], sha256=s['sha256'], quote=s['quote']) for s in srcs[:2]] + [dict(url=pi['url'], sha256=pi['sha256'], quote=pi['quote'])]))
        except Missing as e:
            problems.append((i, c['name'], str(e)))
    for i, (dec, reason, specs) in sorted(O.items()):
        c = CANDS[i]
        try:
            ev = []
            for s in specs:
                if s[0] == 'oa':
                    ev.append(OA(c['author'], s[1]))
                elif s[0] == 'oa_name':
                    ev.append(E('https://api.openalex.org/authors/' + c['author'].split('/')[-1], '"display_name":' + json.dumps(s[1])))
                elif s[0] == 'student':
                    ev.append(DISS(s[1]))
                elif s[0] == 'math':
                    ev.append(MATH(s[1]))
                elif s[0] == 'eecs':
                    rows = EECS([s[1]])
                    ev += [dict(url=r['url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed']) for r in ([rows[0], rows[-1]] if len(rows) > 1 else rows)]
                elif s[0] == 'page':
                    ev.append(E(s[1], s[2]))
            if not ev:
                raise Missing('no evidence')
            review.append(dict(index=i, author=c['author'], name=flip(c['name']), decision=dec, reason=reason, evidence=ev))
        except Missing as e:
            problems.append((i, c['name'], str(e)))
    seen = {r['index'] for r in review}
    missing = [(i, c['name']) for i, c in enumerate(CANDS) if i not in seen]
    review.sort(key=lambda r: r['index'])
    json.dump(adds, open(f'{stage}/additions.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(periods, open(f'{stage}/overrides.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(homes, open(f'{stage}/home-departments.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(review, open(f'{stage}/review.json', 'w'), indent=1, ensure_ascii=False)
    print('accepted rows', len(adds), 'periods', len(periods), 'review', len(review))
    print('PROBLEMS', len(problems)); [print('  ', p) for p in problems]
    print('MISSING', missing)


if __name__ == '__main__':
    main(sys.argv[1])
