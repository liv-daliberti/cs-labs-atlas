# Tsinghua reviewed all-member batch — 2026-11-08

Status: onboarding and incomplete. This input-only branch preserves the original55 reviewed memberships and adds323dated role observations for310additional distinct lab-member pairs. PI count remains207; Wang Zhiliang and all other new PI/date/alias/charter proposals are not automatically admitted. No canonical package or release is promoted.

## Reviewed input delta

| Measure | before | after |
|---|---:|---:|
| Source-supported PIs |207|207|
| Reviewed distinct lab-member pairs |55|365|
| Labs with reviewed members |6|14|
| Additional dated role observations |0|323|

The existing `few-students-evidence.json` is byte-for-byte unchanged (SHA256 `2e5e22ee594af21ae6e194437f3a8bcb4e670810cd9bff5ee833abb08a533c6e`). New evidence uses the standard `roster-evidence.json` input. Its legacy `students` container includes all member roles; it does not classify every entry as a student. Current and former roles can describe the same member.

| PI | added role observations | added distinct member pairs |
|---|---:|---:|
|喻文健|40|40|
|翟季冬|55|53|
|陈键飞|16|16|
|Gao Mingyu|38|37|
|Xu Wei|1|1|
|李振华|44|44|
|贺飞|18|18|
|王建勇|44|37|
|刘永进|67|64|

The323observations retain118PhD,82master,2graduate-without-inferred-phase and41undergraduate degree-role observations;80other observations cover postdocs, researchers, staff, research assistants, administrative staff, visitors and members whose current role is unspecified. These are role-episode counts, not unique-person counts. Mixed RA/intern headings remain member; mixed engineer/assistant headings remain broad staff. No MPhil label or guessed doctoral phase is introduced.

Current membership uses the actual2026capture observation. Explicit alumni start/end or graduation years are retained only where quoted; old cohort starts without an evidenced overlap with2016–2026 are held. Future degree endpoints stay expected dates and never become actual attendance ends or future relation years. Visiting/intern membership is separate from degree attendance: a visitor with an incoming2027degree is not recorded as an enrolled2027student. Explicit external-university co-advising retains the external institution and never implies Tsinghua degree enrollment or physical presence.

Two within-lab bilingual equivalences are directly named in the same source: JennySheng（盛芊芊）/盛芊芊 and PerevoznikovaAlisa（爱丽丝）/爱丽丝. The canonical Chinese names preserve current-member and earlier master-role histories under one person within Liu Yongjin’s lab. No aliases are inferred across labs or by transliteration.

## Holds and precision

390source observations were reviewed.67remain outside this admission:28with unresolved membership-window overlap,28explicitly before2016,2future entrants,7shared NM-team rows without an individual PI-lab tie, and2unproven name matches to existing faculty. All held rows and their original proof are preserved in `scratch/tsinghua-members-1108/held-observations.json`.

The shared NM team includes multiple faculty. Its staff list alone does not establish that every person belongs to Yang Jiahai’s own PI-centered lab. Wang Zhiliang’s separate PI proposal remains unapplied. MADSys and THUIAR multi-PI roster pages are also not auto-admitted.

Chen Jianfei’s postdoc YuanYang matches an existing faculty name under the native matcher; Liu Yongjin’s unspecified member 张涛 matches a different Automation PI name. Both are held until source identity disambiguation prevents a name-only attachment to a faculty collection ID. Neither a public name match nor a plausible transliteration proves identity.

## Validation and remaining native issue

Independent replay verified all323admitted quotes, role sections, original decompressed capture SHA256values and2016–2026relation years across9distinct source pages. It also verified that the original55input is unchanged. Source receipts and the admitted/held count receipt are under `scratch/tsinghua-members-1108/`.

A light census/member trial against code14e613f retained207distinct PIs and14member-bearing labs but produced364member pairs: it incorrectly merged two separately listed PACMAN postdocs, JialiLi and JialinLi, by a long given-name prefix. Their separate current cards link `/~zjd/author/jiali-li/` and `/~zjd/author/jialin-li/` on the same original captured page. Both truthful rows remain in this reviewed input; the coordinator is fixing the general native merge rule before final integration. This is not a missing source or an invented alias. No heavy paper/fulltext builder ran.

Pending work includes final native recheck after that shared identity fix; broader lab/member census beyond these14labs; actual unresolved appointment and membership years; PI/member bibliography identities; school-attributed papers and member-paper links; and local-copy collection. Career publication lists and institution-wide works are not substituted for school-attributed lab papers.
