# School-admission process v4: measured baseline and proposed design (R3d, 2026-11-17)

Status: PROPOSAL for the owner. Nothing here changes an owner rule; every change that would is marked **[OWNER RULE]**. The one code
change already landed is listed in section 5. Raw measurements: `scratch/process-v4-1117/` (`stagejobs.psv`, `logstats.json`).

## 1. Method and limits (read first)
Sources: `sacct` for job names `cs-stage*` (the kept history starts 2026-11-03: 106 jobs), `stage-N-gate.json` timestamps, `labpage-audit-discovery.jsonl`
records of 17 schools (4,335 PI records with a timestamp per check), `reviewed/lab-websites.json` of 24 schools, the queue (1,118 tasks), the
coordination log (2,388 lines, 2026-11-10 onward) and questions file (358 blocks), `ONBOARDING-LESSONS.md` (89 + 8 lessons), `scratch/refactor-1117/status.md`
(live gates of 31 charters). Session and question counts are **proxies**: distinct `claude-*`/`codex-*` names and question blocks that mention the school
in the log (a block that names two schools counts for both). Wall-clock "first start to gate pass" exists only where gate files kept a time
(`gatech`, `vt`, `uchicago`, `hkust`, `cambridge`, `toronto`, `purdue`, `utaustin`); a gate file is overwritten by the next run.

## 2. Measured baseline
### 2.1 Headline
| Measure | Value | Where it comes from |
|---|---|---|
| Georgia Tech, stages 0-8 (first protocol-v3 school, one worker) | 26 h (11-03 16:38 -> 11-04 18:42) | gate files |
| Same stages, schools started 11-07 | VT stage 6 on 11-13 (6 d); HKUST gate 9 on 11-16 (9 d); Purdue gate 2 on 11-17 (10 d); Toronto stage 6 still open 11-17 (10 d); Cambridge still stage 1-2 (10 d) | gate files, log |
| Slurm for all `cs-stage*` jobs since 11-03 | 106 jobs, ~17 wall-h, ~35 CPU-h, 8 failed | sacct |
| Slurm for lab-page audit jobs (`lp-audit`, 99 jobs) | ~92 CPU-h, 2 failed | sacct |
| Where the elapsed time goes | agent sessions and owner questions, not Slurm: 17 wall-h of stage jobs against 10-day school timelines | above |
| Live gate state of 31 charters (R0) | first failing stage: s1 11, s2 6, s6 6, s3 4, s10 2, s0 2; open items by stage: s2 2,556 (16 schools), s3 1,509 (20), s5 616 (10), s1 126 (13), s4 87 (6), s6 83 (29) | `status.md` |
| Queue tasks that name a stage | 202 of 1,118; stage 1: 61 tasks / 23 schools; stage 6: 36 tasks, 38 distinct sessions, ~210 task-hours created->done | queue |
| Agent sessions per school (log proxy) | median ~11; ZJU 38, SJTU 38, NTU 37, HKUST 36, CMU 35, Tsinghua 34, Stanford 32, Berkeley 29, MIT 29, Princeton 27; five unstarted schools 0-2 | log |
| Owner-question blocks (proxy, 358 total) | identity/scope/census 94, fetch/robots/host authorization 65, approve a run / more rounds / budget 34, promotion/release/merge 30, waiver/threshold 26, sources/licence 7, other 102 | questions file |
| One-off scripts | 208 tracked `school-one-off` files / 29,211 lines (VT 106, CMU 43, MIT 19, Berkeley 17) + 700 untracked under `hierarchy/<school>/tmp` (Cambridge 311, NTU 187, SJTU 120, Tsinghua 29) | R0 inventory |
| Lessons | 97 (89 + 8): 68 fixed with a test, 15 documented only, 6 open; by stage 0:15, 1:10, 2:9, 6:9, 8:6, 4:5, 7:5, 5:4, 3:3 (+ multi-stage) | lessons file |

