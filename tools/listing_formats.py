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
  uw_allen_cards   UW Paul G. Allen School 2025- (www.cs.washington.edu/people/{faculty-members,emeritus,adjunct}/): Elementor cards, p.elementor-heading-title; the name is the
               link labelled "Read the bio for ..." (the profile), the following heading paragraphs are the title(s) and, for adjuncts, the home unit (kept as a title line)
  uw_ece_staff UW ECE WordPress (www.ece.uw.edu/people/faculty/): div.stafftemplate--entry, span.stafftemplate--name (link), span.stafftemplate--title; interests, office, phone and
               e-mail spans are dropped
  uw_ischool_card UW Information School Drupal (ischool.uw.edu/people/faculty): article.card, h2 link name, p.small em title; ONE page lists every group (data-type: faculty,
               visitingguest, phd, staff, ...), kept as `division`; a rank still needs the title
  uw_amath_directory UW Applied Mathematics Drupal (amath.washington.edu/people/faculty): h2.directory-item__name link, strong.directory-item__title ('<br>'-separated lines)
  uw_hcde_columns UW HCDE Drupal (www.hcde.washington.edu/faculty): div.column holding h2 > a > strong name and the <p> title that follows
"""

import html as H
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit

TAG = re.compile(r'<[^>]+>')


def clean(s):
    s = re.sub(r'<script.*?</script>', ' ', s, flags=re.S | re.I)
    return ' '.join(H.unescape(TAG.sub(' ', s)).split())


def illinois_campus_faculty(h):
    """Campus-wide Illinois faculty listing, preserving unit and source userid.

    A person can occur in several units. Keep each source occurrence; the
    directory userid supports cross-checking without merging people by name.
    """
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for group in soup.select('ul.faculty-list'):
        heading = group.find_previous(['h2', 'h3'])
        unit = clean(str(heading)) if heading else ''
        for row in group.find_all('li', recursive=False):
            link = row.find('a', href=True)
            title = row.select_one('.notes, .ws-a-z-notes')
            if not link or not title:
                continue
            name, role = clean(str(link)), clean(str(title))
            if not name or not role:
                continue
            from urllib.parse import parse_qs
            userid = parse_qs(urlsplit(link['href']).query).get('netID', [''])[0].split('@')[0]
            out.append(dict(name_listed=name, titles=[role], profile=link['href'],
                            division=unit, source_key=userid, quote_parts=[name, role]))
    return out


def illinois_directory_cards(h, categories=None):
    """Illinois directory cards, with category supplied by the reviewed listing slot.

    Use the separate school/affiliate/emeritus pages: numeric CSS categories on
    the combined directory do not establish a person's appointment category.
    """
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.directory-list .item.person'):
        if categories is not None and not categories.intersection(card.get('class', [])):
            continue
        name = card.select_one('.details .name a[href]')
        title = card.select_one('.details .title')
        if not name or not title:
            continue
        listed, text = clean(str(name)), clean(str(title))
        if not listed or not text:
            continue
        out.append(dict(name_listed=listed, titles=[text], profile=name['href']))
    return out


def stanford_cs_legacy(h):
    """Unpaged CS directory tables: names and faculty categories, without contacts.

    The section heading supplies a category, not an individual professor rank.
    Some faculty have no link; their printed first-cell name still counts.
    """
    soup = BeautifulSoup(h, 'html.parser')
    categories = {'Regular Faculty', 'Lecturers', 'Emeritus Faculty',
                  'Courtesy Faculty', 'Adjunct Faculty', 'Visiting and Acting Faculty'}
    out = []
    for table in soup.select('table'):
        heading = table.find_previous(['h1', 'h2', 'h3', 'h4'])
        category = clean(heading.get_text(' ', strip=True)) if heading else ''
        if category not in categories:
            continue
        for tr in table.select('tr'):
            cells = tr.find_all('td', recursive=False)
            if len(cells) != 4:
                continue
            name = clean(cells[0].get_text(' ', strip=True))
            if not name:
                continue
            link = cells[0].select_one('a[href]')
            out.append(dict(name_listed=name, titles=[], division=category,
                            homepage=link['href'] if link else None))
    return out


def ucsd_cse_cards(h):
    """UC San Diego CSE faculty-profiles page (Drupal 8, 2017-2026): section headings with name cards, no per-person rank.

    The heading ('Faculty', 'Emeritus', 'Adjunct', 'Affiliated', 'Lecturer', 'Researcher', 'Continuing Lecturer') is the only category the page prints,
    so it is the title; the quote is the card name plus that heading (verbatim excerpts). Leadership repeats faculty and 'Alumni' lists
    former members (not an appointment), so both are skipped. 2020-era pages put the name in <h4>, 2024-era pages in <p><strong>.
    """
    soup = BeautifulSoup(h, 'html.parser')
    keep = {'Full': 'Faculty', 'Faculty': 'Faculty', 'Adjunct': 'Adjunct', 'Lecturer': 'Lecturer', 'Lecturers': 'Lecturer', 'Emeritus': 'Emeritus',
            'Emeritus Faculty': 'Emeritus', 'Affiliated': 'Affiliated', 'Researcher': 'Researcher', 'Researchers': 'Researcher',
            'Continuing Lecturer': 'Continuing Lecturer', 'Continuing Lecturers': 'Continuing Lecturer'}
    out, seen, heading, label = [], set(), None, None
    for el in soup.find_all(['h3', 'a']):
        if el.name == 'h3':
            heading = clean(el.get_text(' ', strip=True))
            label = keep.get(heading)
            continue
        href = el.get('href') or ''
        if not re.search(r'/people/faculty-profiles/[a-z0-9-]+/?$', href) or label is None:
            continue
        nm = el.find(['h4', 'h5', 'strong'])
        name = clean(nm.get_text(' ', strip=True)) if nm else ''
        if not name or (label, href) in seen:
            continue
        seen.add((label, href))
        out.append(dict(name_listed=name, titles=[heading], profile=href, homepage=None, division=None, quote_parts=[name, heading]))
    return out


def ucsd_cse_info_cols(h):
    """UC San Diego CSE faculty page, 2017H2-2019 (Drupal 8 'faculty__info__col' blocks): name in <h2>, then the printed title.

    Contact lines (e-mail, phone, office) follow the title in the same block and are never kept.
    """
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for col in soup.select('div.faculty__info__col'):
        h2 = col.find('h2')
        if h2 is None:
            continue
        name = clean(h2.get_text(' ', strip=True))
        link = h2.find_parent('a', href=True)
        title = ''
        for node in h2.find_parent('a').next_siblings if h2.find_parent('a') else h2.next_siblings:
            if getattr(node, 'name', None) == 'br':
                break
            if isinstance(node, str) and node.strip():
                title = clean(node)
                break
        if not name or not title:
            continue
        out.append(dict(name_listed=name, titles=[title], profile=None, homepage=link['href'] if link else None, division=None))
    return out


def ucsd_jacobs_findprofile(h):
    """Jacobs School faculty search results (findprofile.sfe?department=<code>, 2016-2017): one table row per person.

    The name is 'Last, First M.'; each <p class=profiledept> holds one appointment, 'Title , UNIT' (printed units: CSE, Calit2, ...).
    Expertise text and contact details are not kept.
    """
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for tr in soup.select('table#faclist tr'):
        a = tr.select_one('p[style*="bold"] a[href]')
        if a is None:
            continue
        titles = [clean(p.get_text(' ', strip=True)) for p in tr.select('span.profiledept p')]
        titles = [t for t in titles if t]
        if not titles:
            continue
        out.append(dict(name_listed=clean(a.get_text(' ', strip=True)), titles=titles, profile=a['href'], homepage=None, division=None))
    return out


def stanford_cs_cards(h):
    """CS Faculty by Name: all faculty categories, with each card's written title."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for li in soup.select('li'):
        name = li.select_one('.views-field-title h3')
        title = li.select_one('.views-field-su-person-short-title .field-content')
        if name is None or title is None:
            continue
        link = name.find_parent('a', href=True)
        out.append(dict(name_listed=clean(name.get_text(' ', strip=True)),
                        titles=[clean(title.get_text(' ', strip=True))],
                        profile='https://www.cs.stanford.edu' + link['href'] if link and link['href'].startswith('/') else link['href'] if link else None,
                        homepage=None, division=None))
    for card in soup.select('.su-card__contents'):
        name, title = card.select_one('h3 a[href]'), card.select_one('.su-person-short-title')
        if name is not None and title is not None:
            out.append(dict(name_listed=clean(name.get_text(' ', strip=True)),
                            titles=[clean(title.get_text(' ', strip=True))],
                            profile='https://www.cs.stanford.edu' + name['href'] if name['href'].startswith('/') else name['href'], homepage=None, division=None))
    return out


def stanford_ee_cards(h):
    """EE directory cards; administrators alongside faculty are excluded."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for heading in soup.select('h3.description, h3.orglist__display-name'):
        link, title = heading.select_one('a[href]'), heading.select_one('small')
        if link is None or title is None:
            continue
        role = clean(title.get_text(' ', strip=True))
        if not re.search(r'Professor|Faculty|Lecturer|Emerit', role, re.I):
            continue
        out.append(dict(name_listed=clean(link.get_text(' ', strip=True)),
                        titles=[role], profile=link['href'], homepage=None, division=None))
    return out


def stanford_ee_bulletin(h):
    """Official EE Bulletin faculty paragraphs, including courtesy and emeriti.

    Keep the full faculty paragraph as the quote so each printed rank is sourced
    together with its names. Administrative committee paragraphs are excluded.
    A name's asterisk denotes recall, not another person or an inferred rank.
    """
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for p in soup.select('#facultytextcontainer > p'):
        first = p.find('em')
        if first is None:
            continue
        label = clean(first.get_text(' ', strip=True))
        if not re.match(r'^(?:Emeriti|(?:Courtesy |Adjunct |Visiting |Consulting )?(?:Associate |Assistant )?Professors?|Lecturers)\b', label):
            continue
        emeriti = label.startswith('Emeriti')
        text = clean(p.get_text(' ', strip=True))[len(label):]
        text = re.sub(r'\s*\(deceased[^)]*\)', '', text, flags=re.I)
        text = re.sub(r'\(\s*\*Recalled to active duty\s*\)', '', text)
        sections = re.split(r';\s*\(\s*(Associate Professors?|Professors,\s*Research)\s*\)\s*', text) if emeriti else [text]
        for pos in range(0, len(sections), 2):
            role = label if pos == 0 else sections[pos - 1]
            for token in sections[pos].split(','):
                name = token.strip(' *;():\u00a0')
                if not name or len(name.split()) < 2:
                    continue
                out.append(dict(name_listed=name, titles=([label, role] if emeriti and role != label else [role]),
                                homepage=None, division='Emeriti' if emeriti else None, quote_raw=str(p)))
    return out


def berkeley_eecs_faculty(h):
    """Berkeley EECS's old table and later unpaged media faculty lists."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for tr in soup.select('tr'):
        link = tr.select_one('strong a[href*="/Faculty/Homepages/"]')
        if not link:
            continue
        cell = link.find_parent('td')
        if not cell:
            continue
        text = list(cell.stripped_strings)
        if len(text) < 2 or text[0] != link.get_text(' ', strip=True):
            continue
        title = text[1]
        if not re.search(r'Professor|Lecturer|Faculty', title, re.I):
            continue
        out.append(dict(name_listed=text[0], titles=[title], homepage=None,
                        division=None, profile=link['href']))
    for card in soup.select('div.media, div.cc-image-list__item'):
        head = card.select_one('h3.media-heading a[href], div.cc-image-list__item__content h3 a[href]')
        role = card.select_one('div.media-body p strong, div.cc-image-list__item__content p strong')
        if not head or not role:
            continue
        name = head.get_text(' ', strip=True)
        title = role.get_text(' ', strip=True)
        if name and re.search(r'Professor|Lecturer|Faculty', title, re.I):
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=head['href']))
    return out


def berkeley_eecs_directory(h):
    """2018 unpaged EECS directory: retain only explicitly labelled faculty roles."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for tr in soup.select('table.eecs-static-table tbody tr'):
        cells = tr.find_all('td', recursive=False)
        if len(cells) != 7:
            continue
        status = cells[4].get_text(' ', strip=True)
        if status not in ('Faculty', 'Lecturer', 'Professor in Residence'):
            continue
        name = cells[0].get_text(' ', strip=True)
        link = cells[0].select_one('a[href]')
        if name:
            out.append(dict(name_listed=name, titles=[status], homepage=None,
                            division=cells[5].get_text(' ', strip=True),
                            profile=link['href'] if link else None))
    return out


def mit_csail_pi(h):
    """CSAIL PI roster: old JSON, Drupal cards, or complete Solr response."""
    try:
        data = json.loads(h)
    except (ValueError, TypeError):
        # The 2016–2017 Exhibit endpoint has one trailing comma after its last
        # item. Preserve every field and remove only that final separator.
        try:
            data = json.loads(re.sub(r',\s*\]\s*}', ']}', h))
        except (ValueError, TypeError):
            data = None
    if isinstance(data, dict):
        if isinstance(data.get('items'), list):
            return [dict(name_listed=x['label'], titles=[x['position']], homepage=None,
                         division=None, profile=x.get('url'))
                    for x in data['items'] if x.get('label') and x.get('position')]
        response = data.get('response') or {}
        docs = response.get('docs') or []
        if response.get('numFound') != len(docs):
            return []  # A truncated Solr page cannot establish full-year coverage.
        return [dict(name_listed=' '.join(x['ss_title'].split()), titles=[x['ss_field_title']], homepage=None,
                     division=x.get('ss_name'), profile=x.get('ss_url'))
                for x in docs if x.get('ss_title') and x.get('ss_field_title')]
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('div.info-block'):
        link = card.select_one('h2.card-heading')
        profile = link.find_parent('a', href=True) if link else None
        title = card.select_one('.field--name-field-title')
        if not link or not title:
            continue
        name = link.get_text(' ', strip=True)
        role = title.get_text(' ', strip=True)
        if name and role:
            out.append(dict(name_listed=name, titles=[role], homepage=None,
                            division=None, profile=profile['href'] if profile else None))
    return out


def nus_cs_legacy_tables(h):
    """Old NUS CS faculty tables, excluding administrators and research assistants."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for table in soup.select('table'):
        head = table.select_one('tr')
        if not head or not re.search(r'\bName\s+Designation\b', head.get_text(' ', strip=True)):
            continue
        for tr in table.select('tr')[1:]:
            cells = tr.find_all('td', recursive=False)
            if len(cells) < 2:
                continue
            name = ' '.join(cells[0].get_text(' ', strip=True).split())
            title = ' '.join(cells[1].get_text(' ', strip=True).split())
            if not re.search(r'\b(?:Professor|Lecturer|Instructor)\b', title, re.I):
                continue
            link = cells[0].select_one('a[href]')
            if name and title:
                out.append(dict(name_listed=name, titles=[title], homepage=None,
                                division=None, profile=link['href'] if link else None))
    return out


def nus_cs_inline_roster(h):
    """NUS CS page's source-embedded faculty arrays; receipts quote the raw source code."""
    out, seen = [], set()
    for suffix in ('', '_research', '_teaching', '_adjunct', '_courtesy'):
        block = re.search(r'\$scope\.allStaffs' + suffix + r'\s*=\s*\[(.*?)\n\s*\];', h, re.S)
        if not block:
            continue
        body = block.group(1)
        pat = re.compile(r'\{\s*name:\s*"(?P<name>(?:\\.|[^"\\])*)"\s*,\s*title:\s*"(?P<title>(?:\\.|[^"\\])*)"', re.S)
        matches = list(pat.finditer(body))
        for i, m in enumerate(matches):
            name = H.unescape(m.group('name')).strip()
            title = H.unescape(m.group('title')).strip()
            if not name or not re.search(r'\b(?:Professor|Lecturer|Instructor)\b', title, re.I):
                continue
            segment = body[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(body)]
            dept = re.search(r'\bDept:\s*"([^"]+)"', segment)
            if dept and dept.group(1) != '252':
                continue
            bio = re.search(r'\bBio:\s*"([^"\\]*)"', segment)
            key = (name, title)
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=bio.group(1) if bio else None,
                            quote_raw=m.group(0)))
    return out


def nus_cs_any(h):
    return nus_cs_inline_roster(h) if '$scope.allStaffs' in h else nus_cs_legacy_tables(h)


