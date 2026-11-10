# HKUST all-units census expansion: stage 0/1 log (2026-11-10)

Scope (owner 2026-11-10): computing-related PIs in any HKUST department. Provisional coordinator answers, logged for owner confirmation:
1. HKUST-GZ people are not counted; keep only a Hong Kong HKUST appointment on an official page; GZ-only people are recorded as excluded with the reason.
2. Institutes and centres (RI, IAS, BDI, ...) count a person only with a department appointment on an official page; centres are not labs.
3. ISOM and MAE are Wayback-only (see below); history goes through the single shared Wayback chain.
4. Joint appointments (ECE category 38) are primary_unresolved until the page states the home department.
5. The embedded JSON row (name, title, category) plus the page sha256 is accepted as the faculty basis for ECE, RI and CBE, flagged as such.
6. Ten Guangzhou or cross-campus people (Pan Hui, Hui Xiong, Hao Liu, Jing Tang, Wei Zeng, Kang Zhang, Ming Liu, Dengbo He, Huan Yu, Hongce Zhang) stay out until a Hong Kong department appointment is shown.

Robots slip: mae.hkust.edu.hk answers `User-agent: * / Disallow: /`. One request to https://mae.hkust.edu.hk/people (404) was made on 2026-11-10 after that robots file had been read. It should not have been made. No further request to mae.hkust.edu.hk will be made, live or otherwise; MAE is Wayback-only.

Other host findings: isom.hkust.edu.hk serves an untrusted TLS chain (no workaround attempted, Wayback-only); the other unit hosts allow their directory paths and name no AI agent.
