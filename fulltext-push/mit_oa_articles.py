"""DSpace@MIT's Open Access Articles collection (hdl 1721.1/49433, the MIT faculty open-access policy's deposits:
author manuscripts of journal and conference papers, many published by IEEE / ACM / Springer) as an open-copy channel
for MIT lab papers without a local copy (2026-10-26).

harvest  OAI-PMH ListRecords, metadataPrefix=oai_dc, set=col_1721.1_49433 (robots.txt leaves /server/oai open; one
         request per 12 s, Retry-After honoured on 429/503, as ../../claude-mit-20261020/tools/mit_dspace_rest.py), every
         page stored zlib-compressed in raw/mit_oa_articles.sqlite (resumable from the last resumption token).
match    an item matches a missing MIT lab paper by DOI (dc:relation / dc:identifier) or by normalized title
         (pi_hierarchy.norm_title, >= 30 characters) -> the work gains the candidate https://hdl.handle.net/1721.1/<n>
         (evidence: the item's OAI record). The handle is then resolved by lab_channels.py mit dspace (OAI-PMH ORE ->
         the item's ORIGINAL PDFs through the REST API); the collector's title check applies.
usage: mit_oa_articles.py harvest | match [--dry]
"""
import html, json, re, sqlite3, sys, time, zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

OAI = 'https://dspace.mit.edu/server/oai/request'
SET = 'col_1721.1_49433'
DB = F.HERE / 'raw' / 'mit_oa_articles.sqlite'
# seconds between OAI requests: 12 until 2026-10-27, when the repository answered 429 with Retry-After 900 after 37 pages;
# 20 from 2026-10-30 (Retry-After is still honoured on every 429 / 503)
PACE = 20.0


def db():
    c = sqlite3.connect(str(DB))
    c.execute('CREATE TABLE IF NOT EXISTS pages (n INTEGER PRIMARY KEY, token TEXT, next_token TEXT, fetched_at TEXT, body BLOB)')
    return c


def harvest():
    import requests
    c = db()
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    row = c.execute('SELECT n, next_token FROM pages ORDER BY n DESC LIMIT 1').fetchone()
    n, token = (row[0] + 1, row[1]) if row else (0, None)
    if row and not token:
        print(json.dumps(dict(harvest='complete', pages=n))); return
    last = 0.0
    while True:
        params = dict(verb='ListRecords', resumptionToken=token) if token else dict(verb='ListRecords', metadataPrefix='oai_dc', set=SET)
        time.sleep(max(0, PACE - (time.monotonic() - last))); last = time.monotonic()
        try:
            r = s.get(OAI, params=params, timeout=(20, 180))
        except Exception as e:
            print(json.dumps(dict(error=str(e)[:120]))); time.sleep(60); continue
        if r.status_code in (429, 503):
            wait = min(int(r.headers.get('Retry-After') or 300), 1800)
            print(json.dumps(dict(status=r.status_code, wait=wait, at=F.now(), headers={k: v for k, v in r.headers.items() if 'rate' in k.lower() or 'retry' in k.lower()})), flush=True)
            time.sleep(wait); continue
        if r.status_code != 200:
            print(json.dumps(dict(status=r.status_code, stop=True))); return
        err = re.search(r'<error code="([^"]+)"', r.text)
        if err:  # an OAI-PMH error (e.g. badResumptionToken) is never stored as a page, so it cannot end the harvest as 'complete'
            print(json.dumps(dict(oai_error=err.group(1), token=token, stop=True))); return
        m = re.search(r'<resumptionToken[^>]*>([^<]*)</resumptionToken>', r.text)
        nxt = html.unescape(m.group(1)).strip() if m else ''
        c.execute('INSERT INTO pages VALUES (?,?,?,?,?)', (n, token, nxt, F.now(), zlib.compress(r.content)))
        c.commit()
        if n % 25 == 0:
            print(json.dumps(dict(page=n, token=nxt)), flush=True)
        n += 1
        if not nxt:
            (F.HERE / 'raw' / 'mit_oa_articles.done').write_text(F.now() + '\n')
            print(json.dumps(dict(harvest='complete', pages=n))); return
        token = nxt


def items():
    c = db()
    for (body,) in c.execute('SELECT body FROM pages ORDER BY n'):
        x = zlib.decompress(body).decode('utf-8', 'replace')
        for rec in x.split('<record>')[1:]:
            h = re.search(r'oai:dspace\.mit\.edu:1721\.1/(\d+)', rec)
            if not h or 'status="deleted"' in rec:
                continue
            titles = [html.unescape(t) for t in re.findall(r'<dc:title>(.*?)</dc:title>', rec, re.S)]
            vals = re.findall(r'<dc:(?:identifier|relation)>(.*?)</dc:(?:identifier|relation)>', rec, re.S)
            dois = {F.ndoi(html.unescape(m.group(0))) for v in vals for m in [re.search(r'10\.\d{4,9}/\S+', html.unescape(v))] if m}
            dois = {re.sub(r'[.,;)\]]+$', '', d) for d in dois}
            yield dict(handle=h.group(1), titles=titles, dois=sorted(dois), date=(re.findall(r'<dc:date>(.*?)</dc:date>', rec) or [None])[-1])


def match(dry=False):
    import lab_channels as L
    miss, known, base = L.plan_for('mit')
    by_doi, by_t = {}, {}
    for it in items():
        for d in it['dois']:
            by_doi.setdefault(d, it)
        for t in it['titles']:
            k = F.nt(t)
            if len(k) >= 30:
                by_t.setdefault(k, it)
    n, rows = Counter(), []
    for r, w in miss:
        d = F.ndoi(r.get('doi'))
        it, how = (by_doi.get(d), 'doi') if d and d in by_doi else (by_t.get(F.nt(r['title'])), 'title')
        if not it:
            continue
        n['matched_' + how] += 1
        u = f"https://hdl.handle.net/1721.1/{it['handle']}"
        if u in known[w] or any(f"1721.1/{it['handle']}" in k for k in known[w]):
            n['handle_already_known'] += 1; continue
        rows.append(dict(work_id=w, url=u, landing_url=u, version='acceptedVersion', source='mit_oa_articles_oai',
                         detail=json.dumps(dict(handle=it['handle'], match=how, item_titles=it['titles'][:1], item_dois=it['dois'][:3], paper_doi=d,
                                                title=r['title']))))
    n['items_indexed_doi'] = len(by_doi); n['items_indexed_title'] = len(by_t)
    added = 0 if dry else L.write('mit', L.new_rows(rows, known), 'mit_oa_articles')
    rec = dict(at=F.now(), school='mit', step='mit_oa_articles', missing_in_catalog=len(miss), rows=len(rows), works=len({r['work_id'] for r in rows}),
               candidates_added=added, dry=dry, **n)
    print(json.dumps(rec), flush=True)
    if not dry:
        with open(F.HERE / 'logs' / 'channels.jsonl', 'a') as f:
            f.write(json.dumps(rec) + '\n')


if __name__ == '__main__':
    {'harvest': harvest, 'match': lambda: match('--dry' in sys.argv)}[sys.argv[1]]()
