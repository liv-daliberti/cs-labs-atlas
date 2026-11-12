# Tsinghua: gitignored build inputs on main (2026-11-12, buildability worker)
Only reviewed/ and reports/ are git-tracked. A clean checkout needs these files in code/hierarchy/tsinghua and code/listings/tsinghua; they were copied into main on 2026-11-12 (owner approval: make Tsinghua rebuildable from main) and verified by sha256. `tools/input_manifest.py check tsinghua` re-verifies them against hierarchy/tsinghua/inputs-manifest.sha256.json.

| file (under code/) | bytes | sha256 | source |
|---|---|---|---|
| hierarchy/tsinghua/derived/census-faculty.json | 120 | d0810e00f8cc8276b34f0f2e8f8479330745f087f85f99f9a057f173a7aeb46d | scratch/tsinghua-source-type-root-integration-1108/native-git/hierarchy/tsinghua/derived (same sha as tmp/rb-1113) |
| hierarchy/tsinghua/derived/collection.json.gz | 5,666 | 4970c2e405dfa0ec1a5629f64572cd4a8ae83ebf09fec6aedc2871f3f2d90726 | same native-git dir |
| hierarchy/tsinghua/raw/openalex-sweep.sqlite | 564,531,200 | cb63d8851634a573be07801a00905e2c45b1ccc4b1ae4ab82ec2b5df25e4241a | same native-git dir; the sha equals the one recorded in derived/PROVENANCE.md (Slurm 32180189) |
| hierarchy/tsinghua/raw/pi-works.sqlite | 53,248 | 46dd3c6a408aa264fabf7b81ef0a9e4f82ddf72f03170055a9c777e51983b6bc | same native-git dir |
| hierarchy/tsinghua/raw/school-captures.sqlite | 5,500,928 | 251036e5750742acc1d865c72b91b033fea6649a9cf9ba0be78605962d49307d | same native-git dir; canonical (see below) |
| listings/tsinghua/derived/listings.json | 524,687 | e76356d6f931c936fb0eb6c7d5a3da5c12d90096271d38850fd9b35e9e942085 | hierarchy/tsinghua/tmp/rb-1113/listings/tsinghua/derived |

## The 120-byte census-faculty.json is the real input, not a stub
Its `faculty` list is empty by design: "All 207 persons supplied exactly once by reviewed census-additions.json" (610 kB, tracked). Without it, or with the wrong census, a build drops lab papers (7,901 vs 2,203). Do not "fill" it.

## Which school-captures.sqlite is canonical
Two different stores had the same name. Main's old file (sha e4a0692d..., 1,650,688 B, 2026-11-10: live 73, cdx 56, captures 38, js_render 2, live_transport 44) is a different lineage from the stage-0 native store (sha 251036e5..., live 578, robots 86, blocked 1, live_transport 258; no cdx/captures rows). Only 46 of main's 73 live URLs are in the 578; 27 are only in the old file. The build reads the store only through `pihier/source_metadata._cached_primary` (live table, by URL and body sha), and main's committed derived outputs (pis.json e32ed80c..., lab_papers a652f2da..., students 375e7e67...) are byte-identical to the build run on the 578-live store (tmp/rb-1113). The 578 store is therefore the one that reproduces main, and it is installed as school-captures.sqlite. Main's old file is kept unchanged as raw/school-captures-main-20261110.sqlite (a byte-identical copy was taken before the replacement); nothing was deleted.

## Rebuild verification from main (2026-11-12)
Private overlay (tools/overlay_root.py --private, code = main 793d325f-era, outputs deleted first), Slurm 32224041 (2 CPUs, 40 G, 13:53 wall, 20.8 GB peak RSS): pis.json, students.json, lab_papers.jsonl.gz and student_papers.jsonl.gz are sha256-identical to main's derived (359 PIs, 8,059 lab papers, 1,523 student papers, 820 lab-student pairs; no lab-paper drop). report.json differs only in provenance (builtAt, overlay paths, code commit). The 563 MB sweep was not opened by this build (no preflight requirement for Tsinghua), but is pinned by sha above.
Main's raw/school-captures.sqlite is an append-only store that a live collector (fetch.py) writes; it gained one live row at 10:08 on the day of the copy, so its sha moves (input_manifest.py reports it as a warning).