### 2.2 Top failure causes (lessons text and live gate items; a lesson can carry two causes)
| Cause | Count |
|---|---|
| Gate / ledger / receipt / review-sample mismatches (a gate demands a fresh draw or receipt; a rebuild invalidates it) | 34 lessons; 5 schools blocked at s6 "build changed since the draw" |
| Scope, identity, name merge, home department | 19 lessons; 94 question blocks; 4 schools failing s3 on "no accepted home department" |
| Wayback / CDX / robots / host policy | 11 lessons; 65 question blocks; 6 schools at s1 "nocapture: no archived 200 capture" |
| Worktree / path / overlay / env / import | 9 lessons |
| Format drift, parsers, paged listings | 8 lessons; 2 schools "paged directory" |
| Slurm limits, memory, `/tmp` | 7 lessons |
| Stale-output logic (a named output exists, so the step "ran") | 5 lessons (L-70, L-90, UC 29, GT 35 ...) and the discovery bug below |

### 2.3 Stage 3 in detail
Steps (`stage_gate.STEPS['3']`) and what each touches:
| Step | Source | Cost measured |
|---|---|---|
| census-refresh, homes, homes-shared | local (census, reviewed files) | seconds; `home_departments_school.py` and `census_build.py` have no network code |
| build (`pi_hierarchy.py`) | local | 1-2 min (UChicago 53 s) |
| labpage-discover | live PI/profile pages (3 s per host) + Wayback (6 s shared slot) + DBLP dump, ORCID, OpenAlex fields (local) | median 1-25 s per PI at schools with a warm capture store; **Purdue 179 s median, 212 s mean** |
| labpage-audit | reads the discovery records and the capture store | 2 h limit; ~1 CPU-h per run; 99 `lp-audit` jobs for ~20 schools = ~5 runs per school |
| pi-basis, `lab_websites.py build/verify`, website review | hand + local | agent time, not measured |

**Where Purdue's 12+ h goes.** Purdue has 369 PIs. The first 15 took 53 min (job 32393491 started 16:17, first record 20:55Z): 212 s per PI, so
**369 PIs need ~21.7 h and the job's 12 h limit ends it after ~200**. Per-check timestamps of the discovery files (Gatech, Stanford, Purdue, 3.9 h of checks) split the time:
Wayback history (`wayback_capture` 3 spread captures + `wayback_cdx` per people/alumni page) = **38-40% + 6-8% = 46%** at the two warm schools;
live candidate-site fetches 22-33%; school-profile fetches 6-10% (48% at Purdue: every profile is a cold fetch). Per PI at Purdue: ~4 Wayback requests (52 `ok_wayback`
checks in 14 PIs) at a 6 s shared slot plus archive latency. The Wayback floor for 369 PIs is ~2.5 h (1,480 requests x 6 s); the other 19 h is request latency,
because one process waits for each answer. The same discovery code finds every website from local or school-page evidence: of 1,493 chosen sites,
`school_profile_link` 813, `dblp_person_url` 270, `pi_evidence_url` 191, `earlier_homepage_find` 121, `orcid_researcher_url` 87, earlier pass 11; **no site came
from a search**. The Wayback history captures serve stage 6 (students over time), not stage-3 website discovery.

**The bug.** `labpage-audit-discovery.jsonl` is append-only, so `step_done` read "file exists" as "step ran". A job cut off at 200 of 369 PIs left a
file that counted as finished; the audit then ran on a partial set. Fixed and landed (section 5).

**Website outcomes** (24 schools with a register, 4,478 labs): real website 2,521 (56%), recorded reason 1,359 (30%), `none` 389, pending-access 101, pending 35, no record 75 (ZJU).
Reasons: `profile_only_no_homepage` 481, `no_web_presence_found` 474, `new_arrival_no_site_yet` 149, `host_blocked_by_robots` 67,
`host_challenge_no_wayback` 42, `site_at_other_institution` 41, `emeritus_or_admin_no_lab` 40. Share of labs ending in a reason: MIT 49%, CMU 39%, Gatech 41%,
Toronto 48%, UChicago 51%, Oxford 60%, NTU 94% (blocked by policy), Tsinghua/ZJU unfinished. A reason costs the same discovery as a site; the 955 reasons for "no homepage" are
negative results the audit cannot improve with more fetching.

