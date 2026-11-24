# Reviewed inputs and review contracts

One document for everything a person or reviewer decides and the build reads. Merged 2026-11-17 (process v4 decision 6, owner-approved) from `REVIEWED-INPUTS.md`
and the five reviewed-input contracts, which are unchanged copies in `archive/docs/` (`REVIEWED-INPUTS.md`, `DBLP-ORCID-REVIEWS.md`, `MEMBER-PAPER-REVIEWS.md`,
`PRIMARY-AUTHOR-REVIEW-LOADER.md`, `RECOVERY-SOURCE-REVIEWS.md`, `SOURCE-METADATA-REVIEW.md`, `SOURCE-TYPE-REVIEWS.md`).

## Where decisions live now: the evidence store
Per-person decisions are kept with their source in one SQLite evidence store per school (`docs/EVIDENCE-STORE.md`; `tools/evidence_store.py`, `bin/atlas evidence-store`).
Michigan and Princeton are store-sourced; for other schools the files below remain the source of truth and the store is a lossless import and exporter (the `record` column is the
original entry). A new per-person decision is recorded with `atlas evidence-store record` (or the reviewed file, then `sync`); the reviewer-template audits are `docs/PER-PI-ADMISSION.md`.
Everything below describes the file formats and the build-side contracts, which do not change with the store. Coordination decisions (owner answers) are in `leases/coord/DECISIONS.md`.

Contents: 1 reviewed files and who reads them; 2 per-paper claim reviews; 3 DBLP ORCID inheritance; 4 exact member-paper reviews; 5 derived-only primary author reviews;
6 complete publisher recovery source review; 7 exact source titles; 8 exact source type reviews.


## 1. Reviewed files and who reads them
Small, hand-curated decision files the build and the audits read. They are tracked in git (named one by one in
`.gitignore`), copied into every release at the same paths, and each must stay under 5 MB. Generated files are not
reviewed inputs, even when a reviewed verdict is folded into them.

| File | Read by | What it decides |
|---|---|---|
| `hierarchy/census-overrides.json` | `pi_hierarchy.py`, `chain_audit.py` | per school and person: exclusions (with `why`, `revisit_after`), `is_pi`, aliases, collection person, DBLP/ORCID/OpenAlex ids, `not_openalex`, `mixed_openalex`, reviewed periods, PI basis |
| `hierarchy/home-departments.json` | the site builder, `export_release.py`, `school_profiles.py` | a PI's home department, with evidence and status |
| `hierarchy/zero-paper-review.json` | `zero_paper_ledger.py`, `chain_audit.py` | verdicts for labs with no lab papers |
| `hierarchy/zero-paper-labs.json` | the site builder, `export_release.py`, `organize_tree.py` | the zero-paper ledger (diagnosis + the reviewed verdict; written by `zero_paper_ledger.py`) |
| `hierarchy/chain-reasons.json` | `chain_audit.py` | `explained` / `fix` verdicts for open chain-audit items |
| `hierarchy/student-corrections.json` | `pi_hierarchy.py` | drop, rename or re-source one student record |
| `hierarchy/student-identity-review.json` | `pi_hierarchy.py`, `chain_audit.py` | same-person / different-people verdicts within a lab |
| `hierarchy/student-name-candidates.json` | `tools/student_name_candidates.py` (writer) | queue of one-letter surname typos within a lab, `verdict` empty; a `same_person` verdict goes into `student-identity-review.json` (R-STU-13) |
| `hierarchy/cs-venues.json` | CS-related candidate tools | the computing venue list |
| `hierarchy/<school>/missing-pi-review.json` | `chain_audit.py` | decisions for listed faculty the census lacks |
| `hierarchy/<school>/cs-related-review.json` | `chain_audit.py`, `export_release.py` | decisions for CS-related candidates in other departments |
| `hierarchy/<school>/missed-labs-review.json` | read by no build step (a record, like `missing-pi-review.json`); its accepted people are also in `census-additions.json` / `cs-related-review.json` | the 2026-11-09 missed-computing-labs search: one decision per candidate (accepted, not_faculty, faculty_not_computing, no_appointment_evidence, already_in_census_as, ...), the PI-basis grants on census rows, the Wayback queue and the hand-check (`tools/missed_labs_candidates.py`) |
| `hierarchy/<school>/few-students-evidence.json` | `pi_hierarchy.py`, `chain_audit.py` | researched advisees of thin labs, with quotes and hashes |
| `hierarchy/<school>/relation-evidence.json` | `pi_hierarchy.py` (R-STU-08) | re-captured url, sha256 and quote for collection relations that had none (cmu, epfl, mit; `tools/relation_recapture.py`, bodies in `relation-captures.sqlite`, not tracked) |
| `hierarchy/<school>/gap-evidence.json` | `pi_hierarchy.py`, the site builder | researched gap labs: status, identity, students |
| `hierarchy/stanford/tobagi-review.json` | review record | one Stanford PI's reviewed case |
| `hierarchy/nicknames/{names,extras}.csv` | `pi_hierarchy.py` | given-name pairs (public carltonnorthern/nicknames table, Apache-2.0, plus curated extras) |
| `census/<school>-additions.json` | `pi_hierarchy.py`, `export_release.py` | listed faculty the census missed |
| `periods/<school>-faculty-periods.json` | `pi_hierarchy.py` | reviewed faculty periods |
| `hierarchy/<school>/reviewed/paper-claim-review.json` | `pihier.identity`, `pihier.reviewed_claims`, `pihier.build` | sourced per-PI claim holds/rejections and explicit edition bridges; never forces admission |
| `hierarchy/<school>/reviewed/recovery-source-review.json` | `pihier/recovery_reviews.py`, normal native recovery gates | Exact original recovery/PID/publication/PDF-bound complete publisher metadata projection; no admission override |

