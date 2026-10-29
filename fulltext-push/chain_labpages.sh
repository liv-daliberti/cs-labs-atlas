#!/bin/sh
# Lab-pages round (2026-10-26), after chain_refresh.sh ($1 = its pid; nothing overlaps): Berkeley's and CMU's lab-paper
# lists were rebuilt while chain_refresh ran (berkeley 22:55Z, cmu 23:17Z), so their new lab papers are added to the
# catalogs (add_works.py at every school, as lists keep growing) and get the cheap channels first; then every school gets the lab-publication-page channel (labpages), the
# PI-homepage fallback (pihomes), Princeton's OAR index (oar), MIT's DSpace handles (dspace, which resolves the
# handles the labpages / mit_oa_articles steps added); Princeton's packages are imported and collected last.
# run_steps.sh serializes every channel run (one arXiv-bulk user at a time).   log -> logs/chain-labpages.log
cd "$(dirname "$0")"
# wait for chain_refresh.sh's channel runs to end (its last one is Princeton's; its final Princeton collector pass may
# still be running - collectors run beside channel steps as usual)
[ -n "$1" ] && while kill -0 "$1" 2>/dev/null && ! grep -q '"done": "princeton oa_arxiv openalex proceedings arxiv_title s2 core"' logs/steps-princeton.log.since-$1 2>/dev/null; do
  awk -v t="2026-10-26T23:30" 'index($0, "\"at\": \"") && substr($0, index($0, "\"at\": \"") + 7, 16) >= t' logs/steps-princeton.log > logs/steps-princeton.log.since-$1 2>/dev/null
  sleep 60
done
rm -f logs/steps-princeton.log.since-$1
PY="/usr/local/anaconda3/2024.02/bin/python -I -u"
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"chain_labpages\": \"start\"}"
nice -n 5 $PY berkeley_catalog.py
for s in cmu epfl mit princeton; do nice -n 5 $PY add_works.py $s; done
NW=$(ls -d /n/fs/resemble/homogenizing-science/data/fulltext/princeton/discovery/claude-labpapers-newworks-*/ | xargs -n1 basename | sed 's/^/cs_pi_works:/')
(cd /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015 && /usr/local/anaconda3/2024.02/bin/python -u tools/import_all_when_free.py $NW)
./run_steps.sh berkeley proceedings arxiv_title s2 core techrpt pubpages >> logs/steps-berkeley.log 2>&1
./run_steps.sh cmu oa_arxiv openalex proceedings arxiv_title s2 core >> logs/steps-cmu.log 2>&1
./run_steps.sh epfl oa_arxiv openalex proceedings arxiv_title s2 core >> logs/steps-epfl.log 2>&1
# channels chain_refresh.sh leaves out: Europe PMC by DOI and PMC links (all schools), KiltHub/Figshare (CMU: 10.1184 handles)
./run_steps.sh cmu figshare europepmc pmc >> logs/steps-cmu.log 2>&1
for s in berkeley epfl mit princeton; do ./run_steps.sh $s europepmc pmc >> logs/steps-$s.log 2>&1; done
./run_steps.sh berkeley labpages pihomes >> logs/steps-berkeley.log 2>&1
./run_steps.sh epfl labpages pihomes >> logs/steps-epfl.log 2>&1
./run_steps.sh cmu labpages pihomes >> logs/steps-cmu.log 2>&1
./run_steps.sh mit labpages pihomes >> logs/steps-mit.log 2>&1
./run_steps.sh princeton oar labpages pihomes >> logs/steps-princeton.log 2>&1
[ -f raw/mit_oa_articles.done ] && nice -n 5 $PY mit_oa_articles.py match >> logs/steps-mit.log 2>&1
./run_steps.sh mit dspace >> logs/steps-mit.log 2>&1
./princeton_pass.sh >> logs/princeton-pass.log 2>&1
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"chain_labpages\": \"done\"}"
