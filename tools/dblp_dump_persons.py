"""Every census PI's full DBLP person page, read from DBLP's official dump instead of the cached co-author answers.

Why (2026-10-29): the builder anchors a PI's identity on the PI's DBLP publication list, but the cached lists
(claude-<school>-*/raw/dblp_pubs.json.gz) hold only the records some census PI's query happened to return. A PI whose DBLP
id was found as a co-author there (pi_hierarchy 'unique DBLP person of that exact name among the cached publication
co-authors', e.g. Song Mei at Berkeley: 13 of his ~100 records) or who was added to the census later had a partial or
empty list, so most of their own school-affiliated works failed identity.

Source: var/data/dblp-dump/dblp-2026-09-01.xml.gz, DBLP's own monthly bulk release (doi:10.4230/dblp.xml.2026-09-01;
see tools/dblp_dump_index.py), never the bot-walled dblp.org site.
  pass 1  person records (<www key="homepages/<pid>">): their author names (the first is the primary name, the rest are
          aliases), urls (ORCID, homepages) and affiliation notes, for (a) every DBLP pid a PI record carries and (b) every
          person record that carries a PI's exact name (pis.json names and census additions) (base name, a DBLP homonym number like ' 0001' set aside), so a PI
          without a census pid can be looked up; 'disambiguation' profiles are flagged (they pool unresolved homonyms)
  pass 2  every publication record (CoRR preprints included: they anchor identity, not venue) whose author string is one
          of the target persons' name strings (DBLP gives each person one unique string per name form)
-> hierarchy/dblp-dump-persons.json.gz
   {dump, persons: {pid_url: {names, urls, orcid, affiliations, disambiguation, pubs: [{key, type, title, year, dois,
    authors: [[name, orcid]]}]}}, by_name: {normalized PI name: [pid_url, ...]}}
usage: dblp_dump_persons.py [<school>]
  with a school key (an onboarding school) only that school's PIs, written to hierarchy/<key>/dblp-dump-persons-school.json.gz and read by the
  builder next to the shared file; the shared file (which a release build reads) is never rewritten (UChicago PROTOCOL-FRICTION 43).
"""
import gzip, html, json, re

from pi_hierarchy import toks  # noqa: E402

import atlas_paths as P  # noqa: E402  (every path in one place)
import census_overrides as CO  # noqa: E402
HERE = P.WORK
DUMP = P.DBLP_DUMP_XML
import sys  # noqa: E402
import school_config as S  # noqa: E402  (the school charters)
ONE = sys.argv[1] if len(sys.argv) > 1 else None
OUT = P.data_w('dblp-dump-persons-school.json.gz', ONE) if ONE else P.data('dblp-dump-persons.json.gz')
SCHOOLS = [ONE] if ONE else S.keys()  # released and onboarding schools: a new school's PIs get their DBLP pages before its first release
REC = re.compile(r'<(article|inproceedings|proceedings|book|incollection|phdthesis|mastersthesis|www|data) ([^>]*?)key="([^"]+)"[^>]*>(.*?)</\1>', re.S)
AUTH = re.compile(r'<(?:author|editor)([^>]*)>(.*?)</(?:author|editor)>', re.S)
ORC = re.compile(r'orcid="([0-9X-]{19})"')
DOI = re.compile(r'<ee[^>]*>https?://(?:dx\.)?doi\.org/([^<]+)</ee>')
URL = re.compile(r'<url[^>]*>(.*?)</url>')
NOTE = re.compile(r'<note[^>]*type="([^"]+)"[^>]*>(.*?)</note>', re.S)
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S)
YEAR = re.compile(r'<year>(\d{4})</year>')


def text(s):
    return re.sub(r'<[^>]+>', '', html.unescape(s or '')).strip()


def base(name):
    """'Song Mei 0001' -> 'song mei' (DBLP homonym number set aside)."""
    return ' '.join(toks(re.sub(r'\s+\d{4}$', '', name)))


