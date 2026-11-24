# Rights and citation (owner decision 2026-11-05)

The atlas data and the site content are © 2026 Liv d'Aliberti under **CC BY-NC 4.0**. AI training and scraping bots are
blocked (signals, not enforcement: see the end), normal search engines are kept, and users are asked to cite a **Zenodo dataset
DOI** minted from the public GitHub repository's releases. Not legal advice: these are the owner's chosen terms.

## Placeholders: one edit each

| Placeholder | Defined in | Flows to | Status |
|---|---|---|---|
| owner name (`Liv d'Aliberti`) | `tools/rights/rights.json` `owner_name`, `given_names`, `family_names` (code repo); `scripts/rights/rights.json` (site repo, same values) | LICENSE, NOTICE, CITATION.cff, .zenodo.json, README "How to cite", HF card, site footer, site terms page | filled |
| `{{ZENODO_DOI}}` | the same two files, key `zenodo_doi` | the citation, BibTeX and the `# doi:` line of CITATION.cff (becomes `doi:` when real), HF card, site terms page | set 2026-11-05: concept DOI 10.5281/zenodo.23988437 (all versions); release 2026-10-29.4 is version DOI 10.5281/zenodo.23988438 |
| `{{CONTACT}}` | the same two files, key `contact` | NOTICE, README, HF card, site terms page (how to ask for commercial use) | filled: the GitHub issues page |
| ORCID | none found | left out everywhere | not used |

Code repo: edit `tools/rights/rights.json`; the next `tools/export_release.py` run renders everything into the public repo.
Site repo: edit `scripts/rights/rights.json`, then run `python3 scripts/apply-rights.py` (it rewrites the footers, meta tags and the
terms page; `npm test` fails while they are out of date). No e-mail address belongs in either file.

## The owner's Zenodo steps (not done by an agent)

1. Log in to zenodo.org with GitHub.
2. In Zenodo's GitHub settings, switch on the `cs-labs-atlas` repository.
3. Publish a GitHub release of the public repo (the export carries `.zenodo.json` and `CITATION.cff`).
4. Copy the DOI Zenodo mints (use the concept DOI for "all versions"), set `zenodo_doi` in both `rights.json` files, re-export, and
   re-run the site's `apply-rights.py`. Then uncomment nothing by hand: the generators switch `# doi:` to `doi:`.

## What enforcement exists and what does not

- `robots.txt` (AI crawlers disallowed, search engines allowed), `/.well-known/tdmrep.json`, the `tdm-reservation` meta tag and headers,
  and `noai, noimageai` are honoured only by compliant crawlers. They also state the reservation of text-and-data-mining rights
  (EU Directive 2019/790 Art. 4(3)), which is the legal value.
- Real blocking of non-compliant scrapers needs host-level bot protection or rate limits (WAF rules, user-agent and ASN blocks, a
  bot-management product). That belongs in the hosting configuration, not in this repository.
- The licence itself (CC BY-NC) is not a technical control; it governs what a person may do with data they hold.
