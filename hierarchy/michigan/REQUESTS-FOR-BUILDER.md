# Michigan onboarding: requests for the builder (pi_hierarchy, audits, evidence check, release, export, tree)

These are written by the Michigan onboarding agent (2026-10-29), which may not edit the builder's files. Each request
says what, why, and the Michigan file that shows the case. None of them blocks stages 0–5; numbers 1 and 2 matter for
stage 7, and 3 matters for stages 2 and 6.

1. **`tools/dblp_recover.py` for protocol schools (stage 7).**
   - `candidates()` reads `P.sweep(DBLP[school]) / 'raw/dblp_pubs.json.gz'`. A protocol school has no legacy sweep, so
     `DBLP['michigan']` raises `KeyError`.
   - Ask: when `school not in DBLP`, read the PI's records from `hierarchy/dblp-dump-persons.json.gz`. It is complete
     for Michigan as of 2026-10-29 21:30 UTC: 3,694 persons, regenerated with the onboarding schools included.
2. **R-PAP-03 for homepage-derived periods.** `periods/michigan-faculty-periods.json` now writes a
   `kind: "faculty_end_moved"` evidence item when the statement that closes a period says the PI moved.
   - The case: Michael Cafarella. "Before coming to MIT he was a professor of Computer Science and Engineering at the
     University of Michigan from 2009 to 2020." CSE kept listing him as *adjunct* in 2021–2026.
   - `listings_after_move()` should already set those listings aside, since it looks for `end_moved` in the evidence
     kind. Please confirm in the Michigan build.
3. **`chain_audit.py` coverage: `pending_*` decisions are not decisions.**
   - `hierarchy/michigan/cs-related-review.json` has 22 `pending_openalex` decisions: ECE faculty whose computing work
     can be decided only with the OpenAlex sweep. The audit counts any decision as "decided", so coverage shows 0 open.
   - Ask: treat a decision whose value starts with `pending` as open. `tools/stage_gate.py michigan 2` already does.
4. **Defense evidence carries a second quote.**
   - Rows of `hierarchy/michigan/labpage-evidence.json` with `section: "dissertation defense announcement"` cite the
     candidate in `quote` (the announcement head through the name) and the chair in `host_quote` ("Faculty Host
     <PI>", same page and sha256).
   - Ask: keep `host_quote` as a second source of the relation, so a reader sees why the PI is the adviser.
5. **Name aliases for two Michigan PIs** (for `hierarchy/census-overrides.json`, if that file is yours):
   - "Satinder Singh Baveja" is the CSE listing's name; DBLP's "Satinder Singh" (pid from the dump) is the same person.
     The Robotics listing says "Satinder Singh Baveja Professor".
   - "Chad Jenkins" is the CSE listing's name; DBLP's "Odest Chadwicke Jenkins" is the same person.
   - Both are recorded as `census_alias` decisions in `cs-related-review.json`.
6. **Lab-page students are automatic and unreviewed.** The students in `hierarchy/michigan/labpage-evidence.json` carry
   `auto: true`. Please keep the flag in `students.json` so that the accuracy sample (stage 9) can stratify on it.
