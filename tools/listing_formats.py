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
  gt_people    Georgia Tech College of Computing Drupal 7 sites 2016-2023 (scs/ic/cse.gatech.edu people/faculty): div.gt-person-box, name in h4.name.fn, the
               titles ';'-separated in div.gt-people-content up to the first <br> (Research Areas and the e-mail link are dropped). 2016 captures are page 1 of 4
  gt_card      Georgia Tech Drupal 9 sites 2023- (scs/ic/cse/scp, ECE-style profile-card): h4.card-block__title name, h6.card-block__subtitle title(s). IC and CSE
               list everyone on one page; SCS and SCP page it 12 per page (?page=N), so a capture is partial there
  ece_old      Georgia Tech ECE 2016-2023-03 (www.ece.gatech.edu/faculty-staff-directory): div.field-full-name link, div.field-jobtitle
  ece_new      Georgia Tech ECE 2023-04- (ece.gatech.edu/directory): field-person-name item and field-person-official-job-title item; paged (partial)
  isye_old     Georgia Tech ISyE 2016-2023 (www.isye.gatech.edu/people): h4.name link, div.field-content under field-emp-title; every category of person
  isye_card    Georgia Tech ISyE 2023- (www.isye.gatech.edu/people/faculty): div.person-name link, div.person-type
  wu_teaser    WashU McKelvey School of Engineering sites 2023/24- (cse/ese/bme.washu.edu/faculty-research/directory.html): article.faculty-directory__teaser,
               h3.faculty-directory__teaser-name, p.faculty-directory__teaser-title, the profile on engineering.washu.edu as the link (data-shortdept names the department)
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


def _titles(t):
    """Title lines of a cell: split on <br> first, then on ';' of the decoded text ('Regents&#039; Professor' holds an entity ';'); the 'E-Mail' link text is dropped."""
    out = []
    for part in re.split(r'<br\s*/?>', t, flags=re.I):
        for x in clean(part).split(';'):
            x = re.sub(r'\s*\bE-?mail\b\s*$', '', x.strip(), flags=re.I)
            if x:
                out.append(x)
    return out


def gt_people(h):
    out = []
    for p in re.split(r'<div class="gt-person-box', h)[1:]:
        nm = re.search(r"<h4 class=['\"]name fn['\"]>(.*?)</h4>", p, re.S)
        if not nm:
            continue
        body = re.search(r"<div class=['\"]gt-people-content[^'\"]*['\"]>(.*?)</div>", p, re.S)
        first = re.split(r'<br\s*/?>|<strong>', body.group(1), maxsplit=1, flags=re.I)[0] if body else ''
        link = re.search(r'href="([^"]+)"', nm.group(1))
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(first), homepage=link.group(1) if link else None, division=None))
    return out


def gt_card(h):
    out = []
    for p in re.split(r'<div class="row profile-card__content', h)[1:]:
        nm = re.search(r'<h4 class="card-block__title">(.*?)</h4>', p, re.S)
        if not nm:
            continue
        sub = re.search(r'<h6 class="card-block__subtitle[^"]*">(.*?)</h6>', p, re.S)
        link = re.search(r'href="([^"]+)"', nm.group(1))
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(sub.group(1)) if sub else [], homepage=link.group(1) if link else None, division=None))
    return out


def ece_old(h):
    out = []
    for p in re.split(r'<div class="faculty-staff-information">', h)[1:]:
        nm = re.search(r'<div class="field-full-name">(.*?)</div>', p, re.S)
        if not nm:
            continue
        jt = re.search(r'<div class="field-jobtitle">(.*?)</div>', p, re.S)
        link = re.search(r'href="([^"]+)"', nm.group(1))
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(jt.group(1)) if jt else [], homepage=link.group(1) if link else None, division=None))
    return out


def ece_new(h):
    out = []
    for p in re.split(r'<div data-history-node-id=', h)[1:]:
        nm = re.search(r'field--name-field-person-name[^>]*>\s*<div class="field__item">(.*?)</div>', p, re.S)
        if not nm:
            continue
        jt = re.search(r'field--name-field-person-official-job-title[^>]*>\s*<div class="field__item">(.*?)</div>', p, re.S)
        link = re.search(r'<a href="(/directory/[^"]+)"', p)
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(jt.group(1)) if jt else [], homepage=link.group(1) if link else None, division=None))
    return out


def isye_old(h):
    out = []
    for p in re.split(r'<!-- Person -->', h)[1:]:
        nm = re.search(r'<h4 class="(?:field-content )?name">(.*?)</h4>', p, re.S)
        if not nm:
            continue
        jt = re.search(r'views-field-field-emp-title">\s*<div class="field-content">(.*?)</div>', p, re.S)
        link = re.search(r'href="([^"]+)"', nm.group(1))
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(jt.group(1)) if jt else [], homepage=link.group(1) if link else None, division=None))
    return out


def isye_card(h):
    out = []
    for m in re.finditer(r'<div class="w-100 px-0 pt-0 person-name">(.*?)</div>\s*<div class="person-type[^"]*">(.*?)</div>', h, re.S):
        link = re.search(r'href="([^"]+)"', m.group(1))
        out.append(dict(name_listed=clean(m.group(1)), titles=_titles(m.group(2)), homepage=link.group(1) if link else None, division=None))
    return out


def seas_directory(h):
    """Harvard SEAS directory (2019-): older Drupal markup prefixes field classes with `field-wrapper`."""
    out = []
    for p in re.split(r'<h2 class="node-title[^"]*person__detailed-name', h)[1:]:
        nm = re.search(r'<span class="[^"]*\bperson__name\b[^"]*">(.*?)</span>', p, re.S)
        if not nm:
            continue
        tt = re.search(r'class="[^"]*\bperson__primary-title\b[^"]*".*?<div class="field-item">(.*?)</div>', p, re.S)
        link = re.search(r'href="([^"]+)"', p.split('</h2>', 1)[0])
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(tt.group(1)) if tt else [], homepage=link.group(1) if link else None, division=None))
    return out


