# Publication runbook

This procedure is shared by human maintainers, CI and any assistant. GitHub's
`website` branch is the source of truth. Research is frozen on `dev` with
`atlas release --target site`; use an exact accepted release ID, never a moving
working package. A website edition may improve presentation without changing the
underlying frozen research release.

## Prepare

From a clean `website` checkout, install `npm ci` and
`python3 -m pip install -r requirements-publishing.txt`. Bootstrap metadata using
`npm run bootstrap -- --without-papers --authoring` to run an existing publication. To build
new research, retain the atlas authoring data plus the frozen release and paper
stores. The bootstrap restores the published atlas inputs without replacing local code; the exact accepted research release and stores are separate research inputs.

```sh
python3 scripts/release.py prepare --release 2026-11-02 \
  --releases-dir /data/releases --stores /data/stores
```

Preparation checks the frozen hashes and evidence gates, builds the hierarchy,
reader and scope exports, validates the data contract and runs regressions.
`deployment/release.json` pins the research; asset manifests pin the website.

## Versioned data distribution

Choose a new website tag; never overwrite an existing publication directory.
After preparation, package metadata and paper download descriptors:

```sh
python3 scripts/data-package.py --tag web-2026-11-03.1 --origin https://YOUR-HOST
node scripts/prepare-atlas.mjs atlas r2
```

Copy the generated asset manifest named by `lib/atlas-release.json` from
`atlas-storage/releases/` to `deployment/asset-manifest.json`. The package command
writes a pinned `deployment/bootstrap.json`. Preserve old versioned download
parts when preparing subsequent editions. These are ordinary static assets
served by either hosting adapter; they require no platform-specific download API.

For a single command covering preparation, packaging and the release gate:

```sh
python3 scripts/publish.py release --release 2026-11-02 \
  --releases-dir /data/releases --stores /data/stores \
  --edition web-2026-11-03.1 --origin https://YOUR-HOST \
  --bundle /data/publications/web-2026-11-03.1
```

## Validate the exact publication

```sh
python3 scripts/bundle-site.py --release-dir /data/releases/2026-11-02 \
  --stores /data/stores --output /data/publications/web-2026-11-03.1 --verify-papers
python3 scripts/publish.py validate --bundle /data/publications/web-2026-11-03.1
python3 scripts/publish.py check --bundle /data/publications/web-2026-11-03.1
```

`validate` runs unit checks, formatting, the runtime build, readiness, a paper
checksum smoke test and the six-school browser suite. It copies the runtime
into `bundle/code/` and tests that copy. The receipt binds source, runtime,
configuration and asset hashes. `check` refuses changed or untested inputs.
Run all four browser projects on a machine with the required browser libraries;
`--projects desktop mobile` is available for a constrained local review, with
cross-browser CI still required. The receipt records exactly which projects ran.

Copy bundles are independent. `--mode link` on the bundler is only for local
previews when disk duplication is impractical; activation refuses these bundles.
Never mutate sources linked into a preview. Store artifacts on read-only storage.

## Docker or managed Node deployment

```sh
export ATLAS_DATA_DIR=/data/publications/web-2026-11-03.1
docker compose -f portable/compose.yaml up --build -d
npm run smoke -- https://YOUR-HOST EXPECTED_MANIFEST_SHA256
```

Serve HTTPS through your normal reverse proxy (`portable/Caddyfile.example`).
Use the code inside the verified bundle for production:
`node /srv/atlas/current/code/portable/server.mjs`, with
`ATLAS_DATA_DIR=/srv/atlas/current`. The server resolves the symlink at startup,
so in-flight requests keep using the old publication until restart.

For an existing service, activation changes `current` atomically, restarts it,
and checks the exact manifest and a hosted paper. A failed smoke test restores
the previous symlink and restarts the prior service.

```sh
python3 scripts/publish.py activate --bundle /data/publications/web-2026-11-03.1 \
  --root /srv/atlas --restart-command '["systemctl","restart","atlas"]' \
  --origin https://YOUR-HOST
python3 scripts/publish.py rollback --root /srv/atlas \
  --restart-command '["systemctl","restart","atlas"]' --origin https://YOUR-HOST
```

Review withdrawn-paper permissions before rolling back data. Routine code-only
rollbacks should retain the current research allowlist. Source checks are required
before a new release; rollback checks the previously tested artifact's own bytes.

## Existing Sites adapter

After committing the canonical source:

```sh
python3 scripts/sync-host.py /path/to/site-adapter
```

This refuses conflicting host edits and preserves provider configuration. Copy
prepared atlas data/downloads and transport chunks into the adapter without
changing their bytes. Build the native adapter and run its checks. Before upload,
run the canonical `publish.py check` gate. Upload admitted objects with
`upload-atlas.py --reader-release /data/releases/2026-11-02 --stores /data/stores
--only-unverified`. Pass maintenance credentials through hidden stdin or a secret
manager, never through source, arguments or receipts.

Use the hosting provider's ordinary source save/deploy API with the verified
archive and commit. Record the prior saved version before deployment. After a
successful deploy, run `npm run smoke -- https://HOST EXPECTED_MANIFEST_SHA256`
and browser checks against the public origin. If smoke fails, redeploy the prior
saved version; retain its artifacts and review withdrawal rules first.

## Operations

`/healthz` is liveness. `/readyz` checks the manifest, both page entry points,
root data, all school packages and the paper allowlist. A missing or corrupt
required object returns 503. Probe readiness after restart and from your uptime
monitor. Set `ATLAS_ACCESS_LOG=1` for structured status/timing logs without query
strings or credentials. Failed reads produce server errors; content hashes keep
changed data from being served silently.

`node portable/benchmark.mjs URL` records cold/warm and concurrent request timings
in a JSON report. Performance changes should follow measurements. Reports and
receipts stay in `outputs/`; only public download pins and source enter Git.
