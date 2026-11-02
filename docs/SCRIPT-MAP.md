# Script map: the one-school and one-off scripts, and where each went (ROADMAP item 5)

**Status: done 2026-10-31.** The moves are made (`git mv`, history kept); `tests/test_script_map.py` checks this map
against the tree.

Inventory of 2026-10-31 (refactor agent). Scope: every tracked script (`.py`, `.sh`, `.slurm`) under `hierarchy/` except the
build itself (`rebuild.sh`, `rebuild-all.slurm`, `organize-tree.slurm`, `build-equivalence.slurm`, `layout-equivalence.slurm`, `labpage-audit.slurm`), under
`census/`, the per-school listing configs `listings/scripts/config_<school>.py`, the per-school tools `tools/<school>_*.py`, and
the per-school scripts of `fulltext-push/`.

**389 scripts:** 116 deferred, 4 folded, 4 kept, 265 retired.

## How a school is added now

A school is a charter, `schools/<key>.toml`, and the stage tools take the key (`docs/ADDING-A-SCHOOL.md`); `atlas stage-gate <key>`
checks each stage. Nothing in this map is needed for it:
- the one-off research tools of the six pre-protocol schools (gap, few-students, thesis, period, CS-related, home-department, chain
  research) produced reviewed inputs that stay where they are (`hierarchy/<school>/*.json`, `census/`, `periods/`); their code
  is in `archive/` with the same relative path, as a record;
- the pre-protocol census builders (`tools/princeton_census.py`, `berkeley_census.py`, `epfl_census.py`, `epfl_profiles.py`,
  `berkeley_pubs.py`, `census/build_mit_census.py`, `census/tools/build_cmu_*.py`) built census files that are now frozen inputs;
  a protocol school uses `tools/census_build.py <key>`;
- `hierarchy/organize-tree.slurm` defaults to the released charters (`$CS_ATLAS_SCHOOLS`) instead of a list of six;
- the one-school runners became `tools/sweep_school.py <key>`, or are the stage tools run with the key
  (`tools/dblp_recover.py <key>`, `tools/labpage_recover.py run <key>`, `tools/pi_fulltext_affiliation.py works|pdf <key>`).

Also moved with their directory: the four batch lists of `hierarchy/gap-tools-cmu/` (`batch1.txt` .. `batch4.txt`). The
export (`tools/export_release.py`) copies `archive/` into the code record, so the public copy keeps these scripts.

Fates: **folded** (into a config-driven tool, path given), **kept** (data or config, read by live code), **retired** (`git mv`
to `archive/<same path>`: no build, collector or stage tool runs it), **deferred** (another agent owns the file; listed for
them). "Live callers" are what the build, the collectors, the stage tools, the CLI, CI or the tests run, found with `git grep`
by path, by basename and by module import, then checked by hand: every hit not listed was a basename collision.

## `census/ (single files)` (1: 1 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build_mit_census.py` | MIT computer-science faculty census and PI determination, 2016-2026 (step 0 of the four-school build). | none | retired: `archive/census/build_mit_census.py` |

## `census/tools/ (single files)` (3: 3 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build_cmu_census.py` | CMU School of Computer Science faculty census, 2016-2026, with the PI determination (step 0 of the four-school build: | none | retired: `archive/census/tools/build_cmu_census.py` |
| `build_cmu_report.py` | census/cmu-report.md from census/cmu-faculty.json and census/cmu-listing-only.json (tools/build_cmu_census.py). | none | retired: `archive/census/tools/build_cmu_report.py` |
| `fetch_listings.py` | Yearly Wayback captures of CMU SCS faculty listings the sweep lacks, one capture per year 2016-2026 (CDX collapse=timestamp:4, status 200), raw bytes (id_), kept in census/captures-cmu.sqlite with ... | none | retired: `archive/census/tools/fetch_listings.py` |

