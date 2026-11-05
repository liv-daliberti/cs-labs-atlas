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
`atlas stage-gate washu 0`: **fail, one open item**: `openalex snapshot: no works of I204465549`. Everything else passes (charter, 13 hosts). The snapshot extension
(`atlas pipeline snapshot-ext SCHOOLS=washu --from-worktree`, 16 filter tasks + merge, about 25 min, no credits) needs the committed charter and the owner D-decisions below (the related and excluded ids change what it filters);
it is the coordinator's to schedule next, not run here (no Slurm in this run). Not waived.
`atlas stage-gate washu 0 --traps`: one finding, `captures: neither raw/labpage-captures.sqlite nor ... exists`: a stage-8 file that cannot exist at stage 0 (proposed tool fix: run `captures_traps` from stage 8, not at stage 0).

## Decisions for the owner (before the first sweep)
D1 lineage children; D2 related institutions; D3 excluded ids / look-alikes; D4 Washington University School of Law; D5 borderline departments; D6 thesis repository. Recommendations are in the coordinator report.
Under the scope decision above no blanket unit keep/drop is needed; what remains is which institution ids the sweep reads.
