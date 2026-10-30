"""Access review of works at status 'needs_access_review' (2026-10-29).

The collector (homogenizing-science/scripts/collect_princeton_fulltext_expanded.py save_result) sets needs_access_review
when every candidate URL it tried for a work failed. It asks a (work, URL) pair again only when the pair has no attempts
row, so 'back to the queue' means what collector_wrapper.py requeue and fulltext-push/retry_transient.py do: delete the
pair's attempt rows (each kept in <store>/staged/requeued-attempts.jsonl) and the next pass asks again.

Per URL the failure cause comes from the attempt detail and host: challenge (bot challenge / validate.perfdrive.com /
the empty-202 challenge), login (redirect to an identity provider / login page), paywall_or_forbidden (HTTP 401/403),
publisher_landing_no_pdf (a publisher landing page without a PDF link), robots_disallow, robots_unavailable (the
robots.txt request itself answered 4xx), not_found (404/410), embargoed (signed store 403), unapproved_redirect,
landing_no_pdf, not_pdf, identity_mismatch, tls_error, policy_skip, too_large, transient (timeouts, connection errors,
DNS, 5xx, 429, source_paused), other.

Per work:
  requeue_untried    the work already has candidate URLs never tried: status -> queued, nothing deleted
  requeue_transient  some pair failed only transiently, at most twice (counting earlier requeues), on a host that is not
                     a challenge host and not one of retry_transient.SKIP_HOSTS: those pairs' attempts are deleted
                     (logged) and status -> queued; the loop asks again
  closed             every pair failed for a lasting reason: the status stays needs_access_review (tools/chain_audit.py
                     explains exactly that status as 'only paywalled or login copies found'; the collector has no closed
                     state) and the reason goes to the side table access_review(work_id, verdict, cause, causes, ...)
Writes: short transactions, busy_timeout 120 s, <= 200 rows each, WHERE status='needs_access_review' (a work the
collector moved meanwhile is left alone). Every change -> review-20261029/<school>.jsonl.
usage: review_access.py classify|apply <school>
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[1] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
OUT = HERE / 'review-20261029'
STORES = P.STORES
sys.path.insert(0, str(HERE))
from retry_transient import TRANSIENT, SKIP_HOSTS  # noqa: E402  (the push's own transient rule and publisher hosts)

PUBLISHERS = re.compile(r'(?:^|\.)(?:acm\.org|ieee\.org|ieeexplore\.ieee\.org|sciencedirect\.com|elsevier\.com|springer\.com|nature\.com|wiley\.com|'
                        r'tandfonline\.com|sagepub\.com|ssrn\.com|cambridge\.org|oup\.com|academic\.oup\.com|jstor\.org|science\.org|cell\.com|'
                        r'annualreviews\.org|informs\.org|aps\.org|iop\.org|iopscience\.iop\.org|siam\.org|pnas\.org|degruyter\.com|emerald\.com|'
                        r'worldscientific\.com|mitpressjournals\.org|direct\.mit\.edu|ams\.org|asme\.org|ascelibrary\.org|aip\.org|pubs\.acs\.org|'
                        r'rsc\.org|thieme-connect\.com|karger\.com|lww\.com|jamanetwork\.com|nejm\.org|bmj\.com|thelancet\.com|healthaffairs\.org|'
                        r'aeaweb\.org|journals\.uchicago\.edu|muse\.jhu\.edu|emerald\.com|igi-global\.com|inderscience\.com|liebertpub\.com|'
                        r'royalsocietypublishing\.org|optica\.org|osapublishing\.org|spiedigitallibrary\.org|researchgate\.net|semanticscholar\.org)$')
LOGIN_HOST = re.compile(r'(?:^|[.-])(?:idp|login|auth|sso|shibboleth|wayf|openathens|signin|accounts|myaccount|cas|ezproxy|secure)(?:[.-]|$)')
CHALLENGE = re.compile(r'perfdrive|captcha|cloudflare|challenge|Just a moment|HTTP 202 with an empty body|radware|incapsula|distil|px-captcha|'
                       r'validate\.|hcaptcha|recaptcha', re.I)
PRIORITY = ['challenge', 'login', 'paywall_or_forbidden', 'publisher_landing_no_pdf', 'robots_disallow', 'robots_unavailable', 'embargoed',
            'not_found', 'integrity_mismatch', 'unapproved_redirect', 'landing_no_pdf', 'not_pdf', 'identity_mismatch', 'tls_error', 'too_large', 'policy_skip',
            'transient_on_challenge_or_publisher_host', 'transient_exhausted', 'transient', 'other']


def now():
    return datetime.now(timezone.utc).isoformat()


def host(u):
    return (urlsplit(u or '').hostname or '').lower()


def cause(a):
    """(cause, transient?) of one attempts row."""
    d, st, h = a['detail'] or '', a['status'], host(a['url'])
    if st == 'excluded_nonarticle':
        return 'policy_skip', False
    if st == 'identity_mismatch' or re.search(r'title differs|DOI mismatch|arXiv identifier differs', d):
        return 'identity_mismatch', False
    if CHALLENGE.search(re.sub(r'https?://\S+', ' ', d)) or re.search(r'outside the evidence-approved public hosts: \S*(?:perfdrive|captcha)', d):
        return 'challenge', False
    m = re.match(r'Redirect or URL outside the evidence-approved public hosts: (\S+)', d)
    if m:
        return ('login' if LOGIN_HOST.search(m.group(1)) or re.search(r'login|signin|auth', m.group(1)) else 'unapproved_redirect'), False
    if re.search(r'login|sign in|paywall|subscription', d, re.I):
        return 'login', False
    if 'robots.txt disallows' in d:
        return 'robots_disallow', False
    if 'Signed file store refused' in d:
        return 'embargoed', False
    if re.search(r'Infoscience web page not fetched', d):
        return 'policy_skip', False
    if re.search(r'\b(?:40[0-9]|41[0-9]) Client Error.*robots\.txt', d):
        return 'robots_unavailable', False
    if re.search(r'\b(?:401|403) Client Error', d):
        return 'paywall_or_forbidden', False
    if re.search(r'\b(?:404|410) Client Error', d):
        return 'not_found', False
    if re.search(r'CERTIFICATE_VERIFY_FAILED|SSLCertVerificationError|TooManyRedirects|Exceeded \d+ redirects', d):
        return 'tls_error' if 'CERT' in d else 'other', False
    if re.search(r'MD5 mismatch|checksum mismatch', d):
        return 'integrity_mismatch', False
    if re.search(r'exceeds|too large', d, re.I):
        return 'too_large', False
    if TRANSIENT.search(d) or re.search(r'NameResolutionError|Failed to resolve|Errno -[23]', d):
        return 'transient', True
    if 'no unambiguous primary PDF link' in d or 'no unambiguous' in d:
        return ('publisher_landing_no_pdf' if PUBLISHERS.search(h) else 'landing_no_pdf'), False
    if re.search(r'neither a PDF|not a PDF|pdfinfo|PDF failed|not a complete JATS|XML', d):
        return 'not_pdf', False
    if re.search(r'\b4\d\d Client Error', d):
        return 'not_found' if '404' in d else 'other', False
    return 'other', False


def load(school):
    store = STORES / school
    db = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    db.row_factory = sqlite3.Row
    ids = [r[0] for r in db.execute("SELECT id FROM works WHERE status='needs_access_review'")]
    atts, cands = defaultdict(list), defaultdict(set)
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        q = ','.join('?' * len(part))
        for a in db.execute(f'SELECT * FROM attempts WHERE work_id IN ({q})', part):
            atts[a['work_id']].append(dict(a))
        for w, u in db.execute(f'SELECT work_id, url FROM candidates WHERE work_id IN ({q})', part):
            cands[w].add(u)
    # hosts that served a challenge anywhere in this catalog: never asked again
    chall = {host(u) for (u, st, d) in db.execute("SELECT url, status, detail FROM attempts WHERE detail LIKE '%perfdrive%' OR detail LIKE '%captcha%' OR "
                                                  "detail LIKE '%challenge%' OR detail LIKE '%HTTP 202 with an empty body%' OR detail LIKE '%cloudflare%'")
             if cause(dict(url=u, status=st, detail=d))[0] == 'challenge'}
    db.close()
    prior = Counter()
    want = set(ids)
    log = store / 'staged' / 'requeued-attempts.jsonl'
    if log.exists():
        with log.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('work_id') in want:
                    prior[(r['work_id'], r['url'])] += 1
    return store, ids, atts, cands, chall, prior


def classify(school):
    store, ids, atts, cands, chall, prior = load(school)
    plan = []
    for w in ids:
        pairs = defaultdict(list)
        for a in atts[w]:
            pairs[a['url']].append(a)
        untried = sorted(cands[w] - set(pairs))
        causes, retry = {}, []
        for u, aa in pairs.items():
            cs = [cause(a) for a in aa]
            h = host(u)
            finals = [c for c, t in cs if not t]
            if finals:
                causes[u] = min(finals, key=PRIORITY.index)
            elif h in chall or h in SKIP_HOSTS:
                causes[u] = 'transient_on_challenge_or_publisher_host'
            elif len(aa) + prior[(w, u)] <= 2:
                causes[u] = 'transient'; retry += [a['id'] for a in aa]
            else:
                causes[u] = 'transient_exhausted'
        cset = Counter(causes.values())
        if untried:
            v = 'requeue_untried'
        elif retry:
            v = 'requeue_transient'
        else:
            v = 'closed'
        primary = min(causes.values(), key=PRIORITY.index) if causes else 'no_attempts'
        plan.append(dict(id=w, verdict=v, cause=primary, causes=dict(cset), untried=len(untried), retry_attempt_ids=retry,
                         urls={u: c for u, c in list(causes.items())[:8]}, max_attempt_id=max([a['id'] for a in atts[w]] or [0])))
    OUT.mkdir(exist_ok=True)
    with open(OUT / f'access-plan-{school}.jsonl', 'w') as f:
        for p in plan:
            f.write(json.dumps(p) + '\n')
    url_causes = Counter(c for p in plan for c in p['urls'].values())
    print(json.dumps(dict(school=school, needs_access_review=len(ids), verdicts=Counter(p['verdict'] for p in plan),
                          closed_by_cause=Counter(p['cause'] for p in plan if p['verdict'] == 'closed'), url_causes=url_causes,
                          challenge_hosts=sorted(chall)[:20])), flush=True)


def apply(school):
    store = STORES / school
    plan = [json.loads(l) for l in open(OUT / f'access-plan-{school}.jsonl')]
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    db.row_factory = sqlite3.Row
    for attempt in range(30):
        try:
            db.execute('CREATE TABLE IF NOT EXISTS access_review (work_id TEXT PRIMARY KEY, verdict TEXT, cause TEXT, causes_json TEXT, '
                       'max_attempt_id INTEGER, reviewed_at TEXT, review TEXT)')
            db.commit(); break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(20)
    log = open(OUT / f'{school}.jsonl', 'a')
    rq = (store / 'staged' / 'requeued-attempts.jsonl').open('a')
    n = Counter()
    for i in range(0, len(plan), 200):
        part = plan[i:i + 200]
        for attempt in range(30):
            try:
                recs, removed = [], []
                for p in part:
                    w = p['id']
                    cur = db.execute('SELECT status FROM works WHERE id=?', (w,)).fetchone()
                    if not cur or cur['status'] != 'needs_access_review':
                        recs.append(dict(id=w, kind='access', skipped=f"status is now {cur['status'] if cur else None}")); continue
                    if p['verdict'] == 'closed':
                        db.execute('INSERT OR REPLACE INTO access_review VALUES (?,?,?,?,?,?,?)',
                                   (w, 'closed', p['cause'], json.dumps(p['causes']), p['max_attempt_id'], now(), 'fulltext-push/review_access.py 2026-10-29'))
                        recs.append(dict(id=w, kind='access', old=dict(status='needs_access_review'),
                                         new=dict(status='needs_access_review', access_review='closed'), reason=p['cause'], causes=p['causes']))
                        continue
                    if p['verdict'] == 'requeue_transient':
                        q = ','.join('?' * len(p['retry_attempt_ids']))
                        rows = [dict(r) for r in db.execute(f'SELECT * FROM attempts WHERE id IN ({q}) AND work_id=?', p['retry_attempt_ids'] + [w])]
                        for r in rows:  # logged before the delete, as collector_wrapper.requeue does
                            rq.write(json.dumps(dict(r, requeued_at=now(), requeued_by='fulltext-push/review_access.py')) + '\n')
                        rq.flush()
                        db.execute(f'DELETE FROM attempts WHERE id IN ({q}) AND work_id=?', p['retry_attempt_ids'] + [w])
                        removed += rows
                    c = db.execute("UPDATE works SET status='queued' WHERE id=? AND status='needs_access_review'", (w,)).rowcount
                    db.execute('INSERT OR REPLACE INTO access_review VALUES (?,?,?,?,?,?,?)',
                               (w, p['verdict'], p['cause'], json.dumps(p['causes']), p['max_attempt_id'], now(), 'fulltext-push/review_access.py 2026-10-29'))
                    recs.append(dict(id=w, kind='access', old=dict(status='needs_access_review'), new=dict(status='queued'), reason=p['verdict'],
                                     causes=p['causes'], attempts_removed=len(p['retry_attempt_ids']) if p['verdict'] == 'requeue_transient' else 0))
                db.commit(); break
            except sqlite3.OperationalError as e:
                db.rollback(); print(json.dumps(dict(retry=str(e))), flush=True); time.sleep(20)
        else:
            raise RuntimeError('catalog stayed locked')
        t = now()
        for r in recs:
            r['at'] = t
            n['skipped' if 'skipped' in r else (r['new'].get('access_review') or r['reason'])] += 1
            log.write(json.dumps(r) + '\n')
        rq.flush(); log.flush()
        time.sleep(0.3)
    db.close(); log.close(); rq.close()
    print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    {'classify': classify, 'apply': apply}[sys.argv[1]](sys.argv[2])
