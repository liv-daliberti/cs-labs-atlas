"""The polite landing-page check for the reader's candidate links (owner rule 2026-11-01: a link turns readable only when confirmed to be the
paper). Input: hierarchy/derived/reader/link-check-requests.tsv (tools/reader_export.py; one row per paper and candidate URL, with the
paper's title, DOI and first-author family name). Output: hierarchy/reviewed/reader/link-verdicts.jsonl (P.data('reader-link-verdicts.jsonl')),
one object per checked URL, which tools/reader_links.py reads as basis `landing_page_metadata`:
  key, url, verdict (match | mismatch | unreachable), title_seen, authors_seen, fetched_at, robots_ok, plus reason / status / how.

Manners, all of them:
  - robots.txt of every host (and of every redirect target) is read first, and a rule set binds this client only when our own agent AND
    ClaudeBot, anthropic-ai, Claude-Web, Claude-User and Claude-SearchBot may all fetch the URL (the collectors' rule). A refusal is a verdict
    `unreachable` with robots_ok false, never an attempt;
  - one request at a time per host, at least GAP seconds apart (the larger of that and the robots crawl delay); hosts run in parallel;
  - no logins, paywalls or challenges: HTTP 401/402/403/429, a challenge page (Cloudflare and the like) or an empty 202 is `unreachable` and
    not retried; three hard failures in a row pause the host for the run (its remaining rows get reason host_paused);
  - hosts that refuse automated clients (fulltext-push/retry_transient.SKIP_HOSTS) and the never-used hosts (Deep Blue, news.umich.edu,
    record.umich.edu, DBLP) are not asked at all;
  - an HTML page is read for its own metadata (citation_title / dc.title / og:title / <title> and citation_author / dc.creator); an open PDF
    (url_kind `file`, a non-publisher host, at most 25 MB) is read in memory for page 1 and judged by identity_rule.judge; nothing is stored.
Verdict: `match` = the seen title carries at least 80% of the paper's significant words (at least 3 of them; a shorter title must be equal) and
the first author's family name is among the authors seen (when the page lists authors); `mismatch` = a title seen that shares under half of the
paper's words; anything else is `unreachable` with the reason. Rows already in the file are kept (resume).
usage: link_check.py [--limit N] [--hosts a,b] [--workers 12] [--gap 5]
"""
import argparse, json, re, sys, tempfile, threading, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[1] / 'fulltext-push'))
import atlas_paths as P  # noqa: E402
import identity_rule as R  # noqa: E402

UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
AI_AGENTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', 'Claude-User', 'Claude-SearchBot')
NEVER = {'deepblue.lib.umich.edu', 'news.umich.edu', 'record.umich.edu', 'dblp.org', 'www.dblp.org', 'dblp.uni-trier.de'}
CHALLENGE = re.compile(r'(cf-chl-|challenge-platform|<title>Just a moment|Attention Required! \| Cloudflare|verify you are a human|hcaptcha|'
                       r'Checking your browser|px-captcha|perfdrive|Access Denied</title>|not a bot|Verifying your browser|Are you a robot|Pardon our interruption)', re.I)
BIBLIO = ('citation_title', 'dc.title', 'dcterms.title', 'eprints.title')  # tags that carry the paper's own title (not a site or section title)
MAX_HTML, MAX_PDF = 2_000_000, 25_000_000


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.m, self.title, self._in_title = defaultdict(list), '', False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta' and a.get('content'):
            n = (a.get('name') or a.get('property') or '').lower()
            if n:
                self.m[n].append(a['content'].strip())
        elif tag == 'title':
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, d):
        if self._in_title and len(self.title) < 500:
            self.title += d


def page_meta(html):
    p = Meta()
    try:
        p.feed(html)
    except Exception:
        pass
    m = p.m
    biblio = next((m[k][0] for k in BIBLIO if m.get(k)), '')
    title = biblio or next((m[k][0] for k in ('og:title', 'twitter:title') if m.get(k)), '') or ' '.join(p.title.split())
    authors = [a for k in ('citation_author', 'dc.creator', 'dcterms.creator', 'eprints.creators_name', 'author') for a in m.get(k, [])]
    return ' '.join(title.split()), authors[:30], bool(biblio)


