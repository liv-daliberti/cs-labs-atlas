# Homogenizing Science website

The public website source for the CS research atlas: two HTML/JavaScript pages,
a small Node server, and a verified publication bundle. **No ChatGPT account,
AI assistant, Sites plugin, React framework, or runtime npm dependency is
required to run or publish this version.**

Anyone with the source, a permitted data bundle and access to their own hosting
can publish a copy. Access to the existing owner's domain is still controlled
by its hosting account. This repository does not grant that access.

## Run an existing publication

```sh
git clone --branch website https://github.com/liv-daliberti/cs-labs-atlas.git
cd cs-labs-atlas
ATLAS_DATA_DIR=/absolute/path/to/publication-bundle node portable/server.mjs
```

Open `http://127.0.0.1:8787`. Node 22.13+ is required. Change the listening
address with `HOST` and `PORT`. `/healthz` reports the loaded release ID.

The bundle contains `config.json`, `bundle.json`, and `objects/<sha256>` files.
It includes site assets and **only the paper files admitted by a frozen research
release**. The current complete library is about 84 GB, so data is distributed
separately from Git source. Obtain a verified bundle from the dataset maintainer
or build one from the accepted research release and stores below. The small CI
fixture is synthetic test data; it is not the research atlas.

## Publish using Docker and your hosting account

```sh
export ATLAS_DATA_DIR=/absolute/path/to/publication-bundle
docker compose -f portable/compose.yaml up --build -d
```

The container runs as an unprivileged user, mounts data read-only, and exposes
port 8787 on host loopback. Put your normal HTTPS reverse proxy in front of it;
`portable/Caddyfile.example` shows the three-line Caddy configuration. Point
your own domain at that server. Ensure the container user can read the bundle.
HTTPS is needed for the browser's checksum APIs outside localhost.

You can instead run the Node server under your existing process supervisor,
container platform or VM. `npm run build` creates a small `dist/` with the
runtime code; run `node dist/portable/server.mjs` with `ATLAS_DATA_DIR` set.
The Docker image contains code only; a publication bundle is mounted separately.

Updates are immutable bundle deployments: build a new directory, verify it,
change `ATLAS_DATA_DIR`, and restart. Keep the prior bundle for rollback, but
review its paper permissions before re-exposing older files. There are no
public maintenance/upload endpoints in this server, and no shared write token
is needed to publish. Use normal SSH/container/platform access to deploy.

## Build a publication from accepted research

Research code lives on the repository's `dev` branch. Its `atlas release
--target site` command freezes accepted research without deploying it. Never
publish active working packages or bypass the evidence and attribution gates.

The website authoring checkout needs the retained atlas data plus the exact
frozen release and paper stores. Large data is not in this Git branch. With
those inputs available:

```sh
npm ci
python3 scripts/release.py prepare --release 2026-11-02 \
  --releases-dir /data/releases --stores /data/stores
python3 scripts/bundle-site.py \
  --release-dir /data/releases/2026-11-02 --stores /data/stores \
  --output /data/publications/2026-11-02 --verify-papers
```

Preparation checks release hashes, hierarchy, scope, reader decisions,
authentication/transport regressions and the build. The bundler requires the
exact prepared asset bytes and frozen reader allowlist, then creates a new
directory atomically. It refuses to replace an existing publication.

`--verify-papers` checks every paper hash while building; the server also checks
each object before serving it and rechecks changed files. Copy mode is the
default and gives an independent bundle. `--mode link` is a space-saving,
same-filesystem preview option: it shares source inodes, so do not edit those
files or use it as an independent archival copy. No paper files are added to Git.

The original Sites deployment remains supported in the maintainer's authoring
checkout. `upload` and `ready` in `scripts/release.py` belong to that adapter;
they are not needed for the Node/Docker deployment described here. The portable
server uses the same allowlist, range and checksum implementation.

## Develop and test

```sh
npm ci
npm test
npm run format:check
npx playwright install chromium
```

For browser tests against a complete publication, start the server with its
bundle and run `npm run test:browser`. `ATLAS_BASE_URL` selects a different
server. Tests cover desktop/mobile navigation, six-school switching, search,
keyboard lab selection, deep links, student filters, reader opening, downloads
and viewport overflow. The full suite requires the six-school dataset.

CI needs no research data or credentials:

```sh
npm run fixture
ATLAS_DATA_DIR=outputs/fixture node portable/server.mjs
# In another terminal:
ATLAS_FIXTURE=1 npm run test:browser -- --grep 'synthetic fixture'
```

The synthetic test uses the actual department page and reader code, including
hidden-lab rules and XML rendering. HTTP tests cover ranges, caching, withdrawn
papers, checksum tampering, traversal, and the absence of write endpoints.
Reports and failure screenshots/traces go under `outputs/` and are ignored by Git.

| Path | Responsibility |
| --- | --- |
| `atlas/` | The two pages and their browser code/styles |
| `lib/atlas-storage.mjs` | Release admission, HTTP caching, byte ranges and paper serving |
| `lib/chunked-graph.mjs` | Bounded streaming of verified storage chunks |
| `portable/file-bucket.mjs` | Read-only filesystem adapter with SHA-256 verification |
| `portable/server.mjs` | Node HTTP adapter; no framework or platform authentication |
| `scripts/` | Release preparation, bundling and regression checks |
| `deployment/` | Pinned research ID and asset manifest; no credentials |

The `website` branch is exported from the maintained website checkout using
`scripts/export-website.py`. The exporter selects current code explicitly and
excludes old collection/import scripts, provider scaffolding, runtime data,
credentials and private deployment receipts. It does not push or deploy.

Preserve attribution rules in `AGENTS.md`. The research dataset, publication
licenses and third-party code notices retain their own terms; source access
does not grant additional rights to redistribute papers.
