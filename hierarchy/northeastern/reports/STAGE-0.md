# Northeastern onboarding, stage 0 - 2026-11-24

Northeastern is registered as `northeastern`, Northeastern University (Boston), status `onboarding`. This registers the school and its sources; no PI, student, paper or website coverage is claimed.

## Scope

Owner decision D-0056 (`leases/coord/DECISIONS.md`) is binding. OpenAlex I12912129, ROR https://ror.org/04t5xt781 (GRAS 2025 CS&E band 51-75), verified against the local 2026-10-14 institutions snapshot (`oa_institutions.py search`, `lineage`); live ROR API not queried.

- In: the Boston campus and the US/Canada network campuses (all carry "Northeastern University" in their strings), internal institutes (Khoury, Experiential AI, Network Science Institute, Roux, COE units).
- Regex-only (`openalex_related`): Mills College I91481961, CTBP I4210145836, IAIFI I4210160315, MGHPCC I2803022237. Mills College is a lineage child; making it related gates every Mills authorship by the affiliation regex, so Mills-only strings (pre-2022 independent college) never count and "Mills College at Northeastern University" strings (2022 on) do. There is no per-id year field, so this is how the 2022 boundary is implemented. CTBP, IAIFI and MGHPCC credit papers of in-scope PIs and never add a PI.
- Excluded: Northeastern University London I2800917498, SMFA I2799861705, Plum Island LTER I4387152758.
- Traps (never match, in `openalex_excluded` and in must_not_match): Northeastern University Shenyang I9224756, Northeastern Illinois I27639287, Northeastern State I192664086/I4210091566, Northeast Ohio Medical I95240055. The main regex rejects "Northeastern University" followed within 30 characters by Shenyang/China/Liaoning/Qinhuangdao/PRC/London/UK, and the domain part refuses `neu.edu.cn`. A bare "Northeastern University" string is ambiguous by itself and matches.

## Charter checks

`atlas charters`: ok (34 charters). 26 must_match and 38 must_not_match cases, including all trap institutions, Chinese and London string forms, `mail.neu.edu.cn`, `neiu.edu`, Mills College bare, Boston University/College, MIT, Harvard.

## Host gate

`school_hosts.py northeastern`: 14 hosts, 0 inconsistent. Live: Khoury, MIE (`/faculty/`), COE, COS, CSSH, Roux (Crawl-delay 10 s), Network Science Institute, Library. Wayback-only: ccs.neu.edu and www.ccis.northeastern.edu (legacy CCIS hosts, 2016-17 and 2018-19 eras), ece and bioe (probe http 401), ai.northeastern.edu (probe challenge). `none`: repository.library.northeastern.edu (robots disallows); thesis robots = disallowed.

## Gate

`atlas stage-gate northeastern 0` fails only on "openalex snapshot: no works of I12912129" until the snapshot extension merges.

## Snapshot extension

Job ids are appended below.

Submitted 2026-11-24 from committed charter `083ae505` (`OA_DATE=2026-10-14 atlas pipeline snapshot-ext SCHOOLS=northeastern --from-worktree`): filter array **32539235**, dependent merge **32539236**; receipts `scratch/pipeline-snapshot-ext-20261124-132052-440237/`. No API credits.

Tasks 1-15 of filter array 32539235 failed at once on node012 and node016 (`sqlite3.OperationalError: database or disk is full`, node-local /tmp); task 0 ran on node806. Merge 32539236 was cancelled. Tasks 1-15 were resubmitted excluding both nodes (`--array=1-15`, job **32540042**) with merge **32540043** (`afterok` on 32540042 and on 32539235_0), same committed code snapshot. No API credits.
