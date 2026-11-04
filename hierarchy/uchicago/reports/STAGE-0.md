# University of Chicago, stage 0: charter and config

Date: 2026-11-02. Protocol: `docs/ADDING-A-SCHOOL.md` v2.3. Branch `agent/uchicago` (not landed: release freeze). Status stays `onboarding`.

## What was done
- `atlas new-school uchicago --name "University of Chicago"`; charter `schools/uchicago.toml` (`atlas charters`: 8 charters ok).
- **Ids** (OpenAlex institutions table of the 2026-10-14 snapshot, no API credits; ROR at api.ror.org/v2, 2026-11-02):
  University of Chicago `I40347166`, ROR `024mw5h28`, lineage itself only. Related: Medical Center `I4210087865` (ROR 0076kfe04),
  TTIC `I160992636` (ROR 02sn5gb64; ROR relates it only to Toyota Technological Institute, Japan).
  Lineage children of I40347166 (also ROR children): Argonne National Laboratory and four Argonne facilities, Evanston Hospital,
  Chan Zuckerberg Biohub Chicago, CLEAR, two CNRS international laboratories.
- **Hosts:** `tools/school_hosts.py uchicago`: 10 hosts, 0 inconsistent, no challenge anywhere, no Disallow naming Claude's agents.
  linguistics.uchicago.edu names ClaudeBot in a `Crawl-delay: 10` group (allowed; 10 s binds us; tool fixed to apply it).
  math.uchicago.edu moved to mathematics.uchicago.edu. ttic.edu, math: robots.txt 404 (no rules). Booth disallows `/*.pdf` and some paths, not listings.
- **OpenAlex snapshot extension** for UChicago (`OA_EXT=uchicago`, jobs 32079155 array + 32079156 merge) writes `ext-uchicago.sqlite` beside the main store.
- **Gate** `atlas stage-gate uchicago 0`: charter ok, hosts ok; snapshot part pending the merge job.

## Owner decisions (2026-11-03, all three as recommended)
- **D1 yes:** UChicago Medical Center (`I4210087865`) is a related institution (Michigan Medicine precedent): an authorship tagged only with it counts when its raw
  affiliation names the university (the charter regex).
- **D2 yes:** TTIC is in scope as its own department; the pending mark is cleared (charter department, related id `I160992636`, host and regex alternative stay).
- **D3 (first 2026-11-03, superseded the same day):** Argonne (and its four facilities), Evanston Hospital and CZ Biohub Chicago stay in the lineage for the sweep; decide at stage 7.
- **D3 final (2026-11-03): "related".** Argonne National Laboratory and its four facilities, Evanston Hospital and CZ Biohub Chicago are treated like the Medical Center and Michigan Medicine: a work credited only to one of them counts for UChicago only when the author's raw affiliation names the university, or the PI has a documented joint appointment (cited). Charter: the seven ids are in `openalex_related`; filter, sweep and builder read them regex-only (per affiliation).
