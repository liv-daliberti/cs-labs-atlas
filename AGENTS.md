# Research atlas attribution rules

For current release preparation and publication, use `docs/PUBLISHING.md` and
`python3 scripts/release.py`. The same commands and receipts apply to people,
CI, ChatGPT and Claude. Do not recreate the workflow in chat or one-off scratch
scripts. Historical checkpoints below retain attribution decisions; they do
not replace the current release runbook.

These rules apply to every collection, import, graph projection, map, count, search
result, and export in this site. They were explicitly requested by the owner.

- Keep person–paper authorship separate from person–lab membership and paper–lab
  attribution. A roster, degree advisor, or current employer must never assign a
  person's entire publication history to that lab.
- Default lab papers require a verified PI AUTHOR on that exact paper, evidence
  of the PI's faculty appointment at publication, and a supported connection to
  that lab during that appointment. A thesis-advisor or acknowledgment role is
  not authorship and cannot qualify a default lab paper (owner update 2026-10-19).
  University appointment dates and lab leadership dates are separate claims.
  A source's observation year, graduate affiliation, current leader listing or
  personal bibliography cannot establish a historical faculty/lab interval.
  (Owner decision 2026-10-21: a captured department faculty listing proves the
  appointment for papers from its own calendar year; see "department listings".)
  Imprecise boundary dates stay unresolved unless paper-specific dates resolve
  them. Retain other personal works and advised works outside default lab totals.
- Consolidate alternate names only with explicit identity evidence, such as the
  same independently verified personal profile or institutional identifier.
  Keep source names, receipts and redirects so old person links still resolve.
- Resolve attribution separately for each paper and each lab. Preserve the
  appropriate PI/lab's paper connection when another lab's inferred link is
  withheld. Multiple supported lab attributions are allowed; never infer an
  exclusive lab from the person's current position.
- Retain papers on their authors' own records even when no lab attribution is
  established. Keep such work unassigned to a lab. Missing evidence means
  attribution is unresolved, not that the paper or authorship should be deleted.
- A shared paper may establish a paper-specific collaborator context. Do not
  turn coauthorship into formal membership, employment, or an advising claim.
  Keep sourced roster entries and dated memberships independent.
- Publication-time affiliation still needs its own evidence. A PI name alone
  does not prove the paper was written at their present institution or lab.
- Preserve original source observations and rejected/withheld links for audit,
  but exclude unsupported lab links from visible lab papers, connection graphs,
  totals, copy counts, searches, and current CSV exports.
- Imports must run the same paper-specific attribution checks before they enter
  the live projection. Frontend filtering is a defensive check, not a substitute
  for correcting the projection. Rebuild summaries/exports after changing links.
- Never use a missing author-ID match as evidence that someone is absent from
  the paper. Check saved primary bylines and reviewed identity evidence. Do not
  promote a name-only candidate into verified authorship.

Regression example: “Behavior-Consistent Deep Reinforcement Learning”
(arXiv 2605.21214; paper_daca0ec4b9ee5602f546) names Liv G. d'Aliberti and
Benjamin Eysenbach. It belongs with Ben's papers and Liv's own research record.
It must not appear in Manoel Horta Ribeiro's Humans and Machines Lab papers.
Liv's HML roster record remains; her Ben connection is a paper-specific
collaboration unless independent membership/advising evidence is collected.

Implementation: scripts/reconcile-lab-identities-periods.py and
scripts/project-lab-periods.py build the dated PI projection from the frozen v109
baseline and reviewed evidence. Review/rebase their inputs before a later refresh;
do not replay an older frozen import over newer evidence. The earlier
enforce-advisor-attribution.py lacks the faculty/lab date gate and must not replace
the current projection. atlas/assets/advisor-attribution.js also checks the
accepted edition's year. Run the date, identity and attribution regression tests
before publishing.
Broader collections must follow these same rules when collecting/rebuilding
attributions; do not treat an older unreviewed association as a new verified link.

Department roster and outside advisors:
- Keep every sourced student record visible under the student's department even
  without a publication-index identity, known advisor, or laboratory membership.
- Store academic advising as its own relationship. Preserve each source's year;
  different advisors in different years do not prove simultaneous co-advising.
- Record an outside advisor's actual home department/institution with its source
  and observation date. Never backdate a present affiliation to historical work
  or manufacture a CS lab for a non-CS advisor.
- Verify individual works through exact repository records or a named official
  roster-to-owned-publication-to-primary-byline chain when possible. Missing
  bibliographic identities stay unresolved; index candidates are not authorship.
- Update department views, person records, typed graph relations, review queues
  and downloadable exports together. Retain source receipts locally.

Preserve the CS structure checkpoint described in
`research/cs-structure-20261016/README.md` during future collector refreshes.
Reconcile current source-bound person/work and advising observations, exact paper
roles, held identities, and checked local-copy aliases before replacing exports.
The frozen import baseline is for reproducibility, not an overwrite of newer data.

