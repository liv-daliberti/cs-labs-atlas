"""Yearly listing rows for the CS-related additions (2026-10-22), built with the listings pipeline's own extractor and
matcher (listings/scripts: extract.blocks, match.find_pi/classify, build.region_bounds/page_flags/future_start,
profiles.STRICT_TITLE) so the rows have the same form as listings/cmu/listings.json.

Sources: (a) captures already in listings/cmu/captures.sqlite (department listings the listings sweep planned: ECE,
MechE, Chemistry, Philosophy home-department lists, and SCS affiliated/core lists that quote a person's home title);
(b) department listings captured for this review into hierarchy/cmu/cs-related-captures.sqlite (table plan_csr).
Every row's quote is checked to be a substring of the capture's extracted text before it is kept.
usage: listing_rows.py > rows.json
"""
import collections, importlib, json, re, sqlite3, sys, zlib
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'listings/scripts'))
import extract, match, build, profiles  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent))
from people import P  # noqa: E402

cfg = importlib.import_module('config_cmu')
SLOTS = {s['slot']: s for s in cfg.SLOTS}
USE = ['ECE faculty (home department)', 'ECE courtesy faculty (home department)', 'ECE adjunct faculty (home department)',
       'MechE faculty (home department)', 'Chemistry faculty (home department)', 'Philosophy faculty (home department)',
       'MLD core faculty', 'MLD affiliated faculty', 'MLD adjunct faculty', 'CBD affiliated faculty', 'CBD voting faculty',
       'HCII affiliated faculty', 'HCII faculty', 'RI affiliated faculty', 'RI faculty', 'S3D/ISR affiliated faculty',
       'S3D/ISR faculty index', 'S3D/ISR core faculty', 'LTI affiliated faculty', 'LTI faculty', 'CSD faculty']
pis = [dict(pi=n, aliases=al, departments=[d]) for n, d, _, al in P]
# strict listings: profiles.STRICT_TITLE, plus department-head / dean titles ('Associate Department Head for Research')
FAC_TITLE = re.compile(profiles.STRICT_TITLE.pattern + r'|\b(Department Head|Head|Dean|University Professor)\b', re.I)
NONFAC = re.compile(r'Student|Post-?doc|Postdoctoral|Scientist|Staff|Research Associate|Visiting Scholar|Engineer\b', re.I)
CUT = re.compile(r'\s(Read full bio|Read More|Keywords|Email|Phone|Full Profile|Profile Page|Contact|Office)\b|\S+@|\(?\d{3}\)?[\s.-]\d{3}[.-]\d{4}|\+\d')


def name_rx(name):
    t = [x for x in re.sub(r'\([^)]*\)', ' ', name).replace(',', ' ').split() if x]
    if len(t) < 2:
        return None
    first, last = re.escape(t[0].rstrip('.')), re.escape(t[-1])
    return re.compile(r'(?<![\w-])(?:' + last + r'\s*,\s*' + first + r'(?:\s+[A-Z]\.?)?' + r'|' + first + r'(?:\s+[A-Z][\w.\-]*){0,2}\s+' + last + r'(?![\w-]))')


def fallback(text, pi_name, names):
    """Name + title cut straight from the collapsed text, for entries the block matcher misses (names glued to titles
    such as 'Blanton , ShawnProfessor – ECE', or 'Last , First' with initials)."""
    out = []
    for n in names:
        rx = name_rx(n)
        if not rx:
            continue
        for m in rx.finditer(text):
            rest = text[m.end():m.end() + 160]
            c = CUT.search(rest)
            title = rest[:c.start()] if c else rest[:110]
            title = title.strip(' ,;:|-–—')
            if not title or not FAC_TITLE.search(title) or NONFAC.search(title):
                continue
            q = text[m.start():m.end() + len(rest[:c.start()] if c else rest[:110])].strip()
            out.append(dict(name_as_written=m.group(0), quote=q, title=title))
            break
        if out:
            break
    return out
ms = match.matchers(pis)
idx = match.Index(ms)


