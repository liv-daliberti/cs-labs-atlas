# UCSD onboarding, stage 1 (sources and captures) - 2026-11-24

CSE is the only full-coverage department. Its faculty page has had three templates, each with a format in `tools/listing_formats.py` and a fixture test
(`tests/test_ucsd_cse_cards.py`):

| era | slot (URL) | format | what the page prints |
|---|---|---|---|
| 2016-2017H1 | Jacobs School faculty search results, `www.jacobsschool.ucsd.edu/faculty/faculty_bios/findprofile.sfe?department=cse` (the CSE page then only framed it) | `ucsd_jacobs_findprofile` | name and one title line per appointment ("Professor , CSE", "Faculty-Affiliate , Calit2") |
| 2017H2-2019 | `cse.ucsd.edu/people/faculty-profiles` | `ucsd_cse_info_cols` | name and printed title; contact lines never kept |
| 2020-2026 | `cse.ucsd.edu/people/faculty-profiles` | `ucsd_cse_cards` | section heading only (Faculty/Full, Continuing Lecturer, Lecturer, Researcher, Adjunct, Affiliated, Emeritus); the heading is the title and the quote is name + heading |

Choices: the heading is only a category, not a per-person rank, so `[census].rank_words` maps "Full"/"Faculty" to ladder and "Affiliated" to courtesy; this is the
page's own classification, not an inferred rank. "Alumni" and "Faculty Alumni" sections (people who left) and "Department Leadership" (repeats Faculty) are
skipped. The old Jacobs rows print "Faculty , CSE" (5 people) with no rank word: they stay `other` and go to stage 2 as ranked-unknown rather than ladder.
The CSE sub-pages (adjunct, affiliated, emeritus) repeat the main page's sections from 2020 on and have no sections before, so they are not slots.
`cseweb.ucsd.edu` (legacy host) has no 200 captures at the listing URLs searched (people/faculty.html, faculty/).

Captures: job 32539946 (run_school.sh, one round, 59 min Wayback pacing); 20 capture rows over 2016H1-2026H1, `ucsd unplanned slot-halves: 0`. 2019H1 has no Wayback
capture for the URL; 2019 is covered by its H2 capture.

Output: 2,785 rows, 248 people (CSE), `listings/ucsd/derived/rows.json`. Ranks in 2026H1: ladder 78, lecturer 11, research 1, adjunct 8, courtesy 45, emeritus 19.
Gate: `atlas stage-gate ucsd 1`: pass, `roster_years_open` 0.

Open item for stage 2: the other computing units (ECE, HDSI/SCIDS, Cognitive Science, Mathematics, MAE, Bioengineering, SDSC, Qualcomm Institute, ...) are discovery
sources only; their listings are captured by the stage-2 `units` step.
