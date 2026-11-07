# Toronto onboarding checkpoint — November 7, 2026

The preserved Claude charter has been copied into an isolated branch and repaired for current live sources. Scope remains St George CS plus computing-related faculty with explicit appointment evidence; campus-specific and cross-appointed entries remain distinguishable. The census below is provisional, not a passed historical PI census.

## Charter and source gates

Charter validation and charter traps pass. All 13 host checks are consistent: six stale/dead probes were replaced using explicit links on the official CS directory or iSchool homepage; iSchool's current faculty directory is `/faculty-directory/`. Statistics returned robots HTTP 403 and is Wayback-only. TSpace's named AI-agent exclusion is retained; it is never queried. Robotics requires a 60-second crawl delay. Affiliated-unit listing URLs beyond the reviewed CS/iSchool pages still need source discovery and semantic review.

Stage 0 currently has one open automated finding: the local OpenAlex snapshot has no indexed Toronto works. The coordinator authorized one standard Toronto snapshot extension after this charter commit (16 tasks, one CPU/8 GB/59 minutes each, then the standard merge). No OpenAlex API call or remote snapshot extension has yet run at this checkpoint. Do not infer that the shared filtered snapshot contains no Toronto coauthor bylines; it is not a complete Toronto sweep.

## Current listing evidence

Official source: https://web.cs.toronto.edu/people/faculty-directory, captured 2026-11-07T15:40:55, SHA-256 `ab4fff5fca74192a963b7a39ee58ac698b8e46d7a1179317d230f8163a8b5337`. The complete current page has 214 entries: 89 research stream, 22 teaching stream, 19 emeriti, 58 cross-appointed, 15 status-only and 11 adjunct. Two entries omitted by naive tr parsing are recovered from malformed source rows; contact and research cells never become titles. Each category has its own charter slot and reviewed expected count.

A current-only census preview has 85 qualifying research-stream rank candidates and 129 non-PI entries. The 89 main entries exclude three visiting professors and one status-only scientist from automatic PI candidacy. All cross-appointed entries are currently held for home-unit evidence; teaching/emeritus/adjunct entries need the normal reviewed independent-PI basis. A deterministic 30-row listing sample (seed 20261107) was read against its exact quote, section, rank and linked homepage; no parsing mismatch found. This does not substitute for campus eligibility or historical recall review.

The main directory includes dual-campus faculty. Homepage evidence explicitly names UTM/UTSC for Jessica Burgner-Kahrs, David Fleet, Michael Molloy, Gennady Pekhimenko, Sushant Sachdeva, Bianca Schroeder, Florian Shkurti and Akshayaram Srinivasan. Some also explicitly name St George. Preserve those distinctions and review eligibility before reporting a St George-only PI population; do not silently admit or exclude by URL host.

## Website register

Every one of the 85 provisional PIs has a register entry. All linked targets were attempted once without following HTTP redirects or querying archives. Outcomes: 68 HTTP 200, nine HTTP redirects held for review, seven names without a linked homepage, one Statistics-host page deferred by policy. Visible content review establishes 59 PI/lab websites with actual official-directory outgoing-link evidence and captured-body date/hash. Kuldeep Meel has a documented other-institution/on-leave case: his captured homepage foregrounds Georgia Tech and explicitly says Toronto is on leave. There are 25 open entries: redirects, frame shells, institutional profile cards, missing homepage leads or an archive-dependent target. These are pending research, not claims that no lab website exists.

The website gate has exactly 25 unresolved entries and must not be reported passed. Students and paper-page extraction were deferred throughout. Positive personal-page content reviews use `classification_review`, not the unresolved-candidate `review_note` field. Re-running generic audit discovery may overwrite reviewed content classifications; preserve them.

## Reproducibility and next steps

Code/parser validation: 1426 tests passed, 15 skipped; lint, charter validation, zero charter traps and secret scan passed. Raw source pages remain in school-captures.sqlite. Receipt and deterministic sample details are preserved under `scratch/top25-resume-1107/toronto-*`. Source-only reviewed files and this report are committed; raw HTML, contact cells and derived census outputs are not committed.

Next: run the authorized single snapshot extension, then its sanity check and local PI-paper chain; review campus/home-unit cases and explicit appointment periods; resolve the 25 website cases with recorded redirect/frame/official-profile links; queue historical listing coverage through the shared archive workflow. No historical gate, PI precision gate, paper precision gate or student gate passes at this checkpoint.

