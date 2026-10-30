"""Reviewed OpenAlex author ids for a protocol school's PIs (protocol stage 5), written into the school's section of the
shared hierarchy/census-overrides.json (keys openalex, why_openalex, openalex_evidence, aliases), which the builder and
tools/stage_gate.py read.

inputs  hierarchy/<key>/openalex-identity-review.json: hand-reviewed decisions {name: {openalex: [ids], why, aliases?}}
        hierarchy/<key>/cs-related-review.json: accepted people with no DBLP id take the OpenAlex ids of their
        computing-share test (tools/cs_related_school.py share_test: ORCID, or full name with namesakes set aside), when
        the test passed on them (why: 'computing-share identity rule')
evidence for each id, the first sweep work (hierarchy/<key>/openalex-sweep.sqlite, papers only) whose authorship under
        that id lists the school: url = the work's API url, sha256 = sha256 of the stored work record (json, sorted keys,
        as the sweep stored it), quote = '<raw author name> | <raw affiliation string>'
Only this school's entries change; other schools' sections and the file layout are kept.
usage: oa_identity_school.py <key> [--dry-run]
"""
import hashlib, json, sqlite3, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pi_hierarchy import NOT_PAPERS  # noqa: E402
from cs_related_candidates import school_test  # noqa: E402

OA = 'https://openalex.org/'


def full(a):
    return a if a.startswith('http') else OA + a


def wanted(key):
    rev = json.loads((P.HIERARCHY / key / 'openalex-identity-review.json').read_text())['decisions']
    out = {n: dict(openalex=[full(a) for a in d['openalex']], why=d['why'], aliases=d.get('aliases') or [], basis='reviewed') for n, d in rev.items()}
    cen = {x['name']: x for x in json.loads((P.CENSUS / f'{key}-faculty.json').read_text())['faculty']}
    add = {x['name']: x for x in json.loads((P.CENSUS / f'{key}-additions.json').read_text())} if (P.CENSUS / f'{key}-additions.json').exists() else {}
    for d in json.loads((P.HIERARCHY / key / 'cs-related-review.json').read_text())['decisions']:
        if d['decision'] != 'accepted' or d['name'] in out:
            continue
        x = cen.get(d['name']) or add.get(d['name']) or {}
        sh = (d.get('cs_basis') or {}).get('openalex_share') or {}
        if x.get('dblp') or (d.get('cs_basis') or {}).get('dblp') or sh.get('result') != 'computing' or not sh.get('ids'):
            continue
        bases = '; '.join(f"{a['author'].rsplit('/', 1)[-1]}: {a['basis']}" for a in sh.get('authors') or [])
        out[d['name']] = dict(openalex=[full(a) for a in sh['ids']], aliases=[], basis='share_test',
                              why=f"computing-share identity rule (hierarchy/{key}/cs-related-review.json, {S.get(key)['name']}): {bases}")
    return out


def evidence(key, ids):
    at_school = school_test(key); ev = {}
    c = sqlite3.connect(f"file:{P.HIERARCHY / key / 'openalex-sweep.sqlite'}?mode=ro", uri=True)
    for (b,) in c.execute('select body from pages order by year desc, page'):
        for w in json.loads(zlib.decompress(b)):
            if w.get('type') in NOT_PAPERS:
                continue
            for a in w.get('authorships') or []:
                aid = (a.get('author') or {}).get('id')
                if aid in ids and aid not in ev and at_school(a):
                    raw = next((r for r in a.get('raw_affiliation_strings') or [] if r), '')
                    ev[aid] = dict(url=w['id'].replace(OA, 'https://api.openalex.org/works/'), sha256=hashlib.sha256(json.dumps(w, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                                   quote=f"{a.get('raw_author_name') or ''} | {raw}", observed=w.get('publication_date'), source='OpenAlex sweep 2026-10-29 (hierarchy/<key>/openalex-sweep.sqlite)'.replace('<key>', key))
        if len(ev) == len(ids):
            break
    return ev


def main(key, dry=False):
    want = wanted(key)
    ev = evidence(key, {a for d in want.values() for a in d['openalex']})
    f = P.HIERARCHY / 'census-overrides.json'; txt = f.read_text(); ov = json.loads(txt)
    sec = ov.setdefault(key, {}); n = {'reviewed': 0, 'share_test': 0, 'no_evidence': 0}
    for name, d in want.items():
        ids = [a for a in d['openalex'] if a in ev]
        n['no_evidence'] += len(d['openalex']) - len(ids)
        if not ids:
            continue
        e = sec.setdefault(name, {})
        e['openalex'] = ids; e['why_openalex'] = f"2026-10-30 ({d['basis']}): {d['why']}"
        e['openalex_evidence'] = [ev[a] for a in ids]
        if d['aliases']:
            e['aliases'] = list(dict.fromkeys(list(e.get('aliases') or []) + d['aliases']))
        n[d['basis']] += 1
    print(json.dumps(dict(n, people=len(want))))
    if not dry:
        f.write_text(json.dumps(ov, indent=1, ensure_ascii='\\u' in txt) + ('\n' if txt.endswith('\n') else ''))


if __name__ == '__main__':
    main(sys.argv[1], '--dry-run' in sys.argv)