def cuhk_cse_faculty_table(h):
    """CUHK CSE's faculty table: preserve the printed name, position and profile."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for tr in soup.select('table.foo-table tr'):
        cells = tr.find_all('td', recursive=False)
        if len(cells) < 6:
            continue
        name = ' '.join(cells[1].get_text(' ', strip=True).split())
        title = ' '.join(cells[5].get_text(' ', strip=True).split())
        profile = cells[1].select_one('a[href]')
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=profile['href'] if profile else None))
    return out


def cuhk_erg_cse_directory(h):
    """Engineering faculty index, restricted to its CSE department label."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.view-content .people-wrap'):
        department = card.select_one('.people-dept-wrap')
        name_el = card.select_one('.people-name-wrap')
        title_el = card.select_one('.people-title-wrap')
        if not department or not name_el or not title_el:
            continue
        dept = ' '.join(department.get_text(' ', strip=True).split())
        if dept not in {'Computer Science and Engineering', 'Computer Science & Engineering'}:
            continue
        name = ' '.join(name_el.get_text(' ', strip=True).split())
        title = ' '.join(title_el.get_text(' ', strip=True).split())
        link = card.select_one('.people-website a[href]')
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=link['href'] if link else None))
    return out


def cuhk_cse_profile_cards(h):
    """The complete 2018 CSE faculty page: one named card and position per person."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.facultyppl-container .people-list-item'):
        name_el = card.select_one('h3')
        title_el = card.select_one('.field-value.position')
        if not name_el or not title_el:
            continue
        name = ' '.join(name_el.get_text(' ', strip=True).split())
        title = ' '.join(title_el.get_text(' ', strip=True).split())
        profile = name_el.find_parent('a', href=True)
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=profile['href'] if profile else None))
    return out


def cuhk_cse_any(h):
    """One charter slot spans the Engineering directory and CSE's historical layouts."""
    if 'people-dept-wrap' in h:
        return cuhk_erg_cse_directory(h)
    if 'facultyppl-container' in h:
        return cuhk_cse_profile_cards(h)
    return cuhk_cse_faculty_table(h)


def ustc_cs_cards(h):
    """USTC CS rank pages: the heading is the appointment title, each news card is one person."""
    soup = BeautifulSoup(h, 'html.parser')
    heading = soup.select_one('li.col_title h2')
    title = heading.get_text(' ', strip=True) if heading else ''
    if not title:
        return []
    out = []
    for card in soup.select('.col_news_list.listcon li.news'):
        link = card.select_one('.news_title a[href]')
        if not link:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        if name:
            out.append(dict(name_listed=name, titles=[title], homepage=None, division=None,
                            profile=link['href']))
    return out


def uestc_college_teachers(h):
    """UESTC college-specific faculty cards; one of PAGENUM's roster pages."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.ex_img > ul > li'):
        link = card.select_one('h2 a[href]')
        title = card.select_one('span > p')
        if not link or not title:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        rank = ' '.join(title.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href']))
    return out


def pku_cs_cards(h):
    """PKU School of Computer Science 教研系列 (2023-09- cs.pku.edu.cn/szdw/jyxl/amz/ALL.htm): `ul.list15 li` cards, `h3 big` the name, `p` lines
    `职称：...` (title), `研究所：...` (institute). The ALL page lists every name on one page."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for li in soup.select('ul.list15 li'):
        big = li.select_one('h3 big')
        if not big:
            continue
        a = li.find('a', href=True)
        name = re.sub(r'[\s\u3000]+', '', big.get_text())
        fields = {}
        for p in li.select('p'):
            m = re.match(r'\s*(职称|研究所)[：:]\s*(.+)', p.get_text(' ', strip=True))
            if m:
                fields[m.group(1)] = ' '.join(m.group(2).split())
        if name and fields.get('职称'):
            out.append(dict(name_listed=name, quote_name=' '.join(big.get_text().split()), titles=[fields['职称']], profile=a['href'] if a else None,
                            homepage=None, division=fields.get('研究所')))
    return out


def pku_cs_namelist(h):
    """PKU Department of Computer Science and Technology 教研系列 (2020-2023 cs.pku.edu.cn/szdw1/jyxl.htm and its letter pages): `ul#teachernamelist li`
    with `h4 a` the name, then two `p` lines, the title and the institute."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for li in soup.select('ul#teachernamelist li'):
        a = li.select_one('h4 a')
        ps = [' '.join(p.get_text(' ', strip=True).split()) for p in li.select('.txt p')]
        if not a or not ps:
            continue
        name = re.sub(r'[\s\u3000]+', '', a.get_text())
        if name:
            out.append(dict(name_listed=name, quote_name=' '.join(a.get_text().split()), titles=[ps[0]], profile=a['href'], homepage=None,
                            division=ps[1] if len(ps) > 1 else None))
    return out


def uestc_scse_bands(h):
    """UESTC School of Computer Science and Engineering 师资介绍 (www.scse.uestc.edu.cn/sz.jsp?urltype=tree.TreeTempUrl&wbtreeid=1081, 2019-2020): `div.list`
    blocks, `.listHead span` the professional-title band printed (正高, 副高, 中级及以下) and `.listBody a` one link per teacher. The band is the title as printed."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for blk in soup.select('div.list'):
        head = blk.select_one('.listHead span')
        band = ' '.join(head.get_text(' ', strip=True).split()) if head else ''
        if not band:
            continue
        for a in blk.select('.listBody a[href]'):
            name = re.sub(r'[\s\u3000]+', '', a.get_text())
            if name:
                out.append(dict(name_listed=name, quote_name=' '.join(a.get_text().split()), titles=[band], profile=a['href'], homepage=None, division=None))
    return out


def hit_cs_current_table(h):
    """HIT Faculty of Computing roster: only its explicitly headed CS school."""
    soup = BeautifulSoup(h, 'html.parser')
    heading = soup.find(string=lambda text: text and text.strip() == '计算机科学与技术学院')
    table = heading.find_next('table') if heading else None
    if table is None:
        return []
    out = []
    group = None
    for row in table.select('tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) == 1 and int(cells[0].get('colspan', 1)) > 1:
            group = ' '.join(cells[0].get_text(' ', strip=True).split())
            continue
        for cell in cells:
            if int(cell.get('colspan', 1)) > 1:
                continue
            name = ' '.join(cell.get_text('', strip=False).split())
            if name:
                out.append(dict(name_listed=name, titles=['教师'], homepage=None,
                                division=group, profile=None))
    return out


def hit_teacher_list(h):
    """HIT's 2018 Webplus all-teacher directory, one page of its six-page list.

    The directory identifies people as teachers but does not print an
    individual academic rank. Dates alongside names are article dates.
    """
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for row in soup.select('#wp_news_w6 .wp_article_list_table tr'):
        link = next((a for cell in row.find_all('td', recursive=False)
                     if (a := cell.find('a', href=True, title=True, recursive=False))), None)
        if not link:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        if name and name == link.get('title', '').strip():
            out.append(dict(name_listed=name, titles=['教师'], homepage=None,
                            division=None, profile=link['href']))
    return out


def princeton_cs_faculty(h):
    """Princeton CS's unpaged faculty directory, preserving printed titles."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for row in soup.select('.people-facstaff .person'):
        name_field = row.select_one('h2.person-name')
        link = name_field.select_one('a[href]') if name_field else None
        title = row.select_one('.person-title')
        if not name_field or not title:
            continue
        name = ' '.join((link or name_field).get_text(' ', strip=True).split())
        rank = ' '.join(title.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href'] if link else None))
    for row in soup.select('.custom_card__container.people li.custom_card'):
        link = row.select_one('h3.custom_card__heading a[href]')
        title = row.select_one('.custom_card__snippet .position, .custom_card__snippet .title')
        if not link or not title:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        rank = ' '.join(title.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href']))
    return out


def mit_eecs_legacy_faculty(h):
    """EECS Faculty & Advisors, 2016–2021 Drupal directory."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for row in soup.select('ul.faculty-list > li.views-row'):
        name_field = row.select_one('.views-field-title .card-title')
        link = name_field.select_one('a[href]') if name_field else None
        title = row.select_one('.views-field-field-person-title')
        if not name_field or not title:
            continue
        name = ' '.join(name_field.get_text(' ', strip=True).split())
        rank = ' '.join(title.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href'] if link else None))
    return out


def mit_eecs_faculty_cards(h):
    """EECS faculty-only role page after the 2021 site redesign."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.facetwp-template .people-entry'):
        link = card.select_one('h5 a[href]')
        title = card.find('p', recursive=False)
        if not link or not title:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        rank = ' '.join(title.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href']))
    return out


def whu_cs_legacy(h):
    """2016–2018 Wuhan CS directory: named records with one printed rank."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for row in soup.select('.j_name_num dd.j_name'):
        link = row.select_one('.name a[href]')
        rank = row.select_one('.job_name')
        if not link or not rank:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        title = ' '.join(rank.get_text(' ', strip=True).split())
        # The source also embeds empty templates and ambiguous composite
        # ranks ("教授,副教授,讲师"); neither establishes one appointment.
        if name and title in {'教授', '副教授', '讲师'}:
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=link['href']))
    return out


def whu_cs_zrjs(h):
    """2022+ Wuhan CS full-time faculty rows, excluding navigation and sex fields."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for row in soup.select('.teacher-list-item ul.li-xinxi li'):
        link = row.select_one('.name a[href]')
        rank = row.select_one('.zhichen')
        if not link or not rank:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        title = ' '.join(rank.get_text(' ', strip=True).split())
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=link['href']))
    return out


def whu_cs_talents(h):
    """Wuhan CS high-level talents: named cards and their printed rank."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.talent-item li a[href]'):
        name_el, rank = card.select_one('.title'), card.select_one('.technical')
        if not name_el or not rank:
            continue
        name = ' '.join(name_el.get_text(' ', strip=True).split())
        title = ' '.join(rank.get_text(' ', strip=True).split())
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None,
                            division=None, profile=card['href']))
    return out


def whu_cs_emeritus(h):
    """Retired-faculty list; the page heading supplies the role category."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for link in soup.select('.teacher-list.honored .teacher-list-item li a'):
        name = ' '.join(link.get_text(' ', strip=True).split())
        if name:
            out.append(dict(name_listed=name, titles=['退休教师'], homepage=None,
                            division=None, profile=None))
    return out


def seu_department_faculty(h):
    """SEU's embedded teachers-by-department tables; exclude staff and lab admin tables."""
    soup = BeautifulSoup(h, 'html.parser')
    tables = soup.select('.desktop-view table') or soup.select('.wp_articlecontent table')[:3]
    academic = {'计算机科学系', '计算机工程系', '影像科学与技术系'}
    legacy = not tables
    if legacy:
        tables = [table for table in soup.select('table.table-name')
                  if table.find_previous('h2') and clean(table.find_previous('h2').get_text(' ', strip=True)) in academic]
    out, seen = [], set()
    for table in tables:
        heading = table.find_previous('h2')
        division = clean(heading.get_text(' ', strip=True)) if heading else None
        if division in {'学院机关', '计算中心'}:
            continue
        for cell in table.select('td'):
            if cell.find('table'):
                continue
            name = clean(cell.get_text())
            link = cell.select_one('a[href]')
            profile = link['href'] if link else None
            if legacy and profile and profile.startswith('/'):
                profile = 'http://cse.seu.edu.cn' + profile
            if not name or (profile is not None and (name, profile) in seen):
                continue
            seen.add((name, profile))
            # The source certifies a teacher in one of the three academic
            # departments, but does not print a professor/lecturer rank.
            out.append(dict(name_listed=name, titles=['教师'], homepage=None,
                            division=division if division in academic else None, profile=profile))
    return out


def utaustin_cs_people(h):
    """UT Austin CS Drupal faculty/researcher cards, with the listed appointment title."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.views-row, .faculty-and-researchers'):
        link = card.select_one('.views-field-title a[href^="/people/faculty-researchers/"]')
        title = card.select_one('.views-field-field-contact-faculty-title .field-content')
        if not link or not title:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        rank = ' '.join(title.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href']))
    for card in soup.select('.node-facstaff-directory-page'):
        link = card.select_one('.field-name-title a[href^="/people/faculty-researchers/"]')
        title = card.select_one('.field-name-field-faculty-title .field-item, '
                                '.field-name-field-contact-faculty-title .field-item')
        if not link or not title:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        rank = ' '.join(title.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href']))
    return out


def purdue_cs_people(h):
    """Purdue CS faculty cards with source-stated role and profile URL."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.people-item'):
        link = card.select_one('.people-name a[href]')
        title = card.select_one('.people-title')
        if not link or not title:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        role = ' '.join(title.get_text(' ', strip=True).split())
        if name and role:
            out.append(dict(name_listed=name, titles=[role], homepage=None,
                            division=None, profile=link['href']))
    if not out:
        for tr in soup.select('table.directory tr'):
            cells = tr.find_all('td', recursive=False)
            if len(cells) < 2:
                continue
            name = ' '.join(cells[0].get_text(' ', strip=True).split())
            role = ' '.join(cells[1].get_text(' ', strip=True).split())
            profile = tr.select_one('a[href*="/people/faculty/"]')
            if name and role:
                out.append(dict(name_listed=name, titles=[role], homepage=None,
                                division=None, profile=profile['href'] if profile else None))
    return out


def utaustin_cs_faculty_legacy(h):
    """The older UT Austin CS /faculty directory exposes names, ranks and profile links."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for card in soup.select('.views-row'):
        block = card.select_one('.views-field-nothing .field-content')
        name_el = block.select_one('.prof-name') if block else None
        profile = card.select_one('.views-field-view-user a[href^="/directory/"]')
        fixed_title = card.select_one('.views-field-field-user-title .field-content')
        if name_el is None and profile is None:
            profile = card.select_one('.views-field-nothing strong a[href^="/directory/"]')
            name_el = profile.parent if profile else None
        elif name_el is not None:
            profile = block.select_one('a[href^="/directory/"]')
        if not name_el and not profile:
            continue
        name = ' '.join((name_el or profile).get_text(' ', strip=True).split())
        if fixed_title:
            title = ' '.join(fixed_title.get_text(' ', strip=True).split())
        else:
            title_parts = []
            for node in name_el.next_siblings:
                if getattr(node, 'name', None) == 'br' and title_parts:
                    break
                if getattr(node, 'name', None) != 'br':
                    part = node.get_text(' ', strip=True) if hasattr(node, 'get_text') else str(node).strip()
                    if part:
                        title_parts.append(part)
            title = ' '.join(' '.join(title_parts).split())
        home = next((a.get('href') for a in card.select('a[href]')
                     if a.get_text(' ', strip=True).lower() == 'homepage'), None)
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=home,
                            division=None, profile=profile.get('href') if profile else None))
    return out


def ustc_cs_legacy_sidebar(h):
    """The 2016–2020 CS site embeds dated rank rosters beside faculty profiles."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for heading in soup.select('a.gk'):
        title = heading.get_text(' ', strip=True)
        if title not in {'院士', '大师讲席', '教授', '副教授'}:
            continue
        table = heading.find_next('table')
        if not table:
            continue
        for link in table.select('a[href]'):
            href = link.get('href') or ''
            if not re.search(r'(?:/page\.htm|\.html)$', href):
                continue
            name = ' '.join(link.get_text(' ', strip=True).split())
            if name and '名单' not in name:
                out.append(dict(name_listed=name, titles=[title], homepage=None, division=None,
                                profile=href))
    return out


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


def jhu_cs_faculty_card(h):
    """Johns Hopkins CS WordPress faculty cards in the stored 2016–2019 listings.

    A card's h3 names the person and its h6, when present, gives the written appointment;
    image alt text and research-group links are not faculty-list entries.
    """
    out = []
    for p in re.split(r'<div\b[^>]*class="highlight-box faculty-member-card"[^>]*>', h)[1:]:
        name = re.search(r'<h3\b[^>]*>(.*?)</h3>', p, re.S)
        title = re.search(r'<h6\b[^>]*>(.*?)</h6>', p, re.S)
        if not name:
            continue
        link = re.search(r'<a\b[^>]*href="([^"]+)"', name.group(1))
        out.append(dict(name_listed=clean(name.group(1)), titles=_titles(title.group(1)) if title else [],
                        homepage=H.unescape(link.group(1)) if link else None, division=None))
    return out


def jhu_bme_faculty(h):
    """BME's faculty directory cards; credentials are not part of person names."""
    out = []
    for card in re.split(r'<div\s+class="zn-faculty-profile\s*"[^>]*>', h)[1:]:
        name = re.search(r'<div class="zn-name">(.*?)</div>', card, re.S)
        title = re.search(r'<div class="zn-position">(.*?)</div>', card, re.S)
        if not name:
            continue
        link = re.search(r'<a\b[^>]*href="([^"]+)"', name.group(1))
        printed = clean(name.group(1))
        person = re.sub(r'(?:,\s*(?:MD|MSE|MS|PhD|ScD|MPH))+$', '', printed, flags=re.I)
        out.append(dict(name_listed=person, titles=_titles(title.group(1)) if title else [],
                        homepage=H.unescape(link.group(1)) if link else None, division=None))
    return out