## Authorized snapshot extension submitted

After charter commit `665d937`, the standard `snapshot-ext` pipeline passed sbatch test-only without preemption and was submitted once: filter array `32142785` (tasks 0–15, one requested CPU, 8 GB, 59 minutes each) followed by merge `32142786` (one CPU, 16 GB, 59 minutes; afterok dependency). The filter tasks started at 16:41:19 on November 7. Code is pinned to the charter commit; main snapshot is unchanged, output is the separate `ext-toronto.sqlite`.

Input manifest date is 2026-10-14: 2,415 work/author parts, 749,420,454,328 compressed bytes streamed; raw parts are not materialized. Manifest/URLs and run metadata are reusable at `scratch/top25-resume-1107/toronto-snapshot-input-manifest.json` (SHA-256 `8e15e80d77e4ce69ffb29f0a98860a5d40f8ec72b446ea9b0fee4eca093e31cc`) and `scratch/pipeline-snapshot-ext-20261107-164118-424406/jobs.json`. The shared filesystem showed 686 GB available before submission. Filtered size, successful completion, sweep sanity and next-stage jobs remain to measure; no second school extension is authorized by this checkpoint.

## Website follow-up

Twelve additional eligible pages were verified by resolving explicit HTTP Location headers, HTML redirects, frames or an official institutional-profile homepage link, with a fresh host-policy check before each target. The register now has **71 verified websites, one documented other-institution/on-leave site, and 13 pending entries**. Every resolved chain preserves the original official href, intermediate source date/hash, response or HTML link evidence, and final capture date/hash; indirect links are labeled as chains, never represented as direct hrefs.

Three redirect destinations challenged the collector (Alán Aspuru-Guzik, Niv Dayan and Bo Wang). Their live hosts were stopped and marked Wayback-only; no challenge workaround was attempted. Daniel Wigdor's destination is an Apache default installation page and remains pending. Remaining entries: these four, Lisa Strug (Statistics access policy), Anna Goldenberg (institutional card needs a lab link), and seven names without a homepage link in the official CS listing (Arvind Gupta, Rahul G. Krishnan, Alex Mariakakis, Gururaj Saileshwar, Sam Toueg, Nathan Wiebe and Ningning Xie). The site gate remains open for 13 entries (17 findings, including the additional archive flag on four of them). Nandita Vijaykumar's newly resolved homepage explicitly names both CS and the Scarborough department, adding another campus-review case.

## Local-data continuation queued

The standard local-data pipeline is afterok-chained to snapshot merge `32142786`, pinned to `258c96b`: DBLP affiliated-person pass `32142868`, local snapshot sweep `32142869`, sweep sanity check `32142870`, and outside-CS candidate generation `32142871`. Each stage is explicitly capped at 59 minutes (two CPUs; 16 GB for DBLP, 24 GB for the other stages), with the standard excluded nodes and a successful no-preemption test-only probe. No second remote snapshot pass or OpenAlex API request is involved. Job manifest: `scratch/pipeline-onboard-data-20261107-165004-606753/jobs.json`. Candidate output remains provisional until source/scope/identity review; jobs do not admit students.

## Explicit appointment starts recovered from cached homepages

Five reviewed starts now carry exact captured quotes and the independent official rank listing: Eyal de Lara (2002), Toniann Pitassi (fall 2001), Thomas Ristenpart (January 2026), Ohad Shamir (August 2026), and Khai Truong (2006). Month/season precision is preserved; no lab foundation or departure date is invented. Every quote and body hash was rechecked against the cached bytes. The automatic scanner's two other suggestions were administrative chair terms (Marsha Chechik, David Fleet); neither was accepted as a faculty start/end interval. This is appointment evidence for five current candidates, not complete historical census coverage.

## Five official-link gaps resolved

Fresh institutional sources establish five additional sites: Gururaj Saileshwar's UTM profile links his research homepage; Alex Mariakakis's official Blue Book profile links the CHAI lab; Schwartz Reisman Institute's community page links Rahul G. Krishnan and Ningning Xie; and Anna Goldenberg's previously captured SickKids profile links her Vector profile, which links Goldenberg Lab. Exact hrefs and all selected-page hashes were checked against cached bytes. The register now contains **76 verified sites, one documented other-institution/on-leave case, and eight pending cases** (12 gate findings because four also require archive work). No students were admitted or extracted.

