# Georgia Institute of Technology, stage 4: appointment periods

Date: 2026-11-03/04. Jobs 32096413 (fetch of 456 PIs' homepages and Wayback captures), 32096414 extract, 32096415 gaps (61 PIs with span gaps), 32096416 extend; all COMPLETED. `periods_school.py truncated` run locally afterwards.
Gate (`atlas stage-gate gatech 4`): **fail, 28 PIs open** (stop point; no gate waiver recorded, that is the owner's call). 36 PIs have a period, 392 have contiguous listings.

## The 28 open PIs
The 28: Polo Chau, Elliot Moore II, Charles C. Kemp, David W. Rosen, John E. Taylor, Julie Linsey, Kinsey Herrin, Nader Sadegh, Nassim Parvin, Roger Jianxin Jiao, Wei Wang, Wei-Chun Wang, William T. Trotter, Yan Wang, Yu (Jeffrey) Hu, Kok-Meng Lee, Molei Tao, Sung Ha Kang, Frank L. Hammond, Anirban Mazumdar, Ilija Uzelac, William Singhose, Sudheer Chava, Young Mi Choi, Shreyas Kousik, Jon Sanford, Alexander Oettl, Roger Ball.
Every one is a PI of a unit (ME, ISyE, CEE, Design, Math, ...) whose directory is a script shell or paged in alternating years in Wayback, so the listing years have holes (examples: Polo Chau 2016-20, 2022; Charles Kemp 2016-23, 2024, 2026 with 2025 missing;
David Rosen, Nader Sadegh, Roger Jiao and Julie Linsey 2016-22, 2024, 2026 with 2023 and 2025 missing; William Trotter 2017, 2019-20). `gaps` and `extend` looked for dated profile or homepage captures of the missing years and found none naming a ladder title.
Options for the owner: (a) accept each as `unit_directory_gap` in `gate-exceptions.json` with the list above and the profile URLs tried (`gap-year-evidence.json`), keeping the PI (the appointment is continuous by neighbouring dated listings but the rule forbids inferring); or (b) supply archived profile URLs per person.

## Truncated-title PIs (the 8 of stage 2), new tool `periods_school.py truncated`
For the years a department card cut the title short, dated profile captures of exactly those years must name the person with a ladder title. Result: 8 people with truncated rows examined here (38 in stage 2; 30 are covered by an adjacent ladder year);
**3 closed** (Srinivas Aluru, Mustaque Ahamad, Melody Jackson: reviewed periods in `census-overrides-school.json`), **5 stay open**: C. David Sherrill (2024-26), Zvi Galil (2024, 2026), Mark Borodovsky (2024) are PIs without a dated profile capture of those years;
David Joyner and Peter Swire are not PIs (research / other rank in the census) and no profile capture of 2023-26 names either with a professor title: they stay out of the census. Evidence: `hierarchy/gatech/truncated-title-evidence.json`.

The tool only examines people whose rows of a year are ALL unranked cut-off cards; Santosh Vempala, Dana Randall (their rows that year also carry an adjunct rank) and Carrie Bruce (research rank) are not covered and still need a hand look.

## Home departments (R8) and the ML Center question
- Homes are no longer read from title text: `Joint with ...` is the OTHER unit of a joint appointment (-> `also`), `Starting Fall'26`, `KUKA Chair of ...` and anything cut off with an ellipsis are not units; the home is then the department of the listing row. `College of Architecture` is a charter home name. The gate now rejects a home that is not a charter department, affiliated unit or `[census].home_units` name (test): the 16 bad homes are gone (456 homes, stage-3 gate passes).
- **ML Center is a home for 21 PIs (owner question, nothing changed).** Each person's academic school, from the other unit pages (latest dated quote):
  AE (Aerospace): Dimitri Mavris, Evangelos Theodorou, Yongxin Chen, Karen Feigh (2026-11-03 live listing). BME: May D. Wang, Gari D. Clifford (2025-01-17). Physics/Biological Sciences: Daniel Goldman (Physics 2024-06-27, Biological Sciences 2025-02-21);
  Biological Sciences: Jeffrey Skolnick (2026-11-03), Hannah Choi (2025-02-21). Math: Molei Tao, Sung Ha Kang (2017-02-17 listing; Math pages after 2018 are shells). ChBE: Fani Boukouvala, Joseph K. Scott (2026-11-03). Music: Alexander Lerch (2026-11-03).
  No other unit page found (only the ML Center listing): Wei Zhu (Math), Sudheer Chava and Alexander Oettl (Scheller, listed as 'Chava, Sudheer Scheller College of Business'), Wenjing Liao (Math), Reza Sameni (ECE/BME), Anna A. Ivanova (Psychology), Samuel Shapero (**suspect**: the ML listing reads 'Samuel Shapero Research Engineer', GTRI research engineer; the accepted quote runs into the next person's title).
  Recommendation: make the home the academic school where one is evidenced, `ML Center` only as `also`; hold the six without a school evidence and remove Samuel Shapero from the census additions (a research engineer is not a PI).

## Friction and next
Next: stage 5 (identity) after the owner decides the 28 open PIs. See PROTOCOL-FRICTION.md rows 24-26.

## Owner decisions of 2026-11-04 (recorded in docs/DECISIONS.md) and their result
- **Second look at the 28 PIs** (`periods_school.py deep`, Slurm 32098735, 1 h 37 min; `deep-gap-evidence.json`): for each gap year, whole-window CDX of the PI's homepages (listing, DBLP), profile-URL variants (`/people/<slug>`, `/directory/<slug>`, `/directory/person/<slug>`, `/person/`, `/users/`, `/faculty/`, `/profile/`, `/people/faculty/`) on the hosts of the PI's home unit and www.cc.gatech.edu, the charter profile patterns and
  `reviewed/person-urls.json` (person-supplied URLs; none supplied yet). **4 PIs closed with dated quotes** (Wei Wang, Molei Tao, Sung Ha Kang, Young Mi Choi: reviewed periods in `census-overrides-school.json`); Jon Sanford (2017-19) and Roger Ball (2017-19) have partial proof; **24 PIs carry reviewed `unproven_years` with `why_unproven`** (R-PAP-28 bridges their papers at build time).
  Annual reports and news items were not searched by URL guess; no source of dated appointment text outside the unit and personal pages turned up. Google Scholar and LinkedIn were not used.
- **ML Center is not a home** (`[census].center_units = ["ML"]`): 14 people now have the evidenced academic school as home and the ML Center as `also` (Mavris, Theodorou, Y. Chen, Feigh: Aerospace; M. Wang, Clifford: BME; Goldman, Skolnick, H. Choi: Biological Sciences (Goldman also Physics); Tao, Kang, Zhu, Liao: Mathematics; Chava, Oettl: Scheller (Oettl from the 2017 ML listing that names Scheller); Boukouvala, Scott: ChBE; Lerch: Music; Ivanova: Psychology).
  Zhu, Liao, Chava and Ivanova are evidenced by their own live profile pages (2026-11-04, `cs-related-hand.json`). Samuel Shapero is removed (`[cs_related].not_faculty`). **Reza Sameni is held** (no academic school evidenced: his profile page names no GT unit); he is out of the PI set until the owner supplies one.
- **Gate:** `atlas stage-gate gatech 3`: pass (454 PIs, 454 homes); `atlas stage-gate gatech 4`: **pass** (40 periods, 390 contiguous listings, 24 reviewed unproven gaps).
