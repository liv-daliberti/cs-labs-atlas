"""A review page for hand checks (ROADMAP #36): one static HTML page per sample, a verdict box per row, verdicts exported to the JSON the rounds record.

The page is a single local file: no external script, font or image, nothing is sent anywhere. Open it in a browser, or serve it on 127.0.0.1
(`serve`). Each row shows what the checker needs: the row's facts, the verbatim quote, the capture link (a plain link to the archived page, followed
only when you click it) and, for lab-page students, the page text around the quote when the collector Python can read the stored capture.
Verdicts are kept in the browser's localStorage while you work (a convenience; the Export button is the record) and download as
`verdicts-<set>.json`.

  review_page.py labpage <school> --kind students|papers [--n 20] --seed S [--out DIR]
        the same random.sample(additions, n) under random.seed(S) that `labpage_audit.py sample` prints, as <out>/review-<school>-<kind>-<seed>.{json,html}
  review_page.py accuracy <school> [--sample lab_precision|student_precision|lab_coverage ...] [--out DIR]
        the rows of accuracy/sample[-<school>].json (the released schools share sample.json), one page per sample
  review_page.py build <review set .json> [--out FILE.html]      a page from a review set (`format: review-set/1`)
  review_page.py serve <page.html> [--port 8765]                 serve its folder on 127.0.0.1 only
  review_page.py export <verdicts.json> --round N --label TEXT [--date D] [--out DIR]
        labpage: <out>/round-<school>-<N>.json, the spec for `labpage_audit.py record` (it computes the membership score, the role/year count and the result
                 by the acceptance bar of docs/LAB-PAGES.md, scaled by sample size / 20)
        accuracy: <out>/record-<school>-<sample>.tsv, the lines `accuracy/record.py <school> <sample>` reads on stdin
Nothing here writes a data file: `export` writes into --out (default: the scratch directory), and the recording tools stay what applies a round.
"""
import argparse
import datetime
import functools
import gzip
import html
import http.server
import json
import random
import socketserver
import sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
ACC = CODE / 'accuracy'
RELEASED = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')
FAIL_TYPES = ['namesake', 'not_at_school', 'outside_appointment', 'not_a_paper', 'wrong_student', 'other', 'missing_from_build', 'student_not_linked']

CONTROLS = {
    'labpage_students': [dict(name='membership', label='Membership', options=['ok', 'error', 'doubtful']),
                         dict(name='role_year', label='Role / years', options=['ok', 'error'])],
    'labpage_papers': [dict(name='paper', label='Paper', options=['ok', 'error', 'doubtful'])],
    'accuracy_precision': [dict(name='verdict', label='Verdict', options=['correct', 'incorrect', 'unclear'])],
    'accuracy_lab_coverage': [dict(name='true_lab_paper', label='A true lab paper', options=['yes', 'no']),
                              dict(name='in_build', label='In the build', options=['yes', 'no'])],
}
# failure_type is a second box that only matters for `incorrect`; it is optional on the page and checked at export
OPTIONAL = {'accuracy_precision': [dict(name='failure_type', label='If incorrect', options=['-'] + FAIL_TYPES)]}


def short(v, n=300):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + '...'


def read_rows(path):
    p = str(path)
    s = gzip.open(p, 'rt', encoding='utf-8').read() if p.endswith('.gz') else Path(p).read_text(encoding='utf-8')
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return [json.loads(x) for x in s.splitlines() if x.strip()]


def http_links(pairs):
    return [dict(label=lab, url=u) for lab, u in pairs if u and str(u).startswith('http')]


