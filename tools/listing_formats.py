"""Faculty-listing page formats: HTML -> person entries (name as listed, titles, homepage), for tools/listing_rows.py.

A format is a function html -> [dict(name_listed, titles, homepage)] registered in FORMATS with a detector. A charter
listing slot may name its format (`format = "..."`); otherwise the first detector that matches the page is used. A new
school whose pages match no format adds one function here (with a fixture test), never a school-specific script.
Contact details on the page (email, phone, office) are never returned.

formats
  eecs_table   Michigan EECS site 2016-2019 (eecs.umich.edu/eecs/faculty/{cse,ece}faculty.html): one table row per person,
               the name in a bold span inside the homepage link ('Abernethy, Jacob'), the titles as <br>-separated lines
               up to '<b>Division:</b>'
  eecs_wp      Michigan EECS WordPress 2019-2026 (cse/ece.engin.umich.edu people pages): div.eecs_person_wrapper, the
               name in <h4> ('Ackerman, Mark S.'; from 2025 <p class=eecs_person_name>), each title in span.person_title_section (several titles may share one
               span, '; '-separated), the homepage as a.person_web
"""
import html as H
import re

TAG = re.compile(r'<[^>]+>')


def clean(s):
    s = re.sub(r'<script.*?</script>', ' ', s, flags=re.S | re.I)
    return ' '.join(H.unescape(TAG.sub(' ', s)).split())


def eecs_table(h):
    out = []
    for m in re.finditer(r'<td valign="top">(.*?)</td>\s*</tr>', h, re.S | re.I):
        cell = m.group(1)
        nm = re.search(r'<span[^>]*font-weight:\s*bold[^>]*>(.*?)</span>|<a [^>]*>\s*<b>(.*?)</b>', cell, re.S | re.I)
        if not nm or 'Division:' not in cell:
            continue
        link = re.search(r'<a href="([^"]+)"[^>]*>\s*(?:<span[^>]*font-weight|<b>)', cell, re.S | re.I)
        body = cell[nm.end():cell.find('<b>Division:</b>')]
        titles = [clean(x) for x in re.split(r'<br\s*/?>', body, flags=re.I)]
        div = re.search(r'<b>Division:</b>\s*([^<]*)', cell)
        out.append(dict(name_listed=clean(nm.group(1) or nm.group(2)), titles=[t for t in titles if t], homepage=link.group(1) if link else None,
                        division=clean(div.group(1)) if div else None))
    return out


def eecs_wp(h):
    out = []
    parts = re.split(r"<div class=['\"]eecs_person_wrapper['\"][^>]*>", h)
    for p in parts[1:]:
        nm = re.search(r'<h4>(.*?)</h4>|<p class=[\'"]eecs_person_name[\'"]>(.*?)</p>', p, re.S)
        if not nm:
            continue
        titles = [clean(x) for x in re.findall(r"<span class=['\"]person_title_section['\"]>(.*?)</span>", p, re.S)]
        web = re.search(r"<a href=['\"]([^'\"]+)['\"] class=['\"]person_web", p)
        out.append(dict(name_listed=clean(nm.group(1) or nm.group(2)), titles=[t for t in titles if t], homepage=web.group(1) if web else None, division=None))
    return out


FORMATS = {
    'eecs_table': (eecs_table, re.compile(r'<b>Division:</b>', re.I)),
    'eecs_wp': (eecs_wp, re.compile(r"class=['\"]eecs_person_wrapper['\"]")),
}


def parse(h, fmt=None):
    """(format name, entries); (None, []) when no format matches."""
    if fmt:
        return fmt, FORMATS[fmt][0](h)
    for name, (fn, det) in FORMATS.items():
        if det.search(h):
            return name, fn(h)
    return None, []