def jhu_bme_complete_faculty(h):
    """BME's older complete-faculty tables, including explicit appointment groups."""
    soup = BeautifulSoup(h, 'html.parser')
    main = soup.select_one('#main-content')
    if not main or 'JHU BME complete faculty listing' not in main.get_text(' ', strip=True):
        return []
    out = []
    for table in main.select('table.stripe'):
        heading = table.find_previous('h2')
        division = heading.get_text(' ', strip=True) if heading and heading in main.descendants else None
        for tr in table.select('tr'):
            cells = tr.select('td.people')
            if len(cells) != 2:
                continue
            printed = ' '.join(cells[0].stripped_strings)
            person = re.sub(r'(?:,\s*(?:MD|MSE|MS|PhD|ScD|MPH))+$', '', printed, flags=re.I)
            title = ' '.join(cells[1].stripped_strings)
            if len(person.split()) < 2 or not title:
                continue
            link = cells[0].find('a', href=True)
            out.append(dict(name_listed=person, titles=[title],
                            homepage=link['href'] if link else None, division=division))
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


def uw_allen_cards(h):
    """Allen School cards: a name link (aria-label "Read the bio for ...") opens each card; heading paragraphs up to the next name link are its titles."""
    out, cur = [], None
    for m in re.finditer(r'<p class="elementor-heading-title[^"]*">(.*?)</p>', h, re.S):
        body = m.group(1)
        link = re.search(r'<a href="([^"]+)" aria-label="Read the bio for', body)
        if link:
            cur = dict(name_listed=clean(body), titles=[], homepage=H.unescape(link.group(1)), division=None)
            out.append(cur)
        elif cur is not None and clean(body):
            cur['titles'].append(clean(body))
    return out



def uw_allen_directory(h):
    """Allen School faculty directory before the 2025 redesign: 2016's Drupal view (div.people-short-listing-name) and the 2017-2024
    Bootstrap rows (div.directory-name). The page states no per-person rank; every entry sits under the page heading 'Faculty', which
    is recorded as the title (census rank 'other' unless a dated profile gives the rank)."""
    out, seen = [], set()
    for m in re.finditer(r"<div class=['\"](?:directory-name|people-short-listing-name)['\"]>\s*<a href=['\"]([^'\"]+)['\"]>\s*([^<]+?)\s*</a>", h):
        name = clean(m.group(2))
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(dict(name_listed=name, titles=['Faculty'], homepage=H.unescape(m.group(1)), division=None))
    return out


def uw_ee_mainlist(h):
    """UW Electrical Engineering faculty table of 2016-17 (www.ee.washington.edu / www2.ee.washington.edu /people/faculty/, table.mainlist):
    one row per person, '<strong><a href=...>Surname, Given</a></strong>' (the link is optional). The page states no per-person rank (the
    chair table above it is not the list); 'Faculty' is recorded as the title (census rank 'other' unless a dated profile gives the rank)."""
    m = re.search(r'<table class="mainlist">(.*?)</table>', h, re.S)
    if not m:
        return []
    out, seen = [], set()
    for r in re.finditer(r'<td nowrap>\s*<strong>\s*(?:<a href="([^"]+)">)?\s*([^<]+?)\s*(?:</a>)?\s*</strong>', m.group(1)):
        listed = clean(r.group(2))
        sur, _, given = listed.partition(',')
        given = re.sub(r'\s*\([^)]*\)', '', given).strip()
        name = f'{given} {sur.strip()}'.strip() if given else listed
        if not name or name in seen or len(name.split()) < 2:
            continue
        seen.add(name)
        out.append(dict(name_listed=name, quote_name=listed, titles=['Faculty'], homepage=H.unescape(r.group(1)) if r.group(1) else None, division=None))
    return out


