# SJTU faculty roster completeness review — 2026-11-15

Read the complete current sections of fifteen unambiguous PI-owned faculty-platform indices and 444 stored student-specific detail pages. All evidence reuses captured pages; no blocked host was retried. New current members use the capture year only. Teacher-sidebar metadata does not supply a student's degree.

This commit adds 28 current student rows across eight PIs, plus Pan Li's dated PhD alumnus KHOUANETHEVA PHOLSENA (2015–2021; explicit faculty chronology starts in 2002). The 29 rows give 29 distinct PI/name pairs. Root reviewer `codex-sjtu-ntu-1115` independently checked the original bytes, SHA-256, verbatim visible quotes, stated roles and years, and PI identity. Checks passed for all admitted rows; `git diff --check` passed.

Current additions: 牛力 6 PhD; 沈艳艳 3 PhD; 涂仕奎 1 PhD; 王浩洋 2 PhD + 1 master's; 王烁 2 PhD; 夏虞斌 8 PhD; 易冉 1 master's; 郑圣安 2 PhD + 2 master's. Zheng's English index is tied to the full Chinese identity on the same faculty site's profile. Wang Haoyang's stored profile agrees with the official CS profile on symmetric cryptography and his NTU doctorate.

A further 59 dated-alumni evidence rows remain outside this commit until explicit faculty chronology is approved: 牛力 11, 沈艳艳 15, 夏虞斌 33. Their literal membership/role/date evidence passed the independent source check; student registration alone is not treated as a faculty appointment. A newly captured own CV explicitly places Li Niu at SJTU from September 2018; appointment review remains separate. Yi Ran's 龚致君 record begins in 2020, before the proven July 2021 faculty arrival, and remains held. Pre-2016 graduates remain out. `wangdong1` names 王冬 rather than census 王东; `wuyadong1` is an unresolved namesake and is not used.

Source packets and reviewable held proposals: `hierarchy/sjtu/tmp/recall-final-1115/`. Hash-verified captures: candidate `hierarchy/sjtu/work/student-recall-captures.sqlite`. The final stage-6 draw must follow the final rebuild and use its new default seed; this source sweep is not a recall signoff.
