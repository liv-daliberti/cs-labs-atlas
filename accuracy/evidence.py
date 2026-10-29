"""Compact evidence sheets for the drawn items (helper for the hand judgments; reads sample.json and the packages).

usage: evidence.py <school> <lab|student|coverage|scov> > sheet.txt
"""
import gzip, html, json, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sample import H, dblp_persons  # noqa: E402

ACC = Path(__file__).parent


def nt(t):
    t = unicodedata.normalize('NFKD', html.unescape(str(t or ''))).lower()
    return re.sub(r'[^a-z0-9]+', '', ''.join(c for c in t if not unicodedata.combining(c)))[:120]


def ndoi(d):
    return re.sub(r'^https?://(dx\.)?doi\.org/', '', str(d or '').lower()).strip() or None


def yr(p):
    per = ';'.join(f"{q['id'].split('_')[-1]}:{q.get('start')}-{q.get('end') or ''}" for q in p.get('periods') or [])
    ly = sorted({l['year'] for l in p.get('listings') or []})
    return f"periods[{per}] listings[{ly[0] if ly else ''}-{ly[-1] if ly else ''} n={len(ly)}]"


def short(x, n):
    x = re.sub(r'\s+', ' ', str(x or ''))
    return x if len(x) <= n else x[:n] + '…'