def uw_stat_people(h):
    """UW Statistics people view (stat.uw.edu/people/faculty): span.person-name holds the name link; field-position the rank
    (plus the named position and job title as further titles)."""
    out = []
    for blk in re.split(r'<div class="faculty-column', h)[1:]:
        nm = re.search(r'<span class="field-content person-name"><a href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not nm:
            continue
        titles = []
        for fld in ('field-position', 'field-named-faculty-position', 'field-job-title'):
            m = re.search(r'views-field-' + fld + r'"><[a-z]+ class="field-content">(.*?)</(?:strong|em|div)>', blk, re.S)
            if m and clean(m.group(1)):
                titles.append(clean(m.group(1)))
        out.append(dict(name_listed=clean(nm.group(2)), titles=titles, homepage=H.unescape(nm.group(1)), division=None))
    return out

def uw_ece_staff(h):
    out = []
    for p in re.split(r'<div class="stafftemplate--entry">', h)[1:]:
        nm = re.search(r'<span class="stafftemplate--name">(.*?)</span>', p, re.S)
        if not nm:
            continue
        tt = re.search(r'<span class="stafftemplate--title">(.*?)</span>', p, re.S)
        link = re.search(r'<a href="([^"]+)"', nm.group(1))
        out.append(dict(name_listed=clean(nm.group(1)), titles=[x.strip() for x in clean(tt.group(1)).split(';') if x.strip()] if tt else [],
                        homepage=H.unescape(link.group(1)) if link else None, division=None))
    return out


def uw_ischool_card(h):
    out = []
    for m in re.finditer(r'<article aria-label="[^"]*" id="card-[^"]*" class="card clearfix" data-type="([^"]*)"(.*?)</article>', h, re.S):
        p = m.group(2)
        nm = re.search(r'<h2 class="h1">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', p, re.S)
        if not nm:
            continue
        tt = re.search(r'<p class="small">(.*?)</p>', p, re.S)
        out.append(dict(name_listed=clean(nm.group(2)), titles=_titles(tt.group(1)) if tt else [], homepage=H.unescape(nm.group(1)), division=m.group(1)))
    return out


def uw_amath_directory(h):
    out = []
    for p in re.split(r'<h2 class="directory-item__name">', h)[1:]:
        nm = re.match(r'\s*<a href="([^"]+)"[^>]*>(.*?)</a>', p, re.S)
        if not nm:
            continue
        tt = re.search(r'<strong class="directory-item__title">(.*?)</strong>', p, re.S)
        out.append(dict(name_listed=clean(nm.group(2)), titles=_titles(tt.group(1)) if tt else [], homepage=H.unescape(nm.group(1)), division=None))
    return out


def uw_hcde_columns(h):
    out = []
    for m in re.finditer(r'<h2><a href="([^"]+)"[^>]*><strong>(.*?)</strong></a></h2>\s*<p>(.*?)</p>', h, re.S):
        out.append(dict(name_listed=clean(m.group(2)), titles=_titles(m.group(3)), homepage=H.unescape(m.group(1)), division=None))
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
        role = re.search(r'<td[^>]*class="views-field views-field-field-(?:sd-classifications-ref|tax-singular)"[^>]*>(.*?)</td>', row, re.S)
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


def cambridge_academic_staff(h):
    """The department's 2016–2020 academic-staff directory, not its all-person list."""
    soup = BeautifulSoup(h, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    table = soup.select_one('table.directory')
    if 'Academic staff' not in title or table is None:
        return []
    out = []
    for tr in table.select('tr'):
        cell = tr.select_one('td.name')
        if cell is None:
            continue
        printed = cell.get_text(' ', strip=True)
        person = re.sub(r',\s*(?:Prof(?:essor)?|Dr)\.?\s+', ', ', printed, flags=re.I)
        if len(person.split()) < 2:
            continue
        link = cell.find('a', href=True)
        # Keep the printed spelling for exact evidence lookup: removing Dr/Prof
        # from the normalized name must not drop the whole historical row.
        rank = re.search(r',\s*(Prof(?:essor)?)\.?\s+', printed, re.I)
        entry = dict(name_listed=person, titles=[rank.group(1) if rank else 'Academic staff'],
                     homepage=link['href'] if link else None, division='Academic staff')
        if printed != person:
            entry['quote_name'] = printed
        out.append(entry)
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


def epfl_ic_legacy(h):
    """EPFL IC's 2016–2017 sectioned professor list (ic.epfl.ch/professors).

    The cards omit personal job titles. Keep the page's section as the
    appointment category, including courtesy, adjunct, scientist and honorary.
    """
    section_titles = {
        'Professors': 'Professor',
        'Professeurs': 'Professor',
        'Courtesy Appointments': 'Courtesy Appointment',
        'Senior Scientists': 'Senior Scientist',
        "Maîtres d'enseignement et de recherche": "Maître d'enseignement et de recherche",
        'External adjunct Professors': 'External adjunct Professor',
        'Professeurs titulaires externes': 'Professeur titulaire externe',
        'Honorary Professors': 'Honorary Professor',
        'Professeurs honoraires': 'Professeur honoraire',
    }
    out = []
    for section in re.split(r'<div\b[^>]*class="\s*htmlBox"[^>]*>', h)[1:]:
        heading = re.search(r'<h2\b[^>]*>(.*?)</h2>', section, re.S)
        category = clean(heading.group(1)) if heading else ''
        title = section_titles.get(category)
        if not title:
            continue
        for card in re.split(r'<div\s+class="g-span-1_4"[^>]*>', section)[1:]:
            name = re.search(r'<h2\b[^>]*itemprop="name"[^>]*>(.*?)</h2>', card, re.S)
            if not name:
                continue
            link = re.search(r'<a\b[^>]*href="([^"]+)"', name.group(1))
            out.append(dict(name_listed=clean(name.group(1)), titles=[title],
                            homepage=H.unescape(link.group(1)) if link else None, division=category))
    return out


def epfl_ic_contact(h):
    """EPFL IC's 2019–2026 contact list with explicit per-person job titles."""
    out = []
    for card in re.split(r'<div\b[^>]*class="contact-list-row"[^>]*>', h)[1:]:
        name = re.search(r'<a\b(?=[^>]*itemprop="name")[^>]*>(.*?)</a\s*>', card, re.S)
        title = re.search(r'<p\b(?=[^>]*itemprop="jobTitle")[^>]*>(.*?)</p\s*>', card, re.S)
        if not name:
            continue
        link = re.search(r'href="([^"]+)"', name.group(0))
        out.append(dict(name_listed=clean(name.group(1)), titles=_titles(title.group(1)) if title else [],
                        homepage=H.unescape(link.group(1)) if link else None, division=None))
    return out


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


def toronto_legacy_faculty(h):
    """The pre-2019 DCS faculty.htm tables: faculty, cross appointments, status-only.

    The old page has no rank column. Preserve the section as the title instead of
    inventing a professorial rank from a name in the directory.
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    out = []
    sections = {
        ('NAME', 'PHONE', 'EMAIL', 'OFFICE'): 'Faculty',
        ('NAME', 'DEPARTMENT'): 'Cross-appointed Faculty',
        ('NAME', 'AFFILIATION'): 'Status-only and Adjunct Faculty',
    }
    for table in BeautifulSoup(h, 'html.parser').find_all('table'):
        rows = table.find_all('tr')
        if not rows:
            continue
        header = tuple(clean(cell.get_text(' ', strip=True)).upper() for cell in rows[0].find_all(['td', 'th']))
        section = sections.get(header)
        if not section:
            continue
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'], recursive=False)
            if not cells:
                continue
            name = clean(cells[0].get_text(' ', strip=True))
            if not name or name.upper() == 'NAME':
                continue
            link = cells[0].find('a', href=True)
            out.append(dict(name_listed=name, titles=[section],
                            profile=urljoin('http://web.cs.toronto.edu/', link['href']) if link else None,
                            homepage=None, division=None))
    return out


def toronto_full_directory(h):
    """One complete 2019-2021 DCS directory page across all named sections."""
    out, seen = [], set()
    for section in ('researchstream', 'teachingstream', 'emeriti', 'crossappointed', 'statusonly', 'adjunct'):
        for row in toronto_directory(h, section):
            key = (row['name_listed'].casefold(), tuple(row['titles']))
            if key not in seen:
                out.append(row)
                seen.add(key)
    if out:
        return out

    # The 2019 Squarespace layout used h2 section headings and h3 person cards
    # instead of the later tables. Keep the written rank immediately after each
    # name, and retain its section so cross appointments are not lost.
    from bs4 import BeautifulSoup
    sections = {'Teaching Stream Faculty', 'Tenure Stream Faculty', 'Professors Emeriti',
                'Cross-Appointed Faculty', 'Status-Only Faculty', 'Adjunct Faculty'}
    section = None
    for tag in BeautifulSoup(h, 'html.parser').find_all(['h2', 'h3']):
        if tag.name == 'h2':
            label = clean(tag.get_text(' ', strip=True))
            section = label if label in sections else None
            continue
        if not section:
            continue
        name = clean(tag.get_text(' ', strip=True))
        if not name:
            continue
        link = tag.find('a', href=True)
        rank = clean(str(tag.next_sibling or ''))
        titles = [rank, section] if rank and len(rank) < 100 else [section]
        key = (name.casefold(), tuple(titles))
        if key not in seen:
            out.append(dict(name_listed=name, titles=titles,
                            homepage=H.unescape(link['href']).strip() if link else None,
                            division=None))
            seen.add(key)
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
        printed = ' '.join((a.get('title') or a.get_text()).split())
        name = re.sub(r'[\s\u3000]+', '', printed)
        if name:
            out.append(dict(name_listed=name, quote_name=printed, titles=[], profile=a['href'], homepage=None, division=division))
    return out


def zju_cs_en_faculty_list(h):
    """ZJU College of Computer Science and Technology English-site Faculty Directory (www.en.cs.zju.edu.cn/{rgznyjs,jsjrjyjs,jsjxtjgywlaqyjs,gysjyjs,22164}/list.htm, one list per
    research institute, `div.tearch_class` names it; the 2023 site adds one combined page faculty_lists/list.htm with a `li.wp_sublist` per institute): each teacher is `span.Article_Title a[title]`, printed as pinyin `Family Given` (Zhuang Yueting); names only, no rank."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for sub in soup.select('li.wp_sublist'):  # the 2023 combined page "Faculty Lists (by research institutes)": one sub-list per institute
        title = sub.select_one('h3.sublist_title a')
        division = clean(title.get_text(' ', strip=True)) if title else None
        for a in sub.select('ul.t_name_list li a'):
            printed = ' '.join(a.get_text().split())
            if printed:
                out.append(dict(name_listed=printed, quote_name=printed, titles=[], profile=a.get('href'), homepage=None, division=division))
    if out:
        return out
    inst = soup.select_one('div.tearch_class')
    division = clean(inst.get_text(' ', strip=True)) if inst else None
    for a in soup.select('ul.wp_article_list span.Article_Title a'):
        printed = ' '.join((a.get('title') or a.get_text()).split())
        if printed:
            out.append(dict(name_listed=printed, quote_name=printed, titles=[], profile=a.get('href'), homepage=None, division=division))
    return out


def zju_cs_old_jiaoshiml(h):
    """Zhejiang College of Computer Science 教师名录, the 2016-2019 PHP site (redir.php?cust=jiaoshiml&id=256, served GB2312): one `<table>` per institute,
    its `<th>` is the institute and each teacher is `<td class="szdw"><div><a href=...object_id=N>name</a>`. Names only (no rank); full-width spaces collapsed."""
    from bs4 import BeautifulSoup
    out = []
    for table in BeautifulSoup(h, 'html.parser').find_all('table'):
        th = table.find('th')
        division = clean(th.get_text(' ', strip=True)) if th else None
        for a in table.select('td.szdw div a[href]'):
            printed = ' '.join(a.get_text().split())
            name = re.sub(r'[\s\u3000]+', '', printed)
            if name:
                out.append(dict(name_listed=name, quote_name=printed, titles=[], profile=a['href'], homepage=None, division=division))
    return out


def zju_cad_fixed_researchers(h):
    """ZJU State Key Lab of CAD&CG 实验室固定研究人员 (www.cad.zju.edu.cn/Agencyteam/Innovationteam/130.html, 2016-2020): one table, the first cell of each row is
    `name<full-width space>title` (a second line may add （院士）). The printed first cell is the quote; research direction and contact cells are never kept."""
    from bs4 import BeautifulSoup
    out = []
    for tr in BeautifulSoup(h, 'html.parser').select('div.zhuwenn table tr'):
        tds = tr.find_all('td')
        if len(tds) < 2:
            continue
        printed = ' '.join(tds[0].get_text(' ', strip=True).replace('\xa0', ' ').split())
        m = re.match(r'^(\S(?:[\S ]{0,6}?\S)?)\s*(副教授|教授|副研究员|研究员|助理教授|讲师|高级工程师|工程师|博士后|博士)(.*)$', printed)
        if not m:
            continue
        name = re.sub(r'\s+', '', m.group(1))
        if 1 < len(name) <= 4:
            out.append(dict(name_listed=name, quote_name=printed.split(m.group(2))[0].strip() + ' ' + m.group(2), titles=[m.group(2)], profile=None, homepage=None,
                            division='实验室固定研究人员'))
    return out


def zju_cad_fixed_researchers_2025(h):
    """ZJU State Key Lab of CAD&CG 固定研究人员 on the 2025 WordPress/Elementor site (www.cad.zju.edu.cn/innovationteam): rank headings (`h2.elementor-heading-title`:
    院士, 教授/长聘教授, 百人计划研究员, 副教授/长聘副教授, 特聘研究员、专职研究员) each followed by `|`-separated name paragraphs. A name's title is the heading above it;
    the quote is the name plus that heading (an explicit omission between them)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(h, 'html.parser')
    out, heading, started = [], None, False
    for el in soup.select('h2.elementor-heading-title, div.elementor-widget-text-editor p'):
        text = ' '.join(el.get_text(' ', strip=True).split())
        if el.name == 'h2':
            if text == '院士':
                started = True
            if started:
                heading = text
            continue
        if not started or heading is None or not re.fullmatch(r'[\u4e00-\u9fff]{2,4}', text):
            continue
        out.append(dict(name_listed=text, quote_parts=[text, heading], titles=[heading], profile=(el.find('a') or {}).get('href'), homepage=None,
                        division='固定研究人员'))
    return out


def zju_cst_szdw_names(h):
    """ZJU College of Software Technology 师资队伍 (www.cst.zju.edu.cn/szdw/list.htm, archived from 2024-01): one table in `div.wp_articlecontent`, one `<td><a title=name>` per
    teacher, names only (no rank). Full-width spaces inside a name (伍　赛) are collapsed for name_listed and kept (normalised to one space) for the quote."""
    from bs4 import BeautifulSoup
    out = []
    for a in BeautifulSoup(h, 'html.parser').select('div.wp_articlecontent table td a[href]'):
        printed = ' '.join(a.get_text(' ', strip=True).split())
        name = re.sub(r'[\s\u3000]+', '', printed)
        if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', name):
            out.append(dict(name_listed=name, quote_name=printed, titles=[], profile=a['href'], homepage=None, division=None))
    return out


def zju_isee_table(h):
    """ZJU College of Information Science and Electronic Engineering 师资队伍 (www.isee.zju.edu.cn/21034/list*.htm, the 2018-2019 paged table, 10 rows a page): each row's
    first cell is `<img alt=name>` plus the name, then rank, department (学系/研究所/院机关) and research cells. Rank '未填写' (not filled in) is no title; contact cells
    (phone, e-mail, office) are never kept. Staff rows (院机关) are kept with their printed department as the division."""
    from bs4 import BeautifulSoup
    out = []
    for tr in BeautifulSoup(h, 'html.parser').select('table tr'):
        tds = tr.find_all('td', recursive=False)
        if len(tds) < 4 or tds[0].find('img') is None:
            continue
        printed = ' '.join(tds[0].get_text(' ', strip=True).split())
        name = re.sub(r'[\s\u3000]+', '', printed)
        if not re.fullmatch(r'[\u4e00-\u9fff]{2,4}', name):
            continue
        rank = clean(tds[1].get_text(' ', strip=True))
        out.append(dict(name_listed=name, quote_name=printed, titles=[] if rank in ('', '未填写') else [rank], profile=None, homepage=None,
                        division=clean(tds[2].get_text(' ', strip=True)) or None))
    return out


def zju_ee_teach_list(h):
    """ZJU College of Electrical Engineering 教师队伍 (ee.zju.edu.cn/index.php?s=/Index/teacher/catid/17.html, 2018-2020): `div.teach-title` institute headings, each
    followed by `ul.teach-list` of `a.teach-wrap > h3` names (names only, no rank). The post-doctoral group (博士后) is not faculty and is skipped."""
    from bs4 import BeautifulSoup
    out = []
    soup = BeautifulSoup(h, 'html.parser')
    for it in soup.select('div.items div.introduce'):   # the 2018 template: name <h3>, department <dd>, printed title <dd> (the detail link is the last <dd>)
        h3 = it.find('h3')
        dds = [clean(d.get_text(' ', strip=True)) for d in it.find_all('dd') if not d.find('a')]
        printed = ' '.join(h3.get_text(' ', strip=True).split()) if h3 else ''
        m = re.match(r'^[A-Za-z\-. ]*\(?([\u4e00-\u9fff]{2,4})\)?$', printed)
        name = re.sub(r'[\s\u3000]+', '', printed) if re.fullmatch(r'[\u4e00-\u9fff\s\u3000]{2,5}', printed) else (m.group(1) if m else '')
        if name:
            out.append(dict(name_listed=name, quote_name=printed, titles=dds[1:2], profile=None, homepage=None, division=dds[0] if dds else None))
    if out:
        return out
    for ul in soup.select('ul.teach-list'):
        title = ul.find_previous('div', class_='teach-title')
        division = clean(title.get_text(' ', strip=True)) if title else None
        if division and '博士后' in division:
            continue
        for a in ul.select('a.teach-wrap'):
            h3 = a.find('h3')
            printed = ' '.join((h3 or a).get_text(' ', strip=True).split())
            name = re.sub(r'[\s\u3000]+', '', printed)
            if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', name):
                out.append(dict(name_listed=name, quote_name=printed, titles=[], profile=a.get('href'), homepage=None, division=division))
    return out


def zju_math_teachers_asp(h):
    """ZJU School of Mathematical Sciences 师资队伍 (www.math.zju.edu.cn/teachers.asp, ASP site 2016-2018, GB2312): a bold centred cell names the institute, the table after it holds
    one `<a href=teacher_intro.asp?userid=N>name</a>` per teacher. Names only (no rank)."""
    out = []
    division = None
    for m in re.finditer(r'font-weight:\s*bold">([^<]{2,30})</td>|<a href=teacher_intro\.asp\?userid=(\d+)[^>]*>([^<]+)</a>', h):
        if m.group(1):
            division = clean(m.group(1))
            continue
        printed = ' '.join(m.group(3).split())
        name = re.sub(r'[\s\u3000]+', '', printed)
        if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', name):
            out.append(dict(name_listed=name, quote_name=printed, titles=[], profile='teacher_intro.asp?userid=' + m.group(2), homepage=None, division=division))
    return out


def zju_cse_teacher_list(h):
    """ZJU College of Control Science and Engineering 师资队伍 (www.cse.zju.edu.cn/39568/list.htm, 2023-2025): `h3.research-name` institute headings, then `li.teacher-item > a`
    names (names only, no rank)."""
    from bs4 import BeautifulSoup
    out = []
    for h3 in BeautifulSoup(h, 'html.parser').select('h3.research-name'):
        division = clean(h3.get_text(' ', strip=True))
        ul = h3.find_next('ul', class_='teacher-list')
        for a in (ul.select('li.teacher-item a') if ul else []):
            printed = ' '.join(a.get_text(' ', strip=True).split())
            name = re.sub(r'[\s\u3000]+', '', printed)
            if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', name):
                out.append(dict(name_listed=name, quote_name=printed, titles=[], profile=a.get('href'), homepage=None, division=division))
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


_TS_SW_EN_ROLES={
 'Guest Professor':'Guest Professor',
 'Distinguished Visiting Professors':'Distinguished Visiting Professor',
 'Visiting Professor':'Visiting Professor',
 'Professors':'Professor',
 'Associate Professors':'Associate Professor',
 'Assistant Professors':'Assistant Professor',
}
_TS_SW_EN_HONORS={'Academician of Chinese Acadamy of Engineering','NSFC Distinguished Young Scholars Program Recipients'}
_TS_SW_EN_MAIN={'Professors','Associate Professors','Assistant Professors'}
_TS_SW_EN_BASE='https://www.thss.tsinghua.edu.cn/publish/soften/3553/index.html'
def _ts_sw_source_occurrences(h):
 soup=BeautifulSoup(h,'html.parser');box=soup.select_one('div.box_detail')
 if box is None or not box.find('h2') or clean(box.find('h2').get_text(' ',strip=True))!='Faculty':
  raise ValueError('SW English source lacks the Faculty article container')
 out=[];band=None;seen_bands=set()
 for p in box.find_all('p',recursive=False):
  strong=p.find('strong')
  if strong:
   band=clean(strong.get_text(' ',strip=True))
   if band not in _TS_SW_EN_ROLES and band not in _TS_SW_EN_HONORS:raise ValueError('Unreviewed SW faculty band: '+band)
   seen_bands.add(band)
  for a in p.find_all('a',href=True):
   shown=clean(a.get_text(' ',strip=True));name=shown.rstrip(',').strip()
   if not name or band is None:raise ValueError('SW source has an unnamed or unbanded person')
   link=urljoin(_TS_SW_EN_BASE,a['href']);u=urlsplit(link)
   if u.scheme not in ('http','https'):raise ValueError('SW source profile is not a public web link')
   # Only the literal siblings after this person's link can supply its qualifier.
   tail=[]
   for sibling in a.next_siblings:
    if getattr(sibling,'find',None) and getattr(sibling,'name',None) and sibling.find('a'):break
    if getattr(sibling,'name',None)=='a':break
    tail.append(sibling.get_text(' ',strip=True) if getattr(sibling,'name',None) else str(sibling))
   qualifier='on leave' if re.match(r'^\s*\(on leave\)',clean(' '.join(tail))) else None
   out.append(dict(name_listed=name,quote_name=shown,source_band=band,profile=link,qualifier=qualifier,appointment_band=band in _TS_SW_EN_ROLES,main_rank_band=band in _TS_SW_EN_MAIN))
 if not set(_TS_SW_EN_ROLES).issubset(seen_bands):raise ValueError('SW source lost a reviewed appointment band')
 return out

def tsinghua_sw_english_bands(h):
 occurrences=_ts_sw_source_occurrences(h);by_profile={}
 for p in occurrences:
  if not p['appointment_band']:continue
  key=p['profile'];role=_TS_SW_EN_ROLES[p['source_band']]
  if key in by_profile:raise ValueError('SW source repeats an appointment profile; resolve its role explicitly')
  titles=[role]+([p['qualifier']] if p['qualifier'] else [])
  by_profile[key]=dict(name_listed=p['name_listed'],titles=titles,profile=key,homepage=None,division=p['source_band'],quote_parts=[p['quote_name'],p['source_band']]+([p['qualifier']] if p['qualifier'] else []))
 # Every honorary occurrence must independently identify a real listed appointment.
 # Same profile plus same cleaned name establishes source-local deduplication only.
 for p in occurrences:
  if p['appointment_band']:continue
  existing=by_profile.get(p['profile'])
  if existing is None or existing['name_listed']!=p['name_listed']:raise ValueError('SW honor lacks matching individual appointment/profile')
 return list(by_profile.values())



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
    soup = BeautifulSoup(h, 'html.parser')
    content = soup.select_one('#vsb_content') or soup
    out, band = [], None
    for p in content.find_all('p'):
        text = clean(p.get_text(' ', strip=True).replace('\xa0', ' '))
        st = p.find('strong')
        label = clean(st.get_text('', strip=True)) if st else ''
        if st is not None and re.fullmatch(r'[^：:]{1,12}[：:]', label):
            band = clean(st.get_text('', strip=True)).rstrip('：:')
            if text == label:
                continue
        if band is None or not text:
            continue
        seen = set()
        for a in p.find_all('a', href=True):
            shown = clean(a.get_text(' ', strip=True))
            name = shown.replace(' ', '')
            if name:
                out.append(dict(name_listed=name, quote_name=shown, titles=[band], profile=a['href'], homepage=None, division=None)); seen.add(name)
        rest = clean(' '.join(t for t in p.find_all(string=True) if t.find_parent('a') is None and t.find_parent('strong') is None).replace('\xa0', ' '))
        for tok in rest.split():
            if tok not in seen and re.fullmatch(r'[\u4e00-\u9fff]{2,4}', tok):
                out.append(dict(name_listed=tok, titles=[band], profile=None, homepage=None, division=None))
    return out


def tsinghua_me_zh(h):
    """Tsinghua Mechanical Engineering 在职教师 list (szdw/zzjs.htm): `<a word="中级" title=NAME href=...>`; the `word` attribute is the same filter bucket on every row (checked: all 160 live rows say 中级), so it is never kept as a title: names only."""
    from bs4 import BeautifulSoup
    out = []
    for a in BeautifulSoup(h, 'html.parser').select('a[word][title][href]'):
        out.append(dict(name_listed=re.sub(r'[\s\u3000]+', '', a['title']), titles=[], profile=a['href'], homepage=None, division=None))
    return out


def tsinghua_me_en(h):
    """Tsinghua Mechanical Engineering English faculty list (en/People/Registered_Faculty): `<h2 class=sz_tit>Professor</h2>` bands, then `li.ss a[title]` cards."""
    from bs4 import BeautifulSoup
    out, band = [], None
    for el in BeautifulSoup(h, 'html.parser').select('h2.sz_tit, li.ss a[title][href]'):
        if el.name == 'h2':
            band = clean(el.get_text(' ', strip=True))
        elif band:
            out.append(dict(name_listed=clean(el['title']), titles=[band], profile=el['href'], homepage=None, division=None))
    return out


def tsinghua_math_bands(h):
    """Tsinghua Mathematical Sciences faculty list (szdw1/js/ayjs.htm): `<div class="post">教授</div><dl class="deptList">` rank bands with `<dd><a>` name links."""
    from bs4 import BeautifulSoup
    out = []
    for post in BeautifulSoup(h, 'html.parser').select('div.post'):
        dl = post.find_next_sibling('dl')
        if dl is None:
            continue
        band = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', clean(post.get_text(' ', strip=True)))
        for a in dl.select('dd a'):
            name = clean(a.get_text(' ', strip=True)).replace(' ', '')
            if name:
                out.append(dict(name_listed=name, titles=[band], profile=a.get('href'), homepage=None, division=None))
    return out


def tsinghua_bme_cards(h):
    """Tsinghua Biomedical Engineering 在职教师 series page (ryqk/zzjs/jyxl.htm): `<h2>教研系列（…）</h2>` series heading, then `li a[title]` cards with `<p>NAME</p>`; the series is not a rank."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(h, 'html.parser')
    h2 = soup.select_one('div.ny-right h2')
    series = re.split(r'[（(]', clean(h2.get_text(' ', strip=True)))[0] if h2 else None
    if not series:
        return []
    out = []
    for a in soup.select('div.ny-right li a[title][href]'):
        p = a.select_one('div.info p')
        if p is not None:
            out.append(dict(name_listed=clean(p.get_text(' ', strip=True)).replace(' ', ''), titles=[series], profile=a['href'], homepage=None, division=None))
    return out


def tsinghua_dpi_archive(h):
    """DPI's 2017–2025 portal: named cards grouped by institute, including explicitly labelled staff."""
    out = []
    for group in BeautifulSoup(h, 'html.parser').select('div.home3 div.dr div.third[id]'):
        heading = group.find('h5', recursive=False)
        if heading is None:
            continue
        division = clean(heading.get_text(' ', strip=True))
        for card in group.select('ul > li'):
            name = card.find('h6', recursive=False)
            title = card.find('p', recursive=False)
            profile = card.find('a', href=True, recursive=False)
            if name is None or title is None or profile is None:
                continue
            shown = clean(name.get_text(' ', strip=True))
            name = re.sub(r'[\s\u3000]+', '', shown)
            if not re.fullmatch(r'[\u3400-\u4dbf\u4e00-\u9fff·]{2,5}', name):
                continue
            href = profile['href'].strip()
            if not href or re.match(r'javascript:|mailto:|#', href, re.I):
                continue
            role = clean(title.get_text(' ', strip=True))
            if not role or re.search(r'@|\d{5,}|电话|邮箱|\b(?:email|tel)\b', role, re.I):
                continue
            out.append(dict(name_listed=name, titles=[role], profile=href, homepage=None, division=division,
                            **({'quote_name': shown} if shown != name else {})))
    return out


def tsinghua_dpi_json(raw_text):
    """Listing format; title eligibility remains in the charter's title_filter."""
    # Use the existing source-extraction bootstrap; both paths share validation.
    from school_web import extract
    import json_people
    extract.json_blocks(raw_text.encode())  # validate the same original JSON used for quotes
    out = []
    for _group, p in json_people.dpi_teacher_records(json.loads(raw_text)):
        name, title, unit = (p[k].strip() for k in ('teacherName', 'prorank', 'unit'))
        out.append(dict(name_listed=name, titles=[title], profile=p['url'], homepage=None, division=unit,
                        quote_parts=[name, title]))
    return out


def tsinghua_dpi_rendered(h):
    """Tsinghua Precision Instruments faculty page (faculty.dpi.tsinghua.edu.cn/teacher.jsp?...wbtreeid=1052) AFTER JavaScript (tools/js_render_capture.py):
    `li > a[href] .info` cards with `<h3>NAME</h3>`, `<p>职称：TITLE</p>` and `<p>单位：UNIT</p>`. The raw HTML is a shell; the list is loaded by script."""
    from bs4 import BeautifulSoup
    out = []
    for a in BeautifulSoup(h, 'html.parser').select('li > a[href]'):
        h3 = a.select_one('div.info h3')
        if h3 is None:
            continue
        title = unit = None
        for p in a.select('div.info p'):
            t = clean(p.get_text(' ', strip=True))
            if t.startswith('职称：'):
                title = t[3:].strip()
            elif t.startswith('单位：'):
                unit = t[3:].strip()
        out.append(dict(name_listed=clean(h3.get_text(' ', strip=True)).replace(' ', ''), titles=[title] if title else [], profile=a['href'], homepage=None, division=unit))
    return out


# ---- Tsinghua older site eras (stage 1, 2026-11-14): banded text rosters and a few card layouts -------------------------------------------------------
_TS_RANK = (r'(?:[一-鿿]{0,8}(?:教授|研究员|院士|讲师|教师|工程师|实验师|编辑|正高级|副高级|正高|副高|中级|所长|副所长|教研系列|研究系列|实验员)'
            r'[一-鿿/、]{0,16})')
_TS_DIV = r'(?:[一-鿿]{2,20}(?:研究所|研究院|研究中心|中心|学院|系))'
_TS_FACULTY_BAND = re.compile(r'教授|研究员|院士|讲师|教师|教研系列|研究系列|正高|副高|中级')
_TS_NOT_FACULTY = re.compile(r'工程师|实验师|编辑|实验员|所长|博士后')
_TS_STOP = {'教授', '副教授', '讲师', '研究员', '副研究员', '院士', '博士后', '其他', '其它', '暂无', '无', '正高级', '副高级', '中级'}


def _ts_lines(fragment):
    """Text lines of an HTML fragment: block tags and <br> break lines, every link end is a name separator (\\x01); entities and nbsp are plain spaces.
    A label split over tags is joined back ('正 高 级' + '：', '中' + '级：', '设' + '计工程研究所')."""
    h = re.sub(r'(?is)<(script|style)\b.*?</\1>|<!--.*?-->', '', fragment)
    h = re.sub(r'(?i)</a>', '\x01', h)
    h = re.sub(r'(?i)<br\s*/?>|</?(?:p|div|li|ul|tr|td|th|h\d|dd|dt|dl|table)\b[^>]*>', '\n', h)
    h = H.unescape(TAG.sub('', h)).replace('\xa0', ' ').replace('\u3000', ' ')
    h = re.sub(r'(教|院|副教|研|副研|讲|正高|副高)\s+(授|士|究\s*员|师|级)(?=\s*[：:])', lambda m: re.sub(r'\s+', '', m.group(0)), h)
    h = re.sub(r'(正|副)\s*高\s*级', r'\1高级', h)
    h = re.sub(r'(?<![\u4e00-\u9fff])中\s*级(?=\s*[：:]|\s*$)', '中级', h, flags=re.M)
    lines = [ln for ln in h.split('\n') if ln.strip()]
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if out and re.fullmatch(r'\s*[：:]\s*', ln):
            out[-1] = out[-1].rstrip() + '：'
        elif i + 1 < len(lines) and len(ln.strip()) == 1:
            cand = (ln.strip() + lines[i + 1].strip()).replace(' ', '')
            if re.fullmatch(_TS_DIV, cand) or re.fullmatch(_TS_RANK + r'\s*[：:]?', cand):
                out.append(ln.strip() + lines[i + 1].strip())
                i += 1
            else:
                out.append(ln)
        else:
            out.append(ln)
        i += 1
    return out


def _ts_names(text):
    """(name, as printed) pairs in a run of text: separators are 、，; / | spaces and link ends; a one-character token pairs with the next one
    ('周 明' -> 周明, printed '周 明', which is the quote the row needs)."""
    for _ in range(3):
        text = re.sub(r'[（(][^（）()]*[）)]', '', text)
    toks = [t for t in re.split(r'[\x01|、,，;；/\s]+', text) if t]
    out, i = [], 0
    while i < len(toks):
        t = shown = toks[i]
        if re.fullmatch(r'[\u4e00-\u9fff]', t) and i + 1 < len(toks) and re.fullmatch(r'[\u4e00-\u9fff]', toks[i + 1]):
            t, shown, i = t + toks[i + 1], t + ' ' + toks[i + 1], i + 1
        i += 1
        if t in _TS_STOP or re.search(r'教授|研究员|工程师|实验师|实验员|讲师|编辑|院士|所长|主任|书记|助理|博士后|教师', t):
            continue
        if re.fullmatch(r'[\u4e00-\u9fff·]{2,4}', t) or re.fullmatch(r'[A-Z][A-Za-z.\'-]{1,}', t):
            out.append((t, shown))
    return out


def tsinghua_banded_text(h):
    """Tsinghua department rosters written as rank-banded text (old /publish/<dept>/ sites 2016-2020, the VSB math jsml list): lines such as
    `教授：A、B、C`, `副教授：...`, institute headings (`摩擦学研究所`) and rank headings (`正高级`). A name list counts only under a faculty band (教授, 研究员,
    院士, 讲师, ...; 所长, 工程师, 实验师 and 博士后 bands are skipped) and a sentence (`。`) ends the band, so prose never yields names.
    The band is the title, the institute heading the division."""
    soup = BeautifulSoup(h, 'html.parser')
    box = soup.select_one('div.box_detail') or soup.select_one('div.gp-article') or soup.body or soup
    band = division = None
    out = []

    def emit(text):
        if band and _TS_FACULTY_BAND.search(band) and not _TS_NOT_FACULTY.search(band):
            for n, shown in _ts_names(text):
                out.append(dict(name_listed=n, titles=[band], profile=None, homepage=None, division=division, **({'quote_name': shown} if shown != n else {})))
    for line in _ts_lines(str(box)):
        for _ in range(3):
            line = re.sub(r'[（(][^（）()]*[）)]', '', line)   # remarks such as （按姓氏拼音排序） and award lists
        if '。' in line:
            if not re.match(r'\s*' + _TS_RANK + r'\s*[：:]', line):
                band = None   # prose, not a name list
                continue
            line = line.replace('。', '')
        line = line.strip()
        if re.fullmatch(_TS_DIV, line.replace(' ', '')):
            division = line.replace(' ', '')
            band = None
            continue
        if re.fullmatch(_TS_RANK, line.replace(' ', '')) and not re.search(r'[：:]', line):
            band = re.sub(r'\s+', '', line)
            continue
        for seg in re.split(r'(?<=[：:])', line):
            if not seg.strip():
                continue
            if seg.rstrip()[-1:] not in '：:':
                emit(seg)
                continue
            body = seg.rstrip()[:-1]
            m = re.search(r'(' + _TS_RANK + r'|' + _TS_DIV + r')\s*$', body.replace('\u0001', ' '))
            if m is None:
                band = None   # an unknown label (学术带头人, 研究方向包括): its names are not a rank band
                continue
            emit(body[:len(body) - len(m.group(0))] if body.endswith(m.group(0)) else '')
            label = re.sub(r'\s+', '', m.group(1))
            if re.fullmatch(_TS_DIV, label) and not re.search(r'教授|研究员|院士|讲师', label):
                division, band = label, None
            else:
                band = label
    return out


def tsinghua_me_column(h):
    """Tsinghua Mechanical Engineering 在职教师 list 2019-2020 (me.tsinghua.edu.cn/column/25_1.html): `<a word="C" href="../essay/..">name</a>` letter-bucket
    links, the same rows as tsinghua_me_zh without the title attribute; names only (spaced names such as '陈 恳' are joined)."""
    out = []
    for a in BeautifulSoup(h, 'html.parser').select('div.tea-text a[word][href]'):
        shown = clean(a.get_text(' ', strip=True))
        name = re.sub(r'[\s\u3000]+', '', shown)
        if name:
            out.append(dict(name_listed=name, titles=[], profile=a['href'], homepage=None, division=None, **({'quote_name': shown} if shown != name else {})))
    return out


def tsinghua_bme_person_table(h):
    """Tsinghua School of Medicine site 2017-2020 (www.med.tsinghua.edu.cn/Person?method=101&param=124, 生物医学工程系): `div.cont_item` with an `<h2>` series
    (教研系列, ...), then table rows `td.title` research area + `li a[href*=perId]` names. The series is the title, the area the division."""
    out = []
    for item in BeautifulSoup(h, 'html.parser').select('div.content div.cont_item'):
        series = item.find('h2')
        series = clean(series.get_text(' ', strip=True)) if series else None
        for tr in item.select('tr'):
            area = tr.select_one('td.title')
            for a in tr.select('li a[href]'):
                name = re.sub(r'[\s　]+', '', a.get_text('', strip=True))
                if name:
                    out.append(dict(name_listed=name, titles=[series] if series else [], profile=a['href'], homepage=None,
                                    division=clean(area.get_text(' ', strip=True)) if area else None))
    return out


_TS_BME_BANDS_BASE='https://www.med.tsinghua.edu.cn/szdw/swyxgcx.htm'
_TS_BME_BANDS={'教研系列','教学系列','研究系列','实验技术系列'}
def tsinghua_bme_med_bands(h):
 soup=BeautifulSoup(h,'html.parser');containers=soup.select('section.n_shizi div.content_li div.fl00')
 if not containers:raise ValueError('BME full faculty-series containers absent')
 out=[];seen=set();profiles=set()
 for box in containers:
  heading=box.select_one('div.title002 h3')
  if heading is None:raise ValueError('BME series container lacks heading')
  band=' '.join(heading.get_text(' ',strip=True).split())
  if band not in _TS_BME_BANDS or band in seen:raise ValueError('Unreviewed/repeated BME series: '+band)
  seen.add(band)
  for a in box.select('a[href]'):
   name=' '.join(a.get_text(' ',strip=True).split());url=urljoin(_TS_BME_BANDS_BASE,a['href']);u=urlsplit(url)
   if not name or u.scheme not in ('http','https') or u.hostname!='www.med.tsinghua.edu.cn' or not u.path.startswith('/info/'):
    raise ValueError('BME person has no literal name or own individual profile')
   if url in profiles:raise ValueError('BME person profile repeated; review source role explicitly')
   profiles.add(url)
   li=a.find_parent('li');area=li.find('h5',recursive=False) if li else None
   division=' '.join(area.get_text(' ',strip=True).split()) if area else None
   out.append(dict(name_listed=name,titles=[band],profile=url,homepage=None,division=division,quote_parts=[name,band]))
 if seen!=_TS_BME_BANDS:raise ValueError('BME complete source lost a reviewed series container')
 return out



def tsinghua_bme_med_areas(h):
    """Tsinghua School of Medicine 生物医学工程系 教研系列 sub-pages 2021-2024 (www.med.tsinghua.edu.cn/szdw/swyxgcx/jyxl/<area>.htm): `div.content_li`
    with `div.title001 h3` research area, then `li a[title][href]` cards; the area is the division, the series (教研系列) the title."""
    out = []
    for box in BeautifulSoup(h, 'html.parser').select('div.content_li'):
        area = box.select_one('div.title001 h3')
        area = clean(area.get_text(' ', strip=True)) if area else None
        for a in box.select('li a[title][href]'):
            name = re.sub(r'[\s　]+', '', a['title'])
            if name:
                out.append(dict(name_listed=name, titles=['教研系列'], profile=a['href'], homepage=None, division=area))
    return out


def tsinghua_air_zh_cards(h):
    """Tsinghua AIR Chinese team pages 2022- (air.tsinghua.edu.cn/airtd/yjtd.htm): `div.yjtd_tit h1` band, then `li` cards whose `<h2>` is `<b>name</b>` followed
    by the title text (院长/讲席教授); the biography paragraph is not kept."""
    out = []
    for box in BeautifulSoup(h, 'html.parser').select('div.yjtd_tit'):
        band = clean(box.get_text(' ', strip=True))
        body = box.find_next_sibling('div', class_='yjtd_nr')
        for li in (body.select('li') if body else []):
            h2, a = li.select_one('h2'), li.select_one('a[href]')
            b = h2.find('b') if h2 else None
            if b is None or not clean(b.get_text(' ', strip=True)):
                continue
            name = re.sub(r'[\s\u3000]+', '', clean(b.get_text(' ', strip=True)))
            title = clean(h2.get_text(' ', strip=True))[len(clean(b.get_text(' ', strip=True))):].strip()
            out.append(dict(name_listed=name, titles=[title] if title else [], profile=a['href'] if a else None, homepage=None, division=band))
    return out


def tsinghua_au_alpha(h):
    """Tsinghua Automation faculty A-Z page 2020- (szdw/jsdw1/aszmcz.htm, 按姓名首字母): `div.list-line div.n-list a div.item` names for every letter on one page,
    no titles; links that are `javascript:;` have no profile."""
    out = []
    for a in BeautifulSoup(h, 'html.parser').select('div.list-line div.n-list a'):
        item = a.select_one('div.item')
        shown = clean(item.get_text(' ', strip=True)) if item else ''
        name = re.sub(r'[\s\u3000]+', '', shown)
        if name:
            href = a.get('href')
            out.append(dict(name_listed=name, titles=[], profile=None if not href or href.startswith('javascript') else href, homepage=None, division=None,
                            **({'quote_name': shown} if shown != name else {})))
    return out


def tsinghua_iiis_people(h):
    """Tsinghua IIIS people page 2016-2025 (iiis.tsinghua.edu.cn/people/, en/people/, zh/people/): a series heading (`教研系列`, ...) then `div.list_team li`
    cards: `div.name a` and the first `div.area` line as the title (院长，教授)."""
    out = []
    for li in BeautifulSoup(h, 'html.parser').select('div.list_team li'):
        a = li.select_one('div.name a')
        if a is None:
            continue
        name = clean(a.get_text(' ', strip=True))
        area = li.select_one('div.area')
        head = li.find_parent('div', class_='list_team')
        series = head.find_previous(class_=re.compile(r'\btitle\b|\btit\b')) if head is not None else None
        out.append(dict(name_listed=name, titles=[clean(area.get_text(' ', strip=True))] if area else [], profile=a.get('href'), homepage=None,
                        division=clean(series.get_text(' ', strip=True)) if series is not None else None))
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



def ntu_moss_faculty(h):
    """SCE/SCSE moss_staffac.asp: photo rows, then a literal name and parenthesized rank.

    Keep only that heading and its linked faculty URL. Degrees, contact details and
    research-interest cells are outside the roster evidence emitted here.
    """
    from bs4 import BeautifulSoup
    out = []
    heading = re.compile(r'^(.+?)\s+\(([^()]*(?:Prof(?:essor)?|Lecturer|Research (?:Fellow|Scientist))[^()]*)\)', re.I)
    for tr in BeautifulSoup(h, 'html.parser').find_all('tr'):
        cells = tr.find_all('td', recursive=False)
        if len(cells) < 4 or cells[0].find('img') is None:
            continue
        cell = cells[1]
        match = heading.match(clean(cell.get_text(' ', strip=True)))
        if match is None:
            continue
        name, rank = match.groups()
        link = next((a.get('href') for a in cell.find_all('a', href=True)
                     if clean(a.get_text(' ', strip=True)) == name
                     and re.match(r'https?://', a['href'], re.I)), None)
        out.append(dict(name_listed=name, titles=[rank], profile=link, homepage=None,
                        division=None, quote=match.group(0)))
    return out


def ntu_img_cards(h):
    """NTU SCSE 2021 faculty list (www.ntu.edu.sg/scse/about-us/our-people/faculty, Sitefinity img-card--academic): h3.img-card__title link (honorific + name,
    the DR-NTU profile), the Appointments paragraph (one title per line). The honorific is not part of the name; the e-mail and the biography teaser are dropped."""
    from bs4 import BeautifulSoup
    out = []
    for card in BeautifulSoup(h, 'html.parser').select('.img-card--academic'):
        a = card.select_one('.img-card__title a')
        if a is None:
            continue
        name = re.sub(r'^(?:Emeritus Prof|Adj(?:unct)? (?:Assoc |Asst )?Prof|Assoc Prof|Asst Prof|Prof|Dr|Mr|Ms|Mrs)\s+', '', clean(a.get_text(' ')))
        titles = []
        quote_parts = [clean(a.get_text(' '))]
        for p in card.select('.img-card__interests, .img-card__desc'):
            if 'Appointments:' in p.get_text():
                body = re.sub(r'^.*?Appointments:\s*', '', p.decode_contents(), flags=re.S)
                titles = [clean(x) for x in re.split(r'<br\s*/?>', body, flags=re.I)]
                quote_parts.append(clean(p.get_text(' ', strip=True)))
        out.append(dict(name_listed=name, titles=[t for t in titles if t], profile=a.get('href'), homepage=None, division=None,
                        quote_parts=quote_parts))
    return out


def sjtu_cs_en_institutes(h):
    """SJTU School of Computer Science English faculty list (cs.sjtu.edu.cn/en/Faculty.aspx, archived 2016-2024): one `p.tc` per institute, then
    `div.Faculty` with `<h3>Rank:</h3>` followed by `<ul><li><a href=PeopleDetail.aspx?id=N>Family Given</a>` (pinyin, family name first). Commented-out
    blocks are ignored (the parser drops comments). The rank heading is the listed title; the institute is the division; `(Joint)` stays on the name
    as a title note. name_listed is the name as the page spells it ('Fu Yuxi': family name first)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for box in soup.select('div.Faculty'):
        p_ = box.find_previous_sibling('p')
        division = clean(p_.get_text(' ', strip=True)) if p_ else None
        for h3 in box.find_all('h3'):
            rank = clean(h3.get_text(' ', strip=True)).rstrip(':\uff1a').strip()  # the Chinese list ends its rank headings with a full-width colon
            ul = h3.find_next_sibling('ul')
            for a in (ul.select('li a[href]') if ul else []):
                raw = clean(a.get_text(' ', strip=True))
                note = re.search(r'\((Joint)\)', raw)
                name = re.sub(r'\s*\((?:Joint)\)', '', raw).strip()
                toks_ = name.split()
                listed = name  # as the page spells it (family name first): the row quote must be a substring of the page text
                out.append(dict(name_listed=listed, titles=[rank] + ([note.group(1)] if note else []), profile=a['href'], homepage=None, division=division))
    return out


def sjtu_cs_ajax_teachers(h):
    """SJTU School of Computer Science directory feed (cs.sjtu.edu.cn/active/ajax_teacher_list.html, 2025-): a JSON object whose `content` is HTML,
    one `div.rc-item` per institute: `div.tit .name` is the institute, `div.dt p` the leaders ('所 长：' + linked name) and `div.name-list span a`
    the other teachers. No rank is printed (names only, titles=[]; the leader labels are not kept). name_listed is the name as the page spells it
    with wide spaces folded to one space, so it is a substring of the text listings/scripts/json_people.py renders for the same capture."""
    import json
    from bs4 import BeautifulSoup
    try:
        doc = json.loads(h)
    except ValueError:
        return []
    out = []
    for item in BeautifulSoup((doc.get('content') if isinstance(doc, dict) else '') or '', 'html.parser').select('div.rc-item'):
        nm = item.select_one('div.tit .name')
        division = clean(nm.get_text(' ', strip=True)) if nm else None
        for a in item.select('div.dt a[href], div.name-list a[href]'):
            name = clean(a.get_text(' ', strip=True))
            if name:
                out.append(dict(name_listed=name, titles=[], profile=a['href'], homepage=None, division=division))
    return out

HONORIFIC = re.compile(r'^(Emeritus Prof|Adj(?:unct)? (?:Assoc |Asst )?Prof|Assoc Prof|Asst Prof|Prof|Dr|Mr|Ms|Mrs)\.?\s+')
HONOR_RANK = {'assoc prof': 'Associate Professor', 'asst prof': 'Assistant Professor', 'prof': 'Professor', 'emeritus prof': 'Emeritus Professor'}


def ntu_person(raw, designations):
    """One NTU unit-page entry as the listing row the review reads: the honorific is stripped (its rank, literal on the page, leads the titles),
    'SURNAME, Given' and an upper-case surname become 'Given Surname'."""
    raw = clean(raw.replace('\u200b', ''))
    m = HONORIFIC.match(raw)
    rank = HONOR_RANK.get(m.group(1).lower()) if m else None
    name = raw[m.end():] if m else raw
    if ',' in name:
        fam, giv = [x.strip() for x in name.split(',', 1)]
        name = f'{giv} {fam}'
    name = ' '.join(w.capitalize() if len(w) > 1 and w.isupper() else w for w in name.split())
    titles = ([rank] if rank else []) + [clean(d.replace('\u200b', '')) for d in designations if clean(d.replace('\u200b', ''))]
    return dict(name_listed=name, titles=titles, profile=None, homepage=None, division=None)


def _br_lines(el):
    return [x for x in re.split(r'<br\s*/?>', el.decode_contents(), flags=re.I) if clean(x)]


def ntu_coe_cards(h):
    """NTU College of Engineering sites (EEE, CEE 2026): article.coe-about-leadership__card, h3 name (surname in capitals) and p.__role (rank)."""
    from bs4 import BeautifulSoup
    out = []
    for card in BeautifulSoup(h, 'html.parser').select('article.coe-about-leadership__card'):
        nm = card.select_one('.coe-about-leadership__name')
        if nm is None:
            continue
        role = card.select_one('.coe-about-leadership__role')
        e = ntu_person(nm.get_text(' ', strip=True), [role.get_text(' ', strip=True)] if role else [])
        a = card.select_one('a[href*="dr.ntu.edu.sg"]')
        e['profile'] = a.get('href') if a else None
        out.append(e)
    return out


def ntu_profile_cards(h):
    """NTU profile lists (WKWSCI, ADM, SBS, MAE when rendered): div.profile-row / div.profile-card with a .name-text name and a designation block (lines split on <br>)."""
    from bs4 import BeautifulSoup
    out = []
    for card in BeautifulSoup(h, 'html.parser').select('div.profile-row, div.profile-card'):
        nm = card.select_one('.name-text')
        if nm is None:
            continue
        des = card.select_one('.profile-row-designation, .profile-card-designation')
        a = card.select_one('a[href]')
        e = ntu_person(nm.get_text(' ', strip=True), [clean(x) for x in _br_lines(des)] if des is not None else [])
        e['profile'] = a.get('href') if a else None
        out.append(e)
    return out


def ntu_spms_table(h):
    """NTU SPMS faculty tables: <td><strong>SURNAME, Given</strong><br><span>Rank</span>..."""
    from bs4 import BeautifulSoup
    out = []
    for td in BeautifulSoup(h, 'html.parser').find_all('td'):
        st = td.find('strong', recursive=False)
        sp = td.find('span', recursive=False)
        if st is None or sp is None or ',' not in st.get_text():
            continue
        a = td.find('a', string=re.compile('Profile'))
        e = ntu_person(st.get_text(' ', strip=True), [sp.get_text(' ', strip=True)])
        e['profile'] = a.get('href') if a else None
        out.append(e)
    return out


def ntu_medicine_table(h):
    """NTU Lee Kong Chian School of Medicine faculty table: first cell a link 'Prof Given SURNAME', second cell the appointments split on <br>."""
    from bs4 import BeautifulSoup
    out = []
    for tr in BeautifulSoup(h, 'html.parser').select('table tbody tr'):
        tds = tr.find_all('td', recursive=False)
        if len(tds) < 2:
            continue
        a = [x for x in tds[0].find_all('a') if clean(x.get_text())]
        if not a:
            continue
        e = ntu_person(a[-1].get_text(' ', strip=True), [clean(x) for x in _br_lines(tds[1])])
        e['profile'] = a[-1].get('href')
        out.append(e)
    return out


NTU_FORMATS = ('ntu_coe_cards', 'ntu_profile_cards', 'ntu_spms_table', 'ntu_medicine_table')


def ntu_unit_text(html):
    """Verification text of an NTU unit page read through its format (name + title rows), or None when no NTU format parses it."""
    for fmt in NTU_FORMATS:
        rows = FORMATS[fmt][0](html)
        if rows:
            return ntu_entries_text(rows)
    return None


def ntu_entries_text(rows):
    """Verification text of the parsed rows: 'Name Title Title Profile' per person, the 'Profile' marker ending each entry (cs_related_school.CUT)."""
    return ' '.join(f"{r['name_listed']} {' '.join(r['titles'])} Profile" for r in rows)


FORMATS = {
    'ucsd_cse_info_cols': (ucsd_cse_info_cols, re.compile(r'(?!)')),
    'ucsd_jacobs_findprofile': (ucsd_jacobs_findprofile, re.compile(r'(?!)')),
    'ucsd_cse_cards': (ucsd_cse_cards, re.compile(r'(?!)')),
    'illinois_campus_faculty': (illinois_campus_faculty, re.compile(r'(?!)')),
    'illinois_directory_cards': (illinois_directory_cards, re.compile(r'(?!)')),
    # On the CS affiliate-and-adjunct page these category groups are separate
    # source occurrences: preserve their slot kind without inventing title text.
    'illinois_cs_affiliates': (lambda h: illinois_directory_cards(h, {'cat5'}), re.compile(r'(?!)')),
    'illinois_cs_adjuncts': (lambda h: illinois_directory_cards(h, {'cat3'}), re.compile(r'(?!)')),
    'stanford_cs_legacy': (stanford_cs_legacy, re.compile(r'(?s)Regular Faculty</h3>.*post_form_nam_last')),
    'stanford_cs_cards': (stanford_cs_cards, re.compile(r'(?s)Faculty by Name.*su-person-short-title')),
    'stanford_ee_cards': (stanford_ee_cards, re.compile(r'(?s)<title>[^<]*Stanford (?:EE|Electrical Engineering).*?(?:orglist__display-name|class="description")')),
    'stanford_ee_bulletin': (stanford_ee_bulletin, re.compile(r'(?s)<title>\s*Electrical Engineering\b.*facultytextcontainer')),
    'hit_cs_current_table': (hit_cs_current_table, re.compile(r'(?!)')),
    'berkeley_eecs_faculty': (berkeley_eecs_faculty, re.compile(r'(?!)')),
    'berkeley_eecs_directory': (berkeley_eecs_directory, re.compile(r'(?!)')),
    'mit_csail_pi': (mit_csail_pi, re.compile(r'(?!)')),
    'nus_cs_any': (nus_cs_any, re.compile(r'(?!)')),
    'cuhk_cse_any': (cuhk_cse_any, re.compile(r'(?!)')),
    'cuhk_cse_profile_cards': (cuhk_cse_profile_cards, re.compile(r'class=["\'][^"\']*facultyppl-container')),
    'cuhk_erg_cse_directory': (cuhk_erg_cse_directory, re.compile(r'class="people-dept-wrap"')),
    'cuhk_cse_faculty_table': (cuhk_cse_faculty_table, re.compile(r'class="[^"]*foo-table')),
    'purdue_cs_people': (purdue_cs_people, re.compile(r'class="people-item"')),
    'utaustin_cs_people': (utaustin_cs_people, re.compile(r'views-field-field-contact-faculty-title')),
    'utaustin_cs_faculty_legacy': (utaustin_cs_faculty_legacy, re.compile(r'class="prof-name"')),
    'ustc_cs_cards': (ustc_cs_cards, re.compile(r'class="col_news_list listcon"')),
    'pku_cs_cards': (pku_cs_cards, re.compile(r'class="list15 list15s')),
    'pku_cs_namelist': (pku_cs_namelist, re.compile(r'id="teachernamelist"')),
    'uestc_scse_bands': (uestc_scse_bands, re.compile(r'class="listHead"')),
    'uestc_college_teachers': (uestc_college_teachers, re.compile(r'urltype=tsites\.CollegeTeacherList.*?class="ex_img"', re.S)),
    'whu_cs_legacy': (whu_cs_legacy, re.compile(r'class="j_name_num"')),
    'whu_cs_zrjs': (whu_cs_zrjs, re.compile(r'class="teacher-list-item".*?class="li-xinxi"', re.S)),
    'whu_cs_talents': (whu_cs_talents, re.compile(r'class="talent-item"')),
    'whu_cs_emeritus': (whu_cs_emeritus, re.compile(r'class="teacher-list honored')),
    'seu_department_faculty': (seu_department_faculty, re.compile(r'<title>教师按系别</title>')),
    'hit_teacher_list': (hit_teacher_list, re.compile(r'id="wp_news_w6"')),
    'princeton_cs_faculty': (princeton_cs_faculty, re.compile(r'class="people people-facstaff"|custom_card__container people')),
    'mit_eecs_legacy_faculty': (mit_eecs_legacy_faculty, re.compile(r'class="faculty-list"')),
    'mit_eecs_faculty_cards': (mit_eecs_faculty_cards, re.compile(r'class="facetwp-template"')),
    'ustc_cs_legacy_sidebar': (ustc_cs_legacy_sidebar, re.compile(r'(?!)')),
    'ntu_coe_cards': (ntu_coe_cards, re.compile(r'coe-about-leadership__card')),
    'ntu_profile_cards': (ntu_profile_cards, re.compile(r'ntu-profile-list')),
    'ntu_spms_table': (ntu_spms_table, re.compile(r"<strong[^>]*>[A-Z][A-Z' -]+, [A-Z]")),
    'ntu_medicine_table': (ntu_medicine_table, re.compile(r'Faculty and Joint Faculty')),
    'ntu_moss_faculty': (ntu_moss_faculty, re.compile(r'(?!)')),
    'ntu_img_cards': (ntu_img_cards, re.compile(r'img-card--academic')),
    'tsinghua_ee_any': (tsinghua_ee_any, re.compile(r'(?!)')),
    'tsinghua_banded_text': (tsinghua_banded_text, re.compile(r'(?!)')),
    'tsinghua_me_column': (tsinghua_me_column, re.compile(r'(?!)')),
    'tsinghua_bme_person_table': (tsinghua_bme_person_table, re.compile(r'(?!)')),
    'tsinghua_bme_med_bands': (tsinghua_bme_med_bands, re.compile(r'(?!)')),
    'tsinghua_bme_med_areas': (tsinghua_bme_med_areas, re.compile(r'(?!)')),
    'tsinghua_iiis_people': (tsinghua_iiis_people, re.compile(r'(?!)')),
    'tsinghua_au_alpha': (tsinghua_au_alpha, re.compile(r'(?!)')),
    'tsinghua_air_zh_cards': (tsinghua_air_zh_cards, re.compile(r'(?!)')),
    'tsinghua_ee_text': (tsinghua_ee_text, re.compile(r'图片列表.{0,3000}?(?:教\s*授|副教授)\s*[：:]', re.S)),
    'tsinghua_au_old_list': (tsinghua_au_old_list, re.compile(r'<table[^>]*uetable')),
    'tsinghua_insc_bands': (tsinghua_insc_bands, re.compile(r'(?!)')),
    'tsinghua_dpi_archive': (tsinghua_dpi_archive, re.compile(r'(?!)')),
    'tsinghua_dpi_json': (tsinghua_dpi_json, re.compile(r'(?!)')),
    'tsinghua_dpi_rendered': (tsinghua_dpi_rendered, re.compile(r'(?!)')),
    'tsinghua_me_zh': (tsinghua_me_zh, re.compile(r'(?!)')),
    'tsinghua_me_en': (tsinghua_me_en, re.compile(r'(?!)')),
    'tsinghua_math_bands': (tsinghua_math_bands, re.compile(r'(?!)')),
    'tsinghua_bme_cards': (tsinghua_bme_cards, re.compile(r'(?!)')),
    'tsinghua_ee_embedded': (tsinghua_ee_embedded, re.compile(r'function topage_\d_\d\(keyword, yjly, szm\)')),
    'tsinghua_ee_rendered': (tsinghua_ee_rendered, re.compile(r'id="showdatainfo')),
    'tsinghua_sw_english_bands': (tsinghua_sw_english_bands, re.compile(r'(?!)')),
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
    'sjtu_cs_en_institutes': (sjtu_cs_en_institutes, re.compile(r'class="Faculty"')),
    'sjtu_cs_ajax_teachers': (sjtu_cs_ajax_teachers, re.compile(r'rc-item')),
    'zju_cs_zuzhi_names': (zju_cs_zuzhi_names, re.compile(r'class="zuzhi"')),
    'zju_cs_en_faculty_list': (zju_cs_en_faculty_list, re.compile(r'class=.tearch_class.>[^<]*Institute|class=.tearch_class.>State Key Lab|class="sublist_title"')),
    'zju_cs_old_jiaoshiml': (zju_cs_old_jiaoshiml, re.compile(r'class="szdw"')),
    'zju_cad_fixed_researchers': (zju_cad_fixed_researchers, re.compile(r'class="zhuwenn"')),
    'zju_cad_fixed_researchers_2025': (zju_cad_fixed_researchers_2025, re.compile(r'elementor-heading-title[^>]*>院士<')),
    'zju_cst_szdw_names': (zju_cst_szdw_names, re.compile(r'class="wp_articlecontent"[^>]*>\s*<div[^>]*paging_content[^>]*>\s*<table')),
    'zju_isee_table': (zju_isee_table, re.compile(r'class="zp"')),
    'zju_ee_teach_list': (zju_ee_teach_list, re.compile(r'class="teach-list"|class="introduce">\s*<h3>')),
    'zju_math_teachers_asp': (zju_math_teachers_asp, re.compile(r'teacher_intro\.asp\?userid=')),
    'zju_cse_teacher_list': (zju_cse_teacher_list, re.compile(r'class="teacher-box1">\s*<h3 class="research-name"')),
    'tsinghua_cs_list': (tsinghua_cs_list, re.compile(r'class="people01-nr"')),
    'tsinghua_sw_names': (tsinghua_sw_names, re.compile(r'class="group-title"')),
    'tsinghua_iiis_cards': (tsinghua_iiis_cards, re.compile(r'class="ls16 flex"')),
    'tsinghua_au_cards': (tsinghua_au_cards, re.compile(r'class="list13 flex"|class="teacher-list"')),
    'tsinghua_air_cards': (tsinghua_air_cards, re.compile(r'class="yjtd_tit"')),
    'hkust_faculty_table': (hkust_faculty_table, re.compile(r'(?!)')),
    'toronto_legacy_faculty': (toronto_legacy_faculty, re.compile(r'(?!)')),
    'toronto_full_directory': (toronto_full_directory, re.compile(r'(?!)')),
    'toronto_research': (lambda h: toronto_directory(h, 'researchstream'), re.compile(r'(?!)')),
    'toronto_teaching': (lambda h: toronto_directory(h, 'teachingstream'), re.compile(r'(?!)')),
    'toronto_emeriti': (lambda h: toronto_directory(h, 'emeriti'), re.compile(r'(?!)')),
    'toronto_cross': (lambda h: toronto_directory(h, 'crossappointed'), re.compile(r'(?!)')),
    'toronto_status': (lambda h: toronto_directory(h, 'statusonly'), re.compile(r'(?!)')),
    'toronto_adjunct': (lambda h: toronto_directory(h, 'adjunct'), re.compile(r'(?!)')),
    'cambridge_profile': (cambridge_profile, re.compile(r'class="cst-job-titles')),
    'oxford_person_index': (oxford_person_index, re.compile(r'class="personIndex"')),
    'cambridge_directory': (cambridge_directory, re.compile(r'views-field-field-sd-classifications-ref')),
    'cambridge_academic_staff': (cambridge_academic_staff, re.compile(r'<title>[^<]*Academic staff')),
    'epfl_ic_legacy': (epfl_ic_legacy, re.compile(r'class="g-span-1_4"')),
    'epfl_ic_contact': (epfl_ic_contact, re.compile(r'class="contact-list-row"')),
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
    'jhu_cs_faculty_card': (jhu_cs_faculty_card, re.compile(r'class="highlight-box faculty-member-card"')),
    'jhu_bme_faculty': (jhu_bme_faculty, re.compile(r'class="zn-faculty-profile\s*"')),
    'jhu_bme_complete_faculty': (jhu_bme_complete_faculty, re.compile(r'JHU BME complete faculty listing')),
    'wu_teaser': (wu_teaser, re.compile(r'class="faculty-directory__teaser"')),
    'isye_card': (isye_card, re.compile(r'class="w-100 px-0 pt-0 person-name"')),
    'uw_allen_cards': (uw_allen_cards, re.compile(r'aria-label="Read the bio for')),
    'uw_stat_people': (uw_stat_people, re.compile(r'(?s)(?=.*stat\.uw\.edu)(?=.*class="field-content person-name").*views-field-field-position')),
    'uw_ee_mainlist': (uw_ee_mainlist, re.compile(r'<table class="mainlist">')),
    'uw_allen_directory': (uw_allen_directory, re.compile(r"(?s)class=['\"](?:directory-name|people-short-listing-name)['\"]>\s*<a href=['\"][^'\"]*cs\.washington\.edu")),
    'uw_ece_staff': (uw_ece_staff, re.compile(r'class="stafftemplate--entry"')),
    'uw_ischool_card': (uw_ischool_card, re.compile(r'<article aria-label="[^"]*" id="card-[^"]*" class="card clearfix" data-type=')),
    'uw_amath_directory': (uw_amath_directory, re.compile(r'class="directory-item__name"')),
    'uw_hcde_columns': (uw_hcde_columns, re.compile(r'<h2><a href="[^"]+"[^>]*><strong>')),
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
    """A capture of one page of a paged directory (pager markers and a ?page=N or ?pg=N link): it parses to a few people while the rest sit on pages
    the archive may not hold (UChicago CS 2017: 5 of about 45). listing_rows.py reports it and plan_fetch.charter_usable rejects it."""
    pager_marker = re.search(r'class=["\'][^"\']*\b(?:pager|pagination)\b', html) or re.search(r'>\s*Show More\s*<', html, re.I)
    query_pager = bool(pager_marker and
                       re.search(r'(?:[?&]|&amp;)(?:page=(?:%2C|,)?[1-9]\d*|pg=(?:[2-9]|[1-9]\d+))', html))
    wp = re.search(r'<em class="all_pages">\s*(\d+)\s*</em>', html)
    uestc = re.search(r'\bPAGENUM=([2-9]|[1-9]\d+)\b', html)
    sitebuilder = 'class="p_pages"' in html and bool(re.search(r'class="p_no"><a href="[^"]+/\d+\.htm"', html))   # Webplus p_pages pager (PKU CS)
    onethink = bool(re.search(r'class="onethink pagination[^"]*"[^>]*>(?:(?!</div>).)*?<a class="num" href="index\d+\.htm"', html, re.S))   # PKU WICT cards (indexN.htm)
    return query_pager or bool(uestc) or sitebuilder or onethink or bool('class="wp_paging' in html and wp and int(wp.group(1)) > 1)


def page_links(html, base_url):
    """{n: absolute url} of the other pages a paged directory links (`?page=N`, `?title=&amp;page=N`), n >= 1, same path as `base_url`. Pages the pager
    only elides ('1 2 3 ... last') are filled in from the largest linked number by substituting it into a linked URL, so the result covers 1..last.
    Used by plan_fetch to fetch every page of a paged slot (R3, Georgia Tech friction 10: the pipeline took one page for a whole half-year)."""
    import urllib.parse
    base_url = re.sub(r'^(https?://[^/]+?):(?:80|443)(?=/|$)', r'\1', base_url)   # Wayback keeps ':80' in the original of old captures; its CDX does not match it
    base = urllib.parse.urlsplit(base_url)
    # Visual SiteBuilder's college directory uses one-based PAGENUM; page 1
    # is the base URL and its last-page link gives the required page count.
    if 'urltype=tsites.CollegeTeacherList' in html:
        paged = re.findall(r'href="([^\"]*\bPAGENUM=(\d+)[^\"]*)"', html)
        pages = [(int(n), urllib.parse.urljoin(base_url, H.unescape(href))) for href, n in paged]
        pages = [(n, url) for n, url in pages if urllib.parse.urlsplit(url).path == base.path
                 and urllib.parse.urlsplit(url).netloc == base.netloc and n >= 2]
        if pages:
            template = pages[0][1]
            last = max(n for n, _ in pages)
            return {n - 1: re.sub(r'(?<=PAGENUM=)\d+', str(n), template, count=1)
                    for n in range(2, last + 1)}
    # Webplus `p_pages` pager with reverse-numbered files (PKU CS: page 2 of 12 is `jyxl/11.htm`, the last page `jyxl/1.htm`); the last page number K gives
    # display page n the file K - n + 1.
    wpp = re.findall(r'class="p_no"><a href="([^"]*?)(\d+)\.htm">(\d+)</a>', html)
    if 'class="p_pages"' in html and wpp:
        last = max(int(n) for _, _, n in wpp)
        prefix = wpp[0][0]
        if last > 1:
            return {n - 1: urllib.parse.urljoin(base_url, f'{prefix}{last - n + 1}.htm') for n in range(2, last + 1)}
    # PKU WICT `onethink pagination`: page 1 is index.htm, page N+1 is indexN.htm (the pager lists every page number)
    ot = re.findall(r'<a class="num" href="index(\d+)\.htm"', html) if 'onethink pagination' in html else []
    if ot:
        return {int(n): urllib.parse.urljoin(base_url, f'index{n}.htm') for n in sorted(set(ot), key=int)}
    found = {}
    for href in re.findall(r'href="([^"]*[?&;](?:page|pg)=(?:%2C|,)?\d+[^"]*)"', html):
        u = urllib.parse.urljoin(base_url, H.unescape(href))
        sp = urllib.parse.urlsplit(u)
        if sp.path.rstrip('/') != base.path.rstrip('/') or sp.netloc.lower().split(':')[0] != base.netloc.lower().split(':')[0]:
            continue
        m = re.search(r'(?:^|&)(page|pg)=(?:%2C|,)?(\d+)', sp.query)
        if m:
            n = int(m.group(2)) - (1 if m.group(1) == 'pg' else 0)
            if n >= 1:
                found.setdefault(n, u)
    # Chinese university sites built with Webplus use /list2.htm, /list3.htm
    # rather than a query parameter. The all_pages marker establishes the
    # required count even when the pager elides middle links.
    if 'class="wp_paging' in html and re.fullmatch(r'.*/list(?:\d+)?\.htm', base.path):
        m = re.search(r'<em class="all_pages">\s*(\d+)\s*</em>', html)
        if m and int(m.group(1)) > 1:
            base_dir = base.path.rsplit('/', 1)[0]
            return {n - 1: f'{base.scheme}://{base.netloc}{base_dir}/list{n}.htm'
                    for n in range(2, int(m.group(1)) + 1)}
    if not found:
        return {}
    tmpl = found[min(found)]
    return {n: found.get(n) or re.sub(r'(^|[?&])(page|pg)=((?:%2C|,)?)\d+',
                                      lambda m: f'{m.group(1)}{m.group(2)}={m.group(3)}{n + (m.group(2) == "pg")}',
                                      tmpl, count=1)
            for n in range(1, max(found) + 1)}


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


def whu_cs_rank_table(h):
    """Wuhan CS's unpaged ASP roster: printed name and rank, no contact fields."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for row in soup.select('table tr'):
        name_cell = row.select_one('td.w1')
        rank_cell = row.select_one('td.w4')
        link = name_cell.select_one('a[href]') if name_cell else None
        if not link or not rank_cell or not re.search(r'(?:^|/)teacherinfo\.aspx\?id=\d+', link['href']):
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        rank = ' '.join(rank_cell.get_text(' ', strip=True).split())
        if name and rank:
            out.append(dict(name_listed=name, titles=[rank], homepage=None,
                            division=None, profile=link['href']))
    return out


FORMATS['whu_cs_rank_table'] = (whu_cs_rank_table, re.compile(r'(?!)'))


# ---- Carnegie Mellon School of Computer Science units (Stage 1, 2026-11-13): one reader per site era -----------------------------------------
# CMU's seven SCS units changed platform two to four times between 2016 and 2026 (Drupal 7 views tables, ISR/MLD hand-built bio pages,
# a WordPress 'Connections' directory, Fusion/Toolset cards, the 2022 Hugo-style filterable cards). Slots name the era's reader in
# schools/cmu.toml; none of them auto-detects (the detector never matches), so a page is only read by the era that names it.
_CMU_LEAD = re.compile(r'^(?:Dr|Prof|Professor)\.?\s+', re.I)


def _cmu_t(node):
    return ' '.join(node.get_text(' ', strip=True).split()) if node is not None else ''


def _cmu_entry(name, titles, href=None, division=None):
    name = _CMU_LEAD.sub('', ' '.join((name or '').split())).strip(' ,')
    titles = [t for t in (' '.join(x.split()) for x in titles) if t]
    return dict(name_listed=name, titles=titles, homepage=None, division=division, profile=href) if name else None


def cmu_scs_views_table(h):
    """CSD directory/faculty (Drupal 7 views table 2016-2023, people/faculty 2024-2026) and the all-people directory.
    Name cells: 'Last' + 'First' cells (2016-2018), one 'Last, First' link (2019-2024), or the link followed by the title line (2026); the title cell
    carries 'prof-title' or 'professional-title'. Office, phone and e-mail cells are never read."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for tr in soup.select('tbody tr'):
        cells = {}
        for td in tr.find_all('td', recursive=False):
            for c in td.get('class') or []:
                cells[c] = td
        last = next((v for k, v in cells.items() if k.endswith('field-computed-last-name')), None)
        first = next((v for k, v in cells.items() if k.endswith('field-computed-first-name')), None)
        lone = next((v for k, v in cells.items() if k.endswith('views-field-field-first-name')), None)
        title_cell = next((v for k, v in cells.items() if 'prof-title' in k or 'professional-title' in k), None)
        name_cell = last or lone
        if name_cell is None:
            continue
        link = name_cell.select_one('a[href]')
        name = _cmu_t(link) if link else _cmu_t(name_cell)
        printed = None
        if first is not None:   # two cells: the page prints 'Last First' (no comma); the entry keeps 'Last, First'
            printed = f'{name} {_cmu_t(first)}'
            name = f'{name}, {_cmu_t(first)}'
        if not name or name.lower().startswith('name'):
            continue
        titles = [_cmu_t(title_cell)] if title_cell is not None else []
        if not titles and link is not None:
            for sib in link.next_siblings:   # 2026: the link, <br>, the title, <br>, then office lines
                text = ' '.join(str(sib).split()) if isinstance(sib, str) else ''
                if text:
                    titles = [text]
                    break
        e = _cmu_entry(name, titles, link['href'] if link else None)
        if e:
            if printed:
                e['quote_name'] = ' '.join(printed.split())
            out.append(e)
    return out


def cmu_lti_directory(h):
    """LTI directory/all/154/N (Drupal 7 views grid 2016-2024): td.col-N, h2 name in a profile link, div.field-computed-prof-title."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for td in soup.select('td[class*="col-"]'):
        h2 = td.select_one('h2')
        title = td.select_one('.views-field-field-computed-prof-title')
        if h2 is None or title is None:
            continue
        a = h2.find_parent('a', href=True)
        e = _cmu_entry(_cmu_t(h2), [_cmu_t(title)], a['href'] if a else None)
        if e:
            out.append(e)
    return out


def cmu_filterable_cards(h, sections=None):
    """Hugo-style filterable cards (LTI lti.cmu.edu/people/faculty 2024-, S3D faculty-index 2022-): div.filterable, h2 > a.name, optional h3 title.
    `sections` limits the read to div.section-id ids (LTI: core-faculty-bios; its affiliated and adjunct sections are other slots' groups)."""
    soup = BeautifulSoup(h, 'html.parser')
    roots = [d for d in soup.select('div.section-id') if sections is None or d.get('id') in sections] or [soup]
    out = []
    for root in roots:
        for card in root.select('div.filterable'):
            h2 = card.select_one('h2')
            if h2 is None:
                continue
            h3 = card.select_one('h3')
            a = h2.select_one('a[href]')
            e = _cmu_entry(_cmu_t(h2), [_cmu_t(h3)] if h3 is not None else [], a['href'] if a else None)
            if e:
                out.append(e)
    return out


def cmu_lti_cards(h):
    return cmu_filterable_cards(h, {'core-faculty-bios'})


def cmu_bio_h1_h2(h):
    """ISR and MLD hand-built bio pages 2016-2017H1 (people/core-faculty.html): <h1>Name</h1><h2>Title</h2> per person after the page's own heading."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for h1 in soup.select('#mainContent h1, div.content h1'):
        h2 = h1.find_next_sibling('h2')
        nxt = h1.find_next_sibling(['h1', 'h2'])
        if h2 is None or nxt is not h2:
            continue
        e = _cmu_entry(_cmu_t(h1), [_cmu_t(h2)])
        if e:
            out.append(e)
    return out


def cmu_bio_h2_h3(h):
    """ISR and MLD bio pages and cards 2017H2-2026 (people/core-faculty.html): <h2>Name</h2> (a link on the card pages) followed by <h3>Title</h3>;
    an <h2> without an <h3> right after it is page furniture."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for h2 in soup.select('h2'):
        h3 = h2.find_next_sibling()
        while h3 is not None and h3.name not in ('h2', 'h3', 'h1', 'h4') and h3.name in ('p', 'span') and not _cmu_t(h3):
            h3 = h3.find_next_sibling()
        if h3 is None or h3.name != 'h3' or h3.get('class') and 'collapsed' in h3['class']:
            continue
        a = h2.select_one('a[href]')
        e = _cmu_entry(_cmu_t(h2), [_cmu_t(h3)], a['href'] if a else None)
        if e:
            out.append(e)
    return out


def cmu_ri_legacy(h):
    """RI ri_people.html?fcode=N (2016): one table per person, name in a bold link, the title in the next row's <b>; contact rows are never read."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for font in soup.select('table font[style*="font-weight:bold"]'):
        a = font.select_one('a[href]')
        tr = font.find_parent('tr')
        nxt = tr.find_next_sibling('tr') if tr is not None else None
        b = nxt.find('b') if nxt is not None else None
        if a is None or b is None:
            continue
        e = _cmu_entry(_cmu_t(a), [_cmu_t(b)], a['href'])
        if e:
            out.append(e)
    return out


def cmu_ri_cards(h):
    """RI people/faculty (WordPress 2017-2026: a table, div.RIperson, then div.ri_person): <strong><a>Name</a></strong>, then the title line before the next <br>."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for strong in soup.select('strong'):
        a = strong.find('a', href=True)
        if a is None or not re.search(r'/ri-[a-z]+/', a['href']):
            continue
        title = ''
        for sib in strong.next_siblings:
            if isinstance(sib, str):
                if sib.strip():
                    title = ' '.join(sib.split())
                    break
            elif sib.name == 'br':
                continue
            else:
                break
        e = _cmu_entry(_cmu_t(a), [title], a['href'])
        if e:
            out.append(e)
    return out


def cmu_hcii_cards(h):
    """HCII people/faculty: Drupal 7 cards 2016-2022H1 (li.t-card-listing--card, h3 link, pane-node-field-up2-job-title) and Drupal 9 teasers 2022H2-
    (div.person-teaser, h2 link, h3.faculty-content-heading-position)."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for li in soup.select('li.t-card-listing--card'):
        h3 = li.select_one('h3 a[href]')
        t = li.select_one('.pane-node-field-up2-job-title')
        if h3 is None:
            continue
        e = _cmu_entry(_cmu_t(h3), [_cmu_t(t)] if t is not None else [], h3['href'])
        if e:
            out.append(e)
    for card in soup.select('div.person-teaser'):
        a = card.select_one('h2 a[href]')
        t = card.select_one('.faculty-content-heading-position')
        if a is None:
            continue
        e = _cmu_entry(_cmu_t(a), [_cmu_t(t)] if t is not None else [], a['href'])
        if e:
            out.append(e)
    return out


def cmu_s3d_index(h):
    """ISR/S3D people/faculty-index.html: <h1>Core Faculty</h1> / <h1>Affiliated Faculty</h1> sections of <h2>Dr. Name</h2> cards with no title line
    (the section heading is the category; Post Docs and other sections are not faculty and are skipped)."""
    soup = BeautifulSoup(h, 'html.parser')
    out, section = [], None
    for el in soup.find_all(['h1', 'h2']):
        if el.name == 'h1':
            section = _cmu_t(el)
            continue
        if section not in ('Core Faculty', 'Affiliated Faculty'):
            continue
        a = el.select_one('a[href]')
        e = _cmu_entry(_cmu_t(el), [], a['href'] if a else None, division=section)
        if e:
            out.append(e)
    return out


def cmu_cbd_connections(h):
    """CBD directory/faculty/voting-faculty (WordPress Connections, 2016-2020): div.cn-entry, span.fn.n given + family name (kept given-first, as the page prints it), span.title."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for entry in soup.select('div.cn-entry'):
        fn, family = entry.select_one('.fn'), entry.select_one('.family-name')
        title = entry.select_one('span.title')
        if fn is None or family is None:   # the .fn span prints given, additional (middle) and family names in order
            continue
        a = entry.select_one('.fn a[href]')
        e = _cmu_entry(_cmu_t(fn), [_cmu_t(title)] if title is not None else [], a['href'] if a else None)
        if e:
            out.append(e)
    return out


def cmu_cbd_cards(h):
    """CBD people/voting-faculty.html (2021-): a div per person, <h2>Name</h2>, then <p><strong>Title</strong><br>Carnegie Mellon University<br>unit</p>."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for h2 in soup.select('h2'):
        strong = h2.find_next_sibling('p')
        strong = strong.find('strong') if strong is not None else None
        # the picture paragraph comes first on the card
        p = h2.find_next_sibling('p')
        while p is not None and p.find('strong') is None and p.find_next_sibling('p') is not None and p.find('img') is not None:
            p = p.find_next_sibling('p')
        strong = p.find('strong') if p is not None else None
        if strong is None:
            continue
        a = h2.select_one('a[href]')
        e = _cmu_entry(_cmu_t(h2), [_cmu_t(strong)], a['href'] if a else None)
        if e:
            out.append(e)
    return out


def _cmu_directory_feed(unit_rx):
    """The SCS-wide directory feed behind www.cs.cmu.edu/directory (JSON {data: [{n, aff, titl[], dept[]}]}, archived 2025-2026): one reader per unit, counting a
    record for the unit only when its own `dept` list names it (the record carries every department of a person; students and staff keep their `aff`)."""
    rx = re.compile(unit_rx)

    def read(h):
        try:
            data = json.loads(h)
        except ValueError:
            return []
        records = data.get('data') if isinstance(data, dict) else data
        out = []
        for r in records if isinstance(records, list) else []:
            if not isinstance(r, dict) or not isinstance(r.get('n'), str):
                continue
            depts = [' '.join(H.unescape(x).split()) for x in r.get('dept') or [] if isinstance(x, str)]
            titles = [' '.join(H.unescape(x).split()) for x in r.get('titl') or [] if isinstance(x, str)]
            if any(rx.search(d) for d in depts):
                e = _cmu_entry(r['n'], titles, division=r.get('aff'))
                if e:
                    out.append(e)
        return out
    return read


CMU_DIRECTORY_UNITS = {'csd': r'\bComputer Science Department\b', 'mld': r'\bMachine Learning Department\b', 'lti': r'\bLanguage Technologies Institute\b',
                       'ri': r'^Robotics Institute$', 'hcii': r'\bHuman-Computer Interaction Institute\b',
                       's3d': r'\b(?:Software and Societal Systems Department|Institute for Software Research)\b', 'cbd': r'\bComputational Biology Department\b'}
for _unit, _rx in CMU_DIRECTORY_UNITS.items():
    FORMATS[f'cmu_scs_directory_{_unit}'] = (_cmu_directory_feed(_rx), re.compile(r'(?!)'))

for _name, _fn in [('cmu_scs_views_table', cmu_scs_views_table), ('cmu_lti_directory', cmu_lti_directory), ('cmu_lti_cards', cmu_lti_cards),
                   ('cmu_bio_h1_h2', cmu_bio_h1_h2), ('cmu_bio_h2_h3', cmu_bio_h2_h3), ('cmu_ri_legacy', cmu_ri_legacy), ('cmu_ri_cards', cmu_ri_cards),
                   ('cmu_hcii_cards', cmu_hcii_cards), ('cmu_s3d_index', cmu_s3d_index), ('cmu_cbd_connections', cmu_cbd_connections),
                   ('cmu_cbd_cards', cmu_cbd_cards)]:
    FORMATS[_name] = (_fn, re.compile(r'(?!)'))


# ---- Peking University: Wangxuan Institute (WICT) and School of Intelligence Science and Technology (SIST), Stage 1 2026-11-18 ----------------------------
def _pku_clean(t):
    return ' '.join(t.replace('\xa0', ' ').split())


def pku_wict_team_nav(h):
    """WICT www.icst.pku.edu.cn/team/content_86.htm (2016-2018 site): the left menu `li.leftchild` links read `name_ title` (the underscore divides name and rank)."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for a in soup.select('li.leftchild > a[href]'):
        name, sep, title = _pku_clean(a.get_text('', strip=True)).partition('_')
        name, title = name.replace(' ', ''), title.strip()
        if sep and name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None, division=None, profile=a['href']))
    return out


