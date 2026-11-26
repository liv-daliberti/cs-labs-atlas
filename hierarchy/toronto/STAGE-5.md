# Toronto stage 5: Identity anchors

Verified 2026-11-16 using clean code snapshot ddabc6ccde988dc35aca1c76ac4dae513dacf437 and completed native job 32328672 (exit 0:0). The hierarchy, copies, offline ledger, link diagnosis and student audit completed coherently; all 20 reviewed input hashes stayed unchanged.

The source repairs are recorded in [the repair report](reports/RECALL-PHOTO-FIXED-SOURCE-REPAIRS-20261116.json). Exact native and gate receipts are retained in the scratch run toronto-recall-repaired-ddabc6cc; this gate output has SHA256 4c59a83d7def8a1bcd66a98c041707bef7d6e37c7c800ce144e4ded418100f21.

Result: **PASS**. No gate waiver or unexplained gate item. Per-PI student and link gaps remain disclosed in the counters under the existing coverage ratchet; stage 6 is a separate required review.

Gate counters:

```json
{
  "dblp": 153,
  "openalex": 43,
  "orcid": 1,
  "reviewed_no_identity": 5,
  "dblp+openalex": 14,
  "anchors_yield_checked": true,
  "pi_cov_lab_papers_gap": 0,
  "pi_cov_students_gap": 49,
  "pi_cov_links_gap": 55
}
```
