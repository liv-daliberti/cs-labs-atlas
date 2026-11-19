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

## Hosting rule (D-0012, owner 2026-11-18, re-confirming 2026-11-01)
The site hosts only Creative Commons (CC*) and public-domain full texts. Every other confirmed local copy is shown as a link to its source with a
local-copy marker (`stored_copy`, `link_basis: confirmed_copy`). `tools/reader_export.py` `decide()` enforces it from the licence (asset, candidate,
or arXiv/OpenAlex metadata); an unknown licence is a link. Licence and basis stay in every row as metadata. The 2026-11-17 "host every confirmed copy"
behaviour (commit b780330a) is superseded. An explicitly reviewed independent library snapshot (`--library-snapshot`) is a separate owner-admitted path.

## Reviewed home departments

A research freeze combines the copied school-local home registers into the
release's shared `hierarchy/home-departments.json`, which the website hierarchy
builder reads. Explicit local reviews and holds follow the same precedence as
the working registry. The freeze uses only its copied inputs; later working-tree
changes cannot alter the released decisions. Per-PI admission still filters held
PIs from this shared register unless the owner explicitly selects unfiltered
school-wide data.

Recording a home department does not publish a lab. A lab must also be included
in the admitted research/interim site input, and the resulting Site version must
be deployed. Check the published PI inventory and department labels after that
step; do not report assignments as live solely because the research review is
complete.
