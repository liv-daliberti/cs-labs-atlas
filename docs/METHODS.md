# Methods

This document describes how the five-school CS PI-lab hierarchy and the wider atlas were built, the rules that decide
what is in them, the evidence model, and the known gaps. Tool names refer to `code/` (see `code/README.md` for the
order in which they ran).

## 1. Definitions (owner decisions, 2026-10-21 / 22)

- **School → department → PI lab → papers + students → student papers.** Every school is built the same way, by the same
  builder (`tools/pi_hierarchy.py`).
- **PI lab.** One faculty PI plus their advisees. Each PI has exactly one own lab. An existing unit (from the project's
  earlier per-school collection) is reused as the lab only when the PI is its single leader; otherwise a new own lab is
  created (`lab.basis = new_own_lab`) and the multi-leader / umbrella unit stays a *collective*. Names containing
  centre/center, initiative, consortium, program(me), project, cluster or institute (and not lab/laboratory/group) are
  collectives. Collectives are never labs.
- **PI.** A faculty member at the school at some point in 2016–2026 (professor ranks, including research professors where
  the school lets them advise; not postdocs, staff scientists, visitors, or teaching / adjunct / courtesy-only appointments
  without advising) who has stated PhD advising in the window, or who heads their own lab or group. The basis and its
  evidence are in `pi_basis`. Census PIs that review found had no appointment in the window are excluded
  (`excluded_pis.json`).
