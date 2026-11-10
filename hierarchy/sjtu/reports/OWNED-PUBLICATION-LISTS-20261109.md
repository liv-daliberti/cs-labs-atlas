# Owned publication lists, 2026-11-09 (T115)

Source class: titles listed verbatim on the PI-named official SJTU profile or on the owned homepage that the official profile links (website status `verified_website`). Offline scan of the cached page bytes against the 303,961 stored works (`scratch/sjtu-ownedlists-1109/scan_lists.py`, job 32177405): a work is a candidate only if its normalized title (28+ characters) occurs verbatim in the page text and the page states the work's year (or one year either side) within 220 characters. Every record in `reviewed/pi-publication-lists.json` carries url, page sha256, observed time and a verbatim quote.

This file is a separate input from the DBLP-derived person records. It is read by the native as the `pi_institutional_publication_list` identity route: a work also needs a byline name matching the PI alias, the exact listed title within one year, and the ordinary school, appointment and type gates.

PIs without an owned DBLP record are un-held only when the byline alias is evidenced: the alias is the byline name present in at least 60 percent of the PI's listed works and consistent with the profile URL slug (王士林 added by hand: two spellings, 17 of 17 works). 84 PIs were un-held this way, 20 PIs with DBLP bindings also gain a list, 104 lists and 2445 records in total. Faculty periods are unchanged: a PI without a dated period contributes only works dated to the 2026 listing year.

Also held: 沈为 "Image Stitching" (book chapter), from the corrected 27-PID package.
