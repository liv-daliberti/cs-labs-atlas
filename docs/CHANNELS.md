# Discovery channels: one plugin per open-copy source (2026-10-30, owner)

Every source of open full-text copies for the lab papers (arXiv, OpenAlex, Semantic Scholar, CORE, PMC, DBLP, lab
pages, repositories, Wayback, ...) is one module in `fulltext-push/channels/`, and one runner,
`fulltext-push/channel_runner.py`, does everything around it. Each paper a channel examines leaves a dated check in
the checks store, so a new source counts toward the unavailability ledger (`docs/UNAVAILABLE.md`) without more wiring.

## The interface

```python
NAME = 'mysource'                      # = the module name = the step name run_steps.sh / lab_channels.py use

def APPLIES(school, paper) -> bool:    # can this source say anything about this paper?
    ...                                # paper: channels.Paper(key, work_id, r, known)
                                       #   key = the paper key of copies.json, work_id = its catalog work,
                                       #   r = the lab-paper row (title, doi, year, byline, pis, oa, editions),
                                       #   known = the work's known URLs (candidates, attempts, pending packages)

def discover(school, papers, ctx):     # papers = the Papers APPLIES selected
    for p in papers:
        yield ctx.result(p, 'found', urls=[...], query='what was asked', detail={...})   # or 'none' / 'error'
```

`urls` are candidate rows (`dict(url, landing_url, version, license, source, detail)`) or plain URL strings (source =
`NAME`). `ctx` (`channel_runner.Ctx`) gives `school`, `known` (live), `n` (a Counter for the summary line; set
`n['stopped']` when the channel stops early, so unanswered papers count as `error`), `dry`, `miss`, `all_papers`,
`has_arxiv(urls)`, `session()`, `polite_get(url, delay)` (robots.txt honoured, paced), `env(name)` (keys from
`~/.config/cs-atlas/*.env`, never printed or written), and `write(rows, step)` for a channel that writes as it goes.

## What the runner does

For `channel_runner.py <school> <channel> ... [--dry]` (also reached through `lab_channels.py` and `run_steps.sh`):

1. the plan: the school's lab papers without a copy by the coverage counter's rule, matched to their catalog works,
   with their known URLs (`lab_channels.plan_for`; catalogs read-only in short chunks);
2. `APPLIES` -> `discover` -> Results;
3. known-URL filtering: a URL the work already has is not written again;
4. candidates in committed batches of at most 200 rows with a busy timeout (the collectors share the catalog), with an
   evidence file per 100 rows; Princeton gets a discovery package for its own import path;
5. one row per Result in `fulltext-push/checks/<school>.sqlite` (`checks.py`: paper key, work, channel, date, query,
   found / none / error, detail);
6. one summary line in `fulltext-push/logs/channels.jsonl`.

`--dry` writes nothing (no candidates, checks or summary line). Channels that write their own candidates as they go
(dspace, infoscience, wayback_acm) still do so in a dry run, as before the port.

## Adding a source

1. Write `fulltext-push/channels/<name>.py` with `NAME`, `APPLIES`, `discover` (above). Ask only documented, public
   interfaces; check robots.txt (also its groups for ClaudeBot and anthropic-ai) and pace requests (`ctx.polite_get`);
   never work around a paywall, a login or a bot challenge, and stop asking a host that serves one.
2. Add the name to `channels.NAMES`.
3. Add a fixture test to `tests/test_channels.py` (the parametrized interface test covers every name in `NAMES`;
   add a test of the channel's own matching on fixture papers).
4. Run it dry on one school, then for real: `fulltext-push/run_steps.sh <school> <name>`.
5. If the ledger should demand the source for every paper, add it to `unavailable_ledger.SOURCES` / `applicable()` and
   to the table in `docs/UNAVAILABLE.md`.

## Ported channels (2026-10-30)

All 22 steps of `lab_channels.py` are plugins: oa_arxiv, openalex, arxiv_title, proceedings, s2, core, europepmc, pmc,
figshare, techrpt, pubpages, homepages, dspace, infoscience, labpages, pihomes, oar, wayback_acm, dblp_ee, oa_refresh,
oa_editions, s2_title. Their bodies still live in `lab_channels.py` (`step_<name>`) and its helper modules; the adapter
`channels/_legacy.py` runs each body unchanged on every missing paper and turns its outcome into Results, with
`lab_channels.SCOPE[name]` as `APPLIES`. Old and new produce identical candidates: CMU dry runs on 2026-10-30, with the
works' known URLs and with none (proceedings 13 = 13 rows, dblp_ee 23 = 23, labpages 202 = 202, openalex 2,081 = 2,081,
oa_arxiv 3 = 3). Moving a body into its module is the next step per channel; the interface does not change.

## Native channels (written for the interface, 2026-10-30)

- `arxiv_loose`: arXiv versions posted under a different title, from the local arXiv OAI index: title similarity
  >= 0.80 and word Jaccard >= 0.55, the same author set (every byline family among the record's authors; long bylines:
  6 of the first 8 and every PI; one- or two-name bylines: also the same first author), first version 3 years before to
  1 year after, and no near-tie with another record. Validated on a hand-checked sample before its first write
  (fulltext-push/review-20261030/arxiv-loose-sample.json).
- `ledger_found`: the open copies the unavailability ledger's checks found that are not candidates yet
  (`new_open_urls` in `hierarchy/<school>/unavailable.jsonl.gz`).
- `oa_publisher`: the publisher's own open copy of papers OpenAlex marks gold, hybrid, bronze or diamond, when no
  candidate reaches it (its open location's PDF, else its landing page, else the DOI); not for ACM, IEEE and SSRN,
  which refuse automated clients or serve a challenge. Either the copy, or a recorded reason (robots, challenge,
  paywall) for the ledger.
