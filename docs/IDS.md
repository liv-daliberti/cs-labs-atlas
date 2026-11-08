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
  PIs. A connected reciprocal graph supports more than two advisers. The native external key selects candidates; it
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
The ID report separates reciprocal co-advising groups from shared external identity groups and includes the reviewed source
hashes. As with all isolated preparations, its registry and auxiliary cross-reference files require complete global review
before promotion.

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
