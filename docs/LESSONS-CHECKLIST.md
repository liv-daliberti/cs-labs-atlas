# Onboarding lessons: the open checklist and the fixed-lesson test table

Merged 2026-11-17 (process v4 decision 6, owner-approved). The full 97-lesson friction ledger with its prose is `archive/docs/ONBOARDING-LESSONS-full.md`
(unchanged copy; lesson ids L-01..L-97 are stable). Lessons from onboarding Michigan, UChicago and Georgia Tech (merged 2026-11-05 on the owner's request),
Toronto/HKUST/Virginia Tech (2026-11-16) and SJTU (2026-11-16). Run every trap check at once with `atlas stage-gate <key> --traps` (`tools/onboarding_traps.py`);
the process that uses these is `docs/SCHOOL-PROCESS.md`.

## 1. Open and documented-only lessons: read before starting a school (21)

`documented` = a rule or procedure only, no code; `open` = a ROADMAP row (#44, #52-#55) says what is left. Details and school citations: the archived ledger.

| ID | Stage | Status | Lesson | Where the fix or rule lives |
|---|---|---|---|---|
| L-09 | 0 | documented | Pipeline jobs run the COMMITTED HEAD; uncommitted tool edits silently did not run. | protocol "Slurm and snapshots": commit first. `atlas pipeline` does not warn yet: ROADMAP #53 |
| L-15 | 0 | documented+checked | The affiliation regex matched "University of Michigan - Shanghai Jiao Tong Joint Institute" and "at Dearborn"; test it against DBLP notes as well as OpenAlex strings. | `must_match` / `must_not_match` cases are required by `charter_traps` |
| L-17 | any | documented | A session restart loses job ids; two sessions ran the same chain after a coordinator restart; a leftover background command submitted a later stage. | protocol: record job ids in the stage report; one driver per branch; a wait never submits. Leases/checkpoints: ROADMAP #48 (open) |
| L-21 | all | open (workaround fixed) | Reviewed files resolve to the main checkout (ROADMAP #44). `atlas_paths.data()` resolves `hierarchy/<school>/reviewed/...` under `CS_ATLAS_CODE`, so onboarding writers and worktree builds read and write main's copy; main stays ... | `tools/overlay_root.py` builds the overlay code root and is tested; protocol "Reviewed files and the overlay root"; the call-site conversion (`root=HERE`) is ROADMAP ... |
| L-27 | 1 | documented | Parsers silently drop entries without a homepage link, and formats drift inside one site. | assert parsed entries equal the page's markers; compare people per year after every format fix |
| L-37 | 2 | open | Faculty of other universities listed with a title like "Professor; University of North Carolina" became PIs. | reviewed `exclude` with the quoted title; automatic flag (R16): ROADMAP #55 |
| L-42 | 2/7 | documented | Michigan's census review and gap years: courtesy/affiliate rows, DBLP candidates are mostly students, arXiv-heavy theorists fail the share test. | protocol stage 2 notes; `cs_related_school.share_test` |
| L-50 | 4 | documented | Periods written by a tool must use ISO dates (`20261029` reads as unresolved); closed ranges followed by professor rows are rank steps; "(beginning 9/2017)" is a future start (R-PAP-02). | protocol stage 4; `docs/RULES.md` |
| L-52 | 4 | open | `periods_school.py gaps` does not write `unproven_years`/`why_unproven` for a gap it searched and could not close (hand edit of the overrides). | ROADMAP #55 |
| L-53 | 4 | open | A PI appointed "Fall 2026" needs a year-precision period from a live page; no tool writes one. | ROADMAP #55 |
| L-56 | 5 | documented | First-given-name matching admits namesakes ('Jeong M. Park'/'Jeong Joon Park'); a homepage's DBLP pid can be missing from the dump; cross-school PIs must carry the same id in both schools. | protocol stage 5; ROADMAP #49 (identity cross-checks, open) |
| L-61 | 6/7 | open | The acceptance keys on the sha of the additions file, so any regeneration, recover or audit re-run silently un-wires accepted rows (third time at UChicago); `restamp` does not refuse a shrink to 0; the round limit (4 per kind) is ... | commit the additions with the acceptance that stamps them (documented); key on rows, refuse shrink, count rounds: ROADMAP #52 |
| L-67 | 6 | documented | Michigan's no-Deep-Blue rule. A repository that disallows AI agents by name is not used in any form, not through Wayback either, and its holdings reach us only through OpenAlex and CORE. | `[thesis].robots = "disallowed-for-ai-agents"`; ledger `REPO` note |
| L-68 | 6 | documented | Math Genealogy is blocked by robots.txt for this client (offline since 21 October 2026, then disallowed); OpenReview serves a bot challenge; CORE is paused pending a licence; orcid public API is `Disallow: /`. Stop using a host ... | R-STU-16, c2e7567 (CORE off every run list), `school_hosts` gate; the whitelist entry `unavailable_incomplete` while CORE is paused |
| L-74 | 7 | open | A middle stage failing left its afterok dependants pending; `atlas pipeline status` does not name the failed stage's log. `build-audit` should end with link diagnosis and student audit. | ROADMAP #53 |
| L-79 | 8 | documented | A stale hot journal after `scancel`: a SQLite `-journal` next to a catalog means a writer died mid-transaction; do not delete or copy without it. | `docs/RUNBOOK.md` "Locks and journals"; `tools/relocate_data.py --settle-journals` |
| L-84 | all | documented | 2026 sweep gaps: refresh before release. The snapshot and the lab-page captures end before the release date; new hires and 2026 preprints (Qi, Tomlin) need a refresh. | ROADMAP #51 (trickled re-pull); protocol stage 10 "refresh before release" |
| L-85 | 10 | documented | The spot-checks are an early go/no-go (owner 2026-11-05: the 50-row spot-checks are drawn and judged from the freshly built packages right after the rebuild, before freeze, export and site steps). | ROADMAP #47 (open as a release gate); protocol stage 9/10 |
| L-86 | 10 | documented | Release freeze refuses dirty tracked inputs; the onboarding branch's reviewed files must be committed and landed at each gate. | protocol "Running three schools in parallel" |
| L-88 | any | documented | The agent's own scratch work: a blanket decision or a count was taken before looking at rows (UC 62, 66; GT 18 first run flagged every candidate). | protocol rule: read the proposals before `--write`; look at the new rows by PI before counting a jump |
| L-89 | 8 | documented | CORE paused: papers with no cached CORE answer stay `incomplete_check` and the evidence whitelist needs an entry (lower it when CORE resumes). | `docs/evidence-whitelist.json` (`unavailable_incomplete`) |

Open items in ROADMAP: L-21 (reviewed files resolve to main; workaround tool), L-37, L-52, L-53 (#55), L-61 (#52), L-74 (#53); L-09, L-70 and L-87 each name one small open item in #53.

## 2. Fixed lessons and the test that guards each (56)

`cited` = the test is named in the ledger; `matched by identifier` = the test file that references the tool/function the ledger names (2026-11-17 mapping, not a claim that every assertion covers the whole lesson). `onboarding_traps.py` checks are in `tests/test_onboarding_traps.py` for the `fixed+checked` rows.

| ID | Stage | Lesson (short) | Test | Basis |
|---|---|---|---|---|
| L-01 | 0 | A charter made in a worktree was invisible to `atlas charters`, `school_config` and `new-school` (they read ... | `test_atlas_cli.py`, `test_new_school.py` | matched by identifier |
| L-03 | 0 | `new-school` wrote `started` as the UTC date. | `test_new_school.py` | cited |
| L-04 | 0 | The filtered OpenAlex snapshot knows only the charters that existed when it was filtered; the API sweep (10k ... | `test_atlas_pipeline.py` | matched by identifier |
| L-05 | 0/7 | The snapshot filter dropped a school hit when an authorship also held an excluded institution (UChicago + ... | `oa_snapshot::test_exclusion_is_per_affiliation_not_per_authorship` | cited |
| L-06 | 0 | Related vs lineage institutions (medical centres, Argonne, Biohub): read the children and decide ... | `test_oa_institutions.py` | matched by identifier |
| L-07 | 0 | `oa_institutions.py` under `python -I` fails; `search` printed unrelated rows in snapshot order with no "N ... | `test_oa_institutions.py` | matched by identifier |
| L-08 | 0 | `atlas submit` always pinned main's HEAD; a job could not run unlanded onboarding code. | `test_atlas_cli.py` | matched by identifier |
| L-10 | 0 | `stage_gate <key> 0` crashed (`KeyError '0'`): stage 0 had no gate. | `test_stage_gate_stage0.py` | cited |
| L-11 | 0 | Charter authoring is a blank-page job; the affiliation regex, REPO pattern and collector config were found ... | `test_onboarding_traps.py`, `test_new_school.py` | matched by identifier |
| L-13 | 0 | Crawl-delay counted only for `*` and our UA; UChicago Linguistics named ClaudeBot in a `Crawl-delay: 10` ... | `test_school_web_robots.py` | matched by identifier |
| L-14 | 0 | A moved department shows as `http 310`; the old host stayed in unit and listing slots (three Mathematics ... | `test_stage_gate_stage0.py` | cited |
| L-16 | 0 | `tools/slurm_wait.py` had no command line: three "waits" returned at once. | `test_slurm_wait.py` | matched by identifier |
| L-18 | 1 | Finding URL eras by CDX was hundreds of lines per URL; the 2016 homepage's links find the old URLs faster ... | `test_discover_listings.py` | matched by identifier |
| L-19 | 1 | `school_web.py` and every collector stage tool must run under `python -I`; one missed `sys.path` edit killed ... | `test_school_web_isolated.py` | cited |
| L-20 | 1 | `reports/` and `reviewed/` are tracked, but tools write them into main's data tree while commits go on the ... | `test_sync_school_files.py` | matched by identifier |
| L-23 | 1 | The gate failed a year that had a recorded reason. | `test_protocol_rules_michigan.py` | cited |
| L-24 | 1 | Paged directories pass the "5 people" rule while holding one page of several (CS 2017: 5 of ~45; Georgia ... | `test_ustc_stage1_listing.py`, `test_paged_directories.py` | matched by identifier |
| L-28 | 1/6 | Wayback 429 shared clock. `wb.py` kept its own stamp clock beside the shared 5 s clock and 429 cooldown; ... | `test_host_throttle_shared.py` | cited |
| L-31 | 2 | A queued dependency was rewired by another session; no way to see it. Waiting without polling had no tool for ... | `test_atlas_pipeline.py` | matched by identifier |
| L-32 | 2 | A tool added to the `onboard-data` chain read `pis.json` (a stage-7 output) and crashed after 40 minutes; the ... | `test_cs_related_composed_census.py`, `test_cs_related_candidates_census_fallback.py` | matched by identifier |
| L-33 | 2 | OpenAlex candidates decided `not_faculty_listed` because only three units were searched and `units` took one ... | `test_units_done.py`, `test_cs_related_composed_census.py` | matched by identifier |
| L-35 | 2 | A second `candidates` + `review` run replaced 23 additions by 6 and lost 17 accepted people (the candidate ... | `test_cs_related_candidates_census_fallback.py` | cited |
| L-36 | 2/3 | `census_build.py` must re-run after the review (additions get person records only then), after `dblp-ids`, ... | `test_stage_gate.py` | matched by identifier |
| L-38 | 2 | The 'Jr.' suffix merge. The suffix read as the family name, so every 'X Jr.' merged (Isbell absorbed Lever ... | `test_census_suffix_names.py` | cited |
| L-40 | 2 | `pending_openalex` decisions counted as decided in the chain audit; alias forms ('Satinder Singh Baveja'). | `test_cs_related_school.py` | matched by identifier |
| L-41 | 2/7 | Bulk pulls need a sanity gate; ENCODE and PNNL dataset records are non-papers every reader must drop; the ... | `test_sweep_check.py` | matched by identifier |
| L-44 | 3 | Stage-3 step order: `census-refresh` then `homes` then `build` then `labpage-discover` then `labpage-audit`; ... | `test_stage_gate.py`, `test_labpage_sharding.py` | matched by identifier |
| L-45 | 3 | A build older than the reviewed inputs that feed the census (a leftover background command built before the ... | `test_onboarding_freshness.py` | cited |
| L-46 | 3/4 | Home department came from title text ("Starting Fall'26", "KUKA Chair of...") and passed the gate. | `test_home_units_r8.py` | matched by identifier |
| L-47 | 3/5/6 | No papers for 64 of 138 labs: the shared DBLP persons file lacked the school (its writer step was `shared` ... | `test_dblp_dump_persons.py` | matched by identifier |
| L-48 | 3/6/7 | School-local outputs. The audit summary, census overrides and student audit were tracked shared files; an ... | `test_onboarding_traps.py`, `test_labpage_audit_new_school.py` | matched by identifier |
| L-49 | 4 | Homepage fetching shares the Wayback lock; 248 PIs take about 3 hours; the fetch re-queried CDX every run (70 ... | `test_research_plan.py` | matched by identifier |
| L-51 | 4 | Gap years: unit directories miss whole years; truncated-title years; PIs listed in one year with works in ... | `test_periods_work_years.py` | matched by identifier |
| L-54 | 5 | No anchor but no identity either (Dupont, Rogers): the gate knew only anchors. 91 PIs without identity at ... | `test_oa_identity_candidates.py` | matched by identifier |
| L-57 | 5/any | A job died at start: node-local `/tmp` full on one node, and its afterok dependants sat in ... | `test_job_code_snapshot.py` | cited |
| L-58 | 6 | Scripts, inputs and `--output` of a Slurm job in the agent scratchpad are invisible on compute nodes (the ... | `test_census_overrides.py` | matched by identifier |
| L-59 | 6 | Reviewed inputs were git-ignored, so git-archive releases silently lost them (`thesis-evidence`, ... | `test_gitignore_reviewed_inputs.py` | cited |
| L-60 | 6/7 | R13: the lab-page audit un-wired accepted students and papers. Each `audit` run after wiring compared the ... | `test_labpage_moved_in.py`, `test_onboarding_traps.py` | matched by identifier |
| L-64 | 6 | Adviser-bearing student lists (TTIC) had no pipeline place; alumni lists parsed from flattened text ran words ... | `test_census_overrides.py`, `test_new_school.py` | matched by identifier |
| L-66 | 6 | Thesis repositories: allowed by robots yet unreadable at the stated rate (records x crawl delay); ETD ... | `test_etd_crawl.py` | matched by identifier |
| L-69 | 6/7 | Every-lab coverage reasons. 312 of 447 Georgia Tech labs passed stage 6 on the tool's boilerplate `sources_exhausted` reason; the owner rejects `sources_exhausted` without real search effort. Per-lab reasons need that lab's own audit facts. | `test_onboarding_traps.py` | matched by identifier |
| L-70 | 7 | `labpage-recover` needs `labpage-pubs.jsonl.gz`, which no protocol step writes; `build` was "done" once ... | `test_school_closeout.py`, `test_labpage_duplicate_recovery.py` | matched by identifier |
| L-71 | 7 | Link diagnosis ran before the build, wrote an empty file, and was not idempotent; a stale recorded gate was ... | `test_atlas_cli.py`, `test_onboarding_traps.py` | matched by identifier |
| L-72 | 7 | Title resolution used only the API: 1,252 titles waited for credits although the snapshot extension holds ... | `test_snapshot_title_lookup.py` | matched by identifier |
| L-73 | 7 | `link_diagnosis` read the release's `chain-audit.json`, which has no entry for an onboarding school. | `test_link_diagnosis_repeat.py` | matched by identifier |
| L-76 | 8 | The ledger crashed on onboarding schools (no `REPO` and `REPO_PATTERN` entry; uchicago and gatech once fell ... | `test_onboarding_traps.py`, `test_ledger_repo_schools.py` | matched by identifier |
| L-77 | 8 | labpage-captures.sqlite vs labpage-audit-captures.sqlite. The ledger and the `labpages` channel read a file ... | `test_onboarding_traps.py` | matched by identifier |
| L-78 | 8 | Copy collectors without loop_job did not resubmit (`school-collector.slurm` had no `--signal` and no ... | `onboarding_traps::test_every_collector_script_of_the_repository_restarts_itself` | cited |
| L-80 | 8 | The copy target (85%) is a target, not a gate. Georgia Tech: 42.1% with a ceiling of 53.3% under the access ... | `test_stage_gate.py` | matched by identifier |
| L-81 | 9 | Stage-9 draws bind a `copies.json` sha (and the build's file hashes): any rebuild after the draw makes `files ... | `test_stage_gate.py` | matched by identifier |
| L-83 | 3-9 | Stage-gate files go stale. A recorded `stage-<n>-gate.json` outlives the data it judged (UChicago's recorded ... | `test_onboarding_traps.py`, `test_atlas_cli.py` | matched by identifier |
| L-87 | any | A full `bin/atlas test` must pass before the commit, not a subset: tests leave another checkout's tool ... | `test_listed_not_in_census_paths.py` | matched by identifier |
| L-90 |  | Toronto's local-copy counter predates its current package. The stage runner previously skipped ... | `test_onboarding_freshness.py` | matched by identifier |
| L-93 |  | The published interim school workflow intentionally preserves the November 7 reader allowlist. A newly ... | `test_onboarding_doctor.py` | cited |
| L-94 |  | `reader_export.py` emits `stored_copy`, but the website importer retained only link location/basis. Local ... | `test_reader_export.py` | matched by identifier |
| L-95 |  | Repairing only each sampled gap leaves other known sparse rosters for the next review/rebuild cycle. | `test_research_plan.py` | matched by identifier |

## 3. Fixed in the ledger but no guarding test located (20)

The ledger names a commit or a code path, but no test referencing it was found on 2026-11-17. Treat these like section 1 until a test is named; the full text is in the archive.

| ID | Stage | Lesson (short) | Fix named in the ledger |
|---|---|---|---|
| L-02 | 0 | `bin/atlas` run from main's directory imported main's `atlas_cli`, not the worktree's. | c74c5f4 |
| L-12 | 0 | robots.txt alone proves nothing: a Cloudflare challenge sat in front of every umich.edu host but one. | `[web].wayback_only_suffixes`, `school_config.host_use`, probe fetch in `school_hosts.py` |
| L-22 | 1 | `listing_rows.py` crashed on a new school (`listings/<key>/derived/` missing) and chose one format per slot ... | era holding the capture date names the format; fallback to detection (tests) |
| L-25 | 1 | Captures run before the page formats were written left every row `unusable (format None)`; two 35-45 minute ... | step waits for queued steps; `check` command for `captures` (`plan_fetch.py --check`); write formats from one sample ... |
| L-26 | 1 | Wayback `id_` captures can be gzip-encoded (full 230 KB lists looked like script shells); Wayback shells ... | `school_web.body`, `repair_gzip`; shell flag in `units` |
| L-29 | 1 | Truncated titles ("..." loses the word Professor) make a row rank `other`, so span gaps are invisible. | `periods_school.py truncated` (3060144), stage-4 step |
| L-30 | 2 | `RANKS` knew no UChicago/Georgia Tech title words ("Instructional Professor", "Adjoint Professor"): PIs ... | charter `[census].rank_words` (tests) |
| L-34 | 2 | The review's name match was literal: 'Karen M Feigh', 'Toktay, L. Beril' found no evidence. | middle-name/initial forms (test with both cases) |
| L-39 | 5 | A cloned Drupal card ('Clone of Hadi Esmaeilzadeh') was a second PI with its own reviewed id. | `census_build.CLONE_OF` (test) |
| L-43 | 3 | The lab-page audit and its toolkit read hand tables (`labpage_audit.SCHOOLS`, own-institution names, a ... | tables fall back to the charter; toolkit read from the running checkout (tests) |
| L-55 | 5 | An identity anchor must yield papers. A bare DBLP pid passed the gate with 0 papers (identity needs DBLP ... | ROADMAP #43 (ff709b7): `stage_gate.yield_gaps`, release preflight; second OpenAlex pass for DBLP-only PIs |
| L-62 | 6 | The lab-page generic extractor was tuned on seven schools; every new school found new idioms (kinship lists, ... | 8+ rules with tests; protocol: draw a 100-row sample BEFORE round 1 and batch the rule fixes (GT R9). Look at new rows ... |
| L-63 | 6 | Student rosters and ETD: names-only rosters + co-authorship gave false relations in three hand rounds ... | R-STU-02/18 with tests; protocol: pilot a roster rule on 20 rows; per-person decisions with evidence ... |
| L-65 | 6 | Student fill rules. One student under two names (R-STU-13); capture-year dating of undated members ... | `docs/RULES.md`; 2f00c30, eb59b21 (visiting everywhere), 6e1b13e (pairs) |
| L-75 | 7/10 | The zero-paper gate. Zero-paper labs need a recorded reason; the check must run on the REBUILT outputs, and ... | ROADMAP #43; 4870edc (`atlas release` anchor check); `zero_paper_ledger.py` |
| L-82 | 9 | A guest-editor editorial, a poster abstract, a "Closure to ..." reply passed as lab papers (draw 1: 0.84). | R-PAP-31 (`REPLY_COMMENTARY_TITLE`, `SPECIAL_ISSUE_TITLE`) |
| L-91 |  | HKUST's registry still describes native b16 while its current derived package and gate receipts have moved ... | The doctor names its actual package/counter paths, reads canonical `atlas_paths` data, labels recorded gates, and ... |
| L-92 |  | VT's `reports/STAGE-6-7-LABPAGE-HOLD-20261112.md` records organization names, previous-institution news, and ... | Keep the existing general parser tests and fresh-sample/acceptance rules. Fix source-format errors in batches before ... |
| L-96 |  | A new package invalidates a final sample, while unchanged source facts need not be researched again. | Research case IDs bind source bytes, capture year, PI context and policy, excluding student counts and package hashes. ... |
| L-97 |  | Shared sources and repeated receipt checks duplicate I/O, while shared rosters can invite unsupported PI ... | Inspect each cached URL once, reuse exact saved capture pointers without refetching, hash a shared review report once ... |
