# Harvard canonical rebuild recipe (prepared 2026-11-10, not run)

Why it is not one command on main today: main's Harvard `raw/` and `derived/` are the 2026-11-07 package (38 PIs, 54 accepted homes). Everything newer lives in the private overlay `hierarchy/harvard/tmp/overlay` (private copies, never symlinks into main):

| what | where it is now | needed by |
|---|---|---|
| listing captures 2016-2026 (129 captures, 82 plan rows) | overlay `listings/harvard/raw/captures.sqlite` | `listing_rows.py` -> census |
| school captures incl. periods fetch pages | overlay `hierarchy/harvard/raw/school-captures.sqlite` | periods, census evidence |
| lab-page audit captures (487 in main + Zitnik page + live fetches) | overlay `hierarchy/harvard/raw/labpage-audit-captures.sqlite` | lab-page student evidence (quotes) |
| derived: rows.json, census-faculty, collection, home-departments, dblp-ids, pis, students, lab_papers, student_papers, labpage-audit, link-diagnosis, copies/ledger inputs | overlay `hierarchy/harvard/derived` | the package |
| reviewed inputs | tracked on main (landed) | all |

## Choice A: owner approves promoting the private stores into main (reserved decision, not approved)
1. Check `squeue -u od2961` (one heavy native at a time) and `bin/atlas task land-lock status`.
2. Promote additively, with backups in `scratch/harvard-promotion-<date>/`: copy the overlay's listing store to main `hierarchy/harvard/raw/listings-captures.sqlite` (alias of `listings/harvard/raw/captures.sqlite`), copy `school-captures.sqlite`, merge the overlay labpage captures (INSERT of rows with id above main's maximum; ids 1..487 identical).
3. On main: `bin/atlas run tools/listing_rows.py harvard`; `tools/census_build.py harvard`; `tools/home_departments_school.py harvard`; `tools/dblp_ids_school.py harvard`; `tools/oa_identity_school.py harvard` (it writes the shared census-overrides file for a released school: use the school-local move as in the landed commits); `tools/periods_school.py extract|gaps|extend harvard` only if the stores changed (Wayback: single chain, never submit).
4. `sbatch --test-only` then `sbatch --array=0 --export=ALL,MODE=build,SCHOOL_LIST=harvard hierarchy/build-school.slurm` from a clean main checkout (pi_hierarchy, 3 cpu, 40G, about 5 minutes); then `tools/labpage_audit.py audit harvard` (and restore the reviewed `labpage-additions.json` from git: the audit regenerates it and drops manual rows), `tools/link_diagnosis.py harvard`, `atlas ids`, `atlas copies harvard`, `atlas ledger harvard`.
5. Review: counts against the overlay package (3493 lab-paper rows / 3146 works before the 25 Zitnik/Seigal members; 75 of 79 PIs with papers); `bin/atlas stage-gate harvard 0 .. 10` with exit codes; hash main's derived files before and after; register the package; land through the land-lock.

## Choice B (no promotion): the overlay package as the final package
Run the same builder with an explicit output root, as Tsinghua's isolated native does (`PI_HIERARCHY_OUT=<package dir>`), reading the private overlay for inputs:
```
O=/n/fs/resemble/homogenizing-science/worktrees/harvard-deepdive/hierarchy/harvard/tmp/overlay
CS_ATLAS_CODE=$O PI_HIERARCHY_OUT=/n/fs/resemble/homogenizing-science/scratch/harvard-final-1110/package \
  bin/atlas run tools/pi_hierarchy.py harvard          # about 5 min, nice; check squeue first
CS_ATLAS_CODE=$O bin/atlas run tools/overlay_root.py harvard --out $O --verify     # main derived unchanged
```
then ids, copies and the ledger against that package root (Tsinghua `scratch/tsinghua-native52-1110/run_native.py` is the model; it pins a code commit and frozen input hashes in FROZEN-INPUTS.sha256). The package is then registered like the other isolated natives; main's `raw` and `derived` are never written. Evidence quotes of the Zitnik rows are verifiable only from the overlay's labpage capture store until the capture merge is approved.

Recommendation: B first (no reserved decision needed), A when the owner approves promotion.