CMU/EPFL people checkpoint (2026-10-19):
- Preserve the additive import and per-lab map projection recorded in
  `research/university-people-repair-20261019/`. The repair script uses frozen
  v110 inputs for reproducibility; rebase before running it against later work.
- Non-Princeton atlas rosters are loaded through each unit's `peopleFile`.
  Keep those shards, collection memberships, department filters and exports in
  sync. Zero eligible lab papers must not hide sourced students.
- Shared directories and faculty pages mentioning students are not individual
  profile identifiers. Keep unresolved named source observations visible without
  transferring an existing person's publications to them.
- Degree-program start/end dates are not lab-membership or advising intervals.
  Actual roster, source-specific advising and paper-collaborator contexts retain
  distinct types. New authorship alone never qualifies a lab paper.
- Run `scripts/test-university-people.py` with the date/identity/attribution
  regressions after changes to these collections or their map adapter.

MIT checkpoint (2026-10-19):
- The additive MIT importer/projector uses the v111 checkpoint under
  `.research-sweeps/mit-cs-deep-20261019/baseline`. Rebase before later refreshes;
  never replay it over newer collection or reader data without reconciliation.
- Frozen roster/bibliography evidence and repository metadata remain in that
  stage folder. Repository and bibliography PDF downloads are resumable and
  may finish after publication. New bytes require validation and a new reader
  snapshot before becoming visible on the website.
- MIT repository association is not publication-time institutional affiliation
  or a CS classification. Preserve actual degree departments and literal adviser
  lists; compound adviser text is not a single identified PI.
- Personal bibliography, shared group bibliography and commentary references
  have separate source-ownership classifications. Apply those classifications
  to PDF-only discoveries as well as DOI/arXiv citations.
- Keep arXiv editions separate from publisher editions even when arXiv metadata
  cites the journal DOI. Run `scripts/test-mit-cs.py` alongside existing people,
  date/identity, attribution, collection and storage regressions.

MIT lab-by-lab checkpoint (2026-10-19):
- `scripts/deepen-mit-labs.py` adds reviewed lab evidence to the immutable v112
  baseline under `.research-sweeps/mit-cs-lab-audit-20261019/baseline`. It supersedes
  replaying the first MIT import. Rebase again before any subsequent refresh.
- Run `scripts/project-mit-cs.py` with `MIT_STAGE` set to that lab-audit stage,
  followed by `scripts/build-mit-lab-audit.py`. The normal projector default still
  points to the older stage and must not be used for a later refresh.
- A reviewed lab can retain unresolved identities, dates, rosters or papers.
  Preserve its findings and gaps; the audit status does not certify exhaustive
  historical coverage. The audit page and CSV cover the 101 inventoried groups.
- `scripts/test-mit-deep-dive.py` checks additive preservation against v112 and
  supersedes the earlier MIT baseline test for this release. Run it alongside
  the existing university-people, faculty/lab period, attribution, collection,
  browser and storage checks. Preserve earlier reader mappings exactly.

Claude arrivals checkpoint (2026-10-19):
- `scripts/integrate-claude-arrivals.py` and `project-claude-arrivals.py` use the
  immutable v113 baseline in `.research-sweeps/claude-wrap-20261019/baseline`.
  Rebase before future refreshes. Preserve the additions and frozen evidence
  described in `research/claude-wrap-20261019/README.md`.
- New catalogue records without independent primary proof remain candidates;
  they must not inherit lab attribution from search terms or PI names.
- `scripts/test-claude-arrivals.py` supersedes the prior MIT deep-dive test's
  cross-university byte-equality requirement for this additive release. It keeps
  MIT byte-identical and checks all prior works, authorships and reader mappings.
- Preserve advising-only people without assigning a lab. Canonical person merges
  must union dated graph evidence rather than overwrite an older observation.

Sequential MIT checkpoint (2026-10-19):
- `scripts/integrate-mit-sequential.py` uses the immutable v114 baseline in
  `.research-sweeps/mit-sequential-20261019/baseline`. Rebase before replaying
  against a later release. Preserve other schools and existing reader mappings.
- The deeper pass is genuinely sequential: ANA is reviewed with recorded gaps;
  the other 100 groups remain queued. Earlier source-review labels do not mark
  them complete in this pass. Preserve `research/mit-sequential-20261019/progress.json`.
- ANA staff leadership does not satisfy the owner's faculty PI requirement.
  Its personal works and thesis advising are accessible without granting default
  lab eligibility. The explicit all-personal-works view must remain opt-in.
- Run `scripts/test-mit-sequential.py` and the existing attribution, identity,
  university-people, collection, storage and browser checks before publication.

Algorithmic Alignment checkpoint (2026-10-19):
- `scripts/integrate-mit-alignment.py` uses an immutable v115 baseline under
  `.research-sweeps/mit-alignment-20261019`. Rebase before a later refresh.
- ANA and Algorithmic Alignment are the two reviewed groups in the sequential
  pass; 99 remain queued. Keep the shared sequential progress file current.
