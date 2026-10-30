#!/bin/bash
# Local-reuse inventory, pass 1 (2026-10-29): list every *.pdf in the bounded source folders the owner named, one
# folder at a time (sequential), find -maxdepth 6, under nice/ionice idle. Symlinks are not followed (find default).
# Skipped: data/fulltext/*/objects (the stores themselves) - none of the folders below contains them.
# -> lists/<label>.tsv  (bytes \t path), logs/find.log
#SBATCH --job-name=localreuse-find
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=08:00:00
#SBATCH --output=fulltext-push/local-reuse/logs/find-%j.out
set -u
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
HERE=${CS_ATLAS_FULLTEXT_PUSH}/local-reuse
R=${CS_ATLAS_SWEEPS}
HS=${CS_ATLAS_WORLD_ATLAS}
dirs=(
  "$R/release-20261023/huggingface/papers"
  ${CS_ATLAS_RESEARCH_LIBRARY}
)
for d in "$R"/mit-* "$R"/princeton-hunt-* "$R"/princeton-claude-labs-publish-* "$R"/princeton-deep-* \
         "$R"/local-reuse-integration-* "$R"/cs300-* "$R"/cs19-* "$R"/cs11-* "$R"/cs10-* "$R"/cs18-* \
         "$R"/homogenizing-cs21 "$R"/homogenizing-cs-next "$R"/claude-homogenization-20261019 "$R"/claude-labrecords-20261019 \
         "$R"/claude-cmu-20261017 "$R"/claude-epfl-20261019 "$R"/claude-mit-20261020 "$R"/claude-berkeley-20261021 \
         "$R"/claude-stanford-20261027 "$R"/claude-princeton-20261015 "$HS"/.work/* "$HS"/data/enrichment; do
  [ -d "$d" ] && dirs+=("$d")
done
for d in "${dirs[@]}"; do
  label=$(echo "${d#/n/fs/resemble/}" | tr '/' '_')
  out="$HERE/lists/$label.tsv"
  [ -s "$out.done" ] && continue
  t0=$(date +%s)
  nice -n 15 ionice -c3 find "$d" -maxdepth 6 -type f -name '*.pdf' -not -path '*/data/fulltext/*/objects/*' -printf '%s\t%p\n' > "$out.part" 2>>"$HERE/logs/find.err"
  mv "$out.part" "$out"
  echo "{\"dir\": \"$d\", \"pdfs\": $(wc -l < "$out"), \"seconds\": $(( $(date +%s) - t0 ))}" | tee -a "$HERE/logs/find.log" > "$out.done"
  sleep 2
done
echo '{"find": "done"}' >> "$HERE/logs/find.log"
