# UIUC computing-faculty inventory: 2016–2026

Owner decisions: Urbana-Champaign and internal centers including NCSA; exclude
other campuses and separately affiliated institutions. Include everyone with a
qualifying appointment in 2016–2026, including departed and retired faculty
(D-0043 and D-0045).

## Delivered inventory

- 370 distinct PI groups: 198 qualifying core census rows plus 174 additions,
  with two source-reviewed duplicate-name merges. All original 177 PI names are
  retained, adding 193 distinct groups to the owner's missing-data lists.
- 427 faculty identities in the accompanying inventory, including current CS
  faculty whose PI basis has not been established. PI status is separate from
  faculty status.
- UIUC appears in both missing-paper and missing-student lists with **zero
  recorded** entries and `uiuc_inventory_collection_pending`. These are collection
  gaps, not assertions that the real groups have no publications or students.
- One synthetic `<PI> group` per PI follows R-HIER-01. Such labels are not claims
  about official lab branding or whether a historical lab remains active today.

## Source checks

- Captured all eleven official annual appointment books, 2016–2026, and parsed
  only their Urbana-Champaign personnel sections. Derived rows retain names,
  roles, academic units, dates, pages and source hashes; no financial fields.
- The eleven books contain 1,708 CS faculty-role observations. Each observation
  proves its printed date only; no continuous appointment is inferred.
- Checked the preceding 2015 book for early-2016 leads. Jennifer S. Cole's
  faculty-owned CV explicitly states a UIUC CS/Linguistics professorship through
  2016. The 2015 book itself was not treated as a 2016 observation.
- Cross-checked current CS and campus directories with the pinned official DBLP
  dump and the local OpenAlex 2026-10-14 snapshot extension. The failed snapshot
  shard was retried once, preserving the other fifteen completed shards; merge,
  school sweep, sweep check and computing-author extraction completed.
- Additional research/teaching PIs require explicit own-group or doctoral-adviser
  evidence. Membership of a center, a committee seat, or a research job title alone
  was not used as an own-lab proof.
- Verified all 201 addition/new-PI-basis evidence records against stored source
  bytes and literal quotes, including dated row/person/unit bindings. The early
  2016 CV interval separately passed the historical-appointment validator.
- Source-specific identity holds cannot be overridden by a name-matched professor
  card. Adding faculty evidence preserves the original bibliographic candidate ID.
  Five source-backed R-HIER-05 scope exclusions remain explicit.

## Remaining limits

This is not an exhaustive-census certificate or completion of onboarding stages
0–10. The audit retains 30 historical faculty-name records needing identity or PI
basis reconciliation, including possible variants of already included faculty,
and four explicit computing-candidate identity/appointment holds. These records
are not automatically new PI groups or proven faculty absences. Other unresolved
author candidates are retained in the discovery review; many may be students.

The archive collection remained subject to the shared Wayback cooldown. Annual
rosters and current directories do not prove every semester or short appointment.
Historical paper eligibility, bibliographic identity, student collection and the
independent exclusion audit remain separate onboarding work.

## User-facing files

- `/n/fs/resemble/remaining-zero-student-labs-2026-11-21.csv`
- `/n/fs/resemble/lab-coverage-gaps-2026-11-23/university-lab-coverage-gaps.xlsx`
- `/n/fs/resemble/lab-coverage-gaps-2026-11-23/per-university/uiuc.csv`
- `/n/fs/resemble/lab-coverage-gaps-2026-11-23/uiuc-faculty-inventory.csv`
- `/n/fs/resemble/lab-coverage-gaps-2026-11-23/uiuc-faculty-review-needed.csv`
- `/n/fs/resemble/lab-coverage-gaps-2026-11-23/uiuc-historical-cs-roster.csv`
- `/n/fs/resemble/lab-coverage-gaps-2026-11-23/uiuc-source-coverage.csv`

The registry has 33 universities, including UW Seattle and Washington University
in St. Louis as separate entries. The active CSV refresh preserved all non-UIUC
rows and asserted that every original UIUC PI remained present.
