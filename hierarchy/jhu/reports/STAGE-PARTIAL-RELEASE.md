# JHU supported partial package

The owner authorized: “lets add what we have / release what we have for washington university,
harvard, and JHU (and then keep working on improving them)?” after asking to get the other
schools through onboarding. This branch prepares supported data for the coordinator; it does
not mark the school released or publish anything.

## Current reviewed inputs

- Three saved official CS listings supply 146 person rows in their actual capture year, 2026:
  77 main faculty, 46 secondary faculty, and 23 research/visiting/part-time faculty. The
  generated census has 146 faculty records and 91 supported PIs: 55 ladder and 36 courtesy.
  Written ranks, real live URLs, original fetch dates, raw hashes and exact source quotes remain attached.
- Home grouping uses academic units explicitly named in those same titles. For a title naming
  several joint units, the first named unit determines grouping; the full joint appointment
  title remains in the source quote. The charter now recognizes Psychiatry and Behavioral
  Sciences, Genetic Medicine, and General Internal Medicine as observed academic units.
  All 91 PI home records resolve to recognized units.
- Ten explicit appointment starts were reviewed. Hager's automatically extracted start in
  2010 was rejected: the sentence dates his department-chair service in 2010–2015, not his
  faculty appointment. His earlier faculty years remain unproven. A closed assistant-professor
  rank interval in Chien-Ming Huang's CV is a rank change, not a departure.
- Chien-Ming Huang's own saved CV supplies ten PhD advising records and three postdoctoral
  advising records, with each person's JHU affiliation, explicit role, and stated years.
  Present is resolved to the source observation year, 2026. One person has both a completed
  PhD and a subsequent postdoctoral relation; records merge within this lab only. The public
  source's note that Yuxiang Gao has been on leave since 2022 is retained for review.

## Limits and exceptions

The historical listing census is incomplete. Actual current CS coverage reduces the stage-one
open department-years from 43 to 42, without filling any earlier year. The existing AMS 2026
reviewed gap is unchanged. Stage one's exception lists only those exact 42 completeness
findings and quotes the owner's authorization. A new unmatched evidence, schema or identity
failure remains hard under the scoped exception checker.

Appointments unsupported by an explicit period are confined to the sourced listing year.
Research/teaching-only entries remain outside PI status until their own-group or advising
basis is reviewed. Incoming faculty do not become current appointments. Additional units,
historical faculty, lab-page coverage, students, and full texts remain collection work.
Unknown availability is not reported as an exhausted search.

## Build and review status

The sequential metadata build is prepared to follow the shared DBLP job chain: WashU
`32137370`, then Harvard `32137395`, then JHU. It uses the local DBLP dump and saved OpenAlex
snapshot, with no API credits or new archive requests. It refreshes identities, the census,
homes and package; then reads school-local DBLP person pages and snapshot PI works before a
final package build. Identity holds, accuracy judgments and package counts will be recorded
here when the outputs are reviewed.