def judge_page(title_seen, authors_seen, title, first, bibliographic=True):
    """(verdict, why). The title rule is identity_rule's: significant words, letters only."""
    tw = [x for x in R.norm_words(title) if len(x) >= 3 and x not in R.STOP]
    sw = set(R.norm_words(title_seen))
    if not title_seen or not tw:
        return 'unreachable', 'no_title_seen'
    frac = sum(x in sw for x in tw) / len(tw)
    back = [x for x in R.norm_words(title_seen) if len(x) >= 3 and x not in R.STOP]
    back_frac = (sum(x in set(tw) for x in back) / len(back)) if back else 0
    letters = re.sub(r'[^a-z]', '', ' '.join(authors_seen).lower().encode('ascii', 'ignore').decode()) if authors_seen else ''
    first = first or ''
    author_ok = (not authors_seen) or (first and R.fam(first) and R.fam(first) in letters) or (first and first in letters)
    title_ok = (len(tw) >= 3 and frac >= 0.8 and back_frac >= 0.5) or (len(tw) < 3 and R.norm_words(title) == R.norm_words(title_seen))
    if title_ok and author_ok:
        return 'match', 'title_and_author' if authors_seen else 'title_only'
    if frac < 0.5:
        if not bibliographic:  # a site, section or person page title says nothing about this paper
            return 'unreachable', 'page_title_not_bibliographic'
        return 'mismatch', f'title words {frac:.2f}'
    return 'unreachable', 'title_partly_matched' if title_ok is False else 'first_author_not_among_authors_seen'


class Host:
    """robots.txt (with the AI rules), pacing and the failure count of one host."""

    def __init__(self, name, gap):
        self.name, self.gap, self.rules, self.last, self.fails, self.paused = name, gap, None, 0.0, 0, False

    def wait(self):
        d = max(self.gap, self.delay or 0)
        t = self.last + d - time.monotonic()
        if t > 0:
            time.sleep(t)
        self.last = time.monotonic()

    delay = None


class Checker:
    def __init__(self, gap, session=None):
        import requests
        self.gap, self.hosts, self.lock = gap, {}, threading.Lock()
        self.s = session or requests.Session()
        self.s.headers['User-Agent'] = UA

    def host(self, name):
        with self.lock:
            return self.hosts.setdefault(name, Host(name, self.gap))

    def allowed(self, h, url):  # the robots.txt of the URL's own scheme and host
        """True / False, or None when robots.txt could not be read (a 5xx or a network error: not asked this run)."""
        from protego import Protego
        if h.rules is None:
            h.wait()
            try:
                u = urlsplit(url)
                r = self.s.get(f'{u.scheme}://{u.netloc}/robots.txt', timeout=(10, 25))
                if r.status_code in (401, 403):
                    txt = 'User-agent: *\nDisallow: /\n'
                elif r.status_code == 404 or r.status_code == 410:
                    txt = ''
                elif r.ok:
                    txt = r.text
                else:
                    return None
            except Exception:
                return None
            h.rules = Protego.parse(txt)
            h.delay = float(h.rules.crawl_delay(UA) or 0)
        return bool(h.rules.can_fetch(url, UA) and all(h.rules.can_fetch(url, a) for a in AI_AGENTS))

    def fetch(self, url, kind):
        """(status, content_type, body bytes or None, final_url, reason). Redirects are followed by hand, with robots on each host."""
        for _ in range(5):
            host = (urlsplit(url).hostname or '').lower()
            if host in NEVER:
                return None, '', None, url, 'never_used_host'
            h = self.host(host)
            if h.paused:
                return None, '', None, url, 'host_paused'
            ok = self.allowed(h, url)
            if ok is None:
                return None, '', None, url, 'robots_unreadable'
            if not ok:
                return None, '', None, url, 'robots_disallow'
            h.wait()
            try:
                r = self.s.get(url, timeout=(12, 40), allow_redirects=False, stream=True)
            except Exception as e:
                h.fails += 1
                h.paused = h.fails >= 3
                return None, '', None, url, 'network:' + type(e).__name__
            if r.is_redirect:
                url = urljoin(url, r.headers.get('Location', ''))
                r.close()
                continue
            ct = (r.headers.get('Content-Type') or '').lower()
            if r.status_code in (401, 402, 403, 429) or r.status_code >= 500:
                h.fails += 1
                h.paused = h.fails >= 3
                r.close()
                return r.status_code, ct, None, url, f'http_{r.status_code}'
            if r.status_code != 200:
                r.close()
                return r.status_code, ct, None, url, f'http_{r.status_code}'
            limit = MAX_PDF if 'pdf' in ct else MAX_HTML
            body, size = [], 0
            for chunk in r.iter_content(1 << 17):
                size += len(chunk)
                body.append(chunk)
                if size > limit:
                    break
            r.close()
            data = b''.join(body)
            if not data:
                h.fails += 1
                h.paused = h.fails >= 3
                return 200, ct, None, url, 'empty_body_challenge'
            h.fails = 0
            return 200, ct, data, url, ''
        return None, '', None, url, 'too_many_redirects'

    def check(self, row):
        base = dict(key=row['key'], url=row['url'], fetched_at=now())
        st, ct, data, final, why = self.fetch(row['url'], row['url_kind'])
        base.update(status=st, final_url=final if final != row['url'] else None)
        if data is None:
            return dict(base, verdict='unreachable', title_seen=None, authors_seen=[], robots_ok=why != 'robots_disallow' if why else True, reason=why)
        base['robots_ok'] = True
        if 'pdf' in ct or data[:5] == b'%PDF-':
            with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
                f.write(data)
                f.flush()
                p1, p12 = R.page_text(f.name, 1, 1), R.page_text(f.name, 1, 2)
                meta = R.pdf_meta_title(f.name)
            first = row['first_author_family']
            v, ev = R.judge(p1, row['title'], first, row['doi'], final, None, p12=p12, author_authoritative=bool(first))
            seen = ' '.join(p1.split())[:200]
            if v == 'pass_title':
                return dict(base, verdict='match', title_seen=meta or seen, authors_seen=[first], how='pdf_page1', reason='title_and_author_on_page1')
            ascii_share = sum(ch.isascii() and ch.isalpha() for ch in p1) / max(1, len(p1.replace(' ', '').replace('\n', '')))
            if v == 'undecided' and meta and ascii_share < 0.5:  # a font without a Unicode map: the text cannot be read, the metadata title can
                mw = [x for x in R.norm_words(meta) if len(x) >= 3 and x not in R.STOP]
                tw = [x for x in R.norm_words(row['title']) if len(x) >= 3 and x not in R.STOP]
                if len(tw) >= 4 and len(mw) >= 4 and sum(x in set(mw) for x in tw) / len(tw) >= 0.9 and sum(x in set(tw) for x in mw) / len(mw) >= 0.8:
                    return dict(base, verdict='match', title_seen=meta, authors_seen=[], how='pdf_metadata_title', reason='page text unreadable; the PDF title metadata is the paper title')
            if v == 'fail':
                return dict(base, verdict='mismatch', title_seen=meta or seen, authors_seen=[], how='pdf_page1', reason=R.reason(ev))
            return dict(base, verdict='unreachable', title_seen=meta or seen, authors_seen=[], how='pdf_page1', reason='not_confirmed')
        text = data.decode('utf-8', 'replace')
        if CHALLENGE.search(text[:20000]):
            self.host((urlsplit(final).hostname or '').lower()).fails += 1
            return dict(base, verdict='unreachable', title_seen=None, authors_seen=[], reason='bot_challenge')
        title_seen, authors_seen, biblio = page_meta(text)
        v, why = judge_page(title_seen, authors_seen, row['title'], row['first_author_family'], biblio)
        return dict(base, verdict=v, title_seen=title_seen or None, authors_seen=authors_seen, how='html_meta', reason=why)


