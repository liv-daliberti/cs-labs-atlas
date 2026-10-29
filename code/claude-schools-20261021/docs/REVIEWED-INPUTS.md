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
| `hierarchy/cs-venues.json` | CS-related candidate tools | the computing venue list |
| `hierarchy/<school>/missing-pi-review.json` | `chain_audit.py` | decisions for listed faculty the census lacks |
| `hierarchy/<school>/cs-related-review.json` | `chain_audit.py`, `export_release.py` | decisions for CS-related candidates in other departments |
| `hierarchy/<school>/few-students-evidence.json` | `pi_hierarchy.py`, `chain_audit.py` | researched advisees of thin labs, with quotes and hashes |
| `hierarchy/<school>/gap-evidence.json` | `pi_hierarchy.py`, the site builder | researched gap labs: status, identity, students |
| `hierarchy/stanford/tobagi-review.json` | review record | one Stanford PI's reviewed case |
| `hierarchy/nicknames/{names,extras}.csv` | `pi_hierarchy.py` | given-name pairs (public carltonnorthern/nicknames table, Apache-2.0, plus curated extras) |
| `census/<school>-additions.json` | `pi_hierarchy.py`, `export_release.py` | listed faculty the census missed |
| `periods/<school>-faculty-periods.json` | `pi_hierarchy.py` | reviewed faculty periods |

Not tracked (large or harvested, but in the working root and, where the build reads them, in the sweeps): the census
files (`census/<school>-faculty.json`), the listings (`listings/<school>/listings.json`), the thesis / lab-page evidence
(`hierarchy/<school>/{thesis,labpage}-evidence.json`), and every sqlite sweep.