def seas_directory_d7(h):
    """Harvard SEAS directory before 2020 (Drupal 7: `/directory/<id>` entries, www.seas.harvard.edu/faculty-research/people/ladder and the CS people page):
    <h2><a href="/directory/jaiz">Name</a></h2> then field-primary-title."""
    out = []
    for p in re.split(r'<div class="group-header">', h)[1:]:
        nm = re.search(r'<h2><a href="([^"]*)">(.*?)</a></h2>', p, re.S)
        if not nm:
            continue
        tt = re.search(r'field-name-field-primary-title.*?<div class="field-item[^"]*">(.*?)</div>', p, re.S)
        out.append(dict(name_listed=clean(nm.group(2)), titles=_titles(tt.group(1)) if tt else [], homepage=nm.group(1) or None, division=None))
    return out


def wse_entity(h):
    """Johns Hopkins Whiting School WordPress theme ('wse'): <li class="entity_list_item"> with entity_name(_link) and entity_title (CS 2021-, other Whiting sites)."""
    out = []
    for p in re.split(r'<li class="entity_list_item">', h)[1:]:
        nm = re.search(r'<h\d class="entity_name"[^>]*>(.*?)</h\d>', p, re.S)
        if not nm:
            continue
        jt = re.search(r'<div class="entity_title">(.*?)</div>', p, re.S)
        link = re.search(r'href="([^"]+)"', nm.group(1))
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(jt.group(1)) if jt else [], homepage=link.group(1) if link else None, division=None))
    return out


def wse_contact(h):
    """JHU Whiting contact blocks (CS secondary/research faculty): visible names and titles only.

    A section heading applies until the next heading (Research, Visiting, Part-Time Faculty).
    The JSON-LD copy of each person and the contact details are deliberately not parsed.
    """
    out, division = [], None
    for p in re.split(r'<div class="contact_block">', h)[1:]:
        heading = re.search(r'<h\d class="contact_block_title">(.*?)</h\d>', p, re.S)
        if heading:
            division = clean(heading.group(1))
        nm = re.search(r'<h\d class="contact_name">(.*?)</h\d>', p, re.S)
        if not nm:
            continue
        title = re.search(r'<div class="contact_title">(.*?)</div>', p, re.S)
        link = re.search(r'<a class="contact_link" href="([^"]+)"[^>]*>(.*?)</a>', p, re.S)
        url = H.unescape(link.group(1)) if link else None
        profile = bool(link and clean(link.group(2)).lower() in ('faculty profile', 'profile'))
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(title.group(1)) if title else [],
                        homepage=None if profile else url, division=division,
                        **({'profile': url} if profile else {})))
    return out


def wu_teaser(h):
    out = []
    for p in re.split(r'<article [^>]*class="faculty-directory__teaser"', h)[1:]:
        nm = re.search(r'<h3 class="faculty-directory__teaser-name"[^>]*>(.*?)</h3>', p, re.S)
        if not nm:
            continue
        tt = re.search(r'<p class="faculty-directory__teaser-title">(.*?)</p>', p, re.S)
        link = re.search(r'href="([^"]+)"', p)
        out.append(dict(name_listed=clean(nm.group(1)), titles=_titles(tt.group(1)) if tt else [], homepage=link.group(1) if link else None, division=None))
    return out


def oxford_person_index(h):
    """Oxford's semantic person list; retain written titles and no contact fields."""
    out = []
    for block in re.findall(r'<li\b[^>]*class="personIndex"[^>]*>(.*?)</li>', h, re.S):
        name = re.search(r'<span[^>]*itemprop="name"[^>]*>(.*?)</span>', block, re.S)
        title = re.search(r'<span[^>]*class="list-unbulleted-extra"[^>]*>(.*?)</span>', block, re.S)
        link = re.search(r'<a[^>]*href="([^"]+)"', block)
        if name:
            # a memorial listing carries life dates after the name ('Stephen Cameron (1958-2019)'): they are not part of the name
            nm = re.sub(r'\s*\(\d{4}\s*[-\u2013]\s*\d{4}\)\s*$', '', clean(name.group(1)))
            out.append(dict(name_listed=nm, titles=_titles(title.group(1)) if title else [],
                            homepage=H.unescape(link.group(1)) if link else None, division=None))
    return out


def cambridge_directory(h):
    """CST's public directory: role classifications stay literal; Faculty is not a guessed rank."""
    out = []
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', h, re.S):
        name = re.search(r'<td[^>]*class="views-field views-field-title"[^>]*>(.*?)</td>', row, re.S)
        role = re.search(r'<td[^>]*class="views-field views-field-field-sd-classifications-ref"[^>]*>(.*?)</td>', row, re.S)
        if not name or not role:
            continue
        link = re.search(r'<a[^>]*href="([^"]+)"', name.group(1))
        nm = clean(name.group(1))
        titles = [clean(x) for x in re.findall(r'<a\b[^>]*>(.*?)</a>', role.group(1), re.S)]
        if not titles and clean(role.group(1)):
            titles = [clean(role.group(1))]
        if re.search(r'\(emeritus\)', nm, re.I):
            nm = re.sub(r'\s*\(emeritus\)', '', nm, flags=re.I)
            titles.append('emeritus')
        if nm:
            out.append(dict(name_listed=nm, titles=titles, homepage=H.unescape(link.group(1)) if link else None, division=None))
    return out


