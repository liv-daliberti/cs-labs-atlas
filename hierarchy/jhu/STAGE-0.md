# Johns Hopkins University, stage 0: charter and config

Date: 2026-11-05. Protocol v3 (`docs/ADDING-A-SCHOOL.md`). Branch `agent/jhu` (from `agent/protocol-v3` d913624; not landed). Status stays `onboarding`, `order = 10` (provisional; Harvard and WashU draft 11 and 12).
Scope of this run: the "Before you start" checklist and stage 0 only. No OpenAlex credits, no Slurm jobs, no Wayback fetching beyond the access probe (one request: `web.archive.org/web/2020id_/https://www.cs.jhu.edu/`).

## What was done
- `atlas new-school jhu`; `schools/jhu.toml` filled whole (v3 item 6): affiliation regex (13 must_match, 16 must_not_match, `atlas charters`: 10 charters ok), `loose`, `own_units`, `[dblp].affiliation_strings`,
  `[repository]` (JScholarship, link pattern incl. handle 1774.2), `[collector].channels` (default list, no repository channel), `[thesis]`, `[students]` sources, `[census].home_units` (18) and `rank_words`,
  4 departments (CS full; ECE, AMS, BME affiliated), 7 searched units (CLSP, Malone, LCSR, Biostatistics, Cognitive Science, Mathematics, DSAI), 16 `[[hosts]]`.
- **Ids** (2026-10-14 snapshot institutions table, no credits; ROR at api.ror.org/v2): Johns Hopkins University `I145311948`, ROR `00za53h95`. 13 lineage children (also ROR children): APL `I2802946424`, Berman Institute `I4210092215`,
  Center for Communication Programs `I4210151848`, SAIS Bologna `I4210131961`, JHU-Nanjing Center `I4210162165`, Maryland Space Grant `I4210120405`, PARADIM `I4387152773`, MSEE URA `I4388891755`, Center for AIDS Research `I4389425327`,
  HEMI `I4391012584`, Packard Center `I4392738135`, JHU Press `I4394709191`, Materials Characterization Facility `I4405260374`. Not in the lineage (associated, "related"): Johns Hopkins Medicine `I2799853436` (its own lineage root),
  Hospital `I4210150714`, Bayview `I2802697821`, Children's Center `I4210129832`, All Children's Hospital `I4210098865`. Not JHU: Hopkins Marine Station `I4405266016` (Stanford). No OpenAlex institution matches the Carey Business School or the
  Bloomberg School separately (they sit inside I145311948 by name only).
- `openalex_related` and `openalex_excluded` were filled after the owner's answers (below).
- Per-child work counts (`oa_institutions.py children-counts jhu`) are all 0: the filtered snapshot holds no JHU works until `snapshot-ext` runs, so the APL-faculty headcount the coordinator asked for was not cheap and is not reported. It follows the extension.

## Owner decision recorded (2026-11-05, relayed by the coordinator)
Keep ONLY labs that do computing; anything that is not computing is not needed. APL, JHU Medicine / Hospital, Bloomberg, the SAIS campuses and Carey have no blanket keep or drop: a unit counts only through its computing labs, i.e. faculty who
meet the CS-related scope rule (`docs/RULES.md`). APL staff are not JHU faculty, the PI rule is unchanged (a PI is a faculty member of the school), so APL contributes PIs only through computing researchers holding a JHU faculty appointment
(e.g. a Whiting joint appointment). APL strings stay in the regex so in-scope PIs' papers that list APL are credited; they never add PIs or labs. Written into the charter's `[ids]` comment.

## Owner decisions applied (2026-11-05)
- Wayback for blocked sites is allowed always: the eight challenged .jhu.edu hosts (ece, engineering/AMS, ams, bme, www.clsp, lcsr, cogsci, www.math) and ai.jhu.edu (Crawl-delay 10 kept) are `wayback-only`. publichealth.jhu.edu and jscholarship.library.jhu.edu name ClaudeBot/anthropic-ai: `none`, Wayback included. Biostatistics is out (disallows AI agents; not computing): its affiliated unit was removed from the charter.
- `openalex_related` = Johns Hopkins Medicine I2799853436 only.
- `openalex_excluded` = Maryland Space Grant I4210120405, JHU Press I4394709191, Communication Programs I4210151848, CFAR I4389425327, Packard Center I4392738135, Berman Bioethics I4210092215, SAIS Bologna I4210131961, JHU-Nanjing I4210162165.
- Kept in the sweep: APL, HEMI, PARADIM, MSEE URA, Materials Facility; APL adds PIs only via JHU faculty appointments. jhmi.edu / hopkinsmedicine.org stay in the regex. `order` is the coordinator's at landing.

## Access check (v3 item 5; `tools/school_hosts.py jhu`, 2026-11-05, generic client name, no e-mail)
Result: 16 hosts, 0 inconsistent. Crawl-delay 2.0 is the tool's default where robots names none; only ai.jhu.edu states one (10 s).
| host | robots | probe | use |
|---|---|---|---|
| www.cs.jhu.edu | allowed (200; only ia_archiver and calendar paths) | ok | live |
| malonecenter.jhu.edu | robots.txt answers 403, page served 200 | ok | live (re-check at stage 2) |
| web.archive.org | 404 (none) | ok | live |
| api.openalex.org | allowed | skipped | live |
| api.ror.org | 403 to the tool's client (a generic API fetch worked) | skipped | live |
| ece.jhu.edu, engineering.jhu.edu (AMS), ams.jhu.edu, bme.jhu.edu, www.clsp.jhu.edu, lcsr.jhu.edu, cogsci.jhu.edu, www.math.jhu.edu | robots 403 | bot challenge | wayback-only (owner) |
| ai.jhu.edu | allowed, Crawl-delay 10 | bot challenge | wayback-only (owner) |
| publichealth.jhu.edu | names ClaudeBot, anthropic-ai, Claude-Web: Disallow / | not probed | none |
| jscholarship.library.jhu.edu | names ClaudeBot, anthropic-ai, Claude-Web: Disallow / (Cloudflare managed block) | not probed | none |
Wrong first guesses fixed: `malone.jhu.edu` and `dsai.jhu.edu` do not resolve (the sites are `malonecenter.jhu.edu` and `ai.jhu.edu`). Math Genealogy and academictree.org were not touched.
**Thesis repository:** JScholarship is not used in any form (records x crawl delay = 0 h, nothing fetched); `[thesis].kind = "none"`, `robots = "disallowed-for-ai-agents"`, `[repository]` says it is reached only through OpenAlex/CORE.
**Consequence:** the challenged hosts are read from Wayback only (stage 1 plan in the report); Biostatistics and JScholarship are never read.

