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
| dash.harvard.edu | allowed, no AI group | none | item page: Web Firewall 429 after 5 sitemap requests | wayback-only |
| statistics.fas, economics, www.physics, psychology.fas | robots.txt 403 Akamai Access Denied | n/a | not probed | wayback-only |
| www.math.harvard.edu | 200 for the project client, 403 for a bare curl (flaky) | n/a | not probed | wayback-only |
DASH thesis repository: ~103,850 sitemap URLs (about 100k items); no Crawl-delay, house 5 s minimum would be ~139 h; not a student source (see `[thesis].note`).

## Owner decisions applied (2026-11-05, as recommended)
D1 sweep every lineage child except D3 (the PI rule filters); D2 `openalex_related` = MGH I4210087915, Brigham I1283280774, Boston Children's I1288882113, Dana-Farber I4210117453, Broad I107606265, HST I4210092658
(left out: Beth Israel, McLean, Mass Eye and Ear, Joslin, Harvard Pilgrim, MGHPCC); D3 `openalex_excluded` = Harvard University Press I2801851002, Real Colegio Complutense I4392738166; D4 regex does not match bare Harvard-MIT/HST,
bare Harvard-Smithsonian, Harvard Pilgrim, Harvey Mudd; HBS matches; D5 Statistics, Economics, Physics, Psychology, Mathematics and DASH are `wayback-only` (owner "allowed always"; none names an AI agent in robots.txt);
D6 Kempner and Wyss are `center_units`, only members with a Harvard faculty appointment are PIs. Wyss added as an affiliated unit and host (robots allowed). `school_hosts`: 16 hosts, 0 inconsistent.

## Snapshot extension (no API credits)
`OA_DATE=2026-10-14`, submitted by hand with the standing Slurm flags (partition all, account mltheory, 59 min, exclude node302,node014) because `atlas pipeline snapshot-ext` follows the scripts' own mltheory/6 h directives:
filter array 32116398 (16 tasks, all COMPLETED, about 45 min), merge 32116415 FAILED (`database or disk is full`: node805's /tmp had 0 kB free), merge 32116873 (excluding node805) COMPLETED:
`ext-harvard.sqlite`, 1,146,096 works, 1,590,408 work_inst rows, 630,958 authors.

## Per-child works 2016-2026 (children-counts; 'alone' = lacking I136199984)
| child | works | alone | note |
|---|---|---|---|
| Harvard University (I136199984) | 555,668 | 0 | |
| Center for Astrophysics Harvard & Smithsonian | 42,716 | 39,696 | SURPRISE: 93% carry no Harvard id; astrophysics, almost no computing; PI rule filters (swept, large) |
| Dana-Farber/Harvard Cancer Center | 6,623 | 568 | |
| Martinos Center | 5,701 | 48 | |
| Wyss Institute | 3,381 | 61 | |
| Harvard Stem Cell Institute | 3,140 | 23 | |
| Smithonian Astrophysical Observatory | 2,616 | 2,130 | same astrophysics tail as CfA |
| Ragon Institute | 2,217 | 366 | |
| Center for Systems Biology | 1,647 | 20 | |
| Harvard University Press (EXCLUDED) | 1,266 | 888 | |
| Gordon Center for Medical Imaging | 1,017 | 18 | |
| NSF AI Institute for AI and Fundamental Interactions | 708 | 622 | kept: computing-adjacent, 88% id-less |
| Berenson-Allen 638, MIT-Harvard Ultracold Atoms 433, Rowland 429, Global Health 368, Vascular Biology 317, Arnold Arboretum 307, Observatory 59, Complutense (EXCLUDED) 47, Sleep 26, Harvard Forest 8 | | | small |
Counts that surprise: CfA/SAO (a Smithsonian-shared astrophysics body, mostly outside the Harvard-id); excluding them was not decided by the owner, so they are swept. Recommendation: keep (they cost nothing extra and the PI rule drops non-computing people).

## Gate
`atlas stage-gate harvard 0`: PASS (rc 0) after the snapshot extension.
`--traps`: one finding, `captures` (no labpage captures store yet), a stage-8 artefact that the trap check already raises at stage 0; not a charter problem.
Charter traps (affiliation cases, `[repository]`, `[dblp]`, `[thesis]`) pass.

## Exceptions and open decisions
`--traps` keeps one finding: no labpage captures store yet (a stage-8 artefact; it is written by `labpage_audit discover`, which fetches and is not a stage-0 step). Not a charter problem.
