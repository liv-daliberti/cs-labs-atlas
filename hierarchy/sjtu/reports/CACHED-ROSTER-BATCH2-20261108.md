# SJTU second reviewed cached-source roster batch, 2026-11-08

Eight additional PI/owned-roster contexts are source-reviewed within the preexisting staged198-context discovery set. This is not eight newly discovered faculty, an exhaustive university inventory, or a canonical package. The first six PI input objects,127 member records and151 role observations are preserved exactly. No identifier/paper/student-paper admission or acquisition policy is activated.

| Newly reviewed roster | Member–lab records | Role observations |
| --- | ---: | ---: |
| 陈国兴 / Guoxing Chen | 16 | 16 |
| 汪宇霆 / Yuting Wang | 9 | 9 |
| 丁家昕 / Jiaxin Ding | 9 | 9 |
| 胡云聪 / Yuncong Hu | 7 | 7 |
| 马叶涵 / Yehan Ma | 17 | 20 |
| 刘盛云 / Shengyun Liu | 7 | 7 |
| 李希君 / Xijun Li | 12 | 12 |
| 张倬胜 / Zhuosheng Zhang | 13 | 13 |
| Additional total | 90 | 93 |

The isolated ordinary `students.researched` stage, using only the reviewed input contexts and no collection-person/name join, produces14 reviewed PI contexts,12 roster-bearing labs,217 member–lab records and244 role histories (217 researched advising,27 researched memberships). The baseline was6contexts,4rosters,127records/151histories. Every old record, relation, source hash, quote, year and native external member ID compares unchanged. This checks the member input stage; full native retention, accepted papers, candidate member-paper links and AtlasID invariance still require a later authorised full build. No registry assignment or scientific package was run here.

The parent progress-report role predicate counts195 explicit-student lab records, including two undergraduate interns, versus113before. An exact traditional degree/student-role set counts193, because `undergraduate_intern` correctly remains a membership relation. Raw-person-ID counts are216all members/194student IDs, compared with127/113before. These are not globally unique-person claims: the source explicitly co-advises Yiming Wang under Rui Wang and Zhuosheng Zhang, so both lab records remain while the native external ID is shared. No global identity or transitive paper ownership is inferred. Other same-name/cross-lab records are not joined merely by a name.

## Exact roles and university timing

Every academic PI has an official current profile, computing-object/method evidence, literal owned-resource link and named owned role. Six links match the destination literally. For Hu, the original cache stores HTTP301metadata for `http://huyuncong.com` to exact `https://huyuncong.com/`; for Zhang, it stores HTTP301metadata for `https://bcmi.sjtu.edu.cn/~zhangzs` to exact `https://bcmi.sjtu.edu.cn/home/zhangzs/`. Those are individually reviewed observed-location receipts, not generic HTTP/slash/path normalization or proof that an unobserved redirect occurred. The metadata record's bytes/hash/date and the destination's original200HTML are preserved separately. No new request or redirect was followed in this task.

Eleven new role-qualified faculty-period rows retain source precision: Chen2021–2024assistant/2025–presentassociate; Wang2020-03onward; Ding2020–2022assistant/2023–2025tenure-track associate/2026onwardtenured associate; Hu faculty start2022-09; Ma2020-11–2023-12assistant/2024-01onwardassociate; Li2024-10onwardassistant professor; Zhang2023-10onwardassistant professor. Liu has only a current2026role observation; no start is invented. Chen's March2021university-join clause and Ding's December2019join clause do not become month-qualified faculty starts. No student, teaching, degree or publication year supplies a faculty interval.

Hu's current official heading/owned page say associate professor, while the detailed chronology retains an ongoing assistant-professor label. The2022-09faculty start is explicit; the promotion date and stale ongoing rank label remain unresolved. His period means academic faculty, not a fabricated rank interval. Li's official heading says assistant researcher, while both the official qualified2024-10chronology and owned profile say assistant professor/doctoral supervisor. Those conflicting labels are preserved; his concurrent2026Ministry secondment does not invent a faculty departure. Both PI eligibilities rest on explicit academic roles/advising and research, never on generic research employment alone.

