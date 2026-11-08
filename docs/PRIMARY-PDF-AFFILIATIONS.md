# Primary PDF author affiliations

An optional `author_affiliation_review` inside a standard `pi-works.sqlite` page-one quote record can document a complete,
individually reviewed set of author blocks. `pihier.primary_affiliations` validates exact work/edition DOI, canonical source
work and raw authorship hashes, the complete ordered raw byline and original author IDs, the original PDF hash/URL, exact
stored page-one text hash, and one named non-overlapping affiliation block per author. Coordinates and block quotations
are extracted from the primary PDF and independently reviewed; they do not identify an OpenAlex author entity by name.

The module returns an explicit hold for wrong sources, changed/missing/ambiguous names, missing blocks, invalid quotations
or coordinates. A hold supplies no replacement flags. Existing flags must stay unchanged and the hold must remain visible
for promotion review; no neighboring author's school is borrowed. An unrequested review leaves existing behavior intact.

A valid review supplies only a derived view for the existing school/campus predicate and its full primary-source evidence.
Original OpenAlex work/authorship bytes remain unchanged. Paper identity, own PI affiliation/admission, faculty timing,
research-type/edition checks, membership roles and candidate-author status remain governed by their existing rules. The
caller must preserve the ordinary own-PI page-one route and all source distinctions, and must report exact candidate-link
effects separately. This module alone does not change the native builder or certify any package.
Each affiliation entry is a complete institutional statement, joining its source address/department/campus lines where
necessary; distinct institutional statements stay separate. Every word of an author block must be represented by its
name or affiliation statements. The existing school predicate is called with the school key, including its excluded-campus
guard; the derived view never lends an old institution ID to a corrected author.
