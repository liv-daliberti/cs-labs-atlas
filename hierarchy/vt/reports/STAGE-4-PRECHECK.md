# Virginia Tech Stage 4 appointment-period precheck

Date: 2026-11-10. This is a precheck against the provisional Stage 2 census, not a passed Stage 4 or an admitted school package.

The current census has 95 provisional professor-rank PIs. Forty-four have continuous dated listing years. Two more have reviewed appointment starts in `hierarchy/vt/reviewed/faculty-periods.json`:

| Person | Supported VT faculty start | Evidence | Limit |
| --- | --- | --- | --- |
| Na Meng | 2015 | [VT CS homepage](https://people.cs.vt.edu/nm8247/) explicitly states she started as an assistant professor in 2015 and has been an associate professor since 2021. The saved 200 response has SHA-256 `c774affa3438214a5b69457c3968ef99442d6ac9ef24784fd6d62aa019ce8146`. | No faculty end or lab start/end stated. |
| Pinar Yanardag | 2023 | [VT CS seminar bio](https://website.cs.vt.edu/research/Seminars/Pinar_Yanardag.html) explicitly states she joined Virginia Tech in Fall 2023. The saved 200 response has SHA-256 `645478f5c74e508f069b7b315eae3cf7af3417818ba519d8de7f6be7f25639f6`. | Year precision only; no faculty end or lab start/end stated. |

`tools/vt_stage4_precheck.py` recomputes the saved response hashes, checks the exact source statements, and writes these two reviewed periods. Run it after `tools/periods_school.py extract vt`, which rewrites the period file. The general extractor found no appointment sentences on the sampled current CS faculty profiles; it did not parse the two statements above. The Anuj Karpatne profile URL returned 404, so it remains a lead.

The Stage 4 gate now reports **49 open PI period gaps**, down from 51. All six Git-ignored evidence-receipt warnings in the initial precheck were resolved by whitelisting those reviewed VT inputs in `.gitignore`; that accounts for the other six items removed from the initial total of 57. Most remaining gaps include the missing 2024 full-name listing. Do not infer a continuous appointment from nearby listing years alone. Stage 2 remains open and may change the census; Stage 3 is also not formally passed.