# ---- review sets ---------------------------------------------------------------------------------------------------------------------
def labpage_set(school, kind, n, seed, rows=None, context=None):
    """The students/papers sample `labpage_audit.py sample` draws (same seed, same random.sample), as a review set."""
    if rows is None:
        rows = json.loads(Path(P.data('labpage-additions.json', school)).read_text(encoding='utf-8'))[kind]
    random.seed(seed)
    sample = random.sample(rows, min(n, len(rows)))
    out = []
    for i, r in enumerate(sample, 1):
        if kind == 'students':
            src = r.get('capture_url') or r.get('url') or ''
            out.append(dict(id=str(i), heading=f"{r['name']}  (PI {r['pi']})",
                            fields=[['role', f"{r.get('role')} ({r.get('role_basis')})"], ['years', f"{r.get('years')} ({r.get('years_basis')})"],
                                    ['alumni', r.get('alumni')], ['PI first year', r.get('pi_first_year')], ['note', r.get('note')]],
                            quote=r.get('quote') or '', context=(context(r) if context else '') or '', links=http_links([('capture', src)])))
        else:
            ev = r.get('evidence') or {}
            lp = ev.get('labpage') or {}
            out.append(dict(id=str(i), heading=f"{r.get('title')}  (PI {r['pi']})",
                            fields=[['year', r.get('year')], ['doi', r.get('doi')], ['venue', r.get('venue')], ['basis', f"{ev.get('basis')} / {ev.get('step')}"],
                                    ['appointment', ev.get('appointment')], ['byline', ', '.join(r.get('byline') or [])]],
                            quote=short(ev.get('quotes') or ev.get('school_via') or '', 700),
                            links=http_links([('evidence', ev.get('url')), ('lab page', lp.get('capture_url') or lp.get('url'))])))
    return dict(format='review-set/1', kind=f'labpage_{kind}', school=school, seed=seed, sample=kind, n=len(out),
                title=f'{school}: lab-page {kind}, seed {seed}', controls=CONTROLS[f'labpage_{kind}'], optional=[], rows=out)


def accuracy_files(school):
    return (ACC / 'sample.json', ACC / 'verdicts.jsonl') if school in RELEASED else (ACC / f'sample-{school}.json', ACC / f'verdicts-{school}.jsonl')


def accuracy_sets(school, samples=('lab_precision', 'student_precision', 'lab_coverage'), sample_file=None, lab=None, stu=None):
    """One review set per accuracy sample (docs/ADDING-A-SCHOOL.md stage 9). Rows come from the package files by the draw's row index."""
    sf = Path(sample_file) if sample_file else accuracy_files(school)[0]
    S = json.loads(sf.read_text(encoding='utf-8'))['schools'][school]
    sets = {}
    for name in samples:
        items = S.get(name) or []
        rows = []
        if name == 'lab_precision':
            L = lab if lab is not None else read_rows(P.data('lab_papers.jsonl.gz', school))
            for it in items:
                r = L[it['i']]
                a, ap = r.get('authorship') or {}, r.get('appointment') or {}
                listing = ap.get('listing') or {}
                rows.append(dict(id=str(it['i']), stratum=it.get('stratum'), key=it['key'], heading=f"{r.get('title')}  (PI {r['pi']})",
                                 fields=[['year', r.get('year')], ['venue', r.get('venue')], ['type', r.get('type')], ['byline', ', '.join(r.get('byline') or [])],
                                         ['PI as', f"{a.get('raw_name')} ({a.get('position')})"], ['affiliations', '; '.join(a.get('raw_affiliations') or [])],
                                         ['school via', short(a.get('school_via') or [], 200)], ['identity', r.get('identity')],
                                         ['appointment', f"listing {listing.get('year')}, {listing.get('kind')}" if listing else short(ap, 240)]],
                                 quote=listing.get('quote') or '',
                                 links=http_links([('paper', r.get('landing')), ('OpenAlex', r.get('oa')), ('listing capture', listing.get('url'))])))
        elif name == 'student_precision':
            T = stu if stu is not None else read_rows(P.data('student_papers.jsonl.gz', school))
            for it in items:
                r = T[it['i']]
                rs = r.get('relation_source') or {}
                rows.append(dict(id=str(it['i']), stratum=it.get('stratum'), key=it['key'], heading=f"{r.get('name')}  (advisor {r['pi']})",
                                 fields=[['status', r.get('status')], ['basis', r.get('basis')], ['byline name', r.get('byline')], ['relation', rs.get('relation')]],
                                 quote=rs.get('quote') or '', links=http_links([('paper', r.get('oa')), ('relation capture', rs.get('url'))])))
        elif name == 'lab_coverage':
            for it in items:
                d = it.get('dblp') or {}
                rows.append(dict(id=it['key'], key=it['key'], heading=f"{d.get('title') or it['key']}  (PI {it.get('pi')})",
                                 fields=[['type', d.get('type')], ['year', d.get('year')], ['venue', d.get('venue')], ['DBLP key', d.get('key')], ['dois', ', '.join(d.get('dois') or [])]],
                                 quote='', links=[]))
        else:
            continue
        kind = 'accuracy_lab_coverage' if name == 'lab_coverage' else 'accuracy_precision'
        sets[name] = dict(format='review-set/1', kind=kind, school=school, sample=name, seed=None, n=len(rows), title=f'{school}: accuracy {name}',
                          controls=CONTROLS[kind], optional=OPTIONAL.get(kind, []), rows=rows)
    return sets