## 2. Per-paper claim reviews

Use `atlas_paths.data('paper-claim-review.json', school)` for the working layout. The input is
`{"version": 1, "school": "harvard", "decisions": [...]}`. Each active decision has a unique `id`, exact `pi`,
`match` containing an `oa`, `doi` or collection `work` identifier, `decision`, `why`, `reviewed_by`, ISO
`reviewed_at` date, and original `evidence` items with `url`, `sha256` and a literal `quote`. Supplied identifiers
must agree on one record; a shared title or name is not an identity selector.

- `hold` preserves an unresolved claim as an explicit review outcome. It does not call the underlying work a non-paper.
- `reject` rejects this PI-paper claim with its sourced reason. It does not blacklist a person or author entity.
- `merge` additionally names an `into` identifier selector for an independently eligible edition of the same PI.
  The accepted target keeps its metadata; every eligible source/target edition and byline remains available for links.
  A missing target holds the source. A review never creates or admits an absent target or crosses PI labs.

There is no `accept` action and no completeness waiver. Normal identity, own-school affiliation, appointment and
paper-type checks remain required. Held/rejected raw works cannot lend new dynamic author-ID anchors. The final
review pass also catches recovered rows and runs before student corroboration and links, preventing orphan links.
Ambiguous matches, conflicting actions, merge cycles, malformed evidence or an input changed during a build stop it.

The loaded input hash and every decision, including unmatched ones, are written to `report.json` as
`paperClaimReview`; the input also enters school provenance. An active review file records current decisions;
retain superseded judgments in the audit artifacts and replace the active decision only after new evidence resolves it.
These decisions do not prove corpus completeness or convert candidate member authorships into verified ones.

Not tracked (large or harvested, but in the working root and, where the build reads them, in the sweeps): the census
files (`census/<school>-faculty.json`), the listings (`listings/<school>/listings.json`), the thesis / lab-page evidence
(`hierarchy/<school>/{thesis,labpage}-evidence.json`), and every sqlite sweep.

Not inputs but kept with the releases: `hierarchy/ids/registry.sqlite` (the atlas id registry, docs/IDS.md; generated by
`tools/atlas_ids.py`, never hand-edited, seeded from `releases/latest` when missing).

## 3. Reviewed DBLP ORCID inheritance (archived as `DBLP-ORCID-REVIEWS.md`)

