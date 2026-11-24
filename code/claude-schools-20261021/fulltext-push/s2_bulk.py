"""Semantic Scholar Datasets API (bulk release), streamed and filtered to our lab papers (2026-11-04, owner: bulk open-access sources, 2).

Terms (read 2026-11-04): the datasets are licensed ODC-BY (dataset README; attribution: cite Kinney et al. 2023, "The Semantic Scholar Open Data
Platform", and Lo et al. 2020 for s2orc); the API licence (semanticscholar.org/product/api/license) allows keyed use, forbids exceeding rate limits and
redistributing the API. We use the key only for the dataset file lists (a few requests), stream each file over HTTPS once and keep only the rows
of our works; the raw dump is never stored. PDF URLs are used only as fetch candidates (the collectors check robots.txt and the file's title).

What the datasets hold (probed 2026-11-04, release 2026-10-27): `papers` has ids and titles but no PDF URL (only isopenaccess); `s2orc` has
content.source.pdfurls and content.source.oainfo (Unpaywall's license / openaccessurl / status; the keys are lower case, pdfurls is often null) for the papers whose PDF S2 parsed. So:
  papers  <task> <of>   corpusid for every target by DOI, then ArXiv id, then normalized title + first author's family name (year within 2)
                        (bulk_oa.match_record); writes FT_RAW/bulk-oa/s2/<release>/papers-<task>.jsonl
  s2orc   <task> <of>   for the corpusids the papers pass found: pdfUrls and oaInfo; writes s2orc-<task>.jsonl
  merge                 one file per dataset: FT_RAW/bulk-oa/s2/<release>/{papers,s2orc}.jsonl.gz (parts removed after the row counts agree)
Matching runs on the raw bytes of each JSON line (a regex for the ids, title and first author); only a hit is parsed.
usage: s2_bulk.py papers|s2orc <task> <of> | merge | release
"""
import gzip
import json
import os
import re
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bulk_oa as B  # noqa: E402
import ftp_common as F  # noqa: E402

API = 'https://api.semanticscholar.org/datasets/v1'
REL_DIR = B.DIR / 's2'
DOI_RE = re.compile(rb'"DOI":"([^"]+)"')
AX_RE = re.compile(rb'"ArXiv":"([^"]+)"')
TITLE_RE = re.compile(rb'"title":"((?:[^"\\]|\\.)*)","authors":\[(?:\{"authorId":(?:null|"[^"]*"),"name":"((?:[^"\\]|\\.)*)")?')
YEAR_RE = re.compile(rb'"year":(\d{4}|null)')
CID_RE = re.compile(rb'^\{"corpusid":(\d+)')


def api(path):
    import requests
    F.load_env()
    h = {'x-api-key': os.environ['S2_API_KEY']}
    for i in range(12):
        r = requests.get(API + path, headers=h, timeout=60)
        if r.status_code == 200:
            return r.json()
        time.sleep(15 + 10 * i)  # the key's limit is shared with the other S2 jobs: wait, do not hammer
    raise RuntimeError(f'S2 datasets API {path}: {r.status_code}')


def release():
    return api('/release/latest')['release_id']


def file_urls(rel, dataset):
    return api(f'/release/{rel}/dataset/{dataset}')['files']


def stream_lines(url, refresh=None):
    """Lines (bytes) of a gzipped JSONL file, streamed (4 MiB reads), never stored."""
    import requests
    for attempt in range(5):
        try:
            with requests.get(url, stream=True, timeout=(30, 120)) as r:
                r.raise_for_status()
                d, buf = zlib.decompressobj(31), b''
                for chunk in r.iter_content(4 << 20):
                    buf += d.decompress(chunk)
                    *lines, buf = buf.split(b'\n')
                    yield from lines
                if buf.strip():
                    yield buf
                return
        except Exception as e:
            print(json.dumps(dict(stream_retry=attempt, error=repr(e)[:150])), flush=True)
            time.sleep(30)
            if refresh is not None:  # the presigned URL expires: ask the file list again
                url = refresh()
            if attempt == 4:
                raise
            # restart the file from its beginning: rows already yielded are matched again, which is harmless (dedup at merge)


def _title(raw):
    return json.loads(b'"' + raw + b'"') if raw else ''