# ---- the page ------------------------------------------------------------------------------------------------------------------------
CSS = '''
:root{--bg:#fff;--fg:#1c1c1c;--mut:#666;--card:#f6f6f4;--line:#d6d6d0;--acc:#1a5fb4;--ok:#1e7a3c;--q:#fffbe6}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--fg:#e6e6e6;--mut:#9a9a9a;--card:#1f1f1f;--line:#3a3a3a;--acc:#78aeed;--ok:#7bd88f;--q:#2a2610}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0}main{max-width:980px;margin:0 auto;padding:8px 16px 80px}
.row{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:14px 0;padding:12px 14px}
.row h2{font-size:15px;margin:0 0 6px}.id{color:var(--mut);font-weight:400;margin-right:8px}
dl{display:grid;grid-template-columns:max-content 1fr;gap:2px 12px;margin:6px 0}dt{color:var(--mut)}dd{margin:0;overflow-wrap:anywhere}
blockquote{margin:8px 0;padding:8px 10px;background:var(--q);border-left:3px solid var(--acc);white-space:pre-wrap;overflow-wrap:anywhere}
.ctx{color:var(--mut);font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}
.ctl{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:8px}.ctl label{color:var(--mut)}
select,input[type=text],button{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:5px;padding:3px 6px}
input[type=text]{flex:1;min-width:200px}button{cursor:pointer}.done{border-left:4px solid var(--ok)}
a{color:var(--acc)}.tag{font-size:12px;color:var(--mut);border:1px solid var(--line);border-radius:10px;padding:0 7px}
@media (max-width:600px){dl{grid-template-columns:1fr}}
'''

JS = '''
const SET = JSON.parse(document.getElementById('set').textContent);
const ALL = SET.controls.concat(SET.optional || []);
const KEY = 'review:' + SET.school + ':' + SET.sample + ':' + SET.seed;
let V = {};
try { V = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { V = {}; }
function save() { try { localStorage.setItem(KEY, JSON.stringify(V)); } catch (e) {} }
function progress() {
  let d = 0;
  SET.rows.forEach((r, k) => { const v = V[r.id] || {}; const ok = SET.controls.every(c => v[c.name]); if (ok) d++; document.getElementById('row-' + k).classList.toggle('done', ok); });
  document.getElementById('progress').textContent = d + ' of ' + SET.rows.length + ' judged';
}
function setv(id, name, val) { (V[id] = V[id] || {})[name] = val; save(); progress(); }
SET.rows.forEach((r, k) => {
  const v = V[r.id] || {};
  for (const c of ALL) { const el = document.getElementById('c-' + k + '-' + c.name); if (v[c.name]) el.value = v[c.name]; el.onchange = () => setv(r.id, c.name, el.value); }
  const note = document.getElementById('n-' + k); note.value = v.note || ''; note.oninput = () => setv(r.id, 'note', note.value);
});
document.getElementById('export').onclick = () => {
  const out = { format: 'review-verdicts/1', kind: SET.kind, school: SET.school, sample: SET.sample, seed: SET.seed, exported_at: new Date().toISOString(),
    verdicts: SET.rows.map(r => Object.assign({ id: r.id, key: r.key || null, stratum: r.stratum || null }, V[r.id] || {})) };
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' }));
  a.download = 'verdicts-' + SET.school + '-' + SET.sample + (SET.seed != null ? '-' + SET.seed : '') + '.json'; a.click();
};
document.getElementById('clear').onclick = () => { if (confirm('Forget every verdict on this page?')) { V = {}; save(); location.reload(); } };
progress();
'''


def esc(v):
    return html.escape('' if v is None else str(v))


