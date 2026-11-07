# JHU supported partial package

The owner authorized: “lets add what we have / release what we have for washington university,
harvard, and JHU (and then keep working on improving them)?” after asking to get the other
schools through onboarding. This branch prepares supported data for the coordinator; it does
not mark the school released or publish anything.

## Supported package

| Measure | Count |
|---|---:|
| Current listing rows / faculty census records | 146 |
| Supported PIs | 91 |
| PIs with paper rows | 78 |
| PI–paper rows / unique papers | 1,483 / 1,402 |
| Students / lab–student pairs | 36 / 37 |
| Sourced advising relations | 43 |
| Labs with students / student-paper links | 6 / 106 |
| Explicit appointment starts | 10 |
| Positive DBLP anchors / unresolved identity holds | 86 / 5 |

Three saved official CS listings supply 77 main faculty, 46 secondary faculty, and 23
research/visiting/part-time faculty rows in their actual capture year, 2026. The supported
PIs comprise 55 ladder and 36 courtesy faculty. Written titles, real live source URLs,
original fetch dates, raw hashes and exact source quotes remain attached. All 91 PI home
records resolve to recognized units. For explicitly joint titles, home grouping uses the
first named academic unit and preserves the entire written title as evidence.

Ten faculty starts have explicit source support. Hager's automatically extracted 2010 start
was rejected because it dates department-chair service, not his faculty appointment. A
closed assistant-professor rank interval in Chien-Ming Huang's CV is a rank change, not a
departure. The other 81 PIs have only their sourced 2026 listing as appointment support;
no intervening historical years have been inferred.

The saved Chien-Ming Huang CV supplies ten PhD and three postdoctoral advising records,
fifteen master's and nine undergraduate records, plus six doctoral entries explicitly
naming other current PIs as advisers. All 43 admitted relation quotes were rechecked against
the exact saved PDF hash `ffab73bf4988a9871dbf953811883a98669c67c03491ff85427670f51fd16bcb`.
Present resolves to the observation year, 2026. A committee membership alone is not an
advising relation: the six other-PI entries quote their separately named actual advisers.
High-school projects, a visiting scholar advised elsewhere, DEng role normalization,
and advisers outside this partial census remain held.

## Identity and precision review

The 78 automatically selected DBLP IDs, six unique exact-name dump anchors and two direct
homepage matches give 86 positive identities. Jaemin Cho's and Xin Li's official profiles
link to the personal homepages curated on their selected DBLP records. Sparse exact-name
records for Alexis Battle, Gillian Hadfield and Zih-Yun “Sarah” Chiu were also checked against
their official profile research descriptions and matched publication titles. These are
positive anchors, not claims that those sparse bibliographies are complete. Other name-form
candidate PIDs remain unmerged and unclaimed. The reviewed school dump extract is frozen as
`raw/dblp-dump-persons-school.ec099fe19db8822882c08e7124cef8d5e945d52ee88217cfbb65ff413deb87dd.json.gz`.

Alex Marder, Joel Bader, Yiqun Chen, Jennifer Hu and Louis Whitcomb remain unresolved identity
holds. None has a DBLP, ORCID or reviewed OpenAlex anchor in the built package, and all five
have zero attributed papers. A hold does not assert that an identity or publication does
not exist. The student identity audit found zero within-lab, across-lab or same-paper
identity duplicates. Its Jindan Huang / Judy Huang possible missed-link candidate remains
unmerged because the given names differ and no saved alias evidence identifies them.

The deterministic accuracy draw has 90 manually reviewed judgments, compared with the saved
raw OpenAlex author names, identities and affiliations, the source appointment/listing
and the exact CV advising quotes:

| Measure | Result | Wilson 95% interval |
|---|---:|---|
| Uniform lab-paper precision | 25/25 | 86.7–100% |
| Lab-paper precision including strata | 35/35 | 90.1–100% |
| Uniform student-link precision | 25/25 | 86.7–100% |
| Student-link precision including strata | 40/40 | 91.2–100% |
| Lab-paper coverage among judged eligible items | 12/13 | 66.7–98.6% |

