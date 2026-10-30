# Michigan, stage 3: PIs and labs

Date: 2026-10-29, updated 2026-10-30. Gate: **passed** (no longer provisional; see the update at the end).

## What was done
- **PI basis.** `tools/census_build.py` decides each PI's basis from the listing row itself; the protocol rules are in
  its docstring.
  - 191 are `ladder_faculty`: a professor title in the department, not courtesy, adjunct, visiting, research, teaching,
    lecturer or emeritus. For ECE, the person also needs an accepted CS-related decision.
  - 20 are `courtesy_faculty`: a CSE courtesy or affiliate appointment whose same row gives a professor rank in the home
    unit.
  - The 37 additions (other units) are `ladder_faculty` from their unit listing.
  - Research scientists, lecturers and emeriti without a ladder row in the window are not PIs yet: no
    `pi-basis-evidence.json` has been researched (see below).
- **Labs.** Every PI gets a new own lab ("<PI> group"); no lab unit is reused. Michigan has no site collection with lab
  units, and lab pages are a stage 6/7 input.
- **Home departments.** `tools/home_departments_school.py michigan` produced 248 rows, all `accepted`, in
  `hierarchy/michigan/home-departments.json`. Each row carries the listing row's url, sha256 and quote.

  | home | PIs | | home | PIs |
  |---|---|---|---|---|
  | Computer Science and Engineering | 121 | | Industrial and Operations Engineering | 3 |
  | Electrical and Computer Engineering | 70 | | Aerospace Engineering | 2 |
  | School of Information | 23 | | Computational Medicine and Bioinformatics | 2 |
  | Robotics | 15 | | Nuclear Engineering and Radiological Sciences | 2 |
  | Mathematics | 4 | | Linguistics, Civil and Environmental Engineering, Neurosurgery, Music, Radiology, Mechanical Engineering | 1 each |

  - Unit spellings are normalized through the charter's `[census].home_units`. The listings write "EECS – Computer
    Science and Engineering", "Linquistics" and "Robotics (effective August 26, 2024)".
  - "Professor of X, Medical School" is read as department X.
- **Builder check.** The builder ran with a wired copy: `tools/wire_charters.py` was applied to
  `hierarchy/michigan/tmp/wiretest/`, then `pi_hierarchy.py michigan` was run from there. The builder's own files were
  not edited.
  - Result: 248 PIs, 0 without a person record, 248 new labs. It also found 6 lab papers; the sweep has only one page
    yet.
  - The chain audit's checks, run in-process: `pi` 248/248; `coverage` 607 items with 0 open.

## Gate
- The `pi` check is 100% (248/248). **Pass.**
- Every PI has an accepted home department (`tools/stage_gate.py michigan 3`). **Pass.**

## Exceptions and pending
- **The shared `hierarchy/home-departments.json` was not written yet.**
  - The builder agent is cutting release `2026-10-29.2`, and `make_release.py` refuses uncommitted changes to tracked
    files.
  - After that release, run `tools/home_departments_school.py michigan --write-shared`. It replaces only Michigan rows.
- **Research and teaching faculty.** 50 research scientists and 2 teaching professors in the CSE/ECE lists are not PIs.
  Each needs a stated group or advisees, recorded in `hierarchy/michigan/pi-basis-evidence.json` with url, sha256 and
  quote. Not researched yet.
- **Emeriti.** 14 emeriti are PIs because they held a ladder title inside the window. Their periods (stage 4) must
  close their lab paper range.

## Update, 2026-10-29 21:40 UTC
- **Builder wired.** The builder now reads the charters (`tools/wire_charters.py`, applied by the coordinator in
  `65b50eb`). I ran `tools/pi_hierarchy.py michigan` itself, for Michigan only.
  - Result: 251 PIs, 0 without a person, 233 with a DBLP list from the regenerated `hierarchy/dblp-dump-persons.json.gz`.
  - Chain checks, in-process: `pi` 251/251, `coverage` 0 open.
- **Shared home departments written.** `tools/home_departments_school.py michigan --write-shared` added 251 Michigan
  rows to `hierarchy/home-departments.json`. It keeps the file's own layout (indent 2), and only Michigan rows change.
- **Gate:** passed. It stays **provisional** on the courtesy-PI rule (19 PIs) and on the CS-related acceptances
  (owner decisions pending).

## Update, 2026-10-30: final PI set. Gate passed
- **Owner decision 4 (2026-10-30):** courtesy appointments count as PIs. The 19 `courtesy_faculty` PIs are no longer
  provisional.
- **The stage 2 decisions are final** (computing-share test, OpenAlex candidates, four more units).
  - Census PIs: 213 (194 `ladder_faculty`, 19 `courtesy_faculty`); the ECE acceptances are +4 and −5.
  - Additions: 75 PIs of other units. Total 288.
- **Home departments.** `tools/home_departments_school.py michigan --write-shared`: 288 rows, all accepted. CSE 122,
  ECE 70, School of Information 34, Robotics 25, Mathematics 10, IOE 8, ME 5, Aerospace 4, CMB 2, NERS 2, and 1 each
  for Linguistics, CEE, Neurosurgery, Music, Radiology and BME.
- **Builder** (`tools/pi_hierarchy.py michigan`): 288 PIs, 0 without a person, 288 new labs. Chain checks in-process:
  `pi` 288/288, `coverage` 0 open (752 items).
- **Gate:** `tools/stage_gate.py michigan 3` **passes** (288 PIs, 288 homes).
- **Still not researched:** research and teaching faculty with a group or advisees (`pi-basis-evidence.json`). They are
  not PIs, as for the released schools without such evidence.
