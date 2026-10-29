# CS Labs Atlas: measured accuracy (2026-10-29)

This file reports a hand-checked accuracy measurement of the six school packages in `work/hierarchy/<school>/`.

The method: draw a fixed random sample (seed 20261029), read the evidence for each sampled item, and record a verdict with a
one-line reason. There are 105 judgments per school and 630 in all. Every verdict is in `verdicts.jsonl`, the figures are in
`summary.json`, the draw is reproducible with `sample.py`, and the figures can be recomputed with `summarize.py`.

## Headline

Precision is measured on the uniform samples, 25 items per school. Coverage is the share of true lab papers (or of students
who have a co-authored paper) that the build has. Intervals are Wilson 95%. *n* counts the judged items in each denominator.

| School | Lab-paper precision | Student-link precision | Lab-paper coverage | Student coverage |
|---|---|---|---|---|
| Princeton | 1.000 [0.867, 1.000] n=25 | 1.000 [0.867, 1.000] n=25 | 0.769 [0.497, 0.918] n=13 | 1.000 [0.701, 1.000] n=9 |
| CMU | 0.920 [0.750, 0.978] n=25 | 1.000 [0.867, 1.000] n=25 | 1.000 [0.785, 1.000] n=14 | 1.000 [0.723, 1.000] n=10 |
| EPFL | 0.880 [0.700, 0.958] n=25 | 1.000 [0.867, 1.000] n=25 | 1.000 [0.757, 1.000] n=12 | 1.000 [0.646, 1.000] n=7 |
| MIT | 1.000 [0.867, 1.000] n=25 | 1.000 [0.867, 1.000] n=25 | 1.000 [0.785, 1.000] n=14 | 1.000 [0.723, 1.000] n=10 |
| Berkeley | 1.000 [0.867, 1.000] n=25 | 1.000 [0.867, 1.000] n=25 | 1.000 [0.772, 1.000] n=13 | 1.000 [0.723, 1.000] n=10 |
| Stanford | 1.000 [0.867, 1.000] n=25 | 1.000 [0.867, 1.000] n=25 | 0.857 [0.601, 0.960] n=14 | 0.875 [0.529, 0.978] n=8 |
| **Pooled** | **0.967 [0.924, 0.986] n=150** | **1.000 [0.975, 1.000] n=150** | **0.938 [0.862, 0.973] n=80** | **0.982 [0.902, 0.997] n=54** |

- **Weighting.** The pooled rows weight every school equally (25 items each). Weighting each school by its number of lab
  papers gives a lab-paper precision of 0.964. Student-link precision weighted the same way is 1.000.
- **Unclear items.** No item was left unclear (0 of 630), so nothing was taken out of a denominator for that reason.
- **The kind of error found.** Every lab-paper error in the uniform samples is a `not_a_paper` record, all at CMU and EPFL.
  None is a namesake, an authorship at another institution, or a date outside the appointment.
- **Meeting abstracts.** These are AGU, APS, ISMRM and journal-supplement abstracts. If the owner counts them as research
  output, pooled uniform precision becomes 0.973 [0.933, 0.990] and CMU becomes 0.960.

## Lab papers

### Precision by stratum

There are 5 items per school in each risky stratum.

| Stratum | Princeton | CMU | EPFL | MIT | Berkeley | Stanford | Pooled |
|---|---|---|---|---|---|---|---|
| uniform | 25/25 | 23/25 | 22/25 | 25/25 | 25/25 | 25/25 | 145/150 = 0.967 [0.924, 0.986] |
| advisee on an unaffiliated byline | 5/5 | 5/5 | 5/5 | 1/5 | 4/5 | 4/5 | **24/30 = 0.800 [0.627, 0.905]** |
| appointment by listing | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 30/30 = 1.000 [0.886, 1.000] |
| identity not a reviewed OpenAlex id | 5/5 | 5/5 | 5/5 | 3/5 | 5/5 | 3/5 | 26/30 = 0.867 [0.703, 0.947] |
| all 40 | 40/40 | 38/40 | 37/40 | 34/40 | 39/40 | 37/40 | 225/240 = 0.938 |

The weakest route is "advisee on an unaffiliated byline". Its errors are not wrong people:

- Four of its six errors are meeting abstracts or a highlights column that reached the lab through that route.
- One is π0, a company paper. The arXiv record carries no affiliations, so the advisee route credited it to Berkeley. The
  paper's first page credits every author to Physical Intelligence.

Appointment by a same-year listing was right 30 times out of 30.

