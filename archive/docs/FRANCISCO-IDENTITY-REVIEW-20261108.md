# Francisco Romero identity review, 2026-11-08

This review resolves one stale Georgia Tech identity hold. The change is confined to Francisco Romero in `hierarchy/gatech/reviewed/census-overrides-school.json`; all 158 other local overrides are identical. The previous hold and its reason remain in review history.

The [official SCS profile](https://scs.gatech.edu/people/francisco-romero), source SHA256 `d04b88a99f1cc58a5ed5c238d73d6667f91f326a3ee35fed8806071c23dfcadf`, names the SCS assistant professor and directly links [his owned homepage](https://www.franciscoaromero.com/home). That homepage, source SHA256 `e4660e1d1c2780d7a62d97dce747c0e80fabcae35c6b7428923e76cb0d61577e`, identifies the same Georgia Tech faculty role and explicitly links DBLP PID `29/6093` and ORCID `0000-0001-6902-405X`. Original hrefs use Google Sites wrappers; the review verifies the literal raw hrefs and unwraps their `q` values without requesting either target. This is an institution-bound owned-source chain, not a same-name identity join.

The proposed input removes only `no_identity` and `why_no_identity` from this PI, adds the explicit owned PID and ORCID, and includes their source URL/hash/quote evidence. `dblp_orcid_review.allowed` permits only the independently owned ORCID. The official local DBLP record contains 32 publications and no ORCID; ownership of its bibliography does not authorize additional identifiers. No reviewed OpenAlex author ID is added.

The paired native census retains all 447 PI records, with all 446 other PIs identical. Francisco's periods remain empty and his unchanged captured faculty listings support 2026 only. No faculty start/end or earlier appointment is inferred from the homepage, old publications, or Stanford degree history. Website, lab, membership and period inputs are untouched.

Both sealed primary PDFs were rehashed and fully parsed again offline. Their exact source IDs/DOIs pass the normal native identity, school, appointment and paper-quality stages after the hold is resolved. The bounded exact-two-source replay admits zero papers before the correction and two afterward; it is not a full-school or career-paper build.

| Paper | Physical version | Pages | Native source byline | Actual PDF SHA256 |
|---|---|---:|---:|---|
| Halo | `2603.17668v1` | 14 | 5 | `6825c712c8c82fd9e3b3e5d157ea34736f5470bd9a630d245c7f3b6105dc1c10` |
| CodecSight | `2604.06036v4` | 14 | 9 | `d4715a529d9a12bba7f400c059daaadc919ad72640c3eab68f4af08b274f1a7c` |

CodecSight v4 is dated 2026-09-15 and names nine authors, including Anya Rajan. The older September 1 DBLP snapshot names eight authors; both version-specific source facts are preserved. The correction does not rewrite either byline, the OpenAlex work date 2026-04-07, edition pointers, or IDs. Halo v1 and its five-author byline are likewise retained.

The self-contained review receipts are in `scratch/francisco-identity-input-review-1108`: `source-replay-manifest.json`, `native-census-comparison.json`, `native-two-paper-replay.json`, and `checkpoint.sqlite`. Successful pinned-code replay job `32149202` completed in seven seconds (MaxRSS 479856 KB). Initial job `32149200` stopped on a missing bounded-replay context field; version two supplies the existing native `from_pw` field and preserves that diagnostic receipt. Source policy and original objects did not change.

The original sealed source packet remains under `scratch/explicit-held-paper-source-review-1108`. This input/report commit requires independent review before landing. No canonical package, registry, catalog, live source cache, or public copy was written. Hancock's genuine 2004 paper and 2016 reprint are a separate scratch-only date-review proposal.
