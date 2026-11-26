# KAIST onboarding, stage 5 (identity), in progress 2026-11-24

Strict per D-0064: `[identity] name_only = "propose"` and a 100-entry Korean `common_surnames` list (first or last token, comma form handled). The name-only DBLP rules (unique_name, unique_exact_name) and, for a common-surname PI, school_affiliation and school_coauthors only PROPOSE; only an identifier binds (homepage URL on the DBLP record equal to the PI's own page, ORCID). OpenAlex: `oa_identity_candidates.py` auto-accepts a unique name match only when the author id carries the PI's ORCID; every other match is held (`held_name_only`).
Own-website links (the website field of each PI's CS profile card, 77 of 77) feed the homepage-equality rule (`profile_websites_school.py`, reviewed/extra-lab-pages.json).

| kind | PIs (of 77) |
|---|---|
| DBLP via homepage URL on the record | 11 |
| DBLP via link on the PI's own homepage | 3 |
| DBLP via school affiliation (rare surname) | 2 |
| DBLP via school coauthors (rare surname) | 1 |
| ORCID | 11 |
| OpenAlex id with the PI's ORCID (written, not yet applied) | 10 |
| held name-only DBLP proposals | 47 |
| held name-only OpenAlex proposals | 61 (6 unmatched) |
| no_identity declared | 0 (none declared yet; every held PI stays open) |

Blocker: `oa_identity_school.py` needs `reviewed/cs-related-review.json`, which `cs_related_school.py review` writes only after the units search finishes. No identity audit drawn.
