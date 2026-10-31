# Unavailable lab papers: the ledger standard (2026-10-30, owner)

Every CS lab paper without a local full-text copy carries a recorded reason **why** there is none, connected to the
paper, resting on dated checks of every applicable open source and on every download attempt. The owner's words: "show
that we definitely tried, and that there is a firm reason why it can't be done."

## Tool

```
/usr/local/anaconda3/2024.02/bin/python -I fulltext-push/unavailable_ledger.py <school> [<school> ...]
        [--max-age-days N]   reuse recorded checks younger than N days (default 30; OpenAlex records: 7)
        [--offline]          no network: stale or missing checks stay missing (-> incomplete_check)
        [--only <paper key>] one paper, printed (debugging)
```

It reads `hierarchy/<school>/copies.json` (the coverage counter, `tools/lab_paper_copies.py`; run it first) for the
set of lab papers without a copy, and writes

- `hierarchy/<school>/unavailable.jsonl.gz`: one record per non-local lab paper (below);
- `hierarchy/<school>/unavailable-summary.json`: `{school, built_at, inputs, papers, by_reason, by_publisher,
  by_reason_publisher, final, not_final, max_age_days}`;
- the per-paper checks into the school's checks store (below);
- `unavailable_reason` / `unavailable_summary` onto each non-local paper of `copies.json` (`lab_paper_copies.attach_ledger`).

Catalogs (`stores/<school>/catalog.sqlite`) are read only, in short chunks; nothing is written to them.

## The checks store (every channel logs its negatives)

`fulltext-push/checks/<school>.sqlite`, table `checks(id, school, paper_key, work_id, channel, at, query, result, detail)`;
`result` is `found`, `none`, `error` or `not_applicable`; `detail` is JSON text. Every discovery channel (a plugin in
`fulltext-push/channels/`, run by `fulltext-push/channel_runner.py`; docs/CHANNELS.md) appends one row per paper it
examined (`fulltext-push/checks.py record`), committed in
batches of at most 200 rows with a busy timeout, so steps of different channels can write at once. The ledger writes its
own checks to the same table, and reuses any check of a channel younger than `--max-age-days` instead of asking again;
only stale or missing checks are asked. The store is outside the full-text stores (the collectors and the Michigan
store are never written) and outside git.

## Sources checked per paper (`checks[].source`)

| source | applicable | what is recorded |
|---|---|---|
| `openalex` | always (every lab paper has an OpenAlex id) | `is_oa`, `oa_status`, every location (host, version, is_oa, pdf_url, source type), whether a usable open location exists; record refreshed when older than 7 days (50 ids per request) |
| `arxiv` | always | the arXiv id from the DOI, the paper's editions, OpenAlex or S2; else the local arXiv OAI index title match (`arxiv_oai.match_one`), and when there is none the best candidate title and its similarity |
| `s2` | always: DOI or arXiv id -> `/paper/batch` (500 per request); else title -> `/paper/search/match` | `openAccessPdf`, `externalIds` (ArXiv, PubMedCentral, ACL, PubMed) |
| `core` | the paper has a DOI (not an arXiv DOI) | CORE repository full-text links (25 DOIs per request) |
| `pmc` | the paper has a PMID / PMCID (OpenAlex, S2, a PubMed link) or a Europe PMC record | PMCID (NCBI ID converter, 200 per request; Europe PMC cache) and the PMC open-data files on S3 |
| `dblp` | always | the DBLP dump records matched by DOI or title + author + year, with their `ee` links (dump date recorded) |
| `proceedings` | always (title >= 20 characters) | the open-proceedings index entry with the same title and year within 2 |
| `repository` | always | the school's open-access repository: MIT DSpace@MIT Open Access Articles (+ handles), EPFL Infoscience, Princeton OAR, CMU KiltHub (Figshare), Berkeley eScholarship, Stanford SDR; matched by DOI or title (>= 30 characters) in the harvested index; the harvest's coverage is part of the detail (a partial harvest is an incomplete check) |
| `labpages` | always | the PI's lab-page captures and homepage captures, through the `labpage_channel` matcher (title, DOI or arXiv id in a bibliography entry); a PI with no page known is recorded as such |
| `wayback_acm` | the DOI is an ACM DOI (10.1145) | the Wayback CDX lookup of `dl.acm.org/doi/pdf/<doi>` (200 + application/pdf captures only) |

A check is *complete* when it is recorded (any result except `error`) and younger than `--max-age-days` (OpenAlex: 7
days). A paper is firmly unobtainable only when every applicable check is complete; otherwise it is `incomplete_check`
and `missing_checks` lists what is missing.

## Download attempts

