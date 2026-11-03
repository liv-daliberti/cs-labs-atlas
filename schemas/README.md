# Website data contract v1

The producer is the accepted research release. The consumer is the website.
`python3 scripts/validate-data.py` checks the boundary before release preparation
is certified; the frozen research checks still decide evidence and attribution.

- `data.json`: `bundleFormat: lazy-atlas-v1`; unique university IDs; SHA-256 asset
  registry; generated CS scope rule and counts. Do not infer missing evidence.
- `data/cs-hierarchy/index.json`: `schools[]` with unique IDs and readable school
  packages. Each package identifies its school and contains `labs`, `papers`,
  `students`, and `departments` arrays.
- Lab `papers[][0]` and `students[][0]` reference package-wide indices. Authorship
  `links[][0:2]` references the same student/paper arrays; its status retains the
  distinction between verified and candidate. No index may be out of bounds.
- `data/reader-objects.json`: exact frozen hosted allowlist, SHA-256 keys, byte
  lengths, formats and optional ordered chunks. No arbitrary path admission.
- `data/publication.json`: research release, website edition and coverage note.
- Bundle `config.json`: schema 1, research release ID, content-addressed asset
  manifest. A new manifest is a new publication; never edit a deployed bundle.

Add new optional fields compatibly. A breaking interpretation needs a new schema
and a reader migration tested with both old and new fixtures.
