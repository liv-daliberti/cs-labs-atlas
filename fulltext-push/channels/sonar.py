"""Channel sonar (2026-11-04): SONAR (sonar.ch, the Swiss institutional-repository portal; also served as folia.unifr.ch) holds open
full texts of papers by Swiss co-authors. Its landing pages (/global/documents/<id>) are a JavaScript app with no PDF link, so the
collector ends at 'no unambiguous primary PDF link' (137 lab papers, 2026-11-03 ledger). The public JSON record
(https://sonar.ch/api/documents/<id>) lists the files; an unrestricted PDF named in `_files` is served directly (HTTP 200,
https://sonar.ch/api/documents/<id>/files/<key>), no redirect, no login.
Only ids a paper's own known URLs already name are asked (one record per id, 3 s apart; robots.txt of sonar.ch is `Allow: /`, checked
for this client and the Anthropic crawler groups). Title search on the API was measured too (80 random missing papers: 0 matches), so
there is no discovery by title or DOI: the channel only opens the records the landing links point to.
The collector's page-1 identity rule decides at download time.
"""
import json
import re

NAME = 'sonar'
ID = re.compile(r'(?:sonar\.ch|folia\.unifr\.ch)/global/documents/(\d+)')
AI_AGENTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', 'Claude-User', 'Claude-SearchBot')


def doc_ids(known):
    return sorted({m.group(1) for u in known for m in [ID.search(u)] if m})


def APPLIES(school, paper):
    return bool(doc_ids(paper.known)) and not any('sonar.ch/api/documents' in u for u in paper.known)


def open_pdf_keys(record):
    """The keys of the record's unrestricted PDF files (fulltext first)."""
    files = (record.get('metadata') or {}).get('_files') or []
    keys = [f['key'] for f in files if str(f.get('key', '')).lower().endswith('.pdf') and not (f.get('restriction') or {}).get('restricted')
            and (f.get('permissions') or {}).get('read', True)]
    return sorted(keys, key=lambda k: (k != 'fulltext.pdf', k))


def discover(school, papers, ctx):
    from protego import Protego
    s = ctx.session()
    rules = Protego.parse(s.get('https://sonar.ch/robots.txt', timeout=(15, 30)).text)
    ok = rules.can_fetch('https://sonar.ch/api/documents/1', s.headers.get('User-Agent', '*')) and all(
        rules.can_fetch('https://sonar.ch/api/documents/1', a) for a in AI_AGENTS)
    for p in papers:
        urls = []
        for i in doc_ids(p.known):
            if not ok:
                break
            txt = ctx.polite_get(f'https://sonar.ch/api/documents/{i}', delay=3.0)
            try:
                rec = json.loads(txt) if txt else {}
            except ValueError:
                rec = {}
            ctx.n['sonar_records'] += 1
            for k in open_pdf_keys(rec)[:1]:
                urls.append(dict(work_id=p.work_id, url=f'https://sonar.ch/api/documents/{i}/files/{k}', landing_url=f'https://sonar.ch/global/documents/{i}',
                                 version=None, source='sonar', detail=f'SONAR record {i}'))
                ctx.n['sonar_open_files'] += 1
        yield ctx.result(p, 'found' if urls else 'none', urls, query='SONAR record ' + ','.join(doc_ids(p.known))[:200])
