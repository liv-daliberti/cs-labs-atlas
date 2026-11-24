"""Missed-labs review (coordinator brief 2026-11-09): decide the leads of tools/missed_labs_leads.py from HELD captures and write
the reviewed file + census additions.

faculty evidence  a stored unit / profile capture (hierarchy/<school>/raw/school-captures.sqlite, departments other than labpage, homepage,
                  defense, gap, student-directory) where the lead's name is followed within 45 characters by a ladder professor title
                  (cs_related_school.PROF_T and not NOT_LADDER); quote, url, sha256 and year are taken from the capture
computing         the cs-related share test on the OpenAlex sweep: >= 5 DBLP-indexed school works and >= 20% of the author's school works
                  (the leads tool's filter), recorded with the author ids; an OpenAlex affiliation is never appointment evidence
decisions         accepted | not_faculty (a title that is not ladder, or a student/member of a PI) | no_appointment_evidence (kept lead)
                  | already_decided (a prior cs-related decision) ; hand decisions in reviewed/missed-labs-hand.json override:
                  {name: {decision, reason}} (faculty_not_computing, left_before_window, already_in_census_as, not_faculty ...)
-> hierarchy/<school>/reviewed/missed-labs-review.json   {school, reviewed, rule, units_searched, counts, decisions}
-> hierarchy/<school>/reviewed/census-additions.json     accepted rows appended (added = missed_labs_20261109), existing rows untouched
usage: missed_labs_review.py <school> [--apply]   (without --apply: prints the counts and the accepted rows only)
"""
import argparse, json, re, sqlite3
from pathlib import Path

import atlas_paths as P  # noqa: E402
import cs_related_school as C  # noqa: E402
import missed_labs_leads as ML  # noqa: E402
from pi_hierarchy import Name, toks  # noqa: E402

SKIP = ('labpage', 'homepage', 'defense', 'gap', 'student', 'cv', 'thesis', 'roster', 'wikidata')
TODAY = '20261109'
WAYBACK_QUEUE = {   # pages the stored captures do not hold; fetched later through the shared Wayback throttle (WAYBACK_LOW=1, queued, no retry on 429)
    'uchicago': ['https://cs.uchicago.edu/people/faculty/', 'https://cs.uchicago.edu/people/', 'https://datascience.uchicago.edu/people/faculty/'],   # cs.uchicago.edu was down for maintenance
    'jhu': ['https://www.cs.jhu.edu/faculty/', 'https://engineering.jhu.edu/faculty/', 'lab hosts of the verify_queue leads (bot-challenged: Wayback only)'],
}
RULE = ('Leads: OpenAlex sweep authors with >= 5 DBLP-indexed school works and >= 20% of their school works so, DBLP-affiliated persons and '
        'listed-not-in-census names, none in the census or a prior cs-related decision. Accepted only with a stored unit/profile capture that names '
        'the person followed by a ladder professor title; an OpenAlex or DBLP affiliation alone is never appointment evidence.')


def slug(name):
    return '-'.join(toks(name))


def title_after(text, m_end, own=None):
    tail = text[m_end:m_end + 260]
    t = C.PROF_T.search(tail)
    if not t or t.start() > (200 if own and own in tail[:t.start()] else 45):
        return None
    between = tail[:t.start()]
    if re.search(r'former|retired|emerit|visiting', between, re.I):
        return None
    if own and own in between:
        pass   # a profile heading repeats the person's own name ('Isaac Kohane, MD, PhD Isaac Kohane, MD, PhD Chair of ...')
    elif re.search(r'[a-z]{2,}\s+[A-Z][a-z]+\s+[A-Z][a-z]+', between) and not re.fullmatch(r"(?:\s*(?:[A-Z][\w.'-]*|and|&|of))+\s*", between):
        return None  # another person's name sits between (a named chair such as 'Harry Lewis and Marlyn McGrath Professor' is the person's own title)
    return tail[:t.end()], t.end()


