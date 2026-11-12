# SJTU: gitignored build inputs on main (2026-11-12, buildability worker)
Only reviewed/ and reports/ are git-tracked. These files were missing from main and were copied from hierarchy/sjtu/tmp/rb-1112 (the overlay whose build reproduced main's derived outputs byte for byte) into code/hierarchy/sjtu on 2026-11-12 (owner approval: make SJTU rebuildable from main), verified by sha256. `tools/input_manifest.py check sjtu` re-verifies every input file against hierarchy/sjtu/inputs-manifest.sha256.json.

| file (under code/hierarchy/sjtu) | bytes | sha256 |
|---|---|---|
| derived/collection.json.gz | 16,433 | 35c6a098a16f1111bda30ca23f325f23470fdbec161accfced0276bc9e16d198 |
| raw/pi-works.sqlite | 34,463,744 | 4af64775091b1c3517004fe887d58f79d1cfe9de0ad56959cbe2b0848765447a |
| raw/dblp-dump-pages-school.json.gz | 6,039 | 26dc33f33380588cf7b5ece3214b1c8911e8ec7dd614ae8eaef5af4ca06712c0 |
| raw/dblp-dump-persons-school.json.gz | 602,044 | 2464baeb0bc5cfcad771c0d0168db0d5b785b267a5a90d7d422b64161d1955a0 |

Already on main and unchanged: derived/census-faculty.json (153 B, f2c83dbf...: empty by design, the 198 faculty are in reviewed/census-additions.json), raw/openalex-sweep.sqlite (e9f3ddc4..., 812,576,768 B), raw/school-captures.sqlite (5fb8aff9...), listings/sjtu/derived/*.
The original producer of the three raw files is not recorded in main (they existed only in tmp/rb-1112); their sha256 is pinned here.

## Rebuild verification from main (2026-11-12)
Private overlay (code = main, outputs deleted first), Slurm 32224042 (2 CPUs, 40 G, 51:09 wall of the 59 min limit, 23.8 GB peak RSS): students.json and student_papers.jsonl.gz are sha256-identical to main's derived. pis.json and lab_papers.jsonl.gz differ by exactly two papers of 王 瑞 (3,658 -> 3,656): the ACL tutorial abstracts 10.18653/v1/2021.eacl-tutorials.5 and 10.18653/v1/2021.emnlp-tutorials.6, now dropped as `not_paper:meeting_abstract:genre` by the owner's 2026-11-12 genre rule (main commit 793d325f, which postdates main's SJTU derived). No input is missing; main's SJTU derived is stale against current code and will lose those two papers at its next rebuild. Use a walltime above 59 min for SJTU (51 min measured).