- The AAG dossier preserves 22 identity redirects, source-owned name variants,
  thesis advising, and two additional individually sourced research members.
  Personal publication counts include other institutions and advising-only theses;
  they must not replace the separate eligible-lab counts.
- Run `scripts/test-mit-alignment.py`, `scripts/test-mit-sequential.py`, and the
  existing date, people, attribution, collection and storage checks after changes.

PDOS sequential checkpoint (2026-10-19):
- `scripts/integrate-mit-pdos.py` uses the fresh immutable v116 baseline in
  `.research-sweeps/mit-cs-lab-by-lab-20261019/baseline`. Rebase before replaying.
- ANA, Algorithmic Alignment and PDOS are reviewed with gaps; 98 groups remain
  queued. Continue one MIT CS lab at a time. Preserve the shared progress file.
- PDOS paper bytes live in `research-library/mit-cs/pdos/` in the workspace.
  New copies are local only. Do not add them to the hosted reader registry
  or upload PDFs without a later user request. Preserve previous reader mappings.
- The PDOS roster is stale for Henry Corrigan-Gibbs, Alexandra Henzinger, Ariel
  Szekely and Ryan Lehmkuhl. Preserve newer individual-profile observations,
  Henry's 2020–2025 MIT faculty interval, source conflicts and historical records.
- Keep the 374-entry bibliography separate from eligible 2016–2026 lab records.
  Theses, PostScript files and title-review holds have explicit distinct statuses.
  Existing edition candidates must not create new counted duplicate lab records.
- Run `test-mit-pdos.py`, the alignment/sequential tests, and existing people,
  date/identity, attribution, collection and storage checks before publication.

Algorithmic Design sequential checkpoint (2026-10-19):
- `scripts/integrate-mit-adg.py` uses the immutable v117 baseline in
  `.research-sweeps/mit-algorithmic-design-20261019`. Rebase before any replay.
- Four groups are reviewed with gaps: ANA, Algorithmic Alignment, PDOS and ADG.
  Preserve the shared progress file; 97 groups remain queued.
- The ADG dossier has 21 roster observations and 38 catalogue records. Its local
  archive is `research-library/mit-cs/algorithmic-design/`; new paper bytes remain
  local only. Preserve existing hosted readers and the PDOS dossier byte-for-byte.
- Preserve the two institutional/profile identity redirects, Xiao/Sean Zhan's
  sourced name aliases, and separate source observations for GPTOpt/SemanticOpt.
  Pre-faculty work, BrepDiff without a PI author, and personal-only ZeroShotOpt
  do not qualify as default ADG papers. Maxine's present adviser is a separate
  observation from her ADG alumni years.
- One retained PDF is malformed; PCBS's primary edition remains under review.
  A local file or a current roster does not establish authorship or lab attribution.
- Run `test-mit-adg.py`, prior sequential lab tests, and the people, date,
  identity, attribution, storage and browser regressions before publishing.

Algorithms sequential checkpoint (2026-10-19):
- `scripts/integrate-mit-algorithms.py` uses the immutable live v118 baseline in
  `.research-sweeps/mit-algorithms-20261019`. Rebase before a later refresh.
  Run the MIT projector and audit builder with `MIT_STAGE` set to that folder.
- Five groups are reviewed with gaps; 96 remain queued. Algorithms has 13 listed
  faculty, 601 people/advising observations and 2,903 source citations. Citations
  are not distinct accepted works: 400 indexed candidates remain held.
- Preserve the separate academic-advising, postdoc-mentoring, thesis-reader and
  related-group-roster contexts. None grants direct Algorithms membership.
  John Urschel's old student label is stale; his newer faculty source is retained.
  Supertech's stale roster labels do not override dated CV graduation evidence.
- The five eligible Algorithms papers have exact group-featured institutional
  news evidence, PI authorship and faculty dates. Refashion has no qualifying PI
  author; Williams's 2011 ACC paper predates his MIT faculty appointment.
- Local paper bytes are in `research-library/mit-cs/algorithms/`. Preserve local
  receipts, unresolved PDF/edition checks and PostScript labels. New bytes stay
  local only; hosted reader registries and prior lab dossiers remain unchanged.
- Preserve complete source citations and separate arXiv editions. A personal
  bibliography, edited volume, thesis supervision or indexed candidate cannot
  create a default lab-paper connection.
- Run `test-mit-algorithms.py`, prior sequential lab tests, and the existing people,
  date, identity, attribution, collection, storage and browser checks.

ALFA sequential checkpoint (2026-10-19):
- `scripts/integrate-mit-alfa.py` uses the immutable v119 baseline under
  `.research-sweeps/mit-alfa-20261019`. Rebase before a later refresh.
  Run the MIT projector and audit builder with MIT_STAGE set to that folder.
- Six groups are reviewed with gaps; 95 remain queued. The ALFA dossier retains
  268 current/historical roster observations, with source roles and independent
  identity candidates. Observations are not necessarily distinct people.
