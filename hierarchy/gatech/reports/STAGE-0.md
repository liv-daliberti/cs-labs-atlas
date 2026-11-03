# Georgia Institute of Technology, stage 0: charter and config

Date: 2026-11-03. Protocol: `docs/ADDING-A-SCHOOL.md` v2.3. Branch `agent/gatech` (from `agent/uchicago`; not landed). Status stays `onboarding`.

## What was done
- `atlas new-school gatech`; charter `schools/gatech.toml` (`atlas charters`: 9 charters ok, regex tested against 10 match / 13 non-match strings).
- **Ids** (OpenAlex institutions table of the 2026-10-14 snapshot, no API credits; ROR at api.ror.org/v2, 2026-11-03): Georgia Institute of Technology `I130701444`,
  ROR `01zkghx44`, lineage itself only. Lineage children (also ROR children): GTRI `I4388482740`, Georgia Tech-CNRS Laboratory `I4210089931` (Metz),
  Wallace H. Coulter BME Department `I2802612298` (joint with Emory), Center for Translational Research in Neuroimaging and Data Science `I4210133909`, Georgia Space Grant
  Consortium `I4210101104`. Related, not lineage: Georgia Tech-Europe `I1288283403` (ROR 02m5dy175, Metz). Not swept: Georgia Tech Foundation, Tools for Life.
  No OpenAlex institution exists for the Shenzhen institute.
- **Hosts:** `tools/school_hosts.py gatech`: 14 hosts, 0 inconsistent, no challenge, no robots rule naming Claude's agents anywhere; math.gatech.edu has `Crawl-delay: 10` for `*`.
  BME has no `/people` or `/faculty` page (404): its directory URL is found at stage 2 only if needed.
- **Snapshot extension** (`OA_EXT=gatech`, jobs 32085755 array + 32085756 merge, `--from-worktree`) writes `ext-gatech.sqlite`.
- Wayback coverage seen in stage-1 prep (`discover_listings.py`): www.cc.gatech.edu/people/faculty, scs.gatech.edu/people/faculty and cse.gatech.edu/people/faculty have captures
  in nearly every half-year 2016-2026; `ic.gatech.edu/people/faculty` has 2016H1 then nothing until 2023H2 (IC needs another URL era, likely www.ic.gatech.edu or cc.gatech.edu pages);
  `scp.cc.gatech.edu` starts 2023-12 (the school was founded 2022-23); ECE `/directory` is patchy before 2023; ISyE `/people/faculty` starts 2023.
- **Snapshot extension done** (2026-11-03, 17 jobs COMPLETED, merge 41 s): `ext-gatech.sqlite`, 202,525 works. `atlas stage-gate gatech 0`: **pass** (14 hosts, 202,471 snapshot works).

## Evidence for the owner decisions (works in ext-gatech.sqlite, 2016-2026; authorship-level institution tags)
| institution | works tagged | of which GT's own id absent from the work |
|---|---|---|
| Georgia Tech (I130701444) | 199,901 | - |
| GTRI | 3,941 | 1,576 |
| Coulter BME dept | 7,020 | 231 |
| Georgia Tech-CNRS Lab (Metz) | 1,362 | 548 |
| Georgia Tech-Europe (related) | 1,105 | 510 |
| CTRN (GT/Emory/GSU centre) | 1,376 | 216 |
| Georgia Space Grant Consortium | 1 | 1 |

## Owner decisions needed (nothing below is applied beyond the recommended draft in the charter)
- **D1 departments.** In: the four College of Computing schools (CS, IC, CSE, CSP) as full-coverage departments; ECE and ISyE as `affiliated` (computing faculty by the share test); ML Center, Math, BME
  as searched units. Cybersecurity and Privacy has no pre-2022 listing by construction (founded 2022-23; its faculty sat in CS/ECE before), so it needs `listing_gaps` for 2016-2021 and stage 4 periods from the
  other schools' listings. Recommendation: yes as drafted.
- **D2 related institutions.** GTRI is a UARC, a separate employer of research staff (not faculty); 1,576 of its 3,941 works lack GT's own id. Georgia Tech-Europe / Georgia Tech-CNRS (Metz) are overseas units with
  few Atlanta faculty. Shenzhen: Georgia Tech Shenzhen Institute is a Tianjin University entity and the partnership ended Sept 2024; no OpenAlex id. Recommendation: GTRI, GT-Europe, GT-CNRS are out of PI scope
  (no PIs from them unless a person holds a GT faculty listing), and the regex excludes "Georgia Tech Shenzhen". Keep them in the sweep for now; decide `openalex_excluded` at stage 7 (the per-affiliation filter makes exclusion safe for joint bylines).
- **D3 ids.** Keep lineage `I130701444` only as primary; Coulter BME stays in (a GT department, joint with Emory); recommend excluding CTRN and the Space Grant Consortium (a tri-university centre and a
  consortium, not GT departments). `openalex_related` currently holds GT-Europe only (swept so D2 has data); recommend dropping it from related once D2 is settled, since Europe-only authorships would otherwise count by regex.
- **D4 Shenzhen regex** (`georgia tech` not followed by Shenzhen): confirm.
