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
| CORE (`core`, `core_bulk`) | core.ac.uk/terms, read from the Wayback capture of 20261104051851 (the live page refuses bots). Section 3 requires permission for API use in this research and discovery interface. The owner confirmed on 2026-11-15 that CORE API use is allowed across all schools. The separate bulk dataset is not used. | Allowed for every school through the registered API credential. Respect API rate limits; keep unanswered or failed checks incomplete. `core_bulk` uses API queries, not the bulk dataset. Candidate links point to original repositories. |
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
- DR-NTU (NTU; dr.ntu.edu.sg answers our client 405 at its WAF, ruled out of bounds live): `wayback_drntu` (D-0033, 2026-11-21) adds the latest
  Internet Archive capture of each file under `dr.ntu.edu.sg/bitstream/10356/<n>/` (one CDX prefix lookup per handle on the shared 8 s slot, cached in
  `raw/wayback_lookups.jsonl` kind `drntu`); never a live DR-NTU request. `WAYBACK_DRNTU_LIMIT` (default 50) caps new lookups per run (the pilot).
- ACM (any school): `wayback_acm_vol` (2026-11-21) asks wayback_acm's question, a status-200 PDF capture of `dl.acm.org/doi/pdf/<doi>` or its
  `?download=true` twin, with one CDX *prefix* lookup per ACM volume (`10.1145/<volume>.`) on the shared web.archive.org slot (host_throttle,
  a 429 stops it). One request answers every paper of the volume and both URL forms; wayback_acm asks up to two exact lookups per paper at its
  own 8 s pace outside host_throttle. Answers go to `raw/wayback_lookups.jsonl` in wayback_acm's record form, so wayback_acm and the ledger's
  wayback_acm source skip those URLs. Run it with `fulltext-push/wayback-acm-vol.slurm` (SCHOOLS most ACM papers first; passes retry after a stop).
  The rotator counts a work as waiting for Wayback once its live candidates were all tried, so these works earn NTU a turn.

### Gaps closed and limits found (2026-11-04, later)
- **EPFL:** the OAI endpoint answered HTTP 405 at page ~282 (28,167 records kept) and is not asked again. `oai_repo.py harvest-rest epfl` enumerates the
  same collections through the REST API the downloads already use (`/server/api/discover/search/objects?scope=<collection>`, 100 a page, 3 s apart,
  resumable by page; robots.txt does not disallow `/server/api`). Records are `rest:<item uuid>` in the same table; a matched record is asked once for its
  ORIGINAL bundle and its PDFs become candidates `.../core/bitstreams/<uuid>/content` (source `oai_repo_epfl`, the form the earlier REST pass wrote, so known URLs dedup).
