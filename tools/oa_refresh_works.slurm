#!/bin/bash
# Refresh the recent OpenAlex works (tools/oa_refresh_works.py, docs/RUNBOOK.md "Refresh the recent OpenAlex works"): the API step, one stream, credits capped.
#   atlas submit tools/oa_refresh_works.slurm      with OA_ARGS="fetch princeton cmu ... --years 2026 --cap 900" in the environment (default below)
# Network-bound (one request per ~1.5 s), so 1 CPU. Writes only to <SCRATCH>/oa-refresh-<tag>/ and the ledger raw/openalex_budget.jsonl; the merge step is local.
#SBATCH --job-name=oa-refresh-works
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --output=fulltext-push/logs/oa-refresh-works-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
# shellcheck disable=SC2086
"$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/oa_refresh_works.py" ${OA_ARGS:-fetch princeton cmu epfl mit berkeley stanford michigan uchicago gatech --years 2026 --cap 900}
