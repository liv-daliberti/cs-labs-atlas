# Tsinghua reviewed lab members — 2026-11-08

Status: onboarding and incomplete. This input-only branch preserves the original 55 memberships and adds 323 dated role observations for 310 additional distinct lab-member pairs. The native census remains 207 PIs. New PI, appointment, alias and charter proposals are outside this batch. No canonical package or release is promoted.

## Reviewed input delta

| Measure | Before | After |
|---|---:|---:|
| Source-supported PIs | 207 | 207 |
| Distinct lab-member pairs | 55 | 365 |
| Labs with reviewed members | 6 | 14 |
| Additional dated role observations | 0 | 323 |

The original `few-students-evidence.json` is unchanged, with SHA256 `2e5e22ee594af21ae6e194437f3a8bcb4e670810cd9bff5ee833abb08a533c6e`. New evidence uses `roster-evidence.json`. Its legacy `students` container holds every reviewed member role; current and former roles can describe the same person.

| PI | Added role observations | Added distinct member pairs |
|---|---:|---:|
| 喻文健 | 40 | 40 |
| 翟季冬 | 55 | 53 |
| 陈键飞 | 16 | 16 |
| Gao Mingyu | 38 | 37 |
| Xu Wei | 1 | 1 |
| 李振华 | 44 | 44 |
| 贺飞 | 18 | 18 |
| 王建勇 | 44 | 37 |
| 刘永进 | 67 | 64 |

The new observations retain 118 PhD, 82 master, 2 graduate and 41 undergraduate role episodes. Another 80 episodes cover postdocs, researchers, staff, research assistants, administrative staff, visitors and members with unspecified current roles. These are role histories, not unique-person counts. Mixed RA/intern headings remain “member”; mixed engineer/assistant headings remain broad “staff”. No MPhil label or doctoral phase is guessed.

Current membership uses the actual 2026 capture observation. Alumni dates are retained only where stated. Older cohort starts without an evidenced overlap with 2016–2026 remain held. Future endpoints stay expected dates and do not become actual attendance ends or future relation years. Visiting membership is separate from degree attendance: a visitor with an incoming 2027 degree is not recorded as an enrolled 2027 student. Explicit external-university co-advising preserves that institution and does not establish Tsinghua degree enrollment or physical presence.

Two bilingual equivalences are explicit within Liu Yongjin’s roster: Jenny Sheng（盛芊芊）/盛芊芊 and Perevoznikova Alisa（爱丽丝）/爱丽丝. Their canonical Chinese names preserve current membership and earlier master-role histories under one person in that lab. No cross-lab or transliteration-based alias is inferred.

## Holds

Of 390 reviewed observations, 67 remain outside admission: 28 with unresolved window overlap, 28 explicitly before 2016, 2 future entrants, 7 shared NM-team rows without an individual PI-lab tie, and 2 unproven matches to faculty identities. Original proofs remain in `scratch/tsinghua-members-1108/held-observations.json`.

The NM team lists multiple faculty. Its staff list does not establish membership in Yang Jiahai’s individual PI lab. Wang Zhiliang’s separate PI proposal remains unapplied. MADSys and THUIAR shared rosters were also withheld. Chen Jianfei’s postdoc Yuan Yang and Liu Yongjin’s unspecified member 张涛 match existing faculty names under the native matcher; both stay held until source evidence disambiguates identity.

## Validation

Independent replay verified all 323 admitted quotes, role sections, original decompressed capture hashes and relation years across 9 source pages. Every retained relation year lies in 2016–2026. It also confirmed that the original 55-member input is unchanged.

The initial native trial on `14e613f` produced 364 pairs because it merged separately listed PACMAN postdocs Jiali Li and Jialin Li by a long given-name prefix. Their distinct current cards link `/~zjd/author/jiali-li/` and `/~zjd/author/jialin-li/`. The coordinator fixed the general merge rule in `6c79c87`. The before-fix receipt remains at `scratch/tsinghua-members-1108/smoke-before-prefix/failure-receipt.json`.

The fixed native trial passes: 207 distinct PIs, 365 member pairs and 14 labs. All original 55 relation objects survive unchanged. It retains 298 researched advising role relations and 80 researched membership role relations, with nonstudent roles checked individually to remain memberships. Both postdocs remain distinct, and current/earlier role histories are preserved. The trial uses all 207 standard census additions from main. Its passing receipt and clean code provenance are at `scratch/tsinghua-members-1108/smoke/summary.json`; the roster SHA256 is `0b1860a2cb086becec0dfa91017d15f41fea6ede310eb7e2a5330a1fb28208ac`.

Only light census/member checks ran. Broader member coverage, unresolved years, bibliography identities, school-attributed papers, member-paper links and local copies remain open. Career publication lists and institution-wide works have not been counted as school-attributed lab papers.