def pku_wict_cards(h):
    """WICT www.icst.pku.edu.cn/xztd/xztd_01/index.htm (2019-): `ul.m-list > li` with `div.m-tt` holding the name link and `<em>` rank (20 per page, `indexN.htm` pager)."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for tt in soup.select('ul.m-list div.m-tt'):
        a, em = tt.select_one('a[href]'), tt.select_one('em')
        name = _pku_clean(a.get_text(' ', strip=True)).replace(' ', '') if a else ''
        title = _pku_clean(em.get_text(' ', strip=True)) if em else ''
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None, division=None, profile=a['href']))
    return out


def pku_sist_cards(h):
    """SIST sai.pku.edu.cn/szdw/zzjs.htm (Webplus, 8 per page, reverse-numbered pager): `div.ltjs_text` with `<h3>` name and `<dd><b>职称：</b>rank</dd>`; contact lines are not kept."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for box in soup.select('div.ltjs_text'):
        h3 = box.select_one('h3')
        title = ''
        for dd in box.select('dd'):
            b = dd.select_one('b')
            if b and b.get_text(strip=True).rstrip('：:') == '职称':
                title = _pku_clean(dd.get_text(' ', strip=True))[len(_pku_clean(b.get_text(' ', strip=True))):].strip()
        a = box.find_parent('a')
        name = _pku_clean(h3.get_text(' ', strip=True)).replace(' ', '') if h3 else ''
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None, division=None, profile=a['href'] if a and a.get('href') else None))
    return out


