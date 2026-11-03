# University of Chicago, stage 5: identity

Date: 2026-11-03. Gate (`atlas stage-gate uchicago 5`): **2 open of 124 PIs** (anchors: 58 DBLP, 45 DBLP + ORCID, 19 reviewed OpenAlex).

## What was done
- `dblp_ids_school.py` (job 32086533) and `homepage_links_school.py` (32086535); `census_build.py` re-run to fold `dblp-ids.json` into the census (friction 34).
- `oa_identity_school.py`: 17 people anchored by the computing-share identity rule, 2 by hand review (`reviewed/openalex-identity-review.json`):
  Gordon Kindlmann (A5045224825) and Bill/William Fefferman (A5040618965, ORCID 0000-0002-9627-0210).

## Open (hand judgement, not guessed)
- **Todd Dupont**: 8 DBLP candidates, none names the school; no OpenAlex author id of the name in the school sweep.
- **Anne Rogers**: 7 DBLP candidates, none names the school (one has 77 records in the window); no OpenAlex id in the sweep.
  Need a reviewed DBLP pid (homepage or coauthor evidence) or an OpenAlex id; the stage-5 gate accepts either.
`dblp_dump_persons.py` (shared output) was not run (needs `--allow-shared`).
