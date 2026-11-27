# UCSD onboarding, stage 4 (appointment periods) - submitted, 2026-11-24

Chain submitted by hand (stage_gate has no dependency option): `atlas_pipeline.submit('stage4-ucsd', ..., dependency='afterany:32543240')`, so Wayback fetching starts only
when the stage-3 labpage-discover array ends (one fetching stage at a time, L-28/L-49). Jobs (afterok chain): periods-fetch 32545271, extract 32545272, gaps 32545273,
extend 32545274, truncated 32545275, deep 32545276. Run again for PIs that stage 2 adds (fetch is incremental).

## Recovery, 2026-11-27

The original fetch timed out; extract and its dependent steps were cancelled.
Offline extraction from the saved captures proposed 14 periods. Source review
rejected seven postal-code false years and a biography of another person, and
held two historical open-ended statements pending later departure evidence.

Five independently reviewed periods are now in `reviewed/faculty-periods.json`:
Christensen starts July 2016, confirmed through the 2026-07-17 capture; Shacham's
2007–2018 interval carries the literal announced Fall 2018 move to UT Austin;
Geiger starts in 2020, confirmed 2026-11-25; Cheng starts in 1986 and Ramamoorthi
on 2014-07-01, both confirmed by current official profiles on 2026-11-27.
No unsupported appointment day is inferred from a month or year.

Jensen's full-professor phase is not a total UCSD departure: his later emeritus
listings remain. Zhou's historical start statement is not used to infer a
current open interval; her dated annual listings remain independent evidence.
Neither omitted period removes a PI or a listing.

Original bytes are preserved under UCSD raw `papers60-20261127/`; each accepted
evidence item names its source file and original SHA-256. The exact five-period
input hash is c4339e4523eb2a46af95d51e395f25d7facc63a5bd31df30cdec6d62f6772232.
Independent source receipt: `ucsd-papers60-1127/independent-review/`
`faculty-period-repaired-input-audit-r2.json`, SHA-256
f64a0c6c8ec7208358d69711df413b59430fcd049b5d21652436487cd698e2c8.
This records source approval; later native, paper, identity and download gates
are assessed against their own frozen inputs and outputs.
