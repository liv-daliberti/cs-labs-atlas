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
  uc_cs_table  UChicago CS Drupal site 2016-2018 (www.cs.uchicago.edu/directories/table/{faculty,Other-Academic-Appointments}): tr.odd/even, name in
               the first cell, the titles as <br>-separated lines of the second up to 'Research Interests:', the homepage as the 'Personal website' link
  uc_people_li UChicago CS 2018-2022 (people/faculty/) and Statistics 2019- (stat.uchicago.edu/people/): li.mix, the class tokens name the group
               (only 'faculty'-bearing tokens are kept: Statistics lists students, staff and visitors on the same page), name in h3 (a link or
               span), title in <small> or <b>, the department profile as `profile`
  uc_card      UChicago CS WordPress 2022- (people/uchicago-faculty/...): div.card--person, h3.card__title, div.card__position, a.card__url (profile)
  galton_cells Statistics 2016-2019 (galton.uchicago.edu/people/faculty.shtml, emeriti.shtml): table cells with <a href="/faculty/x.shtml"><strong>Name</strong></a>,
               then a span with a script-written email (dropped), 'Office: ...' (dropped) and the title lines
  ttic_media   TTIC 2017- (www.ttic.edu/faculty/): div.media-body, h2.media-heading name, h3 title(s), the 'Home Page' link
  ttic_table   TTIC 2016-2017 (www.ttic.edu/faculty.php): <td><strong>Name</strong>, Title<br />, the 'Home Page' link
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
        # the name opens the cell, in a bold span or <b>, inside the homepage link or (no homepage) bare (2018 'Meerkov')
        nm = re.match(r'\s*(?:<a [^>]*>\s*)?(?:<span[^>]*font-weight:\s*bold[^>]*>(.*?)</span>|<b>(.*?)</b>)', cell, re.S | re.I)
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


def _ln(h):
    return [clean(x).strip(' ,') for x in re.split(r'<br\s*/?>', h, flags=re.I) if clean(x).strip(' ,')]


def uc_cs_table(h):
    out = []
    for m in re.finditer(r'<tr class="(?:odd|even)[^"]*">(.*?)</tr>', h, re.S | re.I):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', m.group(1), re.S | re.I)
        if len(tds) < 2 or not clean(tds[0]):
            continue
        titles = []
        for t in _ln(tds[1]):
            if t.lower().startswith('research interests'):
                break
            titles.append(t.rstrip(' ,'))
        web = re.search(r'<a href="([^"]+)"[^>]*>\s*Personal website', ''.join(tds[2:]), re.I)
        out.append(dict(name_listed=clean(tds[0]), titles=[t for t in titles if t], homepage=web.group(1) if web else None, division=None))
    return out


def uc_people_li(h):
    out = []
    for m in re.finditer(r'<li class="mix ([^"]*)">(.*?)</li>', h, re.S | re.I):
        toks, body = m.group(1).split(), m.group(2)
        if not any('faculty' in t for t in toks):
            continue
        hh = re.search(r'<h3[^>]*>(.*?)</h3>', body, re.S | re.I)
        if not hh:
            continue
        nm = re.search(r'<(?:a|span)[^>]*>(.*?)</(?:a|span)>', hh.group(1), re.S | re.I)
        tl = re.search(r'<(?:small|b)>(.*?)</(?:small|b)>', hh.group(1), re.S | re.I)
        prof = re.search(r'<a href="([^"]*/people/profile/[^"]*)"', body, re.I)
        if nm and clean(nm.group(1)):
            out.append(dict(name_listed=clean(nm.group(1)), titles=_ln(tl.group(1)) if tl else [], homepage=None, division=None,
                            profile=prof.group(1) if prof else None, groups=toks))
    return out


def uc_card(h):
    out = []
    for p in re.split(r'<div class="card card--person[^"]*"[^>]*>', h)[1:]:
        nm = re.search(r'<h3 class="card__title">(.*?)</h3>', p, re.S)
        if not nm:
            continue
        pos = re.search(r'<div class="card__position">(.*?)</div>', p, re.S)
        url = re.search(r'<a class="card__url" href="([^"]+)"', p)
        out.append(dict(name_listed=clean(nm.group(1)), titles=_ln(pos.group(1)) if pos else [], homepage=None, division=None, profile=url.group(1) if url else None))
    return out


def ttic_media(h):
    out = []
    for p in re.split(r'<div class="media-body">', h)[1:]:
        nm = re.search(r'<h2 class="media-heading">(.*?)</h2>', p, re.S)
        if not nm:
            continue
        head = p[:p.find('</div>')] if '</div>' in p else p
        web = re.search(r'<a href="([^"]+)"[^>]*>\s*Home Page', head, re.I)
        out.append(dict(name_listed=clean(nm.group(1)), titles=[clean(t) for t in re.findall(r'<h3[^>]*>(.*?)</h3>', head, re.S) if clean(t)],
                        homepage=web.group(1) if web else None, division=None))
    return out


def ttic_table(h):
    out = []
    for m in re.finditer(r'<td><strong>(.*?)</strong>,?\s*(.*?)<br\s*/?>(.*?)</td>', h, re.S | re.I):
        web = re.search(r'<a href="([^"]+)"[^>]*>\s*Home Page', m.group(3), re.I)
        out.append(dict(name_listed=clean(m.group(1)), titles=[clean(m.group(2))] if clean(m.group(2)) else [], homepage=web.group(1) if web else None, division=None))
    return out


def galton_cells(h):
    out = []
    for m in re.finditer(r'<strong>((?:(?!</strong>).)*)</strong>(?:</a>)?\s*<br\s*/?>\s*<span class="text">(.*?)</span>\s*</td>', h, re.S | re.I):
        body = re.sub(r'<script.*?</script>', ' ', m.group(2), flags=re.S | re.I)
        titles = [t for t in _ln(body) if not re.match(r'(?:office|phone|fax)\b', t, re.I)]
        out.append(dict(name_listed=clean(m.group(1)), titles=titles, homepage=None, division=None))
    return out


FORMATS = {
    'eecs_table': (eecs_table, re.compile(r'<b>Division:</b>', re.I)),
    'eecs_wp': (eecs_wp, re.compile(r"class=['\"]eecs_person_wrapper['\"]")),
    'uc_cs_table': (uc_cs_table, re.compile(r'<tr class="(?:odd|even)[^"]*">.*?(?:Personal website|Research Interests)', re.S)),
    'uc_people_li': (uc_people_li, re.compile(r'<li class="mix ')),
    'uc_card': (uc_card, re.compile(r'card card--person')),
    'galton_cells': (galton_cells, re.compile(r'</strong>(?:</a>)?\s*<br\s*/?>\s*<span class="text">')),
    'ttic_media': (ttic_media, re.compile(r'class="media-heading"')),
    'ttic_table': (ttic_table, re.compile(r'<td><strong>')),
}


def parse(h, fmt=None):
    """(format name, entries); (None, []) when no format matches."""
    if fmt:
        return fmt, FORMATS[fmt][0](h)
    for name, (fn, det) in FORMATS.items():
        if det.search(h):
            return name, fn(h)
    return None, []
