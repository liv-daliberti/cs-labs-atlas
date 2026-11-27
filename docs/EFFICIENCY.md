# Collection and build efficiency

`atlas build SCHOOL [...]` now reuses a native package only when its registered
inputs, code and output hashes match its successful build receipt. `--force`
rebuilds explicitly. The existing `pi_hierarchy.py` CLI uses the same path, so
pipeline and rebuild-script callers adopt it without separate scheduling.

The receipt lives beside the school's derived package. Reviewed content is
hashed; large SQLite inputs and their journals use the closeout registry's
size/mtime guards. Missing optional inputs are recorded, so adding one
invalidates the receipt. Changed outputs and input drift prevent reuse. A
per-school filesystem lock serializes builders. This is an execution cache,
not a passing source, recall, accuracy or release gate. Existing downstream
audits remain required.

The policy-aware lab-page fetcher shares successful public captures through
`CACHE/shared-public-captures/`. Concurrent identical requests take one NFS
lock and reuse one hash-verified body. Every school receives its own capture
row with the original observation time and copied-from provenance. Charter,
robots/AI-agent and refusal checks still precede this layer. Requests with
credentials, cookies, custom headers or query authentication are excluded.
Live captures have a one-day sharing lifetime measured from the original
observation; explicit historical archive URLs can be retained longer. Existing
local capture behavior remains unchanged. Explicit refresh uses the existing
`force` behavior; it does not waive access policy. Refusals and Retry-After
cooldowns prevent repeated identical requests. Corrupt bytes stop reuse.

`atlas pipeline` and protocol calls to `atlas_pipeline.submit` now keep an
NFS-locked submission registry in `CACHE/pipeline-submissions.json`. An exact
queued/running chain returns its existing job IDs, including completed
prerequisites. A different overlapping chain is refused rather than changing
another job's dependencies. Terminal chains may be run again. Submission is
journaled before and after each sbatch; interrupted acknowledgement is resolved
by its unique Slurm job comment. Unknown scheduler/accounting results stop
submission rather than creating duplicates. Inspect the comment and accounting
receipt before reconciling an uncertain historical submission. Existing jobs
are not cancelled; already-running code adopts these changes on restart.

Use `atlas pipeline ... --test-only` before scheduling long work. The registry
does not replace task claims, scientific input seals, explicit resource requests
or the standing non-preemption check. Caches, source captures and job receipts
remain outside Git; do not copy credentials into them.
