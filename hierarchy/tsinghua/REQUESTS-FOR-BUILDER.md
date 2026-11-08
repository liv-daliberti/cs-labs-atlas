# Tsinghua native integration: CJK identity handling

2026-11-08, source review branch `agent/tsinghua-expansion-1108`.

Native identity fix integrated in `245c00f` (1,547 tests passed, 18 skipped). The reproducer below records the original failure at `b2e650f`; it is retained as the reason for the fix. Literal CJK identities and lab-scoped fallback member IDs are now preserved, and distinct same-name profiles require explicit disambiguation before downstream PI indexing. A full Tsinghua native trial and source-bound input integration remain required.

The 88 reviewed census additions use the exact public Chinese names from named official profiles. No English transliterations were inferred. A native smoke check against main b2e650f exposes a prerequisite shared-code fix:

```python
from collections import Counter
from pihier.census import merge_census_rows
from pihier.names import toks

assert toks('孙家广') == []
assert toks('顾明') == []
# rows = reviewed/census-additions.json
merged, _ = merge_census_rows(rows, {}, Counter())
print(len(rows), len(merged))  # 88 1
```

`merge_census_rows` constructs `nk = 'name:' + ' '.join(toks(name))` unconditionally. Every CJK-only name therefore shares `name: ` and merges into one person. `census_build.merge_people` also skips names with fewer than two Latin tokens; `pi_listings` rejects CJK-only surnames, and student external IDs strip non-Latin characters. Those paths need a consistent, source-name-preserving design, meaningful native regression tests, and a separately claimed shared-code change. Empty Latin token sets must never identify unrelated people. Same written Chinese names are not automatically the same identity either: the existing Tsinghua directory has two distinct 周强 profiles.

Do not work around this by guessing romanizations or by attaching every career bibliography record to a school. Public bilingual variants need explicit same-person source evidence. The two English-name IIIS DBLP decisions in this branch already carry independent citation anchors; all other identity/paper work remains open.

This branch changes reviewed inputs only. The root coordinator owns the fix landing and subsequent isolated native trial build, charter integration and canonical promotion.
