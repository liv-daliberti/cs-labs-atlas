# Finish one school without rebuilding the review workflow

Toronto's November 2026 closeout repeated three kinds of work: source repairs
found during successive reviews, native rebuilds followed by another late gate
failure, and custom readiness/draw/receipt scripts for each attempt. A status
table can expose this loop; it cannot remove it. Use one driver, one repair
batch, one native run, and one fixed review draw per resulting build.

## Work in two passes

During the collection/repair pass, finish the source population or source-format
batch before drawing final recall or accuracy samples. An error in dates,
roles, school scope, or a template is a reason to inspect all matching rows,
not just repair the sampled example. Reuse the captured source bodies and
existing independent review receipts. Put every known unresolved issue on the
same repair board, including paper-link findings and identity holds. Group
related findings into one investigated cause. This does not change the
scientific evidence requirements or make unreadable sources negative evidence.

The initial source pass should cover complete eligible rosters, not aim to add
one student to each empty lab. Toronto's November 14 repair deliberately added
30 relationships to improve the number of covered PIs; the final recall gate
asks whether the eligible names on the full roster are recorded. These are
different measurements. Pilot each new source layout before scaling it, and
keep document/capture dates, degree dates, and membership periods separate.
Batch a template correction across all affected rows before the final review.

During closeout, stop adding unrelated scope to that candidate. Record new
leads separately for the next batch. A genuine correctness error still stops
closeout, preserves its failed reviews, and starts a new repaired candidate.
Never carry a verdict forward just to avoid a fresh required review.

Before collecting again, run `atlas closeout research SCHOOL --out BOARD.json`
against the actual candidate overlay. The planner inventories both registered
recall, school and lab-page audit capture caches offline, rehashes original response bytes,
and retains distinct versions and recorded access refusals. Existing readable
captures become `inspect_saved_source` work rather than another fetch. An empty
extracted-text field does not discard saved HTML. Inspect the original bytes;
a cached page is still pending whole-source review, never an accepted roster
or a recall verdict. The JSON board lists `capture_stores` for locating them.
Audit stores retain every matching saved version, using the actual archived
response URL's year rather than a later fetch year. Refusals remain visible
even when another store has readable bytes. Captured bytes still require a
whole-source review; inventorying an old page does not accept its members.

Private school overlays must retain the archived listing source databases as
well as `rows.json` and coverage summaries. The overlay helper snapshots the
registered listing `.sqlite` stores through the backup API, including committed WAL data, and preserves the private
copy on reuse. Select the actual reviewed candidate as the source root; an old
summary cannot stand in for missing captured bytes.

After a reviewed PI merge, reconcile the website register's PI keys and rekey
explicitly owned roster entries before sealing. Preserve source-reviewed
website objects and dates: older discovery/audit rows can contain superseded
claims. Use the CLI's reviewed-entry preservation or a documented key-only
reconciliation; calling the lower-level website generator alone is not a new
source review. Aliases do not automatically reassign roster ownership.

Check the native representation of open student intervals before sealing.
The integer-year reader drops a null endpoint: `[2024, null]` alone becomes
2024, not an interval through the capture date. Keep the original stated
interval. When a hash-verified captured source explicitly shows the student
as current with an open stated interval, record a separately reviewed
observation for that capture year. This records presence, not graduation or
an inferred end date. Investigate the whole matching class, including roles
and alumni exclusions; a capture year does not date an undated former member.

## Reusable commands

Start with `bin/atlas closeout stages <school>`. This shows stages 0–10 with
their current gate, prerequisites, concrete findings, and the next eligible
stage/action. Student and paper work can proceed after identity is complete;
accuracy waits for students, papers, and availability. `--json` produces the
same board for automation. Run against the actual candidate data root so a
stale canonical package cannot hide a candidate's progress. The board keeps
formal research release and verified interim website publication distinct.

