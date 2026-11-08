# Exact-work member-paper reviews

`member-paper-review.json` is an optional, school-local reviewed input. Version 1
supports one retained candidate, an exact lead OpenAlex work with a nonempty arXiv
DOI, and an explicitly identified primary PDF version. Names and titles are never
selectors. Folded-only editions, recovered records without their exact native
source, and competing source versions remain held. No school input is enabled by
installing this consumer.

The input is registered in `atlas_paths.DATA_FILES` for flat and split layouts and
limited to 5 MB. The closed schema is `schemas/member_paper_review.schema.json`.
Each independent review names its reviewer/date, exact PI and native member ID,
OA, nullable collection work, DOI and arXiv version. All identifiers must agree.
Duplicate IDs invalidate the input; multiple reviews selecting one candidate hold
all those reviews, including when one has an invalid proof.

## Preimages and order

The consumer runs after ordinary paper identity, university, appointment, type,
claim/edition reviews, membership retention, candidate generation and weak-member
filtering. It cannot rescue a paper, membership or missing link. A review must bind
the final ordinary output, not a preliminary trial or an old candidate count.

`member-paper-semantic-v1` hashes canonical UTF-8 JSON (sorted keys, compact
separators, no NaN). It binds every field of the full candidate, member, accepted
paper and complete native source work, plus the persisted edition array. Unknown
future scientific fields participate automatically. Only these top-level fields
are omitted:

| Record | Omitted fields |
|---|---|
| Candidate | `studentAtlasId`, `atlasWorkId`, `labId` |
| Member | `atlasId`, `alsoPi` |
| Paper | `atlasWorkId`, transient `_bylines` |

`_bylines` is removed by the ordinary writer. The persisted paper and edition
fields, and the complete exact lead source work and its ordered authorships, stay
bound. This version does not certify a compact folded-edition pointer. When a
future builder preserves fuller edition records, their fields also change the
paper preimage and require fresh independent approval.

Exactly one candidate, retained member, accepted paper and source-work digest must
match. Repeated identical source observations are harmless; distinct source
preimages are ambiguous. A mismatch leaves the original candidate unchanged and
emits a held reason in `report.json.memberPaperReview`. Invalid input structure
stops the build before output publication. Verified/held counters are separate
from ordinary link counts.

## Source and temporal proof

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

## ID and release boundary

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
