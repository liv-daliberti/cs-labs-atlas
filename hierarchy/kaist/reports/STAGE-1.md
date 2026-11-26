# KAIST onboarding, stage 1 - 2026-11-24

## Sources and captures
- Full-coverage department: School of Computing (`cs.kaist.ac.kr/people/faculty`). One page lists every category (Professor, Joint Professor, Emeritus, Affiliated, Research, Invited) as headed groups; server-rendered, so no Selenium needed. The new format `kaist_cs_horiz` (tools/listing_formats.py, fixture test tests/test_kaist_stage1_listing.py) reads li.horiz_item, keeps the group heading as a title line and as `division`, drops office, e-mail and phone, and quotes the printed name (the page puts soft hyphens inside names).
- Wayback exact-URL CDX showed 46 captures 2016-03-26..2026-10-06. `run_school.sh kaist` (job 32539583, 1 h 34 min, Wayback's shared 6 s clock) stored 17 captures covering every half-year 2016H1-2026H1 that has one.
- `listing_rows.py kaist`: 1628 rows, 0 entries without a quote, 275 listed names. Ranks: ladder 819, courtesy 357, emeritus 244, research 90, visiting 46.

## Korean-language listing finding (owner questions, see STAGE-2.md)
The page is Latin-named through 2024H1 ('Doo-Hwan Bae') and Hangul-only from 2024H2 ('배두환'); 2025-2026 rows are Hangul only. The live site no longer serves an English list (`?lang=en`, `?gubun_lang=en` and `/en/...` give Hangul or 404). Each card carries a stable profile id (`/people/view?idx=N`): 99 ids occur in both a Latin-named and a Hangul-named capture, 24 only in Hangul captures, 45 only in Latin ones. The census builder cannot merge a Hangul spelling with a Latin one; no merge rule was invented.
Rank words (charter): Hangul titles are mapped by the charter's `rank_words` (교수/부교수/조교수 ladder, 명예교수 emeritus, 연구교수 research, 초빙교수/방문교수 visiting, 겸직교수 and 겸임교수 plus 'Joint/Affiliated Professor' courtesy). The mapping of 겸임/겸직 to the old English 'Affiliated'/'Joint' headings is my reading, not stated by the page.

## Gate
`atlas stage-gate kaist 1`: pass (exit 0): 1 department, roster source present, `roster_years_open` 0. Affiliated units get their listings in stage 2 (`cs_related_school.py units`).
