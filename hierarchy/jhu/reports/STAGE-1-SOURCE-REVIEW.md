# JHU stage 1: source review, 2026-11-06

Branch: `agent/history-jhu-20261106`, based on accepted main `10d7df3`.
Stage 1 remains open. No waiver, census acceptance, release, landing, or push was performed.

## Sources collected and reviewed

The raw evidence is in the shared data store
`/n/fs/resemble/homogenizing-science/code/hierarchy/jhu/raw/school-captures.sqlite`.
The branch's `reviewed/historical-source-review.json` records 18 official live-page receipts,
20 reviewed historical facts, and seven previously saved exact-URL CDX results. Every fact
has a verbatim quote and a source carrying URL, raw-byte SHA-256, and capture time. The
collector's stored `fetched_at` is local New York time; the receipt also gives an explicit UTC time.
No contact details are copied into reviewed facts or fixtures.

The historical facts include Yuille and Schatz arriving in 2016, Cao arriving in 2018,
Kosaraju's retirement reported in July 2020, Khashabi's 2022 arrival report, Hadfield's 2025
arrival report, and Chiu's 2026 arrival report. These are source statements, not inferred
continuous appointment intervals. The July 2020 retirement report does not establish an exact
retirement day.

The September 2022 welcome article distinguishes Anjalie Field's and Ziang Xiao's research
ranks from their announced future tenure-track starts, July 2023 and January 2024. The January
2024 collective welcome article independently names them and five other assistant professors.
The Fall 2018 seminar biography calls Mathias Unberath a postdoctoral fellow; the January 2020
biography calls him an assistant research professor. Those observations must not become
ladder appointments. An older three-arrival article lacks a visible publication date; its
image upload directory is not accepted as a date.

## Parser and charter changes

The current CS roster parses 77 entries, matching all 77 visible `entity_list_item` markers.
Two linked faculty lists were absent from the charter and had no supported parser:

| Official page | Visible person markers | Parsed entries | Raw SHA-256 |
|---|---:|---:|---|
| [CS main faculty](https://www.cs.jhu.edu/faculty/) | 77 | 77 | `edcd65cb150863b03ec33fa3cf7572d0a90cfba20ca260453752aab5b8d39959` |
| [CS secondary faculty](https://www.cs.jhu.edu/people/cs-affiliates/joint-and-secondary-faculty/) | 46 | 46 | `3192b4b3bfd6230196515442f3556a1f77f1a88446cb686fd7dc3997d2ca9e81` |
| [CS research, visiting, part-time faculty](https://www.cs.jhu.edu/people/cs-affiliates/research-visiting-and-part-time-faculty/) | 23 | 23 | `913b49eb2266aff5d71b710c209012f55de881c8edcd4f92916e11f050cb7b35` |

`wse_contact` parses each visible contact block once, ignoring duplicate JSON-LD and contact
details. It retains research/visiting/part-time section headings and separates faculty-profile
links from personal websites. Fixture URLs and visible names/titles were checked against the
saved HTML. The charter includes these exact secondary and research URLs for 2026 only;
this is the reviewed observation year, not a claim that the URLs first existed in 2026.
Earlier eras remain to be discovered.

Two rank safeguards accompany the new slots. An explicit `Incoming Assistant Professor`
title is `other`, because an announced arrival proves no current appointment. Stephanie
Milani's current profile independently says she is incoming. An otherwise ladder-ranked title
in a `kind = "courtesy"` listing is classified `courtesy` while preserving the written home-unit
title; research and emeritus ranks retain their classifications. This uses the existing
`census_build` courtesy-faculty review path instead of turning secondary faculty into primary CS
appointments. Reviewed home departments and research-faculty PI basis still belong to later stages.

## Archive discovery and access limits

No archive request was made by this branch while the shared cooldown was active. Shared job
`32136252` owns the round-robin discovery queue under project scratch
`completion-20261106-onboarding/`; its scheduled start was November 6 at 23:22:21 New York time.
The coordinator must reconcile the host-throttle state before further archive work.

Cached exact-CDX evidence proves only these URL discoveries:

| URL | Saved 200 captures | First | Last | Review |
|---|---:|---|---|---|
| `www.cs.jhu.edu/faculty/` | 59 | 2016-01-22 | 2026-11-04 | Main URL spans the window; formats still need historical samples. |
| `www.cs.jhu.edu/people/` | 57 | 2016-03-12 | 2026-10-02 | Landing-page candidate; not presumed a faculty roster. |
| `ece.jhu.edu/people/` | 0 | — | — | Empty exact query, not evidence that ECE has no faculty captures elsewhere. |
| `ece.jhu.edu/faculty/` | 0 | — | — | Discover earlier URL from the queued old homepage. |
| `engineering.jhu.edu/ams/people/` | 45 | 2016-03-03 | 2025-11-18 | AMS era already repaired in accepted main. |
| `ams.jhu.edu/people/` | 0 | — | — | No useful additional work in the original Claude dirty charter. |
| `bme.jhu.edu/people/faculty/` | 45 | 2020-12-18 | 2026-07-28 | Originals use `www.bme.jhu.edu`; pre-2020 era remains unresolved. |

The official academic catalogue's robots.txt allows ordinary current department pages but
explicitly disallows `/archive/` for `User-agent: *`. The historical archive was not fetched.
A permitted current CS catalogue page was checked and contains no faculty roster. No archive
or alternate client was used to work around the disallow. Other JHU challenge blocks and
named-AI robots exclusions remain in force.

## Validation and remaining work

All 46 tests in the five school-specific listing-format modules plus listing continuity passed.
The JHU charter schema check passed. Full-capture checks found 77/77, 46/46, and 23/23 entries;
every parsed row had a source quote, and the new secondary rows kept courtesy context.

The last stage-one gate still has 43 open department-years: CS 2016–2026, ECE 2016–2026,
AMS 2016–2025, and BME 2016–2026. The existing reviewed AMS 2026 gap remains unchanged.
Live-page source review does not count as archived listing coverage and this change does not
populate the listing plan or fabricate an `ok` status.

Next steps are to review the shared job's historical samples, implement formats for each
observed era, read old ECE/BME homepage links to discover their exact faculty URLs, and submit
the capture plan only after coordinating the one archive lane. The two new 2026 CS URLs also
need exact-CDX discovery; earlier CS secondary/research URLs must be learned from archived
links before widening their charter ranges. Then run the listing plan, `listing_rows`, and the
stage-one gate. Temporary 429 responses remain retryable access failures, never reviewed gaps.
