"""s2_title step (2026-10-29): Semantic Scholar /paper/search/match for missing lab papers that the s2 step's DOI batch
could not use: papers with no DOI (and no arXiv id), and papers whose DOI has no S2 record (cached 'DOI:..' with no data).
Requests go through ../../claude-cmu-20261017/tools/s2_key_lookup.py s2() (the user's key from the environment, never
printed; one request per 1.2 s across every process via its wait_turn() pacing file; 429 backs off). The run stops
after 15 consecutive failed answers (search/match has answered 429 from this network before). Answers are cached in the
same cache as the s2 step (raw/s2_key.jsonl, id 'match:<normalized title>').
A match counts only as s2_key_lookup.candidates() decides: identical normalized title, a shared author family name with
the byline, a year within 2. Its ArXiv id -> the bulk copy on GCS, ACL id -> aclanthology.org, PMCID -> NLM's S3 copy,
openAccessPdf on a usable host.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone

import ftp_common as F


def step(school, miss, known, n, has_arxiv):
    import os, requests
    import s2_key_lookup as s2k
    cache = {}
    if s2k.CACHE.exists():
        for line in s2k.CACHE.open():
            try:
                r = json.loads(line); cache[r['id']] = r
            except ValueError:
                pass
    targets = []
    for r, w in miss:
        d = F.ndoi(r.get('doi'))
        a = F.arxiv_of(r, None)
        if a or len(F.nt(r.get('title'))) < 20:
            continue
        if d:
            rec = cache.get('DOI:' + d) or cache.get('DOI:' + (r.get('doi') or ''))
            if not rec or rec.get('error') or rec.get('data'):
                continue
            n['s2_title_doi_without_record'] += 1
        else:
            n['s2_title_no_doi'] += 1
        targets.append(dict(school=school, work_id=w, doi=None, corpus=None, title=r['title'], year=r.get('year'),
                            people=list(r.get('byline') or []) + list(r.get('pis') or [])))
    todo = list(dict.fromkeys(t['title'] for t in targets if 'match:' + s2k.nt(t['title']) not in cache
                              or cache['match:' + s2k.nt(t['title'])].get('error')))
    n['s2_title_to_ask'] = len(todo)
    s = requests.Session(); s.headers['x-api-key'] = os.environ['S2_API_KEY']; s.headers['User-Agent'] = s2k.UA
    fails = 0
    with s2k.CACHE.open('a') as f:
        for k, title in enumerate(todo):
            r = s2k.s2(s, 'GET', '/paper/search/match', params={'query': title, 'fields': s2k.FIELDS})
            lid = 'match:' + s2k.nt(title)
            at = datetime.now(timezone.utc).isoformat()
            if r is None or r.status_code not in (200, 404, 400):
                rec = dict(id=lid, at=at, error=r.status_code if r is not None else 'failed'); fails += 1
            else:
                rec = dict(id=lid, at=at, data=(r.json().get('data') or [None])[0] if r.status_code == 200 else None); fails = 0
                n['s2_title_answered'] += 1
            cache[lid] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
            if fails >= 15:
                n['s2_title_stopped_after_failures'] = k + 1
                break
            if k % 200 == 199:
                print(json.dumps(dict(s2_title_asked=k + 1, of=len(todo))), flush=True)
    found, cn = s2k.candidates(targets, defaultdict(set, {w: set(u) for w, u in known.items()}), cache)
    for k, v in cn.items():
        n['s2_title_' + k] += v
    return [dict(work_id=t['work_id'], url=u, landing_url=land, version=ver, source='s2_title_' + src, detail=det) for t, u, land, ver, src, det in found]
