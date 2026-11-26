# ETH Zurich onboarding, stage 1 - 2026-11-24

Gate `atlas stage-gate ethz 1`: pass (0 open). Wayback is the owner's slow lane (one request per 15 s across all sessions), so the captures took about 4 hours.

Departments (coverage full): D-INFK (Computer Science) and D-ITET (Information Technology and Electrical Engineering). Page formats (tools/listing_formats.py, tests/test_listing_formats_ethz.py), one per site era:
- INFK professors: `eth_infk_h4` (inf.ethz.ch/people/faculty.html, 2016-2021 and the 2021-2022 span variant) and `eth_infk_bold` (people/faculty/faculty.html, 2022-10 on). Emeriti `eth_infk_emeriti` and affiliated `eth_infk_affiliated` are captured from 2025 only: the emeriti page states each person's tenure years, and the extra years would only spend the shared Wayback slots.
- ITET: `eth_itet_any` ('Prof. Name' headings 2016-, and the 2017 professors table 'Last, First, Prof. Dr.'). The page gives no rank beyond 'Prof.', so the charter's ladder rank word is `\bprof\b`.
Roster years open (reported, not blocking): INFK 2017 (no archived capture), 2020 (no capture; the 2020-2021H1 captures are script shells that parse to 0); ITET 2018, 2020, 2021 (no capture).
Rows: 1058 rows, 717 listing rows used; people INFK 80, ITET 59.
Flag: 105 entries had no quote (emeriti/affiliated cards that have no title line); they carry the page's own tenure/heading text.

Affiliated units (stage 2 searches): MAVT has a static professors page (mavt.ethz.ch/people/faculty/professors.html, Wayback captured by the `units` step). BAUG, BIOL, BSSE, HEST, MAT, MTEC and PHYS publish their people lists with JavaScript (PersonListCard); they were rendered once with tools/js_render_capture.py on Slurm (job 32540154 and 32541418, robots allowed, no challenge, rendered DOM and raw HTML stored in the js_render table; current 2026 lists only, no history). ARCH, CHAB, EAPS, GESS, MATH and USYS: no people list found at any probed URL (rendered DOM names no professors); recorded as units without a usable listing, candidates there are decided on DBLP/OpenAlex evidence or excluded_unresolved. Centres (CSCS, SDSC, SEC, AI Center, Collegium, INI): not yet searched.
