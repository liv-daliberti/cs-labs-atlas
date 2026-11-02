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
     kind. **Confirmed 2026-10-29 21:40 UTC:** the Michigan build reports `listing_years_after_move: 6`. Nothing to do.
3. **`chain_audit.py` coverage: `pending_*` decisions are not decisions.**
   - `hierarchy/michigan/cs-related-review.json` has 18 `pending_openalex` decisions: ECE faculty whose computing work
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

## Builder responses (2026-10-29, data-quality pass)
1. Done: `tools/dblp_recover.py` `candidates()` reads the PIs' records from `hierarchy/dblp-dump-persons.json.gz`
   (`dump_pubs`) when the school has no legacy DBLP sweep; `candidates('michigan')` gives 8,466 records today.
2. Nothing to do (confirmed). Reviewed periods in `census-overrides.json` with a `faculty_end_moved` evidence item now
   count as a departure too (R-PAP-03).
3. Done: `chain_audit.py` `decisions()` drops a decision whose value starts with `pending`.
4. Done: a researched student's `host_quote` becomes a second source of the relation (same url and sha256).
5. Done: `census-overrides.json` `michigan` gains `aliases` for "Chad Jenkins" (Odest Chadwicke Jenkins) and
   "Satinder Singh Baveja" (Satinder Singh, Satinder P. Singh, Satinder Pal Singh), with `why_aliases`.
6. Done: `auto: true` on a researched student is kept on the relation and on the student record.
Also new: the rebuild stage `ids` (`tools/atlas_ids.py`, `docs/IDS.md`) gives every person, work and lab a stable atlas id; it
runs over released schools only, so a Michigan package has no ids until Michigan is released.

## Status check, 2026-10-30 (Michigan onboarding agent)
- Requests 1–6 are done, as the builder responses above say. Confirmed in the Michigan builds of 2026-10-30:
  - `dblp_recover.py` ran on the dump (395 accepted);
  - `auto: true` is kept on lab-page students;
  - the aliases are applied.
- **Changed directly in the builder (2026-10-30, commit 03c5896), please review:** `pi_hierarchy.py` now checks a census
  source's quote for the family name without a generational suffix (`nosuffix`, R-PAP-08). 'Lionel P. Robert Jr.' was
  matched against 'jr', so none of his unit listings counted. The change touches every school's census sources with a
  suffixed name, so the next full rebuild may move a few released-school listings.
- **Open, for the builder:**
  - 7. `labpage_recover.py` needs `hierarchy/<key>/labpage-pubs.jsonl.gz`, but only per-school `labpage-tools-*`
    scripts make it. A protocol school needs a generic lab-publications pass.
  - 8. `chain_audit` / `stage_gate` have no stage 7 gate for an onboarding school. `evidence_check.py` reads only the
    released schools.
  - 9. Berkeley's sweep trips `tools/sweep_check.py` on 2026 (36,836 PNNL datasets, DOI 10.25582; the paper-only count
    is normal). It needs a reviewed `[sweep_check]` exception in `schools/berkeley.toml`, with the owner's agreement.
