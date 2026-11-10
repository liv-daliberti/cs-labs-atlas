# Virginia Tech Stage 3 precheck

2026-11-10. **Preparatory evidence, not a passed Stage 3 gate.** Stage 2 remains open; the complete school PI set, shared home ledger and built lab package are not finalized.

## Current CS PI websites

The strict offline verifier now passes **53 of 64** current provisional CS PI websites, up from 51. Kurt Luther’s Crowd Intelligence Lab page and Denis Gracanin’s personal page passed source, capture-hash, PI identity and substantive-content checks. Kurt’s new page explicitly names him and Virginia Tech; the previously registered Crowd URL remains as an alternate lead because its capture timed out. Denis’s existing official-profile-linked page contains a reviewed autonomic-computing research record. Exact URLs, hashes, source receipts and verifier verdicts are in `scratch/vt-followthrough-1110/stage3-two-site-review.json`. Eleven strict website holds remain in `scratch/vt-followthrough-1110/supported-PI-website-gaps.json`.

Ryan P. McMahan’s recorded target page identifies a current University of Central Florida appointment and only a Virginia Tech PhD; it stays pending for VT site and current-role review. The remaining holds include uncaptured or inaccessible targets, pages without sufficient rendered research content, and PIs with no proven site.

## Current CS PI home departments

`tools/vt_stage3_home_precheck.py` verified the saved 2026 official CS directory body and its SHA-256, then checked the exact professor-rank quote for each of the **64** current provisional CS PI records. `reviewed/current-cs-home-precheck.json` records Computer Science as the source-backed home for this current CS subset. It does not write the shared home-department ledger or decide affiliated-unit PIs. The formal Stage 3 chain follows the completed Stage 2 census: census refresh, homes, build, lab-page discovery and audit.