An owned DBLP person binding establishes a bibliography identity; it does not require importing every ORCID listed on that record. Source review found multiple ORCIDs on two Zhejiang person records. These identifiers are unresolved, not proven false. Keep the original XML and person sidecars intact.

A per-PI census override can opt into controlled inheritance:

```json
{
  "dblp_orcid_review": {
    "allowed": [],
    "why": "No independently reviewed owned ORCID source has been admitted.",
    "evidence": []
  }
}
```

An empty `allowed` list withholds all additional ORCIDs from the DBLP dump. For every nonempty allowed entry, add an evidence object with that bare `orcid`, original source `url`, `sha256` and a literal `quote` containing the same identifier. The source must actually establish that identifier for this PI; a DBLP link alone is not independent corroboration for an uncertain DBLP identifier. Invalid or unbacked allowlists, duplicate identifiers and conflicting reviews across merged census spellings fail before native admission.

The native PI record carries `dblpOrcidReview`. The dump still supplies its ordinary owned PID, publication DOI/title anchors and original metadata. ORCIDs outside the review are recorded under `dblpOrcidsWithheld` and counted once per PI. They do not become authorship or person-ID anchors. Independently reviewed explicit census/override ORCIDs remain unchanged; this policy governs automatic dump inheritance. An active `identityHold` continues to block bibliography inference and paper attribution even if the ORCID inheritance review has positive entries.

Without this optional input, existing behavior is unchanged. No new ORCID or PID is created merely by listing it in the policy: only permitted identifiers actually present on the source DBLP record can be inherited. The new contract does not declare any withheld identifier false, merge people, rewrite raw records or change public/private copy rights.

Regression checks cover empty and positive allowlists, complete source preservation, repeated-run idempotence, explicit census identifiers, unresolved identity holds, ordinary default behavior, native round trips and strict PI output schemas in both data layouts.

## 4. Exact-work member-paper reviews (archived as `MEMBER-PAPER-REVIEWS.md`)

`member-paper-review.json` is an optional, school-local reviewed input. Version 1
supports one retained candidate, an exact lead OpenAlex work with a nonempty arXiv
DOI, and an explicitly identified primary PDF version. Names and titles are never
selectors. Version 1 requires an empty persisted edition array and one distinct
exact native lead source. Folded editions, recovered records without their exact native
source, and competing source versions remain held. No school input is enabled by
installing this consumer.

The input is registered in `atlas_paths.DATA_FILES` for flat and split layouts and
limited to 5 MB. The closed schema is `schemas/member_paper_review.schema.json`.
Each independent review names its reviewer/date, exact PI and native member ID,
OA, nullable collection work, DOI and arXiv version. All identifiers must agree.
Duplicate IDs invalidate the input; multiple reviews selecting one candidate hold
all those reviews, including when one has an invalid proof.

### Preimages and order

The consumer runs after ordinary paper identity, university, appointment, type,
claim/edition reviews, membership retention, candidate generation and weak-member
filtering. It cannot rescue a paper, membership or missing link. A review must bind
the final ordinary output, not a preliminary trial or an old candidate count.

`member-paper-semantic-v1` hashes canonical UTF-8 JSON (sorted keys, compact
separators, no NaN). It binds every field of the full PI, candidate, member, accepted
paper and complete native lead source work, plus the persisted edition array. Unknown
future scientific fields participate automatically. Only these top-level fields
are omitted:

| Record | Omitted fields |
|---|---|
| Candidate | `studentAtlasId`, `atlasWorkId`, `labId` |
| Member | `atlasId`, `alsoPi` |
| Paper | `atlasWorkId`, transient `_bylines` |
| PI | `atlasId`, `labId`, `asStudent`, AtlasIDs-derived `appointments`, build summaries `counts` and `funnel` |

PI `oaAuthorIds` are scientific fields. Before hashing, the consumer anticipates
the exact anchored-ID list that the normal writer will persist, without changing
the PI or anchored counter. Names, source person IDs, identity holds/policies,
faculty periods, listings, ranks, units and lab provenance remain bound. Cross-school
ID annotations do not replace the sourced faculty `periods`.

