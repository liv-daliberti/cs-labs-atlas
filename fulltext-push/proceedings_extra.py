"""proceedings_extra (2026-11-25, every-school-to-60% push): a supplement to the open proceedings title index.

The proceedings channel (lab_channels.step_proceedings) and the ledger's proceedings source match a lab paper's
normalized title against the Princeton sweep's frozen index (claude-princeton-20261015/.../proceedings/index.json.gz).
That index has no CVF workshop papers, no ACCV, no CVPR 2026 Findings and no MICCAI. All of these are free PDFs on the
organisers' own hosts, while the DOI copy (IEEE or Springer LNCS) is closed. This script lists them into
raw/proceedings_extra.json.gz in the same row format, [title, year, pdf_url, landing_url, venue]. ftp_common.proceedings_index()
reads both files.

Hosts and rules (checked 2026-11-25):
- openaccess.thecvf.com: robots.txt 404, no bot challenge.
- papers.miccai.org: robots.txt 404. MICCAI 2024 and 2025 list PDFs; 2021-2023 index pages are 404 at the same path.
- No AI-agent opt-out on either host.
Requests: F.UA, one at a time, DELAY seconds apart. Index pages only; no PDF is fetched here.

usage: proceedings_extra.py [--out FILE] [--delay S] [--only cvf|miccai]
"""
import argparse, gzip, html, json, re, sys, time
from urllib.parse import urljoin
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402
import requests  # noqa: E402

CVF = 'https://openaccess.thecvf.com'
# main-conference listings the frozen index lacks, and workshop menus (each lists workshop pages)
CVF_MAIN = ['ACCV2020', 'ACCV2022', 'ACCV2024', 'CVPR2026_findings']
CVF_MENUS = ([f'CVPR{y}_workshops/menu.py' for y in range(2016, 2021)] + [f'CVPR{y}_workshops/menu' for y in range(2021, 2026)]
             + ['CVPR2026_workshops'] + ['ICCV2017_workshops/menu.py', 'ICCV2019_workshops/menu.py']
             + [f'ICCV{y}_workshops/menu' for y in (2021, 2023, 2025)] + ['WACV2020_workshops/menu.py']
             + [f'WACV{y}_workshops/menu' for y in range(2021, 2027)] + ['ACCV2022_workshops/menu', 'ACCV2024_workshops/menu'])
MICCAI = {2024: 'https://papers.miccai.org/miccai-2024/', 2025: 'https://papers.miccai.org/miccai-2025/'}

TITLE_PDF = re.compile(r'<dt class="ptitle">.*?<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<dt class="ptitle">|\Z)', re.S)
PDF = re.compile(r'href="([^"]+?\.pdf)"')


def clean(t):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', t or ''))).strip()


class Fetch:
    def __init__(self, delay):
        self.s = requests.Session(); self.s.headers['User-Agent'] = F.UA; self.delay = delay; self.last = 0.0; self.n = 0; self.bad = []

    def get(self, url):
        time.sleep(max(0.0, self.last + self.delay - time.time()))
        self.last = time.time(); self.n += 1
        try:
            r = self.s.get(url, timeout=60)
        except Exception as e:  # noqa: BLE001
            self.bad.append((url, type(e).__name__)); return None
        if r.status_code != 200:
            self.bad.append((url, r.status_code)); return None
        return r.text


def cvf_listing(fx, path, venue, year, rows):
    """One CVF listing page (main conference, or one workshop): every ptitle entry with a .pdf link."""
    url = f'{CVF}/{path}'
    page = fx.get(url)
    if page is None:
        return 0
    if 'day=' in page and 'ptitle' not in page:  # day-paginated main listing
        page = fx.get(f'{url}?day=all') or page
    k = 0
    for land, title, rest in TITLE_PDF.findall(page):
        m = PDF.search(rest)
        t = clean(title)
        if m and len(F.nt(t)) >= 20:
            rows.append([t, year, urljoin(url, m.group(1)), urljoin(url, land), venue]); k += 1
    return k


