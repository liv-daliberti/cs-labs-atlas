# UIUC initial PI lab inventory — 2026-11-23

The official current CS directories yield **177 PI labs**: 108 with a ladder
faculty basis (including six individually verified named-chair professors), and
69 with a CS affiliate appointment and an explicit professor title in a home
unit. The census contains 257 distinct faculty entries; 80 remain outside the
PI inventory without sufficient advising/group or faculty-standing evidence.

This is a source-backed current inventory for the requested coverage report,
not a complete historical UIUC census or a published school package. Other
computing-related units and departed faculty still need the normal onboarding
review. PI group labels follow R-HIER-01; generated labels are not presented as
the official names of separately named laboratories.

## Source review

Three saved HTTP-200 pages supply four reviewed listing groups: school faculty
(154 rows), affiliates (78), adjuncts (16), and emeriti (14). Five people occur
in more than one group: 262 source occurrences, 257 distinct people. The source
manifest is `reviewed/live-listing-sources.json`. Its hashes are checked against
the original bodies in `raw/school-captures.sqlite`; all source quotes are
verified by the ordinary listing/census readers.

Separate numeric groups on the affiliate-and-adjunct page are parsed into
distinct reviewed slots: an adjunct's outside-employer professor title must not
become a regular UIUC faculty appointment. Explicit adjunct/emeritus slot kinds
now constrain an otherwise bare professor title, as courtesy slots already do.
UIUC's charter recognizes literal `Asst Prof`, `Assoc Prof`, teaching-associate,
and research-associate title forms without turning teaching/research titles into
ladder appointments. The named-chair records in `pi-basis-evidence.json` have
individually read professor-status quotes from saved official profiles. An
emeritus-only chair profile was inspected and remains excluded.

## Coverage interpretation

UIUC has a real lab inventory, so the export lists its PI names and source URLs.
Its paper/student coverage remains **collection pending**, with blank counts
rather than invented zeros. UIUC is kept separate from the zero-count totals
calculated from the other schools' built packages. The 2016–2026 historical
roster gaps are neither waived nor filled by current observations.

The independent OpenAlex snapshot import remains filter job 32513186 followed
by merge 32513187. No existing school package is rebuilt for this report.
