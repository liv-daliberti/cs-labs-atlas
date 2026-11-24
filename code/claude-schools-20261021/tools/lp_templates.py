"""Structural readers for lab-page templates (ROADMAP P2 #27): al-folio/Jekyll, Google Sites and WordPress team pages.

The flattened page text the member extractor reads runs adjacent one-line sections together ('Postdocs and Visitors: A, B
Undergraduate Researchers: C'), so a name can take the neighbouring section's role. These readers walk the HTML instead:
`detect(html, url)` names the template, `locate(html, template, name)` returns the heading chain and the entry text that
contain a name, from the DOM (a heading element and the siblings up to the next heading of the same or a higher level; an
entry is a list item, table row, card, column or paragraph). Used by tools/labpage_audit.py to set a template page's
section and entry text before the rules run. Pure functions of the HTML: no network, no files.
"""
import re

from bs4 import BeautifulSoup, NavigableString

TEMPLATES = ('google_sites', 'wordpress', 'al_folio')
HEADING_CLASS = re.compile(r'wp-block-heading|elementor-heading-title|entry-title|section-title|card-title|heading', re.I)
ROLE_LABEL = re.compile(r'\b(?:students?|postdocs?|post-?doctoral|alumni|alumnae|faculty|staff|undergraduates?|visitors?|researchers?|members?|collaborators?|interns?|scholars?|fellows?|team)\b', re.I)
ENTRY_TAGS = ('li', 'tr', 'p', 'td', 'dd')
ENTRY_CLASS = re.compile(r'(?:^|\s)(?:team-member|wp-block-column|card|profile|person|member|elementor-widget-wrap)(?:\s|$)', re.I)


def detect(html, url=''):
    """'google_sites' | 'wordpress' | 'al_folio' | None."""
    h = (html or '')[:20000].lower()
    u = (url or '').lower()
    if 'sites.google.com' in u or 'name="generator" content="google sites"' in h or 'gstatic.com/atari' in h or 'sites.google.com' in h[:5000]:
        return 'google_sites'
    if 'al-folio' in h or 'al_folio' in h or ('jekyll' in h and ('class="profile' in h or 'class="people' in h or 'navbar-brand' in h)):
        return 'al_folio'
    if 'wp-content' in h or 'content="wordpress' in h or 'wp-block-' in h:
        return 'wordpress'
    return None


def _level(el):
    if re.fullmatch(r'h[1-6]', el.name or ''):
        return int(el.name[1])
    if el.get('role') == 'heading':
        try:
            return int(el.get('aria-level') or 3)
        except ValueError:
            return 3
    if el.name in ('div', 'span', 'p', 'strong', 'b') and HEADING_CLASS.search(' '.join(el.get('class') or [])) and len(el.get_text(' ', strip=True)) < 80:
        return 4
    if el.name in ('p', 'div', 'strong', 'b', 'em', 'span', 'dt', 'summary') and len(el.get_text(' ', strip=True)) < 48:
        t = el.get_text(' ', strip=True)
        whole = el.name in ('strong', 'b', 'em') and el.parent is not None and el.parent.get_text(' ', strip=True) == t
        if ROLE_LABEL.search(t) and not re.search(r'\b(?:19|20)\d\d\b', t) and (t.endswith(':') or whole or el.name in ('dt', 'summary')):
            return 7  # a bold or colon-terminated sub-label ("Master's students:") inside a section
    return None


def sections(html):
    """[(heading chain 'Students > PhD Students', [entry texts])] in document order."""
    soup = BeautifulSoup(html or '', 'lxml')
    for t in soup(['script', 'style', 'noscript', 'nav', 'header', 'footer']):
        t.decompose()
    chain, out, cur = [], [], None
    def in_card(el):
        return any(a.name == 'div' and ENTRY_CLASS.search(' '.join(a.get('class') or [])) for a in el.parents)

    for el in soup.descendants:
        if isinstance(el, NavigableString):  # a bare text label between a heading and a list: 'Postdocs' / 'Ph.D. Students'
            t = str(el).strip()
            if (t and len(t) < 48 and ROLE_LABEL.search(t) and not re.search(r'\d', t) and el.parent is not None
                    and el.parent.name in ('body', 'div', 'section', 'article', 'main', 'p', 'td', 'span')
                    and not any(a.name in ('li', 'a', 'dd', 'tr') for a in el.parents)
                    and (el.parent.name in ('body', 'div', 'section', 'article', 'main') or len(el.parent.get_text(' ', strip=True)) < 48 + len(t))
                    and not in_card(el)):
                lv0 = 7
                chain = [(l, tt) for l, tt in chain if l < lv0] + [(lv0, t.rstrip(':'))]
                cur = (' > '.join(tt for _, tt in chain), [])
                out.append(cur)
            continue
        lv = _level(el)
        if lv is not None and not in_card(el):
            txt = el.get_text(' ', strip=True)
            if not txt:
                continue
            chain = [(l, t) for l, t in chain if l < lv] + [(lv, txt)]
            cur = (' > '.join(t for _, t in chain), [])
            out.append(cur)
            continue
        if cur is None or (lv is not None):
            continue
        cls = ' '.join(el.get('class') or [])
        is_card = el.name == 'div' and ENTRY_CLASS.search(cls)
        if not (el.name in ENTRY_TAGS or is_card) or in_card(el):
            continue
        if is_card:
            if el.find(lambda e: e is not el and e.name == 'div' and ENTRY_CLASS.search(' '.join(e.get('class') or []))):
                continue  # a container of cards: its cards are the entries
        elif el.find(lambda e: e is not el and e.name in ENTRY_TAGS):
            continue  # a container: its children are the entries
        txt = el.get_text(' ', strip=True)
        if txt and len(txt) < 600:
            cur[1].append(txt)
    return out


def locate(html, name):
    """(heading chain, entry text) of the smallest entry that contains `name`, else (None, None)."""
    return locate_in(sections(html), name)


def locate_in(secs, name):
    """locate() over already parsed sections()."""
    nm = re.sub(r'\s+', ' ', name or '').strip().lower()
    if not nm:
        return None, None
    best = (None, None)
    for head, entries in secs:
        for e in entries:
            if nm in re.sub(r'\s+', ' ', e).lower() and (best[1] is None or len(e) < len(best[1])):
                best = (head, e)
    return best