def cvf(fx, rows, counts):
    for path in CVF_MAIN:
        y = int(re.search(r'(\d{4})', path).group(1))
        counts[path] = cvf_listing(fx, path, venue=path.replace('_', ' '), year=y, rows=rows)
    for menu in CVF_MENUS:
        y = int(re.search(r'(\d{4})', menu).group(1)); conf = menu.split('/')[0]
        page = fx.get(f'{CVF}/{menu}')
        if page is None:
            counts[menu] = None; continue
        # workshop pages: '/CVPR2024_workshops/MDEC' (2021-), or relative 'CVPR2019_CV-COPS.py' under the menu's directory (2016-20)
        base = f'{CVF}/{conf}/'
        subs = sorted({urljoin(base, h)[len(CVF) + 1:] for h in re.findall(r'href="([^"#?:]+)"', page)
                       if (h.lstrip('/').startswith(conf + '/') or re.fullmatch(r'[A-Za-z]+\d{4}_[^/]+\.py', h))
                       and not h.rstrip('/').endswith(('menu', 'menu.py'))})
        tot = 0
        for h in subs:
            tot += cvf_listing(fx, h, venue=f'{conf.replace("_", " ")}', year=y, rows=rows)
        if not subs:  # a single-page workshop listing (e.g. CVPR2026_workshops)
            tot = cvf_listing(fx, menu, venue=conf.replace('_', ' '), year=y, rows=rows)
        counts[menu] = tot


def miccai(fx, rows, counts):
    for y, url in MICCAI.items():
        page = fx.get(url)
        if page is None:
            counts[f'MICCAI{y}'] = None; continue
        k = 0
        for m in re.finditer(r'<b>(.*?)</b>(.*?)href="(https://papers\.miccai\.org/miccai-\d+/paper/[^"]+\.pdf)"[^>]*>PDF</a>\]&nbsp;\[<a href="([^"]+)"', page, re.S):
            t = clean(m.group(1))
            if len(F.nt(t)) >= 20:
                rows.append([t, y, m.group(3), 'https://papers.miccai.org' + m.group(4) if m.group(4).startswith('/') else m.group(4), f'MICCAI{y}']); k += 1
        counts[f'MICCAI{y}'] = k


JOURNALS = {  # venue (as the ledgers spell it) -> article landing page by DOI; the page's citation_pdf_url is a free PDF
    'Frontiers of Information Technology & Electronic Engineering':
        lambda d: 'https://www.fitee.zjujournals.com/en/article/doi/10.1631/' + d.split('/', 1)[1].upper() + '/',
    'Machine Intelligence Research': lambda d: 'https://www.mi-research.net/en/article/doi/' + d,
}
META = lambda name: re.compile(r'<meta\b[^>]*\bname="' + name + r'"[^>]*\bcontent="([^"]+)"', re.I)


def journals(fx, rows, counts):
    """Self-hosted Chinese journals whose own sites give free PDFs (checked 2026-11-25: no AI-agent opt-out, no challenge).
    Only the DOIs that some school's unavailable ledger still lists at these venues are asked; the row's title is the
    page's own citation_title, so the proceedings match stays a title match."""
    import glob
    want = {}
    for f in glob.glob(str(F.P.HIERARCHY / '*' / 'derived' / 'unavailable.jsonl.gz')):
        for line in gzip.open(f, 'rt'):
            r = json.loads(line)
            if r.get('venue') in JOURNALS and r.get('doi'):
                want[r['doi'].lower()] = r['venue']
    for venue in JOURNALS:
        k = 0
        for doi in sorted(d for d, v in want.items() if v == venue):
            land = JOURNALS[venue](doi)
            page = fx.get(land)
            if page is None:
                continue
            pdf, title = META('citation_pdf_url').search(page), META('citation_title').search(page)
            year = META('citation_(?:publication_)?date').search(page)
            if pdf and title and pdf.group(1).startswith('http') and len(F.nt(clean(title.group(1)))) >= 20:
                y = int(re.search(r'(\d{4})', year.group(1)).group(1)) if year and re.search(r'\d{4}', year.group(1)) else None
                rows.append([clean(title.group(1)), y, pdf.group(1).replace(' ', '%20'), land, venue]); k += 1
        counts[venue] = dict(asked=sum(1 for v in want.values() if v == venue), listed=k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(F.P.FT_RAW / 'proceedings_extra.json.gz'))
    ap.add_argument('--delay', type=float, default=2.0)
    ap.add_argument('--only', choices=['cvf', 'miccai', 'journals'])
    a = ap.parse_args()
    fx = Fetch(a.delay); rows = []; counts = {}
    if a.only in (None, 'miccai'):
        miccai(fx, rows, counts)
    if a.only in (None, 'journals'):
        journals(fx, rows, counts)
    if a.only in (None, 'cvf'):
        cvf(fx, rows, counts)
    seen = set(); out = []
    for r in rows:
        if (r[0], r[2]) not in seen:
            seen.add((r[0], r[2])); out.append(r)
    p = Path(a.out); tmp = p.with_name(f'.{p.name}.part')
    tmp.write_bytes(gzip.compress(json.dumps(out).encode()))
    tmp.replace(p)
    print(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(timespec='seconds'), out=str(p), entries=len(out),
                          requests=fx.n, failed=fx.bad[:20], n_failed=len(fx.bad), by_listing=counts)))


if __name__ == '__main__':
    main()