- O'Reilly and Hemberg are research scientists. Their PI/co-leader roles do not
  qualify a faculty-only lab comparison. Personal papers remain accessible.
  Retain original imported contexts alongside explicit role corrections.
- Current roster labels may be stale. Preserve the newer Cristian Colón profile
  and resume observation separately from the UROP roster entry. Do not convert
  alumni years to membership intervals or coauthorship to advising.
- Preserve exact publisher/preprint bylines, the ALFA-Chains revision title,
  editor-only records, and separately held indexed candidates. Hemberg is absent
  from the Nature climate article's publisher byline, despite index inclusion.
- Local paper files are in `research-library/mit-cs/alfa/`. New bytes stay local;
  previous hosted readers and earlier lab dossiers must remain unchanged.
- Run test-mit-alfa.py, prior sequential lab tests and the people, date, identity,
  attribution, collection, storage and browser checks before publication.

Applied Computing sequential checkpoint (2026-10-20):
- `scripts/integrate-mit-applied-computing.py` uses the immutable v120 baseline
  under `.research-sweeps/mit-applied-computing-20261020`. Rebase before replaying;
  run the MIT projector and audit builder with MIT_STAGE set to that folder.
- Seven groups are reviewed with gaps; 94 remain queued. Preserve the shared
  progress file and all earlier lab dossiers.
- Three Alan Edelman records resolve through explicit institutional profile
  links and a personal-page redirect. Preserve original records, contexts,
  authorship, dated faculty evidence and both old person-ID redirects.
- The Applied Computing page lists only the PI. Related Julia Lab roster and
  bibliography observations do not establish Applied Computing membership or
  exact lab-paper attribution. Preserve existing supported Julia paper links.
- Personal advising, postdoc mentoring and repository thesis supervision remain
  separate roles. A thesis adviser is not its author. The current professorship
  starts July 2002; earlier appointment observations do not bridge the gap.
- The MIT draft of Robust benchmarking names Edelman; arXiv 1608.04295 does
  not. Preserve separate editions and bylines. SmartSolve is a software release.
- Paper files and receipts are in `research-library/mit-cs/applied-computing/`.
  New bytes stay local; preserve existing hosted readers.
- Run test-mit-applied-computing.py, earlier sequential lab tests and the people,
  date, identity, attribution, collection, storage and browser checks.

AI Technology and Systems sequential checkpoint (2026-10-20):
- `scripts/integrate-mit-aits.py` uses the immutable live v121 baseline under
  `.research-sweeps/mit-aits-20261020`. Rebase before replaying; run the MIT
  projector and audit builder with MIT_STAGE set to that folder.
- Eight groups are reviewed with gaps; 93 remain queued. Preserve prior lab
  dossiers, hosted readers, and the shared sequential progress file.
- AITS is a Lincoln Laboratory staff research group. Its three listed assistant
  group leaders and historical leadership do not establish MIT faculty status.
  Outside academic appointments are separate; no faculty-only lab papers added.
- The dossier retains 43 current staff biographies, historical student/intern
  observations, and mentoring programs. Unnamed outreach mentees are not an
  MIT student roster. Jaime Pena's news text and group hyperlink conflict;
  keep the historical observation and exact-paper authorship separately.
- The modern official bibliography ends in June 2023. Historical author pages,
  CV entries and newer news retain distinct provenance. Personal authorship uses
  independent profile-email, exact PDF byline and institutional author-ID chains.
  Source-only, edited-volume and abstract-only records retain their types.
- Paper files live in `research-library/mit-cs/ai-technology-systems/`; new bytes
  stay local. A title check alone does not verify publisher edition. Keep failed
  URL receipts and unresolved copy editions, without promoting them to readers.
- Run test-mit-aits.py, earlier sequential lab tests and the people, date,
  identity, attribution, collection, storage and browser checks before publishing.

Broderick sequential checkpoint (2026-10-20):
- `scripts/integrate-mit-broderick.py` uses the immutable live v122 baseline in
  `.research-sweeps/mit-broderick-20261020`. Rebase before replaying; run the MIT
  projector and audit builder with MIT_STAGE set to that folder.
- Nine groups are reviewed with gaps; 92 remain queued. Preserve earlier lab
  dossiers, readers, personal works, original observations and identity redirects.
- Broderick's two institutional records share an independently verified owned
  profile. Retain both original records and the redirect. MIT faculty starts in
  January 2015; that date does not establish a historical lab leadership interval.
- The six eligible lab papers have exact group-featured institutional evidence,
  verified PI authorship and supported faculty dates. Personal bibliographies and
  student/advising records do not supply that lab evidence.
- Preserve 22 direct roster observations and 26 distinct advising/mentoring
  observations, including two additional undergraduates. Newer appointments,
  stale roster labels and source-specific co-advisers remain separate.
- Huggins's owned thesis and MIT repository edition have identical full extracted
  text; reuse the existing record, with Broderick as adviser only. Manuel's INEGI
  report records his contributor role without inventing authorship. Preserve
  conflicting manuscript bylines, arXiv title revisions and separate editions.
