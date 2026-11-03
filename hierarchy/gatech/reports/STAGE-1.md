# Georgia Institute of Technology, stage 1: sources and captures

Date: 2026-11-03. Gate (`atlas stage-gate gatech 1`): **pass** with 21 reviewed `listing_gaps` year entries (below). Jobs: captures 32087538 (first pass, no formats yet), 32087808 (after the formats and `replan.py`).

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

## Exceptions (every one is a charter `listing_gaps` entry, for the owner to review)
- **Paged directories.** The Drupal 7 sites showed 9 people per page in 2016 (CS, IC 2016-17, CSE: page 1 of about 40 only; pages 2+ are archived at other dates). From 2023-24 the Drupal 9
  site shows 12 per page for CS and CSP (page 1 only is archived; `?page=N` and the A-Z letter pages are sporadic) and 40 per page for ECE. The pipeline takes one capture per half-year, so these
  years are recorded as gaps: CS 2016, 2024-26; IC 2016-17; CSE 2016; CSP 2023-26 (and 2016-22, school not yet founded); ECE 2024-26.
- **What this means for stage 2-4.** The School of Cybersecurity and Privacy has NO listing rows at all, and CS has none for 2024-26, so people hired into them since 2023 are not in the census from
  listings. Stage 2's DBLP-affiliation and OpenAlex candidate rules are the net for them; stage 4 bridges 2024-26 for already-listed CS faculty from profile pages (`[periods].profile_patterns`).
  Request R3 (general): let `plan_fetch` merge several captures of a paged slot in one half-year (page 0..N and the letter pages), which would close all 21 gap years.
- **Truncated titles.** From 2023 the cards cut long titles with an ellipsis ("Executive Director, Institute for Data…"): about 10% of gt_card rows (6 of 30 CSE, 7 of 59 IC in 2026) lose the
  word "Professor" and read as unranked in that year; the profile page has the full title. Stage 4's profile bridging and the other years' ladder rows cover them; to check at stage 2.
- ISyE and ECE lists carry every category (staff, postdocs, emeriti): ranks filter them at stage 2; both are `affiliated` departments.
- ISyE 2016-2018 pages use a second `h4.name` template (handled by the same format).
- Live probes: all live hosts served real pages, none challenged; robots.txt allowed every fetch.
