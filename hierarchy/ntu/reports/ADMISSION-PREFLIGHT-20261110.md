# NTU admission preflight, 2026-11-10 (claude-ntu-1110)

Partial: identity preflight done, first isolated native built and reviewed in part. Not admitted.

- **PI contexts 103 -> 100.** Gong Tiantian / Tiantian Gong, Cheng Yu / Yu Cheng and Li Penghui / Penghui Li are one person each: the same official directory lists them surname-first (/computing/our-faculty) and given-name-first (/computing/our-faculty/faculty-at-ccds), with the same college, rank and area. The surname-first record is kept, the other card and its sha256 move into its `sources` and `aliases`. Both Li Yi contexts stay held.
- **DBLP identity.** 9 owned PIDs -> 63 bound (54 by rule, local dump only; `dblp_ids_school.py` + R-PAP-42/44), 37 held. school_affiliation 36 and school_coauthors 8 kept (Toronto precedent); unique_name/unique_exact_name accepted only with an ORCID agreeing with an NTU-affiliated OpenAlex author (from the 119,037-work source sweep, offline) or 10+ owned-page titles. Decisions: `DBLP-BINDINGS-REVIEW-20261110.json`. ORCID inheritance stays `allowed: []`.
- **No live profile fetch.** dr.ntu.edu.sg (host `none`) answers robots.txt with an AWS WAF human-verification page: bot challenge, so live use is closed; profile pages could only come through Wayback.
- **Periods.** No new faculty period: the cached owned pages hold no further literal NTU start statements beyond the four already projected (Bian, Joty, Han Yu, Timothy van Bremen). The 2026 listings prove 2026 only.
- **Native inputs frozen** in scratch `ntu-admit-1110/native-v1/native-input-manifest.json` (sweep sha 75ba2aad..., 119,037 works / 800,497 authorships, sweep-check pass). Isolated native job 32178367 (afterany the queued ZJU native 32178276, itself afterany SJTU 32177967).

## First isolated native (job 32178779, pin 4305456, 2m55s, exit 0; all protected paths unchanged, offline)
- 61 of 100 PIs DBLP-bound (39 held; Du Yuxuan and Wei Lu were held by the identity spot check, see `DBLP-BINDINGS-REVIEW-20261110.json`; rule: a bound record with fewer than 10 records in 2016-2026 is held).
- Package: 1,569 lab-paper rows (1,517 works) for 53 PIs; 47 PIs have no paper (appointment evidence is the 2026 listing only); 105 member pairs/106 relations unchanged; 234 student-paper candidates, 0 verified; schemas 0 errors.
- Source-title guard (R-PAP-41): 1,504 DOIs checked, 1 hold (Long Cheng, arXiv 2605.21987 `Generative Conversational Recommender System` vs `HGCRS: ...`: a retitling, reviewer clears).
- Identity hand check of 50 bindings: 2 wrong (both held), 2 unsure (Will Cong, Djordje Zikelic: DBLP affiliation elsewhere, ORCID agrees with an NTU OpenAlex author, 0 package papers), 46 ok.
- Isolated ID preparation: 1,802 new IDs, 0 changed issued IDs, 0 redirects, 20 existing work IDs reused; registry untouched.
- Offline copy reuse plan: 25 NTU DOIs (26 papers) already have a local copy in other schools' catalogs; nothing imported.

## Native v3 (job 32183525, pin 5160a48, 3m59s, exit 0), 2026-11-10
Official-profile ORCIDs (Wayback) bound 5 more PIs (66 bound, 34 held) and allow 11 ORCIDs. Package: 1,696 rows (v2 1,569), 1,640 works (1,517), 54 PIs with papers (53); 127 rows gained, all for Liu Yang (2026 only, ORCID identity, NTU raw affiliations, security/software-engineering topics; 16 sampled titles ok), 0 lost; schemas 0 errors; protected paths unchanged; identity-withheld authorships 2,810 -> 1,507. `pi_orcid` is the identity of 436 rows (Niyato 238, Liu 127, Cong 22, Tan 15, Rajapakse 14, Bei 11, Easwaran 9); 435 carry an NTU raw affiliation, 1 is a cross-affiliated byline (R-PAP rule). Namesake OpenAlex ids: 0 of 288 anchored ids (mixed_openalex check). Identity check of the 5 new and 6 ORCID-corroborated bindings: 11 ok (Gouleakis, Ke Yiping, Lee Bu Sung, Miao Chun Yan add no rows).

## Native v4 (job 32184458, pin 64e5c8a, 4m13s, exit 0), 2026-11-10
Adds four literal faculty-start periods (Niyato 2008-07, Ong 2022-08, X. Wang 2025-07-01, Vun 1991). Package: 3,339 rows (v3 1,696), 3,252 works (1,640), 54 PIs with papers; Niyato 239 -> 1,863 (2016-2026), Ong 7 -> 19 (2023-2026), Wang 28 -> 35 (2025-2026), identity-held Vun 0 rows; 1 row lost (a 2026 Niyato row folded into another); schemas 0 errors; protected paths unchanged; mixed_openalex check 0 of 288 anchored ids. Stage 1: the SCSE faculty list exists in Wayback for 2021 only (79 cards, parser `ntu_img_cards`); 2016-2020 and 2022-2025 have no capture of any faculty list.