def records():
    tail = ''
    with gzip.open(DUMP, 'rt', encoding='utf-8', errors='replace') as f:
        while True:
            chunk = f.read(8 << 20); buf = tail + chunk; end = 0
            for m in REC.finditer(buf):
                end = m.end(); yield m.group(1), m.group(3), m.group(4)
            tail = buf[end:]
            if not chunk:
                break


def source_targets(school):
    """Accepted PIs, including a school's core census before its first build.

    Native outputs are optional here: they cannot be required to collect the
    identity evidence that the first native build itself needs.
    """
    def read(name, default):
        path = P.data(name, school)
        return json.loads(path.read_text()) if path.exists() else default

    def values(value):
        return [value] if isinstance(value, str) else list(value or [])

    census = read('census-faculty.json', {})
    census = census.get('faculty', []) if isinstance(census, dict) else census
    rows = read('pis.json', []) + [x for x in census if x.get('is_pi')]
    rows += [x for x in read('census-additions.json', []) if x.get('is_pi', True)]
    overrides = CO.section(school)
    pids, names = set(), set()
    for row in rows:
        name = row.get('censusName') or row.get('name') or row.get('pi')
        override = overrides.get(name) or {}
        if override.get('exclude'):
            continue
        pids.update(q.rstrip('/') for q in values(row.get('dblp')) + values(row.get('dblpDropped')) + values(override.get('dblp'))
                    if isinstance(q, str) and '/pid/' in q)
        forms = values(row.get('names')) + [name]
        forms += values(row.get('aliases')) + values(override.get('aliases'))
        names.update(base(n) for n in forms if n and len(toks(n)) >= 2)
    return pids, names


def main():
    pids, names = set(), set()
    for s in SCHOOLS:
        school_pids, school_names = source_targets(s)
        pids |= school_pids
        names |= school_names
    want = {'homepages/' + q.split('/pid/', 1)[1] for q in pids}
    persons, by_name = {}, {}
    for typ, key, body in records():  # pass 1
        if typ != 'www' or not key.startswith('homepages/'):
            continue
        ns = [text(a) for _, a in AUTH.findall(body)]
        hit = [n for n in ns if base(n) in names]
        if key in want or hit:
            url = 'https://dblp.org/pid/' + key.split('/', 1)[1]
            notes = NOTE.findall(body)
            urls = [text(u) for u in URL.findall(body)]
            persons[url] = dict(names=ns, urls=urls, orcid=sorted({m.group(1) for u in urls for m in [re.search(r'orcid\.org/([0-9X-]{19})', u)] if m}),
                                affiliations=[text(v) for t, v in notes if t == 'affiliation'],
                                disambiguation=any(t == 'disambiguation' for t, _ in notes), pubs=[])
            for n in hit:
                by_name.setdefault(base(n), []).append(url)
    print(json.dumps(dict(pass1_persons=len(persons), wanted=len(want), found_wanted=sum(('https://dblp.org/pid/' + k.split('/', 1)[1]) in persons for k in want))), flush=True)
    owner = {}
    for url, p in persons.items():
        for n in p['names']:
            owner.setdefault(n, set()).add(url)
    n_pubs = 0
    for typ, key, body in records():  # pass 2
        if typ in ('www', 'data'):
            continue
        auths = [(text(a), (ORC.search(attr) or [None, None])[1]) for attr, a in AUTH.findall(body)]
        hit = {u for a, _ in auths for u in owner.get(a, ())}
        if not hit:
            continue
        t = TITLE.search(body); y = YEAR.search(body)
        rec = dict(key=key, type=typ, title=text(t.group(1)) if t else '', year=int(y.group(1)) if y else None,
                   dois=sorted({html.unescape(d).strip().lower() for d in DOI.findall(body)}), authors=[list(a) for a in auths])
        for u in hit:
            persons[u]['pubs'].append(rec)
        n_pubs += 1
    with gzip.open(OUT, 'wt') as f:
        json.dump(dict(dump=DUMP.name, persons=persons, by_name=by_name), f, ensure_ascii=False)
    print(json.dumps(dict(persons=len(persons), pub_records=n_pubs, out=str(OUT))), flush=True)


if __name__ == '__main__':
    main()
