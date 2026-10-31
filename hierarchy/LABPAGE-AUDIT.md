# Lab-page audit

Generated 2026-10-31T05:43:13+00:00 by `tools/labpage_audit.py`; method and reason codes in `docs/LAB-PAGES.md`.

## Lab pages

| school | labs | found | none found | none found by reason |
|---|---:|---:|---:|---|
| princeton | 140 | 46 | 94 | pi_homepage_only_no_lab_site 79, profile_only_no_homepage 8, site_at_other_institution 2, no_web_presence_found 2, new_arrival_no_site_yet 1, emeritus_or_admin_no_lab 1, pi_left_school_site_moved 1 |
| mit | 277 | 99 | 178 | pi_homepage_only_no_lab_site 144, no_web_presence_found 26, profile_only_no_homepage 2, host_challenge_no_wayback 1, host_blocked_by_robots 1, site_dead_no_wayback 1, new_arrival_no_site_yet 1, emeritus_or_admin_no_lab 1, pi_left_school_site_moved 1 |
| cmu | 458 | 190 | 268 | pi_homepage_only_no_lab_site 218, no_web_presence_found 24, profile_only_no_homepage 13, site_dead_no_wayback 5, host_blocked_by_robots 4, site_at_other_institution 2, pi_left_school_site_moved 2 |
| berkeley | 209 | 53 | 156 | pi_homepage_only_no_lab_site 136, no_web_presence_found 11, emeritus_or_admin_no_lab 6, profile_only_no_homepage 2, pi_left_school_site_moved 1 |

## Students listed on lab pages

| school | listed | current | alumni | in build | missing (reason: n) | genuinely missing | proposed |
|---|---:|---:|---:|---:|---|---:|---:|
| princeton | 2684 | 1705 | 979 | 1408 | undated_alumni_cannot_place 402, not_in_people_section 205, outside_2016_2026 139, not_a_student 120, reviewer_excluded 115, undated_cannot_place 57, name_unresolved 47, at_previous_school 27, after_pi_left 27 | 137 | 137 |
| mit | 5851 | 3075 | 2776 | 3420 | undated_alumni_cannot_place 1166, outside_2016_2026 324, not_a_student 195, reviewer_excluded 187, not_in_people_section 129, name_unresolved 126, undated_cannot_place 84, after_pi_left 52, at_previous_school 29, evidence_not_in_build 2 | 137 | 137 |
| cmu | 13170 | 8762 | 4408 | 6864 | not_in_people_section 2155, undated_cannot_place 2071, name_unresolved 520, not_a_student 349, outside_2016_2026 321, undated_alumni_cannot_place 274, at_previous_school 145, evidence_not_in_build 6 | 465 | 465 |
| berkeley | 6647 | 4109 | 2538 | 2778 | not_in_people_section 890, shared_page_no_adviser 659, undated_cannot_place 480, outside_2016_2026 454, name_unresolved 292, at_previous_school 274, undated_alumni_cannot_place 136, not_a_student 116, after_pi_left 43, reviewer_excluded 22, evidence_not_in_build 2 | 501 | 501 |

## Papers listed on lab pages

| school | listed | 2016-2026 | lab papers | missing (reason: n) | genuinely missing | proposed |
|---|---:|---:|---:|---|---:|---:|
| princeton | 7754 | 3316 | 2251 | outside_window 3299, undated_entry 946, unresolved_metadata 384, from_previous_school 252, no_school_affiliation_evidence 127, other_institution_affiliation 98, outside_appointment 72, not_a_paper 30, pi_not_author 15, parse_artifact 10 | 59 | 59 |
| mit | 13392 | 6099 | 4111 | outside_window 6570, unresolved_metadata 690, undated_entry 510, from_previous_school 311, pi_not_author 237, no_school_affiliation_evidence 218, not_a_paper 138, not_yet_resolved 79, outside_appointment 72, other_institution_affiliation 60, parse_artifact 20 | 132 | 132 |
| cmu | 30878 | 16161 | 9489 | outside_window 12867, not_yet_resolved 6304, undated_entry 1046, parse_artifact 187, not_a_paper 181 | 0 | 0 |
| berkeley | 10334 | 4717 | 2838 | outside_window 5044, unresolved_metadata 741, from_previous_school 486, undated_entry 474, no_school_affiliation_evidence 131, not_a_paper 114, other_institution_affiliation 106, parse_artifact 92, pi_not_author 86, outside_appointment 49, not_yet_resolved 1 | 45 | 45 |

## Hand-check rounds (acceptance bar: docs/LAB-PAGES.md)

| school | round | date | students | membership errors (doubtful = 0.5) | role/year errors | papers | paper errors | result | what changed |
|---|---:|---|---:|---:|---:|---:|---:|---|---|
| princeton | 1 | 2026-10-30 | 22 | 1.0 | 6 | 22 | 0.0 | fail | first audit (before the strict rules) |
| princeton | 2 | 2026-10-30 | 20 | 1.5 | 1 | - | - | fail | strict rules |
| mit | 1 | 2026-10-30 | 20 | 1.0 | 2 | 20 | 1.0 | pass | first MIT audit |
| mit | 2 | 2026-10-31 | 20 | 0.5 | 4 | 20 | 1.5 | fail | rediscovery (other-group, institution-listing, generic-page rules) |
| berkeley | 1 | 2026-10-31 | 20 | 6.5 | 0 | - | - | fail | first Berkeley audit |
