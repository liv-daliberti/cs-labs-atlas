# University of Chicago, stage 2: faculty census (partial; blocked)

Date: 2026-11-02. Gate: not run. Blocked on the OpenAlex snapshot extension merge (job 32079156, behind another session's held job 32079275).

## Done
- `tools/census_build.py uchicago`: 270 people, **88 PIs** (CS + TTIC, basis ladder_faculty) after the UChicago rank words were added (Instructional Professor = teaching,
  Adjoint Professor = adjunct; PROTOCOL-FRICTION 17). STAT is `affiliated`: 82 listed people, none a PI until reviewed.
- Unit listings captured (`cs_related_school.py units`): DSI, BOOTH, MATH, CDAC (26 Wayback captures + 5 live) into `captures/uchicago.sqlite`.
- Filter half of the extension finished (16/16 tasks, parts in scratch); `sweep_from_snapshot`, `atlas pipeline onboard-data` (DBLP pass, sweep, sweep check, OpenAlex candidates) are ready and tested.

## Next (once the merge has run)
`atlas pipeline onboard-data SCHOOLS=uchicago --from-worktree`, then `cs_related_school.py candidates|review uchicago`, share test, stage-gate 2.
