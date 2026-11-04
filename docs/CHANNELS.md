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
- `reader_link` (2026-11-03): the open-copy link the release's reader confirmed for a link-only paper queued for download
  (`reader/<school>.jsonl.gz`, ledger `found_awaiting_download` / `pending_retry`; the priority file's rule) when the paper's
  catalog work does not hold it yet. Hosts the other channels never use (`s2_key_lookup.BAD_HOSTS`) are skipped. `downloads.slurm`
  runs it with `ledger_found` before each loop starts.
- `oa_publisher`: the publisher's own open copy of papers OpenAlex marks gold, hybrid, bronze or diamond, when no
  candidate reaches it (its open location's PDF, else its landing page, else the DOI); not for ACM, IEEE and SSRN,
  which refuse automated clients or serve a challenge. Either the copy, or a recorded reason (robots, challenge,
  paywall) for the ledger.

## Repository harvests: `oai_repo` (2026-11-04, owner)

Owner 2026-11-04: harvest each school's institutional repository over its standard bulk interface (OAI-PMH), politely, because author
manuscripts often live only there. `fulltext-push/oai_repo.py` is the harvester, `channels/oai_repo.py` the channel, `[oai_repo]` in the
school's charter the configuration (verdict, base URL, metadataPrefix, sets, delay, landing template).

- **Harvest:** `oai_repo.py harvest <school>` reads robots.txt first (this client's user agent, ClaudeBot and anthropic-ai against the base
  path; the declared Crawl-delay raises the charter's delay), takes one flock per host, and follows resumption tokens one request at a time.
  Everything goes into one SQLite file per school, `raw/oai_repo/<school>.sqlite` (records, state, sets_resolved), never per-record files.
  It is resumable (the token is stored after every page) and incremental (a finished set is asked again with `from=<start of the last harvest>`).
  A 403, a 202 (bot challenge), a non-XML body or an OAI error stops the harvest; Retry-After is honoured. Slurm: `fulltext-push/oai-repo.slurm`
  (one job, schools one after another, so one request in flight at a time).
- **Match:** `run_steps.sh <school> oai_repo` (the runner's usual plan: lab papers without a copy). Rules in order: DOI equal to a DOI the record
  names as its own; a handle/landing URL of the record already among the paper's known URLs; equal normalized title (>= 25 characters), years
  within 2, and the identity rule's authors (shared family names >= half of the smaller side, one of the paper's PIs among the creators).
  No title-only match. Candidates are the record's open file URLs, else its handle/landing page (the collector reads `citation_pdf_url`);
  records whose rights say restricted, embargoed or metadata-only give none. `catalog_lock.backup_catalog` runs before the write, which
  goes through `write_candidates` -> `write_batches` under the catalog lock.
- **Hand check:** after a repository's candidates are downloaded, 20 matched candidates are read on page 1; more than 1 wrong rolls that
  repository's candidates back (`source = 'oai_repo_<school>'` identifies them).

### Verdicts (robots.txt and terms read 2026-11-04; none of the robots.txt files has a ClaudeBot or anthropic-ai group)

| School | Repository | Verdict | Why |
|---|---|---|---|
| MIT | DSpace@MIT `dspace.mit.edu/server/oai/request` | harvest | `/server/oai` is not disallowed (the `/search`, `/browse`, `/admin` rules do not touch it); 20 s pace after the 429 of 2026-10-27. The OA Articles collection harvested whole on 2026-10-30 is seeded from `raw/mit_oa_articles.sqlite` without a request; CSAIL Digital Archive, AI Lab Publications, LIDS and the CS collection are new |
| EPFL | Infoscience `infoscience.epfl.ch/server/oai/openaire4` | harvest | only `/server/opensearch/*` and the search/admin paths are disallowed; the standard `/server/oai/request` context answers 400 to every verb, the OpenAIRE context works (oai_openaire: datacite creators, DOIs, file URLs) |
| CMU | KiltHub through Figshare's OAI `api.figshare.com/v2/oai`, set `portal_231` | harvest | `kilthub.cmu.edu` serves a bot challenge (202, empty body): never fetched. `api.figshare.com` has no robots.txt (404). Files of a matched record come from the public API `/v2/articles/<id>` |
| UChicago | Knowledge `knowledge.uchicago.edu/oai2d` | harvest | robots.txt disallows `/search /api /administration /account /uploads /me /login /logout /records/*/preview`, not `/oai2d`; Crawl-delay 10 kept. oai_dc has no file URLs: the record page is the candidate |
| Princeton | OAR `oar.princeton.edu` (DSpace 5 JSPUI) | skip | no OAI-PMH endpoint (`/oai/request`, `/jspui/oai/request`: 404). The item pages were already indexed from the robots-listed sitemap (the `oar` channel) |
| Berkeley | eScholarship `escholarship.org/oai` | skip | CloudFront answers 403 "Request blocked" to this client, for `/robots.txt` too: an access block we do not work around |
| Stanford | SDR `purl.stanford.edu` / SearchWorks | skip | no OAI endpoint on either host; the robots-listed sitemaps list PURLs only, so a harvest would be one request per PURL over the whole repository, not a bulk interface |
| Georgia Tech | SMARTech `repository.gatech.edu` | skip | robots.txt: `Disallow: /server/oai/*` and `/server/api/*` (core/bitstreams and core/mapping allowed) |
| Michigan | Deep Blue | never | owner rule: it disallows AI agents by name |

### Dissertation item-page crawl for advisers: `etd_crawl.py` (2026-11-04, owner)
Georgia Tech's OAI is disallowed and UChicago's oai_dc has no contributors, so the adviser field is read from the dissertation item pages,
politely: one host, one request per >= 10 s (the declared Crawl-delay), robots.txt (this client, ClaudeBot, anthropic-ai) checked for every URL,
resumable (`raw/etd_crawl/<school>.sqlite`, queue + pages), stopping on a block or 25 login views in a row. Per page only title, author, degree/type,
year, department, advisors, URL, sha256 and a short quote are kept. Georgia Tech: the `/entities/publication/<uuid>` pages of the sitemap (the
`/items/<uuid>` URLs answer the login view to this client), dissertation = Resource Subtype Dissertation/Doctoral. UChicago: the OAI harvest's
doctoralThesis records. `etd_crawl.py evidence <school>` matches advisors to PIs by full name and writes `thesis-evidence.json` rows (quote + page hash),
read by `tools/pihier/students.py` like the other researched sources; written only after a 20-row hand round at the standard bar.

## Bulk open-access sources (2026-11-04, owner)

Four channels that match a bulk source to the lab papers LOCALLY (DOI first, then arXiv id, then normalized title plus first author:
`fulltext-push/bulk_oa.py`, one targets table `raw/bulk-oa/targets.jsonl.gz` of every missing lab paper of every school). Run: `bulk-oa-targets.slurm`
(table), `s2-bulk.slurm` (the S2 filter jobs), then `bulk-oa-channels.slurm` (channels per school, catalog backup before every write).

| source | terms read 2026-11-04 | verdict (one line) |
|---|---|---|
| OpenAlex snapshot (`oa_locations`) | OpenAlex data is CC0; the snapshot is the project's own filtered copy (docs/OPENALEX-SNAPSHOT.md); locations are Unpaywall's data | allowed: read all locations of the paper's records and its same-DOI / same-title records, no network; URLs are fetch candidates under each host's robots.txt |
| Semantic Scholar Datasets (`s2_bulk`) | dataset README: ODC-BY, cite Kinney et al. 2023 (and Lo et al. 2020 for s2orc); API licence: keyed use, no exceeding rate limits, no redistribution of the API | allowed: file lists with our key (a few requests), each file streamed once on Slurm and filtered to our papers, nothing else stored; PDF URLs only as fetch candidates. `papers` has no PDF URL (only isopenaccess): the URLs come from `s2orc` (content.source.pdfUrls, oaInfo) |
| CORE (`core_bulk`) | core.ac.uk/terms (read through a search summary; the page itself refuses bots): datasets ODC-BY but downloadable only for users representing registered organisations (individuals go to the API); API free for individuals and public research organisations for unfunded research | dataset: NOT used (no registration). API: used with the owner's key at the documented rate, as the `core` channel always has; owner to confirm that the "unfunded research" clause covers this project (decision 1 of the report) |
| arXiv (`arxiv_bulk`) | arXiv bulk-access page: metadata openly available; articles mostly under the default arXiv licence (arXiv may distribute, builders of indexes must link back to arXiv) | allowed: metadata from our OAI-PMH harvest (the Kaggle copy needs a login; its mirror in gs://arxiv-dataset/metadata-v5 stops in 2020), PDFs from storage.googleapis.com only, every candidate's landing URL is the arxiv.org abstract page, never arxiv.org fetched |

- `oa_locations`: see its module docstring. `s2_bulk`: reads `raw/bulk-oa/s2/<release>/{papers,s2orc}.jsonl.gz`; ArXiv, PubMedCentral and ACL ids of a
  matched record become the bulk arXiv copy, the PMC open-data files and aclanthology.org. `core_bulk`: DOI queries through the `core` step's cache, plus
  title queries (exact normalized title, same first author, year within 2) for papers without a DOI. `arxiv_bulk`: the OAI record's DOI field, then an
  arXiv id the paper names, then the exact normalized title with the same author set.
- Identity: a record matched by title is only a candidate; the collector's page-1 rule (`identity_rule.py`) decides at download time, and the
  hand check of 20 matched candidates per source is recorded in the report that landed this.

### Bulk open-access sources: results of 2026-11-04
- Identity hand check (page 1 of 20 downloaded copies per source, `bulk_oa_report.py sample`): `s2_bulk` 0 wrong of 20 (kept); `oa_locations` 2 wrong of 20
  (a handbook chapter for the handbook through a same-title sibling record; a wrong arXiv link on an OpenAlex record) and `arxiv_bulk` 1 wrong plus 1
  unconfirmed of 7 (a series Part I matched by the arXiv record's DOI field, which carries Part II's DOI) -> both ROLLED BACK by
  `bulk_oa_rollback.py` (wrong copies reverted, every candidate of the channel not yet downloaded deleted, copies that passed stay); their code stays in the
  tree, off the run lists, until the matching is tightened (sibling records only with a matching container type; arXiv ids only from the paper's own
  record; a DOI match also needs a compatible title). `core_bulk`: no copy downloaded yet, so no check was possible; its candidates stay.
- eScholarship (Berkeley; escholarship.org blocks us at its CDN): `wayback_escholarship` adds the Internet Archive capture of the item PDF (`id_` URL form,
  one CDX lookup per 8 s); CORE's hosted copies (`core.ac.uk/download/...`) answer a Cloudflare challenge, so they are not used.
