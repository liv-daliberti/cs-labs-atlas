# Slurm jobs in fulltext-push run from a code snapshot (docs/CONTRIBUTING.md), with this directory's DATA kept shared.
# Source after paths.sh:   . "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
# The modules here write their caches, logs, locks and reviews next to the code (raw/, checks/, logs/, review-*/,
# local-reuse/ident, ...: the OpenAlex budget log, the per-channel run_steps locks, the checks store). Left in a snapshot they
# would vanish with it, and the daily OpenAlex budget would be forgotten. So every entry of the main checkout's
# fulltext-push/ that the commit does not contain (all untracked data) is linked into the snapshot, one level down inside
# local-reuse/. Code stays the commit's; data stays shared. Use "$CS_ATLAS_FULLTEXT_PUSH" for the code, and logs/ is shared.
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || return 1
_m=$CS_ATLAS_CODE/fulltext-push
for _p in "$_m"/* "$_m"/local-reuse/*; do
  _n=${_p#"$_m"/}
  case $_n in __pycache__|*/__pycache__) continue;; esac
  [ -e "$CS_ATLAS_FULLTEXT_PUSH/$_n" ] || [ -L "$CS_ATLAS_FULLTEXT_PUSH/$_n" ] || ln -s "$_p" "$CS_ATLAS_FULLTEXT_PUSH/$_n"
done
unset _m _p _n
