# DBLP-listed works confirmed by page 1 (R-PAP-36)

Decided by the owner on 2026-11-05 ("yes"); rule text in `docs/RULES.md` R-PAP-36. This note keeps the design, the evidence rules, the risks and what the first
scratch run measured. The tool is `tools/dblp_recover.py` (the 2026-10-22 DBLP recovery, extended); the builder reads its output as `RECOVERED_KINDS` `dblp`
(`tools/pihier/papers.py::recovered_rows`).

## The case
The round-r2 coverage samples missed true lab papers that the PI's DBLP person page lists and OpenAlex either lacks or gives the PI no school (MIT: Devadas IACR ePrint 2021,
Mossel NeurIPS 2022, Shah JMLR 2025, Freund COLT 2022; Berkeley, Michigan, Stanford and Princeton had the same type). About 8 of the 11 round-r2 coverage misses were this case.

## What was wrong before
1. The recovery's candidates came from the cached DBLP lists of the 2026-10 census queries (pre-protocol schools), which hold only what those queries returned. Mossel's 2022 NeurIPS paper
   and Freund's COLT paper were never candidates. Now: the cached lists plus the PI's full person page from the DBLP dump (`dump_pubs`), de-duplicated by bare key.
2. A record only the dump has carries no `ee` (the dump extract keeps no links); `ee` now comes from the dump XML (`dump_ee`, one streaming pass per run, never dblp.org: it
   answers automated clients with a challenge page).
3. JMLR volume pages were not mapped to their PDFs (Shah 2025). IACR ePrint is **not** asked: `eprint.iacr.org` answers automated clients with a Cloudflare challenge and its robots.txt
   carries an AI policy against using the PDFs, so Devadas's 2021 ePrint paper stays unconfirmed (Wayback has no copy to use either).
4. A record with no page-1 evidence was `not_recovered` and forgotten. Now: status `dblp_unconfirmed` with a reason (`no_open_page1_source`, `page1_fetch_failed`,
   `page1_read_school_not_named`), `--retry` asks again.

## Evidence rules (all must hold)
- the DBLP key is on the PI's own DBLP person page (the dump, or a reviewed pid in the census overrides); an id whose person names contradict the PI's middle name is dropped (R-PAP-35);
- the year is inside a dated appointment (a reviewed period, or a captured listing year) by the existing period rules; the builder re-applies them when the row is made;
- the work is not already a lab paper (title or DOI) and passes the not-a-paper rules (R-PAP-18/19/27/31/33) at build time;
- OpenAlex by DOI first: an authorship at the PI's name that lists the school is accepted (`openalex_authorship`); one that lists only other institutions is left out (the PI was elsewhere);
- otherwise page 1 of the paper names the school for the PI (`pi_fulltext_affiliation.tie`: marker, near, footnote, or single institution) from arXiv v1 (public GCS bulk copy) or an open PDF on a
  proceedings host (ACL Anthology, PMLR, CVF, NeurIPS, USENIX, IJCAI, AAAI, OpenReview, JMLR); robots.txt first, `host_throttle` slots shared with the download loops (3 s, 429 cooldowns);
  no paywall, login or bot challenge is ever worked around;
- the row records `school_via: ['page1_dblp: <key>', 'page 1 (<how>): ...']`, the PDF url and sha256, the quotes, the DBLP key and the fetch time.

## Not used
- publisher landing text (no open source gives affiliations there under these rules); ACM DL, IEEE Xplore, Springer, Elsevier: paywalled or refusing automated clients;
- a name match alone, or an advisee on the byline without page 1 (that is R-PAP-11/12's route for OpenAlex works, not for DBLP-only records).

## Risks
- A DBLP person page of a PI who shares a name with another DBLP person mixes records (Newman). The census id is checked against the PI's middle name (R-PAP-35); nothing else
  separates two same-named people on one page, so rows rest on page 1 or an OpenAlex authorship, never on the page alone.
- Page 1 may name the school for a different author of the same name; `tie` requires the PI's own name with the marker, or within 160 characters, or the only institution of the block.
- Dual affiliations: a school named next to a company on the PI's line counts (the paper credits the school); the appointment check still limits the year.
- The unconfirmed ledger is not a coverage claim: those records are unverified, not wrong. Most are IEEE, ACM or Springer papers with no open copy.

## Measured (scratch, 2026-11-05)
Per school, records tried and how they ended (confirmed by an OpenAlex authorship at the PI's name that lists the school, by page 1 from arXiv, by page 1 from an open PDF; not confirmed with the reason;
OpenAlex says another institution): see the report of the 2026-11-05 accuracy-fixes run (`accuracy/FIXES-20261105.md` is not kept; numbers are in the commit message of the rebuild and the coordinator's report).
