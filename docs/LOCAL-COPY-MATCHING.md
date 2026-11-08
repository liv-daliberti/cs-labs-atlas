# Local-copy identity matching

`ftp_common.match_work` and `is_local` use the accepted work identifier, OpenAlex
identifier, normalized DOI, arXiv DOI, explicit accepted editions and catalog
aliases. Their candidate order agrees with `lab_paper_copies.resolve`: search all
exact candidates for an eligible local record, then retain the first exact record
when none is local. A queued primary identifier must not hide a local edition.

Normalized titles remain discovery hints. A same-title record, agreement on year
or an unreviewed author similarity cannot suppress a missing-paper seed or prove
that its bytes belong to the target. The actual “Mind the gap” audit case contains
distinct 2017 VLDB and 2019 HotNets papers with different DOIs.

Catalog state must pass the existing identity and copy-quality checks before a
record is eligible. An old title/DOI entry in the convenience `local` set does not
override an ineligible status. Asset-quality failures do not classify the target
work itself as nonresearch.

Offline reuse proposals bind canonical target identifiers to independently
reviewed source paths, actual hashes, sizes and content evidence. They are plans,
not imports or public redistribution permission. Before any later apply, acquire
the destination catalog writer lock, create its required backup **before** the
first write, and revalidate the planned canonical target, source bytes and current
destination state. A later preimage recovery audit does not replace a missing
before-write backup.
