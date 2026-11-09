# Tsinghua exact source corrections before edition grouping

The reviewed inputs correct two nonempty truncated titles and eight source types before normal edition
identity and quality rules run. They also hold one exact PAM2018 source claim with unresolved full authorship.
All selectors bind the exact PI, source work/DOI, complete original and eligible-row preimages, ordered byline,
and owned primary bibliography or publication evidence. A stale positive correction fails closed.

## Reviewed changes

- W4306179722, DOI10.1145/3495243.3517021, and W3023980905, DOI10.1145/3372224.3380897:
  the same truncated `Experience` title falsely merged two distinct MobiCom papers. Exact owned PID61/1951-1
  records and complete eight-author primary citations supply the different full titles. The NianSun/NianXiangSun
  record-local form is source-attested; no global alias or person identity is created.
- Seven ZhuSongChun chapter sources have exact owned monograph/DOI/byline authority. Type-only projection
  makes the normal book rule fold them into their eligible book, increasing its folded chapters from5to12.
- ChenZhenpeng W7163740557 has a complete owned TOSEM research citation with the full ordered byline and DOI.
  Its article-type projection preserves the ordinary date. No fetched Crossref response, volume number,
  DOI hyperlink or general journal-page heading is asserted.
- LiZhenhua W2792053284, DOI10.1007/978-3-319-76481-8_8, is held by the existing exact-claim mechanism.
  Seven raw authorships disagree with the owned five-author record. Full originals and distinct source author
  identifiers are preserved; neither duplicate authors nor global IDs are resolved by names. Prior holds remain.

## Actual verification

Root replay32156505 matched all14 complete case sources/eligible rows, all16 scoped original PID objects,
and both original registered HTML capture rows. It projected the8types without changing dates, full bylines,
PI/member/link objects or raw sources. Copied-graph replay32156531 proved the exact PAM hold removes only
its own PI/source row and no direct candidate link.

The integrated code passed2783tests/23skipped, lint,19charters and history scan0findings in32156543.
Complete normal native32156623 then finished14m59, peak20231300KiB, using18frozen input files with exactly
two reviewed-slot replacements. It produced615PI-paper relations/611distinct source-work keys, with all
586member records,625role episodes and611candidate links unchanged. Verified member-paper links remain0.

Independent whole-graph comparison32156751 found only the seven chapter-row folds, the exact PAM hold,
the TOSEM type change and corresponding source-proof metadata changes. It initially held one additional
PI metadata delta: dynamic anchor A5144286967 disappeared from LiZhenhua. Root follow-up tied that anchor
to the exact held PAM source and proved identity.py/reviewed_claims.py byte-equal between builds. Every
other original source context and all other PI metadata apart from expected counts/funnel are unchanged.
No global author/person identifier was merged, redirected or deleted. The original HOLD receipt is retained.

Receipts and complete private packages are under scratch/tsinghua-source-type-root-integration-1108/:
INDEPENDENT-SOURCE-REPLAY.json, INDEPENDENT-HOLD-REPLAY.json, TYPE-COLD-NATIVE-COMPLETED.json,
INDEPENDENT-COLD-DELTA-RECEIPT.json and EXPLAINED-PAM-ANCHOR-DELTA.json.

These are corrective source inputs and code, not a normal package or release promotion. Other source,
edition/date and author-identity cases retain their review status. Full bibliography/student/copy coverage,
Stage9 accuracy certification and issued-ID/canonical promotion remain unfinished.
