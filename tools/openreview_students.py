"""R-STU-27: a student's own public OpenReview profile as dated student-adviser evidence (owner decision 2026-11-13, docs/RULES.md).

Name-first search of api2.openreview.net (GET /profiles/search?term=<name>, one login, the official REST API) for each candidate of
tools/selfdeclared_candidates.py. A profile is admitted only when ALL hold: (1) its name matches the candidate; (2) a history entry at the school
(institution domain or name from the charter) with a student position (PhD / MS) whose dates overlap the PI's appointment window; (3) a relation
of type PhD Advisor or Advisor whose name matches the PI by token set (>= 2 tokens, hyphen/space folded: Jia-Wang = Jiawang) or whose username
does. Relations are one-directional: the student declares the adviser. Flags: co_advised (a second adviser is named; admitted only because the PI
is a named adviser), common_name_pi (the PI's name is a very common one), second_same_name_profile (another profile of the same name: HELD,
never admitted), role_unspecified (generic 'student' with no PhD/MS cue and a bare 'Advisor' relation: HELD).

Politeness (charter record docs/host-rulings.json, owner ruling 2026-11-13): profile search/read only; >= 6 s between requests across processes
(timestamp file under a lock); one session; a persistent response cache on local disk (chmod 600) so no request is ever repeated; the FIRST HTTP
429, any 401/403, a challenge/captcha/MFA/verification marker, or a login without a token stops the run and writes a stop-for-the-day marker (no retry,
no evasion, a challenge URL is never opened); a per-run request budget; --dry-run reads the cache only. Credentials come only from
~/.config/cs-atlas/openreview.env (OPENREVIEW_USERNAME, OPENREVIEW_PASSWORD) and are never printed, logged or stored. The account is currently the
owner's personal account; a dedicated project account is recommended.

  openreview_students.py run <school> [--budget N] [--max-minutes M] [--dry-run] [--cache DIR] [--all]
  openreview_students.py status
Output: <scratch>/openreview-students/proposals-<school>.json (reviewed-additions shape of LP-STU-01: school, rules, students, papers, held).
Cache and proposals hold private individuals' names (profiles may hold emails): local only, never committed.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import atlas_paths as P  # noqa: E402
import selfdeclared_candidates as C  # noqa: E402

RULE = 'R-STU-27'
BASE = 'https://api2.openreview.net'
MIN_GAP = 6.0
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory; robots.txt honoured)'
ENV = Path(os.path.expanduser('~/.config/cs-atlas/openreview.env'))
STATE = P.SCRATCH / 'openreview-students'
CAPTURE_YEAR = 2026
RULE_TEXT = ("A student's own public OpenReview profile is dated student-adviser evidence when it (1) matches the candidate's name, (2) has a "
             "history entry at the school with a PhD/MS student position overlapping the PI's appointment, and (3) declares a PhD Advisor/Advisor "
             "relation naming the PI (token-set name match, >= 2 tokens, or username). Co-advised rows are admitted only when the PI is a named "
             "adviser; a second same-name profile, or an unspecified role, holds the row.")
ADVISOR_TYPES = {'phd advisor', 'ph.d. advisor', 'advisor', 'doctoral advisor'}
COMMON = frozenset('wang li zhang liu chen yang huang zhao wu zhou xu sun ma zhu hu guo he lin gao luo zheng liang xie tang han cao deng feng song yu shen '
                   'jiang wei xiao lu tan lim lee ng chan wong cheung lau chow ho kim tay teo goh ong smith kumar singh'.split())
CHALLENGE = re.compile(r'captcha|challenge|cloudflare|verification|two-factor|mfa|otp|access denied|are you a robot', re.I)


class Stop(Exception):
    """Stop for the day: no retry, no evasion."""


# ---------------------------------------------------------------- names
def _fold(s):
    s = unicodedata.normalize('NFKD', str(s or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def ntoks(name):
    """Tokens of a name; a hyphenated token is kept joined (Jia-Wang -> jiawang)."""
    return re.sub(r"[^a-z一-鿿 ]", '', _fold(name).replace('-', '').replace('_', ' ').replace('.', ' ').replace("'", '')).split()


def name_match(a, b):
    """Token-set match, both names with >= 2 tokens: equal sets, or the shorter a subset of the longer (middle names), or the concatenated tokens
    equal (Jia Wang = Jiawang). A single token never matches."""
    A, B = ntoks(a), ntoks(b)
    if not A or not B:
        return False
    if len(A) >= 2 and len(B) >= 2:
        sa, sb = set(A), set(B)
        sm, lg = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
        if sm <= lg:
            return True
    ja, jb = sorted(''.join(A)), sorted(''.join(B))
    return max(len(A), len(B)) >= 2 and len(ja) >= 5 and ja == jb


def username_name(user):
    return re.sub(r'\d+$', '', str(user or '').lstrip('~')).replace('_', ' ')


# ---------------------------------------------------------------- school spec
def school_spec(school):
    import school_config as S
    cfg = S.get(school)
    names = [cfg.get('name', '').lower().removeprefix('the ').strip()]
    ov = cfg.get('openreview') or {}
    names += [n.lower() for n in ov.get('names') or []]
    excl = re.compile(cfg['affiliation']['excluded_regex'], re.I) if (cfg.get('affiliation') or {}).get('excluded_regex') else None
    doms = [d.lower() for d in (ov.get('domains') or (cfg.get('web') or {}).get('domains') or [])]
    return dict(domains=doms, names=[n for n in names if n], excluded=excl)


def inst_ok(h, spec):
    i = h.get('institution') or {}
    d = (i.get('domain') or '').lower()
    n = (i.get('name') or '').lower()
    if spec.get('excluded') and spec['excluded'].search(n):
        return False
    return any(d == x or d.endswith('.' + x) for x in spec['domains']) or any(x and x in n for x in spec['names'])


def position_role(pos):
    p = (pos or '').lower()
    if re.search(r'professor|postdoc|post-doc|faculty|lecturer|research fellow|scientist|engineer|intern|undergrad|bachelor|visiting', p) and 'student' not in p:
        return None
    if re.search(r'ph\.?\s?d|doctoral|doctorate|dphil|candidate', p):
        return 'phd'
    if re.search(r'master|\bm\.?s\.?c?\b|mphil|m\.?eng', p):
        return 'masters'
    if re.search(r'student|research assistant', p):
        return 'student'
    return None


def _ov(h, win):
    s = h.get('start') or 0
    e = h.get('end') or CAPTURE_YEAR
    return s <= win[1] and e >= win[0]


# ---------------------------------------------------------------- validation
def validate(profiles, school_spec_, pinames, window, qname):
    """Judge a search result for one (candidate, PI). Returns dict(status admitted|held|none, profile, row fields, flags, reasons)."""
    matches = [p for p in profiles if any(name_match(qname, n) for n in prof_names(p))]
    good, why = [], []
    for p in matches:
        c = p.get('content') or {}
        hs = [h for h in c.get('history') or [] if inst_ok(h, school_spec_)]
        st = [(h, position_role(h.get('position'))) for h in hs]
        st = [(h, r) for h, r in st if r and _ov(h, window)]
        rels = [r for r in c.get('relations') or [] if str(r.get('relation') or '').lower() in ADVISOR_TYPES]
        named = [r for r in rels if any(name_match(x, pn) for x in (r.get('name'), username_name(r.get('username'))) if len(ntoks(x)) >= 2 for pn in pinames)]
        if not hs:
            why.append('no_school_history')
        elif not st:
            why.append('no_student_position_overlapping_window')
        elif not named:
            why.append('no_advisor_relation_naming_pi')
        if st and named:
            good.append((p, st, rels, named))
    if not good:
        return dict(status='none', reasons=sorted(set(why)) or ['no_name_match'], flags=[])
    if len(good) > 1:
        return dict(status='held', reasons=['two_validating_profiles'], flags=['second_same_name_profile'], profile=good[0][0].get('id'))
    p, st, rels, named = good[0]
    flags = []
    if len({(r.get('username') or r.get('name')) for r in rels}) > 1:
        flags.append('co_advised')
    if len(pinames[0].split()) <= 2 and any(t in COMMON for t in ntoks(pinames[0])):
        flags.append('common_name_pi')
    others = [q for q in matches if q is not p and not _other_elsewhere(q, school_spec_)]
    if others:
        flags.append('second_same_name_profile')
    h, role = max(st, key=lambda x: (x[0].get('start') or 0))
    rel = named[0]
    if role == 'student':
        if str(rel.get('relation')).lower() in ('phd advisor', 'ph.d. advisor', 'doctoral advisor'):
            role = 'phd'
        else:
            flags.append('role_unspecified')
    status = 'held' if ('second_same_name_profile' in flags or 'role_unspecified' in flags) else 'admitted'
    return dict(status=status, flags=flags, profile=p, history=h, role=role, relation=rel, reasons=[])


def _other_elsewhere(q, spec):
    """True when another same-name profile has history and none of it is at this school (clearly somebody else)."""
    hs = (q.get('content') or {}).get('history') or []
    return bool(hs) and not any(inst_ok(h, spec) for h in hs)


def prof_names(p):
    return [n.get('fullname') or ' '.join(filter(None, [n.get('first'), n.get('middle'), n.get('last')])) for n in (p.get('content') or {}).get('names') or []]


def build_row(res, cand, term_sha, captured):
    p, h, rel = res['profile'], res['history'], res['relation']
    pid = p.get('id')
    inst = h.get('institution') or {}
    nm = next((n for n in prof_names(p) if name_match(cand['name'], n)), cand['name'])
    start, end = h.get('start'), h.get('end')
    y0 = start or cand['window'][0]
    years = [y0, end or CAPTURE_YEAR]
    rs, re_ = rel.get('start'), rel.get('end')
    quote = (f"OpenReview profile {pid}: history: {h.get('position')}, {inst.get('name')} ({inst.get('domain')}), {start or '?'}-{end or 'present'}; "
             f"relation: {rel.get('relation')}: {rel.get('name') or username_name(rel.get('username'))}"
             + (f" ({rs or '?'}-{re_ or 'present'})" if rs or re_ else ''))
    return dict(pi=cand['pi'], name=nm, role=res['role'], years=years, years_basis='openreview_history_dates' + ('' if end else '_open_end'),
                url=f'https://openreview.net/profile?id={pid}', capture_url=f'https://openreview.net/profile?id={pid}',
                sha256=term_sha, captured=captured, quote=quote, alumni=bool(end), rule=RULE, auto=True, source='self_declared_openreview',
                evidence_kind='self_declared_openreview', profile_id=pid, flags=res['flags'],
                note='The student\'s own OpenReview profile declares this adviser (one-directional relation); quote built from the history and relation fields. R-STU-27')


# ---------------------------------------------------------------- client
def load_env(path=ENV):
    env = {}
    for line in Path(path).read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.strip().split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def term_file(cache, term):
    return Path(cache) / (hashlib.sha1(term.encode()).hexdigest()[:16] + '.json')


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')


def guard_url(url, params=None):
    """Never send a URL containing 'email=' (api2.openreview.net/robots.txt, checked 2026-11-13: `User-agent: *` / `Disallow: /*?*email=`)."""
    q = '&'.join(f'{k}={v}' for k, v in sorted((params or {}).items()))
    if 'email=' in (str(url) + '?' + q).lower() or 'email%3d' in (str(url) + '?' + q).lower():
        raise ValueError('refused: a request URL containing email= is never sent (robots.txt)')


class Client:
    def __init__(self, cache, state=STATE, budget=100, session=None, dry=False, env_path=ENV, clock=time.time, sleep=time.sleep):
        self.cache, self.state, self.budget, self.dry = Path(cache), Path(state), budget, dry
        self.n, self.logged_in, self.clock, self.sleep, self.env_path = 0, False, clock, sleep, env_path
        self.cache.mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        self.session = session
        if not dry and (self.state / f'STOPPED-{today()}').exists():
            raise Stop('stopped for the day: ' + (self.state / f'STOPPED-{today()}').read_text().strip())

    def _stop(self, why):
        (self.state / f'STOPPED-{today()}').write_text(why + '\n')
        raise Stop(why)

    def _gap(self):
        """>= MIN_GAP between requests of any process: a locked timestamp file."""
        with open(self.state / 'last-request', 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                last = float(f.read() or 0)
            except ValueError:
                last = 0.0
            d = MIN_GAP - (self.clock() - last)
            if d > 0:
                self.sleep(d)
            f.seek(0)
            f.truncate()
            f.write(str(self.clock()))

    def _sess(self):
        if self.session is None:
            import requests
            self.session = requests.Session()
            self.session.headers['User-Agent'] = UA
        return self.session

    def _check(self, r, what):
        code = r.status_code
        if code == 429:
            self._stop(f'HTTP 429 on {what}')
        if code in (401, 403):
            self._stop(f'HTTP {code} on {what}')
        if code != 200:
            self._stop(f'HTTP {code} on {what}')
        if CHALLENGE.search((r.text or '')[:600]):
            self._stop(f'challenge marker on {what}')

    def login(self):
        if self.logged_in or self.dry:
            return
        env = load_env(self.env_path)
        guard_url(BASE + '/login')
        self._gap()
        self.n += 1
        r = self._sess().post(BASE + '/login', json={'id': env['OPENREVIEW_USERNAME'], 'password': env['OPENREVIEW_PASSWORD']}, timeout=30)
        self._check(r, 'login')
        j = r.json()
        if 'token' not in j or any(k in j for k in ('mfa', 'otp', 'verification')):
            self._stop('login returned no token or asked for a second factor')
        self.session.headers['Authorization'] = 'Bearer ' + j['token']
        self.logged_in = True

    def search(self, term):
        """The parsed search response, from the cache when present (never repeated). None in dry-run when uncached."""
        f = term_file(self.cache, term)
        if f.exists():
            return json.loads(f.read_text())
        if self.dry:
            return None
        if self.n >= self.budget:
            raise Stop('request budget reached')
        self.login()
        if self.n >= self.budget:
            raise Stop('request budget reached')
        params = {'term': term, 'es': 'true'}
        guard_url(BASE + '/profiles/search', params)
        self._gap()
        self.n += 1
        r = self._sess().get(BASE + '/profiles/search', params=params, timeout=60)
        self._check(r, 'search')
        j = r.json()
        j['_term'] = term
        f.write_text(json.dumps(j))
        os.chmod(f, 0o600)
        return j


# ---------------------------------------------------------------- run
def run(school, cache, budget=100, dry=False, max_minutes=55, include_all=False, cands=None, client=None):
    spec = school_spec(school)
    cands = cands if cands is not None else C.generate(school, include_all)
    cl = client or Client(cache, budget=budget, dry=dry)
    t0 = time.time()
    rows, held, none, uncached, stop = [], [], 0, 0, None
    seen = set()
    try:
        for c in cands:
            if time.time() - t0 > max_minutes * 60:
                stop = 'time limit'
                break
            j = cl.search(c['name'])
            if j is None:
                uncached += 1
                continue
            res = validate(j.get('profiles') or [], spec, c['pinames'], tuple(c['window']), c['name'])
            if res['status'] == 'none':
                none += 1
                continue
            f = term_file(cl.cache, c['name'])
            if res['status'] == 'held' and 'profile' in res and not isinstance(res['profile'], dict):
                held.append(dict(pi=c['pi'], name=c['name'], flags=res['flags'], reasons=res['reasons'], profile_id=res['profile']))
                continue
            captured = datetime.datetime.fromtimestamp(f.stat().st_mtime, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
            row = build_row(res, c, hashlib.sha256(f.read_bytes()).hexdigest(), captured)
            dk = (row['pi'], row['profile_id'])
            if dk in seen:
                continue
            seen.add(dk)
            (rows if res['status'] == 'admitted' else held).append(row)
    except Stop as e:
        stop = str(e)
    out = dict(school=school, generated_at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'), rules={RULE: RULE_TEXT},
               students=sorted(rows, key=lambda r: (r['pi'], r['name'])), papers=[], held=held,
               summary=dict(candidates=len(cands), admitted=len(rows), held=len(held), no_validation=none, uncached=uncached, requests=cl.n, stopped=stop))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('school')
    r.add_argument('--budget', type=int, default=100, help='max requests this run (login counts)')
    r.add_argument('--max-minutes', type=float, default=55)
    r.add_argument('--dry-run', action='store_true', help='cache only, no request')
    r.add_argument('--cache', default=str(STATE / 'cache'))
    r.add_argument('--all', action='store_true')
    r.add_argument('--out')
    sub.add_parser('status')
    a = ap.parse_args(argv)
    if a.cmd == 'status':
        print('stopped today:', (STATE / f'STOPPED-{today()}').exists(), '| cached responses:', len(list((STATE / 'cache').glob('*.json'))) if (STATE / 'cache').exists() else 0)
        return 0
    out = run(a.school, a.cache, a.budget, a.dry_run, a.max_minutes, a.all)
    path = Path(a.out) if a.out else STATE / f'proposals-{a.school}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    os.chmod(path, 0o600)
    print(a.school, json.dumps(out['summary']), '->', path)
    return 3 if out['summary']['stopped'] and 'time limit' not in out['summary']['stopped'] and 'budget' not in out['summary']['stopped'] else 0


if __name__ == '__main__':
    sys.exit(main())
