"""R-PAP-06 criterion found at Tsinghua (2026-11-10): for a PI with an OWNED DBLP bibliography, an anchored OpenAlex author id whose
school works contain NONE of the PI's DBLP works (matched by DOI or normalised title) is another person's record: `mixed_openalex`
(each authorship then needs per-work evidence). Pure function plus a CLI that scans a sweep (see usage)."""
import re


def norm_title(t):
    return re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()


def norm_doi(d):
    return re.sub(r'^https?://(dx\.)?doi\.org/', '', (d or '').strip().lower())


def dblp_keys(pubs):
    """(dois, titles) of the PI's DBLP records (titles of 25+ characters only: short titles collide)."""
    dois = {norm_doi(d) for p in pubs for d in p.get('dois') or [] if d}
    titles = {norm_title(p.get('title')) for p in pubs if len(norm_title(p.get('title'))) >= 25}
    return dois, titles


def overlap(work_records, dois, titles):
    """How many of the id's works (dicts with doi, title) are DBLP works of the PI."""
    return sum(1 for w in work_records if (norm_doi(w.get('doi')) in dois and w.get('doi')) or norm_title(w.get('title')) in titles)


def verdict(work_records, pubs, min_pubs=5):
    """'mixed' when the PI has >= min_pubs DBLP records, the id has >= 1 school work and none is a DBLP work of the PI;
    'anchored_verified' when at least one is; 'undecided' otherwise (too few DBLP records or no work under the id)."""
    if len(pubs) < min_pubs or not work_records:
        return 'undecided'
    dois, titles = dblp_keys(pubs)
    return 'anchored_verified' if overlap(work_records, dois, titles) else 'mixed'
