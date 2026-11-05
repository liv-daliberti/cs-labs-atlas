# University of Chicago, stage 9: accuracy

Date: 2026-11-05. Gate (`atlas stage-gate uchicago 9`): **pass**. Method, numbers and every error: `accuracy/ACCURACY.md` (section "University of Chicago"); files `accuracy/sample-uchicago.json`, `verdicts-uchicago.jsonl`, `summary-uchicago.json`.

| Measure | Result | Bar |
|---|---|---|
| Lab-paper precision | 0.958 [0.798, 0.993] (23 of 24, 1 unclear) | 0.95 |
| Student-link precision | 1.000 [0.867, 1.000] (25 of 25) | 0.97 |
| Lab-paper coverage | 1.000 [0.741, 1.000] (11 of 11 true lab papers) | 0.90 |
| Student coverage | 1.000 [0.610, 1.000] (6 of 6) | none |

Found on the way: the sampler's lab-coverage pool read only the shared `dblp-dump-persons.json.gz`, which has no UChicago PIs (they are in `hierarchy/uchicago/raw/dblp-dump-persons-school.json.gz`); with it the pool was empty. `sample.dblp_persons(wanted, school)` now adds the school-local file (test in `tests/test_accuracy_sample_school.py`); `oalookup.py` takes the affiliation pattern from the charter for a school outside its table. Errors: one namesake cluster on a DBLP person page (Yuxin Chen, 6 papers), one initial-only match to a 2,938-author ATLAS paper; neither needed a rule to pass the bars (owner decisions in the report). The draw binds the sha of `copies.json`: rerun `sample.py --school uchicago` and the judgments if copies.json is rewritten before the release.