- **Scope.** All faculty doing CS-related work in any department ("All universities should include all faculty that work
  on CS-related topics / publish in CS venues, even if not in CS"). Operationally: the census of the computing
  departments, plus candidates from any department whose school-affiliated output is substantially DBLP-indexed (8+ school
  works 2016–2026, 5+ and 20%+ of them in DBLP, last author on 30%+ or 30+ works), each reviewed for faculty status, PI
  basis and appointment (`scope_review.json.gz`). DBLP is the computer-science bibliography, so "publishes in CS venues"
  means "has DBLP-indexed papers".
- **Lab paper.** A 2016–2026 work (not a dataset, peer review, erratum, supplement, retraction or similar) where
  1. an authorship matches the PI's name **and that authorship lists the school**: its own OpenAlex institutions
     (including the institution lineage), its raw affiliation strings, or — when OpenAlex recorded no affiliation — the
     paper's own first page (version 1 of the arXiv PDF, or the proceedings PDF) ties the school to the PI;
  2. that authorship **is the PI**: the work is on the PI's DBLP person page (by DOI or title), is a DBLP-verified work
     of the PI in the earlier collection, is on the PI's own institutional publication list or their lab's publications
     page, carries the PI's ORCID or a reviewed OpenAlex author id, has a stated advisee of the PI as co-author, or its
     OpenAlex author id is *anchored* (it sits at the PI's name on works proven by one of the above);
  3. it falls in the PI's **appointment**: inside a reviewed faculty period (boundary years count when supported), or in a
     calendar year for which a captured, dated department faculty listing names the PI (a same-year listing proves that
     year only).

  Editions (arXiv preprint, conference version, journal version) share a normalized title and are one paper; the
  published edition leads and the others are listed in `editions`.
- **Students.** People whose advising record names the PI (thesis records' adviser fields, graduate rosters, alumni
  pages, FPO / defense announcements, lab pages), and members of the PI's own reused unit. Readers, examiners and
  committee members are not advisers. Senior-thesis advising counts for students (never for PI status).
- **Student paper.** A lab paper of the PI with one of the PI's students on its byline: the student's verified authorship
  in the collection (`verified`), or the student's name on an authorship that lists the school, or — within three years of
  the recorded advising — on the byline of the PI's lab paper (`candidate`).
- **Department.** As the site places the PI (`department()` in `scripts/build-cs-hierarchy.py`): a reviewed home
  department (`home_department_review`) when the PI is listed by a computing department but homed elsewhere; at CMU the
  seven SCS departments by code; at MIT EECS; at EPFL the IC school; at Princeton the first listed department. A computing
  department is `department_coverage = full`; other departments are `affiliated` (covered through their CS-related PIs
  only).

## 2. Sources

| layer | sources |
|---|---|
| faculty census | department faculty listings, live and as Wayback captures for 2016–2026 (one row per person-year), faculty profiles, school directories; EPFL people.epfl.ch and Infoscience org units; Berkeley EECS pages |
| appointment periods | arrival / departure statements on profiles, CVs and news pages ("joined Princeton in 2015"), reviewed; bridged periods from consecutive listings |
| PI status | thesis repositories (Princeton DataSpace, CMU SCS reports archive and KiltHub, MIT DSpace, EPFL Infoscience, Berkeley EECS dissertations and technical reports, department thesis lists), graduate rosters, lab pages |
| papers | OpenAlex: every work 2016–2026 with an authorship affiliated to the school (institution lineage), per school; the PIs' own OpenAlex works; DBLP person pages and DBLP's monthly XML dump; the PIs' institutional publication lists; lab publication pages; arXiv bulk PDFs (page 1 only) for affiliation |
| students | thesis repositories and adviser fields, rosters, alumni pages, FPO announcements, lab / group people pages (live and Wayback) |
| home departments | department faculty pages and profiles (reviewed) |
| wider atlas | official university and department directories of research units, unit homepages, reviewed leadership sources, unit bibliographies, OpenAlex / Crossref / Europe PMC metadata |

All fetching honoured robots.txt with per-host delays (typically one request per 2–3 s) and a descriptive User-Agent;
pages blocked by robots or bot challenges were recorded as such, not worked around (Wayback captures were used where the
archive has them).

## 3. Evidence model

Every claim that is not bibliographic metadata carries evidence: the page URL (often a Wayback `id_` URL, which pins the
archived bytes), the SHA-256 of the captured bytes, and a verbatim quote. At build time each quote was checked to be an
exact substring of a whitespace-collapsed text view of the stored capture, and to contain the name it supports. The
captures (SQLite stores of page bytes) are not distributed; the URL and hash let anyone re-fetch and compare.

In this release, quotes were further scrubbed of personal contact details (e-mail addresses, including obfuscated
`name [at] host` forms; phone numbers; office / campus addresses), so a scrubbed quote is no longer a byte-exact substring
of its page: the redaction markers `[email removed]`, `[phone removed]`, `[address removed]` show where. Earlier
collection steps had already replaced some contact fields with `[contact omitted]`.

Identity evidence for papers is recorded per lab on each paper (`labs[].identity`, `labs[].authorship.school_via`,
`labs[].appointment`), so every lab–paper link can be audited: which authorship, which affiliation string, which anchor,
which period or listing.

## 4. Per-school notes

- **Princeton.** The census starts from the 91 own-lab PIs of the earlier collection plus CS faculty (2016–2026
  listings) who advised a PhD student in the window, then CS-related faculty of other departments (ECE, ORFE, Mathematics,
  MAE, Psychology, …). Periods are reviewed arrival statements.
- **Carnegie Mellon.** The seven SCS departments (CSD, MLD, RI, HCII, LTI, S3D, CBD) plus CS-related faculty elsewhere
  (ECE, Mechanical Engineering, Tepper, Heinz, Chemical Engineering, …). Courtesy and adjunct listings do not make a PI
  without advising.
- **EPFL.** The IC school plus CS-related faculty of other schools (STI institutes, SB Mathematics, ENAC, CDM, SV);
  departments are written "School — Institute".
- **MIT.** EECS plus CS-related faculty of other departments (Sloan, Aeronautics and Astronautics, Media Arts and
  Sciences, Mechanical Engineering, Mathematics, Brain and Cognitive Sciences, …); CSAIL principal research scientists
  without an academic department are placed under CSAIL with that note.
- **UC Berkeley.** EECS (the CS and EE divisions) plus CS-related faculty of other departments (Mechanical Engineering,
  IEOR, Mathematics, the School of Information, …). Berkeley has no earlier site collection, so its census and its small
  collection come from its own sweep (`tools/berkeley_census.py`); DBLP person pages were partly unavailable, so the EECS
  faculty publication pages serve as an additional identity anchor.
- **Stanford** is being built by the same pipeline and will appear as `data/schools/stanford/` when its package exists.

## 5. The wider atlas

The atlas is the project's earlier inventory of research units at 300 ranked universities (all fields), with reviewed
leadership, dated activity evidence and linked papers in three views:

- `strict`: a verified PI identity is on the paper with the university's affiliation (PI as last author);
- `reviewed`: the paper is on the unit's own reviewed bibliography (exact identifier match);
- `combined`: either; the atlas's default view.

A unit is in CS scope when its field is `computer_and_information_sciences` or its department matches the computing
pattern in `scope_rule.json`. At the five schools, the atlas's inventory units are replaced by the PI labs of
`data/schools` (`cs_hidden = replaced_by_pi_labs`); `pis.jsonl.gz` `lab.atlas_unit_id` links a PI lab to its atlas unit
when one exists. The atlas's lab-paper rules are older and different from the five schools' rule; use `data/schools` for
the strict PI-lab model.

## 6. Known gaps

- **Papers.** Coverage against the PIs' own DBLP pages (published, non-preprint papers in appointment years) is 82–88% per
  school (`profiles.json` `dblp_reference`). Missing papers are mostly (a) OpenAlex records with no affiliation on the PI's
  authorship and no readable first page, (b) works OpenAlex lacks, (c) papers in years the PI's documented appointment
  does not cover. Venue coverage outside DBLP (e.g. biology, economics) is not measured.
- **Appointments.** Periods are year-granular at the ends; a PI's earliest or latest year can be missing when no listing
  of that year was archived.
- **Students.** Public sources under-represent current students, master's and undergraduate students, and students of
  departments that do not deposit theses; some labs rely on a single roster capture. `candidate` student–paper links are
  name matches (school-affiliated authorship), not verified identities. The same person can have two student ids when
  two labs' sources could not be tied to one record.
- **Student duplicates and missed links.** The packages give one student id per person across a school's labs and
  merge near-duplicate names within a lab; records merged into another keep their old ids in `merged_ids` (and other
  spellings in `aliases`), so older ids can be mapped. An independent audit (`tools/student_audit.py`,
  `data/schools/student_audit.json`) lists what probably still slipped through:

<!-- student-audit:start -->
| | princeton | cmu | epfl | mit | berkeley | stanford |
|---|---|---|---|---|---|---|
| Lab–student pairs | 3,524 | 9,382 | 3,986 | 7,652 | 4,452 | 3,218 |
| Probable duplicate pairs within one lab | 0 | 1 | 0 | 0 | 0 | 0 |
| People under several student ids across labs | 47 | 99 | 13 | 329 | 21 | 13 |
| Papers linked to two ids of one person | 0 | 0 | 0 | 0 | 0 | 0 |
| Students with probably missed paper links | 52 | 298 | 27 | 136 | 124 | 99 |
| Probably missed student–paper links | 189 | 856 | 123 | 541 | 355 | 299 |
| Students with no paper link | 1,927 | 3,699 | 1,481 | 3,638 | 1,346 | 560 |
<!-- student-audit:end -->

  "Students with no paper link" is not an error by itself: many students (undergraduate and master's thesis students,
  recent arrivals) have no lab paper in the window.
- **Zero labs.** A few labs have zero lab papers (e.g. a PI who joined in 2026) or zero students; each has a diagnosis
  and a reviewed verdict in `zero_labs.json`.
- **Atlas.** Inventory depth is uneven across universities (`universities.discovery.coverage_status`); many units lack a
  named leader, papers or people. Some API collection limits are recorded in `atlas_summary.json`
  (`publication_summary.api_collection_blockers`).
- **Metadata** (titles, venues, author strings) is as the sources recorded it; no manual normalization beyond edition
  merging.

## 7. Privacy

No e-mail addresses, phone numbers or office addresses are included; personal homepage URLs of atlas people were
dropped; local build paths were removed. Names, roles, years and advisors are as stated by public university sources.
Corrections and removals can be requested through the repository's issues.