def cambridge_profile(h):
    """The department's own profile heading and explicit job titles, without biographical guesses."""
    name = re.search(r'<h1[^>]*class="campl-sub-title"[^>]*>(.*?)</h1>', h, re.S)
    box = re.search(r'<div[^>]*class="cst-job-titles[^"]*"[^>]*>(.*?)</div>', h, re.S)
    if not name or not box:
        return []
    titles = [clean(x) for x in re.findall(r'<li\b[^>]*>(.*?)</li>', box.group(1), re.S)]
    nm = re.sub(r'^(?:Dr|Prof(?:essor)?)\.?\s+', '', clean(name.group(1)), flags=re.I)
    nm = re.sub(r'(?:\s+(?:FRS|FACM))+$', '', nm)
    return [dict(name_listed=nm, titles=titles, homepage=None, division=None)] if titles else []


def vt_directory(h, section):
    """VT CS cards in one named appointment section; ignore repeated navigation."""
    main = re.search(r'<main\b[^>]*>(.*?)</main>', h, re.S | re.I)
    if not main:
        return []
    groups = {'teaching and research faculty': 'main', 'courtesy faculty': 'courtesy',
              'affiliate faculty': 'affiliate', 'adjunct faculty': 'adjunct', 'emeritus faculty': 'emeritus'}
    parts = re.split(r'<h[23]\b[^>]*>(.*?)</h[23]>', main.group(1), flags=re.S | re.I)
    selected, out = None, []
    for i in range(1, len(parts), 2):
        heading = clean(parts[i])
        if heading.casefold() in groups:
            selected = groups[heading.casefold()]
        elif heading.casefold() != 'find faculty by research area':
            selected = None
        if selected != section:
            continue
        if selected in ('adjunct', 'emeritus'):
            for item in re.findall(r'<div\b[^>]*class=[\'\"][^\'\"]*\bvt-text\b[^\'\"]*[\'\"][^>]*>\s*<p>(.*?)</p>', parts[i + 1], re.S | re.I):
                name = clean(item)
                link = re.search(r'<a\b[^>]*href=[\'\"]([^\'\"]+)', item, re.I)
                if name:
                    out.append(dict(name_listed=name, titles=[heading],
                                    homepage=H.unescape(link.group(1)).strip() if link else None, division=None))
            continue
        for card, role in re.findall(r'<span\b[^>]*class=[\'\"][^\'\"]*\bvt-list-title\b[^\'\"]*[\'\"][^>]*>(.*?)</span>\s*<p\b[^>]*class=[\'\"][^\'\"]*\bvt-list-description\b[^\'\"]*[\'\"][^>]*>(.*?)</p>', parts[i + 1], re.S | re.I):
            link = re.search(r'<a\b[^>]*href=[\'\"]([^\'\"]+)[\'\"][^>]*>(.*?)</a>', card, re.S | re.I)
            if not link:
                continue
            name = clean(re.sub(r'<span\b[^>]*class=[\'\"]sr-only[\'\"][^>]*>.*?</span>', '', link.group(2), flags=re.S | re.I))
            if name:
                out.append(dict(name_listed=name, titles=[clean(role)] if clean(role) else [],
                                homepage=H.unescape(link.group(1)).strip(), division=None,
                                quote=clean(card + ' ' + role)))
    return out


def toronto_directory(h, section):
    """One explicitly selected CS directory section, retaining only name and written position.

    Some source rows omit their opening tr tag. Fixed header column counts let us
    retain those entries without pulling contact or research cells into titles.
    """
    # 2021-2022 captures call the research section `tenurestream`; the current page calls it `researchstream`
    ids = ('researchstream', 'tenurestream') if section == 'researchstream' else (section,)
    m = None
    for sid in ids:
        m = re.search(r'<h2\b[^>]*id=[\'"]' + re.escape(sid) + r'[\'"][^>]*>.*?</h2>\s*<table\b[^>]*>(.*?)</table>', h, re.S | re.I)
        if m:
            break
    if not m:
        return []
    cells = re.findall(r'<td\b[^>]*>(.*?)(?=</td>|<td\b|</tr>|$)', m.group(1), re.S | re.I)
    columns = 5 if section == 'teachingstream' else 3
    if len(cells) % columns and section == 'teachingstream':
        # a teaching row may omit its phone/office cells (2025-04 capture): pair each name cell with the position cell after it
        out = []
        for i in range(len(cells) - 1):
            if '@' in cells[i] or not re.search(r'Teaching Stream|Lecturer|Instructor|Professor', cells[i + 1]) or re.search(r'Teaching Stream|Lecturer|Instructor', cells[i]):
                continue
            link = re.search(r'<a\b[^>]*href=[\'"]([^\'"]+)', cells[i], re.I)
            name = clean(re.split(r'<br\s*/?>', cells[i], flags=re.I)[0])
            if name:
                out.append(dict(name_listed=name, titles=[clean(cells[i + 1])], homepage=H.unescape(link.group(1)).strip() if link else None, division=None))
        return out
    if len(cells) % columns:
        raise ValueError(f'Toronto {section}: incomplete directory row ({len(cells)} cells)')
    out = []
    for i in range(0, len(cells), columns):
        first = re.split(r'<br\s*/?>', cells[i], flags=re.I)
        name = clean(first[0])
        link = re.search(r'<a\b[^>]*href=[\'"]([^\'"]+)', first[0], re.I)
        titles = [clean(x) for x in first[1:] if clean(x)] if section in ('researchstream', 'emeriti') else [clean(cells[i + 1])]
        if name:
            out.append(dict(name_listed=name, titles=[t for t in titles if t],
                            homepage=H.unescape(link.group(1)).strip() if link else None, division=None))
    return out


