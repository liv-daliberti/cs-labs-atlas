#!/bin/bash
#SBATCH --job-name=nsf-par
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=24:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/nsf-par-%j.out
# 2026-11-04 NSF Public Access Repository titles for the US schools not yet searched (nsf_par_lab.py: one exact-title phrase
# search per 3 s, robots.txt sets no rule, cached by normalized title in raw/nsf_par.sqlite; paywalled publishers first).
# LIMIT=N caps the searches (the pilot); the candidates are written by `nsf_par_lab.py add` (catalog lock) once the search ends.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1  # submit from the code root
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
S=${SCHOOLS:-stanford michigan uchicago}
"$CS_ATLAS_COLLECTOR_PY" -I -u nsf_par_lab.py search $S ${LIMIT:+--limit=$LIMIT} < /dev/null
[ -n "$ADD" ] && "$CS_ATLAS_COLLECTOR_PY" -I -u nsf_par_lab.py add $S < /dev/null
echo '{"nsf-par": "done"}'
