# Georgia Tech onboarding: protocol friction log

Started 2026-11-03 from branch `agent/uchicago` (all of UChicago's fixes in). Same columns as UChicago's log. Fixed = general tool/doc change with a test;
Requested = outside the onboarding tools. Target: fewer minutes lost than UChicago's (about 270).

| # | date | stage | what went wrong | fix / request | min |
|---|---|---|---|---|---|
| 1 | 11-03 | 0 | `python -I tools/oa_institutions.py` (the doc's `python -I` habit for tools) fails: `No module named oa_snapshot`. | Fixed: the doc and the tool docstring say `atlas run tools/oa_institutions.py` (the tool handles no downloads, so no `-I`). | 2 |
| 2 | 11-03 | 0 | `oa_institutions.py search georgia --country US` printed 60 unrelated Georgia institutions in snapshot order; the school was not among them and nothing said rows were cut. | Fixed: best-first order (names starting with the text, then shorter), `--type`, a "N more" line (test). | 4 |
| 3 | 11-03 | 0 | Charter authoring is a blank-page job: the affiliation regex, home_units, own_units, hosts and the department slots were written by hand from the UChicago charter (about 25 min). Probing for each department's listing URL and each affiliated unit's directory was by hand `curl` (BME has no `/people` or `/faculty`; the host gate caught the 404). | Requested R1: `atlas new-school --like <key>` (copy a released charter's structure with the school's ids/domains blanked) and a `discover_listings.py <key> --live` that probes `/people`, `/people/faculty`, `/faculty`, `/directory` on each charter host. | 25 |