def main(school, what):
    S = json.load(open(ACC / 'sample.json'))['schools'][school]
    pis = {p['pi']: p for p in json.load(open(H / school / 'pis.json'))}
    if what in ('lab', 'coverage'):
        pages = dblp_persons({q for p in pis.values() for q in p.get('dblp') or []})
        dd = {pi: ({ndoi(x) for q in p.get('dblp') or [] for r in pages.get(q, []) for x in r['dois']},
                   {nt(r['title'].rstrip('.')) for q in p.get('dblp') or [] for r in pages.get(q, [])}) for pi, p in pis.items()}
        del pages
    if what == 'lab':
        want = {it['i']: it for it in S['lab_precision']}
        for i, line in enumerate(gzip.open(H / school / 'lab_papers.jsonl.gz', 'rt')):
            if i not in want:
                continue
            r, it = json.loads(line), want[i]
            a, p = r['authorship'], pis[r['pi']]
            ondblp = 'DOI' if r.get('doi') and ndoi(r['doi']) in dd[r['pi']][0] else ('TITLE' if nt(r['title']) in dd[r['pi']][1] else 'no')
            ap = r.get('appointment') or {}
            print(f"#{i} [{it['stratum']}] PI={r['pi']} ({','.join(p.get('departments') or [])}) {yr(p)} dblp_ids={len(p.get('dblp') or [])}")
            print(f"   T={short(r['title'],110)} | {r.get('date')} {r.get('type')} | {short(r.get('venue'),40)} | doi={r.get('doi')} {r['oa'].split('/')[-1]}")
            print(f"   AUTH raw={a.get('raw_name')} pos={a.get('position')} inst={short(a.get('institutions'),80)} aff={short(a.get('raw_affiliations'),110)}")
            print(f"   VIA={short(a.get('school_via'),110)} | id={r.get('identity')} | appt={ap.get('periodId') or ap.get('listing') and ('listing ' + str(ap['listing'].get('year') if isinstance(ap['listing'], dict) else ap['listing']))} | onPIdblp={ondblp}")
            print(f"   BYLINE({len(r.get('byline') or [])})={short(r.get('byline'),120)} | school={short(r.get('byline_school'),70)} eds={len(r.get('editions') or [])}")
    elif what == 'student':
        want = {it['i']: it for it in S['student_precision']}
        rows, works = {}, set()
        for i, line in enumerate(gzip.open(H / school / 'student_papers.jsonl.gz', 'rt')):
            if i in want:
                rows[i] = json.loads(line); works.add((rows[i]["pi"], rows[i]["oa"]))
        lp = {}
        for line in gzip.open(H / school / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            if (r["pi"], r["oa"]) in works:
                lp[(r["pi"], r["oa"])] = r
        stj = json.load(open(H / school / 'students.json'))
        for i in sorted(rows):
            r, it = rows[i], want[i]
            s = next((x for x in stj.get(r['pi']) or [] if x['person'] == r['student']), {})
            rels = '; '.join(f"{rel.get('type')}{sorted(set(rel.get('years') or []))[:1]}..{sorted(set(rel.get('years') or []))[-1:]} " +
                             short((rel.get('sources') or [{}])[0].get('quote') or (rel.get('sources') or [{}])[0].get('url'), 90)
                             for rel in (s.get('relations') or [])[:3])
            L = lp.get((r["pi"], r["oa"]), {})
            fam = [t for t in re.split(r'[\s.,-]+', unicodedata.normalize('NFKD', s.get('name') or r.get('name') or '').lower()) if len(t) > 1]
            fam = fam[-1] if fam else '?'
            def m(b):
                return fam in unicodedata.normalize('NFKD', str(b)).lower()
            hit = [b for b in L.get('byline') or [] if m(b)] + [b for e in L.get('editions') or [] for b in e.get('byline') or [] if m(b)]
            print(f"#{i} [{it['stratum']}] PI={r['pi']} STUDENT={r.get('name')} ({r['student']}) basis={r.get('basis')} status={r.get('status')}")
            print(f"   S: name={s.get('name')} aliases={s.get('aliases')} roles={s.get('roles')} rels={short(rels,260)}")
            print(f"   P: {short(L.get('title'),100)} | {L.get('date')} | {short(L.get('venue'),35)} | {r['oa'].split('/')[-1]} doi={L.get('doi')}")
            print(f"   byline hits={sorted(set(hit))} | n={len(L.get('byline') or [])} school={short(L.get('byline_school'),120)}")
    elif what == 'coverage':
        items = S['lab_coverage']
        have = {}
        for line in gzip.open(H / school / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            for e in [r] + list(r.get('editions') or []):
                if e.get('doi'):
                    have.setdefault(('d', ndoi(e['doi'])), []).append((r['pi'], r['oa']))
            have.setdefault(('t', nt(r['title'])), []).append((r['pi'], r['oa']))
        for it in items:
            d, p = it['dblp'], pis[it['pi']]
            hits = [x for k in [('d', ndoi(x)) for x in d['dois']] + [('t', nt(d['title'].rstrip('.')))] for x in have.get(k, [])]
            own = sorted({x[1].split('/')[-1] for x in hits if x[0] == it['pi']})
            other = sorted({x[0] for x in hits if x[0] != it['pi']})
            print(f"* {it['key']} | {d['type']} {d['year']} | {short(html.unescape(d['title']),110)} | dois={d['dois']}")
            print(f"   authors={short(d['authors'],160)} | PI {yr(p)} depts={p.get('departments')}")
            print(f"   BUILD: in_PI_lab={own or 'NO'} other_labs={other[:3]}")
    elif what == 'scov':
        stj = json.load(open(H / school / 'students.json'))
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 14
        start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        cands = S['student_coverage_order'][start:start + n]
        need = {c['pi'] for c in cands}
        pages = dblp_persons({q for pi in need for q in pis[pi].get('dblp') or []})
        sp = {}
        for line in gzip.open(H / school / 'student_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            if r['pi'] in need:
                sp.setdefault((r['pi'], r['student']), []).append(r)
        lp = {}
        for line in gzip.open(H / school / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            if r['pi'] in need:
                lp[(r['pi'], r['oa'])] = r
                lp.setdefault(('t', r['pi'], nt(r['title'])), r)
                if r.get('doi'):
                    lp.setdefault(('d', r['pi'], ndoi(r['doi'])), r)

        def nm(x):
            t = [w for w in re.split(r'[\s.]+', unicodedata.normalize('NFKD', re.sub(r'\s+\d{4}$', '', x)).encode('ascii', 'ignore').decode().lower().replace('-', ' ')) if w]
            return t
        for c in cands:
            s = next(x for x in stj[c['pi']] if x['person'] == c['person'])
            src = [so for rel in s.get('relations') or [] for so in rel.get('sources') or []]
            q = next((short(so.get('quote') or so.get('url'), 130) for so in src if re.search(r'(?i)thes|dissert|phd|doctoral', str(so))), short(src[0], 130) if src else '')
            links = sp.get((c['pi'], c['person']), [])
            forms = [nm(f) for f in [s['name']] + list(s.get('aliases') or [])]
            co = []
            for qid in pis[c['pi']].get('dblp') or []:
                for r in pages.get(qid, []):
                    if any(len(f) >= 2 and len(a) >= 2 and a[-1] == f[-1] and a[0][0] == f[0][0] for a in map(nm, r['authors']) for f in forms):
                        inb = lp.get(('t', c['pi'], nt(r['title'].rstrip('.')))) or next((lp.get(('d', c['pi'], ndoi(d))) for d in r['dois'] if lp.get(('d', c['pi'], ndoi(d)))), None)
                        co.append(f"{r['year']} {short(html.unescape(r['title']),60)} [{r['key'].split('/')[0]}/{r['key'].split('/')[1]}]{' IN-LAB ' + inb['oa'].split('/')[-1] if inb else ''}")
            co.sort(reverse=True)
            print(f"* {c['key']} | {c['name']} aliases={s.get('aliases')} roles={s.get('roles')} phd_year={c['phd_year']}")
            print(f"   src: {q}")
            print(f"   linked={len(links)}: {[(l['oa'].split('/')[-1], short((lp.get((c['pi'], l['oa'])) or {}).get('title'), 40)) for l in links[:3]]}")
            print(f"   PI-DBLP coauthored={len(co)} ({sum('IN-LAB' in x for x in co)} in lab): {co[:4]}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
