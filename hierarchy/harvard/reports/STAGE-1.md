# Harvard stage 1: historical faculty evidence review, 2026-11-06

Historical listing coverage remains **incomplete**. This report records the initial historical review. The owner subsequently authorized a supported partial release; the current scope, finite completeness exceptions and build results are documented in [PARTIAL-PACKAGE.md](PARTIAL-PACKAGE.md). Unknown historical years remain unknown, and the school remains onboarding pending coordinator release.

## Evidence saved and reviewed

`reviewed/history-source-review.json` is a source inventory and dated research handoff. It does not add PIs, appointment periods, listing coverage, or gate exceptions automatically. Its 12 official sources and 58 live listing rows carry URLs, raw-body SHA-256 hashes and verbatim quotes. Captured bytes remain in the shared untracked container `code/hierarchy/harvard/raw/school-captures.sqlite`, table `live`. All source hashes and HTML quotes were checked against that container. PDF quotes were checked against `pdftotext -layout` output with whitespace normalized.

- The current CS people directory's Faculty checkbox submits `role[46]=46`. The three saved pages have 20, 20 and 18 rows: 58 distinct names. The unfiltered directory has 15 pages and mixes faculty, graduate students, research appointees and staff. The faculty filter itself includes affiliates, visitors, emeriti, lecturers, preceptors and Associates, so 58 names does not mean 58 approved PIs. These live observations prove only the capture calendar year, 2026.
- Nine official appointment-news sources provide 13 date findings. Examples include Dwork's announced January 2017 start; Yu's announced January 2018 start; Glassman's announced January 2019 start; a retrospective explicit 2019 start for Tambe; Brantley's actual July 1, 2024 start; and announced future starts for Wattenberg, Viégas, Kakade, Du, Albergo and Wang. Reddi's announcement is an Electrical Engineering computing-review lead. Future appointment language never proves an appointment on the announcement date. Kakade's January year is contextually inferred from the October 2021 article and remains flagged for confirmation before writing a period. No season was converted into a fabricated month or day.
- The official `RESEARCH 2023-24` brochure was captured as a 22,688,254-byte PDF, SHA-256 `ee2ea163641081ea646c24b33b0056b85671ec98f0ad017f78d57d4595f08042`, at `https://seas.harvard.edu/media/91022/download?attachment=`. It supplies historical faculty and research-area discovery leads, including computing faculty outside CS. Its academic-year label was not converted into calendar-year listing coverage or appointment intervals. The raw PDF is in the container; extracted scratch copies are under the school's ignored `tmp/`.
- Wattenberg and Frankle currently have official SEAS profiles titled `Associate in Computer Science`. The prior professor announcements are historical leads; the current titles do not determine an exact departure date. Search-index descriptions calling Wattenberg a professor were stale and were rejected in favor of the captured official page.

## Parser and charter repairs

The saved host probe `https://web.archive.org/web/2020id_/https://seas.harvard.edu/faculty` was overlooked because it is in `live`, not `captures`. Its body has the older SEAS `field-wrapper` classes; the parser returned zero rows. The corrected class matching returns 20 rows, preserving titles and profile links. The fixture checks both markup forms, a missing title, and the historical pager's search/sort parameters. This nonexact archive selector lacks a saved resolved capture timestamp and response headers. It proves a markup form only; no 2020 appointment or listing year is credited.

The all-SEAS directory includes non-CS professors. `title_match` selects title lines but previously did not prevent the fallback rank classifier from admitting every other SEAS professor into full-coverage CS. A new optional slot `title_filter` in `listing_rows.py` excludes those rows **after** capture parsing and pagination checks. The Harvard all-SEAS slot requires a Computer Science title. The CS-area slots stay unfiltered to retain CS faculty with named-chair, dean, or cross-disciplinary titles. The integration fixture proves that the optional filter removes the Materials Science row, preserves the CS row, leaves the capture parser complete, and preserves default behavior when omitted.

The charter names `seas_directory`, removes broad prefix CDX from the all-SEAS slot, and adds the observed faculty-filter URL for 2026. Exact historical URL-era boundaries remain unproven. The earlier charter's claim of 82 captures is not backed by a saved CDX response in this school's container; it is not treated as reviewed capture evidence.

## Access and remaining gaps

No direct archive request or competing archive driver was started. The coordinator owns job `32136252` and the shared discovery queue in `scratch/completion-20261106-onboarding/`. The coordinator's latest throttle reading, at 22:36 ET on November 6, puts new-school archive eligibility no earlier than **23:55:51 ET**. That time can move; the existing driver must recheck the shared throttle before fetching. A 429 or cooldown does not establish absence.

The historical CRCS annual-report lead and theory faculty-profile lead both returned **403 on robots.txt** (`crcs.seas.harvard.edu`, `toc.seas.harvard.edu`). Content requests stopped before either source was fetched. Both hosts are now explicitly `wayback-only` under D5. No report content or Yaron Singer appointment facts from those leads were admitted. No named-AI denial was bypassed.

At this review the school store contains 37 live captures, 18 robots records, zero CDX rows, and zero exact historical captures. Stage 1 still needs a usable, complete listing for **every CS calendar year 2016 through 2026**. The saved live 2026 listing is reviewable evidence, but has not been injected into the Wayback listing plan. There is no reviewed gap-year reason.

Next archive work, through the coordinator's sole driver:

1. Complete exact-URL discovery for `seas.harvard.edu/faculty`, `seas.harvard.edu/computer-science/people` and the queued older `www.seas.harvard.edu/` homepage. Inspect homepage links to discover pre-redesign faculty URLs rather than treating guessed empty URLs as absence.
2. Test the linked `www.seas.harvard.edu/faculty` alias seen in the saved older markup, and the observed faculty-filter query as exact URLs. Do not assert era date boundaries until the responses are saved.
3. Fetch one exact-timestamp sample per observed markup era; retain the raw capture, hash, timestamp and parser result. Fetch all linked pages within the same half-year before crediting a complete listing. The older all-SEAS pager has nine total pages; the current all-SEAS pager has ten.
4. Run the charter listing plan, `listing_rows.py harvard`, and stage-1 gate. Keep missing captures, transient failures and reviewed genuine source gaps distinct. Historical news and the academic-year brochure do not replace the full roster requirement.

## Validation

- School listing-format and Harvard integration tests: 19 passed.
- `school_config.py --check harvard`: passed.
- Ruff, including the modified parser/test files: passed.
- Raw-body hashes, 58 contact-free listing quotes, distinct-name count and all appointment-news quote substrings: checked locally.
- Overlay gate rerun: stage 0 **PASS**, 18 hosts, zero inconsistent hosts, 1,139,920 snapshot works. Stage 1 **FAIL**, 11 open CS department-years (`never planned` for 2016–2026), zero reviewed gap years. Gate command exited 1 as expected. No waiver was added.
