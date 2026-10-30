# Build rules

The rules `tools/pi_hierarchy.py` (and the audits) apply, with the date each was decided. Each rule has a stable id;
`tools/make_release.py` copies this file into every release and lists the ids in the release `MANIFEST.json`. The code
comments next to each rule carry the cases that motivated it; `tests/` holds those cases as tests.

Format: `### <id> (<date>, <who>)` then the rule. "owner" is a decision by the project owner; "owner: best judgement" is
one the owner delegated; "build" is a fix found while building.

## The hierarchy

### R-HIER-01 (2026-10-21, owner)
School → department → PI lab → papers + students → student papers. Every census faculty member with `is_pi` gets one
own lab (the PI and their advisees). A census lab unit is reused only when the collection unit has this PI as its single
leader; otherwise a new own lab is proposed and the multi-leader or umbrella unit stays a collective, not a lab.

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

### R-PAP-17 — not papers
Datasets, paratext, peer reviews, errata, supplementary materials, grants, standards, retractions, reference entries
and library guides are not papers (`NOT_PAPERS`).

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
Per-pattern counts and ten samples each on the 2026-10-29 build: `docs/not-paper-patterns-20261029.md`. One-page columns
('CACM community') are not caught (no page counts). OpenAlex type `editorial` alone is not dropped (127 such rows have
research-like titles). Report: `not_paper:<tag>`, samples in `notPaperSamples`.

### R-PAP-19 (2026-10-29, owner: accuracy sample) — meeting abstracts are not papers (R2)
Dropped (`meeting_abstract:<why>`): a meeting-abstract venue (AGU Fall Meeting Abstracts, Bulletin of the APS, APS
Division/March Meeting Abstracts, ECS Meeting Abstracts, ISMRM proceedings, EGU General Assembly); a supplement or
meeting DOI (`10.58530/` ISMRM, `10.5194/egusphere|epsc`, `suppl`/`supplement`, AACR `.am20xx`, ECS `/ma20xx`, ASH
`blood-20xx-`, `meetingabstracts`) on an abstract, article or other record; a title `Abstract 136:`; type
`conference-abstract` in a journal's meeting supplement (Cancer Research, Circulation, Blood, Stroke, JCO, JASA, Academy of
Management Proceedings, ...); a single-author `conference-abstract` (keynotes and invited talks, IWASI 2017 'Covering
our world with sensors'), unless the PI's DBLP page lists the same title with co-authors (OpenAlex cut the byline); and
a `conference-abstract` titled as a keynote or invited talk. CS conference abstracts with co-authors (EC, FPGA, SIGCSE,
CHI EA) stay. Reversible per school: the report counts every `not_paper:meeting_abstract:*` tag.

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

### R-PAP-25 (2026-10-29, owner: accuracy sample) — bare unit names (R6)
A PI authorship with no institution whose raw affiliation strings are only unit names counts as the school when, for
every string: a generic name every school has ('Computer Science'; all words discipline words, `generic_unit`) is the
PI's own unit and another author on the byline lists the school; a name only this school has is the PI's own unit (a
census department, or a unit the PI's school-affiliated strings name on 2+ works) with an anchored identity or a school
co-author ('Operations Research & Financial Engineering', Sircar), or any unit of the school (census departments,
collection units, units seen on the school's strings) with a school co-author ('Center for Information Technology
Policy', Mittal with Bhagoji). `bare_unit_school`, `school_via_bare_unit`.

### R-PAP-26 (2026-10-29, owner: accuracy sample) — date by the venue version (R9)
A preprint or repository deposit (type preprint, an arXiv DOI, or a repository as primary source) whose normalized title
is a venue publication on the PI's DBLP person page (not CoRR, ECCC or IACR ePrint) is dated by that record's year, the
earliest if several, for the appointment check and the row's year (`dated_by`: the OpenAlex date and the DBLP key).
Engelhardt's ML4H 2023 paper had only its October 2021 arXiv record; Sandholm's IJCAI 2009 paper was a 2018 KiltHub
deposit. A venue version from before the atlas window (2016) takes the row out (`dated_before_window`): a later deposit
or preprint of an older paper is not a lab paper of 2016-2026. `venue_version_date`.

## Students

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

## Student–paper links

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

### R-LNK-05 (2026-10-29, owner) — links carry their evidence
Every byline link (`within_lab_byline_match`, `byline_name_with_school_affiliation`, `advisee_name_on_lab_paper_byline`,
`full_name_on_lab_paper_byline`) carries the work id, the exact byline string matched (`byline`) and the student's own
roster source (`relation_source`: relation type, url, sha256, quote); every link carries `relation_source`. Evidence
items with url, sha256 and quote are preferred when a relation or period keeps two; MIT's collection writes the quoted
sentence as `statement`, which becomes the quote (`best_sources`).

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

### R-ID-04 (2026-10-29, owner) — joining works
Rows sharing a work anchor, editions included, are one work across labs and schools; two rows of one lab are never one
work (they join only through their own lead record).

### R-ID-05 (2026-10-29, owner) — everywhere
The ids are written by the rebuild stage `ids` into the packages, copied into every release with the registry and the
cross-reference table, and carried by the tree, the GitHub export and the site handoff; `make_release.py` refuses a
package without them.
