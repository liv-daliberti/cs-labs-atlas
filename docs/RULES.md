# Build rules

The rules `tools/pi_hierarchy.py` (and the audits) apply, with the date each was decided. Each rule has a stable id;
`tools/make_release.py` copies this file into every release and lists the ids in the release `MANIFEST.json`. The code
comments next to each rule carry the cases that motivated it; `tests/` holds those cases as tests.

Format: `### <id> (<date>, <who>)` then the rule. "owner" is a decision by the project owner; "owner: best judgement" is
one the owner delegated; "build" is a fix found while building.

## The hierarchy

### R-SRC-01 (2026-11-16, owner) — a unit's founding bounds its source window
A unit founded after the school window starts requires Stage 1 faculty listings from its founding year onward.
The school window remains 2016–2026. Pre-founding unit-years are inapplicable, not waived; founding proves no PI
appointment and excuses no missing roster in an active year. The charter records `founded_year` and `founded_evidence`
with an official school-domain history URL, original captured SHA-256, literal visible quote naming the year, and
the owner's review (`reviewed_by`, `reviewed_on`, `owner_quote`). Stage 1 verifies the saved HTTP-200 bytes and quote;
missing or invalid proof keeps the entire school window required and fails the gate. Owner approved AIR's 2020–2026
source window on 2026-11-16: “Review AIR from its 2020 founding (Recommended)”. AIR's 2020–2021 source gaps remain open.

### R-HIER-01 (2026-10-21, owner)
School → department → PI lab → papers + students → student papers. Every census faculty member with `is_pi` gets one
own lab (the PI and their advisees). A census lab unit is reused only when the collection unit has this PI as its single
leader; otherwise a new own lab is proposed and the multi-leader or umbrella unit stays a collective, not a lab.

### R-HIER-05 (2026-11-09, Claude on the owner's delegation) — computing-as-object social scientists are out of scope
Owner delegated the choice to Claude on 2026-11-09 (coordinator question `owner_question_1_computing_as_object`). Faculty whose research object is digital society, ethics or
information policy rather than computing methods are EXCLUDED as a class, even when the computing-share test passes (it counts DBLP-indexed CHI/CSCW venues). A PI is in
scope when computing is their research method or object across the body of work. Recorded reviewed scope exclusions (`decision: excluded_scope`, evidence kept in the review row):
Oxford Internet Institute's Gina Neff (sociologist, OII listing 2022: 'Professor of Technology & Society'; all 16 works arrive by advisee routes, not by her own ORCID or
DBLP id; the last 3 carry a Cambridge Minderoo Centre affiliation), Luciano Floridi, Mariarosaria Taddeo, Sandra Wachter and Bernie Hogan. Their works do not enter through
any route. Reversible per person with new evidence; a person whose own work is computing methods is not covered by this class.

### R-HIER-02 (2026-10-21, owner)
Centres, initiatives, consortia, programmes, projects, clusters and institutes are not labs (`COLLECTIVE`), unless the
unit name also says lab, laboratory or group.

### R-HIER-03 (2026-10-27, owner)
Across labs, a matching name alone never makes one student. Name variants merge only within one lab (one PI); same-name
records in other labs are counted (`student_same_name_other_labs_unmerged`) and listed by `tools/student_audit.py` as
candidates for review.

### R-HIER-04 (2026-10-29, build)
The PI is not their own student: a lab roster record whose full first given name and family name are the PI's own
(nickname-equal, generational suffix ignored, initials never count) and that holds no student or postdoc role leaves the
lab's students (`pisListedAsOwnStudent` in the report). `full_pair`.

## Which papers are a lab's papers

A work from `hierarchy/<school>/openalex-sweep.sqlite` (plus the PI's own works in `pi-works.sqlite`, and the DBLP and
lab-page recoveries) is the PI's lab paper when (a) an authorship that matches the PI's name ties it to the school,
(b) that authorship is the PI (identity), and (c) the paper falls in the PI's appointment.

### R-PAP-01 (2026-10-21, owner) — appointment
A paper is inside the appointment when `contains()` places every possible publication date inside a reviewed faculty
period (the site's rule; boundary years unresolved), or else when a captured department listing from the paper's own
calendar year names the PI. A listing proves that calendar year only.

### R-PAP-02 (2026-10-28, build) — listings that prove nothing
A dated listing row that lists the person as a student or postdoc, or announces a future appointment ("incoming",
"will join", "starting 2025"), proves no appointment (`not_faculty_row`). Reviewed values may carry a season note
("2020 (Fall)"), which narrows the date to that term (`datebounds`).

### R-PAP-03 (2026-10-29, owner) — stale listings after a move
A listing after an evidenced departure (`faculty_end_moved` evidence) is a stale page, not an appointment: Princeton ECE
kept Mung Chiang (left 2017) and Yuxin Chen (left 2021) on its list through 2026. Such years are kept aside as
`listingsAfterMove`; a later collection or reviewed period that covers the year keeps the listing.
`listings_after_move`. Since 2026-10-29 a reviewed period (census-overrides.json) whose evidence has kind
`faculty_end_moved` counts as the departure too (Cynthia Rudin, MIT Sloan to Duke in 2016: MIT CSAIL's PI listing still
named her in 2026; Sharad Goel, Stanford MS&E to Harvard Kennedy School in July 2021).
Since 2026-11-02 (owner) a PI dropped from the school's own faculty listing (adjunct, courtesy or emeritus rows count while the row exists) has left: a reviewed period closes at the month of the first dated listing without them, bounded by the last dated listing that has them; both captures are cited in the override's evidence (`faculty_end_moved`).

### R-PAP-04 — identity of the authorship
In order: never an author id reviewed as someone else's (`notOpenAlex`), or another PI's reviewed id (2026-10-28: Simon
and Philip Wong); a reviewed OpenAlex author id; the PI's ORCID; a DBLP-verified collection work; the PI's DBLP person
page by DOI or by title (±1 year); the PI's institutional publication list; the lab's own publications page (title inside
a citation, 30+ characters); a stated advisee of the PI as co-author. An author id that two or more advisee co-authored
works carry, or that sits at the PI's name on an identified work, is anchored and identifies the PI's other works.

### R-PAP-05 (2026-10-29, build) — the DBLP dump
The PI's full DBLP person page comes from DBLP's own dump (`tools/dblp_dump_persons.py`), not only the cached lists. A
PI without a DBLP id takes the one person record of exactly that name when no other record carries the name; a census
DBLP id whose names never carry the PI's name is dropped (`name_conflict`); ORCIDs on the DBLP person join the PI's.

### R-PAP-06 (2026-10-29, build) — mixed author ids
A reviewed mixed OpenAlex id (another person's record that also holds some of the PI's works; Song Mei) neither anchors
nor blocks: each authorship under it needs per-work evidence.

### R-PAP-07 (2026-10-29, owner: best judgement) — initials
Two initials prove nothing ('M. Wang' is not Mengdi Wang, 'Y. L. Chen' is not Yuxin Chen): for the advisee-co-author
identity, the PI or the advisee must be written with a full given name, unless the initials spell every given name of a
PI with two or more ('M.T. Islam' is Md Tauhidul Islam). `all_initials`.

### R-PAP-08 (2026-10-29, build) — generational suffixes
'John W. Fisher III' is John Fisher: a trailing Jr/Sr/II/III/IV is not the family name (`nosuffix`).

### R-PAP-09 (2026-10-29, build) — the school's own institutes
A raw affiliation string made only of the school's own unit names (CMU's Robotics, Neuroscience, Language Technologies
... Institute) names no other institution (`OWN_UNITS`).

### R-PAP-10 (2026-10-29, build) — page 1 ties
A sweep work whose OpenAlex record gives the PI no school, while the paper's own first page (read by
`tools/pi_fulltext_affiliation.py`) ties the school to this PI by name, is affiliated: the primary source outranks
OpenAlex's derived affiliation (Chi Jin, Karthik Narasimhan, Adam Perer).

### R-PAP-11 (2026-10-28, build) — advisee at the school
When the PI's authorship names no institution (none, or a department only) and a stated advisee of the PI on the same
byline lists the school, the paper is the lab's (identity and appointment still apply).

### R-PAP-12 (2026-10-29, owner) — unaffiliated bylines
A work of the PI's own anchored or reviewed OpenAlex id whose byline carries no institution at all (typically arXiv) is
the lab's when a stated advisee of the PI is on that byline by full name.

### R-PAP-13 (2026-10-29, owner: best judgement) — transition years
For such unaffiliated bylines, in a PI's arrival or departure year a listing proves only its own side of the capture
date: Thomas Griffiths's last Berkeley listing is April 2018 and he moved to Princeton that July, so an unaffiliated
September 2018 preprint is not a Berkeley lab paper (an affiliated one still is). The window's first year (2016) is no
arrival and the current year no departure. `transition_side`.
The build counts every paper a transition-year listing admitted by its side of the capture (ROADMAP #29, `report.json` counts
`transition_year_{unaffiliated,affiliated}_{inside,outside,undecided,no_capture}`; `undecided` is a date range that straddles the
capture date, `transition_status`). The count is reported; affiliated papers stay in as before.

### R-PAP-14 (2026-10-28, build) — namesake PIs
When two PIs claim one paper through the same byline name, the PI holding that author id as a reviewed id keeps it; else
the PI whose given names the byline spells out; a byline with initials only that no reviewed id settles goes to neither
(Philip / Simon Wong, Hari / Hamsa Balakrishnan, Jean-Philippe / Patrick Thiran).

### R-PAP-15 (2026-10-29, owner: best judgement) — books and translations
A run of 5+ book chapters of one PI with one venue and one year is one book: the chapters fold into the book's own
record, or into one chapter standing for the book. Outside EPFL, a book or chapter whose title reads as German, French,
Spanish, Italian or Portuguese and not English is a translated edition and is dropped (Leiserson's lab had 131 chapters
of the German and French editions of CLRS). `fold_books`, `foreign_title`.

### R-PAP-16 (2026-10-29, build) — editions
One record per unique paper and lab: editions (preprint, conference, journal) share a normalized title; the published
edition leads (a non-arXiv DOI, then a collection work). A second OpenAlex record of the same collection work is kept as
an edition, with its own byline.

A sourced `paper-claim-review.json` merge can name the preferred edition by exact OA/DOI/work identifiers
(2026-11-08). When source and target already belong to the same native edition group, the target is selected while its
complete, normally eligible row still exists, before compact edition pointers replace it. The target must independently
pass identity, own school, faculty time and paper-type gates; a review never admits it from title similarity or reconstructs
missing affiliation/appointment fields. Conflicting targets, ambiguous selectors and cycles stop the build. A missing
complete target holds the source; a folded pointer alone cannot authorize a new lead. All eligible bylines remain available
for candidate student links. Different-title reviewed merges retain their existing eligible-target handling.

### R-PAP-17 — not papers
An exact owned DBLP CoRR recovery (`journals/corr/`) retains type `preprint` even though DBLP uses an `article` XML element. This format correction does not supply authorship, school affiliation or faculty time; the ordinary recovery gates still apply. Harvard's verified January2026 Iglesias manuscript `journals/corr/abs-2602-00669` triggered this correction (2026-11-16).

Datasets, paratext, peer reviews, errata, supplementary materials, grants, standards, retractions, reference entries
and library guides are not papers (`NOT_PAPERS`).
Publisher records titled `Notice of Removal: ...` are removal notices, not the research paper they name. Oxford's sampled IEEE Internet of Things Journal DOI `10.1109/jiot.2020.2967734` is dropped as `removal_notice`; an ordinary paper with the same subject remains eligible.

