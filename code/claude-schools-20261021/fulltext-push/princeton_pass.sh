#!/bin/sh
# Princeton lab papers (2026-10-22): import the push's candidate packages (discovery/claude-labpapers-<step>-<stamp>/)
# through Princeton's own import path (claude-princeton-20261015/tools/import_all_when_free.py cs_open_copies:<package>,
# which waits for a safe supervisor phase and the free .collector.lock), then one collector pass, restricted to the lab
# works those packages name (--work-ids), with the unchanged collector through the CMU stage's collector_wrapper.py
# (per-host pacing, robots.txt, 6 s for web.archive.org, the identity check). Skipped while a Princeton supervisor is
# collecting. Resumable: imported packages carry a catalog receipt; the collector skips tried URLs.
# log -> logs/princeton-pass.log
cd "$(dirname "$0")"
[ -f raw/downloads_stopped_for_disk ] && { echo '{"skipped": "downloads stopped: /n/fs/similarity under 150 GB free (disk_guard.sh)"}'; exit 0; }
PY=/usr/local/anaconda3/2024.02/bin/python
PRIN=/n/fs/similarity/maxent-grpo/.research-sweeps/claude-princeton-20261015
OUT=/n/fs/similarity/homogenizing-science/data/fulltext/princeton
WRAPPER=/n/fs/similarity/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools/collector_wrapper.py
pk=$(ls -d $OUT/discovery/claude-labpapers-*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && (cd $PRIN && $PY -u tools/import_all_when_free.py $pk)
ls $OUT/discovery/claude-labpapers-*/work-ids.txt >/dev/null 2>&1 || exit 0
cat $OUT/discovery/claude-labpapers-*/work-ids.txt | sort -u > raw/princeton-lab-work-ids.txt
if $PY -I -c "import json,sys; s=json.load(open('$OUT/run-state.json')); sys.exit(0 if s.get('status')=='running' and s.get('phase')=='collecting' else 1)"; then
  echo '{"skipped": "a Princeton supervisor is collecting"}'; exit 0
fi
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"princeton_pass\": \"start\", \"work_ids\": $(wc -l < raw/princeton-lab-work-ids.txt)}"
cd /n/fs/similarity/homogenizing-science/scripts && nice -n 10 $PY -u $WRAPPER --out $OUT --skip-candidate-import --workers 8 \
  --work-ids /n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/fulltext-push/raw/princeton-lab-work-ids.txt \
  | grep --line-buffered -v '"queue_progress"'
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"princeton_pass\": \"done\"}"
