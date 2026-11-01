# Architecture

One page on how the atlas is put together. Details live in the linked documents; this one says what talks to what.

## What it makes

For each school (a charter, `schools/<key>.toml`), the hierarchy **school -> department -> PI lab -> papers + students**
(docs/RULES.md, scope rules), with the evidence for every claim (url, sha256, verbatim quote), the lab papers' full-text
copies, and a ledger of why a paper has no copy. Seven schools: Princeton, CMU, EPFL, MIT, Berkeley, Stanford, Michigan.

## The four layers

```
 raw            collectors and capture tools write once                OpenAlex sweeps, pi-works, page captures,
                (tools/oa_sweep.py, mpcap.py, listings/, fulltext-push/)  DBLP pulls, listing captures, the stores
 reviewed       decisions with their evidence, in git                   overrides, corrections, researched evidence,
                (hierarchy/**/*-evidence.json, census/, periods/)        review files, labpage-additions + acceptance
 derived        the build makes it; never hand-edited                   packages, copies, ledger, audits, diagnoses
                (tools/pi_hierarchy.py and the stage tools)
 releases       immutable dated copies of derived + reviewed            releases/<id>/ + MANIFEST.json + CHANGES.md
                (tools/make_release.py)  -> consumers read these only
```

docs/DATA-LAYOUT.md has the kinds per file and the target directory split (not applied yet); `tools/atlas_paths.py` is the
only place that knows where anything is (`data(name, school)` for data files, slots for directories, `paths.sh` for shell).

## The build

`tools/pi_hierarchy.py <school>` is a thin entry point over `tools/pihier/`, one module per concern:

| module | rules (docs/RULES.md) | does |
|---|---|---|
| `census` | R-HIER | the PIs, their identity ids, reviewed inputs |
| `periods` | R-PAP-01..03, 13 | appointment periods and dated listings; departures (`faculty_end_moved`) |
| `identity` | R-PAP-04.. | which OpenAlex authorships are the PI's |
| `papers` | R-PAP | lab-paper rows; recovered sources (DBLP, lab page, accepted lab-page additions) |
| `students` | R-STU | students and their relations, each with a hashed source |
| `links` | R-LNK | student -> paper links |
| `names`, `common`, `build` | | name matching, shared readers, the report and the package writer |

Every rule has an id and a test named after it (`tests/test_rule_coverage.py`). Output per school: `pis.json`, `students.json`,
`lab_papers.jsonl.gz`, `student_papers.jsonl.gz`, `report.json` (counts + provenance: the hashed inputs). Equal provenance
means equal inputs, which is what the old-vs-new equivalence job relies on (`hierarchy/build-equivalence.slurm`).

After the build, in order (`hierarchy/rebuild.sh`, stages): `ids` (stable `atl:` ids, docs/IDS.md), `copies` and `ledger`
(from the stores, docs/UNAVAILABLE.md), `audits`, `evidence`, `tests`, `regression`, `validate` (schemas/, docs/DATA-DICTIONARY.md),
`release`, `tree`, `housekeeping`. A failed stage holds the release; regression swings hold it unless `ALLOW_SWINGS=1`.

## Adding to the build without editing it

Reviewed sources enter through named extension points, each gated: `students.RESEARCHED_FILES` and `papers.RECOVERED_KINDS`.
The lab-page additions (docs/LAB-PAGES.md) are read only when `hierarchy/<school>/labpage-acceptance.json` accepts that kind
and names the additions file by sha256, and accepted papers still obey the appointment periods.

## Collectors and the stores

`fulltext-push/` is the downloads side: discovery channels as plugins (`channels/`, docs/CHANNELS.md), one download loop per
school (`lab_first_loop.py`, run as a Slurm job by `downloads.slurm`), and per-school stores `stores/<school>/` (docs/STORES.md:
`catalog.sqlite`, content-addressed `objects/`, one writer per catalog through `catalog_lock.py`). The loops are supervised:
SIGTERM-clean, idle backoff, and a generated status page `hierarchy/COLLECTORS-STATUS.md`. Collectors run under
`COLLECTOR_PY`; the build under the project interpreter `env/atlas` (docs/ENVIRONMENT.md).

## Schools are mechanical

A school is a charter plus `atlas stage-gate <key>` runs through the ten stages of docs/ADDING-A-SCHOOL.md; the stage tools
(`tools/*_school.py`, `sweep_school.py`, `census_build.py`) take the key. The one-school scripts of the first six schools are
in `archive/` (docs/SCRIPT-MAP.md).

## Consumers

The organized tree (`schools/`), the public export (`tools/export_release.py` -> GitHub `main`, tags `release-<id>`), the
site, and the Hugging Face dataset all read a release, never the working packages.

## Where things live

| | |
|---|---|
| `code/` (git `main`; worktrees in `worktrees/`) | code, docs, reviewed inputs, data under `hierarchy/` (git-ignored) |
| `releases/`, `schools/`, `export/`, `site/` | outputs and consumers |
| `stores/`, `cache/`, `external/` | full-text stores, API caches, DBLP dump |
| `scratch/` | throw-away work; `tools/scratch.py` cleans it |
| `archive/` | history, relocation records (`archive/migrations/`) |
| `env/atlas` | the pinned interpreter |

How to work on it: docs/CONTRIBUTING.md. How to run and recover it: docs/RUNBOOK.md.