def hkust_faculty_table(h):
    """HKUST CSE text directory: named faculty rows, excluding contact cells.

    The named link is a department profile, not an independently verified lab
    website. Keep bilingual spellings together as written for source quotes.
    """
    from bs4 import BeautifulSoup
    out = []
    for row in BeautifulSoup(h, 'html.parser').select('tr.search'):
        cells = row.find_all('td', recursive=False)
        name = row.select_one('td.name a[href]')
        if name is None or len(cells) < 2:
            continue
        listed = name.get_text(' ', strip=True)
        titles = [clean(t) for t in re.split(r'<br\s*/?>', cells[1].decode_contents(), flags=re.I)]
        if listed:
            out.append(dict(name_listed=listed, titles=[t for t in titles if t],
                            profile=name['href'], homepage=None, division=None))
    return out


def hkust_faculty_cards(h):
    """HKUST CSE 2018-2021 card directory (www.cse.ust.hk/admin/people/faculty/): a.people-card with p.people-name and p.people-info1 (title)."""
    from bs4 import BeautifulSoup
    out = []
    for a in BeautifulSoup(h, 'html.parser').select('a.people-card'):
        nm = a.select_one('.people-name')
        if nm is None:
            continue
        titles = [clean(t.get_text(' ', strip=True)) for t in a.select('.people-info1')]
        out.append(dict(name_listed=nm.get_text(' ', strip=True), titles=[t for t in titles if t], profile=a.get('href'), homepage=None, division=None))
    seen, uniq = set(), []
    for e in out:   # the page repeats every card for the mobile layout
        if e['name_listed'] not in seen:
            seen.add(e['name_listed']); uniq.append(e)
    return uniq


def hkust_faculty_position_tables(h):
    """HKUST CSE 2016-2017 'Faculty by Position' tables: <td><a>SURNAME, Given</a></td><td>Chinese name</td> ... <td>Position</td>. Listed as the page prints it, 'SURNAME, Given Chinese', so the quote is found in the page text."""
    from bs4 import BeautifulSoup
    out = []
    for row in BeautifulSoup(h, 'html.parser').select('table.fancy tbody tr'):
        cells = row.find_all('td', recursive=False)
        a = cells[0].find('a') if cells else None
        if a is None or len(cells) < 6 or ',' not in a.get_text():
            continue
        fam, giv = [x.strip() for x in a.get_text(' ', strip=True).split(',', 1)]
        zh = cells[1].get_text(' ', strip=True).replace('\xa0', ' ').strip()
        title = clean(cells[5].get_text(' ', strip=True))
        out.append(dict(name_listed=' '.join(x for x in (f'{fam}, {giv}', zh) if x), titles=[title] if title else [], profile=a.get('href'), homepage=None, division=None))
    return out


def hkust_faculty_any(h):
    """The three HKUST CSE directory eras (2016-17 position tables, 2018-21 cards, 2022- text table): the first that parses."""
    for fn in (hkust_faculty_table, hkust_faculty_cards, hkust_faculty_position_tables):
        es = fn(h)
        if es:
            return es
    return []


def zju_cs_teacher_cards(h):
    """Zhejiang College of Computer Science 全院教师查询 (csen/qyjscx_95580, rendered: the cards are built by script): `article.teacher-card` with `h1.teacher-name`,
    one `span.badge` rank (教授, 副教授, 百人计划研究员, 讲师 ...) and the person.zju.edu.cn profile link. E-mail and research lines are contact/topic text and are not kept."""
    from bs4 import BeautifulSoup
    out = []
    for card in BeautifulSoup(h, 'html.parser').select('article.teacher-card'):
        n = card.select_one('h1.teacher-name')
        if n is None:
            continue
        a = card.select_one('a[href]')
        out.append(dict(name_listed=re.sub(r'[\s\u3000]+', '', n.get_text()), titles=[clean(b.get_text(' ', strip=True)) for b in card.select('span.badge') if clean(b.get_text(' ', strip=True))],
                        profile=a['href'] if a else None, homepage=None, division=None))
    return out


