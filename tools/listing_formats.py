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


def toronto_directory(h, section):
    """One explicitly selected CS directory section, retaining only name and written position.

    Some source rows omit their opening tr tag. Fixed header column counts let us
    retain those entries without pulling contact or research cells into titles.
    """
    m = re.search(r'<h2\b[^>]*id=[\'"]' + re.escape(section) + r'[\'"][^>]*>.*?</h2>\s*<table\b[^>]*>(.*?)</table>', h, re.S | re.I)
    if not m:
        return []
    cells = re.findall(r'<td\b[^>]*>(.*?)(?=</td>|<td\b|</tr>|$)', m.group(1), re.S | re.I)
    columns = 5 if section == 'teachingstream' else 3
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


FORMATS = {
    'hkust_faculty_any': (hkust_faculty_any, re.compile(r'(?!)')),
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
