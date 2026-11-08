# Tsinghua native onboarding checkpoint — 2026-11-08

Status: onboarding, partial. No school-wide census, stage gate, paper package or release is declared complete.

The charter now identifies Tsinghua independently of National Tsing Hua University and commercial namesakes. Primary OpenAlex I99065089 and ROR03cve4549 were read from the existing local2026-10-14 institutions snapshot; no API request was used. The current reviewed source set covers Beijing CS, IIIS, Software, AIR and individually reviewed computing-related Automation/INSC appointments. Other computing departments, Shenzhen and historical faculty remain open. The17unreviewed lineage children are provisionally excluded from child-only attribution; this is an attribution hold pending review, not an assertion that these units are outside the university-wide research goal.

## Reproducible reviewed census

The standard `reviewed/census-additions.json` extension now contains the complete207-record source-reviewed checkpoint:119previously reviewed baseline identities plus88new records. The original88collection IDs and PI-basis proofs are preserved. There is no custom school builder. With an empty automatic-listing seed, `census_build.py` creates the collection people from these reviewed additions, and the ordinary census/member stages consume them.

The120baseline supported role rows contain one independently reconciled CS/AIR identity, Liu Yang. The two named official profiles share independently checked institutional identity information and agree on his2007CAS doctorate; exact contact details were not retained. Hu Shimin is the duplicate website-ledger entry, not this role duplicate. Two distinct pending Zhou Qiang profiles are not admitted and must never be merged from the written name alone.

Native identity handling uses the source spellings without guessed romanizations. Commit245c00f fixes the former collapse of88Chinese-only names into one group and provides stable lab-scoped member IDs. Duplicate unresolved PI display names stop before downstream name-keyed tables can discard a person.

## Isolated native check

| Measure | Result |
|---|---:|
| Reviewed PI rows / distinct native PI labels |207/207|
| First reviewed student–lab memberships |55|
| Labs with those memberships |6|
| Dated listing years |2026only|
| Historical appointment periods in this input |0|
| School papers admitted by this check |0|

The check runs the standard census seed, census loading, reviewed inputs, PI records, PI indexes and student gathering in a real isolated worktree. It does not run identity, paper or fulltext layers and does not overwrite a canonical package. Its receipt is `scratch/tsinghua-native-review-1108/native-summary.json`; reviewed-source staging and the first independent smoke are retained under `scratch/tsinghua-next-1108/native` and `native-smoke`.

An initial standard-input check correctly held one missing named-listing clause for Yang Jiahai. The previously quoted professor/doctoral-supervisor/lab-director paragraph did not contain his name. A separate exact `姓名：杨家海 职称：教授` clause from the same already saved official profile, hash837b62249f9ea38e18647d86a2847747ecb6367ac8c599e38df842ecc8760772, now supplies the named2026observation. The original basis proof remains unchanged; the failed check is retained in `listing-source-holds.json`. No historical period was inferred.

## Remaining work

- The saved website reviews support61PIs, leaving146without a reviewed owned-site outcome. Official faculty profiles are source provenance and do not fill a lab-website gap.
- A separate follow-on member batch is being integrated with exact roles, dates, explicit PI ties and identity holds. Its scratch counts are not added to this55-membership native result.
- Historical appointments, official bilingual aliases, university-wide lab discovery, local-dump bibliography identities and institution-attributed2016–2026papers remain incomplete.184career bibliography records for two independently reviewed identities are discovery metadata, not school papers.
- The charter listing slots have no new automatic page parser, history coverage or fresh host probes in this checkpoint. Cached host-policy receipts do not establish a new stage-0 gate pass. Preserve originals and require normal access checks before future fetching.

The parallel Harvard member input and general editorial/edition corrections share this integration branch. Harvard's new original source cache is preserved separately with hash604c7447a7316f5e576e45d95c80923eac1d4d0b58c930768460130983dbdc6e; its flagged paper-attribution review remains held. Neither Harvard nor Tsinghua canonical paper outputs are promoted here.
