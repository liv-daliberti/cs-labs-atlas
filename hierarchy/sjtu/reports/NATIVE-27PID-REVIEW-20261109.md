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
