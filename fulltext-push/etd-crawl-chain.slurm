#!/bin/bash
#SBATCH --job-name=etd-uc-chain
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:58:00
#SBATCH --exclude=node302,node014
#SBATCH --output=fulltext-push/logs/etd-uc-chain-%j.out
# 2026-11-05 UChicago round 2: the sitemap-only Knowledge@UChicago record pages (15,338 not in the OAI queue) at the 10 s Crawl-delay, as a chain of
# 58-minute jobs (~340 pages each). The first job adds the sitemap's record URLs to the queue (idempotent); every job crawls up to MAX pages, resumable.
# Evidence afterwards: etd_crawl.py evidence uchicago (keeps dissertations whose advisor is a census PI).
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
"$FTP_PY" -I -u - <<'PY'
import re, sys
sys.path.insert(0, '.')
import etd_crawl as E, oai_repo as O
c = E.connect('uchicago')
if c.execute('select count(*) from queue').fetchone()[0] > 2000:
    sys.exit(0)   # already enumerated by an earlier job of the chain
cl = O.Client(10.0, low_priority=True)
rob = cl.get('https://knowledge.uchicago.edu/robots.txt').content.decode('utf8', 'replace')
urls = []
for u in re.findall(r'(?im)^sitemap:\s*(\S+)', rob):
    urls += E.sitemap_urls(cl, u, r'/records/')
print('sitemap record urls', len(urls), 'added', E.add_urls('uchicago', urls, front=False), flush=True)
PY
"$FTP_PY" -I -u etd_crawl.py crawl uchicago --max "${MAX:-335}" < /dev/null
echo '{"etd-uc-chain": "job done"}'
