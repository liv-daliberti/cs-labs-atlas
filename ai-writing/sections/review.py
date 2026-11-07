"""Review view of a pilot: per paper the splitter's cut points and every heading-like line that could be an appendix/refs boundary.
usage: review.py SAMPLE.json OUTDIR FROM TO"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
import atlas_paths as P  # noqa: E402
import fulltext_sections as S  # noqa: E402
rows = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); lo, hi = int(sys.argv[3]), int(sys.argv[4])
res = {}
for l in open(out / 'res.jsonl'):
    r = json.loads(l); res[r['i']] = r
KEY = re.compile(r'appendi|supplement|online (?:material|resource)|^\s*[A-Z][.:]?\s+[A-Z]|^\s*[A-Z]\.\d|proof|additional (?:result|experiment|detail)|^\s*(?:references|bibliography|acknowledg|conclusion)', re.I)
for i in range(lo, min(hi, len(rows))):
    r, x = rows[i], res[i]
    p = P.STORES / r['path']
    if 'error' in x:
        print(f"[{i}] {r['school']} {r['kind']} {r['year']} ERROR {x['error']}"); continue
    f = x['flags']
    if r['kind'] == 'pdf':
        t, _ = S.read_pdf(p)
    else:
        t = S._xml_text(p.read_text('utf-8', 'ignore'))
    t = S.clean(t)
    print(f"[{i}] {r['school']} {r['kind']} {r['year']} pg={f.get('pages')} app={f['appendix_found']}/{f['appendix_position']}/{f['appendix_rule']} refs={f['refs_found']} intro={f['intro_found']} words main/app={f['main_words']}/{f['appendix_words']} trunc={f['truncated']}")
    if x['appendix']:
        print('   APPX starts:', x['appendix'][:110])
    print('   MAIN ends  :', x['main'][-90:])
    n = 0
    for m in re.finditer(r'^[^\n]{2,90}$', t, re.M):
        ln = m.group(0)
        if m.start() > len(t) * 0.35 and (re.match(r'^\s*(?:APPENDI|Appendi|SUPPLEMENT|Supplement|REFERENCES|References|BIBLIOGRAPHY|Bibliography)', ln) or re.match(r'^\s*[A-Z][.:]?\s+[A-Z][a-z]', ln) and len(ln.split()) < 10 and "," not in ln and not ln.rstrip().endswith(("-", "–")) or re.match(r'^\s*[A-Z]\.\d', ln)):
            print(f"      {m.start()*100//len(t):3d}% {ln.strip()[:80]}"); n += 1
            if n > 6: break