def zju_cs_zuzhi_names(h):
    """Zhejiang College of Computer Science 教师名录 (csen/27003 and its institute sub-lists 27055-27063): `ul.zuzhi` holds one `<a title=name href=profile>` per
    teacher; no rank or title is printed (names only), and the institute is the page's `span.titl`. Full-width and wide spaces inside a name are collapsed."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(h, 'html.parser')
    inst = soup.select_one('span.titl')
    division = clean(inst.get_text(' ', strip=True)) if inst else None
    out = []
    for a in soup.select('ul.zuzhi li a[href]'):
        name = re.sub(r'[\s\u3000]+', '', a.get('title') or a.get_text())
        if name:
            out.append(dict(name_listed=name, titles=[], profile=a['href'], homepage=None, division=division))
    return out


def tsinghua_cs_list(h):
    """Tsinghua CS faculty list (jzgml.htm): institute <h4>, rank band <h3>, then <li> cards `<h2><a title=NAME>` + first <p> = title.
    Phone and e-mail <p>s are contact lines and are never kept."""
    from bs4 import BeautifulSoup
    out = []
    for dl in BeautifulSoup(h, 'html.parser').select('div.people01-nr dl'):
        division = clean(dl.find('h4').get_text(' ', strip=True)) if dl.find('h4') else None
        for li in dl.select('li'):
            a = li.select_one('div.text h2 a[href]')
            if a is None:
                continue
            ps = li.select('div.text p')
            out.append(dict(name_listed=clean(a.get_text(' ', strip=True)), titles=[clean(ps[0].get_text(' ', strip=True))] if ps else [],
                            profile=a['href'], homepage=None, division=division))
    return out


def tsinghua_sw_names(h):
    """Tsinghua School of Software list (szdw/jsml.htm): `.group-title` bands (institute or 院士) with `.name-container a.name` links; no titles."""
    from bs4 import BeautifulSoup
    out, division = [], None
    for el in BeautifulSoup(h, 'html.parser').select('div.group-title, div.group-people'):
        if 'group-title' in el.get('class', []):
            division = clean(el.get_text(' ', strip=True))
            continue
        for a in el.select('div.name-container a.name[href]'):
            out.append(dict(name_listed=clean(a.get_text(' ', strip=True)), titles=[], profile=a['href'], homepage=None, division=division))
    return out


def tsinghua_iiis_cards(h):
    """Tsinghua IIIS people page (rydw.htm): `ul.ls16 li a` cards with `<h4>` name and `<p>` title line; interest text is not a title."""
    from bs4 import BeautifulSoup
    out = []
    for a in BeautifulSoup(h, 'html.parser').select('ul.ls16 li a[href]'):
        n, t = a.select_one('div.txt h4'), a.select_one('div.txt p')
        if n is not None:
            out.append(dict(name_listed=clean(n.get_text(' ', strip=True)), titles=[clean(t.get_text(' ', strip=True))] if t else [],
                            profile=a['href'], homepage=None, division=None))
    return out


def tsinghua_au_cards(h):
    """Tsinghua Automation institute pages (szdw/jsdw1/<group>/<institute>.htm): 2023+ `ul.list13 li a` cards, name in `<h3><big>`;
    the 2022 template is `div.teacher-list a div.item` under `div.research-name`. No title on either; javascript:; links have no profile."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for a in soup.select('ul.list13 li a[href]'):
        n = a.select_one('div.con h3')
        if n is not None and clean(n.get_text(' ', strip=True)):
            out.append(dict(name_listed=clean(n.get_text(' ', strip=True)), titles=[], profile=a['href'], homepage=None, division=None))
    if out:
        return out
    division = soup.select_one('div.research-name')
    division = clean(division.get_text(' ', strip=True)) if division else None
    for a in soup.select('div.teacher-list a[href]'):
        n = a.select_one('div.item')
        if n is not None and clean(n.get_text(' ', strip=True)):
            href = a['href']
            out.append(dict(name_listed=clean(n.get_text(' ', strip=True)), titles=[], profile=None if href.startswith('javascript') else href, homepage=None, division=division))
    return out


def tsinghua_air_cards(h):
    """Tsinghua AIR English team page (our_team/Research_Team.htm): `div.yjtd_tit h1` band (Professor, ...) then `li` cards with `<h2>` name and `<h3>` title."""
    from bs4 import BeautifulSoup
    out = []
    for box in BeautifulSoup(h, 'html.parser').select('div.yjtd_tit'):
        band = clean(box.get_text(' ', strip=True))
        body = box.find_next_sibling('div', class_='yjtd_nr')
        for li in (body.select('li') if body else []):
            n, t, a = li.select_one('h2'), li.select_one('h3'), li.select_one('a[href]')
            if n is not None and clean(n.get_text(' ', strip=True)):
                out.append(dict(name_listed=clean(n.get_text(' ', strip=True)), titles=[clean(t.get_text(' ', strip=True))] if t else [],
                                profile=a['href'] if a else None, homepage=None, division=band))
    return out


def tsinghua_cs_old_list(h):
    """Tsinghua CS faculty list 2011-2020 (/publish/cs/4797/index.html, 教职工名录): `div.box_detail` with an institute `<h1>` and `<li><p>` lines
    `正高：<a>name</a>， <a>name</a>` / `副高：...`; the band is the title. The page's own first `<h1>` is the list title, not an institute."""
    from bs4 import BeautifulSoup
    box = BeautifulSoup(h, 'html.parser').select_one('div.box_detail')
    out, division = [], None
    for el in (box.find_all(['h1', 'li']) if box else []):
        if el.name == 'h1':
            t = clean(el.get_text(' ', strip=True))
            division = None if '名录' in t else t
            continue
        p = el.find('p')
        if p is None:
            continue
        m = re.match(r'\s*([^：:]{1,10})[：:]', p.get_text('', strip=False).replace('\xa0', ' '))
        band = clean(m.group(1)) if m else None
        for a in p.find_all('a', href=True):
            name = clean(a.get_text(' ', strip=True)).replace(' ', '')
            if name:
                out.append(dict(name_listed=name, titles=[band] if band else [], profile=a['href'], homepage=None, division=division))
    return out


def tsinghua_iiis_media(h):
    """Tsinghua IIIS full-time faculty list 2016-2024 (/list-324-1.html): `h4.color_danger` series heading, then `div.media-body` cards with
    `<strong><a>name</a></strong><br> title <br> interests`; the title is the first text line after the name."""
    from bs4 import BeautifulSoup
    out, series = [], None
    for el in BeautifulSoup(h, 'html.parser').select('h4.color_danger, div.media-body'):
        if el.name == 'h4':
            series = clean(el.get_text(' ', strip=True))
            continue
        a = el.select_one('strong a')
        if a is None or not clean(a.get_text(' ', strip=True)):
            continue
        lines = [clean(t) for t in el.get_text('\n', strip=True).split('\n')]
        title = lines[1] if len(lines) > 1 else None
        out.append(dict(name_listed=clean(a.get_text(' ', strip=True)), titles=[title] if title else [], profile=a.get('href'), homepage=None, division=series))
    return out


