# WashU deep dive, 2026-11-09 (branch agent/washu-deepdive)

Scope: census, historical listings, papers, students, full texts, websites for the 2026-11-07 partial package.

- Listings: the engineering Bulletin PDFs (bulletin.wustl.edu/about/prior/) give a dated faculty section per department and edition
  (`tools/washu_bulletin_listings.py`, manifest `reviewed/bulletin-listing-sources.json`; the row year is the document's printed date).
  Wayback adds CSE/ESE/BME 2020-2026. All 28 department-years without evidence are closed. MEMS and EECE joined the charter as affiliated departments.
- CS-related review: 228 candidates, 17 accepted. Units are read live only (`UNITS_LIVE_ONLY=1`); the Wayback years are queued.
- Identity: 15 hand-reviewed OpenAlex ids for the new PIs (`reviewed/openalex-identity-review.json`); held: Bobick, Stern, Lee, Schaettler, Liu, Bogost, Turner.
- R-STU-23 extension: see `reviewed/thesis-committee-chair-held.json` for each collection (rows, hand check, status). The Open Scholarship host answered 403
  at art_sci_etds/3562 after about 300 requests; the crawl stopped and was not retried.
- Overlay: `tools/overlay_root.py --private-data` keeps every write out of main's derived/raw/listings. Built outputs live in
  code/hierarchy/washu/tmp/dd-overlay/.
