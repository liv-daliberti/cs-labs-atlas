# ETH Zurich onboarding, stage 0 - 2026-11-24

Registered as `ethz` (status `onboarding`), scope D-0055. Charter commit 5e966772 on agent/ethz.

- Ids: I35440088, ROR 05a28rw58 verified live at api.ror.org (active, ETH Zurich). The whole lineage (109 children) is kept; `openalex_excluded` and `openalex_related` are empty. The ETH Board parent I2799323385 is in every ETH-domain lineage (EPFL, PSI, Empa, WSL, Eawag) and must never be an id or an exclusion.
- Regex separates ETH from EPFL, UZH, ZHAW ("Swiss Federal Institute of Technology" alone does not match). `school_config.py --check ethz`: ok. The DBLP-note test still needs the dump pass of the onboard-data chain.
- Hosts: `school_hosts.py ethz`: 24 hosts, 0 inconsistent. ethz.ch hosts answer robots.txt with a 404 CMS page (no rules); datascience.ch challenged (wayback-only); research-collection has Crawl-delay 10 and a 429 rate limit on bursts; phys.ethz.ch redirects to www.phys.ethz.ch; ini.uzh.ch is a UZH host (discovery only).
- Snapshot extension: first run 32538935/6 lost 10 filter tasks to node016 (/tmp full); resubmitted by the coordinator as 32539006 -> merge 32539008 (OA_DATE=2026-10-14, excluding node302,node014,node016).
- Stage 1 discovery so far (Wayback CDX, exact URLs): INFK faculty.html 2016-2021H1 then faculty/faculty.html 2021H2- (gaps 2017, 2018H1, 2019H2, 2020H1, 2024H1), emeriti.html from 2017, affiliated-faculty.html from 2021; ITET the-department/faculty.html, faculty/professors.html and people-a-z.html. Page formats, captures, the unit listings and stage 2 are not done.