def tsinghua_sw_old_list(h):
    """Tsinghua School of Software list 2012-2020 (/publish/soft/3655/index.html, 教师名录): `div#s2_right_con` with `<p><strong>band</strong></p>` then a
    `<p>` of names, linked (`<a>`) or plain text separated by spaces. The band (院士, 杰青, 教授, 讲师/助理研究员/助理教授, ...) is the title; honour bands
    repeat people who also sit in 教授 and are kept as written."""
    from bs4 import BeautifulSoup
    root = BeautifulSoup(h, 'html.parser').select_one('div#s2_right_con')
    out, band = [], None
    for p in (root.find_all('p') if root else []):
        strong = p.find('strong')
        text = clean(p.get_text(' ', strip=True).replace('\xa0', ' '))
        if strong is not None and not p.find('a') and clean(strong.get_text(' ', strip=True)) == text:
            band = text
            continue
        if band is None or not text or text == '教师名录':
            continue
        links = p.find_all('a', href=True)
        seen = set()
        for a in links:
            name = clean(a.get_text(' ', strip=True)).replace(' ', '')
            if name:
                out.append(dict(name_listed=name, titles=[band], profile=a['href'], homepage=None, division=None)); seen.add(name)
        rest = clean(' '.join(t for t in p.find_all(string=True) if t.find_parent('a') is None).replace('\xa0', ' '))
        for tok in rest.split():
            if tok and tok not in seen and re.search(r'[\u4e00-\u9fff]{2,4}|[A-Za-z]{2,}', tok) and tok not in ('、', '，'):
                out.append(dict(name_listed=tok, titles=[band], profile=None, homepage=None, division=None))
    return out


def tsinghua_ee_rendered(h):
    """Tsinghua EE faculty page (ryqk/teacher/xxgdzyjs/js2.htm) AFTER JavaScript (tools/js_render_capture.py): `li#yjs_N` institute (`div.type`), then `div.line` rows
    with the rank band in `div.l` (高 级 / 副高级 / 中 级) and the names as `<a>` links in `ul[id^=showdatainfo]`. The raw HTML holds the same list only as embedded JSON."""
    from bs4 import BeautifulSoup
    out = []
    for li in BeautifulSoup(h, 'html.parser').select('li[id^=yjs_]'):
        t = li.select_one('div.type')
        inst = clean(t.get_text(' ', strip=True)) if t else None
        for line in li.select('div.line'):
            band = line.select_one('div.l')
            band = clean(band.get_text('', strip=True)).replace(' ', '').rstrip('：:') if band else None
            for a in line.select('ul a[href]'):
                name = clean(a.get_text(' ', strip=True))
                if name:
                    out.append(dict(name_listed=name, titles=[band] if band else [], profile=a['href'], homepage=None, division=inst))
    return out


def tsinghua_ee_embedded(h):
    """Tsinghua EE faculty page as ARCHIVED (raw HTML, no JavaScript run): the lists are embedded as `qh_data = [{showTitle, fields, url}]` inside
    `function topage_<institute>_<band>(...)`; the institute is `li#yjs_<i>` `div.type` and the band 1/2/3 = 高级 / 副高级 / 中级 (same page as tsinghua_ee_rendered)."""
    import json as _json
    inst = dict(re.findall(r'<li id="yjs_(\d+)">\s*<div class="con">\s*<div class="type">(.*?)</div>', h, re.S))
    band = {'1': '高级', '2': '副高级', '3': '中级'}
    out = []
    for m in re.finditer(r'function topage_(\d)_(\d)\(keyword, yjly, szm\)\s*\{\s*var qh_itemid = "[^"]+";\s*var qh_data = (\[.*?\]);', h, re.S):
        i, j, js = m.groups()
        try:
            rows = _json.loads(js)
        except ValueError:
            continue
        for e in rows:
            name = clean(e.get('showTitle') or '')
            if name:
                out.append(dict(name_listed=name, titles=[band.get(j, j)], profile=(e.get('url') or {}).get('asString'), homepage=None, division=clean(inst.get(i, '')) or None))
    return out


def tsinghua_au_old_list(h):
    """Tsinghua Automation faculty list 2016-2019 (/publish/au/1096/index.html, 在职教师 按研究所划分): `div.box_detail` with an institute `<p>` and tables whose text cells are
    `<div><a>name</a></div><div>title</div>` (the picture cells carry only an image link)."""
    from bs4 import BeautifulSoup
    box = BeautifulSoup(h, 'html.parser').select_one('div.box_detail')
    out, division = [], None
    for el in (box.find_all(['p', 'td']) if box else []):
        if el.name == 'p':
            t = clean(el.get_text(' ', strip=True))
            if t and len(t) <= 14 and re.search(r'所|中心|系', t):
                division = t
            continue
        divs = el.find_all('div', recursive=False)
        if len(divs) >= 2 and divs[0].find('a', href=True):
            name = clean(divs[0].get_text(' ', strip=True)).replace(' ', '')
            if name:
                out.append(dict(name_listed=name, titles=[clean(divs[1].get_text(' ', strip=True))], profile=divs[0].find('a')['href'], homepage=None, division=division))
    return out


