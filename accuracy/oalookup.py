"""OpenAlex evidence for the coverage items (helper): the PI's authorship on the DBLP record's work (by DOI, else title
search), with institutions and raw affiliations, and the byline's school-affiliated co-authors. Responses are cached in
work/accuracy/cache/openalex.jsonl.gz-free form (one JSON per line) so re-runs make no requests.

usage: oalookup.py <school>
"""
import html, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evidence import nt, short  # noqa: E402

ACC = Path(__file__).parent
CACHE = ACC / 'cache' / 'openalex.jsonl'
AFF = {'princeton': r'princeton', 'cmu': r'carnegie|cmu', 'epfl': r'epfl|lausanne|polytechnique f', 'mit': r'massachusetts inst|\bmit\b|csail',
       'berkeley': r'berkeley', 'stanford': r'stanford'}
SEL = 'id,doi,display_name,publication_date,type,authorships,primary_location'


def key():
    for line in open(os.path.expanduser('~/.config/cs-atlas/openalex.env')):
        if line.startswith('OPENALEX_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')


def get(url, cache, k):
    if url in cache:
        return cache[url]
    time.sleep(1.1)
    req = urllib.request.Request(url + ('&' if '?' in url else '?') + 'api_key=' + k, headers={'User-Agent': 'cs-atlas-accuracy/1.0'})
    try:
        body = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:
        body = {'error': str(e)[:200]}
    if 'error' in body:
        return body
    cache[url] = body
    CACHE.parent.mkdir(exist_ok=True)
    with open(CACHE, 'a') as f:
        f.write(json.dumps({'url': url, 'body': body}) + '\n')
    return body


def fam(name):
    t = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    t = re.sub(r'\s+\d{4}$', '', t)
    return re.split(r'[\s.]+', t.strip())[-1]


def show(w, pi, school, rx):
    f = fam(pi)
    print(f"   OA {w['id'].split('/')[-1]} {short(w.get('display_name'),80)} | {w.get('publication_date')} {w.get('type')} | {short(((w.get('primary_location') or {}).get('source') or {}).get('display_name'),30)}")
    co = []
    for a in w.get('authorships') or []:
        nm = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
        insts = [i.get('display_name') for i in a.get('institutions') or []]
        affs = a.get('raw_affiliation_strings') or []
        if f in unicodedata.normalize('NFKD', nm).encode('ascii', 'ignore').decode().lower():
            print(f"   PI-AUTH {nm}: inst={short(insts,90)} aff={short(affs,150)}")
        elif any(re.search(rx, x, re.I) for x in insts + affs):
            co.append(nm)
    print(f"   school co-authors: {short(co,150)} (of {len(w.get('authorships') or [])})")


def main(school):
    k = key()
    cache = {}
    if CACHE.exists():
        for line in open(CACHE):
            d = json.loads(line); cache[d['url']] = d['body']
    S = json.load(open(ACC / 'sample.json'))['schools'][school]
    for it in S['lab_coverage']:
        d = it['dblp']
        print(f"* {it['key']}")
        w = None
        for doi in d['dois']:
            if doi.lower().startswith('10.48550'):
                continue
            b = get('https://api.openalex.org/works/doi:' + urllib.parse.quote(doi.lower(), safe='/') + '?select=' + SEL, cache, k)
            if b.get('id'):
                w = b; break
        if w is None:
            t = re.sub(r'[^\w\s-]', ' ', html.unescape(d['title'])).strip()
            b = get('https://api.openalex.org/works?filter=title.search:' + urllib.parse.quote(t) + '&per_page=5&select=' + SEL, cache, k)
            res = [x for x in b.get('results') or [] if nt(x.get('display_name')) == nt(d['title'].rstrip('.'))]
            for x in res[:2]:
                show(x, it['pi'], school, AFF[school])
            if not res:
                print('   OA: no match', b.get('error', ''))
            continue
        show(w, it['pi'], school, AFF[school])


if __name__ == '__main__':
    main(sys.argv[1])