`_bylines` is removed by the ordinary writer. The persisted paper and edition
fields, and the complete exact lead source work and its ordered authorships, stay
bound. Persisted edition metadata is a preimage, not proof of every omitted
nonlead source authorship; version 1 holds any nonempty edition group. When a
future builder preserves fuller edition records, their fields also change the
paper preimage and require fresh independent approval.

Exactly one PI, candidate, retained member, accepted paper and source-work digest must
match. Repeated identical source observations are harmless; distinct source
preimages are ambiguous. A mismatch leaves the original candidate unchanged and
emits a held reason in `report.json.memberPaperReview`. Invalid input structure
stops the build before output publication. Verified/held counters are separate
from ordinary link counts.

### Source and temporal proof

The retained proof binds original response hashes and observations, a sealed source
packet and independent replay, and the full source object's compressed and
uncompressed hashes. It records official PI context, the owned PI-to-person link,
owned self/adviser and degree clauses, a complete authored-publication citation
with its exact arXiv link, and the primary PDF's actual SHA/size/page count/full
parse/fulltext hash. Complete ordered native/printed author lists, explicit spelling
bindings and every author's affiliation map are required. Only the selected slot
names a member ID; the other authors gain no certification. Literal quotes and
PDF/source bytes are independently reviewed before creating this input. The
consumer validates their bindings; it does not download or reopen private bodies.

Link forms distinguish DOM anchors, printed URLs and a citation in the same owned
document. Literal relative DOM hrefs use standard URL resolution. A different
captured URL requires an explicit finite `reviewed_same_personal_path_ownership`
association, both source hashes, named-PI destination clause, reviewed-record
digest and receipt hash. Its exact tuple is required; there is no HTTP/HTTPS or
slash alias fallback. This is an ownership review, never an observed redirect
claim, global URL alias or person anchor. Such an association must concern the
same institutional host and personal path; it cannot resolve another host/path.

Degree bounds are typed dates with stated year/month/day precision. Certification
requires every possible source-edition date and every possible preserved native
accepted date to lie in the guaranteed membership interval: the latest possible
start through the earliest possible end. Boundary-year uncertainty holds the
review. Capture-year arrays and ordinary candidate heuristics do not prove this
interval. Source edition dating and native accepted dating remain separate and
unchanged; a failed review does not exclude the work or alumni membership.

### ID and release boundary

The selected existing row becomes `status=verified`,
`basis=reviewed_exact_member_paper`, with `workReview.identity_scope=exact_work`.
Its complete original candidate and approved review are retained. No name, alias,
role, relation URL, date, source observation, byline, work identifier, paper or
member record changes. This verifies authorship only for this PI/member/work.

AtlasIDs validates the retained proof before any registry mutation. It excludes
these rows from both the wanted-byline query and consumption of the returned OA
author map; an ordinary row with the same work/byline cannot lend its result.
Member URLs and independent ordinary identity reviews retain their existing
meaning. ID annotations are checked again against the semantic preimages before
the transaction commits or any package is published. Scoped validation counts
appear only when applicable in `IDS-REPORT.json.stats`.

A scoped savepoint rolls back all assignment effects on a failed guard. Publishing
inside a caller-owned transaction is held without changing that transaction;
explicit write=False staging preserves its ownership. If removing an earlier OA
bridge would split/redirect an issued member ID reachable from its ordinary
anchors (or issued member annotation), the run holds for separate identity review.
This cannot identify historical records whose normal anchors have all changed.
This mechanism does not repair an earlier global person join. Before enabling
actual reviews, compare the full cohort using disposable copies of the same
registry: every issued ID, anchor owner, redirect, split, appointment, crossref,
lab/work ID and `alsoPi`/`asStudent` relation. Hold unexpected changes; do not run
AtlasIDs against a live registry as a dry run (`write=False` still commits IDs).

Evidence checking validates the new basis and proof. JSON releases retain the
scope and complete scrubbed proof; when a school has scoped rows its CSV gains
scope, review-ID and input-SHA columns. Scrubbed release quotes are display
evidence, not raw preimages to replay. With no optional input, native science rows,
IDs and release column layouts retain their existing behavior. Existing tree and
coverage totals count links of both statuses; they are not verified-identity totals.