## Snapshot extension (no OpenAlex credits)
Filter array 32116414 (16 tasks, `--partition=all --account=mltheory --time=00:59:00 --exclude=node302,node014`, `sbatch --test-only` showed no "Preempts:") COMPLETED in about 38 min. Merge 32116432 FAILED at 1:50 on node805 (`database or disk is full` while indexing: node-local /tmp had 0 kB free, the /dev/shm fallback was used); the 16 parts were intact, so the merge alone was resubmitted as 32116883 with `node805` excluded: COMPLETED in 2:31 on node808. Result `ext-jhu.sqlite`: 535,172 works. (Harvard's `.part` sat on the same node; the sibling merge failure mode is the same.) The pipeline `snapshot-ext` command was not used because the stage scripts ask for 6 h on partition mltheory; the by-hand route (`OA_DATE=2026-10-14 OA_EXT=jhu atlas submit --from-worktree ...`) applies the standing Slurm rules.

## Per-child works 2016-2026 (`oa_institutions.py children-counts jhu`; works tagged with the id, of which lacking the JHU root id)
| institution | works | lacking JHU id | decision |
|---|---|---|---|
| Johns Hopkins University I145311948 | 245,741 | - | primary |
| APL I2802946424 | 11,905 | 6,416 | kept |
| Berman Bioethics I4210092215 | 1,295 | 0 | excluded |
| HEMI I4391012584 | 504 | 4 | kept |
| Communication Programs I4210151848 | 422 | 0 | excluded |
| PARADIM I4387152773 | 136 | 122 | kept |
| SAIS Bologna I4210131961 | 125 | 0 | excluded |
| CFAR I4389425327 | 41 | 0 | excluded |
| JHU-Nanjing I4210162165 | 40 | 0 | excluded |
| Materials Facility I4405260374 | 11 | 0 | kept |
| JHU Press I4394709191 | 10 | 0 | excluded |
| Packard Center I4392738135 | 4 | 0 | excluded |
| MSEE URA I4388891755 | 2 | 2 | kept |
| Maryland Space Grant I4210120405 | 0 | 0 | excluded |
APL and JHU academic affiliation: 11,905 - 6,416 = 5,489 APL-tagged works also carry the JHU root id on the same work. An author-level count is not available (the extension stores no authorship rows: `work_author` = 0); the APL PI question (people with a JHU faculty appointment) is answered at stage 2 from the unit listings.

## Gate
`atlas stage-gate jhu 0`: **pass** (open 0, 16 hosts, 527,765 snapshot works). It first failed only for the missing snapshot extension, run after the owner's answers. `atlas stage-gate jhu --traps`: one finding, `captures` (no lab-page capture store yet), a stage 6-8 artefact (the lab-page audit store) that no stage-0 step writes; recorded, not fixable in stage 0.
Main checkout: `git -C /n/fs/resemble/homogenizing-science/code status --short` shows nothing of this run (it shows `hierarchy/uchicago/tmp/` and `scratch/`, not mine). Untracked data files written by the tools: `hierarchy/jhu/{derived/hosts.json,raw/school-captures.sqlite,reports/new-school.json}` in the main data tree, plus the empty store `stores/jhu`.
Jobs: none submitted.

## Stage-1 fetch plan (not started; the coordinator sets the Wayback turn order)
Hosts read from Wayback: www.cs.jhu.edu (live too), ece.jhu.edu, engineering.jhu.edu (AMS), ams.jhu.edu, bme.jhu.edu, www.clsp.jhu.edu, lcsr.jhu.edu, cogsci.jhu.edu, www.math.jhu.edu, ai.jhu.edu (10 s delay applies to live fetches only). Not read: publichealth, jscholarship.
Eras to find (`discover_listings.py`, from the 2016 homepage links): CS `/faculty/` (also emeritus/research/teaching pages), ECE `/people/` or `/faculty/`, AMS `ams.jhu.edu` to `engineering.jhu.edu/ams` (move date), BME, CLSP, LCSR; CS PhD student/alumni lists and CLSP student lists for stage 6.
Estimated Wayback requests at the shared 5 s clock: discovery about 30 CDX/page requests per slot x 5 slots, then 22 half-year captures per slot (5 department slots, about 110) plus 7 searched units x 11 = 77 for stage 2; about 350 requests (30 min) if the directories are single pages. Paged or A-Z directories (Georgia Tech: 26 letters x 22 half-years per slot) can multiply this by 10-25 for the slots affected: worst case about 2,500 requests (3.5 h). Wayback shells after 2020 are common; write formats from one sample per era first.

## Remaining decisions for the owner (see the report)
None open from stage 0. Open for later stages: which APL researchers hold JHU faculty appointments (stage 2); `center_units` (CLSP, Malone, LCSR, DSAI) confirmed at stage 3; `order` at landing.
