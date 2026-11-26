# NYU onboarding, stage 2 - 2026-11-25

Gate: `atlas stage-gate nyu 2` has ONE open item: "excluded_unresolved audit: no independent reviewer recorded". Everything else passes (candidates file present, no `pending_openalex`, sweep check done). The 50-row audit is drawn and NOT judged.

## Census (after the section-aware formats)
- 271 persons, 179 PIs (171 ladder_faculty, 8 courtesy_faculty). 29 CS-related additions accepted from other units (Courant Math/applied math, Steinhardt, Stern, CNS and others) are in `reviewed/census-additions.json`.
- The Courant CS and Tandon formats split the Associated/Affiliated groups into courtesy slots; Grossman faculty (Brandes, Lattanzi, J. Tan, Shenhav) and the Global Network Assistant Professor (Siby) are `census.not_pi` under D-0058.
- Trefethen stays ladder_faculty, window 2016-2017 only (owner ruling D-0075).

## CS-related review (candidates 391: 274 DBLP-affiliation, 117 OpenAlex-rule)
accepted 29; excluded_unresolved 358 (351 no_source_covers_window, 7 identity_collision); research_or_other_rank 3; census_alias 1.
Unit captures: MATH 10, CNS 3, PSYCH 5, LING 4, MCC 8, GROSSMAN 8 (script shells every year), CUSP 4, WAGNER 1, BIO 4, CHEM 4, PHYS 3, ITP 11 (shells), STERN 0, PHIL 0, ECON 0, POLITICS 0, DATASCI_STATS 0. The empty units are guessed URLs: most of the 351 unresolved rows are people of those units, so the audit is expected to find admissible faculty there.

## Audit draw
`reviewed/excluded-unresolved-audit.json`: seed 20377973d42d, population 358, sample 50, worker claude-nyu-1124 (reviewer fields empty).

## Notes
- ECE courtesy slot kept: the 2019 ECE capture does carry an Affiliated group; later ECE captures parse 0. Remaining half-years of that slot are unplanned (Wayback lane shared with stage 4), reported only.
- Jobs: snapshot-ext 32539354/55, onboard-data 32542906-09, captures 32542900/32563384, units 32543374/32543953.