Use the school's existing data overlay and committed code checkout. Set the
existing `CS_ATLAS_CODE`, `CS_ATLAS_HIERARCHY`, and `CS_ATLAS_SCHOOL_CONFIGS` slots
exactly as for its build. Claim the school task before running writes; keep the
lease and task heartbeat. Shared reviewed inputs should be private copies in
the overlay while other schools are changing them.

```sh
bin/atlas closeout plan toronto
bin/atlas closeout seal toronto --run-dir "$CS_ATLAS_SCRATCH/toronto-closeout-01" --repairs repairs.json
bin/atlas closeout submit toronto --run-dir "$CS_ATLAS_SCRATCH/toronto-closeout-01"
bin/atlas closeout status toronto --run-dir "$CS_ATLAS_SCRATCH/toronto-closeout-01"
bin/atlas closeout certify toronto --run-dir "$CS_ATLAS_SCRATCH/toronto-closeout-01"
bin/atlas closeout draw toronto --run-dir "$CS_ATLAS_SCRATCH/toronto-closeout-01"
```

The repair board is a small record of work already reviewed, not another
approval round. Each resolved case points to its existing receipt:

```json
{
  "school": "toronto",
  "cases": [
    {
      "id": "source-template-date-repairs",
      "status": "resolved",
      "receipt": {"path": "/your/review/receipt.json", "sha256": "its actual SHA-256"}
    }
  ]
}
```

`seal` refuses open cases, changed receipts, an uncommitted checkout, or missing
essential build inputs. It records the code commit, data roots, charter,
registered school inputs and shared reviewed inputs, including absent optional
inputs. Reviewed content is SHA-256 bound. Large raw stores use size/mtime
guards to avoid repeated large NFS reads; the resulting package files are
hashed in full. This is an operational consistency check, not a new scientific
acceptance decision. Downloads can continue without changing sealed evidence.

The seal also hashes upstream census, collection, yearly listings, coverage
and recovered-paper files. They are builder inputs despite their registry
classification as derived or work files. Freshness checks include these same
inputs, so changing a listing cannot silently reuse an older native build.
Native outputs remain outside the input seal, allowing checkpointed phases
to write their results without invalidating their own run.

`submit` schedules one snapshot-bound Slurm job: build → copies → cached-only
availability ledger → link diagnosis → student audit → gates 1–5, 7, 8. It uses
the existing preemption check, explicit resources and pipeline snapshot helper.
All prerequisite gate findings are collected on the same package, even when
one gate fails. Cached-only ledger operation never authorizes new network
collection and can still leave a school short of the existing evidence bar.

`status` reads the receipt without scheduler polling. Logs and output hashes
are in the run directory. After a failed phase or job timeout, `submit` checks
the exact prior job's terminal state before allowing a retry. The worker
resumes at the failed or changed phase, preserving valid earlier build work.
It refuses duplicate/live/unknown jobs. A changed scientific input requires a
new repaired batch/run rather than silently rebinding this one.

`certify` requires unchanged inputs, clean matching builder provenance, all
native artifacts, passing prerequisite gates, and the exact producer job's
actual `COMPLETED 0:0` state. It makes one scheduler query; do not poll it.
Only then can `draw` create the existing default-seed recall sample. Calling
`draw` again returns the preserved original; it cannot pick a different seed.
Prior failed worksheets are archived. A fresh independent reviewer still
checks the whole fixed sample under the existing recall protocol.

Stages 6 and 9 remain real review work. Use the existing accuracy workflow on
this same final package, preserve failed results, and only integrate/publish
after all required gates pass. The tool does not waive gates, sign reviews,
change admissions, publish data, or promise that every source question can be
resolved automatically.

## Toronto handoff

The latest inspected Toronto native (`32343708`) reached gate 7 with
`links: 3 unexplained of 3962`. The subsequent source-backed repair has its own
independent approval and application receipt. Those belong in the same repair
batch as the population-wide chronology corrections, before the next native
and final sample. The active school owner retains the current run; the shared
tool replaces the custom scripts for subsequent closeouts, without launching
another competing Toronto job.