def faculty_hits(rows, name):
    t = re.sub(r'[^\w ]', '', name.replace('-', ' ')).split()
    pat = re.compile(r'(?<![\w])' + re.escape(t[0]) + r'[\w. ()"\u2019-]{0,25}?' + r'(?<![\w])' + re.escape(t[-1]) + r'(?-i:(?![a-z]))', re.I)
    out = []
    for url, dept, ts, sha, text in rows:
        for m in pat.finditer(text):   # every mention: a profile page names the person in its navigation before the heading that carries the title
            ta = title_after(text, m.end(), t[-1])
            if not ta:
                continue
            title, tend = ta
            out.append({'url': url, 'sha256': sha, 'observed': ts, 'dept': dept, 'year': int((ts or '0000')[:4]) or None,
                        'quote': ' '.join(text[m.start():m.end() + tend].split()), 'ladder': not C.NOT_LADDER.search(title)})
            break
    return out


def scratch_rows(school):
    """(url, 'profile', timestamp, sha256, text) for the pages the profile pass stored in the scratch store (live 200s and Wayback 200s)."""
    import time, zlib
    import school_web as W
    f = Path('/n/fs/resemble/homogenizing-science/scratch/missed-labs-profile') / f'{school}.sqlite'
    if not f.exists():
        return []
    c = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
    out = []
    for url, fetched, st, sha, ct, raw in c.execute('select url, fetched_at, status, sha256, content_type, raw_zlib from live where status=200'):
        try:
            text = W.flat(W.extract.blocks(zlib.decompress(raw), ct, url))
        except Exception:  # noqa: BLE001
            continue
        out.append((url, 'profile', (fetched or time.strftime('%Y%m%d')).replace('-', '').replace(':', '')[:8], sha, text))
    try:
        for url, ts, sha, text in c.execute("select capture_url, wayback_timestamp, sha256, text from captures where http_status=200 and text is not null"):
            out.append((url, 'profile', ts, sha, text))
    except sqlite3.OperationalError:
        pass
    return out