`attempts[]` = every row of the catalog's `attempts` table for the paper's catalog work and the catalog works sharing its
DOI or normalized title (the collector's lab-paper group): `{url, at, status, cause, detail}`, `cause` as
`fulltext-push/review_access.py cause()` classifies it (paywall_or_forbidden, login, challenge, robots_disallow,
landing_no_pdf, not_pdf, not_found, unapproved_redirect, identity_mismatch, transient, ...). `access_review` is the
stores' access-review verdict and cause, when there is one.

## Copies that do not count (2026-10-31, owner)

- **Quarantined: robots.txt for an Anthropic crawler.** A copy the collector took from a path whose robots.txt disallows
  ClaudeBot, anthropic-ai or another Claude agent (the collector checked only its own user agent until 2026-10-30) is
  moved to `<store>/quarantine/robots-ai/`, its catalog status becomes `quarantined_robots_ai`, and the paper's reason is
  `open_copy_robots_disallowed` (`fulltext-push/quarantine_robots_ai.py`; per-store `manifest.jsonl` with work id, both
  paths, sha256, URLs and the rule; `restore` reverses it). 1,961 works on 2026-10-31.
- **Identity.** A copy counts only with a confirmed identity. The collector confirms a file when the catalog title or
  DOI is in its first three pages; a file it accepted without that (`provider_link_only_review_pending`) is reviewed by
  `fulltext-push/identity_review.py`: it passes when at least 80% of the title's significant words are in page 1's title
  region (its first 600 characters) and the first author's family name or the DOI is on page 1, or when page 1's arXiv
  stamp is the arXiv id the copy was downloaded as, Semantic Scholar or OpenAlex maps the work's DOI to it and the first
  author is on page 1. Failures are reverted (`revert_downloads.py`: back to needs_access_review, the download's attempt
  marked identity_mismatch, so that URL is not asked again; the work's other candidates still are). Measured on a hand
  check of 20 passes and 20 failures (2026-10-31, review-20261030/identity-review-handcheck.json): about 5% of passes are
  not the paper (1 of 20, 1 uncertain), and a few true papers fail. Two reverted copies were the paper: one whose catalog
  title carries a suffix ("... to Appear in a Festschrift for Grigori Mints"), one retitled before publication; they go
  back through the queue like every reverted work, and their reason in the ledger is the identity mismatch until another
  copy is found.

## Publisher and venue

`publisher`: OpenAlex `primary_location.source.host_organization_name`, else the lineage of the DOI's location, else the
Crossref member of the DOI prefix (`api.crossref.org/prefixes/<prefix>`, cached), else `"unknown"`. `venue`: the
primary location's source display name. Common names are folded (IEEE, ACM, Springer Nature, Elsevier, SSRN (Elsevier),
Wiley, Taylor & Francis, Optica, SPIE, ...).

## Reason codes (`reason_code`)

Exactly one per paper, the first that applies in this order:

| code | final | meaning |
|---|---|---|
| `found_awaiting_download` | no | an open candidate exists that the collector has not tried yet (in the catalog, a discovery package, or found by this run's checks) |
| `found_not_in_catalog` | no | a check found an open copy, but the paper has no catalog work to attach it to |
| `pending_retry` | no | the last failures are temporary (timeouts, 5xx, 429, a paused host) or a redirect awaiting allowlist review; the collector asks again |
| `incomplete_check` | no | at least one applicable source was not checked (or its check is stale or failed); `missing_checks` lists them |
| `identity_unconfirmed` | no | a copy is downloaded, but the identity rule neither confirmed nor rejected it (identity_check `provider_link_only_review_pending`); it does not count until confirmed |
| `open_copy_bot_challenge` | yes | the only open copy is on a host that served a bot challenge (never worked around) |
| `open_copy_behind_login` | yes | the only open copy redirects to a login / identity provider |
| `open_copy_robots_disallowed` | yes | the only open copy is on a path robots.txt disallows (for our client, `*`, ClaudeBot or anthropic-ai) |
| `landing_page_without_pdf` | yes | the open locations are landing pages (PubMed record without PMC text, a repository record without a file) with no PDF |
| `open_copy_unusable` | yes | the listed open copies are gone (404/410), not the paper (title check failed), not a PDF, or too large |
| `paywall_only` | yes | a location is listed as open, but every URL tried answered 401/403 (paywall or forbidden) |

A paper open at the publisher (OpenAlex gold / hybrid / bronze) whose publisher host refused this client gets the code of
the refusal (`open_copy_robots_disallowed`, `open_copy_bot_challenge`, `open_copy_behind_login`), else `paywall_only`.
| `publisher_only_closed` | yes | closed at the publisher (OpenAlex not OA) and no open copy in any checked source |
| `no_doi_no_match` | yes | no DOI, and no source matched the title |

`summary` is one sentence built from the record, e.g. "Only at IEEE (closed access, IEEE Transactions on Robotics). No
arXiv version (no arXiv id; best title match 0.62). No open copy in OpenAlex, Semantic Scholar, CORE, DBLP links, the
open proceedings, DSpace@MIT or the PI's lab and home pages; checked 2026-10-30. 1 attempt: ieeexplore.ieee.org 403
(paywall_or_forbidden)."

## Record (`unavailable.jsonl.gz`)

```
{key, school, work_id, status, reason_code, final, summary, publisher, venue, doi, year, title, is_oa, oa_status,
 arxiv, checked_at, checks: [{source, at, query, result, detail}], missing_checks: [source],
 attempts: [{url, at, status, cause, detail}], access_review: {verdict, cause} | null, untried_candidates: [url]}
```

`key` is the paper key of `copies.json` (`work` or `oa`). `checked_at` is the ledger run's time; each check carries its
own date.

## Pipeline, release and gate

- `hierarchy/rebuild.sh` stage `ledger` runs after `copies` and before `evidence`, for every school in `SCHOOL_IDS`
  and every charter with status `onboarding`.
- `tools/make_release.py` copies `unavailable.jsonl.gz` and `unavailable-summary.json` into the release;
  `MANIFEST.json` records the ledger's counts by `reason_code` per school.
- The organized tree's per-lab `papers.csv` has `copy_status`, `unavailable_reason` and `unavailable_summary`.
- `tools/evidence_check.py` fails the build when a non-local lab paper has no ledger entry (`unavailable_missing`),
  when an entry's `checked_at` is older than the school's `lab_papers.jsonl.gz` (`unavailable_stale`), or when
  `incomplete_check` exceeds its whitelisted count in `docs/evidence-whitelist.json` (`unavailable_incomplete`, each
  entry with a stated reason). `tools/build_regression.py` flags large swings in the reason-code counts.