### Coverage

The coverage sample has 15 records per school, 90 in all, drawn from the PIs' own DBLP person pages in DBLP's 2026-09-01
dump. Each record is an article or inproceedings, not a CoRR preprint, dated 2016–2026, and falls inside one of the PI's
periods or listing years. Each record was judged against the lab-paper rule using its OpenAlex authorship, plus the stored
page 1 where needed. It was then matched to the build by DOI or normalized title.

| School | DBLP records drawn | True lab papers | in the build | Not lab papers: absent | Not lab papers: in the build |
|---|---|---|---|---|---|
| Princeton | 15 | 13 | 10 | 1 | 1 |
| CMU | 15 | 14 | 14 | 0 | 1 |
| EPFL | 15 | 12 | 12 | 1 | 2 |
| MIT | 15 | 14 | 14 | 0 | 1 |
| Berkeley | 15 | 13 | 13 | 2 | 0 |
| Stanford | 15 | 14 | 12 | 0 | 1 |
| Pooled | 90 | 80 | 75 (0.938 [0.862, 0.973]) | 4 | 6 |

The build was right to leave out four of the drawn records:

- Heide's Torc Robotics paper.
- Charbon's TU Delft paper.
- Zaharia's Databricks paper.
- Moura's paper published online in September 2015, before his evidenced period.

The six records that are not lab papers but are in the build are seminar reports, workshop proposals, a column, a tribute
and a keynote abstract. They are listed under the failure analysis below.

## Student links

### Precision by stratum

| Stratum | Each school | Pooled |
|---|---|---|
| uniform | 25/25 | 150/150 = 1.000 [0.975, 1.000] |
| within_lab_byline_match | 5/5 | 30/30 = 1.000 [0.886, 1.000] |
| advisee_name_on_lab_paper_byline | 5/5 | 30/30 = 1.000 [0.886, 1.000] |
| full_name_on_lab_paper_byline | 5/5 | 30/30 = 1.000 [0.886, 1.000] |

Every sampled link names the same person as the byline author, 240 out of 240. The variants it handled correctly include:

| Kind of variant | Examples |
|---|---|
| Married names | Murray-Nerger |
| Cut family names | Rafael-Patino; Candela (Garza); Arreguit (O'Neill); 'Bailey Trang' (Nguyen) |
| Nicknames | Tony / Anthony Chen; Fred Callaway |
| Swapped name order | 'Lin Yen-Chen' |
| OpenAlex typos | 'Gonzale Debada' |
| A name split across two byline entries | You Liang Lionel / Wong |

### Coverage

The sample covers 10 PhD advisees per school whose advisor relation has a dissertation or thesis source and a PhD year of
2018 or later.

- Six of the 60 have no co-authored paper with that PI, on DBLP or in the sweep. They are counted in the 60 but kept out of
  the denominator.
- Of the remaining 54, the build links 53 to at least one real co-authored lab paper, which gives 0.982 [0.902, 0.997].

Seventeen candidates were screened out in draw order before the tenth PhD student was reached. They are listed in
`screened.jsonl`:

- 16 at MIT, where the DSpace record of the thesis shows an S.M., M.Eng. or MBA degree.
- 1 at Stanford, a postdoc whose source line also named someone else's dissertation advisor.

## Failure analysis

There are 27 incorrect items out of 630.

| Failure type | Count | Where |
|---|---|---|
| not_a_paper | 20 | 14 in the lab-precision samples (5 in the uniform samples), 6 found through coverage |
| missing_from_build | 5 | Lab-paper coverage: Princeton 3, Stanford 2 |
| not_at_school | 1 | Berkeley, π0 |
| student_not_linked | 1 | Stanford, Izzy Aguiar |
| namesake / outside_appointment / wrong_student | 0 | — |

### Every incorrect item, and whether a general rule could fix it

The rule references in the last column (R1–R10) point to the proposed rules in the next section.

| # | School · sample · stratum | Item | Failure | Reason | Fixable by |
|---|---|---|---|---|---|
| 1 | cmu · lab · uniform | Sarah Fox · W7153821956 | not_a_paper | A CHI 2026 workshop proposal ('Workshop on Developing Standards …') | R1 |
| 2 | cmu · lab · uniform | B. Erik Ydstie · W3111311984 | not_a_paper (abstract) | AGU Fall Meeting 2019 abstract | R2 |
| 3 | epfl · lab · uniform | Ronan Boulic · W2769791602 | not_a_paper | Editorial foreword to a Computers & Graphics special section | R1 |
| 4 | epfl · lab · uniform | Maryna Viazovska · W7221524172 | not_a_paper | Oberwolfach Reports workshop report (the organizers' report) | R1 |
| 5 | epfl · lab · uniform | Mathias Payer · W7127958959 | not_a_paper | Zenodo record of type software (the artifact, not the CLower paper) | R1 |
| 6 | mit · lab · identity_not_reviewed | Bonnie Berger · W2677610438 | not_a_paper | F1000 announcement of the 2017 ISCB senior-scientist award | R1 |
| 7 | mit · lab · identity_not_reviewed | Polina Golland · W2752575772 | not_a_paper (abstract) | Stroke-supplement meeting abstract ('Abstract 136: …') | R2 |
| 8 | mit · lab · advisee_unaffiliated | Elfar Adalsteinsson · W4401572680 | not_a_paper (abstract) | ISMRM meeting abstract | R2 |
| 9 | mit · lab · advisee_unaffiliated | Bonnie Berger · W2605429657 | not_a_paper | 'Principles of Systems Biology, No. 31', a Cell Systems highlights column | R1 |
| 10 | mit · lab · advisee_unaffiliated | William D. Oliver · W3002031535 | not_a_paper (abstract) | APS March Meeting 2018 abstract | R2 |
| 11 | mit · lab · advisee_unaffiliated | Dirk Englund · W2609132648 | not_a_paper (abstract) | APS March Meeting 2017 abstract | R2 |
| 12 | berkeley · lab · advisee_unaffiliated | Sergey Levine · W4404350116 | not_at_school | π0 is a Physical Intelligence paper; page 1 credits Levine and Kevin Black to the company only | R3 |
| 13 | stanford · lab · identity_not_reviewed | Aviad Rubinstein · W2950014110 | not_a_paper | One of 16 chapters of his 2019 ACM Books monograph kept beside the book; the chapters have no venue, so the fold rule missed them | R4 |
| 14 | stanford · lab · identity_not_reviewed | Anshul Kundaje · W7204929729 | not_a_paper | A 2026 Stanford dissertation by Minji Kang; Kundaje is her adviser in the catalogue byline, not an author | R5 |
| 15 | stanford · lab · advisee_unaffiliated | Kawin Setsompop · W4401571924 | not_a_paper (abstract) | ISMRM 2023 meeting abstract | R2 |
| 16 | princeton · coverage | Naveen Verma · conf/iwasi/Verma17 | not_a_paper (abstract) | One-page IWASI 2017 keynote abstract, in the build | R2 |
| 17 | cmu · coverage | Ken Koedinger · conf/lats/ThomasDKMPRSTK25 | not_a_paper | L@S 2025 workshop proposal, in the build | R1 |
| 18 | epfl · coverage | James Larus · journals/cacm/Larus22 | not_a_paper | 'CACM community', a one-page CACM column, in the build | Partly (R1 cannot see columns reliably) |
| 19 | epfl · coverage | Mathias Payer · journals/dagstuhl-reports/ChisnallGHP21 | not_a_paper | Dagstuhl Seminar 21481 report, in the build | R1 |
| 20 | mit · coverage | Joel Emer · journals/micro/BurgerCEHHM25 | not_a_paper | 'Derek Chiou', an IEEE Micro tribute, in the build | R1 (title is only a person's name) |
| 21 | stanford · coverage | Mykel Kochenderfer · journals/dagstuhl-reports/0001KKTG24 | not_a_paper | Dagstuhl Seminar 24361 report, in the build | R1 |
| 22 | princeton · coverage | Prateek Mittal · conf/nips/BhagojiCM19 | missing_from_build | NeurIPS 2019 with his student Bhagoji. Mittal's only affiliation is 'Center for Information Technology Policy', and the roster spells the student 'Arjun Nitin Nitin Bhagoji' | R6 + R7 |
| 23 | princeton · coverage | Prateek Mittal · journals/iacr/PatlanSHMV25 | missing_from_build | OpenAlex has no record of 'AI Agents in Cryptoland' (arXiv 2503.16248) | Partly (R8) |
| 24 | princeton · coverage | Ronnie Sircar · journals/siamrev/ChanS17 | missing_from_build | Sircar's only affiliation is 'Operations Research & Financial Engineering'; co-author Patrick Chan (his PhD) is not on the roster | R6 |
| 25 | stanford · coverage | Jacob Fox · journals/jctb/FoxPS25 | missing_from_build | OpenAlex gives Fox no affiliation and the paper has no advisee | R8 |
| 26 | stanford · coverage | Barbara Engelhardt · conf/ml4h/MandyamJYLE23 | missing_from_build | ML4H 2023 with her student Mandyam. The only OpenAlex record is dated by its October 2021 arXiv v1, before her 2023 Stanford period | R9 |
| 27 | stanford · student coverage | Johan Ugander · ext:stanford:izzy-aguiar | student_not_linked | Three lab papers byline 'Izabel Aguiar'; Izzy and Izabel are not a known nickname pair, so the given-name guard blocks the link | R10 |

### Proposed rules

These are proposals only: no code or data was changed.

- **R1 Non-research record types and titles** (fixes 1, 3, 4, 5, 6, 9, 17, 19, 20, 21).
  - Drop OpenAlex type `software`.
  - Drop records whose venue is `Oberwolfach Reports` or `Dagstuhl Reports` (DOI prefix `10.4230/dagrep`).
  - Drop records whose title matches:
    - `^(Foreword|Preface|Editorial|Guest editorial|Introduction to the special)`
    - `\bAward\b.*:` or an `Award` announcement in F1000/ISCB
    - `, No\. \d+$`, which marks highlights columns
    - `^Workshop on ` or `: A (Collaborative )?Workshop`, which marks CHI and L@S workshop proposals
  - Drop records whose title is just a person's name (tributes and obituaries).
  - One-page columns (item 18) need page counts. OpenAlex `biblio` first and last page is a usable signal for CACM and IEEE
    Micro.
- **R2 Meeting abstracts** (fixes 2, 7, 8, 10, 11, 15, 16). These depend on a policy decision. If the owner does not count
  meeting abstracts as papers, drop type `conference-abstract` when one of these holds:
  - the venue is a meeting-abstract series (AGU Fall Meeting Abstracts, Bulletin of the American Physical Society,
    Proceedings ISMRM with DOI prefix `10.58530`);
  - the title starts `Abstract \d+:`;
  - the abstract is a single-author keynote of one page.

  The seven abstract items would otherwise count as correct; see the headline note on meeting abstracts.
- **R3 Check page 1 before the unaffiliated-advisee route** (fixes 12). For an unaffiliated arXiv record, run the existing
  page-1 reader (`tools/pi_fulltext_affiliation.py`) first. Refuse the advisee route when page 1 credits the PI only to
  another institution.
- **R4 Fold book chapters without a venue** (fixes 13). Extend the 2026-10-29 fold rule:
  - group chapters by the book's DOI prefix (for example `10.1145/3241304.*`) or by OpenAlex's host book;
  - fold them into the book's own record when the lab has one, as it does here.
- **R5 Dissertations are not the adviser's papers** (fixes 14). Drop type `dissertation` from a PI's lab. Stanford Digital
  Repository bylines list advisers and readers, sometimes with life dates such as `Kundaje, Anshul, 1980-`.
- **R6 Bare unit names as the school** (fixes 22, 24). Count a PI's raw affiliation as the school when it names only a unit
  that the school's census lists (a department, centre or program). This extends the 2026-10-29 rule about the school's own
  units that contain institution words.
- **R7 Clean doubled name tokens in the roster** (part of 22). 'Arjun Nitin Nitin Bhagoji' should become 'Arjun Nitin
  Bhagoji', so that the advisee and student matchers see the student.
- **R8 DBLP-anchored works with no PI affiliation** (fixes 25, and 23 only if a record exists).
  - Run the page-1 reader on DBLP person-page works whose OpenAlex authorship gives the PI no institution.
  - Optionally, build a row from a DBLP record with no OpenAlex match when page 1 shows the school. The build already makes
    such DBLP-key rows; Hazan `ChenH24` and Jiajun Wu `DingZ0T24` are two.
- **R9 Date by the venue version** (fixes 26). When OpenAlex has only a preprint record but the PI's DBLP page has the venue
  version (same title, later year), use the later date for the appointment check. This applies only if the PI's affiliation
  names the school.
- **R10 Nickname table** (fixes 27). Add `izzy ↔ isabel / izabel / isabella` to `hierarchy/nicknames/extras.csv`.

### Problems found outside the scored criteria

These problems are recorded in the reasons and flags but were not scored as errors:

- **Misdated row.** CMU, Sandholm, W2113405756 (`date_wrong`) is a 2018 KiltHub deposit of a 2009 IJCAI paper. It is still
  inside his period, but it is dated 2018.
- **Wrong title and DOI.** Stanford, Manning, W3011573503 (`metadata_wrong`). The row carries the title and DOI of an
  unrelated SLATE 2023 paper, while the live OpenAlex record is Stanza (arXiv 2003.07082). The lab membership is right.
- **Duplicate student record.** At MIT, Harrell's lab holds the same person twice: Pablo José Ortiz-Lampier (the thesis
  record, with no links) and Pablo Ortiz (`ext:mit:pablo-ortiz`, with 5 links). A within-lab merge would fix it: the given
  name matches, and one family name is half of the other's hyphenated family name.
- **Reused person id.** At Berkeley, `berkeley_fac_john-wright`, the faculty member's id, is the id of the hardware PhD
  student John Wright (Nikolić lab).
- **Student in the wrong lab.** At Stanford, Shirley Wu sits in James Zou's lab, but her thesis source names Leskovec as her
  adviser.
- **Rows met through the student sample that are not papers.**

  | School | Row | What it is |
  |---|---|---|
  | CMU | W4255267968 | protocols.io protocol |
  | CMU | W3136338351 | JST machine-translated record of the OpenPose paper |
  | MIT | W4310263535 | Publisher Correction |
  | Berkeley | W7128768787 | Figshare supplement |
  | Stanford | W7139980406 | Zenodo software |

  R1 together with existing erratum and translation handling would catch these.

## Provenance and method

- **Date and seed.** 2026-10-29. Seed 20261029, with `random.Random(20261029)` reset for each school.
- **Draw order.** The draw is consumed in this order: lab uniform, then the three lab strata, then student uniform, then the
  three student strata, then coverage, then the student-coverage shuffle. `sample.py` documents this order.
- **What the draw read.** The package files listed below, the 13:40 build, plus `hierarchy/dblp-dump-persons.json.gz`
  (extracted from DBLP's 2026-09-01 dump).
- **Later rebuild.** Another process rebuilt the Princeton, CMU and EPFL `students.json`, `lab_papers.jsonl.gz` and
  `student_papers.jsonl.gz` at 14:06–14:16, after the draw. The rebuild left the row counts and every sampled row key at the
  same position unchanged. The verdicts are tied to the hashes below; the later hashes are recorded in `summary.json` →
  `notes`.
- **Judgment criteria.** These are the task's definitions, read against `tools/pi_hierarchy.py`, including the 2026-10-29
  rules on given names, transition years, books and initials.
  - A lab paper is correct when three things hold: the PI is the author; the record is a research output; and the work was
    done at the school during the evidenced appointment or in a year with a department listing.
  - A student link is correct when the student record and the byline author are the same person. Whether the student is
    really that PI's advisee is not part of this measure.
  - Meeting abstracts are judged `not_a_paper` and carry `policy: meeting_abstract`, so that either policy can be reported.
  - Preprints, technical reports, reviews, research chapters, software papers in journals and consortium papers count as
    research output.
- **Evidence.** The evidence used, in order:
  - the row itself (authorship institutions, raw affiliations, school_via, identity, appointment);
  - whether the work is on the PI's DBLP person page (DOI or title);
  - the period and listing years in `pis.json`;
  - the student records, their sources and quotes in `students.json`;
  - for coverage: the OpenAlex API (by DOI, else title search), cached in `cache/openalex.jsonl`;
  - the stored PDF page 1 (Stanford OmniRe);
  - the MIT DSpace item API for thesis degrees, cached in `cache/mit-dspace-degrees.json`.

  No paywalled, login or dblp.org pages were used.
- **Files.**
  - `sample.py`: the draw.
  - `evidence.py`: compact evidence sheets.
  - `oalookup.py`: OpenAlex lookups for coverage.
  - `record.py`: appends verdicts.
  - `summarize.py`: builds `summary.json`.
  - `verdicts.jsonl`: 630 lines.
  - `screened.jsonl`: 17 lines.
  - `sample.json`: the draw, with the file hashes.
  - `summary.json`.

### Package sha256 (the measured 13:40 build)

| School | File | sha256 |
|---|---|---|
| princeton | `pis.json` | `8c34bee8c541aa6dc9b891ced54e26a66a1eaba15b9babb66874828b67777cdf` |
| princeton | `students.json` | `d82ac04a99ce8a66687fef61963e994cbe0c3ed6e1917b804ed33ea93946d0b5` |
| princeton | `lab_papers.jsonl.gz` | `3cc0a295a6930802d0edfa8b3f5b4fbc429db4af9308a8e1b2d588aa7b191ccf` |
| princeton | `student_papers.jsonl.gz` | `941a877e543bbd360fe91ec9b7bb5745141d5f45831c9e68b1b8300dab49f2f6` |
| princeton | `copies.json` | `cda57a19be7a5d4eae0289e82461b0109396b7300b7e2bb0fbbfc45918ebd21e` |
| cmu | `pis.json` | `a1fd910ac587bec694425ac90295e24a0abf23dc293c0aac80a9b467cd7e79ef` |
| cmu | `students.json` | `6ac5eca93bca9da351c110bb12136e1b9d8955cb1141eaff2f0b6d42a3bc0163` |
| cmu | `lab_papers.jsonl.gz` | `a7d89af6b998cc86fa2b46d2df5f9799df8e38d72e51cba3dfaf9b3e69415b1d` |
| cmu | `student_papers.jsonl.gz` | `afb767de3584fde09a16a96184f3931524cf5dfdabbfed651ba5e671b7ea6032` |
| cmu | `copies.json` | `57fa891801dc88186093b784cc19bcaeedb473af62b0c7a2dcb6a127c94fcb37` |
| epfl | `pis.json` | `a670f8b05aa44083e5e9e8d2504d8160c52159a131645c4d238acea49852778c` |
| epfl | `students.json` | `f0e80a9bacf4d1819cd633a9a263728b332ac59810891298e74686b21de529b3` |
| epfl | `lab_papers.jsonl.gz` | `a1bb1205a8193789fea9e86b56c29063f206dbee5701808af2be24216d66c3ba` |
| epfl | `student_papers.jsonl.gz` | `ed50bfd3c6b9f2840d29a0374240ea5e091e155845237aeee9a5aa9e17b1fb71` |
| epfl | `copies.json` | `44f576407724d0340d1a43ac2e3ba317f23cf006e90faa848070d5a8ed3f2c23` |
| mit | `pis.json` | `71bc5024f954235145e9df9ab9378dcc1aa93a15783e55999e13dcecf86f8b3d` |
| mit | `students.json` | `64ab9e2c2da99f1e0f30f4184e6b617330efc01568da6b2ee4be73732418c159` |
| mit | `lab_papers.jsonl.gz` | `66fc4792669bd51c48a612f2906ba572e9673d3e3d1f089941ea960feb8ccc6e` |
| mit | `student_papers.jsonl.gz` | `a9ff242b9f795cb1287a0ff380cbdb429b238aa7e7418d2744bfa28f1874b803` |
| mit | `copies.json` | `6053e5f0e89d32ae39fa6dd7c784510ff777686ec2b5eac4de0637eba1a4824c` |
| berkeley | `pis.json` | `c7b4e78508c5fec8692d229a9e6e884f6d5734534dd0af8a548188c61867a2ee` |
| berkeley | `students.json` | `8a9ec1476e1e208634c56b93cc65608606f7e4dadbe1c418e9bd5b0b80817482` |
| berkeley | `lab_papers.jsonl.gz` | `0218c6422e4735e3add677dcd7eae7115079f9f1c4876ffc8d14d2feede2b80a` |
| berkeley | `student_papers.jsonl.gz` | `9051a931eb7367cf60c3cd7aaca88783ff002fe136165152c06690b01ba4c1bd` |
| berkeley | `copies.json` | `79cd24482ba7e5c2c627b93cf10c4c4dd27ea59d446310a69b7ca324a66376ad` |
| stanford | `pis.json` | `ee16bd74f68502566a1a5f0f0c6b854d1ea063edb30e7a8f82acd0dcfdcef3db` |
| stanford | `students.json` | `7c9018f632348e6a3ff62e096e7f9e8c9d1bf1543134aa64470c969ba2695efc` |
| stanford | `lab_papers.jsonl.gz` | `50d1491b59c94ec80a2af5e8e6c506f6014df42d94906bc50b101fdaff795cbe` |
| stanford | `student_papers.jsonl.gz` | `1f70b7a89e3d0094534d7d2760824f9688bee4e357d4b596b14250aa072dbe23` |
| stanford | `copies.json` | `4faa6ca02a91dd494dc8a3cdc058b96d200ed4e3f11b4e607487ff719b0f9987` |
| (all) | `hierarchy/dblp-dump-persons.json.gz` | `6e86d6a14d0086adbb3a9085d1029a5204bf240709a6b14f6349a32913591831` |
