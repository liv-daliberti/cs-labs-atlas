"""Add the CS lab papers that no full-text catalog work matches (by the counter's rule: collection id, OpenAlex-keyed id,
DOI, arXiv DOI, normalized title) to their school's catalog, as queued works the collector can then reach.

work id     the paper's collection work id when it has one, else <school>_oa_<OpenAlex W id>
work row    the lab paper's OpenAlex title, DOI (else the arXiv DOI when it has an arXiv version), year; graph_json is the
            paper node (OpenAlex id, venue, PIs, byline school people); metadata_source a small evidence file under
            discovery/claude-<school>-labpapers/evidence/
cmu / epfl / mit   straight into data/fulltext/<school>/catalog.sqlite (INSERT OR IGNORE works + paper node; commits per
            batch of 200; the collectors wait at most 120 s for a lock), as their catalog builders do
princeton   a package data/fulltext/princeton/discovery/claude-labpapers-newworks-<stamp>/ in the cs_pi_works format
            (new-works.jsonl with the OpenAlex record as oa_json, new-work-candidates.jsonl empty, associations.jsonl
            empty), imported by ../../claude-princeton-20261015/tools/import_all_when_free.py cs_pi_works:<package>
Candidates come afterwards from lab_channels.py (openalex, oa_arxiv, ...).
usage: add_works.py <school> [--dry]
"""
import json, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F


def main():
    school = sys.argv[1]; dry = '--dry' in sys.argv
    papers = F.lab_papers(school)
    cs = F.catalog_state(school, with_urls=False)
    todo = [r for r in papers.values() if not F.match_work(school, r, cs) and not F.is_local(school, r, cs)]
    bodies = F.oa_bodies(school, [r['oa'] for r in todo])
    lacking = [r['oa'] for r in todo if r['oa'] not in bodies]
    if lacking and not dry:
        bodies.update(F.fetch_oa_bodies(lacking))
    n = Counter(not_in_catalog=len(todo))
    works = []
    for r in todo:
        a = F.arxiv_of(r, bodies.get(r['oa']))
        wid = r['work'] or F.oa_work_id(school, r)
        doi = F.ndoi(r.get('doi')) or (f'10.48550/arxiv.{a}' if a else None)
        node = dict(id=wid, type='paper', name=r['title'], year=r.get('year'), doi=doi, openalex=r['oa'], venue=r.get('venue'), pis=r['pis'],
                    byline_school=r.get('byline_school'), status=f'{school}_cs_lab_paper_added_20261022',
                    source='claude-schools-20261021/hierarchy/' + school + '/lab_papers.jsonl.gz')
        works.append((wid, r, doi, node, bodies.get(r['oa'])))
    print(json.dumps(dict(n, sample=[w[0] for w in works[:3]])), flush=True)
    if dry or not works:
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
    if school == 'princeton':
        pkg = F.FT / 'princeton' / 'discovery' / f'claude-labpapers-newworks-{stamp}'
        (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
        ev = pkg / 'evidence' / 'lab-papers.json'
        ev.write_text(json.dumps(dict(rule=__doc__, created_at=F.now(), works=[w[3] for w in works]), ensure_ascii=False))
        with open(pkg / 'new-works.jsonl', 'w') as f:
            for wid, r, doi, node, body in works:
                f.write(json.dumps(dict(id=wid, node=node, metadata=body or {}, source=str(ev), rule='cs lab paper (claude-schools-20261021 hierarchy) not yet in the catalog'),
                                   ensure_ascii=False) + '\n')
        (pkg / 'new-work-candidates.jsonl').write_text('')
        (pkg / 'associations.jsonl').write_text('')
        (pkg / 'work-ids.txt').write_text('\n'.join(w[0] for w in works) + '\n')
        (pkg / 'summary.json').write_text(json.dumps(dict(created_at=F.now(), new_works=len(works), associations=0, new_work_candidates=0, rules=__doc__), indent=1))
        print(json.dumps(dict(package=str(pkg), new_works=len(works))))
        return
    disc = F.FT / school / 'discovery' / f'claude-{school}-labpapers' / 'evidence'
    disc.mkdir(parents=True, exist_ok=True)
    wrows, nrows = [], []
    for i in range(0, len(works), 100):
        part = works[i:i + 100]
        ev = disc / f'added-works-{stamp}-{i // 100:04d}.json'
        ev.write_text(json.dumps(dict(rule=__doc__, created_at=F.now(), works=[w[3] for w in part]), ensure_ascii=False))
        for wid, r, doi, node, body in part:
            wrows.append((wid, r['title'], doi, r.get('year'), json.dumps(node, ensure_ascii=False), str(ev), 'queued'))
            nrows.append((wid, 'paper', r['title'], json.dumps(node, ensure_ascii=False)))
    db = F.connect_rw(school)
    n['works_added'] = F.write_batches(db, 'INSERT OR IGNORE INTO works(id,title,doi,year,graph_json,metadata_source,status) VALUES (?,?,?,?,?,?,?)', wrows)
    n['nodes_added'] = F.write_batches(db, 'INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)', nrows)
    db.close()
    (F.HERE / 'logs').mkdir(exist_ok=True)
    with open(F.HERE / 'logs' / 'added-works.jsonl', 'a') as f:
        f.write(json.dumps(dict(at=F.now(), school=school, **n)) + '\n')
    print(json.dumps(dict(n)))


if __name__ == '__main__':
    main()