- Paper files live in `research-library/mit-cs/broderick/`. New bytes stay local;
  title checks and exact-edition checks are distinct. Preserve unavailable links,
  held identities and source captures without promoting them to hosted readers.
- Run test-mit-broderick.py, prior sequential lab tests and the people, date,
  identity, attribution, collection, storage and browser checks before publishing.

CBMM sequential checkpoint (2026-10-20):
- `scripts/integrate-mit-cbmm.py` uses the immutable live v123 baseline under
  `.research-sweeps/mit-cbmm-20261020`. Rebase before replaying; run the MIT
  projector and audit builder with MIT_STAGE set to that folder.
- Ten groups are reviewed with gaps; 91 remain queued. Preserve earlier lab
  dossiers, hosted readers, personal works, contexts and identity redirects.
- CBMM is a multi-institution center. Preserve each source's institution,
  archival date and literal role. The Engineering of Intelligence Teams roster
  is a named center team directory. Group adviser listings do not establish
  individual student-adviser relationships; explicit advising remains separate.
- MIT records the funding end as 2025-08-31. This does not supply each person's
  employment or membership end date. Post-boundary papers require further
  center attribution review. Poggio's newly reviewed faculty confirmation ends
  at 2025-06-30; his later emeritus transition date remains unresolved.
  Do not use older unreviewed faculty observations to bypass these boundaries.
- Katz and Oliva are research staff. Preserve their explicit role corrections
  and original observations. The Katz alias merge has independent profile-link
  evidence. Guangyu Robert Yang's `/people/yang-1` profile is distinct from
  Mingshi Yang's `/people/yang` profile.
- Exact bibliography-row Funded and Related labels remain distinct from
  verified MIT PI authorship and publication-time affiliation. DOI-title
  conflicts, source-only citations and possible duplicate editions stay held.
- New paper files live in `research-library/mit-cs/cbmm/` and remain local only.
  Preserve HTTP fallback receipts and explicitly deferred HTTPS links. Manual
  revision/byline conflicts override automatic identifier matches. Memo 073v4
  is a replacement notice, not a full-paper copy; Memo 090_0 and the older
  arXiv 2202.09028v3 copy have unresolved edition/byline conflicts.
- Run test-mit-cbmm.py, prior sequential lab tests and the people, date,
  identity, attribution, collection, storage and browser checks before publishing.

CCSE sequential checkpoint (2026-10-20):
- `scripts/integrate-mit-ccse.py` uses the immutable live v124 baseline under
  `.research-sweeps/mit-ccse-20261020`. Rebase before replaying; run both the MIT
  projector and audit builder with MIT_STAGE set to that folder.
- Eleven groups are reviewed with gaps; 90 remain queued. Preserve previous
  dossiers, hosted readers, personal works, source observations and redirects.
- CCSE is an interdisciplinary Schwarzman College of Computing unit. Its 81
  listed PIs comprise 34 core and 47 affiliated investigators, including two
  co-directors. The 61 graduate-student directory entries are center/program
  observations, not membership in every investigator's individual lab.
- Keep explicit academic advising, research mentoring, repository thesis authors,
  and literal adviser fields separate. The 84-record linked thesis collection
  provides 83 public original-paper links; one record has no ORIGINAL bundle.
- Preserve research-staff and emeritus roles, dated leave, Pierrehumbert's Oxford
  appointment, and newer observations superseding stale roster labels. Current
  directories and owned bibliographies do not establish historical faculty dates.
- Directory student counts follow the source's explicit student section. A
  faculty title mentioning undergraduate education does not identify a student.
  Project unit departments from organizational evidence, not member affiliations.
- Default CCSE papers require exact center evidence, a verified PI author, and
  independently dated MIT faculty support. Person-specific paper affiliations
  qualify only the named person; an adviser or inventor is not a paper author.
- Name-search candidates remain held even when their arXiv metadata is valid.
  Preserve publisher/preprint editions, source-title/byline variants, historical
  citations, and exact-edition key aliases. Keep manual copy conflicts above
  automatic title/identifier checks.
- Paper bytes, source captures, receipts and the offline index live in
  `research-library/mit-cs/ccse/`; new files stay local. Preserve the per-PI
  coverage report and unresolved source/identity/file gaps.
- Run test-mit-ccse.py, prior sequential lab tests and the people, date, identity,
  attribution, collection, storage and browser checks before publishing.

CDML and Claude arrivals checkpoint (2026-10-20):
- `scripts/integrate-mit-cdml.py` uses the immutable v125 baseline in
  `.research-sweeps/mit-cdml-20261020`. CDML is the twelfth sequentially reviewed
  group, with gaps; 89 remain queued. Preserve its dossier and shared progress.
- CDML's 2,604 bibliography observations, 13 investigators and 22 distinct
  directory students are separate from its four eligible lab papers. Preserve
  source-specific advising, mentoring, thesis committee and related-roster roles.
  Madry and Sontag leave/current-role evidence must not extend faculty dates.
