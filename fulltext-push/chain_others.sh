#!/bin/sh
# Steps 2-4 of the lab-paper full-text push for MIT, CMU, EPFL and Princeton (after Berkeley's channels; run_steps.sh
# serializes every channel run, so only one process ever uses the arXiv bulk copy):
#   2  add_works.py <school>: lab papers no catalog work matches become queued works (Princeton: package + import)
#   3/4 lab_channels.py steps on every lab paper without a copy (queued and needs_access_review alike): the paper's own
#      arXiv id and OpenAlex locations, the arXiv title match, Semantic Scholar, PMC, CORE (+ Figshare/KiltHub at CMU,
#      Infoscience REST at EPFL); last, Wayback copies of ACM DL PDFs (slow: 8 s per lookup).
# The school's running collector loop reaches the new candidates in its next pass; Princeton gets princeton_pass.sh.
# log -> logs/chain-others.log
cd "$(dirname "$0")"
. ../paths.sh  # every path in one place (tools/atlas_paths.py)
PY="${CS_ATLAS_COLLECTOR_PY} -I -u"
for s in mit cmu epfl princeton; do nice -n 5 $PY add_works.py $s; done
NW=$(ls -d $CS_ATLAS_STORES/princeton/discovery/claude-labpapers-newworks-*/ | xargs -n1 basename | sed 's/^/cs_pi_works:/')
(${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $NW)
./run_steps.sh mit oa_arxiv openalex proceedings arxiv_title s2 pmc core >> "$CS_ATLAS_FT_LOGS"/steps-mit.log 2>&1
./run_steps.sh cmu oa_arxiv openalex proceedings arxiv_title s2 pmc figshare core >> "$CS_ATLAS_FT_LOGS"/steps-cmu.log 2>&1
./run_steps.sh epfl oa_arxiv openalex proceedings arxiv_title s2 pmc core infoscience >> "$CS_ATLAS_FT_LOGS"/steps-epfl.log 2>&1
./run_steps.sh princeton oa_arxiv openalex proceedings arxiv_title s2 pmc core >> "$CS_ATLAS_FT_LOGS"/steps-princeton.log 2>&1
./princeton_pass.sh >> "$CS_ATLAS_FT_LOGS"/princeton-pass.log 2>&1
for s in berkeley mit cmu epfl princeton; do ./run_steps.sh $s wayback_acm >> "$CS_ATLAS_FT_LOGS"/steps-$s.log 2>&1; done
./princeton_pass.sh >> "$CS_ATLAS_FT_LOGS"/princeton-pass.log 2>&1
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"chain_others\": \"done\"}"
