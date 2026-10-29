#!/bin/bash
# Rebuild all six CS-hierarchy packages, then the student and chain audits (2026-10-28: namesake, other-adviser,
# season dates, incoming listings, basis advisees, full-given-name advisers, advisee-at-school affiliation and
# rules, reviewed student corrections, coverage-review census additions; 2026-10-29: DBLP dump lists, mixed ids, edition
# bylines, page-1 ties for sweep hits, PI-as-own-student, advisee-initials guard, given-name guard, within-lab byline
# matching, unaffiliated-byline advisees). Packages are backed up first.
#SBATCH --job-name=cs-hier-rebuild
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/hierarchy/logs/rebuild-all-%j.out
set -u
cd /n/fs/resemble/cs-atlas/work
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
B=hierarchy/logs/pkg-before-rebuild-$SLURM_JOB_ID
for s in princeton cmu epfl mit berkeley stanford; do
  mkdir -p $B/$s && cp hierarchy/$s/{pis.json,students.json,report.json,lab_papers.jsonl.gz,student_papers.jsonl.gz} $B/$s/
done
rm -f hierarchy/*/link-diagnosis.json  # stale diagnoses would hide open items from the re-diagnosis
for s in ${SCHOOLS:-princeton cmu epfl mit berkeley stanford}; do echo "== $s $(date +%T)"; $PY -u tools/pi_hierarchy.py $s || echo "FAILED $s"; done
echo "== student audit $(date +%T)"; $PY -u tools/student_audit.py princeton cmu epfl mit berkeley stanford > /dev/null
echo "== chain audit (open items) $(date +%T)"; $PY -u tools/chain_audit.py > /dev/null
echo "== link diagnosis $(date +%T)"; $PY -u tools/link_diagnosis.py princeton cmu epfl mit berkeley stanford || true
echo "== chain audit $(date +%T)"; $PY -u tools/chain_audit.py
echo "== done $(date +%T)"
