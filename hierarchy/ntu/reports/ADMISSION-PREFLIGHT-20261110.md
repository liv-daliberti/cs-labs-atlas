# NTU admission preflight, 2026-11-10 (claude-ntu-1110)

Partial: identity preflight done, first isolated native queued, scientific review not started. Not admitted.

- **PI contexts 103 -> 100.** Gong Tiantian / Tiantian Gong, Cheng Yu / Yu Cheng and Li Penghui / Penghui Li are one person each: the same official directory lists them surname-first (/computing/our-faculty) and given-name-first (/computing/our-faculty/faculty-at-ccds), with the same college, rank and area. The surname-first record is kept, the other card and its sha256 move into its `sources` and `aliases`. Both Li Yi contexts stay held.
- **DBLP identity.** 9 owned PIDs -> 63 bound (54 by rule, local dump only; `dblp_ids_school.py` + R-PAP-42/44), 37 held. school_affiliation 36 and school_coauthors 8 kept (Toronto precedent); unique_name/unique_exact_name accepted only with an ORCID agreeing with an NTU-affiliated OpenAlex author (from the 119,037-work source sweep, offline) or 10+ owned-page titles. Decisions: `DBLP-BINDINGS-REVIEW-20261110.json`. ORCID inheritance stays `allowed: []`.
- **No live profile fetch.** dr.ntu.edu.sg (host `none`) answers robots.txt with an AWS WAF human-verification page: bot challenge, so live use is closed; profile pages could only come through Wayback.
- **Periods.** No new faculty period: the cached owned pages hold no further literal NTU start statements beyond the four already projected (Bian, Joty, Han Yu, Timothy van Bremen). The 2026 listings prove 2026 only.
- **Native inputs frozen** in scratch `ntu-admit-1110/native-v1/native-input-manifest.json` (sweep sha 75ba2aad..., 119,037 works / 800,497 authorships, sweep-check pass). Isolated native job 32178367 (afterany the queued ZJU native 32178276, itself afterany SJTU 32177967).