def tsinghua_insc_bands(h):
    """Tsinghua INSC faculty page (szdw_/zzjs.htm): `<p><strong>副教授：</strong></p>` band paragraphs, then paragraphs of name links (some names are plain text)."""
    from bs4 import BeautifulSoup
    out, band = [], None
    for p in BeautifulSoup(h, 'html.parser').find_all('p'):
        text = clean(p.get_text(' ', strip=True).replace('\xa0', ' '))
        st = p.find('strong')
        if st is not None and re.fullmatch(r'[^：:]{1,12}[：:]', clean(st.get_text('', strip=True))) and not p.find('a'):
            band = clean(st.get_text('', strip=True)).rstrip('：:')
            continue
        if band is None or not text:
            continue
        seen = set()
        for a in p.find_all('a', href=True):
            name = clean(a.get_text(' ', strip=True)).replace(' ', '')
            if name:
                out.append(dict(name_listed=name, titles=[band], profile=a['href'], homepage=None, division=None)); seen.add(name)
        rest = clean(' '.join(t for t in p.find_all(string=True) if t.find_parent('a') is None).replace('\xa0', ' '))
        for tok in rest.split():
            if tok not in seen and re.fullmatch(r'[\u4e00-\u9fff]{2,4}', tok):
                out.append(dict(name_listed=tok, titles=[band], profile=None, homepage=None, division=None))
    return out


def tsinghua_ee_text(h):
    """Tsinghua EE faculty page 2022-2025 as ARCHIVED: plain text after `图片列表`: institute heading (…研究所 / …中心), then `教 授：`, `副教授：`, `讲 师：` ... bands each followed by name tokens."""
    from bs4 import BeautifulSoup
    t = BeautifulSoup(h, 'html.parser').get_text(' ')
    i = t.find('图片列表')
    area = t[i + 4:] if i >= 0 else t
    area = re.sub(r'([教讲高中副助])\s+([授师级理])', r'\1\2', area)
    out, division, band = [], None, None
    for tok in area.replace('\xa0', ' ').split():
        if re.search(r'版权所有|Copyright', tok):
            break
        if re.search(r'(?:研究所|中心)$', tok) and len(tok) <= 14:
            division, band = tok, None
        elif tok.endswith(('：', ':')):
            band = tok.rstrip('：:')
        elif band and division and re.fullmatch(r'[\u4e00-\u9fff]{2,4}', tok):
            out.append(dict(name_listed=tok, titles=[band], profile=None, homepage=None, division=division))
        elif re.search(r'版权所有|Copyright', tok):
            break
    return out


def tsinghua_ee_any(h):
    """Tsinghua EE faculty page, any archived template: embedded JSON (2025-09 on), else the rendered DOM, else the 2022-2025 plain-text template."""
    return tsinghua_ee_embedded(h) or tsinghua_ee_rendered(h) or tsinghua_ee_text(h)


FORMATS = {
    'tsinghua_ee_any': (tsinghua_ee_any, re.compile(r'(?!)')),
    'tsinghua_ee_text': (tsinghua_ee_text, re.compile(r'图片列表.{0,3000}?(?:教\s*授|副教授)\s*[：:]', re.S)),
    'tsinghua_au_old_list': (tsinghua_au_old_list, re.compile(r'<table[^>]*uetable')),
    'tsinghua_insc_bands': (tsinghua_insc_bands, re.compile(r'(?!)')),
    'tsinghua_ee_embedded': (tsinghua_ee_embedded, re.compile(r'function topage_\d_\d\(keyword, yjly, szm\)')),
    'tsinghua_ee_rendered': (tsinghua_ee_rendered, re.compile(r'id="showdatainfo')),
    'tsinghua_sw_old_list': (tsinghua_sw_old_list, re.compile(r'id="s2_right_con"[^>]*>.{0,400}教师名录', re.S)),
    'tsinghua_cs_old_list': (tsinghua_cs_old_list, re.compile(r'class="box_detail"[^<]*<h1[^>]*>.{0,200}在职教师名录', re.S)),
    'tsinghua_iiis_media': (tsinghua_iiis_media, re.compile(r'class="color_danger"')),
    'vt_main': (lambda h: vt_directory(h, 'main'), re.compile(r'(?!)')),
    'vt_courtesy': (lambda h: vt_directory(h, 'courtesy'), re.compile(r'(?!)')),
    'vt_affiliate': (lambda h: vt_directory(h, 'affiliate'), re.compile(r'(?!)')),
    'vt_adjunct': (lambda h: vt_directory(h, 'adjunct'), re.compile(r'(?!)')),
    'vt_emeritus': (lambda h: vt_directory(h, 'emeritus'), re.compile(r'(?!)')),
    'hkust_faculty_any': (hkust_faculty_any, re.compile(r'(?!)')),
    'zju_cs_teacher_cards': (zju_cs_teacher_cards, re.compile(r'class="teacher-card"')),
    'zju_cs_zuzhi_names': (zju_cs_zuzhi_names, re.compile(r'class="zuzhi"')),
    'tsinghua_cs_list': (tsinghua_cs_list, re.compile(r'class="people01-nr"')),
    'tsinghua_sw_names': (tsinghua_sw_names, re.compile(r'class="group-title"')),
    'tsinghua_iiis_cards': (tsinghua_iiis_cards, re.compile(r'class="ls16 flex"')),
    'tsinghua_au_cards': (tsinghua_au_cards, re.compile(r'class="list13 flex"|class="teacher-list"')),
    'tsinghua_air_cards': (tsinghua_air_cards, re.compile(r'class="yjtd_tit"')),
    'hkust_faculty_table': (hkust_faculty_table, re.compile(r'(?!)')),
    'toronto_research': (lambda h: toronto_directory(h, 'researchstream'), re.compile(r'(?!)')),
    'toronto_teaching': (lambda h: toronto_directory(h, 'teachingstream'), re.compile(r'(?!)')),
    'toronto_emeriti': (lambda h: toronto_directory(h, 'emeriti'), re.compile(r'(?!)')),
    'toronto_cross': (lambda h: toronto_directory(h, 'crossappointed'), re.compile(r'(?!)')),
    'toronto_status': (lambda h: toronto_directory(h, 'statusonly'), re.compile(r'(?!)')),
    'toronto_adjunct': (lambda h: toronto_directory(h, 'adjunct'), re.compile(r'(?!)')),
    'cambridge_profile': (cambridge_profile, re.compile(r'class="cst-job-titles')),
    'oxford_person_index': (oxford_person_index, re.compile(r'class="personIndex"')),
    'cambridge_directory': (cambridge_directory, re.compile(r'views-field-field-sd-classifications-ref')),
    'eecs_table': (eecs_table, re.compile(r'<b>Division:</b>', re.I)),
    'eecs_wp': (eecs_wp, re.compile(r"class=['\"]eecs_person_wrapper['\"]")),
    'uc_cs_table': (uc_cs_table, re.compile(r'<tr class="(?:odd|even)[^"]*">.*?(?:Personal website|Research Interests)', re.S)),
    'uc_people_li': (uc_people_li, re.compile(r'<li class="mix ')),
    'uc_card': (uc_card, re.compile(r'card card--person')),
    'galton_cells': (galton_cells, re.compile(r'</strong>(?:</a>)?\s*<br\s*/?>\s*<span class="text">')),
    'ttic_media': (ttic_media, re.compile(r'class="media-heading"')),
    'ttic_table': (ttic_table, re.compile(r'<td><strong>')),
    'gt_people': (gt_people, re.compile(r'class="gt-person-box')),
    'gt_card': (gt_card, re.compile(r'class="card-block__title"')),
    'ece_old': (ece_old, re.compile(r'class="field-full-name"')),
    'ece_new': (ece_new, re.compile(r'field--name-field-person-official-job-title')),
    'isye_old': (isye_old, re.compile(r'<!-- Person -->')),
    'seas_directory': (seas_directory, re.compile(r'person__detailed-name')),
    'seas_directory_d7': (seas_directory_d7, re.compile(r'field-name-field-primary-title')),
    'wse_entity': (wse_entity, re.compile(r'class="entity_list_item"')),
    'wse_contact': (wse_contact, re.compile(r'class="contact_block"')),
    'wu_teaser': (wu_teaser, re.compile(r'class="faculty-directory__teaser"')),
    'isye_card': (isye_card, re.compile(r'class="w-100 px-0 pt-0 person-name"')),
}


