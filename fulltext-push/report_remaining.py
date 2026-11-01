"""Why the remaining lab papers have no local copy, per school: each lab paper without a copy (the counter's rule) by
catalog state - untried candidates left (the collector has not reached them yet), every known link tried and failed,
or no link at all - and by publisher (DOI prefix). Read-only, rowid-chunked. -> logs/remaining-<school>.json
usage: report_remaining.py <school> ..."""
import json, sqlite3, sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

PUB = {'10.1109': 'IEEE', '10.1145': 'ACM', '10.1007': 'Springer', '10.1016': 'Elsevier', '10.1038': 'Nature', '10.1126': 'Science (AAAS)',
       '10.1002': 'Wiley', '10.1111': 'Wiley', '10.1137': 'SIAM', '10.1364': 'Optica', '10.1117': 'SPIE', '10.1073': 'PNAS', '10.1093': 'Oxford UP',
       '10.1561': 'now publishers', '10.48550': 'arXiv DOI', '10.18653': 'ACL', '10.1101': 'bioRxiv/medRxiv', '10.1609': 'AAAI', '10.4230': 'LIPIcs',
       '10.1080': 'Taylor & Francis', '10.1177': 'SAGE', '10.1103': 'APS', '10.1088': 'IOP', '10.3389': 'Frontiers', '10.1371': 'PLOS',
       '10.1186': 'BMC', '10.1162': 'MIT Press', '10.1214': 'IMS', '10.1287': 'INFORMS', '10.1017': 'Cambridge UP', '10.1146': 'Annual Reviews',
       '10.2139': 'SSRN', '10.5281': 'Zenodo', '10.1063': 'AIP', '10.1021': 'ACS', '10.1039': 'RSC', '10.3390': 'MDPI', '10.1515': 'De Gruyter',
       '10.1142': 'World Scientific', '10.1049': 'IET', '10.21437': 'ISCA', '10.52202': 'ACM (SoK/CCS?)', '10.1287/': 'INFORMS',
       '10.1158': 'AACR', '10.1152': 'APS (physiology)', '10.1523': 'J Neurosci', '10.7554': 'eLife', '10.1162/': 'MIT Press',
       '10.24963': 'IJCAI', '10.14778': 'PVLDB', '10.1613': 'JAIR', '10.5555': 'ACM (no DOI page)', '10.2172': 'OSTI'}


def main():
    for school in sys.argv[1:]:
        papers = F.lab_papers(school)
        cs = F.catalog_state(school, with_urls=False)
        db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
        cands, atts, fails = defaultdict(set), defaultdict(set), defaultdict(Counter)
        for w, u in F.chunks(db, 'candidates', 'work_id, url', n=20000):
            cands[w].add(u)
        for w, u, st, d in F.chunks(db, 'attempts', 'work_id, url, status, detail', n=20000):
            atts[w].add(u)
            if st != 'downloaded':
                fails[w][(urlsplit(u).hostname or '?') + ': ' + (d or st or '')[:70]] += 1
        db.close()
        state, pub, why, host_fail = Counter(), defaultdict(Counter), Counter(), Counter()
        for r in papers.values():
            if F.is_local(school, r, cs):
                state['local'] += 1; continue
            w = F.match_work(school, r, cs)
            d = F.ndoi(r.get('doi'))
            p = PUB.get(d.split('/')[0], d.split('/')[0] or 'no DOI') if d else 'no DOI'
            if not w:
                s = 'not_in_catalog'
            elif cands[w] - atts[w]:
                s = 'untried_candidates_left'
            elif cands[w]:
                s = 'all_links_failed'
                for k in fails[w]:
                    host_fail[k] += 1
            else:
                s = 'no_open_link_found'
            state[s] += 1; pub[s][p] += 1
        out = dict(school=school, lab_papers=len(papers), state=dict(state), by_publisher={s: dict(c.most_common(15)) for s, c in pub.items()},
                   top_failures=dict(host_fail.most_common(25)))
        (F.P.FT_LOGS / f'remaining-{school}.json').write_text(json.dumps(out, indent=1))
        print(json.dumps(dict(school=school, lab_papers=len(papers), **state)), flush=True)


if __name__ == '__main__':
    main()
