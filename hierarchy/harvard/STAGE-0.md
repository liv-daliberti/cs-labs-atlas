# Harvard University: stage 0 (charter and config), 2026-11-05

Protocol v3 (branch `agent/harvard` from `agent/protocol-v3` d913624). No OpenAlex API credits, no Slurm jobs, no Wayback fetching beyond the access check were used.

## Owner decision recorded (2026-11-05, relayed by the coordinator)
Keep ONLY labs that do computing. Medical School, hospitals (MGH, Brigham, Dana-Farber, Boston Children's), Broad, Wyss, Kempner and the other Harvard units have no blanket keep or drop: a unit
counts only through its computing labs (faculty meeting the CS-related scope rule, docs/RULES.md). Their affiliation strings stay in `loose` / `own_units` so papers of in-scope computing PIs
are credited; they never add a PI or lab alone. A PI is a Harvard faculty member; research staff of an affiliated institute without a Harvard appointment are not PIs.

## Done
- `atlas new-school harvard`; the whole charter `schools/harvard.toml` filled: ids (lineage I136199984, ROR 03vek6s52 verified against api.ror.org v2), affiliation regex with 12 `must_match` and 16 `must_not_match`
  cases, `loose`, `own_units`, `[dblp]` strings, `[census]` home units and rank words, departments (SEAS Computer Science, full), 6 affiliated units, `[thesis]`, `[students]`, `[collector]`, `[repository]` (DASH), 15 hosts.
- `school_config --check harvard`: ok. `school_hosts harvard`: 15 hosts, 0 inconsistent.
- OpenAlex lineage read from the snapshot (`oa_institutions.py lineage`): 22 lineage children, ~24 related. Harvard Medical School, SEAS, Kennedy, Kempner, Radcliffe and HBS are NOT institutions in OpenAlex (they roll up to I136199984);
  `children-counts` prints 0 works everywhere because the filtered snapshot predates the charter (the extension is the next step).

## Host access (probed 2026-11-05, client `HomogenizingScienceResearch/0.2`)
| host | robots | crawl delay | probe | use |
|---|---|---|---|---|
| web.archive.org | 404 (none) | house 2 s | ok | live |
| seas.harvard.edu | allowed (Drupal defaults) | none | ok | live |
| dbmi.hms.harvard.edu | allowed | none | ok | live |
| hsph.harvard.edu | allowed (names GPTBot, ChatGPT-User only) | none | ok | live |
| www.hks.harvard.edu, www.mcb.harvard.edu, kempnerinstitute.harvard.edu | allowed | none | ok | live |
| dash.harvard.edu | allowed, no AI group | none | item page: Web Firewall 429 after 5 sitemap requests | none |
| statistics.fas, economics, www.physics, psychology.fas | robots.txt 403 Akamai Access Denied | n/a | not probed | none |
| www.math.harvard.edu | 200 for the project client, 403 for a bare curl (flaky) | n/a | not probed | none |
DASH thesis repository: ~103,850 sitemap URLs (about 100k items); no Crawl-delay, house 5 s minimum would be ~139 h; not a student source (see `[thesis].note`).

## Gate
`atlas stage-gate harvard 0`: FAIL, one open item: the OpenAlex snapshot holds no works of I136199984 (needs `snapshot-ext` after the charter is committed and D1-D3 are decided; ~25 min, no credits).
`--traps`: one finding, `captures` (no labpage captures store yet), a stage-8 artefact that the trap check already raises at stage 0; not a charter problem.
Charter traps (affiliation cases, `[repository]`, `[dblp]`, `[thesis]`) pass.

## Exceptions and open decisions
See the report to the coordinator: D1 children to sweep, D2 related set, D3 exclusions, D4 HBS/HST/CfA, D5 blocked FAS hosts, D6 Kempner/Wyss/CfA computing coverage.
`openalex_related` / `openalex_excluded` are left EMPTY in the charter until the owner answers (proposals are in comments).
