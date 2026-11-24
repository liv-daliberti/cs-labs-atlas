"""R-PAP-42: an OpenAlex author id judged by the ORCID it carries against the ORCIDs of the PI's source-bound DBLP person record."""


def bare(orcid):
    return (orcid or '').replace('https://orcid.org/', '').strip().upper() or None


def classify(author_orcid, pi_orcids, verified_works_under_id):
    """'match' (stays anchored), 'mixed' (conflict, but a DBLP-DOI-verified work of the PI sits under the id: R-PAP-06),
    'not' (conflict, none does: namesake id) or 'undecided' (the id carries no ORCID: per-work review)."""
    a = bare(author_orcid)
    if not a or not {bare(o) for o in pi_orcids}:   # no ORCID on the id, or none known for the PI: nothing to conflict with
        return 'undecided'
    if a in {bare(o) for o in pi_orcids}:
        return 'match'
    return 'mixed' if verified_works_under_id else 'not'
