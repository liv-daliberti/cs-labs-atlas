# Atlas ids

Stable, opaque ids for every person, work and lab in the atlas (2026-10-29, owner; `tools/atlas_ids.py`; rules R-ID-01 to
R-ID-05 in `docs/RULES.md`). They are assigned by the rebuild stage `ids`, right after the build and before every consumer,
and carried through the packages, the releases, the organized tree, the GitHub export and the site handoff. The older ids
(`<school>:<pi-slug>`, collection person ids, `ext:<school>:<name>`, OpenAlex/DBLP/lab-page paper keys) stay as they were.

| entity | form | example |
|---|---|---|
| person (PI or student) | `atl:p:<12 hex>` | `atl:p:3f0c…` |
| work (a unique paper) | `atl:w:<12 hex>` | `atl:w:9a41…` |
| lab (one PI at one school) | `atl:l:<school>:<pi-slug>` | `atl:l:princeton:tom-griffiths` |

## How an id is made
Each entity has anchors: the identifiers it carries, ranked strongest first.

| entity | anchors, strongest first |
|---|---|
| person | ORCID; reviewed OpenAlex author id (a PI's `reviewedOpenAlex`, minus reviewed mixed ids; for a student, see below); DBLP person (pid); collection person id (`coll:<school>:<id>`, every merged id of the record too); else `name:<school>:<normalized name>:<evidence url>` for every evidence url of the record |
| work | DOI (not arXiv); OpenAlex work id; DBLP key; arXiv id (from an arXiv DOI or work key, version dropped); collection work (`coll:<school>:<work>`); lab-page record (`labpage:<sha1>`); the row's editions contribute theirs |
| lab | `lab:<school>:<the PI's person id>` |

A new id is `atl:p:` / `atl:w:` + the first 12 hex digits of sha256 of the entity's strongest anchor (with `#1`, `#2` appended
on the rare collision). Lab ids are `atl:l:<school>:<pi-slug>` from the PI's name when first issued (a `-2` suffix if taken).

## The registry: an id never changes
`hierarchy/ids/registry.sqlite` holds `ids` (id, kind, the anchor it was minted from, issue date, status `active` or
`redirect`, redirect target) and `anchors` (every anchor ever seen and its id). On every build each entity looks itself up
through all its anchors: a hit keeps the issued id, and new anchors (a newly found ORCID, a DOI) are added to it. Only an
entity no anchor has ever seen gets a new id. The registry is copied into every release (`hierarchy/ids/registry.sqlite`) and
a missing working registry is seeded from `releases/latest`; it is not in git (tens of MB).

- **Merges are redirects.** When one entity's anchors hit two issued ids, the earlier-issued id stays and the other becomes
  `status = 'redirect'` with `redirect_to`; it is never reissued (`hierarchy/ids/redirects.tsv`).
- **Splits mint.** When the data now separates two entities that one id covered, the entity holding the anchor the id was
  minted from keeps it; the other gets a new id.
- **Deterministic.** Entities are joined by shared anchors (a union over the whole atlas), components are processed in the
  order of their strongest anchor, and ties among registry hits go to the earliest issue date, then the smaller id. A rebuild
  gives the same ids, and so does the same input in another order, with or without the registry (`tests/test_atlas_ids.py`).

## Joining people
- Within a school, records that share a collection person id are one person (the same student in several labs).
- Across labs and schools, people are joined only by ORCID, a reviewed OpenAlex id or a DBLP person, never by name alone
  (R-HIER-03). A join by such an identifier between two people whose family names differ is refused and reported
  (`IDS-REPORT.json` `conflicts`).
- A record with no identifier (`ext:` students found by the targeted research) is anchored by its name and each evidence
  url. The same name on two different pages stays two people; the same name on the same page (a roster that names both
  advisers) is one.
