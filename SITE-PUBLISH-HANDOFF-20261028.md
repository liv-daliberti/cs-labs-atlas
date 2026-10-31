# Site publication handoff: Stanford + hidden zero-paper labs (2026-10-28)

> **Public access enabled October 29, 2026 (owner request):** Both pages now load without sign-in. Maintenance endpoints require a separate Sites runtime secret and reject anonymous GET/HEAD/PUT requests. Public-ready source commit: `f7917f841aa6337d342dea3b566796a2d0f554f1`; deployment `appgdep_6ae3380564c881919f2a6725d9433800` succeeded. This supersedes the owner-private audience notes below.

> **Published October 29, 2026:** Option A (the two-page site) is now live at https://homogenizing-science.ldaliberti.chatgpt.site, with owner-only access preserved. Stanford is included; the six detailed schools show 1,469 PI labs with papers, and ten zero-paper PI labs retain reviewed hidden reasons. The CS atlas and CS departments directory are the only pages. Saved abstracts, existing reader mappings, the live storage runtime, and October 23 source evidence were preserved.
>
> Source checkout: `/n/fs/resemble/homogenizing-science/site`; pushed commit `dca30ecbb2e69a08e29203e0b135428cbb5828c0`. Deployment `appgdep_6ae336403f7881919ae387d969d11698` returned **succeeded**. Hierarchy, scope, two-page links, abstract interactions, metadata, storage and build checks passed. No visual browser verification was available. The original preparation notes below are retained for history.

The owner approved publishing on 2026-10-28. Claude has no Sites credential, so the upload has to run through the Sites
workflow (Codex's plugin, with the service credential on hidden stdin).

## What is ready
- **Where:** `/n/fs/resemble/homogenizing-science/archive/site-history/princeton-live-20261015`, branch `claude/cs-audit-20261016`. Nothing pushed or published.
- **Commit `23e888ab`:** records the previously uncommitted state of the 330 files the change touches (the 10-22 two-page /
  "PI labs with papers only" work and the 10-26 data build). Squash it into the next commit if preferred.
- **Commit `1ecafb5a`:** Stanford as the 6th school, and zero-paper PI labs hidden with reasons (29 files).
  - Builder: `scripts/build-cs-hierarchy.py`. Stanford has id `stanford-university`. CS is covered in full; EE counts as a
    home department not covered in full; other computing faculty go under their reviewed home department.
  - Data: `atlas/data/cs-hierarchy/{6 schools}.json.gz`, `index.json` (adds `hiddenLabs` and `hiddenLabsFile`) and
    `hidden-labs.json` (new: PI, department, category, verdict and reason per hidden lab). The build stops if a zero-paper
    lab has no ledger row.
  - Pages: `atlas/cs-departments.{js,html}`, `atlas/app.js`, `atlas/index.html`.
  - Also: `atlas/data/cs-pi-labs/*.json.gz` (6 files), `atlas/data/universities/stanford-university.json.gz`,
    `atlas/data.json`, `atlas/data/cs-metrics.json.gz`, `atlas/downloads/cs-hierarchy-labs.csv`,
    `scripts/build-cs-scope.py`, `scripts/cs_scope.py`, the tests and `AGENTS.md`.
- **Shown / hidden PI labs:**
  - Princeton 137 / 3: Bhattacharjee joined_after_window; Schapire no_appointment_coverage; LaPaugh no_output_found.
  - CMU 456 / 2: Scherlis identity_unanchored; Randi Williams no_school_affiliation.
  - EPFL 167 / 2: Shokrollahi no_school_affiliation; Decotignie not_in_school_sweep.
  - MIT 275 / 2: Terman no_output_found; Sipser no_school_affiliation.
  - Berkeley 202 / 1: Barsky no_output_found.
  - Stanford 232 / 0.
  - All 10 hidden labs carry the reviewed verdict zero_is_right.
- **Tests that pass:** `scripts/test-cs-hierarchy.py`, `node scripts/test-cs-departments-page.mjs`,
  `scripts/test-cs-scope.py`, `tests/test_princeton_library_overlay.py`, `tests/test_sweep_metadata.py`.
- **Tests that fail, and failed before this change:**
  - `scripts/test-site-pages.py`: the `data/local-papers.json` digest, after another session's uncommitted 11:39 edit
    that didn't update `data.json`.
  - `tests/test_affiliations.js`: it needs a removed page's bundle.

## How live differs
- **The live checkout** (`catalogue-publish-20261021`, v144/v145) is older. Its atlas shows inventory CS units (9,799) across 53
  pages and doesn't read `cs-hierarchy` or `cs-pi-labs`. Only its `cs-departments.js` reads `cs-hierarchy`, and it
  already hides zero-paper labs.
- **Live `scripts/build-cs-hierarchy.py`** reads a frozen copy at `research/release-20261023/hierarchy` (5 schools).
- **Live abstracts:** live papers carry `abstractFile`/`abstractKey` from `scripts/enrich-overnight-abstracts.py`
  (`data/cs-abstracts/<school>.json.gz`), matched by position (`paperIndex`). Rebuilt files are ordered differently,
  so the abstracts must be re-matched by OpenAlex id.
- **Live `cs-departments.js`** accepts abstract files only for princeton, cmu, epfl, mit and berkeley.

## Option A: the owner's 10-22 decision (two pages, PI labs with papers only)
Publish princeton-live-20261015 as the site source through the Sites workflow:
1. Fix the `local-papers.json` digest: register the other session's edit, or restore the file.
2. Decide what happens to the staged page deletions and the other uncommitted edits.
3. Port the live-only additions: abstracts re-matched by OpenAlex id, and the 10-23 release content.

## Option B: minimum change to live
1. In live `scripts/build-cs-hierarchy.py`, port from princeton-live: the Stanford entries (`SCHOOLS`, `FULL_CODES`,
   `CORE`, and the `department()` branches), `LEDGER`, `CATEGORIES`, `hidden_labs()` and the main-block writes.
2. Freeze `hierarchy/{stanford,cmu,epfl,mit,...}`, `home-departments.json` and `zero-paper-labs.json` (from
   `.research-sweeps/claude-schools-20261021/hierarchy`) under a new `research/release-<date>/hierarchy`, and point `H`
   at it.
3. Rebuild, then re-match the abstracts by OpenAlex id.
4. Add `stanford` to the abstract-file pattern in `cs-departments.js`.
5. Add Stanford to the method text in `cs-departments.html`.
6. Run `scripts/build-cs-scope.py`.

## Checks before publishing (AGENTS.md / README)
- **Build order:** `build-cs-hierarchy.py`, then `build-cs-scope.py`, then `node scripts/source-atlas-assets.mjs pack`.
- **Tests:** `scripts/test-cs-scope.py`, `scripts/test-site-pages.py`, `scripts/test-cs-hierarchy.py` and
  `node scripts/test-cs-departments-page.mjs`, plus the attribution, identity, people and storage checks.
- **Privacy:** the site stays owner-private, and the update endpoint stays non-public.
- **Storage:** `lib/atlas-release.json` is in r2 mode. Upload and confirm the new objects before the manifest changes
  (`node scripts/prepare-atlas.mjs atlas r2`, Sites workflow).