The roster review follows actual role headings and keeps current, former and future roles distinct:

- Chen's three `Research Assistants & Interns` entries retain the unresolved individual subtype as `research_assistant_or_intern`, not guessed students or doctoral advisees. Former research assistants remain research assistants despite later foreign master/PhD destinations.
- Wang's two undergraduate interns retain that exact role and membership relation. Their later PhD institutions/supervisors do not become degrees/advisers in this lab.
- Ma's `Graduated → Undergraduate Students` heading determines the completed role. Cornell/Tokyo/HKUST/other master/PhD parentheses are next destinations. The graduated-master row remains master's, even though its next destination is a PhD at Tohoku. Current versus completed degree histories coexist. Literal `Ruijie Fu` and `Fuijie Fu` remain separate source spellings; no alias is guessed.
- Li's12individually paired current names/degree labels are under explicit advising/co-advising text. Other advisers are not invented. The alumnus's `CSCWD2026` citation is not a membership or graduation date.
- Zhang's13current role observations use2026only. Earlier programme/roster labels never become an advising start before his2023-10faculty appointment. The explicitly incoming December2026postdoc transition is not applied early at the November capture. All three2027incoming students remain held.

Current source observations are calendar-year points, not invented programme attendance spans. Explicit former role intervals retain their literal endpoints; graduated-section year labels remain points. Undated or institution/appointment-boundary histories are held rather than converted into current enrollment.

## Holds and limits

There are36new named-role holds: Chen2historical starts at his2021faculty boundary; Wang3internship starts at the2020-03boundary; Ding4undated master alumni; Liu8undated former members with unknown prior roles/institution periods; Li1alumnus with no membership date; Zhang3future2027students plus15past degree/roster histories whose postappointment advising or year semantics remain unresolved. Their original names/quotes/roles/destination notes are retained privately. Previously held first-batch cases remain held and unchanged. Commented-out Ma entries were not treated as published members.

All14active PI overrides keep `no_identity=true` and empty DBLP-derived ORCID allowlists. Literal own bibliography links in original bodies remain inactive; no discovery index, ORCID inheritance, OA author ownership, accepted work, alias, source publication date or career-school admission is supplied. Student-paper verifications are0. The institutional partial charter's host/lineage/XJTLU holds remain intact; source membership admissions do not waive acquisition or full-build permission.

## Reproducibility

Private packet: `scratch/sjtu-cached-rosters-1108/`. The immutable cache has484responses and SHA256 `89b8fed64e7b23c8e1f66bc65264fa44d1a9b4d77a973d4887f7244504470fee`; it is read-only. A restartable SQLite checkpoint indexed278cached official/owned pages from the198discovery contexts, using a single node-local cache copy. Discovery classification did not approve any member. The original sibling analysis manifest `15d56f81f97443d7f95d73367765866c0e1b2881f333426b4d79780144587d5d` remains discovery-only.

`original-source-packet-v1.json` preserves16originalHTMLresponses and2stored observed-redirect metadata receipts. `new-eight-source-review.json` binds each PI's official/owned/role/membership decisions and all36holds; `native-member-stage/receipt.json` binds exact before/after hashes and negative checks for future students, destination degrees, mixed subtypes and role history. `baseline-reviewed-inputs/` preserves all five original reviewed input files. All old objects and scientific observations are unchanged; source edits append only the eight reviewed contexts. Scheduler job32150628 was the cache index (8seconds,144904KiB); the queue's earlier32150626annotation was corrected as an unowned predicted ID and was never used. No collector was started/stopped, no network/API/archive/paid call was made, and no canonical/store/catalog/registry write or landing occurred.

Parent review precedes landing. Full ordinary isolated native integration, accepted-paper/member/ID comparison and any canonical promotion remain separately coordinated; the2016–2026paper window and university-scope holds are unchanged.
