# Exact owned-publication evidence for recovered sources

CMU's held cold trial32150403 exposed19 lost sources whose publication author is an attested spelling on the
PI's exact owned DBLP person record, but differs from the census spelling: StevenWu/ZhiweiStevenWu,
MariaBalcan/NinaBalcan and RuslanSalakhutdinov/RussSalakhutdinov. Another33 sources had an event/publication-year
discrepancy that incorrectly invalidated their publication-format evidence. Neither failure proves that the source
paper is outside the appointment, lacks the PI's own school, or is not research.

`recovered_publication_binding` resolves only the exact key on a PI's already owned PID, matching a nonempty
normalized literal title, compatible DOI and that publication's owner byline. Only that PID's attested selfnames
can supplement the local matcher for this recovery. Wrong PID/key/title/DOI and a different publication's author
cannot lend an alias. The PI record, global names, OpenAlex identities and registry anchors remain unchanged.

The same bound matcher is used by the earlier existing-recovery byline guard and the replay of the target's own
raw school authorship. A matching colleague's school does not qualify the target, and the ordinary school/campus
guard still applies. A source alias is not a new PI identity assertion or student-person verification.
When the alias is necessary, even a first recovery replays its own source. Alias-enabled raw authorship must
match the bound publication's nonempty title and compatible DOI as well as the evidence's source ID; a wrong
work cannot lend an affiliation. Ordinary existing-name routes, empty-byline first recoveries and first sources
outside the owned-DBLP route keep their previous admission rules; this change grants them no new alias authority.

Format and literal-page authority are separate from publication dates. An exact owned publication may establish
inproceedings/article/incollection even when the recovery's year differs. Both years remain in
`ctx.recovered_source_quality[*].year_disagreements`; `review_reasons` and `recovered_source_review:*` counters
make date discrepancies, panel-report titles and work-in-progress titles explicit. The recovery row keeps its
original date/year, while all ordinary window, appointment, DOI, R-PAP-26/36/38 and genre/quality gates remain.
The stricter corroboration requirement for a newly asserted DOI is unchanged. Source format cannot erase an
explicit raw abstract or other nonpaper type, replace source venue spelling, or borrow a longer same-title paper.

Date/genre diagnostics are not approval. In the frozen evidence, Trust Assessment names the2014 workshop while
its recovery says2016; Verified Optimization is substantive work-in-progress text with copyright2021 while its
recovery says2023; the iStar panel report explicitly summarizes a2024 discussion while its recovery says2025.
These remain scientific review issues, with original sources and both dates intact. The generic diagnostic does
not decide publication date from an event date, reject all delayed proceedings, or certify all inproceedings as
research. School-specific reviewed claims can hold an uncertain source independently of its format proof.

RyanO'Donnell's conference source conf/innovations/FilmusOW19 independently supplies DOI
10.4230/lipics.itcs.2019.34 and12 pages (owned year2019, recovery2018). Its complete eligible record can now
reach ordinary edition selection. It remains separate from journal DOI10.1214/22-ejp749: the shared OpenAlex
identifier alone cannot join source-distinct collection/title components. No publisher record is reconstructed.

`tests/fixtures/recovered-source-binding.json` contains109 compact reviewed source projections with individual
hashes and frozen input hashes:12 actual alias/date/short-abstract cases plus the prior97 quality controls.
All95 nonpaper controls remain excluded; the other2 controls pass format/quality only. Original private API/PID
bytes and both cold trial packages remain immutable outside git. Native regressions check the actual existing
byline guard, own-school replay, unchanged recovery dating, faculty/window/arXiv-date holds, and Ryan's separate
conference/journal records. No new heavy native, canonical, registry or store write is part of this change.
