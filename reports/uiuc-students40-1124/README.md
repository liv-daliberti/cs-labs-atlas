# Fourth UIUC ten-lab student roster batch — 2026-11-24

Reviewed all available owned current/alumni rosters and linked advising CVs for these ten labs, including the PICL data array consumed by its page JavaScript. Added 285 supported student–lab memberships (333 source observations) for 2016–2026. All ten labs previously had no qualifying students. This is complete against the reviewed source inventory, with unresolved source observations retained separately; public pages do not establish unlisted real-world completeness.

| PI | Prior qualifying students | Supported students |
| --- | ---: | ---: |
| Eric Chitambar | 0 | 15 |
| John M. Dallesasse | 0 | 24 |
| Chandra Chekuri | 0 | 20 |
| Sayan Mitra | 0 | 60 |
| Wenjuan Zhu | 0 | 4 |
| Yang Liu | 0 | 7 |
| Brian Bailey | 0 | 18 |
| Sarah Gimbert Sterman | 0 | 16 |
| Deming Chen | 0 | 87 |
| Abigail Wooldridge | 0 | 34 |

The review distinguishes current students, dated alumni, prior degree episodes, research membership, staff, postdocs and committee-only roles. Same-person degree stages count once per lab. Deming Chen's newer CV adds students absent from the HTML roster; expected future PhD completions are not treated as completed degrees. Sarah Sterman's owned roster data is parsed as JSON data, never executed. Her additional PhD mentorships of Arif Demirtas and Jina Hur have separately archived UIUC enrollment evidence; no cross-lab collection identity is reused. Abigail Wooldridge's interrupted PhD episode is retained without claiming a PhD degree, and generic graduate research assistants remain generic.

Ninety-six unresolved source observations remain attached to their PIs without accepted identities, years, relationships or publication links. These include undated undergraduate episodes (some belonging to people with a separately accepted dated graduate episode), possible prior-school mentoring, and alumni credentials without an identified student role. Their names, original quotes, hashes and reasons remain inspectable in `roster-review.json` and the reviewed inputs.

The preceding 48 manual PI groups are preserved unchanged. Sources carry their original raw SHA-256, capture time and literal quotes. Raw captures live in `stores/uiuc/metadata/uiuc-students40-1124`; the replayable source builder is included here. Independent source review uses a seeded 50-row sample plus full source/role/date/identity/hold checks. Native promotion is guarded by completed full tests, a landed producer commit, exact input hashes, five schema checks, an independent hash-bound native receipt, and strict preservation of every existing PI ID, listing year, member source/role, paper identifier and student-paper link.

Operational build/promotion and list receipts live in `scratch/uiuc-students40-1124`. No push or website deployment is performed.
