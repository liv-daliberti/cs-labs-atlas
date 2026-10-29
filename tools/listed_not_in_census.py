"""Completeness check: every person a captured department faculty listing names as faculty (2016-2026) who is not in
the school's census at all (PI or not). Those are candidate computing PIs the hierarchy may be missing.

listings  listings/<school>/captures.sqlite (the yearly listing captures; blocks_json = the page as text blocks, JSON
          endpoints already turned into name / title blocks) and, for Princeton, claude-princeton-listings-20261022
names     a block that looks like a person's name followed by a block with a faculty title (Professor, Lecturer,
          Faculty, Instructor, Emeritus...), or one block "Name, Title"; postdoc / student / staff titles are skipped
census    census/<school>-faculty.json names and aliases (every row, PI or not) and hierarchy/census-overrides.json
-> hierarchy/<school>/listed-not-in-census.json [{name, years, titles, pages, example: {capture_url, sha256, quote}}]
usage: listed_not_in_census.py <school> ...
"""
import collections, json, re, sqlite3, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'listings/scripts')); sys.path.insert(0, str(Path(__file__).parent))
import match  # noqa: E402  (the listings' own title patterns)
from pi_hierarchy import Name, toks  # noqa: E402

NAME = re.compile(r"^(?:Dr\.?|Prof\.?)?\s*[A-ZÀ-Ž][\w'’.\-À-ž]+(?: [A-ZÀ-Ž(][\w'’.\-À-ž)]*){1,4}$")
PAIR = re.compile(r"^([A-ZÀ-Ž][\w'’.\-À-ž]+(?: [A-ZÀ-Ž][\w'’.\-À-ž]*){1,3}),?\s+((?:Assistant |Associate |Adjunct |Visiting |Research |Teaching |Full |Courtesy |"
                  r"Distinguished |University |Institute |Emerit\w* )*(?:Professor|Lecturer|Instructor|Faculty)\b.{0,80})$")
SKIP = re.compile(r"^(Faculty|People|Professors?|Emerit\w*|Lecturers?|Research|Directory|Department|School|Office|Contact|Home|News|"
                  r"Events|About|Menu|Search|Staff|Students|Alumni|Affiliated|Core|Adjunct|Courtesy|Visiting)\b", re.I)


def captures(school):
    if school == 'princeton':
        db = Path('/n/fs/resemble/maxent-grpo/.research-sweeps') / 'claude-princeton-listings-20261022/captures/listings.sqlite'
    else:
        db = HERE / 'listings' / school / 'captures.sqlite'
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    cols = [r[1] for r in c.execute('pragma table_info(captures)')]
    q = 'select capture_url, wayback_timestamp, sha256, blocks_json, department from captures where http_status=200' if 'blocks_json' in cols else None
    if q is None:  # the Princeton store keeps raw bytes only
        import zlib; sys.path.insert(0, str(Path('/n/fs/resemble/maxent-grpo/.research-sweeps') / 'claude-princeton-listings-20261022/scripts')); import extract as pex  # noqa
        for url, ts, ct, raw, sha, dept in c.execute('select capture_url, wayback_timestamp, content_type, raw_zlib, sha256, department from captures where http_status=200'):
            yield url, ts, sha, [t for _, t in pex.blocks(zlib.decompress(raw), ct)], dept
        return
    for url, ts, sha, bj, dept in c.execute(q):
        b = json.loads(bj) if bj else []
        b = b.get('blocks', []) if isinstance(b, dict) else b
        yield url, ts, sha, [x[-1] if isinstance(x, list) else x.get('text') if isinstance(x, dict) else x for x in b], dept


COMPUTING = {'princeton': {'Computer Science'}, 'cmu': None, 'mit': {'EECS', 'CSAIL'}, 'epfl': None, 'berkeley': {'EECS'}, 'stanford': {'CS', 'EE'}}
INSTITUTIONAL = re.compile(r"\b(University|Career|Distinguished|Research|Founders|Group|Family|Development|Service|Alumni|Electronics|America|Seminar|"
                           r"Series|Intranet|Department|Chairs?|Schweiz|Equality|Professorship|Foundation|Fund|Institute|Center|Centre|Lab|Program|Fellow)\b")


def chair_fragment(blocks, i, n, t):
    """'Herbert A. Simon' + 'Professor of ...' right after a person's own name: an endowed chair, not a person."""
    prev = blocks[i - 1] if i else ''
    return bool(INSTITUTIONAL.search(n)) or (bool(NAME.match(prev)) and not SKIP.match(prev) and re.match(r'(University )?Professor', t) is not None)


def activity(school, names):
    """School-affiliated OpenAlex authorships 2016-2026 per candidate name (the hierarchy sweep)."""
    import zlib
    from pi_hierarchy import INST, AFF
    inst = 'https://openalex.org/' + INST[school]; aff = re.compile(AFF[school], re.I)
    idx = collections.defaultdict(list)
    for n in names:
        for f, l in Name([n]).forms:
            idx[l].append(n)
    cnt = collections.Counter()
    c = sqlite3.connect(f'file:{HERE}/hierarchy/{school}/openalex-sweep.sqlite?mode=ro', uri=True)
    for (b,) in c.execute('select body from pages'):
        for w in json.loads(zlib.decompress(b)):
            for a in w.get('authorships') or []:
                raw = a.get('raw_author_name') or ''; tk = toks(raw)
                if len(tk) < 2:
                    continue
                for n in set(idx.get(tk[-1], [])):
                    if Name([n]).match(raw) and (inst in [l for i in a.get('institutions') or [] for l in i.get('lineage') or []] or any(aff.search(z) for z in a.get('raw_affiliation_strings') or [])):
                        cnt[n] += 1
    return cnt


