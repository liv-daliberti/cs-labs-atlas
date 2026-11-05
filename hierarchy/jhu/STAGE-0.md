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
- `openalex_related` and `openalex_excluded` are left EMPTY in the charter until the owner answers D2-D4 below; no snapshot extension is submitted yet (it needs the ids).
- Per-child work counts (`oa_institutions.py children-counts jhu`) are all 0: the filtered snapshot holds no JHU works until `snapshot-ext` runs, so the APL-faculty headcount the coordinator asked for was not cheap and is not reported. It follows the extension.

## Owner decision recorded (2026-11-05, relayed by the coordinator)
Keep ONLY labs that do computing; anything that is not computing is not needed. APL, JHU Medicine / Hospital, Bloomberg, the SAIS campuses and Carey have no blanket keep or drop: a unit counts only through its computing labs, i.e. faculty who
meet the CS-related scope rule (`docs/RULES.md`). APL staff are not JHU faculty, the PI rule is unchanged (a PI is a faculty member of the school), so APL contributes PIs only through computing researchers holding a JHU faculty appointment
(e.g. a Whiting joint appointment). APL strings stay in the regex so in-scope PIs' papers that list APL are credited; they never add PIs or labs. Written into the charter's `[ids]` comment.

## Access check (v3 item 5; `tools/school_hosts.py jhu`, 2026-11-05, generic client name, no e-mail)
Result: 16 hosts, 0 inconsistent. Crawl-delay 2.0 is the tool's default where robots names none; only ai.jhu.edu states one (10 s).
| host | robots | probe | use |
|---|---|---|---|
| www.cs.jhu.edu | allowed (200; only ia_archiver and calendar paths) | ok | live |
| malonecenter.jhu.edu | robots.txt answers 403, page served 200 | ok | live (re-check at stage 2) |
| web.archive.org | 404 (none) | ok | live |
| api.openalex.org | allowed | skipped | live |
| api.ror.org | 403 to the tool's client (a generic API fetch worked) | skipped | live |
| ece.jhu.edu, engineering.jhu.edu (AMS), ams.jhu.edu, bme.jhu.edu, www.clsp.jhu.edu, lcsr.jhu.edu, cogsci.jhu.edu, www.math.jhu.edu | robots 403 | bot challenge | none |
| ai.jhu.edu | allowed, Crawl-delay 10 | bot challenge | none |
| publichealth.jhu.edu | names ClaudeBot, anthropic-ai, Claude-Web: Disallow / | not probed | none |
| jscholarship.library.jhu.edu | names ClaudeBot, anthropic-ai, Claude-Web: Disallow / (Cloudflare managed block) | not probed | none |
Wrong first guesses fixed: `malone.jhu.edu` and `dsai.jhu.edu` do not resolve (the sites are `malonecenter.jhu.edu` and `ai.jhu.edu`). Math Genealogy and academictree.org were not touched.
**Thesis repository:** JScholarship is not used in any form (records x crawl delay = 0 h, nothing fetched); `[thesis].kind = "none"`, `robots = "disallowed-for-ai-agents"`, `[repository]` says it is reached only through OpenAlex/CORE.
**Consequence:** ten department and unit hosts (ECE, AMS on two hosts, BME, CLSP, LCSR, Cognitive Science, Math, DSAI, Biostatistics) are `none`: v3 says challenged hosts are not used, not through Wayback either. Their listing slots stay in the charter for the record only.

## Gate
`atlas stage-gate jhu 0`: **fail, one open item**: "openalex snapshot: no works of I145311948". That is the snapshot extension, deliberately not run (owner D-decisions first; no credits needed, 25 minutes on 16 tasks).
Everything else passes (charter, 16 hosts consistent). `atlas stage-gate jhu --traps`: one finding, `captures` (no lab-page capture store yet), which is a stage 6-8 artefact and not a stage-0 item.
Main checkout: `git -C /n/fs/resemble/homogenizing-science/code status --short` shows nothing of this run (it shows `hierarchy/uchicago/tmp/` and `scratch/`, not mine). Untracked data files written by the tools: `hierarchy/jhu/{derived/hosts.json,raw/school-captures.sqlite,reports/new-school.json}` in the main data tree, plus the empty store `stores/jhu`.
Jobs: none submitted.

## Remaining decisions for the owner (see the report)
D1 challenged hosts; D2 related ids; D3 lineage children to exclude; D4 SAIS Bologna/Nanjing; D5 borderline departments; D6 `order`. All listed with recommendations in the coordinator report.
