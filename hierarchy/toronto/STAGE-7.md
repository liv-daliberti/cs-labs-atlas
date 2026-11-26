# Toronto stage 7: Paper and student-link evidence

Verified 2026-11-16 using clean code snapshot ddabc6ccde988dc35aca1c76ac4dae513dacf437 and completed native job 32328672 (exit 0:0). The hierarchy, copies, offline ledger, link diagnosis and student audit completed coherently; all 20 reviewed input hashes stayed unchanged.

The source repairs are recorded in [the repair report](reports/RECALL-PHOTO-FIXED-SOURCE-REPAIRS-20261116.json). Exact native and gate receipts are retained in the scratch run toronto-recall-repaired-ddabc6cc; this gate output has SHA256 2d46d105f8582cb9534246ff9f7659f83d9a8aba7d8d03a216444e72d2d5a753.

Result: **PASS**. No gate waiver or unexplained gate item. The rebuilt package contains 9,884 lab-paper rows (9,165 distinct works) and 5,172 student-paper links.

Gate counters:

```json
{
  "papers": 207,
  "links": 1397
}
```