- **Source-backed co-advising (2026-11-08).** Within one school, memberships carrying the same native `ext:` student
  record may join when their full names are compatible and reciprocal source quotations explicitly identify the
  co-advisers. Every citation retains its URL and SHA256; a given-name-only adviser must be unique among the school's
  PIs. A full adviser label may omit one-letter given-name initials, including a leading initial when another full given
  name remains. The family and all full given words remain mandatory; the observed token sequence must still identify
  one PI across the school. Thus `John Smith` cannot distinguish `John D. Smith` from `John X. Smith`, while the exact
  full label can. This does not add aliases or relax the required co-advising source statement or issued-ID guard.
  A connected reciprocal graph supports more than two advisers. The native external key selects candidates; it
  never becomes a global person anchor. Each membership retains its own role, years and source citations. Names or a
  shared external key alone still leave records separate. A cited co-advising claim that cannot be resolved, incompatible
  names, or a join reaching two previously issued person IDs raises `CoadvisingIDConflict` before assignment or writes;
  its `holds` records identify the evidence requiring review. One existing issued ID is reused. Source proof is recorded
  in `IDS-REPORT.json` `coadvising_evidence`; this does not verify candidate student-paper author identities.
- **Students who became PIs.** For each student-paper link, the byline author id on the student's linked lab paper is read
  from the school's OpenAlex sweep; when it is a PI's reviewed OpenAlex id and both the student's name and the byline are
  name-compatible with the PI (same family name and first full given name, or a nickname pair; initials never count), the
  student record joins that PI (Chi Jin: Jordan's student at Berkeley, PI at Princeton).
- **Two schools.** A PI at two atlas schools is one person with two labs (`appointments` on `pis.json`): Thomas Griffiths
  (Berkeley, then Princeton; DBLP 34/4472 and his ORCID added to the Princeton record from the DBLP dump on 2026-10-29),
  Jason Lee (Princeton, then Berkeley). People whose other school is not an atlas school (Alex Dimakis, UT Austin; Mung
  Chiang, Purdue; Yuxin Chen, Penn) have one appointment.

## Joining works
Rows sharing any work anchor (including through their editions) are one work, across labs and schools. A component that
would put two rows of one lab together (two records the builder kept apart, e.g. Zenodo versions behind one OpenAlex record)
is split: those rows join only through their own lead record, and register only its anchors.

### Reviewed retirement of a corrupt work identifier

A source record can combine identifiers from different papers. Holding that record in a bibliography does not remove an
older registry association. An exact reviewed retirement removes only the corrupt identifier from active `anchors`;
the issued work ID, its other identifiers, every science row and every unrelated ID remain unchanged. No title or name
rule can retire an identifier. A later assignment containing the retired identifier holds before any package writes,
even when that component also has a valid DOI. SQLite guards also prevent the identifier from becoming active again.

The version1 `retire_work_anchors` review requires a reviewer/date/reason, original URL/SHA256/quoted evidence, the physical
source registry SHA256, `registry_fingerprint(db)` for its complete schema and all tables, and each exact four-field
anchor row plus the complete seven-field issued-ID preimage. Apply only to an isolated registry for review first:

```bash
"$CS_ATLAS_PY" -I "$CS_ATLAS_TOOLS/atlas_ids.py" --registry /tmp/reviewed-registry.sqlite \
  --retire-work-anchors /tmp/exact-anchor-review.json
"$CS_ATLAS_PY" -I "$CS_ATLAS_TOOLS/atlas_ids.py" --registry /tmp/reviewed-registry.sqlite \
  --retire-work-anchors /tmp/exact-anchor-review.json --apply-retirements \
  --retirement-backup /tmp/whole-registry-before.sqlite
```

Dry run is the default. Applying requires a new consistent whole-registry backup; the tool validates every preimage,
works locally and replaces the target atomically only if its full source preimage still agrees. The immutable
`retired_work_anchors` history retains the original association, review and source evidence. Replaying the identical
review is a no-op; a conflicting review or partial retirement state holds. Restoring a retired identifier requires a
separate explicit source review mechanism, never automatic reuse. Active cross-reference exports read `anchors` and
exclude retired keys; regenerate the complete cohort exports at a reviewed promotion, never publish a partial school
cross-reference or treat an old export as proof that a retired key is active. Live global changes still require the
normal exact task claim and serialized promotion; preparing this review does not authorize them.

## Where the ids are
| place | fields |
|---|---|
| `hierarchy/<school>/pis.json` | `atlasId`, `labId`, `appointments` [{school, pi, labId}], `asStudent` (the person's student records elsewhere) |
| `hierarchy/<school>/students.json` | `atlasId`; `alsoPi` when the student is a PI in the atlas |
| `hierarchy/<school>/lab_papers.jsonl.gz` | `atlasWorkId` |
| `hierarchy/<school>/student_papers.jsonl.gz` | `studentAtlasId`, `atlasWorkId`, `labId` |
| `hierarchy/ids/crossref.tsv.gz` | `atlas_id, entity, scheme, value`: ORCID, OpenAlex author/work, DBLP person/key, DOI, arXiv, collection person/work, lab page, name evidence, legacy PI/lab/student ids |
| `hierarchy/ids/persons-cross-school.json` | people with PI appointments at two atlas schools, or a student record at one and a PI appointment at another, with the identifiers that joined them |
| `hierarchy/ids/redirects.tsv`, `IDS-REPORT.json` | merged ids; counts, conflicts refused |
| release `MANIFEST.json` | `ids` (the counts) |
| organized tree | `lab.json` `labId`, `piAtlasId`, `appointments`, `asStudent`; `students.csv` `atlas_id`, `also_pi`; `papers.csv` `atlas_work_id` |
| GitHub export | every row: `atlas_id`, `atlas_lab_id`, `atlas_work_id`, `student_atlas_id`, ...; `data/ids/` (see its `docs/SCHEMA.md`) |

Run alone: `python tools/atlas_ids.py` (every released school; `--no-sweep` skips the student-to-PI byline step).

### Release mode: unresolved co-advising holds stay separate (2026-11-09)

`tools/atlas_ids.py --skip-coadvising-holds` (or `ATLAS_IDS_SKIP_COADVISING_HOLDS=1`, `run(..., skip_coadvising_holds=True)`)
lets a release proceed while explicit reviews are pending. Every co-advising group that would otherwise raise
`CoadvisingIDConflict` (several issued person IDs, unresolved or negative evidence, incompatible names) is left unjoined:
its memberships keep their own issued IDs, nothing is redirected, nothing new is minted for it, and the groups are listed in
`IDS-REPORT.json` `coadvising_holds_skipped`. If an ordinary shared anchor would still join a skipped group, the run raises
instead. The default stays fail-closed; a release may use this mode only with the skipped list recorded in its manifest notes.

## Person-specific co-advising evidence and shared personal pages

A co-advising guard is activated only by a source clause naming the person being checked. Its report preserves the exact
character span in the original quote. Roster boilerplate such as "many students are co-advised", or a preceding student's
qualifier, does not assert co-advising for another member. An actual negative clause about the subject still holds for
review. Ordinary compatible name+source-URL anchors already proving identity do not require invented reciprocal quotes;
several previously issued person IDs still hold before assignment or redirects.

The existing shared `student-identity-review.json` input also supports explicit `scope: "cross_lab"`, `verdict: "same_person"`
reviews. Each names one school, an exact native external person key, the exact `{pi, person}` memberships, a full canonical
name and one `identity_url`. Each membership must cite a `roster_person_link` whose URL/hash already occurs in its unchanged
native relation sources, with an original HTML anchor binding that name to the shared personal page. A hashed
`primary_person_page` citation must name the subject at that URL. Only the HTTP empty-path/root spelling is normalized;
redirects, titles and names alone are not identity keys. These reviewed proofs add a normal school-scoped name+URL anchor;
they do not change membership roles/years/sources, paper eligibility or candidate author identity. Ambiguous names, invalid
proofs and multiple issued IDs fail before package or registry writes. Old within-lab review records retain their behavior.
Shared reviews follow the same hierarchy-container path contract as the school packages: the working hierarchy uses its configured flat/split layout, while a release or isolated hierarchy uses its flat reviewed-file location. The ID stage must not add another `hierarchy/` directory or silently skip reviews already present.

The ID report separates reciprocal co-advising groups from shared external identity groups and includes the reviewed source
hashes. As with all isolated preparations, its registry and auxiliary cross-reference files require complete global review
before promotion.

### Exact typed repository author certificates

A cross-lab review with `identity_basis: "typed_repository_author"` uses an original repository record instead of a
personal-page link. It requires the ordinary school/verdict/canonical-name/exact external-membership fields, plus:

- `repository_author`: the actual capture-host `namespace`, RFC6901 `source_json_pointer`, `item_id`, `handle`,
  complete source `author` object, `advisor_bindings` (`pi`, exact typed `source_name`, actual adviser `authority` UUID),
  and `source_record_sha256`. The item digest is SHA256 of UTF-8 JSON with sorted keys, `ensure_ascii=False`, and
  separators `(',', ':')`; it binds the whole selected item, including all metadata and links.
- One `typed_repository_author_record` evidence citation containing the complete original
  `dc.contributor.advisor` and `dc.contributor.author` property pair. Every citation retains the exact original URL,
  body SHA256 and whitespace-normalized literal quote.
- Each membership's `native_sources`: the ordered exact `{url, sha256, quote}` list flattened from that unchanged
  member's relation sources. The complete typed property quote or its original prefix through the complete public
  author value is accepted; a bare name, changed/truncated preimage or unrelated source is not.

Runtime opens only the registered `thesis-captures.sqlite` through `SchoolDir(school, hdir)`, in SQLite read-only mode.
Review-supplied paths are ignored. It requires one successful exact URL/hash capture, at most 8 MiB compressed and
16 MiB expanded, a complete single zlib stream, and a matching original-body hash. It then checks the exact pointer,
canonical whole-item digest, matching item ID/UUID and handle, exactly one author identical to the certificate, and
all native PI bindings against the actual typed adviser names/UUIDs. Native source lists and quotations are checked
against the same selected source record before any identity anchors are added.

A valid proof adds only `coll:<school>:repository-author:<actual capture host>:<actual author authority UUID>`.
It invents no repository person URI and inherits no ORCID, Scopus, first-name or other global identity. A private
validated proof object exists only in temporary ID entities. Only when every key in the entire external-person group
shares that object and the identical source-exact full public mononym (letters, at least two characters, without
unproved aliases) may that mononym pass the normal full-name compatibility guard. A bare mononym remains held.
Ordinary personal-page reviews, negative-clause checks and the multiple-issued-ID guard retain their behavior;
within-lab native identity review ignores this cross-lab certificate. One issued identity is reused without a redirect.
The public ID report records the exact source/item/adviser/native-preimage provenance, never the private proof object.
No membership role/year/source, paper claim or candidate author verification changes. Preparing the certificate or
running disposable fixtures does not authorize global registry/package writes or publication.

A source-proven duplicate that already has two issued IDs requires a separate explicit redirect review. Optional
`issued_id_review` metadata records the exact survivor/alias, baseline registry hash and before-state; `atlas_ids.run`
never executes that metadata or waives its guard. In isolated preparation only, the existing `assign` mechanism can apply
the reviewed two-anchor component using the standard earliest-issued/ID tie policy. The alias remains resolvable, unrelated
IDs remain unchanged, and repeated preparation must create no additional redirect or split. The ordinary ID stage then
runs against that copied reviewed registry; global application remains a separately reviewed operation.

A same-lab work collision stays as separate scientific rows at the ID stage. When a previously issued ID covered several
such components, a split registers each component's unambiguous source lead anchors with its own ID; it does not move a
shared DOI anchor or change paper metadata. Otherwise a replay would repeatedly mint an orphan while the unique source
anchor still pointed at the old shared ID. A split with no unambiguous source identifier holds and rolls back unpublished
assignments. This stability rule does not adjudicate a conflicting DOI, title or edition: those source questions remain
promotion blockers until independently resolved. Existing issued IDs remain present under the normal split policy.

## Work-only authorship certificates

An exact-work member-paper review (R-LNK-08) proves one link, without OA author ownership or a new member URL anchor.
AtlasIDs checks its complete PI/member/paper/original-candidate scientific preimages before assigning IDs, skips it in both byline
bridge stages, and validates post-ID semantic invariance before commit/publication. Proof remains on the link, never
on member relations or aliases. Earlier issued identities remain historical registry state; this mechanism cannot
split, retire or repair them. Before enabling reviews, compare full-cohort disposable registry copies, including
anchor owners, redirects and cross-school relations. See `docs/REVIEWS.md` section 4.


## A published PI keeps its id (D-0001, 2026-11-19)
A PI that loses the anchor its id was minted from (a DBLP binding dropped as a namesake) has no anchor hit, so the registry would mint a second id and the
published atlas id would change. `atlas_ids.py` therefore passes `assign(..., hints=...)` the id the latest release published for the same school and name
(`published_pi_hints`, default `releases/latest/hierarchy`; `--no-published-hints` turns it off). A component with NO anchor hit takes its hint when the
id is still active and no other component's anchors hit it; the new anchors then register to the published id, so the next run needs no hint. An id
already minted for such a PI is repaired once in the registry by redirecting it to the published id (anchors move; backup + sha256 compare-and-swap).

## Reviewed separation of a shared PI fallback

A legacy ASCII-normalized Chinese name can become empty and share a roster-URL fallback with distinct faculty.
An individual primary source can separate a reviewed PI through a `pi_source_person_identity` evidence item in a
reviewed faculty period. The item retains the original URL, body SHA256, literal full-name quotation and capture date.
Its `source_person_review` records `decision: separate_shared_fallback_v1`, the exact `canonical_name`, independently
sourced Latin `full_name` (also a supported PI alias), identical `identity_url`, reviewer/date, baseline pis SHA256,
`old_person_id`, `old_lab_id`, distinct `old_shared_pi_names`, and `old_counts: {labPapers: 0, studentPaperLinks: 0}`.
Before approval, verify the source-to-canonical-person link, original bytes and baseline shared identity, and retain any
existing students and their IDs. This narrow version covers previously empty labs only; other splits need separate review.

The ID stage validates the certificate and adds a school-scoped full-name + individual-URL anchor instead of the generic
fallback. It never moves the old shared anchor, deletes an issued record or creates a redirect. Unreviewed PIs retain
existing behavior. Rebuilds retain the certificate, and a later global identifier can join the same individual source
anchor. No DBLP/OpenAlex/ORCID ownership, appointment interval or paper admission follows from this ID-only certificate.
Compare all registry tables, package IDs and unrelated identities in isolated preparation before promotion.

A reviewed `source_owned_publication_review.decision: owned_per_work_only` also limits native identity propagation:
credited works still pass the ordinary school/window filters, but their unreviewed OpenAlex author IDs do not seed
additional papers or surname-only matches. The same applies to inferred advisee anchors under that explicit scope.
Unscoped PI decisions retain existing behavior. This is separate from the ID-only source-person separation certificate.

## Reviewed id reconciliation before a school promotion (2026-11-25)
A native rebuild of a school carries no ids, and `atlas_ids.py` then finds each entity through its anchors. A record that now
carries different anchors from the ones its id was issued with would mint a second id (a split), or take the earlier-issued
one of two ids that a source-proven duplicate left it (no redirect). `tools/id_reconcile.py` applies the exact reviewed
decisions of `hierarchy/<school>/reviewed/id-reconciliation.json` (version 1) to an ISOLATED registry copy and package
tree, before the ID stage (it refuses the live registry); the ordinary stage then runs on it and issues no new person or lab id.
- `pi_redirects`: two issued person ids and lab ids behind one reviewed duplicate (`census-name-aliases.json`
  `native_pi_merges`, with evidence). The survivor keeps the id; the alias becomes a redirect and its anchors move. Direction:
  the id the PI is published and packaged under survives (D-0001, the repair above); when both ids were published the earlier
  one is the default (R-ID-02).
- `anchor_bindings`: a current anchor of a record is registered to the id the record was issued with, only when that id's
  single minted name+url anchor is the record's name on a url the record still cites (a name alone never binds), the id is
  active and the anchor is new.
- `student_rekeys`: a student record keyed by a faculty collection id (a merged alias PI the rebuilt PI no longer lists) is
  re-keyed to its issued `ext:` key (`rekeyedFrom`, R-STU-07) so its own name+url anchor finds the issued id.
Every entry carries the exact registry before-state (rows and every anchor) and a changed preimage refuses. `verify` is the
promotion gate: every PI and lab id equals the current package's, no issued id leaves the package without a redirect, the
registry only gains rows (plus the reviewed redirects and anchor moves), no person or lab id is minted for an existing
entity, and no conflict is refused. `finish` keeps the live `IDS-REPORT.json` keys the school run does not write and adds
`reviewedIdReconciliations`; `plan` and `swap` replace the registry, exports and packages by compare-and-swap (dry run
unless `--apply`). The school run's `crossref.tsv.gz`, `persons-cross-school.json` and `IDS-REPORT.json` are partial: swap
only what the promotion owns.
