"""JHU Computer Science PhD graduate pages: the department's own defense announcements name each graduate's adviser (R-STU-26).

A page (www.cs.jhu.edu/graduate-studies/2016-phd-graduates/, .../2018-19-phd-graduates/, people/phd-graduates/) holds one block per graduate:
"The Department of Computer Science would like to congratulate Dr. X on the recent successful defense of his thesis work, "T" on <Month d, YYYY>.
Primary Advisor: <PI>[, <PI>]. ..." The block is the department's record that the PI advised the graduate; the defense year is the year of the degree (R-STU-14).

reads    the stored Wayback captures of those pages in the school capture store (department 'student-directory'); nothing is fetched here
writes   defense-evidence.json rows (the shape tools/labpage_students_school.py extract merges as role phd_alumnus, years_basis defense_date):
         {student, host, year, url, capture_url, sha256, quote, host_quote}; host is one adviser name (one row per named adviser)
usage:   cs_phd_graduates.py jhu [--out FILE]
"""
import argparse
import json
import re

import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402

PAGES = re.compile(r'/(?:graduate-studies/(?:2016|2016-17|2017-18|2018-19)-phd-graduates|people/phd-graduates)/?$')
NAME = re.compile(r'^would like to congratulate (?:Dr\.\s+)?(.{3,60}?) on the recent successful defense of (?:his|her|their) thesis work')
DATE = re.compile(r'\bon ((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, (20\d\d))\b')
ADV = re.compile(r'((?:Primary )?Advis[eo]rs?: (.{3,120}?))(?= The Department| Professional Plans| For more| Secondary| Co-?[Aa]dvis| Graduate Studies|$)')


TOK = r"(?:[A-Z][\w'\u2019-]+|[A-Z]\.)"
OLD = re.compile(r'(' + TOK + r'(?: ' + TOK + r'){1,3}) Defense Date: ((?:\w+, )?(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, (20\d\d))'
                 r'.{0,600}?(Primary Advisor: ((?:(?! Abstract:| Biography:).){3,80}?))(?= Abstract:| Biography:| Co-)')


def rows(school='jhu'):
    c = W.con(school)
    seen, out = {}, []
    for cap, txt, ts in c.execute("select capture_url, text, wayback_timestamp from captures where department='student-directory' and http_status=200 order by wayback_timestamp"):
        if not PAGES.search(re.sub(r'^https?://web\.archive\.org/web/\d+id_/', '', cap)):
            continue
        flat = ' '.join((txt or '').replace('\n', ' | ').split())
        flat = flat.replace(' | ', ' ')
        sha = c.execute('select sha256 from captures where capture_url=?', (cap,)).fetchone()[0]
        starts = [m.start() for m in re.finditer(r'would like to congratulate ', flat)]
        for i, st in enumerate(starts):
            chunk = flat[st:starts[i + 1] if i + 1 < len(starts) else len(flat)]
            mn, md, ma = NAME.match(chunk), DATE.search(chunk), ADV.search(chunk)
            if not (mn and md and ma) or ma.start() < md.start():
                continue
            name, yr, hq = re.sub(r'^(?:Dr\.\s+)+', '', mn.group(1).strip()), int(md.group(2)), ma.group(1).rstrip(' .')
            q = chunk[:mn.end(1)]
            for adv in re.split(r'\s*(?:,|;|\band\b|&)\s*', ma.group(2).rstrip(' .')):
                adv = adv.strip()
                if len(adv.split()) < 2 or (name, adv) in seen:
                    continue
                seen[(name, adv)] = 1
                out.append(dict(student=name, host=adv, year=yr, url=re.sub(r'^https?://web\.archive\.org/web/\d+id_/', '', cap), capture_url=cap, sha256=sha,
                                quote=q, host_quote=hq, defense_date=md.group(1), observed=ts[:8]))
        for m in OLD.finditer(flat):   # the 2016-17 page: "<Name> Defense Date: <date> Title: ... Primary Advisor: <PI> Abstract:"
            name, yr, hq = m.group(1), int(m.group(3)), m.group(4)
            for adv in re.split(r'\s*(?:,|;|\band\b|&)\s*', m.group(5).rstrip(' .')):
                adv = adv.strip()
                if len(adv.split()) < 2 or (name, adv) in seen:
                    continue
                seen[(name, adv)] = 1
                out.append(dict(student=name, host=adv, year=yr, url=re.sub(r'^https?://web\.archive\.org/web/\d+id_/', '', cap), capture_url=cap, sha256=sha,
                                quote=flat[m.start():m.start(3)] + str(yr), host_quote=hq, defense_date=m.group(2), observed=ts[:8]))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('school')
    ap.add_argument('--out')
    a = ap.parse_args()
    r = rows(a.school)
    for x in r:
        assert x['quote'] in ' '.join(W.con(a.school).execute('select text from captures where capture_url=?', (x['capture_url'],)).fetchone()[0].replace('\n', ' ').split()), x
    P.data_w('defense-evidence.json', a.school).write_text(json.dumps(r, indent=1, ensure_ascii=False)) if not a.out else open(a.out, 'w').write(json.dumps(r, indent=1, ensure_ascii=False))
    print(len(r), 'rows', len({x['student'] for x in r}), 'students', len({x['host'] for x in r}), 'advisers')