### R-PAP-18 (2026-10-29, owner: accuracy sample) — not papers: repository records and paratext (R1)
Dropped from every lab (`not_a_paper`): OpenAlex type `software` (Zenodo, Figshare, Code Ocean records); supplement and
artifact records by title (`MOESM1`, `Additional file 2 of ...`, `Supplement 1: ...`, `Artifact for ...`, `(Artifact)`,
`Reproduction/Replication package`, `Code and data for ...`) and protocols.io protocols; errata (`Publisher/Author
Correction`, `Correction to:`, `Erratum`, `Corrigendum`); JST machine translations (`【Powered by NICT】`); Dagstuhl
Reports and Manifestos (venue, `10.4230/dagrep`, `10.4230/dagman`, a title ending `(Dagstuhl Seminar N)`); Oberwolfach
Reports (venue, `10.4171/owr`); titles that open as an editorial, foreword, preface, guest editors' introduction,
introduction to a special issue or section, message from the chairs, or 'in this issue'; award or prize announcements
('2017 ISCB Innovator Award: Aviv Regev', a title ending in Award/Prize/Medal of 8 words or fewer); workshop or tutorial
proposals ('Workshop on ...', 'Tutorial: ...', 'Tutorial on ...' at a conference, '...: A Collaborative Workshop with ...');
highlights columns (', No. 31'); tributes ('In memoriam', 'Obituary', 'In memory of ...' and 'A tribute to ...' at the
start of the title, '<Name> (1927–2016)', and a title that is only a person's name: 'Derek Chiou'). The patterns are
anchored: 'Puzzles in Memory of Solomon Golomb', 'Remembering the "when"', '...: A tutorial overview' and 'MedAL' stay.
Per-pattern counts and ten samples each on the 2026-10-29 build: `archive/docs/not-paper-patterns-20261029.md`. One-page columns
('CACM community') are not caught (no page counts). OpenAlex type `editorial` alone is not dropped (127 such rows have
research-like titles). Report: `not_paper:<tag>`, samples in `notPaperSamples`.

**R-PAP-18 addendum (2026-11-18, Harvard gate 9 pi1: Gil's T-RO notice)** IEEE correction notices are titled `Corrections to "<article title>"` (Harvard held Gil's `10.1109/tro.2025.3645896` as a lab paper). `ERRATUM_TITLE` now also matches a title that opens `Correction(s) to` followed by a quote mark; `Corrections to the Kalman filter ...` (no quote) stays a paper.

### R-PAP-19 (2026-10-29, owner: accuracy sample) — meeting abstracts are not papers (R2)
Dated Oxford Stage 9 review (2026-11-14): `Cardiovascular Research` joins the meeting-abstract journals for records typed `conference-abstract`. The sampled P503 item (DOI `10.1093/cvr/cvy060.360`) is in the publisher's 2018 supplement, page S122, “Abstracts > F. Poster Session III”; ordinary journal articles in that venue stay eligible. Test: `test_oxford_cardiovascular_research_poster_abstract_is_not_a_paper`.
Dated Oxford Stage 9 review (2026-11-14): BMJ `Heart` British Cardiovascular Society supplement DOIs of the form `10.1136/heartjnl-YYYY-BCS.N` are meeting abstracts. Oxford's own repository labels the sampled `10.1136/heartjnl-2019-BCS.67` as subtype Abstract in volume 105 Supplement 6, page A69. Ordinary `Heart` research articles with other DOI forms remain eligible. Test: `test_oxford_bcs_heart_supplement_abstract_is_not_a_paper`.
Dated Oxford Stage 9 review (2026-11-14): eight exact `Journal of Pharmacological and Toxicological Methods` volume 88 records with one or two pages are held in Oxford's reviewed `not_papers` list. [Tampere University's record](https://researchportal.tuni.fi/fi/publications/in-silico-modeling-of-human-ips-cardiomyocytes-effect-of-drugs-an/) explicitly calls DOI `10.1016/j.vascn.2017.09.236` a meeting abstract; publisher-deposited Crossref pages and that same issue segment support the other exact decisions. The latter classifications are issue-context inferences, recorded as such in the review file. Full research articles elsewhere in the journal remain eligible.
Dropped (`meeting_abstract:<why>`): a meeting-abstract venue (AGU Fall Meeting Abstracts, Bulletin of the APS, APS
Division/March Meeting Abstracts, ECS Meeting Abstracts, ISMRM proceedings, EGU General Assembly); a supplement or
meeting DOI (`10.58530/` ISMRM, `10.5194/egusphere|epsc`, `suppl`/`supplement`, AACR `.am20xx`, ECS `/ma20xx`, ASH
`blood-20xx-`, `meetingabstracts`) on an abstract, article or other record; a title `Abstract 136:`; type
`conference-abstract` in a journal's meeting supplement (Cancer Research, Circulation, Blood, Stroke, JCO, JASA, Academy of
Management Proceedings, ...); a single-author `conference-abstract` (keynotes and invited talks, IWASI 2017 'Covering
our world with sensors'), unless the PI's DBLP page lists the same title with co-authors (OpenAlex cut the byline); and
a `conference-abstract` titled as a keynote or invited talk. CS conference abstracts with co-authors (EC, FPGA, SIGCSE,
CHI EA) stay. Reversible per school: the report counts every `not_paper:meeting_abstract:*` tag.
**Extension 2026-11-09 (owner delegated the choice to Claude on 2026-11-09; Oxford admission review, T111):** congress-supplement abstracts of two
series are dropped as `meeting_abstract:congress`. (a) Neuromodulation (INS congress; Elsevier DOI `10.1016/j.neurom.YYYY.MM.NNN`) when the record is typed
`conference-abstract` or its title opens with a program code (`PO222 / #1008 `, `O025 `, `RF006 `, `ID: 324641 `); a title-case Neuromodulation article under the
same DOI shape stays. (b) ERS congress abstracts (`10.1183/13993003.congress-YYYY.*`, and the `1393003` typo OpenAlex carries), any type. On the Oxford round-2
package: 10 net-new Denison rows and 1 Min Chen row drop (the owner expected 11 net-new; 10 Denison counts the 'ID: 324641' supplement). Tests: `tests/test_oxford_rules_1109.py`.

### R-PAP-20 (2026-10-29, owner: accuracy sample) — page 1 before the unaffiliated-advisee route (R3)
Before a work enters through R-PAP-12, page 1 (`tools/pi_fulltext_affiliation.py`: the arXiv v1 bulk copy or the
store's local PDF, kept in `pi-works.sqlite` pages) is read: when page 1 names the school nowhere, not even loosely
('Berkeley', 'CMU', 'Lausanne', 'CSAIL'), and its author block (title and arXiv stamp removed) names another institution,
company, e-mail or web domain, the paper was done elsewhere and is dropped (`unaffiliated_page1_elsewhere`; pi-0 is
Physical Intelligence's). A page with no affiliations stays. Without a page read the route stands and the row carries
`page1_check.status = page1_unchecked` and `flags: ['page1_unchecked']`. `page1_elsewhere`.

### R-PAP-21 (2026-10-29, owner: accuracy sample) — chapters without a venue fold by DOI prefix (R4)
A book chapter with no venue is grouped by the book DOI its own DOI extends (`10.1145/3241304.3241312` ->
`10.1145/3241304`): every such chapter folds into the lab's own book record with that DOI (Aviad Rubinstein's 16 chapters
of his ACM Books monograph), and 5+ with no book record fold into one chapter (R-PAP-15). `fold_books`, `doi_book_prefix`.

### R-PAP-22 (2026-10-29, owner: accuracy sample) — dissertations are not the adviser's papers (R5)
OpenAlex type `dissertation`, and any Stanford Digital Repository record (`10.25740/`: theses, honors theses, capstones),
leave the lab unless the PI is the record's first and only author: catalogue bylines list advisers and readers
('Kundaje, Anshul, 1980-' on Minji Kang's dissertation). `not_a_paper` tag `dissertation`.

### R-PAP-23 (2026-10-29, build) — a record carrying another work's DOI
A non-preprint record whose DROPS (LIPIcs/OASIcs) DOI names a venue year two or more years after the record's own date
mixes two works and is dropped (`doi_year_conflict`). Why Manning's row was wrong: not the edition merge, but OpenAlex's
own record W3011573503 (Stanza's 2020 arXiv record, with Manning's ORCID authorship) carried the title and DOI of an
unrelated SLATE 2023 paper in the 2026-10-21 sweep snapshot. Stanza stays through its ACL record.

### R-PAP-24 (2026-10-29, owner: accuracy sample) — page 1 for DBLP-anchored works (R8)
The page-1 pass also reads works on the PI's DBLP person page whose authorship at the PI's name, under any author id,
lists no institution (`candidates` kind b), from the arXiv bulk copy or a local PDF only (no publisher pages). Page 1 now
also ties the school through the PI's symbol marker's footnote at the foot of the page ('Jacob Fox∗' ... '∗ Stanford
University, ...'; not an equal-contribution note): `tie` mode `footnote`; `pi_fulltext_affiliation.py retie <school>`
re-reads stored pages. A work so tied enters at a non-anchored author id when a non-advisee identity (the PI's DBLP page,
ORCID, ...) names it (`pi_work_page1_dblp_hits`).

**Primary-source candidate correction (UW, 2026-11-24).** A cached original primary-page tie plus an independently established non-advisee work identity can also admit the candidate when the index already has affiliation text. The presence of that text does not establish that the provider author ID has been anchored. Preserve the original work and use the same exact PI tie, blocked-ID, full-name, owned-publication, school, appointment and paper-type checks. This route never anchors the new author cluster, never treats a derived author-affiliation review as admission evidence, and never changes a publication date to fill an appointment gap.

### R-PAP-25 (2026-10-29, owner: accuracy sample) — bare unit names (R6)
A PI authorship with no institution whose raw affiliation strings are only unit names counts as the school when, for
every string: a generic name every school has ('Computer Science'; all words discipline words, `generic_unit`) is the
PI's own unit and another author on the byline lists the school; a name only this school has is the PI's own unit (a
census department, or a unit the PI's school-affiliated strings name on 2+ works) with an anchored identity or a school
co-author ('Operations Research & Financial Engineering', Sircar), or any unit of the school (census departments,
collection units, units seen on the school's strings) with a school co-author ('Center for Information Technology
Policy', Mittal with Bhagoji). `bare_unit_school`, `school_via_bare_unit`.

Corporate affiliations are not university units (2026-11-16 source review). A company prefix in a joint company/university
string must not train the unit corpus, and a company-only PI affiliation cannot qualify through an already learned unit
or an unaffiliated-PI/advisee fallback. Independent explicit university or primary paper affiliation evidence remains valid;
withholding an unsupported university attribution does not establish that the work was done exclusively elsewhere.

### R-PAP-26 (2026-10-29, owner: accuracy sample) — date by the venue version (R9)
A preprint or repository deposit (type preprint, an arXiv DOI, or a repository as primary source) whose normalized title
is a venue publication on the PI's DBLP person page (not CoRR, ECCC or IACR ePrint) is dated by that record's year, the
earliest if several, for the appointment check and the row's year (`dated_by`: the OpenAlex date and the DBLP key).
Engelhardt's ML4H 2023 paper had only its October 2021 arXiv record; Sandholm's IJCAI 2009 paper was a 2018 KiltHub
deposit. A venue version from before the atlas window (2016) takes the row out (`dated_before_window`): a later deposit
or preprint of an older paper is not a lab paper of 2016-2026. `venue_version_date`.

### R-PAP-27 (2026-11-02, owner: accuracy pass) — commentaries, columns and short invited abstracts
The Michigan stage-9 sample found a CACM 'Technical perspective' (one page), a CACM Viewpoint (3 pages) and a two-page SIGCSE
keynote abstract. Dropped (`not_a_paper`, tags `commentary`, `column`, `invited_abstract`): a title that opens 'Technical
perspective'; a magazine piece of 3 pages or less (`COLUMN_VENUE`: Communications of the ACM, IEEE Micro, Computer, IEEE
Security & Privacy, IEEE Software, IEEE Pervasive Computing, ... exact venue names, so 'Computer Networks' stays); a
single-author conference-paper record of 2 pages or less (keynotes, invited talks, new-faculty highlights, tutorial abstracts)
unless the PI's DBLP page lists the title with co-authors (OpenAlex cut the byline). The page count is DBLP's `<pages>`
(`tools/dblp_dump_pages.py` -> `hierarchy/dblp-dump-pages.json.gz`, joined by DOI, else title, the largest count when a title has
several records); without a page count only the title rule applies. A bare page number (no range) counts as one page in CACM
and for a conference record (keynote abstracts: ICAART 2016 '5', IWASI 2019 '1'), never for another magazine (ACM Queue's is an
article number). `short_piece`, `page_count`.
Also dropped (`proceedings_volume`): a title opening 'Proceedings' that names a conference, workshop, symposium, race, competition, an
ordinal or a year (whole volumes: SAT Race 2019, MOBICOM 2021); and (`supplement_abstract`) a journal-article record whose title
opens with a number ('203. ...', '(338) ...': abstracts of Biological Psychiatry, Journal of Pain, Journal of Adolescent Health
supplements). Book chapters and records with no venue keep their numbers.

### R-PAP-28 (2026-11-02, owner: accuracy pass) — period boundaries and continuity
Two causes behind Klasnja's missing 2020-2025 papers (Michigan; 12 school-affiliated papers a year). (a) A reviewed period
with a year-precision start ('2020') cannot place a paper dated inside that year against its boundary (`boundary_unresolved`):
a paper whose own authorship names the school (institution lineage or raw affiliation, not the advisee, unit-name, page-1 or
cross-affiliation routes) is kept in the period, the affiliation being the dated statement the period lacks, as in R-PAP-13's
transition years (`period_boundary_affiliated`). (b) A reviewed period built from one dated capture is an open lower bound
that ends at its last confirmation (`asof`), so the years between two such captures held nothing. A continuity period
(`bridge_<a>__<b>`, `reviewed: R-PAP-28 continuity bridge`, citing both captures) covers the gap from the first period's
`asof` to the second's start when the first is open, neither period nor the PI's listings carry departure evidence
(`faculty_end_moved`, `listingsAfterMove`), and the PI's identified works name the school in every full calendar year of the
gap (`continuity_bridge_periods`). `periods.bridge_periods`, `papers.continuity_bridges`, `direct_via`.

### R-PAP-29 (2026-11-02, owner: accuracy pass) — cross-affiliated bylines
Wenisch's HPCA 2016 paper: OpenAlex credits him to NVIDIA only, while a co-author is credited to Michigan (a shifted position)
and his own works of that year name Michigan. A work whose PI authorship names only companies, agencies or other non-university
institutions (OpenAlex type company, nonprofit, government, facility, archive, other), whose byline names the school for another
author, whose PI identity is strong (reviewed id, ORCID, DBLP, institutional list), and with 2+ school-affiliated identified works
of the same year, takes the school as `cross-affiliated byline: ...`. The appointment and paper-type checks still apply.
2026-11-03 (fresh hand check: 3 of 20 wrong): not when the appointment that admits the paper is a non-primary one (`NONPRIMARY`: adjunct, on
leave, consulting, visiting, courtesy, affiliate, emeritus, part-time in the listing quote or the period's evidence quotes). Those were
company papers of an adjunct or leave-taker with one co-author credited to the school (Savarese/Salesforce under a Stanford adjunct
listing, Metze/Meta 'Associate Research Professor (On Leave)', Kalai/Microsoft 'Adjunct Associate Professor'). Counter
`cross_affiliation_nonprimary_appointment`.
2026-11-08 (owner, first Toronto build): an explicit reviewed `cross_affiliation_holds` override can hold this company-only
fallback in the exact source observation years (`action: hold_company_only_fallback`, `years`, reason, and owned-source
URL/SHA256/quote/`observedAt`). The source must explicitly show a nonprimary appointment, and its observation years must
equal the held years. `leave_start`/`leave_end` remain null and `departure_inferred` false. This marks source uncertainty,
not a negative paper/person verdict or a whole-year leave fact: an earlier paper in that same observed year remains held
because the leave dates are unknown. The guard runs only after normal identity/appointment admission and only for the
cross-affiliation fallback; direct own-school or primary-PDF evidence and genuine prior history stay eligible. Malformed
reviews fail closed. Counter `cross_affiliation_review_hold`; exact held candidates and source reviews remain auditable.
Also not when the paper is admitted only by a listing (no period) in the PI's arrival or departure year and falls on the far side of the
capture date (R-PAP-13's transition rule, applied as for an unaffiliated byline: a company credit says nothing about where the work was done;
Smola's 2017 Amazon papers under his last CMU listing, April 2017). Only for a PI with 2+ listing years whose listing is 3+ years old (one captured listing, or a last capture of the past two years, shows no observed
arrival or departure: Turitsyn 2019, Rosenholtz 2024 were wrongly dropped without this). And only when the PI's identified works of that year credit other institutions more often than the school (Smola 2017: Amazon 7, CMU 1; Turitsyn
2019, MIT 11 vs D. E. Shaw 2, stays). Counter `cross_affiliation_transition_outside`. A count of the PI's works
by institution was tried first and rejected: it dropped 8 of 17 true lab papers of dual-role faculty (Freeman, Yang, Xiong, De la Torre). A byline
with no institution at all (pi-0) and a credit to another university are untouched. `school_basis`, `STRONG_IDENTITY`,
`CROSS_KINDS`; counter `school_via_cross_affiliation`.

**R-PAP-29 addendum (2026-11-18, Harvard gate 9 pi1: Tambe's AAAI-23 SAHELI paper)**
A co-author's school credit does not admit a paper whose page 1 credits the PI elsewhere: when the page-1 read of the work (arXiv v1 or the catalog's copy; `pi_fulltext_affiliation.py pdf`, which now also reads
works whose PI authorship is credited only to companies/agencies while another author is the school's) puts the PI's own name at an institution or company that is not the school (footnote line of the PI's marker,
or the sentence after the name; not when it names the school beside another institution), the cross-affiliated route is refused (`page1_pi_credited_elsewhere`, counter `cross_affiliation_page1_pi_elsewhere`).
No page read, or a page that gives the PI no affiliation, leaves the route as it was (Wenisch).

### R-PAP-30 (2026-11-02, owner: accuracy pass) — listings OpenAlex contradicts go to review
Michigan's sample credited Ziyou Song's SSRN preprint to Michigan through a Wayback ECE listing while OpenAlex places his
works of those years at the National University of Singapore. Two signals, built before the rows from the PI's identified
works (identity as R-PAP-04): (1) a listing-only year (a department listing, no period covering the year, and neither the PI's first listing year after 2016
nor the last before the current year: arrival and departure years belong to R-PAP-13) in which the PI's
identified works credit another institution (2+ works) and none credits the school is not an appointment by itself: the papers
that year admits through the weak routes (advisee, unaffiliated byline) are withheld, never the PI's school-affiliated ones
(there are none in such a year); (2) an advisee-route or unaffiliated-byline record whose twin (same normalized title, same PI) credits the PI only to other
institutions goes to the review list, and is withheld when that twin is dated earlier and falls in a year of kind (1) (Song's
SSRN preprint is dated 2025-01-01; its National University of Singapore record 2024-12; his 2024 listing is a visiting page).
Only the advisee routes are ever withheld: a paper naming the school itself, or tied by its first page, stays. Everything
goes to the review list `report.json` -> `staleListingReview` (`kind` `listing_year` with the listing, the other institutions
and the withheld papers, or `twin_record`); no period is closed (R-PAP-03's listing-drop rule of 2026-11-02 stays the owner's
decision). Counters `stale_listing_pi_years`, `stale_listing_withheld`, `twin_record_credits_elsewhere`, `twin_record_withheld`.
`listing_review_prepass`.

### R-PAP-31 (2026-11-05, build: Georgia Tech stage-9 sample) — replies to discussions and special-issue prefaces
The Georgia Tech lab-paper sample (4 errors of 25 uniform rows) found a 'Closure to "..."' (reply to a discussion of a paper in the Journal
of Structural Engineering) and two guest-editor prefaces typed article/editorial ('Special Topic on Monolithic 3-D Integration ...', IEEE Micro
'Special Issue on Top Picks ...'). Dropped (`not_a_paper`): a title that opens 'Closure to', 'Discussion of/on/to', "Authors' reply/response/closure", or
'Comment(s) on / Reply to / Response to' followed by a quotation mark (the quoted title of the work answered) is a `commentary`; a title that opens
'Special Issue/Topic/Section/Collection/Feature ...' or 'Top Picks from ...' is an `editorial`. `REPLY_COMMENTARY_TITLE`, `SPECIAL_ISSUE_TITLE`
(tests/test_not_paper_replies_and_special_issues.py). The rule applies to every school at its next rebuild (about 100 lab-paper rows of the eight
packages match; each release's count of dropped records moves by the same few).

### R-PAP-32 (2026-11-05, owner: UChicago stage-9 sample) — reviewed blocked clusters
A DBLP person page can mix in a namesake: Yuxin Chen's page `Yuxin Chen 0001` carries a security-HCI namesake whose works (6 of the PI's 66 lab
papers) have no OpenAlex author id, so no id can be blocked. The reviewed overrides (`census-overrides` `blocked_clusters`, with `why` and evidence)
name the namesake's group by coauthors: a work whose byline carries `min_coauthors` or more of them is never the PI's (`in_blocked_cluster`, checked in
`authorship_identity` before any identity). Applies to every school's overrides; a cluster needs a reviewed reason and the works it removes.
Tests: `tests/test_blocked_cluster_and_link_rules.py`.

### R-PAP-34 (2026-11-05, owner: round-r2 Michigan verdict) — placeholder PI names
A PI whose name is made only of single letters ('Y Z': the university directory lists a Nuclear Engineering professor by initials) names no one a matcher can tell
from a namesake and anchors no paper (`placeholder_name`). `pi_records` excludes such a census row (`excluded`, reason 'placeholder name') unless the reviewed overrides give a
`display_name` with its evidence; the PI is then built under that name (`censusName` keeps the census spelling, `displayNameBasis` the reason; researched, lab-page and decision files that key the person by the census name still reach the PI, `renamed_pis`). Michigan's 'Y Z' is Yang Zhang, from the
ORCID 0000-0002-7339-8342 and the OpenAlex author A5113215889 that carries it (the molten-salt paper the sample doubted is his). All nine schools were checked: 'Y Z' is the only placeholder
(names such as 'Weinan E', 'H.V. Jagadish', 'R. Ravi' have a word of two letters or more). Tests: `tests/test_namesake_guard_and_placeholder_pi.py`.

### R-PAP-36 (2026-11-05, owner: "yes", the DBLP page-1 extension of R8) — DBLP-listed works confirmed by page 1
A work on the PI's own DBLP person page (the dump or a reviewed pid) that the build lacks, in a year inside a dated appointment (a period, or a listing year), where OpenAlex has no record
or gives the PI no school, is added only when page 1 of the paper (arXiv v1 from the public GCS bulk copy, or an open PDF on a proceedings host: PMLR, NeurIPS, ACL, CVF, USENIX,
IJCAI, AAAI, OpenReview, JMLR, CEUR-WS, BMVA Archive; robots.txt honoured, 3 s per host, 10 s at USENIX (its Crawl-delay)) names the school for the PI (`tie`). `tools/dblp_recover.py` (`candidates`, `dump_ee`, `pdf_url`): the candidates
are now the cached lists plus the PI's full DBLP person page from the dump (the cached lists lacked MIT's Mossel NeurIPS 2022 and Freund COLT 2022), `ee` for a record only the dump has
comes from the dump XML, and the JMLR host was added (Shah JMLR 2025). IACR ePrint is not asked: eprint.iacr.org answers with a Cloudflare challenge and its robots.txt carries an AI policy against the PDFs, so Devadas's 2021 ePrint paper stays `dblp_unconfirmed`. A reviewed blocked cluster (R-PAP-32) also stops a recovered row. A record with no page-1 evidence is not added: it is kept in
`dblp-recover.sqlite` with status `dblp_unconfirmed` and a reason (`no_open_page1_source`, `page1_fetch_failed`, `page1_read_school_not_named`) for later. The rows carry
`school_via: ['page1_dblp: <DBLP key>', 'page 1 (<how>): ...']`, `authorship.page1` with the PDF url, its sha256, the quotes, the DBLP key and the fetch time, identity `dblp_person_page`,
source `dblp_recover:page1_arxiv|page1_open` and enter the normal flow (appointment, editions, dedup against the sweep's works, copies). `dblp_recover.py <school> --retry` asks again for the
unconfirmed. A page-1 read from an arXiv v1 posted 4 or more years before the DBLP record's year is not accepted at build time (`arxiv_predates_record`: Mossel's 2016 TOC paper, v1 2012, names Berkeley), and a byline lists each name once. Not used: the publisher's landing text (no open source parsed there). Tests: `tests/test_dblp_recover_page1.py`.

2026-11-18 (Harvard gate 9 pi1, lab coverage .870: Brooks, Guess & Sketch, ICLR 2024; owner 2026-11-05 'DBLP works added with page-1 proof'): OpenAlex's institution for the PI is derived and can be wrong
(it credited Brooks to Cornell, page 1 says Harvard), so a DOI record whose authorship at the PI's name lists only other institutions no longer closes the record: page 1 is still asked, and the paper is added only
when page 1 (arXiv v1 or an open proceedings PDF) ties the school to the PI by name; with no tie the record closes as `other_institution` (the PI was elsewhere), as before. Records an earlier run closed on the DOI
step alone are asked again by the next `dblp_recover.py <school>` run (`doi_authorship_verdict`). No other exclusion changed; the appointment, window and not-a-paper checks still apply at build time.

### R-PAP-38 (2026-11-06, owner) — book-chapter reprints of older papers
ACM Books and other anthologies reprint older papers as chapters (Essa's 'Video Textures', SIGGRAPH 2000, appears as a 2023 ACM Books chapter; 39 such chapters over the nine
schools, most of 'Seminal Graphics Papers', 'Making Databases Work', 'Providing Sound Foundations for Cryptography'). R-PAP-26 dated a preprint or repository deposit by the PI's DBLP
record of the same title; a record of type `book-chapter` now is dated the same way (`venue_version_date`): the original's year is the work's year, and one before 2016 leaves the lab
(`dated_before_window`). Only a chapter dated 4 or more years after that record (`REPRINT_YEARS`) is re-dated: a Springer Tracts chapter a year or two after its conference is no reprint. A chapter with no DBLP record of the same title, or new chapters of a handbook, are untouched. Tests: `tests/test_not_paper_non_research_records.py`.

### R-PAP-39 (2026-11-06, owner) — editorials whose byline is the guest editors (reviewed records)
Georgia Tech's FITEE special-issue editorial (Fumin Zhang, seven authors who are the guest editors) carries no stored signal: OpenAlex types it article, the sweep keeps no abstract or
references, DBLP has no page count, the DOI is opaque. So the rule is a reviewed entry in the PI's census overrides (`not_papers`: `doi` or `oa`, `why`, `evidence`), applied at the
lab-paper stage (`reviewed_not_paper`, tag `reviewed_not_paper`). A record is such an editorial when its byline is the special issue's editors, as the hand check read it. Tests:
`tests/test_not_paper_non_research_records.py`.

### R-PAP-35 (2026-11-05, owner: round-r2 Michigan namesake) — middle names against name-only identities
An identity that rests on the name through a DBLP person page (DOI or title) or a publication list does not stand when the byline writes middle names and the PI's own names write middle
names and they share no initial (`middle_conflict`, `NAME_ONLY_IDENTITY`; ORCID, author-id, verified-collection and advisee identities are not touched). The Michigan paper by M. E. J. Newman
(Physics) was credited to Mark W Newman (CSE) through a census DBLP id that is the physicist's page. A census DBLP id whose person names all contradict the PI's middle name is dropped like a name mismatch (R-PAP-05; Mark W Newman's census id was the physicist's page, so the anchored author id and every Newman paper followed it; his own page, pid/03/6629, is a reviewed override). The affiliation half of the owner's wording (department match) is not added: a middle-name
contradiction alone settled every case in the packages; the count per school is `namesake_middle_name_conflicts` in `report.json`.

### R-PAP-33 (2026-11-05, owner: round-r2 pooled failures; abstracts decision) — more non-research records
Dropped (`not_a_paper`, `non_research_record`; tests `tests/test_not_paper_non_research_records.py`, each on the real failing rows): a title that opens 'Session Introduction',
'Special-section Introduction' or 'Introduction to the Minitrack/Session' (`session_introduction`); 'Interview:' / 'An interview with' (`interview`); OpenAlex type `editorial` in
ACM eBooks; a title ending '(Conference Presentation)', '(Invited Talk)', '(Keynote Presentation)' (`presentation_only`, SPIE and LIPIcs invited-talk records); a Zenodo, Figshare or Dryad DOI
with no venue (`repository_record`: datasets, software, artifacts; OSF DOIs are preprints and stay); a record with no DOI and no venue whose title is a data file ('... in MATLAB data format',
'Processed data ...', 'Dataset for ...'; `dataset_record`); a repository DOI whose venue is explicitly Zenodo, Figshare or Dryad and whose title names a dataset deposit ('STARCOP dataset: ...', 'Dataset for ...'; `dataset_record`, Oxford November 7 sample). Repository-hosted manuscripts and journal dataset papers are not excluded by this title rule. A conference highlights, report, overview or summary ('Highlights from the ... Conference', 'Report on the ... Workshop', '... Workshop Summary';
`highlights_column`); a title that opens 'Research for Practice' (CACM columns; `column`); an edited-volume record: a book-level ISBN DOI with no chapter suffix on a conference-paper, article or
editorial record (LNCS volumes whose byline is the editors; type `book` stays, R-PAP-15; `edited_volume`); a workshop or session description ('EE2: Workshop on ...' at ISSCC, 'VDS @ KDD 2022',
'KDD-2023 Workshop on ...'; `workshop_proposal`; 'KIT@IWSLT2022' stays); a proceedings-volume title ('Conference on Health, Inference, and Learning (CHIL) 2022': 'Conference|Symposium|Workshop on ...' ending in a year; `proceedings_volume`). **Conference abstracts are not papers (owner, 2026-11-05):** besides R-PAP-19's meeting abstracts and the '(Conference Presentation)' records,
an explicit title suffix '(Abstract Reprint)' is dropped even if its page count is missing or its type is misclassified; a `conference-abstract` record of 2 pages or less in DBLP is dropped whatever its byline (`conference_abstract`); one without a page count, or of 3+ pages (ACM EC, PES General Meeting papers OpenAlex types as abstracts), stays.
**Extension 2026-11-09 (owner delegated the choice to Claude on 2026-11-09; Oxford admission review, T111): Zenodo project deliverables and reports.** A record with a
Zenodo, Figshare or Dryad DOI (venue Zenodo or any other) is dropped as `repository_deliverable` when its OpenAlex type is `report`, or its title carries a project
deliverable code (`D2.5`, `D4.5`, `SMASH-HCM D1.4`, 'Deliverable 5.8', `M5:`), a report title ('Final / Interim / Annual / Progress / Workshop / Case Report',
'Report on ...', a plenary report), a consultation or RFI response ('Response of ... to the ...', 'Response to the ... consultation'), a focus-group record or a
'Preliminary Release'. Zenodo records that are real publications (an article or conference paper, a FAIRsharing paper, a book chapter) stay: the rule never judges a record
by its Zenodo host alone. The remainder (webinars, work plans, survey results, code-for-paper deposits) is held in the Oxford review, not dropped by rule. On the Oxford
round-2 package: 36 of the 81 Zenodo, Figshare and Dryad DOI rows (79 Zenodo) drop, 20 of them among the 44 net-new Zenodo (mostly Sansone). Tests: `tests/test_oxford_rules_1109.py`.

### R-PAP-41 (2026-11-09, Claude on the owner's delegation; Oxford admission review) — source-title guard
A record's title must match the title its source gives for its DOI: arXiv (the id in `10.48550/arxiv.<id>`, any version title) or Crossref. The comparison is normalised
(HTML entities and markup, accents, case, punctuation, '&' = 'and') and tolerant: a subtitle (one title is the other's prefix of 2+ words), a small wording change
('Iterate' / 'Iterative'; character ratio >= 0.78 or stemmed-token Jaccard >= 0.6) all match. A record that matches none of the source titles is HELD (verdict `hold`; a person
reads the pair), never silently dropped or admitted; a DOI with no source title is not judged. Known corrupted: Roberts 'HumBugDB' under arXiv 1705.05180, Gal 'ME-JEPA'
under 2305.17493 (also in the live 7031 candidate). A genuine retitling between arXiv versions is held too and cleared by the reviewer (on the Oxford round-2 package: 10
holds, 2 corrupted and 8 retitles; Crossref's 4 markup-only differences pass). `tools/source_title_guard.py PAPERS SOURCES --out holds.json`; the library functions are
`titles_match`, `title_conflict`, `held_rows`. It is an admission-review gate, not yet a build step: the build has no local arXiv/Crossref title store (the 1,289 arXiv and
640 Crossref titles of the Oxford review were fetched into scratch), so a school's package is checked by running the tool on its `lab_papers.jsonl.gz`.

### R-PAP-43 (2026-11-09, Claude on the owner's delegation; HKUST admission review) — artifact deposits, editor messages, bare front matter
Dropped (`non_research_record`; tests `tests/test_hkust_rules_1109.py`, each on the real HKUST row): a Zenodo, Figshare or Dryad DOI whose title is 'Artifact for ...' / 'OSDI21 Artifact for ...'
(`artifact_deposit`; a software artifact accompanying a paper, not the paper); an `editorial` whose title opens '(A) Message from the ...' (`editor_message`: 'A Message From the Editor-in-Chief', 'Message
from the ... Co-Track Co-Chairs'); a book-chapter, editorial or other record whose whole title is Epilogue, Prologue, Foreword or Afterword (`front_matter`). Narrow on purpose: a longer title
('Epilogue: Lessons ...'), a title only containing 'message' ('A Message-Passing Approach ...') and Zenodo preprints stay. HKUST round 2 had 4 such rows, excluded from its admissible count.

**Extension 2026-11-10 (HKUST admission review): `interview` also drops a title that ends ': an interview with <Name>'** ('Decoding brain dynamics: an interview with Jose Principe on brain-computer interfaces'); tests `tests/test_hkust_rules_1109.py`.

### R-PAP-46 (2026-11-13, VT Stage 9) — conference event recaps
An `article` whose entire title is an ACM, IEEE, USENIX, AAAI or SIAM named conference, symposium or workshop followed by its year is a conference event recap, not a research paper (`conference_report`). Aisling Kelliher's *ACM Creativity and Cognition Conference 2017* is labeled “Scientific Conferences Report” by her VT publication page and describes the meeting program. A title with a research subtitle remains eligible. A `conference-paper` opening with an acronym and “workshop on” is a workshop announcement (`workshop_proposal`) when it has at most two pages or the page count is unavailable: the KDD 2024 GenAI evaluation workshop notice occupies pages 6729–6730, but its OpenAlex record omits the page count. A longer paper remains eligible. Test: `tests/test_not_paper_non_research_records.py`.

### R-PAP-37 (2026-11-05, owner task: Michigan student-paper gaps) — listing continuity
Four Michigan `student_not_linked` findings of accuracy round r2 (Chen, Aksoy, Sattar, Wandke) were checked paper by paper. Two (Chen, Aksoy, both
Gorodetsky's students) are real lab-paper gaps: Gorodetsky's only dated appointment evidence is the AERO unit listing of 2018-2020 (the later AERO
captures are filter or hub pages that name no one), so his 2021-2026 papers, 6-15 a year, every one crediting Michigan Aerospace Engineering in his
own byline, were `outside_appointment`. A listing proves its own calendar year only, so nothing could extend it. The R-PAP-28 argument (no departure
evidence, the PI's own works name the school in every year) now also builds continuity periods from listings alone (`periods.listing_bridge_periods`,
`LISTING_BRIDGE`, `papers.continuity_bridges`): (a) interior, from listing year A's capture date to the next listing year B's, when every year
between qualifies; (b) tail, from the last listing's capture date through the longest run of qualifying years after it (open when the run reaches
today). A year qualifies when the PI's identified works name the school in their own authorship at least once and credit no other institution more
often. Never a head: the years before the first listing are the arrival side (R-PAP-13). Only for a PI with no period at all (R-PAP-28's), no
departure evidence (`listingsAfterMove`, an end_moved period), and no non-primary listing row (adjunct, courtesy, visiting, emeritus, on leave,
part-time). A listing drop closes the period (R-PAP-03, 2026-11-02): a department whose listing was captured and read in a gap year
(`listings/<school>/coverage.json`, per-department format; emeritus slots do not count) and omits the PI stops the run there, and a PI listed in a
department with no coverage data is bridged nowhere (the per-person coverage files of Berkeley, CMU, EPFL, MIT and Stanford say nothing about
department years). The period admits only a paper whose own byline names the school (`direct_via`: not an advisee, unit-name, first-page or
cross-affiliation route) and a first-page-proved DBLP or lab-page addition. Evidence is the listing capture; `reviewed: R-PAP-37 listing continuity`.
A PI needs listings in two or more calendar years (2026-11-06: a single capture shows no span; Mossel's 2017 Berkeley and Browning's 2017-2018 CMU
papers followed a lone 2016 listing, after both had left). Switched on per school by the charter (`[rules] listing_continuity`, TEMPLATE default false):
Michigan (2026-11-05), and Georgia Tech, UChicago, MIT and CMU (owner 2026-11-06, each after a 30-paper hand check: at most 1 error). Berkeley stays off: with
the two-year guard the rule adds nothing there. Per-person coverage schools (Berkeley, CMU, MIT, Stanford, EPFL) bridge only PIs whose listings are not
per-department dept_listing rows (unit listings, census sources); a PI listed in a department with no per-department coverage is never bridged.
Known miss: a PI who moved while naming both institutions (Paulino, Georgia Tech to Princeton 2020: one 2022 paper). Counters `listing_bridge_periods`.
The other two cases are correct non-links, not gaps. Sattar's co-authored papers (2019-2022, arXiv, TSP, ACC, CDC) name the University of California,
Riverside for both authors: Oymak joined Michigan in fall 2023 (his first listing reads 'starting Fall 23'); the one 2021 arXiv record that
carries 'U Michigan' tokens is a co-author's shifted affiliation string. Wandke's papers are UIUC work: the PI row 'Y Z' (Yang Zhang; R-PAP-34 on agent/accuracy-fixes-1105 resolves the placeholder name) is first listed at Michigan in
2024; his 2023 RoboSoft and IEEE Access bylines name Michigan NERS beside UIUC (a prospective affiliation: the NERS people page of October 2023 does
not yet list the PI), and the 2024-2025 bylines name UIUC only. Wayback captures 20230615164134, 20230922051505, 20231003085706 of
ners.engin.umich.edu/people/. Brian Chen's Morressier record (2021, type other, no byline affiliation) is an abstract, not a paper.
Tests: `tests/test_listing_continuity.py`.

## Students

Roster/co-author follow-up (owner, 2026-11-06): retain every independently qualifying PI–student pair. Do not rank competing PIs by their last-author or paper count and discard the weaker pair. Existing roster-year, student-role, co-authorship and single-paper namesake guards still apply; co-authorship alone does not establish advising. `tests/test_roster_namesake_guard.py` checks unequal co-adviser counts and ambiguous single-paper cases.

### R-STU-01 (2026-10-21, owner)
Students are people whose advising context names the PI (by person id, or by name through the PI's full-name forms), the
direct members of a reused lab unit, researched advisees with a quote and hash (gap, few-students, thesis, lab-page
evidence), and advisees named in the PI's own reviewed basis quote.

### R-STU-02 (2026-10-28, owner) — program advising and readers
A student whose only tie to the lab is a "Doctoral (Program)" or "Reader" listing, or whose every source names another
adviser, stays only when they co-authored one of the lab's papers (`droppedProgramOrReaderOnly` in the report).

### R-STU-03 (2026-10-28, build) — adviser names
An adviser field names a PI by full given name only through the PI's full-name forms; an initials-only field goes to no
PI when another PI of the school shares that family name and initial.

### R-STU-04 (2026-10-28) — reviewed corrections
`hierarchy/student-identity-review.json` merges two records of one lab that are one person; `student-corrections.json`
drops, renames or replaces the evidence of a record.

### R-STU-05 (2026-10-29, owner: accuracy sample) — doubled roster tokens (R7)
A student name or alias with a token repeated in a row ('Arjun Nitin Nitin Bhagoji') loses the repeat; the raw name stays
an alias. `dedupe_tokens`.

### R-STU-06 (2026-10-29, owner: accuracy sample) — hyphenated family names within a lab
Within one lab, a record whose family name is one half of another record's hyphenated family name, with the same first
given name (or a nickname pair), is the same student ('Pablo José Ortiz-Lampier' / 'Pablo Ortiz', Harrell's lab).
`hyphen_half`.

### R-STU-07 (2026-10-29, owner: accuracy sample) — a PI's person id is never a student record
A student record keyed by any PI's person id is re-keyed to the lab's own `ext:<school>:<name>` id (Berkeley's faculty
John Wright's id had become the record of Nikolić's PhD student John Wright, lending him the faculty member's person
links). `rekey_pi_person_ids`, `student_records_rekeyed_from_pi_person_id`.

### R-STU-08 (2026-10-29, owner) — re-captured relation evidence
The site collections gave some advising contexts as bare URLs (CMU), hashes without quotes whose capture bodies were lost
(EPFL), or an unhashed DSpace snapshot (MIT). `tools/relation_recapture.py` re-captured the cited pages (a stored copy, a
Wayback `id_` copy near the original observation, or the live page; one request per second per host, robots.txt
respected), and `hierarchy/<school>/relation-evidence.json` gives per (cited url, person) the capture url, the sha256 of
the captured bytes and a verbatim quote naming the student, with `names_pi` when it also names the PI or the PI's lab
(the bodies are in `hierarchy/<school>/relation-captures.sqlite`). A source without url, sha256 and quote takes the
record for its PI, else a student-only record (`names_pi: false`). The source keeps its earlier hash as
`original_sha256`. `apply_relation_evidence`.
Clarified 2026-10-31 (build): the choice is made per lab. An advising context that names several PIs gives each of their
labs the same cited source; each lab takes its own record (the one for its PI, else the student-only one) on its own copy
of the source. Before, the first lab processed wrote its record into the shared source and the others kept it, so a lab
could carry another PI's quote with `names_pi: true`, and which lab came first depended on Python's string hashing (CMU:
Austin Matthews in Lavie's, Neubig's and Dyer's labs). The build's output no longer depends on `PYTHONHASHSEED`.

### R-STU-09 (2026-10-29, owner: link-gap sample) — program-wide academic advisers
A department directory line 'Program: <program> ... Academic Advisor: <name>' whose (program, adviser) pair covers 10+
students and 25%+ of that program's students in the school is the program's academic adviser, not a research adviser
(CMU: MCDS -> Eric Nyberg, 325 of 360; MIIS -> Teruko Mitamura; MSBIC -> Ravi Starzl). Such a relation is weak (as
R-STU-02): the pair stays only when the student co-authored a lab paper. `program_adviser_groups`,
`relation_is_program_advising`.

### R-STU-10 (2026-10-29, owner: link-gap sample) — the student's own roster entry
A quote with two or more 'Advisor(s):' labels is a page of many entries, where the next student's name trails each
adviser value. Only the student's own entry counts: the first adviser label after the student's name (within 250
characters), cut at Publications/Office/Website/Email/Phone or 80 characters, must name the PI by a full-name form. A
relation whose every quote is such a page naming someone else is weak (CMU's SE-PhD page: Moreno's adviser is David
Garlan, not Aldrich or Kästner). `own_roster_entry`.

### R-STU-11 (2026-10-29, owner: link-gap sample) — a basis record's own advisor field
Advisees named in a PI's reviewed basis quote from a DSpace record count only when that record's
`dc.contributor.advisor` names the PI ('Freund, Robert M.' on Renbo Zhao's record in Van Parys's basis).
`dspace_advisors`.

### R-STU-12 (2026-10-31, coordinator: validation findings) — no evidence without a hash
A relation source without a sha256 is no evidence: after the re-captured evidence (R-STU-08) is applied, it leaves the
relation; a relation left with no source, and a student left with no relation, leave the lab (`droppedWithoutHashedSource`
in the report). CMU's site collection cited 2,260 bare URLs that the re-capture could not quote (368 relations, 12
students); MIT 9 (9 relations, 2 students). Record years are integers in 1950 .. next year: a string is read for its
4-digit years, others are dropped (`as_years`); reviewed period dates written as Wayback timestamps are read as ISO
dates (`iso_date`). `drop_hashless_sources`.

### R-STU-13 (2026-11-03, owner) — one student under two names in a lab
Within one lab (never across labs, R-HIER-03), initial-only tokens ('E.D.', 'V.', 'J') are optional wherever they appear,
trailing ones too: 'Alejandro Cuevas' (publishing name) and 'Alejandro E.D. Cuevas V.' (thesis name, the trailing 'V.' a
second-surname initial) are one record. A second surname on one side only ('Maria Gonzalez' / 'Maria Gonzalez Escamilla')
matches the single-surname form, except when both surnames are East Asian family names. The words left must be two or
more with the same first given name; initials on both sides must not conflict; a bare initial plus surname ('J. Smith')
never matches. `initials_optional` (counted as `student_records_merged_initials_optional`, listed in the report's
`studentInitialsMerges`). A same-lab pair with the same given name and family names one edit apart (4+ letters, not both East Asian
family names: 'Alexander Swerdlow' / 'Alexander Swerlow') is never merged by the build: it is queued in the report's
`studentSurnameTypoCandidates` (`surname_typo`, review-file shape, empty `verdict`, with the signals found: shared source
URL, one name the other's alias, a shared linked paper) and `tools/student_name_candidates.py` writes the queue to
`hierarchy/reviewed/student-name-candidates.json`. Only a `same_person` verdict in `student-identity-review.json` merges them.
2026-11-03: of the 30 queued pairs, 13 stay `same_person` (one source showing both spellings, the same thesis title, a DBLP alias record, or the same slot in two captures of one page) and 17 went back to the queue after the owner's strict re-check (same adviser, role and years is not enough); none was found to be two people.

Implementation note (2026-11-16, SJTU recall): exact Han names match the same literal Han spelling inside a bilingual name. Different explicit Han names cannot match through a Latin prefix or a Latin-only alias: `Yun Zhang 张赟` (postdoc) and `Yunhao Zhang 张昀浩` (PhD) are different people. The recall check keeps its existing thresholds, source requirements and Latin-only rules; it infers no transliteration or new identity. Tests: `test_recall_literal_han_names_precede_latin_variants`, `test_recall_latin_alias_cannot_bypass_conflicting_han_name`.

### R-STU-17 (2026-11-04, owner) — the `visiting` student role
A visiting PhD, master's or undergraduate student, a "visiting student researcher", or an exchange or visiting intern who is a student elsewhere, listed on
a lab's own page (or in researched evidence), is a member of THAT lab in the capture year, role `visiting`; they are no longer dropped as "a student of
another institution" (UChicago: Diantong Li and Linus Gan, CUHK, were `not`). Visiting professors, faculty, scientists and scholars stay `not_a_student`; a
bare "Visitors" heading with no student wording is not decided (role `other`, the doubtful path), and so is a heading that names students among others
('Undergraduate and Visiting Students', 'Visiting Students, Scholars and Scientists': the entries decide). `visiting` is a non-PhD role like `masters` and
`undergraduate`: the build gives it `researched_membership`, never `researched_advising`, so it makes no adviser relation for PhD statistics; the release
export lists it as relation `member`, role label 'Visiting student'; the chain audit excuses it from the thesis-link check (it already named `visiting`);
lab coverage counts it as a student like any other role (a lab with only visiting students has students). Undated visiting entries take the same
capture-year dating as other undated members (R-STU-14).
Extraction: `tools/visiting.py` (`VISITING_RX`, `visiting_role`): the entry's own text first ('visiting student from CUHK', '(visiting, CUHK)', 'Visiting
Ph.D. from Tsinghua'; not an earlier stay or the entry's own 'PhD student' statement), else the nearest role heading; the entry's own postdoc, staff, scientist or
visitor title outranks a visiting heading. `labpage_audit.entry_role`, `clean_parenthetical_name`, and `labpage_students_school.extract` (a visiting-students heading is not a `visitors` skip heading; the role filter keeps `visiting`); ELSEWHERE_RX no longer reads 'visiting student at X' as a
student of X, and the other-institution checks are skipped for a `visiting` row.
Past decisions: `student-decisions.json` takes `decision: visiting` (passed on like `uchicago`, role forced to `visiting`); `tools/visiting_roles.py` converted
every researched row whose evidence SHOWS a visiting student, in its quote or in the stored capture it cites (the phrase directly after the name; or, when the row's
own section is a pure visiting heading, that heading before the name with no other role heading or title between): 180 rows (Princeton 13, MIT 45, CMU 80,
EPFL 19, Berkeley 6, Stanford 4, Michigan 9, Georgia Tech 4), keeping the quote, url and the role it had (`role_was`, `converted_from`; `role_quote` is the capture span when the
quote itself does not show it). A hint that nothing shows (a reviewer's note, a section whose heading the capture does not place before the name) converts
nothing: 52 such rows keep their earlier role; UChicago's two `not` rows were changed by hand and keep `original_decision` / `original_why`.
`visiting_decided` in `pihier.students.researched`, `role_label` in `tools/export_release.py`.

### R-STU-18 (2026-11-04, owner: "yes") — evidence-confirmed roster pairs
The UChicago Statistics and CAM people-page rosters stay unwired as a source (no name-and-paper-count rule, old or R*). Only the pairs whose hand
verdict in `reviewed/roster-pair-verdicts.json` is `true` (the student listed or stated as this PI's, or co-advised with this PI, on a stored page) become
student relations: `tools/roster_pair_evidence.py` cuts a verbatim quote and the sha256 from the stored capture and writes `reviewed/roster-evidence.json`,
a researched-evidence file (`RESEARCHED_FILES`, so R-STU-01/R-STU-12 apply: no quote or hash, no relation). Role `phd`, years the pair's roster years.
`unsettled` and `not` pairs are never written. A co-advised student appears under each PI whose own pair is `true`.

### R-STU-19 (2026-11-05, owner: UChicago and Georgia Tech stage-9 samples) — two guards on the byline routes
**A. Hyper-authored papers.** An initials-only byline match ('Y. Zhou', 'Zhou, Y. H.': no given name spelled out) cannot link a student to a paper with
50 or more authors (`HYPER_AUTHORS`, `initials_only`, `hyper_authored`), on every byline route (the collection's person link is unaffected). The threshold is from
the data: among the 2,606 byline links of the nine packages that match on a name the paper does not spell in full, 540 are on papers with 10+ authors, 147 with 20+,
74 with 30+, 37 with 50+ and 11 with 100+, while a lab paper's median byline is 5. UChicago's case: four initial-only 'Zhou' authors of a 2,938-author ATLAS paper
linked to one CS student.
**B. The wide-window routes.** (Owner 2026-11-06: a visiting STUDENT counts, role `visiting` of R-STU-17, unless the entry says visiting scholar, professor, faculty or researcher; a `visitor` row only when the entry says visiting student or PhD; a `member` row counts when the entry's own words after the name, else its heading, say student: `pihier/role_cues.py`, the cues of R-STU-20. Effect on the 592 removed links of the 2026-11-05 scratch build: 17 come back, because the rest are postdocs, visitors and `other` staff by an explicit role.) A `full_name_on_lab_paper_byline` or `within_lab_byline_match` link (the routes outside the narrow window; the three Georgia Tech errors were within-lab matches on the full name) needs the person to hold a student role (`student_role_ok`: phd, doctoral, masters,
undergraduate, student, alumnus or intern, not only research scientist, visitor, postdoc, staff or other) and no relation whose quotes name other advisers only
(`pi_is_adviser`, R-STU-03's test). Georgia Tech's draw: a research scientist (Anderson, Batra), a visiting researcher (Elola, Clifford) and a student of two other
advisers (Basciftci, Van Hentenryck) had entered by full name. Tests: `tests/test_blocked_cluster_and_link_rules.py`.

## Student–paper links

### R-STU-14 (2026-11-03, owner) — capture-year dating of undated lab-page members
An undated member listed under a PhD-student heading of a lab page counts as that lab's student in the year of the Wayback (or live)
capture that shows them, never earlier or later; the same person on captures of several years gets the span of those capture years
(`years_basis: capture_date`). Applies to the lab-page audit's `undated_cannot_place` entries, through
`tools/labpage_students_school.py undated <school>` (`undated_capture_rows`, `member_list_quote_ok`; -> `reviewed/undated-capture-evidence.json`,
a researched-evidence file). Not kept: a member under an alumni / past / former heading (the capture year is not a membership year), any role but
`phd` or `visiting` (R-STU-17; the row keeps its role), a quote that is not a heading followed by a plain list of names (publication, title, collaborator or e-mail cues, more than two lowercase
words), a PI with a one-letter family name (placeholder row), a page that does not name the PI in its first 400 characters (a centre page listing
the PI among several leads). Tests: `tests/test_students_capture_surname.py`.

### R-STU-15 (2026-11-03, owner) — surname-only advisers
A student list that names the adviser by surname only ('PhD Research Advisor: Brei, Luntz', ME graduate list) resolves each surname against the
school's dated faculty listing for that department and the capture's year (`unit_listing:<dept>` in `pis.json`): exactly one faculty member with
that family name (accents and case folded) resolves it; zero or several skip it, a department without a listing for the year skips it, and a surname
is never resolved across departments. The student counts in the capture years; the quote is the student's own entry through the surnames. Charter
`[students].surname_adviser_lists = [{url, department}]`; `tools/labpage_students_school.py surname <school>` (`surname_entries`,
`resolve_surname`; -> `reviewed/surname-adviser-evidence.json`). This is an exception to R-STU-03 (full-name adviser fields) that the owner approved
for surnames the listing resolves uniquely. Tests: `tests/test_students_capture_surname.py`.

### R-STU-16 (2026-11-03, owner) — Mathematics Genealogy Project
The MGP (mathgenealogy.org, genealogy.math.ndsu.nodak.edu) is a source only when its robots.txt and terms allow and the site answers: robots.txt first
(including any group naming ClaudeBot or anthropic-ai), polite pacing, one query per PI by MGP id or name, students with a degree from this school,
year >= 2016 and the PI as advisor; the PI is matched by name plus school plus field, never by name alone. On 2026-11-03 the site served only its
outage notice (PHP disabled since 21 October 2026), robots.txt answered 404 (no rules) and no terms page was reachable, so no query was made.

### R-STU-21 (2026-11-05, owner: "we really need more UChicago students") — lab-page extraction fixes (`tools/labpage_students_school.py extract`)
1. **`previous_school_students` never reads the school's own package.** Once a school is released it is in `S.released()`; a rerun of `extract` after a build then matched every PI with themself and dropped every student the build already held as a "previous school" student (56 accepted lab-page rows vanished). Test `tests/test_previous_school_students_self.py`.
2. **Plain student headings.** A lab page whose members sit under 'Students', 'Current Students', 'Advisees', 'Advising', 'Graduate Members' or 'Undergraduate Members' gives role `student` (a lab member; no degree level stated), not a dropped row. Any heading with a degree or a non-student word keeps lpdom's reading (`generic_student_role`).
3. **Mixed headings** ('PhD students & postdocs', 'Alumni (PhDs and Postdocs)'): the entry's own words decide, the first of PhD or postdoc in its first 60 characters ('Ph.D. 2025, Post Doc @ UIUC' is a PhD); an entry that states neither is a `member`, never a dropped postdoc (`mixed_heading_role`). Postdoc rows are not students and are not written (`dropped_postdoc`).
4. **Alumnus before arrival.** An alumnus whose stated end year is at or before the PI's first listed year here, and whose entry does not name Chicago, was the PI's student elsewhere (Zhang's ETH PhDs 2022-2023, Tomlin's Berkeley advisees, Zhao's UCSB PhDs 2016-2017) and is dropped (`dropped_alumnus_before_arrival`).
5. **A reviewed extra lab page is not skipped for its length** (the 60-candidate department-roster guard still applies to every other page).
`tools/etd_crawl.py role_of`: a repository record typed only `doctoralThesis` (UChicago types master's theses so) has role `student`; only 'Dissertation' or a PhD word gives `phd`.

### R-STU-20 (2026-11-05, owner: Boris Hanin deep dive) — lab-page students corroborated by the PI's byline
A school whose lab-page student additions are not accepted (`labpage-acceptance.json` students `accepted: false`: Princeton, CMU, Stanford, Michigan, after the
extended hand rounds failed) wired none of them, so a PI's own PhD students were off the lab although they stand on the PI's byline (Hanin: 6 current PhD
students on his page, none in the build; Tianze Jiang is on three of his lab papers). The roster alone and co-authorship alone stay no evidence (Stanford rule);
the two together are (R-STU-02 and the UChicago roster rule of 2026-11-04 already pair them). A not-accepted additions row (`labpage-additions.json`) is wired,
and only that row, when all of these hold (`tools/pihier/corroborated.py`, `students.add_corroborated`, run after the lab papers and before the links):
1. it names a student: the row's role is phd, masters, undergraduate or visiting, or the role is empty and the stored capture (its sha256) shows a student cue as the
   NEAREST role cue before the name (`cue_role`: 'supervise several excellent PhD students: A, B, C' is a prose list the audit's heading reader never sees;
   a postdoc, staff, scientist, collaborator, alumni, former, placement or publication cue nearer to the name rejects it: Hanin's postdocs Gage DeZoort and
   Paolo Baglioni, who are on his byline, stay out); a role postdoc/other/staff/member is never read as a student;
2. an alumni row needs stated years (a capture year is not a membership year, R-STU-14); other rows are dated by the capture year (R-STU-14);
3. the student's full first given name (or a nickname pair) and family name, no initials, are on the byline of a lab paper of that PI, the strict given-name
   guard passes, the paper has at most 15 authors (`MAX_AUTHORS`; the 50-author rule for initial-only bylines is R-STU-19 A on agent/accuracy-fixes-1105, a separate guard), and its
   year is within three years of the row's years;
4. the lab holds no student of that name already (R-STU-13 merges stay the only way to join records).
The row builds a record like an accepted one (relation `researched_advising`, `auto`, `corroborated`) and the usual link bases link it. Not wired, counted:
`labpage_students_corroborated_skipped:role|no_student_cue|no_byline|alumni_without_years|in_lab`; wired: `labpage_students_corroborated_wired`; the report lists them
(`labpageStudentsCorroborated`, with up to six corroborating works). Effect, 2026-11-05 scratch rebuild: 358 rows wired (Princeton 26, CMU 53, Stanford 70, Michigan 209), 1,443 links (Hanin 1 -> 6: Jiang x3, Shigida, Bhandarkar, Jelassi); skipped: role 282, no byline 506, no student cue 154, alumni without years, already in the lab 22. Hand check of the final build, 30 random added links (20 R-STU-20, 7 R-LNK-06, all 3 R-LNK-07): 30 correct; a first version without the alumni-section rule wired 13 alumni (Posada, Will Held, Esterwood) whose capture year is not a membership year, and two of 15 sampled links were such rows.
Interaction with agent/accuracy-fixes-1105's R-STU-19 B (the wide-window routes need a student role and the PI as adviser): the wired rows carry a student role and a quote
from the PI's own page. Tests: `tests/test_student_links_hanin.py`.

### R-STU-22 (2026-11-06, owner approved) — a student's own page or ORCID education record
A co-author of a PI who has no lab record of being the PI's student can state it on their own page. **Own-page form** (the evidence standard of the UChicago deep dive: "the student's own page
or CV names the student as this PI's advisee"; `tools/own_page_students.py`, tests `tests/test_own_page_students.py`):
1. **Candidates:** the school-affiliated authors (`byline_school`) of the lab papers of a PI with fewer than three students, 2016-2025, papers of at most 15 authors, at least two co-authored papers, not in the census.
2. **Homepage:** from DBLP's own dump (the person record whose name string is on a pub record with one of the candidate's lab-paper titles, exactly one such person; its `url` entries), from a link whose text is
   the candidate's full name on a lab page we already hold (`hop`), and from Semantic Scholar's paper batch (the author profile's homepage; the project key, never printed). Hosts of aggregators, profiles and the barred sites
   (Deep Blue, news.umich.edu, record.umich.edu, Math Genealogy, academictree.org, Google Scholar, LinkedIn, ...) are skipped.
3. **Read live** only where robots.txt allows: every Disallow of the `*` group, any group naming ClaudeBot / anthropic-ai / claude-web that disallows anything (the host is then skipped whole), Crawl-delay (at least 3 s a host, a host belongs to one
   job); generic User-Agent, no e-mail address; HTML only, at most four pages of one person (the homepage and a CV / about / people link of the same host). A host that answers 403/429/503 is queued for the Wayback lane, not fetched here.
4. **Kept** only a sentence of that page that names the PI right after an adviser cue ('advised by', 'advisor:', 'co-advised by', 'supervised by', 'under the supervision of') with nothing but names and titles in between (a
   'worked closely with' collaborator is not an adviser), where the institution nearest before the cue (this sentence, else the sentence or lines before) is the school, a student cue (PhD, doctoral, graduate student, MS, undergraduate) is in scope
   and no postdoc, research scientist, visiting-faculty, intern or collaborator cue is within the cue's clause. The page must name the candidate in full (namesake guard, R-STU-19/20; the given name is spelled out). The role is the role cue nearest to the adviser cue.
   Years: a range written next to the school ('2017-2022', 'present' = the capture year), a degree year next to the school mention, or, for a person described in the present tense on a page whose newest year is within three years of the capture
   (R-LAB-02), the capture year (R-STU-14). A past-tense statement with no year on the page (owner approved 2026-11-06): the years are the span, first to last, of the student's co-authored lab papers with that PI within 2016-2025, `years_basis: coauthored_lab_papers`; no co-authored lab paper in the window, no row (a span can run past the degree year: papers continue after graduation). The sentence also may not call the PI a committee member, reader or collaborator, and in a sentence the PhD cue outranks MS/BS ('Ph.D. and M.S. at X').
5. Row: `reviewed/few-students-evidence.json`, `rule: R-STU-22`, `source: own_page`, verbatim `quote`, `url`, `captured` (UTC), `sha256` of the extracted page text (and `raw_sha256` of the bytes). Role phd/masters/undergraduate/visiting (R-STU-17).
**ORCID form (proposed, not run):** an ORCID education record of a PhD (or MS/BS) at the school in the window, held by a co-author of the PI, would count only with the PI on the byline of at least one co-authored lab paper in those years
(R-STU-02's logic; ORCID names no advisor). It was not executed: `pub.orcid.org/robots.txt` answers `User-agent: * / Disallow: /` (read 2026-11-06), so the public API is barred to automated clients under the standing robots rule. The sanctioned bulk channel is ORCID's annual public data file (CC0);
whether to fetch it (tens of GB) is an owner decision (not asked for; no ORCID row exists).
**Effect in Michigan (2026-11-06 scratch build, overlay root, main untouched):** labs with students 146 -> 149 of 287 (CSE 88 -> 90, UMSI 8 -> 9); 7 new students and 36 student-paper links of those students (8 new lab-student pairs); of 5,299 co-author candidates 824 had a homepage URL (DBLP 768 incl. lab-page links, Semantic Scholar 43), 605 pages read, 79 robots-barred, 150 queued for Wayback (403); 37 advisee statements, 11 dated (written), 18 past-tense statements without a year listed apart. Hand check of all 11 written rows: 10 correct, 1 doubtful (Yonathan Fisseha: 'advised by Prof. Austin', a bare family name unique among the census faculty and co-authored with Todd Austin).

**Effect in Georgia Tech (2026-11-06 scratch build, overlay root, main untouched):** labs with students 223 -> 233 of 447 (CS 40 -> 45, CSP 4 -> 6, IC 31 -> 32, CSE 18 -> 19, ECE 54 -> 55); 26 new students (1,087 -> 1,113), 31 new lab-student pairs and 190 student-paper links of the new students; of 11,474 co-author candidates 1,189 had a homepage URL (DBLP, stored lab-page links 403 names, Semantic Scholar 81), 938 pages read, 95 robots-barred, 43 queued for Wayback (403/503); 122 advisee statements, 42 dated (written, 29 PIs), 45 past-tense statements without a year listed apart. Hand check (fixed seed 20261106: 30 of the 42, plus all 43 first-pass quotes read): 30 of 30 correct on membership, role and years; the first pass found 2 wrong years (a job start 'since May 2024' and a master's year read as the PhD year; Bing He, Wantong Li), fixed by the same-sentence year rule before counting.

**Effect in UChicago (2026-11-06 scratch build, overlay root, main untouched):** labs with students 89 -> 90 of 134 (CS 53 -> 54); 1 student (Todd Nief, Holtzman's PhD student since 2024) and 3 student-paper links; of 643 co-author candidates 114 had a homepage URL (DBLP, lab-page links, Semantic Scholar), 74 pages read, 23 robots-barred, 5 queued for Wayback; 4 advisee statements, 2 dated (one already in the lab: Xuchen Gong under Tian Li), 2 past-tense statements without a year listed apart. Hand check of all 2 dated rows: 2 of 2 correct (membership, role, years).

### R-STU-23 (2026-11-08, owner: "yes"; extended 2026-11-09, owner: "Make the rule as it makes sense"; extended to Cornell eCommons 2026-11-25, owner D-0072) — a WashU or Cornell thesis or dissertation's Committee Chair is the student's adviser
On a Washington University Open Scholarship thesis or dissertation record (any ETD collection of `repository.library.washu.edu`: eng_etds, art_sci_etds, brown_etds, olin_etds, chemeng_etds,
sph_etds; doctoral or master's, 2016 or later), the "Committee Chair" names the student's adviser, when the chair matches a WashU PI under R-STU-03. Co-chairs each count, under the co-adviser rule.
The role is the degree's (phd or masters; undergraduate and honours work never counts), and the years are the degree year (R-STU-14). Rows:
`hierarchy/washu/reviewed/thesis-committee-chair-evidence.json` (a RESEARCHED_FILES file), built by `tools/fulltext_advisers_build.py washu` from `tools/washu_etd.py parse`. A collection is wired in only
if its hand check passes (27 of 30, or all rows if fewer than 30, seed stated); otherwise its rows stay in `thesis-committee-chair-held.json` with the reason. Engineering: 30 of 30 correct on chair and PI (seed 20261107), 164 rows, 31 PIs.
Hand checks of the extension (2026-11-09): see the WashU deep-dive report in hierarchy/washu/reports/DEEPDIVE-1109.md.
**Cornell (D-0072, 2026-11-25).** On a Cornell eCommons thesis or dissertation record (DSpace REST API, PhD, 2016 or later) the Committee Chair is the student's adviser when the chair matches a Cornell PI under R-STU-03; co-chairs each count. Rows: `hierarchy/cornell/reviewed/thesis-committee-chair-evidence.json` (558 rows, 112 PIs; hand check 30 of 30, worker-judged, seed stated in `thesis-committee-chair-handcheck.json`). Student-coverage sampling counts such rows (`accuracy/sample.py` `thesis_database_phd`).

### R-LNK-06 (2026-11-05, owner: Hanin deep dive) — a dissertation year is the END of the student's work
A PhD student known only from dissertation records (every relation role phd, its source quote a DSpace record whose `dc.contributor.advisor` names the PI)
has one recorded year, the degree year. Papers come mostly BEFORE it; the full-name route's window (two years before to six after) lost them (Jiasi Shen's 2018
paper with Rinard, thesis 2022). For such a student the full-name route (`full_name_on_lab_paper_byline`, R-LNK-01) counts from six years before the degree year
(`DISSERTATION_BEFORE`), on a lab paper of at most 15 authors; initial-only bylines never take the longer window; a roster, lab-page or program year is not a degree year
(old window). 70 links in the scratch rebuild (EPFL 41, Princeton 15, MIT 13, CMU 1); 14 of 14 sampled links correct.

### R-LNK-07 (2026-11-05, owner: Hanin deep dive) — spelling variants of a first given name, within the lab
Within-lab matching (R-LNK-03) reads a byline whose family name is written exactly as the lab student's (the straight reading only: never through the order
swap, which would turn a family-name typo into a match) and whose first given name, 5+ letters on both sides, differs by one insertion, deletion, adjacent
transposition or vowel-for-vowel substitution ('Aiden'/'Aidan', 'Connor'/'Conor', 'Makena'/'Maken'; `vowel_edit`). A consonant for a consonant ('Kavin'/'Navin',
'Anna'/'Anja') is a different name. Not under an East Asian family name (R-LNK-02a: 'Yue'/'Yuan'); never when the student's own spelling or another lab
student's exact name is on the paper, nor on a paper of more than 15 authors; exactly one candidate in the lab; the window and the guard of R-LNK-03 apply.
Counted `link_within_lab_spelling_variant`. Two earlier versions were withdrawn by the hand check: one through the order swap added 213 links and matched
different people ('Swarup Kumar Sahoo' / 'Swarun Kumar', 'Andy Peng' / 'Andy Zeng'); one with any one-edit change of a 4+ letter name added 8 links of which
three were doubtful ('Kavin'/'Navin', 'Yong'/'Yang', 'Anna'/'Anja'). Family-name typos stay queued for review (R-STU-13). Final: 3 links (Igoe, Georgiou, Schwinn), all correct.

### R-LNK-01 — link bases
A lab student is linked to a lab paper by the collection's person link; by their name on a school-affiliated
authorship; by their name on the byline within three years of the recorded advising; by their full name within two
years before to six after (2026-10-28); and by within-lab byline matching (R-LNK-03). Every edition's byline counts
(2026-10-29).

### R-LNK-02 (2026-10-29, owner) — the given-name guard
Every byline link passes a given-name guard: a byline whose first given name is a full word that differs from every
full given-name reading of the student is someone else ('Wei-Ning Chen' had been linked via 'Wei-Chen Chen'). Allowed:
equal, a nickname pair, hyphen/space variants, a middle name used as the preferred name ('Xiang Lisa Li' / 'Lisa Li'),
the family name written first, a 3+ letter prefix ('Avi' / 'Avinash') and a one-letter spelling variant of a 4+ letter
name ('Johann' / 'Johan'). `given_conflict`.

### R-LNK-02a (2026-10-29, review of the guard's kept prefixes)
Under an East Asian family name (`EAST_ASIAN_FAMILY`) a given name that is a prefix of another is a different common
name, not a short form: 'Xin Li' / 'Xinyu Li', 'Xiao Liu' / 'Xiaoyuan Liu', 'Rui Zhao' / 'Ruihan Zhao', 'Seunghak Lee' /
'Seung Hyun Lee'. One-letter spelling variants of 4+ letter names stay allowed ('Kirong' / 'Kiryong Ha').

### R-LNK-02b (2026-10-29, owner: best judgement) — recurring variants
A recurring co-author one letter from a lab student, on 3+ of the lab's papers, with no student of the lab spelled that
way, is the student under a roster misspelling (Yuxin Chen's roster says 'Gene Li', his papers say 'Gen Li').

### R-LNK-03 (2026-10-29, owner) — within-lab byline matching
A byline author who is exactly one student of the lab by family name (including a two-part family name the byline cuts,
or either half of a hyphenated one) and given name (equal, an initial, a nickname pair, or the same letters without
hyphens), within two years before to six after the recorded years, is that student.

### R-LNK-04 (2026-10-29, owner: accuracy sample) — nickname table additions (R10)
`hierarchy/nicknames/extras.csv`: Izzy is a nickname of Isabel, Izabel, Isabella and Isobel (Izzy Aguiar, Ugander's
student, publishes as Izabel Aguiar).

### R-LNK-04a (2026-10-29, owner: link-gap sample) — more nickname pairs
`extras.csv`: Manolis/Emmanouil (Zampetakis), Robbie/Robert, Dima/Dmitry and Dmitri, Ági/Agnes, Lily/Lillian.

### R-LNK-04b (2026-11-05, owner: round-r2 pooled failures) — Greek short forms; Robin Netzorg
`extras.csv`: Fotis/Fotios (Iliopoulos, Sinclair's student: two lab papers read 'Fotis') and Giorgos/Georgios. Robin is not a nickname of Robert, so no table pair is
added; Netzorg (Bin Yu's lab: the dissertation list says Robert, the roster and the ICML paper say Robin) is one reviewed `same_person` decision in
`student-identity-review.json` (R-STU-04). Izzy was added on 2026-10-29 (R-LNK-04). Tests: `tests/test_nicknames_round_r2.py`.

### R-LNK-05 (2026-10-29, owner) — links carry their evidence
Every byline link (`within_lab_byline_match`, `byline_name_with_school_affiliation`, `advisee_name_on_lab_paper_byline`,
`full_name_on_lab_paper_byline`) carries the work id, the exact byline string matched (`byline`) and the student's own
roster source (`relation_source`: relation type, url, sha256, quote); every link carries `relation_source`. Evidence
items with url, sha256 and quote are preferred when a relation or period keeps two; MIT's collection writes the quoted
sentence as `statement`, which becomes the quote (`best_sources`).

### R-LNK-08 (2026-11-08, owner: exact per-work source certification)
An independently reviewed, optional `member-paper-review.json` can certify only one existing retained candidate's
PI/member/accepted-work authorship. Exact identifiers and complete final PI/member/paper/candidate scientific preimages, a source-bound
owned-person citation, complete ordered author/affiliation mapping from a full primary PDF, and independently typed
membership dates must agree. Stale, missing, competing or temporally uncertain proof leaves the candidate unchanged.
Version 1 holds nonempty edition groups: persisted edition pointers alone cannot certify omitted source authorships.
`reviewed_exact_member_paper` carries `workReview.identity_scope=exact_work` and the original candidate. It admits no
paper/member, changes no source/date/alias, and cannot lend an OpenAlex/person anchor through either AtlasIDs byline
bridge path. Both pre-ID and post-ID invariance are checked before publication. Existing global joins require separate
review; full registry-copy comparisons precede enabling actual inputs. Contract: `docs/REVIEWS.md` section 4.
Tests: `tests/test_member_paper_reviews.py`, `tests/test_member_paper_ids.py`.

## Audits

### R-AUD-01 (2026-10-28, owner) — the seven chain checks
`tools/chain_audit.py`: coverage, pi, students, papers, links, copies, one_person; each item passes, is explained (an
evidence file, a rule, or `hierarchy/chain-reasons.json`), or is open.

### R-AUD-02 (2026-10-29, owner: best judgement) — revisit dates
An exclusion with `revisit_after` (a new arrival with no group or advisee yet) is decided only until that date; after it
the person is an open coverage item again. `chain_audit.revisit_due`.

### R-AUD-03 (2026-10-29, as R-LNK-02a) — one person
`tools/student_audit.py` `compatible`: under an East Asian family name a given-name prefix is a different person ('Yuan
Li' / 'Yu-Jhe Li').

### R-AUD-04 (2026-10-29) — build regression
`tools/build_regression.py`: every rebuild is compared with the snapshot taken before it; a school count moving more
than 5% (and by 5+), a PI losing more than 30% and 10+ lab papers, or gaining more than 100% and 20+, holds the release
until reviewed (`ALLOW_SWINGS=1`).

### R-AUD-05 (2026-10-29, owner) — the build-time evidence check
`tools/evidence_check.py` (rebuild stage `evidence`, after the audits, before the release): every PI period has an
evidence item with url, sha256 and quote; every listing has url, sha256 and quote; every student relation has a source
with all three; every lab paper has its school basis and an appointment (a period with evidence or a sourced listing);
every byline link has the work, the byline string and a sourced `relation_source`. A category over its whitelisted count
(`docs/evidence-whitelist.json`, each with its reason) fails the stage and holds the release; `make_release.py` refuses
without a passing strict `hierarchy/EVIDENCE-CHECK.json` newer than the packages.

### R-AUD-06 (2026-10-29, owner) — provenance is required
Every package's `report.json` carries `provenance` (`tools/provenance.py`): the code commit (or dirty with the diff's
sha256 over the build paths), the rule ids, the OpenAlex sweep's fetch dates and sha256, the DBLP dump's date and md5, the
DBLP person extract's and pi-works' dates and sha256, every reviewed input's sha256, and the school's other inputs.
`make_release.py` refuses a package without a complete block.

### R-AUD-07 (2026-10-29, coordinator) — a missing copy's real cause
`tools/lab_paper_copies.py` carries the stores' access-review cause (catalog table `access_review`, written by
`fulltext-push/review_access.py`) into `copies.json`; the chain audit's copies check explains each `needs_access_review`
paper by it (`ACCESS_REASON`): only 401/403, login/identity-provider redirects and bot challenges read as paywalled or
login copies; robots.txt, landing pages without a PDF, not found, policy skips, exhausted retries, unapproved redirects,
non-PDFs and identity mismatches each say so. The copies stage now runs before the audits.

### R-AUD-08 (2026-10-29, owner: link-gap sample) — the link diagnosis
`tools/link_diagnosis.py`: a student's school works are authorships that list the school (not just any institution),
without non-papers, dissertations and abstracts; an initial-only byline counts only when its author id also carries the
student's full given name ('Q. Yu' at Max Planck). A student who publishes without this PI but whose record (id or merged
id) is linked in another lab whose PI is on those works is `linked_in_coadviser_lab`; a linked same-name record of
another lab is `same_name_record_linked_in_other_lab`, never merged (R-HIER-03). A name shared by 4+ school authors is
resolved when exactly one of those author ids shares a school byline with another student of the lab written with a full
given name (`resolved.by = labmate_coauthor`).
**Extension 2026-11-12** (stage-7 trace of the legacy schools): three more reasons for a student whose every work with the PI is left out of the lab's papers. `with_pi_not_a_paper`: all
are records `papers.not_a_paper` drops (Zenodo or software records, edited volumes, meeting abstracts by DOI; the title/venue/DOI/type rules, no page counts); `with_pi_before_window`: all are
dated before 2016 by the PI's DBLP venue year (`venue_version_date`, R-PAP-26/38) though the OpenAlex deposit is later (a 2018 KiltHub copy of a 2012 USENIX paper); and a PI
authorship whose raw affiliation names another institution (`names_other_inst`) without any resolved OpenAlex institution counts as elsewhere, so `with_pi_at_other_institution`
covers a Harvard Society of Fellows byline. Mixed reasons fall back to `with_pi_outside_appointment`.

### R-AUD-09 (2026-10-29, owner) — student-only quotes are counted apart
`tools/evidence_check.py` counts a relation whose only sourced evidence is a re-captured student-only quote (R-STU-08,
`names_pi: false`) as `student_relation_student_only`, and such a link as `link_relation_source_student_only`, each with
its whitelisted count: the page names the student, the adviser rests on the collection's advising context.

### R-AUD-10 (2026-10-30, owner) — every missing copy has a recorded reason
Every CS lab paper without a local full-text copy carries a recorded reason why there is none, resting on dated checks of
every applicable open source and on every download attempt ("show that we definitely tried, and that there is a firm
reason why it can't be done"): the unavailability ledger, `fulltext-push/unavailable_ledger.py` (rebuild stage `ledger`,
after `copies`, before the audits and `evidence`; released and onboarding schools) ->
`hierarchy/<school>/unavailable.jsonl.gz` (one record per non-local paper: exactly one `reason_code`, its `summary`, the
checks, the attempts) and `unavailable-summary.json`; `tools/lab_paper_copies.py` `attach_ledger` puts `unavailable_reason`
and `unavailable_summary` on the paper in `copies.json`. The release carries both files and `MANIFEST.json` `ledger` the
counts by `reason_code`; the organized tree's `papers.csv` has `copy_status`, `unavailable_reason`, `unavailable_summary`.
`tools/evidence_check.py` fails the build on `unavailable_missing` (a non-local paper without a record), `unavailable_stale`
(a record checked before the school's `lab_papers.jsonl.gz` or `copies.json` `counted_at`, 300 s tolerance) and
`unavailable_incomplete` (`incomplete_check`) over their whitelisted counts; `tools/build_regression.py` flags a reason
count moving more than 25% and by 20+. The standard (sources, reason codes and their order, record schema):
`docs/UNAVAILABLE.md`.

## Atlas ids

### R-ID-01 (2026-10-29, owner) — one scheme
People `atl:p:<12 hex>`, works `atl:w:<12 hex>`, labs `atl:l:<school>:<pi-slug>`; opaque, deterministic from the strongest
anchor (person: ORCID, reviewed OpenAlex id, DBLP person, collection person id, school + name + evidence url; work: DOI,
OpenAlex, DBLP key, arXiv id, collection work, lab-page record). `docs/IDS.md`, `tools/atlas_ids.py`.

### R-ID-02 (2026-10-29, owner) — never changes, merges redirect
`hierarchy/ids/registry.sqlite` maps every anchor ever seen to its id; an entity keeps the id any of its anchors finds.
Two ids that become one entity: the earlier-issued stays, the other redirects (`redirects.tsv`) and is never reissued.

### R-ID-03 (2026-10-29, owner) — joining people
Across labs and schools only by ORCID, a reviewed OpenAlex id or a DBLP person, never by name alone; a join between
different family names is refused. A student joins a PI elsewhere when the byline author id on the student's linked lab
paper is that PI's reviewed OpenAlex id and the names are compatible (full first given name or a nickname pair).

Within one school, a shared native `ext:` student record can identify co-advised memberships only with compatible
full names and reciprocal URL/hash/quote evidence explicitly naming the advisers (2026-11-08). A given-only adviser
must be unique schoolwide. Names or the external key alone never join records; each membership's sources, role and
observed years remain distinct. Unresolved cited co-advising, incompatible names, or multiple previously issued person
IDs stop the ID stage before assignment or writes (`CoadvisingIDConflict.holds`); existing issued IDs are not silently
redirected by this route. One already-issued ID is reused. The source proof appears in `IDS-REPORT.json`; candidate
student-paper author identity remains candidate.

### R-ID-04 (2026-10-29, owner) — joining works
Rows sharing a work anchor, editions included, are one work across labs and schools; two rows of one lab are never one
work (they join only through their own lead record).

### R-ID-05 (2026-10-29, owner) — everywhere
The ids are written by the rebuild stage `ids` into the packages, copied into every release with the registry and the
cross-reference table, and carried by the tree, the GitHub export and the site handoff; `make_release.py` refuses a
package without them.

### 2026-11-06: documented death ends an appointment

R-PAP-03 also recognizes `faculty_end_deceased` evidence. Later memorial or stale faculty listings are kept aside as `listingsAfterMove` and do not extend the appointment. Huei Peng’s reviewed end is 2022, supported by the captured ASME DSCD Winter 2022 memorial. ASME and Michigan Engineering disagree by one day, so only year precision is asserted.

### R-STU-24 (2026-11-09, owner approved) — an ORA thesis record's Supervisor contributor
On an Oxford University Research Archive (ora.ox.ac.uk/objects/uuid:...) DPhil/MSc/MPhil record, a contributor with `Role: Supervisor` names the student's adviser. The record must be from 2016 or later;
the supervisor must resolve to exactly one school PI (ORCID match, else family name + first initial unique among the PIs, R-STU-03; a supervisor or author department outside the computing-related set
is skipped); the student's name is spelled out (the OpenAlex byline `Family, Given` or the record's copyright holder). Years: the degree year (R-STU-14). Rows: `reviewed/thesis-evidence.json`,
built by `tools/ora_theses.py` (list from the snapshot extension, crawl at 3 s, parse, evidence); the pages are stored in the capture store. ORA pages carry a recaptcha script for their feedback form, so the
tool judges a page by its own record markers instead of school_web's challenge pattern; robots.txt (`*`, no AI rule) is honoured. 2026-11-09: 1,141 records read, 415 rows, 113 PIs; hand check 30 of 415 (seed 20261109): 30 correct.

### R-STU-25 (2026-11-09, owner approved) — a CS student profile page names the supervisors
An Oxford Computer Science student profile (www.cs.ox.ac.uk/people/First.Last) reads "Doctoral Student ... Supervisors <full names>". Each full-name match with a school PI is a row (`reviewed/roster-evidence.json`,
`tools/cs_student_pages.py`); the line is cut at "Past Student", "Students" and "Co-supervis...". Years: the leaving-date year, else the capture year. 175 rows, 55 PIs; hand check 30 of 175 (seed 20261109): 30 quotes verified in the page; one spill-over (a past-student name after the supervisors) found and fixed.

### R-STU-26 (2026-11-13, owner approved) — a CSE Graduate Placements card is a dated student-adviser pair
On the HKUST CSE page `https://cse.hkust.edu.hk/pg/ourgraduates/` (department's own page; robots.txt allows it) a card reads `<name> / <job> / <employer> / PhD <year> / Supervised by <PI>[ and <PI>]`. A PhD card of 2016-2026 whose supervisor is exactly one CSE PI by the full-name rule (`pihier.names.Name`; a name two PIs share is dropped) is a row: role `phd`, years `[year, year]` (R-STU-14, R-LNK-06), quote = the card text verbatim in the page's text, url and sha256 of the capture. A co-supervised card ('X and Y') is a row only for a named supervisor who is a PI (the PI is a named co-supervisor). Rows: `hierarchy/hkust/reviewed/thesis-evidence.json` shape, built by `tools/hkust_cse_graduates.py`. A PI with no appointment period (listing-only arrival) needs a period record before its rows are wired (Cheng, Lin, Bensaou). Tests: `tests/test_hkust_cse_graduates.py`.

### R-STU-27 (2026-11-13, owner decision, repeated and confirmed: "go ahead, and lets please do it") — a student's own OpenReview profile
A student's own public OpenReview profile (api2.openreview.net, profile search by name) is dated student-adviser evidence when all hold: (1) its name matches the candidate; (2) a `history` entry at this school (institution domain from the charter's `[web].domains`, or the school name; a campus the charter excludes does not count) with a PhD or MS student position whose dates overlap the PI's appointment window; (3) a `relations` entry of type PhD Advisor or Advisor (the student declares it; the relation is one-directional) whose name matches the PI by token set (two or more tokens, hyphen and space folded: Jia-Wang = Jiawang) or whose username does. Candidates come from the frozen 7-feature co-authorship rule (`tools/selfdeclared_candidates.py`, pilot 2026-11-13, F0.5 .48); a candidate is only a name to look up. Student-less PIs and PIs with fewer than three students are searched first.
Flags on the row: `co_advised` (a second adviser is named: still admitted, only because the PI is a named adviser; a profile naming other advisers only is no evidence), `common_name_pi` (a very common PI family name), `second_same_name_profile` (another profile of the same name that is not clearly elsewhere: HELD, never admitted), `role_unspecified` (a generic student position with only a bare Advisor relation: HELD). Years: the history dates (an open end runs to the capture year). Row: `rule: R-STU-27`, `evidence_kind: self_declared_openreview`, `url` = https://openreview.net/profile?id=<id>, `sha256` of the cached API response, `captured`, a quote built verbatim from the matched history and relation fields, role phd/masters; no e-mail address and nothing beyond name, school, adviser, dates and profile id. Proposals go to `scratch/openreview-students/proposals-<school>.json` (the LP-STU-01 reviewed-additions shape) and are wired like any additions file: after the fresh 20-row hand check (docs/ADDING-A-SCHOOL.md, stage 6).
Politeness (host ruling `docs/host-rulings.json`): at least 10 s between requests (two 429s at 6 s on 2026-11-13), one login, a persistent chmod-600 response cache so no request is repeated, a per-run budget of 100 requests; the first HTTP 429, any 401/403, a challenge/captcha/MFA marker stops everything for the UTC day (no retry, no evasion). Credentials only from `~/.config/cs-atlas/openreview.env`. The account is currently the owner's personal account; a dedicated project account is recommended. Pilot 2026-11-13: 27-37% of ground-truth students validated at precision 8/8, 9/9, 10/10. `tools/openreview_students.py`, `tests/test_openreview_students.py`.

### R-PAP-42 (2026-11-09, Claude on the owner's delegation; ZJU admission review) — ORCID-conflict namesake evidence and reciprocal-URL bindings
(a) An OpenAlex author id that carries an ORCID absent from every ORCID of the PI's source-bound DBLP person record is another person's record: `mixed_openalex` when a DBLP-DOI-verified work of the PI sits under it (R-PAP-06: per-work evidence needed), `not_openalex` when none does. An id with that ORCID stays anchored; an id with no ORCID is reviewed per work (`hold`). Evidence per id: the stored work record (url, sha256, literal ORCID quote) and the DBLP record (url, sha256, ORCID quote). Only the id is reviewed, never a name. ZJU: 24 of 33 anchor clusters (681 of 713 relations) were namesakes (Wei Chen, food chemistry, mechanics, oncology). (b) A PI is bound to a DBLP person record when that record lists the exact normalised profile URL the official roster links for the PI, its author name is compatible with the PI's name and its affiliation note names the school (8 ZJU PIs; ORCID inheritance stays unallowed). Library `tools/orcid_namesake.py`; tests `tests/test_zju_orcid_namesake_rule.py`.

### R-PAP-45 (2026-11-13, VT Stage 9 accuracy review) — an anchored id cannot override two independent name and ORCID conflicts
When a byline matches a PI only by a first initial and family name, spells a different full given name after that initial, and the byline's OpenAlex author ORCID disagrees with every source-bound PI ORCID, the anchored-author-id route cannot admit that work. A PI alias naming the full given name, a matching ORCID, or independent per-work DBLP or reviewed page evidence remains eligible. VT's `G. Alan Wang` business papers were attributed to the CS PI `Gang Wang` through a mixed OpenAlex id despite their different ORCIDs; six weak anchored rows are held. This is a per-work guard and does not blacklist the author id or the name. `anchored_orcid_given_name_conflict`; test: `tests/test_namesake_guard_and_placeholder_pi.py`.

### R-STU-28 (2026-11-13, owner decision: asked by the coordinator, answered "Yes, allow it") — the recall check reads ALL captured pages of the PI
`tools/student_recall.py check` compares a sampled PI's listed names with every captured page of that PI on the same host (people, students, alumni pages and alumni sub-pages), not one page. A record entry gives the primary `page` (url, sha256, verbatim quote) as before; further pages go in `extra_pages` [{url, sha256}] (a `page` list is accepted too, first element primary). Every page must be in `student-recall-captures.sqlite` with its sha256; an extra page on another host than the primary page is a finding (a different lab's page cannot validate a name). A name counts when ALL its tokens are on ONE page (tokens never combine across pages); a name on no captured page is the finding "not on any captured page of the PI". Small-caps spacing the page splits after the first letter ('S HEWCHUK') is folded when matching (the original text stays matchable). Unchanged: thresholds R1 .90, R2 .35, U .60, Z 5%, the strict dated/current-section rule, the exclusion cap, the fresh-reviewer sign-off. Test: `tests/test_student_recall.py::test_R_STU_28_names_on_any_captured_page_of_the_pi_same_host_only`.

### R-STU-29 (2026-11-14, owner: "yes", relayed by the coordinator) — an HKUST CSE event page names a PhD candidate and the supervisor
`https://cse.hkust.edu.hk/pg/defenses/<season>/` (the department's own season indexes, 2016-2026; robots.txt allows them, no AI-agent rule) link one page per **PhD Qualifying Examination**, **PhD Thesis Proposal Defence** and **PhD Thesis Defence**. The page reads `By <Mr./Miss/Dr. Given FAMILY>` and `Committee Members: <Prof./Dr. Full Name> (Supervisor) ...`.
1. Evidence: a PhD event of those three kinds, dated 2016 to 2026 and not after the capture date (a future event is held), a spelled-out candidate name (the given name is not an initial), and a committee line marked `(Supervisor)` (also `(Co-supervisor)`, `(Thesis Supervisor)`). Chairperson and plain members never count. MPhil events are skipped.
2. Tie: the supervisor's full name matches exactly ONE HKUST PI by the build's full-name rule (`pihier.names.Name`; a name two PIs share is dropped). A second named supervisor is a row for every named supervisor that is a PI (the PI is a named co-supervisor), as R-STU-26.
3. Role `phd`. Years (R-STU-14): the event year; one student under one PI is one row with years [first event year, last event year] over the student's events (qualifying, proposal, defence); the primary source is the thesis defence, else the latest event, the others go in `other_sources`.
4. Periods: only PIs with a period record (pis.json `periods` or `reviewed/faculty-periods.json`) whose period covers the event years are rows; a PI without one, or an event before the period start or after its end, is HELD (R-STU-26's condition; nothing outside the window). **`--listing-window` (2026-11-25, owner rules 2026-10-21 and 2026-11-02):** a PI with no period record has an event of year Y admitted only when a captured dated department listing names the PI in Y (`period_basis.facultyBasis: department_listing_same_year`, the listing url and sha256 cited on the row); a year without a listing, including every year after the last listing once a later listing without the PI exists, stays held, and an event page alone extends no appointment. Events outside the window are left out of a row that has events inside it. Same check for the R-STU-26 cards (`hkust_cse_graduates.py --listing-window`). Without the flag nothing changes.
5. Quote: the verbatim candidate line (`By <name>`) and the verbatim supervisor line of the page, joined with ` [...] `; url and sha256 of the stored capture (R-STU-12).
Rows (thesis-evidence shape): `tools/hkust_cse_defences.py` (`seasons`, `crawl`, `evidence`; the crawl is one Slurm job, `tools/hkust_defences.slurm`, 3 s, resumable, stops on 401/403/429/challenge). Host ruling in `docs/host-rulings.json`. Risks: namesake students (an event is tied to the PI of that page only), co-supervision, a supervisor name variant that matches no PI (listed in the unmatched report, not guessed), a qualifying exam is not proof of a degree. Tests: `tests/test_hkust_cse_defences.py`.

### R-STU-30 (2026-11-14, owner "yes", relayed by the coordinator) — a Tsinghua page states a student's adviser: department news, the Beijing outstanding-thesis list, a PI's profile page
Sources, all already stored by the crawl (offline; the tool fetches nothing): (a) a department news article or speech on a charter host (www.cs, air, www.thss, iiis, www.ee, www.au, www.me `tsinghua.edu.cn`); (b) the university's 2025 list of outstanding Beijing doctoral theses (`www.tsinghua.edu.cn/jxjywj/...mingdan2025.pdf`: `<year> <subject> <student> <adviser> <title> [提名]`); (c) a PI's own official profile page (`<year>年指导博士生<name>获...`).
1. Statement: ONE sentence names a student (2-4 Han characters starting with a common surname), a student level (博士/直博 -> `phd`, 硕士 -> `masters`; a postdoc, faculty, 'graduate' with no degree, a team or competition adviser, or a clause that lists a postdoc, undergraduates or developers with the student, is never a row) and the adviser by 导师 / 指导教师 / 论文指导教师 / 师从 (patterns A, B, C, E in the tool header; anything else is not a row). The quote is the verbatim sentence part in the flattened page text; url and sha256 of the stored capture (R-STU-12).
2. Tie: the adviser's full Han name equals exactly ONE PI (a name two PIs share, or a bracket-tagged twin, is dropped, never guessed); the page's site must belong to the PI's department (CS and AIR sites -> CS/AIR PIs, ee -> EE, thss -> SW, au -> AU, iiis -> IIIS, me -> ME/SVM; thesis-list subject mapped the same way).
3. Years (R-STU-14): `[y, y]` with y = the article date year, the AWARD year of the thesis list (owner-accepted: the thesis was defended earlier) or the year stated on the profile page. A nomination (提名) line counts like any other: the list names the thesis author and the adviser either way. A year outside 2016-2026, after the capture year (future) or an article with no date is HELD.
4. Periods (kinds 1-3 only): the PI needs a period record (pis.json `periods` or `reviewed/faculty-periods.json`) covering y; none, y before its start or after its end is HELD (nothing outside the window). A listing-based period (earliest stored dated department listing, kind 3, sha-verified) is accepted for EE and AU PIs whose archived-list years are not in pis.json.
5. One student under one PI is one row; the same pair on a second page goes in `other_sources`.
Rows (thesis-evidence shape) and the held list: `tools/tsinghua_adviser_statements.py evidence --captures DB... --pis pis.json --periods faculty-periods.json`. Risks: a namesake adviser outside the PI list (site/department check only), a student level word that belongs to another person in a long sentence, a thesis defended before the PI's period start (held by the year rule). Tests: `tests/test_tsinghua_adviser_statements.py`.

### R-PAP-44 (2026-11-09, Claude on the owner's delegation; Tsinghua bibliography expansion) — title-only DBLP bindings
A faculty-to-DBLP binding normally needs a source-stated English name (a Latin roster name, or Chinese plus Latin on one source). Without it, a binding
is accepted only when (a) the PI's own official profile or owned page credits at least 10 exact long DBLP titles (credited by the person's name in the
citation) and every one belongs to one single DBLP person; (b) that person carries a school affiliation note OR the exact-title list sits on a page the school's own official listing links as that PI's page (url + sha256 recorded; amended 2026-11-09, owner-delegated, first used for Toronto Fan Long and Kirill Serkh, applies to Tsinghua bindings too); and (c) no namesake (another DBLP person of
the same base name, ORCID conflicts as in R-PAP-42) also owns a matched title. Fewer than 10 titles, or a pinyin-name-only match, stays held. Rationale:
a profile list of 10+ exact titles that all sit on one record and appear on the official-listing-linked page (or the record carries the school's affiliation) cannot be another person's work by chance; the 5 earlier Tsinghua holds
(贺飞, 潘浩, 鲁继文, 张长水, 宋韶旭) are overridden only where this holds. `tools/title_only_binding.py`, `tests/test_title_only_binding_rule.py`.
Identity only: papers still pass appointment (R-PAP-01), affiliation and type gates.

Amendment (2026-11-10, owner-delegated; SJTU stage 5): titles on one DBLP person do not make that person the PI (a lab page lists the lab's papers: 11 of 26 SJTU title-only matches were another lab member or a coauthor). A caller passes the PI's byline aliases to `decide(..., pi_aliases=[...])`, and the person's name (numeric suffix, hyphens and word order ignored) must equal one of them (`person_name_not_pi_alias` otherwise). `tests/test_title_only_binding_rule.py`.

### R-PAP-65 (2026-11-25, owner D-0090) — pinyin + exact-unit DBLP note
A faculty-to-DBLP binding without a source-stated Latin name is accepted when (a) the PI's Han-name pinyin equals the DBLP person's base name (given and family order-insensitive), and (b) that person's note in the local pinned DBLP dump (never dblp.org) quotes 'Zhejiang University' with the PI's census unit exactly, and (c) no other DBLP person of the same base name carries a note for that unit. The binding records route `pinyin_plus_exact_unit_note_D0090`, the dump-note quote, the pid and the Latin alias. Identity only: papers still pass appointment (R-PAP-01), affiliation and type gates. Complements R-PAP-44 (title-only bindings). First used by ZJU stage 5 (丁一, 于淼, 杨欢, 赵毅, 虞小鹏, 陈实); `tests/test_zju_d0090_bindings.py`.

### R-HOME-01 (2026-11-09, owner-delegated: "best long-term answer") — home department is the stated primary appointment
A PI's home department is the primary appointment the official page states (a profile's "Primary Teaching Area", or the unit that holds the tenure line). Other units the title names stay as secondary affiliations in `also`; none is discarded. Where a title names several units and no captured official page says which is primary, the reviewed decision lists them in `primary_unresolved` (two or more units including `home_department`): the row is marked `home_basis = primary_unresolved`, `home_department` is only the reporting unit, and every named unit stays visible. Never pick a unit by title order and call it primary. `home_basis` values: `primary_stated`, `primary_unresolved`, `listed_title` (single-unit title, no primary statement needed). Evidence is url + sha256 + verbatim quote. Implemented in `tools/home_departments_school.py` (`apply_reviewed_homes`), tests in `tests/test_home_department_overrides.py`. First applied to the 33 Harvard additions (Yue Lu corrected from Electrical Engineering to Applied Mathematics).

### R-HOST-01 (2026-11-10, Claude on the owner's delegation; owner to confirm) — never-contact hosts need no robots verdict
A charter host on the never-contact list (dblp.org and www.dblp.org: local dump only, never fetched; orcid.org and pub.orcid.org: the public API is not an authorized channel; web.archive.org and web-static.archive.org: only through the shared Wayback throttle) with `use = none` is recorded by `tools/school_hosts.py` as `robots: not_fetched`, `consistent: true`, with no request. Any other `none` host still has its robots.txt read. `tests/test_school_hosts_never_contact.py`.


### R-ACC-01 (2026-11-13, owner decision: "yes" to making gate 9 compare summary hashes with the live build) — an accuracy summary is bound to its build
`tools/stage_gate.py` gate 9 reads `accuracy/summary-<key>.json` and opens with "the build changed since the draw" when any file hash the summary recorded at draw time (`files`: pis.json, students.json, lab_papers.jsonl.gz, student_papers.jsonl.gz, copies.json) differs from the live school package, or the file is missing (the stored `files_now` is written at summarize time and never moves, so it could not see a rebuild after the draw; it is still checked). Thresholds unchanged (lab precision .95, student-link .97, lab coverage .90). The current round's summary (`accuracy/round-r3/summary-<key>.json`, verdicts stay in the round directory) is copied to `accuracy/summary-<key>.json` with the older summary archived beside it. A promotion after a draw therefore reopens gate 9 until a redraw. Test: `tests/test_stage_gate.py::test_R_ACC_01_gate9_compares_the_summary_hashes_with_the_live_build`.

### R-STU-31 (2026-11-14, owner requested Oxford Stage 6 fix while retaining the 20% cap) — source verified external institution exclusions
The Stage 6 student recall X limit remains 20%. A listed name marked `outside_school` is exempt from X's numerator only when `outside_school_evidence` gives a URL, SHA-256, exact visible line and another institution; the line must name both the listed person and that institution, and the captured page must be one of the sampled PI's hash-matched pages. The other institution must not match the sampled school's charter affiliation. The name remains visible in `names_excluded` and `excluded_share`. Missing, mismatched, or merely inferred outside-school claims still count against X. This changes no eligibility, R1, R2, U, or Z thresholds. Test: `tests/test_student_recall.py::test_R_STU_31_captured_same_line_external_school_proof_keeps_x_cap`.

### R-STU-32 (2026-11-14, Oxford Stage 6 source review) — read captured PDF supervision lists
The student recall checker extracts text from a captured PI-owned PDF using `pdftotext`. It checks names and quotes against that extracted text while the capture's SHA-256 remains the hash of the original PDF bytes. An unreadable PDF contributes no names or quotes and cannot silently pass as a readable page. Test: `tests/test_student_recall.py::test_R_STU_32_captured_pdf_supervision_text_is_checked_against_original_bytes`.

### R-PAP-47 (2026-11-15, build: HKUST accuracy review) — retained contact addresses

When a raw authorship explicitly names another institution, an email address at the school does not by itself establish school affiliation. Preserve independent structured school affiliations and a literal named school or dual affiliation outside the contact address. This prevents an old university email on a Huazhong-affiliated authorship from creating an HKUST lab-paper claim. The correction applies to each authorship; another author's school evidence cannot fill the gap. Primary paper-specific affiliation evidence remains available under R-PAP-10.

### R-STU-33 (2026-11-17, owner D-0001 item 7, approving the digest recommendation; Q-0012, 0124, 0134, 0135, 0162, 0245) — shared lab pages without a per-student adviser
A student entry on a roster shared by several PIs (department or institute people page, multi-PI lab or team page, shared-host roster) is excluded unless the ROW itself names the PI as adviser or co-adviser. A "main contact" line, a lab-head listing, a two-PI roster or a profile-page roster with no per-row adviser does not attribute the student to anyone. This is the one-PI rule of R-STU-30 applied to shared pages (examples: Tsinghua FIB-LAB 47 rows for Yong Li, MADSys/THUIAR/NISL shared rosters, SJTU AISL two-PI roster, shared-host rosters in the recall check). A PI's own single-PI lab page is unaffected. Existing rows on such pages are removed by the school's owner session at its next build; this entry changes no data by itself.

### R-STU-34 (2026-11-23, owner D-0046: "Students only") — a lab's student count is student roles only
`counts.students` in pis.json (tools/pihier/build.py) and `students` in LAB-COVERAGE (tools/lab_coverage.py, read straight from students.json) count only
members that pass `pihier.links.student_role_ok` (R-STU-19 rule B): a PhD, masters, undergraduate, student, alumnus or intern role, a `visiting` student
(R-STU-17), or a `member` whose own entry or heading says student. Postdocs, staff, research scientists, non-student visitors and `other` members stay on
the lab in students.json and are counted in the new `counts.members` / LAB-COVERAGE `members`; they are never students, so a lab whose only member is a
postdoc is a 0-student lab (`open` until a reason is recorded). Found 2026-11-23 on the one-student review: Berkeley Chayes and CMU Compeau held only
gap-evidence rows with role `postdoc`; about 5,000 non-student member records across 19 schools were counted as students. At the change, about 40
labs across schools move to 0 students (Harvard 12, Stanford 7, NTU 7). Tests: `tests/test_lab_coverage.py`.

### R-PAP-48 (2026-11-19, owner D-0023; gate-9 round pi2) — supplement and congress abstracts
Rules added after the pi2 reviewers' verdicts (`accuracy/round-pi2/verdicts-{toronto,zju}.jsonl`). Each is anchored to stored OpenAlex fields (DOI shape, type, venue, title, page-1 text); each was run over every lab-paper row of all 27 school packages before landing (counts below; a build only changes at each school's next rebuild). Tests: `tests/test_paperfix_d0023_rules.py`.

(`meeting_abstract:supplement`): (a) an OUP journal item DOI with a dotted item suffix after the article id (`10.1093/jcag/gwaf042.015`, `ehz748.0574`, `ofx163.110`, `esj/aakag023.632`), type article, conference-abstract or other; ordinary OUP DOIs have no such suffix. Every one of the 141 rows it hits is a congress supplement abstract (ESC, IDWeek, SLEEP, Neuro-Oncology, M&M, Innovation in Aging, CAG ...). (b) `Neuromuscular Disorders` DOIs `10.1016/j.nmd.YYYY.MM.NNN` with item number 100 or higher (World Muscle Society congress items; a regular item stays below 100; Brudno's `nmd.2017.06.320`).

### R-PAP-49 (2026-11-19, owner D-0023; gate-9 round pi2) — artifact deposits
(`artifact_deposit`): DOI series `10.4230/artifacts.N` (Dagstuhl/DROPS artifact-evaluation deposits: software or data of a paper, with the paper's title or a repository name; Beck's `artifacts.23555`). LIPIcs/OASIcs paper DOIs are untouched.

### R-PAP-50 (2026-11-19, owner D-0023; gate-9 round pi2) — workshop front matter and proposals
(`workshop_proposal`): conference-paper, conference-abstract or other records titled `<acronym or name>: <First|Second|Nth> [International|Annual|Capitalized words] Workshop ...` (`Meta-HCI: First Workshop on Meta-Research in HCI`, `ADVM'21: 1st International Workshop on ...`, `DRL4IR: 2nd Workshop on ...`). Lower-case words between the ordinal and `workshop` do not match (`Graph coloring: First results on a workshop scheduling problem` stays); `article` records (workshop reports) are not touched.

### R-PAP-51 (2026-11-19, owner D-0023; gate-9 round pi2) — a journal's report on itself
(`editorial`): `Report on the state and changes of the <name> journal` (Chechik's SoSyM 2025 summary by the editors-in-chief). `Report on the state of the art ...` stays.

### R-PAP-52 (2026-11-19, owner D-0023; gate-9 round pi2) — page-1 company footnote
(`page1_elsewhere`, R-PAP-20 extension): the author-block marker of a byline author opens a footnote on page 1 that names a company or industry lab (`1 Google Research. Correspondence to ...`, the marker alone on its line); the unaffiliated-byline route then refuses the paper as `unaffiliated_page1_elsewhere`. Why Fleet's arXiv 2302.14816 got through: R-PAP-12 (an advisee, Norouzi, on an unaffiliated byline) kept it because `page1_elsewhere` only recognised footnotes naming a university, institute or laboratory, and the `Google Research` footnote stands alone after the marker line. A page with no affiliation at all still says nothing.

### R-PAP-53 (2026-11-19, owner D-0023; gate-9 round pi2) — grid author blocks
(`tools/pi_fulltext_affiliation.tie`): a numbered affiliation printed BEFORE the names that carry its marker (`Xingyi He1* 1 Zhejiang University Jiaming Sun2* Hujun Bao1 ...`) now ties the school to the PI whose marker it is; the line must open with the marker and name the school within its first 40 characters. ZJU's OnePose++ (NeurIPS 2022) page 1 is such a block; `ok_untied` kept it out.

### R-PAP-54 (2026-11-19, owner D-0023; gate-9 round pi2) — ZJU key laboratory
(`schools/zju.toml [affiliation] regex/loose`): `State Key Lab(oratory) of CAD&CG` (any of `&`, `&amp;`, `&#x0026;`, `and`) and `计算机辅助设计与图形系统(国家|全国)重点实验室` name Zhejiang University's own key laboratory even when the string omits `Zhejiang University` (OpenAlex gives Wei Chen's TIST 2022 paper and Bao/Zhang's ICCV 2021 paper only `State Key Lab of CAD&CG`). The 2026-11-17 owner ruling (CADCG an affiliated unit, not a department) concerns the roster, not the affiliation string. `Zhejiang Lab` stays excluded (`must_not_match`).


### R-PAP-55 (2026-11-19, owner D-0023; Oxford gate 9 pi2: Worrell's ICALP 2021 volume) — DROPS complete volumes
A record titled `LIPIcs, Volume N, <venue year>, Complete Volume` (or `OASIcs, Volume N, ... Complete Volume`) is the whole proceedings volume (`proceedings_volume`); its byline is the volume's editors. 26 rows across 14 schools match, all complete volumes (oxford 5, cambridge 3, nus 3, ...). Test: `test_R_PAP_55_drops_complete_volume`.

### R-PAP-56 (2026-11-19, owner D-0023; Oxford gate 9 pi2: Namburete's ISUOG abstract) — Ultrasound in Obstetrics and Gynecology congress abstracts
`Ultrasound in Obstetrics and Gynecology` joins the meeting-abstract journals (R-PAP-19) for records typed `conference-abstract` (ISUOG congress items `OP08.03: ...`, DOI `10.1002/uog.NNNNN`); ordinary articles of the journal stay. 6 rows match (oxford 5, cuhk 1), all congress abstracts. Test: `test_R_PAP_56_uog_congress_abstract`.

### R-PAP-57 (2026-11-19, owner D-0023; MIT gate 9 pi2: Modiano's LIDS report) — institutional annual reports
A record titled `Report to the President for year ended June 30, YYYY, <unit>` (the DSpace@MIT annual reports of departments, labs and programs; no DOI, typed article) is administrative reporting, not research (`annual_report`). 11 rows match, all MIT (Peraire 3, Modiano 2, Tidor 2, Sarma, Chandrakasan, Zhao, DiCarlo). Test: `test_R_PAP_57_annual_report`.
D-0023 MIT reviewed entries (R-PAP-39, `hierarchy/mit/reviewed/census-overrides-school.json`, evidence in each entry): the SpaceCHI 2.0 CHI EA 2022 workshop description (Paradiso and Maes bylines; the ACM abstract page invites participation in the workshop) and the single-author DevOps record on Saurabh Amin's author id (its DOI is unregistered in the DOI system; the namesake judgment is the reviewer's inference). MIT is released, so the 14 removed rows are recorded in `hierarchy/mit/reviewed/release-corrections.json` under `not_paper_rule`. SpaceCHI 2.0 is NOT dropped by R-PAP-50 (its title carries no ordinal workshop wording).

### R-PAP-58 (2026-11-19, owner D-0026; Georgia Tech gate 9 pi2: Inan's IEEE Sensors 2016 record) — IEEE live-demonstration abstracts
A record titled `Live demonstration: <system>` (ISCAS, BioCAS and Sensors demo sessions) is the one-page description of a demo, not a paper (`demo_abstract`). 38 rows across 10 schools match, all such demo abstracts (jhu 11, epfl 7, gatech 6, ntu 4, purdue 3, cmu 2, tsinghua 2, others 1). Test: `test_R_PAP_58_live_demonstration`.

### R-PAP-59 (2026-11-19, owner D-0026; Georgia Tech gate 9 pi2: Liu's slides, Hester's Zenodo record) — slide decks and data/code deposits typed book
A title ending `(Presentation)` or `(Slides)` is a slide deck (`presentation_only`; 1 row, gatech). A Zenodo/Figshare/Dryad DOI typed `book` whose title ends in a `(Data ...)`, `(Code ...)`, `(Software ...)` or `(Schema ...)` parenthesis, opens `Official implementation of`, or ends `analysis code`, `analysis dataset` or `notebooks and ... data` is a deposit (`dataset_record`; 5 rows: gatech 2, cuhk 2, harvard 1). Other Zenodo books (monographs, reports, course texts) stay. Test: `test_R_PAP_59_slide_deck_and_book_typed_deposit`.

### R-PAP-60 (2026-11-19, owner D-0026; UChicago gate 9 pi2: Chien's CACM column) — editor-in-chief anniversary columns
`<N> years as editor-in-chief of ...` is an editor's column (`editorial`; 1 row, uchicago). Test: `test_R_PAP_60_editor_anniversary_column`.

### R-PAP-61 (2026-11-20, owner D-0028; SJTU gate 9 pi2: Li Jianhua's FITEE 2018 record) — FITEE special-issue introductions
A Frontiers of Information Technology & Electronic Engineering record whose DOI is `10.1631/fitee.YYNNNN0` ending `0000` is the opening item of a special issue, the guest editors' introduction (`editorial`): `fitee.1840000` 'Security for cyberspace: challenges and opportunities'; Georgia Tech's reviewed `fitee.1820000` entry (R-PAP-39) is the same class. 8 rows across 4 schools match (tsinghua 4, pku 2, cuhk 1, sjtu 1); seven of the eight carry the introduction titles ('Design and application of new storage systems', 'Coordination of networking and computing: toward new information infrastructure', 'Intelligent unmanned systems: important achievements and applications'). Test: `test_R_PAP_61_fitee_issue_introduction`.

### R-PAP-62 (owner-approved 2026-11-25 (D-0074); proposed 2026-11-25, Cornell early gate-9) — a raw affiliation that says the work was done elsewhere
Found by the Cornell early gate-9 sample (lab-paper precision .87). They live in the shared builder, so they change every school's build on its next rebuild, released schools included; owner-approved 2026-11-25 (D-0074); they land on main with the Cornell branch at stage 10. Test: `tests/test_stage9_cornell_early_rules.py`.
A raw affiliation that says where the work was done ('work done at/while at/performed at X', X not the school) names that place as the work's: 'Cornell (work done at MIT)' gives the school no basis (`papers.work_done_elsewhere`, in `_authorship_school_via`). Only when no other raw string names the school.

### R-PAP-64 (owner-approved 2026-11-25 (D-0074); proposed 2026-11-25, Cornell early gate-9) — IOVS abstract supplement, and the chairs' welcome title
- **IOVS.** A type-`article` record in Investigative Ophthalmology & Visual Science with no DOI is an ARVO meeting-abstract supplement (`meeting_abstract:journal_no_doi`); a regular IOVS article has a 10.1167 DOI.
- **Chairs' welcome.** `EDITORIAL_TITLE` also catches "Chairs' welcome/message/preface/foreword/letter/introduction" (optional "CSCW 2018:" prefix) and "welcome (message) from the chairs" (`editorial`).
- **R-PAP-63 withdrawn.** A drop of 100+-author works reached only through an anchored OpenAlex id was proposed for Wen Sun's 71 CMS rows and withdrawn: at other schools it also removes genuine consortium CS papers (Ego-Exo4D, Open X-Embodiment). Wen Sun is fixed by data instead: OpenAlex A5101618125 is recorded `mixed_openalex` in Cornell's census overrides (R-PAP-06); the rebuild removed the same 71 rows.

**D-0028 SJTU paper-claim-review fix (data, not a rule; 2026-11-20).** SJTU's gate-9 coverage .682 came from stale reviewed holds. `hierarchy/sjtu/reviewed/paper-claim-review.json` held 2,179 works with flag `anchored_uncorroborated` (2026-11-09, claude-sjtu-admit-1109): 'OpenAlex author-id anchored row not listed on the PI DBLP person record ... (namesake risk, R-PAP-04/14)'. Since then the PIs were bound to their DBLP person records (identity bindings 2026-11-17/19), and 1,283 of those works are now listed on the PI's DBLP person record by DOI or exact title, so the hold's premise is false and it withheld the paper from the PI before identity (Kong Linghe's IPSN20, NPC19 and TMC17, Liu Gongshen's ACL 2024/2026 and Access 2017, Hua WCSP16, Jin ICCV25, Lu ISci18 all sat under such holds; two of them survive in the build only under a co-author PI). Those 1,283 decisions were removed (ids in scratch/paperfix-1119/released_hold_ids.json); the other 1,112 holds (not on DBLP, other flags) stay. The papers still pass the identity, appointment, affiliation and type gates at the rebuild. One new hold (Orthus, 陈 全): page 1 ties the school only to another author; the builder's page-1 fallback to another author's tie (identity.py, `tie_for_pi(...) or tied.get(...)`) is builder-wide (324 of 12,853 page-1-tied rows in 13 schools) and is left for an owner decision.

**D-0029 Tsinghua namesakes (data; R-PAP-42(a) applied, 2026-11-20).** Tsinghua's gate-9 pi2b precision .900 came from OpenAlex author ids that carry an ORCID absent from every ORCID of the PI's DBLP person record (another person's record, R-PAP-42(a)) yet anchored by a single DBLP-verified work, so the id dragged the namesake's whole cluster into the lab (王会: laser optics and environmental microbiology; 姜宇: planetary dynamics; 刘卫东: partial discharge; 徐枫: fault diagnosis and randomized SVD; 王建民: g-C3N4). The rule was applied to every anchored-only id of the school: 103 ids (83 mixed, 20 not; about 700 anchored rows, 45 PIs) were added to the PI's reviewed `mixed_openalex` or `not_openalex` (evidence per id: the DBLP person record's ORCID and the stored OpenAlex work carrying the other ORCID). A mixed id never anchors (a DBLP-verified work still admits). Two rows the ORCID check cannot reach are held individually: 李国良's mercury-adsorption review (his id carries his ORCID and a second one) and 郑莉's hydrogen supply-chain paper (the DBLP person page itself lists it). ZJU's 30 ids (王锐 A5100431339 and others) are on the unlanded branch `agent/zju-orcid-next-release` for the next release. Test: `test_R_PAP_42_d0029_tsinghua_orcid_conflict_ids_and_holds`. No builder code changed.

**D-0028 SJTU student links (2026-11-20).** Student precision .960 had two causes, recorded as three reviewed exclusions in `hierarchy/sjtu/reviewed/student-link-exclusions.json` (R-LNK, evidence = the stored OpenAlex byline): Zhe Wang (王哲, 孔令和) matched byline 'Zhen Wang' on two papers, because `names.given_conflict` lets a recurring co-author one letter from a lab student stand for the student (a 'roster misspelling'), also under East Asian family names where Zhe and Zhen are different people; and Ruibang Liu (李国强) linked to the published AC4 record whose lead byline lacks him, because `links.link_students` also matches the bylines of the lab paper's EDITIONS (his name is on the SSRN preprint's byline). The builder was not changed. Offline effect of the two causes over all packages (150,783 student links): 107 links kept only by the recurring-variant allowance (89 under East Asian family names; berkeley 23, cmu 30, mit 15, princeton 13, sjtu 9, uchicago 8, stanford 5, toronto 3, oxford 1; many are legitimate preferred-name cases such as Jason Peng = Xue Bin Peng), and 667 links whose matched byline is not on the lead record's byline (stanford 238, berkeley 104, mit 89, cmu 58, michigan 48, hkust 38, princeton 24, sjtu 11, others 1-9). Reported for the next release.

Not changed, and why. The Fleet and Fidler admissions are the deliberate R-PAP-12 (advisee on an unaffiliated byline) and R-PAP-29 (cross-affiliated byline) routes; narrowing R-PAP-29 to single-co-author bylines would drop 235 rows of other schools' genuine joint-appointment papers (Apple/Bigham, Disney/Hodgins ...), so Fidler's `Causal BERT` stays until its page 1 is read (`pi_fulltext_affiliation.py pdf toronto` reads cross-affiliated bylines; R-PAP-29 addendum). Khalil's AAAI-23 New Faculty Highlights, Penn's CHI'18 course and Sanner's SIGIR'25 GENNEXT workshop proposal carry no stored signal (type conference-paper/abstract, research-like titles, no page counts in the DBLP sidecar); they need exact reviewed `not_papers` entries with publisher evidence (R-PAP-39), not a title rule.


### R-HOME-03 (2026-11-25, Cornell homes audit 20 of 50 failed; a general reading of R-HOME-01) — a graduate-field listing never sets the home
A directory row carrying `Faculty (Field) X` or a `CS Field Member` suffix is a graduate-field membership, not an appointment. The home is the `Faculty (Department) X` unit; else the unit the title names ('Associate Professor of Electrical and Computer Engineering', 'Professor; Information Science, CS Field Member', 'Professor ECE, CS Field Member'); the field (here Computer Science) goes to `also`. Where nothing names a unit the row is a `hold` with the note `primary_unresolved`, never the field by default. A title whose "Professor of/in X" is preceded by a donor or chair name ("Laibe/Acheson Professor", "Zak Professor", "Goenka Family Assistant Professor") names a chair, not a unit (`NAMED_CHAIR`), and a title-derived home is accepted only when it matches a known unit (the charter's `census.home_units` aliases); anything else is `primary_unresolved` for review. Reviewed sourced homes (`home_department` + evidence in the census overrides) settle those rows (Cornell: Shmoys = ORIE, You = Chemical and Biomolecular Engineering). Implemented as `profile_home` in `tools/home_departments_school.py`; only rows with a field marker are affected (Cornell is the only school whose stored listing rows carry one: 2,044 rows). Test: `tests/test_home_profile_field.py`. Cornell result for the 159 PIs: Computer Science 150 -> 84, Information Science 0 -> 22, ECE 2 -> 20, ORIE 2 -> 12, MAE 2 -> 5, Statistics 1 -> 5, Mathematics 1 -> 3, and 8 single-unit homes.
A title-derived home must also not be a campus or center (`census.center_units`): 'Cornell Tech' is the New York City campus, so a Cornell Tech professor's home is the department a listing names (Andrea Lodi: ORIE, from the ORIE faculty directory), and a center-only listing whose title names a known unit takes that unit (`title_home_ok`; test `tests/test_home_profile_field.py`).

### R-HOME-02 (2026-11-23, owner D-0048) — a documented first-listed home can settle a joint allocation
For confirmed joint appointments with no stated primary, the owner instructed: “pick one based on what they say on their site or in their publications as their first”. The first department named on the faculty member's owned site or in an authored publication may therefore supply the selected home. This supersedes R-HOME-01's prohibition on source-order selection for these reviewed cases. Preserve the original unit order and all secondary departments. A directory's global department order, alphabetical order, inferred identity or a different author's affiliation is insufficient. Prefer an explicitly stated primary when available.

Record `home_selection_basis = first_listed_site` or `first_listed_publication`, the captured source, verbatim appointment/affiliation quote, subject identity, and `ordered_departments` in source order. The selected home must be the first documented department. Clear the old `primary_unresolved` candidates only after review, keep every former candidate in `also`, and never set `primary_stated` for this selection. `home_basis` retains the first-listed basis, while the allocation is counted as resolved under the owner's selection policy; this is not a claim that a tenure line or formal primary appointment has been established. Faculty-only home records do not change PI eligibility or the lab inventory.

**UW source corrections (2026-11-24; R-PAP-33/38/39, R-LAB-05).** A self-described planned SIG, panel, workshop or course is an event description when its original abstract or primary article page explicitly proposes a discussion or gathering. The reusable source-text check requires event framing; interface panels, longitudinal panel studies and empirical course studies remain research. Sixteen exact UW event claims are independently source-reviewed under R-PAP-39, including cases whose first physical PDF page is only a repository cover. Fourteen research claims from the same short-paper inventory remain eligible. Two Finn records from the 2019 anniversary book are separately reviewed as an older chapter reprint and book front matter; current contributor affiliations do not date the original research.

A former mentee's MIT/Stanford PhD year does not date the mentoring relationship. Explicit mentoring intervals remain usable; current section captures independently establish a current membership point. The old `uw-research-1123` keys were unconditionally emitted collector provenance. Independently reviewed individual records may move to lab-scoped identities while retaining those keys in reviewed provenance; the scientific namesake holds remain explicit. Neither this migration nor same-byte HTTP/HTTPS carrier reconciliation authorizes a global person merge or a completed-PhD inference.

For an explicit current-member section, an undated membership can use the exact original capture year as a single observation point after the normal owner, shared-page, stale-page, departure and faculty-year guards. Original SHA/status and a real capture date are required; this does not create a program start. Archive dates use the archive stamp, including `id_` and `if_`, and never the later retrieval year. Former/alumni sections remain undated without a qualifying relationship date. A numeric last-modified date such as `6/15/2014` is recognized by the existing stale-page rule. An institution initiative is not a person. The UW candidate inventory was independently read before manual additions; disputed current dates and nonpersons remain held.

A retained original PDF can also verify a complete title beyond a truncated citation prefix. The full title must appear on that same source version's title block. Current index metadata cannot replace an older source version's title merely because it is newer. UW's complete 99-proposal title review preserved 96 titles and corrected three exact represented-source titles; the corrected proposal set receives another fresh independent paper round.

**Primary author-layout corrections (UW, 2026-11-24).** Complete, source-bound derived-flag reviews may distinguish literal co-first/second/joint-last-author and equal-advising notes from affiliation markers. Only the recognized contribution statements can be removed from a fully accounted contact tail; a correspondence label cannot hide an institution or unlisted author. For an original without an Abstract heading, a separately quoted complete scientific paragraph may mark the author-header boundary only when its exact full-page text hash and nonoverlapping source rectangle are reviewed. Short/name-only boundaries, affiliation/contact text, duplicate quotes and omitted header content remain held. These layout cases do not change raw work records or PI-paper admission authority.

### R-PAP-66 (2026-11-27, build) — withhold unreliable derived coauthor school flags
A sourced `paper-claim-review` decision `hold_derived_school_flags`, scoped to one school, PI and exact OpenAlex-plus-DOI pair,
withholds the entire derived school-name list on an already eligible claim, including its folded-edition bylines. Empty
means unknown/withheld, not verified absence of school authors. The emitted held evidence names the scope, input hash,
source kind, original URL/hash/quote and reviewer. Partial full-text JATS may justify withholding without certifying a
complete author-affiliation map. Raw byline names, identifiers, PI authorship evidence and normal admission gates remain
unchanged. The hold cannot admit, rekey or merge a paper, waive appointment/identity/genre checks, or block an ordinary
identity anchor. It supersedes competing positive derived flags only on that exact matched claim; a different PI or
unrelated work is unaffected. Prior derivation evidence is retained when present.

**Primary individual-author contradictions (2026-11-27).** If a source review finds that an individual author's
printed affiliation marker or publisher-deposited author-affiliation record contradicts a positive school flag derived
from flattened or combined provider affiliations, record an exact R-PAP-66 hold before publishing that derived list.
The whole list remains unknown until a complete primary mapping is accepted; the contradiction does not reject the
otherwise eligible PI paper. A company or second institution alone is not a contradiction: an explicit primary school
plus company affiliation retains its school-positive interpretation. This rule applies to both physical author-marker
layouts and individual publisher metadata, without inferred person aliases, employment histories or appointment changes.

### R-PAP-67 (2026-11-27, build) — reviewed collaboration uncertainty policy for coauthor school flags
A school may explicitly opt into `derived_school_flags_policy` in its reviewed paper-claim input, separately from exact
R-PAP-66 decisions. Reviewed minimum raw authorship-observation and distinct source-institution-ID counts define a
conservative uncertainty class. They neither prove that unaudited flags are false nor certify smaller records as correct.
Three independently read CMS primary author blocks exposed Riverside/San Diego boundary errors, motivating scrutiny of
large collaboration metadata. Counts, raw source digests, policy provenance and exact affected final claims are reported.
After ordinary identity, school, appointment, genre and edition gates, an unmapped matching claim keeps its paper, PI
authorship evidence, identifiers and complete raw bylines; its entire derived school-name list is explicitly held/unknown.
An empty held list never asserts absence of school authors. A related folded edition cannot restore unreviewed positives.
A complete accepted primary mapping bound to the lead record is retained; other unreviewed transient edition flags clear.
This policy cannot admit, reject, rekey or merge papers, establish individual identities, waive normal gates, or repair an
incorrect PI affiliation. Exact reviewed holds still apply last. Schools without an explicit reviewed opt-in are unchanged.
