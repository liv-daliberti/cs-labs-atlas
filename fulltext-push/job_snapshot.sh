# Slurm jobs in fulltext-push run from a code snapshot (docs/CONTRIBUTING.md). Source after paths.sh:
#     . "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || return 1
# The data these modules keep (raw/, checks/, logs/, local-reuse/ data, review-<stamp>/) is reached through the atlas_paths slots
# FT_RAW, FT_CHECKS, FT_LOGS, FT_LOCAL_REUSE and ft_review() (shell: $CS_ATLAS_FT_*), which point at the main checkout, so the
# snapshot needs no links. Use "$CS_ATLAS_FULLTEXT_PUSH" for the code. (Symlink loop removed 2026-10-31.)
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || return 1