def pku_cs_m_list9(h):
    """PKU CS cs.pku.edu.cn/szdw1/jyxl.htm (2020-2023, 教研系列; Webplus, 8 per page, reverse-numbered pager): `ul#teachernamelist > li` with `h4` name link, then `<p>` rank and `<p>` institute."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for li in soup.select('ul#teachernamelist > li'):
        a = li.select_one('h4 a')
        ps = [_pku_clean(p.get_text(' ', strip=True)) for p in li.select('div.txt p')]
        name = _pku_clean(a.get_text(' ', strip=True)).replace(' ', '') if a else ''
        if name and ps and ps[0]:
            out.append(dict(name_listed=name, titles=[ps[0]], homepage=None, division=ps[1] if len(ps) > 1 and ps[1] else None, profile=a.get('href')))
    return out


def pku_cs_big_cards(h):
    """PKU CS cs.pku.edu.cn/szdw/jyxl/amz/ALL.htm (2023-, all series; 12 per page): `div.con` with `<h3><big>name</big>`, `<p>职称：rank</p>`, `<p>研究所：unit</p>`; contact lines are not kept."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for h3 in soup.select('div.con > h3'):
        big = h3.select_one('big')
        name = _pku_clean(big.get_text(' ', strip=True)).replace(' ', '') if big else ''
        title = division = ''
        for p in h3.find_next_siblings('p'):
            t = _pku_clean(p.get_text(' ', strip=True))
            if t.startswith('职称') and not title:
                title = t.split('：', 1)[-1].split(':', 1)[-1].strip() if ('：' in t or ':' in t) else ''
            elif t.startswith('研究所') and not division:
                division = t.split('：', 1)[-1].strip()
        a = h3.find_parent('a') or (h3.find_parent('li').select_one('a[href]') if h3.find_parent('li') else None)
        if name and title:
            out.append(dict(name_listed=name, titles=[title], homepage=None, division=division or None, profile=a.get('href') if a else None))
    return out


