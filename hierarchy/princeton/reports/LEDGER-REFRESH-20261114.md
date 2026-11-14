# Princeton copy inventory and unavailability ledger refresh (2026-11-14)

The release evidence check had 173 nonlocal papers without a ledger entry and 2,199 stale entries. The ledger dated 2026-11-07 predated the current lab paper package. A ledger-only refresh (Slurm job 32256036) reduced the stale count to zero but exposed four keys retained in an older `copies.json` that no longer appeared in `lab_papers.jsonl.gz`.

Slurm job 32256100, pinned to code commit `8675923c`, reran `tools/lab_paper_copies.py princeton`, then `fulltext-push/unavailable_ledger.py princeton`, then the strict `tools/evidence_check.py princeton`. It completed with exit code 0. The count and ledger now describe the same paper set:

| Measure | Before | After |
| --- | ---: | ---: |
| Distinct lab papers in copy inventory | not captured | 8,732 |
| Nonlocal papers in copy inventory | 2,372 | 2,414 |
| Missing ledger entries | 173 | 0 |
| Stale ledger entries | 2,199 | 0 |
| Incomplete copy searches | 2,032 | 66 |

The 66 incomplete searches remain explicitly labeled `incomplete_check`, mostly because a fresh CORE check is unavailable under the existing pause. Princeton's existing exception allows up to 2,052 incomplete searches; this run did not change the exception or relabel them as firm absences.

The new ledger was built at `2026-11-14T06:13:01.130807+00:00` and has SHA-256 `36bc65c2623055e7d9a5cf3bbadd87e9dde8b7237cd382fda0659f65599e1104`. The strict Princeton evidence check passed. The global strict check fell from 26 to 24 over-whitelist findings; all remaining findings are in other schools. Review output is in `scratch/princeton-ledger-1114/EVIDENCE-CHECK.json`.