## 5. Derived-only primary author reviews (archived as `PRIMARY-AUTHOR-REVIEW-LOADER.md`)

The existing registered raw `pi-works.sqlite` slot optionally holds a separate
`author_review_pages` table. The ordinary `works` and `pages` tables may be empty.
No new input slot or collector is introduced. Missing `author_review_pages` is an
exact no-op, and a table named `proposed_author_review_pages` is never consumed.
Installing this reader enables no school input.

```sql
CREATE TABLE author_review_pages (
  review_id TEXT PRIMARY KEY,
  work TEXT NOT NULL,
  approval TEXT NOT NULL,
  metadata TEXT NOT NULL,
  page1 BLOB NOT NULL
);
```

`approval` is closed JSON with precisely these keys:

| Field | Meaning |
|---|---|
| `version` | Integer `1` |
| `decision` | Exact `reviewed`; proposal/source-supported labels cannot activate it |
| `purpose` | Exact `derived_author_affiliation_flags_only` |
| `school`, `review_id`, `work` | Exact current school, row ID and complete native source-work ID |
| `reviewed_by`, `reviewed_at` | Independent reviewer and valid `YYYY-MM-DD` approval date |
| `source_packet_sha256`, `source_replay_sha256` | Independently reviewed original-source packet and replay bindings |
| `source_work_sha256`, `source_authorships_sha256` | Canonical complete native work and complete ordered authorship preimages |
| `metadata_sha256` | Canonical complete metadata JSON preimage |
| `page1_text_sha256` | Exact decompressed UTF-8 page-one text SHA256 |
| `pdf_sha256`, `pdf_url` | Exact independently reviewed full primary PDF binding |

Canonical hashes use the existing `primary_affiliations.digest`: sorted compact
UTF-8 JSON, preserving every scientific field and author, with no NaN. Packet and
replay hashes refer to independently reviewed bytes; the reader does not fetch or
reopen original PDFs. Producers must verify full bodies, editions, complete source
bylines and mappings before an explicit approval. A proposal is not approved just
because a table or metadata field exists.

`metadata` contains exactly `url`, `pdf_sha256` and `author_affiliation_review`.
The last uses the existing complete version-1 inline or version-2 footnote review
contract. Ordinary `how`, `quotes` or `school_named` authority is forbidden here.
`page1` is zlib-compressed exact UTF-8 text. Payloads are bounded to 2 MiB each,
32 MiB per loaded table and 10,000 rows; exceeding a bound holds the optional
correction, never rejects a scientific work. Truncated, trailing, invalid or
oversized compressed text is held. No unknown review version or boolean version
is accepted.

The identity reader snapshots these rows into `ctx.author_review_pages`, separate
from `ctx.hits`, dynamic PI anchors, `ctx.tied`, `ctx.page_read` and ordinary works.
The paper stage consults them only in `reviewed_byline_school`, after ordinary
identity, school, appointment, type and dating gates. The existing complete source
resolver checks all source/PDF/page-one hashes, ordered names, author slots,
affiliation statements and geometry. School flags still use the normal campus
predicate on a copy. Raw names, author IDs, affiliation strings and institutions
are never modified.

Exactly one matching record must have valid approval and complete current
preimages. Duplicated work reviews, conflicting dedicated/legacy review channels,
wrong schools/works, stale sources, partial maps and malformed payloads retain the
original source-derived flags with a held reason. A dedicated hold does not fall
back to a different correction. Legacy tied/page-read reviews retain their normal
behavior when no dedicated record selects that work. Table/schema or invalid
selector diagnostics appear in the existing primary review report cache; they
cannot admit a paper or change ordinary page-read behavior.

Accepted provenance extends the existing primary-review evidence with
`input_table`, `purpose`, `approval_sha256`, `review_id`, `approved_by`,
`approved_at`, `source_packet_sha256` and `source_replay_sha256`. Held dedicated
evidence carries `status`, `reason`, `work`, `input_table`, and `review_ids`.
Malformed table diagnostics carry `status`, `reason`, `input_table`. The existing
`primary_pdf_affiliation_review_accepted/held` counters count consulted source
reviews once per complete work preimage; global loader diagnostics have a separate
`primary_author_review_input_holds` counter. Root owns optional report-schema
integration; this change does not alter the build writer or schemas.

