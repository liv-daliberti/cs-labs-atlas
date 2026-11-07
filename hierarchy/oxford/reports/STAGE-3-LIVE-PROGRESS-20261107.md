# Oxford live-first PI and website progress — 2026-11-07

This is an incomplete onboarding checkpoint, not a release or a passed school gate.

The cached official Computer Science directory contains 81 faculty records, including 71 current qualifying PIs. All 71 have accepted Computer Science home departments. A pinned core preview (Slurm 32142450, code 8335967) built 71 labs; it intentionally attributed no papers before identity anchors were available. The snapshot sweep has 324,850 works and its sanity check passes. The outside-CS candidate queue contains 297 local-snapshot leads; these are not yet accepted PIs.

Every core PI appears in reviewed/lab-websites.json. There are 23 verified lab or PI homepage URLs with page hashes, dates and official discovery links; two known URLs have unresolved access/archive work; 46 remain pending deeper search. The register is deliberately incomplete and cannot pass stage 3. Three directory URLs (Leslie Ann Goldberg, Alex Rogers, Standa Živný) serve actual PI-authored homepages; their content was reviewed, and the register documents these exceptions to the URL-only profile heuristic. Preserve these reviewed classifications when refreshing the automatic discovery register. Redirect provenance for four selected pages records the original official link and its observed target.

Official profiles for all 71 PIs were captured with school_web, respecting robots and challenge blocks. Twenty-two explicit profile-linked landing-page seeds are in reviewed/extra-lab-pages.json. Students and people subpages were not analyzed or admitted; their review is deferred under the top-25 scope. Existing pages that also contain student text are retained only as raw source captures.

Thirty-five Engineering directory appointment quotes are in reviewed/cs-related-hand.json. Every quote was verified against the saved raw HTML; all 35 directory cards were inspected, with a 30-row retained sample using seed 20261107. Each name matches a local-snapshot computing-share candidate. This establishes appointment-source evidence only; computing/identity acceptance and the other affiliated units remain open. No engineering candidates have been added to the census in this checkpoint.

Ten faculty appointment starts were verified on official profiles and saved in reviewed/faculty-periods.json. The adjacent-CV-date parser bug was fixed separately: a 2024 Oxford appointment followed by a 2009–2024 Cambridge row no longer becomes a 2009 Oxford appointment. Research-fellow and postdoctoral years were not promoted to faculty years. The remaining 61 PIs have only same-year current directory evidence until further dated sources are reviewed.

Slurm 32142511 uses code 24c9395 and the isolated Oxford evidence overlay to run local DBLP identity, census refresh, PI build, school-specific DBLP pages and a final build. No OpenAlex API credits or remote bulk snapshot streams are used. Historical directory discovery remains in the existing shared low-priority queue; this checkpoint issues no Wayback requests.

Validation: parser commit passed 1,391 tests; the evidence branch with website-register support passed 1,404 tests (15 skipped), lint and charters. The school trap check reports zero findings. All 10 appointment records passed raw-hash and verbatim-quote verification; all 23 selected website capture hashes verified. The website gate correctly retains 48 open PI cases. The 35 engineering quotes passed the existing hand_evidence verifier. Detailed receipts and the seeded handcheck are in scratch/top25-resume-1107/. Staged secret scan runs at commit. Historical coverage, affiliated-unit review, identity handcheck, paper-link review and complete website search remain outstanding; no completeness exception is asserted here.

## Final local PI-paper build and bounded review

The completed local build (job 32142511) produced 762 PI-paper rows for 714 unique works across 55 of 71 core-CS labs. All 67 requested DBLP person IDs were present in the local dump, yielding 10,241 publication records; this measures extraction completeness, not identity accuracy. Four PIs have unresolved identities: Jonathan Barrett, Ronnie Clark, Jim Davies and Shan Luo. Students were not extracted.

The deterministic 30-of-67 identity sample (seed 20261107) has 20 independently corroborated identities and 10 still needing corroboration. No false identity was found, but this is not a passed precision gate. Open sample cases: Blanca Rodriguez, Bartek Klin, Varun Kanade, Jonathan Whiteley, Andrew Martin, Christian Rupprecht, Andrzej Murawski, Andrew Simpson, Misha Sra and Hamed Haddadi. The full set of 67 automatic matches remains proposals pending the prescribed review.

The deterministic 30-of-762 paper sample (same seed) has 29 rows supported by source metadata and appointment evidence and one explicit dataset deposit incorrectly admitted as an article: Andrew Markham, STARCOP dataset, OpenAlex W6968916784, DOI 10.5281/zenodo.7863342, repository venue Zenodo. This sample fails; it does not certify stage 7. A narrow repository-DOI + repository-venue + explicit dataset-title filter fixes that pattern while preserving repository manuscripts and journal papers about datasets. The failed sample is retained; rebuilding and a fresh source-bound review remain required after the fix lands. This review did not inspect fulltext authorship.

Source bindings for reproducibility:

- Final lab_papers.jsonl.gz SHA-256: `308490d23f6532c8ab1fe16d6f24a22e9c619b95de6472700a6caa140fc8e18b`.
- Final pis.json SHA-256: `538c1e2aa82c0a8a935c1b1a03061ae9e5779a708f0075c41972606f767d36f2`.
- DBLP identity proposals SHA-256: `7f4de71f0fe77e2bfd9c6965b618538355ad9545e74a36e1c2c31a8307d515ad`.
- Local DBLP person extraction SHA-256: `4920fff7a17c324f229288331c87153d9560e4ebfc8c04caf4ba401694d3a40a`.
- Private audit details: `scratch/top25-resume-1107/oxford-identity-sample.json` and `oxford-paper-sample.json`, with source capture/page hashes and exact evidence.

Open requirements: historical listing completeness; 48 unresolved lab-website entries (46 search pending, two archive pending); the remaining appointment intervals; outside-CS candidate identity/scope review; unresolved DBLP identities and identity precision review; the failed paper sample and rebuilt precision review. Keep Oxford onboarding rather than reporting stages 3–5 or 7 passed. Next: independently corroborate the ten sampled identities, finish remaining websites/CVs, and review the 35 source-supported Engineering candidates before any admission.

## Corrected build and second precision finding

The paper-only rebuild `32142807`, pinned to tested main `0ceb8af`, finished with 761 PI-paper rows across the same 55 labs. It removed exactly the sampled dataset (`not_paper:dataset_record = 1`). A fresh deterministic 30-row metadata sample of the rebuilt population found another explicit nonpaper: Michael Wooldridge, “Learning to Resolve Social Dilemmas: A Survey (Abstract Reprint)”, DOI `10.24963/ijcai.2024/949`, OpenAlex W4401023720. The source explicitly types it conference-abstract; missing page counts let it through the older fallback. The exact '(Abstract Reprint)' suffix now excludes the abstract while preserving the full survey. This second sample remains failed (29 metadata-supported, one explicit abstract reprint); stage 7 is still open. Both failed samples remain preserved.

Rebuilt bindings: lab_papers SHA-256 `dd0bf8fcad76107fc7b457939a96491bcfd6957ea75014489298cfbdb0f10cc1`; pis SHA-256 `a7b2fa87c6d99050abb185eaaad2614a8b58726f0f9c46d59f3fd75790831489`. Detailed second sample: `scratch/top25-resume-1107/oxford-paper-sample-postfix.json`. Rebuild once more after the suffix safeguard, then rebind the review.