def advisees(school, names):
    """Advising records naming each candidate (the school's collection, or Berkeley's own)."""
    from pi_hierarchy import read, SITE
    own = HERE / 'hierarchy' / school / 'collection.json.gz'
    C = read(own if own.exists() else SITE / f'collection-{school}.json.gz')
    people = C['people'] if isinstance(C['people'], list) else list(C['people'].values())
    nm = {n: Name([n]) for n in names}; cnt = collections.Counter()
    for p in people:
        for c in p.get('contexts') or []:
            if 'advis' in (c.get('type') or ''):
                advs = [c.get('advisorName') or c.get('advisor')] + list(c.get('advisors') or [])
                for n, k in nm.items():
                    if any(a and k.match(a) for a in advs):
                        cnt[n] += 1
    return cnt


def run(school):
    cf = HERE / f'census/{school}-faculty-hierarchy.json'
    census = json.loads((cf if cf.exists() else HERE / f'census/{school}-faculty.json').read_text())
    census = census.get('faculty', census) if isinstance(census, dict) else census
    ov = json.loads((HERE / 'hierarchy/census-overrides.json').read_text()).get(school, {}) if (HERE / 'hierarchy/census-overrides.json').exists() else {}
    known = [Name([x['name']] + list(x.get('aliases') or []) + list(ov.get(x['name'], {}).get('aliases') or [])) for x in census]
    by_sur = collections.defaultdict(list)
    for k in known:
        for f, l in k.forms:
            by_sur[l].append(k)
    seen = collections.defaultdict(lambda: dict(years=set(), titles=collections.Counter(), pages=set(), depts=set(), example=None, by_year={}))
    for url, ts, sha, blocks, dept in captures(school):
        if COMPUTING[school] and dept not in COMPUTING[school]:
            continue
        blocks = [str(b).strip() for b in blocks if b]
        for i, b in enumerate(blocks):
            n, t = None, None
            m = PAIR.match(b)
            if m:
                n, t = m.group(1), m.group(2)
            elif i + 1 < len(blocks) and NAME.match(b) and not SKIP.match(b) and match.FAC_RX.search(blocks[i + 1]) and len(blocks[i + 1]) < 120:
                n, t = re.sub(r'^(?:Dr\.?|Prof\.?)\s*', '', b), blocks[i + 1]
            if not n or match.NONFAC_RX.search(t) or match.TITLE_RX.search(n) or len(toks(n)) < 2 or chair_fragment(blocks, i, n, t):
                continue
            tk = toks(n)
            if any(k.match(n) for k in by_sur.get(tk[-1], []) + by_sur.get(''.join(tk[1:]), []) + by_sur.get(tk[0], [])):
                continue
            s = seen[n]; s['years'].add(int(ts[:4])); s['titles'][t[:70]] += 1; s['pages'].add(re.sub(r'^https?://web\.archive\.org/web/\d+id_/', '', url)[:90]); s['depts'].add(dept)
            s['example'] = s['example'] or dict(capture_url=url, sha256=sha, quote=f'{n} {t}'[:200])
            s['by_year'].setdefault(int(ts[:4]), dict(url=url, sha256=sha, quote=f'{n} {t}'[:200], title=t[:120], department=dept,
                                                      observed=f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}'))
    out = [dict(name=n, years=sorted(s['years']), titles=[t for t, _ in s['titles'].most_common(3)], departments=sorted(d for d in s['depts'] if d),
                pages=sorted(s['pages'])[:3], example=s['example'], listings=[s['by_year'][y] for y in sorted(s['by_year'])]) for n, s in seen.items()]
    act = activity(school, [x['name'] for x in out]); adv = advisees(school, [x['name'] for x in out])
    for x in out:
        t = ' '.join(x['titles'])
        x['works_2016_2026'] = act[x['name']]; x['advising_records'] = adv[x['name']]
        x['kind'] = ('ee_only_out_of_scope' if school == 'mit' and re.search(r'\[EE\]', t) and not re.search(r'CS|AI\+D', t) else
                     'emeritus' if re.search(r'Emerit', t, re.I) else 'adjunct_courtesy_visiting' if re.search(r'Adjunct|Courtesy|Visiting|Affiliate', t, re.I) else
                     'teaching' if re.search(r'Lecturer|Teaching|Instructor', t, re.I) else 'research' if re.search(r'Research (Professor|Scientist)|Systems Scientist|Project Scientist', t, re.I) else
                     'ladder' if re.search(r'Professor', t) else 'other')
        x['likely_missing_pi'] = x['kind'] not in ('ee_only_out_of_scope',) and x['works_2016_2026'] >= 3 and (x['advising_records'] > 0 or x['kind'] == 'ladder')
    out.sort(key=lambda x: (not x['likely_missing_pi'], -x['works_2016_2026'], x['name']))
    (HERE / 'hierarchy' / school / 'listed-not-in-census.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    miss = [x for x in out if x['likely_missing_pi']]
    print(json.dumps(dict(school=school, names_not_in_census=len(out), kinds=dict(collections.Counter(x['kind'] for x in out)), likely_missing_pis=len(miss),
                          examples=[(x['name'], f"{x['years'][0]}-{x['years'][-1]}", x['kind'], x['works_2016_2026'], x['advising_records'], x['titles'][0][:45]) for x in miss[:40]])))


if __name__ == '__main__':
    for s in sys.argv[1:]:
        run(s)
