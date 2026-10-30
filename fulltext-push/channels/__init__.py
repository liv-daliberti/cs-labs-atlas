"""Discovery channels as plugins (2026-10-30, owner): one interface for every open-copy source of the lab-paper push.

A channel is one module fulltext-push/channels/<name>.py with
    NAME                          the step name (as run_steps.sh / lab_channels.py <school> <step> call it)
    APPLIES(school, paper) -> bool
                                  whether the channel can say anything about this paper; `paper` is a Paper
                                  (key, work_id, r = the lab-paper row, known = the work's known URLs)
    discover(school, papers, ctx) -> iterable of Result
                                  papers = the applicable Papers; one Result per paper it examined
and the shared runner (fulltext-push/channel_runner.py) does everything else: the plan (the counter's missing lab
papers and their known URLs), known-URL filtering, writing candidates in committed batches (Princeton: a discovery
package), evidence files, a check per applicable paper in the checks store (checks.py; a paper without a Result is
'none', or 'error' when the channel reports it stopped early), and the logs/channels.jsonl summary. The unavailability
ledger reads the checks store, so a new channel counts toward "why we could not get it" without further wiring.

Result(paper_key, work_id, status='found'|'none'|'error', urls=[...], query=..., detail=...): urls are candidate rows
(dict(url, landing_url, version, license, source, detail)) or plain URL strings (source = the channel's NAME).
ctx (channel_runner.Ctx): school, known ({work_id: set of URLs}, shared and updated by the runner), n (Counter for the
summary; a channel that stops early sets n['stopped'] = reason), dry, miss (every missing (row, work_id) pair),
all_papers (every missing Paper), has_arxiv(urls), result(paper, status, urls, query, detail), session(),
polite_get(url, delay) (robots.txt honoured, paced), env(name) (keys from ~/.config/cs-atlas, never printed), and
write(rows, step) for channels that write as they go. How to add one: docs/CHANNELS.md.
"""
import importlib
from collections import namedtuple

Paper = namedtuple('Paper', 'key work_id r known')


class Result(namedtuple('Result', 'paper_key work_id status urls query detail')):
    __slots__ = ()

    def __new__(cls, paper_key, work_id, status='none', urls=(), query=None, detail=None):
        assert status in ('found', 'none', 'error'), status
        return super().__new__(cls, paper_key, work_id, status, list(urls or ()), query, detail)



# every channel module, in the order lab_channels.py has listed them
NAMES = ['oa_arxiv', 'openalex', 'arxiv_title', 'proceedings', 's2', 'core', 'europepmc', 'pmc', 'figshare', 'techrpt', 'pubpages',
         'homepages', 'dspace', 'infoscience', 'labpages', 'pihomes', 'oar', 'wayback_acm', 'dblp_ee', 'oa_refresh', 'oa_editions', 's2_title',
         'arxiv_loose', 'ledger_found', 'oa_publisher']
NATIVE = ['arxiv_loose', 'ledger_found', 'oa_publisher']  # written for the interface (the others run a lab_channels.py step through channels/_legacy.py)


def load(name):
    m = importlib.import_module(f'channels.{name}')
    for attr in ('NAME', 'APPLIES', 'discover'):
        assert hasattr(m, attr), f'channels/{name}.py lacks {attr}'
    return m
