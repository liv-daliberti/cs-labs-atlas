"""Reviewed OpenAlex works created after the sweep snapshot (owner decision D-0073, 2026-11-25; every onboarding school).

The OpenAlex sweep is a snapshot (UMD: 2026-10-14). A work OpenAlex created later for an in-window PI is attributed to the PI as a REVIEWED per-PI
addition, never as a snapshot refresh. Evidence per work (all kept in hierarchy/<key>/reviewed/post-snapshot-works.json):
  - the OpenAlex API work record (`url`) and the sha256 of the fetched JSON (json.dumps(record, sort_keys=True), the oa_identity_school convention);
  - the PI's reviewed OpenAlex author id (census overrides `openalex`, or this file's `authors` section) on that authorship, or the PI's bound ORCID;
  - the raw affiliation string that names the school (`school_test`), as the quote;
  - a publication date inside the PI's appointment window (a listing of the PI from that year, or a reviewed period) and not before the atlas window;
  - created_date after the snapshot.
The query is one request per PI and id kind: works of the author with publication date from `FROM_PUBLICATION` on (the API's from_created_date filter needs a paid plan);
`created_date` and the other tests are applied here. LIMIT: a work created late with a publication date before FROM_PUBLICATION is not found.
Credits: logged in the shared ledger (oa_api); the run stops at its own cap or the shared floor and prints the number of calls.

  post_snapshot_works.py <key>             propose -> hierarchy/<key>/derived/post-snapshot-proposals.json  (READ THEM; nothing is attributed yet)
  post_snapshot_works.py <key> --write     merge the proposals into the reviewed file `works` (an entry already there is kept); then add `reviewed_by`/`why` by hand
pi_hierarchy reads the reviewed file in `pihier.common.sweep_works` (accepted entries whose stored record still hashes to `sha256`), so the ordinary authorship,
identity, appointment and quality rules apply to the work.
"""
import json
import re
import sys

import atlas_paths as P  # noqa: E402
from pihier.common import NOT_PAPERS, SCHOOL_LOOSE, TODAY, WINDOW_START, work_sha  # noqa: E402

SNAPSHOT_CUTOFF = '2026-10-14'      # works created after this date are outside the sweep snapshot
FROM_PUBLICATION = '2026-01-01'
OA = 'https://openalex.org/'


def hits(w, ids, orcids, at_school, listing_years, window_start, raw_rx, cutoff=SNAPSHOT_CUTOFF):
    """The authorships of work `w` that make it a post-snapshot addition for a PI: created after `cutoff`, the author id (or ORCID) is the PI's, the raw affiliation
    names the school (`raw_rx` on a raw affiliation string: it is the quote), the publication year is in the PI's listed years and inside the atlas window, the work is a
    paper (not a NOT_PAPERS type) and not dated after today. -> [authorship summary]; [] when any test fails."""
    if str(w.get('created_date') or '')[:10] <= cutoff or w.get('type') in NOT_PAPERS or str(w.get('publication_date') or '') > TODAY:
        return []
    year = int(w.get('publication_year') or str(w.get('publication_date') or '0')[:4] or 0)
    if year < window_start or year not in set(listing_years):
        return []
    out = []
    for a in w.get('authorships') or []:
        au = a.get('author') or {}
        aid, orc = au.get('id'), re.sub(r'^https?://orcid.org/', '', au.get('orcid') or '')
        raws = [r for r in a.get('raw_affiliation_strings') or [] if r and raw_rx.search(r)]
        if not ((aid and aid in ids) or (orc and orc in orcids)) or not raws or not at_school(a):
            continue
        out.append(dict(author_id=aid, orcid=orc or None, raw_author_name=a.get('raw_author_name'), position=a.get('author_position'),
                        raw_affiliation=next((r for r in raws), ''), institutions=[x.get('display_name') for x in a.get('institutions') or []]))
    return out