**Audit re-runs.** ~5 lab-page audit runs per school (99 `lp-audit` jobs, 20 schools), and the log names the audit 42 times; each rerun follows a rebuild or reviewed-file change, i.e. it is the
"build changed since the draw" loop (5 schools stuck at s6/s7 on it today).

## 3. Design: v4
### 3.1 Principles
1. One command, `atlas school run <key>`, walks a dependency graph; a checkpoint is an artifact plus a content hash, not a gate pass; the run resumes where it stopped.
2. Work is per PI and fail closed per PI: a PI is `done`, `reason` (recorded with its evidence) or `open`. A school is admitted when no PI is `open`; downloads start for every PI that is `done` while others are still open. **[OWNER RULE]** (replaces "stages must pass in order for the whole school").
3. Local first: stored captures, the DBLP dump homepage fields, OpenAlex, ORCID, the evidence store; a network fetch only for what no local source answers, and then through one cache.
4. Decisions live in the evidence store (R1/R3a/R3b: Michigan and Princeton are store-sourced since `266b0dd2`). A run records a decision with its source; a rerun never asks twice.
5. Every judgement uses a standard template and the new correctness rule: exclude with a reason, then a seeded 50-row independent audit (`tools/excluded_audit.py` pattern), the same everywhere a gate needs a human read.

### 3.2 Tracks (merged stages)
```
census (0,1,2) -> PIs+homes (3a) -> windows+identity (4,5) -> catalogue + downloads (7,8)   [critical path: never waits for the tracks below]
                       |-> websites + lab pages (3b)   -> reasons per lab
                       |-> students (6)                -> rosters, rounds
                       |-> accuracy sample (9) on the built package -> release (10)
```
| v3 stage | v4 unit | Change |
|---|---|---|
| 0 charter | `school init` (hosts probe, snapshot, charter template, existing code) | automatic except the charter's human fields |
| 1 listings, 2 census | `census` | one job chain; hosts, captures, rows, DBLP, sweep, candidates are already a Slurm chain (`STEPS`) and become one graph |
| 3 PIs, homes, websites | `pis` (critical path) + `websites` (parallel track) | PI basis and homes block the build; the website audit does not block downloads |
| 4 periods, 5 identity | `windows+identity` | merged; both are per-PI and local-first |
| 6 students | `students` (parallel) | never blocks 7-8; its reviewer rounds use the standard template |
| 7 papers, 8 downloads | `catalogue+downloads` | starts per PI as soon as PI+window+identity are done |
| 9 accuracy, 10 release | `audit+release` | owner-reserved release stays |

### 3.3 What becomes automatic
Hosts probe and `hosts.json`; snapshot extension; stage-1 captures and rows; DBLP/sweep/candidates chain; census refresh, homes, build; website discovery
(already deterministic from local sources); registration of reasons from a fixed vocabulary; completeness checks (section 5); stage-gate readiness reports. Stays human: the charter, a PI's admission when no source decides, identity
namesakes, the 50-row audits, release.

