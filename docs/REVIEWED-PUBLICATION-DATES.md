# Reviewed publication dates

An indexed acceptance date can be corrected from the original publisher JATS
article in `reviewed/publication-date-review.json`. Version 1 decisions name the
school, exact OpenAlex work and DOI, original title and former indexed date, an
explicit review and reason, and the corrected publication day.
This route corrects the day within the unchanged indexed publication year.

Store original HTTP-200 XML privately as
`stores/<school>/metadata/publication-date-sources/<sha256>.xml`. The source record
names its HTTPS URL, capture time, format `jats_xml`, SHA-256 and hash-named file.
The builder rehashes the original and reads only its own front/article-meta:
DOI and title must match, and an explicit electronic publication date must give
the reviewed day. Acceptance/history, issue collection and print dates cannot
supply this correction. Missing, altered, ambiguous or stale evidence stops the
build. Indexed records remain unchanged.

The corrected date runs before the ordinary appointment and window checks.
Identity, school affiliation, paper type and edition rules still apply. Native
records retain the old indexed date, original source and review under `dated_by`.