## `hierarchy/ (single files)` (12: 1 folded, 11 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `period-targets-method.py` | (no docstring) | tools/export_release.py (CODE_RULES: copied into the export as a record) | retired: `archive/hierarchy/period-targets-method.py` |
| `run_dblp_recover.sh` | Recover DBLP-listed lab papers (tools/dblp_recover.py), one school after another (OpenAlex and proceedings hosts see one client). | none | retired: `archive/hierarchy/run_dblp_recover.sh` |
| `run_dblp_recover_followup.sh` | After run_dblp_recover.sh: | none | retired: `archive/hierarchy/run_dblp_recover_followup.sh` |
| `run_dblp_recover_stanford.sh` | DBLP-listed lab-paper recovery for Stanford (tools/dblp_recover.py), 2026-10-27. | none | retired: `archive/hierarchy/run_dblp_recover_stanford.sh` |
| `run_labpage_recover.sh` | Lab-page publication recovery (tools/labpage_recover.py), one school after another; | none | retired: `archive/hierarchy/run_labpage_recover.sh` |
| `run_labpage_recover_stanford.sh` | Lab-page publication recovery for Stanford (tools/labpage_recover.py), 2026-10-27. | none | retired: `archive/hierarchy/run_labpage_recover_stanford.sh` |
| `run_page1.sh` | PI work lists and page-1 affiliation checks (tools/pi_fulltext_affiliation.py), one process per school; | none | retired: `archive/hierarchy/run_page1.sh` |
| `run_page1_all.sh` | Page-1 affiliation checks for every school, one school at a time (work lists, then arXiv v1 page 1); | none | retired: `archive/hierarchy/run_page1_all.sh` |
| `run_page1_pdf.sh` | Page-1 checks only (work lists already fetched), with a chosen number of parallel downloads: | none | retired: `archive/hierarchy/run_page1_pdf.sh` |
| `run_piworks_stanford.slurm` | Stanford PI works by anchored/reviewed OpenAlex id (tools/pi_fulltext_affiliation.py works), needed by the 2026-10-29 unaffiliated-byline rule; | none | retired: `archive/hierarchy/run_piworks_stanford.slurm` |
| `run_stanford_sweep.sh` | Resumable OpenAlex sweep for Stanford in month windows (tools/oa_sweep.py sweep_paged), now with the OpenAlex key from ~/.config/cs-atlas/openalex.env (copied there from soak on 2026-10-27; | none | folded: tools/sweep_school.py stanford; the original is in archive/ |
| `run_sweeps.sh` | OpenAlex school sweeps for the PI hierarchy (2026-10-22); | none | retired: `archive/hierarchy/run_sweeps.sh` |

## `hierarchy/berkeley/cs-related-tools/` (15: 15 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `accepted.py` | Accepted CS-related Berkeley PIs (owner decision 2026-10-22), keyed by candidate index in cs-related-candidates.json. | none | retired: `archive/hierarchy/berkeley/cs-related-tools/accepted.py` |
| `apply.py` | Merge the staged Berkeley CS-related outputs into place (only this review's own keys/rows). | none | retired: `archive/hierarchy/berkeley/cs-related-tools/apply.py` |
| `body.py` | usage: body.py URL NEEDLE [n]: | none | retired: `archive/hierarchy/berkeley/cs-related-tools/body.py` |
| `build.py` | Build the Berkeley CS-related review outputs (owner decision 2026-10-22) from accepted.py / others.py. | none | retired: `archive/hierarchy/berkeley/cs-related-tools/build.py` |
| `copy_offline.py` | Copy the offline evidence (EECS listing captures, EECS dissertation pages, missing-PI review pages) into the store. | none | retired: `archive/hierarchy/berkeley/cs-related-tools/copy_offline.py` |
| `ctx.py` | usage: ctx.py URL-LIKE REGEX [width]: | none | retired: `archive/hierarchy/berkeley/cs-related-tools/ctx.py` |
| `ev.py` | Evidence helpers for the Berkeley CS-related review: | none | retired: `archive/hierarchy/berkeley/cs-related-tools/ev.py` |
| `get.py` | usage: get.py URL... : | none | retired: `archive/hierarchy/berkeley/cs-related-tools/get.py` |
| `index_eecs.py` | Which candidates the captured EECS faculty/emeritus/visiting/teaching lists name, by year; | none | retired: `archive/hierarchy/berkeley/cs-related-tools/index_eecs.py` |
| `lib.py` | (no docstring) | none | retired: `archive/hierarchy/berkeley/cs-related-tools/lib.py` |
| `links.py` | usage: links.py URL REGEX: | none | retired: `archive/hierarchy/berkeley/cs-related-tools/links.py` |
| `match.py` | usage: match.py URL-LIKE [idx...]: | none | retired: `archive/hierarchy/berkeley/cs-related-tools/match.py` |
| `mpcap.py` | Polite fetcher + one SQLite capture store for the Berkeley CS-related scope review (2026-10-22; | none | retired: `archive/hierarchy/berkeley/cs-related-tools/mpcap.py` |
| `others.py` | Non-accepted decisions, keyed by candidate index. | none | retired: `archive/hierarchy/berkeley/cs-related-tools/others.py` |
| `wb.py` | usage: wb.py PAGE_URL YEAR [MONTHFROM]: | none | retired: `archive/hierarchy/berkeley/cs-related-tools/wb.py` |

## `hierarchy/chain-research-20261028/coverage-tools/` (6: 6 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `cap.py` | Polite fetcher + capture store for the 2026-10-28 coverage review. | none | retired: `archive/hierarchy/chain-research-20261028/coverage-tools/cap.py` |
| `dspace.py` | DSpace@MIT REST discover: | none | retired: `archive/hierarchy/chain-research-20261028/coverage-tools/dspace.py` |
| `lib.py` | Helpers for the 2026-10-28 coverage review: | none | retired: `archive/hierarchy/chain-research-20261028/coverage-tools/lib.py` |
| `oa.py` | OpenAlex author lookup (key read from ~/.config/cs-atlas/openalex.env, never printed or stored; | none | retired: `archive/hierarchy/chain-research-20261028/coverage-tools/oa.py` |
| `review.py` | Decision store for the coverage review. | none | retired: `archive/hierarchy/chain-research-20261028/coverage-tools/review.py` |
| `wbprof.py` | (no docstring) | none | retired: `archive/hierarchy/chain-research-20261028/coverage-tools/wbprof.py` |

## `hierarchy/chain-research-20261028/newpi-tools/` (8: 8 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build_newpi.py` | Builds ../newpi-review.json from captures.sqlite (every quote verified by evid.ev). | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/build_newpi.py` |
| `build_stanford.py` | Builds ../stanford-pi-check.json (every quote verified by evid.ev). | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/build_stanford.py` |
| `cap.py` | Polite fetcher + capture store for the 2026-10-28 coverage review. | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/cap.py` |
| `evid.py` | Evidence helper: every quote is verified verbatim against the stored capture text before it is written. | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/evid.py` |
| `lib.py` | Helpers for the 2026-10-28 coverage review: | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/lib.py` |
| `oa.py` | OpenAlex author lookup (key read from ~/.config/cs-atlas/openalex.env, never printed or stored; | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/oa.py` |
| `oa2.py` | Author inspection helpers on top of oa.get (cached in captures.sqlite). | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/oa2.py` |
| `wbprof.py` | (no docstring) | none | retired: `archive/hierarchy/chain-research-20261028/newpi-tools/wbprof.py` |

## `hierarchy/chain-research-20261028/pi-basis-tools/` (6: 6 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build_review.py` | Assemble pi-basis-review.json from captures.sqlite (this directory). | none | retired: `archive/hierarchy/chain-research-20261028/pi-basis-tools/build_review.py` |
| `cap.py` | Polite fetcher + capture store for the 2026-10-28 pi-basis review. | none | retired: `archive/hierarchy/chain-research-20261028/pi-basis-tools/cap.py` |
| `dspace.py` | DSpace@MIT REST discover: | none | retired: `archive/hierarchy/chain-research-20261028/pi-basis-tools/dspace.py` |
| `mit_dspace_all.py` | For each MIT input person: | none | retired: `archive/hierarchy/chain-research-20261028/pi-basis-tools/mit_dspace_all.py` |
| `verify.py` | Re-check every quote in pi-basis-review.json: | none | retired: `archive/hierarchy/chain-research-20261028/pi-basis-tools/verify.py` |
| `wbprof.py` | (no docstring) | none | retired: `archive/hierarchy/chain-research-20261028/pi-basis-tools/wbprof.py` |

## `hierarchy/chain-research-20261028/same-name-tools/` (4: 4 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `add.py` | Add/replace one pair's verdict in same-name-review.json (whole file rewritten each time). | none | retired: `archive/hierarchy/chain-research-20261028/same-name-tools/add.py` |
| `cap.py` | Polite fetcher + capture store for the 2026-10-28 same-name-within-lab review. | none | retired: `archive/hierarchy/chain-research-20261028/same-name-tools/cap.py` |
| `oa.py` | (no docstring) | none | retired: `archive/hierarchy/chain-research-20261028/same-name-tools/oa.py` |
| `raw.py` | (no docstring) | none | retired: `archive/hierarchy/chain-research-20261028/same-name-tools/raw.py` |

## `hierarchy/cmu/cs-related-tools/` (7: 7 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build.py` | Build the CMU CS-related scope outputs (owner decision 2026-10-22) into a staging directory: | none | retired: `archive/hierarchy/cmu/cs-related-tools/build.py` |
| `commit.py` | Write the staged CMU CS-related outputs: | none | retired: `archive/hierarchy/cmu/cs-related-tools/commit.py` |
| `decisions.py` | CMU CS-related scope review (owner decision 2026-10-22): | none | retired: `archive/hierarchy/cmu/cs-related-tools/decisions.py` |
| `fetch_show.py` | Fetch URLs politely into hierarchy/cmu/cs-related-captures.sqlite (via cs-related-tools/csrcap.py) and print, per page, the status and short text windows around appointment/advising keywords. | none | retired: `archive/hierarchy/cmu/cs-related-tools/fetch_show.py` |
| `theses.py` | CMU thesis records (hierarchy/thesis-tools/records.py over hierarchy/cmu/thesis-captures.sqlite), without the quote closures, as JSON; | none | retired: `archive/hierarchy/cmu/cs-related-tools/theses.py` |
| `verify.py` | Check that every {url, sha256, quote} in the staged (or written) CMU CS-related outputs is an exact substring of the text of a stored capture in hierarchy/cmu/cs-related-captures.sqlite with that u... | none | retired: `archive/hierarchy/cmu/cs-related-tools/verify.py` |
| `wb.py` | Wayback captures without the CDX API (which is throttled from this host): | none | retired: `archive/hierarchy/cmu/cs-related-tools/wb.py` |

## `hierarchy/cs-related-tools/` (30: 30 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `author_index.py` | Per-author index of one school's OpenAlex sweep (2016-2026), for the CS-related scope review (owner decision 2026-10-22). | none | retired: `archive/hierarchy/cs-related-tools/author_index.py` |
| `cscap.py` | Capture store of the CS-related scope review (owner decision 2026-10-22): | none | retired: `archive/hierarchy/cs-related-tools/cscap.py` |
| `csrcap.py` | Polite fetcher + one SQLite capture store for the CS-related scope review (2026-10-22; | none | retired: `archive/hierarchy/cs-related-tools/csrcap.py` |
| `epfl_copy_lists.py` | EPFL: copy the school/institute faculty-list captures of the listings sweep (listings/epfl/captures.sqlite) into hierarchy/cs-related-captures-epfl.sqlite unchanged (fetched_at, sha256, bytes; | none | retired: `archive/hierarchy/cs-related-tools/epfl_copy_lists.py` |
| `epfl_identity.py` | EPFL: identity check of candidate OpenAlex author ids against their own works. | none | retired: `archive/hierarchy/cs-related-tools/epfl_identity.py` |
| `epfl_listtext.py` | EPFL: the faculty-list captures of hierarchy/cs-related-captures-epfl.sqlite as (url, school, year, text, normalized text), and name presence/quotes on them. | none | retired: `archive/hierarchy/cs-related-tools/epfl_listtext.py` |
| `epfl_people.py` | EPFL CS-related scope review (owner decision 2026-10-22): | none | retired: `archive/hierarchy/cs-related-tools/epfl_people.py` |
| `epfl_profiles.py` | EPFL: fetch live people.epfl.ch profiles (?lang=en) of the CS-related review's candidates into the review store. | none | retired: `archive/hierarchy/cs-related-tools/epfl_profiles.py` |
| `evidence.py` | Evidence helpers for the CS-related review: | none | retired: `archive/hierarchy/cs-related-tools/evidence.py` |
| `helpers.py` | Shared helpers of the CS-related scope review: | none | retired: `archive/hierarchy/cs-related-tools/helpers.py` |
| `listing_rows.py` | Yearly listing rows for the CS-related additions (2026-10-22), built with the listings pipeline's own extractor and matcher (listings/scripts: | none | retired: `archive/hierarchy/cs-related-tools/listing_rows.py` |
| `pe_epfl.py` | EPFL CS-related scope review (owner decision 2026-10-22) over hierarchy/epfl/cs-related-candidates.json (DBLP-based list). | none | retired: `archive/hierarchy/cs-related-tools/pe_epfl.py` |
| `pe_index.py` | Princeton + EPFL CS-related review (DBLP-based candidate lists): | none | retired: `archive/hierarchy/cs-related-tools/pe_index.py` |
| `pe_merge.py` | Merge the Princeton supplement and the EPFL review (pe_princeton.py, pe_epfl.py outputs in <work>) into the shared files. | none | retired: `archive/hierarchy/cs-related-tools/pe_merge.py` |
| `pe_princeton.py` | Princeton CS-related scope review, supplement (2026-10-26): | none | retired: `archive/hierarchy/cs-related-tools/pe_princeton.py` |
| `pecap.py` | Princeton + EPFL CS-related scope review (owner decision 2026-10-22; | none | retired: `archive/hierarchy/cs-related-tools/pecap.py` |
| `people.py` | People under review for the CS-related scope (owner decision 2026-10-22), CMU, DBLP-based candidate list (hierarchy/cmu/cs-related-candidates.json, 318 candidates). | none | retired: `archive/hierarchy/cs-related-tools/people.py` |
| `plan.py` | Plan of department listing captures used for yearly rows (table plan_csr in hierarchy/cmu/cs-related-captures.sqlite). | none | retired: `archive/hierarchy/cs-related-tools/plan.py` |
| `princeton_build.py` | Build the Princeton outputs of the CS-related scope review (owner decision 2026-10-22) from princeton_decisions.py: | none | retired: `archive/hierarchy/cs-related-tools/princeton_build.py` |
| `princeton_decisions.py` | Reviewed decisions of the Princeton CS-related scope review (2026-10-22); | none | retired: `archive/hierarchy/cs-related-tools/princeton_decisions.py` |
| `princeton_evidence.py` | Evidence per triage row: | none | retired: `archive/hierarchy/cs-related-tools/princeton_evidence.py` |
| `princeton_gather.py` | For each Princeton qualifier, every stored department-list capture (listings sweep store, and this review's store for pages it fetched) that names them: | none | retired: `archive/hierarchy/cs-related-tools/princeton_gather.py` |
| `princeton_lib.py` | Princeton helpers for the CS-related review: | none | retired: `archive/hierarchy/cs-related-tools/princeton_lib.py` |
| `princeton_listing_entries.py` | Every (name, title) entry on the stored Princeton department faculty-list captures outside Computer Science (claude-princeton-listings-20261022/captures/listings.sqlite, plus captures this review f... | none | retired: `archive/hierarchy/cs-related-tools/princeton_listing_entries.py` |
| `princeton_phd_advisers.py` | Princeton PhD (and master's) advising 2016-2025 from the DataSpace OAI dissertation records already harvested into hierarchy/princeton/thesis-captures.sqlite (hierarchy/thesis-tools/records.py), ev... | none | retired: `archive/hierarchy/cs-related-tools/princeton_phd_advisers.py` |
| `princeton_scan.py` | Department-list scan: | none | retired: `archive/hierarchy/cs-related-tools/princeton_scan.py` |
| `princeton_thesis_index.py` | All Princeton DataSpace thesis records 2016-2025 (senior, master's, PhD) from hierarchy/princeton/thesis-captures.sqlite as adviser rows and author rows, each with its quote (exact substring of the... | none | retired: `archive/hierarchy/cs-related-tools/princeton_thesis_index.py` |
| `princeton_triage.py` | Triage table for the Princeton CS-related review: | none | retired: `archive/hierarchy/cs-related-tools/princeton_triage.py` |
| `review_decisions.py` | Reviewed decisions for every candidate of the CS-related scope (2026-10-22). | none | retired: `archive/hierarchy/cs-related-tools/review_decisions.py` |
| `universe.py` | The candidate universe of the CS-related scope review, per school: | none | retired: `archive/hierarchy/cs-related-tools/universe.py` |

## `hierarchy/few-students-tools-20261028/` (5: 5 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build_entries.py` | Build few-students evidence entries (2026-10-28) from profile_scan.json (Stanford profiles + Wayback) and the Berkeley captures in captures.sqlite. | none | retired: `archive/hierarchy/few-students-tools-20261028/build_entries.py` |
| `cap.py` | Polite fetcher + capture store for the 2026-10-28 few-students / zero-paper investigation. | none | retired: `archive/hierarchy/few-students-tools-20261028/cap.py` |
| `merge.py` | Write the 2026-10-28 few-students / zero-paper results into the hierarchy files (backups first, merge, never overwrite). | none | retired: `archive/hierarchy/few-students-tools-20261028/merge.py` |
| `scan_profiles.py` | Scan every distinct Wayback capture (2015-2026) plus the live page of each Stanford profile; | none | retired: `archive/hierarchy/few-students-tools-20261028/scan_profiles.py` |
| `wbprof.py` | (no docstring) | none | retired: `archive/hierarchy/few-students-tools-20261028/wbprof.py` |

## `hierarchy/few-students-tools-cmu/` (25: 25 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `a_kilthub.py` | Worker A helper: search KiltHub theses for a name (item_type 8) and/or fetch article JSONs; | none | retired: `archive/hierarchy/few-students-tools-cmu/a_kilthub.py` |
| `a_retry_wb.py` | Worker A: fetch a few Wayback captures with polite backoff (the archive is refusing connections intermittently). | none | retired: `archive/hierarchy/few-students-tools-cmu/a_retry_wb.py` |
| `b_fs.py` | KiltHub thesis search via the figshare API (item_type 8 = thesis). | none | retired: `archive/hierarchy/few-students-tools-cmu/b_fs.py` |
| `b_fsart.py` | Fetch figshare article JSON(s) and print author, date, degree, department, advisors. | none | retired: `archive/hierarchy/few-students-tools-cmu/b_fsart.py` |
| `b_links.py` | Print hrefs from a cached capture whose anchor text matches REGEX. | none | retired: `archive/hierarchy/few-students-tools-cmu/b_links.py` |
| `build.py` | Build hierarchy/cmu/few-students-evidence.json from decisions_*.py + few-students-captures.sqlite, then re-verify every quote against the stored bytes (sha256 + exact substring + url/capture_url ma... | none | retired: `archive/hierarchy/few-students-tools-cmu/build.py` |
| `c_fs.py` | Worker C: KiltHub (figshare API) thesis lookup. | none | retired: `archive/hierarchy/few-students-tools-cmu/c_fs.py` |
| `c_wb.py` | Worker C: Wayback helper with polite back-off on refused connections (archive.org throttling). | none | retired: `archive/hierarchy/few-students-tools-cmu/c_wb.py` |
| `c_wbbatch.py` | Worker C: run a list of Wayback lookups sequentially with back-off; | none | retired: `archive/hierarchy/few-students-tools-cmu/c_wbbatch.py` |
| `capstore.py` | Polite fetcher + SQLite capture store for the CMU few-students investigation (adapted from gap-tools-cmu). | none | retired: `archive/hierarchy/few-students-tools-cmu/capstore.py` |
| `d_cdx.py` | List Wayback URLs under a prefix (one row per urlkey, status 200), optionally filtered by regex. | none | retired: `archive/hierarchy/few-students-tools-cmu/d_cdx.py` |
| `d_kart.py` | Fetch KiltHub article JSONs by id and print author, date, department, degree, Advisor(s), title. | none | retired: `archive/hierarchy/few-students-tools-cmu/d_kart.py` |
| `d_kilt.py` | KiltHub (figshare API) thesis search: | none | retired: `archive/hierarchy/few-students-tools-cmu/d_kilt.py` |
| `d_ri.py` | RI site search via the WordPress REST search endpoint (robots-allowed), all pages. | none | retired: `archive/hierarchy/few-students-tools-cmu/d_ri.py` |
| `decisions_a.py` | Worker A decisions (CMU few-students investigation, 2026-10-22): | none | retired: `archive/hierarchy/few-students-tools-cmu/decisions_a.py` |
| `decisions_b.py` | Worker B decisions (CMU few-students investigation, 2026-10-21/22): | none | retired: `archive/hierarchy/few-students-tools-cmu/decisions_b.py` |
| `decisions_c.py` | Worker C decisions (CMU few-students investigation): | none | retired: `archive/hierarchy/few-students-tools-cmu/decisions_c.py` |
| `decisions_d.py` | Worker D decisions (CMU few-students investigation): | none | retired: `archive/hierarchy/few-students-tools-cmu/decisions_d.py` |
| `dhelp.py` | Spec helpers for decisions_*.py (CMU few-students investigation). | none | retired: `archive/hierarchy/few-students-tools-cmu/dhelp.py` |
| `f.py` | Fetch URLs into the gap capture DB and print text windows. | none | retired: `archive/hierarchy/few-students-tools-cmu/f.py` |
| `figshare.py` | Search CMU KiltHub (figshare institution) theses: | none | retired: `archive/hierarchy/few-students-tools-cmu/figshare.py` |
| `harvest_theses.py` | Harvest SCS thesis abstracts (2016-2026) from reports-archive.adm.cs.cmu.edu and index their thesis committees. | none | retired: `archive/hierarchy/few-students-tools-cmu/harvest_theses.py` |
| `insp.py` | Print text windows of the latest 200 capture of URL (live url or Wayback capture_url) around REGEX. | none | retired: `archive/hierarchy/few-students-tools-cmu/insp.py` |
| `theses.py` | Query theses_index.json (built by harvest_theses.py from reports-archive.adm.cs.cmu.edu, 2016-2026). | none | retired: `archive/hierarchy/few-students-tools-cmu/theses.py` |
| `wbscan.py` | Fetch one Wayback id_ capture per year (distinct digests, status 200) of URL and print grep windows. | none | retired: `archive/hierarchy/few-students-tools-cmu/wbscan.py` |

## `hierarchy/few-students-tools/` (18: 18 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build.py` | Build hierarchy/<school>/few-students-evidence.json from decisions_<school>.py. | none | retired: `archive/hierarchy/few-students-tools/build.py` |
| `decisions_berkeley.py` | Berkeley few-students decisions (25 PIs), 2026-10-21/22. | none | retired: `archive/hierarchy/few-students-tools/decisions_berkeley.py` |
| `decisions_epfl.py` | EPFL few-students decisions (2026-10-22): | none | retired: `archive/hierarchy/few-students-tools/decisions_epfl.py` |
| `decisions_mit.py` | MIT few-students decisions (17 PIs), 2026-10-22. | none | retired: `archive/hierarchy/few-students-tools/decisions_mit.py` |
| `decisions_princeton.py` | Princeton few-students decisions (13 PIs), 2026-10-22. | none | retired: `archive/hierarchy/few-students-tools/decisions_princeton.py` |
| `dspace_mit.py` | DSpace@MIT discover searches by thesis supervisor (dc.contributor.advisor), 2016-2026, for the few-students MIT PIs. | none | retired: `archive/hierarchy/few-students-tools/dspace_mit.py` |
| `f.py` | Fetch URLs into a school's few-students capture store and print text windows. | none | retired: `archive/hierarchy/few-students-tools/f.py` |
| `fscap.py` | Polite fetcher + per-school SQLite capture store for the few-students lab investigation (2026-10-21/22). | none | retired: `archive/hierarchy/few-students-tools/fscap.py` |
| `fsev.py` | Evidence helpers for the few-students decision modules (decisions_<school>.py). | none | retired: `archive/hierarchy/few-students-tools/fsev.py` |
| `harvest_princeton.py` | Harvest DataSpace OAI-PMH sets (ListRecords, metadataPrefix=dim) for the Princeton few-students PIs. | none | retired: `archive/hierarchy/few-students-tools/harvest_princeton.py` |
| `infosci_epfl.py` | Infoscience (EPFL DSpace-CRIS REST) thesis search by advisor, stored in hierarchy/epfl/few-students-captures.sqlite. | none | retired: `archive/hierarchy/few-students-tools/infosci_epfl.py` |
| `merge.py` | Copy every row of a worker-local capture DB (FSCAP_LOCAL) into the school's few-students-captures.sqlite. | none | retired: `archive/hierarchy/few-students-tools/merge.py` |
| `seed_berkeley.py` | Berkeley few-students seed: | none | retired: `archive/hierarchy/few-students-tools/seed_berkeley.py` |
| `show_princeton.py` | Print the whitespace-collapsed text of stored Princeton captures (read-only): | none | retired: `archive/hierarchy/few-students-tools/show_princeton.py` |
| `techrpts_berkeley.py` | Berkeley EECS technical reports by faculty: | none | retired: `archive/hierarchy/few-students-tools/techrpts_berkeley.py` |
| `verify.py` | Independent re-verification of hierarchy/<school>/few-students-evidence.json against the school's capture store. | none | retired: `archive/hierarchy/few-students-tools/verify.py` |
| `wb_mit.py` | Fetch Wayback id_ captures for the MIT few-students PIs: | none | retired: `archive/hierarchy/few-students-tools/wb_mit.py` |
| `wbhist_berkeley.py` | Fetch one Wayback id_ capture per year (the last capture of each listed year) of a URL, and grep it. | none | retired: `archive/hierarchy/few-students-tools/wbhist_berkeley.py` |

## `hierarchy/gap-tools-berkeley/` (17: 17 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build.py` | Build hierarchy/berkeley/gap-evidence.json from the decisions_*.py modules + the gap capture DB, then re-verify every quote against the stored bytes it cites (by sha256). | none | retired: `archive/hierarchy/gap-tools-berkeley/build.py` |
| `candidates.py` | Scan the Berkeley OpenAlex sweep (read-only) for authorships whose name matches a gap PI and collect the candidate OpenAlex author ids, observed ORCIDs, raw names and sample works. | none | retired: `archive/hierarchy/gap-tools-berkeley/candidates.py` |
| `capstore.py` | Polite fetcher + SQLite capture store for the UC Berkeley EECS PI gap investigation. | none | retired: `archive/hierarchy/gap-tools-berkeley/capstore.py` |
| `decisions_departed.py` | Berkeley gap decisions, worker 'departed' (2026-10-21/22): | none | retired: `archive/hierarchy/gap-tools-berkeley/decisions_departed.py` |
| `decisions_emeriti_a.py` | Berkeley gap decisions, worker emeriti_a (2026-10-21/22): | none | retired: `archive/hierarchy/gap-tools-berkeley/decisions_emeriti_a.py` |
| `decisions_emeriti_b.py` | Berkeley gap decisions, worker emeriti_b (2026-10-21/22): | none | retired: `archive/hierarchy/gap-tools-berkeley/decisions_emeriti_b.py` |
| `decisions_ladder_a.py` | Berkeley gap decisions, worker ladder_a (11 active ladder PIs), 2026-10-21/22. | none | retired: `archive/hierarchy/gap-tools-berkeley/decisions_ladder_a.py` |
| `decisions_ladder_b.py` | Berkeley gap decisions, worker ladder_b (11 recently hired ladder PIs), 2026-10-21/22. | none | retired: `archive/hierarchy/gap-tools-berkeley/decisions_ladder_b.py` |
| `dhelp.py` | Shared helpers for the Berkeley gap decision modules (decisions_*.py). | none | retired: `archive/hierarchy/gap-tools-berkeley/dhelp.py` |
| `f.py` | Fetch URLs into the gap capture DB and print text windows. | none | retired: `archive/hierarchy/gap-tools-berkeley/f.py` |
| `merge_workers.py` | Single-writer merge of the per-worker local capture DBs into hierarchy/berkeley/gap-captures.sqlite. | none | retired: `archive/hierarchy/gap-tools-berkeley/merge_workers.py` |
| `oa.py` | OpenAlex helper (1 req/s; | none | retired: `archive/hierarchy/gap-tools-berkeley/oa.py` |
| `orcid.py` | ORCID record via the orcid.org web-app JSON (pub.orcid.org's robots.txt disallows all; | none | retired: `archive/hierarchy/gap-tools-berkeley/orcid.py` |
| `qa.py` | Independent QA of hierarchy/berkeley/gap-evidence.json against the main capture DB (not the worker DBs). | none | retired: `archive/hierarchy/gap-tools-berkeley/qa.py` |
| `seed.py` | Seed pass: for every gap PI fetch the EECS faculty profile and the EECS dissertations-by-faculty page (live, else newest Wayback id_ capture), and extract the personal-homepage links and dissertati... | none | retired: `archive/hierarchy/gap-tools-berkeley/seed.py` |
| `verify_oa.py` | Check an OpenAlex author's 2016+ works against a stored publication list (PI homepage / CV / lab page). | none | retired: `archive/hierarchy/gap-tools-berkeley/verify_oa.py` |
| `wbscan.py` | Fetch one Wayback id_ capture per year (distinct digests, status 200) of URL and print grep windows. | none | retired: `archive/hierarchy/gap-tools-berkeley/wbscan.py` |

## `hierarchy/gap-tools-cmu/` (17: 17 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `append_newpis.py` | Append rows for the PIs in decisions_newpis.py to hierarchy/cmu/gap-evidence.json, leaving every existing row unchanged, then re-verify every quote of the new rows against the stored bytes (sha256 ... | none | retired: `archive/hierarchy/gap-tools-cmu/append_newpis.py` |
| `build.py` | Build hierarchy/cmu/gap-evidence.json from decisions.py + the gap capture DB, then re-verify every quote. | none | retired: `archive/hierarchy/gap-tools-cmu/build.py` |
| `capstore.py` | Polite fetcher + SQLite capture store for the CMU PI gap investigation. | none | retired: `archive/hierarchy/gap-tools-cmu/capstore.py` |
| `dblp.py` | DBLP helper: author search API and pid XML (one request per 5 s; | none | retired: `archive/hierarchy/gap-tools-cmu/dblp.py` |
| `decisions.py` | Per-PI decisions for the CMU gap investigation (33 PIs, 2026-10-21/22). | none | retired: `archive/hierarchy/gap-tools-cmu/decisions.py` |
| `decisions_newpis.py` | Decisions for the two CMU PIs added after the yearly-listing completeness check (2026-10-22): | none | retired: `archive/hierarchy/gap-tools-cmu/decisions_newpis.py` |
| `f.py` | Fetch URLs into the gap capture DB and print text windows. | none | retired: `archive/hierarchy/gap-tools-cmu/f.py` |
| `figshare.py` | Search CMU KiltHub (figshare institution) theses: | none | retired: `archive/hierarchy/gap-tools-cmu/figshare.py` |
| `insp.py` | Print text windows of the latest 200 capture of URL (live url or Wayback capture_url) around REGEX. | none | retired: `archive/hierarchy/gap-tools-cmu/insp.py` |
| `kilt_newpis.py` | (copy of few-students-tools-cmu/d_kilt.py writing to the gap capture store; | none | retired: `archive/hierarchy/gap-tools-cmu/kilt_newpis.py` |
| `oa.py` | OpenAlex helper (1 req/s; | none | retired: `archive/hierarchy/gap-tools-cmu/oa.py` |
| `oaworks.sh` | (no docstring) | none | retired: `archive/hierarchy/gap-tools-cmu/oaworks.sh` |
| `orcid.py` | ORCID record via the orcid.org web-app JSON (pub.orcid.org's robots.txt disallows all; | none | retired: `archive/hierarchy/gap-tools-cmu/orcid.py` |
| `reverify.py` | Independent re-verification of gap-evidence.json: | none | retired: `archive/hierarchy/gap-tools-cmu/reverify.py` |
| `verify_batch.sh` | (no docstring) | none | retired: `archive/hierarchy/gap-tools-cmu/verify_batch.sh` |
| `verify_oa.py` | Check an OpenAlex author's 2016+ works against a stored publication list (PI homepage / CV / lab page). | none | retired: `archive/hierarchy/gap-tools-cmu/verify_oa.py` |
| `wbscan.py` | Fetch one Wayback id_ capture per year (distinct digests, status 200) of URL and print grep windows. | none | retired: `archive/hierarchy/gap-tools-cmu/wbscan.py` |

## `hierarchy/gap-tools-mit/` (20: 20 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `append_newpis.py` | Append rows for the PIs in spec_newpis.py to hierarchy/mit/gap-evidence.json, leaving every existing row unchanged, then re-verify the whole file with verify_gap_evidence.verify plus a strict per-q... | none | retired: `archive/hierarchy/gap-tools-mit/append_newpis.py` |
| `build_gap_evidence.py` | Build hierarchy/mit/gap-evidence.json (one row per gap-input PI) from spec_mit.py, then re-verify every quote. | none | retired: `archive/hierarchy/gap-tools-mit/build_gap_evidence.py` |
| `capstore.py` | Polite fetcher + SQLite capture store for the MIT gap-lab investigation (hierarchy/mit/gap-captures.sqlite). | none | retired: `archive/hierarchy/gap-tools-mit/capstore.py` |
| `dblp_wb.py` | Fetch the newest Wayback id_ capture of DBLP person pages (dblp.org HTML is bot-walled live) and summarize. | none | retired: `archive/hierarchy/gap-tools-mit/dblp_wb.py` |
| `dspace_round2.sh` | Round 2 of DSpace supervisor searches, started after round 1 exits (one DSpace client at a time). | none | retired: `archive/hierarchy/gap-tools-mit/dspace_round2.sh` |
| `dspace_search.py` | DSpace@MIT discover searches by thesis supervisor (dc.contributor.advisor), 2016-2026, stored in gap-captures.sqlite. | none | retired: `archive/hierarchy/gap-tools-mit/dspace_search.py` |
| `evlib.py` | Helpers that turn researched facts into evidence rows whose quotes are exact substrings of stored captures. | none | retired: `archive/hierarchy/gap-tools-mit/evlib.py` |
| `grep_cap.py` | Print windows of the stored capture of URL (live or capture_url) around REGEX. | none | retired: `archive/hierarchy/gap-tools-mit/grep_cap.py` |
| `links.py` | Print hrefs (absolute) + anchor text of the latest stored capture of URL, filtered by regex. | none | retired: `archive/hierarchy/gap-tools-mit/links.py` |
| `look.py` | Fetch URLs (round-robin across hosts, cached in gap-captures.sqlite) and print text windows around a regex. | none | retired: `archive/hierarchy/gap-tools-mit/look.py` |
| `oa.py` | OpenAlex API helper (1 request/s, key from $OPENALEX_API_KEY, never logged: | none | retired: `archive/hierarchy/gap-tools-mit/oa.py` |
| `scan_collection.py` | Scan the MIT collection (read-only) for advising contexts whose adviser text mentions a gap PI's surname. | none | retired: `archive/hierarchy/gap-tools-mit/scan_collection.py` |
| `scan_repo.py` | Candidate theses from the Codex DSpace snapshot (read-only): | none | retired: `archive/hierarchy/gap-tools-mit/scan_repo.py` |
| `show_hits.py` | (no docstring) | none | retired: `archive/hierarchy/gap-tools-mit/show_hits.py` |
| `spec_mit.py` | Researched facts for the 31 MIT gap labs (2026-10-22). | none | retired: `archive/hierarchy/gap-tools-mit/spec_mit.py` |
| `spec_newpis.py` | Researched facts for the four MIT EECS (AI+D) PIs added after the yearly-listing completeness check (2026-10-22): | none | retired: `archive/hierarchy/gap-tools-mit/spec_newpis.py` |
| `sweep_hits.py` | List OpenAlex sweep (hierarchy/mit/openalex-sweep.sqlite, read-only) authorships matching gap PIs' name variants. | none | retired: `archive/hierarchy/gap-tools-mit/sweep_hits.py` |
| `verify_gap_evidence.py` | Re-verify gap-evidence.json against the stored bytes in gap-captures.sqlite. | none | retired: `archive/hierarchy/gap-tools-mit/verify_gap_evidence.py` |
| `verify_oa.py` | Check an OpenAlex author's works against a stored publication list (MIT gap store; | none | retired: `archive/hierarchy/gap-tools-mit/verify_oa.py` |
| `wbfetch.py` | Fetch Wayback id_ capture URLs into the MIT gap store with the store's convention (url = original, capture_url = the Wayback id_ URL), then print a text window. | none | retired: `archive/hierarchy/gap-tools-mit/wbfetch.py` |

## `hierarchy/gap-tools-princeton-epfl/` (11: 11 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build.py` | Build hierarchy/<school>/gap-evidence.json from decisions_<school>.py and re-verify every quote against stored bytes. | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/build.py` |
| `decisions_epfl.py` | Researched decisions for the EPFL gap PIs (hierarchy/epfl/gap-input.json). | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/decisions_epfl.py` |
| `decisions_princeton.py` | Researched decisions for the Princeton gap PIs (hierarchy/princeton/gap-input.json). | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/decisions_princeton.py` |
| `epfl_helpers.py` | EPFL-only helpers (used by decisions_epfl.py). | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/epfl_helpers.py` |
| `evlib.py` | Helpers for the per-school decision modules (decisions_<school>.py): | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/evlib.py` |
| `f.py` | Interactive CLI over gapcap (all fetches stored in hierarchy/<school>/gap-captures.sqlite). | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/f.py` |
| `gapcap.py` | Polite fetcher + per-school SQLite capture store for the Princeton/EPFL PI gap investigation. | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/gapcap.py` |
| `infosci.py` | EPFL Infoscience (DSpace-CRIS REST) search: | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/infosci.py` |
| `match_works.py` | Verify an OpenAlex author id against the PI's own publication list: | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/match_works.py` |
| `oai.py` | Princeton DataSpace OAI-PMH harvester (robots allows /oai; | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/oai.py` |
| `sweep_hits.py` | For each gap PI, list name-matching authorships in hierarchy/<school>/openalex-sweep.sqlite (read-only): | none | retired: `archive/hierarchy/gap-tools-princeton-epfl/sweep_hits.py` |

## `hierarchy/home-dept-tools/` (6: 6 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `batch_fetch.py` | Fetch a list of URLs (one per line in a file, or argv) round-robin across hosts; | none | retired: `archive/hierarchy/home-dept-tools/batch_fetch.py` |
| `build_output.py` | Build home-departments.json from decisions.py + the capture DB, then re-verify every quote. | none | retired: `archive/hierarchy/home-dept-tools/build_output.py` |
| `capstore.py` | Polite fetcher + SQLite capture store for the home-department sweep. | none | retired: `archive/hierarchy/home-dept-tools/capstore.py` |
| `decisions.py` | Per-PI home-department decisions for the 94-row home-department sweep (2026-10-21). | none | retired: `archive/hierarchy/home-dept-tools/decisions.py` |
| `inspect_capture.py` | Print windows of the whitespace-collapsed text of the latest 200 capture of URL around REGEX. | none | retired: `archive/hierarchy/home-dept-tools/inspect_capture.py` |
| `wayback_fetch.py` | Find Wayback captures (CDX, status 200, distinct digests) of URL and fetch id_ captures newest-first until one's text matches REQUIRE regex (and not REJECT regex). | none | retired: `archive/hierarchy/home-dept-tools/wayback_fetch.py` |

## `hierarchy/michigan/` (2: 2 folded)

| script | what it does | live callers | fate |
|---|---|---|---|
| `run_sweep.sh` | Michigan OpenAlex institution sweep (tools/oa_sweep.py; | none | folded: tools/sweep_school.py <key> = atlas sweep <key> (sweep + sweep check, any charter school); the original is in archive/ |
| `sweep_daily.sh` | Re-run the Michigan sweep after each OpenAlex daily credit reset (00:00 UTC) until every year 2016-2026 is stored. | none | folded: tools/sweep_school.py <key> --daily; the original is in archive/ |

## `hierarchy/missing-pi-tools/` (2: 1 folded, 1 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build_review.py` | Missing-PI review (2026-10-22): | none | retired: `archive/hierarchy/missing-pi-tools/build_review.py` |
| `mpcap.py` | Polite fetcher + one SQLite capture store for the missing-PI review (2026-10-22). | tools/labpage_recover.py (import mpcap); tools/labpage_audit.py (LR.mpcap) | folded: tools/mpcap.py (moved; tools/labpage_recover.py imports it, and through it tools/labpage_audit.py) |

## `hierarchy/mit/cs-related-tools/` (10: 10 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `affiliations.py` | Raw affiliation strings each candidate carries on their MIT works in the school's OpenAlex sweep (hierarchy/mit/openalex-sweep.sqlite, streamed): | none | retired: `archive/hierarchy/mit/cs-related-tools/affiliations.py` |
| `build.py` | Build the MIT CS-related scope outputs (owner decision 2026-10-22) from the reviewed decisions (decisions.py) and the offline evidence gathered by the other tools in this directory: | none | retired: `archive/hierarchy/mit/cs-related-tools/build.py` |
| `copy_listings.py` | Copy department faculty listings into the MIT CS-related review store (hierarchy/mit/cs-related-captures.sqlite), bytes and sha256 unchanged, copied_from naming the source store: | none | retired: `archive/hierarchy/mit/cs-related-tools/copy_listings.py` |
| `decisions.py` | Reviewed decisions for the MIT CS-related scope (owner decision 2026-10-22), keyed by the candidate's name as hierarchy/mit/cs-related-candidates.json writes it. | none | retired: `archive/hierarchy/mit/cs-related-tools/decisions.py` |
| `dspace_queries.py` | Adviser-name queries to DSpace@MIT for listed faculty whose PhD advising the stored captures do not show, in the format the leftover 2026-10-22 session used (six names per request, theses issued 20... | none | retired: `archive/hierarchy/mit/cs-related-tools/dspace_queries.py` |
| `mpcap.py` | [Copied 2026-10-23 for the MIT CS-related scope review; | none | retired: `archive/hierarchy/mit/cs-related-tools/mpcap.py` |
| `scan_listings.py` | Match every candidate (hierarchy/mit/cs-related-candidates.json) against the department faculty listings in the review store (Course Catalog department pages, EECS faculty lists): | none | retired: `archive/hierarchy/mit/cs-related-tools/scan_listings.py` |
| `scan_listings_lib.py` | Name helpers shared by the MIT CS-related review tools. | none | retired: `archive/hierarchy/mit/cs-related-tools/scan_listings_lib.py` |
| `thesis_index.py` | Index every DSpace@MIT thesis item record already captured (no new requests): | none | retired: `archive/hierarchy/mit/cs-related-tools/thesis_index.py` |
| `thesis_match.py` | Theses each candidate supervised, from the thesis index (thesis_index.py): | none | retired: `archive/hierarchy/mit/cs-related-tools/thesis_match.py` |

## `hierarchy/period-tools/` (19: 19 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `bridge.py` | Bridged appointment periods from dated listing rows (appointment-period review, 2026-10-26). | none | retired: `archive/hierarchy/period-tools/bridge.py` |
| `cdx_year.py` | CDX prefix queries for one year, cached in listings/<school>/captures.sqlite (wb.cdx; | none | retired: `archive/hierarchy/period-tools/cdx_year.py` |
| `cdxview.py` | Read cached CDX discovery rows (listings/<school>/captures.sqlite, table cdx) offline. | none | retired: `archive/hierarchy/period-tools/cdxview.py` |
| `cmu_build.py` | Build hierarchy/period-tools/proposals/cmu.json (CMU appointment-period review, 2026-10-26). | none | retired: `archive/hierarchy/period-tools/cmu_build.py` |
| `cmu_entries.py` | CMU appointment-period entries, exec'd by cmu_build.py (E, old, oid, period, nochange, SCH, TODAY in scope). | none | retired: `archive/hierarchy/period-tools/cmu_entries.py` |
| `cmu_show.py` | Compact view of CMU period targets: | none | retired: `archive/hierarchy/period-tools/cmu_show.py` |
| `cmu_util.py` | Helpers for the CMU appointment-period review (2026-10-26). | none | retired: `archive/hierarchy/period-tools/cmu_util.py` |
| `delta.py` | Before/after of one school's package: | none | retired: `archive/hierarchy/period-tools/delta.py` |
| `epfl_build.py` | Build hierarchy/period-tools/proposals/epfl.json (EPFL appointment-period review, 2026-10-26). | none | retired: `archive/hierarchy/period-tools/epfl_build.py` |
| `epfl_util.py` | Helpers for the EPFL appointment-period review (2026-10-26): | none | retired: `archive/hierarchy/period-tools/epfl_util.py` |
| `followup_build.py` | Follow-up appointment-period review (2026-10-27): | none | retired: `archive/hierarchy/period-tools/followup_build.py` |
| `merge_overrides.py` | Merge reviewed appointment periods (hierarchy/period-tools/proposals/<school>.json) into hierarchy/census-overrides.json. | none | retired: `archive/hierarchy/period-tools/merge_overrides.py` |
| `pcap.py` | Capture store of the appointment-period review (2026-10-26): | none | retired: `archive/hierarchy/period-tools/pcap.py` |
| `pm_build.py` | Build proposals/princeton.json and proposals/mit.json for the 2026-10-26 appointment-period review. | none | retired: `archive/hierarchy/period-tools/pm_build.py` |
| `pm_copy.py` | Copy captures unchanged from another mpcap-format store into period-captures.sqlite (as cscap.copy_mp does). | none | retired: `archive/hierarchy/period-tools/pm_copy.py` |
| `pm_fetch.py` | Fetch URLs (argv after --names) via pcap and print snippets around the given names. | none | retired: `archive/hierarchy/period-tools/pm_fetch.py` |
| `pm_show.py` | Print a compact view of each period target: | none | retired: `archive/hierarchy/period-tools/pm_show.py` |
| `pm_wb.py` | Wayback fetch: for each URL, list captures via CDX (2010-2026) and fetch one id_ capture (the earliest after --after YYYY if given, else the latest), printing snippets around the given names. | none | retired: `archive/hierarchy/period-tools/pm_wb.py` |
| `stanford_followup_build.py` | Stanford follow-up appointment-period review (gap 2, 2026-10-27): | none | retired: `archive/hierarchy/period-tools/stanford_followup_build.py` |

## `hierarchy/thesis-tools/` (20: 20 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `berkeley_depts.py` | Source spec for the Berkeley advisee hunt outside EECS (2026-10-27): | none | retired: `archive/hierarchy/thesis-tools/berkeley_depts.py` |
| `build.py` | Build hierarchy/<school>/thesis-evidence.json and hierarchy/thesis-harvest-report.json from the thesis captures. | none | retired: `archive/hierarchy/thesis-tools/build.py` |
| `fetch.py` | Fetch URLs into a school's thesis capture store (tcap) and print status + a text window. | none | retired: `archive/hierarchy/thesis-tools/fetch.py` |
| `harvest_berkeley.py` | Berkeley thesis harvest into hierarchy/berkeley/thesis-captures.sqlite (single writer; | none | retired: `archive/hierarchy/thesis-tools/harvest_berkeley.py` |
| `harvest_berkeley_depts.py` | Berkeley advisee harvest beyond EECS (2026-10-27) into hierarchy/berkeley/thesis-captures.sqlite (single writer). | none | retired: `archive/hierarchy/thesis-tools/harvest_berkeley_depts.py` |
| `harvest_cmu.py` | CMU thesis harvest into hierarchy/cmu/thesis-captures.sqlite (single writer). | none | retired: `archive/hierarchy/thesis-tools/harvest_cmu.py` |
| `harvest_epfl.py` | EPFL thesis harvest: Infoscience (DSpace-CRIS 7) REST discover search (robots.txt allows /server/api; | none | retired: `archive/hierarchy/thesis-tools/harvest_epfl.py` |
| `harvest_lab_sources.py` | Lab / PI page harvest for PIs whose advisees no thesis catalogue shows (2026-10-27), for MIT, CMU, EPFL and Princeton, into hierarchy/<school>/thesis-captures.sqlite (single writer per school; | none | retired: `archive/hierarchy/thesis-tools/harvest_lab_sources.py` |
| `harvest_mit.py` | MIT thesis harvest (2016-2026) from DSpace@MIT into hierarchy/mit/thesis-captures.sqlite (single writer). | none | retired: `archive/hierarchy/thesis-tools/harvest_mit.py` |
| `harvest_princeton.py` | Princeton thesis harvest: | none | retired: `archive/hierarchy/thesis-tools/harvest_princeton.py` |
| `harvest_stanford.py` | Stanford thesis harvest into hierarchy/stanford/thesis-captures.sqlite (single writer). | none | retired: `archive/hierarchy/thesis-tools/harvest_stanford.py` |
| `lab_sources.py` | Source spec for the zero-students pass (2026-10-27) at MIT, CMU, EPFL and Princeton: | none | retired: `archive/hierarchy/thesis-tools/lab_sources.py` |
| `lab_sources_stanford.py` | Stanford source spec for the pre-2023 advising pass (gap 3, 2026-10-27), in the lab_sources.SOURCES format (see the lab_sources.py docstring): | none | retired: `archive/hierarchy/thesis-tools/lab_sources_stanford.py` |
| `merge.py` | Copy every row of a worker-local capture DB (TCAP_LOCAL) into the school's thesis-captures.sqlite. | none | retired: `archive/hierarchy/thesis-tools/merge.py` |
| `names.py` | Name matching for the thesis hunt: | none | retired: `archive/hierarchy/thesis-tools/names.py` |
| `records.py` | Normalized thesis records from the stored captures (hierarchy/<school>/thesis-captures.sqlite; | none | retired: `archive/hierarchy/thesis-tools/records.py` |
| `records_labs.py` | Thesis-style records from the PIs' own pages listed in lab_sources.SOURCES (MIT, CMU, EPFL, Princeton; | none | retired: `archive/hierarchy/thesis-tools/records_labs.py` |
| `summarize.py` | Print the hunt's summary from hierarchy/thesis-harvest-report.json (or thesis-tools/out/ with --draft): | none | retired: `archive/hierarchy/thesis-tools/summarize.py` |
| `tcap.py` | Polite fetcher + per-school SQLite capture store for the thesis-adviser hunt (2026-10-22). | none | retired: `archive/hierarchy/thesis-tools/tcap.py` |
| `verify.py` | Independent re-verification of hierarchy/<school>/thesis-evidence.json against hierarchy/<school>/thesis-captures.sqlite. | none | retired: `archive/hierarchy/thesis-tools/verify.py` |

## `listings/scripts/ (single files)` (4: 4 kept)

| script | what it does | live callers | fate |
|---|---|---|---|
| `config_berkeley.py` | Berkeley EECS faculty listing slots -> URL eras (YYYYMMDD inclusive). | none | kept: kept: the listing slots of a pre-protocol school, read by listings/scripts/plan_fetch.py and build.py (importlib config_<school>); protocol schools take them from the charter |
| `config_cmu.py` | CMU School of Computer Science department faculty listing slots -> URL eras (YYYYMMDD inclusive). | none | kept: kept: the listing slots of a pre-protocol school, read by listings/scripts/plan_fetch.py and build.py (importlib config_<school>); protocol schools take them from the charter |
| `config_epfl.py` | EPFL IC (School of Computer and Communication Sciences) faculty listing slots. | none | kept: kept: the listing slots of a pre-protocol school, read by listings/scripts/plan_fetch.py and build.py (importlib config_<school>); protocol schools take them from the charter |
| `config_mit.py` | MIT listing slots -> URL eras (YYYYMMDD inclusive). | none | kept: kept: the listing slots of a pre-protocol school, read by listings/scripts/plan_fetch.py and build.py (importlib config_<school>); protocol schools take them from the charter |

## `tools/ (single files)` (5: 5 retired)

| script | what it does | live callers | fate |
|---|---|---|---|
| `berkeley_census.py` | Berkeley EECS (CS) in the census format of the other schools, plus the small collection pi_hierarchy.py reads. | none | retired: `archive/tools/berkeley_census.py` |
| `berkeley_pubs.py` | Berkeley EECS "Faculty Publications" pages (www2.eecs.berkeley.edu/Pubs/Faculty/<id>.html): | none | retired: `archive/tools/berkeley_pubs.py` |
| `epfl_census.py` | EPFL IC faculty census and PI determination, 2016-2026 (step 0 of the four-school build, 2026-10-21). | none | retired: `archive/tools/epfl_census.py` |
| `epfl_profiles.py` | people.epfl.ch profiles of census people whose rank the sweep's pages leave unknown (live, else the latest Wayback capture), cached with sha256 in census/raw/profiles.sqlite. | tools/epfl_census.py (reads its profiles.sqlite; retired with it) | retired: `archive/tools/epfl_profiles.py` |
| `princeton_census.py` | Princeton in the census format of the other schools, so tools/pi_hierarchy.py builds all five the same way. | none | retired: `archive/tools/princeton_census.py` |

## `fulltext-push (per-school collector scripts)` (15: 15 deferred)

| script | what it does | live callers | fate |
|---|---|---|---|
| `berkeley-collector.slurm` | berkeley full-text push (2026-10-28): | none | deferred: owned by the downloads agent: left in place |
| `berkeley_catalog.py` | The Berkeley full-text catalog for the CS lab papers: | none | deferred: owned by the downloads agent: left in place |
| `cmu-collector.slurm` | cmu full-text push (2026-10-28): | none | deferred: owned by the downloads agent: left in place |
| `epfl-collector.slurm` | epfl full-text push (2026-10-28): | none | deferred: owned by the downloads agent: left in place |
| `princeton_import.slurm` | Princeton: import the lab-channel candidate packages that are not in the catalog yet (packages written since 2026-10-26 were stranded: | none | deferred: owned by the downloads agent: left in place |
| `michigan-collector.slurm` | Michigan full-text collection (protocol stage 8, 2026-10-30), modelled on stanford-collector.slurm: | none | deferred: owned by the downloads agent: left in place |
| `mit-collector.slurm` | MIT full-text collection for the 7,324 lab papers add_works.py put in the catalog on 2026-10-28. | none | deferred: owned by the downloads agent: left in place |
| `mit-oa-harvest.slurm` | (no docstring) | none | deferred: owned by the downloads agent: left in place |
| `mit-steps.slurm` | (no docstring) | none | deferred: owned by the downloads agent: left in place |
| `mit_oa_articles.py` | DSpace@MIT's Open Access Articles collection (hdl 1721.1/49433, the MIT faculty open-access policy's deposits: | none | deferred: owned by the downloads agent: left in place |
| `princeton-collector.slurm` | princeton full-text push (2026-10-28): | none | deferred: owned by the downloads agent: left in place |
| `princeton_pass.sh` | Princeton lab papers (2026-10-22): | none | deferred: owned by the downloads agent: left in place |
| `repair_berkeley_evidence.py` | One-off repair (2026-10-22): | none | deferred: owned by the downloads agent: left in place |
| `stanford-collector.slurm` | Stanford full-text collection, resumed from resemble after the similarity -> resemble cutover (2026-10-28). | none | deferred: owned by the downloads agent: left in place |
| `stanford_catalog.py` | The Stanford full-text catalog for the CS lab papers (2026-10-27): | none | deferred: owned by the downloads agent: left in place |

## `hierarchy/labpage-tools-cmu/` (18: 18 deferred)

| script | what it does | live callers | fate |
|---|---|---|---|
| `build.py` | Build hierarchy/cmu/labpage-evidence.json and labpage-pubs.jsonl.gz from decisions/*.py + the capture stores, then re-verify every quote against the stored bytes (sha256 lookup + exact substring + ... | none | deferred: owned by the lab-page agent: left in place |
| `capstore.py` | Polite fetcher + SQLite capture store for the CMU lab-page pass (adapted from few-students-tools-cmu/capstore.py). | none | deferred: owned by the lab-page agent: left in place |
| `crawl.py` | Phase 1 pre-crawl for the CMU lab-page pass (resumable, detached). | none | deferred: owned by the lab-page agent: left in place |
| `dhelp.py` | Spec helpers for decisions/*.py (CMU lab-page pass). | none | deferred: owned by the lab-page agent: left in place |
| `lp.py` | Worker CLI for the CMU lab-page pass. | none | deferred: owned by the lab-page agent: left in place |
| `merge.py` | Merge every lab-page capture part into hierarchy/cmu/labpage-captures.sqlite (single writer). | none | deferred: owned by the lab-page agent: left in place |
| `names.py` | Name normalisation + held-person matching with nicknames and spelling variants (CMU lab-page pass). | none | deferred: owned by the lab-page agent: left in place |
| `pubx.py` | Publication-list extraction for the CMU lab-page pass. | none | deferred: owned by the lab-page agent: left in place |
| `refetch.py` | Re-fetch every URL cited by decisions/*.py into labpage-parts/refetch.sqlite (resumable, detached). | none | deferred: owned by the lab-page agent: left in place |
| `report.py` | Summary statistics for the CMU lab-page pass. | none | deferred: owned by the lab-page agent: left in place |
| `w_b02_raw.py` | b02 helper: print a slice of the cached raw HTML of a URL (cache only, never fetches). | none | deferred: owned by the lab-page agent: left in place |
| `w_b02_retry.py` | b02 helper: run lp.py commands (one per line in a job file, args separated by ' \|\|\| ') and retry each while Wayback refuses connections. | none | deferred: owned by the lab-page agent: left in place |
| `w_b04_retry.py` | b04 helper: fetch a list of URLs through lp.py get, retrying when Wayback refuses connections. | none | deferred: owned by the lab-page agent: left in place |
| `w_b05_raw.py` | b05 helper: print src/href/data-file references from a stored capture's raw HTML (no fetching). | none | deferred: owned by the lab-page agent: left in place |
| `w_b05_retry.py` | b05 helper: run `lp.py <args>` again with backoff while Wayback refuses connections. | none | deferred: owned by the lab-page agent: left in place |
| `w_b06_retry.sh` | usage: w_b06_retry.sh <lp.py subcommand and args...> retries on Wayback connection errors (max 4 tries) | none | deferred: owned by the lab-page agent: left in place |
| `w_b07_raw.py` | b07 helper: print a slice of the cached raw HTML of a URL (cache only, never fetches). | none | deferred: owned by the lab-page agent: left in place |
| `w_b08_wb.py` | b08 helper: Wayback CDX / capture fetch with polite backoff on connection errors (web.archive.org has been refusing connections intermittently). | none | deferred: owned by the lab-page agent: left in place |

## `hierarchy/labpage-tools-cmu/decisions/` (29: 29 deferred)

| script | what it does | live callers | fate |
|---|---|---|---|
| `b01.py` | ---------------------------------------------------------------- Umut Acar | none | deferred: owned by the lab-page agent: left in place |
| `b02.py` | ---------------------------------------------------------------- Jeremy Avigad | none | deferred: owned by the lab-page agent: left in place |
| `b03.py` | ---------------------------------------------------------------- Alan Black | none | deferred: owned by the lab-page agent: left in place |
| `b04.py` | ---------------------------------------------------------------- Emma Brunskill | none | deferred: owned by the lab-page agent: left in place |
| `b05.py` | ---------------------------------------------------------------- Justin Chan | none | deferred: owned by the lab-page agent: left in place |
| `b06.py` | ---------------------------------------------------------------- Keenan Crane | none | deferred: owned by the lab-page agent: left in place |
| `b07.py` | ---------------------------------------------------------------- Ryan O'Donnell | none | deferred: owned by the lab-page agent: left in place |
| `b08.py` | ---------------------------------------------------------------- Jodi Forlizzi | none | deferred: owned by the lab-page agent: left in place |
| `b09.py` | ---------------------------------------------------------------- Geoffrey J Gordon | none | deferred: owned by the lab-page agent: left in place |
| `b10.py` | ---------------------------------------------------------------- Vipul Goyal | none | deferred: owned by the lab-page agent: left in place |
| `b11.py` | ---------------------------------------------------------------- Martial Hebert | none | deferred: owned by the lab-page agent: left in place |
| `b12.py` | ---------------------------------------------------------------- Ralph Hollis | none | deferred: owned by the lab-page agent: left in place |
| `b13.py` | ---------------------------------------------------------------- Laszlo Attila Jeni | none | deferred: owned by the lab-page agent: left in place |
| `b14.py` | ---------------------------------------------------------------- Christian Kästner | none | deferred: owned by the lab-page agent: left in place |
| `b15.py` | (no docstring) | none | deferred: owned by the lab-page agent: left in place |
| `b16.py` | ---- Lei Li | none | deferred: owned by the lab-page agent: left in place |
| `b17.py` | (no docstring) | none | deferred: owned by the lab-page agent: left in place |
| `b18.py` | ---------------------------------------------------------------- Heather Miller | none | deferred: owned by the lab-page agent: left in place |
| `b19.py` | ---------------------------------------------------------------- Brad A Myers | none | deferred: owned by the lab-page agent: left in place |
| `b20.py` | ---------------------------------------------------------------- Jignesh Patel | none | deferred: owned by the lab-page agent: left in place |
| `b21.py` | ---------------------------------------------------------------- Aditi Raghunathan | none | deferred: owned by the lab-page agent: left in place |
| `b22.py` | ---------------------------------------------------------------- Anthony Rowe | none | deferred: owned by the lab-page agent: left in place |
| `b23.py` | ---- Jeff Schneider | none | deferred: owned by the lab-page agent: left in place |
| `b24.py` | ---------------------------------------------------------------- Hirokazu Shirado | none | deferred: owned by the lab-page agent: left in place |
| `b25.py` | ---------------- Peter Steenkiste ---------------- | none | deferred: owned by the lab-page agent: left in place |
| `b26.py` | ---------------------------------------------------------------- Christopher Timperley | none | deferred: owned by the lab-page agent: left in place |
| `b27.py` | ---- Wenshan Wang ---- | none | deferred: owned by the lab-page agent: left in place |
| `b28.py` | (no docstring) | none | deferred: owned by the lab-page agent: left in place |
| `b29.py` | ---------------------------------------------------------------- Kun Zhang | none | deferred: owned by the lab-page agent: left in place |

## `hierarchy/labpage-tools-epfl-berkeley/` (20: 20 deferred)

| script | what it does | live callers | fate |
|---|---|---|---|
| `autospec.py` | Automatic first specs from the discovery pass (used because no worker agents could be started). | none | deferred: owned by the lab-page agent: left in place |
| `batchprobe.py` | Fetch every guessed URL in guesses.json (Wayback fallback) plus one level of people/pubs-like links found on them, and record per-page stats in discover/probe-<school>.jsonl (resumable). | none | deferred: owned by the lab-page agent: left in place |
| `discover.py` | First automatic pass for the lab-page pass: | none | deferred: owned by the lab-page agent: left in place |
| `lp.py` | Lab-page pass CLI (EPFL + Berkeley, 2026-10-22). | none | deferred: owned by the lab-page agent: left in place |
| `lpbuild.py` | Build the lab-page pass outputs from per-lab specs (work/<school>/<slug>.json). | none | deferred: owned by the lab-page agent: left in place |
| `lpc.sh` | usage: lpc.sh ID SCRIPT.py args -- run a tools script with private capture DBs (scratchpad lpdb/<ID>-<school>.sqlite) | none | deferred: owned by the lab-page agent: left in place |
| `lpcap.py` | Polite fetcher + per-school SQLite capture store for the lab-page pass (EPFL + Berkeley, 2026-10-22). | none | deferred: owned by the lab-page agent: left in place |
| `lpdom.py` | HTML linearisation for the lab-page pass: | none | deferred: owned by the lab-page agent: left in place |
| `lplab.py` | Lab rows, slugs, seed URLs and stored-capture lookup for the lab-page pass. | none | deferred: owned by the lab-page agent: left in place |
| `lpnames.py` | Name folding, nickname variants and matching against a lab's students_held (lab-page pass, 2026-10-22). | none | deferred: owned by the lab-page agent: left in place |
| `lppubs.py` | Publication-page parsing for the lab-page pass: | none | deferred: owned by the lab-page agent: left in place |
| `lpw.sh` | usage: lpw.sh WORKER_ID <lp.py args> -- runs lp.py with this worker's private capture DBs | none | deferred: owned by the lab-page agent: left in place |
| `merge.py` | Copy every row of a worker-local capture DB into hierarchy/<school>/labpage-captures.sqlite (single writer). | none | deferred: owned by the lab-page agent: left in place |
| `probe.py` | Compact probe of candidate pages for labs the discovery pass left without a people page. | none | deferred: owned by the lab-page agent: left in place |
| `review.py` | Compact review of built specs: | none | deferred: owned by the lab-page agent: left in place |
| `run_build.sh` | Build both schools' outputs offline from the capture stores, then merge any rows copied from sister stores. | none | deferred: owned by the lab-page agent: left in place |
| `run_discover.sh` | Discovery shards for the lab-page pass; | none | deferred: owned by the lab-page agent: left in place |
| `run_wayback.sh` | Wayback captures of each lab's main people page (autospec.py wayback), 2 shards per school, local DBs. | none | deferred: owned by the lab-page agent: left in place |
| `setman.py` | Merge per-lab overrides into manual_pages.json. | none | deferred: owned by the lab-page agent: left in place |
| `verify.py` | Independent re-verification of hierarchy/<school>/labpage-evidence.json and labpage-pubs.jsonl.gz. | none | deferred: owned by the lab-page agent: left in place |

## `hierarchy/labpage-tools-princeton-mit/` (26: 26 deferred)

| script | what it does | live callers | fate |
|---|---|---|---|
| `autom.py` | Automatic member extraction from a stored people page (proposals for review; | none | deferred: owned by the lab-page agent: left in place |
| `build.py` | Build hierarchy/<school>/labpage-evidence.json and labpage-pubs.jsonl.gz from the decision modules dec_<school>_*.py (each defines D = {pi: | none | deferred: owned by the lab-page agent: left in place |
| `dec_mit_main.py` | Lab-page decisions for mit labs, built from the reviewed plan plan_mit.py (people pages, Wayback history in wb_mit.json, reviewer corrections, publication pages) by lpauto.rows_for: | none | deferred: owned by the lab-page agent: left in place |
| `dec_princeton_ham.py` | Lab-page decisions: Princeton, Manoel Horta Ribeiro (Humans and Machines Lab). | none | deferred: owned by the lab-page agent: left in place |
| `dec_princeton_main.py` | Lab-page decisions for princeton labs, built from the reviewed plan plan_princeton.py (people pages, Wayback history in wb_princeton.json, reviewer corrections, publication pages) by lpauto.rows_for: | none | deferred: owned by the lab-page agent: left in place |
| `disc.py` | Discovery crawl for the lab-page pass: | none | deferred: owned by the lab-page agent: left in place |
| `f.py` | Fetch URLs into a school's labpage capture store and print text windows. | none | deferred: owned by the lab-page agent: left in place |
| `lpauto.py` | Turn a reviewed lab plan into member rows (used by dec_<school>_main.py). | none | deferred: owned by the lab-page agent: left in place |
| `lpcap.py` | Polite fetcher + per-school SQLite capture store for the lab-page pass (Princeton + MIT, 2026-10-22). | none | deferred: owned by the lab-page agent: left in place |
| `lpev.py` | Evidence helpers for the lab-page decision modules (dec_<school>_<batch>.py). | none | deferred: owned by the lab-page agent: left in place |
| `merge.py` | Copy every row of worker-local capture DBs into hierarchy/<school>/labpage-captures.sqlite. | none | deferred: owned by the lab-page agent: left in place |
| `missingsrc.py` | List plan people/pubs URLs (live, not Wayback) that have no stored 200 capture. | none | deferred: owned by the lab-page agent: left in place |
| `names.py` | Name matching for the lab-page pass: | none | deferred: owned by the lab-page agent: left in place |
| `newrows.sh` | usage: newrows.sh SCHOOL "PI" ["PI" ...] -- dry-run those PIs and print their NEW rows compactly | none | deferred: owned by the lab-page agent: left in place |
| `peek.py` | Show a stored people page as heading-delimited sections with the person-like names found in each, marked against the lab's students_held (names.match). | none | deferred: owned by the lab-page agent: left in place |
| `plan_mit.py` | Reviewed lab-page plan for MIT (see lpauto.py for the keys). | none | deferred: owned by the lab-page agent: left in place |
| `plan_princeton.py` | Reviewed lab-page plan for Princeton (see lpauto.py for the keys). | none | deferred: owned by the lab-page agent: left in place |
| `pubhtml.py` | Print the raw HTML (whitespace-collapsed) around the first occurrence of a text in a stored page, to write a pubx spec. | none | deferred: owned by the lab-page agent: left in place |
| `pubrev.py` | Review publication extraction for every Pubs page in plan_<school>.py: | none | deferred: owned by the lab-page agent: left in place |
| `pubx.py` | Publication-list extraction for the lab-page pass, and the compare against the PI's lab papers. | none | deferred: owned by the lab-page agent: left in place |
| `run_disc.sh` | Discovery crawl for one school into a worker-local capture DB (merged later by merge.py). | none | deferred: owned by the lab-page agent: left in place |
| `run_wb.sh` | Wayback history for plan people pages, one shard per process, into worker-local stores (merged later with merge.py). | none | deferred: owned by the lab-page agent: left in place |
| `survey.py` | Run autom.extract over every stored 200 HTML page of each lab's dossier (profile pages skipped) and summarise: | none | deferred: owned by the lab-page agent: left in place |
| `verify.py` | Independent re-verification of hierarchy/<school>/labpage-evidence.json and labpage-pubs.jsonl.gz against the school's capture store (hierarchy/<school>/labpage-captures.sqlite only; | none | deferred: owned by the lab-page agent: left in place |
| `wb3.py` | Wayback history for a lab page: | none | deferred: owned by the lab-page agent: left in place |
| `wbbatch.py` | Fetch Wayback history for every plan people page: | none | deferred: owned by the lab-page agent: left in place |

## `hierarchy/labpage-tools-stanford/` (8: 8 deferred)

| script | what it does | live callers | fate |
|---|---|---|---|
| `discover.py` | Automatic discovery of Stanford PIs' publication pages: | none | deferred: owned by the lab-page agent: left in place |
| `peek.py` | peek.py N PI [PI...]: | none | deferred: owned by the lab-page agent: left in place |
| `seeds.py` | Seed URLs per Stanford PI for the lab-page publication pass: | none | deferred: owned by the lab-page agent: left in place |
| `setdec.py` | Edit decisions.json: setdec.py PI URL[@mode] [URL...] \| setdec.py PI --none REASON \| setdec.py PI --notes TEXT | none | deferred: owned by the lab-page agent: left in place |
| `stbuild.py` | Build hierarchy/stanford/labpage-pubs.jsonl.gz and labpage-pubs-report.json from the reviewed decisions (decisions.json in this directory: | none | deferred: owned by the lab-page agent: left in place |
| `stcap.py` | Stanford support for the lab-page publication pass (2026-10-27): | none | deferred: owned by the lab-page agent: left in place |
| `stlp.py` | Review CLI for the Stanford lab-page publication pass. | none | deferred: owned by the lab-page agent: left in place |
| `verify.py` | Independent re-verification of hierarchy/stanford/labpage-pubs.jsonl.gz against labpage-captures.sqlite. | none | deferred: owned by the lab-page agent: left in place |
