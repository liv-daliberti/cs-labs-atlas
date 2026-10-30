# vendor/: outside code the pipeline runs, copied into the repository

Until 2026-10-30 the collectors, the Princeton importer, several channels and the AI-writing study imported code
straight out of old working folders (`maxent-grpo/.research-sweeps/claude-*/tools`, `homogenizing-science/scripts`,
the site build's `scripts/`). That code is now here, **code only, never data**, one directory per origin:

| Directory | Origin | Files | Used by |
|---|---|---|---|
| `homogenizing_scripts/` | `homogenizing-science/scripts` (the world atlas) | 23 | the full-text collector `collect_princeton_fulltext_expanded.py` and its imports; `publications.py` for `cs_pi_works` |
| `cmu_tools/` | `.research-sweeps/claude-cmu-20261017/tools` | 6 | `collector_wrapper.py` (run by `fulltext-push/lab_first_loop.py`, `princeton_pass.sh`), `s2_key_lookup`, `core_search`, `arxiv_bulk`, `arxiv_oai`, `europepmc_lookup` (`ftp_common`, `lab_channels`, `labpage_channel`, `s2_title`, ai-writing) |
| `princeton_tools/` | `.research-sweeps/claude-princeton-20261015/tools` | 9 | `import_all_when_free.py` (the Princeton import path: `newsteps.slurm`, `chain_*.sh`, ...) and the package modules it imports (`cs_pi_works`, `cs_complete`, `cs_open_copies`, `cs_structure_catalog`); `cs_nsf_par`, `oar_index`, `catalog_snapshot` |
| `homogenization_tools/` | `.research-sweeps/claude-homogenization-20261019/tools` | 3 | `study_copies` (lab_channels pmc/figshare), `fulltext_store`, `homog` (ai-writing) |
| `epfl_tools/`, `mit_tools/` | the EPFL and MIT sweeps' `tools/` | 1 + 1 | `epfl_infoscience_rest`, `mit_dspace_rest` (lab_channels) |
| `princeton_listings/` | `.research-sweeps/claude-princeton-listings-20261022/scripts` | 2 | `extract`, `match` (tools/listed_not_in_census.py, tools/princeton_census.py) |
| `site_builder/` | `maxent-grpo/princeton-live-20261015/scripts` | 1 | `build-cs-hierarchy.py` (tools/school_profiles.py, tools/export_release.py) |

**Provenance.** `PROVENANCE.tsv` has one row per file: the vendored path, the source path, the source's sha256 when it
was copied, the vendored file's sha256, and the rewrites applied. Each file also starts with a one-line header naming its
source and sha256. The scripts import each other by bare module name, as before, so each directory goes on `sys.path`.

**What changed in the copies** (tools/vendor_sync.py, applied mechanically and recorded per file):
- code locations: `sys.path` entries and the collector's scripts directory point at the sibling `vendor/` directories;
- data locations: every absolute data path (a stage's `STAGE`, `ROOT`, `HERE`; the stores; the site collections) goes
  through `tools/atlas_paths.py` and gives the same directory under today's layout. The stages' data stays where it
  is (`atlas_paths.archive_sweep(<stage>)`) and follows the project move.
Nothing else: the logic is the original's, byte for byte.

**Checks.** `atlas vendor check` (`tools/vendor_sync.py check`): every vendored file matches its row (no unrecorded
edits; CI runs this with `--no-sources`), and every original is compared with its recorded sha256: **DRIFT** means the
original changed after it was copied (review the change, then `atlas vendor sync` and commit). Run it before switching
the download loops over.

**Retiring the originals.** The download loops on rinse still run the originals (`collector_wrapper.py` from the CMU
sweep each round). Do not move or delete them until every loop has been restarted on this code
(docs/ENVIRONMENT.md, "Switching the collectors over"). After that, every source path in `PROVENANCE.tsv` can be
retired (the sweeps go to `archive/sweeps/`), and vendor/ is the only copy: edit it directly and drop the file's entry
from `ORIGINS` in tools/vendor_sync.py (the provenance row stays as history).

Not vendored (the data they read stays outside the repository and is listed in docs/ENVIRONMENT.md): DBLP lists,
captures, rosters and census sources in the sweeps, and the site collections (`collection-<school>.json.gz`).
