# Georgia Institute of Technology, stage 1: sources and captures

Date: 2026-11-03. Gate (`atlas stage-gate gatech 1`): **pass** with 11 reviewed `listing_gaps` year entries (7 are the Cybersecurity and Privacy years before the school existed; 4 are real archive gaps, below). Jobs: captures 32087538 (first pass, no formats), 32087808 (formats), 32087861 / 32089234 / 32089330 (R3: paged directories fetched page by page, then the A-Z letter fallback).

## URL eras (exact-URL CDX, `tools/discover_listings.py`; links read from the 2016 Wayback homepages)
| dept | era | URL | format |
|---|---|---|---|
| CS (School of Computer Science) | 2016- | `scs.gatech.edu/people/faculty` | gt_people (Drupal 7, to 2023), gt_card (Drupal 9, 2023-; paged) |
| IC | 2016-2023-06 / 2023-07- | `www.ic.gatech.edu/person/faculty` (not `/people`) / `ic.gatech.edu/people/faculty` | gt_people / gt_card (one page of about 60) |
| CSE | 2016- | `cse.gatech.edu/people/faculty` | gt_people / gt_card (one page) |
| CSP (Cybersecurity and Privacy) | 2023-12- | `scp.cc.gatech.edu/people/faculty` | gt_card (paged, 12 per page) |
| ECE (affiliated) | 2016-2023-03 / 2023-04- | `www.ece.gatech.edu/faculty-staff-directory` / `ece.gatech.edu/directory` | ece_old (all staff) / ece_new (paged, 40) |
| ISyE (affiliated) | 2016-2023-04 / 2023-05- | `www.isye.gatech.edu/people` / `/people/faculty` | isye_old / isye_card (all people categories) |

## Counts (`listings/gatech/derived/rows.json`, 9,794 rows; distinct names per year)
CS 37-46 (2017-2023); IC 49-66 (2018-2026); CSE 19-36 (2017-2026); ISyE 138-192; ECE 321-391 (every staff category). IC 2016-17 and CS/CSE 2016: partial (below).

## Paged directories (R3, general fix) and what is left
`plan_fetch.fetch_pages` now treats a paged slot as one listing: it takes the page links of the chosen capture (`?page=N`, `&amp;page=N`; the ':80' of old Wayback URLs is dropped), fetches the capture of each page
nearest in time within the same half-year, and when `?page=N` pages are not archived falls back to the A-Z letter pages (`/people/faculty/a` ... one per letter). Pages are stored in `plan_pages` (page, capture URL,
timestamp; each capture keeps its own sha256) and `listing_rows.py` merges them into one row set per slot-half. Tests: Drupal 7 and Drupal 9 fixtures, the letter fallback, the port.
Gap years before the fix: 21 (CS 2016, 2024-26; IC 2016-17; CSE 2016; CSP 2023-26; ECE 2024-26). After:
| unit | gap years closed | gap years left |
|---|---|---|
| CS | 2016, 2024, 2026 | 2025 (letter 'n' not archived in either half-year) |
| IC | 2016, 2017 | none |
| CSE | 2016 | none |
| CSP | 2025, 2026 | 2023 (page 1 of 2 only), 2024 (no complete page set); 2016-22 school not yet founded |
| ECE (affiliated) | 2024, 2025 | 2026 (letters u, v, y not archived) |
People per year now: CS 37-121 (2016: 59, 2024: 78, 2026: 52), IC 47-66, CSE 17-36, CSP 28 (2025), 31 (2026), ISyE 138-192, ECE 321-433. 12,019 rows. The union of A-Z letter pages in 2024 holds more names than the
paged list (78 vs about 60): it carries every classification on the school page, and stage 2's rank filter decides who counts.

## Remaining exceptions (charter `listing_gaps`, for owner review)
- CS 2025, CSP 2023-24, ECE 2026 as in the table. People hired into the Cybersecurity and Privacy school in 2023-24 are not in the census from listings; stage 2's DBLP and OpenAlex candidate rules and
  stage 4's profile bridging cover them.
- **Truncated titles.** From 2023 the cards cut long titles with an ellipsis ("Executive Director, Institute for Data…"): about 10% of gt_card rows (6 of 30 CSE, 7 of 59 IC in 2026) lose the
  word "Professor" and read as unranked in that year; the profile page has the full title. Stage 4's profile bridging and the other years' ladder rows cover them; to check at stage 2.
- ISyE and ECE lists carry every category (staff, postdocs, emeriti): ranks filter them at stage 2; both are `affiliated` departments.
- ISyE 2016-2018 pages use a second `h4.name` template (handled by the same format).
- Live probes: all live hosts served real pages, none challenged; robots.txt allowed every fetch.