def run(school, apply=False, min_cs=5):
    leads, per_source = ML.build(school, min_cs)
    root = Path(P.CODE) / 'hierarchy' / school
    db = sqlite3.connect(f'file:{P.data("school-captures.sqlite", school)}?mode=ro', uri=True)
    rows = [r for r in db.execute("select capture_url,department,wayback_timestamp,sha256,text from captures where http_status=200 and text is not null")
            if not r[1].startswith(SKIP)]
    rows += scratch_rows(school)   # pages of the profile pass (tools/missed_labs_fetch.py), kept outside main's capture store
    units = sorted({r[1].split(':')[0] for r in rows})
    hand = ML.load(Path(__file__).resolve().parents[1] / 'hierarchy' / school / 'reviewed/missed-labs-hand.json') or ML.load(root / 'reviewed/missed-labs-hand.json') or {}
    decisions, accepted = [], []
    for e in leads:
        if 'oa' in e['sources'] and e['works'] and e['cs'] / e['works'] < 0.2 and 'dblp' not in e['sources']:
            continue  # below the computing share: not a lead
        d = {'name': e['name'], 'sources': e['sources'], 'oa_ids': e['oa_ids'], 'dblp_indexed': e['cs'], 'school_works': e['works'],
             'last_author': e['last'], 'years': e['years']}
        h = hand.get(e['name'])
        hits = faculty_hits(rows, e['name']) if len(toks(e['name'])) >= 2 else []
        lad = [x for x in hits if x['ladder']]
        if h:
            d.update(h)
        elif e['prior_decision']:
            d.update(decision='already_decided', reason=f"prior cs-related decision {e['prior_decision']}")
        elif e['student_or_member']:
            d.update(decision='not_faculty', reason='matches a student, postdoc or member recorded for a PI (derived/students.json)')
        elif lad and e['cs'] >= min_cs:
            d.update(decision='accepted', reason='ladder professor title in a stored unit/profile capture; computing share test passed',
                     evidence=lad[:12])
            accepted.append((e, lad))
        elif hits:
            d.update(decision='not_faculty', reason='only a non-ladder title in stored captures', evidence=hits[:3])
        else:
            d.update(decision='no_appointment_evidence', reason='no stored unit/profile capture names them with a professor title; lead kept',
                     units_searched=units)
        decisions.append(d)
    # hand decisions may demote an automatic accept
    accepted = [(e, l) for e, l in accepted if not hand.get(e['name'])]
    counts = {}
    for d in decisions:
        counts[d['decision']] = counts.get(d['decision'], 0) + 1
    live = [d for d in decisions if d['decision'] == 'no_appointment_evidence' and d['years'] and d['years'][-1] >= 2022]
    queue = [{'name': d['name'], 'dblp_indexed': d['dblp_indexed'], 'school_works': d['school_works'], 'last_author': d['last_author'], 'oa_ids': d['oa_ids'],
              'next': 'official unit faculty list / profile via Wayback (live only where robots allows); not in a stored capture'}
             for d in sorted(live, key=lambda d: (-d['last_author'], -d['dblp_indexed']))[:40]]
    print(school, 'per source', per_source, 'decisions', counts)
    merged = []   # one person under two name forms ('Margo I. Seltzer' / 'Margo Seltzer'): keep the one with more works, fold the other in
    for e, lad in sorted(accepted, key=lambda x: -x[0]['works']):
        for m in merged:
            if Name([m[0]['name']]).match(e['name']) or Name([e['name']]).match(m[0]['name']):
                m[0].setdefault('aliases', []).append(e['name']); m[0]['oa_ids'] = sorted(set(m[0]['oa_ids']) | set(e['oa_ids']))
                m[0]['dblp'] = sorted(set(m[0]['dblp']) | set(e['dblp'])); m[1].extend(x for x in lad if x not in m[1])
                for d in decisions:
                    if d['name'] == e['name']:
                        d.update(decision='already_in_census_as', reason=f"name variant of {m[0]['name']} (same pass)")
                break
        else:
            merged.append((e, list(lad)))
    accepted = merged
    counts = {}
    for d in decisions:
        counts[d['decision']] = counts.get(d['decision'], 0) + 1
    adds = []
    for e, lad in accepted:
        yrs = sorted({x['year'] for x in lad if x['year']})
        adds.append({'name': e['name'], 'aliases': e.get('aliases', []), 'collection_person_id': f'{school}_fac_{slug(e["name"])}', 'dblp': e['dblp'],
                     'rank': 'ladder', 'title_as_listed': lad[0]['quote'], 'departments': sorted({x['dept'].split(':')[-1] for x in lad}),
                     'years_listed': yrs,
                     'sources': [{'url': x['url'], 'sha256': x['sha256'], 'quote': x['quote'], 'kind': 'unit_listing:' + x['dept'].split(':')[-1],
                                  'observed': x['observed']} for x in lad],
                     'is_pi': True,
                     'pi_basis': {'kind': 'ladder_faculty', 'url': lad[0]['url'], 'sha256': lad[0]['sha256'], 'quote': lad[0]['quote'],
                                  'observed': lad[0]['observed'], 'role': 'professor title on a stored unit or profile capture',
                                  'cs_related': {'dblp': e['dblp'], 'openalex': e['oa_ids'], 'dblp_indexed': e['cs'], 'school_works': e['works'],
                                                 'share': round(e['cs'] / max(e['works'], 1), 3),
                                                 'oa_share': round(e['oa_cs'] / e['oa_n'], 3) if e.get('oa_n') else None,
                                                 'share_flag': bool(e.get('oa_n')) and e['oa_cs'] / e['oa_n'] < 0.2}},
                     'lab_units': [], 'added': 'missed_labs_' + TODAY})
    for a in adds:
        print('ACCEPT', a['name'], a['departments'], a['years_listed'], '|', a['title_as_listed'], '| cs', a['pi_basis']['cs_related']['dblp_indexed'], '/',
              a['pi_basis']['cs_related']['school_works'])
    if apply:
        rv = Path(__file__).resolve().parents[1] / 'hierarchy' / school / 'reviewed'
        rv.mkdir(parents=True, exist_ok=True)
        (rv / 'missed-labs-review.json').write_text(json.dumps({'school': school, 'reviewed': TODAY, 'rule': RULE, 'units_searched': units,
                                                                'counts': counts, 'per_source': per_source, 'verify_queue': queue, 'wayback_queue': WAYBACK_QUEUE.get(school, []), 'decisions': decisions}, indent=1, ensure_ascii=False))
        cur = ML.load(rv / 'census-additions.json')
        if cur is None:
            cur = ML.load(root / 'reviewed/census-additions.json') or []
        cur = [r for r in cur if r.get('added') != 'missed_labs_' + TODAY]   # idempotent: this pass's rows are rebuilt
        have = {r['name'] for r in cur}
        cur = cur + [a for a in adds if a['name'] not in have]
        (rv / 'census-additions.json').write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    return decisions, adds


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('school'); ap.add_argument('--apply', action='store_true'); a = ap.parse_args()
    run(a.school, a.apply)
