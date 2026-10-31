# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools/collector_wrapper.py (sha256 73b55a6cf239c301ffe6467c42bc8d5c56b01a7de272b76d6c85b689b3793c92); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""The Princeton collector (homogenizing-science/scripts/collect_princeton_fulltext_expanded.py), unchanged on disk,
run for the CMU and EPFL catalogs with these additions:

- The repositories' signed-URL file stores are approved redirect targets: KiltHub / Figshare
  (ndownloader.figshare.com -> s3-eu-west-1.amazonaws.com/pstorage-cmu-348901238291901/...) and Infoscience
  (infoscience.epfl.ch/bitstreams/<uuid>/download -> cf002.cdn.4science.cloud/4s-assetstore-epfl-prod/...).
  Their robots.txt answers 403 because the stores refuse every request without a signed key, which the collector
  would read as "disallow all". The origin's robots.txt, checked on the first hop, governs (ndownloader.figshare.com
  has none; infoscience.epfl.ch allows /bitstreams). The stores get a rule set allowing only the repository's own
  storage path, and the collector's per-host pacing (3 s) still applies.
- The response size limit is 500 MiB instead of 100 MiB: 22 SCS dissertations exceed 100 MiB (the largest 473 MiB).
- Infoscience files come through its REST API, the machine interface robots.txt leaves open:
  /bitstreams/<uuid>/download (the web front end) is requested as /server/api/core/bitstreams/<uuid>/content, and
  web pages (/handle/, /record/, /items/, /entities/) are not fetched. The web front end answered with an empty
  HTTP 202 (its bot challenge) on and off on 2026-10-19 while the REST API served the earlier harvest for hours.
  infoscience.epfl.ch is asked at most once per 10 s, and an empty 202 pauses it for the rest of the pass (as the
  collector does for HTTP 429); nothing works around a challenge.
- bioRxiv and medRxiv are asked at most once per 15 s (2026-10-21): at the collector's 3 s bioRxiv answered HTTP 429 and
  was paused for every pass, leaving several hundred preprint candidates untried.
