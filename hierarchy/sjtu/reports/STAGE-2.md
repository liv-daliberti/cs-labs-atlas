# SJTU stage 2, 2026-11-24

Result: pass; 0 open findings. Candidate: `/n/fs/resemble/homogenizing-science/scratch/sjtu-stage9-1124/overlay`.

Reviewed the entire 320-row held-decision population against saved source captures before testing. Found recurring short-field/first-rank errors: explicit computing methods were missed, and earlier postdoc/research ranks outranked current professor or doctoral-supervisor statements. Corrected 16 source-supported PI admissions (445 → 461) and one rank-contaminated parsed name (陈凯高级 → 陈凯, still not a PI). Original decisions and SHA-256-bound source receipts are preserved in `STAGE2-WHOLE-SOURCE-REPAIRS-20261124.json`. No new bibliographic ID, student relationship, or prior appointment year was inferred.

The school intentionally uses reviewed census additions plus an empty base census. A generic census-refresh attempt stopped before any output on 56 historical same-name/profile-migration groups; those unresolved identities remain separate. The existing source-reviewed additions path is retained, rather than replacing it with name-only historical merges. The stage-2 gate has zero generated candidates; the 562 manually reviewed decisions are reported separately. This is not a claim of university-wide census completeness.

Gate receipt: `/n/fs/resemble/homogenizing-science/scratch/sjtu-stage9-1124/overlay/hierarchy/sjtu/reports/stage-2-gate.json` (SHA-256 `53f66b707b61413b2b0209c5dc58c9ac6d4a96e4032a5950cd29d1a2b0ce83c1`).

Validation: full project test suite, lint and all 33 charters passed in Slurm job `32539477` (`COMPLETED`, `0:0`, 5m47s). The current profile-card charter also passes the charter check. Code was unchanged; candidate reviewed files were read from the private overlay. No push or main integration has occurred.
