"""Per-lab website register (owner 2026-11-07: every lab has a lab website or a reason why not).

A read-only consolidation of the lab-page audit's records (tools/labpage_audit.py, docs/LAB-PAGES.md): for every PI of a school,
the lab's own page or the PI's homepage with how it was found, a sha256 and the date, or the audit's reason code with the places checked.
It builds no parallel discovery: a PI the audit has no record for is listed as `unaudited` (run `labpage_audit.py discover <school>`).

  lab_websites.py build <school> [--out FILE]     -> hierarchy/<school>/reviewed/lab-websites.json
  lab_websites.py summary <school>...
"""
import argparse
import gzip
import json
import sys

import atlas_paths as P

FOUND_RESULTS = ('ok', 'ok_wayback', 'does_not_name_pi_kept_strong_source')


def how_found(lp):
    """The check that produced the chosen site: its source (school_profile_link, dblp_person_url, ...) and the page it was listed on."""
    url = (lp.get('urls') or {}).get('lab_site')
    for c in lp.get('checks') or []:
        if c.get('source') == 'candidate_site' and c.get('url') == url and c.get('result') in FOUND_RESULTS:
            via = c.get('via') or 'candidate'
            on = next((x.get('on') for x in lp['checks'] if x.get('source') == via and x.get('url') == url and x.get('on')), None)
            return via, on, c
    return lp.get('source') or 'prior_pass', None, None


def entry(rec):
    lp = rec['lab_page']
    urls = lp.get('urls') or {}
    ev = lp.get('evidence') or {}
    out = {'pi': rec['pi'], 'status': lp['status'], 'reason_code': lp['reason_code'], 'reason': lp['reason'], 'audited_at': rec.get('audited_at')}
    if urls.get('lab_site'):
        via, on, chk = how_found(lp)
        out.update(url=urls['lab_site'], kind='lab_site' if lp['status'] == 'found' else 'pi_homepage', people_page=urls.get('people_page'),
                   alumni_page=urls.get('alumni_page'), pubs_page=urls.get('pubs_page'), found_via=via, listed_on=on,
                   sha256=ev.get('sha256') or (chk or {}).get('sha256'), checked_at=(chk or {}).get('at') or rec.get('audited_at'),
                   students_page_status=rec['students']['page_status'])
    else:
        out['places_checked'] = sorted({f"{c['source']}:{c['result']}" for c in lp.get('checks') or []})
        out['checked_at'] = max((c.get('at') or '' for c in lp.get('checks') or []), default=None) or rec.get('audited_at')
    return out


def build(school):
    pis = [p['pi'] for p in json.load(open(P.data('pis.json', school)))]
    recs = {}
    with gzip.open(P.data('labpage-audit.jsonl.gz', school), 'rt') as f:
        for line in f:
            r = json.loads(line)
            recs[r['pi']] = r
    labs = [entry(recs[p]) if p in recs else {'pi': p, 'status': 'unaudited'} for p in pis]
    return {'school': school, 'tool': 'tools/lab_websites.py', 'source': 'labpage-audit.jsonl.gz', 'labs': labs}


def counts(doc):
    c = {'labs': len(doc['labs']), 'website': 0, 'reason': 0, 'neither': 0}
    for e in doc['labs']:
        if e.get('url'):
            c['website'] += 1
        elif e['status'] == 'none_found' and e.get('reason_code') and e.get('places_checked') is not None:
            c['reason'] += 1
        else:
            c['neither'] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'summary'])
    ap.add_argument('schools', nargs='+')
    ap.add_argument('--out')
    a = ap.parse_args()
    for s in a.schools:
        doc = build(s)
        if a.cmd == 'build':
            out = a.out or str(P.data_w('lab-websites.json', s))
            json.dump(doc, open(out, 'w'), indent=1, ensure_ascii=False)
        print(s, json.dumps(counts(doc)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
