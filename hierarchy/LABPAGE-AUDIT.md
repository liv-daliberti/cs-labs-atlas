# Lab-page audit

Generated 2026-10-31T18:39:59+00:00 by `tools/labpage_audit.py`; method and reason codes in `docs/LAB-PAGES.md`.

## Lab pages

| school | labs | found | none found | none found by reason |
|---|---:|---:|---:|---|
| princeton | 140 | 44 | 96 | pi_homepage_only_no_lab_site 81, profile_only_no_homepage 8, site_at_other_institution 2, no_web_presence_found 2, new_arrival_no_site_yet 1, emeritus_or_admin_no_lab 1, pi_left_school_site_moved 1 |
| mit | 277 | 99 | 178 | pi_homepage_only_no_lab_site 144, no_web_presence_found 26, profile_only_no_homepage 2, host_challenge_no_wayback 1, host_blocked_by_robots 1, site_dead_no_wayback 1, new_arrival_no_site_yet 1, emeritus_or_admin_no_lab 1, pi_left_school_site_moved 1 |
| cmu | 458 | 190 | 268 | pi_homepage_only_no_lab_site 218, no_web_presence_found 24, profile_only_no_homepage 13, site_dead_no_wayback 5, host_blocked_by_robots 4, site_at_other_institution 2, pi_left_school_site_moved 2 |
| epfl | 169 | 86 | 83 | pi_homepage_only_no_lab_site 75, no_web_presence_found 5, pi_left_school_site_moved 2, profile_only_no_homepage 1 |
| berkeley | 209 | 53 | 156 | pi_homepage_only_no_lab_site 136, no_web_presence_found 11, emeritus_or_admin_no_lab 6, profile_only_no_homepage 2, pi_left_school_site_moved 1 |

## Students listed on lab pages

`removed by strict rule`: proposals the 2026-10-31 rule (undated names in older labs need an explicit current marker) removed.

| school | listed | current | alumni | in build | missing (reason: n) | genuinely missing | proposed | removed by strict rule |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| princeton | 2631 | 1686 | 945 | 1378 | undated_alumni_cannot_place 267, not_in_people_section 198, undated_cannot_place 159, outside_2016_2026 150, not_a_student 120, reviewer_excluded 115, at_previous_school 42, name_unresolved 42, site_at_other_institution 31, after_pi_left 27 | 102 | 102 | 73 |
| mit | 5851 | 3075 | 2776 | 3420 | undated_alumni_cannot_place 1166, outside_2016_2026 324, not_a_student 195, reviewer_excluded 187, not_in_people_section 129, name_unresolved 126, undated_cannot_place 84, after_pi_left 52, at_previous_school 29, evidence_not_in_build 2 | 137 | 137 | - |
| cmu | 12795 | 8575 | 4220 | 6848 | not_in_people_section 1991, undated_cannot_place 1643, name_unresolved 385, site_at_other_institution 353, not_a_student 317, outside_2016_2026 308, at_previous_school 279, undated_alumni_cannot_place 206, after_pi_left 105, shared_page_no_adviser 66, evidence_not_in_build 6 | 288 | 288 | 23 |
| epfl | 6867 | 5265 | 1602 | 3276 | not_in_people_section 1820, undated_cannot_place 709, name_unresolved 393, outside_2016_2026 142, after_pi_left 128, at_previous_school 125, not_a_student 40, undated_alumni_cannot_place 24, reviewer_excluded 20, site_at_other_institution 7, evidence_not_in_build 1 | 182 | 182 | 68 |
| berkeley | 6610 | 4108 | 2502 | 2778 | not_in_people_section 881, shared_page_no_adviser 659, undated_cannot_place 556, outside_2016_2026 443, name_unresolved 282, at_previous_school 253, not_a_student 114, undated_alumni_cannot_place 106, after_pi_left 43, site_at_other_institution 31, reviewer_excluded 22, evidence_not_in_build 2 | 440 | 440 | 20 |

## Papers listed on lab pages

| school | listed | 2016-2026 | lab papers | missing (reason: n) | genuinely missing | proposed |
|---|---:|---:|---:|---|---:|---:|
| princeton | 7607 | 3184 | 2134 | outside_window 3293, undated_entry 945, unresolved_metadata 355, from_previous_school 253, no_school_affiliation_evidence 120, other_institution_affiliation 100, outside_appointment 72, not_a_paper 32, pi_not_author 28, parse_artifact 10 | 56 | 56 |
| mit | 13392 | 6099 | 4111 | outside_window 6570, unresolved_metadata 690, undated_entry 510, from_previous_school 311, pi_not_author 237, no_school_affiliation_evidence 218, not_a_paper 138, not_yet_resolved 79, outside_appointment 72, other_institution_affiliation 60, parse_artifact 20 | 132 | 132 |
| cmu | 30878 | 16161 | 9505 | outside_window 12922, unresolved_metadata 2648, from_previous_school 1057, undated_entry 1046, other_institution_affiliation 760, pi_not_author 736, no_school_affiliation_evidence 515, outside_appointment 267, not_a_paper 188, parse_artifact 187, not_yet_resolved 28 | 215 | 215 |
| epfl | 10532 | 6759 | 3453 | outside_window 3646, pi_not_author 1360, unresolved_metadata 722, not_a_paper 624, from_previous_school 284, no_school_affiliation_evidence 128, undated_entry 119, other_institution_affiliation 69, outside_appointment 49, parse_artifact 19 | 33 | 33 |
| berkeley | 10352 | 4734 | 2847 | outside_window 5043, unresolved_metadata 739, from_previous_school 486, undated_entry 476, no_school_affiliation_evidence 131, not_a_paper 115, other_institution_affiliation 106, parse_artifact 92, pi_not_author 86, outside_appointment 49, not_yet_resolved 11 | 44 | 44 |

## Hand-check rounds (acceptance bar: docs/LAB-PAGES.md)

| school | round | date | students | membership errors (doubtful = 0.5) | role/year errors | papers | paper errors | result | what changed |
|---|---:|---|---:|---:|---:|---:|---:|---|---|
| princeton | 1 | 2026-10-30 | 22 | 1.0 | 6 | 22 | 0.0 | fail | first audit (before the strict rules) |
| princeton | 2 | 2026-10-30 | 20 | 1.5 | 1 | - | - | fail | strict rules |
| princeton | 3 | 2026-10-31 | 20 | 3 | 1 | - | - | fail | after the role/year, other-institution, older-lab and not-paper rules |
| princeton | 4 | 2026-10-31 | 20 | 1.5 | 0 | 20 | 0.0 | students_fail_papers_pass | strict undated rule (explicit current marker); last round |
| mit | 1 | 2026-10-30 | 20 | 1.0 | 2 | 20 | 1.0 | pass | first MIT audit |
| mit | 2 | 2026-10-31 | 20 | 0.5 | 4 | 20 | 1.5 | fail | rediscovery (other-group, institution-listing, generic-page rules) |
| cmu | 1 | 2026-10-31 | 20 | 11 | 1 | 20 | 2.5 | fail | first CMU audit |
| berkeley | 1 | 2026-10-31 | 20 | 6.5 | 0 | - | - | fail | first Berkeley audit |