### 3.4 Batched Wayback and one cache
- One sqlite, `<stores>/_shared/wayback-cdx.sqlite`: rows `(urlkey, timestamp, original, digest, status)`, a `prefix_queries` table (`host/path-prefix`, from-year, fetched_at, complete flag), and the 200 captures' hashes. All stages read it (stage 1 listings, 2 units, 3 PIs/labs, 4 periods, 7 papers); today each stage keeps its own capture sqlite and each PI re-queries CDX.
- Per-host CDX prefix queries (`matchType=prefix`, `collapse=urlkey` handled client-side) fetch all captures of a lab host once (e.g. `www.cs.purdue.edu/homes/*` = all 369 PIs' pages in a few paged requests) instead of 369 exact queries. Equivalence test: for a sample of 200 URLs the prefix result equals the exact-URL result, run once per host before the cache is trusted.
- The shared 6 s start-to-start slot (`host_throttle.wait_slot`, 8 s where the rulings say so) stays the only pacing; it is cluster-wide, so **N parallel shards do not break it** and hide latency: discovery becomes ~2.5-3 h at Purdue size instead of 21.7 h.
- Captures needed for history (3 per page) are requested lazily by the `students` track and only for PIs with a real people page.

### 3.5 Local-first sources
Order per PI: reviewed website/evidence rows (store) -> stored captures (any school store, `LOCAL-COPY-MATCHING`) -> DBLP dump `homepage` fields and ORCID researcher URLs (already local files) -> school profile link (one cached fetch per profile) -> only then the live PI page, and Wayback only for history. A PI whose website is already proven by a local source skips the fetch of the other sources: the five sources above found every one of 1,493 sites, so the later ones add checks, not sites. The gate needs a dated "official discovery link" check (`lab_websites.official_check`); the profile-link check provides it, so the skip must still record that check. **[OWNER RULE]** only if the owner wants the other sources' negative checks kept for audit; they do not change which site is chosen.

### 3.6 Config and adapters, not per-person scripts
A source adapter = (host pattern, listing format, extractor, date convention) in `schools/<key>.toml` plus a shared registry in `tools/listing_formats.py`; a per-person fix is a row in the evidence store with its source, never a script. Targets: the 208 tracked one-offs and 700 untracked tmp scripts collapse into adapters or rows. Rule: a script that names a person or a school key outside `schools/` or the store is refused by the lint (`atlas lint` check, allow-list for the existing 208).

### 3.7 Standard reviewers and audit sampling
One reviewer template (`atlas review-page`, input = the draw, output = verdict rows into the store with `reviewed_by`, seed and sample hash) for stages 2, 3 (homes, websites), 5, 6, 9. Audit sampling: 50 rows per measure per school, seed recorded, independent reviewer, fail closed on a stale draw (build hash) and *re-draw only when the build changes*, never per attempt. This is the 11-17 gate-2 rule extended to every stage. **[OWNER RULE]** to extend; the evidence bar per row does not change.

### 3.8 Coordination state (coordinator request)
A worker on 11-17 could not find the log and created a second one. Today: the log is `scratch/top25-goal-1107/OVERNIGHT-LOG.md` (1.1 MB, 2,388 lines, a scratch path), questions in `OVERNIGHT-QUESTIONS.md`, decisions spread over `docs/DECISIONS.md`, memory files and the log, the queue in `leases/queue.jsonl`. Proposal: one directory next to the queue, `leases/coord/`, holding `LOG.md` (append only, one line per event), `QUESTIONS.md` and `DECISIONS.md`; commands `atlas note "..."` (UTC stamp and session added), `atlas ask --school S "..."`, `atlas decide ...` (decision rows go to the evidence store when per-person, else DECISIONS.md); `AGENTS.md` names the paths and the commands (added now, section 5). Until then AGENTS.md names the current files. Expected saving: no duplicate logs, a worker finds the open questions in one place; the per-school owner-question count (358 blocks) is read by `atlas ask --list`.

### 3.9 Docs and lessons
56 docs in `docs/`. Proposed: (a) merge the six reviewed-input docs (`DBLP-ORCID-REVIEWS`, `MEMBER-PAPER-REVIEWS`, `PRIMARY-AUTHOR-REVIEW-LOADER`, `RECOVERY-SOURCE-REVIEWS`, `SOURCE-METADATA-REVIEW`, `SOURCE-TYPE-REVIEWS`) with `REVIEWED-INPUTS.md` into one `REVIEWS.md`, now backed by the store; (b) move the dated one-off notes (`FRANCISCO-IDENTITY-REVIEW-20261108`, `ZJU-STAGE0-REVIEW-20261108`, `RECOVERED-SOURCE-BINDING-20261108`, `RECOVERED-SOURCE-QUALITY-20261108`, `FULL-ELIGIBLE-EDITIONS-20261108`, `STAGE0-COHORT-20261111`) to `archive/docs/`; (c) fold `SCHOOL-CLOSEOUT` and `ADDING-A-SCHOOL` (757 lines) into one `SCHOOL-PROCESS.md` generated from the step graph; (d) `SCRIPT-MAP` (587 lines) generated from `bin/atlas` and the R0 inventory; (e) of 97 lessons keep the 21 documented/open as a one-page checklist and turn the 68 fixed ones into trap checks (`onboarding_traps.py` already holds 11): the ledger becomes test names, not prose.

## 4. Changes, savings and risk
| # | Change | Expected saving (measured basis) | Risk | Owner rule? |
|---|---|---|---|---|
| 1 | Explicit step completion (landed) | Purdue: avoids an audit on ~200 of 369 PIs; a rerun resumes the discovery | none | no |
| 2 | Shard `labpage-discover` (array over PI chunks; shared 6 s slot) | Purdue 21.7 h -> ~3 h; no school above 6 h | low: needs the shared stamp dir on every node | no |
| 3 | Move Wayback history out of discovery (lazy, students track) | 46% of discovery time (Gatech/Stanford) on the stage-3 critical path | low: the audit must find the captures when stage 6 asks | no (stage 3's gate does not read them); changes the stage definition |
| 4 | Shared CDX store + prefix queries | CDX is 6-8% of discovery and ~100% of stage-1/2/4 Wayback lookups; per-PI exact queries become one query per host | medium: prefix/exact equivalence must be tested | no |
| 5 | Parallel tracks, downloads per PI | downloads start after stage 5 instead of 8; today a school's downloads wait on stage 6/7 findings (6 schools show s6 as first failure) although stages 7-8 pass | medium: release bar unchanged, but a PI-level gate replaces a school-level gate | **yes** |
| 6 | `atlas school run`: one graph, checkpoints by hash | removes the repeated "build changed since the draw" reruns (~5 audit runs per school, 5 schools stuck) | medium | no |
| 7 | Reviewer templates + 50-row audits everywhere | fewer fresh rounds: stage 6 used 36 tasks / 38 sessions; one round per build | low | **yes** (extends the 11-17 rule) |
| 8 | Adapters and rows instead of scripts | 208 + 700 scripts; no new per-school script | medium | no |
| 9 | One coordination directory | no duplicate logs; questions countable | low | no (AGENTS.md rule text) |
| 10 | Docs/lessons merge | 56 -> ~35 docs; 97 lessons -> 21 + tests | low | no |

Order: 1 (done), 2+3 (Purdue now), 4, 6, 9, then 5 and 7 after the owner decides. Not saved: the owner-question stream (65 fetch/robots questions) falls only if hosts are decided once at stage 0 by the charter (`host_use`) and the decision is stored; that already exists, enforcement is missing.

## 5. Landed with this proposal
- `0e4f7756` Stage 3: a partial `labpage-audit-discovery.jsonl` no longer counts as a finished step (`tools/discovery_marker.py`, `stage_gate.step_done`, `discover` writes `labpage-audit-discovery.done.json`; tests in `tests/test_stage_gate.py`).
- `AGENTS.md`: section "Coordination log and owner questions" naming the files.
Not landed on purpose: a shared CDX cache. `lpcap` already caches each exact CDX answer per school, CDX is only 6-8% of discovery, and the real saving needs the prefix design of 3.4.

## 6. Owner decisions needed
1. Per-PI fail-closed admission and downloads starting per PI (change 5): approve? Recommend yes, keeping the school-level release gate.
2. Extend the seeded 50-row independent audit and the standard reviewer to stages 3, 5 and 6 (change 7): recommend yes.
3. Move Wayback history captures out of stage-3 discovery into the students track (change 3): recommend yes.
4. Keep the negative checks of later local sources when the first source proves a website (3.5)? Recommend no for stage 3; keep the dated official-link check.
5. Coordination directory `leases/coord/` and the three commands (3.8): recommend yes.
6. Docs/lessons merge (3.9): recommend yes; nothing is deleted without the archive copy.
