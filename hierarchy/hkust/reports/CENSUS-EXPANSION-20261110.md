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

## hosts.json (stage 0 host gate)
`school_hosts.py hkust` ran in the private overlay on 2026-11-10: 16 hosts, 0 inconsistent (14 live unit hosts and cse; isom and mae Wayback-only; their robots rows were seeded from the earlier checks so neither host was contacted again). The file is NOT in main's derived directory: copying it there was denied by the permission classifier and is queued for the owner.
- path: /n/fs/resemble/homogenizing-science/code/hierarchy/hkust/tmp/census-1110-overlay/hierarchy/hkust/derived/hosts.json
- sha256: 8548f3543fb59142a407a1c1559d5af247c7a233293a53c969e6ba133fcdd5e7
- ISOM and MAE listing URLs (CDX prefix query, 2026-11-10): isom.hkust.edu.hk/faculty-and-staff/directory; www.mae.ust.hk/en/people/faculty and www.mae.ust.hk/people/faculty.html. Hosts mae.ust.hk, mae.hkust.edu.hk, isom.hkust.edu.hk are wayback_only_suffixes.

## Portal (researchportal.hkust.edu.hk / facultyprofiles) is not a source (coordinator, 2026-11-10)
The central faculty portal redirects to researchportal.hkust.edu.hk, which answered a bot challenge to the earlier collector; the rule is to stop at challenges and the block was not cleared. No portal page is cited, and no site entry rests on it. A fresh reviewer agent read portal profiles that link personal sites for Anyi Rao, Wei Xue and Yiding Feng; that is an unsupported lead only: those sites are not recorded (their extra-lab-pages entries were removed) and their content is not copied. Their reasons rest on the official EMIA and IEDA unit pages that were read under robots.

## Own-page title evidence (R-PAP-44), 2026-11-10 (provisional; evidence only, not applied)
Zhiyao Xie, Ling Pan and Zili Meng: the own publications page (linked from the official ECE profile as Personal Homepage) holds 67, 48 and 53 exact long DBLP titles of one DBLP person each (compared against a DBLP dump persons file written by an accidental run, see the incident note to the coordinator; re-run in a private path before use); no same-base-name rival shares a matched title; the person's name equals the PI's. This record does NOT change census-overrides-school.json: Zhiyao Xie and Ling Pan are held no_identity there by the gates worker and Zili Meng is already bound; the gates worker may bind the first two on this evidence (pages: https://zhiyaoxie.com/publications/, https://ling-pan.github.io/publications/, https://zilimeng.com/papers.html, sha256 07716709c7eb..., c44a3c0ecf48..., 946dbd2239a4...).