Corrected flags can change ordinary candidate links and their bases, but do not
upgrade their status. No member/PI input, paper admission, appointment, publication
date or registry operation is performed by this loader. Normal weak-member
retention can depend on resulting candidate availability; no R-STU policy is
changed and no global membership-invariance claim is made. Before enabling the
three real Tsinghua maps, paired same-code map-off/map-on cold builds must preserve
the actual strong member objects and every scientific PI-paper admission/date/
type/identity/appointment/full source group. Unexpected differences hold for
independent review. All existing 540/530/119 artifacts remain immutable.

## 6. Complete publisher recovery source review (archived as `RECOVERY-SOURCE-REVIEWS.md`)

Optional school-local `reviewed/recovery-source-review.json` version1 corrects the **whole representation** of an existing, exact DBLP recovery, before ordinary identity, own-school, appointment/window and source-quality/edition gates. It cannot introduce an absent recovery, import another PID's publication, waive admission, force edition joins or create OpenAlex aliases. Absent input preserves legacy behavior. A stale, incomplete or competing targeted proof holds only that source; another genuinely eligible edition remains available.

Each review binds the exact PI/kind/publication key and canonical SHA256 of the complete original recovery, an owned PID's exact publication-record SHA256, the original source capture hash, and the actual full publisher PDF's URL/hash/bytes/pages plus complete parse evidence and original page1 text hash. Publisher and owned publication must agree on exact DOI, normalized title, year and complete ordered byline. The original unordered byline must contain precisely the same people. Every author has an individual literal affiliation block in the reviewed layout excerpt; the PI's own block must match the school charter. Changing a neighbouring author or borrowing a shared text block is held.

The machine constructs one complete publisher projection, rather than accepting arbitrary output fields. It carries the exact DBLP publication URI and publisher DOI, title, year, venue, ordered authors and own page1 evidence. Original provider IDs remain solely in preserved observation history: a mixed journal OpenAlex record is not relabelled as a conference. Only an arXiv relation literally present in the actual publisher excerpt is retained. No global name or ID anchor changes occur. The report's `recoverySourceReview` includes the input hash, complete original and projected observations, source hashes and decisions. Ordinary output fields retain page1 PDF evidence; originals and reviewed inputs remain unchanged.

The source-real Ryan regression binds original recovery2018 (mixed journal OA W2889877476) to owned PID34/5965 / conf/innovations/FilmusOW19 and actual12page ITCS2019 publisher PDF SHA256413af8f90f2f7cae621a454aa7106324fe8089b6ba5253035f98fa1c4b1b05cb, DOI10.4230/LIPIcs.ITCS.2019.34. The publisher order is Yuval Filmus, Ryan O’Donnell, Xinyu Wu; the latter two have individual CMU blocks. The independently identified2022 journal DOI10.1214/22-ejp749 remains separate. The original bad year/order/provider observation is retained in the report, not silently rewritten in raw/cache inputs. Compact fixture hashes and local original-byte replay are in the independent review scratch receipt; public inputs contain selected publication quotes rather than contact details.

This review corrects scientific metadata only. A catalog claiming the actual2019 conference bytes as the complete2022 journal requires a separate compare-and-swap asset identity correction; no catalog or stored object is changed by the builder. Neither private local availability nor a publication source implies redistribution permission.

## 7. Exact source titles before grouping (archived as `SOURCE-METADATA-REVIEW.md`)

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
must give the same eligible date. Ordinary type/genre/translation gates then run, followed by
book/edition grouping. Missing/ineligible sources are never reconstructed from compact editions or force-admitted.
A matching PI/OA corrective selector with a stale hash, wrong DOI/PID/key, changed author array or date change
raises an explicit `ValueError` requiring renewed review before grouping. It never silently emits the known unsafe
original title. The in-memory report retains the held reason, original eligible row, exact original source when found,
and all available complete source variants, including changed preimages. A selector with no ordinarily eligible row
remains `no_eligible_source`; it does not reconstruct or admit a source. A controlled build must require expected
projections and zero unexplained holds before claiming readiness. Existing unsupported person identities stay in
the normal claim-review pipeline.

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