def targets(key):
    """[{pi, ids, orcids, years}] for the school's PIs listed in the current year that carry a reviewed OpenAlex id, a hand id of this file's `authors`, or an ORCID."""
    import census_overrides as CO
    ov = CO.section(key)
    rf = P.data('post-snapshot-works.json', key)
    hand = (json.loads(rf.read_text()).get('authors') or {}) if rf.exists() else {}
    cen = json.loads(P.data('census-faculty.json', key).read_text())['faculty']
    out = []
    for x in cen:
        if not x.get('is_pi'):
            continue
        name = x['name']
        years = sorted({int(l['year']) for l in x.get('listings') or [] if l.get('year')}) or sorted({int(y) for y in x.get('years_listed') or []})
        o = ov.get(name) or {}
        ids = [OA + i if not str(i).startswith('http') else i for i in (o.get('openalex') or [])] + list((hand.get(name) or {}).get('openalex') or [])
        orcids = [re.sub(r'^https?://orcid.org/', '', i) for i in ([x.get('orcid')] if isinstance(x.get('orcid'), str) else list(x.get('orcid') or [])) + list((hand.get(name) or {}).get('orcid') or [])]
        if years and years[-1] >= int(SNAPSHOT_CUTOFF[:4]) and (ids or orcids):
            out.append(dict(pi=name, ids=sorted(set(ids)), orcids=sorted(set(orcids)), years=years))
    return out


def query(cl, t):
    """The works of the PI's author ids (else ORCIDs) published since FROM_PUBLICATION: one request (up to 100 works)."""
    if t['ids']:
        filt = 'author.id:' + '|'.join(i.rsplit('/', 1)[-1] for i in t['ids'])
    else:
        filt = 'author.orcid:' + '|'.join(t['orcids'])
    r, _ = cl.get('works', {'filter': f'{filt},from_publication_date:{FROM_PUBLICATION}', 'per-page': '100'}, kind='post-snapshot')
    return (r or {}).get('results') or []


def main(key, write=False, cap=400, floor=3000):
    import oa_api
    from cs_related_candidates import school_test
    cl = oa_api.Client(cap=cap, kind='post-snapshot', floor=floor)
    at_school = school_test(key)
    raw_rx = re.compile(SCHOOL_LOOSE[key], re.I)
    window_start = int(str(WINDOW_START)[:4])
    props, n = [], dict(pis=0, works_fetched=0)
    for t in targets(key):
        n['pis'] += 1
        for w in query(cl, t):
            n['works_fetched'] += 1
            h = hits(w, set(t['ids']), set(t['orcids']), at_school, t['years'], window_start, raw_rx)
            if h:
                props.append(dict(pi=t['pi'], work=w['id'], doi=w.get('doi'), title=w.get('title'), publication_date=w.get('publication_date'), created_date=w.get('created_date'),
                                  url=w['id'].replace(OA, 'https://api.openalex.org/works/'), sha256=work_sha(w), authorships=h, record=w))
    out = P.data('post-snapshot-works.json', key).parent.parent / 'derived' / 'post-snapshot-proposals.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(cutoff=SNAPSHOT_CUTOFF, from_publication=FROM_PUBLICATION, calls=cl.requests, credits=cl.used, proposals=props), indent=1, ensure_ascii=False))
    if write:
        rf = P.data_w('post-snapshot-works.json', key)
        cur = json.loads(rf.read_text()) if rf.exists() else {}
        cur.setdefault('works', {})
        for p in props:
            cur['works'].setdefault(p['work'], {k: p[k] for k in ('pi', 'work', 'doi', 'title', 'publication_date', 'created_date', 'url', 'sha256', 'authorships', 'record')})
        rf.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    print(json.dumps(dict(**n, proposals=len(props), calls=cl.requests, credits=cl.used, remaining=cl.remaining)))


if __name__ == '__main__':
    main(sys.argv[1], '--write' in sys.argv)
