#!/bin/bash
# Rebuild all six CS-hierarchy packages on Slurm: hierarchy/rebuild.sh with every stage (snapshot of the current counts,
# pi_hierarchy.py per school, the student/chain audits and link diagnosis, tests, the build regression check, copies,
# the dated release, and the organized tree from that release). Rule history: docs/RULES.md (2026-10-28: namesake,
# other-adviser, season dates, incoming listings, basis advisees, full-given-name advisers, advisee-at-school
# affiliation and rules, reviewed student corrections, coverage-review census additions; 2026-10-29: DBLP dump lists,
# mixed ids, edition bylines, page-1 ties for sweep hits, PI-as-own-student, advisee-initials guard, given-name guard,
# within-lab byline matching, unaffiliated-byline advisees). Check with `sbatch --test-only` first.
#SBATCH --job-name=cs-hier-rebuild
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=hierarchy/logs/rebuild-all-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_WORK"
# rebuild.sh takes its own code snapshot (tools/job_code_snapshot.sh) of CS_ATLAS_SNAPSHOT_COMMIT (`atlas submit` sets it to HEAD at submit time)
TAG=rebuild-$SLURM_JOB_ID exec bash hierarchy/rebuild.sh
