# Cornell onboarding, stage 0 - 2026-11-24

Cornell is registered as `cornell`, Cornell University, status `onboarding`, provisional `order = 41` (the coordinator sets it at landing),
`site_uni = cornell-university`. This registers the school and its sources; no PI, student, paper or website coverage is claimed.

## Scope

Owner decision D-0057 (`leases/coord/DECISIONS.md`) is binding: Ithaca campus with its statutory colleges and internal centres plus Cornell Tech NYC;
UCSD/NYU-style regex-only hospitals; census 2016-2026 including departed and retired faculty; computing faculty only.
OpenAlex I205783295, ROR https://ror.org/05bnh6r87 (GRAS 2025 CS&E rank 45), verified 2026-11-24 against the local 2026-10-14 institutions snapshot
(`oa_institutions.py search Cornell`, `lineage I205783295`; live ROR API not queried).

- Lineage children kept: the four statutory colleges (CALS I4210092791, ILR I4210098983, Human Ecology I4210144145, Veterinary Medicine I4210151139),
  Agricultural Experiment Station I4392738320, Atkinson Center I4387155861, Lab of Ornithology I4387153357, Cornell Tech I4405261073 and
  Weill Cornell Medicine I4387153466 (adds a PI only under the CS-related rule, Harvard/JHU precedent).
- Excluded: PARADIM I4387152773, New York Sea Grant I4210134430, New York Space Grant I4210141610 (all lineage children) and Weill Cornell Medical College
  in Qatar I4210152471 (a 'related' associate, not a child). The regex does not match the Qatar campus by name or by its domain (qatar-med.cornell.edu).
- Related, regex-only: Weill Cornell Medical Center I4405272987 (a lineage child, healthcare) and NewYork-Presbyterian I1340179700. Both are listed in
  `openalex_related`, so the snapshot filter gates them by the affiliation regex (UCSD precedent for lineage-child hospitals); they never add a PI.
  The task text said to sweep WCMC with the lineage "as Harvard does"; I chose the regex gate because D-0057 says regex-only and it is the stricter reading.
  Weill Cornell Medicine itself stays a plain lineage child. Bare "NewYork-Presbyterian" does not match (must_not_match).
- Not Cornell, never swept: MSKCC, Rogosin, Houston Methodist, Burke, the other 'related' hospitals, Museum of the Earth, Paleontological Research
  Institution, Hubbard Brook LTER, Great Lakes Research Consortium. D-0057's "Hospital for Special Surgery" is not in the lineage output; ignored.
- Look-alikes: Cornell College I145220665 (Iowa), Cornell Scott-Hill Health Center I4210151875, the county Cornell Cooperative Extension associations.
- Not in the lineage and not named in D-0057, so left out: Cornell High Energy Synchrotron Source I4387153242 and Cornell Feline Health Center
  I4405270756 (open question for the owner; their papers still credit through "Cornell University" strings).

## Charter checks

`school_config.py --check cornell`: ok. 30 must_match and 34 must_not_match cases: Cornell University spellings (Univ., Ithaca, DBLP note form),
Cornell Tech / Cornell NYC Tech, Bowers College, Sibley, Meinig, Weill Cornell Medicine/College/Medical Center, ILR/CALS/Vet statutory-college names,
AgriTech, Lab of Ornithology, e-mail and URL forms; and the traps: bare "Cornell", Cornell College, Cornell Scott-Hill, Cornell Cooperative Extension
counties, Cornell Dubilier, the Qatar campus (name, "Cornell University in Qatar", domain, e-mail), Ithaca College, bare Ithaca, TC3, bare
NewYork-Presbyterian, MSKCC, HSS, Rogosin, Houston Methodist, Burke, PRI, Museum of the Earth, PARADIM, Sea/Space Grant, Technion, Columbia, SUNY.
`check` does not apply `excluded_regex`, so the Qatar exclusions are built into the main regex as lookaheads and the domain lookahead; `excluded_regex`
repeats them for independent use. Bare "Cornell" is never matched; "Ithaca" appears only in `loose`.
CS is the only full-coverage department (its directory is the shared Bowers CIS Drupal directory with Information Science and Statistics and Data
Science). Information Science, Statistics and Data Science, ECE, ORIE, MAE, BME, CEE, Mathematics, Psychology, Linguistics, CALS Computational Biology,
Cornell Tech, the Weill Cornell Institute for Computational Biomedicine and Population Health Sciences are affiliated units (stage-2 discovery sources,
no automatic admission), as at UMD and UCSD.

## Host gate

`school_hosts.py cornell`: 19 hosts, 0 inconsistent. 13 live (all probes ok, no challenge, no group naming ClaudeBot or anthropic-ai), 6 wayback-only
(legacy hosts), 0 none. Crawl-delay is 2 s everywhere except phs.weill.cornell.edu (10 s). `icb.weill.cornell.edu` and the legacy `www.<dept>`
hosts return 404 for robots.txt (no rules). No AI-named blocks anywhere.
- Engineering departments moved to `www.duffield.cornell.edu/<dept>/faculty-and-staff/` (or `/faculty-staff/`); `www.ece|mae|bme|cee|orie.cornell.edu`
  now redirect there, so they are wayback-only legacy hosts. Probe correction: `www.orie.cornell.edu` redirects every path, so it is legacy too.
- Thesis repository eCommons (DSpace 7): robots `allowed` (no AI-named group; disallows /search, /browse, /entities); OAI-PMH `/server/oai/request`
  answered 200 to Identify.

## Gates

`atlas stage-gate cornell 0`: fails only on "openalex snapshot: no works of I205783295" until the snapshot extension merges (as UCSD/UIUC).

## Snapshot extension

Charter committed at `167a3b5a`; `OA_DATE=2026-10-14`, no API credits, node302/014/016/012 excluded (node016: /tmp full for ETHZ; node012: 15 of 16 tasks of the first run failed within 24 s there).
- First run: filter **32539132** -> merge 32539133, cancelled (15/16 tasks failed in 24 s on node012).
- Second run: filter **32539409** (16 tasks): 14 COMPLETED, tasks 1 and 14 TIMEOUT at the 59-min cap (the filter is not resumable; the 14 finished parts were kept). Merge 32539410 cancelled.
- Rerun of only tasks 1 and 14: filter **32540579** (COMPLETED in 44:42 and 40:24), merge **32540581** (afterok, COMPLETED in 4:28), commit pinned to `167a3b5a`.
- Result: `ext-cornell.sqlite` holds 446,085 works of I205783295. `atlas stage-gate cornell 0`: **pass** (0 open, 19 hosts).
Receipts: `scratch/pipeline-snapshot-ext-20261124-132938-096691/`.
