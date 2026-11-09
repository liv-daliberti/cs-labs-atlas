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
from pi_hierarchy import toks  # noqa: E402

SKIP = ('labpage', 'homepage', 'defense', 'gap', 'student-directory')
TODAY = '20261109'
RULE = ('Leads: OpenAlex sweep authors with >= 5 DBLP-indexed school works and >= 20% of their school works so, DBLP-affiliated persons and '
        'listed-not-in-census names, none in the census or a prior cs-related decision. Accepted only with a stored unit/profile capture that names '
        'the person followed by a ladder professor title; an OpenAlex or DBLP affiliation alone is never appointment evidence.')


def slug(name):
    return '-'.join(toks(name))


def title_after(text, m_end):
    tail = text[m_end:m_end + 90]
    t = C.PROF_T.search(tail)
    if not t or t.start() > 45:
        return None
    between = tail[:t.start()]
    if re.search(r'[a-z]{2,}\s+[A-Z][a-z]+\s+[A-Z][a-z]+', between):  # another person's name sits between
        return None
    title = tail[:t.end()].strip(' ,;-–')
    return title


def faculty_hits(rows, name):
    t = re.sub(r'[^\w ]', '', name).split()
    pat = re.compile(re.escape(t[0]) + r'[\w. ()"\u2019-]{0,25}' + re.escape(t[-1]), re.I)
    out = []
    for url, dept, ts, sha, text in rows:
        m = pat.search(text)
        if not m:
            continue
        title = title_after(text, m.end())
        if title:
            out.append({'url': url, 'sha256': sha, 'observed': ts, 'dept': dept, 'year': int((ts or '0000')[:4]) or None,
                        'quote': ' '.join((m.group(0) + ' ' + title).split()), 'ladder': not C.NOT_LADDER.search(title)})
    return out


def run(school, apply=False, min_cs=5):
    leads, per_source = ML.build(school, min_cs)
    root = Path(P.CODE) / 'hierarchy' / school
    db = sqlite3.connect(f'file:{P.data("school-captures.sqlite", school)}?mode=ro', uri=True)
    rows = [r for r in db.execute("select capture_url,department,wayback_timestamp,sha256,text from captures where http_status=200 and text is not null")
            if not r[1].startswith(SKIP)]
    units = sorted({r[1].split(':')[0] for r in rows})
    hand = ML.load(root / 'reviewed/missed-labs-hand.json') or {}
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
    print(school, 'per source', per_source, 'decisions', counts)
    adds = []
    for e, lad in accepted:
        yrs = sorted({x['year'] for x in lad if x['year']})
        adds.append({'name': e['name'], 'aliases': [], 'collection_person_id': f'{school}_fac_{slug(e["name"])}', 'dblp': e['dblp'],
                     'rank': 'ladder', 'title_as_listed': lad[0]['quote'], 'departments': sorted({x['dept'].split(':')[-1] for x in lad}),
                     'years_listed': yrs,
                     'sources': [{'url': x['url'], 'sha256': x['sha256'], 'quote': x['quote'], 'kind': 'unit_listing:' + x['dept'].split(':')[-1],
                                  'observed': x['observed']} for x in lad],
                     'is_pi': True,
                     'pi_basis': {'kind': 'ladder_faculty', 'url': lad[0]['url'], 'sha256': lad[0]['sha256'], 'quote': lad[0]['quote'],
                                  'observed': lad[0]['observed'], 'role': 'professor title on a stored unit or profile capture',
                                  'cs_related': {'dblp': e['dblp'], 'openalex': e['oa_ids'], 'dblp_indexed': e['cs'], 'school_works': e['works'],
                                                 'share': round(e['cs'] / max(e['works'], 1), 3)}},
                     'lab_units': [], 'added': 'missed_labs_' + TODAY})
    for a in adds:
        print('ACCEPT', a['name'], a['departments'], a['years_listed'], '|', a['title_as_listed'], '| cs', a['pi_basis']['cs_related']['dblp_indexed'], '/',
              a['pi_basis']['cs_related']['school_works'])
    if apply:
        rv = Path(P.CODE).parent / 'worktrees/missed-labs-b' / 'hierarchy' / school / 'reviewed'
        rv.mkdir(parents=True, exist_ok=True)
        (rv / 'missed-labs-review.json').write_text(json.dumps({'school': school, 'reviewed': TODAY, 'rule': RULE, 'units_searched': units,
                                                                'counts': counts, 'per_source': per_source, 'decisions': decisions}, indent=1, ensure_ascii=False))
        cur = ML.load(rv / 'census-additions.json')
        if cur is None:
            cur = ML.load(root / 'reviewed/census-additions.json') or []
        have = {r['name'] for r in cur}
        cur = [r for r in cur if r.get('added') != 'missed_labs_' + TODAY] + [a for a in adds if a['name'] not in have]
        (rv / 'census-additions.json').write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    return decisions, adds


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('school'); ap.add_argument('--apply', action='store_true'); a = ap.parse_args()
    run(a.school, a.apply)