- web.archive.org is asked at most once per 6 s (2026-10-21: MIT's 566 Wayback copies at 3 s, beside the CDX lookups,
  got the host's connections refused by the Archive).
- A 403 from a signed file store is a per-file refusal (an embargoed or restricted KiltHub / Infoscience file): it does not
  count toward the three failures that pause a host for the pass (2026-10-21: four 403s paused the KiltHub store and 218
  Figshare files were skipped).
- Slow hosts never hold a pass: a host whose robots.txt crawl delay would make a worker wait more than MAX_WAIT
  (aaai.org asks for 43,200 s; on 2026-10-19 two AAAI papers kept a CMU pass open for over 12 hours) is asked at
  most once per crawl delay across passes (last request times in <out>/staged/slow-host-last.json); in between, its
  works fail at once as source_paused and the next pass's requeue asks again.
- Requeue at the start of each pass: attempts that failed only because a source was paused (source_paused), because
  Infoscience answered an empty 202, or because a redirect went to one of the stores above before they were
  approved, are removed for works still without a copy, so this pass asks again. Every removed row is kept in
  <out>/staged/requeued-attempts.jsonl.

Usage: the collector's own arguments (--out, --skip-candidate-import, --workers ...).
"""
import json, re, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

SCRIPTS = Path(__file__).resolve().parents[1] / 'homogenizing_scripts'
sys.path.insert(0, str(SCRIPTS))
import collect_princeton_fulltext_expanded as c
from protego import Protego

DELIVERY = {'s3-eu-west-1.amazonaws.com': '/pstorage-cmu-348901238291901/',
            'cf002.cdn.4science.cloud': '/4s-assetstore-epfl-prod/'}
# 2026-10-30: dspace.mit.edu (HTTP 429 at 3 s; Open Access Articles manuscripts of MIT's IEEE / ACM / Springer papers) at
# one request per 15 s, bioRxiv / medRxiv slowed from 15 s to 30 s (429 again at 15 s); a 429 still pauses the host for the
# pass and the pass-start requeue asks again next pass
MIN_DELAY = {'infoscience.epfl.ch': 10.0, 'www.biorxiv.org': 30.0, 'www.medrxiv.org': 30.0, 'web.archive.org': 6.0, 'dspace.mit.edu': 15.0}
MAX_WAIT = 300.0
IS_BITSTREAM = re.compile(r'^https?://infoscience\.epfl\.ch/bitstreams/([0-9a-f-]{36})/download')
IS_PAGE = re.compile(r'^https?://infoscience\.epfl\.ch/(?:handle|record|items|entities)/')
CHALLENGE = 'HTTP 202 with an empty body (the site\'s bot challenge); retry in a later pass'
c.PUBLIC_REDIRECT_HOSTS |= set(DELIVERY)
_init, _get, _pause = c.PublicClient.__init__, c.PublicClient.get, c.PublicClient.pause


def __init__(self, out, allowed):
    _init(self, out, allowed)
    for host, prefix in DELIVERY.items():
        self.rules[host] = Protego.parse(f'User-agent: *\nAllow: {prefix}\nDisallow: /\n')


def pause(self, key, delay):
    delay = max(delay, MIN_DELAY.get(key, 0))
    if delay <= MAX_WAIT:
        return _pause(self, key, delay)
    path = self.out / 'staged' / 'slow-host-last.json'
    with self.guard:
        last = json.loads(path.read_text()) if path.exists() else {}
        if time.time() - last.get(key, 0) < delay:
            self.blocked[key] = f'robots.txt asks for {delay:.0f} s between requests; asked again in a later pass'
            raise RuntimeError('source_paused: ' + self.blocked[key])
        last[key] = time.time()
        path.parent.mkdir(exist_ok=True)
        tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(last, indent=1)); tmp.replace(path)
    self.last[key] = time.monotonic()


def get(self, url, limit=500 * 1024 * 1024):
    m = IS_BITSTREAM.match(url)
    if m:
        url = f'https://infoscience.epfl.ch/server/api/core/bitstreams/{m.group(1)}/content'
    if IS_PAGE.match(url):
        raise ValueError('Infoscience web page not fetched: its files come through the REST API (/server/api)')
    try:
        data, final, ctype = _get_following(self, url, limit)
    except c.requests.HTTPError as e:
        store = urlsplit(e.response.url).hostname if e.response is not None else ''
        if store in DELIVERY and e.response.status_code == 403:
            # The signed store refuses one restricted or embargoed file, not every request: this must not count toward
            # the three failures that pause the store for the rest of the pass (it served other files in the same pass).
            with self.guard:
                self.failures[store] = max(0, self.failures[store] - 1)
                if self.blocked.get(store) == 'Repeated access or network failures' and self.failures[store] < 3:
                    del self.blocked[store]
            raise ValueError('Signed file store refused this file (HTTP 403): restricted or embargoed') from None
        raise
    host = urlsplit(final).hostname or ''
    if host in MIN_DELAY and not data:
        self.blocked[host] = CHALLENGE
        raise RuntimeError('source_paused: ' + CHALLENGE)
    if not data:
        # an empty 2xx answer is never a paper: figshare.com and arodes.hes-so.ch answer an empty HTTP 202 (a WAF bot
        # challenge, 2026-10-30). The host is paused for the pass and the attempt is recorded as a challenge, which the
        # pass-start requeue does not ask again (nothing works around a challenge).
        self.blocked[host] = CHALLENGE_FINAL
        raise ValueError(CHALLENGE_FINAL)
    if 'html' in (ctype or '').lower() and b'<' not in data[:512] and data.lstrip()[:1] == b'<':
        data = data.lstrip()  # www.osti.gov pages open with > 512 bytes of whitespace: the collector's HTML test reads the first 512
    _TIER.final = final  # the URL the file came from (the identity rule's arXiv check)
    return data, final, ctype


# Redirects (2026-10-30): the collector follows a redirect only to a host some candidate of the catalog already names.
# 680 lab papers stopped at 'Redirect or URL outside the evidence-approved public hosts'. Approved now, per redirect:
#   - the same site: the target's registrable domain equals the requested URL's (www.psyarxiv.com <- psyarxiv.com,
#     ijcai.org <- www.ijcai.org, publications.ri.cmu.edu <- www.ri.cmu.edu, backoffice.biblio.ugent.be <- biblio.ugent.be)
#   - the Handle System (hdl.handle.net) and the DOI resolver (doi.org) resolving to the record's registered home, when
#     that home is not a publisher host (review_access.PUBLISHERS) and not a login / identity provider (LOGIN_HOST)
#   - documented moves of one site: biorobotics.ri.cmu.edu -> biorobotics.org (the CMU Biorobotics Lab's site),
#     lirias.kuleuven.be -> kuleuven.limo.libis.be (KU Leuven's Lirias records served by its library system LIBIS)
# robots.txt (with the AI-crawler groups above), the per-host pacing and the title check apply on the new host as on any.
OUTSIDE = 'Redirect or URL outside the evidence-approved public hosts: '
MOVES = {'biorobotics.ri.cmu.edu': {'biorobotics.org', 'www.biorobotics.org'}, 'lirias.kuleuven.be': {'kuleuven.limo.libis.be'}}
RESOLVERS = {'hdl.handle.net', 'doi.org', 'dx.doi.org'}
LOGIN_HOST = re.compile(r'(?:^|[.-])(?:idp|login|auth|sso|shibboleth|wayf|openathens|signin|accounts|myaccount|cas|ezproxy|secure)(?:[.-]|$)')
PUBLISHER = re.compile(r'(?:^|\.)(?:acm\.org|ieee\.org|sciencedirect\.com|elsevier\.com|springer\.com|nature\.com|wiley\.com|tandfonline\.com|'
                       r'sagepub\.com|ssrn\.com|cambridge\.org|oup\.com|jstor\.org|science\.org|cell\.com|annualreviews\.org|informs\.org|aps\.org|'
                       r'iop\.org|siam\.org|pnas\.org|degruyter\.com|emerald\.com|worldscientific\.com|direct\.mit\.edu|ams\.org|asme\.org|'
                       r'ascelibrary\.org|aip\.org|acs\.org|rsc\.org|karger\.com|lww\.com|jamanetwork\.com|bmj\.com|thelancet\.com|optica\.org|'
                       r'osapublishing\.org|spiedigitallibrary\.org|researchgate\.net|semanticscholar\.org|scitation\.org|igi-global\.com|'
                       r'inderscience\.com|liebertpub\.com|royalsocietypublishing\.org|mdpi\.com|frontiersin\.org|amazonaws\.com|primo\.exlibrisgroup\.com)$')
CC2 = {'ac', 'co', 'edu', 'gov', 'org', 'com', 'net', 'or', 'ne', 'go'}


def site(h):
    p = (h or '').lower().split('.')
    return '.'.join(p[-3:]) if len(p) >= 3 and len(p[-1]) == 2 and p[-2] in CC2 else '.'.join(p[-2:])


def redirect_ok(origin, target):
    if not target or LOGIN_HOST.search(target) or re.search(r'login|signin|auth', target):
        return False
    if target in MOVES.get(origin, ()):
        return True
    if site(origin) == site(target) and not PUBLISHER.search(target):
        return True
    return origin in RESOLVERS and not PUBLISHER.search(target)


CHALLENGE_FINAL = 'HTTP 202 with an empty body (the site\'s bot challenge); the host is not asked again'


def _get_following(self, url, limit):
    origin = urlsplit(url).hostname or ''
    for _ in range(4):
        try:
            return _get(self, url, limit)
        except ValueError as e:
            m = str(e)
            target = m[len(OUTSIDE):].strip() if m.startswith(OUTSIDE) else None
            if not target or target in self.allowed or not redirect_ok(origin, target):
                raise
            with self.guard:
                self.allowed.add(target)
    return _get(self, url, limit)


c.PublicClient.__init__, c.PublicClient.get, c.PublicClient.pause = __init__, get, pause

# robots.txt groups naming Anthropic's crawlers bind this client too (2026-10-30, owner: never bypass a robots.txt rule,
# including rules naming ClaudeBot or anthropic-ai; hal.science, for one, disallows / for them while allowing '*'). Every
# rule set the collector parses answers can_fetch only when the client's own user agent AND each of these may fetch the URL;
# a refusal is the collector's usual 'robots.txt disallows URL' (access review: robots_disallow).
AI_AGENTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', 'Claude-User', 'Claude-SearchBot')


class _AIRules:
    def __init__(self, rules):
        self._rules = rules

    def can_fetch(self, url, user_agent):
        return self._rules.can_fetch(url, user_agent) and all(self._rules.can_fetch(url, a) for a in AI_AGENTS)

    def __getattr__(self, name):
        return getattr(self._rules, name)


class _ProtegoAI:
    @staticmethod
    def parse(content):
        return _AIRules(Protego.parse(content))


c.Protego = _ProtegoAI


# Landing pages (2026-10-30): the collector follows a landing page's one PDF link. Its parser took the citation_pdf_url
# meta tag, else DSpace '/bitstream/' links; 2,994 lab papers ended at 'no unambiguous primary PDF link'. Sampled pages
# (fulltext-push/review-20261029, 2026-10-30): most are repository records without a file (PubMed, eprints, Pure, CDS,
# Zenodo datasets) and stay so, but author and lab pages (vhil.stanford.edu 'View PDF', web.stanford.edu/~user/...html)
# and IRIS / DSpace-CRIS repositories (/retrieve/<uuid>/<file>.pdf) carry exactly one PDF the old parser skipped. Tiers:
#   citations  citation_pdf_url, bepress_citation_pdf_url, eprints.document_url (a .pdf) meta tags
#   pdfs       DSpace '/bitstream/' PDF links; else <link type="application/pdf">; else every <a> whose path ends in .pdf
#              (or is a /retrieve/ or /bitstreams/ file) and is not a supplement, slides or poster
# The collector still requires exactly one distinct link, and the title check on the downloaded file applies.
NOT_ARTICLE = re.compile(r'supp|slide|poster|present|handout|appendi|errat|abstract[-_.]|cover|flyer|cv[-_.]|resume|syllabus|\.ppt|privacy|'
                         r'datenschutz|protection|licen[cs]e|terms|conditions|policy|sponsor|brochure|cfp|call[-_]?for|program(?:me)?[-_.]|'
                         r'schedule|agenda|form[-_.]|guidelines|template|manual|newsletter|annual[-_]?report', re.I)
# A PDF reached through the new tiers (a <link type=application/pdf>, or the page's one PDF anchor) counts only when the
# collector's identity check finds the catalog title (or DOI) in it: on 2026-10-30, 21 of 27 such files whose title
# was not found were repository privacy statements, licence pages, a conference sponsorship flyer or another paper.
_TIER = __import__('threading').local()


class Links(c.base.HTMLParser):
    def __init__(self):
        super().__init__(); self.citations = []; self._bit = []; self._link = []; self._any = []
        _TIER.loose = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        name = (a.get('name') or '').lower()
        if tag == 'meta' and a.get('content') and (name in ('citation_pdf_url', 'bepress_citation_pdf_url') or
                                                   (name == 'eprints.document_url' and a['content'].lower().split('?')[0].endswith('.pdf'))):
            self.citations.append(a['content'])
        href = (a.get('href') or '').strip()
        if tag == 'link' and href and (a.get('type') or '').lower() == 'application/pdf':
            self._link.append(href)
        if tag == 'a' and href and not href.lower().startswith(('mailto:', 'javascript:', '#')):
            path = urlsplit(href).path.lower()
            if '.pdf' in href.lower() and '/bitstream/' in href:
                self._bit.append(href)
            elif (path.endswith('.pdf') or re.search(r'/retrieve/[0-9a-f-]{20,}/[^/]+\.pdf$|/bitstreams/[0-9a-f-]{36}/download$', path)) \
                    and not NOT_ARTICLE.search(path.rsplit('/', 1)[-1]):
                self._any.append(href)

    @property
    def pdfs(self):
        out = self._bit or self._link or self._any
        _TIER.loose = bool(out) and not self.citations and not self._bit
        return out


_check_identity, _process_work = c.base.check_identity, c.process_work


# Download-time identity rule (local edit 2026-10-31, owner): a file whose catalog title the collector's own check did
# not find (identity 'provider_link_only_review_pending') goes through the automatic rule of
# fulltext-push/identity_rule.py, the module identity_review.py uses for the copies already in the catalogs:
#   pass       counted, with the rule's identity tag (auto_title_author_page1 / auto_arxiv_id_doi_mapping)
#   fail       never counted: the attempt fails as 'identity unconfirmed: <reason>' (access review: identity_mismatch),
#              the work stays queued for its other candidates, and the file leaves objects/ for
#              quarantine/identity-rejected/ (manifest.jsonl; the newest REJECT_KEEP files are kept, older ones pruned;
#              a file another downloaded work also uses stays where it is)
#   undecided  (no text layer, or neither a first author nor a DOI known) keeps the pending state, as before
# A PDF reached through the new landing-page tiers is never kept without evidence (undecided is rejected there too).
CODE_ROOT = Path(__file__).resolve().parents[2]
if str(CODE_ROOT / 'fulltext-push') not in sys.path:
    sys.path.append(str(CODE_ROOT / 'fulltext-push'))
import identity_rule as IR  # noqa: E402
REJECT_KEEP = 500
_REJECT_LOCK = __import__('threading').Lock()


def _s2_cache():
    try:
        import s2_key_lookup as s2k
        return s2k.CACHE
    except Exception:
        return None


def _reject(row, path, ev, why):
    import os
    store = Path(path).parents[1]
    rel = str(Path(path).relative_to(store))
    qdir = store / 'quarantine' / 'identity-rejected'
    with _REJECT_LOCK:
        shared = False
        try:
            db = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
            shared = bool(db.execute("SELECT 1 FROM works WHERE file_path=? AND status IN ('downloaded','fulltext_xml') AND id<>? LIMIT 1",
                                     (rel, row['id'])).fetchone())
            db.close()
        except sqlite3.Error:
            shared = True  # unsure: leave the file where it is
        moved = None
        if not shared and Path(path).exists():
            moved = str(Path('quarantine') / 'identity-rejected' / Path(path).name)
            qdir.mkdir(parents=True, exist_ok=True)
            os.rename(path, store / moved)
        qdir.mkdir(parents=True, exist_ok=True)
        with open(qdir / 'manifest.jsonl', 'a') as m:
            m.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(), work_id=row['id'], title=row.get('title'), doi=row.get('doi'),
                                    object=rel, kept_as=moved, shared_file=shared, why=why, evidence=ev,
                                    final_url=getattr(_TIER, 'final', None))) + '\n')
        files = sorted((f for f in qdir.iterdir() if f.suffix == '.pdf'), key=lambda f: f.stat().st_mtime)
        for f in files[:max(0, len(files) - REJECT_KEEP)]:
            f.unlink()  # a rejected file is not a paper; the manifest keeps its record


def check_identity(row, path):
    loose, _TIER.loose = getattr(_TIER, 'loose', False), False
    identity = _check_identity(row, path)
    if identity != IR.PENDING:
        return identity
    store = Path(path).parents[1]
    first = IR.first_author(CODE_ROOT, store.name, row['id'], row.get('title'), row.get('doi'), catalog=store / 'catalog.sqlite')
    mapped = IR.mapped_arxiv(row.get('doi'), _s2_cache(), CODE_ROOT / 'fulltext-push' / 'raw' / 'ledger_openalex.jsonl')
    verdict, ev = IR.judge(IR.page_text(path, 1, 1), row.get('title'), first, row.get('doi'), getattr(_TIER, 'final', None), mapped)
    if verdict in IR.TAGS:
        return IR.TAGS[verdict]
    if verdict == 'fail' or loose:
        why = ('landing-page PDF link; ' if loose else '') + (IR.reason(ev) if verdict == 'fail' else ev.get('why', 'undecided'))
        _reject(row, path, ev, why)
        raise ValueError('identity unconfirmed: ' + why)
    return identity


def process_work(work, client, out):
    _TIER.loose = False
    _TIER.final = None
    return _process_work(work, client, out)


c.base.Links = Links
c.base.check_identity, c.process_work = check_identity, process_work


def requeue(out):
    db = sqlite3.connect(str(out / 'catalog.sqlite'), timeout=300)
    rows = db.execute("""SELECT a.* FROM attempts a JOIN works w ON w.id=a.work_id
                         WHERE w.status NOT IN ('downloaded','fulltext_xml') AND a.status='unavailable' AND (
                           a.detail LIKE 'source_paused:%'
                           OR (a.url LIKE '%infoscience.epfl.ch%' AND a.detail='Response is neither a PDF nor an HTML landing page')
                           OR a.detail IN ('Redirect or URL outside the evidence-approved public hosts: cf002.cdn.4science.cloud',
                                           'Redirect or URL outside the evidence-approved public hosts: s3-eu-west-1.amazonaws.com'))""").fetchall()
    if not rows:
        return
    cols = [d[0] for d in db.execute('SELECT * FROM attempts LIMIT 0').description]
    log = out / 'staged' / 'requeued-attempts.jsonl'
    log.parent.mkdir(exist_ok=True)
    with log.open('a') as f:
        for r in rows:
            f.write(json.dumps(dict(zip(cols, r), requeued_at=datetime.now(timezone.utc).isoformat())) + '\n')
    for attempt in range(20):
        try:
            db.executemany('DELETE FROM attempts WHERE id=?', [(r[0],) for r in rows]); db.commit(); break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(30)
    print(json.dumps(dict(requeued_attempts=len(rows))), flush=True)


if __name__ == '__main__':
    out = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else None
    if out:
        requeue(out)
    c.main()
