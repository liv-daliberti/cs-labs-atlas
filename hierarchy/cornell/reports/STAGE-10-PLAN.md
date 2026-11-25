# Cornell stage 10: release freeze plan (2026-11-25). Nothing here has been run; no gate-9 draw, no landing, no release.

Dry run (`bin/atlas run tools/pi_release.py cornell`, after the held-PI work below): partial, 156/157 included, 1 held (A. Kevin Tang), 496 school items. Department-search (units) PIs join a LATER release (D-0001).

## Held PIs (resolved 2026-11-25; an unresolved PI stays held)
| PI | before | now |
|---|---|---|
| Belongie | website official link not recorded | reasoned absence `site_at_other_institution` (KU research-portal page, no Cornell tie; Cornell profile HTTP 403) |
| Ferrari | same | `website_found`: the Cornell Duffield profile her CS profile's "Research Website" field links (her lab site lisc.mae.cornell.edu did not answer) |
| Chen | same | reasoned absence `pi_left_school_site_moved`: Cornell listings 2016-2018 only, 5 Cornell works all 2016, profile 404; the AMP Lab page is stale and not accepted. Window is short; stage 4 may settle it |
| Lodi | website link + students | `website_found`: the Cornell Tech profile (tech.cornell.edu/people/andrea-lodi/) his CS profile links; the unibo.it page is at another institution and is not used |
| Greenberg | website link + students | `website_found`: the Cornell AAP profile his CS profile links (Professor Emeritus) |
| van Schijndel | website link + students | `website_found`: vansky.github.io, linked from his CS profile |
| Van Loan | anchors 0 papers + students | `website_found` (cs.cornell.edu/cv, linked from his profile) + researched reasons in `reviewed/lab-coverage-reasons.json` (students and papers; DBLP list ends 2015, emeritus) |
| Tang | anchors 0 papers + students | STILL HELD, not an identity miss: reviewed OpenAlex id A5103277656 has 32 Cornell works 2016-2018+, but his only listing evidence is the 2016 faculty page, so his appointment window is empty. The periods chain (32546302-07) and the eCommons chair rows (a 2022 thesis chaired by him) should settle it; then rebuild |
Rows are in `reviewed/person-website-review.json` (worker hand review, sha256 of each page fetched 2026-11-25, robots respected).

## A. Must land BEFORE the official gate-9 draw (the draw binds the build and copies.json, L-81)
1. Periods chain: 32546302 (fetch, running) -> 32546303..07 (extract, gaps, extend, truncated, deep), then the stage-4 holds, then `atlas stage-gate cornell 4`. Tang settles here.
2. Units chain 32550849..77 (14 serial links, reordered 2026 + 2020 first). Units candidates join a later release, but the stage-2 review and audit must pass; the draw must not predate them.
3. Live students: labpage-links 32550531 -> extract 32550532 -> directories 32550533; labpage-history 32548152 (4 shards) -> merge 32548153 -> audit-history 32548154 (wait on periods-fetch and the rediscover audit); homepage-links 32547140; then the first lab-page students round (fresh 20, at most 1 error) and the stage-7 hand items (zero-paper labs need reasons, links check 0 open).
4. Rule decision: R-PAP-62, R-PAP-64 and the chairs'-welcome title are owner-approved (D-0074, 2026-11-25); the freeze rebuild carries them: ONE rebuild (`pi_hierarchy.py cornell`, one heavy builder at a time; it changes every school's build on its next rebuild).
5. After the last build: `add_works.py cornell --early` again, `lab_paper_copies.py cornell` (copies.json), `pi_release.py cornell` dry run, `atlas stage-gate cornell catalogue`. The draw must come after all of this: any later build voids it (gate 9's staleness check).

## B. The draw (order of use)
- Early go/no-go draw already exists (accuracy/sample-cornell.json, legacy config); it is not gate evidence, and `accuracy/summarize.py` was NOT run on it.
- Official draw (owner 2026-11-25): `accuracy/g9_round.py` with a fresh seed, round pi2. `accuracy/round-pi2/` holds 29 schools' draws and none of Cornell's, so a Cornell file there overwrites nothing (the tool never overwrites; the seed must not have been used by an earlier round or draw). Steps: `python accuracy/g9_round.py plan --schools cornell`, `draw --seed <fresh N> --schools cornell --yes`, `batches`, `sheets`, `convert`, then `ACCURACY_ROUND=pi2 python accuracy/summarize.py --school cornell`. pi2b/pi2c are for redraws of superseded schools; pi1 is the pre-11-19 form. Cornell gets ONE pi2 draw, so draw only at the freeze.
- Reviewers: fresh and independent (never the worker), <= 25 rows a batch, and the brief must REQUIRE row-level checks (open the stored evidence for every row); the early reviewers made 3-4 tool calls each.
- Student coverage now has 417 candidates (`thesis_database_phd`).

## C. Landing (touches shared files: every school's build reads tools/pihier/papers.py)
1. `bin/atlas task land-lock acquire` (one session lands at a time; ttl 1 h, the land script renews it).
2. `tools/agent_worktree.sh land cornell`: rebases agent/cornell onto main, runs the full tests on a compute node (srun, partition all), fast-forwards main. Full suite at 61dc05db: `python -m pytest -q -p no:warnings tests`, exit 0.
3. R-PAP-62/64 and the title extension are owner-approved (D-0074) and land with the branch (they change released schools' next rebuild). Shared files touched: tools/pihier/papers.py (rules), accuracy/sample.py (student-coverage rule, used by every school's draw), tools/cs_related_school.py (units order), docs/RULES.md, docs/SCHOOL-PROCESS.md, tools/cornell_ecommons.py (Cornell only). Everything under hierarchy/cornell/ is Cornell only.

## D. Release (owner or coordinator decides; not before gate 9 passes on the included subset)
1. `atlas stage-gate cornell 9` and `atlas stage-gate cornell 10` (>= 1 included PI and g9 passing; held PIs are reported, not blocking).
2. `status = "released"` in schools/cornell.toml, regenerate paths.sh.
3. `atlas release --per-pi --add-school cornell` (= `make_release.py --per-pi --add-school cornell`): preflight, rebuild, regression, validate, reader export, release, notes check, organized tree, GitHub export (local commit); then the two external steps `export-push` (tag + push) and `hf-upload`, which need `--yes-push` / `--yes-hf`; last the site handoff note (SITE-HANDOFF.md). It rebuilds and exports EVERY school: the shared, other-schools-touching step. A PI an earlier release published is carried; Cornell has none.
4. Site handoff: the owner or coordinator, from the release's SITE-HANDOFF.md.