Coverage has one real missing paper: Alan Yuille, “Regularizing face verification nets for
pain intensity regression,” DOI `10.1109/icip.2017.8296449`. His raw affiliation names his
own CS department in Baltimore and coauthor Harry Quon explicitly names JHU; this is a
missing R-PAP-25 bare-unit case, not a precision exception. Two other coverage candidates
are explicitly unclear: Yuille's 2019 “Robustness of Object Recognition…” lacks his own
raw affiliation, and Tinoosh Mohsenin's “Metareasoning for Edge-Cloud…” has a DBLP 2026 issue
year against an OpenAlex 2025-09-05 article date and only a sourced 2026 faculty listing.
Those two are outside the judged denominator. There are no thesis/alumni student-coverage
candidates under the current sample protocol; student coverage is unmeasured.

The pre-ledger draw was retained in project scratch. After ledger attachment, the draw was
bound to final copies hashes and all sample keys and populations were verified unchanged.
A canonical rebuild must revalidate those same reviewed keys before rebinding any changed
package hashes. Overlay Git symlinks can produce a misleading dirty provenance flag; no
report flag was manually cleared.

## Availability and visible remaining work

The offline ledger completed at `2026-11-07T05:44:15.342411+00:00`: 1,402 unique non-local
papers comprise **847 found_not_in_catalog** and **555 incomplete_check**. Local copies are
zero. These are cached-source measurements, not exhausted searches. Missing or unperformed
checks remain explicit; no archive or API requests were used for the package/ledger run.
The coordinator owns the finite availability completeness exception and final release.

Historical listing coverage remains incomplete in 42 department-years: CS 2016–2025,
ECE 2016–2026, AMS 2016–2025 and BME 2016–2026. The existing AMS 2026 reviewed gap remains.
The historical source review retains 104 receipts, 33 exact quoted facts and cached URL-era
leads; the shared archive driver owns requests and cooldown handling.

Other open collection includes broader CS-related candidate discovery, systematic lab-page
review, students in 85 of the 91 supported labs, and paper yield for eight positively
identified PIs: Uthsav Chitra, Zih-Yun “Sarah” Chiu, Gillian Hadfield, Krishna Murthy
Jatavallabhula, Murat Kocaoglu, Lydia Zakynthinou, Roy Adams and Jon Donnelly. Zero current
yield is not a claim that those PIs lack publications. The uncollected census, lab-page and
student findings are recorded in gate-exceptions.json with the owner's quotation; each of the eight zero-yield
labs separately has a snapshot-limited papers reason quoting its actual funnel and admitted
2026 listing window in lab-coverage-reasons.json. No unmatched finding, identity, evidence,
schema or precision failure is allowed by the completeness exceptions. Missing lab-page
acceptance is kept missing rather than recording a fictitious accepted review.

Seven secondary-faculty records remain held from PI status pending source-based home/basis
review: Muyinatu Bell, Rama Chellappa, Ralph Etienne-Cummings, Kimia Ghobadi, Michael Miller,
Jerry Prince and Rebecca Schulman. Their written titles remain in the faculty census;
these are not negative faculty or computing decisions.

## Verification and job provenance

The sequential metadata lane was WashU `32137370`, corrected JHU `32137986`, then Harvard
`32137992`; the JHU dump finished before Harvard's scan began. The first JHU job `32137614`
was canceled after exposing inherited main-checkout data-slot variables. Reviewed inputs
remained intact, and the sourced listing/census were restored before resubmission. The
corrected script exports every overlay data slot, verifies the reviewed manifest resolves
to the branch file, and requires at least 146 listing rows. It used two CPUs, 24 GB and a
59-minute limit with the four restricted nodes excluded. No competing archive work ran.
The final audit store imports 110 genuine saved HTTP-200 source captures, retaining their original fetch dates and URLs. Every source and destination
body was independently rehashed; no artificial empty capture database was created. This
satisfies the stage-eight capture preflight while systematic lab-page review remains open.

The institution sweep check passes. Final schema validation has zero violations. Build-time
appointment, listing, student relation, paper affiliation and student-link evidence checks
have zero failures; ledger missing/stale counts are zero, with the measured 555 incomplete
checks preserved. Accuracy sample/verdict/summary files are committed separately from raw
and generated package artifacts. Thirty-seven focused accuracy, stage-gate and live-listing regression checks pass.
The coordinator will rebuild canonically and run the
release-wide checks before making any status or publication decision.