for _name, _fn in [('pku_cs_m_list9', pku_cs_m_list9), ('pku_cs_big_cards', pku_cs_big_cards), ('pku_wict_team_nav', pku_wict_team_nav), ('pku_wict_cards', pku_wict_cards), ('pku_sist_cards', pku_sist_cards)]:
    FORMATS[_name] = (_fn, re.compile(r'(?!)'))


def _first_parse(*fns):
    def read(h):
        for fn in fns:
            es = fn(h)
            if es:
                return es
        return []
    return read


pku_wict_any = _first_parse(pku_wict_team_nav, pku_wict_cards)   # one slot spans both site eras
pku_cs_any = _first_parse(pku_cs_m_list9, pku_cs_big_cards)
FORMATS['pku_wict_any'] = (pku_wict_any, re.compile(r'(?!)'))
FORMATS['pku_cs_any'] = (pku_cs_any, re.compile(r'(?!)'))


def uw_hcde_h3(h):
    """UW HCDE faculty page, archived eras 2016-2025 (Wayback): an A-Z table, one cell per person: `<h3>` holding a photo and the name (as
    `<strong><a>`, `<a><strong>`, `<a><img/><strong>` or a bare `<a>`; anchors `<a id="A">` carry no text), then the first `<p>` (sometimes inside a
    `<div>`) with the title, which 2016-2019 continues after `<br/>` with Website | Email links (cut at the first `<br/><strong>` / `<strong>` / `<a`).
    A heading counts only when it holds a photo or a bold name and the name has two words (menus and sidebars: 'Helpful Links', 'People')."""
    out = []
    for m in re.finditer(r'<h3>(.*?)</h3>\s*(?:<div>\s*)?<p>(.*?)</p>', h, re.S):
        inner, p = m.group(1), m.group(2)
        if '<img' not in inner and '<strong>' not in inner:
            continue
        nm = clean(re.sub(r'<img\b[^>]*>', ' ', inner))
        if not nm or len(nm.split()) < 2 or len(nm) > 60:
            continue
        hrefs = [x for x in re.findall(r'<a\s+href="([^"#][^"]*)"', inner)]
        p = re.split(r'<br\s*/?>\s*(?:<strong>|<a\b)|<strong>|<a\b', p, maxsplit=1)[0]
        out.append(dict(name_listed=nm, titles=_titles(p), homepage=H.unescape(hrefs[-1]) if hrefs else None, division=None))
    return out


