# WashU stage 1: historical source review

Reviewed 2026-11-06 on `agent/history-washu-20261106`, based on accepted main
`10d7df3`. Original Claude worktrees and the shared archive task queue are preserved.
The school stays `onboarding`, stage 0. No waiver, release, push or publication.

## Evidence collected during the archive cooldown

The official index at `https://bulletin.wustl.edu/about/prior/` links ten engineering
Bulletin PDFs, academic editions 2016–17 through 2025–26. `school_web` fetched the
index and these ten explicit links, caching the raw bodies in
`hierarchy/washu/raw/school-captures.sqlite`, table `live`.

Robots allows `/about/prior/`, including the linked PDFs; it disallows `/prior/`.
The historical HTML fetch was refused by `school_web` before any page request.
No `/prior/` HTML was fetched, and no alternate host was used to evade its rule.
The Bulletin host is now in the charter; the host gate passes with 14 hosts and
zero inconsistencies. The host check reused the cached archive probe, making no
new archive request.

`reviewed/historical-source-review.json` preserves 30 department Faculty sections
(CSE, ESE, BME in each PDF), each with source URL, raw SHA256, full verbatim
whitespace-normalized quote, PDF bookmark page, printed date, academic edition,
and creation metadata. `tools/washu_bulletin_review.py` regenerates the evidence
offline, verifies raw hashes and index membership, uses the PDF department
bookmarks, and refuses missing faculty boundaries or conflicting printed dates.
No person, appointment interval, accepted listing row or coverage claim is
automatically created from these source sections.

| Academic edition | Printed date | Departments preserved |
|---|---|---|
| 2016–17 | 2016-10-04 | CSE, ESE, BME |
| 2017–18 | 2017-10-18 | CSE, ESE, BME |
| 2018–19 | 2018-10-29 | CSE, ESE, BME |
| 2019–20 | 2019-10-29 | CSE, ESE, BME |
| 2020–21 | 2021-01-15 | CSE, ESE, BME |
| 2021–22 | 2022-11-16 | CSE, ESE, BME |
| 2022–23 | 2023-04-28 | CSE, ESE, BME |
| 2023–24 | 2024-06-03 | CSE, ESE, BME |
| 2024–25 | 2025-07-11 | CSE, ESE, BME |
| 2025–26 | 2026-07-16 | CSE, ESE, BME |

Printed dates match each PDF's creation metadata. The 2021–22 PDF was generated
after its academic year and is explicitly flagged for date review. The other
edition labels also do not establish continuous appointments or both calendar
years. Dates are preserved independently, pending individual roster review and
a standard import path for dated official catalog evidence.

The 2016 CSE faculty section proves historical names that contemporary rosters
miss, including Yasutaka Furukawa, Benjamin Moseley, Robert Pless and Sanmay Das.
It also preserves the original rank grouping: professors, associate professors,
assistant professors, practice, research, lecturers, senior professors and
emeriti. Research and teaching appointments still need the stage-3 PI-basis
review. Senior professors are not silently assigned ladder or emeritus status.
Its text provides actual legacy profile URL shapes, for example
`cse.wustl.edu/faculty/Pages/faculty.aspx?bio=109` and
`cse.wustl.edu/faculty/Pages/Ruth-Miller.aspx`; these are discovery leads, not
newly fetched or validated historical directory slots.

The BME 2017–18 section links Patricia Widder to the exact legacy URL
`bme.wustl.edu/faculty/Pages/default.aspx`, a useful explicit directory discovery
lead for the shared archive follow-up. Its archive availability is not yet known.

An additional permitted live primary source now establishes the exact old CSE
directory URL, rather than only per-person profile shapes:

- Source: `https://bulletin.wustl.edu/undergrad/Bulletin_2023-24_Undergraduate.pdf`,
  printed 2023-09-22, PDF page 1141 (printed page 1140).
