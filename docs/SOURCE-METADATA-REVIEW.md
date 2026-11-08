# Exact source titles before grouping

`paper-source-review.json` is an optional school-reviewed input, version1, distinct from `paper-title-review.json`.
The latter's v1 contract stays display-only after grouping and fills missing titles only. This new input corrects an
explicitly reviewed, nonempty truncated source title on an already eligible original before quality, book folding,
and fixed R16 title components. Its initial decision is only `owned_publication_title`, a strict word-boundary prefix completion; no other field or unrelated nonempty-title rewrite is supported.

The review selects one PI, source OA identifier, DOI and optional collection work. It binds the canonical SHA256 of
the complete unmodified source work, its literal old title and complete ordered byline. The exact already-owned PID
must contain one publication with the declared key, unchanged whole-record hash, same DOI, intended full title,
and compatible complete ordered authors. Existing per-record name matching handles attested bibliographic name
forms; it does not create PI aliases, global name merges, ORCID activation or verified member links. Exact DOI/key
and source preimages prevent a different publication from lending its title. No name-only or title-only selector exists.

`source_metadata.apply` receives complete rows only after ordinary PI identity, own-school, appointment and
namesake gates. It copies the eligible row and changes its title only. A recomputation of ordinary venue dating
must give the same eligible date, or the review is held. Ordinary type/genre/translation gates then run, followed by
book/edition grouping. Missing/ineligible sources are never reconstructed from compact editions or force-admitted.
A stale hash, wrong DOI/PID/key, changed author array, conflicting review or date change does not project metadata.
Per-source held outcomes remain explicit; a controlled build must require expected projections and zero unexplained
holds before claiming readiness. Existing unsupported person identities stay in the normal claim-review pipeline.

`report.paperSourceReview` retains each original complete work and eligible row plus its outcome. Applied review
provenance accompanies lab rows, including when a reviewed source becomes a nonleading edition. Thus neither raw
sources nor full per-source bylines/dates/affiliations are overwritten. Bibliographic sources establish titles, DOI,
author lists, publication kind and bibliography year; this operation does not assert publisher PDF bytes, author↔school
marker layout or online-versus-issue dates. Those need their own evidence when claimed or disputed.

The first source-real case is two unrelated MobiCom papers whose original titles both read `Experience`.
Their exact owned DOI/key/full-title/ordered-author records restore separate scientific groups. The original fixed
119-case failure remains reported; this change is not a Stage9 claim or authorization to promote a new package.
Other duplicate-byline, type and monograph-chapter issues need separate exact-source projections/guards; this
initial title-only input cannot silently alter them or blanket-reclassify LNCS chapters.
