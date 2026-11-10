"""R-PAP-44: a DBLP person binding from credited exact titles alone (no Chinese+English self-name on a source).

Owner-delegated 2026-11-09. Accept only when (a) the PI's own official profile or owned page credits at least MIN_TITLES
exact long DBLP titles and every one of them belongs to the one candidate person, (b) that person carries a school
affiliation note OR the exact-title list sits on a page the school's own official listing links as that PI's page (url and
sha256 recorded; amended 2026-11-09, owner-delegated), and (c) no other DBLP person of the same base name (a namesake) also
owns one of the matched titles. Pinyin-name-only matches never qualify. Pure function: the evidence is gathered by the caller."""
import re

MIN_TITLES = 10


def base_name(name):
    return re.sub(r'\s+\d{4}$', '', name or '').strip().lower()


def decide(matched_keys, persons, pid, affiliated, listing_linked_page=None):
    """matched_keys: DBLP record keys of the credited exact titles found on the PI's own page.
    persons: {pid: {'names': [...], 'keys': set of record keys}}.
    affiliated: the DBLP person carries a school affiliation note. listing_linked_page: {'url', 'sha256'} of the page the
    official listing links as the PI's page, which holds the titles (alternative to the note). Returns (accepted, reason)."""
    keys = set(matched_keys)
    if len(keys) < MIN_TITLES:
        return False, 'fewer_than_10_exact_titles'
    own = persons.get(pid)
    if own is None or not keys <= own['keys']:
        return False, 'titles_not_all_on_one_person'
    page_ok = bool(listing_linked_page and listing_linked_page.get('url') and listing_linked_page.get('sha256'))
    if not (affiliated or page_ok):
        return False, 'no_school_affiliation'
    mine = {base_name(n) for n in own['names']}
    for other, p in persons.items():
        if other != pid and {base_name(n) for n in p['names']} & mine and keys & p['keys']:
            return False, 'namesake_shares_matched_titles'
    return True, 'accepted'
