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
