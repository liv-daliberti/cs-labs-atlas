# Derived-only primary author reviews

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