def rows_for(blocks, slot, slot_name, dept, cap, orig, wts, sha, half):
    out, rej = [], []
    lo, hi, has_region = build.region_bounds(blocks, slot, orig)
    flags = build.page_flags(blocks, slot)
    text = extract.collapse("\n".join(t for _, t in blocks))
    observed = f"{wts[:4]}-{wts[4:6]}-{wts[6:8]}"
    bm = match.all_block_matches(blocks, idx, split_cells=bool(slot.get('split_name_cells')))
    for mi in sorted({x for d in bm for x in d}):
        pi = pis[mi]
        for hit in match.find_pi(blocks, bm, mi):
            if has_region and not (lo <= hit['block_index'] < hi):
                continue
            if slot.get('quote_require') and not re.search(slot['quote_require'], hit['quote']):
                continue
            if hit['match_basis'] == 'initials':
                others = [x for x in build.ambiguous_initials(text, hit) if match.norm(x) != match.norm(hit['name_as_written'])]
                if others:
                    rej.append((pi['pi'], slot_name, observed, 'ambiguous initials', hit['quote'])); continue
            ok, why, emer, visit = match.classify(hit, slot, flags, slot.get('untitled_ok', False) if has_region else False)
            if ok and (slot.get('listing_label') or slot.get('strict_title') or slot.get('strict')) and not FAC_TITLE.search(' | '.join(hit['title_lines'])):
                ok, why = False, 'entry without a faculty title (strict listing)'
            if not ok:
                rej.append((pi['pi'], slot_name, observed, why, hit['quote'])); continue
            r = dict(pi=pi['pi'], department=dept, page_url=orig, capture_url=cap, wayback_timestamp=wts, observed_on=observed,
                     year=int(wts[:4]), sha256=sha, quote=hit['quote'], rank_as_listed=hit['title_lines'][0] if hit['title_lines'] else None,
                     section_heading=hit['section_heading'], name_as_written=hit['name_as_written'], emeritus=emer, visiting=visit,
                     future_start_note=build.future_start(hit['quote'], observed), outside_pi_departments=dept != pi['departments'][0],
                     listing=slot.get('listing_label') or slot_name, half=half, match_basis=hit['match_basis'])
            if slot.get('listing_label'):
                r['listing_source'] = slot_name
            out.append((r, text))
    got = {r['pi'] for r, _ in out}
    for pi in pis:
        if pi['pi'] in got:
            continue
        for f in fallback(text, pi['pi'], [pi['pi']] + list(pi['aliases'])):
            r = dict(pi=pi['pi'], department=dept, page_url=orig, capture_url=cap, wayback_timestamp=wts, observed_on=observed,
                     year=int(wts[:4]), sha256=sha, quote=f['quote'], rank_as_listed=f['title'], section_heading=None,
                     name_as_written=f['name_as_written'], emeritus=bool(re.search(r'emerit|retired', f['title'], re.I)),
                     visiting=bool(re.search(r'\bvisiting\b', f['title'], re.I)), future_start_note=build.future_start(f['quote'], observed),
                     outside_pi_departments=dept != pi['departments'][0], listing=slot.get('listing_label') or slot_name, half=half,
                     match_basis='text_fallback')
            if slot.get('listing_label'):
                r['listing_source'] = slot_name
            out.append((r, text))
    return out, rej


def from_listings_store():
    con = sqlite3.connect(f"file:{HERE}/listings/cmu/captures.sqlite?mode=ro", uri=True)
    plan = con.execute("select slot, dept, year, half, page_url, capture_url, wayback_timestamp, status from plan where status='ok' order by dept, slot, year, half").fetchall()
    for slot_name, dept, year, half, page_url, cap, ts, status in plan:
        if slot_name not in USE:
            continue
        final_url, sha, raw, ct = con.execute("select final_url, sha256, raw_zlib, content_type from captures where capture_url=?", (cap,)).fetchone()
        m = re.match(r"https://web\.archive\.org/web/(\d{14})id_/(.*)$", final_url or cap)
        wts, orig = (m.group(1), m.group(2)) if m else (ts, page_url)
        blocks = extract.blocks(zlib.decompress(raw), ct, cap)
        rows, rej = rows_for(blocks, SLOTS[slot_name], slot_name, dept, f"https://web.archive.org/web/{wts}id_/{orig}", orig, wts, sha, half)
        for r, text in rows:
            r['capture_store'] = 'listings/cmu/captures.sqlite'
        yield rows, rej


def from_csr_store():
    con = sqlite3.connect(f"file:{HERE}/hierarchy/cmu/cs-related-captures.sqlite?mode=ro", uri=True)
    try:
        plan = con.execute("select slot, dept, year, half, page_url, capture_url, wayback_timestamp, slot_json from plan_csr where status='ok'").fetchall()
    except sqlite3.OperationalError:
        return
    for slot_name, dept, year, half, page_url, cap, wts, slot_json in plan:
        row = con.execute("select sha256, content, content_type from captures where (capture_url=? or url=?) and status=200 and error is null order by id desc limit 1", (cap, cap)).fetchone()
        if not row:
            continue
        sha, raw, ct = row
        blocks = extract.blocks(zlib.decompress(raw), ct, cap)
        slot = json.loads(slot_json)
        rows, rej = rows_for(blocks, slot, slot_name, dept, cap, page_url, wts, sha, half)
        for r, text in rows:
            r['capture_store'] = 'hierarchy/cmu/cs-related-captures.sqlite'
        yield rows, rej


if __name__ == '__main__':
    allrows, allrej = [], []
    for rows, rej in list(from_listings_store()) + list(from_csr_store() or []):
        for r, text in rows:
            if r['quote'] not in text:
                allrej.append((r['pi'], r['listing'], r['observed_on'], 'quote not in extracted text', r['quote'])); continue
            allrows.append(r)
        allrej += rej
    seen, out = set(), []
    for r in allrows:
        k = (r['pi'], r['capture_url'], r['quote'], r['section_heading'])
        if k not in seen:
            seen.add(k); out.append(r)
    out.sort(key=lambda r: (r['pi'], r['department'], r['observed_on'], r['listing']))
    json.dump(dict(rows=out, rejected=allrej), sys.stdout, indent=1, ensure_ascii=False)
