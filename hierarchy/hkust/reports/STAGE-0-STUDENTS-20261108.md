# HKUST student evidence progress — 2026-11-08

Status: onboarding; no formal stage gate or research release is claimed.

The owner requested student and paper coverage for every lab. This pass manually reviewed current-student sections on 20 verified HKUST PI/lab pages and recorded 206 student–lab memberships (156 PhD, 23 MPhil, 27 exact degree unspecified). The standard census and student stages read all 206 memberships: labs with students rise from 0/53 to 20/53 in the isolated input set. They produce 203 distinct student IDs; three cross-lab memberships have explicit co-advising evidence. All 53 PIs remain present.

Every membership retains its source URL, original capture SHA-256, exact name/entry quote, role-heading evidence and review receipt. The observation year is 2026 only; no attendance interval is inferred from a prior degree or a start date. MPhil entries override mixed headings; Xiaomin Ouyang's mixed graduate list stays `student` rather than guessing PhD. Postdoc-only and generic member entries are excluded. Comma-form names preserve their original spelling as aliases after the native builder normalizes them.

The 139 automatic proposals were not accepted as a batch. Individual review found a non-person ("Hong Kong"), NTU-era students on a later HKUST PI page, award mentions, and mixed-degree headings. The original proposals and a deterministic 30-row inspection are retained under `scratch/top25-roles-students-1107`; the builder consumes only the manually reviewed subset. Nine additional named cases are held for incoming/future status, Guangzhou campus attribution, unresolved same-name identity, or historical status. The two same-name Yuchen Wang entries are not silently merged.

Remaining work: 33 of 53 labs still lack reviewed student evidence in this input set; this is not evidence that they have no students. The native full paper build is pending the top-25 metadata extension. No new school-attributed paper or verified student–paper identity is counted in this student-only integration check. The separate frozen HKUST preview remains unchanged.

Other reviewed inputs in this batch: nine UESTC profiles explicitly support a doctoral-supervisor PI basis; 29 DBLP identities across UT Austin (6), Purdue (10), NUS (7), CUHK (6) are corroborated by two exact personally credited works on verified PI sites. These identify authors, not their institution-attributed career papers. One additional identity remains held because two source quotes did not reproduce.

Checks: all source capture hashes verified; every selected name and quote reproduces within the manually inspected current section; all 206 memberships consumed by the existing native census/student pipeline, with no missing pairs. The full package, paper accuracy and school coverage gates remain separate.