The new official Blue Book page explicitly lists Mariakakis at St George. Saileshwar's UTM profile explicitly lists Mathematical and Computational Sciences and a Mississauga address; his personal homepage lists Toronto CS with courtesy ECE. This is a further campus eligibility case, not automatic exclusion or St George admission. Preserve campus distinctions until reviewed.

Eight website cases remain: Alán Aspuru-Guzik, Niv Dayan, Bo Wang and Lisa Strug (access/archive work); Daniel Wigdor (default server page); Arvind Gupta, Sam Toueg and Nathan Wiebe (further official-link search). Source and target capture receipts: `scratch/top25-resume-1107/toronto-official-gap-followup.jsonl` and `toronto-gap-homepages.jsonl`. Each new positive entry independently passes the strict website provenance gate; the complete 85-PI register remains incomplete.

## Dated historical sources recovered live

Two official historical PDFs were captured and retained with hashes: the 2016 Faculty Highlights brochure (`https://www.cs.toronto.edu/dcs/documents/Faculty_Highlights_2016.pdf`, SHA-256 `b94509a08d8e1eb9908f29f2b6ad7cb886db932a6c79131e27f7bfeccb3d74f3`) and the 2017–18 SGS Calendar (`https://sgs.calendar.utoronto.ca/sites/default/files/PDFs/SGS_Calendar_2017-18.pdf`, SHA-256 `524d2b6e7ae16a1480fc80e737f0d161b15c365fa9fe2a89a845596c55c8c143`). Both were retrieved November 7; the PDF's historical publication year is separate from the capture date. The brochure's appointment spreads were visually reviewed.

Raquel Urtasun's explicit retrospective statement, “A faculty member since 2014,” supports the sixth reviewed faculty start. The brochure also establishes these historical role/scope leads; none is silently treated as a complete historical census or an exact start date:

| Source page | Evidence | Review consequence |
| --- | --- | --- |
| 2 | Ben Rossman and Aleksandar Nikolov: CS assistant professors, 2015/2016 appointments heading | Historical rank evidence; exact start still needs review. |
| 2 | David Liu and Jacqueline Smith: assistant professors, teaching stream | Preserve teaching classification; no automatic independent-PI admission. |
| 2 | Arvind Gupta: distinguished visiting professor | Preserve visiting classification for this period. |
| 2 | Ashton Anderson: UTSC, starting summer 2017 | Announced future arrival, not an observed 2016 appointment. |
| 3 | David Duvenaud, Roger Grosse, Alec Jacobson and David Levin: CS assistant professors, 2016/2017 appointments heading | Historical rank evidence; no exact start inferred from heading. |
| 3 | Sanja Fidler: UTM assistant professor | Historical campus evidence; review eligibility. |
| 3 | Gennady Pekhimenko (UTSC), Sushant Sachdeva (UTM), Nisarg Shah (CS): starting summer 2017 | Preserve campus and future-announcement distinction. |

The SGS Calendar's printed pages 267–268 list full, emeritus and associate graduate-faculty members. Those membership labels and academic degree suffixes are not faculty ranks. Some glyphs are missing in text extraction, so candidate names need visual correction before census ingestion. This source is held for historical corroboration; it was not fed to the rank parser.

Additional website follow-up: Nathan Wiebe's official Physics profile explicitly says UTSG, non-budgetary cross-appointment, with CS as home department. Its only group link is the broad Quantum Optics category, so it does not close the lab-site gap. Arvind Gupta's department-hosted Vanguard lab lead returned a challenge; the host is stopped and Wayback-only. The register still has eight pending entries, now five with archive work. Raw receipts and PDF extracts are in `scratch/top25-resume-1107/toronto-historical-followup.jsonl` and `toronto-*-2016/2017-18.*`.

The two calendar pages have now been visually reviewed and the missing glyphs corrected in a separate historical lead register: `reports/HISTORICAL-MEMBERS-2017-18.json`. It contains 94 source-bound names: 61 full members, 10 emeritus members and 23 associate members. Each keeps its membership class, source page, original extracted spelling and any visual correction. All remain held for rank, campus scope and identity review; this register is not a census admission input.
