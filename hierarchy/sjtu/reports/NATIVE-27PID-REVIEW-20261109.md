# SJTU isolated native with 27 owned DBLP bibliographies, 2026-11-09 (admission still HELD)

Runtime is the common SJTU runtime `4ca6712` (the one that gated advisory authority for the 6-PID native 32158250). The first attempts used the later runtime `c49480c`, which activates advisee identity routes (a Nanjing physicist "Rui Wang" was credited to 王瑞 through `advisee_coauthor`): job 32171244 and 32175417 failed at their own guards and are superseded. The registry-preimage guard now compares the registry with its value at job start (another session rewrites it legitimately).

| Job | Owned PIDs | Package rows (distinct works) | Verdict |
| --- | ---: | ---: | --- |
| 32158250 (earlier, 6 PIDs) | 6 | 233 | held baseline |
| 32175624 (11 PIDs, controlled) | 11 | 867 (862) | sealed, guards pass, 0 verified links |
| 32175626 (27 PIDs) | 27 | 1970 (1928) | sealed, guards pass, 0 verified links, 207 candidate student links |

Independent work-level review (`scratch/sjtu-admit-1109/coauthor-check-27pid.json`, `review-27pid.json`): rows credited by the OpenAlex author-id anchor and not listed on the PI's DBLP person record are held unless the byline shares a coauthor with at least five co-publications on that record (this catches the Chinese-name namesakes: tropical-disease, dermatology, materials and cardiology papers credited to 周煊赫 and 沈艳艳); books, book chapters and bylines without SJTU affiliation text are held. 189 new rows are proposed holds (not yet written into `paper-claim-review.json`, which needs original-source evidence per row); 1781 rows, 1740 distinct works, remain candidates, 1632 of them with a typed faculty period and the rest on a 2026-only listing. Fifty-row spot checks (seeds 20261109 and 20261110, 100 rows): 100 of 100 plausible on school affiliation, byline form and topic; no page-1 or copy check. Not a formal stage 9 (50, not 105; no coverage denominator).

## Standing rules for SJTU natives (owner decision 2026-11-09)

- Run SJTU natives only on runtime commit `4ca6712682c16fcdf4cb283fd3335b5e94f157a9` (snapshot of `worktrees/zju-native-runtime-1108`), never on `c49480c` or later main: those activate advisee identity routes and misattribute namesakes (Rui Wang to 王瑞).
- The 189 proposed holds are now 189 additional `hold` decisions in `reviewed/paper-claim-review.json`, each with original stored-record evidence (url, sha256 of the stored compressed work blob, quote of title/credited authorship/affiliation/type) and the flagging rule recorded in `flag_rule`. A coauthor-overlap rule proposes; it is not evidence. Held works are excluded from the package.

## Corrected package (job 32177052, runtime 4ca6712, input commit 75c2ade before rebase)

| Measure | Value |
| --- | ---: |
| Owned DBLP bibliographies | 27 of 198 |
| Package rows / distinct works | 1782 / 1741 (earlier uncorrected 27-PID: 1970 / 1928; 6-PID baseline: 233) |
| Held claim decisions in `paper-claim-review.json` | 319 (118 earlier + 201 new, each with stored-record evidence) |
| Rows with typed faculty period / 2026 listing only | 1669 / 113 |
| Faculty with at least one paper | 25 |
| Candidate student links (verified: 0) | 207; 4 fail the name/date check (Jinhua Wu 2021 before 2022 start; Binlin/Binglin Zhou x2; Yiming/Yiting Wang), 161 are undated and cannot be checked |
| Population audit (school text, date vs period/listing, type) | 1781 of 1782 pass; the one failure is 沈为 "Image Stitching", a book chapter (hold next cycle) |
| Stored-record open-copy pointers (upper bound, nothing fetched) | 936 PDF URL, 85 landing page, 720 none of 1741 |
| Isolated ID rehearsal against registry c5df145c (copy; real registry unchanged) | 468 people, 1741 works, 0 conflicts, 1 co-advising hold skipped (Yiming Wang) |

Not met: 2500-paper target (1741 candidates), copies (nothing measured), formal 105-row hand-judged stage 9, 171 faculty without an owned bibliography, 79 without period evidence.