- CDML paper files are in `research-library/mit-cs/cdml/`. Retain manual
  edition/byline conflicts above automatic title or identifier matches.
- `scripts/integrate-claude-refresh.py`, `project-claude-refresh.py` and
  `project-claude-refresh-people.py` use the fresh immutable post-CDML snapshot
  in `.research-sweeps/claude-arrivals-20261020/projection-baseline`. Never replay
  older imports over this combined checkpoint. Keep its frozen input hashes,
  source dispositions and edition addendum.
- The Claude refresh adds source-only catalogue records across Princeton, CMU,
  EPFL and MIT. Index/search ownership does not prove authorship or affiliation.
  Historical department and research-unit observations retain their dates and
  literal roles; they are not current appointments or inferred lab intervals.
- CMU's WebAssembly Research Center has independent organizational evidence.
  Princeton's Arora Research Lab has reviewed unit evidence; Appel's adviser
  listing remains an adviser listing. Preserve exact identifier-backed merges,
  the EPFL two-person identity split, and all prior sequential MIT corrections.
- Explicit arXiv identity takes precedence over an ancillary publisher DOI.
  Preserve the separately reviewed publisher candidates and unresolved metadata
  variants. New metadata loads on demand from `collection-metadata` shards;
  it does not alter canonical bylines, dates or the saved analysis snapshot.
- Exact institutional repository handles recovered 1,401 additional source
  observations on existing records. Preserve their receipts without treating
  title similarity alone as identity. Run `reconcile-claude-refresh-reuse.py`
  after the additive import and before final exports. `priorPersonLinkObservations` retains
  original candidate evidence when an evidenced identity merge resolves to a
  separately verified author link.
- New PDFs remain local only. The searchable reuse index is
  `research-library/claude-arrivals-20261020/index.html`. Preserve existing
  hosted reader registries and every earlier MIT dossier byte-for-byte.
- `test-claude-refresh.py` checks preservation against the post-CDML snapshot.
  It supersedes prior single-lab tests' cross-university byte-equality constraints
  for this combined update. Run it with university-people, faculty/lab period,
  attribution, identity, collection, browser and storage regressions. The CDML
  and earlier sequential tests were checked before the broader additive import.

Princeton PI connections checkpoint (2026-10-21):
- `scripts/integrate-princeton-pi-connections.py` uses the immutable baseline in
  `.research-sweeps/claude-pi-connections-20261021/baseline`. Rebase before replaying;
  it refuses to run over live files changed by anything but its own last output.
- Each Princeton unit leader resolved through an explicit identifier (CS profile id;
  a collection leader record only within its own unit) gains a lab_leadership
  context and verified works for exactly the papers the unit policy already
  permits. No person merges, no leadership interval, no policy or count changes.
- The CS structure graph gains `leads` (PI -> unit) and verified `authored`
  (PI -> paper) edges; princeton-network.js accepts `leads` with an endpoint check.
- PI works carry the paper aliases and the policy year (online-first dates can
  precede it). Keep both when rebuilding person works.
- Run test-princeton-pi-connections.py with the existing attribution, identity,
  people, collection, storage and browser checks. See research/claude-pi-connections-20261021.

Owner decision, every PI has their own lab (2026-10-21):
- A PI's own lab is the PI and the people they advise, as one thing. Collectives
  (centres, initiatives, multi-PI groups) contain labs and are no one's own lab:
  CITP is a centre, and Manoel Horta Ribeiro's lab is a separate unit.
- `scripts/integrate-princeton-pi-own-labs.py` (immutable baseline in
  `.research-sweeps/claude-pi-own-labs-20261021/baseline`, --restore) keeps, creates,
  converts (adviser listing) or claims one single-leader lab per lab-record PI, adds
  advisees and the lab record's people as formal memberships (one record per name;
  never a second membership), and nests the lab `part_of` collectives that list the
  PI as a leader, never inside another PI's lab. A claimed unit's co-listed PIs keep
  their own labs; their step-1 leadership there moves to superseded lists.
- A PI lab sits in its PI's home department (the lab record's curated first
  department, as the site labels it). CS "associated"/"affiliated" status and
  centres are not department appointments; a lab homed elsewhere stays in the
  CS collection only as "CS collection context".
- Checkpoint order: PI connections, PI own labs, PI lab papers,
  `finalize-claude-refresh-exports.py`, lab student papers. To change an earlier
  step, --restore the later ones in reverse order, move their baselines aside, and
  replay in order. Run test-princeton-pi-own-labs.py with the other Princeton tests.

Owner update, Princeton PI lab papers (2026-10-21):
- For a PI's own lab, the publication-time lab connection is the PI's own
  authorship at Princeton: a verified PI author, a Princeton affiliation on the
  PI's authorship of that work, and a date inside the PI's reviewed faculty
  period. The PI's own lab: a unit with the PI as its only leader, typed research
  group or laboratory, not an adviser listing, program, centre, initiative or
  cluster. Collectives keep the earlier evidence rule.
