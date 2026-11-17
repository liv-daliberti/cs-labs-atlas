# Reviewed inputs

Small, hand-curated decision files the build and the audits read. They are tracked in git (named one by one in
`.gitignore`), copied into every release at the same paths, and each must stay under 5 MB. Generated files are not
reviewed inputs, even when a reviewed verdict is folded into them.

| File | Read by | What it decides |
|---|---|---|
| `hierarchy/census-overrides.json` | `pi_hierarchy.py`, `chain_audit.py` | per school and person: exclusions (with `why`, `revisit_after`), `is_pi`, aliases, collection person, DBLP/ORCID/OpenAlex ids, `not_openalex`, `mixed_openalex`, reviewed periods, PI basis |
| `hierarchy/home-departments.json` | the site builder, `export_release.py`, `school_profiles.py` | a PI's home department, with evidence and status |
| `hierarchy/zero-paper-review.json` | `zero_paper_ledger.py`, `chain_audit.py` | verdicts for labs with no lab papers |
| `hierarchy/zero-paper-labs.json` | the site builder, `export_release.py`, `organize_tree.py` | the zero-paper ledger (diagnosis + the reviewed verdict; written by `zero_paper_ledger.py`) |
| `hierarchy/chain-reasons.json` | `chain_audit.py` | `explained` / `fix` verdicts for open chain-audit items |
| `hierarchy/student-corrections.json` | `pi_hierarchy.py` | drop, rename or re-source one student record |
| `hierarchy/student-identity-review.json` | `pi_hierarchy.py`, `chain_audit.py` | same-person / different-people verdicts within a lab |
| `hierarchy/student-name-candidates.json` | `tools/student_name_candidates.py` (writer) | queue of one-letter surname typos within a lab, `verdict` empty; a `same_person` verdict goes into `student-identity-review.json` (R-STU-13) |
| `hierarchy/cs-venues.json` | CS-related candidate tools | the computing venue list |
| `hierarchy/<school>/missing-pi-review.json` | `chain_audit.py` | decisions for listed faculty the census lacks |
| `hierarchy/<school>/cs-related-review.json` | `chain_audit.py`, `export_release.py` | decisions for CS-related candidates in other departments |
| `hierarchy/<school>/missed-labs-review.json` | read by no build step (a record, like `missing-pi-review.json`); its accepted people are also in `census-additions.json` / `cs-related-review.json` | the 2026-11-09 missed-computing-labs search: one decision per candidate (accepted, not_faculty, faculty_not_computing, no_appointment_evidence, already_in_census_as, ...), the PI-basis grants on census rows, the Wayback queue and the hand-check (`tools/missed_labs_candidates.py`) |
| `hierarchy/<school>/few-students-evidence.json` | `pi_hierarchy.py`, `chain_audit.py` | researched advisees of thin labs, with quotes and hashes |
| `hierarchy/<school>/relation-evidence.json` | `pi_hierarchy.py` (R-STU-08) | re-captured url, sha256 and quote for collection relations that had none (cmu, epfl, mit; `tools/relation_recapture.py`, bodies in `relation-captures.sqlite`, not tracked) |
| `hierarchy/<school>/gap-evidence.json` | `pi_hierarchy.py`, the site builder | researched gap labs: status, identity, students |
| `hierarchy/stanford/tobagi-review.json` | review record | one Stanford PI's reviewed case |
| `hierarchy/nicknames/{names,extras}.csv` | `pi_hierarchy.py` | given-name pairs (public carltonnorthern/nicknames table, Apache-2.0, plus curated extras) |
| `census/<school>-additions.json` | `pi_hierarchy.py`, `export_release.py` | listed faculty the census missed |
| `periods/<school>-faculty-periods.json` | `pi_hierarchy.py` | reviewed faculty periods |
| `hierarchy/<school>/reviewed/paper-claim-review.json` | `pihier.identity`, `pihier.reviewed_claims`, `pihier.build` | sourced per-PI claim holds/rejections and explicit edition bridges; never forces admission |
| `hierarchy/<school>/reviewed/recovery-source-review.json` | `pihier/recovery_reviews.py`, normal native recovery gates | Exact original recovery/PID/publication/PDF-bound complete publisher metadata projection; no admission override |

## Per-paper claim reviews

Use `atlas_paths.data('paper-claim-review.json', school)` for the working layout. The input is
`{"version": 1, "school": "harvard", "decisions": [...]}`. Each active decision has a unique `id`, exact `pi`,
`match` containing an `oa`, `doi` or collection `work` identifier, `decision`, `why`, `reviewed_by`, ISO
`reviewed_at` date, and original `evidence` items with `url`, `sha256` and a literal `quote`. Supplied identifiers
must agree on one record; a shared title or name is not an identity selector.

- `hold` preserves an unresolved claim as an explicit review outcome. It does not call the underlying work a non-paper.
- `reject` rejects this PI-paper claim with its sourced reason. It does not blacklist a person or author entity.
- `merge` additionally names an `into` identifier selector for an independently eligible edition of the same PI.
  The accepted target keeps its metadata; every eligible source/target edition and byline remains available for links.
  A missing target holds the source. A review never creates or admits an absent target or crosses PI labs.

There is no `accept` action and no completeness waiver. Normal identity, own-school affiliation, appointment and
paper-type checks remain required. Held/rejected raw works cannot lend new dynamic author-ID anchors. The final
review pass also catches recovered rows and runs before student corroboration and links, preventing orphan links.
Ambiguous matches, conflicting actions, merge cycles, malformed evidence or an input changed during a build stop it.

The loaded input hash and every decision, including unmatched ones, are written to `report.json` as
`paperClaimReview`; the input also enters school provenance. An active review file records current decisions;
retain superseded judgments in the audit artifacts and replace the active decision only after new evidence resolves it.
These decisions do not prove corpus completeness or convert candidate member authorships into verified ones.

Not tracked (large or harvested, but in the working root and, where the build reads them, in the sweeps): the census
files (`census/<school>-faculty.json`), the listings (`listings/<school>/listings.json`), the thesis / lab-page evidence
(`hierarchy/<school>/{thesis,labpage}-evidence.json`), and every sqlite sweep.

Not inputs but kept with the releases: `hierarchy/ids/registry.sqlite` (the atlas id registry, docs/IDS.md; generated by
`tools/atlas_ids.py`, never hand-edited, seeded from `releases/latest` when missing).
