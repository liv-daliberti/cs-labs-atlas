# Georgia Institute of Technology, stage 5: identity

Date: 2026-11-04. `atlas stage-gate gatech 5 --run --submit --from-worktree` (jobs 32099101 dblp-ids, 32099102 homepage-links, 32099103 dblp-dump-persons, all COMPLETED), then the OpenAlex review. Gate: **pass** (454 PIs: 206 DBLP + ORCID, 157 DBLP only, 88 reviewed OpenAlex ids, 3 reviewed `no_identity`).

## What was done
- DBLP ids (rules: homepage URL, school affiliation note, unique exact name, unique name) and ORCIDs from the DBLP persons: 363 of 454 PIs. 91 were left (mostly the 105 PIs of other units, whose DBLP records rarely name the school).
- **New tool `tools/oa_identity_candidates.py`** (test) proposes OpenAlex author ids for those 91 from `oa-author-stats.json.gz`: same family name, spelled-out first given name equal (an initial only matches a PI who is listed by an initial; the author's most frequent raw name must itself match), no conflicting middle initial, 3+ school works, not a namesake (another ORCID than the PI's, or works ending before the first listing).
  A unique match, or one author with 20+ works and 5x the next, is accepted automatically (`auto: true`, with works, years, raw names, ORCID and venues as the `why`): **78 PIs**. Spot check of 14 random auto decisions against the PI's home department and the author's venues: all plausible (Ueda/Ames/Mazumdar mechatronics and robotics, Ting neurophysiology, Peng Qiu bioinformatics, Warnke combinatorics, Economou architecture, ...).
- **Hand decisions (10)** with evidence in `openalex-identity-review.json`: Babak Mahmoudi, Ken Brown (Kenneth R. Brown, quantum computing), Michael Hunter (transportation simulation), Peng Chen (CSE), Saman Zonouz (two ids, split profile), Sudheer Chava (four ids, one finance-and-NLP professor), Xin Chen (ISyE), Young Mi Choi, Hadi Esmaeilzadeh (the listing name carries a "Clone of" prefix), Steve Mussmann (Mussmann, Stephen).
- **Reviewed `no_identity` (3):** Francisco Romero (listed 2026 only), Veronica Rivera (starts Fall 2026), Merrick Furst (no OpenAlex author with 3+ school works matches; no school DBLP records 2016-2026). No papers are attributed to them.
- `tools/oa_identity_school.py` wrote the ids (88 people) into the school-local overrides with a sweep work as evidence (url, sha256, quote).
- Reza Sameni stays held (stage 4); no academic school turned up in this stage either.

## For the owner
- The 78 automatic matches are rule-based, not individually hand-read; the stage-9 accuracy sample will measure them. Say so if you want each read by hand first.
- Cross-school PIs (same person at another atlas school) should carry the same DBLP id or ORCID in both schools: not checked in this stage; stage 6 relies on it.
