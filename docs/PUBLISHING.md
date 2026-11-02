# Research releases for website publication

The shared end-to-end runbook is `site/docs/PUBLISHING.md` in the sibling site
checkout. The workflow is the same for a person, CI, ChatGPT or Claude.

From the accepted, clean research checkout:

```sh
bin/atlas release --target site --tag publication-20261102 --dry-run
bin/atlas release --target site --tag publication-20261102
```

Use a fresh tag. The site target includes preflight, rebuild, schema validation,
regression, reader export, release freeze, notes and `SITE-HANDOFF.md`.
It does not export/push GitHub, upload Hugging Face, or deploy the website.
Follow `CONTRIBUTING.md` to integrate accepted code without touching another
operator's uncommitted research. Preserve all evidence and attribution gates.

The exact frozen ID is persisted in `<scratch>/<tag>/run.json`; downstream
steps never select `latest`. Resume with the same `--tag --target site --resume`.
Changed source/options require a new tag. A downstream-only run must supply
`--release-id <exact-id>`; for example `--from notes --release-id 2026-11-02`.
An interrupted freeze can have produced a release before recording success:
inspect `release.log` and the manifest before starting a new downstream run.

Site preparation uses ordinary Python/Node commands and JSON reports. Only
the final hosting adapter needs the provider's deployment interface.
See the site runbook for credentials, checks, resuming uploads and live
verification. Never claim an export or deployment merely because a release
was frozen or a handoff written.
