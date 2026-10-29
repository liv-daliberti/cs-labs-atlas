"""Index every DSpace@MIT thesis item record already captured (no new requests): the EECS by-year harvest and adviser
queries in hierarchy/mit/thesis-captures.sqlite, and the adviser queries of the leftover 2026-10-22 session in
hierarchy/cs-related-captures-mit.sqlite, plus this review's own store. One row per (item, source capture):
handle, student, advisers, degree statement, issued year, department(s), and the exact quotes (advisor field through
author field; degree statement) cut from the capture's stored text.
usage: thesis_index.py <out.jsonl>
"""
import json, re, sqlite3, sys, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import mpcap  # noqa: E402

H = mpcap.HERE
SRC = [('hierarchy/mit/thesis-captures.sqlite', 'NULL'), ('hierarchy/cs-related-captures-mit.sqlite', 'text'),
       ('hierarchy/mit/cs-related-captures.sqlite', 'text')]


def items(d):
    for o in ((d.get('_embedded') or {}).get('searchResult') or {}).get('_embedded', {}).get('objects', []):
        yield (o.get('_embedded') or {}).get('indexableObject') or {}


def vals(md, k):
    return [v.get('value') for v in md.get(k) or []]


def qd(desc, deg, text):
    """The degree statement as it stands in the capture text: the dc.description 'Thesis: ...' line, else the
    dc.description.degree field."""
    if desc and desc[0] in text:
        return desc[0]
    if deg:
        q = '"dc.description.degree" : [ { "value" : ' + json.dumps(deg[0], ensure_ascii=False)
        if q in text:
            return q
    return None


def main(out):
    seen = set(); n = 0
    with open(out, 'w') as f:
        for db, col in SRC:
            c = sqlite3.connect(f'file:{H}/{db}?mode=ro', uri=True)
            for cid, url, sha, body, text in c.execute(f"select id, url, sha256, content, {col} from captures where status=200 and url like '%dspace.mit.edu/server/api/discover%'"):
                try:
                    raw = zlib.decompress(body)
                except zlib.error:
                    raw = body
                try:
                    d = json.loads(raw)
                except Exception:
                    continue
                if text is None:
                    text = mpcap.to_text(raw, 'application/json')
                for it in items(d):
                    md = it.get('metadata') or {}
                    adv = vals(md, 'dc.contributor.advisor')
                    if not adv:
                        continue
                    k = (it.get('handle'), sha)
                    if k in seen:
                        continue
                    seen.add(k)
                    desc = [v for v in vals(md, 'dc.description') if v and v.startswith('Thesis')]
                    deg = vals(md, 'dc.description.degree')
                    qa = None
                    a0 = json.dumps(adv[0], ensure_ascii=False)
                    m = re.search(r'"dc\.contributor\.advisor" : \[ \{ "value" : ' + re.escape(a0) + r'.{0,600}?"dc\.contributor\.author" : \[ \{ "value" : "[^"]*"', text)
                    if m:
                        qa = m.group(0)
                    qa_short = '"dc.contributor.advisor" : [ { "value" : ' + a0
                    f.write(json.dumps(dict(db=db, capture_id=cid, url=url, sha256=sha, handle=it.get('handle'), uuid=it.get('uuid'), advisers=adv,
                                            student=(vals(md, 'dc.contributor.author') or [None])[0], degree_statement=desc, degree=deg,
                                            issued=(vals(md, 'dc.date.issued') or [None])[0], depts=vals(md, 'dc.contributor.department'),
                                            quote_advisor=qa if qa and qa in text else (qa_short if qa_short in text else None),
                                            quote_degree=qd(desc, deg, text)), ensure_ascii=False) + '\n')
                    n += 1
    print('items', n)


main(sys.argv[1])
