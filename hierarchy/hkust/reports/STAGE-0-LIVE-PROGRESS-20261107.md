# HKUST live-first core checkpoint, 2026-11-07

This is an incomplete onboarding checkpoint. It is not a release, a complete
university census, or a passed identity/paper/accuracy gate.

The current official CSE regular-faculty directory was captured on 2026-11-07.
The reviewed live-source manifest binds its raw SHA-256
`5efbf6f3f3fae6e6106d263ff1accbc6a5efffb6461e4187dee26f5e1fdbe31d`,
53 entries and actual observation time. The new standard directory parser
produces 53 faculty rows and 53 ladder-faculty PIs, preserving bilingual names
and excluding contact cells. A 30-row sample with seed 20261107 was inspected;
all sampled professor ranks and named rows were supported by the captured
directory. Historical coverage is not inferred from this current listing.

The charter uses primary OpenAlex institution I200769079 and ROR 00q4vv597,
checked in the local institutions snapshot. The separate related Guangzhou
university I4405261251 is excluded from automatic Hong Kong attribution. No
related-only expansion is configured. The charter and its configured CSE host
check pass; other computing-related units and repository access remain open.

The standard website register contains 47 captured websites with reproduced
official discovery navigation and six unresolved cases. Five previously
pending homepages were individually reviewed: Cunsheng Ding's navigational
academic homepage, Andrew Horner's homepage and linked research interests,
Pedro Sander's homepage and linked HTML CV, Nevin Zhang's framed homepage and
published frame contents, and Chaojian Li's Sponge Computing Lab and named PI
on its team page. The first four are PI-homepage fallbacks, not claims of a
separately named lab. The team page establishes Chaojian Li as Principal
Investigator; students have not been admitted by this website review.

One previously staged website pass was held in this stricter register:
Long Chen's independent homepage still lacks a reproduced official discovery
link. Yinghao Xu's official profile links the HTTP version of his homepage;
the register preserves that literal link and its independently checked HTTPS
version on the identical host and path. The other
open cases are Yike Guo, Jiaya Jia, Huamin Qu, Chi-Keung Tang and Dan Xu. Failed
access and incomplete navigation are not proof that a website does not exist.

School-local census overrides record 25 individually reviewed DBLP identities.
Nine have compatible full names and verified website link evidence; sixteen
more were checked against multiple exact works independently listed on the
PI's verified website. These decisions identify authors only. Career
bibliographies do not count as verified HKUST papers without school affiliation,
appointment, paper-only and edition checks. Other identity proposals remain
unaccepted. The standard school-local DBLP input contains only the reviewed
identities, with automatic name-only assignment disabled.

Eight faculty appointment starts were reviewed with source hashes and quotes:
Pedro Sander 2006, Shuai Wang 2019, Xiaomin Ouyang fall 2024, Lionel Parreaux
February 2021, Jiasi Shen 2023, Qian Zhang September 2005, Mo Li 2023, and
Wei Wang 2015. Rank promotions are not treated as school
departures. An automatic Yangqiu Song candidate was explicitly rejected: its
2016 date belongs to advisee Huiru Xiao and the advisee's subsequent employment,
not to the PI's appointment. Albert Chung's 2001 date belongs to his Oxford
DPhil; joining HKUST afterward does not state an exact joining year. Bo Li's
affiliation since 1996 still needs explicit faculty-role dating. Review appointment candidates before acceptance;
do not rerun automatic extraction over these reviewed periods without review.

The parser exposed a census handoff defect: separately parsed department
profiles were discarded when no personal homepage was listed. The census
writer now retains the department profile as a fallback; a separate verified
lab website is still required. An integration regression test covers both
profile-only rows and retention of an explicit homepage.

The cohort metadata extension is running as array 32145819, merge 32145820,
pinned to code 095e2ae. It collects 16 primary-institution lineages in one
streaming pass, with no OpenAlex API credits, and does not change the existing
snapshot stores. Receipt: `scratch/top25-goal-1107/snapshot-jobs.json`. Paper
counts will be measured from the standard build after the extension finishes.

Validation: 1,516 tests passed, 15 skipped; lint and all 16 charters passed.
The all-stage trap check retains the expected missing lab-page cache: the
standard cache importer requires the first built PI package. That import is
scheduled after the preview build. No empty cache is used to satisfy it.

Open work: complete the six website cases, the remaining author identities
and appointment intervals, historical CSE sources and computing faculty in
other departments; build and independently review school-attributed papers;
then continue student evidence under the owner's resumed goal. No new paper
admissions or completeness exceptions are claimed in this checkpoint.
