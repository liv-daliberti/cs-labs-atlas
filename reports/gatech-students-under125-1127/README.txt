Georgia Tech: under 125 zero-student labs without increasing one-student labs.

User baseline: 152 zero-student / 60 one-student labs in the live native package. The prior 15D source batch is validated but deliberately not applied separately, since it would produce 137 zero / 72 one.

This batch adds 131 distinct PI-student relationships / 132 degree-role episodes across 25 labs. Thirteen additional previously empty labs each have at least two independently source-backed students. Eight existing one-student labs and four pending 15D singletons receive additional students. Combined projection: 124 zero / 60 one / 1817 student memberships. These are projections until the complete native rebuild, validation, CAS application and export finish.

Evidence is original first-party HTML/PDF capture bytes, including the university doctoral-dissertation register, typed owned lab rosters, dated alumni records, named co-adviser CV entries, and student-owned biographies. Raw hashes and literal quotes are checked. Current rosters are dated only by observation; historical graduation or advising dates are explicit. Unspecified graduate degrees stay generic student. Foreign-degree students and undated alumni are held, and coauthorship never proves advising.

The mathematics register has separate doctoral and master tables. Only the doctoral table is used here. Literal surname-first source names are retained in input; the validator uses the pre-existing native clean_person_name to compare their generated display names. Original author strings and adviser-initial resolution are retained in roster-review.json. Existing Anna Kirkpatrick, Kevin Shu and Yuchen He are not recounted. Ambiguous surname-only adviser entries, Blekherman D. and the Yiao/Yao typo are held.

One person (Chase Sun) has a source-stated current PhD role and a separately dated 2026 MS completion; these are two role observations, not two students. Zackory Erickson's 2021 GT PhD is historical, separately dated by his own CV. The Sasha/Alexandra identity is corroborated by the faculty-owned roster and leaves the census identity untouched.

Raw captures and work receipts are retained in school work/students-under125-1127 (KEEP). Reproduce with PYTHONPATH=tools python reports/gatech-students-under125-1127/prepare_batch.py, then validate all six recovery reports with reports/gatech-students10-1126/validate_batch.py.
