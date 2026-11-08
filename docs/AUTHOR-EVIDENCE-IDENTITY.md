# Author evidence for local-copy identity checks

`identity_rule.first_author` and `review_identity.authors_of` borrow names only
through exact work/OpenAlex identifiers or an unambiguous normalized DOI.
Normalized titles never join author records, including legacy title keys supplied
by callers. Exact own-record identities take priority over DOI fallback.

The author indexes track source-work identity even when a record has no readable
author names. Distinct works claiming the same DOI make that DOI lookup ambiguous;
matching family names do not resolve the ambiguity. Repeated lab relations for
one work remain one source. A cached OA record explicitly listed among a native
paper's accepted editions shares that declared identity group; a similar title
does not establish such a group.

An ordered author/byline list in the record itself remains direct author evidence.
Generic school membership stays weak evidence and cannot be invented as an
authoritative first author when the full paper byline is absent.

This changes evidence selection for future identity checks. It does not alter
catalogs, stored assets, paper admission, aliases, prior receipts or publication
metadata. Existing wrong-DOI collisions require separate source correction and
review; an ambiguous DOI here supplies no borrowed authors.
