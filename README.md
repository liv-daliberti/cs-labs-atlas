# Homogenizing Science website

Two research pages, a dependency-free Node runtime, and an independently verified
publication bundle. This `website` branch is the **authoritative website source**.
People, CI, ChatGPT and Claude use the same commands. No assistant account is required.

## Fresh checkout → both pages

Requires Node 22.13+ and Python 3.11+. Run:

```sh
git clone --branch website https://github.com/liv-daliberti/cs-labs-atlas.git
cd cs-labs-atlas
npm ci
npm run dev
```

Open http://127.0.0.1:8787. This uses a small, clearly labeled synthetic dataset,
including the atlas, department, lab, student, paper and reader interactions.
It is test data, not scientific evidence. No research files or credentials are needed.

## Obtain and run the published research

```sh
npm run bootstrap -- --without-papers
ATLAS_DATA_DIR=outputs/publication npm start
```

The checked-in `deployment/bootstrap.json` pins a versioned catalogue by SHA-256.
Metadata downloads are split into verified parts. `--without-papers` gets the
atlas and records; stored paper buttons need the next step. For a full publication:

```sh
npm run bootstrap
```

The full paper library is approximately 84 GB. Downloads resume at verified object
boundaries; unchanged files are reused. Every object and archive part is checked
against the pinned checksum. Only currently admitted public paper copies are
retrievable; a later withdrawal can prevent restoring that paper from the host.
Keep an independent permitted archive if you need historical reproducibility.
The downloader never changes attribution decisions or substitutes different bytes.

## Develop and verify

```sh
npm test
npm run format:check
npx playwright install chromium firefox webkit
npm run dev
# another terminal
ATLAS_FIXTURE=1 npm run test:browser -- --grep 'synthetic fixture'
```

CI checks both real pages with synthetic data, Chromium desktop/mobile, Firefox,
WebKit, accessibility, failure/retry paths, and visual baselines. It builds **and
runs** the Docker image, then checks readiness and a stored paper. Browser traces,
screenshots and reports go under ignored `outputs/`. Update screenshot baselines
only after inspecting the intended UI change (`--update-snapshots`).

The six-school full-data suite also runs before release; synthetic CI is not a
substitute for the research evidence, scope and reader checks.

## Publish or operate

See [the publishing runbook](docs/PUBLISHING.md) for preparation, the test gate,
versioned downloads, staging, Docker deployment, smoke verification and rollback.
Anyone with a permitted data bundle and their own hosting access can publish a
copy. The existing public domain remains controlled by its hosting account.

| Source | Responsibility |
| --- | --- |
| `atlas/app.js` | Shared state, CS policy presentation, application initialization |
| `atlas/modules/` | Data loading, metrics, visualization, record rendering, navigation |
| `atlas/cs-departments.js` | Department browsing and evidence details |
| `lib/` | Content-addressed admission, checksums and byte-range transport |
| `portable/` | Node/Docker adapter, fixtures, readiness, smoke and browser tests |
| `scripts/` | Frozen research preparation, bootstrap, release gate and host synchronization |
| `schemas/` | Website data contract and compatibility rules |

Research code is maintained on `dev`. Hosting adapters consume this branch via
`scripts/sync-host.py`; do not edit a host and export it back over GitHub.
The existing Sites checkout retains only its platform-specific package, routes
and hosting configuration. Its publication uses the same tested website bytes.

Keep the attribution rules in `AGENTS.md`. Dataset, source, third-party code and
paper licenses retain their existing terms; access does not expand redistribution rights.
