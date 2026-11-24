# Local copy eligibility

`tools/copy_quality.py` checks actual assets independently of work identity,
university/date eligibility and redistribution permission. A failed asset leaves
the target work in its bibliography and needing a suitable copy. It is never a
work-level `nonresearch` decision.

Full-text XML needs substantive article-body paragraphs. Metadata, an abstract,
an empty `body`, or a PMC “Full Text Availability” rights notice does not supply
the article. The observed notice says: “The license terms selected by the
author(s) for this preprint version do not permit archiving in PMC. The full text
is available from the preprint server.” A body element alone is insufficient.
Short complete letters can have one paragraph; no three-paragraph or 1,000-character
quota is imposed. Namespaces and comments are supported; external entities are
not resolved and no network access occurs.
The conservative lower bound is 200 body-text characters. A shorter XML body is
quality-unconfirmed; that is not evidence that the underlying work is nonresearch.

XML paths, SHA256, sizes, identities, versions and licences come from the XML
asset itself. A `fulltext_xml` work row can still retain an old quarantined PDF's
fields. Those fields neither qualify a stub nor hide a good XML asset, and an
XML licence cannot authorize the older PDF hash. A valid same-work alternative
can qualify when another asset fails.

PDF checks require successful local parsing and reject explicit panel/SIG
descriptions or slide-deck evidence. Slide metadata must be corroborated by
bullet-slide content without a narrative article heading. A paper merely
discussing panels, or an ordinary short paper, is preserved. These checks are an
asset-quality guard, not a replacement for a complete physical identity audit.
Fewer than 200 extractable characters on the first three PDF pages is also
quality-unconfirmed, without classifying the work; this holds title-only or
unreadable-text assets rather than treating parseability alone as a full paper.

`lab_paper_copies.run`, `reader_export.school_rows` and the collectors' shared
catalog state apply the guard. Coverage records `copy_quality_unconfirmed` and
`copy_quality_reason` when actual assets fail. Export cannot qualify a copy from
catalog status alone. Checks use indexed catalog lookups, never source writes;
only accepted identity candidates are checked lazily by the counter/reader.
The collector's shared state checks its local rows. Parsed results are cached
within the process by actual path/device/inode/size/mtime and format; changed
files are rechecked. Both PDF and XML bytes are hashed and measured, and must
match the selected asset's own expected SHA256 and size. A parseable replacement
PDF cannot inherit stale catalog identity. Cold checks read local files and can take longer than a
metadata-only coverage count, so production rebuilds remain Slurm work.

Future lab-first loop and Princeton pass starts use
`fulltext-push/collector_quality.py`. It retains the unchanged vendored wrapper's
robots, redirect, pacing, retry, identity and catalog-lock behavior and rejects
inadequate bytes before successful admission. Other candidates can still be
tried. Already running collectors are not stopped, rewritten or reloaded by this
change. Direct legacy vendor entrypoints remain legacy entrypoints; use the
guarded entrypoint for new starts.

The 2026-11-08 offline audit's 205 supported reuse plans, 22 held targets and six
failed reuse assets remain separate review artifacts. Eleven of its 1,990 XML
entries contained notice-only bodies. No local import, canonical promotion,
public hosting or redistribution is authorized by an eligibility result.