def task_papers(task, of):
    rel = release()
    files = file_urls(rel, 'papers')
    out = REL_DIR / rel
    out.mkdir(parents=True, exist_ok=True)
    ix = B.index(B.read_targets())
    by_doi, by_ax, by_t = ix
    kept = n = 0
    tmp = out / f'papers-{task}.jsonl.part'
    with open(tmp, 'w') as f:
        for fi in range(task, len(files), of):
            t0 = time.time()
            for line in stream_lines(files[fi], lambda fi=fi: file_urls(rel, 'papers')[fi]):
                n += 1
                md, ma = DOI_RE.search(line), AX_RE.search(line)
                doi = md.group(1).decode().lower() if md else None
                ax = ma.group(1).decode() if ma else None
                hit = (doi in by_doi) or (ax and re.sub(r'v\d+$', '', ax) in by_ax)
                title = fam1 = year = None
                if not hit:
                    mt = TITLE_RE.search(line)
                    if mt and len(mt.group(1)) >= 20:
                        title = _title(mt.group(1))
                        k = F.nt(title)
                        fam1 = B.fam(_title(mt.group(2))) if mt.group(2) else ''
                        hit = f'{k}|{fam1}' in by_t
                        my = YEAR_RE.search(line)
                        year = int(my.group(1)) if my and my.group(1) != b'null' else None
                if not hit:
                    continue
                o = json.loads(line)
                ex = o.get('externalids') or {}
                title = title or o.get('title')
                fam1 = fam1 if fam1 is not None else B.fam(((o.get('authors') or [{}])[0] or {}).get('name') or '')
                how, rows = B.match_record(ix, doi=ex.get('DOI'), arxiv=ex.get('ArXiv'), title=o.get('title'), first_family=fam1, year=o.get('year'))
                if not rows:
                    continue
                kept += 1
                f.write(json.dumps(dict(corpusid=o['corpusid'], how=how, doi=ex.get('DOI'), arxiv=ex.get('ArXiv'), pmc=ex.get('PubMedCentral'), acl=ex.get('ACL'),
                                        isopenaccess=o.get('isopenaccess'), title=o.get('title'), year=o.get('year'),
                                        targets=[[r['school'], r['key'], r['work_id']] for r in rows])) + '\n')
            print(json.dumps(dict(papers_shard=fi, seconds=round(time.time() - t0), rows_seen=n, kept=kept)), flush=True)
    tmp.replace(out / f'papers-{task}.jsonl')


def corpus_ids(rel):
    ids = set()
    p = REL_DIR / rel / 'papers.jsonl.gz'
    with gzip.open(p, 'rt') as f:
        for line in f:
            ids.add(json.loads(line)['corpusid'])
    return ids


def task_s2orc(task, of):
    rel = release()
    files = file_urls(rel, 's2orc')
    want = {str(c).encode() for c in corpus_ids(rel)}
    out = REL_DIR / rel
    kept = n = 0
    tmp = out / f's2orc-{task}.jsonl.part'
    with open(tmp, 'w') as f:
        for fi in range(task, len(files), of):
            t0 = time.time()
            for line in stream_lines(files[fi], lambda fi=fi: file_urls(rel, 's2orc')[fi]):
                n += 1
                m = CID_RE.match(line)
                if not m or m.group(1) not in want:
                    continue
                o = json.loads(line)
                src = (o.get('content') or {}).get('source') or {}
                kept += 1
                f.write(json.dumps(dict(corpusid=o['corpusid'], pdfurls=src.get('pdfurls') or src.get('pdfUrls') or [], oainfo=src.get('oainfo') or src.get('oaInfo'))) + '\n')
            print(json.dumps(dict(s2orc_shard=fi, seconds=round(time.time() - t0), rows_seen=n, kept=kept)), flush=True)
    tmp.replace(out / f's2orc-{task}.jsonl')


def merge(dataset, rel=None):
    rel = rel or release()
    d = REL_DIR / rel
    parts = sorted(d.glob(f'{dataset}-*.jsonl'))
    seen, rows = set(), 0
    tmp = d / f'{dataset}.jsonl.gz.tmp'
    with gzip.open(tmp, 'wt') as g:
        for p in parts:
            for line in p.open():
                c = json.loads(line)['corpusid']
                if c in seen:  # a restarted stream wrote the row twice
                    continue
                seen.add(c)
                g.write(line); rows += 1
    tmp.replace(d / f'{dataset}.jsonl.gz')
    for p in parts:
        p.unlink()
    print(json.dumps(dict(merged=dataset, parts=len(parts), rows=rows, release=rel)))


def read(rel=None):
    """-> {corpusid: dict(papers row, pdfurls, oainfo)} of the newest merged release (or `rel`)."""
    if rel is None:
        rels = sorted(p.name for p in REL_DIR.glob('*') if (p / 'papers.jsonl.gz').exists())
        rel = rels[-1] if rels else None
    if rel is None:
        return {}, None
    out = {}
    with gzip.open(REL_DIR / rel / 'papers.jsonl.gz', 'rt') as f:
        for line in f:
            o = json.loads(line)
            out.setdefault(o['corpusid'], dict(o, pdfurls=[], oainfo=None))
    p = REL_DIR / rel / 's2orc.jsonl.gz'
    if p.exists():
        with gzip.open(p, 'rt') as f:
            for line in f:
                o = json.loads(line)
                if o['corpusid'] in out:
                    out[o['corpusid']].update(pdfurls=o['pdfurls'], oainfo=o['oainfo'])
    return out, rel


if __name__ == '__main__':
    a = sys.argv[1]
    if a == 'papers':
        task_papers(int(sys.argv[2]), int(sys.argv[3]))
    elif a == 's2orc':
        task_s2orc(int(sys.argv[2]), int(sys.argv[3]))
    elif a == 'merge':
        merge(sys.argv[2])
    elif a == 'release':
        print(release())
