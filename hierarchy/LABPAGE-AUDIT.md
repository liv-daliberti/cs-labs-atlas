# Lab-page audit

Generated 2026-10-31T16:02:43+00:00 by `tools/labpage_audit.py`; method and reason codes in `docs/LAB-PAGES.md`.

## Lab pages

| school | labs | found | none found | none found by reason |
|---|---:|---:|---:|---|
| princeton | 140 | 44 | 96 | pi_homepage_only_no_lab_site 81, profile_only_no_homepage 8, site_at_other_institution 2, no_web_presence_found 2, new_arrival_no_site_yet 1, emeritus_or_admin_no_lab 1, pi_left_school_site_moved 1 |
| mit | 277 | 99 | 178 | pi_homepage_only_no_lab_site 144, no_web_presence_found 26, profile_only_no_homepage 2, host_challenge_no_wayback 1, host_blocked_by_robots 1, site_dead_no_wayback 1, new_arrival_no_site_yet 1, emeritus_or_admin_no_lab 1, pi_left_school_site_moved 1 |
| cmu | 458 | 190 | 268 | pi_homepage_only_no_lab_site 218, no_web_presence_found 24, profile_only_no_homepage 13, site_dead_no_wayback 5, host_blocked_by_robots 4, site_at_other_institution 2, pi_left_school_site_moved 2 |
| berkeley | 209 | 53 | 156 | pi_homepage_only_no_lab_site 136, no_web_presence_found 11, emeritus_or_admin_no_lab 6, profile_only_no_homepage 2, pi_left_school_site_moved 1 |

## Students listed on lab pages

| school | listed | current | alumni | in build | missing (reason: n) | genuinely missing | proposed |
|---|---:|---:|---:|---:|---|---:|---:|
| princeton | 2631 | 1686 | 945 | 1378 | undated_alumni_cannot_place 267, not_in_people_section 198, outside_2016_2026 155, not_a_student 120, reviewer_excluded 115, undated_cannot_place 86, name_unresolved 42, at_previous_school 38, site_at_other_institution 29, after_pi_left 27 | 176 | 176 |
| mit | 5851 | 3075 | 2776 | 3420 | undated_alumni_cannot_place 1166, outside_2016_2026 324, not_a_student 195, reviewer_excluded 187, not_in_people_section 129, name_unresolved 126, undated_cannot_place 84, after_pi_left 52, at_previous_school 29, evidence_not_in_build 2 | 137 | 137 |
| cmu | 13170 | 8762 | 4408 | 6864 | not_in_people_section 2132, undated_cannot_place 1918, name_unresolved 497, not_a_student 348, outside_2016_2026 319, at_previous_school 287, undated_alumni_cannot_place 196, after_pi_left 122, shared_page_no_adviser 66, evidence_not_in_build 6 | 415 | 415 |
| berkeley | 6647 | 4109 | 2538 | 2778 | not_in_people_section 890, shared_page_no_adviser 659, undated_cannot_place 547, outside_2016_2026 448, name_unresolved 292, at_previous_school 286, not_a_student 116, undated_alumni_cannot_place 105, after_pi_left 43, reviewer_excluded 22, evidence_not_in_build 2 | 459 | 459 |

## Papers listed on lab pages

| school | listed | 2016-2026 | lab papers | missing (reason: n) | genuinely missing | proposed |
|---|---:|---:|---:|---|---:|---:|
| princeton | 7607 | 3184 | 2134 | outside_window 3293, undated_entry 945, unresolved_metadata 355, from_previous_school 253, no_school_affiliation_evidence 120, other_institution_affiliation 100, outside_appointment 72, not_a_paper 32, pi_not_author 28, parse_artifact 10 | 56 | 56 |
| mit | 13392 | 6099 | 4111 | outside_window 6570, unresolved_metadata 690, undated_entry 510, from_previous_school 311, pi_not_author 237, no_school_affiliation_evidence 218, not_a_paper 138, not_yet_resolved 79, outside_appointment 72, other_institution_affiliation 60, parse_artifact 20 | 132 | 132 |
| cmu | 30878 | 16161 | 9505 | outside_window 12922, unresolved_metadata 2648, from_previous_school 1057, undated_entry 1046, other_institution_affiliation 760, pi_not_author 736, no_school_affiliation_evidence 515, outside_appointment 267, parse_artifact 187, not_a_paper 181, not_yet_resolved 28 | 222 | 222 |
| berkeley | 10334 | 4717 | 2838 | outside_window 5044, unresolved_metadata 741, from_previous_school 486, undated_entry 474, no_school_affiliation_evidence 131, not_a_paper 114, other_institution_affiliation 106, parse_artifact 92, pi_not_author 86, outside_appointment 49, not_yet_resolved 1 | 45 | 45 |

## Hand-check rounds (acceptance bar: docs/LAB-PAGES.md)

| school | round | date | students | membership errors (doubtful = 0.5) | role/year errors | papers | paper errors | result | what changed |
|---|---:|---|---:|---:|---:|---:|---:|---|---|
| princeton | 1 | 2026-10-30 | 22 | 1.0 | 6 | 22 | 0.0 | fail | first audit (before the strict rules) |
| princeton | 2 | 2026-10-30 | 20 | 1.5 | 1 | - | - | fail | strict rules |
| princeton | 3 | 2026-10-31 | 20 | 3 | 1 | - | - | fail | after the role/year, other-institution, older-lab and not-paper rules |
| mit | 1 | 2026-10-30 | 20 | 1.0 | 2 | 20 | 1.0 | pass | first MIT audit |
| mit | 2 | 2026-10-31 | 20 | 0.5 | 4 | 20 | 1.5 | fail | rediscovery (other-group, institution-listing, generic-page rules) |
| cmu | 1 | 2026-10-31 | 20 | 11 | 1 | 20 | 2.5 | fail | first CMU audit |
| berkeley | 1 | 2026-10-31 | 20 | 6.5 | 0 | - | - | fail | first Berkeley audit |