- Raw SHA256: `7c8abbc913e4f74b3871fb7c49b290b622b433188cbf9275db6ae8bd9d09f5fa`.
- Verbatim normalized quote: “Additional information can be found on our CSE
  website (http://cse.wustl.edu/), or any of the CSE faculty
  (https://cse.wustl.edu/faculty/Pages/default.aspx) can oﬀer further guidance
  and information about our programs.”

The body is cached in the same school `live` table. This makes
`cse.wustl.edu/faculty/Pages/default.aspx` an evidence-backed exact-URL CDX
follow-up. The directory itself was not fetched; neither its capture range nor
its page format is asserted. The original shared queue is unchanged. The 2016
undergraduate PDF was also cached (SHA256
`f40f1bc68c84280c0d3c153e5a191fc6404275d09ad4bffa59aaafd8f20a0ab3`)
but did not contain that directory hyperlink; its general CSE website link
does not establish an additional directory era.

## Cached directory review and charter corrections

| Source | Cards | Parsed | Pagination |
|---|---:|---:|---|
| CSE archive 2020-09-15 22:23:51 | 41 | 41 | none detected |
| CSE archive 2024-05-28 16:27:41 | 48 | 48 | none detected |
| CSE live cached 2026-11-05 | 49 | 49 | none detected |
| ESE live cached 2026-11-05 | 75 | 75 | none detected |
| BME live cached 2026-11-05 | 36 | 36 | none detected |

The archived CSE homepage links directly to `faculty-research/directory.html` in
2020 and 2024. All five directory bodies match `wu_teaser`, with exact card/row
parity. Small fixture excerpts carry their original URL and body hash. ESE's
directory mixes affiliates with core faculty: `Hongyu An` has the literal title
`Affiliate, Radiology`, so the WashU charter now recognizes `affiliate,` as
courtesy. This title does not independently prove a professor rank. The CSE
dean-only card remains `Dean`, with no fabricated professor title.

ESE and BME each now use a single slot name across their wustl.edu and washu.edu
URL eras. Their current eras name the verified `wu_teaser` parser. Their URL-era
date bounds remain provisional until exact-URL discovery returns; no format is
asserted for the unsampled legacy ESE/BME era.

## Gate and precise remaining work

The post-review check reports stage 0 **pass** (14 hosts, 284,817 snapshot
works), stage 1 **fail**, **31 open department-years** (down from 33), zero
reviewed gap exceptions. The two usable CSE captures were copied strictly
offline to the previously absent standard listing store, preserving their raw
bytes, timestamps and hashes. Both pass the standard planner's `usable` and
`charter_usable` checks. Standard `listing_rows.py` emits **89 rows, 52 people**:
41 rows for CSE 2020H2 and 48 for CSE 2024H1. Every emitted quote is a substring
of the stored text; every raw hash and observation year was independently
verified. No quotation or card was dropped. The raw hashes are respectively
`6e2f9f6c0703ac49c930ba5ff86a3c5d3dbcb6926c6ac18328ab59cc1de07e0f` and
`c367f8f40d192e9c6c5940f665cc72add18ddbee37bb08068cc5ace7b152947a`.

The cached-only reuse receipt is
`hierarchy/washu/tmp/history-offline-listing-reuse-20261106.json`; it records
zero network requests, both source capture URLs, timestamps, original hashes
and card counts. Standard outputs are `listings/washu/raw/captures.sqlite` and
`listings/washu/derived/{rows,coverage}.json` (untracked data).
The fresh gate receipt is
`scratch/completion-20261106-washu-history-gates.json` under the project root;
the original takeover gate receipt remains preserved.

The open annual items are CSE 2016–19, 2021–23, 2025–26, and every ESE/BME year
2016–26. CSE 2020H1 and 2024H2 still need the normal half-year capture pass even
though the annual gate now has evidence for those years.

1. Coordinate with the owner of shared discovery job **32136252** before any
   archive request. Preserve its round-robin tasks and respect the global host
   throttle, including a cooldown extended by another transient 429. The
   coordinator's latest eligibility floor is **2026-11-06 23:55:51 ET**; recheck
   the shared throttle rather than assuming that floor remains current.
2. Review the queue's old CSE/SEAS/Engineering homepage samples for exact linked
   faculty directory URLs; inspect ESE/BME samples for format drift and dates.
   Add actual eras only after evidence, then run the standard half-year plan.
3. Review the preserved catalog sections per person, keeping printed date and
   academic edition distinct. A catalog-source importer must cite the actual
   PDF and raw hash and preserve PDF text as the quote source; it must not invent
   Wayback timestamps or merge academic years into appointment intervals.
4. Parse the completed capture plan, review card parity, pagination, and annual
   counts, then rerun stage 1. A transient 429 never becomes `no capture` or a
   `listing_gaps` exception.

Reproduce the offline evidence with:

```
bin/atlas run tools/washu_bulletin_review.py --out hierarchy/washu/reviewed/historical-source-review.json
```

Validation: eight focused real-source/boundary/date tests pass; all 12 charters
validate; repository lint and whitespace checks pass. The full repository suite
passes: **1,318 passed, 15 skipped**, two existing datetime deprecation warnings,
97.03 seconds. Log: `hierarchy/washu/tmp/history-tests-20261106.log`.
