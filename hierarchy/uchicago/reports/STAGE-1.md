# University of Chicago, stage 1: sources and captures

Date: 2026-11-02. Gate (`atlas stage-gate uchicago 1`): **pass** (every department has an ok listing capture in every year 2016-2026), with the exceptions below.

## URL eras (exact-URL CDX, `tools/discover_listings.py`)
| dept | era | URL | format |
|---|---|---|---|
| CS | 2016-2018 | `www.cs.uchicago.edu/directories/table/faculty` (Drupal table; found from the links of the 2016 people page) | uc_cs_table |
| CS | 2018-11 - 2022-02 | `www.cs.uchicago.edu/people/faculty/` | uc_people_li |
| CS | 2022-02 - | `cs.uchicago.edu/people/uchicago-faculty/full-time-faculty/` (also emeritus-faculty) | uc_card |
| CS | 2016-2025 | `.../directories/table/Other-Academic-Appointments` (lecturers, associate members; 2019+ captures are shells) | uc_cs_table |
| TTIC | 2016-2017-01 / 2017-01 - | `www.ttic.edu/faculty.php` / `www.ttic.edu/faculty/` | ttic_table / ttic_media |
| STAT | 2016-2019 / 2019-09 - | `galton.uchicago.edu/people/faculty.shtml` (+ emeriti.shtml) / `stat.uchicago.edu/people/` (all groups; faculty classes kept) | galton_cells / uc_people_li |

## Counts (`listings/uchicago/derived/rows.json`, 3,083 rows)
People per year (distinct names): CS 43 (2016), 5 (2017, partial), 53 ... 78 (2026); TTIC 34 ... 46; STAT 46 ... 49.
Distinct people: CS 112, TTIC 110, STAT 82. Rank mix 2025: CS 123 ladder rows, 14 teaching, 14 emeritus; TTIC 46 ladder, 24 research, 26 other; STAT 81 ladder.

## Exceptions
- **CS 2017: partial.** The only capture (2017-08-29) is page 1 of a paged directory (5 of about 45 people); pages 2+ are archived only from 2019. 2017 H1 and 2018 H1 have no capture. Stage 4 must bridge 2017 for the CS PIs with other evidence.
- CS 2017 H1, 2018 H1: `nocapture`. CS emeritus before 2022 and STAT emeritus after 2019: `nocapture` / `unusable` (lists under 5 people; emeriti also appear on the main lists). CS other appointments 2017-2018 `nocapture`, 2019+ `unusable` (0 entries: shells). STAT 2020 H1, TTIC 2019 H2: `nocapture`.
- 2026 H2: nocapture-equivalent (half-year in progress; captures run to 2026-10).
- Live probes: all live hosts served real pages, none challenged.

## TTIC and the CS department (evidence for owner decision D2)
20 people are listed by both the CS department and TTIC (e.g. Julia Chuzhoy, Nathan Srebro, Madhur Tulsiani, Yury Makarychev, Michael Maire, Matthew Walter,
Karen Livescu, Kevin Gimpel, David McAllester, Risi Kondor, Rebecca Willett, Chenhao Tan, Haifeng Xu): joint appointments and moves between the two. Four
(Willett, Kondor, Lafferty/Koehler via Statistics) also appear in Statistics. TTIC alone has 110 listed people over the window, almost all computing.
