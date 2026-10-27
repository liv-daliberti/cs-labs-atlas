"""Why does a PI lab lack papers or students? One row per gap lab, from the package funnel and the collection.

papers   no_person (no collection person and no DBLP list) | no_identity_anchor (no DBLP list, no verified works) |
         no_openalex_name_hits (OpenAlex has no authorship of that name at the school) | no_school_affiliation (name hits,
         none listing the school) | identity_unproven (school-affiliated hits, none tied to the PI) |
         outside_appointment (proven papers, none in a period or a listed year)
students no_advising_records (no advising context mentions the surname) | adviser_name_unmatched (mentions, no match) |
         advising_matched_elsewhere (records exist but another census row took them)
-> hierarchy/<school>/gaps.json and a printed summary
usage: diagnose_gaps.py <school> [...]
"""
import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import read, toks, SITE, HERE  # noqa: E402


def diagnose(school):
    pis = read(HERE / 'hierarchy' / school / 'pis.json')
    own_c = HERE / 'hierarchy' / school / 'collection.json.gz'
    C = read(own_c if own_c.exists() else SITE / f'collection-{school}.json.gz')
    people = C['people'] if isinstance(C['people'], list) else list(C['people'].values())
    mentions = collections.Counter()  # surname -> advising contexts mentioning it
    for person in people:
        for c in person.get('contexts') or []:
            if 'advis' not in (c.get('type') or ''):
                continue
            txt = ' '.join(str(x) for x in [c.get('advisorName'), c.get('advisor')] + list(c.get('advisors') or []) +
                           [s.get('quote') or '' for s in c.get('sources') or []])
            for t in set(toks(txt)):
                mentions[t] += 1
    rows = []
    for p in pis:
        c = p['counts']; f = p.get('funnel') or {}
        if c['labPapers'] and c['students']:
            continue
        r = dict(pi=p['pi'], rank=p.get('rank'), title=p.get('title'), listed=[l['year'] for l in p['listings']],
                 periods=[(q['start'], q['end']) for q in p['periods']], person=bool(p['personIds']), funnel=f, students=c['students'])
        if not c['labPapers']:
            r['papers'] = ('no_person' if not p['personIds'] and not f.get('dblpTitles') else
                           'no_identity_anchor' if not f.get('dblpTitles') and not f.get('verifiedWorks') else
                           'no_openalex_name_hits' if not f.get('name_hits') else
                           'no_school_affiliation' if not f.get('school_affiliated') else
                           'identity_unproven' if not f.get('identity') else 'outside_appointment')
        if not c['students']:
            sur = (toks(p['pi']) or [''])[-1]
            r['studentMentions'] = mentions.get(sur, 0)
            r['students_cause'] = 'no_advising_records' if not r['studentMentions'] else 'adviser_name_unmatched_or_namesake'
        rows.append(r)
    json.dump(rows, open(HERE / 'hierarchy' / school / 'gaps.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(dict(school=school, gap_labs=len(rows), papers=dict(collections.Counter(r.get('papers') for r in rows if r.get('papers'))),
                          students=dict(collections.Counter(r.get('students_cause') for r in rows if r.get('students_cause'))),
                          ranks=dict(collections.Counter(str(r['rank']) for r in rows)))))


if __name__ == '__main__':
    for s in sys.argv[1:]:
        diagnose(s)
