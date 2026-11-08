# Release 2026-11-08: issued-person ID review

The release hold file has 23 groups:21 multiple-issued-ID conflicts plus separate EPFL and Harvard source-evidence holds. An independent replay also checked each group without issued history, so an ID redirect cannot conceal a later source failure.

Two groups pass the existing reciprocal co-advising source gate: Berkeley/Mihir Singhal (Jelani Nelson and Venkatesan Guruswami), and CMU/Jiangyifei Zhu (Swarun Kumar and Justin Chan). Their original roster response bodies, SHA256 hashes and exact student-specific clauses were replayed from the capture databases. The reviewed input records their exact issued IDs, all owned anchor rows, the complete baseline registry fingerprint and the standard earliest-issued/ID survivor decision.

An isolated preparation using the existing atlas_ids.assign mechanism redirects exactly two aliases. It mints and splits no IDs, preserves every unrelated ID/anchor row, retains both historical IDs as resolvable, and is a no-op on repeat. These decisions do not change any membership, role, attendance year, paper, or candidate author identity. The metadata is a manual review record; atlas_ids.run does not execute it or waive its guard. Live registry application is a separate exact-preimage operation after this review lands.

The other19 multiple-issued groups still require original-source review: without issued history they reach unresolved reciprocal co-advising evidence. EPFL/Vidit has a single-token-name compatibility hold; Harvard/Jaeyeon Kim has one-sided evidence. No redirect is approved for these21 remaining groups, and this partial review does not unblock the whole release. Current details remain in the input's unresolved ledger and scratch/release-1108-issued-id-review/conflict-audit.json.

Validation: 23 current native membership groups and a consistent whole-registry snapshot audited; five original capture references replayed for the two approved groups; exact isolated assignment and repeat invariance passed. No network or global registry/package writes occurred during review. The final landing runs the repository full test, lint, charter and history-scan gates under the land lock.
