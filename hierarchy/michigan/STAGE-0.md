# Michigan, stage 0: charter and config

Date: 2026-10-29. Protocol: `docs/ADDING-A-SCHOOL.md` (v1, revised during this run). Gate: **passed, with two owner
decisions open** (below).

## What was done
- **Charter:** `schools/michigan.toml`, from `schools/TEMPLATE.toml` (new). `python tools/school_config.py --check michigan`
  passes. Its checks cover the required fields, the id formats, and the affiliation regex against 10 `must_match` and
  11 `must_not_match` strings.
- **Charters for the six released schools.** `schools/{princeton,cmu,epfl,mit,berkeley,stanford}.toml` restate what the
  builder's tables say: institution id, ROR, affiliation regex, DBLP sweep, own units, computing departments and the
  site department map. `tests/test_school_config.py` asserts they agree with `pi_hierarchy.py`.
  - `atlas_paths.SCHOOL_IDS` is now the released charters in `order`. The list is unchanged, and `paths.sh` was
    regenerated.
  - Michigan has `status = "onboarding"`, so it stays out of the build, the release and the tree until stage 10.
- **Identifiers.** Verified with `api.openalex.org/institutions` and `api.ror.org`, 2026-10-29.
  - University of Michigan: OpenAlex `I27837315`, ROR `00jmfr291`. Its lineage is itself only.
  - Dearborn (`I4210130704`) and Flint (`I4210092198`) have their own lineage, so the lineage filter excludes them.
    They are recorded as `openalex_excluded`.
  - Michigan Medicine (`I4210114445`, ROR `01zcpa714`) is a *related* institution, not a child. It is swept as
    `openalex_related` (see decision 1).
- **Store.** `/n/fs/resemble/homogenizing-science/data/fulltext/michigan` holds `catalog.sqlite` (schema copied from
  Stanford's catalog, no works yet), `objects/` and `discovery/`. It is linked as `/n/fs/resemble/cs-atlas/stores/michigan`.
- **Package directory.** `hierarchy/michigan/` exists. Its `tmp/` subfolder is ignored by git.
- **Hosts.** `python tools/school_hosts.py michigan` checked 16 hosts against robots.txt and probed each live one
  (`hierarchy/michigan/hosts.json`). Result: 16 hosts, 0 inconsistent.

| host | robots | probe | use |
|---|---|---|---|
| web.archive.org | allowed (no robots.txt) | ok | live (Wayback `id_`) |
| cse.engin.umich.edu, ece.engin.umich.edu | allowed, Crawl-delay 10 | **Cloudflare challenge** | wayback-only |
| www.si.umich.edu, lsa.umich.edu, ioe.engin.umich.edu, medschool.umich.edu, sph.umich.edu, michiganross.umich.edu | allowed | **Cloudflare challenge** | wayback-only |
| web.eecs.umich.edu | unreachable (TLS verification fails) | not fetched | wayback-only |
| robotics.umich.edu | allowed | ok | live |
| deepblue.lib.umich.edu, news.umich.edu, record.umich.edu | **disallows ClaudeBot, anthropic-ai and Claude-Web by name** | not fetched | none |
| api.openalex.org, api.ror.org | allowed | not probed | live |

- **Shared tools now read the charters.** `oa_sweep.py` (lineage plus related ids, OR-ed), `cs_related_candidates.py`,
  `dblp_dump_persons.py` (includes onboarding schools), `listed_not_in_census.py` (computing departments, lineage ids,
  regex), `student_audit.py`, `zero_paper_ledger.py`, `link_sweep.py`, `school_profiles.py` and `listings/scripts/wb.py`.
  `listings/scripts/plan_fetch.py` falls back to the charter's listing slots when there is no `config_<key>.py`.
- **New tools.**
  - `tools/school_config.py` reads and checks the charters.
  - `tools/school_web.py` is the polite Wayback and live client, generalized from Stanford's `st_web.py`. It detects
    Cloudflare challenges and robots rules that name AI agents.
  - `tools/school_hosts.py` is the stage-0 host gate.
  - `tools/dblp_affiliated.py` finds dump persons whose affiliation note or URL names the school.
  - `tools/listing_formats.py` and `tools/listing_rows.py` are used in stages 1–2.
- **Started early.** Both are inputs to stages 2 and 7.
  - The OpenAlex sweep (`hierarchy/michigan/run_sweep.sh`) stopped at once: the shared key had 492 credits left today.
    `hierarchy/michigan/sweep_daily.sh` reruns it after each 00:00 UTC reset until 2026 is stored.
  - The DBLP affiliation pass found 904 persons (721 by affiliation note, 10 by URL only, 173 by both).

## Counts
7 charters (6 released, 1 onboarding); 16 hosts (2 usable live, 1 Wayback, 10 Wayback-only, 3 none); 904 DBLP persons.

## Gate
- Every host named in the charter was checked against its robots.txt. None that the charter marks `live` served a
  challenge. **Pass.**
- The charter is reviewed and committed. **Pass**: commit `bbfe406`, with the listing slots added in stage 1.

## Exceptions and owner decisions
1. **Michigan Medicine as a related institution (decision requested).**
   - Michigan's health system is not in the university's lineage, unlike Stanford's (`Stanford Health Care` is a child
     of `I97018004`).
   - The sweep includes `I4210114445`. An authorship tagged only with Michigan Medicine counts for Michigan only when
     its raw affiliation string matches the regex (for example "University of Michigan Medical School"). Dropping it
     would lose Computational Medicine and Bioinformatics and other Medical School PIs whose works OpenAlex tags only
     with the health system.
2. **Deep Blue (decision requested).**
   - `deepblue.lib.umich.edu/robots.txt` allows `*` but disallows ClaudeBot, anthropic-ai and Claude-Web by name. It
     also says `Content-Signal: ai-train=no, use=reference`.
   - This project's fetchers are Claude agents, so Deep Blue is not used: not live, not through OAI-PMH or REST, and not
     through its Wayback captures. The same applies to news.umich.edu and record.umich.edu.
   - Stage 6 falls back to the CSE and ECE defence announcements and the PhD and alumni lists (Wayback), and to lab
     pages.
   - If the owner reads the robots file differently (for example: the named agents are training crawlers, and a
     metadata inventory under the project's own User-Agent is fine), Deep Blue's OAI-PMH endpoint is the best student
     source.
3. **Wayback for challenged hosts.**
   - Every umich.edu web host except robotics.umich.edu sits behind a Cloudflare challenge. The live hosts are not used
     again (`captures/michigan.sqlite` table `blocked`).
   - Their pages are read from Wayback `id_` captures, which the protocol prefers anyway. This is recorded as a
     judgement, not a workaround: the archive is a separate public host, and nothing is fetched from the challenged
     hosts.

### Owner decisions, 2026-10-30 (all five accepted as recommended)
1. Michigan Medicine: an authorship tagged only with Michigan Medicine counts when its raw affiliation string names the
   University of Michigan (the `[affiliation].regex` rule above). **Decided.**
2. Deep Blue, news.umich.edu and record.umich.edu: not used in any form, Wayback included. **Decided.**
3. Challenged umich.edu hosts: read only from existing Wayback `id_` captures. **Decided.**
4. Courtesy appointments count as PIs (19 PIs). Stage 3 no longer rests on a pending decision. **Decided.**
5. The ambiguous computing-related acceptances (8 ECE, 4 Mathematics) are settled by the OpenAlex computing-share test
   in stage 2, now that the sweep has finished (2026-10-29 20:51 EDT).