def parse(h, fmt=None):
    """(format name, entries); (None, []) when no format matches."""
    if fmt:
        return fmt, FORMATS[fmt][0](h)
    for name, (fn, det) in FORMATS.items():
        if det.search(h):
            return name, fn(h)
    return None, []


def is_paged(html):
    """A capture of one page of a paged directory (pager markers and a ?page=N link): it parses to a few people while the rest sit on pages
    the archive may not hold (UChicago CS 2017: 5 of about 45). listing_rows.py reports it and plan_fetch.charter_usable rejects it."""
    return bool(re.search(r'class="pager"|class="pagination"', html) and re.search(r'(?:[?&]|&amp;)page=(?:%2C|,)?[1-9]', html))


def page_links(html, base_url):
    """{n: absolute url} of the other pages a paged directory links (`?page=N`, `?title=&amp;page=N`), n >= 1, same path as `base_url`. Pages the pager
    only elides ('1 2 3 ... last') are filled in from the largest linked number by substituting it into a linked URL, so the result covers 1..last.
    Used by plan_fetch to fetch every page of a paged slot (R3, Georgia Tech friction 10: the pipeline took one page for a whole half-year)."""
    import urllib.parse
    base_url = re.sub(r'^(https?://[^/]+?):(?:80|443)(?=/|$)', r'\1', base_url)   # Wayback keeps ':80' in the original of old captures; its CDX does not match it
    base = urllib.parse.urlsplit(base_url)
    found = {}
    for href in re.findall(r'href="([^"]*[?&;]page=(?:%2C|,)?\d+[^"]*)"', html):
        u = urllib.parse.urljoin(base_url, H.unescape(href))
        sp = urllib.parse.urlsplit(u)
        if sp.path.rstrip('/') != base.path.rstrip('/') or sp.netloc.lower().split(':')[0] != base.netloc.lower().split(':')[0]:
            continue
        m = re.search(r'(?:^|&)page=(?:%2C|,)?(\d+)', sp.query)
        if m and int(m.group(1)) >= 1:
            found.setdefault(int(m.group(1)), u)
    if not found:
        return {}
    tmpl = found[min(found)]
    return {n: found.get(n) or re.sub(r'(^|[?&])page=((?:%2C|,)?)\d+', lambda m: f'{m.group(1)}page={m.group(2)}{n}', tmpl, count=1) for n in range(1, max(found) + 1)}


def letter_links(html, base_url):
    """{letter: absolute url} of an A-Z index under the listing's own path (`/people/faculty/a`, one link per letter that has people): the other way a
    Drupal 9 directory is paged. Georgia Tech's `?page=N` pages are mostly unarchived but its letter pages are, so plan_fetch falls back to them."""
    import urllib.parse
    base_url = re.sub(r'^(https?://[^/]+?):(?:80|443)(?=/|$)', r'\1', base_url)
    base = urllib.parse.urlsplit(base_url)
    out = {}
    for href in re.findall(r'href="([^"]+)"', html):
        sp = urllib.parse.urlsplit(urllib.parse.urljoin(base_url, H.unescape(href)))
        m = re.fullmatch(re.escape(base.path.rstrip('/')) + r'/([A-Za-z])/?', sp.path)
        if m and sp.netloc.lower() == base.netloc.lower() and not sp.query:
            out.setdefault(m.group(1).lower(), f'{sp.scheme}://{sp.netloc}{sp.path}')
    return out
