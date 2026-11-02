#!/usr/bin/env python3
"""The site is two pages (owner decision 2026-10-22): atlas/index.html (the CS atlas) and
atlas/cs-departments.html, with the scripts, styles and data they use. Checks that

  * those are the only pages under atlas/, and every script or stylesheet there is one a page loads;
  * every link on the two pages resolves to a file that exists: each href/src in their HTML (a download
    through data.json `downloads`, as app.js rewrites it), each page or data path written literally in the
    scripts they load, and the links the pages build at run time: the atlas's "Open in CS departments"
    links (school, department and lab exist in atlas/data/cs-hierarchy) and cs-departments.js's
    "Open in the CS atlas" links (the university loads that PI lab from its data/cs-pi-labs file);
  * every data.json asset and download exists, every shown lab's papers file is a registered asset and
    its people file exists, and atlas-source/manifest.json lists only existing files with their bytes.

    python3 scripts/test-site-pages.py
"""
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
A = R / 'atlas'
PAGES = ('index.html', 'cs-departments.html')
fails = []


def check(ok, *what):
    if not ok:
        fails.append(what)


def read(rel):
    raw = (A / rel).read_bytes()
    return json.loads(gzip.decompress(raw) if rel.endswith('.gz') else raw)


# Every file under atlas/, from directory listings (no per-file metadata calls).
files = set()
for root, dirs, names in os.walk(A):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    files.update(str((Path(root) / n).relative_to(A)) for n in names if not n.startswith('.'))
I = read('data.json')

# Only the two pages; every script and stylesheet is loaded by one of them.
pages = sorted(f for f in files if f.endswith(('.html', '.htm')))
check(pages == sorted(PAGES), 'pages under atlas/', pages)
loaded, html = set(), {}
for page in PAGES:
    html[page] = (A / page).read_text()
    for ref in re.findall(r'<(?:script|link)[^>]*(?:src|href)="([^"]+)"', html[page]):
        loaded.add(ref)
code = sorted(f for f in files if f.endswith(('.js', '.css')))
check(set(code) == loaded, 'scripts/styles not loaded by a kept page, or missing', sorted(set(code) ^ loaded))

# Static links in the two pages.
links = 0
for page in PAGES:
    for ref in re.findall(r'(?:href|src)="([^"]*)"', html[page]):
        ref = ref.replace('&amp;', '&')
        links += 1
        if re.match(r'^(https?:)?//', ref) or ref.startswith('mailto:'):
            continue
        path = ref.split('#')[0].split('?')[0]
        if path in ('', './', '.'):
            continue  # this page, with a query
        if path.startswith('downloads/'):
            name = path[len('downloads/'):]
            mapped = I['downloads'].get(name) or I['downloads'].get(re.sub(r'\.gz$', '', name))
            check(path in files or ('downloads/' + mapped) in files if mapped else path in files, page, 'download link', ref)
            if mapped:
                check('downloads/' + mapped in files, page, 'download mapping', name, mapped)
            continue
        check(path in files, page, 'link', ref)

# Pages and data paths written literally in the scripts the pages load.
for script in sorted(f for f in loaded if f.endswith('.js')):
    text = (A / script).read_text()
    if script == 'assets/d3.min.js':
        continue  # the library's own strings (t.html, t.json) are not links
    for target in re.findall(r'[A-Za-z0-9_-]+\.html', text):
        check(target in PAGES, script, 'names a removed page', target)
    for target in re.findall(r"""['"]((?:data|downloads|papers)/[A-Za-z0-9_./-]+\.(?:json|gz|csv|pdf))['"]""", text):
        check(target in files, script, 'data path', target)
    links += 1

# Run-time links. Atlas -> CS departments: school, department and lab of every PI lab the atlas shows.
index = json.loads((A / 'data/cs-hierarchy/index.json').read_text())
schools = {s['id']: s for s in index['schools']}
for u in I['universities']:
    block = u['csScope']
    if 'labsFile' not in block:
        continue
    check(block['school'] in schools and block['labsFile'] in files, u['id'], 'PI labs file / school')
    H = read(f"data/cs-hierarchy/{block['school']}.json.gz")
    depts, ids = {d['name'] for d in H['departments']}, {l['id'] for l in H['labs']}
    for lab in read(block['labsFile'])['labs']:
        links += 1
        check(lab['hierarchy']['id'] in ids and lab['department'] in depts, u['id'], 'cs-departments link', lab['id'])
    # CS departments -> atlas: ./?university=<uni>&lab=<hierarchy id> opens that lab or explains why it is hidden.
    atlas_labs = {r['hierarchy']['id'] for r in read(block['labsFile'])['labs']}
    for lab in H['labs']:
        links += 1
        check(lab['id'] in atlas_labs, u['id'], 'atlas link from cs-departments', lab['id'])
check(set(schools) == {u['csScope'].get('school') for u in I['universities']} - {None}, 'every CS departments school is in the atlas')
check('&amp;lab=' in (A / 'cs-departments.js').read_text() and 'cs-departments.html?school=' in (A / 'app.js').read_text(), 'cross-page links')

# Data the atlas loads: every asset and download exists; shown labs' files are reachable.
missing = [a for a in I['assets'] if a not in files]
check(not missing, 'data.json assets missing', missing[:10])
check(all('downloads/' + v in files for v in I['downloads'].values()), 'data.json downloads missing')
for rel in [x for x in I['assets'] if not x.startswith(('data/labs/', 'data/lab-people/', 'data/universities/'))]:
    check(hashlib.sha256((A / rel).read_bytes()).hexdigest() == I['assets'][rel], 'asset digest', rel)
for u in I['universities']:
    if 'labsFile' in u['csScope']:
        continue
    for lab in read(u['labsFile'])['labs']:
        if lab.get('csShown'):
            check(not lab.get('papersFile') or lab['papersFile'] in I['assets'], u['id'], 'papers file not registered', lab['id'])
            check(not lab.get('peopleFile') or lab['peopleFile'] in files, u['id'], 'people file missing', lab['id'])

# The chunked source manifest lists existing files only.
manifest = json.loads((R / 'atlas-source/manifest.json').read_text())
for name, entry in manifest['files'].items():
    check(name in files and (A / name).stat().st_size == entry['size'], 'atlas-source manifest', name)
    check(all((R / 'atlas-source/chunks' / c['sha256']).exists() for c in entry['chunks']), 'chunk missing', name)

print(json.dumps(dict(passed=not fails, pages=pages, scriptsAndStyles=len(code), files=len(files), linksChecked=links,
                      assets=len(I['assets']), downloads=len(I['downloads']), failures=len(fails), first=fails[:10]), indent=1))
sys.exit(1 if fails else 0)
