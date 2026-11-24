#!/bin/bash
# Apply the DOI work aliases (ROADMAP #28) school by school, with the coverage counted before and after each (tools/lab_paper_copies.py);
# stops at the first school whose coverage drops. SCHOOLS is the order (default: Berkeley last). Run from a code snapshot of main's HEAD.
#   SCHOOLS="mit princeton" sbatch --export=ALL hierarchy/alias-apply.slurm      (use `sbatch --test-only` first)
#SBATCH --job-name=cs-alias-apply
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00
set -u -o pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
SCHOOLS=${SCHOOLS:-stanford mit epfl princeton cmu berkeley}
cov() { "$CS_ATLAS_PY" -c "import sys,json; sys.path.insert(0,'$CS_ATLAS_TOOLS'); import atlas_paths as P; s=json.load(open(P.data('copies.json','$1')))['summary']; print(s['local'], s['lab_papers'])"; }
for s in $SCHOOLS; do
  echo "== $s $(date +%T)"
  nice -n5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/lab_paper_copies.py" "$s" > /dev/null || exit 1
  before=$(cov "$s")
  nice -n5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/catalog_alias.py" "$s" --apply || exit 1
  nice -n5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/lab_paper_copies.py" "$s" > /dev/null || exit 1
  after=$(cov "$s")
  echo "COVERAGE $s before=[$before] after=[$after]"
  [ "${after%% *}" -ge "${before%% *}" ] || { echo "coverage dropped for $s: stop"; exit 1; }
done
echo "== done $(date +%T)"