uw_hcde_any = _first_parse(uw_hcde_columns, uw_hcde_h3)   # one slot spans the archived (h3 table) and current (h2 columns) eras
FORMATS['uw_hcde_h3'] = (uw_hcde_h3, re.compile(r'(?!)'))
FORMATS['uw_hcde_any'] = (uw_hcde_any, re.compile(r'(?!)'))


def northeastern_people_directory(h):
    """Northeastern CCIS/Khoury WordPress `people-view-all` page 2018-2020: article.people-directory, name link in h3.person-name, the listed
    position(s) in span.position. The page lists students, staff and faculty together, so only rows whose position names a faculty-type
    appointment (professor, lecturer, faculty, scientist, instructor, dean, chair, emerit*) are kept. E-mail and phone are never returned."""
    soup = BeautifulSoup(h, 'html.parser')
    keep = re.compile(r'professor|lecturer|faculty|scientist|instructor|dean\b|chair\b|emerit|research\s+(?:associate|fellow)|practice', re.I)
    out = []
    for art in soup.select('article.people-directory'):
        link = art.select_one('h3.person-name a')
        if not link:
            continue
        name = ' '.join(link.get_text(' ', strip=True).split())
        titles = [' '.join(s.get_text(' ', strip=True).split()) for s in art.select('.position-list .position')]
        titles = [t for t in titles if t]
        if name and titles and any(keep.search(t) for t in titles):
            out.append(dict(name_listed=name, titles=titles, homepage=None, division=None, profile=link.get('href')))
    return out


FORMATS['northeastern_people_directory'] = (northeastern_people_directory, re.compile(r'<article class="people-directory"'))


def northeastern_ccs_headshots(h):
    """Northeastern CCIS WordPress faculty pages 2016- (www.ccs.neu.edu/people/faculty/ and its category subpages): div.headshot, the profile link
    (.../people/faculty/member/<slug>/), p.name and p.position. Each category page is its own slot; the page carries no contact details."""
    soup = BeautifulSoup(h, 'html.parser')
    out = []
    for box in soup.select('div.headshot'):
        link = box.select_one('a[href]')
        name = box.select_one('p.name')
        if not link or not name:
            continue
        titles = [' '.join(p.get_text(' ', strip=True).split()) for p in box.select('p.position')]
        titles = [t for t in titles if t]
        nm = ' '.join(name.get_text(' ', strip=True).split())
        if nm and titles:
            out.append(dict(name_listed=nm, titles=titles, homepage=None, division=None, profile=link['href']))
    return out


FORMATS['northeastern_ccs_headshots'] = (northeastern_ccs_headshots, re.compile(r'<div class="headshot">'))
