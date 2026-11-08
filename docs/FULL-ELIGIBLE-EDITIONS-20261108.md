# Complete eligible edition records before selecting a lead

An OpenAlex record encountered first for a collection work could retain the lead even when a later, independently eligible record described its published version. `rows_from_hits` had already reduced that later record to a compact pointer; `recovered_rows` discarded an independently eligible recovery of an already-seen collection work. The ordinary publisher preference and exact reviewed target selector consequently never saw its full authorship, appointment, date and type.

The native pipeline now retains complete raw and recovered records through the normal identity, own-school, appointment and paper-type checks. Newly retained recoveries of existing works require an explicit PI byline; their OpenAlex school claim is replayed against the original work even for legacy charters. Explicit recovered source types are preserved and checked against the existing non-paper type exclusions. A recovery cannot become a publisher merely because a manuscript already exists.

Before book folding, `collapse_eligible_sources` groups the established exact collection identity and compatible exact PI/OpenAlex duplicates. It selects using the existing source/DOI/collection/year ranking or an exact reviewed preferred target, retaining complete alternatives internally. Thus six source versions of one chapter count as one scientific chapter, while five distinct chapters still invoke the existing book rule. Final edition folding sees those complete alternatives, preserves their bylines for candidate links, and serializes only the existing compact edition fields. Internal full-record/partition fields do not enter packages.

Exact OpenAlex identifiers do not override contradictory metadata. Compatible comma/full-name byline forms and omitted authors can describe the same record. Contradictory ordered bylines, an ambiguous missing-DOI bridge, a same-collection conflicting DOI, or unresolved distinct titles without a DOI bridge raise `EditionIdentityConflict` before serialization; the exception retains every source record and reason. Different populated DOI records with distinct collection identities remain separate and are protected from later title folding (`source_distinct_same_oa_records` counts them). Their underlying-paper/edition relationship is not certified by that conservative retention. No new fuzzy-title or name-only joins are introduced.

## Source-bound regressions and limits

`tests/fixtures/full-eligible-editions-source.json` contains compact reviewed native-relevant metadata extracts bound to four complete original indexed CMU work hashes. Tests check the independent projection hashes; the original bytes were independently replayed locally and remain in private cache/scratch (API caches are not committed):

| Work | Decoded original JSON SHA256 |
|---|---|
| W2889031927 Polar preprint |6556da84f2f082829829e440890151eb62c335bd34eed1f767bba6fb9e93835f|
| W2964241527 Polar published record |4b4debab9493979fe77a2f54d20cc880074c84daab583204d9e8ed2312b3ee1e|
| W2895063194 HMM preprint |304d3a27ec1c5a0fb231588ba3a460c0636c9829a2d245605810b7de0e524787|
| W7223730180 HMM record with publisher DOI/arXiv location |606db744fab38d979651e23bf54c47152b443fae731791a73eb678d1b4475129|

The original Polar publisher PDF is SHA256c93bbac2ff002d1cef2063edf6eebe33b42ccab91d84d30058e57f931db3118f (530620bytes); HMM is SHA256c74b0ba9c2fe33fefc817d46c0055c2d57de2fa44bad733f55d007d4f03c23bd (653100bytes). The HMM full publisher recovery in the fixture is an explicit, source-backed eligible fixture from that actual three-author PDF/DBLP record. It does **not** claim that current CMU recovery inputs contain that record. A negative regression retains the actual source preprint metadata when no full publisher record is available; compact pointers never reconstruct an absent publisher.

Actual sealed CMU duplicate rows are also retained: Maria Balcan W2561047508 has compatible six-author comma/full-name forms and one missing DOI, despite Influence/inuence title text; it becomes one lab row through exact identity, preserving both source bylines. Ryan O'Donnell W2889877476 has different DOI10.1214/22-ejp749 and DOI10.4230/LIPIcs.ITCS.2019.34 records and different author order. Those source-distinct records remain separate for explicit source review. No DOI blacklist or PI/school special case appears in code.

Native regressions exercise both data layouts, reversed source order, an exact reviewed target, independently eligible recovery, wrong PI/school/appointment/type targets, non-paper duplicate bylines, unique chapter counts, unchanged member facts and existing verified links alongside candidate-only name matches. The original CMU paired job32149206, broader canonical deltas, original postcheck failure and all Harvard/HKUST audits remain immutable. This change alone does not approve a rebuilt school, a registry redirect, stage9, a release, complete paper coverage or any canonical promotion.
