# Zhejiang admission review, 2026-11-09

Branch `agent/zju-admit-1109` (task T014). Data-only review of the sealed first native (job 32157747); no registry, ID, release or site change.

## API-anchor clusters (713 relations, 33 clusters)

Rule: an OpenAlex author id is judged by the ORCID it carries in the stored original work records against the ORCIDs on the PI's source-bound DBLP person record (R-PAP-04/06). Evidence per id: the stored work record (url, sha256, literal ORCID quote) and the DBLP record (url, sha256, ORCID quote).

| Class | Clusters | Relations | Action |
|---|---|---|---|
| ORCID matches the PI's DBLP ORCID | 5 | 27 | stay anchored |
| ORCID conflicts, id also holds DBLP-DOI-verified works of the PI | 22 | 678 | `mixed_openalex` (R-PAP-06: per-work evidence needed) |
| ORCID conflicts, no verified work under the id | 2 | 3 | `not_openalex` |
| no ORCID on the id | 4 | 5 | 4 held per claim (陈为), 1 Shen computing work kept (full name, id carries 5 DBLP-verified works) |

The 678 + 3 relations are namesake works (food chemistry, mechanics, oncology, psychiatry, materials) of other people named Wei Chen. Seven per-claim holds are in `paper-claim-review.json`: 4 no-ORCID weak anchors, 2 retraction-marked IEEE T-IV records (R-PAP-17), 1 psychology work under a ORCID-matching but conflated id.

## 13 flagged intersections

Eleven are DOI-identical to the DBLP record with only a title revision (arXiv retitling, subtitle truncation, a "k" lost in OpenAlex); accepted as the same work. The review-article row (J. Visualization 2020) is a paper under R-PAP-18 (surveys stay). The two "Retracted:" T-IV rows are held (above).

## PI identity coverage

A pinned-dump scan (12,928,181 records, sha256 22f96052...) for homepage records with a zju.edu.cn URL or Zhejiang affiliation (3,406) was joined to the 57 PI profile URLs on exact normalized URL. Eight PIs newly bound (DBLP person record lists the exact official profile URL, compatible name, Zhejiang affiliation): 周晓巍, Minjian Zhao, Kui Ren, 章国锋, 林海, 王锐, Feng Lin, 刘玉生. Bound PI contexts 6 -> 14. ORCID inheritance stays unallowed.

## Re-run native (job 32175508, isolated, offline, code ad5b63f)

Completed 11:10, exit 0, MaxRSS 20.5 GB; all five package schemas validate (0 errors) with the schema fix; 128 protected registry/canonical paths unchanged; 0 verified student links. Chained `afterany` behind the SJTU natives. Output: `scratch/zju-admit-1109/native-v5/package/zju/` (not promoted).

| | first native | re-run |
|---|---|---|
| PI-paper relations | 1,169 | 598 |
| distinct works | 1,154 | 576 |
| PIs with papers | 6 | 12 |
| namesake weak anchors surviving | 713 | 27 (26 ORCID-matched, 1 Shen) |

The target of 2,500 distinct papers is not met: the first native's total was inflated by ~680 namesake works, and 94 of 112 PIs still have no admitted bibliography identity (2 of the 8 newly bound PIs yield no 2016-2026 paper under their 2026-listing-only periods).

## Spot check (fixed seed 20261109, 50 rows)

Machine-assisted, not the hand-checked 105-judgment gate sample. 46 of 50 are DBLP-DOI/ORCID identified with a Zhejiang byline and computing venue; 4 are conditional (three cross-affiliated bylines Adobe/Alibaba/Ant Group, one anchored Kui Ren hardware-security row).
