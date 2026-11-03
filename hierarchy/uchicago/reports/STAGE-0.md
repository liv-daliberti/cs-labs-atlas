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

## Owner decisions requested
- **D1 Medical Center as related** (Michigan Medicine precedent, decided 2026-10-30): authorships tagged only with UChicago Medical Center count when the raw
  string matches the regex ("University of Chicago Medicine/Medical Center", "UChicago Medicine"). Recommended: yes.
- **D2 TTIC in scope?** Evidence: TTIC is a separate, philanthropically endowed institution on the university's campus (about page; ROR/OpenAlex: no relation
  to UChicago); every faculty member is computing (coverage "full"); its faculty and the CS department share people (overlap measured in stage 1 report).
  Charter currently includes TTIC as department + related id + regex alternative, marked pending. Recommended: in scope as its own department; if declined,
  remove the `I160992636` related id, the TTIC department, host and regex alternative.
- **D3 Argonne and the other lineage children.** The lineage sweep returns every Argonne authorship (tens of thousands of works). Options: (a) keep the lineage
  whole (an Argonne byline of a UChicago PI is also tagged UChicago; non-PI Argonne staff never become PIs); (b) list I1282105669, I4387156069,
  I4390039281, I4390039261, I4390039288, I4210119687, I4396570630 as `openalex_excluded` (note the snapshot filter drops an authorship that touches any
  excluded id, which would also drop joint UChicago+Argonne bylines like Ian Foster's). Recommended: (a) for the sweep, and decide at stage 7.
