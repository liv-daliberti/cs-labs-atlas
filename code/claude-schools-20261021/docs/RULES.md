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
`listings_after_move`.

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
