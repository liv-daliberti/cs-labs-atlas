#!/bin/bash
#SBATCH --job-name=anchors-stage5
#SBATCH --partition=all
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=00:58:00
#SBATCH --output=hierarchy/logs/anchors-stage5-%j.out
# One stage-5 identity step for one school: STEP=ids|persons|links|stats  SCHOOL=<key>   (submit with `atlas submit --export=ALL,STEP=..,SCHOOL=.. hierarchy/anchors-stage5.slurm`)
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
cd "$CS_ATLAS_WORK"
: "${STEP:?}" "${SCHOOL:?}"
T="$CS_ATLAS_TOOLS"
case $STEP in
  ids) nice -n 5 $CS_ATLAS_PY -u "$T/dblp_ids_school.py" "$SCHOOL" ;;
  persons) nice -n 5 $CS_ATLAS_PY -u "$T/dblp_dump_persons.py" "$SCHOOL" ;;
  links) nice -n 5 $CS_ATLAS_PY -u "$T/homepage_links_school.py" "$SCHOOL" ;;
  stats) nice -n 5 $CS_ATLAS_PY -u "$T/cs_related_candidates.py" --no-venues --stats --out cs-related-candidates-openalex.json "$SCHOOL" ;;
  oa) nice -n 5 $CS_ATLAS_PY -u "$T/oa_identity_candidates.py" "$SCHOOL" && nice -n 5 $CS_ATLAS_PY -u "$T/oa_identity_school.py" "$SCHOOL" --dry-run ;;
  oareal) nice -n 5 $CS_ATLAS_PY -u "$T/oa_identity_school.py" "$SCHOOL" ;;
  *) echo bad STEP; exit 2 ;;
esac