## 8. Exact source type reviews (archived as `SOURCE-TYPE-REVIEWS.md`)

The optional `paper-source-review.json` input may correct only `type` on a complete source row that has already passed normal PI identity, school and appointment gates. It cannot admit a missing source, rewrite a date or byline, inherit author IDs, or resolve a person identity. Normal date, nonpaper, quality, book-fold and edition rules still run. Existing title reviews retain their contract and outputs.

A `source_type` decision binds exact PI/OA/DOI/work selectors, the whole source and eligible-row hashes, every available source variant hash, original type and complete ordered byline. Its only change is `book-chapter` or `article`. A stale or competing positive correction stops the build before grouping and preserves diagnostics and available originals. A source absent after ordinary eligibility remains `no_eligible_source`; the review never recreates it.

`owned_monograph_chapter` binds each explicit chapter DOI and container title to a complete independently eligible parent-book source/row, every available book variant, its actual DOI and an exactly owned PID/publication preimage. Source year and complete ordered bylines agree. Original publisher location says book-chapter on an ebook/book platform. A guessed DOI prefix, generic LNCS chapter or name-only author association is insufficient. The existing R15 fold consumes the corrected copied row; all original chapter/book sources remain in the review report.

`owned_primary_journal_article` reads only the registered school `school-captures.sqlite` slot, fixed `live` table and exact URLs. Whole stored and actual original body hashes must match. The reviewed PI's existing lab URL/evidence binds the named homepage and its literal publication link. One exact bibliography `li` contains the unchanged full title, literal DOI, all source authors in order, named journal, publication label and an actual Paper/Article link. The complete source projection's Crossref `journal-article` kind and journal metadata corroborate this citation. This does not claim an untouched Crossref HTTP response, a DOI hyperlink, a journal volume inferred from a year label, or a downloaded PDF. A new source path, redirect or HTTP/HTTPS alias is never authorized.

Applied `sourceMetadataReviews` entries contain the input/source/eligible-row hashes, original/new type and finite authority. `paperSourceReview` retains the complete original work, full eligible row and all available source variants; book authority also retains available parent-book rows/sources. Raw inputs and ordinary identity/member/link statuses stay unchanged. Public fixtures contain curated normalized scientific metadata and small reconstructed citation fixtures, with the separate actual private source hashes; raw cached HTTP/API bodies remain private.

## 9. Original publisher issue dates

`publisher_issued_date` is a separate decision in `paper-source-review.json`. It corrects a platform creation date before the ordinary appointment check. It requires exact PI/OA/DOI and whole-source/byline preimages, an independently reviewed publisher original, and the PI's unchanged owned DBLP record with the same title, complete ordered byline and original issue year. A missing DBLP DOI is permitted only because the publisher's literal DOI binds the unchanged source; an explicit conflicting DOI is rejected.

The registered school cache must retain the exact publisher HTML and original PDF. Publisher `DC.Date.issued` and `citation_date` prove the original date/year; `DC.Date.created` must equal the index date and be later. The citation title, DOI and complete authors must match. The publisher's `citation_pdf_url` and index PDF URL must name that same-host original. The original first page must contain the same title and all authors, and its physical top region must contain the quoted issue header and year. A PDF stream can list the physical running header after the body; the consumer reads its actual coordinates without rewriting source text.

Only the hit's derived date changes. Raw work records, identity, affiliation, faculty periods, genre and edition rules retain their authority. Missing, changed, competing or inconsistent positive proof stops the build with diagnostics; the known wrong platform date cannot silently return. The report preserves the original index date and all source hashes. UW's ICWSM case applies to both independently owned PI claims, with each appointment checked at the actual 2016 publication date.

Complete primary affiliation reviews may preserve `unresolved_markers` with meaning `unexplained_in_original`. This is limited to a repeated asterisk on at least two authors who each also carry explicit affiliation markers. Every first-page occurrence must lie in those exact author quotes; the symbol cannot label an affiliation group or note. No contribution meaning is invented, and the unknown status remains in the derived evidence.