def page(rs):
    """The static HTML of a review set. No external resource; the set travels inside the page as JSON (`</` escaped)."""
    rows = []
    for k, r in enumerate(rs['rows']):
        fields = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k, v in r.get('fields') or [] if v not in (None, '', 'None'))
        links = ' '.join(f'<a href="{esc(lk["url"])}" target="_blank" rel="noopener noreferrer">{esc(lk["label"])}</a>' for lk in r.get('links') or [])
        ctl = ''.join(f'<label>{esc(c["label"])} <select id="c-{k}-{c["name"]}"><option value="">-</option>'
                      + ''.join(f'<option>{esc(o)}</option>' for o in c['options']) + '</select></label>' for c in rs['controls'] + (rs.get('optional') or []))
        rows.append(f'<section class="row" id="row-{k}"><h2><span class="id">[{esc(r["id"])}]</span>{esc(r["heading"])}'
                    + (f' <span class="tag">{esc(r["stratum"])}</span>' if r.get('stratum') else '') + '</h2>'
                    f'<dl>{fields}</dl>' + (f'<blockquote>{esc(r["quote"])}</blockquote>' if r.get('quote') else '')
                    + (f'<div class="ctx">{esc(r["context"])}</div>' if r.get('context') else '')
                    + (f'<div>{links}</div>' if links else '')
                    + f'<div class="ctl">{ctl}<input type="text" id="n-{k}" placeholder="reason / note"></div></section>')
    data = json.dumps(rs, ensure_ascii=False).replace('</', '<\\/')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Review: {esc(rs["school"])} {esc(rs["sample"])}</title><style>{CSS}</style></head><body>'
            f'<header><h1>{esc(rs["title"])}</h1><span id="progress"></span><button id="export">Export verdicts</button><button id="clear">Clear</button></header>'
            f'<main>{"".join(rows)}</main><script type="application/json" id="set">{data}</script><script>{JS}</script></body></html>')


# ---- export --------------------------------------------------------------------------------------------------------------------------
def labpage_spec(v, round_, label, date=None):
    """The round spec `labpage_audit.py record` reads (docs/LAB-PAGES.md, acceptance bar; the bar scales with sample size / 20)."""
    rows = v['verdicts']
    unjudged = [r['id'] for r in rows if not all(r.get(c['name']) for c in CONTROLS[v['kind']])]
    if unjudged:
        raise SystemExit('unjudged rows: ' + ', '.join(unjudged))
    scale = max(1.0, len(rows) / 20)

    def desc(r):
        return f"{r['id']}: {r.get('note') or ''}".strip()
    spec = dict(school=v['school'], round=round_, label=label, date=date or datetime.date.today().isoformat())
    if v['kind'] == 'labpage_students':
        mem = [desc(r) for r in rows if r['membership'] == 'error']
        dbt = [desc(r) for r in rows if r['membership'] == 'doubtful']
        ry = [desc(r) for r in rows if r['role_year'] == 'error']
        score = len(mem) + 0.5 * len(dbt)
        spec.update(students=dict(sampled=len(rows), seed=v['seed'], membership_errors=len(mem), doubtful_count=len(dbt), role_or_year_errors=len(ry),
                                  items=dict(membership=mem, doubtful=dbt, role_or_year=ry)),
                    membership_score=score, role_year_errors=len(ry), result='pass' if score <= scale and len(ry) <= 2 * scale else 'fail')
    else:
        err = [desc(r) for r in rows if r['paper'] == 'error']
        dbt = [desc(r) for r in rows if r['paper'] == 'doubtful']
        score = len(err) + 0.5 * len(dbt)
        spec.update(papers=dict(sampled=len(rows), seed=v['seed'], errors=len(err), doubtful_count=len(dbt), metadata_errors=0, items=dict(papers=err, doubtful=dbt)),
                    paper_score=score, result='pass' if score <= scale else 'fail')
    return spec


def accuracy_tsv(v):
    """Lines for accuracy/record.py: <ref> <verdict> <failure_type or -> <reason> [<evidence>] [<extra JSON>]; <ref> is the row index or the item key."""
    lines = []
    for r in v['verdicts']:
        note = (r.get('note') or '-').replace('\t', ' ').replace('\n', ' ')
        if v['sample'] == 'lab_coverage':
            if not (r.get('true_lab_paper') and r.get('in_build')):
                raise SystemExit(f"unjudged row {r['id']}")
            truth, built = r['true_lab_paper'] == 'yes', r['in_build'] == 'yes'
            verdict = 'correct' if truth == built else 'incorrect'
            lines.append('\t'.join([r['id'], verdict, '-' if verdict == 'correct' else 'missing_from_build', note, '', json.dumps(dict(true_lab_paper=truth, in_build=built))]))
        else:
            if not r.get('verdict'):
                raise SystemExit(f"unjudged row {r['id']}")
            ft = r.get('failure_type') or '-'
            if r['verdict'] == 'incorrect' and ft == '-':
                raise SystemExit(f"row {r['id']}: incorrect needs a failure type")
            lines.append('\t'.join([r['id'], r['verdict'], ft if r['verdict'] == 'incorrect' else '-', note]))
    return '\n'.join(lines) + '\n'


