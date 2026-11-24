# Ten more UIUC student rosters, 2026-11-24

This batch reviews complete available owned current/alumni rosters and linked CVs for ten more UIUC labs. The iSENS roster was captured after JavaScript rendering. It adds 249 student–lab memberships from 287 source observations; repeated degree and internship episodes count once per person and lab.

| PI | Supported students |
| --- | ---: |
| Bin Hu | 8 |
| Francis Yan | 23 |
| Radhika Mittal | 9 |
| Shenlong Wang | 44 |
| Jugal Garg | 8 |
| Yupeng Zhang | 12 |
| Bhaskar Ray Chaudhury | 2 |
| Minjia Zhang | 38 |
| Koustuv Saha | 60 |
| Elahe Soltanaghai | 45 |

`roster-review.json` records the full sections, exclusions, and identity decisions. `sources.json` and `date-sources.json` locate the archived source bytes and their hashes. `independent-review.json` binds the final reviewed input and seeded 50-row source audit. The first batch's native review is retained in `preceding-batch-native-review.json`.

The scope is eligible named students in these available sources during 2016–2026. Prior-school-only mentoring, postdocs, visiting researchers/scholars, faculty, pets, committee-only relationships, and unsupported collaborator-only cases are excluded. Explicit high-school research students/interns are retained as student memberships, with their source role recorded. This does not establish that a source lists every real-world student or shorter internship.

Capture observations and stated degree/internship dates are retained separately. Undated alumni keep unresolved years. Open intervals retain their open end; no publication year or prior degree date is substituted for a lab membership date. Published future-degree plans are not treated as degrees already earned.

The UIUC native build is checked against the preceding applied package for every paper identifier and edition alias, PI identity/listing year, old student identity/role/source, and student–paper link. All five native files must pass their schemas, and every new reviewed student must appear. Existing publication/advising rules remain the build's gates.
