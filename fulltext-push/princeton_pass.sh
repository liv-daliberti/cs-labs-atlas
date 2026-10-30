#!/bin/sh
# Princeton lab papers (2026-10-22): import the push's candidate packages (discovery/claude-labpapers-<step>-<stamp>/)
# through Princeton's own import path (claude-princeton-20261015/tools/import_all_when_free.py cs_open_copies:<package>,
# which waits for a safe supervisor phase and the free .collector.lock), then one collector pass, restricted to the lab
# works those packages name (--work-ids), with the unchanged collector through the CMU stage's collector_wrapper.py
# (per-host pacing, robots.txt, 6 s for web.archive.org, the identity check). Skipped while a Princeton supervisor is
# collecting. Resumable: imported packages carry a catalog receipt; the collector skips tried URLs.
# log -> logs/princeton-pass.log
cd "$(dirname "$0")"
. ../paths.sh  # every path in one place (tools/atlas_paths.py)
[ -f raw/downloads_stopped_for_disk ] && { echo '{"skipped": "downloads stopped: /n/fs/similarity under 150 GB free (disk_guard.sh)"}'; exit 0; }
PY=${CS_ATLAS_COLLECTOR_PY}
OUT=$CS_ATLAS_STORES/princeton
WRAPPER=$CS_ATLAS_VENDOR/cmu_tools/collector_wrapper.py  # vendored (tools/vendor_sync.py)
pk=$(ls -d $OUT/discovery/claude-labpapers-*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && ($PY -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $pk)
ls $OUT/discovery/claude-labpapers-*/work-ids.txt >/dev/null 2>&1 || exit 0
cat $OUT/discovery/claude-labpapers-*/work-ids.txt | sort -u > raw/princeton-lab-work-ids.txt
if $PY -I -c "import json,sys; s=json.load(open('$OUT/run-state.json')); sys.exit(0 if s.get('status')=='running' and s.get('phase')=='collecting' else 1)"; then
  echo '{"skipped": "a Princeton supervisor is collecting"}'; exit 0
fi
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"princeton_pass\": \"start\", \"work_ids\": $(wc -l < raw/princeton-lab-work-ids.txt)}"
cd "$CS_ATLAS_VENDOR/homogenizing_scripts" && nice -n 10 $PY -u $WRAPPER --out $OUT --skip-candidate-import --workers 8 \
  --work-ids $CS_ATLAS_FULLTEXT_PUSH/raw/princeton-lab-work-ids.txt \
  | grep --line-buffered -v '"queue_progress"'
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"princeton_pass\": \"done\"}"