# ---- serve ---------------------------------------------------------------------------------------------------------------------------
def serve(path, port=8765):
    """Serve the page's folder on 127.0.0.1 only (a file:// page works as well; this is for browsers that block localStorage on file URLs)."""
    path = Path(path).resolve()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(path.parent))
    with socketserver.TCPServer(('127.0.0.1', port), handler) as httpd:
        print(f'http://127.0.0.1:{port}/{path.name}   (Ctrl-C to stop)', flush=True)
        httpd.serve_forever()


def scratch_dir():
    d = Path(P.SCRATCH) / 'review-pages'
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_set(rs, out):
    stem = f"review-{rs['school']}-{rs['sample']}" + (f"-{rs['seed']}" if rs.get('seed') is not None else '')
    (out / f'{stem}.json').write_text(json.dumps(rs, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / f'{stem}.html').write_text(page(rs), encoding='utf-8')
    print(out / f'{stem}.html')


def page_context(school):
    """The page text around a student's quote, from the stored capture (collector Python only); None when it cannot be read."""
    try:
        import labpage_audit as LA
        kit = LA.Kit(school)
    except Exception:  # noqa: BLE001 - the page is useful without it
        return None

    def ctx(r):
        try:
            t = kit.lpev.text(school, r.get('capture_url') or r['sha256'])
        except Exception:  # noqa: BLE001
            return ''
        j = t.find(r['quote'])
        return t[max(0, j - 220): j + len(r['quote']) + 220].replace('\n', ' ') if j >= 0 else '(quote not found in the stored capture)'
    return ctx


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('labpage'); s.add_argument('school'); s.add_argument('--kind', choices=['students', 'papers'], default='students')
    s.add_argument('--n', type=int, default=20); s.add_argument('--seed', type=int, required=True); s.add_argument('--out')
    s = sub.add_parser('accuracy'); s.add_argument('school'); s.add_argument('--sample', nargs='*'); s.add_argument('--out')
    s = sub.add_parser('build'); s.add_argument('set'); s.add_argument('--out')
    s = sub.add_parser('serve'); s.add_argument('page'); s.add_argument('--port', type=int, default=8765)
    s = sub.add_parser('export'); s.add_argument('verdicts'); s.add_argument('--round'); s.add_argument('--label', default=''); s.add_argument('--date'); s.add_argument('--out')
    a = ap.parse_args(argv)
    if a.cmd in ('labpage', 'accuracy', 'export') and a.out:
        Path(a.out).mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if getattr(a, 'out', None) else (scratch_dir() if a.cmd in ('labpage', 'accuracy', 'export') else None)
    if a.cmd == 'labpage':
        write_set(labpage_set(a.school, a.kind, a.n, a.seed, context=page_context(a.school) if a.kind == 'students' else None), out)
    elif a.cmd == 'accuracy':
        for rs in accuracy_sets(a.school, tuple(a.sample or ('lab_precision', 'student_precision', 'lab_coverage'))).values():
            write_set(rs, out)
    elif a.cmd == 'build':
        rs = json.loads(Path(a.set).read_text(encoding='utf-8'))
        dest = Path(a.out) if a.out else Path(a.set).with_suffix('.html')
        dest.write_text(page(rs), encoding='utf-8')
        print(dest)
    elif a.cmd == 'serve':
        serve(a.page, a.port)
    elif a.cmd == 'export':
        v = json.loads(Path(a.verdicts).read_text(encoding='utf-8'))
        if v['kind'].startswith('labpage'):
            if not a.round:
                ap.error('--round is required for a lab-page round')
            spec = labpage_spec(v, a.round, a.label, a.date)
            f = out / f"round-{v['school']}-{a.round}.json"
            f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
            print(f, '->', spec['result'])
            print(f'record it: labpage_audit.py record {f}   (add `acceptance` to the spec when this round decides the wiring)')
        else:
            f = out / f"record-{v['school']}-{v['sample']}.tsv"
            f.write_text(accuracy_tsv(v), encoding='utf-8')
            print(f'{f}\nrecord it: accuracy/record.py {v["school"]} {v["sample"]} < {f}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
