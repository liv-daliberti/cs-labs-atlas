# Cornell onboarding, stage 5 (identity), started 2026-11-25 - hand step partly done for the 159 PIs

## Jobs
- dblp-ids **32547137** (6:42) and dblp-dump-persons **32547138** (5:57), 24G, 59 min, `--exclude node302`; both COMPLETED. Census re-run afterwards (177 persons, 159 PIs) folds the DBLP ids and ORCIDs in.
- homepage-links **32547140**, `afterok:32546302` (periods-fetch): pending, reads only the pages periods-fetch stored.

## DBLP ids (all 159 PIs evaluated)
Basis: homepage_url 52, school_affiliation 38, school_coauthors 29, unique_exact_name 7, unique_name 5, none 28. 131 PIs carry a DBLP pid, 91 an ORCID. The 28 without a pid were settled through OpenAlex below, except three (Pollack, Brachman, Monakhova).

## OpenAlex identity review (`hierarchy/cornell/reviewed/openalex-identity-review.json`, 149 decisions)
- `oa_identity_candidates.py cornell`: 124 auto (unique name match under family name and first given name, school works in the listed years), 26 ambiguous, 6 unmatched. I read all 124 auto entries (works, years, venues, ORCID against the DBLP ORCID): no ORCID conflicts, no non-computing namesake venue.
- 25 hand decisions with evidence (works, years, raw names, ORCID, venues): ORCID equal to the DBLP person for Silva, De Sa, Acharya, Martinez, Spooner, Agarwal, Galhotra, Dean, Ristenpart; two ids of one person for Wang, D. Lee, Martinez, Agarwal, Galhotra, Dean; namesakes set aside: urology Daniel J. Lee / Daniel Lee, materials-science Snehashis Choudhury (for Sanjiban Choudhury), a medical id for Weinberger. "Tom Ristenpart" is OpenAlex "Thomas Ristenpart" (alias added).
- **Blocked:** `oa_identity_school.py cornell` fails on the missing `hierarchy/cornell/reviewed/cs-related-review.json` (stage 2 review, blocked on units). It is run after stage 2; I did not fake that file.

## Anchors per PI (159)
| anchor | PIs |
|---|---|
| DBLP pid | 131 |
| ORCID (from DBLP) | 91 |
| reviewed OpenAlex id | 149 |
| DBLP only, no OpenAlex id | 7: Nate Foster, Daniel Huttenlocher, Elaine Shi, Charles Van Loan (left Cornell or no school works), Christina Delimitrou (left), Wen Sun, Michael Kim |
| **no anchor** | 3: Ronald Brachman, Martha E. Pollack, Kristina Monakhova |

## Open per PI (never block the others)
- Wen Sun: DBLP pid 69/1010-2 with ORCID 0000-0003-4322-5878; the OpenAlex candidates are all flagged namesakes (physics W. Sun with a different ORCID, one NeurIPS id 0009-0005-3752-2173 with 4 works 2024-25 that does not carry the DBLP ORCID). Cannot be settled from the stats; needs a homepage/ORCID check.
- Michael Kim: DBLP pid 165/2964 (homepage_url); all OpenAlex candidates are other Michael/Matthew/Mun Sek Kims in materials, orthopaedics and neurosurgery. No OpenAlex id.
- Brachman, Pollack: DBLP has a name-only person (b/RJBrachman with 3 window records among 2 candidates; p/MEPollack with 0 window records) that names no school; OpenAlex has no author with 3+ school works. Monakhova: one DBLP person (248/2731, 12 window records) names no school or homepage; no OpenAlex author. Each needs a homepage/CV link; otherwise `no_identity` + why.
- Cross-school movers (Cornell to or from MIT/CMU/Berkeley/etc.): ids were taken from the DBLP person / ORCID, not from another atlas school's lab; a check against the other schools' stores is still to do.

Not drawn: the identity audit (waits for the settled PI set).
