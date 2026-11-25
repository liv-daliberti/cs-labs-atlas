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

## Coordinator review fixes (2026-11-25)
- **Cross-school check:** all 159 Cornell PIs against the derived/pis.json of the 38 other atlas schools (exact and relaxed name match). Real same-person matches: Delimitrou and Huttenlocher (MIT), Shi (CMU), Foster (EPFL), Alvisi (UT Austin), Udell (Stanford), Haghtalab, Parikh and Pierson (Berkeley), Rush and Sabuncu (Harvard), Pollack and Owens (Michigan). DBLP pid and ORCID agree with Cornell's wherever both exist; the OpenAlex ids agree for Udell, Parikh and Rush (recorded in their `why`). No disagreement between schools. Two ids are adopted from other schools: Tapan Parikh DBLP 02/5011 (Berkeley; Cornell had held only the name-only 193/6414, not adopted) and Andrew Owens DBLP 85/2697 (Michigan; the candidate Cornell held). Weinberger, Wilson, Kuleshov, Knepper, Alvisi's co-movers etc. are mostly not PIs elsewhere in the atlas, so their ids rest on the DBLP person and ORCID. The Michigan record "Jose Lugo-Martinez" (CMU) is a different person from Jose F. Martinez (different DBLP pid and ORCID).
- **Nate Foster, Delimitrou, Shi:** OpenAlex ids exist (A5013378091 73 works; A5001498296 51; A5089202539 77) with ORCIDs equal to DBLP and to the EPFL, MIT and CMU atlas records. The proposals tool had skipped all three (other prolific PIs that went this way: none; the other DBLP-only PIs have no school works: Huttenlocher, Van Loan, and the namesake cases Wen Sun and Michael Kim). Added as reviewed decisions: 152 now.
- **Monakhova:** anchored by DBLP 248/2731 and ORCID 0000-0002-0100-8704 (name plus computational-imaging field; she has a lab site), in `census-overrides-school.json`.
- **Pollack, Brachman:** excluded as non-PIs under D-0009 (`no_advising_or_lab_evidence`, reversible): President and Professor; Director of the Jacobs Technion-Cornell Institute; the lab-page audit found no site, and no advising evidence. 159 PIs become 157 at the next build.
- **Wen Sun, Michael Kim:** anchored by DBLP pid (and Sun's ORCID 0000-0003-4322-5878); OpenAlex ids stay open per PI (all candidates are namesakes); the homepage-links job may settle them.
- **Anchor counts after the fixes (157 PIs):** DBLP pid 134 (plus 4 now carry Cornell-adopted pids), ORCID about 92, reviewed OpenAlex id 152; no PI without an anchor. `stage-gate cornell 5` still fails until `oa_identity_school.py` runs (needs the stage-2 `cs-related-review.json`).