- **Georgia Tech enumeration:** the live `sitemap1.xml` is cut off by the server at 955,812 bytes, losing about 38,700 of its ~45,000 entries (not ~5,000).
  Wayback holds complete captures (`web.archive.org/web/20261001233421id_/https://repository.gatech.edu/sitemap1.xml`, 6.7 MB, 45,062 entries); its 23,819
  `/entities/publication/` URLs not already queued were added to the crawl queue (`etd_crawl.py add gatech <file>`), so the crawl queue holds ~58,100 publication pages
  (the full sitemap is 95k entries: 58,135 publications, 24.9k archival materials, 9,865 `/items/<uuid>` pages, 1.3k persons/series/orgunits).
  **Not reachable:** the 9,865 `/items/<uuid>` pages answer the login view to this client (and Wayback's captures of them are the same login view); their uuids
  are never `/entities/publication/` uuids (0 of 9,865 overlap; three probes through the crawl queue answered the login view too). The REST API is disallowed
  except `core/bitstreams` and `core/mapping`, OAI is disallowed. OpenAlex, CORE and Semantic Scholar list the works but carry no adviser field.
- **Crawler resilience:** `Client` treats 500/502/503/504 like 429 (back-off 60, 300, 900, 1800 s); after that the etd crawl waits 30 min and asks again
  (12 failed rounds in a row stop it), so a 502 no longer ends the crawl. One crawler per host: new URLs go through `etd_crawl.py add`, never a second client.

### Georgia Tech `/items/` pages: other routes (2026-11-04, owner: "look for other ways")
- **Old SMARTech in Wayback (route taken):** the CDX API lists 48,951 distinct `smartech.gatech.edu/handle/1853/<n>` item pages with a status-200 capture (13,020 with a
  `?show=full` capture, which names `dc.contributor.advisor`, `dc.type`, `dc.description.degree`; the others carry the advisor as the first DC.contributor meta tag before DC.creator,
  read only for a Dissertation or Thesis and quoted as such). `etd_crawl.py crawl gatech@wayback` (charter `[etd_crawl_wayback]`, web.archive.org has no robots.txt, 3 s a request, own queue)
  fetches them full-first; `evidence gatech` merges its rows after the live crawl's, deduplicated by title and author, with Wayback replay URLs and the capture's sha256.
- **Not usable:** the Wayback captures of `repository.gatech.edu/items/<uuid>` are the same login view as the live pages; OATD answers a Cloudflare challenge on /robots.txt (not used);
  NDLTD's search answers 503 "under redevelopment"; WorldCat's robots.txt disallows AI agents; BASE answers 403; the Georgia Tech Primo host does not answer; OpenAlex, CORE and
  Semantic Scholar list the works but carry no adviser field (they can only identify items, and no `/items/<uuid>` -> handle map exists on any allowed page).

### One request budget for web.archive.org (2026-11-04)
Two clients (the download loops' Wayback fetches and the SMARTech crawl) each kept their own clock and drew four 429s in two hours. Every client of
web.archive.org / archive.org now shares `host_throttle.py`'s request clock and 429 cooldown: `SHARED_INTERVAL` (5 s, ~12 a minute against IA's ~15) is the real
limit whatever delay a caller passes (the collector's per-process 6 s is only a floor); a 429 anywhere starts the cooldown (300 s doubled per 429 in 2 h, cap 1 h) and
every client waits it out. The evidence crawl (`oai_repo.Client(low_priority=True)`) yields: while a loop was served in the last minute it takes at most one slot in
three (15 s), the loops keep two; with no loop active it runs at 5 s. The loops run on a pinned commit: the new pace reaches them at their next restart.
Expected: SMARTech crawl 48.6k pages = 2.8 days alone, up to 8.4 days while loops are active; Berkeley's 270 eScholarship PDFs at ~1-2 requests each = 270-540 slots = 25-45 min of the loops' share.

## Download-yield survey (2026-11-04, branch agent/yield-1104)

`fulltext-push/missing_breakdown.py` reprints the numbers below from the ledgers (`hierarchy/<school>/derived/unavailable.jsonl.gz`, built
2026-11-03T21:22Z, seven released schools; it is older than the 2026-11-04 `oai_repo` and bulk-OA writes, so `queued` over-counts). Missing lab-paper
copies: 32,707 = publisher_only_closed 14,298, landing_page_without_pdf 7,651, open_copy_robots_disallowed 3,675, found_awaiting_download 1,692,
paywall_only 1,557, no_doi_no_match 930, open_copy_unusable 846, found_not_in_catalog 701, pending_retry 634, bot_challenge 492, behind_login 207, other 24.

What the measurement says about the open sources of the task:
- **Open-proceedings venues are exhausted.** CVF, PMLR, NeurIPS, ICLR, ACL, USENIX, AAAI, IJCAI, JMLR, LIPIcs, VLDB and SIGPLAN venues hold only ~400
  missing papers in all (CVF 78, AAAI 100, NeurIPS 48, ICLR 30, PMLR 28, USENIX 28, VLDB 32), and the `proceedings` index (235,069 entries, CVPR
  22.8k, ACL 90.8k, NeurIPS 18.8k, PMLR, ECCV, WACV, ...) already gives their exact-title PDFs. A Jaccard >= 0.8 near-title pass over the index (year
  within 2) finds 114 exact and 42 near matches among the missing papers; 97 of the exact ones are `found_not_in_catalog` (works the catalog lacked
  until `add_works.py`, now ~220 left across the schools), the rest already have candidates. CVF's 59 `publisher_only_closed` are workshop papers
  (CVPRW / ICCVW, not in the index) and WACV 2016-2019 (not on CVF). The 14.3k publisher-only papers are IEEE (8.5k: ACC, ICRA, IROS, JSSC, IGARSS,
  CDC, ISIT, ICASSP), Springer LNCS, Elsevier, ACM: no open proceedings host exists for them.
- **Landing pages without a PDF are mostly real no-file records.** Of the 7,651: Infoscience record pages 2,555 (`policy_skip`, handled by the REST
  `oai_repo` harvest), PubMed pages 2,115 (no PMCID), `hdl.handle.net` 656, SSRN 603 (bot-hostile), OSF/PsyArXiv ~200, Zenodo 133 (datasets and code, no
  article), HICSS ~70. 45 landing pages of 15 repository hosts sampled (3 each, robots.txt checked): no `citation_pdf_url` or PDF link on 41; the other 4
  are not articles (zenodo data zips, a site-wide VPAT PDF). The collector already follows `citation_pdf_url`, `<link type=application/pdf>` and
  `/bitstream/`, `/retrieve/` links (vendor/cmu_tools/collector_wrapper.py `Links`); scholarspace.manoa.hawaii.edu (HICSS) serves a DSpace-7 app shell for
  `/bitstream/...` URLs, so those need the REST bitstream route (~70 papers, not built).
- **Stale redirect failures:** `www.psyarxiv.com` (71 papers, pending_retry), `www.rero.ch` (177: the SONAR privacy PDF, correctly refused), `idp.*` /
  `linkinghub.elsevier.com` / `validate.perfdrive.com` (logins and challenges, correctly refused). The psyarxiv same-site rule is already in code; loops
  started before it still run the old collector.
- **Queued papers wait on pacing, not on discovery:** the 1,692 + 634 queued papers sit behind `dspace.mit.edu` (762 known URLs, 15 s clock, five 429s in
  the last two hours) and `hdl.handle.net` (782, mostly the same MIT handles).

### `sonar` (native channel)
SONAR (sonar.ch, also folia.unifr.ch) serves Swiss repositories' open full texts. Its pages are a JavaScript app, so 283 lab papers (262 EPFL) whose known
URLs name a SONAR document ended at 'no unambiguous primary PDF link'. `channels/sonar.py` reads the public JSON record of each named id
(`/api/documents/<id>`, robots.txt `Allow: /`, checked for this client and the Anthropic groups, 3 s apart) and, for an unrestricted PDF in `_files`,
adds `https://sonar.ch/api/documents/<id>/files/<key>` (HTTP 200 straight from sonar.ch). No title or DOI discovery: the API's search matched 0 of 80
random missing papers. Dry run on EPFL: 250 papers asked, 68 open files, 67 new candidates. Run: `bulk-oa-channels.slurm` with `CHANNELS=sonar`.

### NSF PAR for the other US schools: measured, not scaled
`nsf_par_lab.py search stanford --limit=400` (paywalled publishers first): 1 exact-title hit in 400 searches (0.25%; the earlier four-school run: 265 of
12,718). The remaining ~17.9k unsearched paywalled titles (stanford 2,864, michigan 4,127, uchicago 757, gatech 10,132) would cost ~15 h of requests for
~45 papers: `nsf-par.slurm` stays in the tree, not on the run lists.

## Discovery channels back on for every loop (2026-11-10, owner)
The owner (2026-11-10: "I want discovery to be re-enabled. We're missing a bunch for georgia tech, michigan, harvard etc.") reversed the same day's trim of the eight big
schools to oa_arxiv/europepmc/pmc. Policy now:
- every loop's charter `[collector].channels` is the discovery list oa_arxiv, openalex, proceedings, arxiv_title, dblp_ee, s2, europepmc, pmc, figshare, labpages, pihomes.
  `school-collector.slurm` reads the charter at every (re)start; the `CHANNELS` environment is ignored unless `CHANNELS_FORCE=1` (a loop resubmits itself with its
  environment, so a `CHANNELS` set at the first submission used to pin the list and hide the charter).
- `wayback_acm` stays OFF, and `WAYBACK_HOLD=1` (default in the loop scripts; `collector_quality.wayback_held`) keeps the download collectors off web.archive.org, while any
  Wayback listing/capture job is queued or running. The 429 cooldown of 2026-11-10 04:59Z was drawn by loop collectors fetching Wayback snapshot candidates already in their
  catalogs (`raw/host-throttle-429.jsonl` names the job and command of every 429). To release: append `wayback_acm` to the charter and set `WAYBACK_HOLD=0`, only when no listing
  capture runs. CORE API checks are enabled for every school under the 2026-11-15 owner decision.
- OpenAlex: `OA_RESERVE` (default 800; the loop and discovery scripts set 4000) is the `oa_refresh` floor: every list request stops once X-RateLimit-Remaining is under it, so
  discovery spends at most 6,000 of the shared 10,000 daily credits. Every request is in `raw/openalex_budget.jsonl`. S2 keeps its one-request-per-1.2-s clock.
- One-off discovery jobs: `SCHOOL=<key> CHANNELS="..." atlas submit fulltext-push/school-channels.slurm` (run_steps.sh; per-channel locks serialize schools).

## Rotating Wayback fetcher (2026-11-16, owner decision)
One school at a time runs its download loop with `WAYBACK_HOLD=0`; every other loop keeps `WAYBACK_HOLD=1`. `fulltext-push/wayback_rotate.py`, run by the
self-restarting Slurm job `fulltext-push/wayback-rotator.slurm` (job name `wayback-rotator`, 1 CPU, 1 G), gives the turns: about an hour of ACTIVE time each
(minutes while web.archive.org cools down after a 429 do not count), schools ordered by their Wayback-only queue (all candidates on archive hosts, last attempt
`source_paused` or none), largest first, each school once per round. The one-hour turns do not change the slot (`host_throttle`), the cooldowns, robots.txt or the
charters. A turn is never granted while web.archive.org is cooling down, was used by someone else in the last 150 s, a live task claim or lease names
wayback, or an unheld loop that is not the holder exists; a foreign fetcher appearing mid-turn makes the holder yield. Each turn changes only the two loops involved
(scancel, then `loop_starter.submit` with `WAYBACK_HOLD` in the environment, which the loop's own self-resubmits carry). State and per-turn records (school, start, end,
Wayback attempts and successes, 429 rows and 429 events): `fulltext-push/logs/wayback-rotation-state.json`, `fulltext-push/logs/wayback-rotation.jsonl`.
- Start: `WAYBACK_ROTATE_ADOPT=gatech atlas submit fulltext-push/wayback-rotator.slurm` (ADOPT turns the loop that already runs unheld into the first turn).
- Look: `wayback_rotate.py status` (state), `plan` (eligible schools and queues), the `Collector status` page (a held loop shows "wayback held").
- STOP: `scancel -n wayback-rotator`. The holder is re-held (cancelled and resubmitted with `WAYBACK_HOLD=1`) before the job exits, and nothing is resubmitted.
  After a hard kill run `wayback_rotate.py rehold` (it re-holds the recorded holder and any unheld loop).
- A manual restart of a loop without `WAYBACK_HOLD` re-holds it silently; the rotator then sees no unheld loop and grants the next turn.