- Owner decision, department listings (2026-10-21): a captured department
  faculty listing dated in year Y that lists the PI as faculty proves the
  faculty appointment for that PI's papers from year Y, at every school. It
  establishes no interval beyond its own calendar year. Listings live in the
  collection's `facultyListings` (Wayback id_ capture, sha256, verbatim quote);
  a link so proven carries `facultyBasis: department_listing_same_year` and
  `listingId` instead of `periodId`. A reviewed faculty period is used first.
  Arrival statements of any year (before 2016 too) open a period; a departure
  without a stated year bounds it at the last dated confirmation.
- `scripts/integrate-princeton-pi-lab-papers.py` applies it from the immutable
  baseline `.research-sweeps/claude-pi-lab-papers-20261021/baseline` (--restore
  rolls back). Rebase before replaying. Promoted withheld links stay in
  resolvedUnitLinkObservations; upgraded person links in priorPersonLinkObservations.
- Run test-princeton-pi-lab-papers.py and test-princeton-pi-connections.py with
  the existing suite. See research/claude-pi-lab-papers-20261021.

Princeton lab people on lab papers (2026-10-21):
- `scripts/integrate-princeton-lab-student-papers.py` (immutable baseline in
  `.research-sweeps/claude-lab-student-papers-20261021/baseline`, --restore) adds
  CANDIDATE authorship for lab-roster people whose full name is on a lab paper's
  indexed byline (unique in the lab roster, or the one lab member among same-name
  records; not a leader; within two years of the person's observed lab years).
  Never promote these to verified without identity proof.
- Run test-princeton-lab-student-papers.py with the earlier Princeton tests.

Owner decision, CS departments are PI labs only (2026-10-21):
- The CS view is school → department → PI labs → papers + students, at
  Princeton, CMU, EPFL, MIT, Berkeley and Stanford. Departments are the computing
  units in full: Princeton CS; CMU's seven SCS departments; MIT EECS; EPFL IC;
  Berkeley EECS; Stanford CS (owner 2026-10-27). Stanford EE lists only its
  faculty who publish in CS venues, so it is a home department not covered in
  full. A PI they list who is homed elsewhere sits in the home department, which
  is not covered in full; a Stanford courtesy appointment is not a home
  department (no reviewed home: "Home department not yet recorded"). Centres, initiatives, consortia, programmes, projects
  and multi-PI groups are not labs and are not listed; their data is kept.
- `scripts/build-cs-hierarchy.py` writes `atlas/data/cs-hierarchy/<school>.json.gz`
  and `index.json` (page `cs-departments.html`, download
  `downloads/cs-hierarchy-labs.csv`) from the per-school packages of
  `.research-sweeps/claude-schools-20261021/tools/pi_hierarchy.py`. A lab paper:
  the PI on the byline, that authorship listing the school (an institution in the
  school's OpenAlex lineage, or affiliation text), identity anchored by the PI's
  DBLP person page, verified works, an advisee co-author or an OpenAlex author id
  seen on those, inside a reviewed faculty period (contains()) or in the year of
  a captured department listing of the PI. Datasets, reviews and errata are not
  papers. Students are stated advisees (named adviser fields only: never readers,
  examiners or senior-thesis advising) and members of the PI's own unit. A
  student–paper link is a recorded authorship (verified) or the student's name on
  a school-affiliated byline entry of that lab paper (candidate).
- Run `scripts/test-cs-hierarchy.py` and `node scripts/test-cs-departments-page.mjs`.
- Hidden labs (2026-10-28): a PI lab with zero lab papers stays in `<school>.json.gz`
  but neither page lists it. Run `.research-sweeps/claude-schools-20261021/tools/
  zero_paper_ledger.py` after every package rebuild; `build-cs-hierarchy.py` then
  writes `atlas/data/cs-hierarchy/hidden-labs.json` (per school: lab, PI, ledger
  category, reviewed verdict and reason; counts in index.json `hiddenLabs`) and
  stops if a zero-paper lab has no ledger row. It is data, not a page.

Owner decision, the atlas shows only computer science (2026-10-22): "for all
schools to only show CS departments / related to CS departments / staff".
- `scripts/cs_scope.py` is the one definition: a lab is in scope when its field
  is computer_and_information_sciences, its department names a computing
  department, or it is a PI lab of the CS departments view (a PI the computing
  departments list, homed elsewhere). Other fields stay on disk, unshown.
- Build order: `scripts/build-cs-hierarchy.py`, then `scripts/build-cs-scope.py`
  (marks every shard `csScope`/`csScopeReason`, writes CS count cells, metrics
  and the browser copy of the rule). Run `scripts/test-cs-scope.py`.
- Before replaying an earlier checkpoint script that guards shard or data.json
  digests, run `build-cs-scope.py --restore`, replay, then build the scope again.
  Rerun the scope build after any later shard or count rewrite.

Owner decision, site is two pages (2026-10-22): "a bunch of trash / old stuff / irrelevant stuff on
the website"; "why we have so many empty labs on the website view?"
- The site is atlas/index.html (the CS atlas) and atlas/cs-departments.html, with the scripts, styles
  and data they load. Every other page, its scripts/styles and the data and downloads no kept page uses
  were removed (git history keeps them). Do not add pages back. `scripts/test-site-pages.py` checks the
  two pages and that every link on them resolves to an existing file.
- "PI labs with papers only". At the schools of the CS departments view (Princeton, CMU, EPFL, MIT,
  Berkeley, Stanford: atlas/data/cs-hierarchy/index.json) the atlas shows each faculty PI's own lab with at least
  one lab paper; their inventory units are hidden (replaced_by_pi_labs), their data stays on disk.
  Elsewhere it shows the CS units with at least one linked paper (others hidden: no_papers). Each
  university, and the totals, say how many units are not shown.
- The rule is defined once, in `scripts/cs_scope.py` (unit_visibility, pi_lab_visibility,
  atlas_lab_ids). `scripts/build-cs-scope.py` marks csShown/csHidden on every shard lab, writes
  `atlas/data/cs-pi-labs/<university>.json.gz` (the schools' PI labs with paper counts by year and
  lab-paper/student/link counts), counts, metrics and hidden counts, and registers the cs-hierarchy
  files in data.json assets. A PI lab opens in the atlas with the papers and students of its
  cs-hierarchy record (`atlas/assets/cs-pi-labs.js` only reshapes them). siteLab still marks the
  matching inventory unit cs_department_pi_lab; the two pages link a PI lab by its hierarchy id.
- Build order: `scripts/build-cs-hierarchy.py`, then `scripts/build-cs-scope.py`, every time the
  cs-hierarchy files change (the atlas refuses a cs-hierarchy file whose digest differs from data.json).
  Then `node scripts/source-atlas-assets.mjs pack`. Run `scripts/test-cs-scope.py` (it runs
  test-cs-scope-app.cjs), `scripts/test-site-pages.py`, `scripts/test-cs-hierarchy.py` and
  `node scripts/test-cs-departments-page.mjs`. The MIT dossier, Claude arrivals/refresh, Princeton
  network/students/CS-labs/identity and computing/organizations tests were removed with their pages;
  test-lab-periods.py, test-princeton-pi-lab-papers.py and test-princeton-pi-own-labs.py read removed
  Princeton data and are obsolete. Earlier checkpoint sections above describe removed pages.


## Public viewing (owner request, October 29, 2026)

The site is public for reading. This supersedes the earlier owner-private audience requirement. Both maintenance APIs must remain protected by `protectedAtlasUpdate` and the Sites runtime secret `ATLAS_UPDATE_TOKEN`, including HEAD/GET requests. Updaters supply that secret as `update_token` on hidden stdin; it is sent only to this site in `X-Atlas-Update-Token`. Missing or incorrect tokens fail before storage access. Never place the secret in source, browser assets, logs, or hosting.json.

## Relocated workspace and release (2026-10-30)

The canonical workspace is `/n/fs/resemble/homogenizing-science`. Publish from
`site/`; historical `.research-sweeps/` references resolve to `archive/sweeps/`.
Releases are in `releases/<id>/`, each with `SITE-HANDOFF.md`. Do not use the
temporary links under the former workspace paths. The hierarchy build and
validation use the immutable release named in `deployment/release.json` through
`scripts/release_inputs.py`. Reports and the original manifest/handoff are
retained in `research/release-<id>/`.

## Release-only reader publication (2026-11-02)

The research release is pinned by `deployment/release.json`; the hierarchy
builder and its regression check both use `scripts/release_inputs.py`. Verify
the immutable release with that script before rebuilding the site.

`scripts/import-reader-release.py <release-directory>` projects the release's
reader decisions into `atlas/data/local-papers.json` and `reader-objects.json`.
Import diagnostics are kept in `deployment/reader.json`.
The descriptive index uses schema 2: `works` maps exact lookup keys to numeric
positions in `records`; `files` remains a map of SHA-256 to hosted-file metadata.
Ambiguous aliases are withheld. Source-only entries have `link: true` and no
hosted path. Both pages expose the same reader controls. XML is rendered as text,
never inserted as HTML. Large approved files use verified 32 MiB storage chunks.

The compact server allowlist contains exactly the frozen release's hosted files.
`prepare-atlas.mjs` excludes all local `papers/` files from ordinary assets so old
PDFs, page images and extracted text cannot bypass the reader allowlist. Removing
a file from the next release withdraws public access without deleting research
stores or private bucket objects. Uploads use `upload-atlas.py --reader-release
<release-directory> --stores <workspace>/stores` and hidden-stdin credentials.

Run `test-reader-release.py`, `test-paper-reader.mjs`, and `test-atlas-storage.mjs`
with the existing hierarchy, scope, page, department and authentication checks.
