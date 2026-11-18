# Per-PI admission, audits and the blocker inventory (process v4, V4c, 2026-11-17)

Owner decisions 1 and 2 of `PROCESS-V4-PROPOSAL.md` section 6, plus the 11-17 emphasis: per PI, not per school, wherever possible. One PI's open item never holds another PI.

## State table: `tools/pi_states.py` (`atlas stage-gate <school> admission [--record]`, shown by `atlas doctor`)
- Per PI, for the census and stages 3-7: `done` | `excluded_with_reason` (reviewed no_identity/no_papers, a researched reason in the coverage ledger, a gate exception naming the item, a build exclusion) | `open` with the blocking reasons. Written to `hierarchy/<school>/reports/pi-states.json` by `--record` / `stage_gate --run`.
- The evidence bar per PI is unchanged: the table only ATTRIBUTES the existing gate findings (`stage_gate.GATES`, `pi_coverage.ledger`, `chain_audit` per-PI items) to the person they name. A finding that names no person (an acceptance, recall R1/U/R2, a stale register) is a **school item**: reported, never holds a PI, still holds the release.
- Share bars (coverage ratchet, recall Z) stay owner rules: their per-PI gaps are listed `open` but `ratchet`-tolerated: they hold nobody's downloads and are not counted as open for release while the ratchet passes.
- `downloadable` = census clean + window settled + identity anchor, PI not excluded from the build. `downloads_ready.py` reads it (gates 1 and 2 no longer hold the school; gate 0, the sweep check and a fresh build do).
- Stages 3-7 never stop a `--run` chain, and `school_closeout` stages 3-8 wait only for stage 1. `stage_gate` gate 10 (release, still school-wide) needs every PI done or excluded and no open school item of stages 2-7 (judged for onboarding schools; a released school's state is only reported).

## Audits and the one reviewer template: `tools/stage_audit.py` (`atlas stage-audit`)
Classes: `excluded` (stage 2, `excluded_audit.py` kept), `homes`, `websites` (3), `identity` (5), `students` (6). `draw` (seeded, 50 rows, repeat = same file), `review-page` (the template: the draw's rows with their recorded evidence, the rule, the verdict skeleton), `record` (verdict rows carry reviewed_by, seed, sample_hash; the reviewer is not the worker). A draw is invalidated only when its inputs change (a row added/removed/changed; a recorded failure may change or leave: that is its fix). A missing/unreviewed/stale audit is a school item (holds the release); an unfixed failed row holds that PI. Store-sourced schools keep the audit in the evidence store (`audit_run` table), others in `reviewed/audit-<class>.json`. Enforced for onboarding schools; a released school's state is reported (`stage_audit.py show`), not enforced retroactively. Fail rule: a row fails if a source proves it wrong; at most 2 of 50 failures, fixed, else rework and redraw.

## Inventory of school-wide blockers (convert now / keep and why)
| Where | Blocker | Decision |
|---|---|---|
| `stage_gate` g0 | charter, hosts, OpenAlex snapshot | KEEP: no person; a technical prerequisite of every PI |
| g1 | a department with no roster source | KEEP (unit, not PI); no longer holds downloads |
| g2 | undecided candidates, collisions | ALREADY per person; per-PI attribution in `pi_states`; the excluded-class audit and sweep check stay school items |
| g3 | PI basis, home, website register | CONVERTED (per PI); register-level mismatches are school items |
| g4, g5 | window, identity, yield | CONVERTED (per PI) |
| g5/g6 coverage ratchet, recall Z | share of PIs with a gap | KEEP the bar (owner ratchet); per-PI gaps listed |
| g6 | acceptance, recall R1/U/R2/X | KEEP school-wide: sample statistics over the school's labs. QUEUED: per-PI recall verdicts |
| g6/g7 | chain-audit students/one_person/papers/links | CONVERTED (per-PI items) |
| g7 | papers acceptance | KEEP (sample statistic) |
| g8 | copies measured, ledger file exists | QUEUED: per paper of a done PI (ledger reason per paper); the 85% target is already report-only |
| g9 | accuracy sample on the built package | KEEP: a statistic of the package; release evidence |
| g10 | release | KEEP school-wide (owner); see the question below |
| `stage_gate --run` | a failing stage 3-7 gate stops the chain | CONVERTED |
| `school_closeout` stage board | 3-8 wait for the previous stage | CONVERTED (need stage 1 only); 9 and 10 unchanged; `source_preflight` (gates 0, 1) KEEP |
| `onboarding_doctor` | first failing stage | CONVERTED (3-7 shown as per-PI counts) |
| `downloads_ready` | gates 0-2 | CONVERTED (gate 0 + sweep + build freshness remain: one build artifact, one bulk pull) |
| `add_works`, `loop_starter` | readiness | `--early` per PI; loop cache/disk-guard/lock KEEP (technical) |
| `atlas_release` anchors preflight | a PI with 0 papers and no reason fails the release | KEEP (release) |
| `status_table` | gates 0-10 columns | QUEUED: add the per-PI counts |
| `accuracy/sample.py`, student-recall draw | seeded school sample | KEEP: a per-PI sample has no statistical meaning |
| `labpage_audit` discovery step | whole-school job | V4a (sharded, resumable per PI) |
| Student rounds (lab-page acceptance) | school-wide precision rounds | KEEP; an open PI's lab does not hold other labs' rounds |

## Per-PI release (D-0001, owner 2026-11-17; `tools/pi_release.py`, `make_release.py --per-pi`)
Replaces the school-wide gate 10 and the question that stood here. Publish the done PIs, hold the open ones.
1. **Package filter.** included = package PIs that are not hard-open in `pi_states` (ratchet-only gaps do not hold) plus **carried** PIs (published earlier, open now: never removed). Held PIs are listed with their reasons in `RELEASE-SCOPE.md` and `release-scope.json`. `pis.json`, `students.json`, both paper files and `copies.json` (papers) are filtered by `pi`; the same bytes for the same input.
2. **Accuracy on the subset.** `sample.py --round pi1` (seed 20261118, r3 sizes) draws only from the included PIs and records their list and the filtered-file hashes; g9 binds to those, and fails if the included set or its content changed (a PI added later needs a redraw). Draws without `only_pis` are byte-identical to before (checked on gatech r3).
3. **Site field.** `hierarchy/<school>/release-scope.json` and `release-scope.json` (also `MANIFEST.json` -> `scope`): `status` complete|partial, `pis_total`, `pis_included`, `pis_held`, `pis_carried_open`, the held list. The site code is not changed here.
4. **Monotone.** `pi_release.py compare` / the `make_release` preflight compare the filtered package with the last release by atlas ids (PI, lab, lab-student, lab-paper, student-paper), by pre-id keys when the working package has no ids yet, and refuse on any removal (`--allow-removals` records it).
5. **Gate 10.** An onboarding school needs >= 1 included PI and g9 passing on its subset. Held PIs and school items (acceptances, recall) are reported in the scope, not blocking. A released school keeps its status.
**Not yet per PI (reported, not hidden).** A partial release still ships school-wide derived files that name held PIs (`report.json`, the unavailability ledger, `link-diagnosis.json`, `reader/`, `home-departments.json`, `school-profiles.json`, the audits). `make_release --per-pi` therefore refuses a real run with a partial school unless `--allow-derived-unfiltered` (recorded in `scope`). Filtering those and the reader export is the next step. Counts of a partial school in `MANIFEST.json` are recomputed for the included PIs (other count keys null). School-level samples (acceptance, recall) still describe the whole school.