def load_requests(path):
    rows = []
    with open(path) as f:
        head = f.readline().rstrip('\n').split('\t')
        for line in f:
            rows.append(dict(zip(head, line.rstrip('\n').split('\t'))))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--limit', type=int); ap.add_argument('--hosts'); ap.add_argument('--workers', type=int, default=12); ap.add_argument('--gap', type=float, default=5.0)
    ap.add_argument('--requests', default=str(P.HIERARCHY / 'derived' / 'reader' / 'link-check-requests.tsv'))
    a = ap.parse_args(argv)
    out = Path(P.data('reader-link-verdicts.jsonl'))
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in open(out):
            try:
                r = json.loads(line)
                done.add((r['key'], r['url']))
            except (ValueError, KeyError):
                pass
    rows = [r for r in load_requests(a.requests) if (r['key'], r['url']) not in done and (not a.hosts or r['host'] in a.hosts.split(','))]
    try:
        from retry_transient import SKIP_HOSTS
        skip = set(SKIP_HOSTS)
    except Exception:
        skip = set()
    if a.limit:
        rows = rows[:a.limit]
    byhost = defaultdict(list)
    for r in rows:
        byhost[r['host']].append(r)
    chk = Checker(a.gap)
    wlock = threading.Lock()
    counts = defaultdict(int)

    def work(host):
        for r in byhost[host]:
            if host in skip or host in NEVER:
                res = dict(key=r['key'], url=r['url'], verdict='unreachable', title_seen=None, authors_seen=[], fetched_at=now(), robots_ok=True,
                           reason='host_not_asked')
            else:
                try:
                    res = chk.check(r)
                except Exception as e:
                    res = dict(key=r['key'], url=r['url'], verdict='unreachable', title_seen=None, authors_seen=[], fetched_at=now(), robots_ok=True,
                               reason='error:' + type(e).__name__)
            with wlock:
                with open(out, 'a') as f:
                    f.write(json.dumps(res, ensure_ascii=False) + '\n')
                counts[res['verdict']] += 1
                counts['reason:' + str(res.get('reason'))[:40]] += 1
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(work, sorted(byhost, key=lambda h: -len(byhost[h]))))
    print(json.dumps(dict(checked=sum(len(v) for v in byhost.values()), hosts=len(byhost), seconds=int(time.time() - t0),
                          **{k: v for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:25]})), flush=True)


if __name__ == '__main__':
    main()
