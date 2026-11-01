#!/bin/sh
# Refresh round of the lab-paper push (after chain_others.sh): the hierarchy's lab-paper lists keep growing, so new lab
# papers are added to their catalogs and every school's cheap channels run again on what is still missing (cached
# lookups: OpenAlex records, arXiv listing, S2 batch, CORE answers; only new papers cost requests). Waits for
# chain_others.sh ($1 = its pid) so nothing overlaps; run_steps.sh serializes the arXiv bulk users.
# log -> logs/chain-refresh.log
cd "$(dirname "$0")"
. ../paths.sh  # every path in one place (tools/atlas_paths.py)
[ -n "$1" ] && while kill -0 "$1" 2>/dev/null; do sleep 60; done
PY="${CS_ATLAS_COLLECTOR_PY} -I -u"
nice -n 5 $PY berkeley_catalog.py
for s in mit cmu epfl princeton; do nice -n 5 $PY add_works.py $s; done
NW=$(ls -d $CS_ATLAS_STORES/princeton/discovery/claude-labpapers-newworks-*/ | xargs -n1 basename | sed 's/^/cs_pi_works:/')
(${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $NW)
./run_steps.sh berkeley proceedings arxiv_title s2 core techrpt pubpages >> "$CS_ATLAS_FT_LOGS"/steps-berkeley.log 2>&1
./run_steps.sh mit oa_arxiv openalex proceedings arxiv_title s2 core >> "$CS_ATLAS_FT_LOGS"/steps-mit.log 2>&1
./run_steps.sh cmu oa_arxiv openalex proceedings arxiv_title s2 core >> "$CS_ATLAS_FT_LOGS"/steps-cmu.log 2>&1
./run_steps.sh epfl oa_arxiv openalex proceedings arxiv_title s2 core infoscience >> "$CS_ATLAS_FT_LOGS"/steps-epfl.log 2>&1
./run_steps.sh princeton oa_arxiv openalex proceedings arxiv_title s2 core >> "$CS_ATLAS_FT_LOGS"/steps-princeton.log 2>&1
./princeton_pass.sh >> "$CS_ATLAS_FT_LOGS"/princeton-pass.log 2>&1
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"chain_refresh\": \"done\"}"
