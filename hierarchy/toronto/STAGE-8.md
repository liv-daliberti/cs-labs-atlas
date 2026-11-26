# Toronto stage 8: Copies and unavailability ledger

Verified 2026-11-16 using clean code snapshot ddabc6ccde988dc35aca1c76ac4dae513dacf437 and completed native job 32328672 (exit 0:0). The hierarchy, copies, offline ledger, link diagnosis and student audit completed coherently; all 20 reviewed input hashes stayed unchanged.

The source repairs are recorded in [the repair report](reports/RECALL-PHOTO-FIXED-SOURCE-REPAIRS-20261116.json). Exact native and gate receipts are retained in the scratch run toronto-recall-repaired-ddabc6cc; this gate output has SHA256 b83ba69c2f164c26d7698d03ee6892e54d2aac8079bd30e1d0c3502673552d96.

Result: **PASS**. No gate waiver or unexplained gate item. Local copies cover 2,379 of 9,165 works (26.0%). The 85% copy share remains a target, not a gate. Every nonlocal work has a ledger entry; incomplete access checks remain explicit.

Gate counters:

```json
{
  "lab_papers": 9165,
  "local": 2379,
  "local_share": 0.26,
  "copy_target": 0.85,
  "copy_target_met": false
}
```
