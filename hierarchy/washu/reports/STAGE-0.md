# Washington University in St. Louis, stage 0: charter and config

Date: 2026-11-05. Protocol: `docs/ADDING-A-SCHOOL.md` v3.0. Branch `agent/washu` (from `agent/protocol-v3` d913624; not landed). Status stays `onboarding`.
Scope of this run: the "Before you start" checklist and stage 0, no OpenAlex credits, no Slurm jobs, one Wayback probe (the host gate's own).

## Owner scope decision (2026-11-05, relayed by the coordinator)
Keep ONLY labs that do computing. No blanket keep or drop of the School of Medicine, Barnes-Jewish, St. Louis Children's, Siteman, Olin or any other WashU unit:
a unit counts only through its computing labs, i.e. faculty who meet the CS-related scope rule (`docs/RULES.md`; DBLP-indexed / CS-venue work, e.g. I2DB, biostatistics and
informatics faculty who publish in CS venues). Non-computing labs are out. The units' affiliation strings stay in `loose` / `own_units` so papers of in-scope PIs who list them are
credited; they never add PIs or labs. A PI is a faculty member of the school. The look-alike exclusions are identity, not scope and always apply. Recorded at the top of `schools/washu.toml`.

## What was done
- `atlas new-school washu`; `schools/washu.toml` filled whole (v3 item 6): ids, web, affiliation regex + 13 `must_match` / 20 `must_not_match` cases, `loose`, `own_units`,
  `[dblp]`, `[census]` (home_units for 9 units, rank_words), departments CSE (full), ESE and BME (affiliated), affiliated units SDS, MATH, OLIN, PBS, I2DB, BIOS, `[thesis]`,
  `[collector].channels` (the script's default list, written out), `[students]`, `[labpages]`, `[repository]`, `[store]`, 13 `[[hosts]]`.
- `school_config.py --check washu`: ok (every case passes).
- **Ids** (filtered snapshot institutions table, no API credits): WashU `I204465549`, ROR `01yc7t268`, lineage itself only. Lineage children: Washington University Physicians `I4387155636`,
  Tyson Research Center `I4405285149`, Taylor Family Institute for Innovative Psychiatric Research `I4392738227`, Children's Discovery Institute `I4210122064`. Associated, not lineage:
  Barnes-Jewish Hospital `I1299725459` (parent BJC HealthCare `I1328499231`), St. Louis Children's `I1324021844`, Siteman Cancer Center `I4390039355`, WU Medical Center `I4210135078`,
  Central Institute for the Deaf `I2802002475`, Taylor Geospatial Institute `I4402554118` (consortium). Musculoskeletal Research Center `I4405268834` is a WashU unit with its own lineage.
  The School of Medicine has no separate institution (its authorships carry the university id). `children-counts` shows 0 works for all: the snapshot does not hold WashU yet.
  ROR relationships were not looked up (no network call to api.ror.org; its robots.txt answered 403 to the gate).
- **Domain move:** wustl.edu 301s to washu.edu (2023-24) for cse, ese, bme, sds, math, olin, medicine, www, openscholarship; `psychology.wustl.edu`, `statistics.wustl.edu`, `bios.wustl.edu`
  and `pbs.*` do not resolve; Psychology is `psych.washu.edu`; `biostat.wustl.edu` redirects to an unresolvable host; i2db.wustl.edu and sites.wustl.edu stay on wustl.edu.
  The CSE/ESE/BME listing slots are **provisional** (wustl.edu era to 2023, washu.edu from 2024, path `faculty-research/directory.html`); stage 1 fixes the eras from the 2016 homepage links.
- **Hosts** (`school_hosts.py washu`): 13 hosts, 0 inconsistent, no probe challenge, no robots rule naming ClaudeBot / anthropic-ai / Claude-Web anywhere (table in the coordinator report).
  The tool's 2.0 s crawl delay is its floor; robots.txt itself sets `crawl-delay: 1` only on sds.washu.edu and `Crawl-delay: 30` only for the `cludo` group on i2db/sites.wustl.edu.
- **Thesis repository:** WashU Scholarly Repository (formerly Open Scholarship; bepress Digital Commons) at repository.library.washu.edu. `Disallow: /do/` closes the OAI-PMH endpoint to us,
  `/cgi/` scripts disallowed, record pages and sitemaps allowed, no Crawl-delay. ETD sitemaps: `eng_etds` 1,366 records, `art_sci_etds` 3,472; at a 10 s courtesy delay of our own that is 3.8 h
  and 13.4 h. Pilot of an advisor line is stage 6's.

## Gate
(superseded by the update below) `atlas stage-gate washu 0`: fail, one open item: `openalex snapshot: no works of I204465549`. Everything else passes (charter, 13 hosts). The snapshot extension
(`atlas pipeline snapshot-ext SCHOOLS=washu --from-worktree`, 16 filter tasks + merge, about 25 min, no credits) needs the committed charter and the owner D-decisions below (the related and excluded ids change what it filters);
it is the coordinator's to schedule next, not run here (no Slurm in this run). Not waived.
`atlas stage-gate washu 0 --traps`: one finding, `captures: neither raw/labpage-captures.sqlite nor ... exists`: a stage-8 file that cannot exist at stage 0 (proposed tool fix: run `captures_traps` from stage 8, not at stage 0).

## Owner decisions (2026-11-05, all as recommended by the agent; applied in the charter comments)
1. D1: the four lineage children are swept (Washington University Physicians, Tyson Research Center, Taylor Family Institute, Children's Discovery Institute).
2. D2: `openalex_related` = Barnes-Jewish I1299725459, St. Louis Children's I1324021844, Siteman I4390039355, WU Medical Center I4210135078, Musculoskeletal Research Center I4405268834; Central Institute for the Deaf stays unswept.
3. D3: `openalex_excluded` = Taylor Geospatial Institute I4402554118, Washington University of Virginia I4405285522.
4. D4: the School of Law matches the regex (out of computing scope anyway).
5. D5: CSE is the department; ESE and BME affiliated departments; SDS, MATH, OLIN, PBS, I2DB, BIOS affiliated units under the CS-related rule.
6. D6: `[thesis].kind = "none"` until a 20-record pilot in stage 6 shows advisor lines.

## Snapshot extension and final gate (2026-11-05)
Jobs (partition all, account mltheory, 59 min, `--exclude=node302,node014`, `sbatch --test-only` showed no Preempts): filter array **32116375** (16 tasks, `OA_EXT=washu`, `OA_DATE=2026-10-14`, `--from-worktree`, commit 97838e8),
merge **32116393**; all COMPLETED (exit 0:0). Submitted by hand with `atlas submit` (not `atlas pipeline snapshot-ext`) because the pipeline hardcodes `--time=06:00:00`, which routes to mltheory with a start estimate of the next day and has no `--exclude`. No OpenAlex credits.
`atlas stage-gate washu 0`: **pass** (13 hosts, 284,817 snapshot works). `atlas stage-gate washu 0 --traps`: exit 1, one finding only: `captures: neither raw/labpage-captures.sqlite nor raw/labpage-audit-captures.sqlite exists`
(a stage-8 file that cannot exist at stage 0; shared-tool fix proposed in the coordinator report, not made here).

### `oa_institutions.py children-counts washu` (works 2016-2026 in snapshot + extension)
| institution | works tagged | of which the work lacks WashU's own id |
|---|---|---|
| WashU (I204465549) | 128,548 | - |
| Washington University Physicians (I4387155636) | 24 | 15 |
| Tyson Research Center (I4405285149) | 83 | 5 |
| Taylor Family Institute (I4392738227) | 243 | 4 |
| Children's Discovery Institute (I4210122064) | 1 | 0 |
The related ids are not in this table (regex-only, not lineage). Surprises: none large. WashU Physicians is a clinical-practice entity with 24 works, 15 of them lacking the university id: negligible, and any author on them is a medical faculty member who needs CS-related evidence to count.
